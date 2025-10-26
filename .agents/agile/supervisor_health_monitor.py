#!/usr/bin/env python3
"""
Health Monitor for Supervisor

Single Responsibility: Monitor agent and process health

Extracted from SupervisorAgent to follow Single Responsibility Principle.

Design Patterns:
- Observer Pattern: Notify observers of health events
- Strategy Pattern: Configurable heartbeat intervals
"""

import psutil
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from artemis_stage_interface import LoggerInterface


class AgentHealthEvent(Enum):
    """Agent health event types"""
    STARTED = "started"
    PROGRESS = "progress"
    STALLED = "stalled"
    CRASHED = "crashed"
    HUNG = "hung"
    COMPLETED = "completed"


@dataclass
class ProcessHealth:
    """Process health information"""
    pid: int
    stage_name: str
    start_time: datetime
    cpu_percent: float
    memory_mb: float
    status: str
    is_hanging: bool
    is_timeout: bool


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    CRITICAL = "critical"


class HealthMonitor:
    """
    Monitor agent and process health

    Responsibilities:
    - Register/unregister agents
    - Track agent heartbeats
    - Detect hanging processes
    - Detect agent crashes
    - Check agent progress
    - Run watchdog thread for monitoring
    - Notify observers of health events

    Thread-Safety: Thread-safe (uses locks for shared state)
    """

    def __init__(
        self,
        logger: Optional[LoggerInterface] = None,
        verbose: bool = True,
        state_machine: Optional[Any] = None
    ):
        """
        Initialize Health Monitor

        Args:
            logger: Logger for recording events
            verbose: Enable verbose logging
            state_machine: Optional state machine for crash detection
        """
        self.logger = logger
        self.verbose = verbose
        self.state_machine = state_machine

        # Agent registration tracking
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self._agents_lock = threading.Lock()

        # Process tracking
        self.process_registry: Dict[int, ProcessHealth] = {}
        self._process_lock = threading.Lock()

        # Health observers (Observer Pattern)
        self.health_observers: List[Any] = []
        self._observers_lock = threading.Lock()

        # Watchdog thread
        self.watchdog_thread: Optional[threading.Thread] = None
        self._watchdog_running = False

        # Statistics
        self.stats = {
            "agents_registered": 0,
            "heartbeats_received": 0,
            "crashes_detected": 0,
            "hangs_detected": 0,
            "processes_killed": 0,
            "zombie_processes_cleaned": 0
        }

    def register_agent(
        self,
        agent_name: str,
        agent_type: str = "stage",
        metadata: Optional[Dict[str, Any]] = None,
        heartbeat_interval: float = 15.0
    ) -> None:
        """
        Register an agent for health monitoring

        Args:
            agent_name: Name of the agent (e.g., "DevelopmentStage")
            agent_type: Type of agent (e.g., "stage", "worker", "analyzer")
            metadata: Optional metadata about the agent
            heartbeat_interval: Expected heartbeat interval in seconds
        """
        with self._agents_lock:
            self.registered_agents[agent_name] = {
                "type": agent_type,
                "registered_at": datetime.now().isoformat(),
                "metadata": metadata or {},
                "heartbeat_interval": heartbeat_interval,
                "last_heartbeat": None
            }

        self.stats["agents_registered"] += 1
        self._log(f"✅ Registered agent '{agent_name}' ({agent_type})")

        # Notify observers
        self.notify_health_event(
            agent_name,
            AgentHealthEvent.STARTED,
            {"agent_type": agent_type, "metadata": metadata}
        )

    def unregister_agent(self, agent_name: str) -> None:
        """
        Unregister an agent (called when agent completes)

        Args:
            agent_name: Name of the agent
        """
        with self._agents_lock:
            if agent_name in self.registered_agents:
                del self.registered_agents[agent_name]
                self._log(f"✅ Unregistered agent '{agent_name}'")

                # Notify observers
                self.notify_health_event(
                    agent_name,
                    AgentHealthEvent.COMPLETED,
                    {}
                )

    def agent_heartbeat(
        self,
        agent_name: str,
        progress_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record agent heartbeat (agent is alive and making progress)

        Agents should call this periodically (e.g., every 10-30 seconds).

        Args:
            agent_name: Name of the agent
            progress_data: Optional progress information
        """
        with self._agents_lock:
            if agent_name not in self.registered_agents:
                self._log(f"⚠️  Heartbeat from unregistered agent '{agent_name}'", "WARNING")
                return

            # Update last heartbeat time
            self.registered_agents[agent_name]["last_heartbeat"] = datetime.now().isoformat()

        self.stats["heartbeats_received"] += 1

        # Notify observers of progress
        self.notify_health_event(
            agent_name,
            AgentHealthEvent.PROGRESS,
            progress_data or {}
        )

    def detect_hanging_processes(self) -> List[ProcessHealth]:
        """
        Detect hanging processes (high CPU, no progress)

        Returns:
            List of hanging processes
        """
        hanging = []

        with self._process_lock:
            for pid, process_health in list(self.process_registry.items()):
                try:
                    process = psutil.Process(pid)

                    # Check if process is hung
                    cpu_percent = process.cpu_percent(interval=0.1)
                    elapsed = (datetime.now() - process_health.start_time).total_seconds()

                    # Heuristic: high CPU for long time = hanging
                    if cpu_percent > 90 and elapsed > 300:  # 5 minutes
                        process_health.is_hanging = True
                        process_health.cpu_percent = cpu_percent
                        hanging.append(process_health)

                except psutil.NoSuchProcess:
                    # Process already terminated, remove from registry
                    del self.process_registry[pid]
                except Exception as e:
                    self._log(f"Error checking process {pid}: {e}", "WARNING")

        if hanging:
            self.stats["hangs_detected"] += len(hanging)

        return hanging

    def detect_agent_crash(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Detect if an agent has crashed

        Args:
            agent_name: Name of the agent

        Returns:
            Crash info dict if crashed, None otherwise
        """
        try:
            # Check state machine for FAILED state
            if self.state_machine:
                current_state = self.state_machine.get_current_state()
                if current_state and "FAILED" in str(current_state):
                    # Get error details from context
                    context = getattr(self.state_machine, 'context', {})
                    error_info = context.get("error", {})

                    crash_info = {
                        "agent_name": agent_name,
                        "error": error_info.get("message", "Unknown error"),
                        "error_type": error_info.get("type", "Unknown"),
                        "traceback": context.get("traceback", ""),
                        "state": str(current_state)
                    }

                    self.stats["crashes_detected"] += 1
                    return crash_info

            return None

        except Exception as e:
            self._log(f"⚠️  Error detecting crash: {e}", "WARNING")
            return None

    def check_agent_progress(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Check if an agent is making progress

        Args:
            agent_name: Name of the agent

        Returns:
            Progress info dict if progressing, None otherwise
        """
        try:
            # Check state machine for state transitions
            if self.state_machine and hasattr(self.state_machine, 'context'):
                context = self.state_machine.context
                last_transition = context.get("last_transition_time")

                if last_transition:
                    return {
                        "agent_name": agent_name,
                        "last_transition": last_transition,
                        "current_state": str(self.state_machine.get_current_state())
                    }

            return None

        except Exception as e:
            self._log(f"⚠️  Error checking progress: {e}", "WARNING")
            return None

    def monitor_agent_health(
        self,
        agent_name: str,
        timeout_seconds: int = 300,
        check_interval: int = 5
    ) -> Dict[str, Any]:
        """
        Monitor an agent's health (blocking call)

        Args:
            agent_name: Name of the agent to monitor
            timeout_seconds: Maximum time before considering agent hung
            check_interval: How often to check agent status in seconds

        Returns:
            Health status dict
        """
        self._log(f"👀 Monitoring agent '{agent_name}' (timeout: {timeout_seconds}s)")

        start_time = datetime.now()
        last_activity = start_time
        health_status = {
            "agent_name": agent_name,
            "status": "healthy",
            "start_time": start_time.isoformat(),
            "checks_performed": 0
        }

        while True:
            elapsed = (datetime.now() - start_time).total_seconds()
            health_status["checks_performed"] += 1

            # Check if agent has crashed
            crash_detected = self.detect_agent_crash(agent_name)
            if crash_detected:
                health_status["status"] = "crashed"
                health_status["crash_info"] = crash_detected
                health_status["elapsed_time"] = elapsed

                self._log(f"💥 Agent '{agent_name}' crashed!")
                self._log(f"   Error: {crash_detected.get('error')}")

                return health_status

            # Check if agent has hung (timeout exceeded)
            if elapsed > timeout_seconds:
                health_status["status"] = "hung"
                health_status["timeout_seconds"] = timeout_seconds
                health_status["elapsed_time"] = elapsed

                self._log(f"⏰ Agent '{agent_name}' appears hung (timeout: {timeout_seconds}s)")

                return health_status

            # Check for progress (heartbeat)
            progress = self.check_agent_progress(agent_name)
            if progress:
                last_activity = datetime.now()
                health_status["last_activity"] = last_activity.isoformat()

            # Check if stalled (no progress for extended period)
            time_since_activity = (datetime.now() - last_activity).total_seconds()
            if time_since_activity > (timeout_seconds / 2):
                health_status["status"] = "stalled"
                health_status["time_since_activity"] = time_since_activity

                self._log(f"⚠️  Agent '{agent_name}' may be stalled (no activity for {time_since_activity}s)")

            # Sleep before next check
            time.sleep(check_interval)

    def start_watchdog(
        self,
        check_interval: int = 5,
        timeout_seconds: int = 300
    ) -> threading.Thread:
        """
        Start a watchdog thread to monitor agents

        The watchdog checks for:
        1. CRASHED - State machine in FAILED state
        2. HUNG - No state transition for > timeout_seconds
        3. STALLED - No progress for > timeout_seconds/2

        Args:
            check_interval: Seconds between checks (default 5)
            timeout_seconds: Max time before considering hung (default 300 = 5min)

        Returns:
            Watchdog thread (already started)
        """
        def watchdog_loop():
            """Watchdog monitoring loop"""
            self._log(f"🐕 Watchdog started (check_interval={check_interval}s, timeout={timeout_seconds}s)")
            self._watchdog_running = True

            while self._watchdog_running:
                try:
                    time.sleep(check_interval)

                    # Check state machine for crashes
                    if self.state_machine:
                        current_state = self.state_machine.get_current_state()

                        # Detect crash (FAILED state)
                        if current_state and "FAILED" in str(current_state):
                            context = getattr(self.state_machine, 'context', {})
                            error_info = context.get("error", {})

                            crash_info = {
                                "agent_name": context.get("stage_name", "unknown"),
                                "error": error_info.get("message", "Unknown error"),
                                "error_type": error_info.get("type", "Unknown"),
                                "traceback": context.get("traceback", ""),
                                "state": str(current_state)
                            }

                            # Notify observers
                            self.notify_health_event(
                                crash_info["agent_name"],
                                AgentHealthEvent.CRASHED,
                                {"crash_info": crash_info, "context": context}
                            )

                        # Check for hang/stall via state machine transitions
                        if hasattr(self.state_machine, 'context'):
                            context = self.state_machine.context
                            last_transition = context.get("last_transition_time")

                            if last_transition:
                                if isinstance(last_transition, str):
                                    last_transition = datetime.fromisoformat(last_transition)

                                elapsed = (datetime.now() - last_transition).total_seconds()

                                # Hung (exceeded timeout)
                                if elapsed > timeout_seconds:
                                    self.notify_health_event(
                                        context.get("stage_name", "unknown"),
                                        AgentHealthEvent.HUNG,
                                        {
                                            "timeout_info": {
                                                "timeout_seconds": timeout_seconds,
                                                "elapsed_time": elapsed
                                            }
                                        }
                                    )

                                # Stalled (no progress for extended period)
                                elif elapsed > (timeout_seconds / 2):
                                    self.notify_health_event(
                                        context.get("stage_name", "unknown"),
                                        AgentHealthEvent.STALLED,
                                        {"time_since_activity": elapsed}
                                    )

                except Exception as e:
                    self._log(f"⚠️  Watchdog error: {e}", "WARNING")

            self._log("🐕 Watchdog stopped")

        # Start watchdog in daemon thread
        self.watchdog_thread = threading.Thread(target=watchdog_loop, daemon=True)
        self.watchdog_thread.start()

        return self.watchdog_thread

    def stop_watchdog(self) -> None:
        """Stop the watchdog thread"""
        self._watchdog_running = False
        if self.watchdog_thread:
            self.watchdog_thread.join(timeout=5.0)
        self._log("Watchdog stopped")

    def kill_hanging_process(self, pid: int, force: bool = False) -> bool:
        """
        Kill a hanging process

        Args:
            pid: Process ID
            force: Use SIGKILL instead of SIGTERM

        Returns:
            True if killed successfully
        """
        try:
            process = psutil.Process(pid)

            if force:
                process.kill()  # SIGKILL
            else:
                process.terminate()  # SIGTERM

            self.stats["processes_killed"] += 1

            signal_name = "SIGKILL" if force else "SIGTERM"
            self._log(f"💀 Killed hanging process {pid} ({signal_name})")

            # Remove from registry
            with self._process_lock:
                if pid in self.process_registry:
                    del self.process_registry[pid]

            return True

        except Exception as e:
            self._log(f"⚠️  Failed to kill process {pid}: {e}", "WARNING")
            return False

    def cleanup_zombie_processes(self) -> int:
        """
        Clean up zombie processes

        Returns:
            Number of zombies cleaned
        """
        cleaned = 0

        with self._process_lock:
            for pid in list(self.process_registry.keys()):
                try:
                    process = psutil.Process(pid)

                    # Check if zombie
                    if process.status() == psutil.STATUS_ZOMBIE:
                        process.wait()  # Clean up zombie
                        del self.process_registry[pid]
                        cleaned += 1
                        self._log(f"🧟 Cleaned zombie process {pid}")

                except psutil.NoSuchProcess:
                    # Process already gone, remove from registry
                    del self.process_registry[pid]
                except Exception as e:
                    self._log(f"Error cleaning zombie {pid}: {e}", "WARNING")

        if cleaned > 0:
            self.stats["zombie_processes_cleaned"] += cleaned

        return cleaned

    def get_health_status(self) -> HealthStatus:
        """
        Get overall health status

        Returns:
            HealthStatus enum value
        """
        with self._agents_lock:
            # No agents registered
            if not self.registered_agents:
                return HealthStatus.HEALTHY

            # Check for recent heartbeats
            now = datetime.now()
            stalled_count = 0

            for agent_name, agent_info in self.registered_agents.items():
                last_heartbeat = agent_info.get("last_heartbeat")
                if not last_heartbeat:
                    continue

                last_heartbeat_time = datetime.fromisoformat(last_heartbeat)
                elapsed = (now - last_heartbeat_time).total_seconds()
                expected_interval = agent_info.get("heartbeat_interval", 15.0)

                # Agent is stalled if no heartbeat for 3x expected interval
                if elapsed > (expected_interval * 3):
                    stalled_count += 1

            total_agents = len(self.registered_agents)
            stalled_ratio = stalled_count / total_agents if total_agents > 0 else 0

            # Determine health status
            if stalled_ratio >= 0.75:
                return HealthStatus.CRITICAL
            elif stalled_ratio >= 0.5:
                return HealthStatus.FAILING
            elif stalled_ratio > 0:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY

    def register_health_observer(self, observer: Any) -> None:
        """
        Register a health observer (Observer Pattern)

        Args:
            observer: Observer object with on_agent_event() method
        """
        with self._observers_lock:
            if observer not in self.health_observers:
                self.health_observers.append(observer)
                self._log(f"Registered health observer: {type(observer).__name__}")

    def unregister_health_observer(self, observer: Any) -> None:
        """
        Unregister a health observer

        Args:
            observer: Observer to remove
        """
        with self._observers_lock:
            if observer in self.health_observers:
                self.health_observers.remove(observer)
                self._log(f"Unregistered health observer: {type(observer).__name__}")

    def notify_health_event(
        self,
        agent_name: str,
        event: AgentHealthEvent,
        data: Dict[str, Any]
    ) -> None:
        """
        Notify all observers of a health event

        Args:
            agent_name: Name of the agent
            event: Health event type
            data: Event data
        """
        with self._observers_lock:
            for observer in self.health_observers:
                try:
                    if hasattr(observer, 'on_agent_event'):
                        observer.on_agent_event(agent_name, event, data)
                except Exception as e:
                    self._log(f"Error notifying observer: {e}", "WARNING")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get health monitoring statistics

        Returns:
            Dict with statistics
        """
        with self._agents_lock, self._process_lock:
            return {
                **self.stats,
                "registered_agents_count": len(self.registered_agents),
                "monitored_processes_count": len(self.process_registry),
                "watchdog_running": self._watchdog_running,
                "health_status": self.get_health_status().value
            }

    def _log(self, message: str, level: str = "INFO") -> None:
        """
        Log a message

        Args:
            message: Message to log
            level: Log level
        """
        if self.logger:
            self.logger.log(message, level)
        elif self.verbose:
            prefix = "[HealthMonitor]"
            print(f"{prefix} {message}")


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Health Monitor Demo")
    parser.add_argument("--demo", action="store_true", help="Run demo")
    parser.add_argument("--stats", action="store_true", help="Show statistics")

    args = parser.parse_args()

    if args.demo:
        print("=" * 70)
        print("HEALTH MONITOR DEMO")
        print("=" * 70)

        # Create monitor
        monitor = HealthMonitor(verbose=True)

        # Register agents
        print("\n--- Registering agents ---")
        monitor.register_agent("agent1", "stage", heartbeat_interval=10.0)
        monitor.register_agent("agent2", "worker", heartbeat_interval=15.0)

        # Simulate heartbeats
        print("\n--- Simulating heartbeats ---")
        monitor.agent_heartbeat("agent1", {"progress": 50})
        monitor.agent_heartbeat("agent2", {"progress": 75})

        # Get health status
        print("\n--- Health Status ---")
        status = monitor.get_health_status()
        print(f"Overall Health: {status.value}")

        # Show stats
        print("\n--- Statistics ---")
        stats = monitor.get_statistics()
        print(json.dumps(stats, indent=2))

        # Unregister agents
        print("\n--- Unregistering agents ---")
        monitor.unregister_agent("agent1")
        monitor.unregister_agent("agent2")

    elif args.stats:
        monitor = HealthMonitor(verbose=False)
        stats = monitor.get_statistics()
        print(json.dumps(stats, indent=2))

    else:
        parser.print_help()
