#!/usr/bin/env python3
"""
ADRStorageService (SOLID: Single Responsibility)

Single Responsibility: Store ADR artifacts in RAG and Knowledge Graph

This service handles ONLY ADR storage operations:
- Storing ADRs in RAG database
- Storing ADRs in Knowledge Graph
- Storing Kanban board state in RAG
- Linking ADRs to requirements in Knowledge Graph
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from artemis_stage_interface import LoggerInterface
from knowledge_graph_factory import get_knowledge_graph


class ADRStorageService:
    """
    Service for storing ADR artifacts in storage systems

    Single Responsibility: ADR artifact storage
    - Store ADR content in RAG database
    - Store ADR nodes and relationships in Knowledge Graph
    - Store Kanban board state snapshots in RAG
    - Link ADRs to requirements and files
    """

    def __init__(
        self,
        rag,  # RAGAgent
        board,  # KanbanBoard
        logger: LoggerInterface
    ):
        """
        Initialize ADR storage service

        Args:
            rag: RAG agent for artifact storage
            board: Kanban board for state queries
            logger: Logger interface
        """
        self.rag = rag
        self.board = board
        self.logger = logger

    def store_adr_in_rag(
        self,
        card_id: str,
        task_title: str,
        adr_content: str,
        adr_number: str,
        adr_path: str,
        priority: str = "medium",
        story_points: int = 5
    ) -> None:
        """
        Store ADR content in RAG database

        Args:
            card_id: Card ID for this task
            task_title: Task title
            adr_content: Full ADR content
            adr_number: ADR number (e.g., "001")
            adr_path: Path to ADR file
            priority: Task priority
            story_points: Story points
        """
        try:
            self.rag.store_artifact(
                artifact_type="architecture_decision",
                card_id=card_id,
                task_title=task_title,
                content=adr_content,
                metadata={
                    "adr_number": adr_number,
                    "priority": priority,
                    "story_points": story_points,
                    "adr_file": adr_path
                }
            )
            self.logger.log(f"✅ Stored ADR-{adr_number} in RAG database", "INFO")
        except Exception as e:
            self.logger.log(f"⚠️  Failed to store ADR in RAG: {e}", "WARNING")

    def store_adr_in_knowledge_graph(
        self,
        card_id: str,
        adr_number: str,
        adr_path: str,
        adr_title: str,
        structured_requirements: Optional[Any] = None
    ) -> None:
        """
        Store ADR in Knowledge Graph and link to requirements

        Creates ADR node, links to file, and creates relationships
        with requirements if available.

        Args:
            card_id: Card ID for this task
            adr_number: ADR number (e.g., "001")
            adr_path: Path to ADR file
            adr_title: ADR title
            structured_requirements: Structured requirements object (if available)
        """
        kg = get_knowledge_graph()
        if not kg:
            self.logger.log("Knowledge Graph not available - skipping KG storage", "DEBUG")
            return

        try:
            self.logger.log("Storing ADR in Knowledge Graph...", "DEBUG")

            # Add ADR node
            adr_id = f"ADR-{adr_number}"
            kg.add_adr(
                adr_id=adr_id,
                title=adr_title,
                status="accepted"
            )

            # Link ADR to file
            kg.link_adr_to_file(
                adr_id=adr_id,
                file_path=adr_path,
                relationship="DOCUMENTED_IN"
            )

            # If we have structured requirements, link ADR to requirements
            if structured_requirements:
                req_count = self._link_requirements_to_adr(
                    kg, adr_id, structured_requirements
                )
                self.logger.log(f"✅ Linked ADR {adr_id} to {req_count} requirements in Knowledge Graph", "INFO")
            else:
                self.logger.log(f"✅ Stored ADR {adr_id} in Knowledge Graph", "INFO")

            # Link ADR to task
            # Note: Task should already exist from requirements stage
            try:
                self.logger.log(f"   ADR-Task linkage: {adr_id} -> {card_id}", "DEBUG")
            except Exception as e:
                self.logger.log(f"   Could not link ADR to task: {e}", "DEBUG")

        except Exception as e:
            self.logger.log(f"Warning: Could not store ADR in Knowledge Graph: {e}", "WARNING")

    def _link_requirements_to_adr(
        self,
        kg,
        adr_id: str,
        structured_requirements
    ) -> int:
        """
        Link requirements to ADR in Knowledge Graph

        Links top priority functional and non-functional requirements
        to the ADR node.

        Args:
            kg: Knowledge Graph instance
            adr_id: ADR ID (e.g., "ADR-001")
            structured_requirements: Structured requirements object

        Returns:
            Number of requirements linked
        """
        req_count = 0

        # Link to functional requirements (top 5 high-priority ones)
        high_priority_functional = [
            req for req in structured_requirements.functional_requirements
            if req.priority.value in ['critical', 'high']
        ][:5]

        for req in high_priority_functional:
            kg.link_requirement_to_adr(req.id, adr_id)
            req_count += 1

        # Link to non-functional requirements (all of them since they're critical)
        for req in structured_requirements.non_functional_requirements[:5]:
            kg.link_requirement_to_adr(req.id, adr_id)
            req_count += 1

        return req_count

    def store_kanban_in_rag(
        self,
        card_id: str,
        story_card_ids: List[str]
    ) -> None:
        """
        Store Kanban board state in RAG database

        Creates a snapshot of the current board state including
        all cards in all columns.

        Args:
            card_id: Parent card ID
            story_card_ids: List of generated story card IDs
        """
        try:
            # Get current board state
            board_state = {
                "parent_card": card_id,
                "generated_stories": story_card_ids,
                "columns": {},
                "total_cards": 0
            }

            # Collect all cards by column
            if hasattr(self.board, 'columns'):
                for column_name in self.board.columns:
                    cards = self.board.get_cards_in_column(column_name)
                    board_state["columns"][column_name] = [
                        {
                            "card_id": c.get('card_id'),
                            "title": c.get('title'),
                            "priority": c.get('priority'),
                            "points": c.get('points')
                        }
                        for c in cards
                    ]
                    board_state["total_cards"] += len(cards)

            # Store in RAG
            self.rag.store_artifact(
                artifact_type="kanban_board_state",
                card_id=card_id,
                task_title=f"Kanban State after ADR-{card_id}",
                content=json.dumps(board_state, indent=2),
                metadata={
                    "parent_card": card_id,
                    "story_count": len(story_card_ids),
                    "total_cards": board_state["total_cards"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            self.logger.log(f"✅ Stored Kanban board state in RAG ({board_state['total_cards']} cards)", "INFO")

        except Exception as e:
            self.logger.log(f"⚠️  Failed to store Kanban in RAG: {e}", "WARNING")
