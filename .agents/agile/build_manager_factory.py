#!/usr/bin/env python3
"""
Build Manager Factory

Factory Pattern with Registry for creating build managers.
Uses Singleton pattern to ensure single factory instance.

Design Patterns:
- Factory Pattern: Build manager creation
- Registry Pattern: Build system registration
- Singleton Pattern: Single factory instance
"""

from typing import Dict, Type, Optional
from pathlib import Path
import logging
from enum import Enum

from artemis_exceptions import wrap_exception
from build_system_exceptions import UnsupportedBuildSystemError
from build_manager_base import BuildManagerBase


class BuildSystem(Enum):
    """Supported build systems"""
    # Java
    MAVEN = "maven"
    GRADLE = "gradle"
    ANT = "ant"

    # JavaScript/TypeScript
    NPM = "npm"
    YARN = "yarn"
    PNPM = "pnpm"

    # Python
    PIP = "pip"
    POETRY = "poetry"
    PIPENV = "pipenv"
    CONDA = "conda"

    # C/C++
    CMAKE = "cmake"
    MAKE = "make"

    # Rust
    CARGO = "cargo"

    # Go
    GO_MOD = "go"

    # .NET
    DOTNET = "dotnet"

    # Ruby
    BUNDLER = "bundler"

    # PHP
    COMPOSER = "composer"

    # Infrastructure/Shell
    TERRAFORM = "terraform"
    BASH = "bash"


