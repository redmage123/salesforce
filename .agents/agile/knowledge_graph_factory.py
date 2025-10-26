#!/usr/bin/env python3
"""
Knowledge Graph Factory - Singleton Pattern for Artemis

Provides centralized access to the Knowledge Graph across all agents.
Ensures single instance with graceful fallback if Memgraph unavailable.

Usage:
    from knowledge_graph_factory import get_knowledge_graph

    kg = get_knowledge_graph()
    if kg:
        kg.add_file("auth.py", "python")
"""

import os
from typing import Optional
from knowledge_graph import KnowledgeGraph, MEMGRAPH_AVAILABLE


class KnowledgeGraphFactory:
    """
    Singleton factory for Knowledge Graph

    Ensures only one instance exists and provides graceful degradation
    if Memgraph is not available.
    """

    _instance: Optional[KnowledgeGraph] = None
    _initialization_attempted: bool = False
    _initialization_successful: bool = False

    @classmethod
    def get_instance(cls, host: Optional[str] = None, port: Optional[int] = None) -> Optional[KnowledgeGraph]:
        """
        Get or create singleton Knowledge Graph instance

        Args:
            host: Memgraph host (default: localhost or MEMGRAPH_HOST env var)
            port: Memgraph port (default: 7687 or MEMGRAPH_PORT env var)

        Returns:
            KnowledgeGraph instance or None if unavailable
        """
        # Return existing instance if available
        if cls._instance is not None:
            return cls._instance

        # Don't retry if previous initialization failed
        if cls._initialization_attempted and not cls._initialization_successful:
            return None

        # Attempt initialization
        cls._initialization_attempted = True

        # Check if Memgraph library available
        if not MEMGRAPH_AVAILABLE:
            print("⚠️  Knowledge Graph unavailable: gqlalchemy not installed")
            print("   Install with: pip install gqlalchemy")
            print("   Agents will continue without knowledge graph integration")
            return None

        # Get connection parameters
        if host is None:
            host = os.getenv("MEMGRAPH_HOST", "localhost")
        if port is None:
            port = int(os.getenv("MEMGRAPH_PORT", "7687"))

        # Try to connect
        try:
            cls._instance = KnowledgeGraph(host=host, port=port)
            cls._initialization_successful = True
            print(f"✅ Knowledge Graph connected: {host}:{port}")
            return cls._instance

        except Exception as e:
            print(f"⚠️  Knowledge Graph connection failed: {e}")
            print(f"   Host: {host}, Port: {port}")
            print("   Agents will continue without knowledge graph integration")
            print("   To enable, ensure Memgraph is running:")
            print("     docker run -p 7687:7687 memgraph/memgraph")
            cls._initialization_successful = False
            return None

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (useful for testing)"""
        cls._instance = None
        cls._initialization_attempted = False
        cls._initialization_successful = False

    @classmethod
    def is_available(cls) -> bool:
        """Check if Knowledge Graph is available"""
        return cls._initialization_successful and cls._instance is not None


# Convenience function for agents
def get_knowledge_graph(host: Optional[str] = None, port: Optional[int] = None) -> Optional[KnowledgeGraph]:
    """
    Get Knowledge Graph instance (convenience function)

    Args:
        host: Memgraph host (optional)
        port: Memgraph port (optional)

    Returns:
        KnowledgeGraph instance or None
    """
    return KnowledgeGraphFactory.get_instance(host=host, port=port)


# Convenience function to check availability
def is_knowledge_graph_available() -> bool:
    """
    Check if Knowledge Graph is available

    Returns:
        True if available, False otherwise
    """
    return KnowledgeGraphFactory.is_available()
