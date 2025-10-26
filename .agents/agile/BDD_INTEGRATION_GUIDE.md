# BDD Integration Guide for Artemis

## Overview

This guide explains how Behavior-Driven Development (BDD) is integrated into the Artemis autonomous development pipeline, complementing the existing Test-Driven Development (TDD) approach.

## Why BDD + TDD?

### TDD (Test-Driven Development)
- **Focus**: HOW the code works (technical implementation)
- **Tests**: Unit tests, integration tests
- **Perspective**: Developer-centric
- **Language**: Code (pytest, unittest)

### BDD (Behavior-Driven Development)
- **Focus**: WHAT the system should do (business behavior)
- **Tests**: Acceptance criteria in plain language
- **Perspective**: Stakeholder-centric
- **Language**: Gherkin (Given/When/Then)

### Together
- **Technical Correctness** (TDD): Code works as designed
- **Business Value** (BDD): Code meets business requirements
- **Living Documentation**: Scenarios serve as executable specifications
- **Collaboration**: Bridge between business and development

## Pipeline Integration

### Updated Pipeline Flow

```
1. RequirementsParsingStage      → Parse requirements documents
2. SprintPlanningStage            → Plan sprint with story points
3. [NEW] BDDScenarioGenerationStage → Generate Gherkin scenarios
4. ProjectAnalysisStage           → Analyze project structure
5. ArchitectureStage              → Design system architecture
6. ProjectReviewStage             → Review and validate plans
7. DependencyValidationStage      → Validate dependencies
8. [NEW] BDDTestGenerationStage   → Generate pytest-bdd step definitions
9. DevelopmentStage               → Implement solution (TDD + BDD)
10. ValidationStage               → Run unit tests (TDD)
11. [NEW] BDDScenarioValidationStage → Run BDD acceptance tests
12. UIUXStage                     → Evaluate UI/UX compliance
13. CodeReviewStage               → Review code quality
14. IntegrationStage              → Integration testing
15. TestingStage                  → Final quality gates
```

## BDD Stages

### 1. BDD Scenario Generation Stage

**Purpose**: Transform requirements into executable Gherkin scenarios

**Input**:
- Requirements document
- User stories
- Acceptance criteria

**Output**:
- Gherkin .feature files
- Stored in `/tmp/{developer}/features/`

**Process**:
1. Fetch requirements from RAG or context
2. Use LLM to generate Gherkin scenarios
3. Validate Gherkin syntax
4. Store feature files for developers
5. Store in RAG for reference

**Example Output**:
```gherkin
Feature: User Authentication
  As a user
  I want to log in securely
  So that I can access my account

  Scenario: Successful login with valid credentials
    Given I am on the login page
    When I enter valid username "john@example.com"
    And I enter valid password "SecurePass123"
    And I click the "Login" button
    Then I should be redirected to the dashboard
    And I should see a welcome message "Welcome, John"

  Scenario: Failed login with invalid password
    Given I am on the login page
    When I enter valid username "john@example.com"
    And I enter invalid password "WrongPass"
    And I click the "Login" button
    Then I should see an error message "Invalid credentials"
    And I should remain on the login page

  Scenario Outline: Login attempts with various inputs
    Given I am on the login page
    When I enter username "<username>"
    And I enter password "<password>"
    And I click the "Login" button
    Then I should see "<result>"

    Examples:
      | username          | password      | result                |
      | john@example.com  | SecurePass123 | Welcome, John         |
      | invalid@email     | any password  | Invalid credentials   |
      | john@example.com  |               | Password is required  |
```

### 2. BDD Test Generation Stage

**Purpose**: Generate pytest-bdd step definitions from Gherkin scenarios

**Input**:
- Gherkin .feature files from BDDScenarioGenerationStage

**Output**:
- pytest-bdd test files
- Step definition stubs
- Stored in `/tmp/{developer}/tests/bdd/`

**Process**:
1. Parse all .feature files
2. Extract Given/When/Then steps
3. Generate pytest-bdd test file structure
4. Create step definition functions
5. Add TODO markers for implementation
6. Store test files for developers

**Example Output**:
```python
# tests/bdd/test_user_authentication.py
from pytest_bdd import scenarios, given, when, then, parsers
import pytest

# Load all scenarios from feature file
scenarios('../features/user_authentication.feature')

@pytest.fixture
def browser():
    from selenium import webdriver
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

@given('I am on the login page')
def on_login_page(browser):
    browser.get('https://example.com/login')

@when(parsers.parse('I enter valid username "{username}"'))
def enter_username(browser, username):
    browser.find_element_by_id('username').send_keys(username)

@when(parsers.parse('I enter valid password "{password}"'))
def enter_password(browser, password):
    browser.find_element_by_id('password').send_keys(password)

@when(parsers.parse('I click the "{button_text}" button'))
def click_button(browser, button_text):
    browser.find_element_by_xpath(f"//button[text()='{button_text}']").click()

@then('I should be redirected to the dashboard')
def check_dashboard_redirect(browser):
    assert browser.current_url == 'https://example.com/dashboard'

@then(parsers.parse('I should see a welcome message "{message}"'))
def check_welcome_message(browser, message):
    assert message in browser.page_source
```

### 3. BDD Scenario Validation Stage

**Purpose**: Execute BDD scenarios to validate behavior

**Input**:
- pytest-bdd test files
- Implemented code

**Output**:
- BDD test results
- Scenario coverage report
- Failed scenario details

**Process**:
1. Run pytest-bdd tests
2. Collect scenario pass/fail status
3. Generate coverage report (% scenarios passing)
4. Identify failing scenarios
5. Store results in RAG

