# Hydra Configuration for Logging and Output Storage

**Date:** 2025-10-23
**Status:** ✅ COMPLETE

---

## Overview

Artemis now uses Hydra for centralized, hierarchical configuration management. This includes:

1. **Logging Configuration** - Control where logs go, rotation, verbosity
2. **Output Storage Configuration** - Choose between local or remote storage for pipeline outputs

---

## Configuration Structure

```
conf/
├── config.yaml              # Main configuration file
├── logging/                 # Logging configuration group
│   ├── dev.yaml            # Development (DEBUG, /tmp)
│   ├── prod.yaml           # Production (INFO, /var/log/artemis)
│   ├── debug.yaml          # Maximum verbosity
│   └── quiet.yaml          # Errors only
├── output/                  # Output storage configuration group
│   ├── local.yaml          # Local filesystem storage
│   ├── s3.yaml             # AWS S3 storage
│   ├── gcs.yaml            # Google Cloud Storage
│   └── azure.yaml          # Azure Blob Storage
└── ...
```

---

## 1. Logging Configuration

### Available Profiles

**Production (default)**
```bash
python artemis_orchestrator.py card_id=card-001
# Uses logging=prod (INFO level, /var/log/artemis)
```

**Development**
```bash
python artemis_orchestrator.py card_id=card-001 logging=dev
# Uses DEBUG level, logs to /tmp/artemis_logs
```

**Debug Mode**
```bash
python artemis_orchestrator.py card_id=card-001 logging=debug
# Maximum verbosity for troubleshooting
```

**Quiet Mode**
```bash
python artemis_orchestrator.py card_id=card-001 logging=quiet
# Errors and critical only
```

### Override Specific Logging Settings

```bash
# Change log directory
python artemis_orchestrator.py card_id=card-001 logging.log_dir=/custom/log/path

# Change log level
python artemis_orchestrator.py card_id=card-001 logging.log_level=DEBUG

# Change rotation settings
python artemis_orchestrator.py card_id=card-001 logging.max_size_mb=200 logging.backup_count=20

# Combine overrides
python artemis_orchestrator.py card_id=card-001 logging=prod logging.log_level=DEBUG
```

### Environment Variable Overrides

Logging configuration reads from environment variables:

```bash
export ARTEMIS_LOG_DIR=/var/log/artemis
export ARTEMIS_LOG_LEVEL=INFO
export ARTEMIS_LOG_MAX_SIZE_MB=100
export ARTEMIS_LOG_BACKUP_COUNT=10

python artemis_orchestrator.py card_id=card-001
# Uses environment variables
```

### Logging Configuration Schema

```yaml
logging:
  verbose: true              # Enable verbose output
  log_level: INFO           # DEBUG, INFO, WARNING, ERROR, CRITICAL
  log_dir: /var/log/artemis # Log directory path
  max_size_mb: 100          # Max log file size before rotation
  backup_count: 10          # Number of rotated logs to keep
```

### Log Files Created

When using `/var/log/artemis`:

```
/var/log/artemis/
├── artemis_main.log          # Main pipeline execution
├── artemis_supervisor.log    # Supervisor agent logs
├── artemis_developers.log    # Developer agent logs
├── artemis_errors.log         # Error-only log for monitoring
├── artemis_main.log.1         # Rotated logs
├── artemis_main.log.2
└── ...
```

---

## 2. Output Storage Configuration

### Available Backends

**Local Storage (default)**
```bash
python artemis_orchestrator.py card_id=card-001
# Uses output=local (../../outputs directory)
```

**AWS S3**
```bash
python artemis_orchestrator.py card_id=card-001 output=s3
# Requires: ARTEMIS_S3_BUCKET, AWS credentials
```

**Google Cloud Storage**
```bash
python artemis_orchestrator.py card_id=card-001 output=gcs
# Requires: ARTEMIS_GCS_BUCKET, ARTEMIS_GCS_PROJECT, GCS credentials
```

