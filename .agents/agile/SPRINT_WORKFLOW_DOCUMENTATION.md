# Artemis Sprint-Based Agile Workflow

## Overview

Artemis now implements a complete Sprint-based Agile workflow with:
- **Planning Poker** for feature estimation
- **Sprint Planning** stage for organizing work
- **Project Review** stage with architecture feedback loops
- **Retrospective Agent** for continuous learning
- **Dynamic Heartbeat Adjustment** in Supervisor for adaptive monitoring

This document describes the complete workflow, components, and integration points.

---

## Architecture Overview

### New Workflow Stages

```
┌─────────────────────────────────────────────────────────────────┐
│                     ARTEMIS SPRINT WORKFLOW                      │
└─────────────────────────────────────────────────────────────────┘

1. Sprint Planning Stage
   ├─ Extract features from backlog
   ├─ Run Planning Poker (multi-agent estimation)
   ├─ Prioritize by business value & effort
   ├─ Create sprint backlogs
   └─ Update Kanban board

2. Architecture Stage (existing, enhanced)
   ├─ Design system architecture
   └─ Send to Project Review

3. Project Review Stage ★ NEW
   ├─ Review architecture quality
   ├─ Validate sprint feasibility
   ├─ Check for technical debt
   ├─ APPROVE → Continue to Development
   └─ REJECT → Send feedback to Architecture (loop)

4. Development Stage (existing)
   ├─ Multi-agent implementation
   └─ Continue through pipeline...

5. Retrospective Agent ★ NEW (after Testing)
   ├─ Analyze sprint metrics
   ├─ Extract learnings
   ├─ Generate action items
   ├─ Store in RAG for learning
   └─ Communicate to Orchestrator
```

### Component Dependencies

```
┌──────────────────────────────────────────────────────────────┐
│                      COMPONENT DIAGRAM                        │
└──────────────────────────────────────────────────────────────┘

KanbanBoard
  ├─ Sprint Management (create, start, complete)
  ├─ Sprint assignment (assign cards to sprints)
  └─ Velocity tracking

SprintPlanningStage
  ├─ Uses: PlanningPoker
  ├─ Uses: LLMClient
  ├─ Uses: KanbanBoard (sprint mgmt)
  ├─ Uses: SupervisedStageMixin (monitoring)
  └─ Outputs: Prioritized sprint backlogs

PlanningPoker
  ├─ Uses: LLMClient (agent voting)
  ├─ Multi-round estimation
  ├─ Consensus detection
  └─ Outputs: FeatureEstimate with confidence

ProjectReviewStage
  ├─ Uses: LLMClient (review analysis)
  ├─ Uses: AgentMessenger (feedback to Architecture)
  ├─ Uses: KanbanBoard (status updates)
  ├─ Uses: SupervisedStageMixin (monitoring)
  ├─ Inputs: Architecture + Sprints
  └─ Outputs: APPROVED | REJECTED (with feedback)

RetrospectiveAgent
  ├─ Uses: LLMClient (qualitative analysis)
  ├─ Uses: RAG (store/retrieve learnings)
  ├─ Uses: AgentMessenger (communicate results)
  ├─ Inputs: Sprint metrics + outcomes
  └─ Outputs: RetrospectiveReport

SupervisorAgent (enhanced)
  ├─ Dynamic heartbeat adjustment
  ├─ Auto-adjusts based on agent behavior
  └─ Adaptive intervals (5-60 seconds)
```

---

## Planning Poker - Multi-Agent Estimation

### Purpose
Estimate feature complexity using Fibonacci sequence (1, 2, 3, 5, 8, 13, 21) with multiple AI agent perspectives.

### Agents Involved
- **Architect**: System design perspective
- **Senior Developer**: Implementation complexity
- **QA Engineer**: Testing requirements
- **DevOps Engineer**: Deployment & infrastructure

### Process Flow

