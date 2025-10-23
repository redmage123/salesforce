#!/usr/bin/env python3
"""
LLM Client - Unified Interface for OpenAI and Anthropic APIs

Single Responsibility: Provide unified interface to multiple LLM providers
Open/Closed: Can add new providers without modifying existing code
Liskov Substitution: All clients implement LLMClientInterface
Interface Segregation: Minimal interface with just what's needed
Dependency Inversion: Depends on LLMClientInterface abstraction
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from artemis_exceptions import (
    LLMClientError,
    ConfigurationError,
    LLMAPIError,
    wrap_exception
)


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMMessage:
    """Represents a message in a conversation"""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider"""
    content: str
    model: str
    provider: str
    usage: Dict[str, int]  # {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": Z}
    raw_response: Dict  # Full API response for debugging


class LLMClientInterface(ABC):
    """
    Abstract base class for all LLM clients

    Single Responsibility: Define contract for LLM communication
    """

    @abstractmethod
    def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None
    ) -> LLMResponse:
        """Send messages to LLM and get response"""
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        pass


class OpenAIClient(LLMClientInterface):
    """
    OpenAI API client

    Single Responsibility: Handle OpenAI API communication only
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ConfigurationError(
                "OpenAI API key not provided and OPENAI_API_KEY env var not set",
                context={"provider": "openai"}
            )

        # Import OpenAI library (lazy import)
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai library not installed. Run: pip install openai")

    def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None
    ) -> LLMResponse:
        """Send messages to OpenAI and get response"""
        # Convert our LLMMessage format to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        # Default model
        if model is None:
            model = "gpt-5"  # Latest GPT-5 model (supports temperature)

        # Build API call kwargs
        api_kwargs = {
            "model": model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Note: o1 reasoning models have different requirements
        # They don't support temperature and use max_completion_tokens
        # But GPT-5 supports all standard parameters including temperature
        if model.startswith("o1"):
            # o1 models only support temperature=1 (default), so we omit it
            # o1 models use max_completion_tokens instead of max_tokens
            del api_kwargs["temperature"]
            api_kwargs["max_completion_tokens"] = api_kwargs.pop("max_tokens")

        # Add response_format if specified (for JSON mode)
        if response_format:
            api_kwargs["response_format"] = response_format

        # Call OpenAI API
        response = self.client.chat.completions.create(**api_kwargs)

        # Extract response
        content = response.choices[0].message.content

        # Build usage info
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

        return LLMResponse(
            content=content,
            model=response.model,
            provider="openai",
            usage=usage,
            raw_response=response.model_dump()
        )

    def get_available_models(self) -> List[str]:
        """Get available OpenAI models"""
        return [
            "gpt-5",  # Latest GPT-5 (supports temperature)
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "o1-preview",  # Reasoning model (no temperature support)
            "o1-mini"  # Reasoning model (no temperature support)
        ]


class AnthropicClient(LLMClientInterface):
    """
    Anthropic API client

    Single Responsibility: Handle Anthropic API communication only
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ConfigurationError(
                "Anthropic API key not provided and ANTHROPIC_API_KEY env var not set",
                context={"provider": "anthropic"}
            )

        # Import Anthropic library (lazy import)
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic library not installed. Run: pip install anthropic")

    def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None
    ) -> LLMResponse:
        """Send messages to Anthropic and get response"""
        # Anthropic requires system message to be separate
        system_message = None
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Default model
        if model is None:
            model = "claude-sonnet-4-5-20250929"  # Claude Sonnet 4.5

        # Note: Anthropic doesn't support response_format parameter
        # JSON mode is achieved through prompt engineering for Claude

        # Call Anthropic API
        kwargs = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if system_message:
            kwargs["system"] = system_message

        response = self.client.messages.create(**kwargs)

        # Extract response
        content = response.content[0].text

        # Build usage info
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
        }

        return LLMResponse(
            content=content,
            model=response.model,
            provider="anthropic",
            usage=usage,
            raw_response=response.model_dump()
        )

    def get_available_models(self) -> List[str]:
        """Get available Anthropic models"""
        return [
            "claude-sonnet-4-5-20250929",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]


