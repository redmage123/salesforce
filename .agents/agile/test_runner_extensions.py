#!/usr/bin/env python3
"""
Test Runner Extensions - Jest, Robot Framework, Hypothesis

Additional framework support for TestRunner.
These methods are imported and used by test_runner.py
"""

import subprocess
import re
import json
import time
from pathlib import Path
from typing import Dict

# Import TestResult from test_runner
# Note: This will be a circular import, so we'll define it locally for now
from dataclasses import dataclass


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
        if self.total == 0:
            return 0.0
        return round((self.passed / self.total) * 100, 2)

    @property
    def success(self) -> bool:
        return self.failed == 0 and self.errors == 0


def run_jest(test_path: Path, timeout: int = 120) -> TestResult:
    """
    Run Jest (JavaScript/TypeScript) tests

    Jest is Facebook's testing framework for JavaScript.
    Commonly used for React, Node.js, and TypeScript projects.
    """
    start_time = time.time()

    try:
        # Run Jest with JSON output
        cmd = ["npx", "jest", str(test_path), "--json", "--coverage=false"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        duration = time.time() - start_time
        output = result.stdout + result.stderr

        # Parse Jest JSON output
        try:
            # Jest outputs JSON in stdout
            json_match = re.search(r'\{.*"numTotalTests".*\}', output, re.DOTALL)
            if json_match:
                jest_data = json.loads(json_match.group(0))

                total = jest_data.get('numTotalTests', 0)
                passed = jest_data.get('numPassedTests', 0)
                failed = jest_data.get('numFailedTests', 0)
                skipped = jest_data.get('numPendingTests', 0)

                return TestResult(
                    framework="jest",
                    passed=passed,
                    failed=failed,
                    skipped=skipped,
                    errors=0,
                    total=total,
                    exit_code=result.returncode,
                    duration=duration,
                    output=output
                )
        except json.JSONDecodeError:
            pass

        # Fallback: parse text output
        passed = output.count("✓") or output.count("PASS")
        failed = output.count("✕") or output.count("FAIL")

        return TestResult(
            framework="jest",
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
            framework="jest",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=timeout,
            output=f"Error: Tests timed out after {timeout} seconds"
        )
    except Exception as e:
        return TestResult(
            framework="jest",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=0.0,
            output=f"Error running jest: {e}"
        )


def run_robot(test_path: Path, timeout: int = 120) -> TestResult:
    """
    Run Robot Framework tests

    Robot Framework is a keyword-driven acceptance testing framework.
    Uses plain-text syntax that's readable by non-programmers.
    """
    start_time = time.time()

    try:
        # Run Robot Framework with XML output
        output_dir = test_path.parent / "robot_results"
        output_dir.mkdir(exist_ok=True)

        cmd = [
            "robot",
            "--outputdir", str(output_dir),
            "--output", "output.xml",
            str(test_path)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        duration = time.time() - start_time
        output = result.stdout + result.stderr

        # Parse Robot Framework output.xml
        output_xml = output_dir / "output.xml"
        if output_xml.exists():
            import xml.etree.ElementTree as ET
            tree = ET.parse(output_xml)
            root = tree.getroot()

            # Get statistics from XML
            stats = root.find('.//statistics/total/stat')
            if stats is not None:
                passed = int(stats.get('pass', 0))
                failed = int(stats.get('fail', 0))
                total = passed + failed

                return TestResult(
                    framework="robot",
                    passed=passed,
                    failed=failed,
                    skipped=0,
                    errors=0,
                    total=total,
                    exit_code=result.returncode,
                    duration=duration,
                    output=output
                )

        # Fallback: parse text output
        # Format: "X critical tests, Y passed, Z failed"
        match = re.search(r'(\d+) critical tests, (\d+) passed, (\d+) failed', output)
        if match:
            total = int(match.group(1))
            passed = int(match.group(2))
            failed = int(match.group(3))
        else:
            total = passed = failed = 0

        return TestResult(
            framework="robot",
            passed=passed,
            failed=failed,
            skipped=0,
            errors=0,
            total=total,
            exit_code=result.returncode,
            duration=duration,
            output=output
        )

    except subprocess.TimeoutExpired:
        return TestResult(
            framework="robot",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=timeout,
            output=f"Error: Tests timed out after {timeout} seconds"
        )
    except Exception as e:
        return TestResult(
            framework="robot",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=0.0,
            output=f"Error running robot framework: {e}"
        )


def run_hypothesis(test_path: Path, timeout: int = 120) -> TestResult:
    """
    Run Hypothesis (property-based testing) tests

    Hypothesis generates test cases based on properties/invariants.
    Runs with pytest but uses property-based testing strategies.
    """
    start_time = time.time()

    try:
        # Run pytest with Hypothesis
        # Hypothesis integrates with pytest, so we use pytest runner
        cmd = [
            "pytest",
            str(test_path),
            "-v",
            "--tb=short",
            "--hypothesis-show-statistics"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        duration = time.time() - start_time
        output = result.stdout + result.stderr

        # Parse pytest output (Hypothesis runs through pytest)
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        skipped = output.count(" SKIPPED")

        # Count Hypothesis-specific output
        hypothesis_tests = output.count("Hypothesis")

        return TestResult(
            framework="hypothesis",
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=0,
            total=passed + failed + skipped,
            exit_code=result.returncode,
            duration=duration,
            output=output
        )

    except subprocess.TimeoutExpired:
        return TestResult(
            framework="hypothesis",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=timeout,
            output=f"Error: Tests timed out after {timeout} seconds"
        )
    except Exception as e:
        return TestResult(
            framework="hypothesis",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=0.0,
            output=f"Error running hypothesis tests: {e}"
        )


def run_jmeter(test_path: Path, timeout: int = 120) -> TestResult:
    """
    Run JMeter (performance/load testing) tests

    JMeter is Apache's load testing tool for analyzing performance.
    Uses .jmx test plans to simulate load and measure response times.
    """
    start_time = time.time()

    try:
        # Find JMeter test plan files (.jmx)
        jmx_files = list(test_path.glob("**/*.jmx"))

        if not jmx_files:
            return TestResult(
                framework="jmeter",
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                total=0,
                exit_code=1,
                duration=0.0,
                output="Error: No JMeter test plan files (.jmx) found"
            )

        # Run first JMX file (or loop through all if needed)
        jmx_file = jmx_files[0]
        results_dir = test_path / "jmeter_results"
        results_dir.mkdir(exist_ok=True)

        cmd = [
            "jmeter",
            "-n",  # Non-GUI mode
            "-t", str(jmx_file),  # Test plan
            "-l", str(results_dir / "results.jtl"),  # Results log
            "-j", str(results_dir / "jmeter.log")  # JMeter log
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        duration = time.time() - start_time
        output = result.stdout + result.stderr

        # Parse JMeter results (simplified - JMeter doesn't have pass/fail like unit tests)
        # Check if test completed successfully
        if result.returncode == 0:
            # Read results.jtl to count samples
            results_file = results_dir / "results.jtl"
            if results_file.exists():
                with open(results_file, 'r') as f:
                    lines = f.readlines()
                    total = len([l for l in lines if l.strip() and not l.startswith('<')])

                return TestResult(
                    framework="jmeter",
                    passed=total,
                    failed=0,
                    skipped=0,
                    errors=0,
                    total=total,
                    exit_code=result.returncode,
                    duration=duration,
                    output=output
                )

        return TestResult(
            framework="jmeter",
            passed=0,
            failed=1,
            skipped=0,
            errors=0,
            total=1,
            exit_code=result.returncode,
            duration=duration,
            output=output
        )

    except subprocess.TimeoutExpired:
        return TestResult(
            framework="jmeter",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=timeout,
            output=f"Error: Tests timed out after {timeout} seconds"
        )
    except Exception as e:
        return TestResult(
            framework="jmeter",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=0.0,
            output=f"Error running jmeter: {e}"
        )


def run_playwright(test_path: Path, timeout: int = 120) -> TestResult:
    """
    Run Playwright (browser automation) tests

    Playwright is Microsoft's modern browser automation framework.
    Supports Chromium, Firefox, and WebKit with single API.
    """
    start_time = time.time()

    try:
        # Run Playwright tests via pytest (most common usage)
        cmd = [
            "pytest",
            str(test_path),
            "-v",
            "--tb=short",
            "--headed"  # Run in headed mode to see browser
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        duration = time.time() - start_time
        output = result.stdout + result.stderr

        # Parse pytest output
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        skipped = output.count(" SKIPPED")

        return TestResult(
            framework="playwright",
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=0,
            total=passed + failed + skipped,
            exit_code=result.returncode,
            duration=duration,
            output=output
        )

    except subprocess.TimeoutExpired:
        return TestResult(
            framework="playwright",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=timeout,
            output=f"Error: Tests timed out after {timeout} seconds"
        )
    except Exception as e:
        return TestResult(
            framework="playwright",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=0.0,
            output=f"Error running playwright: {e}"
        )


def run_appium(test_path: Path, timeout: int = 120) -> TestResult:
    """
    Run Appium (mobile automation) tests

    Appium is the standard for mobile app automation.
    Supports iOS, Android, and hybrid apps.
    """
    start_time = time.time()

    try:
        # Run Appium tests via pytest (common pattern)
        cmd = [
            "pytest",
            str(test_path),
            "-v",
            "--tb=short"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        duration = time.time() - start_time
        output = result.stdout + result.stderr

        # Parse pytest output
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        skipped = output.count(" SKIPPED")

        return TestResult(
            framework="appium",
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=0,
            total=passed + failed + skipped,
            exit_code=result.returncode,
            duration=duration,
            output=output
        )

    except subprocess.TimeoutExpired:
        return TestResult(
            framework="appium",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=timeout,
            output=f"Error: Tests timed out after {timeout} seconds"
        )
    except Exception as e:
        return TestResult(
            framework="appium",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=0.0,
            output=f"Error running appium: {e}"
        )


def run_selenium(test_path: Path, timeout: int = 120) -> TestResult:
    """
    Run Selenium (browser automation) tests

    Selenium is the classic browser automation framework.
    Supports Chrome, Firefox, Safari, Edge with WebDriver protocol.
    """
    start_time = time.time()

    try:
        # Run Selenium tests via pytest or unittest
        cmd = [
            "pytest",
            str(test_path),
            "-v",
            "--tb=short"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        duration = time.time() - start_time
        output = result.stdout + result.stderr

        # Parse pytest output
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        skipped = output.count(" SKIPPED")

        return TestResult(
            framework="selenium",
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=0,
            total=passed + failed + skipped,
            exit_code=result.returncode,
            duration=duration,
            output=output
        )

    except subprocess.TimeoutExpired:
        return TestResult(
            framework="selenium",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=timeout,
            output=f"Error: Tests timed out after {timeout} seconds"
        )
    except Exception as e:
        return TestResult(
            framework="selenium",
            passed=0,
            failed=0,
            skipped=0,
            errors=1,
            total=0,
            exit_code=1,
            duration=0.0,
            output=f"Error running selenium: {e}"
        )
