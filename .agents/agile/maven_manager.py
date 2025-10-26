#!/usr/bin/env python3
"""
Maven Build System Manager

Comprehensive Maven integration for Artemis supporting:
- Project structure analysis
- Dependency management
- Build lifecycle execution
- Test execution
- Plugin management
- Multi-module projects
- POM parsing and manipulation

Usage:
    from maven_manager import MavenManager

    maven = MavenManager(project_dir="/path/to/project")

    # Analyze project
    info = maven.get_project_info()

    # Run tests
    result = maven.run_tests()

    # Build project
    build_result = maven.build(skip_tests=False)

    # Add dependency
    maven.add_dependency("org.springframework.boot", "spring-boot-starter-web", "3.2.0")
"""

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import json
import logging


class MavenPhase(Enum):
    """Maven build lifecycle phases"""
    VALIDATE = "validate"
    COMPILE = "compile"
    TEST = "test"
    PACKAGE = "package"
    VERIFY = "verify"
    INSTALL = "install"
    DEPLOY = "deploy"
    CLEAN = "clean"
    SITE = "site"


class MavenScope(Enum):
    """Maven dependency scopes"""
    COMPILE = "compile"
    PROVIDED = "provided"
    RUNTIME = "runtime"
    TEST = "test"
    SYSTEM = "system"
    IMPORT = "import"


@dataclass
class MavenDependency:
    """Maven dependency representation"""
    group_id: str
    artifact_id: str
    version: str
    scope: str = "compile"
    type: str = "jar"
    classifier: Optional[str] = None
    optional: bool = False

    def to_xml(self) -> str:
        """Convert to POM XML format"""
        xml = f"""        <dependency>
            <groupId>{self.group_id}</groupId>
            <artifactId>{self.artifact_id}</artifactId>
            <version>{self.version}</version>"""

        if self.scope != "compile":
            xml += f"\n            <scope>{self.scope}</scope>"
        if self.type != "jar":
            xml += f"\n            <type>{self.type}</type>"
        if self.classifier:
            xml += f"\n            <classifier>{self.classifier}</classifier>"
        if self.optional:
            xml += f"\n            <optional>true</optional>"

        xml += "\n        </dependency>"
        return xml


@dataclass
class MavenPlugin:
    """Maven plugin representation"""
    group_id: str
    artifact_id: str
    version: str
    configuration: Dict = field(default_factory=dict)
    executions: List[Dict] = field(default_factory=list)


@dataclass
class MavenProjectInfo:
    """Maven project information"""
    group_id: str
    artifact_id: str
    version: str
    name: str
    packaging: str
    description: Optional[str] = None
    parent: Optional[Dict] = None
    modules: List[str] = field(default_factory=list)
    dependencies: List[MavenDependency] = field(default_factory=list)
    plugins: List[MavenPlugin] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)
    is_multi_module: bool = False

    def __str__(self) -> str:
        return f"{self.group_id}:{self.artifact_id}:{self.version}"


