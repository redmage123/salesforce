# Hugging Face Datasets Integration for Artemis Code Examples

**Date:** October 24, 2025
**Purpose:** Integrate Hugging Face code datasets to massively expand code examples for RAG/KG

---

## Overview

Hugging Face provides **massive, high-quality code datasets** covering **358+ programming languages** with **6TB+ of permissively-licensed code**. This can supplement our curated examples with real-world code from millions of repositories.

---

## Top Datasets for Artemis

### 1. **The Stack (bigcode/the-stack)** ⭐ BEST FOR COVERAGE

**Stats:**
- **358 programming languages**
- **6TB of permissively-licensed source code**
- **Billions of lines of code**
- **Maintained by BigCode Project**

**Why Valuable:**
- Covers ALL 30+ languages we need (Python, Rust, Java, Go, Haskell, Perl, Fortran, R, MATLAB, etc.)
- Permissive licenses only (can use freely)
- Curated for code LLM training
- Reproducible, transparent dataset

**Access:**
```python
from datasets import load_dataset

# Load specific language
ds = load_dataset(
    "bigcode/the-stack",
    data_dir="data/python",  # python, rust, java, etc.
    split="train",
    streaming=True  # Stream for large datasets
)

# Filter by quality
for example in ds:
    code = example['content']
    if len(code) > 100 and len(code) < 5000:  # Reasonable size
        # Process code example
        pass
```

**License:** Permissive licenses only (MIT, Apache 2.0, BSD, etc.)


### 2. **GitHub Code (codeparrot/github-code)** ⭐ BEST FOR DIVERSITY

**Stats:**
- **115M code files**
- **32 programming languages**
- **1TB of code data**
- **60 file extensions**

**Why Valuable:**
- Covers 30 languages including Python, JavaScript, Java, C++, Go, Rust, TypeScript
- Includes license information
- Repository metadata (can find high-quality repos)
- Easy filtering by language and license

**Access:**
```python
from datasets import load_dataset

# Stream Python code with MIT license
ds = load_dataset(
    "codeparrot/github-code",
    streaming=True,
    split="train",
    languages=["Python"],
    licenses=["mit", "apache-2.0"]
)

# Example record structure
example = next(iter(ds))
# {
#     'code': '...',
#     'repo_name': 'owner/repo',
#     'path': 'src/main.py',
#     'language': 'Python',
#     'license': 'mit',
#     'size': 1024
# }
```

**License:** Multiple (MIT, Apache 2.0, GPL, BSD, etc.) - **filter by permissive only**


### 3. **GitHub Code 2025 (nick007x/github-code-2025)** ⭐ BEST FOR QUALITY

**Stats:**
- **1.5M+ repositories**
- **Curated for quality (2025)**
- **Excludes binary files, build artifacts, minified code**
- **Star-based quality filtering**

**Why Valuable:**
- Most recent code (2025 best practices)
- Quality-focused (excludes junk)
- Star filtering (high-quality vs experimental)
- Clean, well-maintained code

**Access:**
```python
from datasets import load_dataset

# Load high-quality repos (2+ stars)
ds_quality = load_dataset(
    "nick007x/github-code-2025",
    "above-2-stars",
    streaming=True
)

# Load experimental/emerging repos
ds_experimental = load_dataset(
    "nick007x/github-code-2025",
    "below-2-star",
    streaming=True
)
```

**License:** Varies by repository


### 4. **BigCodeReward (bigcode/bigcodereward)** ⭐ BEST FOR PATTERNS

**Stats:**
- **14,000+ code conversations**
- **10 LLMs**
- **10 programming languages**
- **8 execution environments**

**Why Valuable:**
- Real developer questions and solutions
- Multiple approaches to same problems
- Execution-validated code
- Covers common patterns

**Access:**
```python
from datasets import load_dataset

ds = load_dataset("bigcode/bigcodereward")

# Each example has:
# - conversation: developer question
# - code_solution: LLM-generated code
# - execution_result: validated output
# - language: programming language
```

**License:** Permissive


### 5. **Source Code (shibing624/source_code)** ⭐ BEST FOR TRAINING

**Stats:**
- **Python: 5.2M+ lines**
- **Java: 4.6M+ lines**
- **C++: 5.2M+ lines**

**Why Valuable:**
- Large volume for popular languages
- Pre-processed for ML training
- Good for language modeling

**Access:**
```python
from datasets import load_dataset

ds = load_dataset("shibing624/source_code", "python")
```

---

## Integration Strategy

### Phase 1: Curated Examples (Current) ✅

**Status:** Complete
- Hand-crafted examples with high quality scores
- 11 examples (5 languages, 6 databases)
- Average quality: 94.7/100
- Focused on design patterns and best practices

