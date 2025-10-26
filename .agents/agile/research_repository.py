#!/usr/bin/env python3
"""
Research Repository Pattern Implementation

Implements Repository Pattern for abstracting RAG storage.
Provides a clean interface for storing and retrieving research examples.
"""

from typing import List, Dict, Any, Optional
from dataclasses import asdict

from rag_agent import RAGAgent
from research_strategy import ResearchExample
from research_exceptions import ExampleStorageError


class ExampleRepository:
    """
    Repository Pattern for research examples.
    Abstracts RAG storage behind a clean interface.
    """

    ARTIFACT_TYPE = "code_example"

    def __init__(self, rag_agent: RAGAgent):
        """
        Initialize repository with RAG agent.

        Args:
            rag_agent: RAG agent for storage
        """
        self.rag = rag_agent

    def store_example(
        self,
        example: ResearchExample,
        card_id: str,
        task_title: str
    ) -> str:
        """
        Store a research example in RAG.

        Args:
            example: Research example to store
            card_id: Card ID for tracking
            task_title: Task title

        Returns:
            Artifact ID

        Raises:
            ExampleStorageError: If storage fails
        """
        try:
            # Prepare metadata
            metadata = {
                "source": example.source,
                "url": example.url or "",
                "language": example.language,
                "tags": example.tags,
                "relevance_score": example.relevance_score,
                "example_type": "research"
            }

            # Store in RAG
            artifact_id = self.rag.store_artifact(
                artifact_type=self.ARTIFACT_TYPE,
                card_id=card_id,
                task_title=f"{task_title} - {example.title}",
                content=example.content,
                metadata=metadata
            )

            return artifact_id

        except Exception as e:
            raise ExampleStorageError(
                artifact_id=example.title,
                message=f"Failed to store example '{example.title}'",
                cause=e
            )

    def store_examples_batch(
        self,
        examples: List[ResearchExample],
        card_id: str,
        task_title: str
    ) -> List[str]:
        """
        Store multiple examples in batch.

        Args:
            examples: List of research examples
            card_id: Card ID
            task_title: Task title

        Returns:
            List of artifact IDs

        Raises:
            ExampleStorageError: If any storage fails
        """
        # Use comprehension for batch storage
        artifact_ids = []
        errors = []

        for example in examples:
            try:
                artifact_id = self.store_example(example, card_id, task_title)
                artifact_ids.append(artifact_id)
            except ExampleStorageError as e:
                errors.append(str(e))

        # Guard clause: raise if too many errors
        if len(errors) > len(examples) / 2:
            raise ExampleStorageError(
                artifact_id="batch",
                message=f"Failed to store {len(errors)}/{len(examples)} examples",
                cause=Exception("; ".join(errors))
            )

        return artifact_ids

    def query_similar_examples(
        self,
        query: str,
        top_k: int = 5,
        language_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query for similar examples.

        Args:
            query: Search query
            top_k: Number of results
            language_filter: Optional language filter

        Returns:
            List of similar examples with metadata
        """
        # Build filters
        filters = {}
        if language_filter:
            filters["language"] = language_filter

        # Query RAG
        try:
            results = self.rag.query_similar(
                query_text=query,
                artifact_types=[self.ARTIFACT_TYPE],
                top_k=top_k,
                filters=filters if filters else None
            )

            return results

        except Exception as e:
            # Wrap exception but don't fail - return empty list
            print(f"Warning: Failed to query examples: {e}")
            return []

    def get_example_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored examples.

        Returns:
            Dictionary with statistics
        """
        try:
            stats = self.rag.get_stats()

            return {
                "total_examples": stats.get("by_type", {}).get(self.ARTIFACT_TYPE, 0),
                "total_artifacts": stats.get("total_artifacts", 0),
                "database_path": stats.get("database_path", ""),
                "chromadb_available": stats.get("chromadb_available", False)
            }

        except Exception as e:
            # Return empty stats on error
            return {
                "total_examples": 0,
                "total_artifacts": 0,
                "database_path": "",
                "chromadb_available": False,
                "error": str(e)
            }

    def deduplicate_examples(self, examples: List[ResearchExample]) -> List[ResearchExample]:
        """
        Remove duplicate examples based on content similarity.
        Uses simple hash-based deduplication for performance.

        Args:
            examples: List of research examples

        Returns:
            Deduplicated list
        """
        # Guard clause
        if not examples:
            return []

        # Use set for O(1) lookup instead of O(n) list contains
        seen_hashes = set()
        unique_examples = []

        for example in examples:
            # Create simple content hash
            content_hash = hash(example.content[:1000])  # Hash first 1000 chars

            # Guard clause: skip if seen
            if content_hash in seen_hashes:
                continue

            seen_hashes.add(content_hash)
            unique_examples.append(example)

        return unique_examples

    def rank_examples_by_relevance(
        self,
        examples: List[ResearchExample],
        query: str,
        technologies: List[str]
    ) -> List[ResearchExample]:
        """
        Rank examples by relevance to query and technologies.

        Args:
            examples: List of examples to rank
            query: Search query
            technologies: Technologies list

        Returns:
            Sorted list by relevance score
        """
        # Guard clause
        if not examples:
            return []

        # Calculate boost scores using comprehension
        query_lower = query.lower()
        tech_lower = [t.lower() for t in technologies]

        boosted_examples = []
        for example in examples:
            boost = self._calculate_boost(example, query_lower, tech_lower)
            # Create new score
            boosted_score = example.relevance_score * boost

            # Create new example with boosted score
            boosted_example = ResearchExample(
                title=example.title,
                content=example.content,
                source=example.source,
                url=example.url,
                language=example.language,
                tags=example.tags,
                relevance_score=boosted_score
            )
            boosted_examples.append(boosted_example)

        # Sort by boosted score
        boosted_examples.sort(key=lambda x: x.relevance_score, reverse=True)

        return boosted_examples

    def _calculate_boost(self, example: ResearchExample, query: str, technologies: List[str]) -> float:
        """
        Calculate relevance boost factor.

        Args:
            example: Research example
            query: Query string (lowercase)
            technologies: Technologies list (lowercase)

        Returns:
            Boost factor (1.0 = no boost)
        """
        boost = 1.0

        # Boost for title match
        if query in example.title.lower():
            boost *= 1.5

        # Boost for technology match
        tech_matches = sum(1 for tech in technologies if tech in example.language.lower() or tech in " ".join(example.tags).lower())
        boost *= (1.0 + tech_matches * 0.2)

        # Boost for source priority (GitHub > HuggingFace > Local)
        source_boost = {
            "github": 1.3,
            "huggingface": 1.2,
            "local": 1.0
        }
        boost *= source_boost.get(example.source.lower(), 1.0)

        return boost
