#!/usr/bin/env python3
"""
Protected Artemis Orchestrator Factory

Creates ArtemisOrchestrator with circuit breaker protection on all critical components.

Usage:
    Instead of:
        orchestrator = ArtemisOrchestrator(card_id, board, messenger, rag, ...)

    Use:
        orchestrator = create_protected_orchestrator(card_id, board, messenger, ...)

This automatically wraps RAG, LLM, and KG with circuit breaker protection.
"""

from typing import Optional, List
from pathlib import Path
import logging
from omegaconf import DictConfig

from artemis_orchestrator import ArtemisOrchestrator
from protected_components import (
    ProtectedRAGAgent,
    ProtectedLLMClient,
    ProtectedKnowledgeGraph,
    check_all_protected_components
)
from kanban_manager import KanbanBoard
from messenger_interface import MessengerInterface
from artemis_stage_interface import PipelineStage, LoggerInterface
from artemis_services import TestRunner
from supervisor_agent import SupervisorAgent
from pipeline_strategies import PipelineStrategy
from circuit_breaker import CircuitBreakerOpenError


def create_protected_orchestrator(
    card_id: str,
    board: KanbanBoard,
    messenger: MessengerInterface,
    rag_db_path: str = "db",
    config=None,
    hydra_config: Optional[DictConfig] = None,
    logger: Optional[LoggerInterface] = None,
    test_runner: Optional[TestRunner] = None,
    stages: Optional[List[PipelineStage]] = None,
    supervisor: Optional[SupervisorAgent] = None,
    enable_supervision: bool = True,
    strategy: Optional[PipelineStrategy] = None,
    enable_observers: bool = True,
    check_health: bool = True
) -> ArtemisOrchestrator:
    """
    Create ArtemisOrchestrator with circuit breaker protection.

    Args:
        card_id: Kanban card ID
        board: Kanban board instance
        messenger: Agent messenger
        rag_db_path: Path to RAG database
        config: Configuration agent (deprecated)
        hydra_config: Hydra configuration
        logger: Logger implementation
        test_runner: Test runner
        stages: Pipeline stages
        supervisor: Supervisor agent
        enable_supervision: Enable supervision
        strategy: Pipeline execution strategy
        enable_observers: Enable observer pattern
        check_health: Check circuit breaker health before starting

    Returns:
        ArtemisOrchestrator instance with protected components

    Raises:
        CircuitBreakerOpenError: If critical components are down
    """
    setup_logger = logger or logging.getLogger("ProtectedOrchestrator")

    # Check circuit breaker health if requested
    if check_health:
        statuses = check_all_protected_components()
        open_breakers = [
            name for name, status in statuses.items()
            if status['state'] == 'open'
        ]

        if open_breakers:
            setup_logger.warning(
                f"⚠️  Circuit breakers OPEN: {', '.join(open_breakers)}. "
                f"Running in degraded mode."
            )

            # Check if critical component (LLM) is down
            if any('llm' in name for name in open_breakers):
                raise CircuitBreakerOpenError(
                    "Cannot start Artemis - LLM service is unavailable",
                    context={
                        "open_breakers": open_breakers,
                        "message": "LLM is a critical component. "
                                 "Please check your API keys and network connection."
                    }
                )

    # Create protected RAG agent
    setup_logger.info("Creating protected RAG agent...")
    protected_rag = ProtectedRAGAgent(
        db_path=rag_db_path,
        fallback_mode=True,  # Use fallback if RAG fails
        verbose=logger is not None and hasattr(logger, 'verbose') and logger.verbose
    )

    # Log RAG circuit breaker status
    rag_status = protected_rag.get_circuit_status()
    if rag_status['state'] != 'closed':
        setup_logger.warning(
            f"RAG circuit breaker in {rag_status['state']} state. "
            f"Using fallback mode."
        )

    # Create protected supervisor with protected LLM client
    if enable_supervision:
        setup_logger.info("Creating protected supervisor...")

        # Create protected LLM client for supervisor
        try:
            protected_llm = ProtectedLLMClient(provider="openai")
            llm_status = protected_llm.get_circuit_status()

            if llm_status['state'] != 'closed':
                setup_logger.warning(
                    f"LLM circuit breaker in {llm_status['state']} state"
                )

            # Create supervisor with protected LLM
            from supervisor_agent import SupervisorAgent
            protected_supervisor = SupervisorAgent(
                logger=logger,
                messenger=messenger,
                card_id=card_id,
                rag=protected_rag,  # Use protected RAG
                verbose=logger is not None and hasattr(logger, 'verbose') and logger.verbose,
                enable_cost_tracking=True,
                enable_config_validation=True,
                enable_sandboxing=True,
                daily_budget=10.00,
                monthly_budget=200.00
            )

            # Enable learning with protected LLM
            protected_supervisor.enable_learning(protected_llm)
            setup_logger.info("✅ Protected supervisor created with circuit breaker protection")

        except CircuitBreakerOpenError:
            setup_logger.error("❌ Cannot create supervisor - LLM circuit breaker open")
            protected_supervisor = None
            enable_supervision = False
        except Exception as e:
            setup_logger.warning(f"⚠️  Supervisor creation failed: {e}")
            protected_supervisor = None
            enable_supervision = False
    else:
        protected_supervisor = None

    # Create orchestrator with protected components
    setup_logger.info("Creating orchestrator with circuit breaker protection...")
    orchestrator = ArtemisOrchestrator(
        card_id=card_id,
        board=board,
        messenger=messenger,
        rag=protected_rag,  # Protected RAG with fallback
        config=config,
        hydra_config=hydra_config,
        logger=logger,
        test_runner=test_runner,
        stages=stages,
        supervisor=protected_supervisor if enable_supervision else None,  # Protected supervisor
        enable_supervision=enable_supervision,
        strategy=strategy,
        enable_observers=enable_observers
    )

    setup_logger.info("✅ Protected orchestrator created successfully")

    # Log overall health status
    health_summary = get_health_summary()
    setup_logger.info(f"System health: {health_summary['status']}")
    if health_summary['degraded_components']:
        setup_logger.warning(
            f"Degraded components: {', '.join(health_summary['degraded_components'])}"
        )

    return orchestrator


