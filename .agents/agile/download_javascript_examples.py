#!/usr/bin/env python3
"""
Download JavaScript code examples from HuggingFace CodeSearchNet and store in ChromaDB.

This script:
1. Downloads JavaScript functions from CodeSearchNet dataset
2. Filters for high-quality examples with documentation
3. Stores examples in ChromaDB/RAG for code generation assistance
4. Creates knowledge graph relationships

Usage:
    python download_javascript_examples.py --limit 1000
    python download_javascript_examples.py --quality-min 0.8 --limit 500
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from rag_agent import RAGAgent
from knowledge_graph_factory import get_knowledge_graph


class JavaScriptExampleDownloader:
    """Downloads and stores JavaScript examples from CodeSearchNet"""

    def __init__(self, rag_agent: Optional[RAGAgent] = None):
        """
        Initialize downloader.

        Args:
            rag_agent: RAG agent for storing examples (optional)
        """
        self.rag = rag_agent or RAGAgent()
        self.kg = get_knowledge_graph()

    def download_from_huggingface(
        self,
        limit: int = 1000,
        quality_min: float = 0.5
    ) -> List[Dict]:
        """
        Download JavaScript examples from HuggingFace CodeSearchNet.

        Args:
            limit: Maximum number of examples to download
            quality_min: Minimum quality threshold (0.0-1.0)

        Returns:
            List of JavaScript code examples
        """
        try:
            from datasets import load_dataset
            import os
        except ImportError:
            print("❌ Error: 'datasets' library not installed")
            print("Install with: pip install datasets")
            sys.exit(1)

        # Load HF token from environment
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            print("❌ Error: HF_TOKEN not found in environment")
            print("Set HF_TOKEN in .env file or environment")
            sys.exit(1)

        print(f"📥 Downloading JavaScript examples from GitHub Code (codeparrot)...")
        print(f"   Limit: {limit}, Quality threshold: {quality_min}")

        try:
            # Load dataset with JavaScript filter from codeparrot
            dataset = load_dataset(
                "codeparrot/github-code",
                split="train",
                streaming=True,  # Use streaming to avoid downloading entire dataset
                languages=["JavaScript"],  # Filter for JavaScript only
                token=hf_token  # Use HF token for authentication
            )

            examples = []
            seen_functions = set()  # Deduplicate

            for i, item in enumerate(dataset):
                if len(examples) >= limit:
                    break

                # Extract code (codeparrot schema uses 'code' field)
                code = item.get('code', '')

                # Skip if no code or very short
                if not code or len(code) < 100:
                    continue

                # Extract documentation from comments
                docstring = self._extract_documentation(code)

                # Skip if no documentation found
                if len(docstring) < 20:
                    continue

                # Deduplicate based on code hash
                code_hash = hash(code)
                if code_hash in seen_functions:
                    continue
                seen_functions.add(code_hash)

                # Calculate simple quality score
                quality_score = self._calculate_quality_score(code, docstring)
                if quality_score < quality_min:
                    continue

                # Extract function name from code
                func_name = self._extract_function_name(code)

                # Extract metadata
                example = {
                    'code': code,
                    'documentation': docstring,
                    'language': 'JavaScript',
                    'quality_score': quality_score,
                    'repo': item.get('repo_name', 'unknown'),
                    'path': item.get('path', 'unknown'),
                    'func_name': func_name,
                    'url': ''
                }

                examples.append(example)

                if (i + 1) % 100 == 0:
                    print(f"   Processed {i + 1} items, collected {len(examples)} quality examples")

            print(f"✅ Downloaded {len(examples)} JavaScript examples")
            return examples

        except Exception as e:
            print(f"❌ Error downloading from HuggingFace: {e}")
            sys.exit(1)

    def _extract_documentation(self, code: str) -> str:
        """
        Extract documentation from JavaScript comments.

        Looks for:
        - JSDoc style comments (/** ... */)
        - Multi-line comments at start of functions
        - Single-line comments before functions

        Args:
            code: JavaScript code

        Returns:
            Extracted documentation string
        """
        import re

        # Look for JSDoc comments
        jsdoc_pattern = r'/\*\*\s*(.*?)\s*\*/'
        jsdoc_matches = re.findall(jsdoc_pattern, code, re.DOTALL)

        if jsdoc_matches:
            # Return longest JSDoc comment
            return max(jsdoc_matches, key=len)

        # Look for multi-line comments
        multiline_pattern = r'/\*\s*(.*?)\s*\*/'
        multiline_matches = re.findall(multiline_pattern, code, re.DOTALL)

        if multiline_matches:
            return max(multiline_matches, key=len)

        return ""

    def _extract_function_name(self, code: str) -> str:
        """
        Extract function name from JavaScript code.

        Args:
            code: JavaScript code

        Returns:
            Function name or 'anonymous'
        """
        import re

        # Look for function declarations
        patterns = [
            r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)',  # function name()
            r'const\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=',  # const name =
            r'let\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=',    # let name =
            r'var\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=',    # var name =
            r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:\s*function', # name: function
        ]

        for pattern in patterns:
            match = re.search(pattern, code)
            if match:
                return match.group(1)

        return "anonymous"

    def _calculate_quality_score(self, code: str, docstring: str) -> float:
        """
        Calculate quality score for code example.

        Factors:
        - Has documentation (docstring)
        - Code length (not too short, not too long)
        - Documentation quality (length, completeness)

        Args:
            code: Function code
            docstring: Documentation string

        Returns:
            Quality score (0.0-1.0)
        """
        score = 0.5  # Base score

        # Documentation quality (0-0.3)
        if len(docstring) > 100:
            score += 0.2
        elif len(docstring) > 50:
            score += 0.1

        # Code length (0-0.2)
        code_lines = len(code.split('\n'))
        if 20 <= code_lines <= 200:
            score += 0.2
        elif 10 <= code_lines <= 300:
            score += 0.1

        # Has parameters documented (0-0.1)
        if '@param' in docstring or 'param' in docstring:
            score += 0.1

        # Has return documented (0-0.1)
        if '@return' in docstring or 'return' in docstring:
            score += 0.1

        return min(score, 1.0)

    def store_in_rag(self, examples: List[Dict]) -> int:
        """
        Store JavaScript examples in RAG database.

        Args:
            examples: List of JavaScript examples

        Returns:
            Number of examples stored
        """
        count = 0

        for example in examples:
            # Create comprehensive content for RAG
            content = f"""
