# Artemis Repository Migration Plan

## Executive Summary

Migrate the Artemis project from `/home/bbrelin/src/repos/salesforce/.agents/agile` to a new standalone repository at `/home/bbrelin/src/repos/artemix`, while keeping Salesforce demos in their current location.

## Current State Analysis

### Artemis Files (to be moved)
**Location:** `/home/bbrelin/src/repos/salesforce/.agents/agile/`
- **Total Size:** ~18MB source + ~7.7MB data = ~26MB
- **Python Files:** 167 `.py` files
- **Total Source Files:** 337 files (py, md, yaml, json)
- **Subdirectories:**
  - `conf/` - Hydra configuration files
  - `db/` - ChromaDB vector database
  - `outputs/` - Stage outputs
  - `prompts/` - Agent prompt templates
  - `stages/` - Modular stage implementations
  - `__pycache__/` - Python cache (exclude from migration)
  - `.pytest_cache/` - Test cache (exclude from migration)

### Artemis Data (to be moved)
**Location:** `/home/bbrelin/src/repos/salesforce/.artemis_data/`
- **Total Size:** ~7.7MB
- **Subdirectories:**
  - `adrs/` - Architecture Decision Records
  - `agent_messages/` - Inter-agent communication logs
  - `artemis_persistence.db` - Persistence database
  - `checkpoints/` - Pipeline checkpoints
  - `code_reviews/` - Code review outputs
  - `cost_tracking/` - LLM cost tracking data
  - `developer_output/` - Generated developer artifacts
  - `logs/` - Execution logs
  - `rag_db/` - RAG database files
  - `requirements/` - Parsed requirements
  - `runs/` - Run history
  - `state/` - State machine data
  - `temp/` - Temporary files

### Salesforce Files (to remain)
**Location:** `/home/bbrelin/src/repos/salesforce/src/`
- Jupyter notebooks for Salesforce demos:
  - `ai_integration_guide.ipynb`
  - `salesforce_ai_revenue_intelligence.ipynb`
  - `agent_assist_rag_salesforce.ipynb`
  - `contract_summarization.ipynb`
  - `lead_opportunity_intelligence.ipynb`
  - `sales_email_generator.ipynb`
- Demo servers:
  - `opportunity_intelligence_server.py`
  - `contract_demo_server.py`
  - `ai_before_after_code_demo.py`
- RAG backend:
  - `rag_backend/vector_db.py`
  - `rag_backend/api_server.py`
  - `rag_backend/mock_data_generator.py`

## Migration Strategy: Clean Copy Approach

**Rationale:** Since Artemis is being separated into its own project, a clean copy is cleaner than git history preservation. This allows:
- Fresh git history for Artemis project
- No bloat from unrelated Salesforce commits
- Clear separation of concerns
- Easier to understand Artemis evolution independently

**Alternative Considered:** Git subtree split to preserve history
**Why Not Used:** Would bring entire Salesforce repo history into Artemis, creating confusion about what's Artemis-specific vs inherited.

## Migration Steps

### Step 1: Create New Artemix Repository
```bash
# Create directory
mkdir -p /home/bbrelin/src/repos/artemix

# Initialize git repository
cd /home/bbrelin/src/repos/artemix
git init
```

### Step 2: Copy Artemis Source Files
```bash
# Copy entire agile directory
cp -r /home/bbrelin/src/repos/salesforce/.agents/agile/* /home/bbrelin/src/repos/artemix/

# Exclude cache directories
rm -rf /home/bbrelin/src/repos/artemix/__pycache__
rm -rf /home/bbrelin/src/repos/artemix/.pytest_cache
```

### Step 3: Copy Artemis Data Directory
```bash
# Copy data directory to new location
cp -r /home/bbrelin/src/repos/salesforce/.artemis_data /home/bbrelin/src/repos/artemix/.artemis_data
```

