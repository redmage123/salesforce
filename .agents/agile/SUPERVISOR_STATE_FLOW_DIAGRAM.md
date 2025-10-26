# Supervisor State Tracking: Visual Flow Diagram

## Complete Flow: Code Review Failure → Refactoring → Retry → Success

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PIPELINE EXECUTION: Code Review Finds Issues → Developer Retries            │
└─────────────────────────────────────────────────────────────────────────────┘

STAGE 1: CODE REVIEW
═══════════════════════════════════════════════════════════════════════════════

┌──────────────────┐
│  Orchestrator    │
│  run_pipeline()  │
└────────┬─────────┘
         │
         │ execute_stage_with_supervision(code_review_stage, ...)
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR AGENT                                    │
│  _execute_stage_with_retries()                                              │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ 1. Execute stage.execute()                                  │            │
│  │ 2. Capture result                                           │            │
│  │ 3. Store in state machine                                   │            │
│  └─────────────────────────────────────────────────────────────┘            │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         │ code_review_stage.execute()
         ▼
┌──────────────────┐
│ CodeReviewStage  │
│                  │
│ 1. Review code   │
│ 2. Generate      │
│    refactoring   │
│    suggestions   │
└────────┬─────────┘
         │
         │ RETURNS
         │
         ▼
    {
        "review_results": [...],
        "refactoring_suggestions": """
            # REFACTORING INSTRUCTIONS
            1. Extract long methods
            2. Use guard clauses
            3. Use next() for first match
            ...
        """,
        "overall_score": 65,
        "total_critical_issues": 5
    }
         │
         │ Result flows back to supervisor
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR AGENT                                    │
│  _handle_successful_execution()                                             │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ if self.state_machine and result is not None:              │            │
│  │     self.state_machine.push_state(                          │            │
│  │         PipelineState.STAGE_COMPLETED,                      │            │
│  │         {                                                   │            │
│  │             "stage": "code_review",                         │            │
│  │             "result": result,  ← STORES COMPLETE RESULT     │            │
│  │             "duration": 12.5,                               │            │
│  │             "retry_count": 0,                               │            │
│  │             "timestamp": "2025-10-25T14:30:22"              │            │
│  │         }                                                   │            │
│  │     )                                                       │            │
│  └─────────────────────────────────────────────────────────────┘            │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         │ push_state()
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARTEMIS STATE MACHINE                                    │
│  _state_stack (Pushdown Automaton)                                          │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ _state_stack.append({                                       │            │
│  │     "state": PipelineState.STAGE_COMPLETED,                 │            │
│  │     "timestamp": datetime.now(),                            │            │
│  │     "context": {                                            │            │
│  │         "stage": "code_review",                             │            │
│  │         "result": {                                         │            │
│  │             "refactoring_suggestions": "...",               │            │
│  │             "overall_score": 65,                            │            │
│  │             "total_critical_issues": 5                      │            │
│  │         },                                                  │            │
│  │         "duration": 12.5,                                   │            │
│  │         "retry_count": 0                                    │            │
│  │     }                                                       │            │
│  │ })                                                          │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                                                                             │
│  STATE STACK NOW:                                                           │
│  [                                                                          │
│    { state: STAGE_COMPLETED, context: { stage: "project_analysis", ... } } │
│    { state: STAGE_COMPLETED, context: { stage: "code_review", ... } } ←NEW │
│  ]                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘

         │
         │ Returns to orchestrator
         ▼
┌──────────────────┐
│  Orchestrator    │
│                  │
│ Receives result  │
└────────┬─────────┘
         │
         │ _store_retry_feedback_in_rag()
         ▼
┌──────────────────┐
│  RAG Database    │
│  (ChromaDB)      │
│                  │
│ Stores:          │
│ - Code issues    │
│ - Refactoring    │
│   suggestions    │
└──────────────────┘


STAGE 2: DEVELOPER EXECUTES (FIRST ATTEMPT - FAILS)
═══════════════════════════════════════════════════════════════════════════════

┌──────────────────┐
│  Orchestrator    │
└────────┬─────────┘
         │
         │ execute_stage_with_supervision(developer_stage, ...)
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR AGENT                                    │
│  _execute_stage_with_retries()                                              │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         │ developer_stage.execute()
         ▼
┌──────────────────┐
│ DeveloperStage   │
│                  │
│ 1. Queries RAG   │
│ 2. Reads code    │
│ 3. Modifies      │
│ 4. Runs build    │
└────────┬─────────┘
         │
         │ ❌ BUILD FAILS!
         │
         ▼
    BuildException("Build failed: compilation errors in app.py")
         │
         │ Exception propagates to supervisor
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR AGENT                                    │
│  except Exception as e:                                                     │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ if self.state_machine:                                      │            │
│  │     self.state_machine.push_state(                          │            │
│  │         PipelineState.STAGE_FAILED,                         │            │
│  │         {                                                   │            │
│  │             "stage": "developer",                           │            │
│  │             "error": str(e),  ← STORES ERROR                │            │
│  │             "error_type": "BuildException",                 │            │
│  │             "retry_count": 1,                               │            │
│  │             "timestamp": "2025-10-25T14:30:45"              │            │
│  │         }                                                   │            │
│  │     )                                                       │            │
│  └─────────────────────────────────────────────────────────────┘            │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         │ push_state()
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARTEMIS STATE MACHINE                                    │
│  _state_stack (Pushdown Automaton)                                          │
│                                                                             │
│  STATE STACK NOW:                                                           │
│  [                                                                          │
│    { state: STAGE_COMPLETED, context: { stage: "project_analysis", ... } } │
│    { state: STAGE_COMPLETED, context: { stage: "code_review", ... } }      │
│    { state: STAGE_FAILED, context: { stage: "developer", error: "..." } }←│
│  ]                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘


STAGE 3: SUPERVISOR QUERIES STATE BEFORE RETRY
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR AGENT                                    │
│  Before retrying, supervisor queries state to inform decision               │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ # Get code review results                                   │            │
│  │ code_review_result = self.get_stage_result('code_review')   │            │
│  │                                                             │            │
│  │ if code_review_result:                                      │            │
│  │     critical_issues = code_review_result.get(              │            │
│  │         'total_critical_issues', 0                          │            │
│  │     )                                                       │            │
│  │     overall_score = code_review_result.get(                │            │
│  │         'overall_score', 100                                │            │
│  │     )                                                       │            │
│  │                                                             │            │
│  │     # Heavy refactoring needed                             │            │
│  │     if critical_issues > 5 or overall_score < 70:          │            │
│  │         self.set_recovery_strategy(                         │            │
│  │             "developer",                                    │            │
│  │             RecoveryStrategy(                               │            │
│  │                 max_retries=5,        # More retries        │            │
│  │                 retry_delay_seconds=180,  # 3 minutes       │            │
│  │                 timeout_seconds=600,   # 10 minutes         │            │
│  │                 backoff_multiplier=1.5                      │            │
│  │             )                                               │            │
│  │         )                                                   │            │
│  └─────────────────────────────────────────────────────────────┘            │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         │ get_stage_result('code_review')
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR AGENT                                    │
│  get_stage_result() - Pattern #4 (next() for first match)                  │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ return next(                                                │            │
│  │     (                                                       │            │
│  │         context['result']                                   │            │
│  │         for state_entry in reversed(                        │            │
│  │             self.state_machine._state_stack                 │            │
│  │         )                                                   │            │
│  │         if (context := state_entry.get('context', {})      │            │
│  │            ).get('stage') == 'code_review'                 │            │
│  │         and 'result' in context                            │            │
│  │     ),                                                      │            │
│  │     None                                                    │            │
│  │ )                                                           │            │
│  └─────────────────────────────────────────────────────────────┘            │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         │ Searches state stack (reversed = latest first)
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARTEMIS STATE MACHINE                                    │
│  _state_stack                                                                │
│                                                                             │
│  Searches in reverse:                                                       │
│  [2] { stage: "developer", error: "..." } ← Skip (no result)                │
│  [1] { stage: "code_review", result: {...} } ← MATCH! Return result         │
│  [0] { stage: "project_analysis", ... }                                     │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         │ RETURNS
         ▼
    {
        "refactoring_suggestions": "# Extract long methods...",
        "overall_score": 65,
        "total_critical_issues": 5
    }
         │
         │ Supervisor analyzes result
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR AGENT                                    │
│  Decision:                                                                  │
│  - critical_issues = 5 (> threshold)                                        │
│  - overall_score = 65 (< 70)                                                │
│  → INCREASE RETRY LIMITS AND TIMEOUT                                        │
│                                                                             │
│  Updated Recovery Strategy:                                                 │
│  - max_retries: 3 → 5                                                       │
│  - retry_delay: 60s → 180s                                                  │
│  - timeout: 300s → 600s                                                     │
└─────────────────────────────────────────────────────────────────────────────┘


STAGE 4: DEVELOPER RETRIES (SECOND ATTEMPT - SUCCESS)
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR AGENT                                    │
│  Retry with extended timeout (600s instead of 300s)                         │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         │ developer_stage.execute()
         ▼
