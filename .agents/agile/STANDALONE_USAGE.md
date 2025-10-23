# Artemis Standalone Usage Guide

Artemis can now run completely standalone without requiring Claude Code! It uses OpenAI or Anthropic APIs directly to power the developer agents.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Ensure you have the required packages
pip install openai anthropic chromadb
```

### 2. Configure API Keys

Copy the example environment file and add your API keys:

```bash
cd .agents/agile
cp .env.example .env
```

Edit `.env` and add your API key:

```env
# For OpenAI (default)
ARTEMIS_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here

# OR for Anthropic
ARTEMIS_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Note**: You can also export environment variables directly:

```bash
export ARTEMIS_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-your-key-here
```

### 3. Create a Task Card

```bash
python3 kanban_manager.py create "Your task title" "Task description with all requirements" "high" 8
```

This will output a card ID like `card-20251022031615`.

### 4. Run Artemis Pipeline

```bash
python3 artemis_orchestrator_solid.py --card-id card-20251022031615 --full
```

Artemis will now:
1. 🔍 Analyze the project and requirements
2. 🏗️ Create an Architecture Decision Record (ADR)
3. ✅ Validate dependencies
4. 💻 **Invoke real LLM-powered developer agents** to write code
5. ✅ Validate TDD compliance
6. 🔗 Integrate the winning solution
7. 🧪 Run comprehensive tests

## 📋 How It Works

### LLM-Powered Developer Agents

Artemis now uses **real LLM APIs** instead of placeholders:

```
┌─────────────────────┐
│ Artemis Orchestrator│
└──────────┬──────────┘
           │
           ├──────────────────────┐
           │                      │
           ▼                      ▼
┌──────────────────┐   ┌──────────────────┐
│  Developer A     │   │  Developer B     │
│  (Conservative)  │   │  (Aggressive)    │
│                  │   │                  │
│  Uses LLM API    │   │  Uses LLM API    │
│  to write code   │   │  to write code   │
└──────────────────┘   └──────────────────┘
           │                      │
           │    Real Python code  │
           │    with tests        │
           │                      │
           └──────────┬───────────┘
                      ▼
            ┌──────────────────┐
            │   Arbitration    │
            │  Selects Winner  │
            └──────────────────┘
```

### Developer Agent Workflow

Each developer agent:

1. **Reads** developer prompt (developer_a_prompt.md or developer_b_prompt.md)
2. **Reads** the ADR with architectural guidance
3. **Calls LLM API** with full context
4. **Receives** complete code implementation from LLM
5. **Writes** implementation files to `/tmp/developer-a/` or `/tmp/developer-b/`
6. **Writes** test files following TDD
7. **Generates** solution report with SOLID principles

## 🎯 Supported LLM Providers

### OpenAI (Default)

```bash
export ARTEMIS_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-your-key-here
```

**Default Model**: `gpt-4o` (GPT-4 Optimized)

**Other Models**: `gpt-4o-mini`, `gpt-4-turbo`, `gpt-4`

### Anthropic

```bash
export ARTEMIS_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Default Model**: `claude-sonnet-4-5-20250929` (Claude Sonnet 4.5)

**Other Models**: `claude-sonnet-4-20250514`, `claude-3-5-sonnet-20241022`

### Specifying a Model

```bash
export ARTEMIS_LLM_MODEL=gpt-4o-mini  # Use cheaper/faster model
```

## 💰 Cost Considerations

Artemis makes LLM API calls for:
- Developer A implementation (~2000-8000 tokens)
- Developer B implementation (~2000-8000 tokens)

**Estimated Cost per Task**:
- **GPT-4o**: $0.05 - $0.20 per task
- **GPT-4o-mini**: $0.01 - $0.05 per task
- **Claude Sonnet 4.5**: $0.10 - $0.40 per task

**Tip**: Use `gpt-4o-mini` for development/testing to reduce costs.

## 📂 Output Structure

After execution, implementations are stored in:

```
/tmp/
├── developer-a/
│   ├── implementation.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── acceptance/
│   └── solution_report.json
│
├── developer-b/
│   └── (same structure)
│
└── adr/
    └── ADR-XXX-task-name.md
```

## 🔧 Advanced Configuration

### Custom RAG Database Path

```bash
export ARTEMIS_RAG_DB_PATH=/path/to/custom/rag_db
```

### Verbose Logging

```bash
export ARTEMIS_VERBOSE=true  # Default
```

### Using Different Models for Different Developers

Currently, both developers use the same provider/model. To use different models, you would need to modify `developer_invoker.py` to accept per-developer configuration.

## ✅ Verification

Test that Artemis is working standalone:

```bash
# Create test task
python3 kanban_manager.py create "Test standalone" "Create a simple hello world function" "low" 2

# Run pipeline (will use real LLM APIs)
python3 artemis_orchestrator_solid.py --card-id <card-id> --full

# Check output
ls -la /tmp/developer-a/
cat /tmp/developer-a/solution_report.json
```

If you see actual code files created, Artemis is running standalone successfully! 🎉

## 🐛 Troubleshooting

### Error: "OpenAI API key not provided"

**Solution**: Set the environment variable:

```bash
export OPENAI_API_KEY=sk-your-key-here
```

### Error: "openai library not installed"

**Solution**: Install the required library:

```bash
pip install openai
```

### Error: "Failed to parse implementation JSON"

**Cause**: LLM response didn't follow expected JSON format

**Solution**:
1. Check `/tmp/pipeline_full_report_<card-id>.json` for details
2. Try with a simpler task
3. Consider using a different model (GPT-4 vs GPT-4o-mini)

### Developer agents return mock data

**Cause**: Old version of `developer_invoker.py` with placeholders

**Solution**: Ensure you're using the updated version that imports `StandaloneDeveloperAgent`

## 📊 Monitoring

Monitor LLM usage in solution reports:

```bash
cat /tmp/developer-a/solution_report.json | jq '.tokens_used'
```

Output:
```json
{
  "prompt_tokens": 2500,
  "completion_tokens": 5000,
  "total_tokens": 7500
}
```

## 🎓 Best Practices

1. **Start Small**: Test with simple tasks before complex ones
2. **Use Cheaper Models for Testing**: `gpt-4o-mini` for development
3. **Monitor Token Usage**: Check solution reports for costs
4. **Provide Clear Task Descriptions**: Better descriptions = better code
5. **Review ADRs**: Architecture decisions guide developer implementations

## 🚀 Next Steps

Now that Artemis is standalone, you can:

1. **Integrate into CI/CD**: Run Artemis in your build pipeline
2. **Batch Processing**: Process multiple cards sequentially
3. **Custom Workflows**: Modify stages for your specific needs
4. **Deploy as Service**: Wrap Artemis in a REST API

## 📖 Additional Resources

- **LLM Client**: `llm_client.py` - Unified LLM interface
- **Developer Agent**: `standalone_developer_agent.py` - LLM-powered implementation
- **Developer Invoker**: `developer_invoker.py` - Orchestrates developer agents
- **Orchestrator**: `artemis_orchestrator_solid.py` - Main pipeline controller

---

**Status**: ✅ Artemis is now fully standalone!

**Version**: 2.0 (Standalone)

**Last Updated**: October 22, 2025
