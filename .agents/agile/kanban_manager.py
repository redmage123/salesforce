#!/usr/bin/env python3
"""
Kanban Board Management Utility
Provides functions for creating, moving, and updating cards on the Agile pipeline Kanban board.
"""

import json
import os
import warnings
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys

from artemis_exceptions import (
    KanbanBoardError,
    KanbanCardNotFoundError,
    FileReadError,
    FileWriteError,
    wrap_exception
)
from artemis_constants import KANBAN_BOARD_PATH

# Board file path (now using constant from artemis_constants)
BOARD_PATH = str(KANBAN_BOARD_PATH)


class CardBuilder:
    """
    Builder pattern for creating Kanban cards (Design Pattern: Builder)

    Reduces complexity from 9 parameters to 2 required parameters.
    Provides fluent API for optional parameters with validation.

    Usage:
        card = (CardBuilder("TASK-001", "Add feature")
            .with_description("Implement new API endpoint")
            .with_priority("high")
            .with_labels(["feature", "backend"])
            .with_story_points(8)
            .with_assigned_agents(["developer-a"])
            .build())
    """

    def __init__(self, task_id: str, title: str):
        """
        Initialize builder with required fields only

        Args:
            task_id: Unique task identifier
            title: Card title
        """
        self._card = {
            'task_id': task_id,
            'title': title,
            'description': '',
            # Sensible defaults
            'priority': 'medium',
            'labels': [],
            'size': 'medium',
            'story_points': 3,
            'assigned_agents': [],
            'acceptance_criteria': [],
            'blocked': False,
            'blocked_reason': None,
        }

    def with_description(self, description: str) -> 'CardBuilder':
        """Set card description"""
        self._card['description'] = description
        return self

    def with_priority(self, priority: str) -> 'CardBuilder':
        """
        Set priority level

        Args:
            priority: Must be 'high', 'medium', or 'low'

        Raises:
            ValueError: If priority is invalid
        """
        valid_priorities = ['high', 'medium', 'low']
        if priority not in valid_priorities:
            raise ValueError(
                f"Invalid priority: {priority}. Must be one of {valid_priorities}"
            )
        self._card['priority'] = priority
        return self

    def with_labels(self, labels: List[str]) -> 'CardBuilder':
        """Set card labels/tags"""
        self._card['labels'] = labels
        return self

    def with_size(self, size: str) -> 'CardBuilder':
        """
        Set card size

        Args:
            size: Must be 'small', 'medium', or 'large'

        Raises:
            ValueError: If size is invalid
        """
        valid_sizes = ['small', 'medium', 'large']
        if size not in valid_sizes:
            raise ValueError(
                f"Invalid size: {size}. Must be one of {valid_sizes}"
            )
        self._card['size'] = size
        return self

    def with_story_points(self, points: int) -> 'CardBuilder':
        """
        Set story points (Fibonacci scale)

        Args:
            points: Must be 1, 2, 3, 5, 8, or 13

        Raises:
            ValueError: If points not in Fibonacci scale
        """
        valid_points = [1, 2, 3, 5, 8, 13]
        if points not in valid_points:
            raise ValueError(
                f"Invalid story points: {points}. Must be Fibonacci: {valid_points}"
            )
        self._card['story_points'] = points
        return self

    def with_assigned_agents(self, agents: List[str]) -> 'CardBuilder':
        """Set assigned agents"""
        self._card['assigned_agents'] = agents
        return self

    def with_acceptance_criteria(self, criteria: List[Dict]) -> 'CardBuilder':
        """Set acceptance criteria"""
        self._card['acceptance_criteria'] = criteria
        return self

    def blocked(self, reason: str) -> 'CardBuilder':
        """Mark card as blocked with reason"""
        self._card['blocked'] = True
        self._card['blocked_reason'] = reason
        return self

    def build(self) -> Dict:
        """
        Build and return the complete card dictionary

        Returns:
            Complete card dictionary with all metadata
        """
        # Generate unique card ID
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        card_id = f"card-{timestamp}"

        # Add system-generated fields
        self._card.update({
            'card_id': card_id,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'moved_to_current_column_at': datetime.utcnow().isoformat() + 'Z',
            'current_column': 'backlog',
            'test_status': {
                'unit_tests_written': False,
                'unit_tests_passing': False,
                'integration_tests_written': False,
                'integration_tests_passing': False,
                'test_coverage_percent': 0
            },
            'definition_of_done': {
                'code_complete': False,
                'tests_passing': False,
                'code_reviewed': False,
                'documentation_updated': False,
                'deployed_to_production': False
            },
            'history': [
                {
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'action': 'created',
                    'column': 'backlog',
                    'agent': 'system',
                    'comment': 'Card created via CardBuilder'
                }
            ]
        })

        return self._card


