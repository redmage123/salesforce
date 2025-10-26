# TDD + BDD Workflow for Artemis

## The Problem with Current Implementation

### Current (INCORRECT) Flow:
```
1. DevelopmentStage → Write implementation code
2. ValidationStage → Run tests AFTER code is written
```

**Issue**: This is NOT Test-Driven Development! Tests are written after implementation, defeating the purpose of TDD.

### Correct TDD Flow (Red-Green-Refactor):
```
1. RED    → Write tests that FAIL (no implementation yet)
2. GREEN  → Write minimal code to make tests PASS
3. REFACTOR → Improve code while keeping tests GREEN
```

## Proposed Solution: Proper TDD + BDD Pipeline

### New Pipeline Flow

```
1. RequirementsParsingStage
2. SprintPlanningStage
3. BDDScenarioGenerationStage     ← Generate Gherkin scenarios (WHAT to build)
4. ProjectAnalysisStage
5. ArchitectureStage
6. ProjectReviewStage
7. DependencyValidationStage

8. [NEW] TDDTestGenerationStage   ← Generate FAILING unit tests (HOW to build)
9. [NEW] BDDTestGenerationStage   ← Generate BDD step definition stubs

10. DevelopmentStage (REFACTORED)  ← RED-GREEN-REFACTOR cycle
    a. Receive failing tests
    b. Run tests → RED (all fail)
    c. Write minimal implementation → GREEN (tests pass)
    d. Refactor code → keep GREEN
    e. Iterate until all tests green

11. ValidationStage                ← Verify all unit tests GREEN
12. BDDScenarioValidationStage    ← Verify all scenarios GREEN
13. UIUXStage
14. CodeReviewStage
15. IntegrationStage
16. TestingStage
```

## Detailed Stages

### Stage 8: TDD Test Generation Stage

**Purpose**: Generate failing unit tests BEFORE implementation

**Input**:
- Requirements
- Architecture design
- BDD scenarios (for understanding expected behavior)

**Output**:
- Unit test files with test functions
- All tests in FAILING state (RED)
- Stored in `/tmp/{developer}/tests/unit/`

**Process**:
1. Analyze requirements and architecture
2. Identify functions/classes to implement
3. Generate comprehensive unit tests using LLM
4. Tests should cover:
   - Happy path
   - Edge cases
   - Error handling
   - Boundary conditions
5. Run tests to verify they FAIL (RED state)
6. Store test files for developers

**Example Output**:
```python
# tests/unit/test_chart_renderer.py
import pytest
from chart_renderer import ChartRenderer  # This doesn't exist yet!

class TestChartRenderer:
    """Unit tests for ChartRenderer - ALL SHOULD FAIL initially"""

    def test_render_bar_chart_with_valid_data(self):
        """RED: This will fail - ChartRenderer not implemented yet"""
        renderer = ChartRenderer()
        data = {"stages": [1, 2, 3], "durations": [10, 20, 15]}

        result = renderer.render_bar_chart(data)

        assert result is not None
        assert "canvas" in result
        assert len(result["data"]) == 3

    def test_render_chart_with_empty_data(self):
        """RED: Should handle empty data gracefully"""
        renderer = ChartRenderer()
        data = {"stages": [], "durations": []}

        result = renderer.render_bar_chart(data)

        assert result is not None
        assert result["data"] == []

    def test_render_chart_raises_error_with_mismatched_data(self):
        """RED: Should raise ValueError for mismatched arrays"""
        renderer = ChartRenderer()
        data = {"stages": [1, 2], "durations": [10, 20, 30]}  # Mismatch!

        with pytest.raises(ValueError, match="Mismatched data"):
            renderer.render_bar_chart(data)

    def test_chart_data_format_matches_chartjs_spec(self):
        """RED: Output should match Chart.js format"""
        renderer = ChartRenderer()
        data = {"stages": ["Stage 1"], "durations": [10]}

        result = renderer.render_bar_chart(data)

        assert "labels" in result
        assert "datasets" in result
        assert isinstance(result["datasets"], list)
```

### Stage 9: BDD Test Generation Stage

**Purpose**: Generate BDD step definition STUBS

**Input**:
- Gherkin .feature files from BDDScenarioGenerationStage

**Output**:
- pytest-bdd test files with step stubs
- Step functions raise `NotImplementedError`
- Stored in `/tmp/{developer}/tests/bdd/`

