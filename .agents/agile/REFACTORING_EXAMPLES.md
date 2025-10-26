# Refactoring Examples - Before & After

This document shows concrete refactoring examples for the most critical antipatterns found.

---

## Example 1: God Class - SupervisorAgent (2732 lines)

### Before (Current - CRITICAL ANTIPATTERN):

```python
class SupervisorAgent:
    """2732-line God Class doing EVERYTHING"""

    def __init__(self, logger, messenger, card_id, rag, verbose,
                 enable_cost_tracking, enable_config_validation,
                 enable_sandboxing, daily_budget, monthly_budget,
                 enable_learning, max_budget_errors):
        # 234-line constructor initializing 12+ components!
        self.cost_tracker = CostTracker(...)
        self.sandbox = SandboxExecutor(...)
        self.learning_engine = ...
        # ... 200 more lines

    # Cost tracking methods (should be in CostTracker)
    def track_llm_call(self, ...): ...
    def check_budget(self, ...): ...
    def get_cost_statistics(self, ...): ...

    # Sandbox methods (should be in SandboxExecutor)
    def execute_code_safely(self, ...): ...
    def scan_security_issues(self, ...): ...

    # Learning methods (should be in LearningEngine)
    def enable_learning(self, ...): ...
    def learn_from_failure(self, ...): ...
    def llm_auto_fix_error(self, ...): ...  # 106 lines!

    # Recovery methods (should be in RecoveryManager)
    def handle_unexpected_state(self, ...): ...
    def execute_with_supervision(self, ...): ...  # 124 lines!

    # Health monitoring (should be in HealthMonitor)
    def check_heartbeat(self, ...): ...
    def get_statistics(self, ...): ...
```

### After (REFACTORED - SOLID Principles):

