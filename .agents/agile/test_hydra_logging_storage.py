#!/usr/bin/env python3
"""
Test script for Hydra logging and storage configuration.

Usage:
  python test_hydra_logging_storage.py card_id=test-001
  python test_hydra_logging_storage.py card_id=test-002 logging=dev
  python test_hydra_logging_storage.py card_id=test-003 output=s3
  python test_hydra_logging_storage.py card_id=test-004 logging=prod logging.log_level=DEBUG
"""

from omegaconf import DictConfig, OmegaConf
import hydra
import os


@hydra.main(config_path="conf", config_name="config", version_base=None)
def test_config(cfg: DictConfig):
    print("=" * 70)
    print("Hydra Configuration Test - Logging & Storage")
    print("=" * 70)

    # Card ID
    print(f"\n📋 Card ID: {cfg.card_id}")

    # Logging Configuration
    print("\n📝 Logging Configuration:")
    print(f"  Log Directory: {cfg.logging.log_dir}")
    print(f"  Log Level: {cfg.logging.log_level}")
    print(f"  Max Size: {cfg.logging.max_size_mb} MB")
    print(f"  Backup Count: {cfg.logging.backup_count}")
    print(f"  Verbose: {cfg.logging.verbose}")

    # Check if log directory exists
    log_dir = cfg.logging.log_dir
    log_dir_exists = os.path.exists(log_dir)
    log_dir_writable = os.access(log_dir, os.W_OK) if log_dir_exists else False
    print(f"\n  Directory Status:")
    print(f"    Exists: {log_dir_exists}")
    print(f"    Writable: {log_dir_writable}")

    # Output Storage Configuration
    print("\n💾 Output Storage Configuration:")
    print(f"  Storage Type: {cfg.output.storage_type}")
    print(f"  Local Path: {cfg.output.local_path}")

    if cfg.output.storage_type == "local":
        # Resolve local path
        from pathlib import Path
        agile_dir = Path(__file__).parent
        if not Path(cfg.output.local_path).is_absolute():
            local_path = (agile_dir / cfg.output.local_path).resolve()
        else:
            local_path = Path(cfg.output.local_path)

        print(f"  Resolved Path: {local_path}")
        print(f"\n  Directory Status:")
        print(f"    Exists: {local_path.exists()}")
        if local_path.exists():
            print(f"    Writable: {os.access(local_path, os.W_OK)}")

    print(f"\n  Remote Provider: {cfg.output.remote.provider}")

    if cfg.output.storage_type == "remote":
        provider = cfg.output.remote.provider
        print(f"\n☁️  Remote Storage ({provider.upper()}):")
        if provider == "s3":
            print(f"  Bucket: {cfg.output.remote.s3.bucket}")
            print(f"  Region: {cfg.output.remote.s3.region}")
            print(f"\n  Environment Variables:")
            print(f"    AWS_ACCESS_KEY_ID: {'✓ set' if os.getenv('AWS_ACCESS_KEY_ID') else '✗ not set'}")
            print(f"    AWS_SECRET_ACCESS_KEY: {'✓ set' if os.getenv('AWS_SECRET_ACCESS_KEY') else '✗ not set'}")
        elif provider == "gcs":
            print(f"  Bucket: {cfg.output.remote.gcs.bucket}")
            print(f"  Project: {cfg.output.remote.gcs.project}")
            print(f"\n  Environment Variables:")
            print(f"    GOOGLE_APPLICATION_CREDENTIALS: {'✓ set' if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') else '✗ not set'}")
        elif provider == "azure":
            print(f"  Container: {cfg.output.remote.azure.container}")
            print(f"  Storage Account: {cfg.output.remote.azure.storage_account}")
            print(f"\n  Environment Variables:")
            print(f"    AZURE_STORAGE_CONNECTION_STRING: {'✓ set' if os.getenv('AZURE_STORAGE_CONNECTION_STRING') else '✗ not set'}")

    # Other configurations
    print("\n🔧 Other Configuration:")
    if hasattr(cfg, 'llm'):
        print(f"  LLM Provider: {cfg.llm.provider if hasattr(cfg.llm, 'provider') else 'configured'}")
    if hasattr(cfg, 'storage'):
        print(f"  Storage Backend: {cfg.storage.rag_db_type if hasattr(cfg.storage, 'rag_db_type') else 'configured'}")
    if hasattr(cfg, 'pipeline'):
        print(f"  Pipeline Strategy: configured")
    if hasattr(cfg, 'security'):
        print(f"  Security Level: configured")

    # Test logger creation
    print("\n🧪 Testing Logger Creation:")
    try:
        from artemis_logger import ArtemisLogger
        logger = ArtemisLogger(
            component="test",
            log_dir=cfg.logging.log_dir,
            log_level=cfg.logging.log_level,
            max_bytes=cfg.logging.max_size_mb * 1024 * 1024,
            backup_count=cfg.logging.backup_count
        )
        logger.info("Test log message from Hydra config test")
        print(f"  ✅ Logger created successfully")
        print(f"  Log file: {logger.get_log_path()}")
    except Exception as e:
        print(f"  ❌ Logger creation failed: {e}")

    # Test storage manager creation
    print("\n🧪 Testing Storage Manager Creation:")
    try:
        # Set environment variables from config for testing
        os.environ["ARTEMIS_OUTPUT_STORAGE"] = cfg.output.storage_type
        os.environ["ARTEMIS_OUTPUT_PATH"] = cfg.output.local_path
        if cfg.output.storage_type == "remote":
            os.environ["ARTEMIS_REMOTE_STORAGE_PROVIDER"] = cfg.output.remote.provider

        from output_storage import OutputStorageManager
        storage = OutputStorageManager()
        info = storage.get_storage_info()
        print(f"  ✅ Storage manager created successfully")
        print(f"  Type: {info['type']}")
        print(f"  Backend: {info['backend']}")
        if info['type'] == 'local':
            print(f"  Base Path: {info['base_path']}")
        elif info['type'] == 'remote':
            print(f"  Provider: {info['provider']}")
    except Exception as e:
        print(f"  ❌ Storage manager creation failed: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("✅ Configuration Test Complete!")
    print("=" * 70)

    # Show full config in YAML format
    print("\n📄 Full Configuration (YAML):")
    print("-" * 70)
    print(OmegaConf.to_yaml(cfg))


if __name__ == "__main__":
    test_config()
