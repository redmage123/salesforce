# Requirements Parser Feature - Complete Implementation Guide

## 🎯 Feature Overview

The Requirements Parser converts free-form user requirements documents into structured YAML/JSON format that the Architecture Agent uses to generate Architecture Decision Records (ADRs).

**Workflow:**
```
User Requirements Document → Requirements Parser Agent → Structured YAML/JSON → Architecture Agent → ADRs
```

---

## 📁 Files Created

### 1. **requirements_models.py**
Data models for structured requirements:
- `StructuredRequirements` - Complete requirements document
- `FunctionalRequirement` - Functional requirements with priorities
- `NonFunctionalRequirement` - Performance, security, compliance, etc.
- `UseCase` - User scenarios and flows
- `DataRequirement` - Data models and entities
- `IntegrationRequirement` - External system integrations
- `Stakeholder`, `Constraint`, `Assumption` - Supporting models
- `Priority` enum - critical/high/medium/low/nice_to_have
- `RequirementType` enum - functional/performance/security/etc.

**Features:**
- ✅ Export to YAML or JSON
- ✅ Load from YAML or JSON
- ✅ Generate human-readable summary
- ✅ Full dataclass support with type hints

### 2. **document_reader.py**
Multi-format document reader supporting:

| Format | Extensions | Library Required |
|--------|-----------|------------------|
| **PDF** | .pdf | `pip install PyPDF2` or `pdfplumber` |
| **Microsoft Word** | .docx, .doc | `pip install python-docx` |
| **Microsoft Excel** | .xlsx, .xls | `pip install openpyxl` |
| **LibreOffice Writer** | .odt | `pip install odfpy` |
| **LibreOffice Calc** | .ods | `pip install odfpy` |
| **Plain Text** | .txt | Built-in |
| **Markdown** | .md, .markdown | Built-in |
| **CSV** | .csv | Built-in |
| **HTML** | .html, .htm | `pip install beautifulsoup4` (optional) |
| **Universal** | Any | `pip install pypandoc` (fallback) |

**Features:**
- ✅ Automatic format detection
- ✅ Graceful library detection (only requires what you use)
- ✅ Extracts text from tables, paragraphs, sheets
- ✅ Fallback to pypandoc for unsupported formats

### 3. **requirements_parser_agent.py**
LLM-powered requirements parser:

**Extraction Steps:**
1. **Overview & Metadata** - Executive summary, business goals, success criteria
2. **Functional Requirements** - What the system must do
3. **Non-Functional Requirements** - Performance, security, compliance
4. **Use Cases** - User scenarios and workflows
5. **Data Requirements** - Data models and entities
6. **Integration Requirements** - External systems
7. **Stakeholders, Constraints, Assumptions** - Supporting information

**Features:**
- ✅ Comprehensive LLM prompts for each extraction step
- ✅ Automatic ID generation (REQ-F-001, REQ-NF-001, etc.)
- ✅ Priority assignment based on content analysis
- ✅ User story generation
- ✅ Acceptance criteria extraction
- ✅ Dependency identification
- ✅ JSON response parsing (handles markdown code blocks)

---

## 🚀 Usage

### Standalone Usage

```bash
# Parse requirements from any supported format
python requirements_parser_agent.py requirements.pdf --output requirements.yaml

# Parse Word document
python requirements_parser_agent.py requirements.docx --format json

# Parse Excel spreadsheet
python requirements_parser_agent.py requirements.xlsx --project-name "My Project"

# Parse LibreOffice document
python requirements_parser_agent.py requirements.odt

# Parse plain text
python requirements_parser_agent.py requirements.txt

# Specify LLM provider and model
python requirements_parser_agent.py requirements.pdf --llm-provider anthropic --llm-model claude-3-opus-20240229
```

### Python API Usage

```python
from requirements_parser_agent import RequirementsParserAgent

# Initialize parser
parser = RequirementsParserAgent(
    llm_provider="openai",
    llm_model="gpt-4",
    verbose=True
)

# Parse requirements
structured_reqs = parser.parse_requirements_file(
    input_file="requirements.pdf",
    project_name="My Project"
)

# Save to YAML
structured_reqs.to_yaml("requirements.yaml")

# Save to JSON
structured_reqs.to_json("requirements.json")

# Get summary
print(structured_reqs.get_summary())

# Access individual requirements
for req in structured_reqs.functional_requirements:
    print(f"{req.id}: {req.title} (Priority: {req.priority.value})")
```

