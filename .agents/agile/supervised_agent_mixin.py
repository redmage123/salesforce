#!/usr/bin/env python3
"""
Supervised Agent Mixin - Hybrid Strategy for Agent Monitoring

Provides:
1. Automatic supervisor registration/unregistration
2. Daemon heartbeat thread for liveness signaling
3. Graceful cleanup on completion or crash

Design Patterns:
- Mixin Pattern: Provides reusable monitoring functionality
- Template Method: supervised_execution() defines the skeleton
- Strategy Pattern: Heartbeat strategy can be customized

Usage:
    class MyAgent(SupervisedAgentMixin):
        def __init__(self, supervisor, ...):
            super().__init__(supervisor, agent_name="MyAgent")

        def execute(self, context):
            with self.supervised_execution():
                # Your work here
                return result
"""

import time
import threading
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from contextlib import contextmanager

# Avoid circular imports
if TYPE_CHECKING:
    from supervisor_agent import SupervisorAgent

# Custom exceptions instead of base Exception
from artemis_exceptions import ArtemisException


class HeartbeatError(ArtemisException):
    """Raised when heartbeat thread encounters an error"""
    pass


class RegistrationError(ArtemisException):
    """Raised when agent registration fails"""
    pass


class SupervisedAgentMixin:
    """
    Mixin class providing supervisor integration for agents

    Implements the Hybrid Strategy:
    - Daemon heartbeat thread (non-blocking background monitoring)
    - Automatic registration/unregistration
    - Context manager for clean execution
    """

    def __init__(
        self,
        supervisor: Optional['SupervisorAgent'],
        agent_name: str,
        agent_type: str = "agent",
        heartbeat_interval: int = 15,
        enable_heartbeat: bool = True
    ):
        """
        Initialize supervised agent

        Args:
            supervisor: SupervisorAgent instance (None = no supervision)
            agent_name: Unique name for this agent
            agent_type: Type of agent (e.g., "stage", "worker", "analyzer")
            heartbeat_interval: Seconds between heartbeats (default 15)
            enable_heartbeat: Enable heartbeat thread (default True)

        Raises:
            ValueError: If agent_name is empty or heartbeat_interval <= 0
        """
        if not agent_name:
            raise ValueError("agent_name cannot be empty")
        if heartbeat_interval <= 0:
            raise ValueError(f"heartbeat_interval must be > 0, got {heartbeat_interval}")

        self.supervisor = supervisor
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.heartbeat_interval = heartbeat_interval
        self.enable_heartbeat = enable_heartbeat and supervisor is not None

        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_stop_event: Optional[threading.Event] = None
        self._progress_data: Dict[str, Any] = {}
        self._logger = logging.getLogger(f"supervised_agent.{agent_name}")

    def _register_with_supervisor(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Register agent with supervisor

        Args:
            metadata: Optional metadata about the agent
        """
        if self.supervisor is None:
            return

        # Unregister first (in case of re-initialization)
        self._unregister_from_supervisor()

        # Register with supervisor
        self.supervisor.register_agent(
            agent_name=self.agent_name,
            agent_type=self.agent_type,
            metadata=metadata or {}
        )

    def _unregister_from_supervisor(self) -> None:
        """
        Unregister agent from supervisor

        Note: Silently ignores errors since unregistration is cleanup
        """
        if self.supervisor is None:
            return

        try:
            self.supervisor.unregister_agent(self.agent_name)
        except (AttributeError, KeyError, ValueError) as e:
            # Agent may not be registered or supervisor may be None
            # Log but don't fail cleanup
            self._logger.debug(f"Unregistration ignored: {e}")
        except Exception as e:
            # Unexpected error - log warning but still don't fail cleanup
            self._logger.warning(f"Unexpected error during unregistration: {e}")

    def _start_heartbeat_thread(self) -> None:
        """Start daemon heartbeat thread"""
        if not self.enable_heartbeat or self.supervisor is None:
            return

        # Stop existing heartbeat if any
        self._stop_heartbeat_thread()

        # Create stop event
        self._heartbeat_stop_event = threading.Event()

        # Create and start heartbeat thread
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,  # Dies with main process
            name=f"{self.agent_name}-heartbeat"
        )
        self._heartbeat_thread.start()

    def _stop_heartbeat_thread(self) -> None:
        """Stop heartbeat thread"""
        if self._heartbeat_stop_event is not None:
            self._heartbeat_stop_event.set()

        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1.0)

        self._heartbeat_thread = None
        self._heartbeat_stop_event = None

    def _heartbeat_loop(self) -> None:
        """Heartbeat thread main loop"""
        while not self._heartbeat_stop_event.is_set():
            try:
                # Send heartbeat with progress data
                self.supervisor.agent_heartbeat(
                    agent_name=self.agent_name,
                    progress_data=self._progress_data.copy()
                )
            except (AttributeError, KeyError, ValueError, TypeError) as e:
                # Expected errors - supervisor might be None or method unavailable
                self._logger.debug(f"Heartbeat error (expected): {e}")
            except Exception as e:
                # Unexpected error - log warning but don't crash heartbeat thread
                self._logger.warning(f"Unexpected heartbeat error: {e}", exc_info=True)

            # Sleep with ability to wake up on stop event
            self._heartbeat_stop_event.wait(timeout=self.heartbeat_interval)

    def update_progress(self, progress_data: Dict[str, Any]) -> None:
        """
        Update progress data that will be sent with next heartbeat

        Args:
            progress_data: Progress information (e.g., {"step": "analyzing", "percent": 50})
        """
        self._progress_data.update(progress_data)

    def set_progress(self, progress_data: Dict[str, Any]) -> None:
        """
        Set progress data (replaces existing data)

        Args:
            progress_data: Progress information
        """
        self._progress_data = progress_data.copy()

    @contextmanager
    def supervised_execution(self, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager for supervised execution

        Handles:
        - Registration with supervisor
        - Starting heartbeat thread
        - Cleanup on completion or exception
        - Unregistration

        Usage:
            with self.supervised_execution(metadata={"task_id": "123"}):
                # Do work
                result = expensive_operation()
                return result

        Args:
            metadata: Optional metadata for registration
        """
        # Register with supervisor
        self._register_with_supervisor(metadata)

        # Start heartbeat thread
        self._start_heartbeat_thread()

        try:
            # Yield control to the with block
            yield

        finally:
            # Always cleanup, even if exception occurs
            self._stop_heartbeat_thread()
            self._unregister_from_supervisor()


class SupervisedStageMixin(SupervisedAgentMixin):
    """
    Specialized mixin for pipeline stages

    Provides stage-specific defaults and helpers
    """

    def __init__(
        self,
        supervisor: Optional[Any],
        stage_name: str,
        heartbeat_interval: int = 15
    ):
        """
        Initialize supervised stage

        Args:
            supervisor: SupervisorAgent instance
            stage_name: Name of the stage
            heartbeat_interval: Seconds between heartbeats
        """
        super().__init__(
            supervisor=supervisor,
            agent_name=stage_name,
            agent_type="stage",
            heartbeat_interval=heartbeat_interval
        )

    def execute_with_supervision(
        self,
        context: Dict[str, Any],
        execute_fn: callable
    ) -> Dict[str, Any]:
        """
        Execute stage with automatic supervision

        Args:
            context: Execution context
            execute_fn: Function that performs the actual work

        Returns:
            Result from execute_fn

        Usage:
            def execute(self, context):
                return self.execute_with_supervision(
                    context,
                    lambda: self._do_actual_work(context)
                )
        """
        metadata = {
            "task_id": context.get("card_id"),
            "stage": self.agent_name
        }

        with self.supervised_execution(metadata):
            return execute_fn()