```python
# 1. Initialize Planning Poker
poker = PlanningPoker(
    agents=["architect", "senior_developer", "qa_engineer", "devops_engineer"],
    llm_client=llm_client,
    logger=logger,
    team_velocity=20.0,  # Story points per sprint
    max_rounds=3
)

# 2. Estimate a feature
estimate = poker.estimate_feature(
    feature_title="User Authentication",
    feature_description="Implement JWT-based auth with OAuth2",
    acceptance_criteria=[
        "Users can register with email/password",
        "OAuth2 login via Google/GitHub",
        "JWT tokens with 15min expiry",
        "Refresh token rotation"
    ]
)

# 3. Results
print(f"Estimate: {estimate.final_estimate} story points")
print(f"Confidence: {estimate.confidence:.0%}")
print(f"Risk: {estimate.risk_level}")
print(f"Est. Hours: {estimate.estimated_hours:.1f}h")
```

### Voting Rounds

**Round 1**: Initial independent votes
```
Architect: 5 points
Senior Developer: 8 points
QA Engineer: 5 points
DevOps Engineer: 3 points
```

**Analysis**: Spread detected (3 to 8), discussion generated:
```
Why the spread?
- DevOps (lowest): "OAuth2 is well-supported, mostly config"
- Senior Dev (highest): "JWT implementation has edge cases, security concerns"

Key concerns: Token refresh complexity, OAuth provider integration
```

**Round 2**: Agents reconsider based on discussion
```
Architect: 5 points
Senior Developer: 5 points
QA Engineer: 5 points
DevOps Engineer: 5 points
```

**Consensus reached**: 5 story points

### Output Structure

```python
FeatureEstimate(
    feature_title="User Authentication",
    feature_description="...",
    rounds=[
        EstimationRound(round_number=1, consensus_reached=False, ...),
        EstimationRound(round_number=2, consensus_reached=True, final_estimate=5)
    ],
    final_estimate=5,
    confidence=0.85,
    risk_level="low",
    estimated_hours=10.0  # Based on team velocity
)
```

---

## Sprint Planning Stage

### Responsibilities
1. Extract features from product backlog
2. Run Planning Poker to estimate all features
3. Prioritize features using weighted scoring
4. Create sprint backlogs based on team velocity
5. Update Kanban board with sprint assignments

### Priority Scoring Algorithm

```python
Priority Score = (Business Value × 0.6) - (Story Points × 0.2) - (Risk × 0.2)
```

**Factors**:
- **Business Value** (0-10): Higher = more important
- **Story Points** (1-21): Lower = easier to complete
- **Risk** (low=1, medium=5, high=10): Lower = more predictable

**Example**:
```
Feature A: Business Value=9, Story Points=5, Risk=low(1)
Priority = (9 × 0.6) - (5 × 0.2) - (1 × 0.2)
         = 5.4 - 1.0 - 0.2
         = 4.2

Feature B: Business Value=7, Story Points=13, Risk=high(10)
Priority = (7 × 0.6) - (13 × 0.2) - (10 × 0.2)
         = 4.2 - 2.6 - 2.0
         = -0.4

→ Feature A is prioritized over Feature B
```

### Sprint Creation

**Team Velocity**: 20 story points per sprint (configurable)

**Packing Algorithm**:
1. Sort features by priority score (descending)
2. Add features to current sprint until velocity limit reached
3. When full, start new sprint
4. Continue until all features assigned

**Example**:
```
Team Velocity: 20 points/sprint

Prioritized Features:
1. User Auth (5 pts, priority=4.2)
2. Dashboard (8 pts, priority=3.5)
3. Notifications (3 pts, priority=3.2)
4. Search (8 pts, priority=2.8)
5. Analytics (13 pts, priority=2.1)

Sprint 1: [User Auth (5), Dashboard (8), Notifications (3)] = 16/20 pts (80% capacity)
Sprint 2: [Search (8), Analytics (13)] = 21/20 pts (105% capacity - overcommitted!)

→ Adjust: Analytics moves to Sprint 3
Sprint 2: [Search (8)] = 8/20 pts (40% capacity)
Sprint 3: [Analytics (13)] = 13/20 pts (65% capacity)
```

