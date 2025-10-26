# UI/UX Stage Documentation

## Overview

The UI/UX Stage is a dedicated pipeline stage in the Artemis system that evaluates developer implementations for:
- **WCAG 2.1 AA Accessibility Compliance**
- **GDPR Privacy & Data Protection Compliance**
- **Overall User Experience Quality**

This stage was separated from the TestingStage to provide focused, comprehensive evaluation of user-facing quality attributes with proper feedback loops for developer iteration.

## Architecture

### Components

#### 1. UIUXStage (uiux_stage.py)
Main stage coordinator that:
- Inherits from `PipelineStage` and `SupervisedStageMixin`
- Orchestrates evaluations for all developer implementations
- Manages feedback loops back to developers
- Uses **adaptive 25-second heartbeat interval** (longest in pipeline due to evaluation complexity)
- Integrates with supervisor for health monitoring and LLM cost tracking

**Key Responsibilities:**
- Execute evaluations for each developer's implementation
- Calculate UX scores based on accessibility and privacy compliance
- Send actionable feedback to developers for iteration
- Store results in RAG for learning
- Broadcast events via Observer pattern

#### 2. WCAGEvaluator (wcag_evaluator.py)
Static analysis tool for WCAG 2.1 Level AA accessibility compliance.

**Evaluates:**
- HTML, JSX, TSX, and Vue files
- 10 WCAG rules across Level A and AA criteria

**Checks Performed:**
1. **WCAG 1.1.1 (Level A)** - Image alt text
2. **WCAG 3.3.2 (Level A)** - Form labels
3. **WCAG 4.1.2 (Level A)** - Button accessible text
4. **WCAG 1.3.1 (Level A)** - Heading hierarchy
5. **WCAG 1.4.3 (Level AA)** - Color contrast
6. **WCAG 2.1.1 (Level A)** - Keyboard navigation
7. **WCAG 4.1.2 (Level A)** - ARIA labels
8. **WCAG 3.1.1 (Level A)** - Language attribute
9. **WCAG 2.4.7 (Level AA)** - Focus indicators
10. **WCAG 2.4.4 (Level A)** - Link text

**Output Structure:**
```python
{
    "wcag_aa_compliance": bool,  # Overall compliance status
    "accessibility_issues": int,  # Total issue count
    "critical_count": int,
    "serious_count": int,
    "moderate_count": int,
    "minor_count": int,
    "accessibility_details": {
        "contrast_ratio": "PASS" | "FAIL",
        "keyboard_navigation": "PASS" | "FAIL",
        "screen_reader_support": "PASS" | "FAIL",
        "aria_labels": "PASS" | "FAIL",
        "focus_indicators": "PASS" | "FAIL"
    },
    "issues": [
        {
            "rule": "1.4.3",
            "severity": "serious",
            "element": "Color styles",
            "description": "Gray on white may have low contrast",
            "suggestion": "Ensure 4.5:1 contrast ratio for normal text",
            "wcag_criterion": "Contrast (Minimum) (Level AA)"
        }
    ]
}
```

#### 3. GDPREvaluator (gdpr_evaluator.py)
Static analysis tool for GDPR compliance.

**Evaluates:**
- JavaScript, TypeScript, Python, and HTML files
- 8 GDPR articles across privacy and data protection requirements

**Checks Performed:**
1. **Article 7** - Cookie consent implementation
2. **Article 13** - Privacy policy and data collection notices
3. **Article 5(1)(c)** - Data minimization (no excessive collection)
4. **Article 17** - Right to erasure (account deletion)
5. **Article 20** - Right to data portability (data export)
6. **Article 25** - Privacy by design (no hardcoded secrets)
7. **Article 7** - Third-party tracking consent
8. **Article 32** - Security of processing (encrypted storage)

**Output Structure:**
```python
{
    "gdpr_compliant": bool,  # Overall compliance status
    "gdpr_issues": int,  # Total issue count
    "critical_count": int,
    "high_count": int,
    "medium_count": int,
    "low_count": int,
    "gdpr_compliance": {
        "consent_management": "PASS" | "FAIL",
        "data_minimization": "PASS" | "FAIL",
        "right_to_erasure": "PASS" | "FAIL",
        "privacy_by_design": "PASS" | "FAIL",
        "cookie_consent": "PASS" | "FAIL",
        "data_export": "PASS" | "FAIL"
    },
    "issues": [
        {
            "article": "Article 7",
            "severity": "critical",
            "category": "consent",
            "description": "Cookie usage detected without consent mechanism",
            "suggestion": "Implement cookie consent banner before storing cookies",
            "gdpr_principle": "Lawful basis for processing"
        }
    ]
}
```

