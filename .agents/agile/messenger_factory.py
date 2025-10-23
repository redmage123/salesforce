#!/usr/bin/env python3
"""
Messenger Factory (SOLID: Factory Pattern + Dependency Inversion)

Creates messenger instances based on configuration.
Allows easy switching between implementations without changing code.

This demonstrates:
- Factory Pattern: Centralized creation of messenger objects
- Dependency Inversion: Depend on MessengerInterface, not concrete implementations
- Open/Closed: Add new messengers without modifying factory (just registration)
"""

import os
from typing import Optional, Dict, Any

from messenger_interface import MessengerInterface, MockMessenger
from agent_messenger import AgentMessenger


class MessengerFactory:
    """
    Factory for creating messenger instances

    Usage:
        # Create from environment variable
        messenger = MessengerFactory.create_from_env(agent_name="architecture-agent")

        # Create specific type
        messenger = MessengerFactory.create(
            messenger_type="file",
            agent_name="architecture-agent"
        )

        # Create with config
        messenger = MessengerFactory.create_from_config(
            agent_name="architecture-agent",
            config={
                "type": "rabbitmq",
                "url": "amqp://localhost",
                "durable": True
            }
        )
    """

    # Registry of messenger types
    _registry: Dict[str, type] = {
        "file": AgentMessenger,
        "mock": MockMessenger,
    }

    @classmethod
    def register_messenger(cls, messenger_type: str, messenger_class: type):
        """
        Register a new messenger type

        This allows extensions without modifying the factory.

        Args:
            messenger_type: Type name (e.g., "rabbitmq", "redis")
            messenger_class: Messenger class implementing MessengerInterface
        """
        if not issubclass(messenger_class, MessengerInterface):
            raise TypeError(
                f"{messenger_class} must implement MessengerInterface"
            )

        cls._registry[messenger_type] = messenger_class

    @classmethod
    def create(
        cls,
        messenger_type: str,
        agent_name: str,
        **kwargs
    ) -> MessengerInterface:
        """
        Create messenger of specified type

        Args:
            messenger_type: Type of messenger ("file", "rabbitmq", "redis", "mock")
            agent_name: Name of agent
            **kwargs: Additional arguments for messenger constructor

        Returns:
            MessengerInterface implementation

        Raises:
            ValueError: If messenger_type is unknown
        """
        if messenger_type not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unknown messenger type: {messenger_type}. "
                f"Available types: {available}"
            )

        messenger_class = cls._registry[messenger_type]

        # Create messenger instance
        return messenger_class(agent_name=agent_name, **kwargs)

    @classmethod
    def create_from_env(
        cls,
        agent_name: str,
        env_var: str = "ARTEMIS_MESSENGER_TYPE",
        default: str = "file"
    ) -> MessengerInterface:
        """
        Create messenger from environment variable

        Args:
            agent_name: Name of agent
            env_var: Environment variable name
            default: Default messenger type if env var not set

        Returns:
            MessengerInterface implementation
        """
        messenger_type = os.getenv(env_var, default)

        # Get type-specific config from environment
        config = cls._get_config_from_env(messenger_type)

        return cls.create(
            messenger_type=messenger_type,
            agent_name=agent_name,
            **config
        )

    @classmethod
    def create_from_config(
        cls,
        agent_name: str,
        config: Dict[str, Any]
    ) -> MessengerInterface:
        """
        Create messenger from configuration dictionary

        Args:
            agent_name: Name of agent
            config: Configuration dictionary with 'type' key and type-specific options

        Returns:
            MessengerInterface implementation

        Example:
            config = {
                "type": "rabbitmq",
                "url": "amqp://localhost",
                "durable": True
            }
        """
        messenger_type = config.get("type", "file")
        messenger_config = {k: v for k, v in config.items() if k != "type"}

        return cls.create(
            messenger_type=messenger_type,
            agent_name=agent_name,
            **messenger_config
        )

    @classmethod
    def _get_config_from_env(cls, messenger_type: str) -> Dict[str, Any]:
        """
        Get messenger-specific configuration from environment variables

        Args:
            messenger_type: Type of messenger

        Returns:
            Configuration dictionary
        """
        config = {}

        if messenger_type == "file":
            # File-based messenger config
            if os.getenv("ARTEMIS_MESSAGE_DIR"):
                config["message_dir"] = os.getenv("ARTEMIS_MESSAGE_DIR")

        elif messenger_type == "rabbitmq":
            # RabbitMQ messenger config
            if os.getenv("ARTEMIS_RABBITMQ_URL"):
                config["rabbitmq_url"] = os.getenv("ARTEMIS_RABBITMQ_URL")

            if os.getenv("ARTEMIS_RABBITMQ_DURABLE"):
                config["durable"] = os.getenv("ARTEMIS_RABBITMQ_DURABLE").lower() == "true"

            if os.getenv("ARTEMIS_RABBITMQ_PREFETCH"):
                config["prefetch_count"] = int(os.getenv("ARTEMIS_RABBITMQ_PREFETCH"))

        elif messenger_type == "redis":
            # Redis messenger config (future implementation)
            if os.getenv("ARTEMIS_REDIS_URL"):
                config["redis_url"] = os.getenv("ARTEMIS_REDIS_URL")

        return config

    @classmethod
    def get_available_types(cls) -> list:
        """
        Get list of available messenger types

        Returns:
            List of messenger type names
        """
        return list(cls._registry.keys())