```python
# ============================================================================
# 1. Cost Tracking - Single Responsibility
# ============================================================================
@dataclass
class BudgetConfig:
    daily_limit: float
    monthly_limit: float
    currency: str = "USD"

class CostTracker:
    """Single Responsibility: Track LLM API costs"""

    def __init__(self, budget: BudgetConfig, logger: LoggerInterface):
        self.budget = budget
        self.logger = logger
        self.daily_cost = 0.0
        self.monthly_cost = 0.0

    def track_llm_call(self, model: str, provider: str,
                      tokens_input: int, tokens_output: int) -> CostEntry:
        """Track single LLM API call"""
        cost = self._calculate_cost(model, provider, tokens_input, tokens_output)

        if self._would_exceed_budget(cost):
            raise BudgetExceededError(f"Would exceed budget: ${cost}")

        self._record_cost(cost)
        return CostEntry(model, provider, cost, tokens_input, tokens_output)

    def get_statistics(self) -> CostStatistics:
        """Get cost statistics"""
        return CostStatistics(
            daily_cost=self.daily_cost,
            monthly_cost=self.monthly_cost,
            budget_remaining=self.budget.daily_limit - self.daily_cost
        )


# ============================================================================
# 2. Sandbox Execution - Single Responsibility
# ============================================================================
class SandboxExecutor:
    """Single Responsibility: Execute code safely in sandbox"""

    def __init__(self, security_scanner: SecurityScanner, logger: LoggerInterface):
        self.scanner = security_scanner
        self.logger = logger

    def execute_safely(self, code: str, scan_security: bool = True) -> ExecutionResult:
        """Execute code in sandbox"""
        if scan_security:
            security_issues = self.scanner.scan(code)
            if security_issues:
                return ExecutionResult(
                    success=False,
                    kill_reason="security_issues",
                    issues=security_issues
                )

        return self._run_in_sandbox(code)


# ============================================================================
# 3. Learning Engine - Single Responsibility
# ============================================================================
class LearningEngine:
    """Single Responsibility: Learn from failures and successes"""

    def __init__(self, llm_client: LLMClient, rag: RAGAgent, logger: LoggerInterface):
        self.llm = llm_client
        self.rag = rag
        self.logger = logger

    def learn_from_failure(self, error: Exception, context: Dict) -> LearningResult:
        """Learn from failure and suggest fix"""
        # Query RAG for similar failures
        similar = self.rag.query_similar_failures(str(error))

        # Use LLM to suggest fix
        fix_suggestion = self._llm_suggest_fix(error, context, similar)

        # Store learning
        self.rag.store_learning(error, context, fix_suggestion)

        return LearningResult(suggestion=fix_suggestion, confidence=0.8)


# ============================================================================
# 4. Recovery Manager - Single Responsibility
# ============================================================================
@dataclass
class RecoveryStrategy:
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    timeout_seconds: float = 600.0
    circuit_breaker_threshold: int = 5

class RecoveryManager:
    """Single Responsibility: Handle error recovery"""

    def __init__(self, learning_engine: LearningEngine, logger: LoggerInterface):
        self.learning = learning_engine
        self.logger = logger
        self.strategies: Dict[str, RecoveryStrategy] = {}

    def handle_unexpected_state(self, current_state: str,
                               expected_states: List[str],
                               context: Dict,
                               auto_learn: bool = False) -> RecoveryResult:
        """Handle unexpected state transition"""
        if auto_learn:
            learning = self.learning.learn_from_failure(
                StateTransitionError(current_state, expected_states),
                context
            )
            return RecoveryResult(success=True, action="learned", learning=learning)

        return RecoveryResult(success=False, action="logged")


# ============================================================================
# 5. Health Monitor - Single Responsibility
# ============================================================================
class HealthMonitor:
    """Single Responsibility: Monitor stage health and heartbeats"""

    def __init__(self, logger: LoggerInterface):
        self.logger = logger
        self.heartbeats: Dict[str, datetime] = {}

    def check_heartbeat(self, stage_name: str, max_silence_seconds: float = 60.0) -> HealthStatus:
        """Check if stage is still alive"""
        last_heartbeat = self.heartbeats.get(stage_name)
        if not last_heartbeat:
            return HealthStatus.UNKNOWN

        silence = (datetime.now() - last_heartbeat).total_seconds()
        if silence > max_silence_seconds:
            return HealthStatus.UNHEALTHY

        return HealthStatus.HEALTHY


# ============================================================================
# 6. Lightweight Supervisor - Coordinates Components
# ============================================================================
class SupervisorAgent:
    """Lightweight coordinator - delegates to specialized components"""

    def __init__(self, config: SupervisorConfig):
        # Use Dependency Injection - components are created externally
        self.cost_tracker = config.cost_tracker
        self.sandbox = config.sandbox
        self.learning = config.learning_engine
        self.recovery = config.recovery_manager
        self.health = config.health_monitor
        self.logger = config.logger

    def execute_with_supervision(self, stage: PipelineStage,
                                 stage_name: str,
                                 card: Dict,
                                 context: Dict) -> Dict:
        """Execute stage with supervision - delegates to components"""
        # 1. Health check
        self.health.record_heartbeat(stage_name)

        # 2. Execute stage
        try:
            result = stage.execute(card, context)

            # 3. Track costs if LLM was used
            if 'tokens_used' in result:
                self.cost_tracker.track_llm_call(...)

            return result

        except Exception as e:
            # 4. Handle failure - delegate to recovery manager
            recovery = self.recovery.handle_unexpected_state(
                current_state="STAGE_FAILED",
                expected_states=["STAGE_COMPLETED"],
                context={"error": str(e), "stage": stage_name},
                auto_learn=True
            )

            if recovery.success:
                self.logger.log("Recovered from failure", "INFO")
                return recovery.result
            else:
                raise


# ============================================================================
# Builder Pattern for Easy Construction
# ============================================================================
class SupervisorBuilder:
    """Builder pattern to construct SupervisorAgent"""

    def __init__(self, logger: LoggerInterface):
        self.logger = logger
        self._budget = BudgetConfig(daily_limit=10.0, monthly_limit=200.0)
        self._enable_learning = True
        self._enable_sandbox = True

    def with_budget(self, daily: float, monthly: float) -> 'SupervisorBuilder':
        self._budget = BudgetConfig(daily_limit=daily, monthly_limit=monthly)
        return self

    def with_learning(self, llm_client: LLMClient, rag: RAGAgent) -> 'SupervisorBuilder':
        self._llm = llm_client
        self._rag = rag
        self._enable_learning = True
        return self

    def build(self) -> SupervisorAgent:
        # Create components
        cost_tracker = CostTracker(self._budget, self.logger)
        sandbox = SandboxExecutor(SecurityScanner(), self.logger)

        learning = None
        if self._enable_learning:
            learning = LearningEngine(self._llm, self._rag, self.logger)

        recovery = RecoveryManager(learning, self.logger)
        health = HealthMonitor(self.logger)

        # Assemble supervisor
        config = SupervisorConfig(
            cost_tracker=cost_tracker,
            sandbox=sandbox,
            learning_engine=learning,
            recovery_manager=recovery,
            health_monitor=health,
            logger=self.logger
        )

        return SupervisorAgent(config)


# ============================================================================
# Usage Example
# ============================================================================
# Before (14 parameters!):
supervisor = SupervisorAgent(
    logger, messenger, card_id, rag, verbose,
    enable_cost_tracking, enable_config_validation,
    enable_sandboxing, daily_budget, monthly_budget,
    enable_learning, max_budget_errors
)

# After (fluent interface):
supervisor = (SupervisorBuilder(logger)
    .with_budget(daily=10.0, monthly=200.0)
    .with_learning(llm_client, rag)
    .build())
```

