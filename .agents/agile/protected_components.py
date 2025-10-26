#!/usr/bin/env python3
"""
Protected Components with Circuit Breakers

Wraps critical Artemis components with circuit breaker protection to prevent
cascading failures.

Usage:
    from protected_components import ProtectedRAGAgent, ProtectedLLMClient

    # Instead of:
    # rag = RAGAgent(db_path="db")

    # Use:
    # rag = ProtectedRAGAgent(db_path="db")

    # Automatically fails fast if RAG is down
"""

from typing import Any, Optional, List, Dict
import logging

from circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    get_circuit_breaker
)
from artemis_exceptions import wrap_exception, RAGStorageError, LLMClientError


class ProtectedRAGAgent:
    """
    RAG Agent with circuit breaker protection.

    Fails fast if ChromaDB or embeddings service is down.
    """

    def __init__(self, *args, fallback_mode: bool = True, **kwargs):
        """
        Initialize protected RAG agent.

        Args:
            fallback_mode: If True, return None on circuit breaker open instead of raising
            *args, **kwargs: Passed to RAGAgent
        """
        from rag_agent import RAGAgent

        self.fallback_mode = fallback_mode
        self.logger = logging.getLogger("ProtectedRAGAgent")

        # Create circuit breaker for RAG
        config = CircuitBreakerConfig(
            failure_threshold=3,  # Open after 3 failures
            timeout_seconds=120,  # Wait 2 minutes before retry
            success_threshold=2   # Need 2 successes to close
        )
        self.breaker = get_circuit_breaker("rag_agent", config)

        # Initialize RAG agent
        try:
            with self.breaker:
                self._rag = RAGAgent(*args, **kwargs)
                self.logger.info("RAG Agent initialized successfully")
        except CircuitBreakerOpenError:
            self.logger.warning("RAG Agent circuit breaker open during initialization")
            self._rag = None
        except Exception as e:
            self.logger.error(f"RAG Agent initialization failed: {e}")
            self._rag = None

    def _handle_circuit_open(self, method_name: str):
        """Handle circuit breaker open state"""
        if self.fallback_mode:
            self.logger.warning(
                f"RAG {method_name} skipped - circuit breaker open. "
                f"Using fallback mode."
            )
            return None
        else:
            raise CircuitBreakerOpenError(
                f"RAG {method_name} failed - circuit breaker open",
                context={"method": method_name}
            )

    def store_artifact(self, *args, **kwargs):
        """Store artifact with circuit breaker protection"""
        if not self._rag:
            return self._handle_circuit_open("store_artifact")

        try:
            with self.breaker:
                return self._rag.store_artifact(*args, **kwargs)
        except CircuitBreakerOpenError:
            return self._handle_circuit_open("store_artifact")

    def query_similar(self, *args, **kwargs):
        """Query similar with circuit breaker protection"""
        if not self._rag:
            return self._handle_circuit_open("query_similar")

        try:
            with self.breaker:
                return self._rag.query_similar(*args, **kwargs)
        except CircuitBreakerOpenError:
            return self._handle_circuit_open("query_similar")

    def delete_artifact(self, *args, **kwargs):
        """Delete artifact with circuit breaker protection"""
        if not self._rag:
            return self._handle_circuit_open("delete_artifact")

        try:
            with self.breaker:
                return self._rag.delete_artifact(*args, **kwargs)
        except CircuitBreakerOpenError:
            return self._handle_circuit_open("delete_artifact")

    def get_circuit_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return self.breaker.get_status()

    # Delegate all other methods
    def __getattr__(self, name):
        """Delegate unknown methods to underlying RAG agent"""
        if self._rag is None:
            return lambda *args, **kwargs: self._handle_circuit_open(name)
        return getattr(self._rag, name)


