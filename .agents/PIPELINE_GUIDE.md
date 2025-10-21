# Agentic Development Pipeline - Usage Guide

## Quick Start

To use the agentic pipeline for development tasks:

```bash
# From /home/bbrelin/src/repos/salesforce/
cd .agents
./run_pipeline.sh "Add pause button to presentation"
```

The pipeline will automatically:
1. Break down your request (Orchestrator)
2. Generate 2 solutions in parallel (Developers A & B)
3. Validate syntax (Validator)
4. Integrate winning solution (Integration)
5. Test comprehensively (Tester)
6. Make final decision (Arbitrator)

## How the Pipeline Works

### Flow Diagram

```
USER REQUEST
    ↓
ORCHESTRATOR (creates task spec)
    ↓
    ├─→ DEVELOPER A (conservative)
    └─→ DEVELOPER B (innovative)
    ↓
VALIDATOR (checks both for syntax errors)
    ↓
ARBITRATOR (scores and selects winner OR requests iteration)
    ↓
    ├─→ [If iteration needed] → Back to Developers with feedback
    └─→ [If winner selected] → Continue
    ↓
INTEGRATION (merges winning solution into notebook)
    ↓
TESTER (executes notebook and validates)
    ↓
    ├─→ [If tests fail] → Back to Arbitrator for iteration
    └─→ [If tests pass] → SUCCESS!
```

### Agent Responsibilities

1. **ORCHESTRATOR** - Analyzes request, creates specification
   - Input: User's plain English request
   - Output: JSON task specification
   - Runtime: ~10 seconds

2. **DEVELOPER A** - Conservative implementation
   - Input: Task specification
   - Output: Minimal change solution
   - Runtime: ~30 seconds
   - Philosophy: Stability over features

3. **DEVELOPER B** - Innovative implementation
   - Input: Task specification
   - Output: Comprehensive solution with enhancements
   - Runtime: ~45 seconds
   - Philosophy: Quality and future-proofing

4. **VALIDATOR** - Syntax validation
   - Input: Both solutions
   - Output: Validation reports
   - Runtime: ~20 seconds
   - Checks: JavaScript, Python, f-strings, HTML, CSS

5. **INTEGRATION** - Merge winning solution
   - Input: Selected solution
   - Output: Updated notebook
   - Runtime: ~15 seconds
   - Creates backup before modifying

6. **TESTER** - Execute and validate
   - Input: Updated notebook
   - Output: Comprehensive test report
   - Runtime: ~60 seconds (notebook execution time)
   - Tests: All 12 slides, JavaScript, DOM, variables, functions

7. **ARBITRATOR** - Final decision maker
   - Input: Validation + test reports
   - Output: Winner selection or iteration request
   - Runtime: ~10 seconds
   - Uses objective scoring (100-point scale)

### Total Pipeline Time

- **Happy path** (first attempt works): ~3 minutes
- **One iteration** (needs fixes): ~6 minutes
- **Multiple iterations**: ~9-12 minutes (max 3 iterations)

## Using Individual Agents

You can also invoke agents individually for debugging:

### 1. Orchestrator Only

```bash
# Create task specification from request
claude-code --agent orchestrator "Add keyboard shortcut for pause"
```

Output saved to: `.agents/tasks/task-{timestamp}.json`

### 2. Run Both Developers

```bash
# Give them the same task spec
claude-code --agent developer-a --task tasks/task-123.json
claude-code --agent developer-b --task tasks/task-123.json
```

Outputs saved to:
- `.agents/solutions/solution-A-{timestamp}.json`
- `.agents/solutions/solution-B-{timestamp}.json`

### 3. Validate Solutions

```bash
claude-code --agent validator \
  --solution-a solutions/solution-A-123.json \
  --solution-b solutions/solution-B-123.json
```

Output: `.agents/validations/validation-{timestamp}.json`

### 4. Test Integration

```bash
# Apply a solution without running full pipeline
claude-code --agent integration --solution solutions/solution-A-123.json
```