**Benefits:**
- ✅ Each class has single responsibility
- ✅ Easy to test individual components
- ✅ Easy to understand each piece
- ✅ No 234-line constructor!
- ✅ No 12-parameter methods!
- ✅ Clear separation of concerns

---

## Example 2: Excessive Parameters - ArtemisOrchestrator.__init__ (14 params)

### Before (CRITICAL ANTIPATTERN):

```python
class ArtemisOrchestrator:
    def __init__(
        self,
        card_id: str,                          # 1
        board: KanbanBoard,                    # 2
        messenger: MessengerInterface,         # 3
        rag: RAGAgent,                         # 4
        config: Optional[ConfigurationAgent],  # 5
        hydra_config: Optional[DictConfig],    # 6
        logger: Optional[LoggerInterface],     # 7
        test_runner: Optional[TestRunner],     # 8
        stages: Optional[List[PipelineStage]], # 9
        supervisor: Optional[SupervisorAgent], # 10
        enable_supervision: bool,              # 11
        strategy: Optional[PipelineStrategy],  # 12
        enable_observers: bool,                # 13
        ai_service: Optional[AIQueryService]   # 14  (!!)
    ):
        # 135 lines of initialization code...
```

**Problems:**
- 🔴 14 parameters = cognitive overload
- 🔴 Hard to remember parameter order
- 🔴 Hard to add new parameters
- 🔴 Hard to test (need to provide 14 args)

### After (REFACTORED):

```python
# ============================================================================
# Option 1: Configuration Object Pattern
# ============================================================================
@dataclass
class OrchestratorConfig:
    """Configuration for ArtemisOrchestrator"""
    # Required parameters
    card_id: str
    board: KanbanBoard
    messenger: MessengerInterface
    rag: RAGAgent

    # Optional parameters with defaults
    logger: Optional[LoggerInterface] = None
    test_runner: Optional[TestRunner] = None
    stages: Optional[List[PipelineStage]] = None
    supervisor: Optional[SupervisorAgent] = None
    strategy: Optional[PipelineStrategy] = None
    ai_service: Optional[AIQueryService] = None

    # Flags
    enable_supervision: bool = True
    enable_observers: bool = True

    # Legacy support
    config: Optional[ConfigurationAgent] = None
    hydra_config: Optional[DictConfig] = None

    def __post_init__(self):
        # Validation and defaults
        if self.logger is None:
            self.logger = PipelineLogger(verbose=True)

        if self.test_runner is None:
            self.test_runner = TestRunner()


class ArtemisOrchestrator:
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.card_id = config.card_id
        self.board = config.board
        # ... rest of initialization


# Usage:
config = OrchestratorConfig(
    card_id="card-001",
    board=board,
    messenger=messenger,
    rag=rag,
    enable_supervision=True
)
orchestrator = ArtemisOrchestrator(config)


# ============================================================================
# Option 2: Builder Pattern (More Flexible)
# ============================================================================
class OrchestratorBuilder:
    """Fluent builder for ArtemisOrchestrator"""

    def __init__(self, card_id: str, board: KanbanBoard):
        # Only required parameters in constructor
        self._card_id = card_id
        self._board = board

        # Set sensible defaults
        self._messenger = None
        self._rag = None
        self._logger = PipelineLogger(verbose=True)
        self._test_runner = TestRunner()
        self._enable_supervision = True
        self._enable_observers = True

    def with_messenger(self, messenger: MessengerInterface) -> 'OrchestratorBuilder':
        self._messenger = messenger
        return self

    def with_rag(self, rag: RAGAgent) -> 'OrchestratorBuilder':
        self._rag = rag
        return self

    def with_supervision(self, supervisor: SupervisorAgent) -> 'OrchestratorBuilder':
        self._supervisor = supervisor
        self._enable_supervision = True
        return self

    def without_supervision(self) -> 'OrchestratorBuilder':
        self._enable_supervision = False
        return self

    def with_observers(self, enable: bool = True) -> 'OrchestratorBuilder':
        self._enable_observers = enable
        return self

    def with_ai_service(self, ai_service: AIQueryService) -> 'OrchestratorBuilder':
        self._ai_service = ai_service
        return self

    def build(self) -> ArtemisOrchestrator:
        # Validate required parameters
        if not self._messenger:
            raise ValueError("Messenger is required")
        if not self._rag:
            raise ValueError("RAG agent is required")

        # Create config object
        config = OrchestratorConfig(
            card_id=self._card_id,
            board=self._board,
            messenger=self._messenger,
            rag=self._rag,
            logger=self._logger,
            test_runner=self._test_runner,
            supervisor=getattr(self, '_supervisor', None),
            enable_supervision=self._enable_supervision,
            enable_observers=self._enable_observers,
            ai_service=getattr(self, '_ai_service', None)
        )

        return ArtemisOrchestrator(config)


# Usage (fluent interface):
orchestrator = (OrchestratorBuilder(card_id, board)
    .with_messenger(messenger)
    .with_rag(rag)
    .with_supervision(supervisor)
    .with_ai_service(ai_service)
    .build())

# Or without supervision:
orchestrator = (OrchestratorBuilder(card_id, board)
    .with_messenger(messenger)
    .with_rag(rag)
    .without_supervision()
    .build())
```

