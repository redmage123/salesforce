#!/usr/bin/env python3
"""
UserStoryGenerator (SOLID: Single Responsibility)

Single Responsibility: Generate user stories from ADR content

This service handles ONLY user story generation:
- Converting ADR content into actionable user stories
- Using LLM or Prompt Manager to generate stories
- Parsing and structuring story responses
"""

import json
import re
from typing import Dict, List, Optional

from artemis_stage_interface import LoggerInterface


class UserStoryGenerator:
    """
    Service for generating user stories from ADR content

    Single Responsibility: User story generation
    - Convert ADR content into user stories via LLM
    - Support RAG-based prompt templates via PromptManager
    - Parse and validate user story format
    """

    def __init__(
        self,
        llm_client,
        logger: LoggerInterface,
        prompt_manager=None  # PromptManager (optional)
    ):
        """
        Initialize user story generator

        Args:
            llm_client: LLM client for generating stories
            logger: Logger interface
            prompt_manager: Prompt manager for RAG-based prompts (optional)
        """
        self.llm_client = llm_client
        self.logger = logger
        self.prompt_manager = prompt_manager

    def generate_user_stories(
        self,
        adr_content: str,
        adr_number: str,
        parent_card: Dict
    ) -> List[Dict]:
        """
        Generate user stories from ADR content using LLM

        Args:
            adr_content: Full ADR markdown content
            adr_number: ADR number (e.g., "001")
            parent_card: Parent task card

        Returns:
            List of user story dicts with title, description, acceptance_criteria, points
        """
        self.logger.log(f"🤖 Generating user stories from ADR-{adr_number}...", "INFO")

        if not self.llm_client:
            self.logger.log("⚠️  No LLM client available - skipping user story generation", "WARNING")
            return []

        try:
            # Build prompt (try RAG first, fallback to default)
            system_message, user_message = self._build_story_generation_prompt(adr_content)

            # Use LLM client's complete() method
            from llm_client import LLMMessage
            messages = [
                LLMMessage(role="system", content=system_message),
                LLMMessage(role="user", content=user_message)
            ]

            llm_response = self.llm_client.complete(
                messages=messages,
                temperature=0.4,
                max_tokens=2000
            )
            response = llm_response.content

            # Parse JSON response
            user_stories = self._parse_story_response(response)

            self.logger.log(f"✅ Generated {len(user_stories)} user stories from ADR-{adr_number}", "INFO")
            return user_stories

        except Exception as e:
            self.logger.log(f"❌ Failed to generate user stories: {e}", "ERROR")
            return []

    def _build_story_generation_prompt(self, adr_content: str) -> tuple[str, str]:
        """
        Build prompt for user story generation

        Tries to get prompt from RAG via PromptManager first,
        falls back to default prompt if unavailable.

        Args:
            adr_content: ADR content to convert

        Returns:
            Tuple of (system_message, user_message)
        """
        # Try to get prompt from RAG first
        if self.prompt_manager:
            try:
                self.logger.log("📝 Loading architecture prompt from RAG", "INFO")
                prompt_template = self.prompt_manager.get_prompt("architecture_design_adr")

                if prompt_template:
                    # Render the prompt with ADR content
                    rendered = self.prompt_manager.render_prompt(
                        prompt=prompt_template,
                        variables={
                            "context": f"Converting ADR to user stories",
                            "requirements": adr_content,
                            "constraints": "Focus on implementation tasks",
                            "scale_expectations": "2-5 user stories"
                        }
                    )
                    self.logger.log(f"✅ Loaded RAG prompt with {len(prompt_template.perspectives)} perspectives", "INFO")
                    return rendered['system'], rendered['user']
                else:
                    raise Exception("Prompt not found in RAG")
            except Exception as e:
                self.logger.log(f"⚠️  Error loading RAG prompt: {e} - using default", "WARNING")

        # Fallback to default prompt
        system_message = """You are an expert at converting Architecture Decision Records (ADRs) into actionable user stories.
Generate user stories that implement the architectural decisions, following best practices:
- Use "As a [role], I want [feature], so that [benefit]" format
- Include specific acceptance criteria
- Estimate story points (1-8 scale)
- Break down complex decisions into multiple stories"""

        user_message = f"""Convert the following ADR into user stories:

{adr_content}

Generate 2-5 user stories in JSON format:
{{
  "user_stories": [
    {{
      "title": "As a developer, I want to implement X, so that Y",
      "description": "Detailed description of what needs to be built",
      "acceptance_criteria": [
        "Given X, when Y, then Z",
        "Criterion 2"
      ],
      "points": 5,
      "priority": "high"
    }}
  ]
}}

Focus on implementation tasks, not architectural discussions."""

        return system_message, user_message

    def _parse_story_response(self, response: str) -> List[Dict]:
        """
        Parse LLM response containing user stories

        Extracts JSON from response and validates structure.

        Args:
            response: LLM response text

        Returns:
            List of parsed user story dicts

        Raises:
            ValueError: If response doesn't contain valid JSON
        """
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            self.logger.log("⚠️  LLM response did not contain valid JSON", "WARNING")
            return []

        data = json.loads(json_match.group(0))
        user_stories = data.get('user_stories', [])

        # Validate story structure
        validated_stories = []
        for story in user_stories:
            if self._validate_story_structure(story):
                validated_stories.append(story)
            else:
                self.logger.log(f"⚠️  Skipping malformed user story: {story.get('title', 'Unknown')}", "WARNING")

        return validated_stories

    def _validate_story_structure(self, story: Dict) -> bool:
        """
        Validate user story has required fields

        Args:
            story: User story dict

        Returns:
            True if valid, False otherwise
        """
        required_fields = ['title', 'description', 'acceptance_criteria', 'points', 'priority']
        for field in required_fields:
            if field not in story:
                return False

        # Validate types
        if not isinstance(story['title'], str):
            return False
        if not isinstance(story['description'], str):
            return False
        if not isinstance(story['acceptance_criteria'], list):
            return False
        if not isinstance(story['points'], (int, float)):
            return False
        if story['priority'] not in ['low', 'medium', 'high', 'critical']:
            return False

        return True
