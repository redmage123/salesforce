#!/usr/bin/env python3
"""
Gradle Build System Manager

Comprehensive Gradle integration for Artemis supporting:
- Groovy DSL and Kotlin DSL (build.gradle / build.gradle.kts)
- Project structure analysis
- Dependency management
- Task execution
- Multi-project builds
- Plugin management
- Android projects

Usage:
    from gradle_manager import GradleManager

    gradle = GradleManager(project_dir="/path/to/project")

    # Analyze project
    info = gradle.get_project_info()

    # Run tests
    result = gradle.run_tests()

    # Build project
    build_result = gradle.build()
"""

import subprocess
import re
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging


class GradleDSL(Enum):
    """Gradle DSL types"""
    GROOVY = "groovy"  # build.gradle
    KOTLIN = "kotlin"  # build.gradle.kts


@dataclass
class GradleDependency:
    """Gradle dependency representation"""
    configuration: str  # implementation, testImplementation, etc.
    group: str
    name: str
    version: str

    def __str__(self) -> str:
        return f"{self.configuration} '{self.group}:{self.name}:{self.version}'"


@dataclass
class GradlePlugin:
    """Gradle plugin representation"""
    plugin_id: str
    version: Optional[str] = None
    apply: bool = True

    def __str__(self) -> str:
        if self.version:
            return f"id '{self.plugin_id}' version '{self.version}'"
        return f"id '{self.plugin_id}'"


@dataclass
class GradleProjectInfo:
    """Gradle project information"""
    name: str
    version: str
    group: str
    dsl: GradleDSL
    plugins: List[GradlePlugin] = field(default_factory=list)
    dependencies: List[GradleDependency] = field(default_factory=list)
    subprojects: List[str] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)
    is_multi_project: bool = False
    is_android: bool = False
    source_compatibility: Optional[str] = None
    target_compatibility: Optional[str] = None


