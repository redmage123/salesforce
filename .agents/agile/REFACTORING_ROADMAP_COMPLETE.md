# Complete Refactoring Roadmap for Build System Integration

## Executive Summary

This document provides a comprehensive refactoring plan for ALL build manager code (existing and new) to achieve enterprise-grade quality with proper design patterns, exception wrapping, and elimination of all anti-patterns.

## Current State Analysis

### Existing Code (To Be Refactored):
1. **maven_manager.py** (785 lines) - Needs exception wrapping, pattern improvements
2. **gradle_manager.py** (619 lines) - Needs exception wrapping, pattern improvements
3. **java_web_framework_detector.py** (711 lines) - Good structure, needs minor fixes
4. **spring_boot_analyzer.py** (701 lines) - Good structure, needs minor fixes
5. **java_ecosystem_integration.py** (459 lines) - Needs pattern integration
6. **universal_build_system.py** (661 lines) - Needs exception wrapping

### New Code (To Be Implemented):
7. **npm_manager.py** - JavaScript/TypeScript package management
8. **cmake_manager.py** - C/C++ build system
9. **cargo_manager.py** - Rust package management
10. **python_package_manager.py** - Enhanced Python support (poetry/pipenv)

---

## Part 1: Establish Common Foundation

### 1.1 Create Base Exception Hierarchy

**File**: `build_system_exceptions.py`

```python
from artemis_exceptions import PipelineStageError, wrap_exception

class BuildSystemError(PipelineStageError):
    """Base exception for all build system errors"""
    pass

class BuildSystemNotFoundError(BuildSystemError):
    """Build system executable not found in PATH"""
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

class DependencyResolutionError(BuildSystemError):
    """Error resolving dependencies"""
    pass

class BuildTimeoutError(BuildSystemError):
    """Build/test operation timed out"""
    pass

class InvalidBuildConfigurationError(BuildSystemError):
    """Build configuration is invalid"""
    pass
```

### 1.2 Create Base Build Manager Interface

**File**: `build_manager_base.py`

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