**Example Output**:
```python
# tests/bdd/test_artemis_demo.py
from pytest_bdd import scenarios, given, when, then, parsers
import pytest

scenarios('../features/artemis_demo.feature')

@pytest.fixture
def browser():
    """TODO: Implement browser fixture"""
    raise NotImplementedError("Browser fixture not implemented yet")

@given(parsers.parse('the Artemis pipeline has completed {count:d} stages'))
def pipeline_completed_stages(count):
    """RED: Step not implemented yet"""
    raise NotImplementedError("TODO: Set up test data for completed stages")

@when('I view the demo page')
def view_demo_page(browser):
    """RED: Step not implemented yet"""
    raise NotImplementedError("TODO: Navigate to demo page")

@then(parsers.parse('I should see a chart showing {count:d} completed stages'))
def verify_chart_stages(browser, count):
    """RED: Step not implemented yet"""
    raise NotImplementedError("TODO: Verify chart has correct number of stages")
```

### Stage 10: DevelopmentStage (REFACTORED for TDD)

**Purpose**: Implement code following RED-GREEN-REFACTOR cycle

**Input**:
- Failing unit tests (TDD)
- BDD step definition stubs
- Requirements, architecture

**Output**:
- Implementation code
- All unit tests PASSING (GREEN)
- BDD step definitions implemented
- Refactored, clean code

**Process** (Red-Green-Refactor Loop):

#### Phase 1: RED - Verify Tests Fail
```python
# Developer receives tests and runs them
$ pytest tests/unit/test_chart_renderer.py

RESULT:
  test_render_bar_chart_with_valid_data ... FAIL (ModuleNotFoundError: No module named 'chart_renderer')
  test_render_chart_with_empty_data ... FAIL
  test_render_chart_raises_error ... FAIL
  test_chart_data_format_matches ... FAIL

Status: ❌ RED - 0/4 tests passing
```

#### Phase 2: GREEN - Minimal Implementation
```python
# chart_renderer.py (MINIMAL implementation to pass tests)
class ChartRenderer:
    def render_bar_chart(self, data):
        stages = data.get("stages", [])
        durations = data.get("durations", [])

        if len(stages) != len(durations):
            raise ValueError("Mismatched data: stages and durations must have same length")

        return {
            "canvas": "chart-canvas",
            "data": list(zip(stages, durations)),
            "labels": stages,
            "datasets": [{"data": durations}]
        }

# Run tests again
$ pytest tests/unit/test_chart_renderer.py

RESULT:
  test_render_bar_chart_with_valid_data ... PASS ✅
  test_render_chart_with_empty_data ... PASS ✅
  test_render_chart_raises_error ... PASS ✅
  test_chart_data_format_matches ... PASS ✅

Status: ✅ GREEN - 4/4 tests passing
```

#### Phase 3: REFACTOR - Improve Code
```python
# chart_renderer.py (REFACTORED - cleaner, better structure)
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ChartData:
    """Value object for chart data"""
    stages: List[str]
    durations: List[int]

    def __post_init__(self):
        if len(self.stages) != len(self.durations):
            raise ValueError("Mismatched data: stages and durations must have same length")

class ChartRenderer:
    """Renders data for Chart.js visualization"""

    def render_bar_chart(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert raw data to Chart.js format

        Args:
            data: Dict with 'stages' and 'durations' keys

        Returns:
            Chart.js compatible data structure
        """
        chart_data = ChartData(
            stages=data.get("stages", []),
            durations=data.get("durations", [])
        )

        return self._format_for_chartjs(chart_data)

    def _format_for_chartjs(self, chart_data: ChartData) -> Dict[str, Any]:
        """Format data according to Chart.js specification"""
        return {
            "canvas": "chart-canvas",
            "data": list(zip(chart_data.stages, chart_data.durations)),
            "labels": chart_data.stages,
            "datasets": [{
                "data": chart_data.durations,
                "label": "Stage Duration (s)"
            }]
        }

# Run tests AGAIN to ensure refactoring didn't break anything
$ pytest tests/unit/test_chart_renderer.py

RESULT:
  test_render_bar_chart_with_valid_data ... PASS ✅
  test_render_chart_with_empty_data ... PASS ✅
  test_render_chart_raises_error ... PASS ✅
  test_chart_data_format_matches ... PASS ✅

Status: ✅ STILL GREEN - 4/4 tests passing (refactoring succeeded!)
```