@dataclass
class GradleBuildResult:
    """Gradle build execution result"""
    success: bool
    exit_code: int
    duration: float
    output: str
    task: str
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class GradleManager:
    """
    Comprehensive Gradle build system manager for Artemis.

    Provides full Gradle integration including:
    - Groovy and Kotlin DSL support
    - Build script parsing
    - Dependency management
    - Task execution
    - Multi-project builds
    - Android project support
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Gradle manager.

        Args:
            project_dir: Gradle project root directory
            logger: Optional logger for output
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.logger = logger or logging.getLogger(__name__)

        # Detect build file
        self.build_file = self._find_build_file()
        self.settings_file = self.project_dir / "settings.gradle"
        if not self.settings_file.exists():
            self.settings_file = self.project_dir / "settings.gradle.kts"

        # Validate Gradle installation
        self._validate_gradle_installation()

    def _find_build_file(self) -> Optional[Path]:
        """Find Gradle build file (Groovy or Kotlin DSL)"""
        groovy = self.project_dir / "build.gradle"
        kotlin = self.project_dir / "build.gradle.kts"

        if kotlin.exists():
            return kotlin
        elif groovy.exists():
            return groovy
        return None

    def _validate_gradle_installation(self) -> None:
        """Validate that Gradle is installed and accessible"""
        try:
            # Try gradlew wrapper first
            gradlew = self.project_dir / "gradlew"
            if gradlew.exists():
                self.gradle_cmd = str(gradlew)
                result = subprocess.run(
                    [self.gradle_cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:
                # Fall back to system gradle
                self.gradle_cmd = "gradle"
                result = subprocess.run(
                    ["gradle", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            if result.returncode != 0:
                raise RuntimeError("Gradle is not properly installed")

            # Parse Gradle version
            version_match = re.search(r'Gradle (\d+\.\d+(?:\.\d+)?)', result.stdout)
            if version_match:
                self.gradle_version = version_match.group(1)
                self.logger.info(f"Detected Gradle version: {self.gradle_version}")

        except FileNotFoundError:
            raise RuntimeError(
                "Gradle not found. Please install Gradle or use Gradle wrapper: "
                "https://gradle.org/install/"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Gradle version check timed out")

    def is_gradle_project(self) -> bool:
        """Check if directory is a Gradle project"""
        return self.build_file is not None or self.settings_file.exists()

    def get_project_info(self) -> GradleProjectInfo:
        """
        Analyze Gradle project and extract comprehensive information.

        Returns:
            GradleProjectInfo with all project details
        """
        if not self.is_gradle_project():
            raise FileNotFoundError(f"No Gradle build file found in {self.project_dir}")

        # Determine DSL type
        dsl = GradleDSL.KOTLIN if self.build_file.suffix == ".kts" else GradleDSL.GROOVY

        # Get project properties via Gradle
        props = self._get_gradle_properties()

        name = props.get("name", self.project_dir.name)
        version = props.get("version", "unspecified")
        group = props.get("group", "")

        # Parse build file for plugins and dependencies
        plugins = self._parse_plugins()
        dependencies = self._parse_dependencies()

        # Get subprojects
        subprojects = self._get_subprojects()

        # Get tasks
        tasks = self._get_tasks()

        # Check if Android project
        is_android = any(
            "com.android" in p.plugin_id
            for p in plugins
        )

        # Get Java compatibility
        source_compat, target_compat = self._get_java_compatibility()

        return GradleProjectInfo(
            name=name,
            version=version,
            group=group,
            dsl=dsl,
            plugins=plugins,
            dependencies=dependencies,
            subprojects=subprojects,
            tasks=tasks,
            properties=props,
            is_multi_project=len(subprojects) > 0,
            is_android=is_android,
            source_compatibility=source_compat,
            target_compatibility=target_compat
        )

    def _get_gradle_properties(self) -> Dict[str, str]:
        """Get Gradle project properties"""
        try:
            result = subprocess.run(
                [self.gradle_cmd, "properties", "--quiet"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            props = {}
            for line in result.stdout.splitlines():
                if ": " in line:
                    key, value = line.split(": ", 1)
                    props[key.strip()] = value.strip()

            return props

        except Exception as e:
            self.logger.warning(f"Failed to get Gradle properties: {e}")
            return {}

    def _parse_plugins(self) -> List[GradlePlugin]:
        """Parse plugins from build file"""
        if not self.build_file:
            return []

        plugins = []
        content = self.build_file.read_text()

        # Parse plugins block
        # Match: id 'plugin-id' version 'x.y.z'
        plugin_pattern = r"id\s+['\"]([^'\"]+)['\"]\s*(?:version\s+['\"]([^'\"]+)['\"])?"

        for match in re.finditer(plugin_pattern, content):
            plugin_id = match.group(1)
            version = match.group(2)

            plugins.append(GradlePlugin(
                plugin_id=plugin_id,
                version=version
            ))

        # Also check for apply plugin syntax
        apply_pattern = r"apply\s+plugin:\s*['\"]([^'\"]+)['\"]"
        for match in re.finditer(apply_pattern, content):
            plugin_id = match.group(1)
            if not any(p.plugin_id == plugin_id for p in plugins):
                plugins.append(GradlePlugin(plugin_id=plugin_id))

        return plugins

    def _parse_dependencies(self) -> List[GradleDependency]:
        """Parse dependencies from build file"""
        if not self.build_file:
            return []

        dependencies = []
        content = self.build_file.read_text()

        # Match: implementation 'group:name:version'
        # Also: implementation group: 'g', name: 'n', version: 'v'
        dep_pattern1 = r"(\w+)\s+['\"]([^:'\"]+):([^:'\"]+):([^'\"]+)['\"]"
        dep_pattern2 = r"(\w+)\s+group:\s*['\"]([^'\"]+)['\"]\s*,\s*name:\s*['\"]([^'\"]+)['\"]\s*,\s*version:\s*['\"]([^'\"]+)['\"]"

        for match in re.finditer(dep_pattern1, content):
            config = match.group(1)
            group = match.group(2)
            name = match.group(3)
            version = match.group(4)

            dependencies.append(GradleDependency(
                configuration=config,
                group=group,
                name=name,
                version=version
            ))

        for match in re.finditer(dep_pattern2, content):
            config = match.group(1)
            group = match.group(2)
            name = match.group(3)
            version = match.group(4)

            dependencies.append(GradleDependency(
                configuration=config,
                group=group,
                name=name,
                version=version
            ))

        return dependencies

    def _get_subprojects(self) -> List[str]:
        """Get subprojects from settings file"""
        if not self.settings_file.exists():
            return []

        content = self.settings_file.read_text()
        subprojects = []

        # Match: include ':subproject'
        pattern = r"include\s+['\"]([^'\"]+)['\"]"

        for match in re.finditer(pattern, content):
            subproject = match.group(1).lstrip(":")
            subprojects.append(subproject)

        return subprojects

    def _get_tasks(self) -> List[str]:
        """Get available Gradle tasks"""
        try:
            result = subprocess.run(
                [self.gradle_cmd, "tasks", "--quiet"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            tasks = []
            for line in result.stdout.splitlines():
                # Tasks are listed as "taskName - description"
                if " - " in line and not line.startswith("-"):
                    task = line.split(" - ")[0].strip()
                    if task:
                        tasks.append(task)

            return tasks

        except Exception as e:
            self.logger.warning(f"Failed to get tasks: {e}")
            return []

    def _get_java_compatibility(self) -> Tuple[Optional[str], Optional[str]]:
        """Get Java source and target compatibility"""
        if not self.build_file:
            return None, None

        content = self.build_file.read_text()

        source_match = re.search(r"sourceCompatibility\s*=\s*['\"]?([^'\"\\s]+)", content)
        target_match = re.search(r"targetCompatibility\s*=\s*['\"]?([^'\"\\s]+)", content)

        source = source_match.group(1) if source_match else None
        target = target_match.group(1) if target_match else None

        return source, target

    def build(
        self,
        task: str = "build",
        clean: bool = True,
        offline: bool = False,
        extra_args: Optional[List[str]] = None,
        timeout: int = 600
    ) -> GradleBuildResult:
        """
        Execute Gradle build.

        Args:
            task: Gradle task to execute (default: build)
            clean: Run clean before build
            offline: Work offline
            extra_args: Additional Gradle arguments
            timeout: Build timeout in seconds

        Returns:
            GradleBuildResult with build outcome
        """
        import time
        start_time = time.time()

        # Build command
        cmd = [self.gradle_cmd]

        if clean:
            cmd.append("clean")

        cmd.append(task)

        if offline:
            cmd.append("--offline")

        if extra_args:
            cmd.extend(extra_args)

        # Execute build
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            duration = time.time() - start_time
            output = result.stdout + result.stderr

            # Parse test results
            tests_run = self._extract_number(output, r'(\d+) tests completed')
            tests_failed = self._extract_number(output, r'(\d+) failed')
            tests_skipped = self._extract_number(output, r'(\d+) skipped')
            tests_passed = tests_run - tests_failed - tests_skipped

            # Extract errors and warnings
            errors = []
            warnings = []

            for line in output.splitlines():
                if "error:" in line.lower() or "failed" in line.lower():
                    errors.append(line.strip())
                elif "warning:" in line.lower():
                    warnings.append(line.strip())

            success = result.returncode == 0 and "BUILD SUCCESSFUL" in output

            return GradleBuildResult(
                success=success,
                exit_code=result.returncode,
                duration=duration,
                output=output,
                task=task,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                tests_skipped=tests_skipped,
                errors=errors[:10],
                warnings=warnings[:10]
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return GradleBuildResult(
                success=False,
                exit_code=1,
                duration=duration,
                output=f"Build timed out after {timeout} seconds",
                task=task,
                errors=[f"Build timeout after {timeout}s"]
            )
        except Exception as e:
            duration = time.time() - start_time
            return GradleBuildResult(
                success=False,
                exit_code=1,
                duration=duration,
                output=str(e),
                task=task,
                errors=[f"Build error: {str(e)}"]
            )

    def run_tests(
        self,
        test_class: Optional[str] = None,
        test_method: Optional[str] = None,
        timeout: int = 300
    ) -> GradleBuildResult:
        """
        Run Gradle tests.

        Args:
            test_class: Specific test class to run
            test_method: Specific test method to run
            timeout: Test timeout in seconds

        Returns:
            GradleBuildResult with test results
        """
        extra_args = []

        if test_class:
            extra_args.append(f"--tests={test_class}")
            if test_method:
                extra_args[-1] += f".{test_method}"

        return self.build(
            task="test",
            clean=False,
            extra_args=extra_args,
            timeout=timeout
        )

    def _extract_number(self, text: str, pattern: str) -> int:
        """Extract number from text using regex pattern"""
        match = re.search(pattern, text)
        return int(match.group(1)) if match else 0


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Gradle Build System Manager"
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Gradle project directory"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Info command
    subparsers.add_parser("info", help="Show project information")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build project")
    build_parser.add_argument("--task", default="build", help="Gradle task")
    build_parser.add_argument("--no-clean", action="store_true", help="Don't clean before build")

    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("--class", dest="test_class", help="Test class to run")
    test_parser.add_argument("--method", dest="test_method", help="Test method to run")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Create Gradle manager
    gradle = GradleManager(project_dir=args.project_dir)

    # Execute command
    if args.command == "info":
        info = gradle.get_project_info()
        print(f"\n{'='*60}")
        print(f"Gradle Project Information")
        print(f"{'='*60}")
        print(f"Name:         {info.name}")
        print(f"Group:        {info.group}")
        print(f"Version:      {info.version}")
        print(f"DSL:          {info.dsl.value}")
        print(f"Multi-project: {info.is_multi_project}")
        print(f"Android:      {info.is_android}")
        if info.source_compatibility:
            print(f"Java Source:  {info.source_compatibility}")
        if info.target_compatibility:
            print(f"Java Target:  {info.target_compatibility}")
        if info.subprojects:
            print(f"Subprojects:  {', '.join(info.subprojects)}")
        print(f"Plugins:      {len(info.plugins)}")
        print(f"Dependencies: {len(info.dependencies)}")
        print(f"Tasks:        {len(info.tasks)}")
        print(f"{'='*60}\n")

    elif args.command == "build":
        result = gradle.build(
            task=args.task,
            clean=not args.no_clean
        )
        print(f"\n{'='*60}")
        print(f"Build Result: {'SUCCESS' if result.success else 'FAILURE'}")
        print(f"{'='*60}")
        print(f"Task:      {result.task}")
        print(f"Duration:  {result.duration:.2f}s")
        print(f"Exit Code: {result.exit_code}")
        if result.tests_run > 0:
            print(f"Tests:     {result.tests_passed}/{result.tests_run} passed")
        if result.errors:
            print(f"\nErrors:")
            for error in result.errors[:5]:
                print(f"  - {error}")
        print(f"{'='*60}\n")

    elif args.command == "test":
        result = gradle.run_tests(
            test_class=args.test_class,
            test_method=args.test_method
        )
        print(f"\n{'='*60}")
        print(f"Test Result: {'SUCCESS' if result.success else 'FAILURE'}")
        print(f"{'='*60}")
        print(f"Tests Run:    {result.tests_run}")
        print(f"Passed:       {result.tests_passed}")
        print(f"Failed:       {result.tests_failed}")
        print(f"Skipped:      {result.tests_skipped}")
        print(f"Duration:     {result.duration:.2f}s")
        print(f"{'='*60}\n")

    else:
        parser.print_help()