class ProtectedLLMClient:
    """
    LLM Client with circuit breaker protection.

    Fails fast if OpenAI/Anthropic API is down.
    """

    def __init__(self, provider: str = "openai", fallback_mode: bool = False):
        """
        Initialize protected LLM client.

        Args:
            provider: LLM provider ("openai" or "anthropic")
            fallback_mode: If True, raise exception on circuit open (no fallback for LLM)
        """
        from llm_client import create_llm_client

        self.fallback_mode = fallback_mode
        self.logger = logging.getLogger(f"ProtectedLLMClient.{provider}")

        # Create circuit breaker for LLM
        config = CircuitBreakerConfig(
            failure_threshold=5,  # Open after 5 failures
            timeout_seconds=60,   # Wait 1 minute before retry
            success_threshold=3   # Need 3 successes to close
        )
        self.breaker = get_circuit_breaker(f"llm_{provider}", config)

        # Initialize LLM client
        try:
            with self.breaker:
                self._llm = create_llm_client(provider)
                self.logger.info(f"LLM Client ({provider}) initialized successfully")
        except CircuitBreakerOpenError:
            self.logger.error(f"LLM Client ({provider}) circuit breaker open during initialization")
            self._llm = None
        except Exception as e:
            self.logger.error(f"LLM Client ({provider}) initialization failed: {e}")
            self._llm = None

    def complete(self, *args, **kwargs):
        """Complete with circuit breaker protection"""
        if not self._llm:
            raise LLMClientError(
                "LLM client unavailable - circuit breaker open",
                context={"method": "complete"}
            )

        try:
            with self.breaker:
                return self._llm.complete(*args, **kwargs)
        except CircuitBreakerOpenError as e:
            raise LLMClientError(
                "LLM API unavailable - circuit breaker open",
                context={"method": "complete", "breaker_status": self.breaker.get_status()}
            ) from e

    def generate_text(self, *args, **kwargs):
        """Generate text with circuit breaker protection"""
        if not self._llm:
            raise LLMClientError(
                "LLM client unavailable - circuit breaker open",
                context={"method": "generate_text"}
            )

        try:
            with self.breaker:
                return self._llm.generate_text(*args, **kwargs)
        except CircuitBreakerOpenError as e:
            raise LLMClientError(
                "LLM API unavailable - circuit breaker open",
                context={"method": "generate_text", "breaker_status": self.breaker.get_status()}
            ) from e

    def get_circuit_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return self.breaker.get_status()

    # Delegate all other methods
    def __getattr__(self, name):
        """Delegate unknown methods to underlying LLM client"""
        if self._llm is None:
            raise LLMClientError(
                f"LLM client unavailable for method: {name}",
                context={"method": name}
            )
        return getattr(self._llm, name)