**Advantages:**
- ✅ Guaranteed quality
- ✅ Explicit anti-pattern prevention
- ✅ Educational comments
- ✅ Production-ready

**Disadvantages:**
- ❌ Small volume (11 examples)
- ❌ Manual creation (time-consuming)
- ❌ Limited pattern coverage


### Phase 2: Hugging Face Augmentation (Proposed) 🔄

**Strategy:** Augment curated examples with filtered Hugging Face code

**Approach:**
1. **Quality Filtering**
   - Star count (GitHub Code 2025: >2 stars)
   - License filtering (permissive only)
   - Size filtering (100-5000 lines)
   - Language-specific heuristics

2. **Pattern Detection**
   - Identify design patterns (Repository, Factory, etc.)
   - Extract class/function definitions
   - Find idiomatic code (language-specific features)

3. **Deduplication**
   - Remove exact duplicates
   - Detect near-duplicates (fuzzy matching)
   - Keep highest quality version

4. **Quality Scoring**
   - Code complexity metrics
   - Documentation coverage
   - Error handling presence
   - SOLID principle adherence

**Target:**
- **100+ examples per language** (3,000+ total for 30 languages)
- **Quality score: 70-100** (curated examples remain 90-100)
- **Coverage: All 30 languages and 10+ databases**

---

## Implementation Plan

### Script: `import_huggingface_examples.py`

