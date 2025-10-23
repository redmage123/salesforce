#!/usr/bin/env python3
"""
Messenger Interface (SOLID: Dependency Inversion Principle)

Abstract interface for agent communication systems.
Allows pluggable implementations (file-based, RabbitMQ, Redis, etc.)
without changing dependent code.

This demonstrates:
- Dependency Inversion: High-level modules depend on abstractions, not concrete implementations
- Open/Closed: Open for extension (new messengers), closed for modification (interface stable)
- Interface Segregation: Focused interface with only essential methods
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class Message:
    """
    Standard message format for inter-agent communication

    This is the common message structure used by ALL messenger implementations.
    """
    protocol_version: str
    message_id: str
    timestamp: str
    from_agent: str
    to_agent: str
    message_type: str  # data_update, request, response, notification, error
    card_id: str
    priority: str  # high, medium, low
    data: Dict[str, Any]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        """Create from dictionary"""
        return cls(**data)


class MessengerInterface(ABC):
    """
    Abstract interface for agent messaging systems

    Any messenger implementation (file-based, RabbitMQ, Redis, etc.)
    must implement these methods.

    Benefits:
    - Swap messenger implementations without changing stage code
    - Test with mock messengers
    - Support multiple deployment environments
    - Maintain consistent API across implementations
    """

    @abstractmethod
    def send_message(
        self,
        to_agent: str,
        message_type: str,
        data: Dict,
        card_id: str,
        priority: str = "medium",
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Send message to another agent

        Args:
            to_agent: Recipient agent name (or "all" for broadcast)
            message_type: Type of message (data_update, request, response, notification, error)
            data: Message payload
            card_id: Associated card ID
            priority: Message priority (high, medium, low)
            metadata: Optional metadata

        Returns:
            Message ID
        """
        pass

    @abstractmethod
    def read_messages(
        self,
        message_type: Optional[str] = None,
        from_agent: Optional[str] = None,
        priority: Optional[str] = None,
        unread_only: bool = True,
        mark_as_read: bool = True
    ) -> List[Message]:
        """
        Read messages from inbox

        Args:
            message_type: Filter by message type
            from_agent: Filter by sender
            priority: Filter by priority
            unread_only: Only unread messages
            mark_as_read: Mark messages as read after retrieval

        Returns:
            List of Message objects
        """
        pass

    @abstractmethod
    def send_data_update(
        self,
        to_agent: str,
        card_id: str,
        update_type: str,
        data: Dict,
        priority: str = "medium"
    ) -> str:
        """
        Convenience method for sending data updates

        Args:
            to_agent: Recipient agent name
            card_id: Card ID
            update_type: Type of update
            data: Update data
            priority: Message priority

        Returns:
            Message ID
        """
        pass

    @abstractmethod
    def send_notification(
        self,
        to_agent: str,
        card_id: str,
        notification_type: str,
        data: Dict,
        priority: str = "low"
    ) -> str:
        """
        Convenience method for sending notifications

        Args:
            to_agent: Recipient agent name (or "all")
            card_id: Card ID
            notification_type: Type of notification
            data: Notification data
            priority: Message priority

        Returns:
            Message ID
        """
        pass

    @abstractmethod
    def send_error(
        self,
        to_agent: str,
        card_id: str,
        error_type: str,
        message: str,
        severity: str = "high",
        blocks_pipeline: bool = True,
        resolution_suggestions: Optional[List[str]] = None
    ) -> str:
        """
        Convenience method for sending errors

        Args:
            to_agent: Recipient agent name
            card_id: Card ID
            error_type: Type of error
            message: Error message
            severity: Error severity
            blocks_pipeline: Whether error blocks pipeline
            resolution_suggestions: Suggested resolutions

        Returns:
            Message ID
        """
        pass

    @abstractmethod
    def update_shared_state(self, card_id: str, updates: Dict):
        """
        Update shared pipeline state

        Args:
            card_id: Card ID
            updates: Dictionary of updates to apply
        """
        pass

    @abstractmethod
    def get_shared_state(self, card_id: str = None) -> Dict:
        """
        Get current shared pipeline state

        Args:
            card_id: Optional card ID to filter

        Returns:
            Shared state dictionary
        """
        pass

    @abstractmethod
    def register_agent(self, capabilities: List[str], status: str = "active"):
        """
        Register agent in agent registry

        Args:
            capabilities: List of agent capabilities
            status: Agent status (active, inactive, error)
        """
        pass

    @abstractmethod
    def cleanup(self):
        """
        Cleanup resources (close connections, delete temp files, etc.)

        Called when messenger is no longer needed.
        """
        pass

    @abstractmethod
    def get_messenger_type(self) -> str:
        """
        Get messenger implementation type

        Returns:
            Messenger type (e.g., "file", "rabbitmq", "redis")
        """
        pass


