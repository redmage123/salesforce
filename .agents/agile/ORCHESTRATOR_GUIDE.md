# Pipeline Orchestrator - Quick Reference Guide

The Pipeline Orchestrator automates the execution of pipeline stages with **dynamic workflow planning** that adapts to task complexity, type, and requirements.

## ✨ New: Dynamic Workflow Planning

The orchestrator now automatically analyzes each task and creates a custom execution plan:

- **Task Complexity Analysis**: Evaluates priority, story points, and description keywords
- **Parallel Developer Scaling**: Runs 1-3 developers based on complexity
  - Simple tasks: 1 developer
  - Medium tasks: 2 developers in parallel
  - Complex tasks: 3 developers in parallel
- **Smart Stage Skipping**: Skips unnecessary stages (e.g., arbitration for single developer, testing for documentation)
- **Resource Management**: Optimizes execution based on task type

### Complexity Scoring

The planner analyzes:
1. **Priority**: High priority tasks get +2 complexity points
2. **Story Points**: More points = higher complexity
3. **Keywords**:
   - Complex: 'integrate', 'architecture', 'refactor', 'performance', 'api'
   - Simple: 'fix', 'update', 'small', 'minor', 'quick'

### Task Types

Automatically detected:
- **Feature**: New functionality (full workflow)
- **Bugfix**: Error corrections (standard workflow)
- **Refactor**: Code restructuring (standard workflow)
- **Documentation**: Docs updates (skips automated testing)

## 🚀 Quick Start

### Run Full Pipeline (Validation → Testing → Done)

```bash
python3 pipeline_orchestrator.py --card-id card-20251021055822 --full
```

This will:
1. ✅ Validate both Developer A and B solutions
2. ✅ Run arbitration to select winner
3. ✅ Integrate winning solution
4. ✅ Run comprehensive testing
5. ✅ Move card to Done (if all pass)

### Continue from Current Stage

```bash
python3 pipeline_orchestrator.py --card-id card-20251021055822 --continue
```

Automatically detects current stage and runs remaining stages to completion.

## 📋 Individual Stage Execution

### Run Validation Only

```bash
python3 pipeline_orchestrator.py --card-id card-20251021055822 --stage validation
```

**What it does**:
- Validates Developer A solution
- Validates Developer B solution
- Checks TDD compliance (9 checks per developer)
- Runs all tests
- Blocks incomplete/failing solutions
- Moves approved solutions to Arbitration

### Run Arbitration Only

```bash
python3 pipeline_orchestrator.py --card-id card-20251021055822 --stage arbitration
```

**What it does**:
- Scores approved developers using 100-point system
- Categories: Syntax, TDD, Coverage, Test Quality, Functionality, Code Quality, Simplicity
- Selects winner (highest score or simplest if tied)
- Updates Kanban board with winner
- Moves to Integration

### Run Integration Only

```bash
python3 pipeline_orchestrator.py --card-id card-20251021055822 --stage integration
```

**What it does**:
- Loads winning solution
- Runs regression tests (all tests must pass)
- Verifies deployment in HTML file
- Moves to Testing if successful

### Run Testing Only

```bash
python3 pipeline_orchestrator.py --card-id card-20251021055822 --stage testing
```

**What it does**:
- Final regression test run
- UI/UX quality evaluation (score ≥80/100)
- Performance evaluation (score ≥70/100)
- Quality gates check
- Moves to Done if all pass

## 🎯 Common Use Cases

### Use Case 1: Automated Full Pipeline

**Scenario**: You have Developer A and B solutions ready, want to run full pipeline autonomously.

```bash
# Single command - runs everything
python3 pipeline_orchestrator.py --card-id card-20251021055822 --full
```

**Expected Output**:
```
[07:30:00] 🔄 Starting Validation Stage
[07:30:05] ✅ Validation complete: DEVELOPER_A_ONLY
[07:30:05] ✅ Card moved to Arbitration
[07:30:05] 🔄 Starting Arbitration Stage
[07:30:10] ✅ Arbitration complete: Winner = developer-a
[07:30:10] ✅ Card moved to Integration
[07:30:10] 🔄 Starting Integration Stage
[07:30:15] ✅ Integration complete: All tests passing
[07:30:15] ✅ Card moved to Testing
[07:30:15] 🔄 Starting Testing Stage
[07:30:20] ✅ Testing complete: All quality gates passed
[07:30:20] ✅ Card moved to Done
[07:30:20] 🎉 PIPELINE COMPLETED SUCCESSFULLY!
```

### Use Case 2: Continue After Manual Work

**Scenario**: You manually fixed something in Development, now want automated execution to Done.

```bash
# Check where card is
python3 kanban_manager.py show

# Continue from current stage
python3 pipeline_orchestrator.py --card-id card-20251021055822 --continue
```

### Use Case 3: Re-run Specific Stage

**Scenario**: Testing failed, you made a fix, want to re-run just testing.

```bash
# Re-run testing stage only
python3 pipeline_orchestrator.py --card-id card-20251021055822 --stage testing
```