### Step 4: Create New Repository Structure
```
artemix/
├── .artemis_data/          # Runtime data (gitignored)
├── conf/                   # Hydra configs
├── db/                     # ChromaDB (gitignored)
├── outputs/                # Stage outputs (gitignored)
├── prompts/                # Agent prompts
├── stages/                 # Stage implementations
├── tests/                  # Unit & integration tests (create if needed)
├── docs/                   # Documentation (create)
├── examples/               # Example usage (create)
├── .env.example            # Example environment vars
├── .gitignore              # Git ignore patterns
├── README.md               # Project README
├── requirements.txt        # Python dependencies
├── setup.py                # Package setup (optional)
└── *.py                    # All Artemis Python modules
```

### Step 5: Create Essential Repository Files

#### .gitignore
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/

# Virtual environments
.venv/
venv/
env/

# Artemis data
.artemis_data/
db/
outputs/
*.db
*.sqlite3

# Environment
.env
.env_artemis

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log
logs/

# Temporary
temp/
tmp/
```

#### requirements.txt
```txt
# Extract from salesforce repo or create fresh
anthropic>=0.40.0
chromadb>=0.5.0
hydra-core>=1.3.0
openai>=1.0.0
neo4j>=5.0.0
datasets>=2.0.0
# ... (list all dependencies)
```

#### README.md
```markdown
# Artemis - AI-Powered Agile Development Pipeline

Artemis is an autonomous multi-agent system for software development that implements agile methodologies including TDD, BDD, code review, and project management workflows.

## Features
- Multi-developer agent orchestration
- Requirements-driven validation
- TDD and quality-driven workflows
- Knowledge graph integration
- RAG-powered code generation
- Checkpoint-based state management

## Installation
[Installation instructions]

## Usage
[Usage examples]