### Kanban Board Integration

```python
# Sprint Planning creates sprints on Kanban
board.create_sprint(
    sprint_number=1,
    start_date="2025-10-23",
    end_date="2025-11-06",
    committed_story_points=16,
    features=[...]
)

# Assign cards to sprints
board.assign_card_to_sprint("card-123", sprint_number=1)

# Start sprint
board.start_sprint(sprint_number=1)
```

---

## Project Review Stage

### Purpose
Quality gate between planning and implementation. Reviews architecture and sprint plans, providing feedback for iteration.

### Review Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Architecture Quality | 30% | Design patterns, maintainability, security |
| Sprint Feasibility | 25% | Capacity utilization, realistic timelines |
| Technical Debt | 20% | Anti-patterns, code smells, missing tests |
| Scalability | 15% | Performance, growth handling |
| Maintainability | 10% | Code organization, documentation |

### Review Process

```
┌──────────────────────────────────────────────────────────┐
│               PROJECT REVIEW WORKFLOW                     │
└──────────────────────────────────────────────────────────┘

1. Extract Architecture + Sprints from context

2. Review Architecture (LLM-powered)
   ├─ Design patterns (score 1-10)
   ├─ Scalability (score 1-10)
   ├─ Security (score 1-10)
   ├─ Maintainability (score 1-10)
   └─ Performance (score 1-10)

3. Review Sprint Feasibility (rule-based + heuristics)
   ├─ Check capacity utilization (warn if >95% or <70%)
   ├─ Check Sprint 1 ambition (warn if >25 points)
   ├─ Validate dependencies
   └─ Assess risk distribution

4. Check Quality Issues (pattern matching)
   ├─ Hardcoded configuration
   ├─ Missing error handling
   ├─ No logging/monitoring
   ├─ Missing tests
   └─ Security vulnerabilities

5. Calculate Overall Score (weighted)
   Score = Σ(criterion_score × weight)

6. Make Decision
   ├─ Score ≥ 8.0: APPROVE
   ├─ Score ≥ 6.0 AND no critical issues: APPROVE
   └─ Otherwise: REJECT

7. Handle Decision
   ├─ APPROVED → Proceed to Development
   └─ REJECTED → Send feedback to Architecture
```

### Feedback Loop to Architecture

When **REJECTED**, the Project Review stage sends detailed feedback:

```python
feedback = {
    "architecture_issues": [
        "Hardcoded database credentials detected",
        "No caching strategy for API calls"
    ],
    "sprint_issues": [
        "Sprint 1 is overcommitted (105% capacity)"
    ],
    "quality_issues": [
        "No logging/monitoring strategy mentioned",
        "Missing error handling for external API calls"
    ],
    "actionable_steps": [
        "Move database config to environment variables",
        "Implement Redis caching layer",
        "Reduce Sprint 1 scope to 80-90% capacity",
        "Add structured logging with correlation IDs"
    ],
    "summary": "Address: 2 architecture issue(s), 1 sprint planning issue(s), 2 quality issue(s)"
}

# Send to Architecture agent via messenger
messenger.send_data_update(
    to_agent="architecture-agent",
    card_id=card_id,
    update_type="review_feedback_for_revision",
    data=feedback,
    priority="high"
)
```

### Iteration Limit

**Max Iterations**: 3 (configurable)

If architecture is rejected 3 times, **forced approval** occurs to prevent infinite loops.

---

## Retrospective Agent

### Purpose
Analyze completed sprints, extract learnings, and drive continuous improvement.

### Sprint Metrics Tracked

```python
SprintMetrics(
    sprint_number=1,
    planned_story_points=20,
    completed_story_points=16,
    velocity=80.0,  # 16/20 = 80%
    bugs_found=5,
    bugs_fixed=4,
    tests_passing=95.0,  # %
    code_review_iterations=2,
    average_task_duration_hours=8.5,
    blockers_encountered=1
)
```

### Retrospective Structure