**Azure Blob Storage**
```bash
python artemis_orchestrator.py card_id=card-001 output=azure
# Requires: ARTEMIS_AZURE_CONTAINER, ARTEMIS_AZURE_STORAGE_ACCOUNT, Azure credentials
```

### Override Specific Storage Settings

```bash
# Change local storage path
python artemis_orchestrator.py card_id=card-001 output.local_path=/custom/output/path

# Override S3 bucket
python artemis_orchestrator.py card_id=card-001 output=s3 output.remote.s3.bucket=my-bucket

# Override GCS project
python artemis_orchestrator.py card_id=card-001 output=gcs output.remote.gcs.project=my-project
```

### Environment Variable Overrides

Output storage reads from environment variables:

```bash
# Local storage
export ARTEMIS_OUTPUT_STORAGE=local
export ARTEMIS_OUTPUT_PATH=../../outputs

# S3 storage
export ARTEMIS_OUTPUT_STORAGE=remote
export ARTEMIS_REMOTE_STORAGE_PROVIDER=s3
export ARTEMIS_S3_BUCKET=my-artemis-bucket
export ARTEMIS_S3_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret

# GCS storage
export ARTEMIS_OUTPUT_STORAGE=remote
export ARTEMIS_REMOTE_STORAGE_PROVIDER=gcs
export ARTEMIS_GCS_BUCKET=my-artemis-bucket
export ARTEMIS_GCS_PROJECT=my-gcp-project
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

python artemis_orchestrator.py card_id=card-001
# Uses environment variables
```

### Output Storage Schema

```yaml
output:
  storage_type: local        # "local" or "remote"
  local_path: ../../outputs  # Local storage directory
  remote:
    provider: s3             # "s3", "gcs", or "azure"
    s3:
      bucket: my-bucket
      region: us-east-1
    gcs:
      bucket: my-bucket
      project: my-project
    azure:
      container: my-container
      storage_account: my-account
```

### Output Directory Structure

Local storage creates this structure:

```
outputs/
├── adrs/
│   └── card-001/
│       └── ADR-001.md
├── developers/
│   └── card-001/
│       ├── developer-a/
│       │   └── solution.py
│       └── developer-b/
│           └── solution.py
├── tests/
│   └── card-001/
│       └── unit_20251023_120000.json
└── reports/
    └── card-001/
        └── pipeline_20251023_120000.json
```

Remote storage (S3/GCS/Azure) uses the same structure but with cloud URIs.

---

## 3. Complete Examples

### Development Environment

```bash
# Local storage, DEBUG logging to /tmp
python artemis_orchestrator.py \
  card_id=card-dev-001 \
  logging=dev \
  output=local
```

### Production Environment

```bash
# S3 storage, INFO logging to /var/log/artemis
python artemis_orchestrator.py \
  card_id=card-prod-001 \
  logging=prod \
  output=s3
```

### Troubleshooting Run

```bash
# Local storage, maximum DEBUG logging
python artemis_orchestrator.py \
  card_id=card-debug-001 \
  logging=debug \
  output=local \
  logging.log_dir=/tmp/artemis_debug
```

### Custom Configuration Mix

```bash
# Production logging, local storage, custom log level
python artemis_orchestrator.py \
  card_id=card-custom-001 \
  logging=prod \
  logging.log_level=DEBUG \
  output=local \
  output.local_path=/custom/path
```

---

## 4. Configuration Priority

Hydra resolves configuration in this order (highest priority first):

1. **CLI overrides** - `logging.log_level=DEBUG`
2. **Environment variables** - `ARTEMIS_LOG_LEVEL=INFO`
3. **Config group selection** - `logging=dev`
4. **Base config.yaml** - Default values

Example:
```bash
export ARTEMIS_LOG_LEVEL=INFO  # Priority 2

python artemis_orchestrator.py \
  card_id=card-001 \
  logging=prod \              # Priority 3 (sets log_level=INFO)
  logging.log_level=DEBUG     # Priority 1 (overrides to DEBUG)

# Final: log_level=DEBUG (CLI override wins)
```