### Use Case 4: Quiet Mode (Less Output)

**Scenario**: Running in CI/CD, want minimal output.

```bash
python3 pipeline_orchestrator.py --card-id card-20251021055822 --full --quiet
```

## 📊 Output Reports

The orchestrator generates detailed JSON reports:

### Validation Report
**File**: `/tmp/validation_report_autonomous.json`

```json
{
  "stage": "validation",
  "developer_a": {
    "status": "APPROVED",
    "test_results": { "passed": 16, "failed": 0 },
    "blockers": []
  },
  "developer_b": {
    "status": "BLOCKED",
    "blockers": [{"id": "B003", "message": "1 test(s) failing"}]
  },
  "decision": "DEVELOPER_A_ONLY",
  "next_stage": "arbitration"
}
```

### Arbitration Report
**File**: `/tmp/arbitration_report_autonomous.json`

```json
{
  "stage": "arbitration",
  "developer_a_score": {
    "total_score": 93,
    "categories": {
      "syntax_structure": 20,
      "tdd_compliance": 10,
      "test_coverage": 15,
      "test_quality": 15,
      "functional_correctness": 13,
      "code_quality": 15,
      "simplicity_bonus": 5
    }
  },
  "winner": "developer-a",
  "decision": "SELECT"
}
```

### Integration Report
**File**: `/tmp/integration_report_autonomous.json`

```json
{
  "stage": "integration",
  "winner": "developer-a",
  "regression_tests": {
    "total": 16,
    "passed": 16,
    "failed": 0,
    "pass_rate": "100.0%"
  },
  "deployment_verified": true,
  "status": "PASS"
}
```

### Testing Report
**File**: `/tmp/testing_report_autonomous.json`

```json
{
  "stage": "testing",
  "regression_tests": { "passed": 16, "failed": 0 },
  "uiux_score": 95,
  "performance_score": 85,
  "all_quality_gates_passed": true,
  "status": "PASS"
}
```

### Full Pipeline Report
**File**: `/tmp/pipeline_full_report_<card-id>.json`

Contains results from all stages in a single file.

## 🔧 How It Works

### Validation Stage
1. Checks if developer directories exist (`/tmp/developer_a`, `/tmp/developer_b`)
2. Loads `solution_package.json` from each developer
3. Runs pytest on `tests/` directory
4. Validates TDD compliance (tests written first, coverage requirements)
5. Blocks developers with failing tests or missing requirements
6. Moves approved solutions to Arbitration

