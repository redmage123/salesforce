# AGENTIC PIPELINE TEST SUITE

**Test-Driven Development (TDD) Framework for Agile Pipeline**

---

## Overview

This directory contains the test infrastructure for the agentic development pipeline. All agents **MUST** write tests before implementation following the **RED → GREEN → REFACTOR** cycle.

---

## Directory Structure

```
tests/
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_template_unit.py
│   └── (agent-specific unit tests)
├── integration/             # Integration tests (component interactions)
│   ├── test_template_integration.py
│   └── (agent-specific integration tests)
├── acceptance/              # Acceptance tests (end-to-end workflows)
│   ├── test_template_acceptance.py
│   └── (feature acceptance tests)
├── fixtures/                # Test data and fixtures
│   ├── sample_task.json
│   ├── sample_solution.json
│   └── (other test data)
└── README.md               # This file
```

---

## Test Types

### 1. Unit Tests (`unit/`)

**Purpose**: Test individual functions/components in isolation

**Characteristics**:
- Fast execution (< 1 second per test)
- Mock external dependencies
- Test one thing per test
- Follow Arrange-Act-Assert pattern

**When to Write**:
- For every function you create
- Minimum 5 unit tests per feature
- Test happy path, error cases, edge cases

**Example**:
```python
def test_validate_json_with_valid_input():
    # Arrange
    valid_json = '{"key": "value"}'

    # Act
    result = validate_json(valid_json)

    # Assert
    assert result is True
```

**Template**: Use `test_template_unit.py`

---

### 2. Integration Tests (`integration/`)

**Purpose**: Test interactions between components

**Characteristics**:
- Test component interactions
- Test file I/O operations
- Test command execution
- Reasonably fast (< 10 seconds per test)

**When to Write**:
- When components interact
- For file operations
- For command executions
- Minimum 3 integration tests per feature

**Example**:
```python
def test_notebook_to_html_workflow(tmp_path):
    # Arrange
    notebook = create_test_notebook(tmp_path)

    # Act
    html = execute_notebook_to_html(notebook)

    # Assert
    assert html.exists()
    assert html.stat().st_size > 1000
```

**Template**: Use `test_template_integration.py`

---

### 3. Acceptance Tests (`acceptance/`)

**Purpose**: Test complete user workflows end-to-end

**Characteristics**:
- Test from user's perspective
- Verify acceptance criteria
- Test complete features
- May take longer (< 60 seconds per test)

**When to Write**:
- For each user story
- To verify acceptance criteria
- For feature completeness
- Minimum 2 acceptance tests per feature

**Example**:
```python
def test_user_can_create_and_complete_task():
    # GIVEN: User has a task
    task = create_task("Add notifications")

    # WHEN: Task flows through pipeline
    process_task_through_pipeline(task)

    # THEN: Task is completed successfully
    assert task.status == "done"
    assert all_acceptance_criteria_verified(task)
```

**Template**: Use `test_template_acceptance.py`

---

## TDD Workflow (RED → GREEN → REFACTOR)

### Required Process for ALL Development

1. **RED Phase** (Write Failing Tests)
   ```bash
   # Write test FIRST (before implementation)
   # Test should FAIL because function doesn't exist yet
   ```

2. **GREEN Phase** (Make Tests Pass)
   ```bash
   # Write MINIMUM code to make test pass
   # Don't worry about code quality yet
   ```

3. **REFACTOR Phase** (Improve Code Quality)
   ```bash
   # Improve code quality
   # Tests must STILL pass
   ```

### Example TDD Workflow

```python
# ============================================
# RED PHASE: Write failing test
# ============================================
def test_calculate_discount():
    assert calculate_discount(100, 0.2) == 80  # FAILS - function doesn't exist

# ============================================
# GREEN PHASE: Minimum code to pass
# ============================================
def calculate_discount(price, discount):
    return price - (price * discount)

# Test now PASSES ✓

# ============================================
# REFACTOR PHASE: Improve quality
# ============================================
def calculate_discount(price: float, discount: float) -> float:
    """
    Calculate discounted price

    Args:
        price: Original price
        discount: Discount percentage (0.0 to 1.0)

    Returns:
        Discounted price

    Raises:
        ValueError: If discount not in valid range
    """
    if not 0 <= discount <= 1:
        raise ValueError("Discount must be between 0 and 1")

    return price - (price * discount)

# Test STILL passes ✓
# Code is now better quality ✓
```

---

## Running Tests

### Run All Tests
```bash
cd /home/bbrelin/src/repos/salesforce/.agents/tests
pytest -v
```

### Run Specific Test Type
```bash
# Unit tests only
pytest unit/ -v

# Integration tests only
pytest integration/ -v

# Acceptance tests only
pytest acceptance/ -v
```

### Run with Coverage
```bash
pytest --cov=../ --cov-report=html --cov-report=term
```

### Run Specific Test File
```bash
pytest unit/test_orchestrator.py -v
```

### Run Specific Test
```bash
pytest unit/test_orchestrator.py::TestOrchestrator::test_create_task -v
```

---

## Quality Gates

**No code advances without**:

✅ **80% minimum test coverage**
✅ **All tests passing (green)**
✅ **Tests written BEFORE implementation** (TDD compliance)
✅ **No skipped tests** (without documented reason)
✅ **Test execution time < 30 seconds** (total)

**Validator Agent will BLOCK code that fails these gates**

---

## Test Coverage Requirements

| Component | Target Coverage | Minimum Coverage |
|-----------|-----------------|------------------|
| Core Functions | 95% | 85% |
| Utility Functions | 90% | 80% |
| Error Handlers | 100% | 90% |
| Integration Flows | 85% | 75% |
| Overall | 90% | 80% |

