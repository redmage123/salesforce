#!/usr/bin/env python3
"""
Circuit Breaker Pattern for Artemis

Prevents cascading failures by failing fast when a component is down.

Design Pattern: Circuit Breaker
Single Responsibility: Prevent cascading failures
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Any, Optional, TypeVar, Generic
from functools import wraps
import logging
from threading import Lock

from artemis_exceptions import PipelineStageError, wrap_exception


class CircuitBreakerOpenError(PipelineStageError):
    """Raised when circuit breaker is open (component is failing)"""
    pass


class CircuitState:
    """Circuit breaker states"""
    CLOSED = "closed"          # Normal operation, requests pass through
    OPEN = "open"              # Failing, reject all requests
    HALF_OPEN = "half_open"    # Testing if component recovered


@dataclass
class CircuitBreakerConfig:
    """
    Circuit breaker configuration

    Args:
        failure_threshold: Number of failures before opening circuit
        timeout_seconds: How long to wait before testing recovery
        half_open_attempts: Number of successful attempts needed to close circuit
        success_threshold: Number of successes needed to close from half-open
    """
    failure_threshold: int = 5
    timeout_seconds: int = 60
    half_open_attempts: int = 1
    success_threshold: int = 2


T = TypeVar('T')


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    States:
    - CLOSED: Normal operation, all requests go through
    - OPEN: Too many failures, reject all requests immediately
    - HALF_OPEN: Testing recovery, allow limited requests

    Usage:
        breaker = CircuitBreaker("rag_agent")

        @breaker.protect
        def query_rag(text):
            return rag.query(text)

        try:
            result = query_rag("test")
        except CircuitBreakerOpenError:
            # Use fallback
            result = use_fallback()

    Example with context manager:
        breaker = CircuitBreaker("api_call")

        with breaker:
            result = expensive_api_call()
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Name of the protected component
            config: Circuit breaker configuration
            logger: Logger instance
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.logger = logger or logging.getLogger(f"CircuitBreaker.{name}")

        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: Optional[datetime] = None

        # Thread safety
        self._lock = Lock()

    def protect(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to protect a function with circuit breaker.

        Args:
            func: Function to protect

        Returns:
            Wrapped function

        Example:
            @breaker.protect
            def risky_operation():
                return call_external_service()
        """
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return self.call(func, *args, **kwargs)
        return wrapper

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        with self._lock:
            # Check if we should reject the request
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.logger.info(f"Circuit breaker {self.name} entering HALF_OPEN state")
                    self.state = CircuitState.HALF_OPEN
                    self.last_state_change = datetime.now()
                else:
                    time_until_retry = self._time_until_retry()
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Retry in {time_until_retry:.1f} seconds.",
                        context={
                            "circuit_breaker": self.name,
                            "state": self.state,
                            "failure_count": self.failure_count,
                            "time_until_retry": time_until_retry
                        }
                    )

        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def _on_success(self):
        """Handle successful execution"""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                self.logger.info(
                    f"Circuit breaker {self.name} successful attempt "
                    f"({self.success_count}/{self.config.success_threshold})"
                )

                # Close circuit if enough successes
                if self.success_count >= self.config.success_threshold:
                    self.logger.info(f"Circuit breaker {self.name} closing (recovered)")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self.last_state_change = datetime.now()

            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0

    def _on_failure(self, exception: Exception):
        """Handle failed execution"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            self.logger.warning(
                f"Circuit breaker {self.name} failure "
                f"({self.failure_count}/{self.config.failure_threshold}): {exception}"
            )

            # Open circuit if too many failures
            if self.failure_count >= self.config.failure_threshold:
                self.logger.error(
                    f"Circuit breaker {self.name} opening due to {self.failure_count} failures"
                )
                self.state = CircuitState.OPEN
                self.last_state_change = datetime.now()
                self.success_count = 0

            # If in half-open, go back to open on any failure
            elif self.state == CircuitState.HALF_OPEN:
                self.logger.error(
                    f"Circuit breaker {self.name} returning to OPEN (half-open test failed)"
                )
                self.state = CircuitState.OPEN
                self.last_state_change = datetime.now()
                self.success_count = 0

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.last_failure_time:
            return True

        elapsed = datetime.now() - self.last_failure_time
        return elapsed >= timedelta(seconds=self.config.timeout_seconds)

    def _time_until_retry(self) -> float:
        """Calculate time until retry is allowed (in seconds)"""
        if not self.last_failure_time:
            return 0.0

        elapsed = datetime.now() - self.last_failure_time
        timeout = timedelta(seconds=self.config.timeout_seconds)
        remaining = timeout - elapsed

        return max(0.0, remaining.total_seconds())

    def reset(self):
        """Manually reset circuit breaker to closed state"""
        with self._lock:
            self.logger.info(f"Circuit breaker {self.name} manually reset")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.last_state_change = datetime.now()

    def get_status(self) -> dict:
        """Get circuit breaker status"""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
                "last_state_change": self.last_state_change.isoformat() if self.last_state_change else None,
                "time_until_retry": self._time_until_retry() if self.state == CircuitState.OPEN else 0.0
            }

    # Context manager support
    def __enter__(self):
        """Enter context - check if circuit is open"""
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.logger.info(f"Circuit breaker {self.name} entering HALF_OPEN state")
                    self.state = CircuitState.HALF_OPEN
                    self.last_state_change = datetime.now()
                else:
                    time_until_retry = self._time_until_retry()
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Retry in {time_until_retry:.1f} seconds.",
                        context={
                            "circuit_breaker": self.name,
                            "state": self.state,
                            "time_until_retry": time_until_retry
                        }
                    )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - record success or failure"""
        if exc_type is None:
            self._on_success()
        else:
            self._on_failure(exc_val)
        return False  # Don't suppress exceptions


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Usage:
        registry = CircuitBreakerRegistry()

        rag_breaker = registry.get_or_create("rag_agent")
        kg_breaker = registry.get_or_create("knowledge_graph")

        # Get all statuses
        statuses = registry.get_all_statuses()
    """

    def __init__(self):
        self.breakers: dict[str, CircuitBreaker] = {}
        self.logger = logging.getLogger("CircuitBreakerRegistry")
        self._lock = Lock()

    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Get existing circuit breaker or create new one.

        Args:
            name: Circuit breaker name
            config: Configuration (optional)

        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if name not in self.breakers:
                self.breakers[name] = CircuitBreaker(name, config)
                self.logger.info(f"Created circuit breaker: {name}")
            return self.breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self.breakers.get(name)

    def reset_all(self):
        """Reset all circuit breakers"""
        with self._lock:
            for breaker in self.breakers.values():
                breaker.reset()
            self.logger.info("Reset all circuit breakers")

    def get_all_statuses(self) -> dict[str, dict]:
        """Get status of all circuit breakers"""
        with self._lock:
            return {
                name: breaker.get_status()
                for name, breaker in self.breakers.items()
            }

    def get_open_breakers(self) -> list[str]:
        """Get names of all open circuit breakers"""
        with self._lock:
            return [
                name for name, breaker in self.breakers.items()
                if breaker.state == CircuitState.OPEN
            ]


# Global registry instance
_global_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """
    Get or create a circuit breaker from global registry.

    Args:
        name: Circuit breaker name
        config: Configuration (optional)

    Returns:
        CircuitBreaker instance

    Example:
        breaker = get_circuit_breaker("rag_agent")

        @breaker.protect
        def query_rag():
            return rag.query(...)
    """
    return _global_registry.get_or_create(name, config)


def get_all_circuit_breaker_statuses() -> dict[str, dict]:
    """Get status of all circuit breakers"""
    return _global_registry.get_all_statuses()


def reset_all_circuit_breakers():
    """Reset all circuit breakers to closed state"""
    _global_registry.reset_all()


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    import sys
    import time

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Circuit Breaker Demo")
    parser.add_argument("--demo", action="store_true", help="Run demo")
    parser.add_argument("--status", action="store_true", help="Show circuit breaker statuses")

    args = parser.parse_args()

    if args.demo:
        print("=" * 80)
        print("CIRCUIT BREAKER DEMO")
        print("=" * 80)

        # Create circuit breaker with low threshold for demo
        config = CircuitBreakerConfig(failure_threshold=3, timeout_seconds=5)
        breaker = CircuitBreaker("demo_service", config)

        # Simulate failing service
        class ServiceState:
            call_count = 0

        @breaker.protect
        def unreliable_service():
            ServiceState.call_count += 1

            # Fail first 3 calls
            if ServiceState.call_count <= 3:
                raise Exception(f"Service failed (call {ServiceState.call_count})")

            return f"Success (call {ServiceState.call_count})"

        # Make calls
        for i in range(10):
            try:
                result = unreliable_service()
                print(f"✅ Call {i+1}: {result}")
            except CircuitBreakerOpenError as e:
                print(f"⛔ Call {i+1}: Circuit breaker OPEN - {e}")
            except Exception as e:
                print(f"❌ Call {i+1}: Failed - {e}")

            time.sleep(0.5)

        print("\n" + "=" * 80)
        print("STATUS:")
        print("=" * 80)
        import json
        print(json.dumps(breaker.get_status(), indent=2))

    elif args.status:
        statuses = get_all_circuit_breaker_statuses()

        if not statuses:
            print("No circuit breakers registered")
        else:
            import json
            print(json.dumps(statuses, indent=2))

    else:
        parser.print_help()
