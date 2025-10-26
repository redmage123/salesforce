#!/usr/bin/env python3
"""
Platform Detection and Resource Allocation Module

Detects the current platform (OS, hardware, resources) and provides
resource allocation recommendations for the Artemis orchestrator.

Single Responsibility: Platform detection and resource profiling
"""

import os
import platform
import psutil
import multiprocessing
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from pathlib import Path
import json
import hashlib


@dataclass
class PlatformInfo:
    """Complete platform and resource information"""

    # Operating System
    os_type: str  # linux, darwin, windows
    os_name: str  # Ubuntu, macOS, Windows 10
    os_version: str  # 22.04, 14.0, 10.0.19045
    os_release: str  # 6.8.0-79-generic

    # Hardware
    cpu_count_physical: int  # Physical cores
    cpu_count_logical: int  # Logical cores (with hyperthreading)
    cpu_frequency_mhz: float  # Current CPU frequency
    cpu_architecture: str  # x86_64, arm64, aarch64

    # Memory
    total_memory_gb: float  # Total RAM
    available_memory_gb: float  # Available RAM

    # Disk
    total_disk_gb: float  # Total disk space
    available_disk_gb: float  # Available disk space
    disk_type: str  # SSD, HDD, Unknown

    # Python Environment
    python_version: str  # 3.11.5
    python_implementation: str  # CPython, PyPy

    # Hostname
    hostname: str

    # Platform hash (for detecting changes)
    platform_hash: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlatformInfo':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class ResourceAllocation:
    """Resource allocation recommendations"""

    # Parallelization
    max_parallel_developers: int  # Maximum concurrent developer agents
    max_parallel_tests: int  # Maximum concurrent test runners
    max_parallel_stages: int  # Maximum stages to run in parallel

    # Resource limits
    max_memory_per_agent_gb: float  # Memory limit per agent
    recommended_batch_size: int  # For batch processing operations

    # Performance tuning
    use_async_io: bool  # Whether to use async I/O
    enable_caching: bool  # Whether to enable aggressive caching
    thread_pool_size: int  # Size of thread pool for I/O operations

    # Reasoning
    reasoning: str  # Explanation of allocation decisions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class PlatformDetector:
    """
    Detects platform information and provides resource allocation recommendations

    Single Responsibility: Platform profiling and resource calculation
    """

    def __init__(self, logger: Optional[Any] = None):
        """
        Initialize platform detector

        Args:
            logger: Optional logger instance
        """
        self.logger = logger

    def detect_platform(self) -> PlatformInfo:
        """
        Detect current platform information

        Returns:
            Complete platform information
        """
        # OS Information
        os_type = platform.system().lower()
        os_name = self._get_os_name()
        os_version = platform.version()
        os_release = platform.release()

        # CPU Information
        cpu_count_physical = psutil.cpu_count(logical=False) or 1
        cpu_count_logical = psutil.cpu_count(logical=True) or 1
        cpu_freq = psutil.cpu_freq()
        cpu_frequency_mhz = cpu_freq.current if cpu_freq else 0.0
        cpu_architecture = platform.machine()

        # Memory Information
        memory = psutil.virtual_memory()
        total_memory_gb = memory.total / (1024 ** 3)
        available_memory_gb = memory.available / (1024 ** 3)

        # Disk Information
        disk = psutil.disk_usage('/')
        total_disk_gb = disk.total / (1024 ** 3)
        available_disk_gb = disk.free / (1024 ** 3)
        disk_type = self._detect_disk_type()

        # Python Information
        python_version = platform.python_version()
        python_implementation = platform.python_implementation()

        # Hostname
        hostname = platform.node()

        # Create platform info
        info = PlatformInfo(
            os_type=os_type,
            os_name=os_name,
            os_version=os_version,
            os_release=os_release,
            cpu_count_physical=cpu_count_physical,
            cpu_count_logical=cpu_count_logical,
            cpu_frequency_mhz=cpu_frequency_mhz,
            cpu_architecture=cpu_architecture,
            total_memory_gb=total_memory_gb,
            available_memory_gb=available_memory_gb,
            total_disk_gb=total_disk_gb,
            available_disk_gb=available_disk_gb,
            disk_type=disk_type,
            python_version=python_version,
            python_implementation=python_implementation,
            hostname=hostname,
            platform_hash=""  # Will be calculated
        )

        # Calculate platform hash
        info.platform_hash = self._calculate_platform_hash(info)

        return info

    def calculate_resource_allocation(self, platform_info: PlatformInfo) -> ResourceAllocation:
        """
        Calculate optimal resource allocation based on platform

        Args:
            platform_info: Detected platform information

        Returns:
            Resource allocation recommendations
        """
        reasoning_parts = []

        # Calculate parallel developers
        # Use 1 developer per 2 cores, capped at 4 for safety
        max_developers = min(
            max(1, platform_info.cpu_count_logical // 2),
            4
        )
        reasoning_parts.append(
            f"Developers: {max_developers} (CPU cores: {platform_info.cpu_count_logical})"
        )

        # Calculate parallel tests
        # Tests can be more parallel - use 1 test runner per core, up to 8
        max_tests = min(
            platform_info.cpu_count_logical,
            8
        )
        reasoning_parts.append(
            f"Test runners: {max_tests} (CPU cores: {platform_info.cpu_count_logical})"
        )

        # Calculate parallel stages
        # Conservative - only 2 stages in parallel to avoid resource contention
        max_stages = 2
        reasoning_parts.append(f"Parallel stages: {max_stages}")

        # Memory per agent
        # Reserve 2GB for system, divide rest by max parallel agents
        reserved_memory = 2.0
        total_agents = max_developers + max_tests
        max_memory_per_agent = max(
            1.0,  # Minimum 1GB per agent
            (platform_info.available_memory_gb - reserved_memory) / total_agents
        )
        reasoning_parts.append(
            f"Memory per agent: {max_memory_per_agent:.1f}GB "
            f"(Available: {platform_info.available_memory_gb:.1f}GB)"
        )

        # Batch size based on memory
        # Larger batches for more memory
        if platform_info.total_memory_gb >= 16:
            batch_size = 100
        elif platform_info.total_memory_gb >= 8:
            batch_size = 50
        else:
            batch_size = 25
        reasoning_parts.append(f"Batch size: {batch_size}")

        # Async I/O - enable on Linux/macOS, optional on Windows
        use_async = platform_info.os_type in ['linux', 'darwin']
        reasoning_parts.append(f"Async I/O: {use_async}")

        # Caching - enable if we have enough memory
        enable_caching = platform_info.available_memory_gb >= 4.0
        reasoning_parts.append(f"Caching: {enable_caching}")

        # Thread pool size
        thread_pool_size = min(platform_info.cpu_count_logical * 2, 16)
        reasoning_parts.append(f"Thread pool: {thread_pool_size}")

        return ResourceAllocation(
            max_parallel_developers=max_developers,
            max_parallel_tests=max_tests,
            max_parallel_stages=max_stages,
            max_memory_per_agent_gb=max_memory_per_agent,
            recommended_batch_size=batch_size,
            use_async_io=use_async,
            enable_caching=enable_caching,
            thread_pool_size=thread_pool_size,
            reasoning=" | ".join(reasoning_parts)
        )

    def _get_os_name(self) -> str:
        """Get friendly OS name"""
        system = platform.system()

        if system == "Linux":
            # Try to get distribution name
            try:
                import distro
                return distro.name(pretty=True)
            except ImportError:
                # Fallback to platform info
                return f"Linux {platform.release()}"
        elif system == "Darwin":
            return f"macOS {platform.mac_ver()[0]}"
        elif system == "Windows":
            return f"Windows {platform.release()}"
        else:
            return system

    def _detect_disk_type(self) -> str:
        """
        Attempt to detect if disk is SSD or HDD

        Returns:
            "SSD", "HDD", or "Unknown"
        """
        try:
            # Linux-specific detection
            if platform.system() == "Linux":
                # Check /sys/block for rotational flag
                for device in Path("/sys/block").iterdir():
                    if device.name.startswith(('sd', 'nvme', 'vd')):
                        rotational_file = device / "queue" / "rotational"
                        if rotational_file.exists():
                            with open(rotational_file) as f:
                                if f.read().strip() == "0":
                                    return "SSD"
                                else:
                                    return "HDD"

            # macOS-specific detection
            elif platform.system() == "Darwin":
                import subprocess
                result = subprocess.run(
                    ["diskutil", "info", "/"],
                    capture_output=True,
                    text=True
                )
                if "Solid State: Yes" in result.stdout:
                    return "SSD"
                elif "Solid State: No" in result.stdout:
                    return "HDD"

            # Windows-specific detection
            elif platform.system() == "Windows":
                import subprocess
                result = subprocess.run(
                    ["powershell", "-Command", "Get-PhysicalDisk | Select-Object MediaType"],
                    capture_output=True,
                    text=True
                )
                if "SSD" in result.stdout:
                    return "SSD"
                elif "HDD" in result.stdout:
                    return "HDD"

        except Exception:
            pass

        return "Unknown"

    def _calculate_platform_hash(self, info: PlatformInfo) -> str:
        """
        Calculate a hash of platform characteristics

        This helps detect if the platform has changed significantly

        Args:
            info: Platform information

        Returns:
            SHA256 hash of key platform characteristics
        """
        # Include key characteristics that shouldn't change
        key_data = (
            f"{info.os_type}|"
            f"{info.os_name}|"
            f"{info.cpu_count_physical}|"
            f"{info.cpu_count_logical}|"
            f"{info.cpu_architecture}|"
            f"{info.total_memory_gb:.0f}|"  # Round to avoid minor variations
            f"{info.hostname}"
        )

        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def platforms_match(self, info1: PlatformInfo, info2: PlatformInfo) -> bool:
        """
        Check if two platform infos represent the same platform

        Args:
            info1: First platform info
            info2: Second platform info

        Returns:
            True if platforms match
        """
        return info1.platform_hash == info2.platform_hash

    def log(self, message: str, level: str = "INFO"):
        """Log a message"""
        if self.logger:
            self.logger.log(message, level)
        else:
            print(f"[{level}] {message}")


def get_platform_summary(info: PlatformInfo, allocation: ResourceAllocation) -> str:
    """
    Generate a human-readable platform summary

    Args:
        info: Platform information
        allocation: Resource allocation

    Returns:
        Formatted summary string
    """
    return f"""
======================================================================
🖥️  ARTEMIS PLATFORM DETECTION
======================================================================

Operating System:
  Type:         {info.os_type}
  Name:         {info.os_name}
  Version:      {info.os_version}
  Release:      {info.os_release}
  Architecture: {info.cpu_architecture}

Hardware:
  CPU Cores:    {info.cpu_count_physical} physical, {info.cpu_count_logical} logical
  CPU Speed:    {info.cpu_frequency_mhz:.0f} MHz
  Total Memory: {info.total_memory_gb:.1f} GB
  Free Memory:  {info.available_memory_gb:.1f} GB
  Disk Space:   {info.available_disk_gb:.1f} GB / {info.total_disk_gb:.1f} GB
  Disk Type:    {info.disk_type}

Python:
  Version:      {info.python_version}
  Implementation: {info.python_implementation}

Resource Allocation:
  Max Parallel Developers: {allocation.max_parallel_developers}
  Max Parallel Tests:      {allocation.max_parallel_tests}
  Max Parallel Stages:     {allocation.max_parallel_stages}
  Memory per Agent:        {allocation.max_memory_per_agent_gb:.1f} GB
  Batch Size:              {allocation.recommended_batch_size}
  Async I/O:               {'Enabled' if allocation.use_async_io else 'Disabled'}
  Caching:                 {'Enabled' if allocation.enable_caching else 'Disabled'}
  Thread Pool Size:        {allocation.thread_pool_size}

Reasoning: {allocation.reasoning}

Platform Hash: {info.platform_hash}

======================================================================
"""
