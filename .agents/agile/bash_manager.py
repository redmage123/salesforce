#!/usr/bin/env python3
"""
Bash Manager - Shell script build management

Handles bash script operations:
- shellcheck (static analysis)
- shfmt (formatting)
- bats (testing framework)
"""

from pathlib import Path
from typing import Dict, List, Optional
from build_manager_base import BuildManagerBase, wrap_exception
from build_system_exceptions import BuildException
from build_manager_factory import register_build_manager, BuildSystem


@register_build_manager(BuildSystem.BASH)
class BashManager(BuildManagerBase):
    """Manages bash shell script projects"""

    @wrap_exception
    def __init__(self, project_dir: Path):
        super().__init__(project_dir)
        self.shell_scripts = list(self.project_dir.glob("**/*.sh"))

    @property
    def name(self) -> str:
        return "bash"

    @wrap_exception
    def detect(self) -> bool:
        """Detect if bash project"""
        return len(self.shell_scripts) > 0

    @wrap_exception
    def install_dependencies(self) -> bool:
        """No dependencies for bash scripts"""
        return True

    @wrap_exception
    def build(self) -> bool:
        """Check syntax and format bash scripts"""
        all_passed = True

        # shellcheck for static analysis
        for script in self.shell_scripts:
            all_passed &= self._run_command(["shellcheck", str(script)])

        # shfmt for formatting check
        for script in self.shell_scripts:
            all_passed &= self._run_command(["shfmt", "-d", str(script)])

        return all_passed

    @wrap_exception
    def run_tests(self) -> bool:
        """Run bats tests if available"""
        test_dir = self.project_dir / "test"
        return (
            self._run_command(["bats", str(test_dir)])
            if test_dir.exists()
            else True
        )

    @wrap_exception
    def clean(self) -> bool:
        """No build artifacts for bash"""
        return True

    @wrap_exception
    def get_metadata(self) -> Dict:
        """Get bash project metadata"""
        return {
            "manager": "bash",
            "shell_scripts": [str(s.relative_to(self.project_dir)) for s in self.shell_scripts],
            "has_tests": (self.project_dir / "test").exists(),
            "script_count": len(self.shell_scripts)
        }


if __name__ == "__main__":
    import sys
    manager = BashManager(Path.cwd())
    sys.exit(0 if manager.detect() else 1)
