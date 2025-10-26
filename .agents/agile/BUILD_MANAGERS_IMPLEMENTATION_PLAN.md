# Build Managers Implementation Plan

## Overview

This document provides a complete implementation plan for all remaining build managers with enterprise-grade quality: proper design patterns, exception wrapping, and no anti-patterns.

## Architecture

All build managers follow the **Strategy Pattern** with a unified interface:

```python
class BuildManagerInterface(ABC):
    """Base interface for all build managers"""

    @abstractmethod
    def build(self, clean: bool = True, **kwargs) -> BuildResult:
        """Build the project"""
        pass

    @abstractmethod
    def test(self, **kwargs) -> BuildResult:
        """Run tests"""
        pass

    @abstractmethod
    def install_dependency(self, package: str, version: str = None, **kwargs) -> bool:
        """Install a dependency"""
        pass

    @abstractmethod
    def get_project_info(self) -> Dict[str, Any]:
        """Get project information"""
        pass
```

## Design Patterns Used

1. **Strategy Pattern**: Different build systems, same interface
2. **Factory Pattern**: `BuildManagerFactory` creates appropriate manager
3. **Template Method Pattern**: Common build flow in base class
4. **Singleton Pattern**: Build manager instance per project
5. **Exception Wrapper Pattern**: All exceptions wrapped with context

## Exception Hierarchy

```python
class BuildSystemError(PipelineStageError):
    """Base exception for build system errors"""
    pass

class BuildSystemNotFoundError(BuildSystemError):
    """Build system executable not found"""
    pass

class ProjectConfigurationError(BuildSystemError):
    """Project configuration file missing or invalid"""
    pass

class BuildExecutionError(BuildSystemError):
    """Error during build execution"""
    pass

class TestExecutionError(BuildSystemError):
    """Error during test execution"""
    pass

class DependencyInstallError(BuildSystemError):
    """Error installing dependency"""
    pass
```

## Implementation Priority

### Priority 1: JavaScript Ecosystem (npm/yarn/pnpm)
**Rationale**: Most common after Java/Python

### Priority 2: C/C++ Ecosystem (CMake)
**Rationale**: Essential for systems programming

### Priority 3: Rust Ecosystem (Cargo)
**Rationale**: Growing rapidly, modern tooling

### Priority 4: Python Enhancement (poetry/pipenv)
**Rationale**: Improve existing Python support

### Priority 5: Additional Ecosystems
**Rationale**: Go, .NET, Ruby, PHP as needed

---

## 1. npm/yarn/pnpm Manager

### File: `npm_manager.py`