Following Scrum framework:
1. **What Went Well** (successes to maintain)
2. **What Didn't Go Well** (problems to address)
3. **Action Items** (concrete improvements)
4. **Key Learnings** (patterns and insights)
5. **Recommendations** (next sprint guidance)

### Analysis Rules

**What Went Well** (automatic detection):
```python
if velocity >= 90%:
    "Excellent velocity: {velocity}% of planned work completed"

if tests_passing >= 95%:
    "High test quality: {tests_passing}% tests passing"

if blockers_encountered == 0:
    "No blockers encountered during sprint"
```

**What Didn't Go Well** (automatic detection):
```python
if velocity < 70%:
    "Low velocity: Only {velocity}% of planned work completed"
    → Action: "Review estimation accuracy and capacity planning"

if bugs_found > bugs_fixed:
    "Bug backlog increased: {bugs_found} found, {bugs_fixed} fixed"
    → Action: "Allocate more time for bug fixes in next sprint"

if code_review_iterations > 3:
    "High code review iterations: {iterations} average"
    → Action: "Improve code quality standards and pre-review checklists"

if blockers_encountered > 2:
    "Multiple blockers: {blockers} encountered"
    → Action: "Identify and address dependency issues in planning"
```

### Sprint Health Assessment

```python
health_score = 0

# Velocity (40% weight)
if velocity >= 90: health_score += 40
elif velocity >= 70: health_score += 25
else: health_score += 10

# Test quality (30% weight)
if tests_passing >= 95: health_score += 30
elif tests_passing >= 80: health_score += 20
else: health_score += 5

# Blockers (20% weight)
if blockers_encountered == 0: health_score += 20
elif blockers_encountered <= 2: health_score += 10
else: health_score += 0

# Bug management (10% weight)
if bugs_fixed >= bugs_found: health_score += 10
elif bugs_fixed >= bugs_found * 0.75: health_score += 5

# Determine health status
if health_score >= 80: "healthy"
elif health_score >= 50: "needs_attention"
else: "critical"
```

### Learning and Storage

All retrospectives are stored in RAG for:
- **Pattern Recognition**: Identify recurring issues across sprints
- **Velocity Trends**: Track team improvement over time
- **Best Practices**: Capture successful patterns
- **Failure Modes**: Document common pitfalls

**RAG Query Example**:
```python
# Future sprints can learn from past
learnings = rag.query("What issues did we have with authentication sprints?")

→ Returns: [
    "Sprint 3: OAuth2 integration took longer than estimated (+5 points)",
    "Sprint 7: Token refresh had edge cases, add 20% buffer",
    "Sprint 12: Security testing caught 3 critical issues, allocate extra QA time"
]
```

---

## Dynamic Heartbeat Adjustment

### Purpose
Supervisor can now dynamically adjust heartbeat monitoring frequency based on agent behavior and workload.

### Adaptive Intervals

| Agent Type | Default | Rationale |
|------------|---------|-----------|
| Standard Stages | 15s | Balanced monitoring |
| CodeReviewStage | 20s | LLM-heavy operations are slow |
| UIUXStage | 25s | Evaluation-heavy, file I/O intensive |
| Sprint Planning | 20s | Planning Poker uses LLMs |
| Project Review | 20s | Architecture analysis uses LLMs |

### Manual Adjustment

```python
# Supervisor detects agent is doing expensive LLM calls
supervisor.adjust_heartbeat_interval(
    agent_name="CodeReviewStage",
    new_interval=30,  # Reduce monitoring frequency
    reason="LLM operations detected - reducing monitoring overhead"
)

# Supervisor detects agent may be stalling
supervisor.adjust_heartbeat_interval(
    agent_name="DevelopmentStage",
    new_interval=10,  # Increase monitoring frequency
    reason="Potential stall detected - increasing monitoring"
)
```

### Auto-Adjustment

```python
# Supervisor automatically adjusts based on metadata
supervisor.auto_adjust_heartbeat("CodeReviewStage")

# Heuristics:
# - If agent metadata has "uses_llm": True → increase interval to 20s
# - If agent metadata has "evaluation_heavy": True → increase to 25s
# - If failure rate > 30% → decrease interval to 10s (catch failures faster)
```

