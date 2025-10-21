# Agentic Development Pipeline for Salesforce AI Presentation

## What This Is

A multi-agent system designed to eliminate syntax errors and workflow issues in the Salesforce AI Presentation development.

**The Problem:**
- Manual code changes causing JavaScript syntax errors (missing braces, undefined variables)
- f-string brace escaping errors (`{` vs `{{`)
- No validation before notebook execution
- Errors discovered only after running (wasted time)

**The Solution:**
- 7 specialized AI agents working in a pipeline
- Automatic syntax validation BEFORE execution
- Parallel development of 2 solutions (conservative vs innovative)
- Comprehensive testing of all 12 slides
- Objective selection criteria
- Automatic iteration when errors found

## Architecture

```
USER REQUEST → ORCHESTRATOR → DEVELOPERS (A & B) → VALIDATOR
                                                        ↓
TESTER ← INTEGRATION ← ARBITRATOR ←──────────────────────┘
   ↓                      ↓
SUCCESS              [ITERATION LOOP]
```

### 7 Agents

1. **Orchestrator** - Breaks down requests into specifications
2. **Developer A** - Conservative, minimal-change solutions
3. **Developer B** - Innovative, comprehensive solutions
4. **Validator** - Validates syntax (JS, Python, f-strings, HTML, CSS)
5. **Integration** - Merges winning solution into notebook
6. **Tester** - Executes notebook and validates all features
7. **Arbitrator** - Scores solutions and selects winner

## Quick Start

### Current Issue: Fix `isPaused` Variable Error

You can fix the current `isPaused` undefined variable error using the pipeline:

```bash
# In Claude Code conversation, use this command:
/fix_presentation "Add isPaused variable declaration that's currently missing"
```

**Or manually:**

The issue is that `isPaused` variable is used but never declared. Fix:

1. Open the notebook cell 50
2. Find line ~1516 where variables are declared
3. Add this line after `let ragTimers = [];`:
   ```javascript
   let isPaused = false;
   ```
4. Make sure it uses single `{` and `}` (the f-string will escape them)

### Setting Up the Pipeline

The pipeline is already configured! Agent prompts are in:
- `.agents/orchestrator_prompt.md`
- `.agents/developer_a_prompt.md`
- `.agents/developer_b_prompt.md`
- `.agents/validator_prompt.md`
- `.agents/integration_prompt.md`
- `.agents/tester_prompt.md`
- `.agents/arbitrator_prompt.md`

### Using the Pipeline in Claude Code

Since this pipeline uses the Task tool within Claude Code, you can invoke it like this:

```markdown
I need to add a pause button to the presentation.

Use the agentic pipeline:
1. Read .agents/orchestrator_prompt.md and create task spec
2. Launch Developer A and Developer B in parallel with their prompts
3. Launch Validator to check both solutions
4. Based on validation, launch Arbitrator to select winner
5. Launch Integration to apply winning solution
6. Launch Tester to verify it works
```

Claude will then execute each agent using the Task tool.

## File Structure

```
.agents/
├── README.md                    # This file
├── PIPELINE_GUIDE.md           # Detailed usage guide
├── orchestrator_prompt.md      # Orchestrator agent prompt
├── developer_a_prompt.md       # Conservative developer
├── developer_b_prompt.md       # Innovative developer
├── validator_prompt.md         # Syntax validator
├── integration_prompt.md       # Integration agent
├── tester_prompt.md            # Test & QA agent
├── arbitrator_prompt.md        # Decision maker
└── tasks/                      # Generated task specs (created on use)
    ├── solutions/              # Developer solutions
    ├── validations/            # Validation reports
    ├── test-reports/           # Test results
    └── decisions/              # Arbitrator decisions
```

## Why This Fixes The Problems

### Problem: "How are you making all these rookie mistakes?"

**Root Causes:**
1. No syntax validation before execution
2. f-string brace escaping confusion
3. Incremental changes without full context
4. Not using error messages properly
5. No testing after each change

**How Pipeline Fixes Each:**

1. **Validator Agent** catches syntax errors before notebook execution
   - Runs Node.js `--check` on JavaScript
   - Counts {{ }} braces for f-string balance
   - Validates all undefined variables
   - Checks function declarations

2. **Two Developers** provide redundancy
   - If one makes a mistake, the other might not
   - Different approaches increase chances of success
   - Arbitrator picks the better solution

3. **Objective Scoring** removes bias
   - 40 points: Syntax (must be perfect)
   - 40 points: Tests (all slides must work)
   - 20 points: Quality (nice to have)
   - No guessing, just scoring

4. **Iteration Loop** auto-fixes errors
   - If both solutions fail, Arbitrator provides specific feedback
   - Developers get EXACT line numbers and fixes needed
   - Up to 3 iterations before escalating to human

5. **Comprehensive Testing** catches runtime errors
   - Executes notebook
   - Validates all 12 slides exist
   - Checks JavaScript runs without errors
   - Verifies DOM elements present
   - Tests interactive features

