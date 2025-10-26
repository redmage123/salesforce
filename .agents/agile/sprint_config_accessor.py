#!/usr/bin/env python3
"""
Sprint Configuration Accessor - Hydra Integration

This module provides type-safe access to sprint workflow configuration
from Hydra's OmegaConf structure, eliminating magic numbers.

Usage:
    from sprint_config_accessor import SprintConfig

    config = SprintConfig.from_hydra(cfg)
    velocity = config.team_velocity
    risk_score = config.get_risk_score('high')
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from omegaconf import DictConfig


@dataclass(frozen=True)
class SprintPlanningConfig:
    """Type-safe access to sprint planning configuration"""

    team_velocity: float
    sprint_duration_days: int
    risk_scores: Dict[str, int]
    priority_weights: Dict[str, float]
    planning_poker_agents: List[str]
    fibonacci_scale: List[int]

    def get_risk_score(self, risk_level: str) -> int:
        """Get risk score for a given risk level (low/medium/high)"""
        return self.risk_scores.get(risk_level, self.risk_scores['medium'])

    def validate_weights(self) -> bool:
        """Validate that priority weights sum to 1.0"""
        total = sum(self.priority_weights.values())
        return abs(total - 1.0) < 0.001  # Allow small floating point error


@dataclass(frozen=True)
class ProjectReviewConfig:
    """Type-safe access to project review configuration"""

    review_weights: Dict[str, float]
    approval_threshold: float
    conditional_approval_threshold: float
    rejection_threshold: float
    max_iterations: int
    overcommitted_threshold: float
    underutilized_threshold: float
    max_sprint1_points: int

    def validate_weights(self) -> bool:
        """Validate that review weights sum to 1.0"""
        total = sum(self.review_weights.values())
        return abs(total - 1.0) < 0.001


@dataclass(frozen=True)
class UIUXEvaluationConfig:
    """Type-safe access to UI/UX evaluation configuration"""

    score_deductions: Dict[str, int]
    critical_accessibility_issues_threshold: int


@dataclass(frozen=True)
class RetrospectiveConfig:
    """Type-safe access to retrospective configuration"""

    health_weights: Dict[str, int]
    velocity_thresholds: Dict[str, float]
    test_quality_thresholds: Dict[str, float]
    health_score_thresholds: Dict[str, int]
    historical_sprints_to_analyze: int

    def validate_weights(self) -> bool:
        """Validate that health weights sum to 100"""
        return sum(self.health_weights.values()) == 100


class SprintConfig:
    """
    Facade for accessing all sprint workflow configuration

    Integrates with Hydra's OmegaConf to provide type-safe,
    validated access to configuration values.
    """

    def __init__(
        self,
        sprint_planning: SprintPlanningConfig,
        project_review: ProjectReviewConfig,
        uiux_evaluation: UIUXEvaluationConfig,
        retrospective: RetrospectiveConfig
    ):
        self.sprint_planning = sprint_planning
        self.project_review = project_review
        self.uiux_evaluation = uiux_evaluation
        self.retrospective = retrospective

    @classmethod
    def from_hydra(cls, cfg: DictConfig) -> 'SprintConfig':
        """
        Create SprintConfig from Hydra configuration

        Args:
            cfg: Hydra DictConfig object (from @hydra.main decorator)

        Returns:
            SprintConfig with all sprint workflow settings

        Example:
            @hydra.main(config_path="conf", config_name="config")
            def main(cfg: DictConfig):
                sprint_config = SprintConfig.from_hydra(cfg)
                print(f"Team velocity: {sprint_config.sprint_planning.team_velocity}")
        """
        # Extract sprint planning config
        sp_cfg = cfg.sprint_planning
        sprint_planning = SprintPlanningConfig(
            team_velocity=float(sp_cfg.team_velocity),
            sprint_duration_days=int(sp_cfg.sprint_duration_days),
            risk_scores=dict(sp_cfg.risk_scores),
            priority_weights=dict(sp_cfg.priority_weights),
            planning_poker_agents=list(sp_cfg.planning_poker.agents),
            fibonacci_scale=list(sp_cfg.planning_poker.fibonacci_scale)
        )

        # Validate weights
        if not sprint_planning.validate_weights():
            raise ValueError(
                f"Sprint planning priority weights must sum to 1.0, "
                f"got {sum(sprint_planning.priority_weights.values())}"
            )

        # Extract project review config
        pr_cfg = cfg.project_review
        project_review = ProjectReviewConfig(
            review_weights=dict(pr_cfg.review_weights),
            approval_threshold=float(pr_cfg.thresholds.approval),
            conditional_approval_threshold=float(pr_cfg.thresholds.conditional_approval),
            rejection_threshold=float(pr_cfg.thresholds.rejection),
            max_iterations=int(pr_cfg.max_iterations),
            overcommitted_threshold=float(pr_cfg.capacity.overcommitted_threshold),
            underutilized_threshold=float(pr_cfg.capacity.underutilized_threshold),
            max_sprint1_points=int(pr_cfg.capacity.max_sprint1_points)
        )

        if not project_review.validate_weights():
            raise ValueError(
                f"Project review weights must sum to 1.0, "
                f"got {sum(project_review.review_weights.values())}"
            )

        # Extract UI/UX evaluation config
        uiux_cfg = cfg.uiux_evaluation
        uiux_evaluation = UIUXEvaluationConfig(
            score_deductions=dict(uiux_cfg.score_deductions),
            critical_accessibility_issues_threshold=int(uiux_cfg.thresholds.critical_accessibility_issues)
        )

        # Extract retrospective config
        retro_cfg = cfg.retrospective
        retrospective = RetrospectiveConfig(
            health_weights=dict(retro_cfg.health_weights),
            velocity_thresholds=dict(retro_cfg.thresholds.velocity),
            test_quality_thresholds=dict(retro_cfg.thresholds.test_quality),
            health_score_thresholds=dict(retro_cfg.thresholds.health_score),
            historical_sprints_to_analyze=int(retro_cfg.historical_sprints_to_analyze)
        )

        if not retrospective.validate_weights():
            raise ValueError(
                f"Retrospective health weights must sum to 100, "
                f"got {sum(retrospective.health_weights.values())}"
            )

        return cls(sprint_planning, project_review, uiux_evaluation, retrospective)

    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'SprintConfig':
        """
        Create SprintConfig from dictionary (for testing)

        Args:
            config_dict: Dictionary with sprint configuration

        Returns:
            SprintConfig instance
        """
        sprint_planning = SprintPlanningConfig(
            team_velocity=config_dict['sprint_planning']['team_velocity'],
            sprint_duration_days=config_dict['sprint_planning']['sprint_duration_days'],
            risk_scores=config_dict['sprint_planning']['risk_scores'],
            priority_weights=config_dict['sprint_planning']['priority_weights'],
            planning_poker_agents=config_dict['sprint_planning']['planning_poker']['agents'],
            fibonacci_scale=config_dict['sprint_planning']['planning_poker']['fibonacci_scale']
        )

        project_review = ProjectReviewConfig(
            review_weights=config_dict['project_review']['review_weights'],
            approval_threshold=config_dict['project_review']['thresholds']['approval'],
            conditional_approval_threshold=config_dict['project_review']['thresholds']['conditional_approval'],
            rejection_threshold=config_dict['project_review']['thresholds']['rejection'],
            max_iterations=config_dict['project_review']['max_iterations'],
            overcommitted_threshold=config_dict['project_review']['capacity']['overcommitted_threshold'],
            underutilized_threshold=config_dict['project_review']['capacity']['underutilized_threshold'],
            max_sprint1_points=config_dict['project_review']['capacity']['max_sprint1_points']
        )

        uiux_evaluation = UIUXEvaluationConfig(
            score_deductions=config_dict['uiux_evaluation']['score_deductions'],
            critical_accessibility_issues_threshold=config_dict['uiux_evaluation']['thresholds']['critical_accessibility_issues']
        )

        retrospective = RetrospectiveConfig(
            health_weights=config_dict['retrospective']['health_weights'],
            velocity_thresholds=config_dict['retrospective']['thresholds']['velocity'],
            test_quality_thresholds=config_dict['retrospective']['thresholds']['test_quality'],
            health_score_thresholds=config_dict['retrospective']['thresholds']['health_score'],
            historical_sprints_to_analyze=config_dict['retrospective']['historical_sprints_to_analyze']
        )

        return cls(sprint_planning, project_review, uiux_evaluation, retrospective)