class ProtectedKnowledgeGraph:
    """
    Knowledge Graph with circuit breaker protection.

    Fails fast if Neo4j is down.
    """

    def __init__(self, fallback_mode: bool = True, *args, **kwargs):
        """
        Initialize protected Knowledge Graph.

        Args:
            fallback_mode: If True, use in-memory fallback when circuit open
            *args, **kwargs: Passed to KnowledgeGraph
        """
        self.fallback_mode = fallback_mode
        self.logger = logging.getLogger("ProtectedKnowledgeGraph")
        self.in_memory_fallback: Dict[str, Any] = {}  # Simple in-memory storage

        # Create circuit breaker for KG
        config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout_seconds=120,
            success_threshold=2
        )
        self.breaker = get_circuit_breaker("knowledge_graph", config)

        # Initialize Knowledge Graph
        try:
            from knowledge_graph import KnowledgeGraph
            with self.breaker:
                self._kg = KnowledgeGraph(*args, **kwargs)
                self.logger.info("Knowledge Graph initialized successfully")
        except CircuitBreakerOpenError:
            self.logger.warning("Knowledge Graph circuit breaker open during initialization")
            self._kg = None
        except Exception as e:
            self.logger.error(f"Knowledge Graph initialization failed: {e}")
            self._kg = None

    def _handle_circuit_open(self, method_name: str, *args, **kwargs):
        """Handle circuit breaker open state with in-memory fallback"""
        if self.fallback_mode:
            self.logger.warning(
                f"KG {method_name} using in-memory fallback - circuit breaker open"
            )
            # Simple in-memory fallback
            if method_name == "add_node":
                node_id = kwargs.get("node_id") or args[0] if args else None
                if node_id:
                    self.in_memory_fallback[node_id] = kwargs
                return node_id
            elif method_name == "query":
                # Return empty results for queries
                return []
            else:
                return None
        else:
            raise CircuitBreakerOpenError(
                f"KG {method_name} failed - circuit breaker open",
                context={"method": method_name}
            )

    def add_node(self, *args, **kwargs):
        """Add node with circuit breaker protection"""
        if not self._kg:
            return self._handle_circuit_open("add_node", *args, **kwargs)

        try:
            with self.breaker:
                return self._kg.add_node(*args, **kwargs)
        except CircuitBreakerOpenError:
            return self._handle_circuit_open("add_node", *args, **kwargs)

    def query(self, *args, **kwargs):
        """Query with circuit breaker protection"""
        if not self._kg:
            return self._handle_circuit_open("query", *args, **kwargs)

        try:
            with self.breaker:
                return self._kg.query(*args, **kwargs)
        except CircuitBreakerOpenError:
            return self._handle_circuit_open("query", *args, **kwargs)

    def get_circuit_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return self.breaker.get_status()

    # Delegate all other methods
    def __getattr__(self, name):
        """Delegate unknown methods to underlying KG"""
        if self._kg is None:
            return lambda *args, **kwargs: self._handle_circuit_open(name, *args, **kwargs)
        return getattr(self._kg, name)


# ============================================================================
# HEALTH CHECK HELPERS
# ============================================================================

def check_all_protected_components() -> Dict[str, Dict[str, Any]]:
    """
    Check health of all protected components.

    Returns:
        Dict of component statuses
    """
    from circuit_breaker import get_all_circuit_breaker_statuses
    return get_all_circuit_breaker_statuses()


def reset_all_circuit_breakers():
    """Reset all circuit breakers to closed state"""
    from circuit_breaker import reset_all_circuit_breakers
    reset_all_circuit_breakers()


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

    parser = argparse.ArgumentParser(description="Protected Components Status")
    parser.add_argument("--status", action="store_true", help="Show all circuit breaker statuses")
    parser.add_argument("--reset", action="store_true", help="Reset all circuit breakers")
    parser.add_argument("--test-rag", action="store_true", help="Test RAG with protection")
    parser.add_argument("--test-llm", action="store_true", help="Test LLM with protection")

    args = parser.parse_args()

    if args.status:
        statuses = check_all_protected_components()
        print(json.dumps(statuses, indent=2))

    elif args.reset:
        reset_all_circuit_breakers()
        print("✅ All circuit breakers reset")

    elif args.test_rag:
        print("Testing RAG with circuit breaker protection...")
        rag = ProtectedRAGAgent(db_path="db", verbose=False)

        try:
            result = rag.query_similar("test query", top_k=1)
            print(f"✅ RAG query successful: {len(result) if result else 0} results")
        except Exception as e:
            print(f"❌ RAG query failed: {e}")

        print(f"\nCircuit breaker status:")
        print(json.dumps(rag.get_circuit_status(), indent=2))

    elif args.test_llm:
        print("Testing LLM with circuit breaker protection...")
        from llm_client import LLMMessage

        llm = ProtectedLLMClient("openai")

        try:
            response = llm.complete(
                messages=[LLMMessage(role="user", content="Say 'test'")],
                max_tokens=10
            )
            print(f"✅ LLM call successful: {response.content[:50]}")
        except Exception as e:
            print(f"❌ LLM call failed: {e}")

        print(f"\nCircuit breaker status:")
        print(json.dumps(llm.get_circuit_status(), indent=2))

    else:
        parser.print_help()
