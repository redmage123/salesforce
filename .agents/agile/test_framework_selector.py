#!/usr/bin/env python3
"""
Test Framework Selector

Automatically selects the appropriate test framework based on:
- Project type (language, technology stack)
- Requirements (unit tests, integration tests, E2E, performance, etc.)
- Existing project structure

Used by Artemis to decide which test framework to employ for a given task.

Usage:
    from test_framework_selector import TestFrameworkSelector

    selector = TestFrameworkSelector(project_dir="/path/to/project")
    framework = selector.select_framework(requirements={"type": "unit", "language": "python"})

    # Returns: "pytest", "jest", "selenium", etc.
"""

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ProjectType(Enum):
    """Project types that influence framework selection"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    WEB_FRONTEND = "web_frontend"
    WEB_BACKEND = "web_backend"
    MOBILE_IOS = "mobile_ios"
    MOBILE_ANDROID = "mobile_android"
    API = "api"
    UNKNOWN = "unknown"


class TestType(Enum):
    """Test types that require specific frameworks"""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    BROWSER = "browser"
    MOBILE = "mobile"
    PERFORMANCE = "performance"
    API_TEST = "api"
    ACCEPTANCE = "acceptance"
    PROPERTY_BASED = "property_based"


@dataclass
class FrameworkRecommendation:
    """Framework recommendation with rationale"""
    framework: str
    confidence: float  # 0.0 to 1.0
    rationale: str
    alternatives: List[str]


class TestFrameworkSelector:
    """
    Intelligent test framework selector for Artemis.

    Analyzes project structure, language, and requirements to recommend
    the most appropriate testing framework.
    """

    def __init__(self, project_dir: Optional[Path] = None):
        """
        Initialize selector with optional project directory.

        Args:
            project_dir: Project root directory for analysis
        """
        self.project_dir = Path(project_dir) if project_dir else None
        self.project_type = self._detect_project_type() if project_dir else ProjectType.UNKNOWN

    def select_framework(
        self,
        requirements: Optional[Dict] = None,
        test_type: str = "unit"
    ) -> FrameworkRecommendation:
        """
        Select the best test framework based on requirements.

        Args:
            requirements: Dict with keys like:
                - type: Test type (unit, e2e, performance, etc.)
                - language: Programming language
                - browser: Whether browser automation needed
                - mobile: Whether mobile testing needed
                - existing_tests: Whether tests already exist
            test_type: Type of testing (unit, integration, e2e, etc.)

        Returns:
            FrameworkRecommendation with selected framework and rationale
        """
        requirements = requirements or {}
        test_type_enum = TestType(test_type) if isinstance(test_type, str) else test_type

        # Extract requirements
        language = requirements.get("language", self._infer_language())
        needs_browser = requirements.get("browser", False)
        needs_mobile = requirements.get("mobile", False)
        needs_performance = requirements.get("performance", False)
        existing_tests = requirements.get("existing_tests", False)

        # Detect existing framework if tests exist
        if existing_tests and self.project_dir:
            existing = self._detect_existing_framework()
            if existing:
                return FrameworkRecommendation(
                    framework=existing,
                    confidence=0.9,
                    rationale=f"Project already uses {existing} framework",
                    alternatives=[]
                )

        # Mobile testing
        if needs_mobile or test_type_enum == TestType.MOBILE:
            return FrameworkRecommendation(
                framework="appium",
                confidence=0.95,
                rationale="Mobile app testing requires Appium for cross-platform support",
                alternatives=[]
            )

        # Performance/Load testing
        if needs_performance or test_type_enum == TestType.PERFORMANCE:
            return FrameworkRecommendation(
                framework="jmeter",
                confidence=0.9,
                rationale="JMeter is the industry standard for performance and load testing",
                alternatives=[]
            )

        # Browser automation / E2E testing
        if needs_browser or test_type_enum == TestType.BROWSER:
            # Prefer modern Playwright over Selenium
            return FrameworkRecommendation(
                framework="playwright",
                confidence=0.85,
                rationale="Playwright provides modern browser automation with better reliability",
                alternatives=["selenium"]
            )

        # Acceptance testing (BDD)
        if test_type_enum == TestType.ACCEPTANCE:
            return FrameworkRecommendation(
                framework="robot",
                confidence=0.8,
                rationale="Robot Framework provides human-readable acceptance tests",
                alternatives=["pytest"]  # with pytest-bdd
            )

        # Property-based testing
        if test_type_enum == TestType.PROPERTY_BASED:
            return FrameworkRecommendation(
                framework="hypothesis",
                confidence=0.95,
                rationale="Hypothesis specializes in property-based testing for Python",
                alternatives=["pytest"]
            )

        # Language-specific unit/integration testing
        if language == "python" or self.project_type == ProjectType.PYTHON:
            return FrameworkRecommendation(
                framework="pytest",
                confidence=0.9,
                rationale="pytest is the modern standard for Python testing",
                alternatives=["unittest"]
            )

        elif language == "javascript" or language == "typescript":
            return FrameworkRecommendation(
                framework="jest",
                confidence=0.9,
                rationale="Jest is the de facto standard for JavaScript/TypeScript testing",
                alternatives=[]
            )

        elif language == "java" or self.project_type == ProjectType.JAVA:
            return FrameworkRecommendation(
                framework="junit",
                confidence=0.9,
                rationale="JUnit is the standard testing framework for Java",
                alternatives=[]
            )

        elif language == "cpp" or language == "c++" or self.project_type == ProjectType.CPP:
            return FrameworkRecommendation(
                framework="gtest",
                confidence=0.9,
                rationale="Google Test is the industry standard for C++ testing",
                alternatives=[]
            )

        # Default to pytest for unknown
        return FrameworkRecommendation(
            framework="pytest",
            confidence=0.5,
            rationale="pytest is a versatile default choice for most projects",
            alternatives=["unittest"]
        )

    def _detect_project_type(self) -> ProjectType:
        """Detect project type from directory structure"""
        if not self.project_dir or not self.project_dir.exists():
            return ProjectType.UNKNOWN

        # Check for language indicators
        if list(self.project_dir.glob("**/*.py")):
            return ProjectType.PYTHON
        elif list(self.project_dir.glob("**/*.java")):
            return ProjectType.JAVA
        elif list(self.project_dir.glob("**/*.cpp")) or list(self.project_dir.glob("**/*.cc")):
            return ProjectType.CPP
        elif (self.project_dir / "package.json").exists():
            # Check if TypeScript or JavaScript
            if list(self.project_dir.glob("**/*.ts")):
                return ProjectType.TYPESCRIPT
            else:
                return ProjectType.JAVASCRIPT

        return ProjectType.UNKNOWN

    def _infer_language(self) -> str:
        """Infer programming language from project type"""
        type_to_lang = {
            ProjectType.PYTHON: "python",
            ProjectType.JAVASCRIPT: "javascript",
            ProjectType.TYPESCRIPT: "typescript",
            ProjectType.JAVA: "java",
            ProjectType.CPP: "cpp"
        }
        return type_to_lang.get(self.project_type, "python")

    def _detect_existing_framework(self) -> Optional[str]:
        """Detect existing test framework from project"""
        if not self.project_dir:
            return None

        # Check for framework-specific files
        if list(self.project_dir.glob("**/conftest.py")) or list(self.project_dir.glob("**/pytest.ini")):
            return "pytest"

        if (self.project_dir / "jest.config.js").exists():
            return "jest"

        if list(self.project_dir.glob("**/*.robot")):
            return "robot"

        if list(self.project_dir.glob("**/*.jmx")):
            return "jmeter"

        # Check test files for imports
        test_files = list(self.project_dir.glob("**/test_*.py")) + list(self.project_dir.glob("**/*_test.py"))
        if test_files:
            with open(test_files[0], 'r') as f:
                content = f.read()
                if "import pytest" in content:
                    return "pytest"
                elif "import unittest" in content:
                    return "unittest"
                elif "from playwright" in content:
                    return "playwright"
                elif "from selenium" in content:
                    return "selenium"
                elif "from appium" in content:
                    return "appium"
                elif "from hypothesis" in content:
                    return "hypothesis"

        return None


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Test Framework Selector - Recommend test framework for projects"
    )
    parser.add_argument(
        "--project-dir",
        help="Project directory to analyze"
    )
    parser.add_argument(
        "--test-type",
        choices=["unit", "integration", "e2e", "browser", "mobile", "performance", "api", "acceptance", "property_based"],
        default="unit",
        help="Type of testing required"
    )
    parser.add_argument(
        "--language",
        help="Programming language (python, javascript, java, cpp, etc.)"
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Requires browser automation"
    )
    parser.add_argument(
        "--mobile",
        action="store_true",
        help="Requires mobile testing"
    )
    parser.add_argument(
        "--performance",
        action="store_true",
        help="Requires performance/load testing"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Create selector
    selector = TestFrameworkSelector(project_dir=args.project_dir)

    # Build requirements
    requirements = {}
    if args.language:
        requirements["language"] = args.language
    if args.browser:
        requirements["browser"] = True
    if args.mobile:
        requirements["mobile"] = True
    if args.performance:
        requirements["performance"] = True

    # Get recommendation
    recommendation = selector.select_framework(
        requirements=requirements,
        test_type=args.test_type
    )

    # Output results
    if args.json:
        print(json.dumps({
            "framework": recommendation.framework,
            "confidence": recommendation.confidence,
            "rationale": recommendation.rationale,
            "alternatives": recommendation.alternatives
        }, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Test Framework Recommendation")
        print(f"{'='*60}")
        print(f"Framework:    {recommendation.framework}")
        print(f"Confidence:   {recommendation.confidence * 100:.0f}%")
        print(f"Rationale:    {recommendation.rationale}")
        if recommendation.alternatives:
            print(f"Alternatives: {', '.join(recommendation.alternatives)}")
        print(f"{'='*60}\n")
