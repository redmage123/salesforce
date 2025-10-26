#!/usr/bin/env python3
"""
Sprint Models - Value Objects and Domain Logic

Provides immutable, type-safe value objects for sprint workflow:
- Feature, PrioritizedFeature
- Sprint
- Clock abstraction for testability
- SprintScheduler, SprintAllocator

Design Patterns:
- Value Object: Immutable, validated objects
- Strategy Pattern: Pluggable scheduling algorithms
- Dependency Injection: Clock interface for testing
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Protocol, Any
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class RiskLevel(Enum):
    """Feature risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================================================
# Clock Abstraction (Dependency Injection for Time)
# ============================================================================

class Clock(Protocol):
    """
    Abstract clock interface for dependency injection

    Allows testing with frozen time instead of system time.
    """
    def now(self) -> datetime:
        """Return current datetime"""
        ...


class SystemClock:
    """Production clock using actual system time"""

    def now(self) -> datetime:
        return datetime.now()


class FrozenClock:
    """Test clock with fixed time (for deterministic tests)"""

    def __init__(self, frozen_time: datetime):
        self.frozen_time = frozen_time

    def now(self) -> datetime:
        return self.frozen_time


# ============================================================================
# Value Objects
# ============================================================================

@dataclass(frozen=True)
class Feature:
    """
    Immutable feature representation (Value Object pattern)

    Validates business rules at construction time:
    - Business value must be 1-10
    - Title cannot be empty
    - Must have acceptance criteria
    """
    title: str
    description: str
    business_value: int  # 1-10 scale
    acceptance_criteria: List[str]

    def __post_init__(self):
        """Validate invariants"""
        if not 1 <= self.business_value <= 10:
            raise ValueError(
                f"Business value must be 1-10, got {self.business_value}"
            )

        if not self.title or not self.title.strip():
            raise ValueError("Feature title cannot be empty")

        if not self.acceptance_criteria:
            raise ValueError("Feature must have acceptance criteria")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'title': self.title,
            'description': self.description,
            'business_value': self.business_value,
            'acceptance_criteria': list(self.acceptance_criteria)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Feature':
        """Create Feature from dictionary"""
        return cls(
            title=data['title'],
            description=data['description'],
            business_value=data['business_value'],
            acceptance_criteria=data['acceptance_criteria']
        )


@dataclass(frozen=True)
class PrioritizedFeature:
    """
    Feature with estimation and prioritization data

    Composition pattern: Contains a Feature and adds estimation data
    """
    feature: Feature
    story_points: int
    estimated_hours: float
    risk_level: RiskLevel
    confidence: float  # 0.0-1.0
    priority_score: float

    @property
    def title(self) -> str:
        """Delegate to wrapped feature"""
        return self.feature.title

    @property
    def description(self) -> str:
        return self.feature.description

    @property
    def business_value(self) -> int:
        return self.feature.business_value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            **self.feature.to_dict(),
            'story_points': self.story_points,
            'estimated_hours': self.estimated_hours,
            'risk_level': self.risk_level.value,
            'confidence': self.confidence,
            'priority_score': self.priority_score
        }


@dataclass(frozen=True)
class Sprint:
    """
    Immutable sprint representation (Value Object pattern)

    Contains sprint metadata, allocated features, and calculated metrics.
    """
    sprint_number: int
    start_date: datetime
    end_date: datetime
    features: List[PrioritizedFeature]
    total_story_points: int
    capacity_used: float  # 0.0-1.0

    @property
    def is_over_capacity(self) -> bool:
        """Check if sprint is over-committed (>95% capacity)"""
        return self.capacity_used > 0.95

    @property
    def is_under_utilized(self) -> bool:
        """Check if sprint is under-utilized (<70% capacity)"""
        return self.capacity_used < 0.70

    @property
    def duration_days(self) -> int:
        """Calculate sprint duration in days"""
        return (self.end_date - self.start_date).days

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'sprint_number': self.sprint_number,
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d'),
            'features': [f.to_dict() for f in self.features],
            'total_story_points': self.total_story_points,
            'capacity_used': self.capacity_used
        }


# ============================================================================
# Sprint Scheduling Logic
# ============================================================================

