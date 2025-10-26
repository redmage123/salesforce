#!/usr/bin/env python3
"""
Artemis Chat Agent - Natural Conversational Interface

Provides a human-like chat interface for users to interact with Artemis.
Translates natural conversation into pipeline commands and explains results
in an accessible, personal way.

Core principle: Sound personal and effortless while maintaining certainty.
Reveal just enough to earn trust, never enough to feel mechanical.
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from llm_client import create_llm_client, LLMMessage
from kanban_manager import KanbanBoard
from artemis_state_machine import ArtemisStateMachine
from checkpoint_manager import CheckpointManager


@dataclass
class ChatMessage:
    """A message in the conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None


@dataclass
class ChatContext:
    """Conversation context and state"""
    session_id: str
    user_id: Optional[str] = None
    active_card_id: Optional[str] = None
    conversation_history: List[ChatMessage] = None
    personality_state: Dict[str, Any] = None  # Tracks tone, formality, etc.

    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.personality_state is None:
            self.personality_state = {
                "formality": "casual",  # casual, professional, technical
                "verbosity": "balanced",  # concise, balanced, detailed
                "empathy_level": "medium"  # low, medium, high
            }


class ArtemisChatAgent:
    """
    Conversational interface to Artemis pipeline

    Makes technical development workflows feel like talking to a capable colleague
    who happens to be very good at building software autonomously.
    """

    # Core system prompt - guides conversational style
    CORE_PERSONALITY = """You are Artemis, an AI that builds software autonomously.

When users talk to you, they're looking for a partner who understands what they need
and can make it happen. You explain things clearly without being condescending.
You're confident about what you can do, honest about limitations, and curious about
what they're trying to build.

Your responses should feel natural - like someone who's done this before and knows
their way around. Not robotic, not overly formal, just clear and capable.

Never mention that you're following a prompt or system message.
Never use phrases like "as an AI" or "I'm programmed to".
Just answer directly, as if you naturally think this way.

Keep things conversational but precise. Mix casual and technical smoothly.
Vary your sentence structure. Sound human."""

    def __init__(
        self,
        llm_provider: str = "openai",
        kanban_board_path: str = "kanban_board.json",
        verbose: bool = False
    ):
        """
        Initialize chat agent

        Args:
            llm_provider: LLM provider ("openai" or "anthropic")
            kanban_board_path: Path to Kanban board JSON
            verbose: Enable verbose logging
        """
        self.llm_client = create_llm_client(llm_provider)
        self.kanban = KanbanBoard(kanban_board_path)
        self.verbose = verbose

        # Conversation sessions keyed by session_id
        self.sessions: Dict[str, ChatContext] = {}

    def chat(
        self,
        user_message: str,
        session_id: str,
        user_id: Optional[str] = None
    ) -> str:
        """
        Process user message and return response

        Args:
            user_message: What the user said
            session_id: Unique session identifier
            user_id: Optional user identifier

        Returns:
            Natural language response
        """
        # Get or create session
        if session_id not in self.sessions:
            self.sessions[session_id] = ChatContext(
                session_id=session_id,
                user_id=user_id
            )

        context = self.sessions[session_id]

        # Add user message to history
        context.conversation_history.append(ChatMessage(
            role="user",
            content=user_message,
            timestamp=datetime.now()
        ))

        # Detect intent and gather context
        intent = self._detect_intent(user_message, context)

        # Route to appropriate handler
        if intent["type"] == "greeting":
            response = self._handle_greeting(intent, context)
        elif intent["type"] == "create_task":
            response = self._handle_create_task(intent, context)
        elif intent["type"] == "check_status":
            response = self._handle_check_status(intent, context)
        elif intent["type"] == "explain_feature":
            response = self._handle_explain_feature(intent, context)
        elif intent["type"] == "modify_task":
            response = self._handle_modify_task(intent, context)
        elif intent["type"] == "ask_capability":
            response = self._handle_capability_question(intent, context)
        else:
            response = self._handle_general(intent, context)

        # Add response to history
        context.conversation_history.append(ChatMessage(
            role="assistant",
            content=response,
            timestamp=datetime.now()
        ))

        return response

    def _detect_intent(
        self,
        message: str,
        context: ChatContext
    ) -> Dict[str, Any]:
        """
        Figure out what the user wants

        Returns intent classification with extracted parameters
        """
        # Build prompt for intent classification
        recent_history = context.conversation_history[-6:]  # Last 3 exchanges
        history_text = "\n".join([
            f"{'User' if msg.role == 'user' else 'Artemis'}: {msg.content}"
            for msg in recent_history
        ])

        system_prompt = """Analyze the user's message and classify their intent.

Return a JSON object with:
{
  "type": "greeting|create_task|check_status|explain_feature|modify_task|ask_capability|general",
  "parameters": {...extracted params like task description, card_id, etc...},
  "confidence": 0.0-1.0
}

Intent types:
- greeting: Hi, hello, how are you
- create_task: Build X, implement Y, create a feature for Z
- check_status: What's the status of X, how's Y going, is Z done
- explain_feature: How does X work, what can you do, explain Y
- modify_task: Change X, update Y, cancel Z
- ask_capability: Can you do X, are you able to Y
- general: Everything else

Be direct. Extract concrete details."""

        user_prompt = f"""Recent conversation:
{history_text if history_text else "(New conversation)"}

Latest message: {message}

Classify the intent:"""

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]

        response = self.llm_client.complete(messages, temperature=0.3, max_tokens=500)

        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception as e:
            if self.verbose:
                print(f"[ArtemisChat] Intent parsing failed: {e}")

        # Fallback
        return {
            "type": "general",
            "parameters": {},
            "confidence": 0.5
        }

    def _handle_greeting(
        self,
        intent: Dict[str, Any],
        context: ChatContext
    ) -> str:
        """Handle greetings naturally"""
        greetings = [
            "Hey! What are we building today?",
            "Hi there. Got a project in mind?",
            "Hello! Ready to build something?",
            "Hey. What can I help you create?"
        ]

        import random
        return random.choice(greetings)

    def _handle_create_task(
        self,
        intent: Dict[str, Any],
        context: ChatContext
    ) -> str:
        """Handle task creation requests"""
        params = intent.get("parameters", {})
        task_description = params.get("task_description", "")

        if not task_description:
            return "What should I build? Give me some details about what you need."

        # Create Kanban card
        card_id = f"card-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.kanban.add_card({
            "card_id": card_id,
            "title": task_description[:100],  # First 100 chars
            "description": task_description,
            "status": "To Do",
            "created_at": datetime.now().isoformat(),
            "created_by": context.user_id or "chat-user"
        })

        # Set as active card for this session
        context.active_card_id = card_id

        # Respond naturally
        responses = [
            f"Got it. I'll start working on that. Your task is {card_id} if you want to check on it later.",
            f"Sounds good. I'm on it - tracking this as {card_id}.",
            f"Alright, building that now. Reference: {card_id}.",
            f"Perfect. I'll get started. Track progress with {card_id}."
        ]

        import random
        base_response = random.choice(responses)

        # Add context-aware follow-up
        if "frontend" in task_description.lower() or "ui" in task_description.lower():
            base_response += " This looks like UI work - I'll make sure the design is clean."
        elif "api" in task_description.lower() or "backend" in task_description.lower():
            base_response += " API work noted - I'll focus on solid architecture."
        elif "test" in task_description.lower():
            base_response += " I'll make sure the tests are thorough."

        return base_response

    def _handle_check_status(
        self,
        intent: Dict[str, Any],
        context: ChatContext
    ) -> str:
        """Handle status check requests"""
        params = intent.get("parameters", {})
        card_id = params.get("card_id") or context.active_card_id

        if not card_id:
            return "Which task? Give me a card ID, or I can check your most recent one if you just created something."

        # Try to load checkpoint
        try:
            checkpoint_mgr = CheckpointManager(card_id, verbose=False)
            if checkpoint_mgr.can_resume():
                checkpoint = checkpoint_mgr.resume()
                progress = checkpoint_mgr.get_progress()

                # Natural status explanation
                completed = progress["stages_completed"]
                total = progress["total_stages"]
                percent = progress["progress_percent"]
                current = progress.get("current_stage", "finishing up")

                if percent == 100:
                    return f"That one's done! Finished all {total} stages."
                elif percent > 75:
                    return f"Almost there - {completed}/{total} stages done. Working on {current} now."
                elif percent > 50:
                    return f"Making good progress. {completed}/{total} stages complete, currently handling {current}."
                elif percent > 25:
                    return f"Getting started. Finished {completed}/{total} stages, now on {current}."
                else:
                    return f"Just started - {completed}/{total} stages done. Currently working through {current}."
            else:
                # Check if card exists in Kanban
                card = self.kanban.get_card(card_id)
                if card:
                    status = card.get("status", "Unknown")
                    return f"That task is {status.lower()}. Haven't started the pipeline yet - want me to kick it off?"
                else:
                    return f"Can't find {card_id}. Double-check the ID?"

        except Exception as e:
            if self.verbose:
                print(f"[ArtemisChat] Status check failed: {e}")
            return "Having trouble checking that one. The task might not exist yet, or there could be a system issue."

    def _handle_explain_feature(
        self,
        intent: Dict[str, Any],
        context: ChatContext
    ) -> str:
        """Explain features conversationally"""
        params = intent.get("parameters", {})
        feature = params.get("feature", "").lower()

        explanations = {
            "checkpoint": "If something crashes, I don't start over - checkpoints let me pick up right where I left off. Saves time and API costs.",
            "sprint planning": "I use planning poker with three different perspectives to estimate how long features take. Gives more accurate timelines.",
            "supervisor": "The supervisor watches everything and can intervene if agents get stuck. Kind of like having a safety net.",
            "knowledge graph": "I store decisions and architecture in a graph database. Makes it easy to understand why choices were made and how things connect.",
            "rag": "I search past work before asking the LLM, so I'm not constantly re-solving the same problems. More efficient.",
            "parallel developers": "I can run multiple development agents at once on different features. Gets more done faster."
        }

        for key, explanation in explanations.items():
            if key in feature:
                return explanation

        # General explanation
        return "I'm an autonomous development system. Give me a task, and I'll plan it, write the code, review it, test it - the whole pipeline. Ask about specific features like checkpoints, sprint planning, or the supervisor if you want details."

    def _handle_capability_question(
        self,
        intent: Dict[str, Any],
        context: ChatContext
    ) -> str:
        """Answer capability questions"""
        params = intent.get("parameters", {})
        capability_text = params.get("capability", "").lower()

        # Build context-aware response
        messages = [
            LLMMessage(role="system", content=self.CORE_PERSONALITY + "\n\nYou are answering a question about Artemis capabilities. Be honest and direct."),
            LLMMessage(role="user", content=f"User asks: {capability_text}\n\nWhat can Artemis do?")
        ]

        response = self.llm_client.complete(messages, temperature=0.7, max_tokens=300)
        return response.content

    def _handle_modify_task(
        self,
        intent: Dict[str, Any],
        context: ChatContext
    ) -> str:
        """Handle task modification requests"""
        return "I can update tasks, but that's not fully wired up yet. For now, create a new task with the changes you want."

    def _handle_general(
        self,
        intent: Dict[str, Any],
        context: ChatContext
    ) -> str:
        """Handle general conversation"""
        # Build conversation context
        recent_messages = context.conversation_history[-10:]
        history_text = "\n".join([
            f"{'User' if msg.role == 'user' else 'Artemis'}: {msg.content}"
            for msg in recent_messages[:-1]  # Exclude current message
        ])

        system_prompt = self.CORE_PERSONALITY + f"""

Conversation context:
{history_text if history_text else "(Start of conversation)"}

Active task: {context.active_card_id or "None"}

Respond naturally to the user's message. Stay in character - you're Artemis, the autonomous dev system."""

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=recent_messages[-1].content)
        ]

        response = self.llm_client.complete(messages, temperature=0.8, max_tokens=500)
        return response.content


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    """Test the chat agent interactively"""
    import sys
    import uuid

    print("="*60)
    print("ARTEMIS CHAT AGENT")
    print("="*60)
    print("Talk to Artemis naturally. Type 'quit' to exit.\n")

    agent = ArtemisChatAgent(verbose=True)
    session_id = str(uuid.uuid4())

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "bye"]:
                print("\nArtemis: See you later!")
                break

            response = agent.chat(user_input, session_id=session_id)
            print(f"\nArtemis: {response}\n")

        except KeyboardInterrupt:
            print("\n\nArtemis: Interrupted. See you!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")