**Benefits:**
- ✅ Easy to understand (2 required params vs 14!)
- ✅ Fluent, readable API
- ✅ Easy to add new parameters
- ✅ Self-documenting code
- ✅ Easy to test (can use defaults)

---

## Example 3: Long Method - _create_default_stages (179 lines)

### Before (ANTIPATTERN):

```python
def _create_default_stages(self) -> List[PipelineStage]:
    """179-line method creating all stages"""
    stages = []

    # Initialize centralized AI Query Service
    ai_service = None
    if AI_QUERY_SERVICE_AVAILABLE and self.llm_client:
        try:
            # ... 20 lines
        except Exception as e:
            # ... 5 lines

    # Initialize Intelligent Router
    self.intelligent_router = None
    if INTELLIGENT_ROUTER_AVAILABLE:
        try:
            # ... 15 lines
        except Exception as e:
            # ... 5 lines

    # Requirements Parsing stage
    if self.llm_client:
        stages.append(RequirementsParsingStage(...))  # 8 lines

    # Sprint Planning stage
    if self.llm_client:
        stages.append(SprintPlanningStage(...))  # 12 lines

    # ... 130 more lines creating 10 more stages!

    return stages
```

### After (REFACTORED):

```python
# ============================================================================
# Stage Factory - Single Responsibility
# ============================================================================
@dataclass
class StageFactoryConfig:
    """Configuration for stage creation"""
    board: KanbanBoard
    messenger: MessengerInterface
    rag: RAGAgent
    logger: LoggerInterface
    llm_client: Optional[LLMClient]
    supervisor: Optional[SupervisorAgent]
    config: Optional[ConfigurationAgent]
    observable: Optional[PipelineObservable]
    test_runner: Optional[TestRunner]

class StageFactory:
    """Factory for creating pipeline stages"""

    def __init__(self, config: StageFactoryConfig):
        self.config = config
        self.ai_service = self._create_ai_service()
        self.intelligent_router = self._create_intelligent_router()

    def create_default_pipeline(self) -> List[PipelineStage]:
        """Create default pipeline stages"""
        stages = []

        # Add optional stages first
        stages.extend(self._create_optional_stages())

        # Add core stages
        stages.extend(self._create_core_stages())

        # Add quality stages
        stages.extend(self._create_quality_stages())

        return stages

    def _create_optional_stages(self) -> List[PipelineStage]:
        """Create optional stages (require LLM)"""
        stages = []

        if self.config.llm_client:
            stages.append(self._create_requirements_stage())
            stages.append(self._create_sprint_planning_stage())

        return stages

    def _create_core_stages(self) -> List[PipelineStage]:
        """Create core pipeline stages"""
        return [
            self._create_project_analysis_stage(),
            self._create_architecture_stage(),
            self._create_dependency_validation_stage(),
            self._create_development_stage()
        ]

    def _create_quality_stages(self) -> List[PipelineStage]:
        """Create quality assurance stages"""
        stages = []

        if self.config.llm_client:
            stages.append(self._create_project_review_stage())

        stages.extend([
            self._create_validation_stage(),
            self._create_uiux_stage(),
            self._create_code_review_stage(),
            self._create_integration_stage(),
            self._create_testing_stage()
        ])

        return stages

    def _create_requirements_stage(self) -> RequirementsParsingStage:
        """Create requirements parsing stage"""
        return RequirementsParsingStage(
            logger=self.config.logger,
            rag=self.config.rag,
            messenger=self.config.messenger,
            supervisor=self.config.supervisor
        )

    # ... similar factory methods for other stages


# ============================================================================
# In ArtemisOrchestrator
# ============================================================================
class ArtemisOrchestrator:
    def _create_default_stages(self) -> List[PipelineStage]:
        """Create stages using factory"""
        factory_config = StageFactoryConfig(
            board=self.board,
            messenger=self.messenger,
            rag=self.rag,
            logger=self.logger,
            llm_client=self.llm_client,
            supervisor=self.supervisor,
            config=self.config,
            observable=self.observable,
            test_runner=self.test_runner
        )

        factory = StageFactory(factory_config)
        return factory.create_default_pipeline()
```