## Pipeline Integration

### Stage Position
The UI/UX stage executes **after CodeReviewStage** and **before TestingStage** in the pipeline:

```
Planning → UI Design → Architecture → Development → CodeReview → UI/UX → Testing → Deployment
```

### Feedback Loop

The UI/UX stage implements a complete feedback mechanism to enable developer iteration:

1. **Evaluation Phase**: Run WCAG and GDPR evaluators on each developer's implementation
2. **Scoring Phase**: Calculate UX score based on issue severity
3. **Feedback Phase**: Send detailed, actionable feedback to developers
4. **Iteration Phase**: Developers fix issues and resubmit
5. **Re-evaluation Phase**: Process repeats until compliance achieved

**Feedback Message Structure:**
```python
{
    "evaluation_status": "PASS" | "NEEDS_IMPROVEMENT" | "FAIL",
    "ux_score": 85,
    "requires_iteration": True,
    "accessibility_feedback": {
        "total_issues": 12,
        "wcag_aa_compliant": False,
        "issues": [...]
    },
    "gdpr_feedback": {
        "total_issues": 3,
        "issues": [...]
    },
    "action_required": "Fix 2 critical GDPR issues, 5 serious accessibility issues"
}
```

**Delivery Mechanism:**
- Sent via `AgentMessenger.send_data_update()` to specific developer agent
- Stored in shared state for retrieval
- High priority for fast iteration
- Includes both structured data and human-readable action summary

## Scoring Algorithm

### UX Score Calculation
The UI/UX stage calculates a composite UX score (0-100) based on:

```python
ux_score = 100
ux_score -= wcag_critical * 20
ux_score -= wcag_serious * 10
ux_score -= wcag_moderate * 5
ux_score -= wcag_minor * 2
ux_score -= gdpr_critical * 20
ux_score -= gdpr_high * 10
ux_score -= gdpr_medium * 5
ux_score -= gdpr_low * 2
ux_score = max(0, ux_score)  # Floor at 0
```

### Evaluation Status Determination
```python
if ux_score >= 90:
    status = "PASS"
elif ux_score >= 70:
    status = "NEEDS_IMPROVEMENT"
else:
    status = "FAIL"
```

**Additional Failure Conditions:**
- Any critical GDPR issues → automatic FAIL
- Any critical accessibility issues → automatic FAIL
- More than 10 serious accessibility issues → automatic FAIL

## Supervisor Integration

### Adaptive Heartbeat
The UI/UX stage uses a **25-second heartbeat interval**, the longest in the pipeline:
- Standard stages: 15 seconds
- CodeReviewStage (LLM-heavy): 20 seconds
- **UIUXStage (evaluation-heavy): 25 seconds**

This adaptive interval accounts for:
- File system I/O for reading multiple files
- Regex pattern matching across large codebases
- Multiple evaluator instantiations
- Feedback message construction

### Supervised Execution
The stage uses the `supervised_execution()` context manager:

```python
def execute(self, card: Dict, context: Dict) -> Dict:
    metadata = {
        "task_id": card.get('card_id'),
        "stage": "uiux"
    }
    with self.supervised_execution(metadata):
        return self._do_uiux_evaluation(card, context)
```

**Benefits:**
- Automatic supervisor registration on init
- Heartbeat thread started automatically
- Health monitoring without boilerplate
- Automatic cleanup on completion
- LLM cost tracking (if evaluators use LLMs in future)
- Critical issue alerts to supervisor

### Progress Tracking
The stage reports progress at key milestones:

```python
self.update_progress({"step": "starting", "progress_percent": 5})
self.update_progress({"step": "evaluating_wcag", "progress_percent": 30})
self.update_progress({"step": "evaluating_gdpr", "progress_percent": 50})
self.update_progress({"step": "calculating_score", "progress_percent": 70})
self.update_progress({"step": "sending_feedback", "progress_percent": 85})
self.update_progress({"step": "complete", "progress_percent": 100})
```