def get_health_summary() -> dict:
    """
    Get summary of circuit breaker health.

    Returns:
        Dict with overall health status
    """
    statuses = check_all_protected_components()

    closed = [name for name, s in statuses.items() if s['state'] == 'closed']
    open_breakers = [name for name, s in statuses.items() if s['state'] == 'open']
    half_open = [name for name, s in statuses.items() if s['state'] == 'half_open']

    # Determine overall status
    if not statuses:
        status = "unknown"
    elif open_breakers:
        # Check if critical components are down
        critical_down = any('llm' in name for name in open_breakers)
        status = "critical" if critical_down else "degraded"
    elif half_open:
        status = "recovering"
    else:
        status = "healthy"

    return {
        "status": status,
        "healthy_components": closed,
        "degraded_components": open_breakers,
        "recovering_components": half_open,
        "total_components": len(statuses),
        "circuit_breakers": statuses
    }


def check_health_before_run(logger: Optional[logging.Logger] = None) -> bool:
    """
    Check health before running pipeline.

    Args:
        logger: Logger for output

    Returns:
        True if healthy enough to run, False otherwise
    """
    log = logger or logging.getLogger("HealthCheck")

    summary = get_health_summary()

    log.info("=" * 70)
    log.info("ARTEMIS HEALTH CHECK")
    log.info("=" * 70)

    log.info(f"Overall Status: {summary['status'].upper()}")
    log.info(f"Total Components: {summary['total_components']}")

    if summary['healthy_components']:
        log.info(f"✅ Healthy: {', '.join(summary['healthy_components'])}")

    if summary['recovering_components']:
        log.warning(f"🔄 Recovering: {', '.join(summary['recovering_components'])}")

    if summary['degraded_components']:
        log.warning(f"⚠️  Degraded: {', '.join(summary['degraded_components'])}")

    log.info("=" * 70)

    # Can run if not critical
    can_run = summary['status'] != "critical"

    if not can_run:
        log.error("❌ Cannot run - critical components unavailable")
        log.error("Please check your LLM API keys and network connection")

    return can_run


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# Monkey-patch the main() function to use protected components
def patch_main_with_protection():
    """
    Patch artemis_orchestrator.main() to use protected components.

    Call this at module import to automatically protect all orchestrators.
    """
    import artemis_orchestrator
    original_main = artemis_orchestrator.main

    def protected_main(cfg: DictConfig):
        """Main with circuit breaker protection"""
        from artemis_services import PipelineLogger
        logger = PipelineLogger(verbose=cfg.logging.verbose)

        # Check health before starting
        if not check_health_before_run(logger):
            logger.log("❌ Health check failed - aborting", "ERROR")
            import sys
            sys.exit(1)

        # Continue with original main (components already protected)
        return original_main(cfg)

    # Replace main
    artemis_orchestrator.main = protected_main


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    import sys
    import json

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Protected Artemis Orchestrator")
    parser.add_argument("--health", action="store_true", help="Check system health")
    parser.add_argument("--health-summary", action="store_true", help="Get health summary JSON")

    args = parser.parse_args()

    if args.health:
        can_run = check_health_before_run()
        sys.exit(0 if can_run else 1)

    elif args.health_summary:
        summary = get_health_summary()
        print(json.dumps(summary, indent=2))

    else:
        # Default: show health
        can_run = check_health_before_run()
        sys.exit(0 if can_run else 1)