### Bounds
- **Minimum**: 5 seconds (avoid excessive overhead)
- **Maximum**: 60 seconds (avoid missing critical failures)

---

## Complete Workflow Example

### Scenario: Build User Management System

```python
# 1. SPRINT PLANNING STAGE
# -------------------------
features = [
    {
        "title": "User Authentication",
        "description": "JWT-based auth with OAuth2",
        "acceptance_criteria": [...],
        "business_value": 9
    },
    {
        "title": "User Profiles",
        "description": "CRUD operations for user data",
        "acceptance_criteria": [...],
        "business_value": 7
    },
    {
        "title": "Role-Based Access Control",
        "description": "Admin/User/Guest permissions",
        "acceptance_criteria": [...],
        "business_value": 8
    }
]

# Run Planning Poker
poker = PlanningPoker(...)
estimates = estimate_features_batch(features, poker, logger)

# Results:
# - User Authentication: 5 points (confidence: 85%, risk: low)
# - User Profiles: 3 points (confidence: 90%, risk: low)
# - RBAC: 8 points (confidence: 70%, risk: medium)

# Prioritize & create sprints
sprints = sprint_planning_stage.execute(card, context)

# Sprint 1: [User Auth (5), User Profiles (3)] = 8/20 points
# Sprint 2: [RBAC (8)] = 8/20 points


# 2. ARCHITECTURE STAGE
# ----------------------
architecture = architecture_stage.execute(card, context)

# Designs:
# - PostgreSQL for user data
# - Redis for session storage
# - JWT tokens with 15min expiry
# - OAuth2 via Passport.js


# 3. PROJECT REVIEW STAGE (Iteration 1)
# ----------------------------------------
review = project_review_stage.execute(card, context)

# Result: REJECTED (score: 6.5/10)
# Issues:
# - "No database migration strategy mentioned"
# - "Missing rate limiting for auth endpoints"
# - "No session invalidation on logout"

# Feedback sent to Architecture agent


# 4. ARCHITECTURE STAGE (Revision)
# ----------------------------------
# Architecture agent receives feedback, adjusts design:
# - Add Flyway for database migrations
# - Add express-rate-limit middleware
# - Implement session blacklist in Redis


# 5. PROJECT REVIEW STAGE (Iteration 2)
# ----------------------------------------
review = project_review_stage.execute(card, context)

# Result: APPROVED (score: 8.2/10)
# → Proceed to Development


# 6. DEVELOPMENT STAGE
# ---------------------
# Multi-agent development proceeds...


# 7. TESTING STAGE
# -----------------
# Sprint 1 completes, tests run...


# 8. RETROSPECTIVE AGENT
# ------------------------
retrospective = retrospective_agent.conduct_retrospective(
    sprint_number=1,
    sprint_data={
        'completed_story_points': 7,  # Only completed User Auth (5) + partial Profiles (2)
        'bugs_found': 2,
        'bugs_fixed': 2,
        'test_pass_rate': 92.0,
        'blockers_encountered': 1  # OAuth2 provider configuration issue
    },
    card_id=card_id
)

# Results:
# What Went Well:
# - "Good test coverage: 92% passing"
# - "All bugs fixed during sprint"

# What Didn't Go Well:
# - "Velocity: Only 35% (7/20 points) - severely underperformed"
# - "OAuth2 blocker delayed User Profiles completion"

# Action Items:
# - "Review estimation for OAuth2 integrations - add 50% buffer"
# - "Set up OAuth2 sandbox environments before sprint starts"
# - "Reduce Sprint 2 scope to account for lower velocity"

# Recommendations:
# - "Consider reducing sprint scope or investigating capacity constraints"
# - "Address blocker resolution process - 2 days lost to OAuth config"

# Health: "critical" (velocity too low)
```

---

## Integration with Orchestrator

The orchestrator needs to be updated to handle the new workflow. Here's the recommended flow:

```python
# artemis_orchestrator.py (updated)

def run_sprint_workflow(card):
    context = {}

    # Step 1: Sprint Planning
    logger.log("Starting Sprint Planning Stage...")
    sprint_result = sprint_planning_stage.execute(card, context)
    context['sprints'] = sprint_result['sprints']
    context['estimates'] = sprint_result['estimates']

    # Step 2: Architecture (existing)
    logger.log("Starting Architecture Stage...")
    arch_result = architecture_stage.execute(card, context)
    context['architecture'] = arch_result['architecture']

    # Step 3: Project Review (with iteration loop)
    max_review_iterations = 3
    for iteration in range(max_review_iterations):
        logger.log(f"Starting Project Review (iteration {iteration+1})...")
        review_result = project_review_stage.execute(card, context)

        if review_result['status'] == 'APPROVED':
            logger.log("Project approved! Proceeding to development...")
            break
        else:
            logger.log("Project rejected, sending feedback to Architecture...")
            # Architecture stage will re-run automatically via messenger callback
            # Wait for architecture revision...
            arch_result = architecture_stage.execute(card, context)
            context['architecture'] = arch_result['architecture']

    # Step 4-7: Existing pipeline (Development → Testing → Deployment)
    development_result = development_stage.execute(card, context)
    # ... continue through pipeline

    # Step 8: Retrospective (after Testing)
    logger.log("Conducting Sprint Retrospective...")
    sprint_data = {
        'sprint_number': 1,
        'completed_story_points': calculate_completed_points(card),
        'bugs_found': testing_result.get('bugs_found', 0),
        'bugs_fixed': testing_result.get('bugs_fixed', 0),
        # ... collect metrics from various stages
    }
    retrospective = retrospective_agent.conduct_retrospective(
        sprint_number=1,
        sprint_data=sprint_data,
        card_id=card['card_id']
    )

    # Step 9: Apply learnings to next sprint
    if retrospective.overall_health == "critical":
        logger.log("Sprint health critical - reducing next sprint scope...")
        adjust_next_sprint_capacity(retrospective.metrics.velocity)
```

---

## Configuration

### Hydra Configuration

```yaml
# conf/config.yaml

sprint_planning:
  enabled: true
  team_velocity: 20  # Story points per sprint
  sprint_duration_days: 14  # 2-week sprints
  heartbeat_interval: 20
  planning_poker:
    agents:
      - architect
      - senior_developer
      - qa_engineer
      - devops_engineer
    max_rounds: 3
    fibonacci_scale: [1, 2, 3, 5, 8, 13, 21, 100]

project_review:
  enabled: true
  max_review_iterations: 3
  heartbeat_interval: 20
  review_weights:
    architecture_quality: 0.30
    sprint_feasibility: 0.25
    technical_debt: 0.20
    scalability: 0.15
    maintainability: 0.10
  approval_threshold: 8.0
  approval_threshold_no_critical: 6.0

retrospective:
  enabled: true
  historical_sprints_to_analyze: 3
  health_thresholds:
    healthy: 80
    needs_attention: 50

supervisor:
  dynamic_heartbeat: true
  heartbeat_bounds:
    min: 5
    max: 60
  auto_adjust: true
```

---

## Key Benefits

### 1. **Realistic Estimation**
- Multi-agent Planning Poker provides diverse perspectives
- Confidence scores help identify risky estimates
- Historical velocity data improves future planning

### 2. **Quality Gates**
- Project Review prevents bad architecture from reaching development
- Feedback loops allow iterative improvement
- Technical debt is caught early

### 3. **Continuous Learning**
- Retrospectives capture sprint outcomes
- RAG stores learnings for future reference
- Team velocity improves over time

### 4. **Adaptive Monitoring**
- Dynamic heartbeat reduces supervisor overhead
- LLM-heavy stages get longer intervals
- Failing stages get more frequent checks

### 5. **Agile Compliance**
- Follows Scrum framework (Planning, Review, Retrospective)
- Sprint-based work organization
- Velocity tracking and capacity planning

