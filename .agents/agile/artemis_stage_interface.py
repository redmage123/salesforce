#!/usr/bin/env python3
"""
Artemis Stage Interfaces (SOLID: Interface Segregation + Dependency Inversion)

Defines abstract base classes for all Artemis pipeline stages to ensure
consistent contracts and enable dependency injection.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional


class PipelineStage(ABC):
    """
    Abstract base class for all pipeline stages

    Following SOLID principles:
    - Single Responsibility: Each stage does ONE thing
    - Open/Closed: Can add new stages without modifying existing code
    - Liskov Substitution: All stages can be used interchangeably where PipelineStage is expected
    - Dependency Inversion: Orchestrator depends on this abstraction, not concrete stages
    """

    @abstractmethod
    def execute(self, card: Dict, context: Dict) -> Dict:
        """
        Execute this pipeline stage

        Args:
            card: Kanban card with task details
            context: Shared context from previous stages

        Returns:
            Dict with stage results to add to context
        """
        pass

    @abstractmethod
    def get_stage_name(self) -> str:
        """Return the name of this stage"""
        pass


class TestRunnerInterface(ABC):
    """Interface for running tests (ISP: Focused interface)"""

    @abstractmethod
    def run_tests(self, test_path: str) -> Dict:
        """Run tests and return results"""
        pass


class ValidatorInterface(ABC):
    """Interface for validators (ISP: Focused interface)"""

    @abstractmethod
    def validate(self, target) -> Dict:
        """Validate target and return results"""
        pass


class LoggerInterface(ABC):
    """Interface for logging (ISP: Focused interface)"""

    @abstractmethod
    def log(self, message: str, level: str = "INFO"):
        """Log a message"""
        pass
