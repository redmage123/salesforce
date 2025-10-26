#!/usr/bin/env python3
"""
Planning Poker - Agile Estimation Technique

Implements Planning Poker for story point estimation with AI agents.
Agents vote on story complexity using Fibonacci sequence, discuss outliers,
and converge on consensus estimates.

Single Responsibility: Coordinate multi-agent estimation voting

SOLID Principles:
- Single Responsibility: Only handles Planning Poker estimation
- Open/Closed: Extensible via strategy pattern
- Liskov Substitution: Works with any LLM client
- Interface Segregation: Minimal focused interface
- Dependency Inversion: Depends on abstractions

Design Patterns:
- Strategy Pattern: Different estimation strategies
- Observer Pattern: Event notifications for progress tracking
- Factory Pattern: LLM client creation
"""

import os
import json
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, asdict
from enum import Enum
from statistics import median, mean
from concurrent.futures import ThreadPoolExecutor, as_completed

from artemis_stage_interface import LoggerInterface
from llm_client import LLMClient
from pipeline_observer import PipelineEvent, EventType, PipelineObservable

# Conditional imports for type checking
if TYPE_CHECKING:
    from ai_query_service import AIQueryService


# ============================================================================
# CONFIGURATION CONSTANTS (replacing magic numbers)
# ============================================================================

class EstimationConfig:
    """Configuration constants for Planning Poker estimation"""
    HOURS_PER_SPRINT = 40  # Standard 40-hour work week
    HEARTBEAT_INTERVAL_MS = 10  # Observer update interval
    ROUND_PENALTY_FACTOR = 0.1  # Confidence penalty per additional round
    FORCED_CONSENSUS_PENALTY = 0.2  # Confidence penalty for forced consensus
    HIGH_RISK_POINTS_THRESHOLD = 13  # Story points triggering high risk
    MEDIUM_RISK_POINTS_THRESHOLD = 8  # Story points triggering medium risk
    HIGH_RISK_CONFIDENCE_THRESHOLD = 0.6  # Confidence below this = high risk
    MEDIUM_RISK_CONFIDENCE_THRESHOLD = 0.7  # Confidence below this = medium risk
    DEFAULT_CONFIDENCE = 0.5  # Default confidence on error
    ERROR_VOTE_POINTS = 5  # Default story points when estimation fails


class FibonacciScale(Enum):
    """Fibonacci scale for story points"""
    TINY = 1
    SMALL = 2
    MEDIUM = 3
    LARGE = 5
    HUGE = 8
    ENORMOUS = 13
    EPIC = 21
    UNKNOWN = 100  # Too complex to estimate


@dataclass
class EstimationVote:
    """Single agent's estimation vote"""
    agent_name: str
    story_points: int
    reasoning: str
    confidence: float  # 0.0 to 1.0
    concerns: List[str]


@dataclass
class EstimationRound:
    """Single round of Planning Poker"""
    round_number: int
    votes: List[EstimationVote]
    consensus_reached: bool
    final_estimate: Optional[int]
    discussion_summary: str


@dataclass
class FeatureEstimate:
    """Complete estimation for a feature"""
    feature_title: str
    feature_description: str
    rounds: List[EstimationRound]
    final_estimate: int
    confidence: float
    risk_level: str  # "low", "medium", "high"
    estimated_hours: float  # Based on team velocity