#### Phase 4: Implement BDD Steps
```python
# tests/bdd/test_artemis_demo.py (NOW IMPLEMENTED)
from pytest_bdd import scenarios, given, when, then, parsers
import pytest
from selenium import webdriver
from chart_renderer import ChartRenderer

scenarios('../features/artemis_demo.feature')

@pytest.fixture
def browser():
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

@pytest.fixture
def chart_renderer():
    return ChartRenderer()

@given(parsers.parse('the Artemis pipeline has completed {count:d} stages'))
def pipeline_completed_stages(count, context):
    context['completed_stages'] = count
    context['stage_data'] = {
        "stages": [f"Stage {i}" for i in range(1, count + 1)],
        "durations": [10 * i for i in range(1, count + 1)]
    }

@when('I view the demo page')
def view_demo_page(browser, chart_renderer, context):
    # Render chart with test data
    chart_data = chart_renderer.render_bar_chart(context['stage_data'])
    browser.get('file:///tmp/artemis_demo.html')

    # Inject chart data
    browser.execute_script(f"renderChart({chart_data})")

@then(parsers.parse('I should see a chart showing {count:d} completed stages'))
def verify_chart_stages(browser, count):
    chart_labels = browser.execute_script('return myChart.data.labels.length')
    assert chart_labels == count, f"Expected {count} stages, got {chart_labels}"
```

### Developer Agent Workflow

The developer agent should:

```python
# Pseudo-code for developer agent

def develop_solution_tdd(requirements, tests, bdd_scenarios):
    """
    Follow TDD Red-Green-Refactor cycle
    """
    iteration = 0
    max_iterations = 10

    while iteration < max_iterations:
        iteration += 1

        # PHASE 1: RED - Run tests, expect failures
        test_results = run_tests("tests/unit/")

        if iteration == 1:
            # First iteration - all tests should fail
            if test_results.all_passing:
                raise TDDViolation("Tests should FAIL before implementation!")

            log(f"✅ RED: {test_results.failed_count} tests failing as expected")

        # PHASE 2: GREEN - Write minimal code to pass tests
        log(f"🔨 Writing implementation for failing tests...")

        # Identify failing tests
        failing_tests = [t for t in test_results.tests if not t.passed]

        # Generate implementation using LLM
        for test in failing_tests:
            implementation = generate_minimal_implementation(
                test=test,
                requirements=requirements
            )
            write_code(implementation)

        # Run tests again
        test_results = run_tests("tests/unit/")

        if test_results.all_passing:
            log(f"✅ GREEN: All {test_results.total_count} tests passing!")

            # PHASE 3: REFACTOR - Improve code quality
            log("🔧 Refactoring code...")
            refactored_code = refactor_code_with_llm(
                current_code=read_implementation(),
                test_coverage=test_results
            )
            write_code(refactored_code)

            # Verify tests still pass after refactoring
            test_results = run_tests("tests/unit/")

            if not test_results.all_passing:
                raise RefactoringError("Tests broke during refactoring! Rolling back...")

            log("✅ Refactoring complete - tests still GREEN")
            break
        else:
            log(f"⚠️  {test_results.failed_count} tests still failing, iterating...")

    # Implement BDD step definitions
    implement_bdd_steps(bdd_scenarios)

    return {
        "implementation": read_implementation(),
        "tdd_cycles": iteration,
        "test_results": test_results,
        "status": "GREEN" if test_results.all_passing else "RED"
    }
```

## Benefits of Proper TDD + BDD

### 1. Design First, Code Second
- Tests define the API/interface before implementation
- Forces thinking about edge cases upfront
- Results in better designed code

### 2. Immediate Feedback Loop
- Know instantly if code meets requirements (tests GREEN)
- Catch bugs during development, not in QA
- Refactoring is safe (tests prevent regressions)

### 3. Living Documentation
- Unit tests document technical behavior
- BDD scenarios document business behavior
- Both stay in sync with code

### 4. Better Code Quality
- TDD leads to modular, testable code
- High test coverage by default (tests written first!)
- Refactoring produces cleaner code

### 5. Confidence in Changes
- Can refactor without fear (tests catch breakage)
- Can add features without breaking existing code
- Can upgrade dependencies safely

## Example: Full TDD + BDD Cycle

### Task: "Calculate pipeline success rate"

#### 1. BDD Scenario (WHAT to build)
```gherkin
Feature: Pipeline Success Rate Calculator
  As a developer
  I want to calculate pipeline success rates
  So that I can track quality metrics

  Scenario: Calculate success rate with all passing stages
    Given a pipeline with 5 stages
    And all 5 stages passed
    When I calculate the success rate
    Then the success rate should be 100%

  Scenario: Calculate success rate with some failures
    Given a pipeline with 10 stages
    And 7 stages passed
    And 3 stages failed
    When I calculate the success rate
    Then the success rate should be 70%
```

