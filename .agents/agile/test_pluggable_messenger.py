#!/usr/bin/env python3
"""
Test Pluggable Messenger System

Tests the complete pluggable messenger architecture:
- MessengerInterface (abstract interface)
- AgentMessenger (file-based implementation)
- RabbitMQMessenger (RabbitMQ implementation)
- MockMessenger (test implementation)
- MessengerFactory (factory pattern)
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.absolute()))

from messenger_interface import MessengerInterface, Message, MockMessenger
from agent_messenger import AgentMessenger
from messenger_factory import MessengerFactory


def test_interface_compliance():
    """Test that all messengers implement MessengerInterface"""
    print("\n" + "=" * 70)
    print("TEST: Interface Compliance")
    print("=" * 70)

    # Test AgentMessenger
    assert issubclass(AgentMessenger, MessengerInterface)
    print("  ✅ AgentMessenger implements MessengerInterface")

    # Test MockMessenger
    assert issubclass(MockMessenger, MessengerInterface)
    print("  ✅ MockMessenger implements MessengerInterface")

    # Try to create RabbitMQMessenger (may not be available)
    try:
        from rabbitmq_messenger import RabbitMQMessenger
        assert issubclass(RabbitMQMessenger, MessengerInterface)
        print("  ✅ RabbitMQMessenger implements MessengerInterface")
    except ImportError:
        print("  ⚠️  RabbitMQMessenger not available (pika not installed)")

    return True


def test_factory_creation():
    """Test MessengerFactory can create different messenger types"""
    print("\n" + "=" * 70)
    print("TEST: Factory Creation")
    print("=" * 70)

    # Get available types
    available = MessengerFactory.get_available_types()
    print(f"  Available types: {available}")
    assert "file" in available
    assert "mock" in available

    # Create file messenger
    file_messenger = MessengerFactory.create(
        messenger_type="file",
        agent_name="test-file-agent"
    )
    assert file_messenger.get_messenger_type() == "file"
    print("  ✅ Created file messenger")

    # Create mock messenger
    mock_messenger = MessengerFactory.create(
        messenger_type="mock",
        agent_name="test-mock-agent"
    )
    assert mock_messenger.get_messenger_type() == "mock"
    print("  ✅ Created mock messenger")

    return True


def test_environment_creation():
    """Test MessengerFactory creates from environment variables"""
    print("\n" + "=" * 70)
    print("TEST: Environment-based Creation")
    print("=" * 70)

    # Test with file messenger
    os.environ["ARTEMIS_MESSENGER_TYPE"] = "file"
    messenger1 = MessengerFactory.create_from_env(agent_name="test-env-1")
    assert messenger1.get_messenger_type() == "file"
    print("  ✅ Created file messenger from ARTEMIS_MESSENGER_TYPE=file")

    # Test with mock messenger
    os.environ["ARTEMIS_MESSENGER_TYPE"] = "mock"
    messenger2 = MessengerFactory.create_from_env(agent_name="test-env-2")
    assert messenger2.get_messenger_type() == "mock"
    print("  ✅ Created mock messenger from ARTEMIS_MESSENGER_TYPE=mock")

    # Test default (no env var)
    if "ARTEMIS_MESSENGER_TYPE" in os.environ:
        del os.environ["ARTEMIS_MESSENGER_TYPE"]
    messenger3 = MessengerFactory.create_from_env(agent_name="test-env-3")
    assert messenger3.get_messenger_type() == "file"  # default
    print("  ✅ Created file messenger (default when no env var)")

    return True


def test_config_creation():
    """Test MessengerFactory creates from config dictionary"""
    print("\n" + "=" * 70)
    print("TEST: Config-based Creation")
    print("=" * 70)

    # Test with file config
    config1 = {"type": "file", "message_dir": "/tmp/test_messages"}
    messenger1 = MessengerFactory.create_from_config(
        agent_name="test-config-1",
        config=config1
    )
    assert messenger1.get_messenger_type() == "file"
    print("  ✅ Created file messenger from config")

    # Test with mock config
    config2 = {"type": "mock"}
    messenger2 = MessengerFactory.create_from_config(
        agent_name="test-config-2",
        config=config2
    )
    assert messenger2.get_messenger_type() == "mock"
    print("  ✅ Created mock messenger from config")

    return True


def test_mock_messenger_operations():
    """Test MockMessenger basic operations"""
    print("\n" + "=" * 70)
    print("TEST: MockMessenger Operations")
    print("=" * 70)

    messenger = MockMessenger(agent_name="test-mock")

    # Test send_message
    msg_id1 = messenger.send_message(
        to_agent="recipient",
        message_type="data_update",
        card_id="card-123",
        data={"test": "data"}
    )
    assert len(messenger.sent_messages) == 1
    print("  ✅ send_message() works")

    # Test send_data_update
    msg_id2 = messenger.send_data_update(
        to_agent="recipient",
        card_id="card-123",
        update_type="test",
        data={"key": "value"}
    )
    assert len(messenger.sent_messages) == 2
    print("  ✅ send_data_update() works")

    # Test send_notification
    msg_id3 = messenger.send_notification(
        to_agent="all",
        card_id="card-123",
        notification_type="test",
        data={"info": "notification"}
    )
    assert len(messenger.sent_messages) == 3
    print("  ✅ send_notification() works")

    # Test send_error
    msg_id4 = messenger.send_error(
        to_agent="orchestrator",
        card_id="card-123",
        error_type="test_error",
        message="Test error message"
    )
    assert len(messenger.sent_messages) == 4
    print("  ✅ send_error() works")

    # Test update_shared_state
    messenger.update_shared_state(
        card_id="card-123",
        updates={"status": "complete"}
    )
    state = messenger.get_shared_state()
    assert state["status"] == "complete"
    print("  ✅ update_shared_state() works")

    # Test get_shared_state
    state = messenger.get_shared_state(card_id="card-123")
    assert state["card_id"] == "card-123"
    print("  ✅ get_shared_state() works")

    return True


def test_file_messenger_operations():
    """Test AgentMessenger basic operations"""
    print("\n" + "=" * 70)
    print("TEST: AgentMessenger (File-based) Operations")
    print("=" * 70)

    # Create messenger with temp directory
    test_dir = "/tmp/test_messenger_ops"
    messenger = AgentMessenger(
        agent_name="test-file",
        message_dir=test_dir
    )

    # Test send_message
    msg_id1 = messenger.send_message(
        to_agent="test-recipient",
        message_type="data_update",
        card_id="card-123",
        data={"test": "data"}
    )
    print(f"  ✅ send_message() works: {msg_id1}")

    # Test send_data_update
    msg_id2 = messenger.send_data_update(
        to_agent="test-recipient",
        card_id="card-123",
        update_type="test",
        data={"key": "value"}
    )
    print(f"  ✅ send_data_update() works: {msg_id2}")

    # Test update_shared_state
    messenger.update_shared_state(
        card_id="card-123",
        updates={"status": "complete"}
    )
    print("  ✅ update_shared_state() works")

    # Test get_shared_state
    state = messenger.get_shared_state(card_id="card-123")
    assert state.get("card_id") == "card-123"
    print("  ✅ get_shared_state() works")

    # Cleanup
    messenger.cleanup()
    print("  ✅ cleanup() works")

    return True


def test_orchestrator_integration():
    """Test ArtemisOrchestrator works with pluggable messenger"""
    print("\n" + "=" * 70)
    print("TEST: ArtemisOrchestrator Integration")
    print("=" * 70)

    # Set environment to use mock messenger
    os.environ["ARTEMIS_MESSENGER_TYPE"] = "mock"

    from artemis_orchestrator import ArtemisOrchestrator
    from kanban_manager import KanbanBoard
    from rag_agent import RAGAgent

    # Create dependencies
    board = KanbanBoard()
    messenger = MessengerFactory.create_from_env(agent_name="artemis-orchestrator")
    rag = RAGAgent(db_path="/tmp/test_rag")

    assert messenger.get_messenger_type() == "mock"
    print(f"  ✅ Created messenger: {messenger.get_messenger_type()}")

    # Create orchestrator
    orchestrator = ArtemisOrchestrator(
        card_id="test-card-001",
        board=board,
        messenger=messenger,
        rag=rag,
        enable_observers=False
    )

    assert orchestrator.messenger.get_messenger_type() == "mock"
    print(f"  ✅ Orchestrator uses {messenger.get_messenger_type()} messenger")

    # Verify interface compliance
    assert hasattr(orchestrator.messenger, "send_message")
    assert hasattr(orchestrator.messenger, "read_messages")
    assert hasattr(orchestrator.messenger, "update_shared_state")
    print("  ✅ Messenger implements MessengerInterface")

    return True


def test_polymorphism():
    """Test that different messengers can be used interchangeably"""
    print("\n" + "=" * 70)
    print("TEST: Polymorphism (Dependency Inversion)")
    print("=" * 70)

    def use_messenger(messenger: MessengerInterface, agent_name: str):
        """Function that accepts any messenger implementation"""
        # Should work with any messenger
        msg_id = messenger.send_message(
            to_agent="test-recipient",
            message_type="test",
            card_id="test-card",
            data={"test": "polymorphism"}
        )
        return msg_id

    # Test with file messenger
    file_messenger = MessengerFactory.create("file", "poly-file")
    msg_id1 = use_messenger(file_messenger, "file")
    print(f"  ✅ Works with file messenger: {msg_id1}")

    # Test with mock messenger
    mock_messenger = MessengerFactory.create("mock", "poly-mock")
    msg_id2 = use_messenger(mock_messenger, "mock")
    print(f"  ✅ Works with mock messenger: {msg_id2}")

    print("  ✅ Polymorphism verified - all messengers interchangeable")

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧪 PLUGGABLE MESSENGER SYSTEM TEST SUITE")
    print("=" * 70)
    print("\nTesting pluggable messenger architecture (Dependency Inversion Principle)")
    print()

    tests = [
        ("Interface Compliance", test_interface_compliance),
        ("Factory Creation", test_factory_creation),
        ("Environment Creation", test_environment_creation),
        ("Config Creation", test_config_creation),
        ("MockMessenger Operations", test_mock_messenger_operations),
        ("FileMessenger Operations", test_file_messenger_operations),
        ("Orchestrator Integration", test_orchestrator_integration),
        ("Polymorphism", test_polymorphism),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ TEST FAILED WITH EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\n🎯 Result: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n✨ Pluggable Messenger System Benefits:")
        print("  • Dependency Inversion: High-level code depends on abstractions")
        print("  • Open/Closed: Add new messengers without modifying existing code")
        print("  • Testability: Easy to use MockMessenger in tests")
        print("  • Flexibility: Switch between file/RabbitMQ/Redis without code changes")
        print("  • Environment-based: Configure messenger via ARTEMIS_MESSENGER_TYPE")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
