#!/usr/bin/env python3
"""
.NET Build Manager (C#/F#/VB.NET)

Enterprise-grade .NET build system management using dotnet CLI.

Design Patterns:
- Template Method: Inherits from BuildManagerBase
- Exception Wrapper: All errors properly wrapped
- Strategy Pattern: Different build configurations and frameworks
"""

from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
import re
import xml.etree.ElementTree as ET

from artemis_exceptions import wrap_exception
from build_system_exceptions import (
    BuildSystemNotFoundError,
    ProjectConfigurationError,
    BuildExecutionError,
    TestExecutionError,
    DependencyInstallError
)
from build_manager_base import BuildManagerBase, BuildResult
from build_manager_factory import register_build_manager, BuildSystem


class BuildConfiguration(Enum):
    """Build configurations"""
    DEBUG = "Debug"
    RELEASE = "Release"


class TargetFramework(Enum):
    """Common .NET target frameworks"""
    NET8 = "net8.0"
    NET7 = "net7.0"
    NET6 = "net6.0"
    NET_STANDARD_2_1 = "netstandard2.1"
    NET_STANDARD_2_0 = "netstandard2.0"
    NET_FRAMEWORK_4_8 = "net48"


class ProjectType(Enum):
    """Project types"""
    CONSOLE = "console"
    CLASSLIB = "classlib"
    WEB = "web"
    WEBAPI = "webapi"
    MVC = "mvc"
    BLAZOR = "blazorserver"
    WORKER = "worker"


@dataclass
class DotNetProjectInfo:
    """.csproj/.fsproj project information"""
    project_name: str
    target_framework: str
    project_type: Optional[str] = None
    sdk: str = "Microsoft.NET.Sdk"
    output_type: Optional[str] = None
    package_references: Dict[str, str] = field(default_factory=dict)
    project_references: List[str] = field(default_factory=list)
    is_solution: bool = False
    solution_projects: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "projectName": self.project_name,
            "targetFramework": self.target_framework,
            "projectType": self.project_type,
            "sdk": self.sdk,
            "outputType": self.output_type,
            "packageReferences": self.package_references,
            "projectReferences": self.project_references,
            "isSolution": self.is_solution,
            "solutionProjects": self.solution_projects
        }


