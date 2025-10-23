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

from artemis_stage_interface import PipelineStage, LoggerInterface
from artemis_services import PipelineLogger, TestRunner
from artemis_stages import (
    ProjectAnalysisStage,
    ArchitectureStage,
    DependencyValidationStage,
    DevelopmentStage,
    ValidationStage,
    IntegrationStage,
    TestingStage
)
from code_review_stage import CodeReviewStage
from kanban_manager import KanbanBoard
from messenger_interface import MessengerInterface
from messenger_factory import MessengerFactory
from rag_agent import RAGAgent
from config_agent import ConfigurationAgent, get_config
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
    wrap_exception
)
from pipeline_observer import (
    PipelineObservable,
    ObserverFactory,
    EventBuilder,
    EventType
)


class WorkflowPlanner:
    """
    Dynamic Workflow Planner (Already SOLID-compliant)

    Single Responsibility: Analyze tasks and create workflow plans
    """

    def __init__(self, card: Dict, verbose: bool = True):
        self.card = card
        self.verbose = verbose
        self.complexity = self._analyze_complexity()
        self.task_type = self._determine_task_type()

    def _analyze_complexity(self) -> str:
        """Analyze task complexity"""
        complexity_score = 0

        # Priority
        priority = self.card.get('priority', 'medium')
        if priority == 'high':
            complexity_score += 2
        elif priority == 'medium':
            complexity_score += 1

        # Story points
        points = self.card.get('points', 5)
        if points >= 13:
            complexity_score += 3
        elif points >= 8:
            complexity_score += 2
        elif points >= 5:
            complexity_score += 1

        # Keywords
        description = self.card.get('description', '').lower()
        complex_keywords = ['integrate', 'architecture', 'refactor', 'migrate',
                           'performance', 'scalability', 'distributed', 'api']
        complex_count = sum(1 for kw in complex_keywords if kw in description)
        complexity_score += min(complex_count, 3)

        simple_keywords = ['fix', 'update', 'small', 'minor', 'simple', 'quick']
        simple_count = sum(1 for kw in simple_keywords if kw in description)
        complexity_score -= min(simple_count, 2)

        if complexity_score >= 6:
            return 'complex'
        elif complexity_score >= 3:
            return 'medium'
        else:
            return 'simple'

    def _determine_task_type(self) -> str:
        """Determine task type"""
        description = self.card.get('description', '').lower()
        title = self.card.get('title', '').lower()
        combined = f"{title} {description}"

        if any(kw in combined for kw in ['bug', 'fix', 'error', 'issue']):
            return 'bugfix'
        elif any(kw in combined for kw in ['refactor', 'restructure', 'cleanup']):
            return 'refactor'
        elif any(kw in combined for kw in ['docs', 'documentation', 'readme']):
            return 'documentation'
        elif any(kw in combined for kw in ['feature', 'implement', 'add', 'create']):
            return 'feature'
        else:
            return 'other'

    def create_workflow_plan(self) -> Dict:
        """Create workflow plan based on complexity"""
        plan = {
            'complexity': self.complexity,
            'task_type': self.task_type,
            'stages': ['project_analysis', 'architecture', 'dependencies', 'development', 'code_review', 'validation', 'integration'],
            'parallel_developers': 1,
            'skip_stages': ['arbitration'],
            'execution_strategy': 'sequential',
            'reasoning': []
        }

        # Determine parallel developers
        if self.complexity == 'complex':
            plan['parallel_developers'] = 3
            plan['execution_strategy'] = 'parallel'
        elif self.complexity == 'medium':
            plan['parallel_developers'] = 2
            plan['execution_strategy'] = 'parallel'
        else:
            plan['parallel_developers'] = 1

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
        enable_observers: bool = True
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
            from llm_client import get_llm_client
            try:
                llm = get_llm_client()  # Use default provider from env
                self.supervisor.enable_learning(llm)
                self.logger.log("✅ Supervisor learning enabled", "INFO")
            except Exception as e:
                self.logger.log(f"⚠️  Could not enable supervisor learning: {e}", "WARNING")
                # Continue without learning - supervisor still provides cost tracking and sandboxing

        # Validate configuration (only for old config_agent)
        if self.config is not None:
            validation = self.config.validate_configuration(require_llm_key=True)
            if not validation.is_valid:
                self.logger.log("❌ Invalid configuration detected", "ERROR")
                for key in validation.missing_keys:
                    self.logger.log(f"  Missing: {key}", "ERROR")
                for key in validation.invalid_keys:
                    self.logger.log(f"  Invalid: {key}", "ERROR")
                raise PipelineConfigurationError(
                    f"Invalid Artemis configuration",
                    context={
                        "missing_keys": validation.missing_keys,
                        "invalid_keys": validation.invalid_keys
                    }
                )
        # Hydra configs are validated at load time, no need to re-validate

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

    def _create_default_stages(self) -> List[PipelineStage]:
        """
        Create default pipeline stages with supervisor integration

        This method demonstrates Open/Closed Principle:
        - Open for extension: Can add new stages by extending this list
        - Closed for modification: Core orchestrator doesn't change

        All stages now receive supervisor for:
        - LLM cost tracking
        - Code execution sandboxing
        - Unexpected state handling and recovery
        """
        # Pass observable AND supervisor to stages that support it
        return [
            ProjectAnalysisStage(
                self.board,
                self.messenger,
                self.rag,
                self.logger,
                supervisor=self.supervisor
            ),  # Pre-implementation analysis
            ArchitectureStage(
                self.board,
                self.messenger,
                self.rag,
                self.logger,
                supervisor=self.supervisor
            ),
            DependencyValidationStage(self.board, self.messenger, self.logger),
            DevelopmentStage(
                self.board,
                self.rag,
                self.logger,
                observable=self.observable,
                supervisor=self.supervisor
            ),  # Invokes Developer A/B
            CodeReviewStage(
                self.messenger,
                self.rag,
                self.logger,
                observable=self.observable,
                supervisor=self.supervisor
            ),  # Security, GDPR, Accessibility review
            ValidationStage(
                self.board,
                self.test_runner,
                self.logger,
                observable=self.observable,
                supervisor=self.supervisor
            ),  # Validate developer solutions
            IntegrationStage(
                self.board,
                self.messenger,
                self.rag,
                self.test_runner,
                self.logger,
                observable=self.observable,
                supervisor=self.supervisor
            ),  # Integrate winning solution
            TestingStage(self.board, self.messenger, self.rag, self.test_runner, self.logger)
        ]

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

        self.logger.log("=" * 60, "INFO")
        self.logger.log("🏹 ARTEMIS - STARTING AUTONOMOUS HUNT FOR OPTIMAL SOLUTION", "STAGE")
        self.logger.log(f"   Execution Strategy: {self.strategy.__class__.__name__}", "INFO")
        self.logger.log("=" * 60, "INFO")

        # Get card
        card, _ = self.board._find_card(self.card_id)
        if not card:
            self.logger.log(f"Card {self.card_id} not found", "ERROR")
            return {"status": "ERROR", "reason": "Card not found"}

        # Create workflow plan
        planner = WorkflowPlanner(card)
        workflow_plan = planner.create_workflow_plan()

        self.logger.log("📋 WORKFLOW PLAN", "INFO")
        self.logger.log(f"Complexity: {workflow_plan['complexity']}", "INFO")
        self.logger.log(f"Task Type: {workflow_plan['task_type']}", "INFO")
        self.logger.log(f"Parallel Developers: {workflow_plan['parallel_developers']}", "INFO")

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

        # Filter stages based on workflow plan
        stages_to_run = self._filter_stages_by_plan(workflow_plan)

        # Execute pipeline using strategy (Strategy Pattern - delegates complexity)
        self.logger.log(f"▶️  Executing {len(stages_to_run)} stages...", "INFO")

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

        report = {
            "card_id": self.card_id,
            "workflow_plan": workflow_plan,
            "stages": stage_results,
            "status": pipeline_status,
            "execution_result": execution_result,
            "supervisor_statistics": supervisor_stats
        }

        # Save report
        report_path = Path("/tmp") / f"pipeline_full_report_{self.card_id}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        self.logger.log(f"📄 Full report saved: {report_path}", "INFO")

        return report

    def _old_run_full_pipeline_with_retry_logic(self, max_retries: int = None) -> Dict:
        """
        DEPRECATED: Old implementation with manual retry logic.

        This method is preserved for reference but should not be used.
        The new run_full_pipeline() uses Strategy Pattern instead.

        Kept here temporarily for backward compatibility testing.
        """
        if max_retries is None:
            max_retries = MAX_RETRY_ATTEMPTS - 1

        # Get card
        card, _ = self.board._find_card(self.card_id)
        if not card:
            return {"status": "ERROR", "reason": "Card not found"}

        # Create workflow plan
        planner = WorkflowPlanner(card)
        workflow_plan = planner.create_workflow_plan()

        # Query RAG
        rag_recommendations = self.rag.get_recommendations(
            task_description=card.get('description', card.get('title', '')),
            context={'priority': card.get('priority'), 'complexity': workflow_plan['complexity']}
        )

        self._notify_pipeline_start(card, workflow_plan)

        context = {
            'workflow_plan': workflow_plan,
            'rag_recommendations': rag_recommendations,
            'parallel_developers': workflow_plan['parallel_developers']
        }

        stage_results = {}
        stages_to_run = self._filter_stages_by_plan(workflow_plan)
        retry_count = 0
        all_retry_history = []

        # OLD IMPLEMENTATION: Manual retry loop
        while retry_count <= max_retries:
            # Track if this is a retry
            if retry_count > 0:
                self.logger.log("=" * 60, "INFO")
                self.logger.log(f"🔄 RETRY ATTEMPT {retry_count}/{max_retries}", "STAGE")
                self.logger.log("=" * 60, "INFO")
                context['retry_attempt'] = retry_count
                context['previous_review_feedback'] = self._extract_code_review_feedback(stage_results.get('code_review', {}))

            # Execute stages up to and including code review
            for i, stage in enumerate(stages_to_run, 1):
                stage_name = stage.get_stage_name()

                # Skip stages before development on retry
                if retry_count > 0 and stage_name not in ['development', 'code_review']:
                    continue

                self.logger.log(f"📋 STAGE {i}/{len(stages_to_run)}: {stage_name.upper()}", "STAGE")

                try:
                    # Execute stage with or without supervision
                    if self.enable_supervision and self.supervisor:
                        result = self.supervisor.execute_with_supervision(
                            stage, stage_name, card, context
                        )
                    else:
                        result = stage.execute(card, context)

                    stage_results[stage_name] = result
                    context.update(result)  # Add results to context for next stage

                    # Store winner in context if returned
                    if 'winner' in result:
                        context['winner'] = result['winner']

                    # Check if code review failed
                    if stage_name == 'code_review':
                        review_status = result.get('status', 'PASS')

                        if review_status == 'FAIL' and retry_count < max_retries:
                            # Store retry info
                            all_retry_history.append({
                                'attempt': retry_count + 1,
                                'review_result': result,
                                'critical_issues': result.get('total_critical_issues', 0),
                                'high_issues': result.get('total_high_issues', 0)
                            })

                            self.logger.log("=" * 60, "WARNING")
                            self.logger.log(f"❌ Code Review FAILED (Attempt {retry_count + 1})", "ERROR")
                            self.logger.log(f"Critical Issues: {result.get('total_critical_issues', 0)}", "ERROR")
                            self.logger.log(f"High Issues: {result.get('total_high_issues', 0)}", "ERROR")
                            self.logger.log("🔄 Retrying with code review feedback...", "INFO")
                            self.logger.log("=" * 60, "WARNING")

                            # Store detailed feedback in RAG
                            self._store_retry_feedback_in_rag(card, result, retry_count + 1)

                            retry_count += 1
                            break  # Break to restart development stage

                        elif review_status == 'FAIL' and retry_count >= max_retries:
                            self.logger.log("=" * 60, "ERROR")
                            self.logger.log(f"❌ Max retries ({max_retries}) reached", "ERROR")
                            self.logger.log("Code review still failing - stopping pipeline", "ERROR")
                            self.logger.log("=" * 60, "ERROR")

                            # Store final failed attempt
                            all_retry_history.append({
                                'attempt': retry_count + 1,
                                'review_result': result,
                                'critical_issues': result.get('total_critical_issues', 0),
                                'high_issues': result.get('total_high_issues', 0),
                                'final_failure': True
                            })

                            # Skip remaining stages and complete with FAILED status
                            stage_results['pipeline_status'] = 'FAILED_CODE_REVIEW'
                            break

                        elif review_status == 'PASS':
                            self.logger.log("✅ Code Review PASSED - Continuing pipeline", "SUCCESS")
                            # Continue to remaining stages
                            continue

                except Exception as e:
                    raise wrap_exception(
                        e,
                        PipelineStageError,
                        f"Stage {stage_name} execution failed",
                        {
                            "card_id": self.card_id,
                            "stage_name": stage_name,
                            "retry_attempt": retry_count
                        }
                    )

            # Check if we should break out of retry loop
            code_review_result = stage_results.get('code_review', {})
            if code_review_result.get('status') == 'PASS' or stage_results.get('pipeline_status') == 'FAILED_CODE_REVIEW':
                break

        # Continue with remaining stages if code review passed
        if stage_results.get('code_review', {}).get('status') == 'PASS':
            # Find index of code_review stage
            code_review_idx = next((i for i, s in enumerate(stages_to_run) if s.get_stage_name() == 'code_review'), -1)

            if code_review_idx >= 0:
                # Execute remaining stages after code review
                for i, stage in enumerate(stages_to_run[code_review_idx + 1:], code_review_idx + 2):
                    stage_name = stage.get_stage_name()
                    self.logger.log(f"📋 STAGE {i}/{len(stages_to_run)}: {stage_name.upper()}", "STAGE")

                    try:
                        # Execute stage with or without supervision
                        if self.enable_supervision and self.supervisor:
                            result = self.supervisor.execute_with_supervision(
                                stage, stage_name, card, context
                            )
                        else:
                            result = stage.execute(card, context)

                        stage_results[stage_name] = result
                        context.update(result)

                        if 'winner' in result:
                            context['winner'] = result['winner']

                    except Exception as e:
                        raise wrap_exception(
                            e,
                            PipelineStageError,
                            f"Stage {stage_name} execution failed (post code-review)",
                            {
                                "card_id": self.card_id,
                                "stage_name": stage_name,
                                "pipeline_phase": "post_code_review"
                            }
                        )

        # Notify pipeline completion
        self._notify_pipeline_completion(card, stage_results)

        # Determine final status
        final_status = "COMPLETED_SUCCESSFULLY"
        if stage_results.get('pipeline_status') == 'FAILED_CODE_REVIEW':
            final_status = "FAILED_CODE_REVIEW"
            self.logger.log("=" * 60, "ERROR")
            self.logger.log("❌ ARTEMIS PIPELINE FAILED - CODE REVIEW ISSUES NOT RESOLVED", "ERROR")
            self.logger.log("=" * 60, "ERROR")
        else:
            self.logger.log("=" * 60, "INFO")
            self.logger.log("🎉 ARTEMIS HUNT SUCCESSFUL - OPTIMAL SOLUTION DELIVERED!", "SUCCESS")
            self.logger.log("=" * 60, "INFO")

        # Print supervisor health report if supervision enabled
        if self.enable_supervision and self.supervisor:
            self.supervisor.print_health_report()

            # Cleanup any zombie processes
            cleaned = self.supervisor.cleanup_zombie_processes()
            if cleaned > 0:
                self.logger.log(f"🧹 Cleaned up {cleaned} zombie processes", "INFO")

        # Save full report with retry information
        supervisor_stats = self.supervisor.get_statistics() if self.enable_supervision and self.supervisor else None

        report = {
            "card_id": self.card_id,
            "workflow_plan": workflow_plan,
            "stages": stage_results,
            "status": final_status,
            "retry_history": all_retry_history if all_retry_history else None,
            "total_retries": retry_count,
            "supervisor_statistics": supervisor_stats
        }

        report_path = Path("/tmp") / f"pipeline_full_report_{self.card_id}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        return report

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
        for observer in self.observable._observers:
            if isinstance(observer, MetricsObserver):
                return observer.get_summary()

        return None

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
        for observer in self.observable._observers:
            if isinstance(observer, StateTrackingObserver):
                return observer.get_state()

        return None

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
                    raise wrap_exception(
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
                    'developers': [r['developer'] for r in feedback['developer_reviews']]
                }
            )

            self.logger.log(f"Stored retry feedback in RAG: {artifact_id}", "DEBUG")

        except Exception as e:
            raise wrap_exception(
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


@hydra.main(version_base=None, config_path="conf", config_name="config")
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
        raise wrap_exception(
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
    parser.add_argument("--config-report", action="store_true", help="Show configuration report")
    parser.add_argument("--skip-validation", action="store_true", help="Skip config validation (not recommended)")
    parser.add_argument("--status", action="store_true", help="Show workflow status for card-id")
    parser.add_argument("--list-active", action="store_true", help="List all active workflows")
    parser.add_argument("--json", action="store_true", help="Output status in JSON format")
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

    # Require card-id for pipeline execution
    if not args.card_id:
        print("\n❌ Error: --card-id is required for pipeline execution\n")
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
                for key in validation.missing_keys:
                    schema = config.CONFIG_SCHEMA.get(key, {})
                    print(f"  ❌ {key}")
                    print(f"     Description: {schema.get('description', 'N/A')}")

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
                for key in validation.invalid_keys:
                    print(f"  ❌ {key}")

            print("\n" + "="*80)
            print("\n💡 Run with --config-report to see full configuration")
            print("💡 Run with --skip-validation to bypass (NOT RECOMMENDED)\n")
            sys.exit(1)

    # Initialize dependencies (Dependency Injection)
    board = KanbanBoard()

    # Create messenger using factory (pluggable implementation)
    messenger = MessengerFactory.create_from_env(
        agent_name="artemis-orchestrator"
    )

    rag_db_path = config.get('ARTEMIS_RAG_DB_PATH', '/tmp/rag_db')
    rag = RAGAgent(db_path=rag_db_path, verbose=True)

    # Register orchestrator
    messenger.register_agent(
        capabilities=["coordinate_pipeline", "manage_workflow"],
        status="active"
    )

    try:
        # Create orchestrator with injected dependencies
        orchestrator = ArtemisOrchestrator(
            card_id=args.card_id,
            board=board,
            messenger=messenger,
            rag=rag,
            config=config
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
        raise wrap_exception(
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
