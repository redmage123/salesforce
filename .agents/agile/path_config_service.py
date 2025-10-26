#!/usr/bin/env python3
"""
PathConfigService (SOLID: Single Responsibility)

Single Responsibility: Centralize all path configuration logic

This service provides a single source of truth for all Artemis path configuration,
eliminating duplicated environment variable reading and path construction logic
throughout the codebase.
"""

import os
from pathlib import Path
from typing import Optional


class PathConfigService:
    """
    Centralized path configuration service

    Single Responsibility: Manage all path configuration for Artemis pipeline
    - Reads environment variables once
    - Provides consistent path construction
    - Handles relative-to-absolute path resolution
    - Maintains default fallbacks
    """

    def __init__(self):
        """Initialize path configuration from environment variables"""
        # Get script directory for resolving relative paths
        self._script_dir = Path(__file__).parent.resolve()

        # Core directories
        self._temp_dir = self._resolve_path(
            os.getenv("ARTEMIS_TEMP_DIR", "../../.artemis_data/temp")
        )
        self._checkpoint_dir = self._resolve_path(
            os.getenv("ARTEMIS_CHECKPOINT_DIR", "../../.artemis_data/checkpoints")
        )
        self._state_dir = self._resolve_path(
            os.getenv("ARTEMIS_STATE_DIR", "../../.artemis_data/state")
        )
        self._status_dir = self._resolve_path(
            os.getenv("ARTEMIS_STATUS_DIR", "../../.artemis_data/status")
        )

        # Artifact directories
        self._adr_dir = self._resolve_path(
            os.getenv("ARTEMIS_ADR_DIR", "../../.artemis_data/adrs")
        )
        self._developer_output_dir = self._resolve_path(
            os.getenv("ARTEMIS_DEVELOPER_DIR", "../../.artemis_data/developer_output")
        )

    def _resolve_path(self, path_str: str) -> Path:
        """
        Resolve path to absolute path

        Args:
            path_str: Path string (absolute or relative)

        Returns:
            Absolute Path object
        """
        if os.path.isabs(path_str):
            return Path(path_str)
        else:
            return self._script_dir / path_str

    # ========================================================================
    # Public API - Core Directories
    # ========================================================================

    @property
    def temp_dir(self) -> Path:
        """Get temporary directory path"""
        return self._temp_dir

    @property
    def checkpoint_dir(self) -> Path:
        """Get checkpoint directory path"""
        return self._checkpoint_dir

    @property
    def state_dir(self) -> Path:
        """Get state directory path"""
        return self._state_dir

    @property
    def status_dir(self) -> Path:
        """Get status directory path"""
        return self._status_dir

    # ========================================================================
    # Public API - Artifact Directories
    # ========================================================================

    @property
    def adr_dir(self) -> Path:
        """Get ADR directory path"""
        return self._adr_dir

    @property
    def developer_output_dir(self) -> Path:
        """Get developer output base directory path"""
        return self._developer_output_dir

    # ========================================================================
    # Public API - Developer-Specific Paths
    # ========================================================================

    def get_developer_dir(self, developer_name: str) -> Path:
        """
        Get specific developer's output directory

        Args:
            developer_name: Name of developer (e.g., "developer-a")

        Returns:
            Path to developer's output directory
        """
        return self._developer_output_dir / developer_name

    def get_developer_tests_dir(self, developer_name: str) -> Path:
        """
        Get specific developer's tests directory

        Args:
            developer_name: Name of developer (e.g., "developer-a")

        Returns:
            Path to developer's tests directory
        """
        return self.get_developer_dir(developer_name) / "tests"

    def get_developer_impl_dir(self, developer_name: str) -> Path:
        """
        Get specific developer's implementation directory

        Args:
            developer_name: Name of developer (e.g., "developer-a")

        Returns:
            Path to developer's implementation directory
        """
        return self.get_developer_dir(developer_name)

    # ========================================================================
    # Public API - Ensure Directories Exist
    # ========================================================================

    def ensure_directories_exist(self):
        """Create all configured directories if they don't exist"""
        directories = [
            self._temp_dir,
            self._checkpoint_dir,
            self._state_dir,
            self._status_dir,
            self._adr_dir,
            self._developer_output_dir
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def ensure_developer_dirs_exist(self, developer_name: str):
        """
        Create developer-specific directories if they don't exist

        Args:
            developer_name: Name of developer (e.g., "developer-a")
        """
        dev_dir = self.get_developer_dir(developer_name)
        tests_dir = self.get_developer_tests_dir(developer_name)

        dev_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Singleton Instance
# ============================================================================

# Create singleton instance for global use
_path_config_instance: Optional[PathConfigService] = None


def get_path_config() -> PathConfigService:
    """
    Get singleton PathConfigService instance

    Returns:
        PathConfigService singleton instance
    """
    global _path_config_instance
    if _path_config_instance is None:
        _path_config_instance = PathConfigService()
    return _path_config_instance


# ============================================================================
# Convenience Functions (for backward compatibility)
# ============================================================================

def get_developer_base_dir() -> Path:
    """Get developer output base directory (convenience function)"""
    return get_path_config().developer_output_dir


def get_developer_tests_path(developer_name: str) -> str:
    """
    Get developer tests path as string (convenience function)

    Args:
        developer_name: Name of developer

    Returns:
        String path to developer's tests directory
    """
    return str(get_path_config().get_developer_tests_dir(developer_name))


def get_developer_path(developer_name: str) -> str:
    """
    Get developer output path as string (convenience function)

    Args:
        developer_name: Name of developer

    Returns:
        String path to developer's output directory
    """
    return str(get_path_config().get_developer_dir(developer_name))