#### 2. TDD Unit Tests (HOW to build - RED)
```python
# tests/unit/test_success_rate_calculator.py
import pytest
from pipeline_calculator import SuccessRateCalculator  # Doesn't exist yet!

class TestSuccessRateCalculator:
    def test_calculates_100_percent_for_all_passing(self):
        """RED: Will fail - no implementation"""
        calc = SuccessRateCalculator()
        result = calc.calculate(total=5, passed=5)
        assert result == 100.0

    def test_calculates_70_percent_for_partial_success(self):
        """RED: Will fail"""
        calc = SuccessRateCalculator()
        result = calc.calculate(total=10, passed=7)
        assert result == 70.0

    def test_raises_error_for_invalid_input(self):
        """RED: Will fail"""
        calc = SuccessRateCalculator()
        with pytest.raises(ValueError):
            calc.calculate(total=5, passed=10)  # More passed than total!
```

Run tests: `pytest` → ❌ **ALL FAIL** (RED)

#### 3. Minimal Implementation (GREEN)
```python
# pipeline_calculator.py
class SuccessRateCalculator:
    def calculate(self, total, passed):
        if passed > total:
            raise ValueError("Passed cannot exceed total")
        return (passed / total) * 100 if total > 0 else 0
```

Run tests: `pytest` → ✅ **ALL PASS** (GREEN)

#### 4. Refactor (Keep GREEN)
```python
# pipeline_calculator.py (refactored)
from typing import Union

class SuccessRateCalculator:
    """Calculate success rates for pipeline stages"""

    def calculate(self, total: int, passed: int) -> float:
        """
        Calculate percentage of passing stages

        Args:
            total: Total number of stages
            passed: Number of passed stages

        Returns:
            Success rate as percentage (0-100)

        Raises:
            ValueError: If passed > total or values are negative
        """
        self._validate_inputs(total, passed)
        return self._compute_percentage(total, passed)

    def _validate_inputs(self, total: int, passed: int) -> None:
        if passed > total:
            raise ValueError(f"Passed ({passed}) cannot exceed total ({total})")
        if total < 0 or passed < 0:
            raise ValueError("Values must be non-negative")

    def _compute_percentage(self, total: int, passed: int) -> float:
        return (passed / total) * 100 if total > 0 else 0.0
```

Run tests: `pytest` → ✅ **STILL GREEN**

#### 5. Implement BDD Steps
```python
# tests/bdd/test_success_rate.py
from pytest_bdd import scenarios, given, when, then, parsers
from pipeline_calculator import SuccessRateCalculator

scenarios('../features/success_rate.feature')

@pytest.fixture
def calculator():
    return SuccessRateCalculator()

@pytest.fixture
def context():
    return {}

@given(parsers.parse('a pipeline with {count:d} stages'))
def pipeline_with_stages(count, context):
    context['total_stages'] = count

@given(parsers.parse('{count:d} stages passed'))
def stages_passed(count, context):
    context['passed_stages'] = count

@when('I calculate the success rate')
def calculate_rate(calculator, context):
    context['result'] = calculator.calculate(
        total=context['total_stages'],
        passed=context['passed_stages']
    )

@then(parsers.parse('the success rate should be {rate:d}%'))
def verify_rate(context, rate):
    assert context['result'] == float(rate)
```

Run BDD tests: `pytest tests/bdd/` → ✅ **ALL PASS**

## Validation Criteria

### ValidationStage Success Criteria:
1. **All unit tests GREEN** (100% passing)
2. **Test coverage ≥ 80%**
3. **No skipped tests** (all tests must run)
4. **Fast execution** (< 5 seconds for unit tests)

### BDDScenarioValidationStage Success Criteria:
1. **All scenarios GREEN** (100% passing)
2. **All Given/When/Then steps implemented**
3. **No pending scenarios**

## Configuration

```yaml
# conf/config.yaml
tdd:
  enabled: true
  test_generation:
    enabled: true
    coverage_target: 80
    include_edge_cases: true
    include_error_handling: true

  red_green_refactor:
    enabled: true
    max_iterations: 10
    verify_red_first: true  # Enforce tests fail before implementation
    verify_green_before_refactor: true

bdd:
  enabled: true
  scenario_generation:
    enabled: true
  test_generation:
    enabled: true
    framework: pytest-bdd
```

## Summary

### Current (WRONG):
```
Code → Tests
```

### Correct TDD:
```
Tests (RED) → Code (GREEN) → Refactor (KEEP GREEN)
```

### Full TDD + BDD:
```
BDD Scenarios (WHAT) → TDD Tests (HOW - RED) → Implementation (GREEN) →
BDD Steps → Refactor (GREEN) → Validate (ALL GREEN)
```

This ensures:
- ✅ Tests drive design (not afterthought)
- ✅ Code meets business requirements (BDD)
- ✅ Code is technically correct (TDD)
- ✅ Code is clean and maintainable (Refactor)
- ✅ High confidence in changes (GREEN tests)