class LLMClientFactory:
    """
    Factory for creating LLM clients

    Single Responsibility: Create appropriate LLM client based on provider
    Open/Closed: Can add new providers without modifying existing code
    """

    @staticmethod
    def create(
        provider: LLMProvider,
        api_key: Optional[str] = None
    ) -> LLMClientInterface:
        """Create LLM client for specified provider"""
        if provider == LLMProvider.OPENAI:
            return OpenAIClient(api_key=api_key)
        elif provider == LLMProvider.ANTHROPIC:
            return AnthropicClient(api_key=api_key)
        else:
            raise ConfigurationError(
                f"Unsupported provider: {provider}",
                context={"provider": str(provider), "supported": ["openai", "anthropic"]}
            )

    @staticmethod
    def create_from_env() -> LLMClientInterface:
        """
        Create LLM client from environment variables

        Checks ARTEMIS_LLM_PROVIDER env var (defaults to "openai")
        """
        provider_str = os.getenv("ARTEMIS_LLM_PROVIDER", "openai").lower()

        if provider_str == "openai":
            provider = LLMProvider.OPENAI
        elif provider_str == "anthropic":
            provider = LLMProvider.ANTHROPIC
        else:
            raise ConfigurationError(
                f"Invalid ARTEMIS_LLM_PROVIDER: {provider_str}",
                context={"provider": provider_str, "supported": ["openai", "anthropic"]}
            )

        return LLMClientFactory.create(provider)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_llm_client(
    provider: str = "openai",
    api_key: Optional[str] = None
) -> LLMClientInterface:
    """
    Convenience function to create LLM client

    Args:
        provider: "openai" or "anthropic"
        api_key: API key (optional, will use env var if not provided)

    Returns:
        LLMClientInterface implementation

    Example:
        client = create_llm_client("openai")
        messages = [
            LLMMessage(role="system", content="You are a helpful assistant"),
            LLMMessage(role="user", content="Write a Python function to add two numbers")
        ]
        response = client.complete(messages)
        print(response.content)
    """
    if provider.lower() == "openai":
        return LLMClientFactory.create(LLMProvider.OPENAI, api_key)
    elif provider.lower() == "anthropic":
        return LLMClientFactory.create(LLMProvider.ANTHROPIC, api_key)
    else:
        raise ConfigurationError(
            f"Invalid provider: {provider}",
            context={"provider": provider, "supported": ["openai", "anthropic"]}
        )


# ============================================================================
# MAIN - TESTING
# ============================================================================

if __name__ == "__main__":
    """Test LLM client"""
    import sys

    # Test with OpenAI
    print("Testing OpenAI client...")
    try:
        openai_client = create_llm_client("openai")
        print(f"✅ OpenAI client created")
        print(f"Available models: {', '.join(openai_client.get_available_models()[:3])}...")

        # Test completion
        messages = [
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="Say 'Hello from OpenAI!' and nothing else.")
        ]

        response = openai_client.complete(messages, max_tokens=100)
        print(f"✅ Response: {response.content}")
        print(f"   Model: {response.model}")
        print(f"   Tokens: {response.usage['total_tokens']}")
    except Exception as e:
        error = wrap_exception(
            e,
            LLMClientError,
            "OpenAI test failed",
            {"provider": "openai"}
        )
        print(f"❌ OpenAI test failed: {error}")

    print("\n" + "="*60 + "\n")

    # Test with Anthropic
    print("Testing Anthropic client...")
    try:
        anthropic_client = create_llm_client("anthropic")
        print(f"✅ Anthropic client created")
        print(f"Available models: {', '.join(anthropic_client.get_available_models()[:3])}...")

        # Test completion
        messages = [
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="Say 'Hello from Anthropic!' and nothing else.")
        ]

        response = anthropic_client.complete(messages, max_tokens=100)
        print(f"✅ Response: {response.content}")
        print(f"   Model: {response.model}")
        print(f"   Tokens: {response.usage['total_tokens']}")
    except Exception as e:
        error = wrap_exception(
            e,
            LLMClientError,
            "Anthropic test failed",
            {"provider": "anthropic"}
        )
        print(f"❌ Anthropic test failed: {error}")
