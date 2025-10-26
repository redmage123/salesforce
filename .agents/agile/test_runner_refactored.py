#!/usr/bin/env python3
"""
Universal Test Runner - Refactored

Design Patterns Applied:
- Strategy Pattern: Different test execution strategies per framework
- Factory Pattern: FrameworkRunnerFactory creates appropriate runners
- Template Method: Base class defines test execution template
- Exception Wrapping: All exceptions wrapped with context

Best Practices:
- Single Responsibility Principle
- Dependency Injection
- Comprehensive logging
- Type hints
- Immutable result objects
"""

import subprocess
import json
import re
import time
import logging
from pathlib import Path
from typing import Dict, Optional, List, Protocol
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from artemis_exceptions import wrap_exception, PipelineStageError


# ============================================================================
# EXCEPTION HIERARCHY
# ============================================================================

class TestRunnerError(PipelineStageError):
    """Base exception for test runner errors"""
    pass


class TestPathNotFoundError(TestRunnerError):
    """Test path does not exist"""
    pass


class TestFrameworkNotFoundError(TestRunnerError):
    """Required test framework not installed"""
    pass


class TestExecutionError(TestRunnerError):
    """Error during test execution"""
    pass


class TestTimeoutError(TestRunnerError):
    """Test execution timeout"""
    pass


class TestOutputParsingError(TestRunnerError):
    """Error parsing test output"""
    pass


# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class TestFramework(Enum):
    """Supported test frameworks"""
    PYTEST = "pytest"
    UNITTEST = "unittest"
    GTEST = "gtest"
    JUNIT = "junit"
    JEST = "jest"
    ROBOT = "robot"
    HYPOTHESIS = "hypothesis"
    JMETER = "jmeter"
    PLAYWRIGHT = "playwright"
    APPIUM = "appium"
    SELENIUM = "selenium"


@dataclass(frozen=True)
class TestResult:
    """Immutable test execution results"""
    framework: str
    passed: int
    failed: int
    skipped: int
    errors: int
    total: int
    exit_code: int
    duration: float
    output: str
    metadata: Dict = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage"""
        if self.total == 0:
            return 0.0
        return round((self.passed / self.total) * 100, 2)

    @property
    def success(self) -> bool:
        """Check if all tests passed"""
        return self.failed == 0 and self.errors == 0 and self.total > 0


# ============================================================================
# STRATEGY PATTERN: Framework Runner Interface
# ============================================================================

class FrameworkRunner(Protocol):
    """Protocol defining framework runner interface"""

    def run(self, test_path: Path, timeout: int) -> TestResult:
        """Run tests and return results"""
        ...


class BaseFrameworkRunner(ABC):
    """
    Abstract base class for framework runners.

    Template Method Pattern: Defines skeleton of test execution.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @wrap_exception(TestExecutionError, "Test execution failed")
    def run(self, test_path: Path, timeout: int) -> TestResult:
        """
        Template method for running tests.

        Defines the skeleton of test execution:
        1. Validate test path
        2. Prepare command
        3. Execute tests
        4. Parse results
        5. Return structured result
        """
        self._validate_test_path(test_path)

        start_time = time.time()

        try:
            cmd = self._prepare_command(test_path)
            raw_result = self._execute_command(cmd, test_path, timeout)
            duration = time.time() - start_time

            return self._parse_results(raw_result, duration)

        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            raise TestTimeoutError(
                f"Tests timed out after {timeout} seconds",
                {"framework": self.framework_name, "timeout": timeout}
            ) from e
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Test execution failed: {e}", exc_info=True)
            raise TestExecutionError(
                f"Failed to execute {self.framework_name} tests",
                {"framework": self.framework_name, "error": str(e)}
            ) from e

    def _validate_test_path(self, test_path: Path) -> None:
        """Validate test path exists"""
        if not test_path.exists():
            raise TestPathNotFoundError(
                f"Test path not found: {test_path}",
                {"path": str(test_path)}
            )

    @abstractmethod
    def _prepare_command(self, test_path: Path) -> List[str]:
        """Prepare command to execute tests"""
        pass

    def _execute_command(
        self,
        cmd: List[str],
        test_path: Path,
        timeout: int
    ) -> subprocess.CompletedProcess:
        """Execute test command"""
        try:
            self.logger.info(f"Executing: {' '.join(cmd)}")
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(test_path.parent) if test_path.is_file() else str(test_path)
            )
        except FileNotFoundError as e:
            raise TestFrameworkNotFoundError(
                f"{self.framework_name} not found in PATH",
                {"framework": self.framework_name, "command": cmd[0]}
            ) from e

    @abstractmethod
    def _parse_results(
        self,
        result: subprocess.CompletedProcess,
        duration: float
    ) -> TestResult:
        """Parse test execution results"""
        pass

    @property
    @abstractmethod
    def framework_name(self) -> str:
        """Framework name"""
        pass