@register_build_manager(BuildSystem.DOTNET)
class DotNetManager(BuildManagerBase):
    """
    Enterprise-grade .NET manager for C#/F#/VB.NET projects.

    Example:
        dotnet = DotNetManager(project_dir="/path/to/project")
        result = dotnet.build(configuration="Release")
        test_result = dotnet.test()
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional['logging.Logger'] = None
    ):
        """
        Initialize .NET manager.

        Args:
            project_dir: Project directory (contains .csproj/.sln)
            logger: Logger instance

        Raises:
            BuildSystemNotFoundError: If dotnet not found
            ProjectConfigurationError: If project file invalid
        """
        self.project_file = None
        self.solution_file = None
        self.is_solution = False

        super().__init__(project_dir, logger)

    @wrap_exception(BuildSystemNotFoundError, ".NET SDK not found")
    def _validate_installation(self) -> None:
        """
        Validate .NET SDK is installed.

        Raises:
            BuildSystemNotFoundError: If dotnet not in PATH
        """
        result = self._execute_command(
            ["dotnet", "--version"],
            timeout=10,
            error_type=BuildSystemNotFoundError,
            error_message=".NET SDK not installed or not in PATH"
        )

        # Extract version
        version = result.output.strip()
        self.logger.info(f"Using .NET SDK version: {version}")

    @wrap_exception(ProjectConfigurationError, "Invalid .NET project")
    def _validate_project(self) -> None:
        """
        Validate project or solution file exists.

        Raises:
            ProjectConfigurationError: If no project/solution file found
        """
        # Check for solution file first
        sln_files = list(self.project_dir.glob("*.sln"))
        if sln_files:
            self.solution_file = sln_files[0]
            self.is_solution = True
            self.logger.info(f"Found solution file: {self.solution_file.name}")
            return

        # Check for project files
        project_files = (
            list(self.project_dir.glob("*.csproj")) +
            list(self.project_dir.glob("*.fsproj")) +
            list(self.project_dir.glob("*.vbproj"))
        )

        if not project_files:
            raise ProjectConfigurationError(
                "No .NET project or solution file found",
                {"project_dir": str(self.project_dir)}
            )

        self.project_file = project_files[0]
        self.logger.info(f"Found project file: {self.project_file.name}")

    @wrap_exception(ProjectConfigurationError, "Failed to parse project file")
    def get_project_info(self) -> Dict[str, Any]:
        """
        Parse project/solution file for information.

        Returns:
            Dict with project information

        Raises:
            ProjectConfigurationError: If project file malformed
        """
        if self.is_solution:
            return self._parse_solution()
        else:
            return self._parse_project()

    def _parse_solution(self) -> Dict[str, Any]:
        """Parse .sln file"""
        solution_projects = []

        with open(self.solution_file, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        # Parse project lines: Project("{GUID}") = "ProjectName", "Path/To/Project.csproj", "{GUID}"
        project_pattern = r'Project\("[^"]+"\)\s*=\s*"([^"]+)",\s*"([^"]+)"'
        for match in re.finditer(project_pattern, content):
            project_name = match.group(1)
            project_path = match.group(2)
            if project_path.endswith(('.csproj', '.fsproj', '.vbproj')):
                solution_projects.append(project_path)

        info = DotNetProjectInfo(
            project_name=self.solution_file.stem,
            target_framework="",  # Solution doesn't have target framework
            is_solution=True,
            solution_projects=solution_projects
        )

        return info.to_dict()

    def _parse_project(self) -> Dict[str, Any]:
        """Parse .csproj/.fsproj/.vbproj file"""
        tree = ET.parse(self.project_file)
        root = tree.getroot()

        # Get SDK
        sdk = root.get('Sdk', 'Microsoft.NET.Sdk')

        # Get PropertyGroup elements
        target_framework = ""
        output_type = None

        for prop_group in root.findall('.//PropertyGroup'):
            if prop_group.find('TargetFramework') is not None:
                target_framework = prop_group.find('TargetFramework').text or ""
            if prop_group.find('OutputType') is not None:
                output_type = prop_group.find('OutputType').text

        # Get package references
        package_references = {}
        for item_group in root.findall('.//ItemGroup'):
            for package_ref in item_group.findall('PackageReference'):
                package_name = package_ref.get('Include')
                version = package_ref.get('Version', '')
                if package_name:
                    package_references[package_name] = version

        # Get project references
        project_references = []
        for item_group in root.findall('.//ItemGroup'):
            for proj_ref in item_group.findall('ProjectReference'):
                proj_path = proj_ref.get('Include')
                if proj_path:
                    project_references.append(proj_path)

        info = DotNetProjectInfo(
            project_name=self.project_file.stem,
            target_framework=target_framework,
            sdk=sdk,
            output_type=output_type,
            package_references=package_references,
            project_references=project_references,
            is_solution=False
        )

        return info.to_dict()

    @wrap_exception(BuildExecutionError, ".NET build failed")
    def build(
        self,
        configuration: str = "Debug",
        framework: Optional[str] = None,
        runtime: Optional[str] = None,
        no_restore: bool = False,
        **kwargs
    ) -> BuildResult:
        """
        Build .NET project.

        Args:
            configuration: Build configuration (Debug/Release)
            framework: Target framework (net8.0, net6.0, etc.)
            runtime: Runtime identifier (win-x64, linux-x64, etc.)
            no_restore: Skip restoring dependencies

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If build fails

        Example:
            result = dotnet.build(configuration="Release", framework="net8.0")
        """
        cmd = ["dotnet", "build"]

        # Use solution or project file
        if self.is_solution:
            cmd.append(str(self.solution_file))
        elif self.project_file:
            cmd.append(str(self.project_file))

        cmd.extend(["-c", configuration])

        if framework:
            cmd.extend(["-f", framework])

        if runtime:
            cmd.extend(["-r", runtime])

        if no_restore:
            cmd.append("--no-restore")

        return self._execute_command(
            cmd,
            timeout=600,
            error_type=BuildExecutionError,
            error_message=".NET build failed"
        )

    @wrap_exception(TestExecutionError, ".NET tests failed")
    def test(
        self,
        configuration: str = "Debug",
        no_build: bool = False,
        verbosity: Optional[str] = None,
        filter: Optional[str] = None,
        **kwargs
    ) -> BuildResult:
        """
        Run .NET tests.

        Args:
            configuration: Build configuration
            no_build: Skip building before testing
            verbosity: Log verbosity (q[uiet], m[inimal], n[ormal], d[etailed], diag[nostic])
            filter: Test filter expression

        Returns:
            BuildResult with test statistics

        Raises:
            TestExecutionError: If tests fail

        Example:
            result = dotnet.test(configuration="Release", verbosity="normal")
        """
        cmd = ["dotnet", "test"]

        # Use solution or project file
        if self.is_solution:
            cmd.append(str(self.solution_file))
        elif self.project_file:
            cmd.append(str(self.project_file))

        cmd.extend(["-c", configuration])

        if no_build:
            cmd.append("--no-build")

        if verbosity:
            cmd.extend(["-v", verbosity])

        if filter:
            cmd.extend(["--filter", filter])

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=TestExecutionError,
            error_message=".NET test execution failed"
        )

    @wrap_exception(DependencyInstallError, "Failed to add package")
    def install_dependency(
        self,
        package: str,
        version: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Add a NuGet package to project.

        Args:
            package: Package name
            version: Package version (optional)

        Returns:
            True if successful

        Raises:
            DependencyInstallError: If installation fails

        Example:
            dotnet.install_dependency("Newtonsoft.Json", version="13.0.3")
        """
        if self.is_solution:
            raise DependencyInstallError(
                "Cannot add package to solution. Specify project file.",
                {"package": package}
            )

        cmd = ["dotnet", "add", str(self.project_file), "package", package]

        if version:
            cmd.extend(["-v", version])

        result = self._execute_command(
            cmd,
            timeout=120,
            error_type=DependencyInstallError,
            error_message=f"Failed to add package {package}"
        )

        self.logger.info(f"Added package {package}")
        return True

    @wrap_exception(BuildExecutionError, "Failed to restore dependencies")
    def restore(self) -> BuildResult:
        """
        Restore NuGet packages.

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If restore fails

        Example:
            dotnet.restore()
        """
        cmd = ["dotnet", "restore"]

        if self.is_solution:
            cmd.append(str(self.solution_file))
        elif self.project_file:
            cmd.append(str(self.project_file))

        return self._execute_command(
            cmd,
            timeout=300,
            error_type=BuildExecutionError,
            error_message="NuGet restore failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to publish")
    def publish(
        self,
        configuration: str = "Release",
        framework: Optional[str] = None,
        runtime: Optional[str] = None,
        output: Optional[str] = None,
        self_contained: bool = False,
        **kwargs
    ) -> BuildResult:
        """
        Publish .NET application.

        Args:
            configuration: Build configuration
            framework: Target framework
            runtime: Runtime identifier
            output: Output directory
            self_contained: Publish as self-contained

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If publish fails

        Example:
            dotnet.publish(configuration="Release", runtime="linux-x64", self_contained=True)
        """
        cmd = ["dotnet", "publish"]

        if self.is_solution:
            cmd.append(str(self.solution_file))
        elif self.project_file:
            cmd.append(str(self.project_file))

        cmd.extend(["-c", configuration])

        if framework:
            cmd.extend(["-f", framework])

        if runtime:
            cmd.extend(["-r", runtime])

        if output:
            cmd.extend(["-o", output])

        if self_contained:
            cmd.append("--self-contained")

        return self._execute_command(
            cmd,
            timeout=600,
            error_type=BuildExecutionError,
            error_message="Publish failed"
        )

    @wrap_exception(BuildExecutionError, "Failed to run application")
    def run(
        self,
        configuration: str = "Debug",
        framework: Optional[str] = None,
        **kwargs
    ) -> BuildResult:
        """
        Run .NET application.

        Args:
            configuration: Build configuration
            framework: Target framework

        Returns:
            BuildResult

        Raises:
            BuildExecutionError: If run fails

        Example:
            dotnet.run(configuration="Debug")
        """
        cmd = ["dotnet", "run"]

        if self.project_file:
            cmd.extend(["--project", str(self.project_file)])

        cmd.extend(["-c", configuration])

        if framework:
            cmd.extend(["-f", framework])

        return self._execute_command(
            cmd,
            timeout=600,
            error_type=BuildExecutionError,
            error_message="Application run failed"
        )

    def clean(self) -> BuildResult:
        """
        Clean build outputs.

        Returns:
            BuildResult
        """
        cmd = ["dotnet", "clean"]

        if self.is_solution:
            cmd.append(str(self.solution_file))
        elif self.project_file:
            cmd.append(str(self.project_file))

        try:
            return self._execute_command(
                cmd,
                timeout=30,
                error_type=BuildExecutionError,
                error_message="Clean failed"
            )
        except BuildExecutionError as e:
            self.logger.warning(f"Clean failed: {e}")
            return BuildResult(
                success=False,
                exit_code=1,
                duration=0.0,
                output=str(e),
                build_system="dotnet"
            )

    def _extract_test_stats(self, output: str) -> Dict[str, int]:
        """
        Extract test statistics from dotnet test output.

        Args:
            output: dotnet test output

        Returns:
            Dict with test statistics
        """
        stats = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'tests_skipped': 0
        }

        # dotnet test summary: "Passed!  - Failed:     0, Passed:    15, Skipped:     0, Total:    15"
        # Or: "Failed!  - Failed:     2, Passed:    13, Skipped:     1, Total:    16"
        summary_match = re.search(
            r'Failed:\s+(\d+),\s+Passed:\s+(\d+),\s+Skipped:\s+(\d+),\s+Total:\s+(\d+)',
            output
        )

        if summary_match:
            failed = int(summary_match.group(1))
            passed = int(summary_match.group(2))
            skipped = int(summary_match.group(3))
            total = int(summary_match.group(4))

            stats['tests_failed'] = failed
            stats['tests_passed'] = passed
            stats['tests_skipped'] = skipped
            stats['tests_run'] = total - skipped

        return stats


