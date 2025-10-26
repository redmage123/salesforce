#!/usr/bin/env python3
"""
Artemis Centralized Logging System

Handles all logging for Artemis with:
- Centralized log directory (/var/log/artemis by default)
- Log rotation
- Multiple log levels
- Structured logging with timestamps
- Automatic directory creation with proper permissions
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional


class ArtemisLogger:
    """
    Centralized logging system for Artemis.

    All logs go to /var/log/artemis/ (configurable via ARTEMIS_LOG_DIR).
    Creates separate log files for different components:
    - artemis_main.log: Main pipeline execution
    - artemis_supervisor.log: Supervisor agent logs
    - artemis_developers.log: Developer agent logs
    - artemis_errors.log: Error-only log for monitoring
    """

    def __init__(
        self,
        component: str = "main",
        log_dir: Optional[str] = None,
        log_level: str = "INFO",
        max_bytes: int = 100 * 1024 * 1024,  # 100MB
        backup_count: int = 10
    ):
        """
        Initialize Artemis logger.

        Args:
            component: Component name (main, supervisor, developers, etc.)
            log_dir: Log directory path (default: /var/log/artemis or ARTEMIS_LOG_DIR)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_bytes: Max log file size before rotation
            backup_count: Number of rotated log files to keep
        """
        self.component = component

        # Get log directory from environment or default
        if log_dir is None:
            log_dir = os.getenv("ARTEMIS_LOG_DIR", "/var/log/artemis")

        self.log_dir = Path(log_dir)

        # Get log level from environment or parameter
        env_log_level = os.getenv("ARTEMIS_LOG_LEVEL", log_level)
        self.log_level = getattr(logging, env_log_level.upper(), logging.INFO)

        # Get rotation settings from environment
        env_max_size = os.getenv("ARTEMIS_LOG_MAX_SIZE_MB")
        if env_max_size:
            max_bytes = int(env_max_size) * 1024 * 1024

        env_backup = os.getenv("ARTEMIS_LOG_BACKUP_COUNT")
        if env_backup:
            backup_count = int(env_backup)

        self.max_bytes = max_bytes
        self.backup_count = backup_count

        # Create logger
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up the logger with file handlers and rotation"""
        # Create log directory with proper permissions
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            # Try to set permissions to 755 (rwxr-xr-x)
            os.chmod(self.log_dir, 0o755)
        except PermissionError:
            # If we can't create /var/log/artemis, fall back to /tmp
            print(f"WARNING: Cannot create {self.log_dir}, falling back to /tmp/artemis_logs", file=sys.stderr)
            self.log_dir = Path("/tmp/artemis_logs")
            self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create logger
        logger = logging.getLogger(f"artemis.{self.component}")
        logger.setLevel(self.log_level)

        # Remove existing handlers
        logger.handlers = []

        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Main log file (with rotation)
        main_log_file = self.log_dir / f"artemis_{self.component}.log"
        main_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        main_handler.setLevel(self.log_level)
        main_handler.setFormatter(detailed_formatter)
        logger.addHandler(main_handler)

        # Error-only log file (for monitoring)
        error_log_file = self.log_dir / "artemis_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        logger.addHandler(error_handler)

        # Console handler (for immediate feedback)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter(
            fmt='[%(levelname)s] %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        return logger

    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)

    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)

    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)

    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)

    def critical(self, message: str):
        """Log critical message"""
        self.logger.critical(message)

    def log(self, message: str, level: str = "INFO"):
        """
        Log message at specified level (for compatibility with existing code).

        Args:
            message: Message to log
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL, SUCCESS, STAGE)
        """
        # Map custom levels to standard ones
        level_map = {
            "SUCCESS": "INFO",
            "STAGE": "INFO",
            "WARNING": "WARNING",
            "ERROR": "ERROR",
            "CRITICAL": "CRITICAL",
            "DEBUG": "DEBUG"
        }

        standard_level = level_map.get(level.upper(), "INFO")

        if standard_level == "DEBUG":
            self.debug(message)
        elif standard_level == "INFO":
            self.info(message)
        elif standard_level == "WARNING":
            self.warning(message)
        elif standard_level == "ERROR":
            self.error(message)
        elif standard_level == "CRITICAL":
            self.critical(message)
        else:
            self.info(message)

    def get_log_path(self) -> Path:
        """Get the path to the main log file"""
        return self.log_dir / f"artemis_{self.component}.log"

    def get_error_log_path(self) -> Path:
        """Get the path to the error log file"""
        return self.log_dir / "artemis_errors.log"


# Global logger instance
_default_logger: Optional[ArtemisLogger] = None


def get_logger(component: str = "main") -> ArtemisLogger:
    """
    Get or create the global Artemis logger.

    Args:
        component: Component name for logging

    Returns:
        ArtemisLogger instance
    """
    global _default_logger
    if _default_logger is None or _default_logger.component != component:
        _default_logger = ArtemisLogger(component=component)
    return _default_logger


def setup_logging(component: str = "main", log_level: str = "INFO"):
    """
    Setup Artemis logging system.

    Args:
        component: Component name
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        ArtemisLogger instance
    """
    global _default_logger
    _default_logger = ArtemisLogger(component=component, log_level=log_level)
    return _default_logger


if __name__ == "__main__":
    # Test the logger
    logger = ArtemisLogger(component="test")

    logger.info("Testing Artemis logger")
    logger.debug("This is a debug message")
    logger.warning("This is a warning")
    logger.error("This is an error")

    print(f"\nLog file: {logger.get_log_path()}")
    print(f"Error log: {logger.get_error_log_path()}")