### Test Document Reader

```bash
# Test reading any document
python document_reader.py requirements.pdf

# Shows:
# - Supported formats on your system
# - Extracted text content
# - Character count
```

---

## 📊 Output Format

### YAML Example

```yaml
project_name: Customer Portal Redesign
version: '1.0'
created_date: '2025-10-24'

executive_summary: Redesign customer portal to improve user experience and add
  self-service capabilities

business_goals:
  - Reduce support tickets by 40%
  - Improve customer satisfaction score to 4.5/5
  - Enable 80% of common tasks to be self-service

success_criteria:
  - Portal load time < 2 seconds
  - 90% of users can complete tasks without help
  - Mobile responsive across all devices

stakeholders:
  - name: Product Manager
    role: Product Owner
    concerns:
      - Feature prioritization
      - User adoption metrics

constraints:
  - type: technical
    description: Must integrate with existing authentication system
    impact: high
    mitigation: Use OAuth 2.0 adapter

assumptions:
  - description: Users have basic computer literacy
    risk_if_false: May need additional training materials
    validation_needed: true

functional_requirements:
  - id: REQ-F-001
    title: User Authentication
    description: Users must be able to log in securely
    priority: critical
    user_story: As a customer, I want to securely log in to my account so that I can
      access my personal information
    acceptance_criteria:
      - Login with email and password
      - Two-factor authentication support
      - Password reset functionality
    estimated_effort: medium
    tags:
      - authentication
      - security

non_functional_requirements:
  - id: REQ-NF-001
    title: Performance
    description: Portal must load quickly
    type: performance
    priority: high
    metric: Page load time
    target: < 2 seconds
    acceptance_criteria:
      - Initial page load < 2s
      - Subsequent navigation < 500ms
    tags:
      - performance
      - user-experience

use_cases:
  - id: UC-001
    title: Update Profile Information
    actor: Registered Customer
    preconditions:
      - User is logged in
    main_flow:
      - Navigate to profile page
      - Click edit button
      - Update information
      - Save changes
    alternate_flows:
      cancel: User clicks cancel and changes are discarded
    postconditions:
      - Profile information is updated in database
    related_requirements:
      - REQ-F-002

data_requirements:
  - id: REQ-D-001
    entity_name: User
    description: Customer user account
    attributes:
      - name: email
        type: string
        required: 'true'
      - name: name
        type: string
        required: 'true'
      - name: phone
        type: string
        required: 'false'
    relationships:
      - has many Orders
      - belongs to Organization
    compliance:
      - GDPR
      - CCPA

integration_requirements:
  - id: REQ-I-001
    system_name: Payment Gateway
    description: Process payments securely
    direction: outbound
    protocol: REST
    data_format: JSON
    frequency: real-time
    authentication: API key
    sla: 99.9% uptime

glossary:
  Customer: End user of the portal
  Self-Service: Ability to complete tasks without support

references:
  - Original Requirements Document v1.0
  - User Research Report 2025
```

---

## 🔧 Installation

### Required Dependencies

```bash
# Core dependencies (always needed)
pip install pyyaml

# LLM client (one of):
pip install openai          # For OpenAI
pip install anthropic       # For Claude

# Optional: Document format support
pip install PyPDF2          # PDF support (or use pdfplumber)
pip install python-docx     # Word documents
pip install openpyxl        # Excel spreadsheets
pip install odfpy           # LibreOffice documents
pip install beautifulsoup4  # HTML support
pip install pypandoc        # Universal converter (fallback)
```

### Complete Installation

```bash
# Install all document format support
pip install pyyaml PyPDF2 python-docx openpyxl odfpy beautifulsoup4
```

---

## 🔄 Integration with Artemis Pipeline

### Next Steps (To Be Implemented)