# CLI interface
if __name__ == "__main__":
    import argparse
    import logging
    import sys
    import json

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description=".NET Manager")
    parser.add_argument("--project-dir", default=".", help="Project directory")
    parser.add_argument("command", choices=["info", "build", "test", "restore", "publish", "run", "clean", "add"],
                       help="Command to execute")
    parser.add_argument("--configuration", "-c", default="Debug", help="Build configuration")
    parser.add_argument("--framework", "-f", help="Target framework")
    parser.add_argument("--runtime", "-r", help="Runtime identifier")
    parser.add_argument("--package", help="Package name to add")
    parser.add_argument("--version", "-v", help="Package version")
    parser.add_argument("--output", "-o", help="Output directory")
    parser.add_argument("--self-contained", action="store_true", help="Self-contained publish")
    parser.add_argument("--verbosity", help="Log verbosity")

    args = parser.parse_args()

    try:
        dotnet = DotNetManager(project_dir=args.project_dir)

        if args.command == "info":
            info = dotnet.get_project_info()
            print(json.dumps(info, indent=2))

        elif args.command == "build":
            result = dotnet.build(
                configuration=args.configuration,
                framework=args.framework,
                runtime=args.runtime
            )
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "test":
            result = dotnet.test(
                configuration=args.configuration,
                verbosity=args.verbosity
            )
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "restore":
            result = dotnet.restore()
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "publish":
            result = dotnet.publish(
                configuration=args.configuration,
                framework=args.framework,
                runtime=args.runtime,
                output=args.output,
                self_contained=args.self_contained
            )
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "run":
            result = dotnet.run(
                configuration=args.configuration,
                framework=args.framework
            )
            print(result)
            sys.exit(0 if result.success else 1)

        elif args.command == "clean":
            result = dotnet.clean()
            print(result)

        elif args.command == "add":
            if not args.package:
                print("Error: --package required for add command")
                sys.exit(1)
            dotnet.install_dependency(args.package, version=args.version)
            print(f"Added {args.package}")

    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