class PlanningPoker:
    """
    Planning Poker implementation for AI agent teams

    Simulates Scrum Planning Poker with AI agents voting on story complexity.
    Agents discuss outliers and converge on consensus estimates.

    Integrations:
    - Observer Pattern: Broadcasts estimation events (started, voting, consensus, failed)
    - AI Query Service: Uses KG-First approach for estimation context
    - Parallel Execution: Concurrent agent voting for 3x speedup
    """

    def __init__(
        self,
        agents: List[str],
        llm_client: LLMClient,
        logger: LoggerInterface,
        team_velocity: float = 20.0,  # Story points per sprint
        max_rounds: int = 3,
        observable: Optional[PipelineObservable] = None,
        ai_service: Optional['AIQueryService'] = None
    ):
        """
        Initialize Planning Poker

        Args:
            agents: List of agent names participating (e.g., ["architect", "developer", "qa"])
            llm_client: LLM client for generating votes
            logger: Logger interface
            team_velocity: Team's average story points per sprint
            max_rounds: Maximum voting rounds before forcing consensus
            observable: Optional PipelineObservable for event broadcasting
            ai_service: Optional AIQueryService for KG-First optimization
        """
        self.agents = agents
        self.llm_client = llm_client
        self.logger = logger
        self.team_velocity = team_velocity
        self.max_rounds = max_rounds
        self.observable = observable
        self.ai_service = ai_service

        # Fibonacci values for voting (list comprehension instead of loop)
        self.fibonacci_values = [v.value for v in FibonacciScale]

        # Event broadcasting helper
        self._notify_event(EventType.STAGE_PROGRESS, {
            "message": "Planning Poker initialized",
            "agents": agents,
            "max_rounds": max_rounds
        })

    def _notify_event(self, event_type: EventType, data: Dict) -> None:
        """
        Notify observers of estimation event

        Args:
            event_type: Type of event
            data: Event data
        """
        if self.observable:
            event = PipelineEvent(
                event_type=event_type,
                stage_name="planning_poker",
                data=data
            )
            self.observable.notify(event)

    def estimate_feature(
        self,
        feature_title: str,
        feature_description: str,
        acceptance_criteria: List[str]
    ) -> FeatureEstimate:
        """
        Run Planning Poker to estimate a feature

        Args:
            feature_title: Feature name
            feature_description: Detailed description
            acceptance_criteria: List of acceptance criteria

        Returns:
            FeatureEstimate with consensus story points
        """
        self.logger.log(f"🎯 Planning Poker: Estimating '{feature_title}'", "INFO")

        # Notify observers: estimation started
        self._notify_event(EventType.STAGE_STARTED, {
            "feature_title": feature_title,
            "feature_description": feature_description,
            "acceptance_criteria_count": len(acceptance_criteria)
        })

        rounds = []
        consensus_reached = False
        final_estimate = None

        for round_num in range(1, self.max_rounds + 1):
            self.logger.log(f"📊 Round {round_num} of {self.max_rounds}", "INFO")

            # Collect votes from all agents
            votes = self._collect_votes(
                feature_title,
                feature_description,
                acceptance_criteria,
                round_num,
                previous_votes=rounds[-1].votes if rounds else None
            )

            # Check for consensus
            consensus, estimate = self._check_consensus(votes)

            # Create discussion if no consensus
            discussion = ""
            if not consensus and round_num < self.max_rounds:
                discussion = self._generate_discussion(votes)
                self.logger.log(f"💬 Discussion: {discussion}", "INFO")
            elif consensus:
                self.logger.log(f"✅ Consensus reached: {estimate} story points", "SUCCESS")

            # Store round
            round_data = EstimationRound(
                round_number=round_num,
                votes=votes,
                consensus_reached=consensus,
                final_estimate=estimate if consensus else None,
                discussion_summary=discussion
            )
            rounds.append(round_data)

            # Break if consensus reached
            if consensus:
                consensus_reached = True
                final_estimate = estimate
                break

        # Force consensus if max rounds reached
        if not consensus_reached:
            final_estimate = self._force_consensus(rounds[-1].votes)
            rounds[-1].consensus_reached = True
            rounds[-1].final_estimate = final_estimate
            self.logger.log(
                f"⚡ Forced consensus after {self.max_rounds} rounds: {final_estimate} points",
                "WARNING"
            )

        # Calculate confidence and risk
        confidence = self._calculate_confidence(rounds)
        risk_level = self._assess_risk(final_estimate, confidence)

        # Estimate hours based on team velocity (using constant)
        estimated_hours = (final_estimate / self.team_velocity) * EstimationConfig.HOURS_PER_SPRINT

        # Notify observers: estimation completed
        self._notify_event(EventType.STAGE_COMPLETED, {
            "feature_title": feature_title,
            "final_estimate": final_estimate,
            "confidence": confidence,
            "risk_level": risk_level,
            "estimated_hours": estimated_hours,
            "rounds_needed": len(rounds)
        })

        return FeatureEstimate(
            feature_title=feature_title,
            feature_description=feature_description,
            rounds=rounds,
            final_estimate=final_estimate,
            confidence=confidence,
            risk_level=risk_level,
            estimated_hours=estimated_hours
        )

    def _collect_votes(
        self,
        feature_title: str,
        feature_description: str,
        acceptance_criteria: List[str],
        round_num: int,
        previous_votes: Optional[List[EstimationVote]] = None
    ) -> List[EstimationVote]:
        """Collect estimation votes from all agents (in parallel for speed)"""
        votes = []

        # Parallelize LLM calls for 3x speedup
        with ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
            # Submit all votes concurrently
            future_to_agent = {
                executor.submit(
                    self._agent_vote,
                    agent_name,
                    feature_title,
                    feature_description,
                    acceptance_criteria,
                    round_num,
                    previous_votes
                ): agent_name
                for agent_name in self.agents
            }

            # Collect results as they complete
            for future in as_completed(future_to_agent):
                agent_name = future_to_agent[future]
                try:
                    vote = future.result()
                    votes.append(vote)
                    self.logger.log(
                        f"  {agent_name}: {vote.story_points} points (confidence: {vote.confidence:.0%})",
                        "INFO"
                    )
                except Exception as e:
                    self.logger.log(f"Error getting vote from {agent_name}: {e}", "ERROR")
                    # Notify observers of vote failure
                    self._notify_event(EventType.STAGE_FAILED, {
                        "agent_name": agent_name,
                        "error": str(e),
                        "fallback": "using_default_vote"
                    })
                    # Add default vote on error (using constants)
                    votes.append(EstimationVote(
                        agent_name=agent_name,
                        story_points=EstimationConfig.ERROR_VOTE_POINTS,
                        reasoning="Error occurred during estimation",
                        confidence=0.0,
                        concerns=["Estimation failed"]
                    ))

        # Sort votes by agent name for consistent ordering
        votes.sort(key=lambda v: v.agent_name)
        return votes

    def _agent_vote(
        self,
        agent_name: str,
        feature_title: str,
        feature_description: str,
        acceptance_criteria: List[str],
        round_num: int,
        previous_votes: Optional[List[EstimationVote]] = None
    ) -> EstimationVote:
        """Get a single agent's vote using LLM"""

        # Build prompt using comprehensions (no manual loops)
        criteria_text = "\n".join(f"- {c}" for c in acceptance_criteria)

        previous_context = ""
        if previous_votes and round_num > 1:
            votes_summary = ", ".join(
                f"{v.agent_name}: {v.story_points}" for v in previous_votes
            )
            previous_context = f"\n\nPrevious round votes: {votes_summary}\nPlease consider these votes and adjust if needed."

        prompt = f"""You are {agent_name} participating in Planning Poker estimation.

Feature: {feature_title}
Description: {feature_description}

Acceptance Criteria:
{criteria_text}

Vote using Fibonacci sequence: 1, 2, 3, 5, 8, 13, 21, 100 (100 = too complex)

Consider:
- Technical complexity
- Unknown dependencies
- Testing requirements
- Integration points
{previous_context}

Respond in JSON format:
{{
    "story_points": <number from Fibonacci sequence>,
    "reasoning": "<brief explanation>",
    "confidence": <0.0 to 1.0>,
    "concerns": ["<concern 1>", "<concern 2>"]
}}
"""

        # Get LLM response
        try:
            from llm_client import LLMMessage

            messages = [
                LLMMessage(role="system", content=f"You are a {agent_name} agent providing technical estimates."),
                LLMMessage(role="user", content=prompt)
            ]

            llm_response = self.llm_client.complete(
                messages=messages,
                response_format={"type": "json_object"}
            )

            data = json.loads(llm_response.content)

            return EstimationVote(
                agent_name=agent_name,
                story_points=int(data.get("story_points", 5)),
                reasoning=data.get("reasoning", "No reasoning provided"),
                confidence=float(data.get("confidence", 0.5)),
                concerns=data.get("concerns", [])
            )

        except Exception as e:
            self.logger.log(f"Error getting vote from {agent_name}: {e}", "ERROR")
            # Default vote (using constants)
            return EstimationVote(
                agent_name=agent_name,
                story_points=EstimationConfig.ERROR_VOTE_POINTS,
                reasoning=f"Default vote (error: {e})",
                confidence=EstimationConfig.DEFAULT_CONFIDENCE,
                concerns=["Unable to properly estimate"]
            )

    def _check_consensus(self, votes: List[EstimationVote]) -> Tuple[bool, Optional[int]]:
        """
        Check if consensus reached

        Consensus rules:
        - All votes within 1 Fibonacci step = consensus
        - Median vote is the consensus value
        """
        if not votes:
            return False, None

        # Get all vote values
        values = [v.story_points for v in votes]

        # Find median
        median_value = int(median(values))

        # Check if all values are within 1 Fibonacci step of median
        fibonacci_index = {v.value: i for i, v in enumerate(FibonacciScale)}
        median_idx = fibonacci_index.get(median_value, 0)

        # Use all() with generator expression for cleaner logic
        consensus = all(
            abs(fibonacci_index.get(value, 0) - median_idx) <= 1
            for value in values
        )

        return consensus, median_value if consensus else None

    def _generate_discussion(self, votes: List[EstimationVote]) -> str:
        """Generate discussion summary for outlier votes using comprehensions"""
        # Find highest and lowest votes
        sorted_votes = sorted(votes, key=lambda v: v.story_points)
        lowest = sorted_votes[0]
        highest = sorted_votes[-1]

        # Collect all concerns using nested comprehension (flattening list of lists)
        all_concerns = ', '.join(set(
            concern
            for vote in votes
            for concern in vote.concerns
        ))

        discussion = f"""
Why the spread?
- {lowest.agent_name} (lowest): {lowest.reasoning}
- {highest.agent_name} (highest): {highest.reasoning}

Key concerns: {all_concerns}
"""
        return discussion.strip()

    def _force_consensus(self, votes: List[EstimationVote]) -> int:
        """Force consensus using weighted average based on confidence"""
        if not votes:
            return EstimationConfig.ERROR_VOTE_POINTS  # Use constant instead of magic number

        # Weighted average by confidence (using comprehensions)
        total_weight = sum(v.confidence for v in votes)
        if total_weight == 0:
            return int(median(v.story_points for v in votes))

        weighted_sum = sum(v.story_points * v.confidence for v in votes)
        weighted_avg = weighted_sum / total_weight

        # Round to nearest Fibonacci number (excluding UNKNOWN)
        fibonacci_vals = [1, 2, 3, 5, 8, 13, 21]
        nearest = min(fibonacci_vals, key=lambda x: abs(x - weighted_avg))

        return nearest

    def _calculate_confidence(self, rounds: List[EstimationRound]) -> float:
        """Calculate overall confidence in estimate using configuration constants"""
        if not rounds:
            return 0.0

        # Start with average agent confidence (comprehension)
        last_round = rounds[-1]
        avg_confidence = mean(v.confidence for v in last_round.votes)

        # Penalize if many rounds needed (using constant)
        round_penalty = EstimationConfig.ROUND_PENALTY_FACTOR * (len(rounds) - 1)

        # Penalize if forced consensus (using constant)
        forced_penalty = EstimationConfig.FORCED_CONSENSUS_PENALTY if not last_round.consensus_reached else 0.0

        final_confidence = max(0.0, avg_confidence - round_penalty - forced_penalty)

        return final_confidence

    def _assess_risk(self, story_points: int, confidence: float) -> str:
        """
        Assess risk level based on estimate and confidence using configuration constants

        Uses a functional approach with a list of risk rules evaluated in priority order
        """
        # Define risk rules as (condition_function, risk_level) tuples
        # Evaluated in order, first match wins
        risk_rules = [
            (
                lambda sp, conf: sp >= EstimationConfig.HIGH_RISK_POINTS_THRESHOLD and
                                 conf < EstimationConfig.HIGH_RISK_CONFIDENCE_THRESHOLD,
                "high"
            ),
            (
                lambda sp, conf: sp >= EstimationConfig.MEDIUM_RISK_POINTS_THRESHOLD and
                                 conf < EstimationConfig.MEDIUM_RISK_CONFIDENCE_THRESHOLD,
                "medium"
            ),
            (
                lambda sp, conf: sp >= EstimationConfig.HIGH_RISK_POINTS_THRESHOLD,
                "medium"
            ),
            (lambda sp, conf: True, "low")  # Default case
        ]

        # Find first matching rule using next() with generator expression
        return next(
            risk_level
            for condition, risk_level in risk_rules
            if condition(story_points, confidence)
        )


def estimate_features_batch(
    features: List[Dict],
    poker: PlanningPoker,
    logger: LoggerInterface
) -> List[FeatureEstimate]:
    """
    Estimate multiple features using Planning Poker

    Args:
        features: List of feature dicts with title, description, acceptance_criteria
        poker: PlanningPoker instance
        logger: Logger

    Returns:
        List of FeatureEstimate objects
    """
    estimates = []

    for i, feature in enumerate(features, 1):
        logger.log(f"\n{'='*60}", "INFO")
        logger.log(f"Feature {i}/{len(features)}", "INFO")
        logger.log(f"{'='*60}", "INFO")

        estimate = poker.estimate_feature(
            feature_title=feature.get("title", "Unknown Feature"),
            feature_description=feature.get("description", ""),
            acceptance_criteria=feature.get("acceptance_criteria", [])
        )

        estimates.append(estimate)

        logger.log(
            f"✅ Estimated: {estimate.final_estimate} points "
            f"(confidence: {estimate.confidence:.0%}, risk: {estimate.risk_level})",
            "SUCCESS"
        )

    return estimates