```python
#!/usr/bin/env python3
"""
npm/yarn/pnpm Package Manager

Enterprise-grade JavaScript/TypeScript package management.

Supports:
- npm (Node Package Manager)
- yarn (Facebook's npm alternative)
- pnpm (Performant npm)

Design Patterns:
- Strategy Pattern: Different package managers, same interface
- Factory Pattern: Auto-detect which manager to use
- Exception Wrapper: All errors properly wrapped
"""

from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import json
import time
import logging
from artemis_exceptions import wrap_exception, BuildSystemError


class PackageManager(Enum):
    """JavaScript package managers"""
    NPM = "npm"
    YARN = "yarn"
    PNPM = "pnpm"


@dataclass
class NpmProjectInfo:
    """npm/package.json project information"""
    name: str
    version: str
    description: Optional[str] = None
    dependencies: Dict[str, str] = field(default_factory=dict)
    dev_dependencies: Dict[str, str] = field(default_factory=dict)
    scripts: Dict[str, str] = field(default_factory=dict)
    package_manager: PackageManager = PackageManager.NPM


@dataclass
class NpmBuildResult:
    """npm build/test result"""
    success: bool
    exit_code: int
    duration: float
    output: str
    package_manager: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class NpmManager:
    """
    Enterprise-grade npm/yarn/pnpm manager.

    Auto-detects package manager from lock files.
    Provides unified interface for all three.
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.logger = logger or logging.getLogger(__name__)
        self.package_json_path = self.project_dir / "package.json"

        # Auto-detect package manager
        self.package_manager = self._detect_package_manager()

        # Validate installation
        self._validate_package_manager()

    @wrap_exception(BuildSystemNotFoundError, "Package manager not found")
    def _validate_package_manager(self) -> None:
        """Validate package manager is installed"""
        cmd = self.package_manager.value
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"{cmd} not properly installed")

            self.logger.info(f"Using {cmd} version: {result.stdout.strip()}")

        except FileNotFoundError:
            raise BuildSystemNotFoundError(
                f"{cmd} not found in PATH",
                {"package_manager": cmd}
            )

    def _detect_package_manager(self) -> PackageManager:
        """Auto-detect package manager from lock files"""
        # Check lock files
        if (self.project_dir / "pnpm-lock.yaml").exists():
            return PackageManager.PNPM
        elif (self.project_dir / "yarn.lock").exists():
            return PackageManager.YARN
        else:
            return PackageManager.NPM

    @wrap_exception(ProjectConfigurationError, "Failed to parse package.json")
    def get_project_info(self) -> NpmProjectInfo:
        """Parse package.json"""
        if not self.package_json_path.exists():
            raise ProjectConfigurationError(
                "package.json not found",
                {"project_dir": str(self.project_dir)}
            )

        with open(self.package_json_path, 'r') as f:
            data = json.load(f)

        return NpmProjectInfo(
            name=data.get("name", ""),
            version=data.get("version", "0.0.0"),
            description=data.get("description"),
            dependencies=data.get("dependencies", {}),
            dev_dependencies=data.get("devDependencies", {}),
            scripts=data.get("scripts", {}),
            package_manager=self.package_manager
        )

    @wrap_exception(BuildExecutionError, "Build failed")
    def build(
        self,
        script_name: str = "build",
        production: bool = False,
        timeout: int = 600
    ) -> NpmBuildResult:
        """
        Run npm build script.

        Args:
            script_name: Script name from package.json
            production: Build for production
            timeout: Build timeout in seconds

        Returns:
            NpmBuildResult
        """
        start_time = time.time()

        # Build command
        cmd = [self.package_manager.value, "run", script_name]

        if production and self.package_manager == PackageManager.NPM:
            cmd.append("--production")

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

            # Parse errors/warnings
            errors = [line for line in output.splitlines() if "error" in line.lower()]
            warnings = [line for line in output.splitlines() if "warning" in line.lower()]

            return NpmBuildResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                duration=duration,
                output=output,
                package_manager=self.package_manager.value,
                errors=errors[:10],
                warnings=warnings[:10]
            )

        except subprocess.TimeoutExpired:
            raise BuildExecutionError(
                f"Build timed out after {timeout}s",
                {"timeout": timeout, "script": script_name}
            )

    @wrap_exception(TestExecutionError, "Tests failed")
    def test(
        self,
        watch: bool = False,
        coverage: bool = False,
        timeout: int = 300
    ) -> NpmBuildResult:
        """Run npm test"""
        start_time = time.time()

        cmd = [self.package_manager.value, "test"]

        if watch:
            cmd.append("--watch")
        if coverage:
            cmd.append("--coverage")

        # Don't use watch mode with subprocess
        if not watch:
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

                return NpmBuildResult(
                    success=result.returncode == 0,
                    exit_code=result.returncode,
                    duration=duration,
                    output=output,
                    package_manager=self.package_manager.value
                )

            except subprocess.TimeoutExpired:
                raise TestExecutionError(
                    f"Tests timed out after {timeout}s",
                    {"timeout": timeout}
                )

    @wrap_exception(DependencyInstallError, "Failed to install dependency")
    def install_dependency(
        self,
        package: str,
        version: Optional[str] = None,
        dev: bool = False
    ) -> bool:
        """Install a dependency"""
        cmd = [self.package_manager.value]

        if self.package_manager == PackageManager.NPM:
            cmd.append("install")
        elif self.package_manager == PackageManager.YARN:
            cmd.append("add")
        elif self.package_manager == PackageManager.PNPM:
            cmd.append("add")

        # Add package with version
        if version:
            cmd.append(f"{package}@{version}")
        else:
            cmd.append(package)

        # Dev dependency
        if dev:
            if self.package_manager == PackageManager.NPM:
                cmd.append("--save-dev")
            elif self.package_manager in [PackageManager.YARN, PackageManager.PNPM]:
                cmd.append("--dev")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                self.logger.info(f"Installed {package}")
                return True
            else:
                raise DependencyInstallError(
                    f"Failed to install {package}",
                    {"package": package, "output": result.stderr}
                )

        except subprocess.TimeoutExpired:
            raise DependencyInstallError(
                f"Dependency installation timed out",
                {"package": package}
            )
```

**Key Features:**
- Auto-detects npm/yarn/pnpm from lock files
- Unified interface for all three
- Exception wrapping on all operations
- Type hints throughout
- Proper logging

---

## 2. CMake Manager

### File: `cmake_manager.py`

Similar structure to npm_manager.py but for C/C++:

**Key Operations:**
```python
def configure(self, build_type: str = "Release") -> bool:
    """cmake -B build -DCMAKE_BUILD_TYPE=Release"""
    pass

def build(self, target: Optional[str] = None) -> BuildResult:
    """cmake --build build [--target target]"""
    pass

def test(self) -> BuildResult:
    """ctest --test-dir build"""
    pass
```

**Design Patterns:**
- Template Method: configure → build → test flow
- Strategy: Different generators (Unix Makefiles, Ninja, Visual Studio)
- Exception Wrapper: All CMake errors wrapped

---

