#!/usr/bin/env python3
"""
Test Hydra Configuration for Artemis

Verifies that Hydra configs load correctly and can be overridden.
"""

import hydra
from omegaconf import DictConfig, OmegaConf
from hydra_config import ArtemisConfig


@hydra.main(version_base=None, config_path="conf", config_name="config")
def test_config(cfg: DictConfig) -> None:
    """
    Test Hydra configuration loading

    Args:
        cfg: Hydra configuration object
    """
    print("\n" + "="*70)
    print("🔧 ARTEMIS HYDRA CONFIGURATION TEST")
    print("="*70)

    # Print raw config
    print("\n📋 Raw Configuration:")
    print(OmegaConf.to_yaml(cfg))

    # Test type-safe access
    print("\n✅ Type-Safe Access:")
    print(f"  Card ID: {cfg.card_id}")
    print(f"  LLM Provider: {cfg.llm.provider}")
    print(f"  LLM Model: {cfg.llm.model}")
    print(f"  RAG DB Path: {cfg.storage.rag_db_path}")
    print(f"  Max Parallel Devs: {cfg.pipeline.max_parallel_developers}")
    print(f"  Code Review Enabled: {cfg.pipeline.enable_code_review}")
    print(f"  GDPR Enforcement: {cfg.security.enforce_gdpr}")
    print(f"  Log Level: {cfg.logging.log_level}")

    # Test stages list
    print(f"\n📝 Pipeline Stages ({len(cfg.pipeline.stages)}):")
    for i, stage in enumerate(cfg.pipeline.stages, 1):
        print(f"  {i}. {stage}")

    # Validate config
    print("\n✅ Configuration Validation:")
    validation_passed = True

    # Check required fields
    if cfg.card_id == "???":
        print("  ❌ card_id is required")
        validation_passed = False
    else:
        print(f"  ✅ card_id: {cfg.card_id}")

    # Check LLM provider
    if cfg.llm.provider not in ["openai", "anthropic", "mock"]:
        print(f"  ❌ Invalid LLM provider: {cfg.llm.provider}")
        validation_passed = False
    else:
        print(f"  ✅ LLM provider: {cfg.llm.provider}")

    # Check API key for non-mock providers
    if cfg.llm.provider != "mock" and not cfg.llm.api_key:
        print(f"  ⚠️  Warning: No API key for {cfg.llm.provider}")
    elif cfg.llm.api_key:
        masked_key = cfg.llm.api_key[:6] + "..." + cfg.llm.api_key[-4:] if len(cfg.llm.api_key) > 10 else "***"
        print(f"  ✅ API key: {masked_key}")

    # Summary
    print("\n" + "="*70)
    if validation_passed:
        print("✅ CONFIGURATION VALID")
    else:
        print("❌ CONFIGURATION INVALID")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_config()