┌──────────────────┐
│ DeveloperStage   │
│                  │
│ 1. Queries RAG   │──────────────┐
└────────┬─────────┘               │
         │                         ▼
         │                  ┌──────────────┐
         │                  │ RAG Database │
         │                  │              │
         │                  │ Returns:     │
         │                  │ - Refactoring│
         │                  │   suggestions│
         │                  └──────┬───────┘
         │                         │
         │◄────────────────────────┘
         │
         │ 2. Applies refactorings:
         │    - Extract long methods
         │    - Use guard clauses
         │    - Use next() for first match
         │
         │ 3. Runs build
         │
         ▼
    ✅ BUILD SUCCESS!
         │
         │ RETURNS
         ▼
    {
        "build_status": "success",
        "tests_passed": 45,
        "refactorings_applied": [
            "Extracted long methods",
            "Applied guard clauses",
            "Used next() for first match"
        ]
    }
         │
         │ Result flows back to supervisor
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR AGENT                                    │
│  _handle_successful_execution()                                             │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ self.state_machine.push_state(                              │            │
│  │     PipelineState.STAGE_COMPLETED,                          │            │
│  │     {                                                       │            │
│  │         "stage": "developer",                               │            │
│  │         "result": result,  ← STORES SUCCESS RESULT          │            │
│  │         "duration": 95.3,                                   │            │
│  │         "retry_count": 2,  ← Second attempt                 │            │
│  │         "timestamp": "2025-10-25T14:35:20"                  │            │
│  │     }                                                       │            │
│  │ )                                                           │            │
│  └─────────────────────────────────────────────────────────────┘            │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         │ push_state()
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARTEMIS STATE MACHINE                                    │
│  _state_stack (Pushdown Automaton)                                          │
│                                                                             │
│  FINAL STATE STACK:                                                         │
│  [                                                                          │
│    { state: STAGE_COMPLETED, context: { stage: "project_analysis" } }      │
│    { state: STAGE_COMPLETED, context: { stage: "code_review",              │
│                                          result: {score: 65, ...} } }       │
│    { state: STAGE_FAILED, context: { stage: "developer",                   │
│                                      error: "Build failed" } }              │
│    { state: STAGE_COMPLETED, context: { stage: "developer",                │
│                                          result: {build: success},          │
│                                          retry_count: 2 } } ←NEW            │
│  ]                                                                          │
│                                                                             │
│  COMPLETE HISTORY PRESERVED:                                                │
│  - Original failure (index 2)                                               │
│  - Successful retry (index 3)                                               │
│  - Code review results that informed retry strategy (index 1)              │
└─────────────────────────────────────────────────────────────────────────────┘


QUERY EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│ Example 1: Get Latest Developer Result                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  result = supervisor.get_stage_result('developer')                          │
│                                                                             │
│  # Searches stack in reverse, returns first match:                          │
│  # Index 3 (success, retry_count=2)                                         │
│  # NOT index 2 (failure)                                                    │
│                                                                             │
│  → {                                                                        │
│      "build_status": "success",                                             │
│      "tests_passed": 45,                                                    │
│      "refactorings_applied": [...]                                          │
│    }                                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ Example 2: Get All Stage Results                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  results = supervisor.get_all_stage_results()                               │
│                                                                             │
│  # Returns dict with latest result for each unique stage:                   │
│  → {                                                                        │
│      "project_analysis": {...},                                             │
│      "code_review": {                                                       │
│          "overall_score": 65,                                               │
│          "total_critical_issues": 5,                                        │
│          "refactoring_suggestions": "..."                                   │
│      },                                                                     │
│      "developer": {                                                         │
│          "build_status": "success",                                         │
│          "tests_passed": 45                                                 │
│      }                                                                      │
│    }                                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ Example 3: Count Developer Retries                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  # Search entire stack for developer attempts                               │
│  developer_attempts = [                                                     │
│      entry for entry in state_machine._state_stack                          │
│      if entry['context'].get('stage') == 'developer'                        │
│  ]                                                                          │
│                                                                             │
│  → [                                                                        │
│      { state: STAGE_FAILED, retry_count: 1 },                               │
│      { state: STAGE_COMPLETED, retry_count: 2 }                             │
│    ]                                                                        │
│                                                                             │
│  total_retries = len(developer_attempts)  # 2                               │
│  final_attempt = developer_attempts[-1]   # Success                         │
└─────────────────────────────────────────────────────────────────────────────┘


KEY ARCHITECTURAL PRINCIPLES
═══════════════════════════════════════════════════════════════════════════════

┌────────────────────────────────────────────────────────────────────────────┐
│ 1. SEPARATION OF CONCERNS                                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   Supervisor:      Monitors health, stores state, manages retries         │
│   Orchestrator:    Manages workflow, stores data in RAG                   │
│   State Machine:   Tracks state, provides history                         │
│                                                                            │
│   ✅ No overlap, clear responsibilities                                    │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ 2. CONTENT-AGNOSTIC MONITORING                                             │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   Supervisor stores COMPLETE results without understanding them            │
│   Works with ANY stage type                                               │
│   Generic push_state(state, context) interface                            │
│                                                                            │
│   ✅ Supervisor doesn't need to know about "refactoring_suggestions"       │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ 3. PUSHDOWN AUTOMATON BENEFITS                                             │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   Stack Structure:   Latest state on top (LIFO)                            │
│   History:           Never loses past states                              │
│   Rollback:          Can pop states to revert                             │
│   Query:             Can search stack for past results                    │
│                                                                            │
│   ✅ Complete audit trail of pipeline execution                            │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ 4. REFACTORING PATTERNS APPLIED                                            │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   Pattern #4:  next() for first match (get_stage_result)                  │
│   Pattern #10: Guard clauses (both helper methods)                        │
│   Pattern #11: Generator pattern (get_all_stage_results)                  │
│                                                                            │
│   ✅ Practicing what we preach                                             │
└────────────────────────────────────────────────────────────────────────────┘
