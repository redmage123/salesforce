# Hugging Face Setup Guide

## Authentication Required

The datasets (The Stack, GitHub Code 2025, BigCodeReward) require Hugging Face authentication and acceptance of dataset terms.

---

## Setup Steps

### 1. Create Hugging Face Account

Visit: https://huggingface.co/join

Create a free account (takes 2 minutes).

---

### 2. Accept Dataset Terms

Visit each dataset page and click "Access repository":

1. **The Stack:** https://huggingface.co/datasets/bigcode/the-stack
   - Click "Access repository"
   - Accept the terms of use
   - Agree to keep your local copy updated

2. **GitHub Code 2025:** https://huggingface.co/datasets/nick007x/github-code-2025
   - Click "Access repository"
   - Accept any terms if prompted

3. **BigCodeReward:** https://huggingface.co/datasets/bigcode/bigcodereward
   - Click "Access repository"
   - Accept any terms if prompted

---

### 3. Get Access Token

1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Name: "artemis-code-examples"
4. Type: **Read** (default)
5. Click "Generate"
6. Copy the token (starts with `hf_...`)

---

### 4. Configure Token

**Option A: Environment Variable (Recommended)**

```bash
# Add to ~/.bashrc or ~/.zshrc
export HF_TOKEN="hf_your_token_here"

# Or set for current session only
export HF_TOKEN="hf_your_token_here"
```

**Option B: Login via CLI**

```bash
# Install huggingface-cli (if not already installed)
pip install huggingface-hub

# Login
huggingface-cli login
# Paste your token when prompted
```

**Option C: Python Code**

```python
from huggingface_hub import login

login(token="hf_your_token_here")
```

---

### 5. Test Access

```bash
# Test import (should work now)
python import_huggingface_examples.py --test --dataset the-stack --language Python --max 10
```

Expected output:
```
🧪 TEST MODE: Importing only 10 examples
🚀 Starting import from the-stack
📥 Streaming from The Stack (Python)...
Importing examples: 100%|███████████████| 10/10
✅ Successfully imported 10 examples
```

---

## Alternative: Use Public Datasets

If you don't want to authenticate, we can use public datasets instead:

### CodeSearchNet (Public, No Auth Required)

```bash
python -c "from datasets import load_dataset; \
           ds = load_dataset('code_search_net', 'python', split='train', streaming=True); \
           print(next(iter(ds)))"
```

### Stack Overflow (Public, No Auth Required)

```bash
python -c "from datasets import load_dataset; \
           ds = load_dataset('koutch/stackoverflow_python', split='train', streaming=True); \
           print(next(iter(ds)))"
```

---

## Quick Start After Authentication

### Test with Small Batch (Streaming, No Download)

```bash
# Test The Stack (Python)
python import_huggingface_examples.py \
    --test \
    --dataset the-stack \
    --language Python \
    --max 10
```

### Import 50 Examples (Still Streaming)

```bash
# Import 50 Python examples from The Stack
python import_huggingface_examples.py \
    --dataset the-stack \
    --language Python \
    --max 50 \
    --populate-rag
```

### Download BigCodeReward (~10GB)

```bash
# Download and import BigCodeReward
python import_huggingface_examples.py \
    --dataset bigcodereward \
    --max 100 \
    --populate-rag \
    --populate-kg
```

### Download GitHub Code 2025 (~100GB)

```bash
# Download high-quality subset
python import_huggingface_examples.py \
    --dataset github-2025 \
    --quality-only \
    --max 500 \
    --populate-rag \
    --populate-kg
```

---

## Troubleshooting

### Error: "401 Unauthorized"

**Problem:** Not authenticated or haven't accepted dataset terms.

**Solution:**
1. Make sure you've accepted terms on dataset page
2. Set HF_TOKEN environment variable
3. Or run `huggingface-cli login`

### Error: "Connection timeout"

**Problem:** Slow internet or dataset temporarily unavailable.

**Solution:**
1. Use streaming mode (--max with smaller number)
2. Try again later
3. Check HuggingFace status: https://status.huggingface.co/

### Error: "Out of memory"

**Problem:** Trying to download large dataset without streaming.

**Solution:**
1. Always use streaming for large datasets (The Stack, GitHub Code)
2. Only download small datasets fully (BigCodeReward ~10GB)
3. Use --max to limit examples

---

## Recommended Workflow

### Day 1: Setup and Test

```bash
# 1. Set up authentication
export HF_TOKEN="hf_your_token_here"

# 2. Accept dataset terms (visit websites)

# 3. Test with 10 examples (streaming)
python import_huggingface_examples.py --test --dataset the-stack --language Python
```

### Day 2: Import Small Batch

```bash
# Import 100 Python examples (streaming, ~5 minutes)
python import_huggingface_examples.py \
    --dataset the-stack \
    --language Python \
    --max 100 \
    --populate-rag
```

### Day 3: Download BigCodeReward

```bash
# Download BigCodeReward (~10GB, ~30 minutes)
python import_huggingface_examples.py \
    --dataset bigcodereward \
    --max 200 \
    --populate-rag \
    --populate-kg
```

### Day 4+: Optionally Download GitHub 2025

```bash
# Download GitHub Code 2025 high-quality subset
# (~100GB, 2-4 hours depending on connection)
python import_huggingface_examples.py \
    --dataset github-2025 \
    --quality-only \
    --max 1000 \
    --populate-rag
```

---

## Storage Planning

| Action | Storage Used | Time | Examples |
|--------|--------------|------|----------|
| **Test (streaming)** | ~0 MB | ~1 min | 10 |
| **100 examples (streaming)** | ~0 MB | ~5 min | 100 |
| **BigCodeReward download** | ~10 GB | ~30 min | 200+ |
| **GitHub 2025 download** | ~100 GB | ~2-4 hours | 1000+ |

**Recommendation:** Start with streaming (0 storage), then download BigCodeReward (~10GB) if you like it.

---

## Status Check

After importing, check what you have:

```bash
# Count examples in RAG
python -c "
from rag_agent import RAGAgent
rag = RAGAgent()
collections = rag._chroma_client.list_collections()
for col in collections:
    print(f'{col.name}: {col.count()} examples')
"
```

Expected output:
```
code_examples_python: 111 examples  # 2 curated + 100 from HF + 9 from HF
code_examples_rust: 1 examples
...
```

---

## Next Steps After Setup

Once authenticated and tested:

1. ✅ Import 100-200 examples per language (streaming)
2. ✅ Test RAG retrieval with developer agents
3. ✅ Optionally download BigCodeReward (~10GB)
4. ✅ Optionally download GitHub Code 2025 (~100GB)
5. ✅ Measure code quality improvements

---

**Need Help?**
- Hugging Face Docs: https://huggingface.co/docs/datasets
- Hugging Face Forum: https://discuss.huggingface.co/
- Dataset Issues: Report on dataset pages