---

## 5. Accessing Configuration in Code

### Using Hydra in Python

```python
from omegaconf import DictConfig
import hydra

@hydra.main(config_path="conf", config_name="config", version_base=None)
def main(cfg: DictConfig):
    # Access logging config
    log_dir = cfg.logging.log_dir
    log_level = cfg.logging.log_level

    # Access output storage config
    storage_type = cfg.output.storage_type
    local_path = cfg.output.local_path

    # Access remote storage config
    if cfg.output.storage_type == "remote":
        provider = cfg.output.remote.provider
        if provider == "s3":
            bucket = cfg.output.remote.s3.bucket
            region = cfg.output.remote.s3.region

    print(f"Logging to: {log_dir} at level {log_level}")
    print(f"Storage type: {storage_type}")

if __name__ == "__main__":
    main()
```

### Using ArtemisLogger

```python
from artemis_logger import get_logger
from omegaconf import DictConfig
import hydra

@hydra.main(config_path="conf", config_name="config", version_base=None)
def main(cfg: DictConfig):
    # Create logger with Hydra config
    logger = get_logger(component="main")

    # Logger automatically reads from environment or uses defaults
    logger.info("Pipeline started")
    logger.debug("Debug information")
    logger.error("Error occurred")

if __name__ == "__main__":
    main()
```

### Using OutputStorageManager

```python
from output_storage import get_storage
from omegaconf import DictConfig
import hydra

@hydra.main(config_path="conf", config_name="config", version_base=None)
def main(cfg: DictConfig):
    # Get storage manager (reads from environment)
    storage = get_storage()

    # Write outputs
    adr_path = storage.write_adr(
        card_id=cfg.card_id,
        adr_number="001",
        content="# ADR Content"
    )

    print(f"ADR written to: {adr_path}")

    # Get storage info
    info = storage.get_storage_info()
    print(f"Using {info['type']} storage: {info['backend']}")

if __name__ == "__main__":
    main()
```

---

## 6. Environment Variable Reference

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `ARTEMIS_LOG_DIR` | `/var/log/artemis` | Directory for log files |
| `ARTEMIS_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `ARTEMIS_LOG_MAX_SIZE_MB` | `100` | Max log file size before rotation (MB) |
| `ARTEMIS_LOG_BACKUP_COUNT` | `10` | Number of rotated logs to keep |

### Output Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `ARTEMIS_OUTPUT_STORAGE` | `local` | Storage type (local or remote) |
| `ARTEMIS_OUTPUT_PATH` | `../../outputs` | Local storage directory |
| `ARTEMIS_REMOTE_STORAGE_PROVIDER` | `s3` | Remote provider (s3, gcs, azure) |

### S3 Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `ARTEMIS_S3_BUCKET` | - | S3 bucket name (required) |
| `ARTEMIS_S3_REGION` | `us-east-1` | AWS region |
| `AWS_ACCESS_KEY_ID` | - | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | - | AWS secret key |

### GCS Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `ARTEMIS_GCS_BUCKET` | - | GCS bucket name (required) |
| `ARTEMIS_GCS_PROJECT` | - | GCP project ID (required) |
| `GOOGLE_APPLICATION_CREDENTIALS` | - | Path to service account JSON |

### Azure Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `ARTEMIS_AZURE_CONTAINER` | - | Azure container name (required) |
| `ARTEMIS_AZURE_STORAGE_ACCOUNT` | - | Azure storage account (required) |
| `AZURE_STORAGE_CONNECTION_STRING` | - | Azure connection string |

---

## 7. Migration from .env_artemis

If you have an existing `.env_artemis` file:

1. **Copy it to .env**
   ```bash
   cp .env_artemis .env
   ```

2. **Source it before running Artemis**
   ```bash
   source .env
   python artemis_orchestrator.py card_id=card-001
   ```

3. **Or use direnv** (recommended)
   ```bash
   # Install direnv
   sudo apt install direnv

   # Create .envrc
   echo "source .env" > .envrc
   direnv allow

   # Now environment variables load automatically
   python artemis_orchestrator.py card_id=card-001
   ```

---

## 8. Testing Configuration

### Test Logging Configuration

```bash
# Test logger standalone
python3 artemis_logger.py

