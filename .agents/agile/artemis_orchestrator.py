#!/usr/bin/env python3
"""
ARTEMIS Orchestrator (SOLID-Compliant Refactoring)

This is a SOLID-compliant refactoring of the original ArtemisOrchestrator.

SOLID Principles Applied:
- Single Responsibility: Orchestrator ONLY orchestrates - delegates work to stages
- Open/Closed: Can add new stages without modifying orchestrator
- Liskov Substitution: All stages implement PipelineStage interface
- Interface Segregation: Minimal interfaces (PipelineStage, TestRunner, etc.)
- Dependency Inversion: Depends on abstractions (PipelineStage), not concretions

Key Improvements:
- 2217 lines → ~200 lines (90% reduction!)
- God class → focused orchestrator + separate stage classes
- Hard-coded dependencies → dependency injection
- Monolithic → modular and testable
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sys

import hydra
from omegaconf import DictConfig, OmegaConf

# Import debug service
from debug_service import DebugService

from artemis_stage_interface import PipelineStage, LoggerInterface
from artemis_services import PipelineLogger, TestRunner
from artemis_stages import (
    ProjectAnalysisStage,
    ArchitectureStage,
    DependencyValidationStage,
    DevelopmentStage,
    ValidationStage,
    IntegrationStage,
    TestingStage,
    ResearchStage
)
from code_review_stage import CodeReviewStage
from arbitration_stage import ArbitrationStage
from sprint_planning_stage import SprintPlanningStage
from project_review_stage import ProjectReviewStage
from uiux_stage import UIUXStage
from retrospective_agent import RetrospectiveAgent
from requirements_stage import RequirementsParsingStage
from ssd_generation_stage import SSDGenerationStage
from platform_detector import PlatformDetector, PlatformInfo, ResourceAllocation, get_platform_summary
from ai_orchestration_planner import (
    OrchestrationPlannerFactory,
    OrchestrationPlan
)
from kanban_manager import KanbanBoard
from messenger_interface import MessengerInterface
from messenger_factory import MessengerFactory
from rag_agent import RAGAgent
from config_agent import ConfigurationAgent, get_config
from llm_client import LLMClient
from hydra_config import ArtemisConfig
from workflow_status_tracker import WorkflowStatusTracker
from supervisor_agent import SupervisorAgent, RecoveryStrategy
from pipeline_strategies import PipelineStrategy, StandardPipelineStrategy
from artemis_constants import (
    MAX_RETRY_ATTEMPTS,
    DEFAULT_RETRY_INTERVAL_SECONDS,
    RETRY_BACKOFF_FACTOR,
    STAGE_TIMEOUT_SECONDS,
    DEVELOPER_AGENT_TIMEOUT_SECONDS,
    CODE_REVIEW_TIMEOUT_SECONDS,
    CODE_REVIEW_PASSING_SCORE
)
from artemis_exceptions import (
    PipelineStageError,
    PipelineConfigurationError,
    RAGStorageError,
    FileReadError,
    FileWriteError,
    create_wrapped_exception
)
from pipeline_observer import (
    PipelineObservable,
    ObserverFactory,
    EventBuilder,
    EventType
)

# Import AIQueryService for centralized KG→RAG→LLM pipeline
try:
    from ai_query_service import create_ai_query_service, AIQueryService
    AI_QUERY_SERVICE_AVAILABLE = True
except ImportError:
    AI_QUERY_SERVICE_AVAILABLE = False

# Import IntelligentRouter for AI-powered stage selection
try:
    from intelligent_router import IntelligentRouter
    INTELLIGENT_ROUTER_AVAILABLE = True
except ImportError:
    INTELLIGENT_ROUTER_AVAILABLE = False


class WorkflowPlanner:
    """
    Dynamic Workflow Planner (Already SOLID-compliant)

    Single Responsibility: Analyze tasks and create workflow plans
    """

    def __init__(self, card: Dict, verbose: bool = True, resource_allocation: Optional['ResourceAllocation'] = None):
        self.card = card
        self.verbose = verbose
        self.resource_allocation = resource_allocation
        self.complexity = self._analyze_complexity()
        self.task_type = self._determine_task_type()

    def _analyze_complexity(self) -> str:
        """Analyze task complexity"""
        # Calculate complexity score using configuration
        priority_scores = {'high': 2, 'medium': 1, 'low': 0}
        points_thresholds = [(13, 3), (8, 2), (5, 1)]
        complexity_thresholds = [(6, 'complex'), (3, 'medium'), (0, 'simple')]

        complexity_score = 0

        # Priority contribution
        priority = self.card.get('priority', 'medium')
        complexity_score += priority_scores.get(priority, 1)

        # Story points contribution
        points = self.card.get('points', 5)
        complexity_score += next((score for threshold, score in points_thresholds if points >= threshold), 0)

        # Keywords contribution
        description = self.card.get('description', '').lower()
        complex_keywords = ['integrate', 'architecture', 'refactor', 'migrate',
                           'performance', 'scalability', 'distributed', 'api']
        simple_keywords = ['fix', 'update', 'small', 'minor', 'simple', 'quick']

        complex_count = sum(1 for kw in complex_keywords if kw in description)
        simple_count = sum(1 for kw in simple_keywords if kw in description)

        complexity_score += min(complex_count, 3) - min(simple_count, 2)

        # Determine complexity level
        return next(level for threshold, level in complexity_thresholds if complexity_score >= threshold)

    def _determine_task_type(self) -> str:
        """Determine task type using keyword matching"""
        description = self.card.get('description', '').lower()
        title = self.card.get('title', '').lower()
        combined = f"{title} {description}"

        # Define task type keywords in priority order
        task_type_keywords = [
            ('bugfix', ['bug', 'fix', 'error', 'issue']),
            ('refactor', ['refactor', 'restructure', 'cleanup']),
            ('documentation', ['docs', 'documentation', 'readme']),
            ('feature', ['feature', 'implement', 'add', 'create'])
        ]

        # Return first matching task type or 'other'
        return next(
            (task_type for task_type, keywords in task_type_keywords if any(kw in combined for kw in keywords)),
            'other'
        )

    def create_workflow_plan(self) -> Dict:
        """Create workflow plan based on complexity"""
        plan = {
            'complexity': self.complexity,
            'task_type': self.task_type,
            'stages': ['requirements_parsing', 'project_analysis', 'architecture', 'dependencies', 'development', 'code_review', 'validation', 'integration'],
            'parallel_developers': 1,
            'max_parallel_tests': 4,  # Default for backward compatibility
            'skip_stages': ['arbitration'],
            'execution_strategy': 'sequential',
            'reasoning': []
        }

        # Determine parallel developers using configuration mapping
        complexity_config = {
            'complex': {'parallel_developers': 3, 'execution_strategy': 'parallel'},
            'medium': {'parallel_developers': 2, 'execution_strategy': 'parallel'},
            'simple': {'parallel_developers': 1, 'execution_strategy': 'sequential'}
        }

        config = complexity_config.get(self.complexity, complexity_config['simple'])
        desired_parallel_developers = config['parallel_developers']

        # Cap parallel developers based on platform resource allocation
        if self.resource_allocation:
            plan['parallel_developers'] = min(
                desired_parallel_developers,
                self.resource_allocation.max_parallel_developers
            )
            if plan['parallel_developers'] < desired_parallel_developers:
                plan['reasoning'].append(
                    f"Limited parallel developers to {plan['parallel_developers']} "
                    f"(platform resources: {self.resource_allocation.max_parallel_developers} max)"
                )
        else:
            plan['parallel_developers'] = desired_parallel_developers

        plan['execution_strategy'] = config.get('execution_strategy', 'sequential')

        # Set max parallel tests based on platform resource allocation
        if self.resource_allocation:
            plan['max_parallel_tests'] = self.resource_allocation.max_parallel_tests
            plan['reasoning'].append(
                f"Max parallel tests set to {plan['max_parallel_tests']} based on platform resources"
            )

        # Skip arbitration if only one developer
        if plan['parallel_developers'] == 1:
            plan['reasoning'].append("Skipping arbitration (only one developer)")
        else:
            plan['stages'].insert(-1, 'arbitration')  # Insert before integration
            plan['skip_stages'].remove('arbitration')

        # Add testing unless documentation
        if self.task_type != 'documentation':
            plan['stages'].append('testing')
        else:
            plan['skip_stages'].append('testing')

        return plan


class ArtemisOrchestrator:
    """
    Artemis Orchestrator - SOLID Refactored

    Single Responsibility: Orchestrate pipeline stages
    - Does NOT implement stage logic (delegates to PipelineStage objects)
    - Does NOT handle logging (delegates to LoggerInterface)
    - Does NOT run tests (delegates to TestRunner)

    Dependencies injected via constructor (Dependency Inversion Principle)
    """

    def __init__(
        self,
        card_id: str,
        board: KanbanBoard,
        messenger: MessengerInterface,
        rag: RAGAgent,
        config: Optional[ConfigurationAgent] = None,
        hydra_config: Optional[DictConfig] = None,
        logger: Optional[LoggerInterface] = None,
        test_runner: Optional[TestRunner] = None,
        stages: Optional[List[PipelineStage]] = None,
        supervisor: Optional[SupervisorAgent] = None,
        enable_supervision: bool = True,
        strategy: Optional[PipelineStrategy] = None,
        enable_observers: bool = True,
        resume: bool = False
    ):
        """
        Initialize orchestrator with dependency injection

        Args:
            card_id: Kanban card ID
            board: Kanban board instance
            messenger: Agent messenger for communication
            rag: RAG agent for learning
            config: Configuration agent (backward compatibility - deprecated)
            hydra_config: Hydra DictConfig (preferred configuration method)
            logger: Logger implementation (default: PipelineLogger)
            test_runner: Test runner (default: TestRunner)
            stages: List of pipeline stages (default: create standard stages)
            supervisor: Supervisor agent (default: create new SupervisorAgent)
            enable_supervision: Enable pipeline supervision (default: True)
            strategy: Pipeline execution strategy (default: StandardPipelineStrategy)
        """
        self.card_id = card_id
        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.resume = resume  # Checkpoint resume flag

        # Observer Pattern - Event broadcasting for pipeline events
        # (Create observable first, then pass to strategy)
        self.enable_observers = enable_observers
        self.observable = PipelineObservable(verbose=True) if enable_observers else None
        if self.enable_observers:
            # Attach default observers (Logging, Metrics, State Tracking)
            for observer in ObserverFactory.create_default_observers(verbose=True):
                self.observable.attach(observer)

        # Pipeline execution strategy (Strategy Pattern)
        # Pass observable to strategy so it can notify stage events
        self.strategy = strategy or StandardPipelineStrategy(
            verbose=True,
            observable=self.observable if enable_observers else None
        )

        # Support both old ConfigurationAgent and new Hydra config
        if hydra_config is not None:
            self.hydra_config = hydra_config
            self.config = None  # New Hydra path
            verbose = hydra_config.logging.verbose
        else:
            self.config = config or get_config(verbose=True)
            self.hydra_config = None  # Old config_agent path
            verbose = True

        self.verbose = verbose  # Store verbose flag for use in other methods
        self.logger = logger or PipelineLogger(verbose=verbose)
        self.test_runner = test_runner or TestRunner()

        # Supervisor agent for resilience and failover
        if hydra_config is not None:
            self.enable_supervision = hydra_config.pipeline.enable_supervision
        else:
            self.enable_supervision = enable_supervision

        self.supervisor = supervisor or (SupervisorAgent(
            logger=self.logger,
            messenger=self.messenger,
            card_id=self.card_id,
            rag=self.rag,  # Share RAG instance - enables learning without lock contention
            verbose=verbose,
            enable_cost_tracking=True,  # Track LLM costs
            enable_config_validation=True,  # Validate config at startup
            enable_sandboxing=True,  # Execute code safely
            daily_budget=10.00,  # $10/day budget
            monthly_budget=200.00  # $200/month budget
        ) if self.enable_supervision else None)

        # Enable learning capability (requires LLM client)
        if self.supervisor:
            try:
                from llm_client import LLMClientFactory
                llm = LLMClientFactory.create_from_env()  # Create from environment variables
                self.supervisor.enable_learning(llm)
                self.logger.log("✅ Supervisor learning enabled", "INFO")
            except ImportError:
                self.logger.log("⚠️  LLM client not available - supervisor learning disabled", "WARNING")
                # Continue without learning - supervisor still provides cost tracking and sandboxing
            except Exception as e:
                self.logger.log(f"⚠️  Could not enable supervisor learning: {e}", "WARNING")
                # Continue without learning - supervisor still provides cost tracking and sandboxing

        # Initialize LLM client for sprint workflow stages
        try:
            self.llm_client = LLMClient.create_from_env()
            self.logger.log("✅ LLM client initialized for sprint workflow", "INFO")
        except Exception as e:
            self.logger.log(f"⚠️  LLM client initialization failed: {e}", "WARNING")
            self.llm_client = None

        # Validate configuration (only for old config_agent)
        if self.config is not None:
            validation = self.config.validate_configuration(require_llm_key=True)
            if not validation.is_valid:
                self.logger.log("❌ Invalid configuration detected", "ERROR")
                # Log missing keys
                [self.logger.log(f"  Missing: {key}", "ERROR") for key in validation.missing_keys]
                # Log invalid keys
                [self.logger.log(f"  Invalid: {key}", "ERROR") for key in validation.invalid_keys]
                raise PipelineConfigurationError(
                    f"Invalid Artemis configuration",
                    context={
                        "missing_keys": validation.missing_keys,
                        "invalid_keys": validation.invalid_keys
                    }
                )
        # Hydra configs are validated at load time, no need to re-validate

        # Platform Detection and Resource Allocation
        self.platform_detector = PlatformDetector(logger=self.logger)
        self.platform_info = self.platform_detector.detect_platform()
        self.resource_allocation = self.platform_detector.calculate_resource_allocation(self.platform_info)

        # Store platform info in RAG and validate against stored data
        self._store_and_validate_platform_info()

        # Display platform information
        if self.verbose:
            summary = get_platform_summary(self.platform_info, self.resource_allocation)
            print(summary)

        # Initialize AI Orchestration Planner
        self.orchestration_planner = OrchestrationPlannerFactory.create_planner(
            llm_client=self.llm_client,
            logger=self.logger,
            prefer_ai=True  # Prefer AI planner, fallback to rule-based if unavailable
        )
        self.logger.log("✅ Orchestration planner initialized", "INFO")

        # Create stages if not injected (default pipeline)
        if stages is None:
            self.stages = self._create_default_stages()
        else:
            self.stages = stages

        # Register stages with supervisor for monitoring
        if self.enable_supervision and self.supervisor:
            self._register_stages_with_supervisor()

    def _register_stages_with_supervisor(self) -> None:
        """
        Register all stages with supervisor agent for monitoring

        Each stage gets custom recovery strategy based on its characteristics
        """
        # Requirements Parsing: LLM-heavy, needs more time
        self.supervisor.register_stage(
            "requirements_parsing",
            RecoveryStrategy(
                max_retries=MAX_RETRY_ATTEMPTS - 1,  # 2 retries
                retry_delay_seconds=DEFAULT_RETRY_INTERVAL_SECONDS,  # 5s
                timeout_seconds=STAGE_TIMEOUT_SECONDS / 15,  # 240s (4 min)
                circuit_breaker_threshold=MAX_RETRY_ATTEMPTS
            )
        )

        # Project Analysis: Fast, can retry quickly
        self.supervisor.register_stage(
            "project_analysis",
            RecoveryStrategy(
                max_retries=MAX_RETRY_ATTEMPTS - 1,  # 2 retries
                retry_delay_seconds=DEFAULT_RETRY_INTERVAL_SECONDS - 3.0,  # 2s
                timeout_seconds=STAGE_TIMEOUT_SECONDS / 30,  # 120s
                circuit_breaker_threshold=MAX_RETRY_ATTEMPTS
            )
        )

        # Architecture: Important, give more time
        self.supervisor.register_stage(
            "architecture",
            RecoveryStrategy(
                max_retries=MAX_RETRY_ATTEMPTS - 1,  # 2 retries
                retry_delay_seconds=DEFAULT_RETRY_INTERVAL_SECONDS,  # 5s
                timeout_seconds=STAGE_TIMEOUT_SECONDS / 20,  # 180s
                circuit_breaker_threshold=MAX_RETRY_ATTEMPTS
            )
        )

        # Dependencies: Fast validation
        self.supervisor.register_stage(
            "dependencies",
            RecoveryStrategy(
                max_retries=MAX_RETRY_ATTEMPTS - 1,  # 2 retries
                retry_delay_seconds=DEFAULT_RETRY_INTERVAL_SECONDS - 3.0,  # 2s
                timeout_seconds=STAGE_TIMEOUT_SECONDS / 60,  # 60s
                circuit_breaker_threshold=MAX_RETRY_ATTEMPTS
            )
        )

        # Development: Most critical, longer timeout
        self.supervisor.register_stage(
            "development",
            RecoveryStrategy(
                max_retries=MAX_RETRY_ATTEMPTS,  # 3 retries
                retry_delay_seconds=DEFAULT_RETRY_INTERVAL_SECONDS * 2,  # 10s
                backoff_multiplier=RETRY_BACKOFF_FACTOR,  # 2.0
                timeout_seconds=DEVELOPER_AGENT_TIMEOUT_SECONDS / 6,  # 600s (10 min)
                circuit_breaker_threshold=MAX_RETRY_ATTEMPTS + 2  # 5
            )
        )

        # Arbitration: Fast decision making, minimal retries
        self.supervisor.register_stage(
            "arbitration",
            RecoveryStrategy(
                max_retries=MAX_RETRY_ATTEMPTS - 1,  # 2 retries
                retry_delay_seconds=DEFAULT_RETRY_INTERVAL_SECONDS - 2.0,  # 3s
                timeout_seconds=STAGE_TIMEOUT_SECONDS / 30,  # 120s (2 min)
                circuit_breaker_threshold=MAX_RETRY_ATTEMPTS  # 3
            )
        )

        # Code Review: Can retry, moderate timeout
        self.supervisor.register_stage(
            "code_review",
            RecoveryStrategy(
                max_retries=MAX_RETRY_ATTEMPTS - 1,  # 2 retries
                retry_delay_seconds=DEFAULT_RETRY_INTERVAL_SECONDS,  # 5s
                timeout_seconds=CODE_REVIEW_TIMEOUT_SECONDS / 10,  # 180s
                circuit_breaker_threshold=MAX_RETRY_ATTEMPTS + 1  # 4
            )
        )

        # Validation: Fast, can retry
        self.supervisor.register_stage(
            "validation",
            RecoveryStrategy(
                max_retries=MAX_RETRY_ATTEMPTS - 1,  # 2 retries
                retry_delay_seconds=DEFAULT_RETRY_INTERVAL_SECONDS - 2.0,  # 3s
                timeout_seconds=STAGE_TIMEOUT_SECONDS / 30,  # 120s
                circuit_breaker_threshold=MAX_RETRY_ATTEMPTS
            )
        )

        # Integration: Important, moderate retry
        self.supervisor.register_stage(
            "integration",
            RecoveryStrategy(
                max_retries=MAX_RETRY_ATTEMPTS - 1,  # 2 retries
                retry_delay_seconds=DEFAULT_RETRY_INTERVAL_SECONDS,  # 5s
                timeout_seconds=STAGE_TIMEOUT_SECONDS / 20,  # 180s
                circuit_breaker_threshold=MAX_RETRY_ATTEMPTS
            )
        )

        # Testing: Can take time, longer timeout
        self.supervisor.register_stage(
            "testing",
            RecoveryStrategy(
                max_retries=MAX_RETRY_ATTEMPTS - 1,  # 2 retries
                retry_delay_seconds=DEFAULT_RETRY_INTERVAL_SECONDS,  # 5s
                timeout_seconds=STAGE_TIMEOUT_SECONDS / 12,  # 300s (5 min)
                circuit_breaker_threshold=MAX_RETRY_ATTEMPTS
            )
        )

    def _store_and_validate_platform_info(self) -> None:
        """
        Store platform information in RAG and validate against stored data

        Checks if stored platform matches current platform and logs warnings if changed.
        Stores complete platform info as RAG artifact for future reference.
        """
        try:
            # Query RAG for previously stored platform info
            stored_platform_data = self.rag.query(
                query="platform_info",
                collection_name="platform_metadata",
                n_results=1
            )

            stored_platform_hash = None
            if stored_platform_data and len(stored_platform_data.get('metadatas', [[]])[0]) > 0:
                # Extract stored platform hash
                stored_metadata = stored_platform_data['metadatas'][0][0]
                stored_platform_hash = stored_metadata.get('platform_hash')

                if stored_platform_hash:
                    # Compare platform hashes
                    if stored_platform_hash != self.platform_info.platform_hash:
                        # Platform has changed
                        self.logger.log("⚠️  Platform configuration has changed since last run!", "WARNING")
                        self.logger.log(f"   Previous platform hash: {stored_platform_hash}", "WARNING")
                        self.logger.log(f"   Current platform hash: {self.platform_info.platform_hash}", "WARNING")
                        self.logger.log("   Updating platform information in RAG...", "INFO")
                    else:
                        # Platform matches
                        self.logger.log("✅ Platform validation: Current platform matches stored configuration", "INFO")

            # Store/update platform information in RAG
            platform_data = self.platform_info.to_dict()
            allocation_data = self.resource_allocation.to_dict()

            # Combine into single document for RAG
            combined_data = {
                "platform": platform_data,
                "resource_allocation": allocation_data,
                "timestamp": datetime.now().isoformat(),
                "platform_hash": self.platform_info.platform_hash
            }

            # Store as RAG artifact
            self.rag.store_artifact(
                artifact_type="platform_metadata",
                content=json.dumps(combined_data, indent=2),
                metadata={
                    "platform_hash": self.platform_info.platform_hash,
                    "os_type": self.platform_info.os_type,
                    "cpu_cores": self.platform_info.cpu_count_logical,
                    "total_memory_gb": self.platform_info.total_memory_gb,
                    "max_parallel_developers": self.resource_allocation.max_parallel_developers,
                    "max_parallel_tests": self.resource_allocation.max_parallel_tests,
                    "timestamp": datetime.now().isoformat()
                },
                collection_name="platform_metadata"
            )

            if self.verbose:
                self.logger.log("✅ Platform information stored in RAG successfully", "INFO")

        except Exception as e:
            # Don't fail the entire pipeline if platform storage fails
            self.logger.log(f"⚠️  Failed to store/validate platform info in RAG: {e}", "WARNING")
            self.logger.log("   Continuing without platform validation...", "INFO")

    def _create_default_stages(self) -> List[PipelineStage]:
        """
        Create default pipeline stages with supervisor integration AND sprint workflow

        NEW Sprint-Based Workflow:
        0. RequirementsParsing - Parse free-form requirements → structured YAML/JSON
        1. SprintPlanning - Estimate features with Planning Poker, create sprints
        2. ProjectAnalysis - Analyze requirements
        3. Architecture - Design system (uses structured requirements)
        4. ProjectReview - Review & approve architecture (with feedback loop)
        5. Development - Multi-agent implementation
        6. CodeReview - Security, GDPR, accessibility
        7. UIUXStage - WCAG & GDPR compliance evaluation
        8. Validation - Test solutions
        9. Integration - Integrate winner
        10. Testing - Final tests
        11. Retrospective - Learn from sprint (handled separately)

        All stages receive supervisor for:
        - LLM cost tracking
        - Code execution sandboxing
        - Unexpected state handling and recovery
        - Dynamic heartbeat adjustment
        """
        stages = []

        # Initialize centralized AI Query Service (KG→RAG→LLM pipeline)
        ai_service = None
        if AI_QUERY_SERVICE_AVAILABLE and self.llm_client:
            try:
                self.logger.log("Initializing centralized AI Query Service...", "INFO")
                ai_service = create_ai_query_service(
                    llm_client=self.llm_client,
                    rag=self.rag,
                    logger=self.logger,
                    verbose=self.verbose
                )
                self.logger.log("✅ AI Query Service initialized successfully", "SUCCESS")
                self.logger.log("   All agents will use KG-First approach for token optimization", "INFO")
            except Exception as e:
                self.logger.log(f"⚠️  AI Query Service initialization failed: {e}", "WARNING")
                self.logger.log("   Agents will use direct LLM calls (no KG optimization)", "WARNING")
                ai_service = None

        # Initialize Intelligent Router for AI-powered stage selection
        self.intelligent_router = None
        if INTELLIGENT_ROUTER_AVAILABLE:
            try:
                self.logger.log("Initializing Intelligent Router for dynamic stage selection...", "INFO")
                self.intelligent_router = IntelligentRouter(
                    ai_service=ai_service,
                    logger=self.logger,
                    config=self.config
                )
                self.logger.log("✅ Intelligent Router initialized successfully", "SUCCESS")
                self.logger.log("   Pipeline will skip unnecessary stages based on task requirements", "INFO")
            except Exception as e:
                self.logger.log(f"⚠️  Intelligent Router initialization failed: {e}", "WARNING")
                self.logger.log("   Pipeline will run all standard stages", "WARNING")
                self.intelligent_router = None

        # Requirements Parsing (new) - Parse requirements documents first
        if self.llm_client:
            stages.append(
                RequirementsParsingStage(
                    logger=self.logger,
                    rag=self.rag,
                    messenger=self.messenger,
                    supervisor=self.supervisor
                    # Note: RequirementsParsingStage already integrated with AIQueryService
                )
            )

        # Sprint Planning (new) - Only if LLM client available
        if self.llm_client:
            stages.append(
                SprintPlanningStage(
                    self.board,
                    self.messenger,
                    self.rag,
                    self.logger,
                    self.llm_client,
                    config=self.config,
                    observable=self.observable,
                    supervisor=self.supervisor
                )
            )

        # Existing stages (now with AI Query Service)
        stages.extend([
            ProjectAnalysisStage(
                board=self.board,
                messenger=self.messenger,
                rag=self.rag,
                logger=self.logger,
                supervisor=self.supervisor,
                llm_client=self.llm_client,
                config=self.config
            )
        ])

        # Software Specification Document Generation (new) - After project analysis, before architecture
        # Intelligently decides if SSD is needed based on task complexity
        if self.llm_client:
            stages.append(
                SSDGenerationStage(
                    llm_client=self.llm_client,
                    rag=self.rag,
                    logger=self.logger,
                    verbose=self.verbose
                )
            )

        # Continue with remaining stages
        stages.extend([
            ArchitectureStage(
                self.board,
                self.messenger,
                self.rag,
                self.logger,
                supervisor=self.supervisor,
                llm_client=self.llm_client,
                ai_service=ai_service  # NEW: centralized KG-First service
            )
        ])

        # Project Review - Validate architecture and sprint plans
        if self.llm_client:
            stages.append(
                ProjectReviewStage(
                    self.board,
                    self.messenger,
                    self.rag,
                    self.logger,
                    self.llm_client,
                    config=self.config,
                    observable=self.observable,
                    supervisor=self.supervisor
                )
            )

        # Research Stage - Retrieve code examples before development
        # Searches GitHub, HuggingFace, and local filesystem for relevant examples
        # Stores examples in RAG for developers to query during implementation
        stages.append(
            ResearchStage(
                rag_agent=self.rag,
                sources=["local", "github", "huggingface"],
                max_examples_per_source=5,
                timeout_seconds=30
            )
        )

        # Continue with existing stages
        stages.extend([
            DependencyValidationStage(self.board, self.messenger, self.logger),
            DevelopmentStage(
                self.board,
                self.rag,
                self.logger,
                observable=self.observable,
                supervisor=self.supervisor
            ),
            # Arbitration - adjudicator selects winner when dev group (2+ developers) competes
            ArbitrationStage(
                logger=self.logger,
                messenger=None,  # Messenger doesn't support register_handler() - arbitration doesn't need it
                observable=self.observable,
                supervisor=self.supervisor,
                ai_service=ai_service
            ),
            # Validation tests ONLY the winner
            ValidationStage(
                self.board,
                self.test_runner,
                self.logger,
                messenger=self.messenger,
                observable=self.observable,
                supervisor=self.supervisor
            ),
            # UI/UX evaluates ONLY the winner (if needed)
            UIUXStage(
                self.board,
                self.messenger,
                self.rag,
                self.logger,
                observable=self.observable,
                supervisor=self.supervisor,
                config=self.config,
                ai_service=ai_service  # NEW: centralized KG-First service
            ),
            # Code Review reviews ONLY the winner
            CodeReviewStage(
                self.messenger,
                self.rag,
                self.logger,
                observable=self.observable,
                supervisor=self.supervisor,
                ai_service=ai_service  # NEW: centralized KG-First service
            ),
            # Integration and Testing proceed with winner
            IntegrationStage(
                self.board,
                self.messenger,
                self.rag,
                self.test_runner,
                self.logger,
                observable=self.observable,
                supervisor=self.supervisor
            ),
            TestingStage(self.board, self.messenger, self.rag, self.test_runner, self.logger)
        ])

        return stages

    def run_full_pipeline(self, max_retries: int = None) -> Dict:
        """
        Run complete Artemis pipeline using configured strategy.

        This method delegates execution to the strategy (Strategy Pattern)
        while handling pipeline-level concerns like card validation and reporting.

        Args:
            max_retries: Maximum number of retries for failed code reviews (default: MAX_RETRY_ATTEMPTS - 1)

        Returns:
            Dict with pipeline execution results
        """
        if max_retries is None:
            max_retries = MAX_RETRY_ATTEMPTS - 1  # Default: 2 retries

        # Start pipeline
        self.logger.log("=" * 60, "INFO")
        self.logger.log("🏹 ARTEMIS - STARTING AUTONOMOUS HUNT FOR OPTIMAL SOLUTION", "STAGE")
        self.logger.log(f"   Execution Strategy: {self.strategy.__class__.__name__}", "INFO")
        self.logger.log("=" * 60, "INFO")

        # Get card
        card, _ = self.board._find_card(self.card_id)
        if not card:
            self.logger.log(f"Card {self.card_id} not found", "ERROR")
            return {"status": "ERROR", "reason": "Card not found"}

        # Create AI-powered orchestration plan
        orchestration_plan = self.orchestration_planner.create_plan(
            card=card,
            platform_info=self.platform_info,
            resource_allocation=self.resource_allocation
        )

        # Convert OrchestrationPlan to dict for backward compatibility
        workflow_plan = orchestration_plan.to_dict()

        self.logger.log("📋 AI-GENERATED ORCHESTRATION PLAN", "INFO")
        self.logger.log(f"Complexity: {workflow_plan['complexity']}", "INFO")
        self.logger.log(f"Task Type: {workflow_plan['task_type']}", "INFO")
        self.logger.log(f"Parallel Developers: {workflow_plan['parallel_developers']}", "INFO")
        self.logger.log(f"Estimated Duration: {workflow_plan['estimated_duration_minutes']} minutes", "INFO")

        # Log AI reasoning
        if workflow_plan.get('reasoning'):
            self.logger.log("AI Reasoning:", "INFO")
            for reason in workflow_plan['reasoning']:
                self.logger.log(f"  • {reason}", "INFO")

        # Query RAG for historical context
        rag_recommendations = self.rag.get_recommendations(
            task_description=card.get('description', card.get('title', '')),
            context={'priority': card.get('priority'), 'complexity': workflow_plan['complexity']}
        )

        # Notify pipeline start
        self._notify_pipeline_start(card, workflow_plan)

        # Build execution context
        context = {
            'card_id': self.card_id,
            'card': card,
            'workflow_plan': workflow_plan,
            'rag_recommendations': rag_recommendations,
            'parallel_developers': workflow_plan['parallel_developers']
        }

        # Use intelligent routing if available
        if self.intelligent_router:
            routing_decision = self.intelligent_router.make_routing_decision(card)
            self.intelligent_router.log_routing_decision(routing_decision)

            # Update workflow plan with intelligent router's recommendations
            workflow_plan['parallel_developers'] = routing_decision.requirements.parallel_developers_recommended
            context['parallel_developers'] = routing_decision.requirements.parallel_developers_recommended

            # Filter stages using intelligent router
            stages_to_run = self.intelligent_router.filter_stages(self.stages, routing_decision)

            self.logger.log(f"🧠 Intelligent routing selected {len(stages_to_run)}/{len(self.stages)} stages", "INFO")
        else:
            # Fallback: Filter stages based on workflow plan
            stages_to_run = self._filter_stages_by_plan(workflow_plan)

        # Checkpoint resume logic
        if self.resume and self.checkpoint_manager.can_resume():
            checkpoint = self.checkpoint_manager.resume()
            self.logger.log(f"📥 Resuming from checkpoint: {len(checkpoint.stage_checkpoints)} stages completed", "INFO")

            # Get completed stages
            completed_stages = set(checkpoint.stage_checkpoints.keys())

            # Filter out completed stages
            original_count = len(stages_to_run)
            stages_to_run = [
                s for s in stages_to_run
                if s.__class__.__name__.replace('Stage', '').lower() not in completed_stages
            ]

            self.logger.log(f"⏭️  Skipping {len(completed_stages)} completed stages", "INFO")
            self.logger.log(f"▶️  Running {len(stages_to_run)} remaining stages", "INFO")
        else:
            # Execute pipeline using strategy (Strategy Pattern - delegates complexity)
            self.logger.log(f"▶️  Executing {len(stages_to_run)} stages...", "INFO")

        # Add orchestrator to context so strategy can access checkpoint_manager
        context['orchestrator'] = self

        execution_result = self.strategy.execute(stages_to_run, context)

        # Extract results
        stage_results = execution_result.get("results", {})
        final_status = execution_result.get("status")

        # Notify pipeline completion
        self._notify_pipeline_completion(card, stage_results)

        # Determine completion status
        if final_status == "success":
            self.logger.log("=" * 60, "INFO")
            self.logger.log("🎉 ARTEMIS HUNT SUCCESSFUL - OPTIMAL SOLUTION DELIVERED!", "SUCCESS")
            self.logger.log("=" * 60, "INFO")
            pipeline_status = "COMPLETED_SUCCESSFULLY"
        else:
            self.logger.log("=" * 60, "ERROR")
            self.logger.log(f"❌ ARTEMIS PIPELINE FAILED - {execution_result.get('error', 'Unknown error')}", "ERROR")
            self.logger.log("=" * 60, "ERROR")
            pipeline_status = "FAILED"
            # Notify pipeline failure
            error = Exception(execution_result.get('error', 'Unknown error'))
            self._notify_pipeline_failure(card, error, stage_results)

        # Print supervisor health report if supervision enabled
        if self.enable_supervision and self.supervisor:
            self.supervisor.print_health_report()

            # Cleanup any zombie processes
            cleaned = self.supervisor.cleanup_zombie_processes()
            if cleaned > 0:
                self.logger.log(f"🧹 Cleaned up {cleaned} zombie processes", "INFO")

        # Build final report
        supervisor_stats = self.supervisor.get_statistics() if self.enable_supervision and self.supervisor else None

        # Run Sprint Retrospective if LLM client available
        retrospective_report = None
        if self.llm_client and final_status == "success":
            try:
                self.logger.log("🔄 Conducting Sprint Retrospective...", "INFO")
                retrospective_report = self._run_retrospective(card, stage_results, context)
                self.logger.log("✅ Retrospective complete", "SUCCESS")
            except Exception as e:
                self.logger.log(f"⚠️  Retrospective failed: {e}", "WARNING")

        report = {
            "card_id": self.card_id,
            "workflow_plan": workflow_plan,
            "stages": stage_results,
            "status": pipeline_status,
            "execution_result": execution_result,
            "supervisor_statistics": supervisor_stats,
            "retrospective": retrospective_report
        }

        # Save report
        report_path = Path("/tmp") / f"pipeline_full_report_{self.card_id}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        self.logger.log(f"📄 Full report saved: {report_path}", "INFO")

        return report

    def run_all_pending_tasks(self, max_tasks: int = None) -> List[Dict]:
        """
        Process all pending tasks on the kanban board until complete

        This method implements the intelligent orchestrator pattern where
        the pipeline iterates over ALL tasks on the board, processes each one,
        and updates the board status accordingly.

        Args:
            max_tasks: Maximum number of tasks to process (None = all)

        Returns:
            List of pipeline reports for each processed task
        """
        self.logger.log("=" * 60, "INFO")
        self.logger.log("🔄 PROCESSING ALL PENDING TASKS ON KANBAN BOARD", "STAGE")
        self.logger.log("=" * 60, "INFO")

        all_reports = []
        task_count = 0

        # Loop until all tasks are complete or max reached
        while self.board.has_incomplete_cards():
            # Get pending cards (backlog + in-progress)
            pending_cards = self.board.get_pending_cards()

            if not pending_cards:
                self.logger.log("✅ No more pending tasks - board complete!", "SUCCESS")
                break

            if max_tasks and task_count >= max_tasks:
                self.logger.log(f"⚠️  Reached maximum task limit ({max_tasks})", "WARNING")
                break

            # Process next card
            card = pending_cards[0]  # Process in order
            card_id = card.get('card_id')
            card_title = card.get('title', 'Unknown')

            self.logger.log("", "INFO")
            self.logger.log("=" * 60, "INFO")
            self.logger.log(f"📋 PROCESSING TASK {task_count + 1}: {card_title}", "STAGE")
            self.logger.log(f"   Card ID: {card_id}", "INFO")
            self.logger.log("=" * 60, "INFO")

            # Temporarily switch card_id for this task
            original_card_id = self.card_id
            self.card_id = card_id

            try:
                # Run full pipeline for this card
                report = self.run_full_pipeline()
                all_reports.append(report)

                task_count += 1

                # Check if task completed successfully
                if report.get('status') == 'COMPLETED_SUCCESSFULLY':
                    self.logger.log(f"✅ Task {task_count} completed successfully", "SUCCESS")
                else:
                    self.logger.log(f"❌ Task {task_count} failed: {report.get('status')}", "ERROR")

            except Exception as e:
                self.logger.log(f"❌ Task {task_count + 1} failed with exception: {e}", "ERROR")
                all_reports.append({
                    "card_id": card_id,
                    "status": "FAILED_WITH_EXCEPTION",
                    "error": str(e)
                })
                task_count += 1

            finally:
                # Restore original card_id
                self.card_id = original_card_id

            # Brief pause between tasks
            self.logger.log("", "INFO")

        # Final summary
        self.logger.log("=" * 60, "INFO")
        self.logger.log("📊 BOARD PROCESSING COMPLETE", "STAGE")
        self.logger.log("=" * 60, "INFO")
        self.logger.log(f"Total tasks processed: {task_count}", "INFO")

        successful = sum(1 for r in all_reports if r.get('status') == 'COMPLETED_SUCCESSFULLY')
        failed = task_count - successful

        self.logger.log(f"✅ Successful: {successful}", "SUCCESS")
        if failed > 0:
            self.logger.log(f"❌ Failed: {failed}", "ERROR")

        # Save consolidated report
        consolidated_report = {
            "total_tasks_processed": task_count,
            "successful_tasks": successful,
            "failed_tasks": failed,
            "task_reports": all_reports,
            "completion_timestamp": datetime.utcnow().isoformat() + 'Z'
        }

        report_path = Path("/tmp") / "pipeline_board_processing_report.json"
        with open(report_path, 'w') as f:
            json.dump(consolidated_report, f, indent=2)

        self.logger.log(f"📄 Consolidated report saved: {report_path}", "INFO")
        self.logger.log("=" * 60, "INFO")

        return all_reports

    def _filter_stages_by_plan(self, workflow_plan: Dict) -> List[PipelineStage]:
        """Filter stages based on workflow plan"""
        stage_names_to_run = workflow_plan.get('stages', [])
        skip_stages = set(workflow_plan.get('skip_stages', []))

        # Map stage names to stage objects
        stage_map = {stage.get_stage_name(): stage for stage in self.stages}

        # Return stages in plan order, excluding skipped
        filtered = []
        for name in stage_names_to_run:
            if name not in skip_stages and name in stage_map:
                filtered.append(stage_map[name])

        return filtered

    def _notify_pipeline_start(self, card: Dict, workflow_plan: Dict):
        """Notify agents and observers that pipeline has started"""
        # Notify observers (Observer Pattern)
        if self.enable_observers:
            event = EventBuilder.pipeline_started(
                self.card_id,
                card_title=card.get('title'),
                workflow_plan=workflow_plan,
                complexity=workflow_plan.get('complexity'),
                parallel_developers=workflow_plan.get('parallel_developers')
            )
            self.observable.notify(event)

        # Legacy messenger notification (keep for backward compatibility)
        self.messenger.send_notification(
            to_agent="all",
            card_id=self.card_id,
            notification_type="pipeline_started",
            data={
                "card_title": card.get('title'),
                "workflow_plan": workflow_plan
            },
            priority="medium"
        )

        self.messenger.update_shared_state(
            card_id=self.card_id,
            updates={
                "pipeline_status": "running",
                "current_stage": "planning"
            }
        )

    def _notify_pipeline_completion(self, card: Dict, stage_results: Dict):
        """Notify agents and observers that pipeline completed"""
        # Notify observers (Observer Pattern)
        if self.enable_observers:
            event = EventBuilder.pipeline_completed(
                self.card_id,
                card_title=card.get('title'),
                stages_executed=len(stage_results),
                stage_results=stage_results
            )
            self.observable.notify(event)

        # Legacy messenger notification (keep for backward compatibility)
        self.messenger.send_notification(
            to_agent="all",
            card_id=self.card_id,
            notification_type="pipeline_completed",
            data={
                "status": "COMPLETED_SUCCESSFULLY",
                "stages_executed": len(stage_results)
            },
            priority="medium"
        )

        self.messenger.update_shared_state(
            card_id=self.card_id,
            updates={
                "pipeline_status": "complete",
                "current_stage": "done"
            }
        )

    def _notify_pipeline_failure(self, card: Dict, error: Exception, stage_results: Dict = None):
        """Notify agents and observers that pipeline failed"""
        # Notify observers (Observer Pattern)
        if self.enable_observers:
            event = EventBuilder.pipeline_failed(
                self.card_id,
                error=error,
                card_title=card.get('title'),
                stages_executed=len(stage_results) if stage_results else 0
            )
            self.observable.notify(event)

        # Legacy messenger notification (keep for backward compatibility)
        self.messenger.send_notification(
            to_agent="all",
            card_id=self.card_id,
            notification_type="pipeline_failed",
            data={
                "error": str(error),
                "stages_executed": len(stage_results) if stage_results else 0
            },
            priority="high"
        )

        self.messenger.update_shared_state(
            card_id=self.card_id,
            updates={
                "pipeline_status": "failed",
                "current_stage": "failed",
                "error": str(error)
            }
        )

    def _run_retrospective(self, card: Dict, stage_results: Dict, context: Dict) -> Dict:
        """
        Run sprint retrospective to learn from pipeline execution

        Args:
            card: Kanban card
            stage_results: Results from all stages
            context: Pipeline context

        Returns:
            Retrospective report dict
        """
        # Collect sprint metrics from stage results
        sprint_data = self._collect_sprint_metrics(card, stage_results, context)

        # Initialize retrospective agent
        retrospective = RetrospectiveAgent(
            llm_client=self.llm_client,
            rag=self.rag,
            logger=self.logger,
            messenger=self.messenger,
            historical_sprints_to_analyze=3
        )

        # Conduct retrospective
        report = retrospective.conduct_retrospective(
            sprint_number=1,  # TODO: Track sprint number in context
            sprint_data=sprint_data,
            card_id=self.card_id
        )

        # Convert to dict for JSON serialization
        return {
            "sprint_number": report.sprint_number,
            "overall_health": report.overall_health,
            "velocity": report.metrics.velocity,
            "velocity_trend": report.velocity_trend,
            "what_went_well_count": len(report.what_went_well),
            "what_didnt_go_well_count": len(report.what_didnt_go_well),
            "action_items_count": len(report.action_items),
            "key_learnings": report.key_learnings,
            "recommendations": report.recommendations
        }

    def _collect_sprint_metrics(self, card: Dict, stage_results: Dict, context: Dict) -> Dict:
        """
        Collect sprint metrics from pipeline execution

        Args:
            card: Kanban card
            stage_results: Stage execution results
            context: Pipeline context

        Returns:
            Sprint metrics dict
        """
        # Calculate story points (from sprint planning or estimate from card)
        planned_story_points = context.get('sprints', [{}])[0].get('total_story_points',
                                                                     card.get('story_points', 5))

        # Count completed vs failed stages
        total_stages = len(stage_results)
        completed_stages = sum(1 for result in stage_results.values()
                             if result.get('status') in ['PASS', 'success', 'completed'])

        # Estimate completion percentage
        completion_rate = (completed_stages / max(total_stages, 1)) * 100

        # Estimate completed story points based on completion rate
        completed_story_points = int(planned_story_points * (completion_rate / 100))

        # Extract test metrics if available
        testing_result = stage_results.get('testing', {})
        tests_passing = testing_result.get('test_pass_rate', 100.0)

        # Extract code review metrics
        code_review_result = stage_results.get('code_review', {})
        code_review_iterations = 1  # Default

        # Extract bugs from validation/testing
        bugs_found = 0
        bugs_fixed = 0
        validation_result = stage_results.get('validation', {})
        if validation_result:
            bugs_found = validation_result.get('issues_found', 0)
            bugs_fixed = validation_result.get('issues_fixed', 0)

        # Count blockers (stages that failed)
        blockers_encountered = total_stages - completed_stages

        return {
            "sprint_number": 1,
            "start_date": card.get('created_at', datetime.now().isoformat())[:10],
            "end_date": datetime.now().isoformat()[:10],
            "total_story_points": planned_story_points,
            "completed_story_points": completed_story_points,
            "bugs_found": bugs_found,
            "bugs_fixed": bugs_fixed,
            "test_pass_rate": tests_passing,
            "code_review_iterations": code_review_iterations,
            "average_task_duration_hours": 0,  # TODO: Calculate from stage durations
            "blockers_encountered": blockers_encountered
        }

    def get_pipeline_metrics(self) -> Optional[Dict]:
        """
        Get pipeline metrics from MetricsObserver

        Returns:
            Dict with pipeline metrics, or None if observers not enabled
        """
        if not self.enable_observers:
            return None

        # Find MetricsObserver in attached observers
        from pipeline_observer import MetricsObserver
        observer = next((obs for obs in self.observable._observers if isinstance(obs, MetricsObserver)), None)
        return observer.get_summary() if observer else None

    def get_pipeline_state(self) -> Optional[Dict]:
        """
        Get current pipeline state from StateTrackingObserver

        Returns:
            Dict with pipeline state, or None if observers not enabled
        """
        if not self.enable_observers:
            return None

        # Find StateTrackingObserver in attached observers
        from pipeline_observer import StateTrackingObserver
        observer = next((obs for obs in self.observable._observers if isinstance(obs, StateTrackingObserver)), None)
        return observer.get_state() if observer else None

    def _extract_code_review_feedback(self, code_review_result: Dict) -> Dict:
        """
        Extract detailed code review feedback for developers

        Args:
            code_review_result: Result from code review stage

        Returns:
            Dict with structured feedback including specific issues and recommendations
        """
        feedback = {
            'status': code_review_result.get('status', 'UNKNOWN'),
            'total_critical_issues': code_review_result.get('total_critical_issues', 0),
            'total_high_issues': code_review_result.get('total_high_issues', 0),
            'developer_reviews': []
        }

        # Extract detailed feedback from each developer's review
        reviews = code_review_result.get('reviews', [])
        for review in reviews:
            developer_name = review.get('developer', 'unknown')
            report_file = review.get('report_file', '')

            # Try to load full review report with detailed issues
            detailed_issues = []
            if report_file and Path(report_file).exists():
                try:
                    with open(report_file, 'r') as f:
                        full_review = json.load(f)
                        detailed_issues = full_review.get('issues', [])
                except Exception as e:
                    raise create_wrapped_exception(
                        e,
                        FileReadError,
                        "Could not load detailed code review report",
                        {
                            "report_file": report_file,
                            "developer": developer_name
                        }
                    )

            feedback['developer_reviews'].append({
                'developer': developer_name,
                'review_status': review.get('review_status', 'UNKNOWN'),
                'overall_score': review.get('overall_score', 0),
                'critical_issues': review.get('critical_issues', 0),
                'high_issues': review.get('high_issues', 0),
                'detailed_issues': detailed_issues,
                'report_file': report_file
            })

        return feedback

    def _store_retry_feedback_in_rag(self, card: Dict, code_review_result: Dict, retry_attempt: int):
        """
        Store code review failure feedback in RAG for developer context

        Args:
            card: Kanban card with task details
            code_review_result: Result from failed code review
            retry_attempt: Current retry attempt number
        """
        try:
            card_id = card['card_id']
            task_title = card.get('title', 'Unknown Task')

            # Extract detailed feedback
            feedback = self._extract_code_review_feedback(code_review_result)

            # Create comprehensive failure report
            content = f"""Code Review Retry Feedback - Attempt {retry_attempt}