Output: `.agents/integration/integration-{timestamp}.json`

### 5. Run Tests

```bash
claude-code --agent tester
```

Output: `.agents/test-reports/test-{timestamp}.json`

### 6. Arbitrate

```bash
claude-code --agent arbitrator \
  --validation validations/validation-123.json \
  --test test-reports/test-123.json
```

Output: `.agents/decisions/decision-{timestamp}.json`

## Common Workflows

### Workflow 1: Standard Development Task

```bash
# Single command runs entire pipeline
./run_pipeline.sh "Add search functionality to presentation"
```

The pipeline automatically:
- Creates task spec
- Generates 2 solutions
- Validates both
- Selects winner
- Integrates into notebook
- Tests comprehensively
- Reports results

### Workflow 2: Fixing Current Issues

For the current `isPaused` variable error:

```bash
./run_pipeline.sh "Fix isPaused variable missing error"
```

Expected behavior:
- Orchestrator identifies: "Need to add 'let isPaused = false;' declaration"
- Developer A: Adds single line at line 1516
- Developer B: Adds line + refactors state management
- Validator: Checks both have proper syntax
- Arbitrator: Likely selects A (simpler, lower risk)
- Integration: Adds the one line
- Tester: Confirms no more isPaused errors

### Workflow 3: Debugging a Failed Solution

If pipeline fails after 3 iterations:

```bash
# Review the decision trail
cat .agents/decisions/decision-*.json | jq '.iteration_number, .feedback_to_agent_a'

# See what went wrong
cat .agents/test-reports/test-*.json | jq '.blocker_issues'

# Try manual fix
claude-code --agent integration --manual-fix <your fix>
```

## Pipeline Configuration

### Adjusting Iteration Limits

Edit `.agents/config.json`:

```json
{
  "max_iterations": 3,
  "timeout_per_agent": 120,
  "auto_deploy": false,
  "require_approval": true
}
```

- `max_iterations`: How many times to retry before escalating (default: 3)
- `timeout_per_agent`: Seconds before killing an agent (default: 120)
- `auto_deploy`: Whether to auto-deploy winning solution (default: false)
- `require_approval`: Ask user before deploying (default: true)

### Tuning Arbitrator Scoring

Edit `.agents/arbitrator_config.json`:

```json
{
  "weights": {
    "syntax": 0.40,
    "testing": 0.40,
    "quality": 0.20
  },
  "passing_threshold": 70,
  "tie_breaker": "prefer_conservative"
}
```

## Monitoring and Logging

### View Pipeline Status

```bash
# Real-time pipeline status
tail -f .agents/logs/pipeline.log
```

### View Agent Outputs

All agent outputs are saved in `.agents/` directory:

```
.agents/
├── tasks/           # Orchestrator outputs
├── solutions/       # Developer outputs
├── validations/     # Validator reports
├── integration/     # Integration reports
├── test-reports/    # Tester outputs
├── decisions/       # Arbitrator decisions
└── logs/            # All logging
```

### Debugging Failed Runs

```bash
# Find the latest failed run
cd .agents/logs
grep "ERROR" pipeline.log | tail -20

# Check which agent failed
cat pipeline.log | jq 'select(.status == "failed")'

# Review that agent's output
cat solutions/solution-A-{timestamp}.json | jq '.risk_assessment'
```

## Best Practices

### 1. Clear Request Descriptions

❌ Bad: "Fix the button"
✅ Good: "Fix the pause button so it properly toggles auto-play on/off"

❌ Bad: "Make it work"
✅ Good: "Ensure all 12 slides render without JavaScript errors"

### 2. Let the Pipeline Iterate

Don't interrupt after first failure. The pipeline is designed to iterate and improve.

### 3. Review Arbitrator Decisions

After completion, review:

```bash
cat .agents/decisions/latest.json | jq '.rationale'
```

Understand WHY a solution was chosen.

### 4. Archive Successful Solutions

```bash
# After successful deployment
mv .agents/solutions/solution-A-*.json .agents/archive/successful/
```