# ============================================================================
# CONCRETE FRAMEWORK RUNNERS
# ============================================================================

class PytestRunner(BaseFrameworkRunner):
    """pytest framework runner"""

    @property
    def framework_name(self) -> str:
        return "pytest"

    def _prepare_command(self, test_path: Path) -> List[str]:
        return ["pytest", str(test_path), "-v", "--tb=short", "--color=no"]

    @wrap_exception(TestOutputParsingError, "Failed to parse pytest output")
    def _parse_results(
        self,
        result: subprocess.CompletedProcess,
        duration: float
    ) -> TestResult:
        output = result.stdout + result.stderr

        # Performance: Single-pass parsing instead of 4 separate count() calls (O(n) vs O(4n))
        import re
        pattern = re.compile(r' (PASSED|FAILED|SKIPPED|ERROR)')
        matches = pattern.findall(output)
        from collections import Counter
        counts = Counter(matches)

        passed = counts.get('PASSED', 0)
        failed = counts.get('FAILED', 0)
        skipped = counts.get('SKIPPED', 0)
        errors = counts.get('ERROR', 0)

        return TestResult(
            framework=self.framework_name,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            total=passed + failed + skipped + errors,
            exit_code=result.returncode,
            duration=duration,
            output=output
        )


class UnittestRunner(BaseFrameworkRunner):
    """unittest framework runner"""

    @property
    def framework_name(self) -> str:
        return "unittest"

    def _prepare_command(self, test_path: Path) -> List[str]:
        return ["python", "-m", "unittest", "discover", "-s", str(test_path), "-v"]

    @wrap_exception(TestOutputParsingError, "Failed to parse unittest output")
    def _parse_results(
        self,
        result: subprocess.CompletedProcess,
        duration: float
    ) -> TestResult:
        output = result.stdout + result.stderr

        # Parse unittest output: "Ran X tests in Y.YYYs"
        ran_match = re.search(r'Ran (\d+) tests', output)
        total = int(ran_match.group(1)) if ran_match else 0

        failures = output.count("FAIL:")
        errors = output.count("ERROR:")
        passed = total - failures - errors

        return TestResult(
            framework=self.framework_name,
            passed=passed,
            failed=failures,
            skipped=0,
            errors=errors,
            total=total,
            exit_code=result.returncode,
            duration=duration,
            output=output
        )


# ============================================================================
# FACTORY PATTERN: Framework Runner Factory
# ============================================================================