## Event Broadcasting

The UI/UX stage broadcasts events via the Observer pattern:

### Event Types
1. **UIUX_EVALUATION_STARTED**
   - Fired when evaluation begins for a developer
   - Data: `{"developer_name": str, "implementation_dir": str}`

2. **UIUX_EVALUATION_COMPLETED**
   - Fired when evaluation passes
   - Data: `{"developer_name": str, "ux_score": int, "status": "PASS"}`

3. **UIUX_EVALUATION_FAILED**
   - Fired when evaluation fails
   - Error: Exception with failure details
   - Data: `{"ux_score": int, "critical_issues": int}`

### Observer Integration
```python
if self.observable:
    event = PipelineEvent(
        event_type=EventType.UIUX_EVALUATION_STARTED,
        card_id=card_id,
        developer_name=developer_name,
        data={"implementation_dir": implementation_dir}
    )
    self.observable.notify(event)
```

## RAG Integration

The UI/UX stage stores evaluation results in RAG for learning:

### Stored Artifacts
```python
self.rag.store_artifact(
    artifact_type="uiux_evaluation",
    card_id=card_id,
    task_title=task_title,
    content=f"""UI/UX Evaluation for {developer_name} - {task_title}

Evaluation Status: {status}
UX Score: {ux_score}/100

Accessibility: {accessibility_issues} issues
GDPR Compliance: {gdpr_issues} issues

This evaluation can inform future implementations.""",
    metadata={
        "developer": developer_name,
        "ux_score": ux_score,
        "accessibility_issues": accessibility_issues,
        "gdpr_issues": gdpr_issues,
        "evaluation_status": status
    }
)
```

### Learning Benefits
- Future developers can learn from past accessibility mistakes
- GDPR patterns can be identified and avoided
- Common anti-patterns can be flagged proactively
- Best practices can be recommended based on successful implementations

## Production Enhancements

The current implementation uses static analysis (regex pattern matching). For production use, consider integrating:

### WCAG/Accessibility
- **axe-core** (Deque Systems) - Automated accessibility testing
- **pa11y** - Accessibility testing tool
- **Lighthouse** - Accessibility audit
- **Playwright/Puppeteer** - Responsive design testing
- **NVDA/JAWS** - Screen reader testing

### GDPR/Privacy
- **OneTrust** - Privacy management platform
- **TrustArc** - Privacy compliance
- **Osano** - Cookie consent management
- **CookieBot** - Cookie scanning and consent
- **Privacy Badger** - Tracking protection analysis

### Performance
- **Lighthouse** - Performance metrics
- **WebPageTest** - Real-world performance
- **Chrome DevTools** - Performance profiling

### Design System Validation
- **Storybook** - Component testing
- **Chromatic** - Visual regression testing
- **Percy** - Visual testing

## Usage Example

### Standalone Evaluation
```python
from uiux_stage import UIUXStage
from wcag_evaluator import WCAGEvaluator
from gdpr_evaluator import GDPREvaluator

# Standalone WCAG evaluation
wcag = WCAGEvaluator()
results = wcag.evaluate_directory("/path/to/implementation")
print(f"Accessibility Issues: {results['accessibility_issues']}")

# Standalone GDPR evaluation
gdpr = GDPREvaluator()
results = gdpr.evaluate_directory("/path/to/implementation")
print(f"GDPR Issues: {results['gdpr_issues']}")
```

### Pipeline Integration
```python
# In artemis_orchestrator.py
from uiux_stage import UIUXStage

# Initialize stage with supervisor
uiux_stage = UIUXStage(
    board=board,
    messenger=messenger,
    rag=rag,
    logger=logger,
    observable=observable,
    supervisor=supervisor  # Automatic health monitoring
)

# Execute in pipeline
result = uiux_stage.execute(card, context)

# Check results
if result['status'] == 'PASS':
    print(f"All developers passed UI/UX evaluation")
else:
    print(f"Some developers need to iterate on UI/UX")
```

## Anti-Patterns Checked

The implementation avoids these anti-patterns:

### Code Smells Avoided
- **God Object**: Each evaluator has single responsibility (WCAG vs GDPR)
- **Duplicate Code**: Shared evaluation logic extracted to base methods
- **Magic Numbers**: Scoring thresholds extracted to constants
- **Long Method**: Evaluation logic split into focused check methods

### Design Patterns Used
- **Template Method**: `supervised_execution()` defines skeleton
- **Observer Pattern**: Event broadcasting for stage lifecycle
- **Strategy Pattern**: Different evaluators can be swapped
- **Single Responsibility**: Each class has one reason to change
- **Dataclass Pattern**: Structured issue representation

## Testing

### Unit Tests
```python
# Test WCAG evaluator
def test_wcag_image_alt_text():
    evaluator = WCAGEvaluator()
    content = '<img src="logo.png">'  # Missing alt
    evaluator._check_images_alt_text(content, "test.html")
    assert len(evaluator.issues) == 1
    assert evaluator.issues[0].rule == "1.1.1"

# Test GDPR evaluator
def test_gdpr_cookie_consent():
    evaluator = GDPREvaluator()
    content = 'document.cookie = "user=john";'  # No consent
    evaluator._check_cookie_consent(content, "test.js")
    assert len(evaluator.issues) == 1
    assert evaluator.issues[0].article == "Article 7"
```

### Integration Tests
```python
# Test full stage execution
def test_uiux_stage_execution():
    stage = UIUXStage(board, messenger, rag, logger, supervisor=supervisor)
    card = {"card_id": "test-123", "title": "Test Feature"}
    context = {
        "developers": [
            {"developer": "dev1", "output_dir": "/tmp/dev1"}
        ]
    }
    result = stage.execute(card, context)
    assert result['stage'] == 'uiux'
    assert 'evaluations' in result
```

## Configuration

### Environment Variables
```bash
# Not currently used, but reserved for future enhancements
ARTEMIS_WCAG_LEVEL=AA  # A, AA, or AAA
ARTEMIS_GDPR_STRICT_MODE=true  # Fail on any GDPR issue
ARTEMIS_UX_SCORE_THRESHOLD=80  # Minimum passing score
```

### Hydra Configuration
```yaml
# conf/config.yaml
stages:
  uiux:
    enabled: true
    heartbeat_interval: 25  # Adaptive for evaluation complexity
    wcag_level: "AA"
    gdpr_strict_mode: false
    min_ux_score: 70
    max_critical_issues: 0
    max_serious_issues: 10
```

## Known Limitations

1. **Static Analysis Only**: Current implementation uses regex patterns, not runtime analysis
2. **No Visual Testing**: Cannot detect visual regressions or design inconsistencies
3. **No Performance Testing**: UI performance not measured
4. **Limited Scope**: Only checks frontend code, not backend privacy compliance
5. **False Positives**: Regex patterns may flag valid code incorrectly
6. **No Context Awareness**: Cannot understand semantic meaning of code

## Future Enhancements

1. **Runtime Testing**: Integrate with Playwright for real browser testing
2. **Visual Regression**: Add Chromatic/Percy for visual testing
3. **Performance Metrics**: Add Lighthouse performance auditing
4. **AI-Powered Analysis**: Use LLMs to understand semantic accessibility issues
5. **Design System Validation**: Check against design system tokens
6. **Automated Fixes**: Suggest or apply automated fixes for common issues
7. **Learning from Past**: Use RAG to recommend patterns from successful implementations
8. **Multi-Language Support**: Extend to mobile (Swift, Kotlin) and desktop (Electron)

## Summary

The UI/UX Stage provides comprehensive accessibility and privacy compliance evaluation with:
- ✅ WCAG 2.1 AA accessibility checking (10 rules)
- ✅ GDPR compliance checking (8 articles)
- ✅ Adaptive 25-second heartbeat for complex evaluations
- ✅ Complete feedback loop for developer iteration
- ✅ Supervisor integration for health monitoring
- ✅ Event broadcasting via Observer pattern
- ✅ RAG storage for learning
- ✅ Separation of concerns from TestingStage
- ✅ Single responsibility per evaluator
- ✅ Anti-pattern avoidance and design pattern usage

This stage ensures that all Artemis implementations meet accessibility standards and privacy regulations before deployment.