**Example Output**:
```
BDD Scenario Validation Report
================================

Feature: User Authentication
  ✅ Scenario: Successful login with valid credentials - PASSED
  ❌ Scenario: Failed login with invalid password - FAILED
     Step failed: "Then I should see an error message"
     Error: AssertionError: Expected "Invalid credentials" not found
  ✅ Scenario Outline: Login attempts - 2/3 PASSED
     ✅ Example 1: john@example.com / SecurePass123 - PASSED
     ❌ Example 2: invalid@email / any password - FAILED
     ✅ Example 3: john@example.com / (empty) - PASSED

Overall: 66.7% scenarios passing (4/6)
Status: NEEDS_IMPROVEMENT (target: 100%)
```

## Configuration

### Enable/Disable BDD Stages

Add to `.agents/agile/conf/config.yaml`:

```yaml
bdd:
  enabled: true
  scenario_generation:
    enabled: true
    temperature: 0.3
    max_tokens: 2000
  test_generation:
    enabled: true
    framework: pytest-bdd  # or behave
  validation:
    enabled: true
    min_pass_rate: 80  # minimum % of scenarios that must pass
    fail_on_incomplete: false  # fail if scenarios not implemented
```

### Dependencies

Add to `requirements.txt`:

```
pytest-bdd>=6.0.0
gherkin-official>=24.0.0
behave>=1.2.6  # alternative to pytest-bdd
```

## Benefits

### 1. Living Documentation
- Gherkin scenarios serve as always-up-to-date documentation
- Stakeholders can read scenarios without technical knowledge
- Scenarios act as contracts between business and development

### 2. Early Requirement Validation
- Catches ambiguous requirements early (during scenario generation)
- Forces clarification of acceptance criteria
- Prevents scope creep

### 3. Automated Acceptance Testing
- Scenarios automatically converted to tests
- Regression testing of business behavior
- Continuous validation of business value

### 4. Improved Collaboration
- Common language between stakeholders and developers
- Scenarios can be reviewed by product owners
- Reduces misunderstandings

### 5. Better Test Coverage
- TDD ensures technical correctness
- BDD ensures business value delivery
- Together: comprehensive quality assurance

## Example: Full BDD Workflow

### Task: "Create Artemis self-demo with Chart.js visualization"

#### 1. Requirements Parsing
```
Title: Create Artemis self-demo with Chart.js visualization
Description: Build an interactive HTML demo showing Artemis pipeline metrics
```

#### 2. BDD Scenario Generation
```gherkin
Feature: Artemis Self-Demo Visualization
  As a stakeholder
  I want to see Artemis pipeline metrics visualized
  So that I can understand the autonomous development process

  Scenario: Display pipeline stage progress
    Given the Artemis pipeline has completed 7 stages
    When I view the demo page
    Then I should see a chart showing 7 completed stages
    And I should see stage names and durations
```

#### 3. BDD Test Generation
```python
@given(parsers.parse('the Artemis pipeline has completed {count:d} stages'))
def pipeline_completed_stages(count, context):
    context['completed_stages'] = count

@when('I view the demo page')
def view_demo_page(browser):
    browser.get('file:///tmp/artemis_demo.html')

@then(parsers.parse('I should see a chart showing {count:d} completed stages'))
def verify_chart_stages(browser, count, context):
    chart_data = browser.execute_script('return myChart.data.labels.length')
    assert chart_data == count
```

#### 4. Development (TDD + BDD)
Developer implements:
- HTML page with Chart.js
- Unit tests for chart rendering (TDD)
- Step definitions for scenarios (BDD)

#### 5. BDD Validation
```
✅ All scenarios passing (100%)
Status: APPROVED
```

## Best Practices

### Scenario Writing
1. **Use business language**, not technical jargon
2. **One scenario = one behavior**
3. **Keep scenarios independent** (can run in any order)
4. **Use scenario outlines** for data-driven tests
5. **Focus on WHAT, not HOW** (avoid implementation details)

### Step Definitions
1. **Reusable steps** across scenarios
2. **Clear, descriptive step names**
3. **Proper abstraction** (page objects, helpers)
4. **Good error messages** when steps fail

### Organization
```
project/
  features/
    user_authentication.feature
    data_visualization.feature
  tests/
    bdd/
      conftest.py          # Shared fixtures
      test_user_auth.py    # Step definitions
      test_visualization.py
    unit/
      test_models.py       # TDD unit tests
    integration/
      test_api.py          # TDD integration tests
```

## Troubleshooting

### Common Issues

**Issue**: Scenarios not generated
- Check requirements are available in RAG
- Verify LLM client is configured
- Check logs for LLM errors

**Issue**: Step definitions not matching
- Verify Gherkin syntax in .feature files
- Check for typos in step text
- Ensure pytest-bdd is installed

**Issue**: Scenarios failing
- Check step implementations
- Verify test data and fixtures
- Review error messages in validation report

## Future Enhancements

1. **Scenario Review Stage**: Allow human review of generated scenarios
2. **BDD Metrics Dashboard**: Visualize scenario coverage and trends
3. **Scenario Prioritization**: Run critical scenarios first
4. **Auto-fix Failing Scenarios**: LLM suggests fixes for failing steps
5. **Integration with JIRA**: Sync scenarios with user stories
6. **Multi-language Support**: Generate scenarios in multiple languages

## References

- [Cucumber BDD](https://cucumber.io/docs/bdd/)
- [pytest-bdd Documentation](https://pytest-bdd.readthedocs.io/)
- [Gherkin Reference](https://cucumber.io/docs/gherkin/reference/)
- [BDD Best Practices](https://cucumber.io/docs/bdd/better-gherkin/)
