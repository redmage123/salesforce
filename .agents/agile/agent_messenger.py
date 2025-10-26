#!/usr/bin/env python3
"""
Agent Messenger - File-Based Inter-Agent Communication System

File-based implementation of MessengerInterface.
Uses JSON files for message passing and shared state storage.

Provides standardized communication protocol for all pipeline agents.
Agents can send/receive messages, update shared state, and coordinate actions.
"""

import json
import os
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from messenger_interface import MessengerInterface, Message


class AgentMessenger(MessengerInterface):
    """
    Handle inter-agent communication

    Usage:
        messenger = AgentMessenger("architecture-agent")

        # Send message
        messenger.send_message(
            to_agent="dependency-validation-agent",
            message_type="data_update",
            card_id="card-123",
            data={"adr_file": "/tmp/adr/ADR-001.md"}
        )

        # Read messages
        messages = messenger.read_messages()

        # Update shared state
        messenger.update_shared_state(
            card_id="card-123",
            updates={"adr_file": "/tmp/adr/ADR-001.md"}
        )
    """

    PROTOCOL_VERSION = "1.0.0"

    def __init__(self, agent_name: str, message_dir: str = "../../.artemis_data/agent_messages"):
        self.agent_name = agent_name

        # Convert relative path to absolute
        if not os.path.isabs(message_dir):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            message_dir = os.path.join(script_dir, message_dir)

        self.message_dir = Path(message_dir)
        self.message_dir.mkdir(exist_ok=True, parents=True)

        # Agent's inbox
        self.inbox = self.message_dir / agent_name
        self.inbox.mkdir(exist_ok=True)

        # Message counter for sequence
        self.message_sequence = 0

    def _generate_message_id(self, data: Dict) -> str:
        """Generate unique message ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        data_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()[:8]
        self.message_sequence += 1
        return f"msg-{timestamp}-{self.agent_name}-{self.message_sequence}-{data_hash}"

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
            to_agent: Recipient agent name
            message_type: Type of message (data_update, request, response, notification, error)
            data: Message payload
            card_id: Associated card ID
            priority: Message priority (high, medium, low)
            metadata: Optional metadata

        Returns:
            Message ID
        """
        message = Message(
            protocol_version=self.PROTOCOL_VERSION,
            message_id=self._generate_message_id(data),
            timestamp=datetime.utcnow().isoformat() + 'Z',
            from_agent=self.agent_name,
            to_agent=to_agent,
            message_type=message_type,
            card_id=card_id,
            priority=priority,
            data=data,
            metadata=metadata or {}
        )

        # Save to recipient's inbox (or broadcast)
        if to_agent == "all":
            # Broadcast to all agents
            self._broadcast_message(message)
        else:
            self._save_message(to_agent, message)

        # Log the send
        self._log_message(message, direction="sent")

        return message.message_id

    def _save_message(self, to_agent: str, message: Message):
        """Save message to recipient's inbox"""
        recipient_inbox = self.message_dir / to_agent
        recipient_inbox.mkdir(exist_ok=True)

        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{self.agent_name}_to_{to_agent}_{message.message_type}.json"
        filepath = recipient_inbox / filename

        with open(filepath, 'w') as f:
            json.dump(message.to_dict(), f, indent=2)

    def _broadcast_message(self, message: Message):
        """Broadcast message to all registered agents"""
        registry = self._get_agent_registry()

        for agent_name in registry.get('agents', {}).keys():
            if agent_name != self.agent_name:
                self._save_message(agent_name, message)

    def _log_message(self, message: Message, direction: str):
        """Log message for audit trail"""
        log_dir = self.message_dir / "logs"
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"{self.agent_name}.log"

        with open(log_file, 'a') as f:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "direction": direction,
                "message_id": message.message_id,
                "message_type": message.message_type,
                "from_agent": message.from_agent,
                "to_agent": message.to_agent,
                "card_id": message.card_id
            }
            f.write(json.dumps(log_entry) + '\n')

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
        messages = []

        # Get message files
        pattern = "*.json" if unread_only else "*.json*"
        message_files = sorted(self.inbox.glob(pattern))

        for filepath in message_files:
            # Skip .read files if unread_only
            if unread_only and filepath.suffix == '.read':
                continue

            try:
                with open(filepath) as f:
                    message_data = json.load(f)

                message = Message.from_dict(message_data)

                # Apply filters
                if message_type and message.message_type != message_type:
                    continue

                if from_agent and message.from_agent != from_agent:
                    continue

                if priority and message.priority != priority:
                    continue

                messages.append(message)

                # Mark as read
                if mark_as_read and not filepath.name.endswith('.read'):
                    new_path = filepath.with_suffix('.json.read')
                    filepath.rename(new_path)

                # Log the read
                self._log_message(message, direction="received")

            except Exception as e:
                print(f"Error reading message {filepath}: {e}")
                continue

        # Sort by priority (high first)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        messages.sort(key=lambda m: priority_order.get(m.priority, 1))

        return messages

    def send_data_update(
        self,
        to_agent: str,
        card_id: str,
        update_type: str,
        data: Dict,
        priority: str = "medium"
    ) -> str:
        """Convenience method for sending data updates"""
        return self.send_message(
            to_agent=to_agent,
            message_type="data_update",
            card_id=card_id,
            priority=priority,
            data={
                "update_type": update_type,
                **data
            }
        )

    def send_request(
        self,
        to_agent: str,
        card_id: str,
        request_type: str,
        requirements: Dict,
        timeout_seconds: int = 300,
        priority: str = "medium"
    ) -> str:
        """Convenience method for sending requests"""
        return self.send_message(
            to_agent=to_agent,
            message_type="request",
            card_id=card_id,
            priority=priority,
            data={
                "request_type": request_type,
                "requirements": requirements
            },
            metadata={
                "requires_response": True,
                "timeout_seconds": timeout_seconds
            }
        )

    def send_response(
        self,
        to_agent: str,
        card_id: str,
        in_response_to: str,
        response_type: str,
        data: Dict,
        priority: str = "medium"
    ) -> str:
        """Convenience method for sending responses"""
        return self.send_message(
            to_agent=to_agent,
            message_type="response",
            card_id=card_id,
            priority=priority,
            data={
                "response_type": response_type,
                "in_response_to": in_response_to,
                **data
            }
        )

    def send_notification(
        self,
        to_agent: str,
        card_id: str,
        notification_type: str,
        data: Dict,
        priority: str = "low"
    ) -> str:
        """Convenience method for sending notifications"""
        return self.send_message(
            to_agent=to_agent,
            message_type="notification",
            card_id=card_id,
            priority=priority,
            data={
                "notification_type": notification_type,
                **data
            }
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
        """Convenience method for sending errors"""
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
        """
        Update shared pipeline state

        Args:
            card_id: Card ID
            updates: Dictionary of updates to apply
        """
        state_file = Path("/tmp/pipeline_state.json")

        # Load existing state
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
        else:
            state = {
                "card_id": card_id,
                "agent_statuses": {},
                "shared_data": {}
            }

        # Update with new data
        for key, value in updates.items():
            if key == "agent_status":
                state["agent_statuses"][self.agent_name] = value
            else:
                state["shared_data"][key] = value

        state["last_updated"] = datetime.utcnow().isoformat() + 'Z'
        state["updated_by"] = self.agent_name

        # Save
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def get_shared_state(self, card_id: str = None) -> Dict:
        """
        Get current shared pipeline state

        Args:
            card_id: Optional card ID to filter

        Returns:
            Shared state dictionary
        """
        state_file = Path("/tmp/pipeline_state.json")

        if not state_file.exists():
            return {}

        with open(state_file) as f:
            state = json.load(f)

        # Filter by card_id if provided
        if card_id and state.get("card_id") != card_id:
            return {}

        return state

    def register_agent(self, capabilities: List[str], status: str = "active"):
        """
        Register agent in agent registry

        Args:
            capabilities: List of agent capabilities
            status: Agent status (active, inactive, error)
        """
        registry_file = Path("/tmp/agent_registry.json")

        # Load registry
        if registry_file.exists():
            with open(registry_file) as f:
                registry = json.load(f)
        else:
            registry = {"agents": {}}

        # Register this agent
        registry["agents"][self.agent_name] = {
            "status": status,
            "capabilities": capabilities,
            "message_endpoint": str(self.inbox),
            "last_heartbeat": datetime.utcnow().isoformat() + 'Z'
        }

        # Save registry
        with open(registry_file, 'w') as f:
            json.dump(registry, f, indent=2)

    def _get_agent_registry(self) -> Dict:
        """Get agent registry"""
        registry_file = Path("/tmp/agent_registry.json")

        if not registry_file.exists():
            return {"agents": {}}

        with open(registry_file) as f:
            return json.load(f)

    def send_heartbeat(self):
        """Send heartbeat to update agent status"""
        registry_file = Path("/tmp/agent_registry.json")

        if not registry_file.exists():
            return

        with open(registry_file) as f:
            registry = json.load(f)

        if self.agent_name in registry["agents"]:
            registry["agents"][self.agent_name]["last_heartbeat"] = (
                datetime.utcnow().isoformat() + 'Z'
            )

            with open(registry_file, 'w') as f:
                json.dump(registry, f, indent=2)

    def cleanup_old_messages(self, days: int = 7):
        """
        Clean up old read messages

        Args:
            days: Delete messages older than this many days
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        for filepath in self.inbox.glob("*.json.read"):
            # Check file modification time
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            if mtime < cutoff:
                filepath.unlink()

    def cleanup(self):
        """
        Cleanup resources (MessengerInterface implementation)

        For file-based messenger, this can optionally clean up old messages.
        """
        # Optional: Clean up old messages (7+ days old)
        self.cleanup_old_messages(days=7)

    def get_messenger_type(self) -> str:
        """
        Get messenger implementation type (MessengerInterface implementation)

        Returns:
            "file" - indicating file-based messenger
        """
        return "file"


# Convenience functions for quick usage

def send_update(from_agent: str, to_agent: str, card_id: str, **data):
    """Quick send data update"""
    messenger = AgentMessenger(from_agent)
    return messenger.send_data_update(to_agent, card_id, "update", data)


def send_notification(from_agent: str, card_id: str, **data):
    """Quick send broadcast notification"""
    messenger = AgentMessenger(from_agent)
    return messenger.send_notification("all", card_id, "notification", data)


def send_error(from_agent: str, to_agent: str, card_id: str, error: str):
    """Quick send error"""
    messenger = AgentMessenger(from_agent)
    return messenger.send_error(to_agent, card_id, "error", error)


if __name__ == "__main__":
    # Example usage
    print("Agent Messenger - Example Usage")
    print("=" * 60)

    # Create messenger for architecture agent
    arch = AgentMessenger("architecture-agent")

    # Register agent
    arch.register_agent(capabilities=[
        "create_adr",
        "evaluate_options",
        "document_decisions"
    ])

    # Send data update
    msg_id = arch.send_data_update(
        to_agent="dependency-validation-agent",
        card_id="card-123",
        update_type="adr_created",
        data={
            "adr_file": "/tmp/adr/ADR-001.md",
            "dependencies": ["chromadb>=0.4.0"]
        }
    )
    print(f"✅ Sent message: {msg_id}")

    # Update shared state
    arch.update_shared_state(
        card_id="card-123",
        updates={
            "agent_status": "COMPLETE",
            "adr_file": "/tmp/adr/ADR-001.md"
        }
    )
    print("✅ Updated shared state")

    # Read messages (as dependency validation agent)
    dep_val = AgentMessenger("dependency-validation-agent")
    messages = dep_val.read_messages()
    print(f"✅ Read {len(messages)} messages")

    for msg in messages:
        print(f"\n  From: {msg.from_agent}")
        print(f"  Type: {msg.message_type}")
        print(f"  Data: {msg.data}")

    # Get shared state
    state = dep_val.get_shared_state(card_id="card-123")
    print(f"\n✅ Shared state:")
    print(f"  ADR File: {state.get('shared_data', {}).get('adr_file')}")

    print("\n" + "=" * 60)
    print("Example complete!")
