#!/usr/bin/env python3
"""
Quick test of ArtemisChatAgent

Tests basic functionality without requiring actual LLM calls
"""

import sys
import json
from unittest.mock import Mock, MagicMock, patch
from artemis_chat_agent import ArtemisChatAgent, ChatContext, ChatMessage


def test_chat_agent_initialization():
    """Test that chat agent initializes correctly"""
    print("Test 1: Chat agent initialization...")

    with patch('artemis_chat_agent.create_llm_client') as mock_llm:
        with patch('artemis_chat_agent.KanbanBoard') as mock_kanban:
            mock_llm.return_value = Mock()
            mock_kanban.return_value = Mock()

            agent = ArtemisChatAgent(llm_provider="openai", verbose=True)

            assert agent is not None
            assert agent.llm_client is not None
            assert agent.kanban is not None
            assert len(agent.sessions) == 0

            print("✅ Initialization test passed")
            return True


def test_chat_context():
    """Test ChatContext creation and state"""
    print("\nTest 2: ChatContext creation...")

    context = ChatContext(
        session_id="test-session-123",
        user_id="test-user"
    )

    assert context.session_id == "test-session-123"
    assert context.user_id == "test-user"
    assert context.active_card_id is None
    assert len(context.conversation_history) == 0
    assert context.personality_state is not None
    assert context.personality_state["formality"] == "casual"

    print("✅ ChatContext test passed")
    return True


def test_intent_detection():
    """Test intent detection with mocked LLM"""
    print("\nTest 3: Intent detection...")

    with patch('artemis_chat_agent.create_llm_client') as mock_llm_factory:
        with patch('artemis_chat_agent.KanbanBoard') as mock_kanban:
            # Setup mocks
            mock_llm = Mock()
            mock_response = Mock()
            mock_response.content = json.dumps({
                "type": "greeting",
                "parameters": {},
                "confidence": 0.95
            })
            mock_llm.complete.return_value = mock_response
            mock_llm_factory.return_value = mock_llm
            mock_kanban.return_value = Mock()

            agent = ArtemisChatAgent(llm_provider="openai", verbose=False)

            # Create context
            context = ChatContext(session_id="test-123")

            # Test intent detection
            intent = agent._detect_intent("Hello!", context)

            assert intent is not None
            assert intent["type"] == "greeting"
            assert intent["confidence"] == 0.95

            print("✅ Intent detection test passed")
            return True


def test_handle_greeting():
    """Test greeting handler"""
    print("\nTest 4: Greeting handler...")

    with patch('artemis_chat_agent.create_llm_client') as mock_llm:
        with patch('artemis_chat_agent.KanbanBoard') as mock_kanban:
            mock_llm.return_value = Mock()
            mock_kanban.return_value = Mock()

            agent = ArtemisChatAgent(llm_provider="openai", verbose=False)
            context = ChatContext(session_id="test-123")

            intent = {"type": "greeting", "parameters": {}}
            response = agent._handle_greeting(intent, context)

            assert response is not None
            assert isinstance(response, str)
            assert len(response) > 0

            print(f"   Sample greeting: '{response}'")
            print("✅ Greeting handler test passed")
            return True


def test_handle_create_task():
    """Test task creation handler"""
    print("\nTest 5: Task creation handler...")

    with patch('artemis_chat_agent.create_llm_client') as mock_llm:
        with patch('artemis_chat_agent.KanbanBoard') as mock_kanban:
            mock_llm.return_value = Mock()
            mock_kanban_instance = Mock()
            mock_kanban.return_value = mock_kanban_instance

            agent = ArtemisChatAgent(llm_provider="openai", verbose=False)
            context = ChatContext(session_id="test-123", user_id="test-user")

            intent = {
                "type": "create_task",
                "parameters": {
                    "task_description": "Build a user authentication system with JWT tokens"
                }
            }

            response = agent._handle_create_task(intent, context)

            assert response is not None
            assert isinstance(response, str)
            assert len(response) > 0
            assert "card-" in response  # Should contain card ID
            assert context.active_card_id is not None
            assert context.active_card_id.startswith("card-")

            # Verify Kanban card was created
            mock_kanban_instance.add_card.assert_called_once()

            print(f"   Created card: {context.active_card_id}")
            print(f"   Response: '{response[:100]}...'")
            print("✅ Task creation handler test passed")
            return True


def test_personality_consistency():
    """Test that personality traits are maintained"""
    print("\nTest 6: Personality consistency...")

    # Test the CORE_PERSONALITY prompt
    assert "You are Artemis" in ArtemisChatAgent.CORE_PERSONALITY
    assert "autonomous" in ArtemisChatAgent.CORE_PERSONALITY.lower()

    # Check that the prompt instructs NOT to use "as an AI"
    # (the phrase will appear in the instruction itself, which is correct)
    assert "Never use phrases like" in ArtemisChatAgent.CORE_PERSONALITY
    assert "conversational" in ArtemisChatAgent.CORE_PERSONALITY.lower()

    print("✅ Personality consistency test passed")
    return True


def main():
    """Run all tests"""
    print("="*60)
    print("ARTEMIS CHAT AGENT TESTS")
    print("="*60)

    tests = [
        test_chat_agent_initialization,
        test_chat_context,
        test_intent_detection,
        test_handle_greeting,
        test_handle_create_task,
        test_personality_consistency
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
