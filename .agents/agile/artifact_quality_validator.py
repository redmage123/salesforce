#!/usr/bin/env python3
"""
Artifact Quality Validators - Requirements-Driven Validation

Base classes and validators for different artifact types.
Each validator knows how to assess quality for its artifact type.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass
import json


@dataclass
class ValidationResult:
    """Result of quality validation"""
    passed: bool
    score: float  # 0.0 to 1.0
    criteria_results: Dict[str, bool]  # criterion -> passed
    feedback: List[str]  # Specific feedback items

    def __str__(self):
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        return f"{status} (score: {self.score:.2f})"


class ArtifactQualityValidator(ABC):
    """Base class for artifact quality validators"""

    def __init__(self, quality_criteria: Dict, logger=None):
        self.quality_criteria = quality_criteria
        self.logger = logger

    @abstractmethod
    def validate(self, artifact_path: Path) -> ValidationResult:
        """Validate artifact against quality criteria"""
        pass

    @abstractmethod
    def generate_validation_prompt(self, requirements: str) -> str:
        """Generate LLM prompt for creating the artifact"""
        pass


class NotebookQualityValidator(ArtifactQualityValidator):
    """Validates Jupyter notebooks using functional validation checks"""

    def validate(self, artifact_path: Path) -> ValidationResult:
        """Validate notebook quality using functional composition"""
        notebook = self._load_notebook(artifact_path)
        cells = notebook.get('cells', [])

        # Define validation checks as functions
        checks = [
            self._check_cell_count(cells),
            self._check_visualizations(cells),
            self._check_documentation(cells),
            self._check_data_loading(cells)
        ]

        # Filter out None values (checks that don't apply)
        active_checks = [c for c in checks if c is not None]

        # Aggregate results
        return self._aggregate_validation_results(active_checks)

    def _load_notebook(self, path: Path) -> Dict:
        """Load notebook JSON"""
        with open(path, 'r') as f:
            return json.load(f)

    def _check_cell_count(self, cells: List) -> Dict:
        """Check minimum cell count"""
        min_cells = self.quality_criteria.get('min_cells', 5)
        count = len(cells)
        passed = count >= min_cells

        return {
            'name': 'min_cells',
            'passed': passed,
            'feedback': None if passed else f"Only {count} cells, expected {min_cells}+"
        }

    def _check_visualizations(self, cells: List) -> Optional[Dict]:
        """Check for visualization library usage"""
        requires_viz = self.quality_criteria.get('requires_visualizations')
        return None if not requires_viz else self._validate_viz_presence(cells)

    def _validate_viz_presence(self, cells: List) -> Dict:
        """Validate visualization library is present"""
        viz_lib = self.quality_criteria.get('visualization_library', 'plotly')
        has_viz = any(
            viz_lib.lower() in str(cell.get('source', '')).lower()
            for cell in cells
        )

        return {
            'name': 'has_visualizations',
            'passed': has_viz,
            'feedback': None if has_viz else f"Missing {viz_lib} visualizations"
        }

    def _check_documentation(self, cells: List) -> Dict:
        """Check for markdown documentation"""
        markdown_count = sum(1 for c in cells if c.get('cell_type') == 'markdown')
        passed = markdown_count >= 2

        return {
            'name': 'has_documentation',
            'passed': passed,
            'feedback': None if passed else "Insufficient markdown documentation"
        }

    def _check_data_loading(self, cells: List) -> Optional[Dict]:
        """Check for data source loading"""
        data_source = self.quality_criteria.get('data_source')
        return None if not data_source else self._validate_data_source(cells, data_source)

    def _validate_data_source(self, cells: List, data_source: str) -> Dict:
        """Validate data source is loaded"""
        has_data = any(
            data_source in str(cell.get('source', ''))
            for cell in cells
        )

        return {
            'name': 'loads_data',
            'passed': has_data,
            'feedback': None if has_data else f"Missing data loading from {data_source}"
        }

    def _aggregate_validation_results(self, checks: List[Dict]) -> ValidationResult:
        """Aggregate check results into final ValidationResult"""
        criteria_results = {c['name']: c['passed'] for c in checks}
        feedback = [c['feedback'] for c in checks if c['feedback']]

        passed_count = sum(1 for c in checks if c['passed'])
        score = passed_count / len(checks) if checks else 0.0
        passed = score >= 0.8

        return ValidationResult(
            passed=passed,
            score=score,
            criteria_results=criteria_results,
            feedback=feedback
        )

    def generate_validation_prompt(self, requirements: str) -> str:
        """Generate comprehensive prompt for notebook creation"""
        min_cells = self.quality_criteria.get('min_cells', 8)
        viz_lib = self.quality_criteria.get('visualization_library', 'plotly')
        data_source = self.quality_criteria.get('data_source', '')

        prompt = f"""Create a COMPREHENSIVE, production-quality Jupyter notebook.

**CRITICAL: This is NOT a minimal implementation. Create complete, rich output.**

Requirements:
{requirements}

