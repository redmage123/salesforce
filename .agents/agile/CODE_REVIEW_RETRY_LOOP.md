# Code Review Retry Loop Implementation

## Overview

The Artemis pipeline now includes an intelligent retry loop that automatically re-implements code when the code review stage fails. This ensures that implementations meet all requirements before proceeding to integration and deployment.

## Problem Solved

**Before**: When code review failed with CRITICAL issues (e.g., missing requirements, security vulnerabilities), the pipeline continued through validation, integration, and testing stages anyway, resulting in incomplete or broken implementations being deployed.

**After**: When code review fails, the pipeline loops back to the development stage with detailed feedback, allowing developers to fix issues before continuing.

## How It Works

### 1. Code Review Failure Detection

When the code review stage completes, the orchestrator checks the status:
- **PASS**: Continue to remaining stages (validation → integration → testing)
- **NEEDS_IMPROVEMENT**: Continue with warnings logged
- **FAIL**: Trigger retry loop if retries remain

### 2. Retry Loop Flow

```
Stage 1-3: Project Analysis → Architecture → Dependencies
    ↓
Stage 4: DEVELOPMENT (Initial)
    ↓
Stage 5: CODE REVIEW
    ↓
  FAIL? → Extract detailed feedback
    ↓
  Store feedback in RAG
    ↓
  Loop back to Stage 4: DEVELOPMENT (Retry #1)
    ↓
  Pass feedback to developers via context
    ↓
Stage 5: CODE REVIEW (Retry #1)
    ↓
Still FAIL? → Repeat up to max_retries (default: 2)
    ↓
PASS → Continue to Stage 6-8: Validation → Integration → Testing
```

### 3. Feedback Mechanism

On each retry, developers receive:

**Structured Feedback in Context**:
```python
context['retry_attempt'] = 1  # Current retry number
context['previous_review_feedback'] = {
    'status': 'FAIL',
    'total_critical_issues': 2,
    'total_high_issues': 3,
    'developer_reviews': [
        {
            'developer': 'developer-a',
            'review_status': 'FAIL',
            'overall_score': 67,
            'critical_issues': 2,
            'detailed_issues': [...]  # Full issue details
        }
    ]
}
```

**Detailed Issues Stored in RAG**:
- Top 10 most critical issues (sorted by severity)
- File path and line number for each issue
- Problem description
- Fix recommendation
- ADR reference (for requirements violations)

## Configuration

### Default Settings

```python
max_retries = 2  # Maximum number of retry attempts (default: 2)
```

### Modifying Retry Limit

When running the pipeline:

```bash
# Default: 2 retries
python3 artemis_orchestrator_solid.py --card-id card-123 --full

# Future: Custom retry limit (requires code modification)
# orchestrator.run_full_pipeline(max_retries=3)
```

## Pipeline Report Changes

The final pipeline report now includes retry information:

```json
{
  "card_id": "card-123",
  "status": "COMPLETED_SUCCESSFULLY" or "FAILED_CODE_REVIEW",
  "total_retries": 1,
  "retry_history": [
    {
      "attempt": 1,
      "review_result": {...},
      "critical_issues": 2,
      "high_issues": 3
    }
  ],
  "stages": {...}
}
```

## Status Outcomes

### Successful Retry
- Status: `COMPLETED_SUCCESSFULLY`
- Code review passed after retry
- Pipeline completes all stages

### Max Retries Exceeded
- Status: `FAILED_CODE_REVIEW`
- Code review still failing after max retries
- Pipeline stops before integration
- Prevents broken code from being deployed

### No Retries Needed
- Status: `COMPLETED_SUCCESSFULLY`
- Code review passed on first attempt
- `total_retries: 0`
- `retry_history: null`

## Logging Output

### Retry Attempt Log
```
============================================================
🔄 RETRY ATTEMPT 1/2
============================================================
```

### Failure Log
```
============================================================
❌ Code Review FAILED (Attempt 1)
Critical Issues: 2
High Issues: 3
🔄 Retrying with code review feedback...
============================================================
```

### Max Retries Log
```
============================================================
❌ Max retries (2) reached
Code review still failing - stopping pipeline
============================================================
```

## File Locations

### Implementation Files
- **Orchestrator**: `/home/bbrelin/src/repos/salesforce/.agents/agile/artemis_orchestrator_solid.py`
  - `run_full_pipeline()`: Main retry loop logic (lines 231-422)
  - `_extract_code_review_feedback()`: Extract detailed feedback (lines 482-525)
  - `_store_retry_feedback_in_rag()`: Store feedback in RAG (lines 527-610)

### Code Review Prompt
- **Prompt**: `/home/bbrelin/src/repos/salesforce/.agents/agile/prompts/code_review_agent_prompt.md`
  - Category 0: REQUIREMENTS_VALIDATION (lines 22-65)
  - Ensures requirements are validated FIRST before other checks

### Review Reports
- **JSON Reports**: `/tmp/code-reviews/code_review_{developer_name}.json`
  - Contains full review with detailed issues
  - Used by retry loop to provide feedback

## Benefits

1. **Requirements Compliance**: Ensures all ADR requirements are met before deployment
2. **Automatic Fix Loops**: No manual intervention needed for fixable issues
3. **Detailed Feedback**: Developers receive specific, actionable feedback
4. **Prevents Bad Deploys**: Failed code never reaches integration/testing
5. **Learning**: All retry feedback stored in RAG for future reference
6. **Transparency**: Full retry history in pipeline reports

## Example Scenario

### Initial Implementation (Attempt 1)
- Developer A creates HTML presentation
- Code review finds 2 CRITICAL issues:
  - Missing real metrics on Slide 3 (requirements violation)
  - Output file at wrong location
- Overall score: 67/100
- Status: **FAIL**

### Retry (Attempt 2)
- Pipeline stores detailed feedback in RAG
- Development stage re-runs with feedback in context
- Developer A receives:
  - "Slide 3 is missing real metrics from an actual Artemis run"
  - "Output file not located at '/tmp/developer-a/slides/artemis_showcase.html'"
- Developer A re-implements with fixes

### Result
- Code review passes with 0 critical issues
- Status: **PASS**
- Pipeline continues to completion
- Final report shows: `total_retries: 1`

## Future Enhancements

Potential improvements:
- Expose `max_retries` as CLI parameter
- Add retry strategy configuration (exponential backoff, etc.)
- Implement partial retries (only re-run failed components)
- Add retry analytics and success rate tracking
- Progressive severity thresholds (retry on CRITICAL only for first retry)

## Related Documentation

- **Code Review Agent**: `prompts/code_review_agent_prompt.md`
- **Requirements Validation**: Category 0 in code review prompt
- **RAG Agent**: `rag_agent.py` (for feedback storage)
- **Pipeline Stages**: `artemis_stages.py` (development stage)
