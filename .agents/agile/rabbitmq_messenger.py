#!/usr/bin/env python3
"""
RabbitMQ Messenger - Distributed Inter-Agent Communication

RabbitMQ-based implementation of MessengerInterface.
Uses RabbitMQ message broker for distributed message passing.

Benefits over file-based:
- Distributed: Agents can run on different machines
- Guaranteed delivery: Messages persist until acknowledged
- Real-time: Push-based, no polling required
- Scalable: Multiple agent instances can share work
- Load balancing: Round-robin across worker pools

Requirements:
    pip install pika
    docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    import pika
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False
    pika = None  # type: ignore

from messenger_interface import MessengerInterface, Message


class RabbitMQMessenger(MessengerInterface):
    """
    RabbitMQ-based messenger for distributed agent communication

    Usage:
        messenger = RabbitMQMessenger(
            agent_name="architecture-agent",
            rabbitmq_url="amqp://localhost"
        )

        # Send message
        messenger.send_message(
            to_agent="dependency-validation-agent",
            message_type="data_update",
            card_id="card-123",
            data={"adr_file": "/tmp/adr/ADR-001.md"}
        )

        # Read messages (blocking, waits for messages)
        def handle_message(message):
            print(f"Received: {message.data}")

        messenger.start_consuming(callback=handle_message)
    """

    def __init__(
        self,
        agent_name: str,
        rabbitmq_url: str = "amqp://localhost",
        durable: bool = True,
        prefetch_count: int = 1
    ):
        """
        Initialize RabbitMQ messenger

        Args:
            agent_name: Name of this agent
            rabbitmq_url: RabbitMQ connection URL
            durable: Whether queues/messages persist across restarts
            prefetch_count: How many unacknowledged messages to buffer
        """
        if not RABBITMQ_AVAILABLE:
            raise ImportError(
                "RabbitMQ messenger requires 'pika' package. "
                "Install with: pip install pika"
            )

        self.agent_name = agent_name
        self.rabbitmq_url = rabbitmq_url
        self.durable = durable
        self.prefetch_count = prefetch_count

        # Connect to RabbitMQ
        self.connection = pika.BlockingConnection(
            pika.URLParameters(rabbitmq_url)
        )
        self.channel = self.connection.channel()

        # Set QoS (prefetch count)
        self.channel.basic_qos(prefetch_count=prefetch_count)

        # Create agent's queue
        self.queue_name = f"artemis.agent.{agent_name}"
        self.channel.queue_declare(
            queue=self.queue_name,
            durable=durable
        )

        # Create broadcast exchange (fanout)
        self.broadcast_exchange = "artemis.broadcast"
        self.channel.exchange_declare(
            exchange=self.broadcast_exchange,
            exchange_type='fanout',
            durable=durable
        )

        # Bind agent queue to broadcast exchange
        self.channel.queue_bind(
            exchange=self.broadcast_exchange,
            queue=self.queue_name
        )

        # Create shared state exchange (topic)
        self.state_exchange = "artemis.state"
        self.channel.exchange_declare(
            exchange=self.state_exchange,
            exchange_type='topic',
            durable=durable
        )

        # Message counter
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
        Send message to another agent via RabbitMQ

        Args:
            to_agent: Recipient agent name (or "all" for broadcast)
            message_type: Type of message
            data: Message payload
            card_id: Associated card ID
            priority: Message priority
            metadata: Optional metadata

        Returns:
            Message ID
        """
        message = Message(
            protocol_version="1.0.0",
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

        # Serialize message
        body = json.dumps(message.to_dict())

        # Set delivery mode (persistent if durable)
        delivery_mode = 2 if self.durable else 1

        # Priority mapping (0-9, higher = more priority)
        priority_value = {"high": 9, "medium": 5, "low": 1}.get(priority, 5)

        properties = pika.BasicProperties(
            delivery_mode=delivery_mode,
            priority=priority_value,
            content_type='application/json',
            message_id=message.message_id,
            timestamp=int(datetime.utcnow().timestamp())
        )

        if to_agent == "all":
            # Broadcast to all agents
            self.channel.basic_publish(
                exchange=self.broadcast_exchange,
                routing_key='',
                body=body,
                properties=properties
            )
        else:
            # Send to specific agent's queue
            target_queue = f"artemis.agent.{to_agent}"
            self.channel.basic_publish(
                exchange='',
                routing_key=target_queue,
                body=body,
                properties=properties
            )

        return message.message_id

    def read_messages(
        self,
        message_type: Optional[str] = None,
        from_agent: Optional[str] = None,
        priority: Optional[str] = None,
        unread_only: bool = True,
        mark_as_read: bool = True
    ) -> List[Message]:
        """
        Read messages from queue (non-blocking)

        Note: RabbitMQ is inherently async. This method reads ONE batch
        of available messages and returns immediately.

        For continuous processing, use start_consuming() instead.

        Args:
            message_type: Filter by message type
            from_agent: Filter by sender
            priority: Filter by priority
            unread_only: Ignored (RabbitMQ always returns unread)
            mark_as_read: Whether to acknowledge messages

        Returns:
            List of Message objects
        """
        messages = []

        # Read messages in non-blocking mode
        for method_frame, properties, body in self.channel.consume(
            self.queue_name,
            inactivity_timeout=0.1  # Return immediately if no messages
        ):
            if method_frame is None:
                break

            # Parse message
            try:
                message_data = json.loads(body)
                message = Message.from_dict(message_data)

                # Apply filters
                if message_type and message.message_type != message_type:
                    # Requeue filtered messages
                    self.channel.basic_nack(
                        delivery_tag=method_frame.delivery_tag,
                        requeue=True
                    )
                    continue

                if from_agent and message.from_agent != from_agent:
                    self.channel.basic_nack(
                        delivery_tag=method_frame.delivery_tag,
                        requeue=True
                    )
                    continue

                if priority and message.priority != priority:
                    self.channel.basic_nack(
                        delivery_tag=method_frame.delivery_tag,
                        requeue=True
                    )
                    continue

                messages.append(message)

                # Acknowledge message if mark_as_read
                if mark_as_read:
                    self.channel.basic_ack(
                        delivery_tag=method_frame.delivery_tag
                    )
                else:
                    # Requeue for later
                    self.channel.basic_nack(
                        delivery_tag=method_frame.delivery_tag,
                        requeue=True
                    )

            except Exception as e:
                # Dead letter the malformed message
                self.channel.basic_nack(
                    delivery_tag=method_frame.delivery_tag,
                    requeue=False
                )
                print(f"Error parsing message: {e}")

        # Cancel consumer
        self.channel.cancel()

        return messages

    def start_consuming(self, callback):
        """
        Start consuming messages (blocking)

        This is the preferred way to process messages with RabbitMQ.
        Callback is invoked for each message received.

        Args:
            callback: Function to call for each message: callback(message: Message)
        """
        def on_message(ch, method, properties, body):
            try:
                message_data = json.loads(body)
                message = Message.from_dict(message_data)

                # Invoke callback
                callback(message)

                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                # Reject and requeue on error
                ch.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=True
                )
                print(f"Error processing message: {e}")

        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=on_message
        )

        print(f"[{self.agent_name}] Waiting for messages...")
        self.channel.start_consuming()

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
        """
        Update shared pipeline state

        Publishes state update to topic exchange so all agents can receive it.

        Args:
            card_id: Card ID
            updates: Dictionary of updates to apply
        """
        state_message = {
            "card_id": card_id,
            "updates": updates,
            "updated_by": self.agent_name,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }

        body = json.dumps(state_message)

        self.channel.basic_publish(
            exchange=self.state_exchange,
            routing_key=f"state.{card_id}",
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2 if self.durable else 1,
                content_type='application/json'
            )
        )

    def get_shared_state(self, card_id: str = None) -> Dict:
        """
        Get current shared pipeline state

        Note: RabbitMQ is not a state store. This is a placeholder.
        In production, use Redis or a database for shared state.

        Args:
            card_id: Optional card ID to filter

        Returns:
            Shared state dictionary (empty in RabbitMQ implementation)
        """
        # RabbitMQ is a message broker, not a state store
        # For shared state, use Redis or database
        return {}

    def register_agent(self, capabilities: List[str], status: str = "active"):
        """
        Register agent in agent registry

        Publishes agent registration to exchange.

        Args:
            capabilities: List of agent capabilities
            status: Agent status
        """
        registration = {
            "agent_name": self.agent_name,
            "capabilities": capabilities,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }

        body = json.dumps(registration)

        # Publish to registry exchange
        self.channel.basic_publish(
            exchange='artemis.registry',
            routing_key='agent.registered',
            body=body
        )

    def cleanup(self):
        """
        Cleanup resources

        Closes RabbitMQ connection.
        """
        if self.channel and self.channel.is_open:
            self.channel.close()

        if self.connection and self.connection.is_open:
            self.connection.close()

    def get_messenger_type(self) -> str:
        """Get messenger implementation type"""
        return "rabbitmq"


if __name__ == "__main__":
    """
    Example usage of RabbitMQ messenger

    Prerequisites:
        docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management
        pip install pika
    """

    if not RABBITMQ_AVAILABLE:
        print("❌ RabbitMQ messenger requires 'pika' package")
        print("Install with: pip install pika")
        exit(1)

    print("RabbitMQ Messenger - Example Usage")
    print("=" * 60)

    # Create messenger
    messenger = RabbitMQMessenger(
        agent_name="example-agent",
        rabbitmq_url="amqp://localhost"
    )

    # Send message
    msg_id = messenger.send_data_update(
        to_agent="test-agent",
        card_id="card-123",
        update_type="test",
        data={"hello": "world"}
    )
    print(f"✅ Sent message: {msg_id}")

    # Cleanup
    messenger.cleanup()
    print("✅ Cleaned up")
