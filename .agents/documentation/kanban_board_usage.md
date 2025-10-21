# KANBAN BOARD USAGE GUIDE

**For Agentic Pipeline Agents**

---

## Quick Start

The Kanban board tracks all tasks through the pipeline from creation to completion. Every task must have a corresponding card on the board.

**Board Location**: `/home/bbrelin/src/repos/salesforce/.agents/agile/kanban_board.json`
**Manager Script**: `/home/bbrelin/src/repos/salesforce/.agents/agile/kanban_manager.py`

---

## For Each Agent

### Orchestrator Agent

**When you receive a new task:**

```python
from kanban_manager import KanbanBoard

board = KanbanBoard()

# Create a new card
card = board.create_card(
    task_id="feature-xyz-001",
    title="Implement XYZ Feature",
    description="Full description of the task",
    priority="high",  # high|medium|low
    labels=["enhancement", "api"],
    size="medium",  # small|medium|large
    story_points=5,  # 1,2,3,5,8,13
    assigned_agents=["developer-a", "developer-b"],
    acceptance_criteria=[
        {
            "criterion": "Feature works without errors",
            "status": "pending",
            "verified_by": null
        }
    ]
)

# Move to orchestration column
board.move_card(
    card['card_id'],
    "orchestration",
    agent="orchestrator",
    comment="Creating task specification"
)

# After spec is complete, move to development
board.move_card(
    card['card_id'],
    "development",
    agent="orchestrator",
    comment="Specification complete, ready for TDD implementation"
)
```

### Developer A/B Agents

**When you start implementing:**

```python
from kanban_manager import KanbanBoard

board = KanbanBoard()

# Card should already be in "development" column
# Update test status as you write tests
board.update_test_status(
    card_id="card-20251021-001",
    test_status={
        "unit_tests_written": True,
        "unit_tests_passing": True,
        "integration_tests_written": True,
        "integration_tests_passing": True,
        "test_coverage_percent": 87
    }
)

# When implementation is complete, move to validation
board.move_card(
    "card-20251021-001",
    "validation",
    agent="developer-b",
    comment="Implementation complete with 87% test coverage"
)
```

### Validator Agent

**When validating a solution:**

```python
from kanban_manager import KanbanBoard

board = KanbanBoard()

# If validation passes
board.move_card(
    "card-20251021-001",
    "arbitration",
    agent="validator",
    comment="Validation passed: syntax OK, TDD compliance verified"
)

# If validation fails (block the card)
board.block_card(
    "card-20251021-001",
    reason="Test coverage below 80% (found 65%)",
    agent="validator"
)
```

### Arbitrator Agent

**After scoring solutions:**

```python
from kanban_manager import KanbanBoard

board = KanbanBoard()

# Update card with winning solution details
board.update_card(
    "card-20251021-001",
    updates={
        "arbitration_score": 92,
        "winning_solution": "developer-b"
    }
)

# Move to integration
board.move_card(
    "card-20251021-001",
    "integration",
    agent="arbitrator",
    comment="Developer B solution selected (score: 92/100)"
)
```

### Integration Agent

**When integrating the solution:**

```python
from kanban_manager import KanbanBoard

board = KanbanBoard()

# If integration succeeds
board.move_card(
    "card-20251021-001",
    "testing",
    agent="integration",
    comment="Integration complete, deployed to production location"
)

# If integration fails
board.block_card(
    "card-20251021-001",
    reason="Merge conflict in integration_agent_prompt.md",
    agent="integration"
)
```

### Test Agent

**When running final tests:**

```python
from kanban_manager import KanbanBoard

board = KanbanBoard()

# Verify acceptance criteria
board.verify_acceptance_criterion(
    card_id="card-20251021-001",
    criterion_index=0,
    verified_by="test-agent"
)

# Update definition of done
board.update_card(
    "card-20251021-001",
    updates={
        "definition_of_done": {
            "code_complete": True,
            "tests_passing": True,
            "code_reviewed": True,
            "documentation_updated": True,
            "deployed_to_production": True
        }
    }
)

# Move to done
board.move_card(
    "card-20251021-001",
    "done",
    agent="test-agent",
    comment="All tests passing (99/100 production readiness)"
)
```

### UI/UX Agent

**When blocking based on quality issues:**

```python
from kanban_manager import KanbanBoard

board = KanbanBoard()

# Block a card due to UI/UX issues
board.block_card(
    "card-presentation-fix-003",
    reason="CRITICAL: Slide 3 AI response not visible, demo blocker",
    agent="uiux-agent"
)
```

**When unblocking after fixes:**

```python
# Unblock after issue resolution
board.unblock_card(
    "card-presentation-fix-003",
    move_to_column="testing",
    agent="uiux-agent",
    resolution="Slide 3 AI response now visible, verified with screenshot"
)
```

---

## Board Columns

| Column | Purpose | WIP Limit |
|--------|---------|-----------|
| **Backlog** | All incoming tasks | None |
| **Orchestration** | Task specification in progress | 3 |
| **Development** | Developer A/B implementing with TDD | 2 |
| **Validation** | Syntax and TDD compliance checking | 2 |
| **Arbitration** | Solution scoring and selection | 1 |
| **Integration** | Merging and deploying solution | 1 |
| **Testing** | Final QA and verification | 2 |
| **Done** | Completed and deployed | None |
| **Blocked** | Requires intervention | None |

