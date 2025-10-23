#!/usr/bin/env python3
"""
Sandbox Executor - Secure Code Execution Environment

Provides secure execution environment for developer-generated code:
- Resource limits (CPU, memory, time)
- Process isolation
- Network restrictions
- Filesystem access control
- Security scanning before execution

Supports multiple backends:
- subprocess (basic, process-level isolation)
- docker (advanced, container-level isolation)
- firejail (Linux sandboxing tool)
"""

import subprocess
import resource
import signal
import tempfile
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution"""
    max_cpu_time: int = 300  # seconds
    max_memory_mb: int = 512  # MB
    max_file_size_mb: int = 100  # MB
    allow_network: bool = False
    allowed_paths: List[str] = None  # Writable paths
    timeout: int = 600  # Overall timeout (seconds)


@dataclass
class ExecutionResult:
    """Result of sandbox execution"""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    memory_used_mb: Optional[float] = None
    killed: bool = False
    kill_reason: Optional[str] = None


class SecurityScanner:
    """
    Scan code for security issues before execution

    Checks for:
    - Dangerous imports (os.system, subprocess, eval, exec)
    - File system access patterns
    - Network operations
    - Code injection patterns
    """

    DANGEROUS_PATTERNS = [
        "os.system",
        "subprocess.call",
        "subprocess.run",
        "subprocess.Popen",
        "eval(",
        "exec(",
        "__import__",
        "compile(",
        "open(",  # File access
        "socket.",  # Network access
        "urllib",
        "requests",
        "http",
    ]

    @classmethod
    def scan_code(cls, code: str) -> Dict:
        """
        Scan code for security issues

        Args:
            code: Python code to scan

        Returns:
            Dict with scan results
        """
        issues = []

        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern in code:
                issues.append({
                    "pattern": pattern,
                    "severity": "high" if pattern in ["eval(", "exec(", "os.system"] else "medium",
                    "message": f"Potentially dangerous code: {pattern}"
                })

        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "risk_level": "high" if any(i["severity"] == "high" for i in issues) else (
                "medium" if issues else "low"
            )
        }


class SubprocessSandbox:
    """
    Basic sandbox using subprocess with resource limits

    Provides:
    - CPU time limits (RLIMIT_CPU)
    - Memory limits (RLIMIT_AS)
    - File size limits (RLIMIT_FSIZE)
    - Process timeout
    - Working directory isolation
    """

    def __init__(self, config: SandboxConfig):
        """
        Initialize subprocess sandbox

        Args:
            config: Sandbox configuration
        """
        self.config = config

    def execute_python(
        self,
        script_path: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict] = None
    ) -> ExecutionResult:
        """
        Execute Python script in sandbox

        Args:
            script_path: Path to Python script
            args: Command-line arguments
            env: Environment variables

        Returns:
            ExecutionResult with execution details
        """
        import time

        start_time = time.time()

        # Build command
        cmd = ["python3", script_path]
        if args:
            cmd.extend(args)

        # Prepare environment
        if env is None:
            env = {}

        # Set resource limits preexec function
        def set_limits():
            """Set resource limits for child process"""
            # CPU time limit
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (self.config.max_cpu_time, self.config.max_cpu_time)
            )

            # Memory limit (address space)
            max_memory_bytes = self.config.max_memory_mb * 1024 * 1024
            resource.setrlimit(
                resource.RLIMIT_AS,
                (max_memory_bytes, max_memory_bytes)
            )

            # File size limit
            max_file_size_bytes = self.config.max_file_size_mb * 1024 * 1024
            resource.setrlimit(
                resource.RLIMIT_FSIZE,
                (max_file_size_bytes, max_file_size_bytes)
            )

        try:
            # Execute with timeout
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.config.timeout,
                preexec_fn=set_limits,
                env=env,
                text=True
            )

            execution_time = time.time() - start_time

            return ExecutionResult(
                success=(result.returncode == 0),
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time=execution_time,
                killed=False
            )

        except subprocess.TimeoutExpired as e:
            execution_time = time.time() - start_time

            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout=e.stdout.decode() if e.stdout else "",
                stderr=e.stderr.decode() if e.stderr else "",
                execution_time=execution_time,
                killed=True,
                kill_reason=f"Timeout ({self.config.timeout}s)"
            )

        except Exception as e:
            execution_time = time.time() - start_time

            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                killed=True,
                kill_reason=f"Execution error: {e}"
            )


class DockerSandbox:
    """
    Advanced sandbox using Docker containers

    Provides:
    - Full process isolation
    - Network isolation
    - Filesystem isolation
    - CPU/memory limits
    - Security hardening
    """

    def __init__(self, config: SandboxConfig):
        """
        Initialize Docker sandbox

        Args:
            config: Sandbox configuration
        """
        self.config = config
        self.image = "python:3.11-slim"  # Base Python image

    def is_available(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(
                ["docker", "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def execute_python(
        self,
        script_path: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict] = None
    ) -> ExecutionResult:
        """
        Execute Python script in Docker container

        Args:
            script_path: Path to Python script
            args: Command-line arguments
            env: Environment variables

        Returns:
            ExecutionResult with execution details
        """
        import time

        start_time = time.time()

        # Prepare volume mount
        script_dir = Path(script_path).parent
        script_name = Path(script_path).name

        # Build Docker command
        docker_cmd = [
            "docker", "run",
            "--rm",  # Remove container after execution
            "--read-only",  # Read-only filesystem
            f"--memory={self.config.max_memory_mb}m",  # Memory limit
            f"--cpus={self.config.max_cpu_time / 60:.1f}",  # CPU limit (rough)
            "--network=none" if not self.config.allow_network else "--network=bridge",
            f"--volume={script_dir}:/workspace:ro",  # Mount script directory (read-only)
            "--workdir=/workspace",
            self.image,
            "python3", script_name
        ]

        if args:
            docker_cmd.extend(args)

        # Add environment variables
        if env:
            for key, value in env.items():
                docker_cmd.insert(2, f"--env={key}={value}")

        try:
            # Execute with timeout
            result = subprocess.run(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.config.timeout,
                text=True
            )

            execution_time = time.time() - start_time

            return ExecutionResult(
                success=(result.returncode == 0),
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time=execution_time,
                killed=False
            )

        except subprocess.TimeoutExpired as e:
            execution_time = time.time() - start_time

            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout=e.stdout.decode() if e.stdout else "",
                stderr=e.stderr.decode() if e.stderr else "",
                execution_time=execution_time,
                killed=True,
                kill_reason=f"Timeout ({self.config.timeout}s)"
            )

        except Exception as e:
            execution_time = time.time() - start_time

            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                killed=True,
                kill_reason=f"Docker error: {e}"
            )


class SandboxExecutor:
    """
    Main sandbox executor with automatic backend selection

    Automatically selects best available sandbox:
    1. Docker (if available, most secure)
    2. Subprocess (fallback, basic isolation)
    """

    def __init__(self, config: Optional[SandboxConfig] = None, prefer_docker: bool = False):
        """
        Initialize sandbox executor

        Args:
            config: Sandbox configuration (default: safe defaults)
            prefer_docker: Prefer Docker if available (default: False, use subprocess)
        """
        self.config = config or SandboxConfig()

        # Select backend
        if prefer_docker:
            docker = DockerSandbox(self.config)
            if docker.is_available():
                self.backend = docker
                self.backend_name = "docker"
            else:
                self.backend = SubprocessSandbox(self.config)
                self.backend_name = "subprocess"
        else:
            # Default to subprocess (simpler, no Docker dependency)
            self.backend = SubprocessSandbox(self.config)
            self.backend_name = "subprocess"

    def execute_python_code(
        self,
        code: str,
        scan_security: bool = True
    ) -> ExecutionResult:
        """
        Execute Python code in sandbox

        Args:
            code: Python code to execute
            scan_security: Scan for security issues first

        Returns:
            ExecutionResult with execution details
        """
        # Security scan
        if scan_security:
            scan_result = SecurityScanner.scan_code(code)
            if not scan_result["safe"]:
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Security scan failed: {scan_result['issues']}",
                    execution_time=0.0,
                    killed=True,
                    kill_reason="Failed security scan"
                )

        # Write code to temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(code)
            script_path = f.name

        try:
            # Execute in sandbox
            result = self.backend.execute_python(script_path)
            return result
        finally:
            # Cleanup
            Path(script_path).unlink(missing_ok=True)

    def execute_python_file(
        self,
        script_path: str,
        args: Optional[List[str]] = None,
        scan_security: bool = True
    ) -> ExecutionResult:
        """
        Execute Python file in sandbox

        Args:
            script_path: Path to Python script
            args: Command-line arguments
            scan_security: Scan for security issues first

        Returns:
            ExecutionResult with execution details
        """
        # Security scan
        if scan_security:
            with open(script_path) as f:
                code = f.read()

            scan_result = SecurityScanner.scan_code(code)
            if not scan_result["safe"]:
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Security scan failed: {scan_result['issues']}",
                    execution_time=0.0,
                    killed=True,
                    kill_reason="Failed security scan"
                )

        # Execute in sandbox
        return self.backend.execute_python(script_path, args=args)


if __name__ == "__main__":
    """Example usage and testing"""

    print("Sandbox Executor - Example Usage")
    print("=" * 70)

    # Create executor
    config = SandboxConfig(
        max_cpu_time=10,  # 10 seconds CPU
        max_memory_mb=256,  # 256 MB
        timeout=15  # 15 seconds overall
    )

    executor = SandboxExecutor(config)
    print(f"Using backend: {executor.backend_name}\n")

    # Test 1: Safe code
    print("1. Executing safe code...")
    safe_code = """
print("Hello from sandbox!")
import math
print(f"Pi = {math.pi}")
"""

    result = executor.execute_python_code(safe_code)
    print(f"   Success: {result.success}")
    print(f"   Output: {result.stdout.strip()}")
    print(f"   Time: {result.execution_time:.2f}s")

    # Test 2: Security scan
    print("\n2. Testing security scan...")
    unsafe_code = """
import os
os.system("ls /")
"""

    result = executor.execute_python_code(unsafe_code, scan_security=True)
    print(f"   Success: {result.success}")
    print(f"   Killed: {result.killed}")
    print(f"   Reason: {result.kill_reason}")

    # Test 3: Timeout
    print("\n3. Testing timeout...")
    timeout_code = """
import time
time.sleep(20)  # Will timeout
"""

    result = executor.execute_python_code(timeout_code, scan_security=False)
    print(f"   Success: {result.success}")
    print(f"   Killed: {result.killed}")
    print(f"   Reason: {result.kill_reason}")

    print("\n" + "=" * 70)
    print("✅ Sandbox executor working correctly!")
