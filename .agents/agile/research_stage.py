#!/usr/bin/env python3
"""
Research Stage - Pipeline Stage for Code Example Research

Implements PipelineStage interface with Observer Pattern integration.
Uses Strategy Pattern for multiple research sources.
Uses Repository Pattern for RAG storage.

Design Patterns:
- Strategy Pattern: Different research sources (GitHub, HuggingFace, Local)
- Factory Pattern: Create research strategies
- Repository Pattern: Abstract RAG storage
- Observer Pattern: Stage notifications

Best Practices:
- No nested loops (use comprehensions)
- No elif chains (use dictionary dispatch)
- Proper exception wrapping
- Logarithmic performance (caching, indexing)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from artemis_stages import PipelineStage
from rag_agent import RAGAgent
from research_strategy import ResearchStrategyFactory, ResearchStrategy, ResearchExample
from research_repository import ExampleRepository
from research_exceptions import ResearchStageError, ResearchSourceError


class ResearchStage(PipelineStage):
    """
    Research Stage - Retrieves code examples before development begins.

    Searches multiple sources (GitHub, HuggingFace, local) for relevant
    code examples and stores them in RAG for developers to query.

    Integrates with Observer Pattern via stage notifications.
    """

    def __init__(
        self,
        rag_agent: RAGAgent,
        sources: Optional[List[str]] = None,
        max_examples_per_source: int = 5,
        timeout_seconds: int = 30
    ):
        """
        Initialize Research Stage.

        Args:
            rag_agent: RAG agent for storage
            sources: List of research sources to use (default: all)
            max_examples_per_source: Max examples per source
            timeout_seconds: Timeout for research operations
        """
        self.rag = rag_agent
        self.repository = ExampleRepository(rag_agent)
        self.sources = sources or ResearchStrategyFactory.get_available_sources()
        self.max_examples_per_source = max_examples_per_source
        self.timeout_seconds = timeout_seconds

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute research stage.

        Args:
            context: Pipeline context with:
                - card_id: Card ID
                - task_title: Task title
                - task_description: Description
                - technologies: List of technologies
                - project_type: Project type (optional)

        Returns:
            Result dict with:
                - success: Boolean
                - status: Status string
                - examples_found: Number of examples found
                - examples_stored: Number of examples stored
                - sources_searched: List of sources searched
                - artifact_ids: List of stored artifact IDs
                - research_summary: Summary of research

        Raises:
            ResearchStageError: If stage fails
        """
        # Extract context
        card_id = context.get('card_id', 'unknown')
        task_title = context.get('task_title', 'Unknown Task')
        task_description = context.get('task_description', '')
        technologies = context.get('technologies', [])

        try:
            # Build research query
            query = self._build_research_query(task_title, task_description, technologies)

            # Create research strategies (Factory Pattern)
            strategies = self._create_strategies()

            # Search all sources (no nested loop - use comprehension)
            all_examples = self._search_all_sources(strategies, query, technologies)

            # Deduplicate and rank
            unique_examples = self.repository.deduplicate_examples(all_examples)
            ranked_examples = self.repository.rank_examples_by_relevance(
                unique_examples,
                query,
                technologies
            )

            # Store top examples
            top_examples = ranked_examples[:self.max_examples_per_source * len(strategies)]
            artifact_ids = self._store_examples(top_examples, card_id, task_title)

            # Build result
            result = {
                "success": True,
                "status": "COMPLETE",
                "examples_found": len(all_examples),
                "examples_stored": len(artifact_ids),
                "sources_searched": self.sources,
                "artifact_ids": artifact_ids,
                "research_summary": self._build_summary(top_examples, strategies)
            }

            return result

        except ResearchSourceError as e:
            # Wrap and re-raise research errors
            error_msg = f"Research stage failed: {e}"
            raise ResearchStageError(error_msg, cause=e)

        except Exception as e:
            # Wrap unexpected errors
            error_msg = f"Unexpected error in research stage: {str(e)}"
            raise ResearchStageError(error_msg, cause=e)

    def _build_research_query(
        self,
        task_title: str,
        task_description: str,
        technologies: List[str]
    ) -> str:
        """
        Build research query from task info.

        Args:
            task_title: Task title
            task_description: Task description
            technologies: Technologies list

        Returns:
            Search query string
        """
        # Guard clause
        if not task_title and not task_description:
            return "code example"

        # Combine title and description
        query_parts = []

        if task_title:
            query_parts.append(task_title)

        if task_description:
            # Take first 100 chars of description
            query_parts.append(task_description[:100])

        query = " ".join(query_parts)

        # Add primary technology if available
        if technologies:
            query = f"{technologies[0]} {query}"

        return query

    def _create_strategies(self) -> List[ResearchStrategy]:
        """
        Create research strategies using Factory Pattern.

        Returns:
            List of research strategies

        Raises:
            ResearchStageError: If strategy creation fails
        """
        try:
            # Use comprehension instead of loop
            strategies = [
                ResearchStrategyFactory.create_strategy(
                    source,
                    timeout_seconds=self.timeout_seconds
                )
                for source in self.sources
            ]

            return strategies

        except ValueError as e:
            raise ResearchStageError(
                f"Failed to create research strategies: {e}",
                cause=e
            )

    def _search_all_sources(
        self,
        strategies: List[ResearchStrategy],
        query: str,
        technologies: List[str]
    ) -> List[ResearchExample]:
        """
        Search all sources for examples.
        No nested loops - uses comprehension with error handling.

        Args:
            strategies: List of research strategies
            query: Search query
            technologies: Technologies list

        Returns:
            List of all examples found (may contain duplicates)
        """
        all_examples = []

        # Search each strategy (comprehension with error handling)
        for strategy in strategies:
            try:
                examples = strategy.search(
                    query=query,
                    technologies=technologies,
                    max_results=self.max_examples_per_source
                )
                all_examples.extend(examples)

            except ResearchSourceError as e:
                # Log error but continue with other sources
                print(f"Warning: {e}")
                continue

            except Exception as e:
                # Log unexpected error but continue
                print(f"Warning: Unexpected error in {strategy.get_source_name()}: {e}")
                continue

        return all_examples

    def _store_examples(
        self,
        examples: List[ResearchExample],
        card_id: str,
        task_title: str
    ) -> List[str]:
        """
        Store examples in RAG using Repository Pattern.

        Args:
            examples: Examples to store
            card_id: Card ID
            task_title: Task title

        Returns:
            List of artifact IDs
        """
        # Guard clause
        if not examples:
            return []

        try:
            artifact_ids = self.repository.store_examples_batch(
                examples=examples,
                card_id=card_id,
                task_title=task_title
            )

            return artifact_ids

        except Exception as e:
            # Don't fail stage if storage fails - just log warning
            print(f"Warning: Failed to store some examples: {e}")
            return []

    def _build_summary(
        self,
        examples: List[ResearchExample],
        strategies: List[ResearchStrategy]
    ) -> str:
        """
        Build research summary.

        Args:
            examples: Examples found
            strategies: Strategies used

        Returns:
            Summary string
        """
        # Guard clause
        if not examples:
            return "No examples found"

        # Count examples by source using dictionary comprehension
        source_counts = {}
        for example in examples:
            source_counts[example.source] = source_counts.get(example.source, 0) + 1

        # Build summary lines using comprehension
        summary_lines = [
            f"Found {len(examples)} code examples from {len(strategies)} sources:",
            *[f"  - {source}: {count} examples" for source, count in source_counts.items()],
            f"\nTop examples:",
            *[f"  - {example.title} ({example.source}, score: {example.relevance_score:.2f})"
              for example in examples[:5]]
        ]

        return "\n".join(summary_lines)

    def validate_prerequisites(self, context: Dict[str, Any]) -> bool:
        """
        Validate that context has required fields.

        Args:
            context: Pipeline context

        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        required_fields = ['card_id', 'task_title']

        # Use all() with generator expression instead of loop
        return all(field in context for field in required_fields)

    def get_required_context_keys(self) -> List[str]:
        """Get list of required context keys"""
        return ['card_id', 'task_title']

    def get_optional_context_keys(self) -> List[str]:
        """Get list of optional context keys"""
        return ['task_description', 'technologies', 'project_type']

    def get_stage_name(self) -> str:
        """Get stage name"""
        return "ResearchStage"

    def get_stage_description(self) -> str:
        """Get stage description"""
        return (
            "Research Stage: Searches multiple sources (GitHub, HuggingFace, local) "
            "for relevant code examples and stores them in RAG for developer reference."
        )

    def supports_async(self) -> bool:
        """This stage supports async execution"""
        return True


# Convenience function
def create_research_stage(
    rag_agent: RAGAgent,
    sources: Optional[List[str]] = None,
    max_examples: int = 5
) -> ResearchStage:
    """
    Create research stage with default configuration.

    Args:
        rag_agent: RAG agent
        sources: Research sources (default: all)
        max_examples: Max examples per source

    Returns:
        Configured ResearchStage instance
    """
    return ResearchStage(
        rag_agent=rag_agent,
        sources=sources,
        max_examples_per_source=max_examples,
        timeout_seconds=30
    )


if __name__ == "__main__":
    # Example usage
    print("Research Stage - Example Usage")
    print("=" * 60)

    from rag_agent import RAGAgent

    # Create RAG agent
    rag = RAGAgent()

    # Create research stage
    stage = create_research_stage(rag, sources=["local"])

    # Execute with context
    context = {
        "card_id": "example-123",
        "task_title": "Create data visualization dashboard",
        "task_description": "Build interactive dashboard with charts",
        "technologies": ["python", "plotly", "pandas"]
    }

    try:
        result = stage.execute(context)

        print("\n✅ Research completed!")
        print(f"Examples found: {result['examples_found']}")
        print(f"Examples stored: {result['examples_stored']}")
        print(f"\nSummary:\n{result['research_summary']}")

    except ResearchStageError as e:
        print(f"\n❌ Research failed: {e}")

    print("\n" + "=" * 60)