# Auto-register RabbitMQ messenger if available
try:
    from rabbitmq_messenger import RabbitMQMessenger
    MessengerFactory.register_messenger("rabbitmq", RabbitMQMessenger)
except ImportError:
    # RabbitMQ messenger not available (pika not installed)
    pass


# Convenience function for quick messenger creation
def create_messenger(
    agent_name: str,
    messenger_type: Optional[str] = None,
    **kwargs
) -> MessengerInterface:
    """
    Quick messenger creation

    Args:
        agent_name: Name of agent
        messenger_type: Type of messenger (None = from environment)
        **kwargs: Additional arguments

    Returns:
        MessengerInterface implementation
    """
    if messenger_type is None:
        return MessengerFactory.create_from_env(agent_name)
    else:
        return MessengerFactory.create(messenger_type, agent_name, **kwargs)


if __name__ == "__main__":
    """Example usage of MessengerFactory"""

    print("Messenger Factory - Example Usage")
    print("=" * 60)

    # Show available types
    print(f"Available messenger types: {MessengerFactory.get_available_types()}")
    print()

    # Example 1: Create file-based messenger
    print("1. Creating file-based messenger:")
    messenger1 = MessengerFactory.create(
        messenger_type="file",
        agent_name="example-agent-1"
    )
    print(f"   ✅ Created: {messenger1.get_messenger_type()}")
    print()

    # Example 2: Create mock messenger
    print("2. Creating mock messenger:")
    messenger2 = MessengerFactory.create(
        messenger_type="mock",
        agent_name="example-agent-2"
    )
    print(f"   ✅ Created: {messenger2.get_messenger_type()}")
    print()

    # Example 3: Create from environment
    print("3. Creating from environment (ARTEMIS_MESSENGER_TYPE):")
    os.environ["ARTEMIS_MESSENGER_TYPE"] = "file"
    messenger3 = MessengerFactory.create_from_env(agent_name="example-agent-3")
    print(f"   ✅ Created: {messenger3.get_messenger_type()}")
    print()

    # Example 4: Create from config
    print("4. Creating from config dictionary:")
    config = {
        "type": "mock"
    }
    messenger4 = MessengerFactory.create_from_config(
        agent_name="example-agent-4",
        config=config
    )
    print(f"   ✅ Created: {messenger4.get_messenger_type()}")
    print()

    # Example 5: Convenience function
    print("5. Using convenience function:")
    messenger5 = create_messenger(
        agent_name="example-agent-5",
        messenger_type="file"
    )
    print(f"   ✅ Created: {messenger5.get_messenger_type()}")
    print()

    print("=" * 60)
    print("✅ All examples completed!")