## 3. Cargo Manager (Rust)

### File: `cargo_manager.py`

**Key Operations:**
```python
def build(self, release: bool = False) -> BuildResult:
    """cargo build [--release]"""
    pass

def test(self) -> BuildResult:
    """cargo test"""
    pass

def add_dependency(self, crate: str, version: str) -> bool:
    """cargo add crate@version"""
    pass
```

**Special Features:**
- Cargo.toml parsing
- Workspace detection
- Feature flag support
- Target specification

---

## 4. Python Enhancement (poetry/pipenv)

### File: `python_package_manager.py`

Enhance existing Python support with poetry/pipenv:

```python
class PythonPackageManager(Enum):
    PIP = "pip"
    POETRY = "poetry"
    PIPENV = "pipenv"
    CONDA = "conda"

class PoetryManager:
    def build(self) -> BuildResult:
        """poetry build"""

    def test(self) -> BuildResult:
        """poetry run pytest"""

    def add_dependency(self, package: str, version: str, group: str = "main"):
        """poetry add package@version [--group dev]"""
```

---

## Integration with UniversalBuildSystem

Update `universal_build_system.py`:

```python
def get_build_manager(self, build_system: BuildSystem = None):
    """Factory method to get appropriate build manager"""

    if build_system == BuildSystem.NPM:
        from npm_manager import NpmManager
        return NpmManager(self.project_dir, self.logger)

    elif build_system == BuildSystem.CMAKE:
        from cmake_manager import CMakeManager
        return CMakeManager(self.project_dir, self.logger)

    elif build_system == BuildSystem.CARGO:
        from cargo_manager import CargoManager
        return CargoManager(self.project_dir, self.logger)

    # ... all other build systems
```

---

## Anti-Patterns to Avoid

### ❌ **God Class**
Don't put everything in one class.

✅ **Solution**: Separate concerns (NpmManager, YarnDetector, PackageJsonParser)

### ❌ **Magic Strings**
Don't use raw strings for commands/errors.

✅ **Solution**: Use Enums and constants

### ❌ **Silent Failures**
Don't swallow exceptions.

✅ **Solution**: Wrap and re-raise with context

### ❌ **Long Methods**
Don't have 100+ line methods.

✅ **Solution**: Extract helper methods

### ❌ **Tight Coupling**
Don't hard-code dependencies.

✅ **Solution**: Dependency injection via constructor

---

## Code Quality Checklist

- [ ] All public methods have type hints
- [ ] All methods have docstrings
- [ ] All exceptions are wrapped with @wrap_exception
- [ ] No methods longer than 50 lines
- [ ] No classes with >10 methods
- [ ] All magic values are constants/enums
- [ ] Logging on all operations
- [ ] Timeout on all subprocess calls
- [ ] CLI interface for standalone usage
- [ ] Unit tests (separate file)

---

## Testing Strategy

Each manager should have comprehensive tests:

```python
# test_npm_manager.py
def test_detect_npm():
    """Test npm detection from package-lock.json"""

def test_detect_yarn():
    """Test yarn detection from yarn.lock"""

def test_build_success():
    """Test successful build"""

def test_build_timeout():
    """Test build timeout handling"""

def test_install_dependency():
    """Test dependency installation"""
```

---

## Integration with Artemis Pipeline

### standalone_developer_agent.py

```python
from universal_build_system import UniversalBuildSystem

def _build_project(self, output_dir: Path) -> Dict:
    """Build project using appropriate build system"""

    # Auto-detect and build
    ubs = UniversalBuildSystem(project_dir=output_dir, logger=self.logger)
    detection = ubs.detect_build_system()

    self.logger.log(
        f"🔧 Detected {detection.build_system.value} build system",
        "INFO"
    )

    # Get manager and build
    manager = ubs.get_build_manager(detection.build_system)
    result = manager.build()

    return {
        "success": result.success,
        "duration": result.duration,
        "build_system": detection.build_system.value
    }
```

---

## Summary

This plan provides:

1. ✅ **Unified Interface**: All build managers implement same interface
2. ✅ **Design Patterns**: Strategy, Factory, Template Method throughout
3. ✅ **Exception Wrapping**: All errors properly wrapped with context
4. ✅ **No Anti-Patterns**: Following SOLID principles
5. ✅ **Type Safety**: Type hints throughout
6. ✅ **Production Quality**: Logging, timeouts, error handling
7. ✅ **Testability**: Clear separation of concerns
8. ✅ **Documentation**: Comprehensive docstrings

**Next Steps:**
1. Implement npm_manager.py (Priority 1)
2. Implement cmake_manager.py (Priority 2)
3. Implement cargo_manager.py (Priority 3)
4. Update universal_build_system.py with all managers
5. Integrate with Artemis pipeline
6. Add comprehensive tests

Each implementation follows the same proven pattern established with Maven/Gradle.