```python
#!/usr/bin/env python3
"""
Import code examples from Hugging Face datasets with quality filtering.
"""

from datasets import load_dataset
from typing import List, Dict, Optional
import re
from code_example_types import CodeExample
from populate_code_examples import CodeExamplePopulator


class HuggingFaceImporter:
    """Import and filter code examples from Hugging Face datasets"""

    def __init__(self, min_quality_score: int = 70):
        self.min_quality_score = min_quality_score
        self.populator = CodeExamplePopulator()

    def import_from_github_code(
        self,
        language: str,
        pattern: Optional[str] = None,
        max_examples: int = 100
    ) -> List[CodeExample]:
        """
        Import code examples from GitHub Code dataset.

        Args:
            language: Programming language (Python, Rust, Java, etc.)
            pattern: Optional design pattern to filter for
            max_examples: Maximum number of examples to import

        Returns:
            List of CodeExample objects
        """
        examples = []

        # Load dataset with streaming
        ds = load_dataset(
            "codeparrot/github-code",
            streaming=True,
            split="train",
            languages=[language],
            licenses=["mit", "apache-2.0", "bsd-3-clause", "bsd-2-clause"]
        )

        for item in ds:
            code = item['content']

            # Quality filters
            if not self._passes_quality_check(code, language):
                continue

            # Pattern detection (if specified)
            if pattern and not self._matches_pattern(code, pattern):
                continue

            # Create CodeExample
            example = self._create_code_example(
                code=code,
                language=language,
                pattern=pattern or self._detect_pattern(code),
                repo_name=item['repo_name'],
                file_path=item['path']
            )

            if example and example.quality_score >= self.min_quality_score:
                examples.append(example)

                if len(examples) >= max_examples:
                    break

        return examples

    def import_from_the_stack(
        self,
        language: str,
        max_examples: int = 100
    ) -> List[CodeExample]:
        """
        Import code examples from The Stack dataset.

        Args:
            language: Programming language
            max_examples: Maximum examples to import

        Returns:
            List of CodeExample objects
        """
        examples = []

        # Load from The Stack
        ds = load_dataset(
            "bigcode/the-stack",
            data_dir=f"data/{language.lower()}",
            split="train",
            streaming=True
        )

        for item in ds:
            code = item['content']

            if not self._passes_quality_check(code, language):
                continue

            example = self._create_code_example(
                code=code,
                language=language,
                pattern=self._detect_pattern(code),
                repo_name=item.get('max_stars_repo_name', 'unknown'),
                file_path=item.get('max_stars_repo_path', '')
            )

            if example and example.quality_score >= self.min_quality_score:
                examples.append(example)

                if len(examples) >= max_examples:
                    break

        return examples

    def _passes_quality_check(self, code: str, language: str) -> bool:
        """
        Quality filtering heuristics.

        Returns:
            True if code passes quality checks
        """
        # Size check (not too small, not too large)
        if len(code) < 100 or len(code) > 5000:
            return False

        # Has comments (documentation)
        if language in ["Python", "JavaScript", "Java", "C++", "Rust"]:
            comment_patterns = {
                "Python": r'(#|""")',
                "JavaScript": r'(//|/\*)',
                "Java": r'(//|/\*)',
                "C++": r'(//|/\*)',
                "Rust": r'(//|/\*)'
            }
            if not re.search(comment_patterns.get(language, r'//'), code):
                return False

        # Has function/class definitions
        has_structure = any([
            re.search(r'\bclass\s+\w+', code),
            re.search(r'\bdef\s+\w+', code),
            re.search(r'\bfunction\s+\w+', code),
            re.search(r'\bfn\s+\w+', code),
            re.search(r'\bpublic\s+\w+\s+\w+\(', code)
        ])

        if not has_structure:
            return False

        # No obvious low-quality indicators
        low_quality_indicators = [
            r'TODO',
            r'FIXME',
            r'HACK',
            r'XXX',
            r'print\(',  # Excessive debugging
        ]

        # Count low-quality indicators (some are okay, but not too many)
        indicator_count = sum(
            len(re.findall(pattern, code, re.IGNORECASE))
            for pattern in low_quality_indicators
        )

        if indicator_count > 5:
            return False

        return True

    def _matches_pattern(self, code: str, pattern: str) -> bool:
        """
        Check if code matches a specific design pattern.

        Args:
            code: Source code
            pattern: Pattern name (Repository, Factory, etc.)

        Returns:
            True if pattern detected
        """
        pattern_indicators = {
            "Repository": [r'class\s+\w+Repository', r'def\s+find_by_id'],
            "Factory": [r'class\s+\w+Factory', r'def\s+create'],
            "Strategy": [r'class\s+\w+Strategy', r'def\s+execute'],
            "Observer": [r'class\s+\w+Observer', r'def\s+notify'],
            "Singleton": [r'_instance\s*=\s*None', r'__new__'],
        }

        indicators = pattern_indicators.get(pattern, [])
        return any(re.search(ind, code) for ind in indicators)

    def _detect_pattern(self, code: str) -> str:
        """
        Attempt to detect design pattern from code.

        Returns:
            Pattern name or "General"
        """
        for pattern, indicators in [
            ("Repository", [r'Repository', r'find_by']),
            ("Factory", [r'Factory', r'create']),
            ("Strategy", [r'Strategy', r'execute']),
            ("Observer", [r'Observer', r'notify']),
            ("Singleton", [r'Singleton', r'instance']),
        ]:
            if any(re.search(ind, code, re.IGNORECASE) for ind in indicators):
                return pattern

        return "General"

    def _create_code_example(
        self,
        code: str,
        language: str,
        pattern: str,
        repo_name: str,
        file_path: str
    ) -> Optional[CodeExample]:
        """
        Create CodeExample from imported code.

        Returns:
            CodeExample or None if quality too low
        """
        # Calculate quality score (simplified)
        quality_score = self._calculate_quality_score(code, language)

        if quality_score < self.min_quality_score:
            return None

        # Extract title from file path
        title = file_path.split('/')[-1].replace('.py', '').replace('_', ' ').title()

        # Detect complexity
        complexity = self._detect_complexity(code)

        # Extract concepts
        demonstrates = self._extract_concepts(code, language)

        return CodeExample(
            language=language,
            pattern=pattern,
            title=f"{title} ({repo_name})",
            description=f"Real-world {pattern} example from {repo_name}",
            code=code,
            quality_score=quality_score,
            tags=[language.lower(), pattern.lower(), "huggingface", "real-world"],
            complexity=complexity,
            demonstrates=demonstrates,
            prevents=[]  # Could be inferred with more analysis
        )

    def _calculate_quality_score(self, code: str, language: str) -> int:
        """
        Calculate quality score (1-100) based on heuristics.

        Returns:
            Quality score
        """
        score = 50  # Base score

        # Has docstrings/comments (+20)
        if re.search(r'("""|\'\'\'/\*\*)', code):
            score += 20

        # Has type hints/annotations (+10)
        if language == "Python" and re.search(r':\s*\w+\s*->', code):
            score += 10
        elif language == "TypeScript" and re.search(r':\s*\w+', code):
            score += 10

        # Has error handling (+10)
        if re.search(r'(try|catch|except|Result|Option)', code):
            score += 10

        # Well-formatted (4-space indentation) (+5)
        if re.search(r'^    \w', code, re.MULTILINE):
            score += 5

        # Reasonable length (+5)
        if 500 <= len(code) <= 2000:
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


# Usage example
if __name__ == "__main__":
    importer = HuggingFaceImporter(min_quality_score=70)

    # Import Python Repository pattern examples
    examples = importer.import_from_github_code(
        language="Python",
        pattern="Repository",
        max_examples=50
    )

    print(f"Imported {len(examples)} examples")
    for ex in examples[:5]:
        print(f"- {ex.title} (Quality: {ex.quality_score})")

    # Populate RAG/KG
    populator = CodeExamplePopulator()
    populator.populate_rag(examples)
```

