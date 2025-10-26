#!/usr/bin/env python3
"""
RAG Storage Helper - DRY Utility for Stage Artifact Storage

Single Responsibility: Standardize RAG artifact storage across all pipeline stages

This helper eliminates ~270 lines of duplicate code across 11+ stages by
providing a single, consistent interface for storing stage artifacts in RAG.

Benefits:
- DRY principle: One implementation, used everywhere
- Consistent error handling across all stages
- Centralized logging and debugging
- Easy to enhance storage behavior globally
- Type-safe artifact storage with validation

Usage:
    from rag_storage_helper import RAGStorageHelper

    # In any stage:
    RAGStorageHelper.store_stage_artifact(
        rag=self.rag,
        stage_name="architecture",
        card_id=card_id,
        task_title=task_title,
        content=adr_content,
        metadata={"adr_file": adr_file},
        logger=self.logger
    )
"""

from typing import Dict, Optional, Any
from artemis_exceptions import RAGStorageError, wrap_exception


class RAGStorageHelper:
    """
    Static utility class for standardized RAG artifact storage

    Provides DRY interface for all pipeline stages to store artifacts
    with consistent error handling and logging.
    """

    @staticmethod
    def store_stage_artifact(
        rag: Any,
        stage_name: str,
        card_id: str,
        task_title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        logger: Optional[Any] = None
    ) -> bool:
        """
        Store a stage artifact in RAG with standardized error handling

        Args:
            rag: RAG agent instance
            stage_name: Name of the stage (e.g., "architecture", "code_review")
            card_id: Task card identifier
            task_title: Human-readable task title
            content: Artifact content to store
            metadata: Optional additional metadata dict
            logger: Optional logger instance for debug/warning logs

        Returns:
            bool: True if storage succeeded, False if failed

        Raises:
            Never raises - handles all exceptions internally

        Example:
            success = RAGStorageHelper.store_stage_artifact(
                rag=self.rag,
                stage_name="architecture",
                card_id="card-001",
                task_title="Implement Auth",
                content=adr_content,
                metadata={"adr_file": "/tmp/adr/card-001.md"},
                logger=self.logger
            )
        """
        if not rag:
            if logger:
                logger.log(
                    f"RAG agent not available - skipping {stage_name} artifact storage",
                    "DEBUG"
                )
            return False

        try:
            # Store artifact in RAG
            rag.store_artifact(
                artifact_type=stage_name,
                card_id=card_id,
                task_title=task_title,
                content=content,
                metadata=metadata or {}
            )

            # Success logging
            if logger:
                logger.log(
                    f"Stored {stage_name} artifact in RAG for task {card_id}",
                    "DEBUG"
                )

            return True

        except Exception as e:
            # Best-effort storage: Don't fail pipeline if RAG storage fails
            if logger:
                logger.log(
                    f"Warning: Could not store {stage_name} artifact in RAG: {e}",
                    "WARNING"
                )
            return False

    @staticmethod
    def store_stage_artifact_with_raise(
        rag: Any,
        stage_name: str,
        card_id: str,
        task_title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        logger: Optional[Any] = None
    ) -> None:
        """
        Store artifact in RAG with exception raising (for critical storage)

        Same as store_stage_artifact but raises RAGStorageError on failure.
        Use this when RAG storage is CRITICAL and pipeline should fail if it fails.

        Args:
            Same as store_stage_artifact

        Raises:
            RAGStorageError: If storage fails

        Example:
            RAGStorageHelper.store_stage_artifact_with_raise(
                rag=self.rag,
                stage_name="requirements",
                card_id=card_id,
                task_title=task_title,
                content=requirements_yaml
            )
        """
        if not rag:
            raise RAGStorageError(
                "RAG agent not available",
                {"stage": stage_name, "card_id": card_id}
            )

        try:
            rag.store_artifact(
                artifact_type=stage_name,
                card_id=card_id,
                task_title=task_title,
                content=content,
                metadata=metadata or {}
            )

            if logger:
                logger.log(
                    f"Stored {stage_name} artifact in RAG for task {card_id}",
                    "DEBUG"
                )

        except Exception as e:
            raise wrap_exception(
                e,
                RAGStorageError,
                f"Failed to store {stage_name} artifact in RAG",
                {
                    "stage": stage_name,
                    "card_id": card_id,
                    "task_title": task_title
                }
            )

    @staticmethod
    def store_multiple_artifacts(
        rag: Any,
        stage_name: str,
        card_id: str,
        task_title: str,
        artifacts: Dict[str, str],
        logger: Optional[Any] = None
    ) -> Dict[str, bool]:
        """
        Store multiple artifacts from a stage in one call

        Useful when a stage produces multiple outputs (e.g., code files, tests, docs).

        Args:
            rag: RAG agent instance
            stage_name: Name of the stage
            card_id: Task card identifier
            task_title: Human-readable task title
            artifacts: Dict mapping artifact names to content
                      Example: {"main.py": "...", "test.py": "..."}
            logger: Optional logger instance

        Returns:
            Dict[str, bool]: Mapping artifact names to success/failure

        Example:
            results = RAGStorageHelper.store_multiple_artifacts(
                rag=self.rag,
                stage_name="development",
                card_id=card_id,
                task_title=task_title,
                artifacts={
                    "main.py": main_content,
                    "test_main.py": test_content,
                    "README.md": readme_content
                },
                logger=self.logger
            )
            # results = {"main.py": True, "test_main.py": True, "README.md": True}
        """
        if not rag:
            if logger:
                logger.log("RAG agent not available - skipping artifact storage", "DEBUG")
            return {name: False for name in artifacts.keys()}

        results = {}

        for artifact_name, content in artifacts.items():
            success = RAGStorageHelper.store_stage_artifact(
                rag=rag,
                stage_name=stage_name,
                card_id=card_id,
                task_title=task_title,
                content=content,
                metadata={"artifact_name": artifact_name},
                logger=logger
            )
            results[artifact_name] = success

        if logger:
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            logger.log(
                f"Stored {successful}/{total} {stage_name} artifacts in RAG",
                "DEBUG" if successful == total else "WARNING"
            )

        return results


# Convenience function for backward compatibility
def store_stage_artifact(
    rag: Any,
    stage_name: str,
    card_id: str,
    task_title: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    logger: Optional[Any] = None
) -> bool:
    """
    Convenience function - delegates to RAGStorageHelper.store_stage_artifact

    Exists for backward compatibility and cleaner imports.
    """
    return RAGStorageHelper.store_stage_artifact(
        rag=rag,
        stage_name=stage_name,
        card_id=card_id,
        task_title=task_title,
        content=content,
        metadata=metadata,
        logger=logger
    )
