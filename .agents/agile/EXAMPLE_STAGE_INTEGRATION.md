# Example: Integrating Supervisor into DevelopmentStage

This document shows a complete before/after example of integrating the supervisor into the DevelopmentStage.

---

## Before (Without Supervisor)

```python
# artemis_stages.py (original)

class DevelopmentStage(PipelineStage):
    """
    Single Responsibility: Execute TDD development with multiple developers
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        logger: LoggerInterface
    ):
        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.logger = logger
        self.developer_invoker = DeveloperInvoker(
            board=board,
            messenger=messenger,
            rag=rag,
            logger=logger
        )

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute development stage"""
        self.logger.log("Starting Development Stage", "STAGE")

        card_id = card['card_id']
        adr_content = context['adr_content']
        adr_file = context['adr_file']

        # Invoke developers
        developer_results = self.developer_invoker.invoke_parallel_developers(
            num_developers=2,
            card=card,
            adr_content=adr_content,
            adr_file=adr_file,
            rag_agent=self.rag
        )

        # Run tests
        test_results = self._run_tests(developer_results)

        return {
            "status": "success",
            "developer_results": developer_results,
            "test_results": test_results
        }
```

**Problems:**
- ❌ No supervisor monitoring
- ❌ No cost tracking for LLM calls
- ❌ No code execution sandboxing
- ❌ No learning from failures
- ❌ No recovery from hung developers

---

## After (With Supervisor Integration)

```python
# artemis_stages.py (with supervisor)

class DevelopmentStage(PipelineStage):
    """
    Single Responsibility: Execute TDD development with multiple developers

    NEW: Integrates with supervisor for monitoring, cost tracking, sandboxing, and learning
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        logger: LoggerInterface,
        supervisor: Optional['SupervisorAgent'] = None  # NEW: Inject supervisor
    ):
        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.logger = logger
        self.supervisor = supervisor  # NEW: Store supervisor reference
        self.developer_invoker = DeveloperInvoker(
            board=board,
            messenger=messenger,
            rag=rag,
            logger=logger
        )

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute development stage with supervisor monitoring"""
        stage_name = "development"
        self.logger.log("Starting Development Stage", "STAGE")

        card_id = card['card_id']
        adr_content = context['adr_content']
        adr_file = context['adr_file']

        # NEW: Register stage with supervisor
        if self.supervisor:
            self.supervisor.register_stage(
                stage_name=stage_name,
                recovery_strategy=RecoveryStrategy(
                    max_retries=3,
                    retry_delay_seconds=10,
                    timeout_seconds=600,  # 10 minutes
                    circuit_breaker_threshold=5
                )
            )

        try:
            # Invoke developers
            developer_results = self.developer_invoker.invoke_parallel_developers(
                num_developers=2,
                card=card,
                adr_content=adr_content,
                adr_file=adr_file,
                rag_agent=self.rag
            )

            # NEW: Track LLM costs for each developer
            if self.supervisor:
                for result in developer_results:
                    if result.get("success") and result.get("llm_usage"):
                        try:
                            self.supervisor.track_llm_call(
                                model=result["llm_usage"]["model"],
                                provider=result["llm_usage"]["provider"],
                                tokens_input=result["llm_usage"]["tokens_input"],
                                tokens_output=result["llm_usage"]["tokens_output"],
                                stage=stage_name,
                                purpose=result["developer"]
                            )
                            self.logger.log(
                                f"Tracked LLM cost for {result['developer']}: "
                                f"${result['llm_usage']['cost']:.4f}",
                                "INFO"
                            )
                        except BudgetExceededError as e:
                            self.logger.log(f"Budget exceeded: {e}", "ERROR")
                            raise

            # NEW: Execute developer code in sandbox
            if self.supervisor and self.supervisor.sandbox:
                for result in developer_results:
                    if not result.get("success"):
                        continue

                    self.logger.log(
                        f"Executing {result['developer']} code in sandbox...",
                        "INFO"
                    )

                    # Get implementation file
                    impl_file = result.get("implementation_file")
                    if impl_file and Path(impl_file).exists():
                        code = Path(impl_file).read_text()

                        # Execute in sandbox
                        exec_result = self.supervisor.execute_code_safely(
                            code=code,
                            scan_security=True
                        )

                        if not exec_result["success"]:
                            error_msg = (
                                f"{result['developer']} code execution failed: "
                                f"{exec_result['kill_reason']}"
                            )
                            self.logger.log(error_msg, "ERROR")

                            # Mark this developer solution as failed
                            result["success"] = False
                            result["error"] = error_msg

            # Run tests
            test_results = self._run_tests(developer_results)

            # Check if we have any successful developers
            successful_devs = [r for r in developer_results if r.get("success")]

            if not successful_devs:
                # NEW: All developers failed - report unexpected state
                if self.supervisor:
                    recovery = self.supervisor.handle_unexpected_state(
                        current_state="STAGE_FAILED_ALL_DEVELOPERS",
                        expected_states=["STAGE_COMPLETED"],
                        context={
                            "stage_name": stage_name,
                            "error_message": "All developers failed",
                            "card_id": card_id,
                            "developer_count": len(developer_results),
                            "developer_errors": [r.get("error") for r in developer_results]
                        },
                        auto_learn=True  # Let supervisor learn how to fix this
                    )

                    if recovery and recovery["success"]:
                        self.logger.log(
                            "Supervisor recovered from all-developers-failed state!",
                            "INFO"
                        )
                        # Would retry or apply learned solution here
                    else:
                        raise Exception("All developers failed and recovery unsuccessful")
                else:
                    raise Exception("All developers failed")

            return {
                "status": "success",
                "developer_results": developer_results,
                "test_results": test_results,
                "successful_developers": len(successful_devs)
            }

        except Exception as e:
            # NEW: Let supervisor learn from this failure
            if self.supervisor:
                self.logger.log(f"Development stage failed, consulting supervisor...", "WARNING")

                recovery = self.supervisor.handle_unexpected_state(
                    current_state="STAGE_FAILED",
                    expected_states=["STAGE_COMPLETED"],
                    context={
                        "stage_name": stage_name,
                        "error_message": str(e),
                        "stack_trace": traceback.format_exc(),
                        "card_id": card_id
                    },
                    auto_learn=True
                )

                if recovery and recovery["success"]:
                    self.logger.log("Supervisor recovered from failure!", "INFO")
                    # The supervisor's learned workflow already executed
                    # We might want to retry the stage here
                else:
                    self.logger.log("Supervisor could not recover", "ERROR")

            # Re-raise after supervisor has learned
            raise
```