---

## Quality Filtering Criteria

### Minimum Requirements
- ✅ **Size:** 100-5000 characters (not too small, not too large)
- ✅ **Documentation:** Has comments/docstrings
- ✅ **Structure:** Contains functions/classes
- ✅ **License:** Permissive only (MIT, Apache 2.0, BSD)
- ✅ **Quality Score:** ≥70/100

### Quality Scoring Algorithm

```python
Base Score: 50

+20: Has docstrings/comments
+10: Has type hints/annotations
+10: Has error handling
+5:  Well-formatted (consistent indentation)
+5:  Reasonable length (500-2000 chars)

Total: 100 max
```

### Pattern Detection Heuristics

| Pattern | Indicators |
|---------|-----------|
| **Repository** | Class name contains "Repository", has `find_by_id` |
| **Factory** | Class name contains "Factory", has `create` method |
| **Strategy** | Class name contains "Strategy", has `execute` method |
| **Observer** | Class name contains "Observer", has `notify` method |
| **Singleton** | Has `_instance` class variable, overrides `__new__` |

---

## Benefits of Hugging Face Integration

### For Artemis Developers

✅ **Massive Scale**
- From 11 curated examples to 3,000+ examples
- All 30 languages covered
- All 10+ databases covered

✅ **Real-World Code**
- Actual production code from GitHub
- Multiple approaches to same problems
- Current best practices (2025)

✅ **Diverse Patterns**
- Design patterns in the wild
- Language-specific idioms
- Framework-specific patterns

✅ **Continuous Updates**
- Datasets updated regularly
- Can re-import for latest practices
- Track evolution of patterns

### For Code Quality

✅ **Better Recommendations**
- More relevant examples for specific tasks
- Language-specific best practices
- Multiple solution approaches

✅ **Reduced Hallucinations**
- Grounded in real code
- Proven patterns
- Tested in production

✅ **Learning from Best**
- High-star repositories
- Well-maintained codebases
- Community-validated approaches

---

## Implementation Timeline

### Week 1: Setup
- [ ] Install Hugging Face datasets library
- [ ] Test access to The Stack and GitHub Code
- [ ] Implement basic quality filtering

### Week 2: Pattern Detection
- [ ] Implement pattern detection heuristics
- [ ] Test quality scoring algorithm
- [ ] Validate deduplication

### Week 3: Integration
- [ ] Import 100 examples for top 5 languages
- [ ] Populate RAG/KG
- [ ] Test retrieval accuracy

### Week 4: Expansion
- [ ] Import examples for all 30 languages
- [ ] Add database-specific code
- [ ] Performance benchmarking

---

## Risks and Mitigations

### Risk 1: Low-Quality Code
**Mitigation:**
- Strict quality filtering (≥70 score)
- Manual review of top patterns
- User feedback loop

### Risk 2: License Violations
**Mitigation:**
- Filter for permissive licenses only
- Track source repository
- Include attribution

### Risk 3: Outdated Practices
**Mitigation:**
- Use GitHub Code 2025 (most recent)
- Filter by star count (active maintenance)
- Re-import periodically

### Risk 4: Storage/Performance
**Mitigation:**
- Use streaming (don't load all into memory)
- Index by pattern and language
- Cache frequently accessed examples

---

## Success Metrics

### Quantitative
- **Example Count:** 3,000+ (from 11)
- **Language Coverage:** 30/30 (from 5/30)
- **Database Coverage:** 10/10 (from 6/10)
- **Avg Quality Score:** ≥75/100

### Qualitative
- Developer satisfaction with example relevance
- Reduction in code review issues
- Faster implementation times
- Better pattern adoption

---

## Recommended Datasets by Use Case

| Use Case | Dataset | Why |
|----------|---------|-----|
| **Maximum Coverage** | The Stack | 358 languages |
| **Quality Code** | GitHub Code 2025 | Curated, recent |
| **Popular Languages** | GitHub Code | 32 languages, 1TB |
| **Design Patterns** | BigCodeReward | Validated solutions |
| **ML Training** | Source Code | Pre-processed |

---

## Next Steps

1. **Install dependencies:**
   ```bash
   pip install datasets transformers
   ```

2. **Create import script:**
   ```bash
   touch import_huggingface_examples.py
   ```

3. **Test with Python:**
   ```bash
   python import_huggingface_examples.py --language Python --max 10
   ```

4. **Expand to all languages:**
   ```bash
   python import_huggingface_examples.py --all --max 100
   ```

---

**Status:** 📋 Ready for Implementation
**Priority:** 🔥 High (massively expands code example coverage)
**Estimated Time:** 2-4 weeks for full integration