# Expected output:
# [INFO] Testing Artemis logger
# [WARNING] This is a warning
# [ERROR] This is an error
# Log file: /var/log/artemis/artemis_test.log
# Error log: /var/log/artemis/artemis_errors.log
```

### Test Output Storage Configuration

```bash
# Test storage manager standalone
python3 output_storage.py

# Expected output:
# Storage Info: {'type': 'local', 'backend': 'LocalStorageBackend', 'base_path': '/path/to/outputs'}
# Wrote test file: /path/to/outputs/adrs/test-card-001/ADR-001.md
```

### Test Full Hydra Configuration

Create `test_hydra_logging_storage.py`:

```python
#!/usr/bin/env python3
from omegaconf import DictConfig, OmegaConf
import hydra

@hydra.main(config_path="conf", config_name="config", version_base=None)
def test_config(cfg: DictConfig):
    print("=" * 60)
    print("Hydra Configuration Test")
    print("=" * 60)

    print("\n📝 Logging Configuration:")
    print(f"  Log Directory: {cfg.logging.log_dir}")
    print(f"  Log Level: {cfg.logging.log_level}")
    print(f"  Max Size: {cfg.logging.max_size_mb} MB")
    print(f"  Backup Count: {cfg.logging.backup_count}")
    print(f"  Verbose: {cfg.logging.verbose}")

    print("\n💾 Output Storage Configuration:")
    print(f"  Storage Type: {cfg.output.storage_type}")
    print(f"  Local Path: {cfg.output.local_path}")
    print(f"  Remote Provider: {cfg.output.remote.provider}")

    if cfg.output.storage_type == "remote":
        provider = cfg.output.remote.provider
        print(f"\n☁️  Remote Storage ({provider}):")
        if provider == "s3":
            print(f"  Bucket: {cfg.output.remote.s3.bucket}")
            print(f"  Region: {cfg.output.remote.s3.region}")
        elif provider == "gcs":
            print(f"  Bucket: {cfg.output.remote.gcs.bucket}")
            print(f"  Project: {cfg.output.remote.gcs.project}")
        elif provider == "azure":
            print(f"  Container: {cfg.output.remote.azure.container}")
            print(f"  Account: {cfg.output.remote.azure.storage_account}")

    print("\n✅ Configuration loaded successfully!")
    print("\nFull config:")
    print(OmegaConf.to_yaml(cfg))

if __name__ == "__main__":
    test_config()
```

Run tests:
```bash
# Test default config
python test_hydra_logging_storage.py card_id=test-001

# Test dev logging
python test_hydra_logging_storage.py card_id=test-002 logging=dev

# Test S3 storage
python test_hydra_logging_storage.py card_id=test-003 output=s3

# Test custom overrides
python test_hydra_logging_storage.py card_id=test-004 logging=prod logging.log_level=DEBUG output.local_path=/tmp/outputs
```

---

## Summary

✅ **Logging Configuration** - 4 profiles (dev, prod, debug, quiet)
✅ **Output Storage Configuration** - 4 backends (local, S3, GCS, Azure)
✅ **Environment Variable Integration** - All settings can be overridden
✅ **CLI Override Support** - Fine-grained control via command line
✅ **Hierarchical Composition** - Combine profiles and overrides easily

**Usage:**
```bash
# Simple
python artemis_orchestrator.py card_id=card-001

# Custom
python artemis_orchestrator.py card_id=card-001 logging=dev output=s3 logging.log_level=DEBUG
```

🚀 **Artemis now has production-ready, flexible configuration management!**