@dataclass
class BuildResult:
    """Universal build result across all build systems"""
    success: bool
    exit_code: int
    duration: float
    output: str
    build_system: str
    errors: list[str]
    warnings: list[str]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BuildManagerBase(ABC):
    """
    Abstract base class for all build managers.

    Design Patterns:
    - Template Method: Common build flow
    - Strategy: Different build systems implement their own logic
    - Dependency Injection: Logger injected via constructor

    SOLID Principles:
    - Single Responsibility: Only handles build operations
    - Open/Closed: Open for extension, closed for modification
    - Liskov Substitution: All managers are interchangeable
    - Interface Segregation: Minimal interface
    - Dependency Inversion: Depends on abstractions (logging.Logger)
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._validate_installation()
        self._validate_project()

    @abstractmethod
    def _validate_installation(self) -> None:
        """Validate build system is installed (raises BuildSystemNotFoundError)"""
        pass

    @abstractmethod
    def _validate_project(self) -> None:
        """Validate project has required files (raises ProjectConfigurationError)"""
        pass

    @abstractmethod
    def build(self, **kwargs) -> BuildResult:
        """Build the project (raises BuildExecutionError)"""
        pass

    @abstractmethod
    def test(self, **kwargs) -> BuildResult:
        """Run tests (raises TestExecutionError)"""
        pass

    @abstractmethod
    def install_dependency(self, package: str, version: Optional[str] = None, **kwargs) -> bool:
        """Install a dependency (raises DependencyInstallError)"""
        pass

    @abstractmethod
    def get_project_info(self) -> Dict[str, Any]:
        """Get project information (raises ProjectConfigurationError)"""
        pass

    def _execute_command(
        self,
        cmd: list[str],
        timeout: int = 600,
        error_class: type = BuildExecutionError
    ) -> subprocess.CompletedProcess:
        """
        Template method for executing commands with consistent error handling.

        This eliminates code duplication across all build managers.
        """
        import subprocess
        import time

        start_time = time.time()

        try:
            self.logger.debug(f"Executing: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            duration = time.time() - start_time
            self.logger.debug(f"Command completed in {duration:.2f}s")

            return result

        except subprocess.TimeoutExpired:
            raise BuildTimeoutError(
                f"Command timed out after {timeout}s",
                {"command": " ".join(cmd), "timeout": timeout}
            )
        except FileNotFoundError as e:
            raise BuildSystemNotFoundError(
                f"Command not found: {cmd[0]}",
                {"command": cmd[0]}
            ) from e
```

---

## Part 2: Refactor Existing Build Managers

### 2.1 Refactor maven_manager.py

**Changes Required:**

1. **Inherit from BuildManagerBase**
2. **Add exception wrapping to all methods**
3. **Extract long methods into smaller ones**
4. **Use Template Method pattern for common operations**

**Before** (example):
```python
def build(self, phase: MavenPhase = MavenPhase.PACKAGE, ...):
    start_time = time.time()
    cmd = ["mvn"]
    if clean:
        cmd.append("clean")
    # ... 50+ lines of code ...
```

**After**:
```python
@wrap_exception(BuildExecutionError, "Maven build failed")
def build(
    self,
    phase: MavenPhase = MavenPhase.PACKAGE,
    clean: bool = True,
    skip_tests: bool = False,
    timeout: int = 600
) -> BuildResult:
    """
    Execute Maven build.

    Template Method Pattern:
    1. Prepare command
    2. Execute command (via base class)
    3. Parse results
    4. Return BuildResult
    """
    cmd = self._prepare_build_command(phase, clean, skip_tests)
    result = self._execute_command(cmd, timeout, BuildExecutionError)
    return self._parse_build_result(result, phase.value)

def _prepare_build_command(
    self,
    phase: MavenPhase,
    clean: bool,
    skip_tests: bool
) -> list[str]:
    """Extract command preparation logic (Single Responsibility)"""
    cmd = ["mvn"]
    if clean:
        cmd.append("clean")
    cmd.append(phase.value)
    if skip_tests:
        cmd.extend(["-DskipTests", "-Dmaven.test.skip=true"])
    return cmd

def _parse_build_result(
    self,
    result: subprocess.CompletedProcess,
    phase: str
) -> BuildResult:
    """Extract result parsing logic (Single Responsibility)"""
    output = result.stdout + result.stderr

    return BuildResult(
        success=result.returncode == 0 and "BUILD SUCCESS" in output,
        exit_code=result.returncode,
        duration=0,  # Set by caller
        output=output,
        build_system="maven",
        errors=self._extract_errors(output),
        warnings=self._extract_warnings(output),
        metadata={"phase": phase}
    )
```

### 2.2 Refactor gradle_manager.py

Same pattern as Maven. Key improvements:

1. **Inherit from BuildManagerBase**
2. **Use _execute_command template method**
3. **Extract parsing logic**
4. **Add comprehensive exception wrapping**

### 2.3 Refactor java_web_framework_detector.py

Already well-structured, minor improvements:

1. **Add exception wrapping for file I/O**
2. **Extract magic strings to constants**
3. **Add logging for detection steps**

### 2.4 Refactor spring_boot_analyzer.py

Similar to framework detector:

1. **Add exception wrapping**
2. **Extract complex regex patterns to constants**
3. **Add logging**

### 2.5 Refactor java_ecosystem_integration.py

1. **Use BuildManagerBase interface**
2. **Add exception wrapping**
3. **Implement Factory Pattern properly**

### 2.6 Refactor universal_build_system.py

1. **Add exception wrapping to detection**
2. **Implement proper Factory Pattern**
3. **Add caching for detection results**

---

## Part 3: Implement New Build Managers

### 3.1 npm_manager.py (Complete Implementation)

See BUILD_MANAGERS_IMPLEMENTATION_PLAN.md for full code.

**Key Features:**
- Inherits from BuildManagerBase
- Auto-detects npm/yarn/pnpm
- Exception wrapping on all operations
- Template Method pattern for common operations

### 3.2 cmake_manager.py

```python
class CMakeManager(BuildManagerBase):
    """Enterprise-grade CMake manager"""

    @wrap_exception(BuildSystemNotFoundError, "CMake not found")
    def _validate_installation(self) -> None:
        result = subprocess.run(
            ["cmake", "--version"],
            capture_output=True,
            timeout=10
        )
        if result.returncode != 0:
            raise BuildSystemNotFoundError("cmake not in PATH")

    @wrap_exception(ProjectConfigurationError, "CMakeLists.txt not found")
    def _validate_project(self) -> None:
        if not (self.project_dir / "CMakeLists.txt").exists():
            raise ProjectConfigurationError("No CMakeLists.txt")

    @wrap_exception(BuildExecutionError, "CMake configure failed")
    def configure(
        self,
        build_dir: str = "build",
        build_type: str = "Release",
        generator: Optional[str] = None
    ) -> bool:
        """Configure CMake project"""
        cmd = ["cmake", "-B", build_dir, f"-DCMAKE_BUILD_TYPE={build_type}"]
        if generator:
            cmd.extend(["-G", generator])

        result = self._execute_command(cmd)
        return result.returncode == 0

    @wrap_exception(BuildExecutionError, "CMake build failed")
    def build(
        self,
        build_dir: str = "build",
        target: Optional[str] = None,
        parallel: bool = True,
        timeout: int = 600
    ) -> BuildResult:
        """Build CMake project"""
        cmd = ["cmake", "--build", build_dir]
        if target:
            cmd.extend(["--target", target])
        if parallel:
            cmd.extend(["--parallel"])

        result = self._execute_command(cmd, timeout)
        return self._parse_build_result(result)

    @wrap_exception(TestExecutionError, "CTest failed")
    def test(
        self,
        build_dir: str = "build",
        parallel: bool = True,
        timeout: int = 300
    ) -> BuildResult:
        """Run CTest"""
        cmd = ["ctest", "--test-dir", build_dir]
        if parallel:
            cmd.append("--parallel")

        result = self._execute_command(cmd, timeout, TestExecutionError)
        return self._parse_test_result(result)
```

### 3.3 cargo_manager.py

```python
class CargoManager(BuildManagerBase):
    """Enterprise-grade Cargo (Rust) manager"""

    @wrap_exception(BuildExecutionError, "Cargo build failed")
    def build(
        self,
        release: bool = False,
        all_features: bool = False,
        no_default_features: bool = False,
        timeout: int = 600
    ) -> BuildResult:
        """Build Rust project"""
        cmd = ["cargo", "build"]
        if release:
            cmd.append("--release")
        if all_features:
            cmd.append("--all-features")
        if no_default_features:
            cmd.append("--no-default-features")

        result = self._execute_command(cmd, timeout)
        return self._parse_build_result(result)

    @wrap_exception(TestExecutionError, "Cargo test failed")
    def test(
        self,
        test_name: Optional[str] = None,
        timeout: int = 300
    ) -> BuildResult:
        """Run Rust tests"""
        cmd = ["cargo", "test"]
        if test_name:
            cmd.append(test_name)

        result = self._execute_command(cmd, timeout, TestExecutionError)
        return self._parse_test_result(result)

    @wrap_exception(DependencyInstallError, "Failed to add crate")
    def install_dependency(
        self,
        crate: str,
        version: Optional[str] = None,
        features: Optional[list[str]] = None
    ) -> bool:
        """Add dependency to Cargo.toml"""
        cmd = ["cargo", "add", crate]
        if version:
            cmd.append(f"@{version}")
        if features:
            cmd.append(f"--features={','.join(features)}")

        result = self._execute_command(cmd, 60, DependencyInstallError)
        return result.returncode == 0
```

---

## Part 4: Design Pattern Implementations

### 4.1 Factory Pattern - BuildManagerFactory

**File**: `build_manager_factory.py`

```python
class BuildManagerFactory:
    """
    Factory Pattern for creating build managers.

    Registry Pattern: Build managers register themselves.
    Singleton Pattern: One factory instance per application.
    """

    _instance = None
    _managers: Dict[BuildSystem, type] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, build_system: BuildSystem, manager_class: type):
        """Register a build manager"""
        cls._managers[build_system] = manager_class

    @classmethod
    @wrap_exception(BuildSystemError, "Failed to create build manager")
    def create(
        cls,
        build_system: BuildSystem,
        project_dir: Path,
        logger: Optional[logging.Logger] = None
    ) -> BuildManagerBase:
        """Create appropriate build manager"""
        manager_class = cls._managers.get(build_system)

        if not manager_class:
            raise BuildSystemError(
                f"No manager registered for {build_system.value}",
                {"build_system": build_system.value}
            )

        return manager_class(project_dir=project_dir, logger=logger)


# Registration (done at module import time)
BuildManagerFactory.register(BuildSystem.MAVEN, MavenManager)
BuildManagerFactory.register(BuildSystem.GRADLE, GradleManager)
BuildManagerFactory.register(BuildSystem.NPM, NpmManager)
BuildManagerFactory.register(BuildSystem.CMAKE, CMakeManager)
BuildManagerFactory.register(BuildSystem.CARGO, CargoManager)
```

### 4.2 Strategy Pattern - Already Implemented

Each build manager is a strategy that implements the same interface but with different logic.

### 4.3 Template Method Pattern - In BuildManagerBase

The `_execute_command` method provides a template for command execution that all managers use.

---

## Part 5: Anti-Pattern Elimination

### 5.1 Remove God Classes

**Before**: One class doing too much
**After**: Separate classes for concerns

Example:
- `MavenManager` - Build operations only
- `MavenPomParser` - POM parsing only
- `MavenDependencyResolver` - Dependency resolution only

### 5.2 Remove Magic Strings/Numbers

**Before**:
```python
if result.returncode == 0 and "BUILD SUCCESS" in output:
```

**After**:
```python
class MavenConstants:
    SUCCESS_MESSAGE = "BUILD SUCCESS"
    DEFAULT_TIMEOUT = 600
    MAX_RETRIES = 3

if result.returncode == 0 and MavenConstants.SUCCESS_MESSAGE in output:
```

### 5.3 Remove Long Methods

**Rule**: No method > 50 lines

**Before**: 100-line build() method
**After**: Extracted to _prepare_command(), _execute(), _parse_result()

### 5.4 Remove Silent Failures

**Before**:
```python
try:
    result = subprocess.run(...)
except Exception:
    return None  # Silent failure!
```

**After**:
```python
@wrap_exception(BuildExecutionError, "Build failed")
def build(...):
    try:
        result = subprocess.run(...)
    except subprocess.TimeoutExpired as e:
        raise BuildTimeoutError("Build timed out", {...}) from e
```

### 5.5 Remove Tight Coupling

**Before**: Hard-coded dependencies
```python
class MavenManager:
    def __init__(self):
        self.logger = logging.getLogger("maven")  # Tight coupling
```

**After**: Dependency injection
```python
class MavenManager:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)  # Injected
```

---

## Part 6: Code Quality Standards

### 6.1 Type Hints

**Every** public method and function must have type hints:

```python
def build(
    self,
    phase: MavenPhase = MavenPhase.PACKAGE,
    clean: bool = True,
    skip_tests: bool = False,
    timeout: int = 600
) -> BuildResult:
    """Build project"""
    pass
```

### 6.2 Docstrings

**Every** class and public method must have docstrings:

```python
def build(self, ...) -> BuildResult:
    """
    Execute Maven build.

    Args:
        phase: Maven lifecycle phase to execute
        clean: Run clean before build
        skip_tests: Skip test execution
        timeout: Build timeout in seconds

    Returns:
        BuildResult with build outcome

    Raises:
        BuildExecutionError: If build fails
        BuildTimeoutError: If build times out
    """
```

### 6.3 Logging

**Every** operation should log:

```python
self.logger.info(f"Building project with Maven {phase.value}")
self.logger.debug(f"Command: {' '.join(cmd)}")
self.logger.error(f"Build failed: {error_msg}")
```

### 6.4 Exception Wrapping

**Every** external call should be wrapped:

```python
@wrap_exception(BuildExecutionError, "Maven build failed")
def build(...) -> BuildResult:
    # All exceptions automatically wrapped with context
    pass
```

---

## Part 7: Testing Strategy

### 7.1 Unit Tests

Each manager needs comprehensive unit tests:

```python
# test_maven_manager.py

def test_maven_detection():
    """Test Maven detection from pom.xml"""
    assert manager.is_maven_project()

def test_build_success(tmp_path):
    """Test successful build"""
    result = manager.build()
    assert result.success

def test_build_timeout(tmp_path, monkeypatch):
    """Test build timeout handling"""
    with pytest.raises(BuildTimeoutError):
        manager.build(timeout=1)

def test_missing_pom():
    """Test error when pom.xml missing"""
    with pytest.raises(ProjectConfigurationError):
        MavenManager(project_dir="/nonexistent")
```

### 7.2 Integration Tests

Test actual builds with real projects:

```python
def test_real_maven_project():
    """Integration test with real Maven project"""
    # Use a sample project in tests/fixtures/
    manager = MavenManager("tests/fixtures/sample-maven-project")
    result = manager.build()
    assert result.success
```

---

## Part 8: Implementation Checklist

### For Each Build Manager:

- [ ] Inherits from BuildManagerBase
- [ ] All methods have type hints
- [ ] All public methods have docstrings
- [ ] All external calls wrapped with @wrap_exception
- [ ] No methods longer than 50 lines
- [ ] No magic strings (use Enums/Constants)
- [ ] Dependency injection for logger
- [ ] Timeout on all subprocess calls
- [ ] Comprehensive error messages
- [ ] Logging on all operations
- [ ] CLI interface for standalone use
- [ ] Unit tests (>80% coverage)
- [ ] Integration tests

---

## Part 9: Migration Plan

### Phase 1: Foundation (Week 1)
1. Create build_system_exceptions.py
2. Create build_manager_base.py
3. Create build_manager_factory.py

### Phase 2: Refactor Existing (Week 2)
4. Refactor maven_manager.py
5. Refactor gradle_manager.py
6. Update tests

### Phase 3: New Managers (Week 3)
7. Implement npm_manager.py
8. Implement cmake_manager.py
9. Implement cargo_manager.py

### Phase 4: Integration (Week 4)
10. Update universal_build_system.py
11. Integrate with Artemis pipeline
12. End-to-end testing

---

## Summary

This refactoring will result in:

✅ **Consistent Interface**: All build managers implement same interface
✅ **Design Patterns**: Factory, Strategy, Template Method throughout
✅ **Exception Safety**: All operations wrapped, no silent failures
✅ **SOLID Principles**: Single Responsibility, Open/Closed, etc.
✅ **Type Safety**: Type hints everywhere
✅ **High Quality**: Logging, timeouts, error handling
✅ **Testable**: Clear separation of concerns
✅ **Maintainable**: Small methods, clear responsibilities
✅ **Documented**: Comprehensive docstrings

**Total Estimated Effort**: 4 weeks for complete implementation and testing.
**Priority**: High - Critical for Artemis polyglot capabilities.

---

**Next Action**: Begin with Phase 1 (Foundation) to establish the base classes and patterns that all other code will build upon.