class FrameworkRunnerFactory:
    """
    Factory for creating framework runners.

    Factory Pattern: Encapsulates object creation logic.
    """

    _runners: Dict[TestFramework, type[BaseFrameworkRunner]] = {
        TestFramework.PYTEST: PytestRunner,
        TestFramework.UNITTEST: UnittestRunner,
        # Additional runners will be registered here
    }

    @classmethod
    def register_runner(
        cls,
        framework: TestFramework,
        runner_class: type[BaseFrameworkRunner]
    ) -> None:
        """Register a new framework runner"""
        cls._runners[framework] = runner_class

    @classmethod
    @wrap_exception(TestRunnerError, "Failed to create framework runner")
    def create_runner(
        cls,
        framework: TestFramework,
        logger: Optional[logging.Logger] = None
    ) -> BaseFrameworkRunner:
        """Create framework runner instance"""
        runner_class = cls._runners.get(framework)

        if not runner_class:
            raise TestRunnerError(
                f"No runner registered for framework: {framework.value}",
                {"framework": framework.value, "available": list(cls._runners.keys())}
            )

        return runner_class(logger=logger)


# ============================================================================
# FACADE: TestRunner - Simplified Interface
# ============================================================================

class TestRunner:
    """
    Unified interface for running tests across multiple frameworks.

    Facade Pattern: Provides simplified interface to complex subsystem.
    Dependency Injection: Accepts logger as dependency.
    """

    def __init__(
        self,
        framework: Optional[str] = None,
        verbose: bool = False,
        timeout: int = 120,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize test runner.

        Args:
            framework: Test framework to use (auto-detected if None)
            verbose: Enable verbose output
            timeout: Test execution timeout in seconds
            logger: Logger instance for dependency injection
        """
        self.framework = framework
        self.verbose = verbose
        self.timeout = timeout
        self.logger = logger or self._create_default_logger(verbose)
        self._detector = FrameworkDetector(logger=self.logger)

    def _create_default_logger(self, verbose: bool) -> logging.Logger:
        """Create default logger"""
        logger = logging.getLogger("TestRunner")
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    @wrap_exception(TestRunnerError, "Test execution failed")
    def run_tests(self, test_path: str) -> TestResult:
        """
        Run tests at specified path.

        Args:
            test_path: Path to test directory or file

        Returns:
            TestResult with execution details

        Raises:
            TestPathNotFoundError: If test path doesn't exist
            TestFrameworkNotFoundError: If framework not installed
            TestExecutionError: If test execution fails
        """
        test_path_obj = Path(test_path)

        # Auto-detect framework if not specified
        if not self.framework:
            self.framework = self._detector.detect_framework(test_path_obj)
            self.logger.info(f"Auto-detected framework: {self.framework}")

        # Get framework enum
        try:
            framework_enum = TestFramework(self.framework)
        except ValueError as e:
            raise TestRunnerError(
                f"Unknown framework: {self.framework}",
                {"framework": self.framework}
            ) from e

        # Create runner and execute tests
        runner = FrameworkRunnerFactory.create_runner(framework_enum, self.logger)
        result = runner.run(test_path_obj, self.timeout)

        self._log_results(result)
        return result

    def _log_results(self, result: TestResult) -> None:
        """Log test results"""
        self.logger.info(
            f"Tests completed: {result.passed} passed, {result.failed} failed, "
            f"{result.skipped} skipped, {result.errors} errors "
            f"({result.pass_rate}% pass rate)"
        )


# ============================================================================
# FRAMEWORK DETECTION
# ============================================================================

class FrameworkDetector:
    """
    Detects test framework from project structure.

    Single Responsibility: Only responsible for framework detection.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("FrameworkDetector")

    @wrap_exception(TestRunnerError, "Framework detection failed")
    def detect_framework(self, test_path: Path) -> str:
        """Auto-detect test framework from test files"""

        # Check for JMeter test plans (.jmx files)
        if list(test_path.glob("**/*.jmx")):
            return TestFramework.JMETER.value

        # Check for Robot Framework (.robot files)
        if list(test_path.glob("**/*.robot")):
            return TestFramework.ROBOT.value

        # Check for Jest (JavaScript/TypeScript)
        if self._is_jest_project(test_path):
            return TestFramework.JEST.value

        # Check for pytest markers
        if list(test_path.glob("**/conftest.py")) or list(test_path.glob("**/pytest.ini")):
            return TestFramework.PYTEST.value

        # Check for Python test files and inspect imports
        framework = self._detect_from_python_files(test_path)
        if framework:
            return framework

        # Check for Google Test (C++ files)
        if list(test_path.glob("**/*_test.cpp")) or list(test_path.glob("**/*_test.cc")):
            return TestFramework.GTEST.value

        # Check for JUnit (Java files)
        if list(test_path.glob("**/*Test.java")):
            return TestFramework.JUNIT.value

        # Default to pytest for Python
        self.logger.warning("Could not detect framework, defaulting to pytest")
        return TestFramework.PYTEST.value

    def _is_jest_project(self, test_path: Path) -> bool:
        """Check if project uses Jest"""
        if (test_path / "package.json").exists() or (test_path / "jest.config.js").exists():
            js_test_files = list(test_path.glob("**/*.test.js")) + list(test_path.glob("**/*.test.ts"))
            return len(js_test_files) > 0
        return False

    @wrap_exception(TestRunnerError, "Failed to detect framework from Python files")
    def _detect_from_python_files(self, test_path: Path) -> Optional[str]:
        """Detect framework from Python test files"""
        python_files = list(test_path.glob("**/test_*.py")) + list(test_path.glob("**/*_test.py"))

        if not python_files:
            return None

        try:
            with open(python_files[0], 'r') as f:
                content = f.read()

                # Check for various frameworks
                if "from playwright" in content or "import playwright" in content:
                    return TestFramework.PLAYWRIGHT.value

                if "from selenium" in content or "import selenium" in content:
                    return TestFramework.SELENIUM.value

                if "from appium" in content or "import appium" in content:
                    return TestFramework.APPIUM.value

                if "from hypothesis" in content or "@given" in content:
                    return TestFramework.HYPOTHESIS.value

                if "import unittest" in content:
                    return TestFramework.UNITTEST.value

                if "import pytest" in content:
                    return TestFramework.PYTEST.value

        except (IOError, OSError) as e:
            self.logger.warning(f"Could not read test file: {e}")
            return None

        return None


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Universal Test Runner - Supports multiple test frameworks"
    )
    parser.add_argument(
        "--framework",
        choices=[f.value for f in TestFramework],
        help="Test framework to use (auto-detected if not specified)"
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Path to test directory or file"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Test execution timeout in seconds (default: 120)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        # Run tests
        runner = TestRunner(
            framework=args.framework,
            verbose=args.verbose,
            timeout=args.timeout
        )

        result = runner.run_tests(args.path)

        # Output results
        if args.json:
            print(json.dumps({
                "framework": result.framework,
                "passed": result.passed,
                "failed": result.failed,
                "skipped": result.skipped,
                "errors": result.errors,
                "total": result.total,
                "pass_rate": result.pass_rate,
                "success": result.success,
                "exit_code": result.exit_code,
                "duration": result.duration
            }, indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"Test Results ({result.framework})")
            print(f"{'='*60}")
            print(f"Total:     {result.total}")
            print(f"Passed:    {result.passed}")
            print(f"Failed:    {result.failed}")
            print(f"Skipped:   {result.skipped}")
            print(f"Errors:    {result.errors}")
            print(f"Pass Rate: {result.pass_rate}%")
            print(f"Duration:  {result.duration:.2f}s")
            print(f"Status:    {'✅ SUCCESS' if result.success else '❌ FAILURE'}")
            print(f"{'='*60}\n")

            if args.verbose:
                print("Test Output:")
                print(result.output)

        # Exit with test result code
        sys.exit(result.exit_code)

    except TestRunnerError as e:
        logging.error(f"Test runner error: {e}")
        if args.json:
            print(json.dumps({"error": str(e), "type": type(e).__name__}, indent=2))
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        if args.json:
            print(json.dumps({"error": str(e), "type": "UnexpectedError"}, indent=2))
        sys.exit(1)