### 5. Learn from Failures

```bash
# Review what went wrong in failed attempts
cat .agents/decisions/*-iteration-*.json | jq '.feedback_to_agent_a.issues[].problem'
```

## Integration with Claude Code

The pipeline is designed to work seamlessly with Claude Code's Task tool.

Each agent invocation becomes:

```python
# In Claude Code conversation
Task(
    description="Run Developer Agent A",
    prompt=f"""
    {read_file('.agents/developer_a_prompt.md')}

    TASK SPECIFICATION:
    {task_spec}

    Provide your solution following the output format specified in the prompt.
    """,
    subagent_type="general-purpose"
)
```

## Troubleshooting

### Issue: Pipeline hangs on agent

**Cause:** Agent taking too long (> 2 minutes)
**Solution:**
```bash
# Check agent status
ps aux | grep claude-code

# Kill if needed
killall -9 claude-code

# Restart with higher timeout
./run_pipeline.sh --timeout 300 "your request"
```

### Issue: Both solutions failing validation

**Cause:** Task specification unclear or too complex
**Solution:**
- Simplify the request
- Break into smaller tasks
- Review orchestrator output for clarity

### Issue: Tests passing but runtime errors

**Cause:** Tester not catching all edge cases
**Solution:**
- Manually test the presentation in browser
- Add new test cases to tester_prompt.md
- Report the gap to improve Tester

### Issue: Arbitrator always picks Agent A

**Cause:** Agent B solutions tend to be more risky
**Solution:**
- Review `arbitrator_config.json` weights
- Maybe increase quality weight
- Review Developer B's risk assessments

## Advanced Usage

### Custom Agent

Create your own specialized agent:

```bash
# Create prompt
cat > .agents/my_agent_prompt.md <<'EOF'
# MY CUSTOM AGENT

You are specialized in...
EOF

# Use in pipeline
claude-code --agent custom --prompt my_agent_prompt.md --task task.json
```

### Parallel Testing

Run multiple test scenarios:

```bash
# Test with different Python versions
docker run python:3.9 ./run_tests.sh
docker run python:3.10 ./run_tests.sh
docker run python:3.11 ./run_tests.sh
```

### A/B Testing Solutions

Deploy both solutions to test environments:

```bash
# Deploy Agent A to staging-a
./deploy.sh --solution A --env staging-a

# Deploy Agent B to staging-b
./deploy.sh --solution B --env staging-b

# Compare metrics after 24h
./compare_metrics.sh staging-a staging-b
```

## Future Enhancements

Planned features:

1. **Machine Learning Integration**
   - Learn from past successes/failures
   - Predict which solution will score higher
   - Auto-tune arbitrator weights

2. **Performance Agent**
   - Optimize for speed/size
   - Bundle analysis
   - Caching strategies

3. **Security Agent**
   - XSS prevention
   - Input sanitization
   - Dependency audits

4. **UI Testing Agent**
   - Selenium-based visual regression
   - Screenshot comparison
   - Interaction recording

5. **Documentation Agent**
   - Auto-generate API docs
   - Update README files
   - Create changelog entries

## Getting Help

```bash
# View pipeline help
./run_pipeline.sh --help

# View agent-specific help
claude-code --agent developer-a --help

# Check configuration
cat .agents/config.json | jq

# Validate agent prompts
./validate_prompts.sh
```

## Summary

The agentic pipeline provides:
✅ Parallel development (2 approaches simultaneously)
✅ Automatic syntax validation (catches errors before execution)
✅ Comprehensive testing (all slides, all features)
✅ Objective selection (100-point scoring system)
✅ Iteration loops (auto-fixes based on feedback)
✅ Audit trail (all decisions logged)

This eliminates the "rookie mistakes" by:
1. Having a dedicated Validator catch syntax errors
2. Testing comprehensively before deployment
3. Allowing iteration when issues are found
4. Maintaining objective standards via scoring

The result: **Higher quality code with fewer errors**.