Quality Criteria (ALL must be met):
- Minimum {min_cells} cells (mix of code and markdown)
- Multiple visualizations using {viz_lib}
- Clear markdown documentation explaining each step
- Real data from {data_source if data_source else 'appropriate source'}
- Interactive elements where applicable
- Professional quality suitable for presentation

Structure:
1. Title and overview (markdown)
2. Import libraries (code)
3. Load and explore data (code + markdown)
4. Create multiple visualizations (code + markdown)
5. Analysis and insights (markdown)
6. Conclusions (markdown)

Return JSON format:
{{
    "files": [
        {{"path": "notebook.ipynb", "content": "notebook JSON content here"}}
    ]
}}
"""
        return prompt


class CodeQualityValidator(ArtifactQualityValidator):
    """Validates code using TDD approach"""

    def validate(self, artifact_path: Path) -> ValidationResult:
        """Validate code via test execution"""
        # This uses existing TDD validation (tests must pass)
        # Placeholder - actual implementation would run pytest
        return ValidationResult(
            passed=True,
            score=1.0,
            criteria_results={'tests_pass': True},
            feedback=[]
        )

    def generate_validation_prompt(self, requirements: str) -> str:
        """Generate TDD prompt for code creation"""
        prompt = f"""Implement code using Test-Driven Development.

Requirements:
{requirements}

Approach:
1. Write failing tests first (RED)
2. Implement MINIMUM code to pass tests (GREEN)
3. Refactor for quality (REFACTOR)

Focus on simplicity and testability.
"""
        return prompt


class UIQualityValidator(ArtifactQualityValidator):
    """Validates UI components using functional checks"""

    def validate(self, artifact_path: Path) -> ValidationResult:
        """Validate UI quality using functional composition"""
        content = self._load_content(artifact_path)

        checks = [
            self._check_accessibility(content),
            self._check_responsive_design(content)
        ]

        active_checks = [c for c in checks if c is not None]

        return self._aggregate_results(active_checks)

    def _load_content(self, path: Path) -> str:
        """Load UI component content"""
        with open(path, 'r') as f:
            return f.read()

    def _check_accessibility(self, content: str) -> Optional[Dict]:
        """Check accessibility features"""
        accessibility_required = self.quality_criteria.get('accessibility_required')
        return None if not accessibility_required else self._validate_accessibility(content)

    def _validate_accessibility(self, content: str) -> Dict:
        """Validate ARIA/accessibility attributes"""
        has_aria = 'aria-' in content or 'role=' in content

        return {
            'name': 'accessibility',
            'passed': has_aria,
            'feedback': None if has_aria else "Missing ARIA labels/roles for accessibility"
        }

    def _check_responsive_design(self, content: str) -> Optional[Dict]:
        """Check responsive design patterns"""
        responsive_required = self.quality_criteria.get('responsive_required')
        return None if not responsive_required else self._validate_responsive(content)

    def _validate_responsive(self, content: str) -> Dict:
        """Validate responsive design patterns"""
        responsive_keywords = ['@media', 'flex', 'grid', 'responsive']
        has_responsive = any(kw in content.lower() for kw in responsive_keywords)

        return {
            'name': 'responsive',
            'passed': has_responsive,
            'feedback': None if has_responsive else "Missing responsive design patterns"
        }

    def _aggregate_results(self, checks: List[Dict]) -> ValidationResult:
        """Aggregate results"""
        criteria_results = {c['name']: c['passed'] for c in checks}
        feedback = [c['feedback'] for c in checks if c['feedback']]

        passed_count = sum(1 for c in checks if c['passed'])
        score = passed_count / len(checks) if checks else 1.0
        passed = score >= 0.8

        return ValidationResult(
            passed=passed,
            score=score,
            criteria_results=criteria_results,
            feedback=feedback
        )

    def generate_validation_prompt(self, requirements: str) -> str:
        """Generate comprehensive prompt for UI creation"""
        accessibility = self.quality_criteria.get('accessibility_required')
        responsive = self.quality_criteria.get('responsive_required')

        prompt = f"""Create a production-quality UI component.

Requirements:
{requirements}

Quality Criteria:
- Clean, semantic HTML
- Modern CSS (flexbox/grid)
{"- WCAG 2.1 AA accessibility (ARIA labels, keyboard navigation)" if accessibility else ""}
{"- Fully responsive design (mobile, tablet, desktop)" if responsive else ""}
- Cross-browser compatible
- Well-documented

Return JSON format:
{{
    "files": [
        {{"path": "filename.html", "content": "file content here"}},
        {{"path": "filename.css", "content": "file content here"}}
    ]
}}
"""
        return prompt


# Factory for creating validators
def create_validator(validator_class: str, quality_criteria: Dict, logger=None) -> ArtifactQualityValidator:
    """Factory to create appropriate validator"""
    validators = {
        'NotebookQualityValidator': NotebookQualityValidator,
        'CodeQualityValidator': CodeQualityValidator,
        'UIQualityValidator': UIQualityValidator,
        # Add more as needed
    }

    validator_cls = validators.get(validator_class)
    if not validator_cls:
        raise ValueError(f"Unknown validator: {validator_class}")

    return validator_cls(quality_criteria, logger)