### Arbitration Stage
1. Loads validation results
2. Scores each approved developer (0-100 points)
3. Compares scores to select winner
4. If tied, prefers simpler solution (Developer A's conservative approach)
5. Updates Kanban card with winner
6. Moves to Integration

### Integration Stage
1. Loads arbitration results to get winner
2. Re-runs all tests (regression check)
3. Verifies deployment in HTML file
4. Blocks if tests fail or deployment not verified
5. Moves to Testing if successful

### Testing Stage
1. Final regression test run (all tests must pass 100%)
2. Evaluates UI/UX quality (checks HTML/CSS properties)
3. Evaluates performance (test execution time, file size)
4. Checks quality gates:
   - All tests passing (100%)
   - UI/UX score ≥80/100
   - Performance score ≥70/100
5. Moves to Done if all gates pass

## 📈 Success Criteria

Each stage has specific success criteria:

### Validation
- ✅ All tests passing (0 failures)
- ✅ TDD compliance verified
- ✅ Coverage ≥80% (Dev A) or ≥90% (Dev B)
- ✅ No critical blockers

### Arbitration
- ✅ Score ≥60/100 (minimum)
- ✅ Winner selected

### Integration
- ✅ All regression tests passing
- ✅ Deployment verified

### Testing
- ✅ 100% test pass rate
- ✅ UI/UX score ≥80/100
- ✅ Performance score ≥70/100

## ❌ Common Failure Scenarios

### Validation Fails
**Reason**: Developer has failing tests

```bash
# Output
[07:30:00] 🔄 Starting Validation Stage
[07:30:05] ❌ Developer B blocked: 1 test(s) failing
[07:30:05] ✅ Developer A approved
[07:30:05] ✅ Validation complete: DEVELOPER_A_ONLY
```

**Solution**: Fix failing tests, re-run validation

### Arbitration Fails
**Reason**: No developer scored ≥60/100

```bash
# Output
[07:30:00] 🔄 Starting Arbitration Stage
[07:30:05] ❌ Developer A score: 45/100 (below minimum 60)
[07:30:05] ❌ No winner selected
```

**Solution**: Improve solution quality, re-run arbitration

### Integration Fails
**Reason**: Regression tests failing after integration

```bash
# Output
[07:30:00] 🔄 Starting Integration Stage
[07:30:05] ❌ Regression tests: 14/16 passing (2 failed)
[07:30:05] ❌ Integration failed
```

**Solution**: Fix regressions, re-run integration

### Testing Fails
**Reason**: Quality gates not met

```bash
# Output
[07:30:00] 🔄 Starting Testing Stage
[07:30:05] ✅ Regression tests: 16/16 passing
[07:30:10] ⚠️ UI/UX score: 75/100 (below 80)
[07:30:10] ❌ Quality gate failed
```

**Solution**: Improve UI/UX, re-run testing

## 🔄 Integration with Claude Code

### Pre-Approve the Orchestrator

Add to your Claude Code settings to auto-approve:

```
Bash(python3 .agents/agile/pipeline_orchestrator.py *)
```

### Use from Chat

```
You: "Run the full pipeline for card-20251021055822"

Claude: [Automatically runs pipeline_orchestrator.py --full]
```

## 💡 Tips & Best Practices

### Tip 1: Use --continue for Interrupted Pipelines

If a pipeline fails at any stage, fix the issue and use `--continue` to resume:

```bash
# Pipeline failed at Integration
# Fix the issue
# Resume from Integration
python3 pipeline_orchestrator.py --card-id card-123 --continue
```

### Tip 2: Check Reports for Detailed Failures

If a stage fails, check the JSON report for details:

```bash
cat /tmp/validation_report_autonomous.json | jq '.developer_a.blockers'
```

### Tip 3: Run Individual Stages During Development

While developing, run stages individually to iterate faster:

```bash
# Make changes to tests
python3 pipeline_orchestrator.py --card-id card-123 --stage validation

# Validation passed, make UI changes
python3 pipeline_orchestrator.py --card-id card-123 --stage testing
```

### Tip 4: Use Quiet Mode in Scripts

When calling from other scripts or CI/CD:

```bash
#!/bin/bash
if python3 pipeline_orchestrator.py --card-id $1 --full --quiet; then
  echo "Pipeline succeeded"
  notify-user "Card $1 is done!"
else
  echo "Pipeline failed"
  notify-user "Card $1 failed - check logs"
fi
```

## 📞 Exit Codes

The orchestrator uses standard exit codes:

- **0**: Success (pipeline completed or already complete)
- **1**: Failure (stage failed or blocked)

Use in shell scripts:

```bash
if python3 pipeline_orchestrator.py --card-id card-123 --full; then
  echo "Success!"
else
  echo "Failed!"
fi
```

## 🎓 Examples

### Example 1: Full Pipeline for New Card

```bash
# Create card (done manually or via orchestrator in backlog)
# Developers work on it
# Run full pipeline
python3 pipeline_orchestrator.py \
  --card-id card-20251021-new \
  --full
```

### Example 2: Continue After Manual Arbitration

```bash
# You manually reviewed and selected winner
# Now automate the rest
python3 kanban_manager.py move card-123 integration
python3 pipeline_orchestrator.py --card-id card-123 --continue
```

### Example 3: Re-validation After Fixes

```bash
# Developer B fixed their failing test
# Re-run just validation
python3 pipeline_orchestrator.py \
  --card-id card-123 \
  --stage validation
```

## 🚨 Troubleshooting

### "Card not found"
**Solution**: Check card ID is correct, card exists in Kanban board

```bash
python3 kanban_manager.py show
```

### "No developer path found"
**Solution**: Ensure `/tmp/developer_a` and `/tmp/developer_b` exist

```bash
ls -la /tmp/developer_*
```

### "Tests not found"
**Solution**: Ensure tests exist in `/tmp/developer_*/tests/`

```bash
ls -la /tmp/developer_a/tests/
```

### "Import Error: kanban_manager"
**Solution**: Run from correct directory

```bash
cd /home/bbrelin/src/repos/salesforce/.agents/agile
python3 pipeline_orchestrator.py --card-id card-123 --full
```

## 📚 Advanced Usage

### Custom Scoring Thresholds

Edit `_score_solution()` in `pipeline_orchestrator.py` to adjust scoring:

```python
# Require higher coverage
if coverage >= 90:  # Changed from 85
    coverage_score = 15
```

### Custom Quality Gates

Edit `run_testing_stage()` to adjust quality gates:

```python
quality_gates_passed = (
    test_results["pass_rate"] == "100.0%" and
    uiux_score >= 90 and  # Raised from 80
    performance_score >= 80  # Raised from 70
)
```

### Integration with CI/CD

```yaml
# .github/workflows/pipeline.yml
name: Run Pipeline
on: [push]
jobs:
  pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Pipeline
        run: |
          python3 pipeline_orchestrator.py \
            --card-id ${{ github.sha }} \
            --full \
            --quiet
```

---

## 🎯 Summary

**Single Command Pipeline**:
```bash
python3 pipeline_orchestrator.py --card-id <card-id> --full
```

**Continue from Current**:
```bash
python3 pipeline_orchestrator.py --card-id <card-id> --continue
```

**Individual Stage**:
```bash
python3 pipeline_orchestrator.py --card-id <card-id> --stage <validation|arbitration|integration|testing>
```

That's it! The orchestrator handles the rest autonomously. 🚀
