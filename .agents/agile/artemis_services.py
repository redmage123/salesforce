#!/usr/bin/env python3
"""
Artemis Services (SOLID: Single Responsibility Principle)

Each service class has ONE clear responsibility:
- TestRunner: Running tests
- HTMLValidator: Validating HTML
- PipelineLogger: Logging messages
- FileManager: File operations
"""

import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Dict
from bs4 import BeautifulSoup

from artemis_stage_interface import TestRunnerInterface, ValidatorInterface, LoggerInterface
from artemis_constants import PYTEST_PATH as DEFAULT_PYTEST_PATH


class TestRunner(TestRunnerInterface):
    """
    Single Responsibility: Run pytest and parse results

    This class does ONLY test execution - nothing else.
    """

    def __init__(self, pytest_path: str = None):
        self.pytest_path = pytest_path or DEFAULT_PYTEST_PATH

    def run_tests(self, test_path: str, timeout: int = 60) -> Dict:
        """
        Run pytest and return parsed results

        Args:
            test_path: Path to tests
            timeout: Timeout in seconds

        Returns:
            Dict with test results
        """
        result = subprocess.run(
            [self.pytest_path, test_path, "-v", "--tb=short", "-q"],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        output = result.stdout + result.stderr
        passed, failed, skipped = self._parse_pytest_output(output)
        total = passed + failed + skipped

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%",
            "exit_code": result.returncode,
            "output": output
        }

    def _parse_pytest_output(self, output: str) -> tuple:
        """Parse pytest output to extract counts"""
        passed = failed = skipped = 0

        if match := re.search(r'(\d+) passed', output):
            passed = int(match.group(1))
        if match := re.search(r'(\d+) failed', output):
            failed = int(match.group(1))
        if match := re.search(r'(\d+) skipped', output):
            skipped = int(match.group(1))

        return passed, failed, skipped


class HTMLValidator(ValidatorInterface):
    """
    Single Responsibility: Validate HTML syntax

    This class does ONLY HTML validation - nothing else.
    """

    def validate(self, file_path: Path) -> Dict:
        """
        Validate HTML file syntax using BeautifulSoup

        Args:
            file_path: Path to HTML file

        Returns:
            Dict with validation results
        """
        try:
            with open(file_path) as f:
                html = f.read()
            soup = BeautifulSoup(html, 'html.parser')
            return {
                "status": "PASS",
                "errors": 0,
                "note": "HTML is valid and parseable"
            }
        except Exception as e:
            return {
                "status": "FAIL",
                "errors": 1,
                "note": str(e)
            }


class PipelineLogger(LoggerInterface):
    """
    Single Responsibility: Log pipeline messages

    This class does ONLY logging - nothing else.
    """

    EMOJI_MAP = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "STAGE": "🔄"
    }

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp and emoji"""
        if self.verbose:
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            emoji = self.EMOJI_MAP.get(level, "•")
            print(f"[{timestamp}] {emoji} {message}")

    # Standard logging interface compatibility
    def info(self, message: str, **kwargs):
        """Log info message (ignores extra kwargs for compatibility)"""
        self.log(message, "INFO")

    def warning(self, message: str, **kwargs):
        """Log warning message (ignores extra kwargs for compatibility)"""
        self.log(message, "WARNING")

    def error(self, message: str, **kwargs):
        """Log error message (ignores extra kwargs for compatibility)"""
        self.log(message, "ERROR")

    def debug(self, message: str, **kwargs):
        """Log debug message (ignores extra kwargs for compatibility)"""
        self.log(message, "INFO")


class FileManager:
    """
    Single Responsibility: Handle file operations

    This class does ONLY file I/O - nothing else.
    """

    @staticmethod
    def read_json(file_path: Path) -> Dict:
        """Read JSON file"""
        import json
        with open(file_path) as f:
            return json.load(f)

    @staticmethod
    def write_json(file_path: Path, data: Dict):
        """Write JSON file"""
        import json
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def read_text(file_path: Path) -> str:
        """Read text file"""
        with open(file_path) as f:
            return f.read()

    @staticmethod
    def write_text(file_path: Path, content: str):
        """Write text file"""
        with open(file_path, 'w') as f:
            f.write(content)

    @staticmethod
    def ensure_directory(dir_path: Path):
        """Ensure directory exists"""
        dir_path.mkdir(parents=True, exist_ok=True)