class KanbanBoard:
    """Manages Kanban board operations"""

    def __init__(self, board_path: str = BOARD_PATH):
        self.board_path = board_path
        self.board = self._load_board()

    def _load_board(self) -> Dict:
        """Load board from JSON file"""
        if not os.path.exists(self.board_path):
            raise KanbanBoardError(
                f"Kanban board not found at {self.board_path}",
                context={"board_path": self.board_path}
            )

        try:
            with open(self.board_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise wrap_exception(
                e,
                FileReadError,
                f"Failed to read Kanban board",
                context={"board_path": self.board_path}
            )

    def _save_board(self) -> None:
        """Save board to JSON file"""
        self.board['last_updated'] = datetime.utcnow().isoformat() + 'Z'

        with open(self.board_path, 'w') as f:
            json.dump(self.board, f, indent=2)

    def _find_card(self, card_id: str) -> tuple[Optional[Dict], Optional[str]]:
        """Find a card by ID, return (card, column_id)"""
        for column in self.board['columns']:
            for card in column['cards']:
                if card['card_id'] == card_id:
                    return card, column['column_id']
        return None, None

    def _get_column(self, column_id: str) -> Optional[Dict]:
        """Get column by ID"""
        for column in self.board['columns']:
            if column['column_id'] == column_id:
                return column
        return None

    def new_card(self, task_id: str, title: str) -> CardBuilder:
        """
        Create a new card using Builder pattern (RECOMMENDED)

        Usage:
            card_dict = (board.new_card("TASK-001", "Add feature")
                .with_description("Implement API")
                .with_priority("high")
                .with_story_points(8)
                .build())

            board.add_card(card_dict)

        Args:
            task_id: Unique task identifier
            title: Card title

        Returns:
            CardBuilder instance for fluent API
        """
        return CardBuilder(task_id, title)

    def add_card(self, card: Dict) -> Dict:
        """
        Add a pre-built card to the backlog

        Args:
            card: Card dictionary (from CardBuilder.build())

        Returns:
            Added card dictionary

        Raises:
            KanbanBoardError: If backlog column not found
        """
        backlog = self._get_column("backlog")
        if not backlog:
            raise KanbanBoardError(
                "Backlog column not found",
                context={"board_path": self.board_path}
            )

        backlog['cards'].append(card)
        self._save_board()
        return card

    def create_card(
        self,
        task_id: str,
        title: str,
        description: str,
        priority: str = "medium",
        labels: List[str] = None,
        size: str = "medium",
        story_points: int = 3,
        assigned_agents: List[str] = None,
        acceptance_criteria: List[Dict] = None
    ) -> Dict:
        """
        Create a new card in the Backlog column

        ⚠️  DEPRECATED: Use new_card() with Builder pattern instead
            This method will be removed in Artemis 3.0

            Old way:
                card = board.create_card("TASK-001", "Title", "Description",
                                        priority="high", story_points=8)

            New way (RECOMMENDED):
                card = (board.new_card("TASK-001", "Title")
                    .with_description("Description")
                    .with_priority("high")
                    .with_story_points(8)
                    .build())
                board.add_card(card)

        Args:
            task_id: Unique task identifier
            title: Card title
            description: Detailed description
            priority: high|medium|low
            labels: List of label tags
            size: small|medium|large
            story_points: Fibonacci scale (1,2,3,5,8,13)
            assigned_agents: List of agent names
            acceptance_criteria: List of {criterion, status, verified_by}

        Returns:
            Created card dictionary
        """
        warnings.warn(
            "create_card() with 9 parameters is deprecated. "
            "Use new_card() with Builder pattern instead. "
            "See method docstring for migration example.",
            DeprecationWarning,
            stacklevel=2
        )
        # Generate card ID
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        card_id = f"card-{timestamp}"

        # Create card
        card = {
            "card_id": card_id,
            "task_id": task_id,
            "title": title,
            "description": description,
            "priority": priority,
            "labels": labels or [],
            "size": size,
            "story_points": story_points,
            "created_at": datetime.utcnow().isoformat() + 'Z',
            "moved_to_current_column_at": datetime.utcnow().isoformat() + 'Z',
            "assigned_agents": assigned_agents or [],
            "current_column": "backlog",
            "blocked": False,
            "blocked_reason": None,
            "test_status": {
                "unit_tests_written": False,
                "unit_tests_passing": False,
                "integration_tests_written": False,
                "integration_tests_passing": False,
                "test_coverage_percent": 0
            },
            "acceptance_criteria": acceptance_criteria or [],
            "definition_of_done": {
                "code_complete": False,
                "tests_passing": False,
                "code_reviewed": False,
                "documentation_updated": False,
                "deployed_to_production": False
            },
            "history": [
                {
                    "timestamp": datetime.utcnow().isoformat() + 'Z',
                    "action": "created",
                    "column": "backlog",
                    "agent": "system",
                    "comment": "Card created"
                }
            ]
        }

        # Add to backlog
        backlog = self._get_column("backlog")
        if backlog:
            backlog['cards'].append(card)
            self._save_board()
            print(f"✅ Created card {card_id}: {title}")
            return card
        else:
            raise KanbanBoardError(
                "Backlog column not found in Kanban board",
                context={"available_columns": [c['column_id'] for c in self.board['columns']]}
            )

    def move_card(
        self,
        card_id: str,
        to_column: str,
        agent: str = "system",
        comment: str = ""
    ) -> bool:
        """
        Move a card to a different column

        Args:
            card_id: Card to move
            to_column: Destination column ID
            agent: Agent performing the move
            comment: Optional comment

        Returns:
            True if successful
        """
        card, from_column = self._find_card(card_id)
        if not card:
            print(f"❌ Card {card_id} not found")
            return False

        to_col = self._get_column(to_column)
        if not to_col:
            print(f"❌ Column {to_column} not found")
            return False

        # Check WIP limit
        if to_col['wip_limit'] is not None:
            if len(to_col['cards']) >= to_col['wip_limit']:
                print(f"⚠️  WIP limit exceeded for {to_column} ({len(to_col['cards'])}/{to_col['wip_limit']})")
                self.board['metrics']['wip_violations_count'] += 1

        # Remove from current column
        from_col = self._get_column(from_column)
        if from_col:
            from_col['cards'] = [c for c in from_col['cards'] if c['card_id'] != card_id]

        # Add to new column
        card['current_column'] = to_column
        card['moved_to_current_column_at'] = datetime.utcnow().isoformat() + 'Z'

        # Add history entry
        card['history'].append({
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "action": "moved",
            "from_column": from_column,
            "to_column": to_column,
            "agent": agent,
            "comment": comment or f"Moved from {from_column} to {to_column}"
        })

        to_col['cards'].append(card)

        # Update metrics if moved to done
        if to_column == "done":
            from datetime import timezone
            card['completed_at'] = datetime.utcnow().isoformat() + 'Z'

            # Calculate cycle time
            created = datetime.fromisoformat(card['created_at'].replace('Z', '+00:00'))
            completed = datetime.now(timezone.utc)
            cycle_time_hours = (completed - created).total_seconds() / 3600
            card['cycle_time_hours'] = round(cycle_time_hours, 2)

            # Update board metrics
            self._update_metrics()

        self._save_board()
        print(f"✅ Moved card {card_id} from {from_column} to {to_column}")
        return True

    def update_card(
        self,
        card_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update card fields

        Args:
            card_id: Card to update
            updates: Dictionary of field updates

        Returns:
            True if successful
        """
        card, column = self._find_card(card_id)
        if not card:
            print(f"❌ Card {card_id} not found")
            return False

        # Update fields
        for key, value in updates.items():
            if key in card:
                card[key] = value

        self._save_board()
        print(f"✅ Updated card {card_id}")
        return True

    def block_card(
        self,
        card_id: str,
        reason: str,
        agent: str = "system"
    ) -> bool:
        """
        Mark a card as blocked and move to Blocked column

        Args:
            card_id: Card to block
            reason: Reason for blocking
            agent: Agent reporting the block

        Returns:
            True if successful
        """
        card, from_column = self._find_card(card_id)
        if not card:
            print(f"❌ Card {card_id} not found")
            return False

        card['blocked'] = True
        card['blocked_reason'] = reason

        self.move_card(card_id, "blocked", agent, f"BLOCKED: {reason}")

        # Update metrics
        self.board['metrics']['blocked_items_count'] = len(self._get_column("blocked")['cards'])
        self._save_board()

        print(f"🚫 Blocked card {card_id}: {reason}")
        return True

    def unblock_card(
        self,
        card_id: str,
        move_to_column: str,
        agent: str = "system",
        resolution: str = ""
    ) -> bool:
        """
        Unblock a card and move to specified column

        Args:
            card_id: Card to unblock
            move_to_column: Where to move the card
            agent: Agent unblocking
            resolution: How the block was resolved

        Returns:
            True if successful
        """
        card, column = self._find_card(card_id)
        if not card or column != "blocked":
            print(f"❌ Card {card_id} not in blocked column")
            return False

        card['blocked'] = False
        old_reason = card['blocked_reason']
        card['blocked_reason'] = None

        self.move_card(card_id, move_to_column, agent, f"UNBLOCKED: {resolution}")

        # Update metrics
        self.board['metrics']['blocked_items_count'] = len(self._get_column("blocked")['cards'])
        self._save_board()

        print(f"✅ Unblocked card {card_id} (was: {old_reason})")
        return True

    def update_test_status(
        self,
        card_id: str,
        test_status: Dict[str, Any]
    ) -> bool:
        """
        Update test status for a card

        Args:
            card_id: Card to update
            test_status: Dictionary with test status fields

        Returns:
            True if successful
        """
        card, column = self._find_card(card_id)
        if not card:
            print(f"❌ Card {card_id} not found")
            return False

        card['test_status'].update(test_status)
        self._save_board()

        print(f"✅ Updated test status for card {card_id}")
        return True

    def verify_acceptance_criterion(
        self,
        card_id: str,
        criterion_index: int,
        verified_by: str
    ) -> bool:
        """
        Mark an acceptance criterion as verified

        Args:
            card_id: Card ID
            criterion_index: Index of criterion to verify
            verified_by: Agent verifying

        Returns:
            True if successful
        """
        card, column = self._find_card(card_id)
        if not card:
            print(f"❌ Card {card_id} not found")
            return False

        if criterion_index >= len(card['acceptance_criteria']):
            print(f"❌ Criterion index {criterion_index} out of range")
            return False

        card['acceptance_criteria'][criterion_index]['status'] = 'verified'
        card['acceptance_criteria'][criterion_index]['verified_by'] = verified_by

        self._save_board()
        print(f"✅ Verified acceptance criterion for card {card_id}")
        return True

    def _update_metrics(self) -> None:
        """Recalculate board metrics"""
        done_column = self._get_column("done")
        if not done_column:
            return

        done_cards = done_column['cards']

        if done_cards:
            cycle_times = [c.get('cycle_time_hours', 0) for c in done_cards if 'cycle_time_hours' in c]
            if cycle_times:
                self.board['metrics']['cycle_time_avg_hours'] = round(sum(cycle_times) / len(cycle_times), 2)
                self.board['metrics']['cycle_time_min_hours'] = round(min(cycle_times), 2)
                self.board['metrics']['cycle_time_max_hours'] = round(max(cycle_times), 2)

            self.board['metrics']['cards_completed'] = len(done_cards)
            self.board['metrics']['throughput_current_sprint'] = len(done_cards)

            # Calculate velocity
            velocity = sum(c.get('story_points', 0) for c in done_cards)
            self.board['metrics']['velocity_current_sprint'] = velocity

            if self.board.get('current_sprint'):
                self.board['current_sprint']['completed_story_points'] = velocity

    def get_board_summary(self) -> Dict:
        """Get summary of board status"""
        summary = {
            "board_id": self.board['board_id'],
            "last_updated": self.board['last_updated'],
            "columns": []
        }

        for column in self.board['columns']:
            summary['columns'].append({
                "name": column['name'],
                "column_id": column['column_id'],
                "card_count": len(column['cards']),
                "wip_limit": column['wip_limit'],
                "cards": [
                    {
                        "card_id": c['card_id'],
                        "title": c['title'],
                        "priority": c['priority'],
                        "blocked": c.get('blocked', False)
                    }
                    for c in column['cards']
                ]
            })

        summary['metrics'] = self.board['metrics']
        summary['current_sprint'] = self.board.get('current_sprint')

        return summary

    def print_board(self) -> None:
        """Print visual representation of board"""
        print("\n" + "="*80)
        print(f"  KANBAN BOARD: {self.board['board_id']}")
        print(f"  Last Updated: {self.board['last_updated']}")
        if self.board.get('current_sprint'):
            sprint = self.board['current_sprint']
            print(f"  Sprint: {sprint['sprint_id']} ({sprint['completed_story_points']}/{sprint['committed_story_points']} points)")
        print("="*80)

        for column in self.board['columns']:
            wip_info = f"(WIP: {len(column['cards'])}/{column['wip_limit']})" if column['wip_limit'] else f"({len(column['cards'])})"
            print(f"\n📋 {column['name']} {wip_info}")
            print("-" * 80)

            if not column['cards']:
                print("  (empty)")
            else:
                for card in column['cards']:
                    blocked_indicator = "🚫 " if card.get('blocked', False) else ""
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(card['priority'], "⚪")
                    print(f"  {blocked_indicator}{priority_emoji} {card['card_id']} - {card['title']}")
                    print(f"     Priority: {card['priority']} | Points: {card.get('story_points', 'N/A')} | Agents: {', '.join(card['assigned_agents'][:2])}")
                    if card.get('test_status'):
                        coverage = card['test_status'].get('test_coverage_percent', 0)
                        print(f"     Tests: {coverage}% coverage")

        print("\n" + "="*80)
        print("METRICS")
        print("="*80)
        metrics = self.board['metrics']
        print(f"  Cycle Time: {metrics.get('cycle_time_avg_hours', 0):.2f}h avg")
        print(f"  Throughput: {metrics.get('throughput_current_sprint', 0)} cards this sprint")
        print(f"  Velocity: {metrics.get('velocity_current_sprint', 0)} story points")
        print(f"  Blocked: {metrics.get('blocked_items_count', 0)} items")
        print(f"  WIP Violations: {metrics.get('wip_violations_count', 0)}")
        print("="*80 + "\n")


def main():
    """CLI interface for Kanban board"""
    if len(sys.argv) < 2:
        print("Usage: kanban_manager.py <command> [args]")
        print("\nCommands:")
        print("  create <task_id> <title> - Create new card")
        print("  move <card_id> <to_column> - Move card")
        print("  block <card_id> <reason> - Block card")
        print("  unblock <card_id> <to_column> - Unblock card")
        print("  show - Display board")
        print("  summary - Show board summary")
        sys.exit(1)

    board = KanbanBoard()
    command = sys.argv[1]

    if command == "create":
        if len(sys.argv) < 4:
            print("Usage: create <task_id> <title>")
            sys.exit(1)
        task_id = sys.argv[2]
        title = ' '.join(sys.argv[3:])
        board.create_card(task_id, title, "Created via CLI")

    elif command == "move":
        if len(sys.argv) < 4:
            print("Usage: move <card_id> <to_column>")
            sys.exit(1)
        card_id = sys.argv[2]
        to_column = sys.argv[3]
        board.move_card(card_id, to_column, "cli")

    elif command == "block":
        if len(sys.argv) < 4:
            print("Usage: block <card_id> <reason>")
            sys.exit(1)
        card_id = sys.argv[2]
        reason = ' '.join(sys.argv[3:])
        board.block_card(card_id, reason, "cli")

    elif command == "unblock":
        if len(sys.argv) < 4:
            print("Usage: unblock <card_id> <to_column>")
            sys.exit(1)
        card_id = sys.argv[2]
        to_column = sys.argv[3]
        board.unblock_card(card_id, to_column, "cli", "Resolved via CLI")

    elif command == "show":
        board.print_board()

    elif command == "summary":
        summary = board.get_board_summary()
        print(json.dumps(summary, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