**Benefits:**
- ✅ Supervisor monitors stage execution
- ✅ LLM costs tracked automatically
- ✅ Code executed in sandbox (security)
- ✅ Failures trigger learning
- ✅ Automatic recovery attempted

---

## Developer Invoker Updates

To support cost tracking, update DeveloperInvoker to include LLM usage in results:

```python
# developer_invoker.py

class DeveloperInvoker:
    def invoke_developer(
        self,
        developer_name: str,
        card: Dict,
        adr_content: str,
        adr_file: str,
        rag_agent: Optional[RAGAgent] = None
    ) -> Dict:
        """Invoke a single developer agent"""

        try:
            # Call LLM for development
            llm_client = get_llm_client()

            response = llm_client.chat(prompt)

            # NEW: Capture LLM usage metadata
            llm_usage = {
                "model": response.model,
                "provider": "openai",  # or detect from client
                "tokens_input": response.usage.prompt_tokens,
                "tokens_output": response.usage.completion_tokens,
                "cost": self._calculate_cost(
                    response.model,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
            }

            # Parse implementation from response
            implementation = self._parse_implementation(response.content)

            return {
                "developer": developer_name,
                "success": True,
                "implementation": implementation,
                "implementation_file": f"/tmp/{developer_name}/implementation.py",
                "llm_usage": llm_usage  # NEW: Include LLM usage
            }

        except Exception as e:
            return {
                "developer": developer_name,
                "success": False,
                "error": str(e),
                "llm_usage": None  # No usage if failed early
            }

    def _calculate_cost(self, model: str, tokens_input: int, tokens_output: int) -> float:
        """Calculate LLM call cost"""
        from cost_tracker import ModelPricing
        return ModelPricing.get_cost(model, tokens_input, tokens_output)
```

---

## Orchestrator Integration

Update ArtemisOrchestrator to create supervisor and inject into stages:

```python
# artemis_orchestrator.py

from supervisor_agent import SupervisorAgent
from llm_client import get_llm_client

class ArtemisOrchestrator:
    def __init__(self, card_id: str, **kwargs):
        # ... existing initialization ...

        # NEW: Create supervisor
        self.supervisor = SupervisorAgent(
            card_id=card_id,
            messenger=self.messenger,
            rag=self.rag,
            verbose=True,
            enable_cost_tracking=True,
            enable_config_validation=True,
            enable_sandboxing=True,
            daily_budget=10.00,
            monthly_budget=200.00
        )

        # NEW: Enable learning
        llm = get_llm_client(provider="openai", model="gpt-4o")
        self.supervisor.enable_learning(llm)

        # Create stages with supervisor
        self.stages = self._create_stages()

    def _create_stages(self):
        """Create stages with supervisor injection"""
        return {
            "project_analysis": ProjectAnalysisStage(
                board=self.board,
                messenger=self.messenger,
                rag=self.rag,
                logger=self.logger,
                supervisor=self.supervisor  # NEW: Inject supervisor
            ),
            "architecture": ArchitectureStage(
                board=self.board,
                messenger=self.messenger,
                rag=self.rag,
                logger=self.logger,
                supervisor=self.supervisor  # NEW: Inject supervisor
            ),
            "development": DevelopmentStage(
                board=self.board,
                messenger=self.messenger,
                rag=self.rag,
                logger=self.logger,
                supervisor=self.supervisor  # NEW: Inject supervisor
            ),
            # ... other stages with supervisor ...
        }

    def run(self, card: Dict):
        """Execute pipeline with supervisor monitoring"""

        # Print initial health
        self.supervisor.print_health_report()

        for stage_name, stage in self.stages.items():
            try:
                # Execute stage (supervisor monitoring happens inside stage)
                result = stage.execute(card, self.context)

                # Update context
                self.context.update(result)

            except Exception as e:
                self.logger.log(f"Stage {stage_name} failed: {e}", "ERROR")
                raise

        # Print final health report
        print("\n" + "="*70)
        print("PIPELINE COMPLETED - FINAL HEALTH REPORT")
        print("="*70)
        self.supervisor.print_health_report()

        # Show learning statistics
        stats = self.supervisor.get_statistics()
        if "learning" in stats:
            ln = stats["learning"]
            print("\n📚 Learning Summary:")
            print(f"   Unexpected states handled: {ln['unexpected_states_detected']}")
            print(f"   Solutions learned: {ln['solutions_learned']}")
            print(f"   Success rate: {ln['average_success_rate']*100:.1f}%")
```

---

## Testing the Integration

```python
# test_development_stage_with_supervisor.py

import os
from supervisor_agent import SupervisorAgent
from artemis_stages import DevelopmentStage

# Setup
os.environ["ARTEMIS_LLM_PROVIDER"] = "mock"

supervisor = SupervisorAgent(
    card_id="test-001",
    enable_cost_tracking=True,
    enable_sandboxing=True,
    verbose=True
)

stage = DevelopmentStage(
    board=board,
    messenger=messenger,
    rag=rag,
    logger=logger,
    supervisor=supervisor  # Inject supervisor
)

# Execute
card = {"card_id": "test-001", "title": "Test task"}
context = {"adr_content": "...", "adr_file": "/tmp/adr.md"}

result = stage.execute(card, context)

# Check supervisor tracked everything
stats = supervisor.get_statistics()

assert "cost_tracking" in stats
assert stats["cost_tracking"]["total_calls"] > 0
print(f"✅ Tracked {stats['cost_tracking']['total_calls']} LLM calls")

assert "security_sandbox" in stats
print(f"✅ Executed code in {stats['security_sandbox']['backend']} sandbox")

supervisor.print_health_report()
```

---

## Migration Checklist

To integrate supervisor into all stages:

- [x] **Create supervisor in orchestrator**
- [x] **Enable learning with LLM client**
- [ ] **Update each stage:**
  - [ ] Add `supervisor` parameter to `__init__`
  - [ ] Register stage on execute
  - [ ] Track LLM calls
  - [ ] Execute code in sandbox
  - [ ] Handle unexpected states
- [ ] **Update developer invoker:**
  - [ ] Include LLM usage in results
  - [ ] Calculate costs per call
- [ ] **Test each stage:**
  - [ ] Verify cost tracking works
  - [ ] Verify sandboxing works
  - [ ] Verify learning triggers on failures

---

## Expected Output

When running with supervisor integration:

```
[Supervisor] Security sandbox enabled (backend: subprocess)
[Supervisor] Cost tracking enabled (daily=$10.00, monthly=$200.00)
[Supervisor] 🧠 Learning engine enabled

Starting Development Stage...
[Supervisor] Registered stage: development

Invoking developer-a...
[Supervisor] Executing code in sandbox (scan: True)
✅ Code executed successfully in 0.04s
Tracked LLM cost for developer-a: $0.0325

Invoking developer-b...
[Supervisor] Executing code in sandbox (scan: True)
✅ Code executed successfully in 0.05s
Tracked LLM cost for developer-b: $0.0310

======================================================================
ARTEMIS SUPERVISOR - HEALTH REPORT
======================================================================

✅ Overall Health: HEALTHY

💰 Cost Management:
   Total LLM Calls:         2
   Total Cost:              $0.06
   Daily Remaining:         $9.94

🛡️  Security Sandbox:
   Backend:                 subprocess
   Blocked Executions:      0

🧠 Learning Engine:
   Unexpected States:       0
   Solutions Learned:       0
   Solutions Applied:       0

======================================================================
```

---

## Summary

**Before:** Stages executed independently with no monitoring

**After:**
- ✅ Supervisor monitors all stage executions
- ✅ LLM costs tracked automatically
- ✅ Code executed securely in sandbox
- ✅ Failures trigger autonomous learning
- ✅ Recovery attempted automatically
- ✅ Complete health reporting

**Next Step:** Apply this pattern to all 8 pipeline stages!