# {example['func_name']}

**Language:** JavaScript
**Repository:** {example['repo']}
**Quality Score:** {example['quality_score']:.2f}

## Documentation
{example['documentation']}

## Code

```javascript
{example['code']}
```

## Source
- Path: {example['path']}
- URL: {example['url']}
"""

            # Store in RAG with rich metadata
            self.rag.store_artifact(
                artifact_type="code_example",
                card_id=f"js_example_{count}",
                task_title=example['func_name'],
                content=content,
                metadata={
                    "language": "JavaScript",
                    "func_name": example['func_name'],
                    "quality_score": example['quality_score'],
                    "repo": example['repo'],
                    "source": "GitHub",
                    "timestamp": datetime.now().isoformat()
                }
            )

            count += 1

            if count % 50 == 0:
                print(f"   Stored {count}/{len(examples)} examples in RAG")

        print(f"✅ Stored {count} JavaScript examples in RAG")
        return count

    def store_in_knowledge_graph(self, examples: List[Dict]) -> int:
        """
        Create knowledge graph relationships for JavaScript examples.

        Args:
            examples: List of JavaScript examples

        Returns:
            Number of relationships created
        """
        if not self.kg:
            print("⚠️  Knowledge Graph not available, skipping...")
            return 0

        count = 0

        for example in examples:
            entity_name = f"JS_{example['func_name']}"

            # Create code example entity
            try:
                self.kg.add_entity(
                    entity_type="CodeExample",
                    name=entity_name,
                    properties={
                        "language": "JavaScript",
                        "func_name": example['func_name'],
                        "quality_score": example['quality_score'],
                        "repo": example['repo']
                    }
                )

                # Create relationships
                # Example -> Language
                self.kg.add_relation(
                    from_entity=entity_name,
                    to_entity="JavaScript",
                    relation_type="WRITTEN_IN"
                )

                # Example -> Repository
                self.kg.add_relation(
                    from_entity=entity_name,
                    to_entity=example['repo'],
                    relation_type="FROM_REPO"
                )

                count += 1

                if count % 50 == 0:
                    print(f"   Created {count} KG relationships")

            except Exception as e:
                # Continue on error (KG might not support all operations)
                pass

        print(f"✅ Created {count} knowledge graph relationships")
        return count

    def download_and_store(
        self,
        limit: int = 1000,
        quality_min: float = 0.5,
        store_kg: bool = True
    ) -> Dict[str, int]:
        """
        Download JavaScript examples and store in RAG/KG.

        Args:
            limit: Maximum examples to download
            quality_min: Minimum quality threshold
            store_kg: Whether to store in knowledge graph

        Returns:
            Dictionary with counts
        """
        # Download examples
        examples = self.download_from_huggingface(
            limit=limit,
            quality_min=quality_min
        )

        if not examples:
            print("❌ No examples downloaded")
            return {"examples_downloaded": 0, "rag_stored": 0, "kg_relationships": 0}

        # Store in RAG
        rag_count = self.store_in_rag(examples)

        # Store in KG
        kg_count = 0
        if store_kg:
            kg_count = self.store_in_knowledge_graph(examples)

        return {
            "examples_downloaded": len(examples),
            "rag_stored": rag_count,
            "kg_relationships": kg_count
        }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Download JavaScript examples from CodeSearchNet and store in RAG"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of examples to download (default: 1000)"
    )
    parser.add_argument(
        "--quality-min",
        type=float,
        default=0.5,
        help="Minimum quality score threshold 0.0-1.0 (default: 0.5)"
    )
    parser.add_argument(
        "--rag-only",
        action="store_true",
        help="Only store in RAG (skip Knowledge Graph)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("JavaScript Example Downloader (CodeSearchNet)")
    print("=" * 70)

    # Initialize downloader
    downloader = JavaScriptExampleDownloader()

    # Download and store
    results = downloader.download_and_store(
        limit=args.limit,
        quality_min=args.quality_min,
        store_kg=not args.rag_only
    )

    print("\n" + "=" * 70)
    print("Download Complete!")
    print("=" * 70)
    print(f"Examples Downloaded: {results['examples_downloaded']}")
    print(f"RAG Examples Stored: {results['rag_stored']}")
    print(f"KG Relationships Created: {results['kg_relationships']}")


if __name__ == "__main__":
    main()
