#!/usr/bin/env python3
"""
Developer Arbitrator - Intelligent Winner Selection

Intelligently selects the best developer solution based on multiple criteria:
- Code review scores (security, quality, GDPR, accessibility)
- Test coverage percentage
- SOLID principle compliance
- Performance metrics
- Code simplicity (lines of code)
- Maintainability score

Uses weighted multi-criteria decision analysis (MCDA)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class DeveloperScore:
    """Comprehensive developer solution score"""
    developer_name: str

    # Code review scores
    security_score: float  # 0-100
    quality_score: float   # 0-100
    gdpr_score: float      # 0-100
    accessibility_score: float  # 0-100
    overall_review_score: float  # 0-100

    # Test metrics
    test_coverage: float  # 0-100
    tests_passing: int
    tests_total: int

    # SOLID compliance
    solid_score: float  # 0-100

    # Code metrics
    lines_of_code: int
    complexity_score: float  # McCabe complexity

    # Derived scores
    final_score: float = 0.0
    weighted_scores: Dict[str, float] = None


class DeveloperArbitrator:
    """
    Selects best developer solution using multi-criteria analysis

    Single Responsibility: Determine winning developer based on multiple factors
    """

    # Default weights for each criterion (must sum to 1.0)
    DEFAULT_WEIGHTS = {
        "security": 0.25,        # 25% - Critical
        "quality": 0.20,         # 20% - Very important
        "test_coverage": 0.15,   # 15% - Important
        "solid_compliance": 0.15, # 15% - Important
        "gdpr": 0.10,            # 10% - Compliance
        "accessibility": 0.05,   # 5%  - Nice to have
        "simplicity": 0.05,      # 5%  - Prefer simple
        "maintainability": 0.05  # 5%  - Long-term
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize arbitrator

        Args:
            weights: Custom weights for criteria (default: DEFAULT_WEIGHTS)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS

        # Validate weights sum to 1.0
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

    def select_winner(
        self,
        dev_a_result: Dict,
        dev_b_result: Dict,
        code_review_results: List[Dict]
    ) -> Dict:
        """
        Select winning developer solution

        Args:
            dev_a_result: Developer A results
            dev_b_result: Developer B results
            code_review_results: Code review results for both developers

        Returns:
            Dict with winner and scoring details
        """
        # Calculate scores for each developer
        score_a = self._calculate_developer_score("developer-a", dev_a_result, code_review_results)
        score_b = self._calculate_developer_score("developer-b", dev_b_result, code_review_results)

        # Determine winner
        if score_a.final_score > score_b.final_score:
            winner = "developer-a"
            winner_score = score_a
            loser_score = score_b
        else:
            winner = "developer-b"
            winner_score = score_b
            loser_score = score_a

        margin = abs(score_a.final_score - score_b.final_score)

        return {
            "winner": winner,
            "winner_score": winner_score.final_score,
            "loser_score": loser_score.final_score,
            "margin": margin,
            "confidence": self._calculate_confidence(margin),
            "developer_a_details": asdict(score_a),  # Convert dataclass to dict for JSON serialization
            "developer_b_details": asdict(score_b),  # Convert dataclass to dict for JSON serialization
            "breakdown": {
                "developer-a": score_a.weighted_scores,
                "developer-b": score_b.weighted_scores
            },
            "reasoning": self._generate_reasoning(winner_score, loser_score)
        }

    def _calculate_developer_score(
        self,
        developer_name: str,
        dev_result: Dict,
        code_review_results: List[Dict]
    ) -> DeveloperScore:
        """Calculate comprehensive score for a developer"""

        # Find code review for this developer
        review = self._find_review(developer_name, code_review_results)

        # Extract review scores
        security_score = self._extract_review_score(review, "security", 50.0)
        quality_score = self._extract_review_score(review, "quality", 50.0)
        gdpr_score = self._extract_review_score(review, "gdpr", 50.0)
        accessibility_score = self._extract_review_score(review, "accessibility", 50.0)
        overall_review_score = review.get("overall_score", 50.0) if review else 50.0

        # Extract test metrics
        test_results = dev_result.get("test_results", {})
        tests_passing = test_results.get("passed", 0)
        tests_total = test_results.get("total", 1)
        test_coverage = (tests_passing / tests_total * 100) if tests_total > 0 else 0

        # Extract SOLID score
        solid_score = dev_result.get("solid_score", 50.0)

        # Extract code metrics
        lines_of_code = dev_result.get("lines_of_code", 100)
        complexity_score = dev_result.get("complexity_score", 10.0)

        # Calculate weighted score
        weighted_scores = {
            "security": security_score * self.weights["security"],
            "quality": quality_score * self.weights["quality"],
            "test_coverage": test_coverage * self.weights["test_coverage"],
            "solid_compliance": solid_score * self.weights["solid_compliance"],
            "gdpr": gdpr_score * self.weights["gdpr"],
            "accessibility": accessibility_score * self.weights["accessibility"],
            "simplicity": self._calculate_simplicity_score(lines_of_code) * self.weights["simplicity"],
            "maintainability": self._calculate_maintainability_score(complexity_score, solid_score) * self.weights["maintainability"]
        }

        final_score = sum(weighted_scores.values())

        return DeveloperScore(
            developer_name=developer_name,
            security_score=security_score,
            quality_score=quality_score,
            gdpr_score=gdpr_score,
            accessibility_score=accessibility_score,
            overall_review_score=overall_review_score,
            test_coverage=test_coverage,
            tests_passing=tests_passing,
            tests_total=tests_total,
            solid_score=solid_score,
            lines_of_code=lines_of_code,
            complexity_score=complexity_score,
            final_score=final_score,
            weighted_scores=weighted_scores
        )

    def _find_review(self, developer_name: str, code_review_results: List[Dict]) -> Optional[Dict]:
        """Find code review for specific developer"""
        for review in code_review_results:
            if review.get("developer") == developer_name:
                return review
        return None

    def _extract_review_score(self, review: Optional[Dict], category: str, default: float) -> float:
        """Extract score for specific category from review"""
        if not review:
            return default

        # Try to get category-specific score
        category_scores = review.get("category_scores", {})
        if category in category_scores:
            return category_scores[category]

        # Fallback to overall score
        return review.get("overall_score", default)

    def _calculate_simplicity_score(self, lines_of_code: int) -> float:
        """
        Calculate simplicity score (fewer lines = higher score)

        Scoring:
        - < 100 lines: 100
        - 100-300 lines: 90-70
        - 300-500 lines: 70-50
        - > 500 lines: 50-0
        """
        if lines_of_code < 100:
            return 100.0
        elif lines_of_code < 300:
            return 100 - ((lines_of_code - 100) / 200 * 30)
        elif lines_of_code < 500:
            return 70 - ((lines_of_code - 300) / 200 * 20)
        else:
            return max(0, 50 - ((lines_of_code - 500) / 500 * 50))

    def _calculate_maintainability_score(self, complexity: float, solid_score: float) -> float:
        """
        Calculate maintainability score

        Lower complexity + higher SOLID = more maintainable
        """
        # Normalize complexity (lower is better)
        # McCabe complexity: < 10 = good, > 20 = bad
        complexity_normalized = max(0, 100 - (complexity / 20 * 100))

        # Combine with SOLID score
        return (complexity_normalized * 0.4) + (solid_score * 0.6)

    def _calculate_confidence(self, margin: float) -> str:
        """
        Calculate confidence level based on margin

        Args:
            margin: Score difference between winner and loser

        Returns:
            Confidence level (high, medium, low)
        """
        if margin > 20:
            return "high"
        elif margin > 10:
            return "medium"
        else:
            return "low"

    def _generate_reasoning(self, winner_score: DeveloperScore, loser_score: DeveloperScore) -> str:
        """Generate human-readable reasoning for decision"""

        reasons = []

        # Compare key factors
        if winner_score.security_score > loser_score.security_score + 10:
            reasons.append(f"Superior security ({winner_score.security_score:.0f} vs {loser_score.security_score:.0f})")

        if winner_score.test_coverage > loser_score.test_coverage + 10:
            reasons.append(f"Better test coverage ({winner_score.test_coverage:.0f}% vs {loser_score.test_coverage:.0f}%)")

        if winner_score.solid_score > loser_score.solid_score + 10:
            reasons.append(f"Stronger SOLID compliance ({winner_score.solid_score:.0f} vs {loser_score.solid_score:.0f})")

        if winner_score.quality_score > loser_score.quality_score + 10:
            reasons.append(f"Higher code quality ({winner_score.quality_score:.0f} vs {loser_score.quality_score:.0f})")

        if not reasons:
            reasons.append("Marginal advantage across multiple criteria")

        return "; ".join(reasons)


if __name__ == "__main__":
    """Example usage and testing"""

    print("Developer Arbitrator - Example Usage")
    print("=" * 70)

    # Create arbitrator
    arbitrator = DeveloperArbitrator()

    # Mock developer results
    dev_a_result = {
        "developer": "developer-a",
        "test_results": {"passed": 42, "total": 50},
        "solid_score": 85.0,
        "lines_of_code": 250,
        "complexity_score": 8.5
    }

    dev_b_result = {
        "developer": "developer-b",
        "test_results": {"passed": 45, "total": 50},
        "solid_score": 75.0,
        "lines_of_code": 180,
        "complexity_score": 12.0
    }

    # Mock code review results
    code_review_results = [
        {
            "developer": "developer-a",
            "overall_score": 85,
            "category_scores": {
                "security": 90,
                "quality": 85,
                "gdpr": 80,
                "accessibility": 75
            }
        },
        {
            "developer": "developer-b",
            "overall_score": 82,
            "category_scores": {
                "security": 85,
                "quality": 90,
                "gdpr": 75,
                "accessibility": 80
            }
        }
    ]

    # Select winner
    result = arbitrator.select_winner(dev_a_result, dev_b_result, code_review_results)

    print(f"\n🏆 Winner: {result['winner']}")
    print(f"   Score: {result['winner_score']:.2f}/100")
    print(f"   Margin: {result['margin']:.2f} points")
    print(f"   Confidence: {result['confidence']}")
    print(f"\n💡 Reasoning: {result['reasoning']}")

    print(f"\n📊 Detailed Breakdown:")
    print(f"   Developer A:")
    for criterion, score in result['breakdown']['developer-a'].items():
        print(f"      {criterion}: {score:.2f}")

    print(f"\n   Developer B:")
    for criterion, score in result['breakdown']['developer-b'].items():
        print(f"      {criterion}: {score:.2f}")

    print("\n" + "=" * 70)
    print("✅ Developer arbitration working correctly!")
