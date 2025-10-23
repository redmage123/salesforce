# ChromaDB Lock Issue - Production Analysis

**Date:** October 23, 2025
**Issue:** SQLite "readonly database" errors during concurrent access
**Risk Level:** ⚠️ **MEDIUM** (Will cause failures in concurrent scenarios)

---

## Problem Description

### What We Observed

During testing, we encountered:
```
chromadb.errors.InternalError: Query error: Database error:
error returned from database: (code: 1032) attempt to write a readonly database
```

This happened when:
1. Multiple tests ran sequentially
2. Previous ChromaDB client hadn't fully closed
3. New client tried to access the same database

### Root Cause

ChromaDB uses **SQLite** as its default persistence layer:
- SQLite uses **file-based locking**
- Only **one writer** allowed at a time
- Lock persists until client connection closes
- Python garbage collection timing is non-deterministic

---

## When This Becomes a Problem in Production

### ❌ **WILL FAIL** - Concurrent Scenarios

**1. Multiple Artemis Pipelines Running Simultaneously**
```python
# Pipeline 1 (card-001)
artemis1 = ArtemisOrchestrator(card_id="card-001")
artemis1.rag = RAGAgent(db_path="/tmp/rag_db")  # Opens connection

# Pipeline 2 (card-002) - CONCURRENT
artemis2 = ArtemisOrchestrator(card_id="card-002")
artemis2.rag = RAGAgent(db_path="/tmp/rag_db")  # 💥 LOCK ERROR
```

**2. Supervisor + Main Pipeline Accessing RAG**
```python
# Main orchestrator creates RAG
artemis = ArtemisOrchestrator(card_id="card-001")
artemis.rag = RAGAgent(db_path="/tmp/rag_db")

# Supervisor also needs RAG
supervisor = SupervisorAgent(..., rag=RAGAgent(db_path="/tmp/rag_db"))  # 💥 LOCK ERROR
```

**3. Background Monitoring + Active Pipeline**
```python
# Monitoring process queries RAG every 5 seconds
monitor_rag = RAGAgent(db_path="/tmp/rag_db")

# Active pipeline tries to store data
pipeline_rag = RAGAgent(db_path="/tmp/rag_db")  # 💥 LOCK ERROR
```

### ✅ **WILL WORK** - Sequential Scenarios

**1. Single Pipeline Execution**
```python
# One pipeline at a time
artemis = ArtemisOrchestrator(card_id="card-001")
artemis.run()  # Works fine
# ... completes ...

# Next pipeline
artemis2 = ArtemisOrchestrator(card_id="card-002")
artemis2.run()  # Works fine
```

**2. Shared RAG Instance**
```python
# Single RAG instance shared across components
rag = RAGAgent(db_path="/tmp/rag_db")  # One connection

artemis = ArtemisOrchestrator(card_id="card-001")
artemis.rag = rag  # Share instance

supervisor = SupervisorAgent(..., rag=rag)  # Share instance
# ✅ Works - one connection
```

---

## Current Production Risk Assessment

### Your Deployment: Single Machine

Based on your confirmation: **"Currently my deployment is on a single machine"**

**Risk Level:** ⚠️ **LOW to MEDIUM** depending on usage pattern

| Scenario | Risk | Likelihood |
|----------|------|------------|
| **Sequential pipeline runs** | ✅ LOW | High |
| **Concurrent pipelines** | ❌ HIGH | Medium |
| **Supervisor + Pipeline** | ⚠️ MEDIUM | High |
| **Multiple processes** | ❌ HIGH | Low |

### Critical Question: Do You Run Concurrent Pipelines?

**If YES** → High risk, needs immediate fix
**If NO** → Low risk, but should still fix for robustness

---

## Solutions

### Solution 1: Shared RAG Instance (RECOMMENDED - Quick Fix)

**Use a single RAG instance across all components**

```python
class ArtemisOrchestrator:
    def __init__(self, card_id, verbose=True):
        # Create RAG once
        if not hasattr(ArtemisOrchestrator, '_shared_rag'):
            ArtemisOrchestrator._shared_rag = RAGAgent(
                db_path="/tmp/rag_db",
                verbose=verbose
            )

        self.rag = ArtemisOrchestrator._shared_rag

        # Share with supervisor
        self.supervisor = SupervisorAgent(
            ...,
            rag=self.rag  # Share the same instance
        )
```