**WIP Limit Enforcement**: System warns when WIP limits are exceeded, but doesn't prevent the move (tracks as violation in metrics).

---

## Command Line Usage

```bash
# Display the board
python3 /home/bbrelin/src/repos/salesforce/.agents/agile/kanban_manager.py show

# Get board summary (JSON)
python3 /home/bbrelin/src/repos/salesforce/.agents/agile/kanban_manager.py summary

# Create a card
python3 /home/bbrelin/src/repos/salesforce/.agents/agile/kanban_manager.py create task-001 "Fix bug in validator"

# Move a card
python3 /home/bbrelin/src/repos/salesforce/.agents/agile/kanban_manager.py move card-20251021-001 validation

# Block a card
python3 /home/bbrelin/src/repos/salesforce/.agents/agile/kanban_manager.py block card-20251021-001 "Test coverage too low"

# Unblock a card
python3 /home/bbrelin/src/repos/salesforce/.agents/agile/kanban_manager.py unblock card-20251021-001 development
```

---

## Card Lifecycle

```
┌──────────┐
│ Backlog  │ ← Card created here
└────┬─────┘
     ↓
┌──────────────┐
│ Orchestration│ ← Task specification
└────┬─────────┘
     ↓
┌──────────────┐
│ Development  │ ← TDD: Write tests → Implement → Refactor
└────┬─────────┘
     ↓
┌──────────────┐
│ Validation   │ ← Check syntax, tests, TDD compliance
└────┬─────────┘
     ↓
┌──────────────┐
│ Arbitration  │ ← Score solutions, select winner
└────┬─────────┘
     ↓
┌──────────────┐
│ Integration  │ ← Merge and deploy
└────┬─────────┘
     ↓
┌──────────────┐
│ Testing & QA │ ← Final verification
└────┬─────────┘
     ↓
┌──────────────┐
│    Done      │ ← Completed!
└──────────────┘

     (Any stage can move to ↓ Blocked ↓ if issues arise)
```

---

## Metrics Tracked

The board automatically tracks:

- **Cycle Time**: Time from Orchestration → Done (target: < 4 hours)
- **Throughput**: Cards completed per sprint
- **Velocity**: Story points completed per sprint
- **WIP Violations**: Times WIP limits were exceeded
- **Blocked Items**: Current count of blocked cards

**View metrics**: They're displayed when you run `kanban_manager.py show`

---

## Best Practices

1. **Always create a card** when starting a new task
2. **Move cards promptly** as they progress through stages
3. **Update test status** as tests are written and pass
4. **Block immediately** when issues arise (don't let broken cards advance)
5. **Verify acceptance criteria** before marking done
6. **Add meaningful comments** when moving cards (helps retrospectives)
7. **Respect WIP limits** - if you hit a limit, finish existing work first
8. **Check the board** before starting work to see current state

---

## Example: Complete Task Flow

```python
from kanban_manager import KanbanBoard

board = KanbanBoard()

# 1. ORCHESTRATOR: Create task
card = board.create_card(
    task_id="email-notif-001",
    title="Add Email Notification on Notebook Failure",
    description="Send email when notebook execution fails",
    priority="medium",
    story_points=3,
    assigned_agents=["developer-a", "developer-b"],
    acceptance_criteria=[
        {"criterion": "Email sent on failure", "status": "pending", "verified_by": None},
        {"criterion": "Email contains error details", "status": "pending", "verified_by": None}
    ]
)

board.move_card(card['card_id'], "orchestration", "orchestrator")
board.move_card(card['card_id'], "development", "orchestrator", "Spec complete")

# 2. DEVELOPER B: Implement with TDD
board.update_test_status(
    card['card_id'],
    {"unit_tests_written": True, "unit_tests_passing": True, "test_coverage_percent": 85}
)
board.move_card(card['card_id'], "validation", "developer-b", "Implementation complete")

# 3. VALIDATOR: Check compliance
board.move_card(card['card_id'], "arbitration", "validator", "Validation passed")

# 4. ARBITRATOR: Select winner
board.update_card(card['card_id'], {"winning_solution": "developer-b", "arbitration_score": 88})
board.move_card(card['card_id'], "integration", "arbitrator", "Developer B selected")

# 5. INTEGRATION: Deploy
board.move_card(card['card_id'], "testing", "integration", "Deployed successfully")

# 6. TEST AGENT: Verify
board.verify_acceptance_criterion(card['card_id'], 0, "test-agent")
board.verify_acceptance_criterion(card['card_id'], 1, "test-agent")
board.move_card(card['card_id'], "done", "test-agent", "All tests passing")

# DONE! Board metrics automatically updated
```

---

## Troubleshooting

**Q: Card not found?**
A: Use `kanban_manager.py show` to see all cards and their IDs

**Q: WIP limit exceeded warning?**
A: Complete existing work before starting new tasks in that column

**Q: Card stuck in Blocked?**
A: Review the `blocked_reason` field, fix the issue, then use `unblock_card()`

**Q: Need to see card history?**
A: Load the board JSON and check the card's `history` array

---

## Integration with Agile Ceremonies

- **Sprint Planning**: Review Backlog, move cards to current sprint
- **Daily Standup**: Agents report card movements automatically
- **Sprint Review**: Demo cards in Done column
- **Retrospective**: Analyze cycle times, blocked items, velocity trends

---

**Last Updated**: October 21, 2025
**Version**: 1.0
