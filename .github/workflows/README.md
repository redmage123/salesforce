# GitHub Actions Workflows

This directory contains automated workflows for the Salesforce AI demo project, integrating GitHub Actions with our Agile/TDD pipeline.

## Available Workflows

### 1. 🔄 Agile/TDD Pipeline (`pipeline.yml`)
**Triggers:** Push to master, Pull requests, Manual dispatch

Executes the full Agile/TDD development pipeline:
- Runs architecture stage (creates ADRs)
- Validates dependencies
- Executes parallel developer implementations (A & B)
- Runs arbitration to select best solution
- Performs integration testing
- Runs final quality gates

**Artifacts:**
- Pipeline reports (JSON)
- Architecture Decision Records (ADRs)
- Test results

**Manual Trigger:**
```bash
# Via GitHub CLI
gh workflow run pipeline.yml

# With specific card
gh workflow run pipeline.yml -f card_id=card-20251021122355
```

---

### 2. ✅ Automated Tests (`tests.yml`)
**Triggers:** Push to master/main, Pull requests

Runs comprehensive test suite:
- Tests across Python 3.10 and 3.11
- Executes pytest with coverage reports
- Generates HTML coverage reports
- Tests all developer solutions

**Artifacts:**
- Coverage reports (HTML)
- Test results

---

### 3. 🔍 Code Quality Checks (`code-quality.yml`)
**Triggers:** Push to master/main, Pull requests

Performs code quality analysis:
- **Black:** Code formatting checks
- **isort:** Import sorting verification
- **Flake8:** Style guide enforcement (PEP 8)
- **Pylint:** Comprehensive linting
- **Bandit:** Security vulnerability scanning

**Fix Issues Locally:**
```bash
# Format code
black .

# Sort imports
isort .

# Check types
mypy .

# Run all checks
flake8 . && pylint . && bandit -r .
```

---

### 4. 📋 Kanban Board Sync (`kanban-sync.yml`)
**Triggers:** After pipeline workflow completion

Automatically updates Kanban board:
- Syncs card status based on pipeline results
- Commits updated board to repository
- Creates summary of completed cards

**Auto-commits:**
- Updates `.agents/agile/kanban_board.json`
- Commits with automated message

---

### 5. 🔀 Pull Request Automation (`pr-automation.yml`)
**Triggers:** PR opened, synchronized, reopened

Automates PR workflows:
- Validates PR description
- Links PRs to Kanban cards
- Shows file change summary
- Auto-labels based on file types
- Suggests review focus areas

**Auto-applied labels:**
- `python` - Python code changes
- `frontend` - HTML/CSS/JS changes
- `notebook` - Jupyter notebook changes
- `tests` - Test file changes
- `ci-cd` - Workflow changes

---

## Workflow Integration Flow

```
┌─────────────────┐
│  Push to Master │
│   or Create PR  │
└────────┬────────┘
         │
         ├──────────────────────────────────────┐
         │                                      │
         ▼                                      ▼
┌─────────────────┐                   ┌─────────────────┐
│  Code Quality   │                   │ Automated Tests │
│     Checks      │                   │   (Multi-Py)    │
└────────┬────────┘                   └────────┬────────┘
         │                                      │
         │              ┌──────────────────────┐│
         │              │                      ││
         ▼              ▼                      ▼▼
┌──────────────────────────────────────────────────┐
│            Agile/TDD Pipeline                    │
│  (Architecture → Validate → Arbitrate →          │
│   Integrate → Test)                              │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  Kanban Board Sync    │
         │  (Auto-update & Push) │
         └───────────────────────┘
```

---

## Setting Up Workflows

### Prerequisites

1. **GitHub Repository Settings:**
   - Enable GitHub Actions in repository settings
   - Grant workflow write permissions:
     - Settings → Actions → General → Workflow permissions
     - Select "Read and write permissions"

2. **Local Development:**
   ```bash
   # Install dependencies
   pip install pytest pytest-cov black isort flake8 pylint mypy bandit

   # Install GitHub CLI (optional, for manual triggers)
   # https://cli.github.com/
   ```

### Environment Variables

The workflows use these environment variables (automatically provided by GitHub):
- `GITHUB_TOKEN` - Authentication token
- `GITHUB_WORKSPACE` - Workspace directory
- `GITHUB_REF` - Branch/tag ref

No additional secrets required for basic operation.

---

## Monitoring Workflows

### Via GitHub UI
1. Go to repository → Actions tab
2. Select workflow from left sidebar
3. View runs, logs, and artifacts

### Via GitHub CLI
```bash
# List workflow runs
gh run list

# View specific run
gh run view <run-id>

# Watch run in real-time
gh run watch

# Download artifacts
gh run download <run-id>
```

---

## Customizing Workflows

### Modify Triggers
Edit the `on:` section in workflow files:

```yaml
on:
  push:
    branches: [ master, develop ]  # Add branches
    paths:
      - 'src/**'                   # Only trigger on src/ changes
  schedule:
    - cron: '0 0 * * *'            # Daily at midnight
```

### Add Notifications
Integrate Slack, Discord, or email notifications:

```yaml
- name: Notify on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Troubleshooting

### Workflow Fails on Push
1. Check workflow logs in Actions tab
2. Verify all required files exist (`.agents/agile/run_pipeline.sh`, etc.)
3. Ensure Python dependencies are correct

### Pipeline Doesn't Find Cards
- Check `.agents/agile/kanban_board.json` exists
- Verify cards have correct `column` status
- Review pipeline logs for card detection

### Kanban Sync Fails to Commit
- Verify workflow has write permissions
- Check for merge conflicts
- Ensure `kanban_board.json` is valid JSON

---

## Best Practices

1. **Commit often:** Workflows run on every push, providing fast feedback
2. **Link PRs to cards:** Include card IDs in PR titles/descriptions
3. **Review workflow logs:** Check Actions tab regularly for issues
4. **Run checks locally:** Use pre-commit hooks to catch issues before pushing
5. **Use manual triggers:** Test workflows with specific cards using workflow_dispatch

---

## Future Enhancements

- [ ] Add deployment workflows (staging/production)
- [ ] Integrate with Salesforce CI/CD
- [ ] Add performance benchmarking
- [ ] Create release automation
- [ ] Add security scanning (SAST/DAST)
- [ ] Integrate with project management tools (Jira, Asana)

---

## Support

For issues with workflows:
1. Check workflow logs in GitHub Actions
2. Review this README
3. Consult `.agents/agile/` documentation
4. Open an issue in the repository

---

**Last Updated:** 2025-10-21
**Maintained By:** Agile/TDD Pipeline Team