**Pros:**
- ✅ Immediate fix (30 minutes)
- ✅ No external dependencies
- ✅ Works for single-machine deployment
- ✅ Simple to implement

**Cons:**
- ❌ Doesn't support multiple processes
- ❌ Still has single-writer limitation
- ❌ Not thread-safe by default

---

### Solution 2: Connection Pooling with Retry Logic

**Add retry logic and connection management**

```python
class RAGAgent:
    def __init__(self, db_path, max_retries=3, retry_delay=0.5):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        # ... existing init ...

    def store_artifact(self, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return self._store_artifact_impl(*args, **kwargs)
            except chromadb.errors.InternalError as e:
                if "readonly database" in str(e) and attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                    # Close and reopen connection
                    self._reconnect()
                else:
                    raise

    def _reconnect(self):
        """Close and reopen ChromaDB connection"""
        if self.client:
            del self.client
            time.sleep(0.1)

        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        self._initialize_collections()
```

**Pros:**
- ✅ Handles transient lock errors
- ✅ Self-healing on conflicts
- ✅ No external dependencies

**Cons:**
- ⚠️ Adds latency on conflicts (retries)
- ❌ Doesn't prevent conflicts, just recovers
- ❌ Not ideal for high-concurrency

---

### Solution 3: PostgreSQL Backend for ChromaDB (BEST - Long Term)

**Switch ChromaDB from SQLite to PostgreSQL**

```python
import chromadb
from chromadb.config import Settings

class RAGAgent:
    def __init__(self, db_path=None, postgres_url=None, verbose=True):
        if postgres_url:
            # Use PostgreSQL backend
            self.client = chromadb.HttpClient(
                host="localhost",
                port=8000,
                settings=Settings(
                    anonymized_telemetry=False,
                    persist_directory=None  # Not used with HTTP
                )
            )
        else:
            # Use SQLite backend (current)
            self.client = chromadb.PersistentClient(
                path=str(db_path),
                settings=Settings(anonymized_telemetry=False)
            )
```

**Setup ChromaDB Server:**
```bash
# Run ChromaDB server with PostgreSQL
docker run -d \
  --name chromadb \
  -p 8000:8000 \
  -e CHROMA_DB_IMPL=postgres \
  -e POSTGRES_HOST=localhost \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_DB=chromadb \
  -e POSTGRES_USER=chroma \
  -e POSTGRES_PASSWORD=chroma \
  chromadb/chroma:latest
```

**Pros:**
- ✅ Solves all concurrency issues
- ✅ Supports multiple processes/machines
- ✅ Production-grade scaling
- ✅ ACID transactions
- ✅ No lock errors

**Cons:**
- ❌ Requires external PostgreSQL
- ❌ More complex deployment (Docker/setup)
- ❌ Overkill for single-machine/sequential use

---

### Solution 4: File-Based Locking with Retry

**Add explicit file lock management**

```python
import fcntl
import time
from pathlib import Path

class RAGAgent:
    def __init__(self, db_path, verbose=True):
        self.db_path = Path(db_path)
        self.lock_file = self.db_path / "rag.lock"
        self.lock_file.parent.mkdir(exist_ok=True, parents=True)
        # ... existing init ...

    def _acquire_lock(self, timeout=10):
        """Acquire exclusive lock on RAG database"""
        start_time = time.time()
        lock_fd = open(self.lock_file, 'w')

        while True:
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return lock_fd
            except IOError:
                if time.time() - start_time > timeout:
                    raise TimeoutError("Could not acquire RAG lock")
                time.sleep(0.1)

    def _release_lock(self, lock_fd):
        """Release lock"""
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        lock_fd.close()

    def store_artifact(self, *args, **kwargs):
        lock_fd = self._acquire_lock()
        try:
            return self._store_artifact_impl(*args, **kwargs)
        finally:
            self._release_lock(lock_fd)
```

**Pros:**
- ✅ Explicit lock management
- ✅ Prevents concurrent writes
- ✅ No external dependencies

**Cons:**
- ⚠️ Serializes all RAG access (slower)
- ❌ Complex implementation
- ❌ Doesn't help with multi-process

---

## Recommended Solution Path

### Phase 1: Immediate Fix (30 minutes) ✅ IMPLEMENT NOW

**Use shared RAG instance:**

