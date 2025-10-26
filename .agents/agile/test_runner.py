#!/usr/bin/env python3
"""
Universal Test Runner

Supports multiple test frameworks:
- pytest (Python)
- unittest/xUnit (Python)
- Google Test/gtest (C++)
- JUnit (Java)

Can be run manually or automatically as part of the pipeline.

Usage:
    # Automatic (from pipeline)
    runner = TestRunner(framework='pytest')
    results = runner.run_tests('/path/to/tests')

    # Manual (command-line)
    python test_runner.py --framework pytest --path /path/to/tests
"""

import subprocess
import json
import re
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

# Import framework extensions
from test_runner_extensions import run_jest, run_robot, run_hypothesis, run_jmeter, run_playwright, run_appium, run_selenium
from debug_mixin import DebugMixin


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


@dataclass
class TestResult:
    """Test execution results"""
    framework: str
    passed: int
    failed: int
    skipped: int
    errors: int
    total: int
    exit_code: int
    duration: float
    output: str

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage"""
        if self.total == 0:
            return 0.0
        return round((self.passed / self.total) * 100, 2)

    @property
    def success(self) -> bool:
        """Check if all tests passed"""
        return self.failed == 0 and self.errors == 0


class TestRunner(DebugMixin):
    """
    Universal test runner supporting multiple frameworks.

    Automatically detects test framework or uses specified framework.
    Can run tests manually or be invoked programmatically.
    """

    def __init__(
        self,
        framework: Optional[str] = None,
        verbose: bool = False,
        timeout: int = 120
    ):
        """
        Initialize test runner.

        Args:
            framework: Test framework to use (auto-detected if None)
            verbose: Enable verbose output
            timeout: Test execution timeout in seconds
        """
        DebugMixin.__init__(self, component_name="test_runner")
        self.framework = framework
        self.verbose = verbose
        self.timeout = timeout

    def run_tests(self, test_path: str) -> TestResult:
        """
        Run tests at specified path.

        Args:
            test_path: Path to test directory or file

        Returns:
            TestResult with execution details
        """
        test_path = Path(test_path)

        self.debug_trace("run_tests",
                        test_path=str(test_path),
                        framework=self.framework or "auto-detect",
                        timeout=self.timeout)

        if not test_path.exists():
            self.debug_log("Test path not found", test_path=str(test_path))
            return TestResult(
                framework="none",
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                total=0,
                exit_code=1,
                duration=0.0,
                output=f"Error: Test path not found: {test_path}"
            )

        # Auto-detect framework if not specified
        if not self.framework:
            self.framework = self._detect_framework(test_path)
            self.debug_log("Framework detected", framework=self.framework)

        # Run tests based on framework
        if self.framework == TestFramework.PYTEST.value:
            return self._run_pytest(test_path)
        elif self.framework == TestFramework.UNITTEST.value:
            return self._run_unittest(test_path)
        elif self.framework == TestFramework.GTEST.value:
            return self._run_gtest(test_path)
        elif self.framework == TestFramework.JUNIT.value:
            return self._run_junit(test_path)
        elif self.framework == TestFramework.JEST.value:
            return self._run_jest(test_path)
        elif self.framework == TestFramework.ROBOT.value:
            return self._run_robot(test_path)
        elif self.framework == TestFramework.HYPOTHESIS.value:
            return self._run_hypothesis(test_path)
        elif self.framework == TestFramework.JMETER.value:
            return self._run_jmeter(test_path)
        elif self.framework == TestFramework.PLAYWRIGHT.value:
            return self._run_playwright(test_path)
        elif self.framework == TestFramework.APPIUM.value:
            return self._run_appium(test_path)
        elif self.framework == TestFramework.SELENIUM.value:
            return self._run_selenium(test_path)
        else:
            return TestResult(
                framework="unknown",
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                total=0,
                exit_code=1,
                duration=0.0,
                output=f"Error: Unknown test framework: {self.framework}"
            )

    def _ensure_init_files(self, test_path: Path):
        """
        Ensure __init__.py files exist in test directories for unittest discovery.

        Args:
            test_path: Path to test directory
        """
        # Get all directories that need __init__.py (including root)
        dirs_needing_init = [test_path] + [d for d in test_path.rglob("*") if d.is_dir()]

        # Create missing __init__.py files
        for directory in dirs_needing_init:
            init_file = directory / "__init__.py"
            init_file.touch(exist_ok=True)

    def _detect_framework(self, test_path: Path) -> str:
        """Auto-detect test framework from test files"""

        # Check for JMeter test plans (.jmx files)
        if list(test_path.glob("**/*.jmx")):
            return TestFramework.JMETER.value

        # Check for Robot Framework (.robot files)
        if list(test_path.glob("**/*.robot")):
            return TestFramework.ROBOT.value

        # Check for Jest (JavaScript/TypeScript)
        if (test_path / "package.json").exists() or (test_path / "jest.config.js").exists():
            js_test_files = list(test_path.glob("**/*.test.js")) + list(test_path.glob("**/*.test.ts"))
            if js_test_files:
                return TestFramework.JEST.value

        # Check for pytest markers
        if list(test_path.glob("**/conftest.py")) or list(test_path.glob("**/pytest.ini")):
            return TestFramework.PYTEST.value

        # Check for Python test files and inspect imports
        python_files = list(test_path.glob("**/test_*.py")) + list(test_path.glob("**/*_test.py"))
        if python_files:
            # Sort by modification time (newest first) to prioritize current tests
            python_files = sorted(python_files, key=lambda p: p.stat().st_mtime, reverse=True)

            # Check most recent file for framework imports
            with open(python_files[0], 'r') as f:
                content = f.read()

                # Check for Playwright
                if "from playwright" in content or "import playwright" in content:
                    return TestFramework.PLAYWRIGHT.value

                # Check for Selenium
                if "from selenium" in content or "import selenium" in content:
                    return TestFramework.SELENIUM.value

                # Check for Appium
                if "from appium" in content or "import appium" in content:
                    return TestFramework.APPIUM.value

                # Check for Hypothesis
                if "from hypothesis" in content or "@given" in content:
                    return TestFramework.HYPOTHESIS.value

                # Check for unittest
                if "import unittest" in content:
                    return TestFramework.UNITTEST.value

                # Check for pytest
                if "import pytest" in content:
                    return TestFramework.PYTEST.value

        # Check for Google Test (C++ files)
        if list(test_path.glob("**/*_test.cpp")) or list(test_path.glob("**/*_test.cc")):
            return TestFramework.GTEST.value

        # Check for JUnit (Java files)
        if list(test_path.glob("**/*Test.java")):
            return TestFramework.JUNIT.value

        # Default to pytest for Python
        return TestFramework.PYTEST.value

    def _run_pytest(self, test_path: Path) -> TestResult:
        """Run pytest tests"""
        import time

        start_time = time.time()

        with self.debug_section("Running pytest", test_path=str(test_path)):
            try:
                cmd = ["pytest", str(test_path), "-v", "--tb=short", "--color=no"]

                if self.verbose:
                    cmd.append("-vv")

                self.debug_log("Executing pytest command", cmd=" ".join(cmd))

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )

                duration = time.time() - start_time
                output = result.stdout + result.stderr

                # Parse pytest output (Performance: Single-pass parsing O(n) vs O(4n))
                import re
                from collections import Counter
                pattern = re.compile(r' (PASSED|FAILED|SKIPPED|ERROR)')
                matches = pattern.findall(output)
                counts = Counter(matches)

                passed = counts.get('PASSED', 0)
                failed = counts.get('FAILED', 0)
                skipped = counts.get('SKIPPED', 0)
                errors = counts.get('ERROR', 0)

                self.debug_log("Pytest results",
                              passed=passed,
                              failed=failed,
                              skipped=skipped,
                              errors=errors,
                              duration_seconds=f"{duration:.2f}")

                return TestResult(
                    framework="pytest",
                    passed=passed,
                    failed=failed,
                    skipped=skipped,
                    errors=errors,
                    total=passed + failed + skipped + errors,
                    exit_code=result.returncode,
                    duration=duration,
                    output=output
                )

            except subprocess.TimeoutExpired:
                self.debug_log("Pytest timeout", timeout_seconds=self.timeout)
                return TestResult(
                    framework="pytest",
                    passed=0,
                    failed=0,
                    skipped=0,
                    errors=1,
                    total=0,
                    exit_code=1,
                    duration=self.timeout,
                    output=f"Error: Tests timed out after {self.timeout} seconds"
                )
            except Exception as e:
                self.debug_log("Pytest execution error", error=str(e))
                return TestResult(
                    framework="pytest",
                    passed=0,
                    failed=0,
                    skipped=0,
                    errors=1,
                    total=0,
                    exit_code=1,
                    duration=0.0,
                    output=f"Error running pytest: {e}"
                )

    def _run_unittest(self, test_path: Path) -> TestResult:
        """Run unittest/xUnit tests"""
        import time
        import os

        start_time = time.time()

        try:
            # Ensure __init__.py files exist in test directories for unittest discovery
            self._ensure_init_files(test_path)

            cmd = ["python", "-m", "unittest", "discover", "-s", str(test_path), "-v"]

            # Add project root to PYTHONPATH so tests can import from src/
            project_root = test_path.parent
            env = os.environ.copy()
            env['PYTHONPATH'] = str(project_root) + os.pathsep + env.get('PYTHONPATH', '')

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env
            )

            duration = time.time() - start_time
            output = result.stdout + result.stderr

            # Parse unittest output
            # Format: "Ran X tests in Y.YYYs"
            ran_match = re.search(r'Ran (\d+) tests', output)
            total = int(ran_match.group(1)) if ran_match else 0

            # Look for failures and errors
            failures = output.count("FAIL:")
            errors = output.count("ERROR:")

            # Check for import errors (when unittest discover finds 0 tests due to imports)
            # This happens when test files exist but can't be imported
            import_errors = output.count("ImportError:") + output.count("ModuleNotFoundError:")
            if total == 0 and import_errors > 0:
                # Tests exist but couldn't be imported - count as errors
                errors = import_errors
                total = import_errors

            passed = total - failures - errors

            return TestResult(
                framework="unittest",
                passed=passed,
                failed=failures,
                skipped=0,  # unittest doesn't report skipped in summary
                errors=errors,
                total=total,
                exit_code=result.returncode,
                duration=duration,
                output=output
            )

        except subprocess.TimeoutExpired:
            return TestResult(
                framework="unittest",
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                total=0,
                exit_code=1,
                duration=self.timeout,
                output=f"Error: Tests timed out after {self.timeout} seconds"
            )
        except Exception as e:
            return TestResult(
                framework="unittest",
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                total=0,
                exit_code=1,
                duration=0.0,
                output=f"Error running unittest: {e}"
            )

    def _run_gtest(self, test_path: Path) -> TestResult:
        """Run Google Test (C++) tests"""
        import time

        start_time = time.time()

        try:
            # Find gtest executable
            test_executables = list(test_path.glob("**/*_test")) + list(test_path.glob("**/test_*"))

            if not test_executables:
                return TestResult(
                    framework="gtest",
                    passed=0,
                    failed=0,
                    skipped=0,
                    errors=1,
                    total=0,
                    exit_code=1,
                    duration=0.0,
                    output="Error: No gtest executables found"
                )

            # Run first executable (or all if multiple)
            test_exe = test_executables[0]

            cmd = [str(test_exe), "--gtest_output=json:test_results.json"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(test_path)
            )

            duration = time.time() - start_time
            output = result.stdout + result.stderr

            # Parse gtest JSON output
            json_file = test_path / "test_results.json"
            if json_file.exists():
                with open(json_file, 'r') as f:
                    test_data = json.load(f)

                total = test_data.get('tests', 0)
                failures = test_data.get('failures', 0)
                errors = test_data.get('errors', 0)
                passed = total - failures - errors

                return TestResult(
                    framework="gtest",
                    passed=passed,
                    failed=failures,
                    skipped=0,
                    errors=errors,
                    total=total,
                    exit_code=result.returncode,
                    duration=duration,
                    output=output
                )
            else:
                # Fallback: parse text output
                passed = output.count("[       OK ]")
                failed = output.count("[  FAILED  ]")

                return TestResult(
                    framework="gtest",
                    passed=passed,
                    failed=failed,
                    skipped=0,
                    errors=0,
                    total=passed + failed,
                    exit_code=result.returncode,
                    duration=duration,
                    output=output
                )

        except subprocess.TimeoutExpired:
            return TestResult(
                framework="gtest",
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                total=0,
                exit_code=1,
                duration=self.timeout,
                output=f"Error: Tests timed out after {self.timeout} seconds"
            )
        except Exception as e:
            return TestResult(
                framework="gtest",
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                total=0,
                exit_code=1,
                duration=0.0,
                output=f"Error running gtest: {e}"
            )

    def _run_junit(self, test_path: Path) -> TestResult:
        """Run JUnit (Java) tests"""
        import time

        start_time = time.time()

        try:
            # Run JUnit tests via Maven or Gradle
            if (test_path / "pom.xml").exists():
                cmd = ["mvn", "test"]
            elif (test_path / "build.gradle").exists():
                cmd = ["gradle", "test"]
            else:
                return TestResult(
                    framework="junit",
                    passed=0,
                    failed=0,
                    skipped=0,
                    errors=1,
                    total=0,
                    exit_code=1,
                    duration=0.0,
                    output="Error: No Maven or Gradle build file found"
                )

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(test_path)
            )

            duration = time.time() - start_time
            output = result.stdout + result.stderr

            # Parse Maven/Gradle output
            # Format: "Tests run: X, Failures: Y, Errors: Z, Skipped: W"
            match = re.search(r'Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)', output)

            if match:
                total = int(match.group(1))
                failures = int(match.group(2))
                errors = int(match.group(3))
                skipped = int(match.group(4))
                passed = total - failures - errors - skipped
            else:
                total = failures = errors = skipped = passed = 0

            return TestResult(
                framework="junit",
                passed=passed,
                failed=failures,
                skipped=skipped,
                errors=errors,
                total=total,
                exit_code=result.returncode,
                duration=duration,
                output=output
            )

        except subprocess.TimeoutExpired:
            return TestResult(
                framework="junit",
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                total=0,
                exit_code=1,
                duration=self.timeout,
                output=f"Error: Tests timed out after {self.timeout} seconds"
            )
        except Exception as e:
            return TestResult(
                framework="junit",
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                total=0,
                exit_code=1,
                duration=0.0,
                output=f"Error running junit: {e}"
            )

    def _run_jest(self, test_path: Path) -> TestResult:
        """Run Jest tests (wrapper for extension function)"""
        return run_jest(test_path, self.timeout)

    def _run_robot(self, test_path: Path) -> TestResult:
        """Run Robot Framework tests (wrapper for extension function)"""
        return run_robot(test_path, self.timeout)

    def _run_hypothesis(self, test_path: Path) -> TestResult:
        """Run Hypothesis tests (wrapper for extension function)"""
        return run_hypothesis(test_path, self.timeout)

    def _run_jmeter(self, test_path: Path) -> TestResult:
        """Run JMeter tests (wrapper for extension function)"""
        return run_jmeter(test_path, self.timeout)

    def _run_playwright(self, test_path: Path) -> TestResult:
        """Run Playwright tests (wrapper for extension function)"""
        return run_playwright(test_path, self.timeout)

    def _run_appium(self, test_path: Path) -> TestResult:
        """Run Appium tests (wrapper for extension function)"""
        return run_appium(test_path, self.timeout)

    def _run_selenium(self, test_path: Path) -> TestResult:
        """Run Selenium tests (wrapper for extension function)"""
        return run_selenium(test_path, self.timeout)


# ============================================================================
# MANUAL EXECUTION (Command-Line Interface)
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Universal Test Runner - Supports pytest, unittest, gtest, junit"
    )
    parser.add_argument(
        "--framework",
        choices=["pytest", "unittest", "gtest", "junit", "jest", "robot", "hypothesis", "jmeter", "playwright", "appium", "selenium"],
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
        print(f"Total:    {result.total}")
        print(f"Passed:   {result.passed}")
        print(f"Failed:   {result.failed}")
        print(f"Skipped:  {result.skipped}")
        print(f"Errors:   {result.errors}")
        print(f"Pass Rate: {result.pass_rate}%")
        print(f"Duration: {result.duration:.2f}s")
        print(f"Status:   {'✅ SUCCESS' if result.success else '❌ FAILURE'}")
        print(f"{'='*60}\n")

        if args.verbose:
            print("Test Output:")
            print(result.output)

    # Exit with test result code
    exit(result.exit_code)