Task: {task_title}
Card ID: {card_id}
Review Status: {feedback['status']}
Critical Issues: {feedback['total_critical_issues']}
High Issues: {feedback['total_high_issues']}

DETAILED ISSUES BY DEVELOPER:

"""

            # Add detailed issues for each developer
            for dev_review in feedback['developer_reviews']:
                developer_name = dev_review['developer']
                content += f"\n{'='*60}\n"
                content += f"Developer: {developer_name}\n"
                content += f"Review Status: {dev_review['review_status']}\n"
                content += f"Score: {dev_review['overall_score']}/100\n"
                content += f"Critical Issues: {dev_review['critical_issues']}\n"
                content += f"High Issues: {dev_review['high_issues']}\n"
                content += f"{'='*60}\n\n"

                # Add top 10 most critical issues
                detailed_issues = dev_review.get('detailed_issues', [])
                if detailed_issues:
                    # Sort by severity (CRITICAL > HIGH > MEDIUM > LOW)
                    severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
                    sorted_issues = sorted(
                        detailed_issues,
                        key=lambda x: severity_order.get(x.get('severity', 'LOW'), 4)
                    )

                    content += "TOP ISSUES TO FIX:\n\n"
                    for i, issue in enumerate(sorted_issues[:10], 1):
                        content += f"{i}. [{issue.get('severity', 'UNKNOWN')}] {issue.get('category', 'Unknown Category')}\n"
                        content += f"   File: {issue.get('file', 'Unknown')}"
                        if issue.get('line'):
                            content += f":{issue.get('line')}"
                        content += "\n"
                        content += f"   Problem: {issue.get('description', 'No description')}\n"
                        content += f"   Fix: {issue.get('recommendation', 'No recommendation')}\n"
                        if issue.get('adr_reference'):
                            content += f"   ADR Reference: {issue.get('adr_reference')}\n"
                        content += "\n"

                content += "\n"

            # Add refactoring suggestions if available
            refactoring_suggestions = code_review_result.get('refactoring_suggestions')
            if refactoring_suggestions:
                content += f"\n{'='*60}\n"
                content += "REFACTORING INSTRUCTIONS\n"
                content += f"{'='*60}\n\n"
                content += refactoring_suggestions
                content += "\n"

            # Store in RAG
            artifact_id = self.rag.store_artifact(
                artifact_type="code_review_retry_feedback",
                card_id=card_id,
                task_title=task_title,
                content=content,
                metadata={
                    'retry_attempt': retry_attempt,
                    'review_status': feedback['status'],
                    'total_critical_issues': feedback['total_critical_issues'],
                    'total_high_issues': feedback['total_high_issues'],
                    'developers': [r['developer'] for r in feedback['developer_reviews']],
                    'has_refactoring_suggestions': refactoring_suggestions is not None
                }
            )

            self.logger.log(f"Stored retry feedback in RAG: {artifact_id}", "DEBUG")

        except Exception as e:
            raise create_wrapped_exception(
                e,
                RAGStorageError,
                "Failed to store retry feedback in RAG",
                {
                    "card_id": card_id,
                    "task_title": task_title,
                    "retry_attempt": retry_attempt,
                    "critical_issues": feedback['total_critical_issues'],
                    "high_issues": feedback['total_high_issues']
                }
            )


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def display_workflow_status(card_id: str, json_output: bool = False):
    """Display workflow status for a given card ID"""
    from workflow_status_tracker import WorkflowStatusTracker

    tracker = WorkflowStatusTracker(card_id=card_id)
    status_file = tracker.status_file

    if not status_file.exists():
        print(f"\n⚠️  No workflow status found for card: {card_id}")
        print(f"   Status file would be: {status_file}")
        print(f"   This workflow may not have started yet, or status tracking wasn't enabled.\n")
        return

    with open(status_file, 'r') as f:
        status_data = json.load(f)

    if json_output:
        print(json.dumps(status_data, indent=2))
        return

    # Human-readable output
    print(f"\n{'='*70}")
    print(f"🏹 ARTEMIS WORKFLOW STATUS")
    print(f"{'='*70}")
    print(f"Card ID: {status_data['card_id']}")
    print(f"Status: {status_data['status'].upper()}")

    if status_data.get('current_stage'):
        print(f"Current Stage: {status_data['current_stage']}")

    if status_data.get('start_time'):
        print(f"Started: {status_data['start_time']}")

    if status_data.get('end_time'):
        print(f"Completed: {status_data['end_time']}")

    if status_data.get('error'):
        print(f"\n❌ ERROR: {status_data['error']}")

    # Display stages
    if status_data.get('stages'):
        print(f"\n{'-'*70}")
        print("STAGES:")
        print(f"{'-'*70}")

        for i, stage in enumerate(status_data['stages'], 1):
            status_icons = {
                'pending': '⏸️',
                'in_progress': '🔄',
                'completed': '✅',
                'failed': '❌',
                'skipped': '⏭️'
            }
            icon = status_icons.get(stage['status'], '❓')
            print(f"\n{i}. {icon} {stage['name']}")
            print(f"   Status: {stage['status']}")

            if stage.get('start_time'):
                print(f"   Started: {stage['start_time']}")
            if stage.get('end_time'):
                print(f"   Completed: {stage['end_time']}")
            if stage.get('error'):
                print(f"   ❌ Error: {stage['error']}")

    print(f"\n{'='*70}\n")


def list_active_workflows():
    """List all active workflows"""
    from pathlib import Path

    status_dir = Path("/tmp/artemis_status")
    if not status_dir.exists():
        print("\nNo active workflows found.\n")
        return

    status_files = list(status_dir.glob("*.json"))
    if not status_files:
        print("\nNo active workflows found.\n")
        return

    print(f"\n{'='*70}")
    print("🏹 ACTIVE ARTEMIS WORKFLOWS")
    print(f"{'='*70}\n")

    for status_file in sorted(status_files):
        card_id = status_file.stem
        with open(status_file, 'r') as f:
            data = json.load(f)

        if data['status'] in ['running', 'failed']:
            status_str = data['status'].upper()
            print(f"📋 {card_id}")
            print(f"   Status: {status_str}")
            if data.get('current_stage'):
                print(f"   Current: {data['current_stage']}")
            print()

    print(f"{'='*70}\n")


def _get_config_path() -> str:
    """Get absolute path to Hydra config directory.

    This allows the orchestrator to be run from any directory,
    not just from .agents/agile.

    Returns:
        Absolute path to the conf directory
    """
    script_dir = Path(__file__).parent
    return str(script_dir / "conf")


@hydra.main(version_base=None, config_path=_get_config_path(), config_name="config")
def main_hydra(cfg: DictConfig) -> None:
    """
    Hydra-powered entry point with type-safe configuration

    Usage:
        python artemis_orchestrator.py card_id=card-001
        python artemis_orchestrator.py card_id=card-002 llm.provider=anthropic
        python artemis_orchestrator.py --config-name env/dev +card_id=dev-001
    """
    # Print configuration
    if cfg.logging.verbose:
        print("\n" + "="*70)
        print("🏹 ARTEMIS PIPELINE ORCHESTRATOR (Hydra-Powered)")
        print("="*70)
        print(f"\nCard ID: {cfg.card_id}")
        print(f"LLM: {cfg.llm.provider} ({cfg.llm.model})")
        print(f"Pipeline: {len(cfg.pipeline.stages)} stages")
        print(f"Max Parallel Developers: {cfg.pipeline.max_parallel_developers}")
        print(f"Code Review: {'Enabled' if cfg.pipeline.enable_code_review else 'Disabled'}")
        print(f"Supervision: {'Enabled' if cfg.pipeline.enable_supervision else 'Disabled'}")
        print("="*70 + "\n")

    # Initialize dependencies (Dependency Injection)
    board = KanbanBoard()

    # Initialize logger before debug service
    logger = PipelineLogger(verbose=cfg.logging.verbose)

    # Initialize Debug Service (supports Hydra config + environment variables)
    debug_config = cfg.get('debug', None) if hasattr(cfg, 'debug') else None
    DebugService.initialize(
        config=debug_config,
        logger=logger,
        cli_debug=None  # Hydra mode: CLI overrides via config
    )

    # Create messenger using factory (pluggable implementation)
    messenger = MessengerFactory.create_from_env(
        agent_name="artemis-orchestrator"
    )

    rag = RAGAgent(db_path=cfg.storage.rag_db_path, verbose=cfg.logging.verbose)

    # Register orchestrator
    messenger.register_agent(
        capabilities=["coordinate_pipeline", "manage_workflow"],
        status="active"
    )

    try:
        # Create orchestrator with Hydra config
        orchestrator = ArtemisOrchestrator(
            card_id=cfg.card_id,
            board=board,
            messenger=messenger,
            rag=rag,
            hydra_config=cfg
        )

        # Run full pipeline
        result = orchestrator.run_full_pipeline()
        print(f"\n✅ Pipeline completed: {result['status']}")

    except Exception as e:
        raise create_wrapped_exception(
            e,
            PipelineStageError,
            "Pipeline orchestrator execution failed",
            {
                "card_id": cfg.card_id
            }
        )


def main_legacy():
    """Legacy CLI entry point (backward compatibility with old argparse interface)"""
    import argparse

    parser = argparse.ArgumentParser(description="Artemis Pipeline Orchestrator")
    parser.add_argument("--card-id", help="Kanban card ID")
    parser.add_argument("--full", action="store_true", help="Run full pipeline")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint (if available)")
    parser.add_argument("--requirements-file", help="Path to requirements document (PDF, Word, Excel, text, etc.)")
    parser.add_argument("--config-report", action="store_true", help="Show configuration report")
    parser.add_argument("--skip-validation", action="store_true", help="Skip config validation (not recommended)")
    parser.add_argument("--status", action="store_true", help="Show workflow status for card-id")
    parser.add_argument("--list-active", action="store_true", help="List all active workflows")
    parser.add_argument("--json", action="store_true", help="Output status in JSON format")
    parser.add_argument("--debug", nargs='?', const='default', metavar='PROFILE',
                       help="Enable debug mode (optional profile: verbose, minimal, default)")
    parser.add_argument("--debug-profile", help="Debug profile to use (verbose, minimal, default)")
    args = parser.parse_args()

    # Handle status queries (don't require config)
    if args.list_active:
        list_active_workflows()
        return

    if args.status:
        if not args.card_id:
            print("\n❌ Error: --card-id is required with --status\n")
            sys.exit(1)
        display_workflow_status(args.card_id, json_output=args.json)
        return

    # Load and validate configuration
    config = get_config(verbose=True)

    if args.config_report:
        config.print_configuration_report()
        return

    # Require card-id OR requirements-file for pipeline execution
    if not args.card_id and not args.requirements_file:
        print("\n❌ Error: --card-id or --requirements-file is required for pipeline execution\n")
        parser.print_help()
        sys.exit(1)

    # Validate configuration before proceeding
    if not args.skip_validation:
        validation = config.validate_configuration(require_llm_key=True)
        if not validation.is_valid:
            print("\n" + "="*80)
            print("❌ CONFIGURATION ERROR")
            print("="*80)
            print("\nThe pipeline cannot run due to invalid configuration.\n")

            if validation.missing_keys:
                print("Missing Required Keys:")
                # Display missing keys with descriptions
                [print(f"  ❌ {key}\n     Description: {config.CONFIG_SCHEMA.get(key, {}).get('description', 'N/A')}")
                 for key in validation.missing_keys]

                # Provide helpful hints
                provider = config.get('ARTEMIS_LLM_PROVIDER', 'openai')
                if 'OPENAI_API_KEY' in validation.missing_keys:
                    print(f"\n💡 Set your OpenAI API key:")
                    print(f"   export OPENAI_API_KEY='your-key-here'")
                if 'ANTHROPIC_API_KEY' in validation.missing_keys:
                    print(f"\n💡 Set your Anthropic API key:")
                    print(f"   export ANTHROPIC_API_KEY='your-key-here'")

            if validation.invalid_keys:
                print("\nInvalid Configuration Values:")
                [print(f"  ❌ {key}") for key in validation.invalid_keys]

            print("\n" + "="*80)
            print("\n💡 Run with --config-report to see full configuration")
            print("💡 Run with --skip-validation to bypass (NOT RECOMMENDED)\n")
            sys.exit(1)

    # Initialize dependencies (Dependency Injection)
    board = KanbanBoard()

    # Initialize logger before debug service
    logger = PipelineLogger(verbose=True)

    # Initialize Debug Service (supports CLI + environment variables)
    # Determine debug CLI value (priority: --debug-profile > --debug)
    cli_debug_value = args.debug_profile or args.debug
    DebugService.initialize(
        config=None,  # Legacy mode: no Hydra config
        logger=logger,
        cli_debug=cli_debug_value
    )

    # Create messenger using factory (pluggable implementation)
    messenger = MessengerFactory.create_from_env(
        agent_name="artemis-orchestrator"
    )

    rag_db_path = config.get('ARTEMIS_RAG_DB_PATH', 'db')
    rag = RAGAgent(db_path=rag_db_path, verbose=True)

    # Register orchestrator
    messenger.register_agent(
        capabilities=["coordinate_pipeline", "manage_workflow"],
        status="active"
    )

    try:
        # Performance: Dict dispatch for O(1) requirements handling strategy selection
        def _create_card_from_requirements():
            """Strategy: Create new card from requirements file (autonomous mode)"""
            from requirements_parser_agent import RequirementsParserAgent
            from document_reader import DocumentReader
            import os
            from datetime import datetime

            print(f"\n🤖 Autonomous Mode: Creating card from requirements file...")
            print(f"📄 Reading: {args.requirements_file}")

            # Read requirements document
            doc_reader = DocumentReader(verbose=False)
            requirements_text = doc_reader.read_document(args.requirements_file)

            # Parse requirements with AI
            parser = RequirementsParserAgent(
                llm_provider=config.get('ARTEMIS_LLM_PROVIDER', 'openai'),
                llm_model=config.get('ARTEMIS_LLM_MODEL', 'gpt-4'),
                rag=rag
            )

            parsed_reqs = parser.parse_requirements_file(args.requirements_file)

            # Extract title: prefer project_name, then first functional requirement, then filename
            filename_without_ext = Path(args.requirements_file).stem
            filename_as_title = filename_without_ext.replace('_', ' ').replace('-', ' ').title()

            if parsed_reqs.project_name and parsed_reqs.project_name != filename_as_title:
                # Use project_name if it's explicitly set and not just derived from filename
                title = parsed_reqs.project_name
            elif parsed_reqs.functional_requirements:
                # Fall back to first functional requirement title
                title = parsed_reqs.functional_requirements[0].title
            else:
                # Last resort: use filename
                title = filename_as_title

            # Generate unique card ID
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            card_id = f"auto-{timestamp}"

            # Determine priority from highest priority functional requirement
            # Map RequirementsParser priorities to KanbanManager priorities
            priority_map = {
                'critical': 'high',     # critical → high
                'high': 'high',         # high → high
                'medium': 'medium',     # medium → medium
                'low': 'low',           # low → low
                'nice_to_have': 'low'   # nice_to_have → low
            }

            priority = 'medium'
            if parsed_reqs.functional_requirements:
                # Get highest priority (critical > high > medium > low > nice_to_have)
                priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'nice_to_have': 4}
                priorities = [req.priority.value for req in parsed_reqs.functional_requirements]
                highest_priority = min(priorities, key=lambda p: priority_order.get(p, 2))
                priority = priority_map.get(highest_priority, 'medium')

            # Calculate story points based on number of requirements
            # Must use Fibonacci numbers: [1, 2, 3, 5, 8, 13]
            total_reqs = len(parsed_reqs.functional_requirements) + len(parsed_reqs.non_functional_requirements)
            fibonacci = [1, 2, 3, 5, 8, 13]
            # Find closest Fibonacci number
            story_points = min(fibonacci, key=lambda x: abs(x - total_reqs))

            # Create card using builder pattern
            card = (board.new_card(card_id, title)
                   .with_description(parsed_reqs.executive_summary or requirements_text[:500])
                   .with_priority(priority)
                   .with_story_points(story_points)
                   .build())

            # Add requirements file reference
            card['requirements_file'] = args.requirements_file
            card['metadata'] = card.get('metadata', {})
            card['metadata']['auto_created'] = True
            card['metadata']['created_from'] = args.requirements_file

            board.add_card(card)

            print(f"✅ Created card: {card_id}")
            print(f"   Title: {title}")
            print(f"   Priority: {card['priority']}")
            print(f"   Story Points: {card['story_points']}")

            return card_id

        def _attach_requirements_to_card():
            """Strategy: Attach requirements file to existing card"""
            card, _ = board._find_card(args.card_id)
            if card:
                board.update_card(args.card_id, {"requirements_file": args.requirements_file})
                print(f"✅ Added requirements file to card: {args.requirements_file}")
            else:
                print(f"⚠️  Card {args.card_id} not found - requirements file will be used from context")
            return args.card_id

        def _use_existing_card():
            """Strategy: Use existing card without requirements file"""
            return args.card_id

        # Performance: O(1) strategy dispatch using dict instead of O(n) if/elif chain
        requirements_strategy = {
            (True, False): _create_card_from_requirements,    # requirements file, no card
            (True, True): _attach_requirements_to_card,       # requirements file + card
            (False, True): _use_existing_card,                # card only
        }

        # Execute appropriate strategy
        strategy_key = (bool(args.requirements_file), bool(args.card_id))
        handler = requirements_strategy.get(strategy_key)

        if handler:
            args.card_id = handler()

        # Create orchestrator with injected dependencies
        orchestrator = ArtemisOrchestrator(
            card_id=args.card_id,
            board=board,
            messenger=messenger,
            rag=rag,
            config=config,
            resume=args.resume
        )

        # Run pipeline
        if args.full:
            result = orchestrator.run_full_pipeline()
            print(f"\n✅ Pipeline completed: {result['status']}")
        else:
            print("Use --full to run the complete pipeline")

    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("💡 Run with --config-report to see full configuration\n")
        sys.exit(1)
    except Exception as e:
        raise create_wrapped_exception(
            e,
            PipelineStageError,
            "Pipeline orchestrator execution failed",
            {
                "card_id": args.card_id
            }
        )


if __name__ == "__main__":
    # Use Hydra by default (check if Hydra args are present)
    if len(sys.argv) > 1 and ('=' in ' '.join(sys.argv[1:]) or '--config-name' in sys.argv):
        # Hydra mode: card_id=xxx or --config-name
        main_hydra()
    else:
        # Legacy mode: --card-id xxx --full
        main_legacy()
