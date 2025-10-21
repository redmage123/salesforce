# ADR Template

# ADR-{number}: {Title}

**Status**: {Proposed | Accepted | Deprecated | Superseded}
**Date**: {YYYY-MM-DD}
**Deciders**: {Architecture Agent}
**Task**: {card-id} - {task description}

---

## Context

{Describe the issue or decision that needs to be made. What is the problem we're trying to solve? What are the requirements and constraints?}

**Requirements**:
- {Requirement 1}
- {Requirement 2}
- {Requirement 3}

**Constraints**:
- {Constraint 1}
- {Constraint 2}

**Current State**:
{What is the current architecture/implementation?}

---

## Decision

{What is the architectural decision we're making? Be specific and concrete.}

**Chosen Approach**: {Brief description}

### Design Details

**Component Structure**:
```
{Show component hierarchy, file structure, or system diagram}
```

**Data Flow**:
```
{Describe how data flows through the system}
```

**Key Components**:
1. **{Component 1}**: {Description and responsibility}
2. **{Component 2}**: {Description and responsibility}
3. **{Component 3}**: {Description and responsibility}

**APIs/Interfaces**:
```python
# Example interfaces
{Show function signatures, class definitions, or API endpoints}
```

**Data Models**:
```python
# Example data structures
{Show data classes, schemas, or database models}
```

---

## Alternatives Considered

### Alternative 1: {Name}
**Description**: {What is this alternative?}
**Pros**:
- {Pro 1}
- {Pro 2}

**Cons**:
- {Con 1}
- {Con 2}

**Why Not Chosen**: {Reason}

### Alternative 2: {Name}
**Description**: {What is this alternative?}
**Pros**:
- {Pro 1}
- {Pro 2}

**Cons**:
- {Con 1}
- {Con 2}

**Why Not Chosen**: {Reason}

---

## Consequences

### Positive Consequences
- ✅ {What becomes easier or better?}
- ✅ {What problems does this solve?}
- ✅ {What future capabilities does this enable?}

### Negative Consequences
- ⚠️ {What becomes harder or more complex?}
- ⚠️ {What technical debt does this create?}
- ⚠️ {What limitations does this impose?}

### Trade-offs
- {Trade-off 1: What we gain vs what we lose}
- {Trade-off 2: What we gain vs what we lose}

---

## Implementation Guidance

### For Developer A (Conservative Approach)
**Recommended Strategy**: {Conservative, minimal-risk implementation}

**Steps**:
1. {Step 1}
2. {Step 2}
3. {Step 3}

**Key Focus**:
- Simplicity over features
- Proven patterns
- Minimal dependencies
- Static content where possible

**Example Implementation**:
```python
{Show simple, conservative code example}
```

### For Developer B (Comprehensive Approach)
**Recommended Strategy**: {Feature-rich, optimized implementation}

**Steps**:
1. {Step 1}
2. {Step 2}
3. {Step 3}

**Key Focus**:
- Edge cases and error handling
- Performance optimization
- Accessibility (WCAG compliance)
- Progressive enhancement

**Example Implementation**:
```python
{Show comprehensive code example}
```

---

## Testing Strategy

**Unit Tests Required**:
- {Test case 1}
- {Test case 2}
- {Test case 3}

**Integration Tests Required**:
- {Integration test 1}
- {Integration test 2}

**Acceptance Criteria**:
- [ ] {Criterion 1}
- [ ] {Criterion 2}
- [ ] {Criterion 3}

**Test Coverage Minimum**:
- Developer A: {80%}
- Developer B: {90%}

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| {Risk 1} | {High/Medium/Low} | {High/Medium/Low} | {How to mitigate} |
| {Risk 2} | {High/Medium/Low} | {High/Medium/Low} | {How to mitigate} |

---

## Dependencies

**Technical Dependencies**:
- {Library 1}: {Version and purpose}
- {Library 2}: {Version and purpose}

**System Dependencies**:
- {Existing component 1}: {How it's used}
- {Existing component 2}: {How it's used}

**Backward Compatibility**:
- {What existing functionality must be preserved?}
- {What breaking changes are acceptable?}

---

## Performance Considerations

**Expected Performance**:
- {Metric 1}: {Target value}
- {Metric 2}: {Target value}

**Scalability**:
- {How does this scale with data/users?}

**Resource Usage**:
- Memory: {Expected usage}
- CPU: {Expected usage}
- Storage: {Expected usage}

---

## Security Considerations

**Security Requirements**:
- {Security requirement 1}
- {Security requirement 2}

**Threat Model**:
- {Threat 1}: {Mitigation}
- {Threat 2}: {Mitigation}

---

## Documentation Requirements

**Developer Documentation**:
- [ ] {Documentation item 1}
- [ ] {Documentation item 2}

**User Documentation**:
- [ ] {Documentation item 1}
- [ ] {Documentation item 2}

**API Documentation**:
- [ ] {API doc 1}
- [ ] {API doc 2}

---

## Review and Approval

**Architecture Review**: {Status}
**Date**: {YYYY-MM-DD}
**Approved By**: {Architecture Agent}

**Feedback from Review**:
- {Feedback item 1}
- {Feedback item 2}

---

## Links

**Related ADRs**:
- {ADR-xxx}: {Title and relationship}

**Related Tasks**:
- {card-id}: {Task description}

**References**:
- {External reference 1}
- {External reference 2}

---

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| {YYYY-MM-DD} | 1.0 | Initial version | Architecture Agent |
| {YYYY-MM-DD} | 1.1 | {Changes} | {Agent} |
