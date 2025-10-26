#!/usr/bin/env python3
"""
Import code examples from Hugging Face datasets with quality filtering.

Usage:
    # Test with small batch (streaming, no download)
    python import_huggingface_examples.py --test --language Python --max 10

    # Import from BigCodeReward (small dataset, ~10GB)
    python import_huggingface_examples.py --dataset bigcodereward --max 100

    # Import from GitHub Code 2025 (quality-focused, ~100GB)
    python import_huggingface_examples.py --dataset github-2025 --quality-only --max 500

    # Stream from The Stack (no download)
    python import_huggingface_examples.py --dataset the-stack --language Python --max 50
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional, Iterator
from datasets import load_dataset
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from code_example_types import CodeExample
from populate_code_examples import CodeExamplePopulator


class HuggingFaceImporter:
    """Import and filter code examples from Hugging Face datasets"""

    def __init__(self, min_quality_score: int = 70, verbose: bool = True):
        """
        Initialize importer.

        Args:
            min_quality_score: Minimum quality score to accept (1-100)
            verbose: Print progress messages
        """
        self.min_quality_score = min_quality_score
        self.verbose = verbose
        self.populator = CodeExamplePopulator()

        # Statistics
        self.stats = {
            'processed': 0,
            'accepted': 0,
            'rejected_size': 0,
            'rejected_quality': 0,
            'rejected_structure': 0
        }

    def import_from_bigcode_reward(
        self,
        max_examples: int = 100
    ) -> List[CodeExample]:
        """
        Import from BigCodeReward dataset (~10GB).
        Contains validated code conversations.

        Args:
            max_examples: Maximum examples to import

        Returns:
            List of CodeExample objects
        """
        if self.verbose:
            print("📥 Loading BigCodeReward dataset...")
            print("   Size: ~10GB")
            print("   Contains: 14K+ validated code conversations")

        try:
            ds = load_dataset("bigcode/bigcodereward", split="train", streaming=True)
        except Exception as e:
            print(f"❌ Error loading BigCodeReward: {e}")
            print("   This dataset may require authentication or acceptance of terms.")
            return []

        examples = []

        if self.verbose:
            pbar = tqdm(total=max_examples, desc="Importing examples")

        for item in ds:
            self.stats['processed'] += 1

            # Extract code and metadata
            code = item.get('code', '') or item.get('solution', '')
            language = item.get('language', 'Unknown')

            if not code or not language:
                continue

            # Quality check
            if not self._passes_quality_check(code, language):
                continue

            # Create example
            example = self._create_code_example(
                code=code,
                language=language,
                pattern=self._detect_pattern(code),
                title=f"Solution from BigCodeReward",
                description=item.get('question', 'Code solution from BigCodeReward'),
                source="BigCodeReward"
            )

            if example and example.quality_score >= self.min_quality_score:
                examples.append(example)
                self.stats['accepted'] += 1

                if self.verbose:
                    pbar.update(1)

                if len(examples) >= max_examples:
                    break

        if self.verbose:
            pbar.close()
            self._print_stats()

        return examples

    def import_from_github_code_2025(
        self,
        quality_only: bool = True,
        max_examples: int = 500
    ) -> List[CodeExample]:
        """
        Import from GitHub Code 2025 dataset (~100GB).
        Quality-focused, curated for 2025.

        Args:
            quality_only: Only import from "above-2-stars" subset
            max_examples: Maximum examples to import

        Returns:
            List of CodeExample objects
        """
        subset = "above-2-stars" if quality_only else "below-2-star"

        if self.verbose:
            print(f"📥 Loading GitHub Code 2025 ({subset})...")
            print(f"   Size: ~{'50-100' if quality_only else '50'} GB")
            print("   Contains: 1.5M+ repositories (2025 curated)")
            print("   ⚠️  This will download data - may take some time!")

        try:
            ds = load_dataset(
                "nick007x/github-code-2025",
                subset,
                split="train",
                streaming=True  # Stream to avoid full download immediately
            )
        except Exception as e:
            print(f"❌ Error loading GitHub Code 2025: {e}")
            return []

        examples = []

        if self.verbose:
            pbar = tqdm(total=max_examples, desc="Importing examples")

        for item in ds:
            self.stats['processed'] += 1

            # Extract code and metadata
            code = item.get('content', '') or item.get('code', '')
            file_path = item.get('path', '')
            repo_name = item.get('repo_id', '') or item.get('repository', '')

            if not code:
                continue

            # Detect language from file extension
            language = self._detect_language_from_path(file_path)

            if not language:
                continue

            # Quality check
            if not self._passes_quality_check(code, language):
                continue

            # Create example
            example = self._create_code_example(
                code=code,
                language=language,
                pattern=self._detect_pattern(code),
                title=f"{Path(file_path).name} ({repo_name})",
                description=f"Real-world code from {repo_name}",
                source=f"GitHub 2025 ({subset})"
            )

            if example and example.quality_score >= self.min_quality_score:
                examples.append(example)
                self.stats['accepted'] += 1

                if self.verbose:
                    pbar.update(1)

                if len(examples) >= max_examples:
                    break

        if self.verbose:
            pbar.close()
            self._print_stats()

        return examples

    def import_from_the_stack(
        self,
        language: str,
        max_examples: int = 50
    ) -> List[CodeExample]:
        """
        Import from The Stack dataset (streaming, no download).
        Contains 358 languages, 6TB total.

        Args:
            language: Programming language (Python, Rust, Java, etc.)
            max_examples: Maximum examples to import

        Returns:
            List of CodeExample objects
        """
        if self.verbose:
            print(f"📥 Streaming from The Stack ({language})...")
            print("   Size: Streaming (no download)")
            print(f"   Total dataset: 6TB across 358 languages")

        try:
            ds = load_dataset(
                "bigcode/the-stack",
                data_dir=f"data/{language.lower()}",
                split="train",
                streaming=True  # IMPORTANT: Streaming mode
            )
        except Exception as e:
            print(f"❌ Error loading The Stack: {e}")
            print("   This dataset may require authentication or acceptance of terms.")
            return []

        examples = []

        if self.verbose:
            pbar = tqdm(total=max_examples, desc="Importing examples")

        for item in ds:
            self.stats['processed'] += 1

            # Extract code and metadata
            code = item.get('content', '')
            file_path = item.get('max_stars_repo_path', '') or item.get('path', '')
            repo_name = item.get('max_stars_repo_name', 'unknown')

            if not code:
                continue

            # Quality check
            if not self._passes_quality_check(code, language):
                continue

            # Create example
            example = self._create_code_example(
                code=code,
                language=language,
                pattern=self._detect_pattern(code),
                title=f"{Path(file_path).name if file_path else 'Code Example'}",
                description=f"From {repo_name} (The Stack)",
                source="The Stack"
            )

            if example and example.quality_score >= self.min_quality_score:
                examples.append(example)
                self.stats['accepted'] += 1

                if self.verbose:
                    pbar.update(1)

                if len(examples) >= max_examples:
                    break

        if self.verbose:
            pbar.close()
            self._print_stats()

        return examples

    def _passes_quality_check(self, code: str, language: str) -> bool:
        """
        Quality filtering heuristics.

        Returns:
            True if code passes quality checks
        """
        # Size check (not too small, not too large)
        if len(code) < 100:
            self.stats['rejected_size'] += 1
            return False

        if len(code) > 10000:  # Increased from 5000 for real-world code
            self.stats['rejected_size'] += 1
            return False

        # Has structure (functions/classes)
        has_structure = any([
            re.search(r'\bclass\s+\w+', code),
            re.search(r'\bdef\s+\w+', code),
            re.search(r'\bfunction\s+\w+', code),
            re.search(r'\bfn\s+\w+', code),
            re.search(r'\bpublic\s+\w+\s+\w+\(', code),
        ])

        if not has_structure:
            self.stats['rejected_structure'] += 1
            return False

        return True

    def _detect_language_from_path(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension"""
        ext_to_lang = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.rs': 'Rust',
            '.go': 'Go',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.hs': 'Haskell',
            '.erl': 'Erlang',
            '.R': 'R',
            '.m': 'MATLAB',
        }

        ext = Path(file_path).suffix.lower()
        return ext_to_lang.get(ext)

    def _detect_pattern(self, code: str) -> str:
        """Attempt to detect design pattern from code"""
        patterns = [
            ("Repository", [r'Repository', r'find_by', r'save']),
            ("Factory", [r'Factory', r'create']),
            ("Strategy", [r'Strategy', r'execute']),
            ("Observer", [r'Observer', r'notify', r'subscribe']),
            ("Singleton", [r'Singleton', r'instance']),
            ("Builder", [r'Builder', r'build']),
        ]

        for pattern, indicators in patterns:
            if any(re.search(ind, code, re.IGNORECASE) for ind in indicators):
                return pattern

        return "General"

    def _create_code_example(
        self,
        code: str,
        language: str,
        pattern: str,
        title: str,
        description: str,
        source: str
    ) -> Optional[CodeExample]:
        """Create CodeExample from imported code"""

        # Calculate quality score
        quality_score = self._calculate_quality_score(code, language)

        if quality_score < self.min_quality_score:
            self.stats['rejected_quality'] += 1
            return None

        # Detect complexity
        complexity = self._detect_complexity(code)

        # Extract concepts
        demonstrates = self._extract_concepts(code, language)

        return CodeExample(
            language=language,
            pattern=pattern,
            title=title[:100],  # Limit title length
            description=description[:200],  # Limit description
            code=code,
            quality_score=quality_score,
            tags=[language.lower(), pattern.lower(), "huggingface", source.lower().replace(' ', '-')],
            complexity=complexity,
            demonstrates=demonstrates,
            prevents=[]  # Could be inferred with more analysis
        )

    def _calculate_quality_score(self, code: str, language: str) -> int:
        """Calculate quality score (1-100) based on heuristics"""
        score = 50  # Base score

        # Has docstrings/comments (+20)
        if re.search(r'("""|\'\'\'/\*\*|//)', code):
            score += 20

        # Has type hints/annotations (+10)
        if language == "Python" and re.search(r':\s*\w+\s*->', code):
            score += 10
        elif language in ["TypeScript", "Java", "C++"] and re.search(r':\s*\w+', code):
            score += 10

        # Has error handling (+10)
        if re.search(r'(try|catch|except|raise|throw|Result|Option)', code):
            score += 10

        # Well-formatted (has indentation) (+5)
        if re.search(r'^    \w', code, re.MULTILINE) or re.search(r'^\t\w', code, re.MULTILINE):
            score += 5

        # Reasonable length (+5)
        if 500 <= len(code) <= 3000:
            score += 5

        return min(score, 100)

    def _detect_complexity(self, code: str) -> str:
        """Detect complexity level"""
        lines = code.count('\n')

        if lines < 50:
            return "beginner"
        elif lines < 200:
            return "intermediate"
        else:
            return "advanced"

    def _extract_concepts(self, code: str, language: str) -> List[str]:
        """Extract programming concepts from code"""
        concepts = []

        concept_patterns = {
            "Error Handling": r'(try|catch|except|raise|throw)',
            "Type Hints": r':\s*\w+\s*->',
            "Async/Await": r'(async|await)',
            "Generics": r'<\w+>',
            "Pattern Matching": r'match\s+\w+',
            "Decorators": r'@\w+',
        }

        for concept, pattern in concept_patterns.items():
            if re.search(pattern, code):
                concepts.append(concept)

        return concepts if concepts else ["General"]

    def _print_stats(self):
        """Print import statistics"""
        print("\n" + "=" * 70)
        print("Import Statistics")
        print("=" * 70)
        print(f"Processed: {self.stats['processed']}")
        print(f"Accepted:  {self.stats['accepted']} ✅")
        print(f"Rejected (size): {self.stats['rejected_size']}")
        print(f"Rejected (structure): {self.stats['rejected_structure']}")
        print(f"Rejected (quality): {self.stats['rejected_quality']}")
        print(f"Acceptance Rate: {(self.stats['accepted'] / max(self.stats['processed'], 1)) * 100:.1f}%")
        print("=" * 70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Import code examples from Hugging Face datasets"
    )
    parser.add_argument(
        "--dataset",
        choices=["bigcodereward", "github-2025", "the-stack"],
        default="the-stack",
        help="Which dataset to import from"
    )
    parser.add_argument(
        "--language",
        type=str,
        default="Python",
        help="Programming language (for The Stack)"
    )
    parser.add_argument(
        "--quality-only",
        action="store_true",
        help="Only import high-quality examples (for GitHub 2025)"
    )
    parser.add_argument(
        "--max",
        type=int,
        default=50,
        help="Maximum examples to import"
    )
    parser.add_argument(
        "--min-quality",
        type=int,
        default=70,
        help="Minimum quality score (1-100)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode (import only 10 examples)"
    )
    parser.add_argument(
        "--populate-rag",
        action="store_true",
        help="Populate RAG database with imported examples"
    )
    parser.add_argument(
        "--populate-kg",
        action="store_true",
        help="Populate Knowledge Graph with imported examples"
    )

    args = parser.parse_args()

    # Test mode overrides
    if args.test:
        args.max = 10
        print("🧪 TEST MODE: Importing only 10 examples")

    # Initialize importer
    importer = HuggingFaceImporter(min_quality_score=args.min_quality)

    # Import examples based on dataset choice
    print(f"\n🚀 Starting import from {args.dataset}")
    print(f"   Quality threshold: {args.min_quality}/100")
    print(f"   Max examples: {args.max}\n")

    examples = []

    try:
        if args.dataset == "bigcodereward":
            examples = importer.import_from_bigcode_reward(max_examples=args.max)

        elif args.dataset == "github-2025":
            examples = importer.import_from_github_code_2025(
                quality_only=args.quality_only,
                max_examples=args.max
            )

        elif args.dataset == "the-stack":
            examples = importer.import_from_the_stack(
                language=args.language,
                max_examples=args.max
            )

    except KeyboardInterrupt:
        print("\n\n⚠️  Import interrupted by user")
        print(f"   Imported {len(examples)} examples before interruption")

    # Show results
    print(f"\n✅ Successfully imported {len(examples)} examples")

    if examples:
        print("\nSample examples:")
        for i, ex in enumerate(examples[:3], 1):
            print(f"  {i}. [{ex.language}] {ex.title}")
            print(f"     Quality: {ex.quality_score}/100 | Complexity: {ex.complexity}")

    # Populate RAG/KG if requested
    if examples and (args.populate_rag or args.populate_kg):
        print("\n" + "=" * 70)
        populator = importer.populator

        if args.populate_rag:
            print("📝 Populating RAG database...")
            rag_count = populator.populate_rag(examples)
            print(f"   ✅ Stored {rag_count} examples in RAG")

        if args.populate_kg:
            print("🕸️  Populating Knowledge Graph...")
            kg_count = populator.populate_knowledge_graph(examples)
            print(f"   ✅ Created {kg_count} KG relationships")

        print("=" * 70)

    print(f"\n🎉 Import complete!")


if __name__ == "__main__":
    main()