---

## Testing the Workflow

### Unit Tests

```python
# test_planning_poker.py
def test_consensus_detection():
    votes = [
        EstimationVote("architect", 5, "...", 0.8, []),
        EstimationVote("developer", 5, "...", 0.9, []),
        EstimationVote("qa", 3, "...", 0.7, [])  # Within 1 Fibonacci step
    ]
    consensus, value = poker._check_consensus(votes)
    assert consensus == True
    assert value == 5

# test_project_review.py
def test_approval_with_good_score():
    arch_review = {"overall_recommendation": "APPROVE"}
    sprint_review = {"score": 9}
    quality_review = {"score": 9, "critical_issues": []}
    score, decision = review_stage._calculate_review_score(
        arch_review, sprint_review, quality_review
    )
    assert decision == "APPROVED"

# test_retrospective.py
def test_health_assessment():
    metrics = SprintMetrics(
        velocity=95.0,
        tests_passing=98.0,
        blockers_encountered=0,
        bugs_fixed=5,
        bugs_found=4
    )
    health = retrospective._assess_sprint_health(metrics)
    assert health == "healthy"
```

### Integration Test

```python
def test_full_sprint_workflow():
    # Create sprints
    result = sprint_planning_stage.execute(card, {})
    assert result['status'] == 'PASS'
    assert len(result['sprints']) > 0

    # Project review
    context = {'architecture': {...}, 'sprints': result['sprints']}
    review = project_review_stage.execute(card, context)
    assert review['status'] in ['APPROVED', 'REJECTED']

    # If rejected, architecture should receive feedback
    if review['status'] == 'REJECTED':
        assert 'feedback' in review
        assert len(review['feedback']['actionable_steps']) > 0
```

---

## Troubleshooting

### Issue: Planning Poker never reaches consensus

**Symptom**: All 3 rounds complete without consensus

**Cause**: Agents have widely different perspectives

**Solution**:
```python
# planning_poker.py uses forced consensus after max_rounds
# Weighted average by confidence:
final_estimate = sum(vote.points * vote.confidence for vote in votes) / sum(vote.confidence)
```

### Issue: Project Review always rejects

**Symptom**: Reaches max_review_iterations (3) and forces approval

**Cause**: Review criteria too strict

**Solution**:
```yaml
# Adjust thresholds in config.yaml
project_review:
  approval_threshold: 7.0  # Lower from 8.0
  approval_threshold_no_critical: 5.5  # Lower from 6.0
```

### Issue: Retrospective shows "critical" health repeatedly

**Symptom**: Team velocity consistently <70%

**Cause**: Team capacity or estimation issues

**Solution**:
```python
# Reduce team_velocity in sprint_planning
sprint_planning:
  team_velocity: 15  # Reduce from 20 to account for lower capacity
```

### Issue: Dynamic heartbeat not adjusting

**Symptom**: All agents stay at 15s interval

**Cause**: Metadata not set on agent registration

**Solution**:
```python
# In stage __init__, pass metadata to supervisor
SupervisedStageMixin.__init__(
    self,
    supervisor=supervisor,
    stage_name="CodeReviewStage",
    heartbeat_interval=20,
    metadata={"uses_llm": True}  # ← Add this
)
```

---

## Summary

Artemis now implements a complete, production-ready Sprint-based Agile workflow:

✅ **Planning Poker** - Multi-agent estimation with confidence scoring
✅ **Sprint Planning** - Automated sprint creation based on velocity
✅ **Project Review** - Quality gate with architecture feedback loops
✅ **Retrospectives** - Automated learning from sprint outcomes
✅ **Dynamic Heartbeat** - Adaptive supervisor monitoring
✅ **Kanban Integration** - Full sprint lifecycle management
✅ **RAG Learning** - Historical pattern recognition
✅ **AgentMessenger** - Real-time feedback communication

This system enables Artemis to self-organize, self-estimate, and self-improve across multiple sprints, learning from each iteration to become more accurate and efficient over time.