## Documentation
[Link to docs]
```

### Step 6: Update Path References

**Files to Update:**
1. `artemis_orchestrator.py` - Update data paths
2. `persistence_store.py` - Update database paths
3. `rag_agent.py` - Update ChromaDB paths
4. `knowledge_graph.py` - Update Neo4j connection
5. `conf/storage/local.yaml` - Update storage paths
6. `conf/logging/*.yaml` - Update log paths
7. All files with hardcoded `/home/bbrelin/src/repos/salesforce/` paths

**Path Update Strategy:**
```python
# Before:
data_dir = Path("/home/bbrelin/src/repos/salesforce/.artemis_data")

# After:
project_root = Path(__file__).parent
data_dir = project_root / ".artemis_data"
```

### Step 7: Create Salesforce Integration Bridge (Optional)

Create a simple integration script in Salesforce repo to invoke Artemis:

**Location:** `/home/bbrelin/src/repos/salesforce/artemis_bridge.py`
```python
#!/usr/bin/env python3
"""
Bridge script to invoke Artemis from Salesforce demos.

Usage:
    python artemis_bridge.py --card-id card-123 --full
"""
import subprocess
import sys
from pathlib import Path

ARTEMIX_PATH = Path("/home/bbrelin/src/repos/artemix")

def invoke_artemis(*args):
    """Invoke Artemis orchestrator in artemix repo"""
    cmd = [
        "python3",
        str(ARTEMIX_PATH / "artemis_orchestrator.py"),
        *args
    ]
    result = subprocess.run(cmd, cwd=ARTEMIX_PATH)
    return result.returncode

if __name__ == "__main__":
    sys.exit(invoke_artemis(*sys.argv[1:]))
```

This allows Salesforce demos to still use Artemis without tight coupling.

### Step 8: Test Artemix Repository

```bash
# Navigate to new repo
cd /home/bbrelin/src/repos/artemix

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run syntax check
python3 -m py_compile artemis_orchestrator.py

# Run a test card
python3 artemis_orchestrator.py --card-id test-001 --full

# Verify outputs
ls -la .artemis_data/developer_output/
```

### Step 9: Initial Git Commit

```bash
cd /home/bbrelin/src/repos/artemix

# Add all files
git add .

# Initial commit
git commit -m "Initial commit: Artemis autonomous development pipeline

Migrated from salesforce repo to standalone project.

Features:
- Multi-agent orchestration
- Requirements-driven validation
- TDD and quality-driven workflows
- Knowledge graph integration
- RAG-powered code generation
- Checkpoint-based state management

Technologies:
- Python 3.10+
- Anthropic Claude API
- ChromaDB vector database
- Neo4j knowledge graph
- Hydra configuration management"
```

### Step 10: Clean Up Salesforce Repo (Optional)

**WARNING:** Only do this after confirming artemix works independently!

```bash
# Create backup first
cd /home/bbrelin/src/repos/salesforce
git checkout -b backup-before-artemis-removal

# Optionally remove Artemis files from salesforce repo
# (Keep if you want them as reference or for backward compatibility)
```

## Post-Migration Tasks

### 1. Update Documentation
- [ ] Update README.md with current features
- [ ] Create CONTRIBUTING.md
- [ ] Create docs/ directory with architecture diagrams
- [ ] Document all agent types and workflows
- [ ] Create API reference

### 2. CI/CD Setup (Future)
- [ ] Create GitHub Actions workflows
- [ ] Add linting (black, flake8, mypy)
- [ ] Add unit test runner
- [ ] Add integration test runner

### 3. Package Distribution (Future)
- [ ] Create setup.py for pip installation
- [ ] Publish to PyPI
- [ ] Create Docker container
- [ ] Create Kubernetes manifests

### 4. Configuration Management
- [ ] Review all Hydra configs for hardcoded paths
- [ ] Create environment-specific configs (dev, prod)
- [ ] Document configuration options

## Dependencies Between Salesforce and Artemix

### Artemix → Salesforce: NONE
Artemix should be completely independent. No imports from salesforce repo.

### Salesforce → Artemix: Optional Bridge
If Salesforce demos want to use Artemis:
- Use `artemis_bridge.py` subprocess invocation
- Or import artemix as Python package (if installed)
- Or keep Artemis in salesforce repo (not recommended)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Broken path references | High | Systematic path update in Step 6 |
| Missing dependencies | Medium | Comprehensive requirements.txt |
| Data loss during copy | High | Verify copy with checksums, keep original |
| Salesforce demos break | Medium | Test demos before removing Artemis from salesforce |
| Configuration errors | Medium | Test with sample card after migration |

## Rollback Plan

If migration fails:
1. Keep original `/home/bbrelin/src/repos/salesforce/.agents/agile/` intact until verification
2. Can delete `/home/bbrelin/src/repos/artemix/` and start over
3. No changes to salesforce repo until Step 10 (optional cleanup)

## Timeline Estimate

- Step 1-3: 5 minutes (directory creation and copy)
- Step 4-5: 15 minutes (repository structure and files)
- Step 6: 30-60 minutes (path updates - most critical)
- Step 7: 10 minutes (bridge script - optional)
- Step 8: 20 minutes (testing)
- Step 9: 5 minutes (git commit)
- **Total: ~90-120 minutes**

## Success Criteria

- [ ] `/home/bbrelin/src/repos/artemix` repository exists
- [ ] All 167 Python files copied successfully
- [ ] No import errors when loading modules
- [ ] Path references updated to relative paths
- [ ] Artemis can execute test card successfully
- [ ] Output files generated in correct locations
- [ ] ChromaDB and Neo4j connections work
- [ ] No references to `/home/bbrelin/src/repos/salesforce/` remain
- [ ] Salesforce demos still work (if using bridge)

## Next Steps After Migration

1. **Create comprehensive documentation**
2. **Add more example cards and tutorials**
3. **Set up testing infrastructure**
4. **Consider GitHub repository creation**
5. **Create demo videos and presentations**
6. **Package for distribution**

---

**Note:** This is a one-way migration. Once completed and verified, the original Artemis files in salesforce repo can be removed or kept as archive.
