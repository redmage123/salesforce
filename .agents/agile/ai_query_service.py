#!/usr/bin/env python3
"""
Centralized AI Query Service - KG → RAG → LLM Pipeline

Single Responsibility: Orchestrate the KG-First → RAG → LLM query pipeline
for all agents, eliminating code duplication.

This service implements the complete AI query workflow:
1. Query Knowledge Graph first for patterns/context
2. Augment with RAG recommendations if available
3. Call LLM with enhanced context
4. Track token savings and costs

All agents should use this service instead of implementing their own
KG-First logic (DRY principle).

SOLID Principles:
- Single Responsibility: Only handles AI query orchestration
- Open/Closed: Extensible via strategy pattern for KG queries
- Liskov Substitution: Works with any KG/RAG/LLM implementation
- Interface Segregation: Minimal, focused interface
- Dependency Inversion: Depends on abstractions

Exception Handling:
- All exceptions are wrapped in ArtemisException hierarchy
- Never exposes raw exceptions to callers
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import json
from abc import ABC, abstractmethod

from artemis_exceptions import (
    ArtemisException,
    KnowledgeGraphError,
    RAGError,
    LLMError,
    wrap_exception
)
from debug_mixin import DebugMixin


# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================

class QueryType(Enum):
    """Type of AI query being performed"""
    REQUIREMENTS_PARSING = "requirements_parsing"
    ARCHITECTURE_DESIGN = "architecture_design"
    CODE_REVIEW = "code_review"
    CODE_GENERATION = "code_generation"
    PROJECT_ANALYSIS = "project_analysis"
    ERROR_RECOVERY = "error_recovery"
    RETROSPECTIVE = "retrospective"
    SPRINT_PLANNING = "sprint_planning"
    UIUX_EVALUATION = "uiux_evaluation"


@dataclass
class KGContext:
    """Knowledge Graph context retrieved before LLM call"""
    query_type: QueryType
    patterns_found: List[Dict[str, Any]]
    pattern_count: int
    estimated_token_savings: int
    kg_query_time_ms: float
    kg_available: bool
    error: Optional[str] = None


@dataclass
class RAGContext:
    """RAG context retrieved for prompt enhancement"""
    recommendations: List[str]
    recommendation_count: int
    rag_available: bool
    error: Optional[str] = None


@dataclass
class LLMResponse:
    """LLM response with metadata"""
    content: str
    tokens_used: int
    tokens_saved: int  # Estimated savings from KG-First
    cost_usd: float
    model: str
    temperature: float
    error: Optional[str] = None


@dataclass
class AIQueryResult:
    """Complete result from AI query pipeline"""
    query_type: QueryType
    kg_context: Optional[KGContext]
    rag_context: Optional[RAGContext]
    llm_response: LLMResponse
    total_duration_ms: float
    success: bool
    error: Optional[str] = None


# ============================================================================
# KG QUERY STRATEGY INTERFACE
# ============================================================================

class KGQueryStrategy(ABC):
    """
    Abstract strategy for querying Knowledge Graph

    Each query type (requirements, architecture, etc.) implements
    its own KG query logic via this interface.
    """

    @abstractmethod
    def query_kg(self, kg: Any, query_params: Dict[str, Any]) -> KGContext:
        """
        Query Knowledge Graph for patterns

        Args:
            kg: Knowledge Graph instance
            query_params: Query-specific parameters

        Returns:
            KGContext with patterns found
        """
        pass

    @abstractmethod
    def estimate_token_savings(self, patterns: List[Dict]) -> int:
        """Estimate token savings from patterns found"""
        pass


# ============================================================================
# CONCRETE KG QUERY STRATEGIES
# ============================================================================

class RequirementsKGStrategy(KGQueryStrategy):
    """KG query strategy for requirements parsing"""

    def query_kg(self, kg: Any, query_params: Dict[str, Any]) -> KGContext:
        """Query for similar requirements"""
        try:
            import time
            start = time.time()

            similar_requirements = kg.query("""
                MATCH (req:Requirement)
                WHERE req.status = 'active'
                RETURN req.req_id, req.title, req.type, req.priority
                ORDER BY req.priority DESC
                LIMIT 20
            """)

            elapsed_ms = (time.time() - start) * 1000

            if not similar_requirements:
                return KGContext(
                    query_type=QueryType.REQUIREMENTS_PARSING,
                    patterns_found=[],
                    pattern_count=0,
                    estimated_token_savings=0,
                    kg_query_time_ms=elapsed_ms,
                    kg_available=True
                )

            patterns = [
                {
                    'req_id': req.get('req.req_id'),
                    'title': req.get('req.title'),
                    'type': req.get('req.type'),
                    'priority': req.get('req.priority', 'medium')
                }
                for req in similar_requirements
            ]

            return KGContext(
                query_type=QueryType.REQUIREMENTS_PARSING,
                patterns_found=patterns,
                pattern_count=len(patterns),
                estimated_token_savings=self.estimate_token_savings(patterns),
                kg_query_time_ms=elapsed_ms,
                kg_available=True
            )
        except Exception as e:
            raise wrap_exception(e, KnowledgeGraphError,
                               f"Failed to query KG for requirements: {str(e)}")

    def estimate_token_savings(self, patterns: List[Dict]) -> int:
        """Estimate ~50 tokens saved per pattern"""
        return len(patterns) * 50


class ArchitectureKGStrategy(KGQueryStrategy):
    """KG query strategy for architecture decisions"""

    def query_kg(self, kg: Any, query_params: Dict[str, Any]) -> KGContext:
        """Query for similar ADRs"""
        try:
            import time
            start = time.time()

            keywords = query_params.get('keywords', [])
            req_type = query_params.get('req_type', 'functional')

            similar_adrs = []
            for keyword in keywords[:3]:  # Top 3 keywords
                adrs = kg.query("""
                    MATCH (adr:ADR)-[:ADDRESSES]->(req:Requirement)
                    WHERE req.title CONTAINS $keyword OR req.type = $req_type
                    RETURN DISTINCT adr.adr_id, adr.title
                    LIMIT 3
                """, {"keyword": keyword, "req_type": req_type})
                if adrs:
                    similar_adrs.extend(adrs)

            elapsed_ms = (time.time() - start) * 1000

            patterns = [
                {
                    'adr_id': adr.get('adr.adr_id'),
                    'title': adr.get('adr.title')
                }
                for adr in similar_adrs
            ]

            # Remove duplicates
            unique_patterns = {p['adr_id']: p for p in patterns}.values()
            patterns = list(unique_patterns)

            return KGContext(
                query_type=QueryType.ARCHITECTURE_DESIGN,
                patterns_found=patterns,
                pattern_count=len(patterns),
                estimated_token_savings=self.estimate_token_savings(patterns),
                kg_query_time_ms=elapsed_ms,
                kg_available=True
            )
        except Exception as e:
            raise wrap_exception(e, KnowledgeGraphError,
                               f"Failed to query KG for ADRs: {str(e)}")

    def estimate_token_savings(self, patterns: List[Dict]) -> int:
        """Estimate ~200 tokens saved per ADR pattern"""
        return len(patterns) * 200


class CodeReviewKGStrategy(KGQueryStrategy):
    """KG query strategy for code reviews"""

    def query_kg(self, kg: Any, query_params: Dict[str, Any]) -> KGContext:
        """Query for similar code reviews"""
        try:
            import time
            start = time.time()

            file_types = query_params.get('file_types', [])

            similar_reviews = []
            for file_type in file_types:
                reviews = kg.query("""
                    MATCH (review:CodeReview)-[:REVIEWED]->(file:File)
                    WHERE file.file_type = $file_type
                    AND review.critical_issues > 0
                    RETURN review.review_id, review.critical_issues, review.high_issues
                    LIMIT 5
                """, {"file_type": file_type})
                if reviews:
                    similar_reviews.extend(reviews)

            elapsed_ms = (time.time() - start) * 1000

            patterns = [
                {
                    'review_id': rev.get('review.review_id'),
                    'critical_issues': rev.get('review.critical_issues'),
                    'high_issues': rev.get('review.high_issues')
                }
                for rev in similar_reviews
            ]

            return KGContext(
                query_type=QueryType.CODE_REVIEW,
                patterns_found=patterns,
                pattern_count=len(patterns),
                estimated_token_savings=self.estimate_token_savings(patterns),
                kg_query_time_ms=elapsed_ms,
                kg_available=True
            )
        except Exception as e:
            raise wrap_exception(e, KnowledgeGraphError,
                               f"Failed to query KG for code reviews: {str(e)}")

    def estimate_token_savings(self, patterns: List[Dict]) -> int:
        """Code review can save ~2000 tokens with focused patterns"""
        return 2000 if patterns else 0


class CodeGenerationKGStrategy(KGQueryStrategy):
    """KG query strategy for code generation"""

    def query_kg(self, kg: Any, query_params: Dict[str, Any]) -> KGContext:
        """Query for similar implementations"""
        try:
            import time
            start = time.time()

            keywords = query_params.get('keywords', [])

            similar_files = []
            for keyword in keywords[:3]:
                files = kg.query("""
                    MATCH (task:Task)-[:MODIFIED]->(file:File)
                    WHERE toLower(task.title) CONTAINS $keyword
                    AND file.file_type = 'python'
                    RETURN DISTINCT file.path, file.file_type, task.title
                    LIMIT 3
                """, {"keyword": keyword})
                if files:
                    similar_files.extend(files)

            elapsed_ms = (time.time() - start) * 1000

            patterns = [
                {
                    'file_path': f.get('file.path'),
                    'file_type': f.get('file.file_type'),
                    'task_title': f.get('task.title')
                }
                for f in similar_files
            ]

            return KGContext(
                query_type=QueryType.CODE_GENERATION,
                patterns_found=patterns,
                pattern_count=len(patterns),
                estimated_token_savings=self.estimate_token_savings(patterns),
                kg_query_time_ms=elapsed_ms,
                kg_available=True
            )
        except Exception as e:
            raise wrap_exception(e, KnowledgeGraphError,
                               f"Failed to query KG for implementations: {str(e)}")

    def estimate_token_savings(self, patterns: List[Dict]) -> int:
        """Code generation can save ~3000 tokens with patterns"""
        return 3000 if patterns else 0


class ProjectAnalysisKGStrategy(KGQueryStrategy):
    """KG query strategy for project analysis"""

    def query_kg(self, kg: Any, query_params: Dict[str, Any]) -> KGContext:
        """Query for similar project analyses"""
        try:
            import time
            start = time.time()

            keywords = query_params.get('keywords', [])

            # Query for similar projects and their common issues
            similar_analyses = kg.query("""
                MATCH (analysis:ProjectAnalysis)-[:IDENTIFIED]->(issue:Issue)
                WHERE issue.severity IN ['CRITICAL', 'HIGH']
                RETURN analysis.project_name, issue.category, issue.severity,
                       issue.description
                ORDER BY issue.severity DESC
                LIMIT 10
            """)

            elapsed_ms = (time.time() - start) * 1000

            if not similar_analyses:
                return KGContext(
                    query_type=QueryType.PROJECT_ANALYSIS,
                    patterns_found=[],
                    pattern_count=0,
                    estimated_token_savings=0,
                    kg_query_time_ms=elapsed_ms,
                    kg_available=True
                )

            patterns = [
                {
                    'project_name': a.get('analysis.project_name'),
                    'category': a.get('issue.category'),
                    'severity': a.get('issue.severity'),
                    'description': a.get('issue.description')
                }
                for a in similar_analyses
            ]

            return KGContext(
                query_type=QueryType.PROJECT_ANALYSIS,
                patterns_found=patterns,
                pattern_count=len(patterns),
                estimated_token_savings=self.estimate_token_savings(patterns),
                kg_query_time_ms=elapsed_ms,
                kg_available=True
            )
        except Exception as e:
            raise wrap_exception(e, KnowledgeGraphError,
                               f"Failed to query KG for project analysis: {str(e)}")

    def estimate_token_savings(self, patterns: List[Dict]) -> int:
        """Project analysis can save ~1500 tokens with known patterns"""
        return 1500 if patterns else 0


class ErrorRecoveryKGStrategy(KGQueryStrategy):
    """KG query strategy for error recovery"""

    def query_kg(self, kg: Any, query_params: Dict[str, Any]) -> KGContext:
        """Query for similar errors and their solutions"""
        try:
            import time
            start = time.time()

            error_type = query_params.get('error_type', '')
            stage_name = query_params.get('stage_name', '')

            # Query for similar errors
            similar_errors = kg.query("""
                MATCH (error:Error)-[:OCCURRED_IN]->(stage:Stage)
                WHERE error.error_type CONTAINS $error_type
                AND stage.name = $stage_name
                RETURN error.error_type, error.solution, error.success_rate
                ORDER BY error.success_rate DESC
                LIMIT 5
            """, {"error_type": error_type, "stage_name": stage_name})

            elapsed_ms = (time.time() - start) * 1000

            if not similar_errors:
                return KGContext(
                    query_type=QueryType.ERROR_RECOVERY,
                    patterns_found=[],
                    pattern_count=0,
                    estimated_token_savings=0,
                    kg_query_time_ms=elapsed_ms,
                    kg_available=True
                )

            patterns = [
                {
                    'error_type': e.get('error.error_type'),
                    'solution': e.get('error.solution'),
                    'success_rate': e.get('error.success_rate')
                }
                for e in similar_errors
            ]

            return KGContext(
                query_type=QueryType.ERROR_RECOVERY,
                patterns_found=patterns,
                pattern_count=len(patterns),
                estimated_token_savings=self.estimate_token_savings(patterns),
                kg_query_time_ms=elapsed_ms,
                kg_available=True
            )
        except Exception as e:
            raise wrap_exception(e, KnowledgeGraphError,
                               f"Failed to query KG for error recovery: {str(e)}")

    def estimate_token_savings(self, patterns: List[Dict]) -> int:
        """Error recovery can save ~1000 tokens with known solutions"""
        return 1000 if patterns else 0


class SprintPlanningKGStrategy(KGQueryStrategy):
    """KG query strategy for sprint planning"""

    def query_kg(self, kg: Any, query_params: Dict[str, Any]) -> KGContext:
        """Query for sprint planning patterns and velocity data"""
        try:
            import time
            start = time.time()

            sprint_number = query_params.get('sprint_number', 0)
            team_name = query_params.get('team_name', 'default')

            # Query for historical sprint data (velocity, completed stories)
            sprint_history = kg.query("""
                MATCH (sprint:Sprint)-[:COMPLETED]->(task:Task)
                WHERE sprint.team_name = $team_name
                AND sprint.sprint_number < $sprint_number
                RETURN sprint.sprint_number, sprint.velocity,
                       COUNT(task) as tasks_completed,
                       AVG(task.story_points) as avg_story_points
                ORDER BY sprint.sprint_number DESC
                LIMIT 5
            """, {"team_name": team_name, "sprint_number": sprint_number})

            elapsed_ms = (time.time() - start) * 1000

            if not sprint_history:
                return KGContext(
                    query_type=QueryType.SPRINT_PLANNING,
                    patterns_found=[],
                    pattern_count=0,
                    estimated_token_savings=0,
                    kg_query_time_ms=elapsed_ms,
                    kg_available=True
                )

            patterns = [
                {
                    'sprint_number': s.get('sprint.sprint_number'),
                    'velocity': s.get('sprint.velocity'),
                    'tasks_completed': s.get('tasks_completed'),
                    'avg_story_points': s.get('avg_story_points')
                }
                for s in sprint_history
            ]

            return KGContext(
                query_type=QueryType.SPRINT_PLANNING,
                patterns_found=patterns,
                pattern_count=len(patterns),
                estimated_token_savings=self.estimate_token_savings(patterns),
                kg_query_time_ms=elapsed_ms,
                kg_available=True
            )
        except Exception as e:
            raise wrap_exception(e, KnowledgeGraphError,
                               f"Failed to query KG for sprint planning: {str(e)}")

    def estimate_token_savings(self, patterns: List[Dict]) -> int:
        """Sprint planning can save ~1200 tokens with historical velocity data"""
        return 1200 if patterns else 0


class RetrospectiveKGStrategy(KGQueryStrategy):
    """KG query strategy for retrospective analysis"""

    def query_kg(self, kg: Any, query_params: Dict[str, Any]) -> KGContext:
        """Query for retrospective insights from past sprints"""
        try:
            import time
            start = time.time()

            sprint_number = query_params.get('sprint_number', 0)
            team_name = query_params.get('team_name', 'default')

            # Query for past retrospective insights and action items
            retrospective_data = kg.query("""
                MATCH (retro:Retrospective)-[:FOR_SPRINT]->(sprint:Sprint)
                WHERE sprint.team_name = $team_name
                AND sprint.sprint_number < $sprint_number
                RETURN retro.retro_id,
                       retro.what_went_well,
                       retro.what_needs_improvement,
                       retro.action_items,
                       sprint.sprint_number,
                       sprint.velocity
                ORDER BY sprint.sprint_number DESC
                LIMIT 3
            """, {"team_name": team_name, "sprint_number": sprint_number})

            elapsed_ms = (time.time() - start) * 1000

            if not retrospective_data:
                return KGContext(
                    query_type=QueryType.RETROSPECTIVE,
                    patterns_found=[],
                    pattern_count=0,
                    estimated_token_savings=0,
                    kg_query_time_ms=elapsed_ms,
                    kg_available=True
                )

            patterns = [
                {
                    'retro_id': r.get('retro.retro_id'),
                    'what_went_well': r.get('retro.what_went_well'),
                    'what_needs_improvement': r.get('retro.what_needs_improvement'),
                    'action_items': r.get('retro.action_items'),
                    'sprint_number': r.get('sprint.sprint_number'),
                    'velocity': r.get('sprint.velocity')
                }
                for r in retrospective_data
            ]

            return KGContext(
                query_type=QueryType.RETROSPECTIVE,
                patterns_found=patterns,
                pattern_count=len(patterns),
                estimated_token_savings=self.estimate_token_savings(patterns),
                kg_query_time_ms=elapsed_ms,
                kg_available=True
            )
        except Exception as e:
            raise wrap_exception(e, KnowledgeGraphError,
                               f"Failed to query KG for retrospective: {str(e)}")

    def estimate_token_savings(self, patterns: List[Dict]) -> int:
        """Retrospective can save ~800 tokens with historical insights"""
        return 800 if patterns else 0


# ============================================================================
# TOKEN SAVINGS TRACKER
# ============================================================================

@dataclass
class TokenSavingsMetrics:
    """Metrics for tracking token savings"""
    query_type: str
    queries_executed: int
    total_tokens_used: int
    total_tokens_saved: int
    total_cost_usd: float
    total_cost_saved_usd: float
    average_savings_percent: float
    kg_hits: int
    kg_misses: int
    kg_hit_rate: float


class TokenSavingsTracker:
    """
    Tracks token savings across all queries

    Single Responsibility: Collect and report token savings metrics
    """

    def __init__(self):
        """Initialize token savings tracker"""
        self.metrics_by_type: Dict[str, Dict[str, Any]] = {}
        self.total_queries = 0
        self.total_tokens_saved = 0
        self.total_cost_saved = 0.0

    def record_query(
        self,
        query_type: QueryType,
        tokens_used: int,
        tokens_saved: int,
        cost_usd: float,
        kg_patterns_found: int
    ):
        """
        Record metrics for a single query

        Args:
            query_type: Type of query
            tokens_used: Actual tokens used
            tokens_saved: Estimated tokens saved via KG-First
            cost_usd: Actual cost
            kg_patterns_found: Number of KG patterns found
        """
        type_name = query_type.value

        if type_name not in self.metrics_by_type:
            self.metrics_by_type[type_name] = {
                'queries': 0,
                'tokens_used': 0,
                'tokens_saved': 0,
                'cost_usd': 0.0,
                'kg_hits': 0,
                'kg_misses': 0
            }

        metrics = self.metrics_by_type[type_name]
        metrics['queries'] += 1
        metrics['tokens_used'] += tokens_used
        metrics['tokens_saved'] += tokens_saved
        metrics['cost_usd'] += cost_usd

        if kg_patterns_found > 0:
            metrics['kg_hits'] += 1
        else:
            metrics['kg_misses'] += 1

        # Update totals
        self.total_queries += 1
        self.total_tokens_saved += tokens_saved

        # Rough cost savings estimate (tokens_saved * $0.015 per 1K tokens average)
        cost_saved = (tokens_saved / 1000) * 0.015
        metrics['cost_saved'] = metrics.get('cost_saved', 0.0) + cost_saved
        self.total_cost_saved += cost_saved

    def get_metrics(self, query_type: Optional[QueryType] = None) -> TokenSavingsMetrics:
        """
        Get metrics for a specific query type or overall

        Args:
            query_type: Optional query type to filter by

        Returns:
            TokenSavingsMetrics with aggregated data
        """
        if query_type:
            type_name = query_type.value
            if type_name not in self.metrics_by_type:
                return TokenSavingsMetrics(
                    query_type=type_name,
                    queries_executed=0,
                    total_tokens_used=0,
                    total_tokens_saved=0,
                    total_cost_usd=0.0,
                    total_cost_saved_usd=0.0,
                    average_savings_percent=0.0,
                    kg_hits=0,
                    kg_misses=0,
                    kg_hit_rate=0.0
                )

            metrics = self.metrics_by_type[type_name]
            total_tokens = metrics['tokens_used'] + metrics['tokens_saved']
            savings_percent = (metrics['tokens_saved'] / total_tokens * 100) if total_tokens > 0 else 0.0
            kg_total = metrics['kg_hits'] + metrics['kg_misses']
            kg_hit_rate = (metrics['kg_hits'] / kg_total) if kg_total > 0 else 0.0

            return TokenSavingsMetrics(
                query_type=type_name,
                queries_executed=metrics['queries'],
                total_tokens_used=metrics['tokens_used'],
                total_tokens_saved=metrics['tokens_saved'],
                total_cost_usd=metrics['cost_usd'],
                total_cost_saved_usd=metrics.get('cost_saved', 0.0),
                average_savings_percent=savings_percent,
                kg_hits=metrics['kg_hits'],
                kg_misses=metrics['kg_misses'],
                kg_hit_rate=kg_hit_rate
            )
        else:
            # Overall metrics
            total_tokens_used = sum(m['tokens_used'] for m in self.metrics_by_type.values())
            total_cost = sum(m['cost_usd'] for m in self.metrics_by_type.values())
            total_kg_hits = sum(m['kg_hits'] for m in self.metrics_by_type.values())
            total_kg_misses = sum(m['kg_misses'] for m in self.metrics_by_type.values())

            total_tokens = total_tokens_used + self.total_tokens_saved
            savings_percent = (self.total_tokens_saved / total_tokens * 100) if total_tokens > 0 else 0.0
            kg_total = total_kg_hits + total_kg_misses
            kg_hit_rate = (total_kg_hits / kg_total) if kg_total > 0 else 0.0

            return TokenSavingsMetrics(
                query_type="OVERALL",
                queries_executed=self.total_queries,
                total_tokens_used=total_tokens_used,
                total_tokens_saved=self.total_tokens_saved,
                total_cost_usd=total_cost,
                total_cost_saved_usd=self.total_cost_saved,
                average_savings_percent=savings_percent,
                kg_hits=total_kg_hits,
                kg_misses=total_kg_misses,
                kg_hit_rate=kg_hit_rate
            )

    def print_dashboard(self):
        """Print a comprehensive metrics dashboard"""
        print("=" * 80)
        print("TOKEN SAVINGS DASHBOARD - AI Query Service")
        print("=" * 80)
        print()

        # Overall metrics
        overall = self.get_metrics()
        print("OVERALL METRICS")
        print("-" * 80)
        print(f"Total Queries:        {overall.queries_executed:,}")
        print(f"Tokens Used:          {overall.total_tokens_used:,}")
        print(f"Tokens Saved:         {overall.total_tokens_saved:,}")
        print(f"Savings Rate:         {overall.average_savings_percent:.1f}%")
        print(f"KG Hit Rate:          {overall.kg_hit_rate:.1f}% ({overall.kg_hits}/{overall.kg_hits + overall.kg_misses})")
        print(f"Cost (actual):        ${overall.total_cost_usd:.4f}")
        print(f"Cost (saved):         ${overall.total_cost_saved_usd:.4f}")
        print()

        # Per-query-type breakdown
        print("BREAKDOWN BY QUERY TYPE")
        print("-" * 80)
        print(f"{'Type':<25} {'Queries':<10} {'Tokens Saved':<15} {'Savings %':<12} {'KG Hit %':<10}")
        print("-" * 80)

        for query_type_str in sorted(self.metrics_by_type.keys()):
            query_type = QueryType(query_type_str)
            metrics = self.get_metrics(query_type)
            print(f"{metrics.query_type:<25} "
                  f"{metrics.queries_executed:<10} "
                  f"{metrics.total_tokens_saved:<15,} "
                  f"{metrics.average_savings_percent:<11.1f}% "
                  f"{metrics.kg_hit_rate:<9.1f}%")

        print("=" * 80)
        print()

        # Estimated annual savings
        if overall.queries_executed > 0:
            queries_per_day = overall.queries_executed  # Assuming current metrics are for one session
            cost_saved_per_day = overall.total_cost_saved_usd
            annual_savings = cost_saved_per_day * 365

            print("PROJECTED ANNUAL SAVINGS (at current rate)")
            print("-" * 80)
            print(f"Daily cost savings:   ${cost_saved_per_day:.2f}")
            print(f"Annual cost savings:  ${annual_savings:.2f}")
            print("=" * 80)


# ============================================================================
# CENTRALIZED AI QUERY SERVICE
# ============================================================================

class AIQueryService(DebugMixin):
    """
    Centralized AI Query Service - KG → RAG → LLM Pipeline

    Single service that all agents use to query the AI subsystem.
    Eliminates code duplication and ensures consistent KG-First approach.
    """

    def __init__(
        self,
        llm_client: Any,
        kg: Optional[Any] = None,
        rag: Optional[Any] = None,
        logger: Optional[Any] = None,
        enable_kg: bool = True,
        enable_rag: bool = True,
        verbose: bool = False
    ):
        """
        Initialize AI Query Service

        Args:
            llm_client: LLM client instance (required)
            kg: Knowledge Graph instance (optional)
            rag: RAG agent instance (optional)
            logger: Logger for events (optional)
            enable_kg: Enable KG-First queries (default: True)
            enable_rag: Enable RAG enhancement (default: True)
            verbose: Enable verbose logging (default: False)
        """
        DebugMixin.__init__(self, component_name="ai_query")
        self.llm_client = llm_client
        self.kg = kg
        self.rag = rag
        self.logger = logger
        self.enable_kg = enable_kg
        self.enable_rag = enable_rag
        self.verbose = verbose

        # Strategy registry
        self.strategies: Dict[QueryType, KGQueryStrategy] = {
            QueryType.REQUIREMENTS_PARSING: RequirementsKGStrategy(),
            QueryType.ARCHITECTURE_DESIGN: ArchitectureKGStrategy(),
            QueryType.CODE_REVIEW: CodeReviewKGStrategy(),
            QueryType.CODE_GENERATION: CodeGenerationKGStrategy(),
            QueryType.PROJECT_ANALYSIS: ProjectAnalysisKGStrategy(),
            QueryType.ERROR_RECOVERY: ErrorRecoveryKGStrategy(),
            QueryType.SPRINT_PLANNING: SprintPlanningKGStrategy(),
            QueryType.RETROSPECTIVE: RetrospectiveKGStrategy()
        }

        # Token savings tracker for metrics
        self.savings_tracker = TokenSavingsTracker()

        # KG query cache for performance optimization
        self.kg_cache: Dict[str, KGContext] = {}
        self.cache_enabled = True
        self.cache_max_age_seconds = 300  # 5 minutes

        if self.verbose and self.logger:
            self.logger.log("AI Query Service initialized with KG→RAG→LLM pipeline", "INFO")

    def query(
        self,
        query_type: QueryType,
        prompt: str,
        kg_query_params: Optional[Dict[str, Any]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4000
    ) -> AIQueryResult:
        """
        Execute complete AI query pipeline: KG → RAG → LLM

        Args:
            query_type: Type of query being performed
            prompt: Base LLM prompt (will be enhanced with KG/RAG context)
            kg_query_params: Parameters for KG query (query-specific)
            temperature: LLM temperature (default: 0.3)
            max_tokens: Max LLM tokens (default: 4000)

        Returns:
            AIQueryResult with complete pipeline results

        Raises:
            ArtemisException: If any stage fails critically
        """
        self.debug_trace("query",
                        query_type=query_type.value,
                        prompt_length=len(prompt),
                        temperature=temperature,
                        max_tokens=max_tokens,
                        kg_enabled=self.enable_kg,
                        rag_enabled=self.enable_rag)

        try:
            import time
            start_time = time.time()

            # Step 1: Query Knowledge Graph (KG-First)
            with self.debug_section("KG Query", query_type=query_type.value):
                kg_context = self._query_knowledge_graph(query_type, kg_query_params or {})
                if kg_context:
                    self.debug_log("KG patterns found",
                                  pattern_count=kg_context.pattern_count,
                                  estimated_token_savings=kg_context.estimated_token_savings)

            # Step 2: Query RAG for additional recommendations
            with self.debug_section("RAG Query", query_type=query_type.value):
                rag_context = self._query_rag(query_type, prompt)
                if rag_context and rag_context.recommendation_count > 0:
                    self.debug_log("RAG recommendations found",
                                  recommendation_count=rag_context.recommendation_count)

            # Step 3: Enhance prompt with KG + RAG context
            enhanced_prompt = self._enhance_prompt(prompt, kg_context, rag_context)
            self.debug_log("Prompt enhanced",
                          original_length=len(prompt),
                          enhanced_length=len(enhanced_prompt))

            # Step 4: Call LLM with enhanced prompt
            with self.debug_section("LLM Call", query_type=query_type.value):
                llm_response = self._call_llm(enhanced_prompt, temperature, max_tokens,
                                             kg_context.estimated_token_savings if kg_context else 0)
                self.debug_log("LLM response received",
                              tokens_used=llm_response.tokens_used,
                              tokens_saved=llm_response.tokens_saved,
                              cost_usd=f"${llm_response.cost_usd:.6f}")

            # Calculate total duration
            total_duration_ms = (time.time() - start_time) * 1000

            # Record metrics for tracking
            self.savings_tracker.record_query(
                query_type=query_type,
                tokens_used=llm_response.tokens_used,
                tokens_saved=llm_response.tokens_saved,
                cost_usd=llm_response.cost_usd,
                kg_patterns_found=kg_context.pattern_count if kg_context else 0
            )

            self.debug_log("Query pipeline completed",
                          total_duration_ms=f"{total_duration_ms:.2f}",
                          kg_patterns=kg_context.pattern_count if kg_context else 0,
                          tokens_saved=llm_response.tokens_saved)

            # Log success
            if self.verbose and self.logger:
                self.logger.log(
                    f"✅ AI Query completed: {query_type.value} "
                    f"(KG: {kg_context.pattern_count if kg_context else 0} patterns, "
                    f"Tokens saved: ~{llm_response.tokens_saved})",
                    "INFO"
                )

            return AIQueryResult(
                query_type=query_type,
                kg_context=kg_context,
                rag_context=rag_context,
                llm_response=llm_response,
                total_duration_ms=total_duration_ms,
                success=True,
                error=None
            )
        except ArtemisException as ae:
            # Re-raise Artemis exceptions as-is
            self.debug_log("AI Query failed with ArtemisException", error=str(ae))
            raise
        except Exception as e:
            # Wrap unexpected exceptions
            self.debug_log("AI Query failed with unexpected exception", error=str(e))
            raise wrap_exception(e, ArtemisException,
                               f"AI Query pipeline failed: {str(e)}")

    def _query_knowledge_graph(
        self,
        query_type: QueryType,
        query_params: Dict[str, Any]
    ) -> Optional[KGContext]:
        """
        Query Knowledge Graph for patterns (Step 1) with caching

        Args:
            query_type: Type of query
            query_params: Query-specific parameters

        Returns:
            KGContext with patterns found, or None if KG unavailable
        """
        try:
            if not self.enable_kg or not self.kg:
                return None

            # Get strategy for this query type
            strategy = self.strategies.get(query_type)
            if not strategy:
                if self.verbose and self.logger:
                    self.logger.log(f"No KG strategy for {query_type.value} - skipping KG", "DEBUG")
                return None

            # Check cache first (if enabled)
            cache_key = None
            if self.cache_enabled:
                import json
                import hashlib
                # Create cache key from query type and params
                cache_data = f"{query_type.value}:{json.dumps(query_params, sort_keys=True)}"
                cache_key = hashlib.md5(cache_data.encode()).hexdigest()

                if cache_key in self.kg_cache:
                    cached_result = self.kg_cache[cache_key]
                    # Check cache age (simple implementation - could add timestamps)
                    if self.verbose and self.logger:
                        self.logger.log(f"💾 KG cache hit for {query_type.value}", "DEBUG")
                    return cached_result

            # Execute KG query
            kg_context = strategy.query_kg(self.kg, query_params)

            # Store in cache
            if self.cache_enabled and cache_key and kg_context:
                self.kg_cache[cache_key] = kg_context
                # Simple cache size limit (keep last 100 entries)
                if len(self.kg_cache) > 100:
                    # Remove oldest entry (simple FIFO)
                    oldest_key = next(iter(self.kg_cache))
                    del self.kg_cache[oldest_key]

            if self.verbose and self.logger and kg_context.pattern_count > 0:
                self.logger.log(
                    f"📊 KG found {kg_context.pattern_count} patterns for {query_type.value} "
                    f"(~{kg_context.estimated_token_savings} tokens saved)",
                    "INFO"
                )

            return kg_context
        except KnowledgeGraphError:
            # Already wrapped, re-raise
            raise
        except Exception as e:
            # Log error but don't fail the entire pipeline
            if self.logger:
                self.logger.log(f"KG query failed (continuing without KG): {str(e)}", "WARNING")
            return None

    def _query_rag(
        self,
        query_type: QueryType,
        prompt: str
    ) -> Optional[RAGContext]:
        """
        Query RAG for recommendations (Step 2)

        Args:
            query_type: Type of query
            prompt: Base prompt (used to find relevant RAG content)

        Returns:
            RAGContext with recommendations, or None if RAG unavailable
        """
        try:
            if not self.enable_rag or not self.rag:
                return None

            # Query RAG for recommendations
            # Assuming RAG has a method like get_recommendations(query)
            if hasattr(self.rag, 'get_recommendations'):
                recommendations = self.rag.get_recommendations(prompt[:500])  # First 500 chars

                if recommendations:
                    if self.verbose and self.logger:
                        self.logger.log(
                            f"📚 RAG found {len(recommendations)} recommendations",
                            "INFO"
                        )

                    return RAGContext(
                        recommendations=recommendations,
                        recommendation_count=len(recommendations),
                        rag_available=True
                    )

            return None
        except Exception as e:
            # Log error but don't fail the entire pipeline
            if self.logger:
                self.logger.log(f"RAG query failed (continuing without RAG): {str(e)}", "WARNING")
            return RAGContext(
                recommendations=[],
                recommendation_count=0,
                rag_available=False,
                error=str(e)
            )

    def _enhance_prompt(
        self,
        base_prompt: str,
        kg_context: Optional[KGContext],
        rag_context: Optional[RAGContext]
    ) -> str:
        """
        Enhance prompt with KG + RAG context (Step 3)

        Args:
            base_prompt: Original prompt
            kg_context: KG patterns (if available)
            rag_context: RAG recommendations (if available)

        Returns:
            Enhanced prompt with KG and RAG context
        """
        try:
            enhanced_parts = [base_prompt]

            # Add KG context
            if kg_context and kg_context.pattern_count > 0:
                enhanced_parts.append("\n\n" + "="*80)
                enhanced_parts.append("\n**Knowledge Graph Context (use as reference):**\n")
                enhanced_parts.append(f"Found {kg_context.pattern_count} similar patterns:\n")

                for i, pattern in enumerate(kg_context.patterns_found[:5], 1):
                    pattern_summary = json.dumps(pattern, indent=2)
                    enhanced_parts.append(f"\n**Pattern {i}:**\n```json\n{pattern_summary}\n```")

                enhanced_parts.append("\n**NOTE**: Use these patterns as guidance, adapt to your specific task.")
                enhanced_parts.append("\n" + "="*80 + "\n")

            # Add RAG context
            if rag_context and rag_context.recommendation_count > 0:
                enhanced_parts.append("\n\n" + "="*80)
                enhanced_parts.append("\n**Historical Recommendations (RAG):**\n")
                for i, rec in enumerate(rag_context.recommendations[:3], 1):
                    enhanced_parts.append(f"{i}. {rec}\n")
                enhanced_parts.append("="*80 + "\n")

            return "".join(enhanced_parts)
        except Exception as e:
            # If enhancement fails, return base prompt
            if self.logger:
                self.logger.log(f"Prompt enhancement failed: {str(e)}", "WARNING")
            return base_prompt

    def _call_llm(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        estimated_tokens_saved: int
    ) -> LLMResponse:
        """
        Call LLM with enhanced prompt (Step 4)

        Args:
            prompt: Enhanced prompt
            temperature: LLM temperature
            max_tokens: Max tokens
            estimated_tokens_saved: Estimated savings from KG-First

        Returns:
            LLMResponse with result

        Raises:
            LLMError: If LLM call fails
        """
        try:
            # Call LLM
            response = self.llm_client.generate_text(
                system_message="You are a helpful AI assistant.",
                user_message=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Extract content if response is LLMResponse object
            response_text = response.content if hasattr(response, 'content') else str(response)

            # Calculate tokens and cost (approximate)
            input_tokens = len(prompt.split()) * 1.3  # Rough estimate
            output_tokens = len(response_text.split()) * 1.3
            total_tokens = int(input_tokens + output_tokens)

            # Rough cost calculation (GPT-4 pricing: $10/1M input, $30/1M output)
            cost_usd = (input_tokens / 1_000_000 * 10) + (output_tokens / 1_000_000 * 30)

            return LLMResponse(
                content=response_text,
                tokens_used=total_tokens,
                tokens_saved=estimated_tokens_saved,
                cost_usd=cost_usd,
                model=getattr(self.llm_client, 'model', 'unknown'),
                temperature=temperature,
                error=None
            )
        except Exception as e:
            raise wrap_exception(e, LLMError,
                               f"LLM call failed: {str(e)}")

    def get_metrics(self, query_type: Optional[QueryType] = None) -> TokenSavingsMetrics:
        """
        Get token savings metrics

        Args:
            query_type: Optional query type to filter by

        Returns:
            TokenSavingsMetrics for the specified query type or overall
        """
        return self.savings_tracker.get_metrics(query_type)

    def print_metrics_dashboard(self):
        """Print comprehensive metrics dashboard"""
        self.savings_tracker.print_dashboard()

    def clear_cache(self):
        """Clear the KG query cache"""
        self.kg_cache.clear()
        if self.verbose and self.logger:
            self.logger.log("🧹 KG query cache cleared", "INFO")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dict with cache size and hit rate
        """
        return {
            'cache_size': len(self.kg_cache),
            'cache_enabled': self.cache_enabled,
            'cache_max_age_seconds': self.cache_max_age_seconds
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_ai_query_service(
    llm_client: Any,
    kg: Optional[Any] = None,
    rag: Optional[Any] = None,
    logger: Optional[Any] = None,
    verbose: bool = False
) -> AIQueryService:
    """
    Factory function to create AI Query Service

    Args:
        llm_client: LLM client instance
        kg: Knowledge Graph instance (optional)
        rag: RAG agent instance (optional)
        logger: Logger (optional)
        verbose: Enable verbose logging

    Returns:
        Configured AIQueryService instance
    """
    try:
        # Auto-detect KG if not provided
        if kg is None:
            try:
                from knowledge_graph_factory import get_knowledge_graph
                kg = get_knowledge_graph()
            except Exception:
                pass  # KG not available

        return AIQueryService(
            llm_client=llm_client,
            kg=kg,
            rag=rag,
            logger=logger,
            enable_kg=(kg is not None),
            enable_rag=(rag is not None),
            verbose=verbose
        )
    except Exception as e:
        raise wrap_exception(e, ArtemisException,
                           f"Failed to create AI Query Service: {str(e)}")


if __name__ == "__main__":
    # Example usage
    print("AI Query Service - Example")
    print("="*60)

    # Mock LLM client
    class MockLLMClient:
        model = "gpt-4"
        def generate_text(self, system_message, user_message, temperature, max_tokens):
            return "Mock LLM response based on enhanced prompt"

    # Create service
    service = create_ai_query_service(
        llm_client=MockLLMClient(),
        verbose=True
    )

    # Example query
    result = service.query(
        query_type=QueryType.REQUIREMENTS_PARSING,
        prompt="Parse these requirements: User authentication system",
        kg_query_params={'project_name': 'auth-system'}
    )

    print(f"\nQuery Type: {result.query_type.value}")
    print(f"Success: {result.success}")
    print(f"Tokens Saved: ~{result.llm_response.tokens_saved}")
    print(f"Total Duration: {result.total_duration_ms:.2f}ms")