---

## Writing Good Tests

### DO ✅

- **Write tests first** (TDD)
- **Test one thing per test**
- **Use descriptive test names**: `test_user_can_create_task_with_valid_input`
- **Follow Arrange-Act-Assert**:
  ```python
  def test_example():
      # Arrange - set up test data
      data = create_test_data()

      # Act - call the function
      result = function_under_test(data)

      # Assert - verify the result
      assert result == expected_value
  ```
- **Use fixtures** for shared setup
- **Test error cases** (not just happy path)
- **Test edge cases** (empty, null, boundary values)
- **Use parametrized tests** for multiple inputs
- **Mock external dependencies**

### DON'T ❌

- **Don't write code before tests** (breaks TDD)
- **Don't test implementation details** (test behavior)
- **Don't create brittle tests** (that break with small changes)
- **Don't skip error testing**
- **Don't use real external services** (use mocks)
- **Don't ignore failing tests**
- **Don't commit commented-out tests**
- **Don't write tests without assertions**

---

## Test Naming Conventions

### Pattern
```python
def test_<what>_<condition>_<expected_result>():
    pass
```

### Examples
```python
# Good ✅
def test_create_card_with_valid_input_returns_card():
    pass

def test_move_card_to_invalid_column_raises_error():
    pass

def test_calculate_cycle_time_with_completed_card_returns_hours():
    pass

# Bad ❌
def test_1():
    pass

def test_card():
    pass

def test_it_works():
    pass
```

---

## Fixtures

**Location**: `fixtures/`

### Available Fixtures

1. **`sample_task.json`**
   - Sample task specification
   - Use for testing task processing

2. **`sample_solution.json`**
   - Sample developer solution
   - Use for testing arbitration/validation

### Using Fixtures

```python
import json
from pathlib import Path

@pytest.fixture
def sample_task():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_task.json"
    with open(fixture_path) as f:
        return json.load(f)

def test_with_fixture(sample_task):
    assert sample_task['task_id'] == "sample-task-001"
```

---

## CI/CD Integration

Tests run automatically:

1. **Before Validation** - Developer A/B submit solutions
2. **During Validation** - Validator checks test compliance
3. **Before Integration** - Integration Agent verifies tests pass
4. **During Testing** - Test Agent runs full suite

**Pipeline BLOCKS if tests fail at any stage**

---

## Test Metrics Tracked

The pipeline tracks:

- **Test Coverage %** (target: ≥ 80%)
- **Test Execution Time** (target: < 30s)
- **Test Pass Rate** (target: 100%)
- **TDD Compliance Rate** (target: 100%)
- **Test-to-Code Ratio** (target: ≥ 1.0)

View metrics in: `.agents/agile/metrics_dashboard.json`

---

## Debugging Failed Tests

### View Detailed Output
```bash
pytest -vv  # Very verbose
```

### Show Print Statements
```bash
pytest -s  # Show stdout
```

### Drop into Debugger on Failure
```bash
pytest --pdb  # Python debugger
```

### Run Only Failed Tests
```bash
pytest --lf  # Last failed
```

---

## Agent-Specific Testing

### Orchestrator Agent
- Test task parsing
- Test spec generation
- Test acceptance criteria creation

### Developer A/B Agents
- Test TDD workflow compliance
- Test solution generation
- Test test coverage calculation

### Validator Agent
- Test syntax validation
- Test TDD compliance checking
- Test coverage verification

### Arbitrator Agent
- Test scoring algorithm
- Test solution comparison
- Test selection logic

### Integration Agent
- Test file merging
- Test deployment
- Test rollback

### Test Agent
- Test comprehensive validation
- Test edge case coverage
- Test regression detection

---

## Examples

### Complete TDD Example

See: `unit/test_template_unit.py` - Class `TestAddNumbers`

This shows:
- Multiple test cases
- Error handling tests
- Edge case tests
- Parametrized tests
- Complete TDD workflow

### Integration Test Example

See: `integration/test_template_integration.py` - `test_multi_step_workflow`

This shows:
- Multi-step process testing
- File I/O testing
- Data flow verification

### Acceptance Test Example

See: `acceptance/test_template_acceptance.py` - `test_user_can_create_task_and_complete_workflow`

This shows:
- User story testing
- Complete feature workflow
- Acceptance criteria verification

---

## Getting Started

### For New Features

1. **Read the task specification**
2. **Identify test scenarios** from acceptance criteria
3. **Create test files**:
   ```bash
   touch unit/test_my_feature.py
   touch integration/test_my_feature_workflow.py
   touch acceptance/test_my_feature_acceptance.py
   ```
4. **Write RED tests** (that fail)
5. **Implement code** to make tests GREEN
6. **Refactor** while keeping tests GREEN
7. **Run coverage check**:
   ```bash
   pytest --cov
   ```
8. **Ensure ≥ 80% coverage**
9. **Submit solution**

### For Bug Fixes

1. **Write test that reproduces the bug** (RED)
2. **Fix the bug** (GREEN)
3. **Refactor if needed**
4. **Verify test passes**
5. **Run regression tests**:
   ```bash
   pytest  # All tests should still pass
   ```

---

## Resources

- **pytest Documentation**: https://docs.pytest.org/
- **TDD Guide**: Martin Fowler's "Test-Driven Development"
- **Coverage.py**: https://coverage.readthedocs.io/

---

## Questions?

- Check test templates in each directory
- Review `agile-tdd-kanban-specification.md`
- See Kanban board usage guide

---

**Remember**:
- Tests are NOT optional
- Write tests FIRST (TDD)
- Aim for ≥ 80% coverage
- All tests must PASS before advancement

**Last Updated**: October 21, 2025
**Version**: 1.0