## Example: Fixing Current Issue

### Current Error

```
Uncaught ReferenceError: isPaused is not defined
    scheduleNextSlide file:///.../salesforce_ai_presentation.html:1893
```

### How Pipeline Would Fix It

**Step 1: Orchestrator**
```json
{
  "task": "Add missing isPaused variable declaration",
  "target": "cell 50, line ~1516",
  "fix": "Add 'let isPaused = false;' after other variable declarations"
}
```

**Step 2: Developer A (Conservative)**
```javascript
// Simply adds the line
let ragTimers = [];
let isPaused = false;  // ← NEW LINE
```

**Step 3: Developer B (Innovative)**
```javascript
// Refactors into state object
const state = {
    currentSlide: 0,
    isPaused: false,  // ← INCLUDED HERE
    timers: {...}
};
```

**Step 4: Validator**
- Agent A: ✅ Syntax valid, 1 line added
- Agent B: ❌ Undefined variable `state` used elsewhere

**Step 5: Arbitrator**
- Agent A score: 95/100 (perfect syntax, minimal change)
- Agent B score: 60/100 (syntax errors in refactor)
- **Winner: Agent A**

**Step 6: Integration**
- Adds `let isPaused = false;` at line 1516
- Verifies brace balance
- Saves notebook

**Step 7: Tester**
- Executes notebook → ✅ Success
- Checks 12 slides → ✅ All present
- JavaScript validation → ✅ No errors
- Variable check → ✅ isPaused declared
- **Result: PASS**

**Total time: ~3 minutes**
**Result: Error fixed with confidence**

## Benefits Over Manual Fixing

| Manual Approach | Pipeline Approach |
|----------------|-------------------|
| Change code blindly | Validator checks first |
| Hope it works | Test before deploying |
| Discover errors after execution | Catch errors before execution |
| One approach (might be wrong) | Two approaches (pick better) |
| No feedback loop | Auto-iteration with fixes |
| Subjective decisions | Objective scoring |
| Time wasted on failures | Fast iteration |

## When to Use What

### Use Full Pipeline For:
- ✅ New features (pause button, search, etc.)
- ✅ Complex changes (refactoring, architecture)
- ✅ Bug fixes where root cause is unclear
- ✅ Changes affecting multiple areas

### Use Individual Agents For:
- 🔧 Validator only: Check existing code
- 🔧 Tester only: Verify current state
- 🔧 Orchestrator only: Understand a request

### Fix Manually For:
- ⚡ Typos (if you're certain)
- ⚡ Single variable declarations
- ⚡ Obvious simple fixes

## Next Steps

### 1. Test the Pipeline

Try fixing the current `isPaused` error using the pipeline:

```
In Claude Code:
"Use the agentic pipeline to fix the isPaused undefined variable error"
```

### 2. Add MCP Server (Optional)

For better JavaScript validation, install the code-validator MCP server:

```bash
# See: /tmp/agentic_pipeline_architecture.md
# Section: "Custom MCP Server: Code Validator"
```

### 3. Customize Agents

Edit agent prompts to match your preferences:
- Adjust Developer A's conservatism level
- Tune Developer B's innovation threshold
- Change Arbitrator scoring weights

### 4. Monitor and Learn

After each pipeline run, review:
```bash
cat .agents/decisions/latest.json | jq '.rationale'
```

Learn what works and what doesn't.

## Troubleshooting

### Pipeline Not Available in Claude Code

The pipeline uses Claude Code's Task tool. Make sure you're in Claude Code, not regular Claude.

### Agents Taking Too Long

Increase timeout in conversation:
```
Set agent timeout to 5 minutes
```

### Both Solutions Failing

The task might be too complex. Break it down:
```
Instead of: "Refactor the entire presentation system"
Try: "Add pause button" (Step 1)
Then: "Add keyboard shortcuts" (Step 2)
```

### Need Human Intervention

If pipeline escalates after 3 iterations:
1. Review the decision trail in `.agents/decisions/`
2. Understand what's failing
3. Either:
   - Simplify the request
   - Fix manually and use as example for agents
   - Improve agent prompts based on learnings

## Documentation

- **PIPELINE_GUIDE.md** - Comprehensive usage guide
- **agentic_pipeline_architecture.md** - Full technical architecture (in `/tmp/`)
- Individual agent prompts - Each agent's detailed instructions

## Support

If you encounter issues with the pipeline:

1. Check `.agents/logs/` for error details
2. Review agent prompts for clarity
3. Simplify the request
4. Try manual fix and use as training example

## Summary

This pipeline **prevents the rookie mistakes** by:
- ✅ Validating syntax before execution
- ✅ Testing comprehensively before deployment
- ✅ Providing parallel solutions
- ✅ Using objective selection criteria
- ✅ Iterating automatically on errors

Result: **Reliable, error-free development** for the Salesforce AI Presentation.