class MockMessenger(MessengerInterface):
    """
    Mock messenger for testing

    Stores messages in memory, doesn't persist anything.
    Useful for unit tests and development.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.sent_messages: List[Message] = []
        self.inbox: List[Message] = []
        self.shared_state: Dict = {}
        self.message_sequence = 0

    def send_message(
        self,
        to_agent: str,
        message_type: str,
        data: Dict,
        card_id: str,
        priority: str = "medium",
        metadata: Optional[Dict] = None
    ) -> str:
        """Send message (stores in memory)"""
        from datetime import datetime

        self.message_sequence += 1
        message = Message(
            protocol_version="1.0.0",
            message_id=f"mock-msg-{self.message_sequence}",
            timestamp=datetime.utcnow().isoformat() + 'Z',
            from_agent=self.agent_name,
            to_agent=to_agent,
            message_type=message_type,
            card_id=card_id,
            priority=priority,
            data=data,
            metadata=metadata or {}
        )

        self.sent_messages.append(message)
        return message.message_id

    def read_messages(
        self,
        message_type: Optional[str] = None,
        from_agent: Optional[str] = None,
        priority: Optional[str] = None,
        unread_only: bool = True,
        mark_as_read: bool = True
    ) -> List[Message]:
        """Read messages (from memory)"""
        return [m for m in self.inbox if
                (not message_type or m.message_type == message_type) and
                (not from_agent or m.from_agent == from_agent) and
                (not priority or m.priority == priority)]

    def send_data_update(
        self,
        to_agent: str,
        card_id: str,
        update_type: str,
        data: Dict,
        priority: str = "medium"
    ) -> str:
        """Send data update"""
        return self.send_message(
            to_agent=to_agent,
            message_type="data_update",
            card_id=card_id,
            priority=priority,
            data={"update_type": update_type, **data}
        )

    def send_notification(
        self,
        to_agent: str,
        card_id: str,
        notification_type: str,
        data: Dict,
        priority: str = "low"
    ) -> str:
        """Send notification"""
        return self.send_message(
            to_agent=to_agent,
            message_type="notification",
            card_id=card_id,
            priority=priority,
            data={"notification_type": notification_type, **data}
        )

    def send_error(
        self,
        to_agent: str,
        card_id: str,
        error_type: str,
        message: str,
        severity: str = "high",
        blocks_pipeline: bool = True,
        resolution_suggestions: Optional[List[str]] = None
    ) -> str:
        """Send error"""
        return self.send_message(
            to_agent=to_agent,
            message_type="error",
            card_id=card_id,
            priority="high",
            data={
                "error_type": error_type,
                "severity": severity,
                "message": message,
                "blocks_pipeline": blocks_pipeline,
                "resolution_suggestions": resolution_suggestions or []
            }
        )

    def update_shared_state(self, card_id: str, updates: Dict):
        """Update shared state (in memory)"""
        self.shared_state.update(updates)
        self.shared_state["card_id"] = card_id

    def get_shared_state(self, card_id: str = None) -> Dict:
        """Get shared state (from memory)"""
        if card_id and self.shared_state.get("card_id") != card_id:
            return {}
        return self.shared_state.copy()

    def register_agent(self, capabilities: List[str], status: str = "active"):
        """Register agent (no-op for mock)"""
        pass

    def cleanup(self):
        """Cleanup (no-op for mock)"""
        pass

    def get_messenger_type(self) -> str:
        """Get messenger type"""
        return "mock"