**Benefits:**
- ✅ Each method has single responsibility
- ✅ Easy to understand workflow
- ✅ Easy to test individual stage creation
- ✅ Easy to customize (override factory methods)
- ✅ Follows Open/Closed Principle

---

## Example 4: Magic Numbers

### Before (ANTIPATTERN):

```python
def _analyze_complexity(self) -> str:
    complexity_score = 0

    if priority == 'high':
        complexity_score += 2  # Magic number!

    if points >= 13:  # Magic number!
        complexity_score += 3  # Magic number!
    elif points >= 8:  # Magic number!
        complexity_score += 2  # Magic number!

    if complexity_score >= 6:  # Magic number!
        return 'complex'
    elif complexity_score >= 3:  # Magic number!
        return 'medium'
    else:
        return 'simple'
```

### After (REFACTORED):

```python
# ============================================================================
# Extract Constants
# ============================================================================
class ComplexityThresholds:
    """Complexity analysis thresholds"""
    # Priority scores
    HIGH_PRIORITY_SCORE = 2
    MEDIUM_PRIORITY_SCORE = 1

    # Story point thresholds
    STORY_POINTS_XL = 13
    STORY_POINTS_LARGE = 8
    STORY_POINTS_MEDIUM = 5

    # Story point scores
    SCORE_XL = 3
    SCORE_LARGE = 2
    SCORE_MEDIUM = 1

    # Final complexity thresholds
    COMPLEX_THRESHOLD = 6
    MEDIUM_THRESHOLD = 3


def _analyze_complexity(self) -> str:
    """Analyze task complexity with named constants"""
    complexity_score = 0

    # Priority contribution
    if priority == 'high':
        complexity_score += ComplexityThresholds.HIGH_PRIORITY_SCORE
    elif priority == 'medium':
        complexity_score += ComplexityThresholds.MEDIUM_PRIORITY_SCORE

    # Story points contribution
    if points >= ComplexityThresholds.STORY_POINTS_XL:
        complexity_score += ComplexityThresholds.SCORE_XL
    elif points >= ComplexityThresholds.STORY_POINTS_LARGE:
        complexity_score += ComplexityThresholds.SCORE_LARGE
    elif points >= ComplexityThresholds.STORY_POINTS_MEDIUM:
        complexity_score += ComplexityThresholds.SCORE_MEDIUM

    # Determine complexity level
    if complexity_score >= ComplexityThresholds.COMPLEX_THRESHOLD:
        return 'complex'
    elif complexity_score >= ComplexityThresholds.MEDIUM_THRESHOLD:
        return 'medium'
    else:
        return 'simple'
```

**Benefits:**
- ✅ Self-documenting code
- ✅ Easy to adjust thresholds
- ✅ Centralized configuration
- ✅ No "magic" numbers

---

## Summary

These refactorings demonstrate:

1. **God Class** → Split into focused classes with single responsibilities
2. **Excessive Parameters** → Use Builder Pattern or Configuration Objects
3. **Long Methods** → Extract to smaller methods and factories
4. **Magic Numbers** → Named constants for clarity

Applying these patterns will:
- ✅ Improve maintainability
- ✅ Reduce bugs
- ✅ Make testing easier
- ✅ Make code self-documenting
- ✅ Follow SOLID principles