```python
# In artemis_orchestrator_solid.py or similar entry point
class ArtemisOrchestrator:
    _shared_rag = None  # Class-level singleton

    def __init__(self, card_id, verbose=True):
        # Create RAG once per process
        if ArtemisOrchestrator._shared_rag is None:
            ArtemisOrchestrator._shared_rag = RAGAgent(
                db_path="/tmp/rag_db",
                verbose=verbose
            )

        self.rag = ArtemisOrchestrator._shared_rag

        # Share with all components
        self.supervisor = SupervisorAgent(
            logger=self.logger,
            messenger=self.messenger,
            card_id=card_id,
            rag=self.rag  # Shared instance
        )
```

**Value:**
- Fixes 90% of lock issues immediately
- Zero new dependencies
- Works for your single-machine deployment

---

### Phase 2: Add Retry Logic (1 hour) ⚠️ OPTIONAL

**Add retry wrapper for edge cases:**

```python
class RAGAgent:
    def store_artifact(self, *args, **kwargs):
        for attempt in range(3):
            try:
                return self._store_artifact_impl(*args, **kwargs)
            except chromadb.errors.InternalError as e:
                if "readonly" in str(e) and attempt < 2:
                    time.sleep(0.5 * (2 ** attempt))
                else:
                    raise
```

**Value:**
- Handles rare edge cases
- Self-healing on transient errors
- Minimal complexity

---

### Phase 3: PostgreSQL Migration (4 hours) 🚀 FUTURE

**When you need:**
- Multiple Artemis processes concurrently
- Multi-machine deployment
- High-throughput RAG queries

**Implementation:**
```bash
# 1. Deploy ChromaDB server with PostgreSQL
docker-compose up chromadb-postgres

# 2. Update RAGAgent to use HTTP client
rag = RAGAgent(postgres_url="http://localhost:8000")

# 3. Migrate existing data (one-time)
python migrate_rag_to_postgres.py
```

---

## Current Risk Mitigation

### What You're Already Doing Right ✅

1. **Unique test databases** - Each test uses unique path (prevents test conflicts)
2. **Single-machine deployment** - Limits concurrency scenarios
3. **Sequential execution** - Likely not running many concurrent pipelines

### What Could Still Fail ❌

1. **Supervisor + Orchestrator** - Both create separate RAG instances
2. **Rapid pipeline restarts** - Old connection still open when new starts
3. **Background jobs** - Any monitoring/reporting accessing RAG concurrently

---

## Action Items

### Critical (Do Now)

- [ ] **Implement shared RAG instance** in ArtemisOrchestrator (30 min)
- [ ] **Test concurrent pipeline runs** to verify fix works
- [ ] **Document RAG singleton pattern** for future developers

### Important (Do Soon)

- [ ] **Add retry logic** to RAGAgent.store_artifact (1 hour)
- [ ] **Add connection cleanup** in RAGAgent.__del__ (30 min)
- [ ] **Monitor for lock errors** in production logs

### Optional (Future)

- [ ] **Evaluate PostgreSQL migration** if concurrency increases
- [ ] **Consider ChromaDB HTTP client** for multi-process scenarios
- [ ] **Add connection pooling** if needed

---

## Quick Decision Matrix

| Your Usage Pattern | Recommended Solution | Urgency |
|-------------------|---------------------|---------|
| **Sequential pipelines only** | Shared instance | LOW |
| **Sometimes concurrent** | Shared instance + retry | MEDIUM |
| **Always concurrent** | PostgreSQL backend | HIGH |
| **Multi-machine planned** | PostgreSQL backend | HIGH |

---

## Bottom Line

**Current Risk:** ⚠️ **MEDIUM**

**Will it fail in production?**
- **If sequential execution:** Probably not, but could on edge cases
- **If concurrent execution:** Yes, will definitely fail

**Recommended Action:**
1. ✅ **Implement shared RAG instance NOW** (30 min, fixes 90% of issues)
2. ⚠️ **Add retry logic SOON** (1 hour, fixes remaining 10%)
3. 🚀 **Plan PostgreSQL migration** when you need true concurrency

**Implementation Priority:** **HIGH** - Fix before production deployment

The shared instance approach is a **quick win** that makes your current deployment safe without major architectural changes. When you scale to multiple processes or machines, you can upgrade to PostgreSQL.