class SprintScheduler:
    """
    Single Responsibility: Calculate sprint dates

    Uses Clock abstraction for testability.
    Can be extended with different scheduling strategies.
    """

    def __init__(self, sprint_duration_days: int = 14, clock: Clock = None):
        """
        Initialize sprint scheduler

        Args:
            sprint_duration_days: Length of each sprint
            clock: Clock implementation (defaults to SystemClock)
        """
        self.sprint_duration_days = sprint_duration_days
        self.clock = clock or SystemClock()

    def calculate_sprint_dates(
        self,
        sprint_number: int,
        base_date: datetime = None
    ) -> tuple[datetime, datetime]:
        """
        Calculate start and end dates for a sprint

        Args:
            sprint_number: Sprint number (1-indexed)
            base_date: Base date for calculations (defaults to now)

        Returns:
            Tuple of (start_date, end_date)
        """
        if base_date is None:
            base_date = self.clock.now()

        # Calculate offset from base date
        days_offset = self.sprint_duration_days * (sprint_number - 1)
        start_date = base_date + timedelta(days=days_offset)
        end_date = start_date + timedelta(days=self.sprint_duration_days)

        return start_date, end_date


class SprintAllocator:
    """
    Single Responsibility: Allocate features to sprints

    Uses greedy bin-packing algorithm to fill sprints based on team velocity.
    """

    def __init__(self, team_velocity: float, scheduler: SprintScheduler):
        """
        Initialize sprint allocator

        Args:
            team_velocity: Team's story points per sprint capacity
            scheduler: SprintScheduler for date calculations
        """
        self.team_velocity = team_velocity
        self.scheduler = scheduler

    def allocate_features_to_sprints(
        self,
        prioritized_features: List[PrioritizedFeature]
    ) -> List[Sprint]:
        """
        Allocate features to sprints using greedy bin-packing

        Features are allocated in priority order, filling each sprint
        until capacity is reached, then starting a new sprint.

        Args:
            prioritized_features: Features sorted by priority (highest first)

        Returns:
            List of Sprint objects with allocated features
        """
        sprints = []
        current_sprint_features = []
        current_story_points = 0
        sprint_number = 1

        for feature in prioritized_features:
            feature_points = feature.story_points

            # Check if feature fits in current sprint
            if current_story_points + feature_points <= self.team_velocity:
                # Add to current sprint
                current_sprint_features.append(feature)
                current_story_points += feature_points
            else:
                # Current sprint is full, finalize it
                if current_sprint_features:
                    sprint = self._create_sprint(
                        sprint_number,
                        current_sprint_features,
                        current_story_points
                    )
                    sprints.append(sprint)
                    sprint_number += 1

                # Start new sprint with this feature
                current_sprint_features = [feature]
                current_story_points = feature_points

        # Add final sprint if it has features
        if current_sprint_features:
            sprint = self._create_sprint(
                sprint_number,
                current_sprint_features,
                current_story_points
            )
            sprints.append(sprint)

        return sprints

    def _create_sprint(
        self,
        sprint_number: int,
        features: List[PrioritizedFeature],
        total_story_points: int
    ) -> Sprint:
        """
        Create a Sprint object with calculated dates and metrics

        Args:
            sprint_number: Sprint number
            features: List of allocated features
            total_story_points: Sum of story points

        Returns:
            Immutable Sprint object
        """
        start_date, end_date = self.scheduler.calculate_sprint_dates(sprint_number)
        capacity_used = total_story_points / self.team_velocity

        return Sprint(
            sprint_number=sprint_number,
            start_date=start_date,
            end_date=end_date,
            features=features,
            total_story_points=total_story_points,
            capacity_used=capacity_used
        )


# ============================================================================
# Factory Functions
# ============================================================================

def create_prioritized_feature(
    feature: Feature,
    estimate,  # FeatureEstimate from planning_poker
    config  # SprintPlanningConfig from sprint_config_accessor
) -> PrioritizedFeature:
    """
    Factory function to create prioritized feature from estimate

    Encapsulates priority calculation logic.

    Args:
        feature: Base feature
        estimate: FeatureEstimate from Planning Poker
        config: SprintPlanningConfig with weights

    Returns:
        PrioritizedFeature with calculated priority
    """
    # Get risk score from config
    risk_score = config.get_risk_score(estimate.risk_level)

    # Calculate priority score using weights from config
    priority_score = (
        feature.business_value * config.priority_weights['business_value'] -
        estimate.final_estimate * config.priority_weights['story_points'] -
        risk_score * config.priority_weights['risk']
    )

    return PrioritizedFeature(
        feature=feature,
        story_points=estimate.final_estimate,
        estimated_hours=estimate.estimated_hours,
        risk_level=RiskLevel(estimate.risk_level),
        confidence=estimate.confidence,
        priority_score=priority_score
    )
