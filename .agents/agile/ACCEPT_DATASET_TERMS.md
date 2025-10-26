# Accept Dataset Terms - Required Action

## You Need To Click "Access Repository" on Each Dataset

Your token is saved (`HF_TOKEN=hf_GuME...`), but you must **manually accept terms** on the Hugging Face website.

---

## Required Actions (5 minutes total)

### 1. The Stack Dataset

**Visit:** https://huggingface.co/datasets/bigcode/the-stack

**Steps:**
1. Log in to HuggingFace (if not already)
2. Click the button: **"Access repository"**
3. Read and accept the terms
4. Confirm

### 2. GitHub Code 2025 Dataset

**Visit:** https://huggingface.co/datasets/nick007x/github-code-2025

**Steps:**
1. Click **"Access repository"** (if shown)
2. Accept any terms

### 3. BigCodeReward Dataset

**Visit:** https://huggingface.co/datasets/bigcode/bigcodereward

**Steps:**
1. Click **"Access repository"** (if shown)
2. Accept any terms

---

## After Accepting Terms

Wait ~2-5 minutes for permissions to propagate, then test:

```bash
cd /home/bbrelin/src/repos/salesforce/.agents/agile

export HF_TOKEN=your_token_here

python import_huggingface_examples.py \
    --test \
    --dataset the-stack \
    --language Python \
    --max 10
```

**Expected output:**
```
🧪 TEST MODE: Importing only 10 examples
📥 Streaming from The Stack (Python)...
Importing examples: 100%|███████| 10/10
✅ Successfully imported 10 examples
```

---

## Alternative: Test with Public Dataset (No Terms Required)

While waiting for permissions, test with a public dataset:

```bash
# Test with CodeSearchNet (public, no terms)
python -c "
from datasets import load_dataset
import os
os.environ['HF_TOKEN'] = 'your_hf_token_here'

ds = load_dataset('code_search_net', 'python', split='train', streaming=True)
print('✅ Successfully connected to public dataset!')
example = next(iter(ds))
print(f'Example code: {example[\"func_code_string\"][:100]}...')
"
```

---

## Status Check

Run this to see if you have access:

```bash
python -c "
from huggingface_hub import HfApi
import os

os.environ['HF_TOKEN'] = 'your_hf_token_here'
api = HfApi(token=os.environ['HF_TOKEN'])

datasets_to_check = [
    'bigcode/the-stack',
    'nick007x/github-code-2025',
    'bigcode/bigcodereward'
]

for dataset in datasets_to_check:
    try:
        info = api.dataset_info(dataset)
        print(f'✅ {dataset}: Access granted')
    except Exception as e:
        if 'gated' in str(e):
            print(f'❌ {dataset}: Need to accept terms at https://huggingface.co/datasets/{dataset}')
        else:
            print(f'⚠️  {dataset}: {str(e)[:50]}...')
"
```

---

## Once You Have Access

Then run the full import:

```bash
# Import 50 Python examples (streaming, 0 storage)
export HF_TOKEN=your_token_here

python import_huggingface_examples.py \
    --dataset the-stack \
    --language Python \
    --max 50 \
    --populate-rag \
    --populate-kg
```

---

**Let me know when you've clicked "Access repository" on the datasets!**