class BuildManagerFactory:
    """
    Factory for creating build managers.

    Implements Factory Pattern with Registry for extensibility.
    Uses Singleton pattern to ensure single factory instance.

    Example:
        factory = BuildManagerFactory.get_instance()
        maven_mgr = factory.create(BuildSystem.MAVEN, project_dir="/path")
    """

    _instance: Optional['BuildManagerFactory'] = None
    _registry: Dict[BuildSystem, Type[BuildManagerBase]] = {}

    def __new__(cls):
        """Singleton: Ensure only one factory instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'BuildManagerFactory':
        """
        Get singleton factory instance.

        Returns:
            BuildManagerFactory instance
        """
        if cls._instance is None:
            cls._instance = BuildManagerFactory()
        return cls._instance

    @classmethod
    def register(
        cls,
        build_system: BuildSystem,
        manager_class: Type[BuildManagerBase]
    ) -> None:
        """
        Register a build manager class.

        Args:
            build_system: Build system identifier
            manager_class: Build manager class (must extend BuildManagerBase)

        Raises:
            ValueError: If manager_class doesn't extend BuildManagerBase

        Example:
            class MavenManager(BuildManagerBase):
                ...

            BuildManagerFactory.register(BuildSystem.MAVEN, MavenManager)
        """
        if not issubclass(manager_class, BuildManagerBase):
            raise ValueError(
                f"{manager_class.__name__} must extend BuildManagerBase"
            )

        cls._registry[build_system] = manager_class

    @classmethod
    def unregister(cls, build_system: BuildSystem) -> None:
        """
        Unregister a build manager.

        Args:
            build_system: Build system to unregister
        """
        if build_system in cls._registry:
            del cls._registry[build_system]

    @classmethod
    def is_registered(cls, build_system: BuildSystem) -> bool:
        """
        Check if build system is registered.

        Args:
            build_system: Build system to check

        Returns:
            True if registered
        """
        return build_system in cls._registry

    @classmethod
    def get_registered_systems(cls) -> list[BuildSystem]:
        """
        Get list of registered build systems.

        Returns:
            List of BuildSystem enums
        """
        return list(cls._registry.keys())

    @wrap_exception(UnsupportedBuildSystemError, "Failed to create build manager")
    def create(
        self,
        build_system: BuildSystem,
        project_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ) -> BuildManagerBase:
        """
        Create a build manager instance.

        Args:
            build_system: Build system to use
            project_dir: Project directory
            logger: Logger instance (dependency injection)

        Returns:
            Build manager instance

        Raises:
            UnsupportedBuildSystemError: If build system not registered

        Example:
            factory = BuildManagerFactory.get_instance()
            maven = factory.create(
                BuildSystem.MAVEN,
                project_dir="/path/to/project",
                logger=my_logger
            )
        """
        if build_system not in self._registry:
            registered = [bs.value for bs in self._registry.keys()]
            raise UnsupportedBuildSystemError(
                f"Build system '{build_system.value}' not registered",
                {
                    "requested": build_system.value,
                    "registered": registered
                }
            )

        manager_class = self._registry[build_system]

        try:
            return manager_class(
                project_dir=project_dir,
                logger=logger
            )
        except Exception as e:
            raise UnsupportedBuildSystemError(
                f"Failed to create {build_system.value} manager: {e}",
                {
                    "build_system": build_system.value,
                    "manager_class": manager_class.__name__,
                    "error": str(e)
                },
                original_exception=e
            )

    def create_auto(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ) -> BuildManagerBase:
        """
        Auto-detect and create appropriate build manager.

        Scans project directory for build files and creates
        the appropriate manager.

        Args:
            project_dir: Project directory
            logger: Logger instance

        Returns:
            Build manager instance

        Raises:
            UnsupportedBuildSystemError: If no build system detected

        Example:
            factory = BuildManagerFactory.get_instance()
            manager = factory.create_auto(project_dir="/path/to/project")
            # Automatically detects Maven/Gradle/npm/etc.
        """
        project_path = Path(project_dir) if project_dir else Path.cwd()

        # Detection order (most specific first)
        detection_map = {
            BuildSystem.MAVEN: ["pom.xml"],
            BuildSystem.GRADLE: ["build.gradle", "build.gradle.kts"],
            BuildSystem.NPM: ["package-lock.json"],
            BuildSystem.YARN: ["yarn.lock"],
            BuildSystem.PNPM: ["pnpm-lock.yaml"],
            BuildSystem.CARGO: ["Cargo.toml"],
            BuildSystem.CMAKE: ["CMakeLists.txt"],
            BuildSystem.GO_MOD: ["go.mod"],
            BuildSystem.POETRY: ["poetry.lock"],
            BuildSystem.PIPENV: ["Pipfile.lock"],
            BuildSystem.COMPOSER: ["composer.json"],
            BuildSystem.BUNDLER: ["Gemfile.lock"],
            BuildSystem.DOTNET: ["*.csproj", "*.sln"]
        }

        for build_system, markers in detection_map.items():
            if not self.is_registered(build_system):
                continue

            for marker in markers:
                if "*" in marker:
                    # Glob pattern
                    if list(project_path.glob(marker)):
                        return self.create(build_system, project_dir, logger)
                else:
                    # Exact file
                    if (project_path / marker).exists():
                        return self.create(build_system, project_dir, logger)

        # No build system detected
        raise UnsupportedBuildSystemError(
            "No build system detected in project",
            {
                "project_dir": str(project_path),
                "registered_systems": [bs.value for bs in self.get_registered_systems()]
            }
        )


# Convenience function for getting factory instance
def get_build_manager_factory() -> BuildManagerFactory:
    """
    Get the build manager factory instance.

    Returns:
        BuildManagerFactory singleton

    Example:
        factory = get_build_manager_factory()
        maven = factory.create(BuildSystem.MAVEN)
    """
    return BuildManagerFactory.get_instance()


# Auto-registration decorator
def register_build_manager(build_system: BuildSystem):
    """
    Decorator to auto-register build managers.

    Args:
        build_system: Build system identifier

    Example:
        @register_build_manager(BuildSystem.MAVEN)
        class MavenManager(BuildManagerBase):
            ...
    """
    def decorator(cls: Type[BuildManagerBase]):
        BuildManagerFactory.register(build_system, cls)
        return cls
    return decorator