1. **Create Requirements Parsing Stage** (`requirements_stage.py`)
   - PipelineStage implementation
   - Reads requirements file from kanban card
   - Outputs structured requirements to context

2. **Update Architecture Stage** (`artemis_stages.py`)
   - Accept structured requirements as input
   - Use structured data to generate ADRs
   - Better ADR quality with detailed requirements

3. **Update Orchestrator** (`artemis_orchestrator.py`)
   - Add requirements parsing stage before architecture
   - Pass requirements file path via kanban card
   - Store structured requirements in RAG

4. **CLI Support** (`artemis_cli.py`)
   - Add `--requirements-file` flag
   - Automatically trigger requirements parsing

5. **Kanban Board Integration**
   - Add `requirements_file` field to cards
   - Track requirements parsing status

---

## 📝 Example Requirements Document

Create a file `example_requirements.txt`:

```
Project: Customer Support Portal

Business Goals:
- Reduce support ticket response time by 50%
- Enable customers to self-serve for common issues
- Improve customer satisfaction to 4.5/5 stars

Stakeholders:
- Sarah Johnson (Product Manager) - Wants to track metrics and ROI
- Mike Chen (Engineering Lead) - Concerned about technical feasibility
- Lisa Brown (Customer Success) - Needs easy-to-use interface

Functional Requirements:

1. User Authentication
   - Customers must be able to register and log in securely
   - Support for social login (Google, Facebook)
   - Two-factor authentication for sensitive actions
   Priority: Critical

2. Ticket Management
   - Customers can create, view, and update support tickets
   - Attach files (images, logs) to tickets
   - Real-time status updates
   Priority: High

3. Knowledge Base Search
   - Full-text search across help articles
   - AI-powered suggestions based on ticket description
   - Article rating and feedback
   Priority: Medium

Non-Functional Requirements:

Performance:
- Page load time must be under 2 seconds
- Search results in under 500ms
- Support 10,000 concurrent users

Security:
- All data encrypted in transit (TLS 1.3)
- PII data encrypted at rest
- GDPR and CCPA compliant

Accessibility:
- WCAG 2.1 AA compliant
- Screen reader compatible
- Keyboard navigation support

Integrations:
- Integrate with Zendesk API for ticket sync
- Slack notifications for critical tickets
- Salesforce CRM data sync

Constraints:
- Must use existing AWS infrastructure
- Budget: $200,000
- Timeline: 6 months
- Must support IE11 (legacy requirement)

Assumptions:
- Users have reliable internet connection
- Customer data is available via API
- Design team will provide UI mockups
```

Then parse it:

```bash
python requirements_parser_agent.py example_requirements.txt
```

---

## ✅ Feature Benefits

1. **Multi-Format Support** - Works with PDFs, Office docs, plain text, and more
2. **LLM-Powered** - Intelligent extraction and categorization
3. **Structured Output** - Clean YAML/JSON for downstream processing
4. **Comprehensive** - Captures all requirement types
5. **Extensible** - Easy to add new requirement types
6. **Standards-Based** - Follows requirements engineering best practices
7. **Pipeline Ready** - Designed for Artemis integration

---

## 🎓 Requirements Engineering Best Practices

The parser follows industry standards:

- **IEEE 830** - Software Requirements Specification
- **BABOK** - Business Analysis Body of Knowledge
- **Agile** - User stories and acceptance criteria
- **TOGAF** - Architecture requirements
- **NIST** - Security and compliance requirements

---

## 🔮 Future Enhancements

- [ ] Requirements validation and conflict detection
- [ ] Traceability matrix generation
- [ ] Requirements prioritization algorithms (MoSCoW, Kano)
- [ ] Change impact analysis
- [ ] Requirements coverage reporting
- [ ] Integration with Jira, Azure DevOps
- [ ] Visual requirements modeling (diagrams)
- [ ] AI-powered requirement quality scoring

---

## 📞 Support

For questions or issues:
- Check the code comments in each file
- Run with `--verbose` for detailed logging
- Test with `python document_reader.py <your_file>` to verify format support

---

**Status:** ✅ Complete - Ready for pipeline integration
**Created:** 2025-10-24
**Version:** 1.0