@dataclass
class MavenBuildResult:
    """Maven build execution result"""
    success: bool
    exit_code: int
    duration: float
    output: str
    phase: str
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class MavenManager:
    """
    Comprehensive Maven build system manager for Artemis.

    Provides full Maven integration including:
    - POM parsing and manipulation
    - Dependency management
    - Build lifecycle execution
    - Test execution
    - Multi-module project support
    """

    # Maven XML namespace
    MAVEN_NS = {"mvn": "http://maven.apache.org/POM/4.0.0"}

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Maven manager.

        Args:
            project_dir: Maven project root directory
            logger: Optional logger for output
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.logger = logger or logging.getLogger(__name__)
        self.pom_path = self.project_dir / "pom.xml"

        # Validate Maven installation
        self._validate_maven_installation()

    def _validate_maven_installation(self) -> None:
        """Validate that Maven is installed and accessible"""
        try:
            result = subprocess.run(
                ["mvn", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                raise RuntimeError("Maven is not properly installed")

            # Parse Maven version
            version_match = re.search(r'Apache Maven (\d+\.\d+\.\d+)', result.stdout)
            if version_match:
                self.maven_version = version_match.group(1)
                self.logger.info(f"Detected Maven version: {self.maven_version}")

        except FileNotFoundError:
            raise RuntimeError(
                "Maven (mvn) not found in PATH. Please install Maven: "
                "https://maven.apache.org/install.html"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Maven version check timed out")

    def is_maven_project(self) -> bool:
        """Check if directory is a Maven project"""
        return self.pom_path.exists()

    def get_project_info(self) -> MavenProjectInfo:
        """
        Parse POM and extract comprehensive project information.

        Returns:
            MavenProjectInfo with all project details
        """
        if not self.is_maven_project():
            raise FileNotFoundError(f"No pom.xml found in {self.project_dir}")

        tree = ET.parse(self.pom_path)
        root = tree.getroot()

        # Register namespace
        ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')

        # Extract basic info
        group_id = self._get_text(root, ".//mvn:groupId")
        artifact_id = self._get_text(root, ".//mvn:artifactId")
        version = self._get_text(root, ".//mvn:version")
        name = self._get_text(root, ".//mvn:name", artifact_id)
        packaging = self._get_text(root, ".//mvn:packaging", "jar")
        description = self._get_text(root, ".//mvn:description")

        # Extract parent info
        parent = None
        parent_elem = root.find(".//mvn:parent", self.MAVEN_NS)
        if parent_elem is not None:
            parent = {
                "groupId": self._get_text(parent_elem, ".//mvn:groupId"),
                "artifactId": self._get_text(parent_elem, ".//mvn:artifactId"),
                "version": self._get_text(parent_elem, ".//mvn:version")
            }

        # Extract modules (multi-module project)
        modules = []
        for module in root.findall(".//mvn:modules/mvn:module", self.MAVEN_NS):
            if module.text:
                modules.append(module.text.strip())

        # Extract properties
        properties = {}
        props_elem = root.find(".//mvn:properties", self.MAVEN_NS)
        if props_elem is not None:
            for prop in props_elem:
                tag = prop.tag.replace("{http://maven.apache.org/POM/4.0.0}", "")
                properties[tag] = prop.text or ""

        # Extract dependencies
        dependencies = []
        for dep in root.findall(".//mvn:dependencies/mvn:dependency", self.MAVEN_NS):
            dependencies.append(MavenDependency(
                group_id=self._get_text(dep, ".//mvn:groupId", ""),
                artifact_id=self._get_text(dep, ".//mvn:artifactId", ""),
                version=self._get_text(dep, ".//mvn:version", ""),
                scope=self._get_text(dep, ".//mvn:scope", "compile"),
                type=self._get_text(dep, ".//mvn:type", "jar"),
                classifier=self._get_text(dep, ".//mvn:classifier"),
                optional=self._get_text(dep, ".//mvn:optional", "false") == "true"
            ))

        # Extract plugins
        plugins = []
        for plugin in root.findall(".//mvn:build/mvn:plugins/mvn:plugin", self.MAVEN_NS):
            plugins.append(MavenPlugin(
                group_id=self._get_text(plugin, ".//mvn:groupId", "org.apache.maven.plugins"),
                artifact_id=self._get_text(plugin, ".//mvn:artifactId", ""),
                version=self._get_text(plugin, ".//mvn:version", "")
            ))

        return MavenProjectInfo(
            group_id=group_id,
            artifact_id=artifact_id,
            version=version,
            name=name,
            packaging=packaging,
            description=description,
            parent=parent,
            modules=modules,
            dependencies=dependencies,
            plugins=plugins,
            properties=properties,
            is_multi_module=len(modules) > 0
        )

    def _get_text(
        self,
        element: ET.Element,
        xpath: str,
        default: str = ""
    ) -> str:
        """Extract text from XML element with namespace support"""
        found = element.find(xpath, self.MAVEN_NS)
        return found.text.strip() if found is not None and found.text else default

    def build(
        self,
        phase: MavenPhase = MavenPhase.PACKAGE,
        skip_tests: bool = False,
        clean: bool = True,
        offline: bool = False,
        profiles: Optional[List[str]] = None,
        extra_args: Optional[List[str]] = None,
        timeout: int = 600
    ) -> MavenBuildResult:
        """
        Execute Maven build.

        Args:
            phase: Maven lifecycle phase to execute
            skip_tests: Skip test execution
            clean: Run clean before build
            offline: Work offline (use local repository only)
            profiles: Maven profiles to activate
            extra_args: Additional Maven arguments
            timeout: Build timeout in seconds

        Returns:
            MavenBuildResult with build outcome
        """
        import time
        start_time = time.time()

        # Build command
        cmd = ["mvn"]

        if clean:
            cmd.append("clean")

        cmd.append(phase.value)

        if skip_tests:
            cmd.extend(["-DskipTests", "-Dmaven.test.skip=true"])

        if offline:
            cmd.append("--offline")

        if profiles:
            cmd.append(f"-P{','.join(profiles)}")

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

            # Parse build results
            tests_run = self._extract_number(output, r'Tests run: (\d+)')
            tests_failed = self._extract_number(output, r'Failures: (\d+)')
            tests_skipped = self._extract_number(output, r'Skipped: (\d+)')
            tests_passed = tests_run - tests_failed - tests_skipped

            # Extract errors and warnings
            errors = re.findall(r'\[ERROR\] (.+)', output)
            warnings = re.findall(r'\[WARNING\] (.+)', output)

            success = result.returncode == 0 and "BUILD SUCCESS" in output

            return MavenBuildResult(
                success=success,
                exit_code=result.returncode,
                duration=duration,
                output=output,
                phase=phase.value,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                tests_skipped=tests_skipped,
                errors=errors[:10],  # Limit to first 10 errors
                warnings=warnings[:10]
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return MavenBuildResult(
                success=False,
                exit_code=1,
                duration=duration,
                output=f"Build timed out after {timeout} seconds",
                phase=phase.value,
                errors=[f"Build timeout after {timeout}s"]
            )
        except Exception as e:
            duration = time.time() - start_time
            return MavenBuildResult(
                success=False,
                exit_code=1,
                duration=duration,
                output=str(e),
                phase=phase.value,
                errors=[f"Build error: {str(e)}"]
            )

    def run_tests(
        self,
        test_class: Optional[str] = None,
        test_method: Optional[str] = None,
        timeout: int = 300
    ) -> MavenBuildResult:
        """
        Run Maven tests.

        Args:
            test_class: Specific test class to run
            test_method: Specific test method to run
            timeout: Test timeout in seconds

        Returns:
            MavenBuildResult with test results
        """
        extra_args = []

        if test_class:
            extra_args.append(f"-Dtest={test_class}")
            if test_method:
                extra_args[-1] += f"#{test_method}"

        return self.build(
            phase=MavenPhase.TEST,
            skip_tests=False,
            clean=False,
            extra_args=extra_args,
            timeout=timeout
        )

    def add_dependency(
        self,
        group_id: str,
        artifact_id: str,
        version: str,
        scope: str = "compile"
    ) -> bool:
        """
        Add dependency to pom.xml.

        Args:
            group_id: Dependency group ID
            artifact_id: Dependency artifact ID
            version: Dependency version
            scope: Dependency scope

        Returns:
            True if added successfully
        """
        try:
            tree = ET.parse(self.pom_path)
            root = tree.getroot()

            # Find or create dependencies section
            deps = root.find(".//mvn:dependencies", self.MAVEN_NS)
            if deps is None:
                deps = ET.SubElement(root, "{http://maven.apache.org/POM/4.0.0}dependencies")

            # Create new dependency element
            dep = ET.SubElement(deps, "{http://maven.apache.org/POM/4.0.0}dependency")

            gid = ET.SubElement(dep, "{http://maven.apache.org/POM/4.0.0}groupId")
            gid.text = group_id

            aid = ET.SubElement(dep, "{http://maven.apache.org/POM/4.0.0}artifactId")
            aid.text = artifact_id

            ver = ET.SubElement(dep, "{http://maven.apache.org/POM/4.0.0}version")
            ver.text = version

            if scope != "compile":
                scp = ET.SubElement(dep, "{http://maven.apache.org/POM/4.0.0}scope")
                scp.text = scope

            # Write back to file
            tree.write(self.pom_path, encoding="UTF-8", xml_declaration=True)

            self.logger.info(f"Added dependency: {group_id}:{artifact_id}:{version}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add dependency: {e}")
            return False

    def _extract_number(self, text: str, pattern: str) -> int:
        """Extract number from text using regex pattern"""
        match = re.search(pattern, text)
        return int(match.group(1)) if match else 0

    def get_dependency_tree(self) -> str:
        """Get Maven dependency tree"""
        try:
            result = subprocess.run(
                ["mvn", "dependency:tree"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.stdout
        except Exception as e:
            self.logger.error(f"Failed to get dependency tree: {e}")
            return ""

    def get_effective_pom(self) -> str:
        """Get effective POM (with all inheritance and interpolation resolved)"""
        try:
            result = subprocess.run(
                ["mvn", "help:effective-pom"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.stdout
        except Exception as e:
            self.logger.error(f"Failed to get effective POM: {e}")
            return ""


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Maven Build System Manager"
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Maven project directory"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Info command
    subparsers.add_parser("info", help="Show project information")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build project")
    build_parser.add_argument("--phase", default="package", help="Maven phase")
    build_parser.add_argument("--skip-tests", action="store_true", help="Skip tests")
    build_parser.add_argument("--no-clean", action="store_true", help="Don't clean before build")

    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("--class", dest="test_class", help="Test class to run")
    test_parser.add_argument("--method", dest="test_method", help="Test method to run")

    # Dependency command
    dep_parser = subparsers.add_parser("add-dep", help="Add dependency")
    dep_parser.add_argument("group_id", help="Group ID")
    dep_parser.add_argument("artifact_id", help="Artifact ID")
    dep_parser.add_argument("version", help="Version")
    dep_parser.add_argument("--scope", default="compile", help="Dependency scope")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Create Maven manager
    maven = MavenManager(project_dir=args.project_dir)

    # Execute command
    if args.command == "info":
        info = maven.get_project_info()
        print(f"\n{'='*60}")
        print(f"Maven Project Information")
        print(f"{'='*60}")
        print(f"Project:      {info}")
        print(f"Name:         {info.name}")
        print(f"Packaging:    {info.packaging}")
        if info.description:
            print(f"Description:  {info.description}")
        print(f"Multi-module: {info.is_multi_module}")
        if info.modules:
            print(f"Modules:      {', '.join(info.modules)}")
        print(f"Dependencies: {len(info.dependencies)}")
        print(f"Plugins:      {len(info.plugins)}")
        print(f"{'='*60}\n")

    elif args.command == "build":
        phase = MavenPhase(args.phase)
        result = maven.build(
            phase=phase,
            skip_tests=args.skip_tests,
            clean=not args.no_clean
        )
        print(f"\n{'='*60}")
        print(f"Build Result: {'SUCCESS' if result.success else 'FAILURE'}")
        print(f"{'='*60}")
        print(f"Phase:     {result.phase}")
        print(f"Duration:  {result.duration:.2f}s")
        print(f"Exit Code: {result.exit_code}")
        if not args.skip_tests:
            print(f"Tests:     {result.tests_passed}/{result.tests_run} passed")
        if result.errors:
            print(f"\nErrors:")
            for error in result.errors[:5]:
                print(f"  - {error}")
        print(f"{'='*60}\n")

    elif args.command == "test":
        result = maven.run_tests(
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

    elif args.command == "add-dep":
        success = maven.add_dependency(
            args.group_id,
            args.artifact_id,
            args.version,
            args.scope
        )
        if success:
            print(f"✓ Added dependency: {args.group_id}:{args.artifact_id}:{args.version}")
        else:
            print(f"✗ Failed to add dependency")

    else:
        parser.print_help()
