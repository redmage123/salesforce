#!/usr/bin/env python3
"""
Reasoning Strategy Integration for Artemis

Integrates Chain of Thought (CoT), Tree of Thoughts (ToT), and Logic of Thoughts (LoT)
into the Artemis prompt system and LLM client.

Design Patterns:
- Strategy Pattern: Different reasoning strategies
- Decorator Pattern: Enhance LLM calls with reasoning
- Factory Pattern: Strategy selection
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import json
import logging

from artemis_exceptions import wrap_exception, LLMClientError
from reasoning_strategies import (
    ReasoningStrategy,
    ReasoningStrategyBase,
    ReasoningStrategyFactory,
    ChainOfThoughtStrategy,
    TreeOfThoughtsStrategy,
    LogicOfThoughtsStrategy,
    SelfConsistencyStrategy
)
from llm_client import LLMClientInterface, LLMMessage, LLMResponse


@dataclass
class ReasoningConfig:
    """Configuration for reasoning strategy"""
    strategy: ReasoningStrategy
    enabled: bool = True

    # CoT specific
    cot_examples: Optional[List[Dict[str, str]]] = None

    # ToT specific
    tot_branching_factor: int = 3
    tot_max_depth: int = 4

    # LoT specific
    lot_axioms: Optional[List[str]] = None

    # Self-Consistency specific
    sc_num_samples: int = 5

    # General
    temperature: float = 0.7
    max_tokens: int = 4000


class ReasoningEnhancedLLMClient:
    """
    Wrapper around LLMClientInterface that adds reasoning capabilities.

    Uses Decorator pattern to enhance any LLM client with reasoning strategies.

    Example:
        base_client = create_llm_client("openai")
        reasoning_client = ReasoningEnhancedLLMClient(base_client)

        response = reasoning_client.complete_with_reasoning(
            messages=[...],
            reasoning_config=ReasoningConfig(strategy=ReasoningStrategy.CHAIN_OF_THOUGHT)
        )
    """

    def __init__(
        self,
        base_client: LLMClientInterface,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize reasoning-enhanced LLM client.

        Args:
            base_client: Base LLM client to enhance
            logger: Logger instance
        """
        self.base_client = base_client
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @wrap_exception(LLMClientError, "Failed to complete with reasoning")
    def complete_with_reasoning(
        self,
        messages: List[LLMMessage],
        reasoning_config: ReasoningConfig,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Complete LLM request with reasoning strategy applied.

        Args:
            messages: Conversation messages
            reasoning_config: Reasoning configuration
            model: Model to use
            temperature: Temperature override
            max_tokens: Max tokens override

        Returns:
            Dict with response and reasoning metadata

        Raises:
            LLMClientError: If completion fails
        """
        if not reasoning_config.enabled:
            # No reasoning - standard completion
            response = self.base_client.complete(
                messages=messages,
                model=model,
                temperature=temperature or 0.7,
                max_tokens=max_tokens or 4000
            )
            return {
                "response": response,
                "reasoning_applied": False,
                "reasoning_strategy": None
            }

        # Create reasoning strategy
        strategy = self._create_strategy(reasoning_config)

        # Extract task from messages
        task = self._extract_task_from_messages(messages)
        context = self._extract_context_from_messages(messages)

        # Generate reasoning-enhanced prompt
        reasoning_prompt = self._generate_reasoning_prompt(
            strategy, task, context, reasoning_config
        )

        # Build enhanced messages
        enhanced_messages = self._build_enhanced_messages(messages, reasoning_prompt)

        # Execute LLM call(s)
        if reasoning_config.strategy == ReasoningStrategy.SELF_CONSISTENCY:
            # Multiple samples for self-consistency
            return self._execute_self_consistency(
                enhanced_messages, strategy, reasoning_config, model, temperature, max_tokens
            )
        elif reasoning_config.strategy == ReasoningStrategy.TREE_OF_THOUGHTS:
            # Tree exploration
            return self._execute_tree_of_thoughts(
                enhanced_messages, strategy, reasoning_config, model, temperature, max_tokens
            )
        else:
            # Single-shot reasoning (CoT, LoT)
            return self._execute_single_reasoning(
                enhanced_messages, strategy, reasoning_config, model, temperature, max_tokens
            )

    def _create_strategy(self, config: ReasoningConfig) -> ReasoningStrategyBase:
        """Create reasoning strategy from config"""
        kwargs = {"logger": self.logger}

        if config.strategy == ReasoningStrategy.TREE_OF_THOUGHTS:
            kwargs["branching_factor"] = config.tot_branching_factor
            kwargs["max_depth"] = config.tot_max_depth
        elif config.strategy == ReasoningStrategy.SELF_CONSISTENCY:
            kwargs["num_samples"] = config.sc_num_samples

        return ReasoningStrategyFactory.create(config.strategy, **kwargs)

    def _extract_task_from_messages(self, messages: List[LLMMessage]) -> str:
        """Extract main task from messages"""
        # Get last user message as task
        for msg in reversed(messages):
            if msg.role == "user":
                return msg.content
        return ""

    def _extract_context_from_messages(self, messages: List[LLMMessage]) -> Optional[str]:
        """Extract context from system messages"""
        for msg in messages:
            if msg.role == "system":
                return msg.content
        return None

    def _generate_reasoning_prompt(
        self,
        strategy: ReasoningStrategyBase,
        task: str,
        context: Optional[str],
        config: ReasoningConfig
    ) -> str:
        """Generate reasoning-enhanced prompt"""
        if config.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT:
            return strategy.generate_prompt(
                task=task,
                context=context,
                examples=config.cot_examples
            )
        elif config.strategy == ReasoningStrategy.TREE_OF_THOUGHTS:
            return strategy.generate_prompt(
                task=task,
                context=context,
                depth=0
            )
        elif config.strategy == ReasoningStrategy.LOGIC_OF_THOUGHTS:
            return strategy.generate_prompt(
                task=task,
                context=context,
                axioms=config.lot_axioms
            )
        else:
            return strategy.generate_prompt(task=task, context=context)

    def _build_enhanced_messages(
        self,
        original_messages: List[LLMMessage],
        reasoning_prompt: str
    ) -> List[LLMMessage]:
        """Build enhanced messages with reasoning prompt"""
        enhanced = []

        # Keep system messages
        for msg in original_messages:
            if msg.role == "system":
                enhanced.append(msg)

        # Add reasoning-enhanced user message
        enhanced.append(LLMMessage(role="user", content=reasoning_prompt))

        return enhanced

    def _execute_single_reasoning(
        self,
        messages: List[LLMMessage],
        strategy: ReasoningStrategyBase,
        config: ReasoningConfig,
        model: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int]
    ) -> Dict[str, Any]:
        """Execute single-shot reasoning (CoT, LoT)"""
        response = self.base_client.complete(
            messages=messages,
            model=model,
            temperature=temperature or config.temperature,
            max_tokens=max_tokens or config.max_tokens
        )

        # Parse response with strategy
        reasoning_output = strategy.parse_response(response.content)

        self.logger.info(
            f"Applied {config.strategy.value} reasoning "
            f"(tokens: {response.usage['total_tokens']})"
        )

        return {
            "response": response,
            "reasoning_applied": True,
            "reasoning_strategy": config.strategy.value,
            "reasoning_output": reasoning_output
        }

    def _execute_tree_of_thoughts(
        self,
        messages: List[LLMMessage],
        strategy: TreeOfThoughtsStrategy,
        config: ReasoningConfig,
        model: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int]
    ) -> Dict[str, Any]:
        """Execute Tree of Thoughts exploration"""
        # Initial exploration
        response = self.base_client.complete(
            messages=messages,
            model=model,
            temperature=temperature or config.temperature,
            max_tokens=max_tokens or config.max_tokens
        )

        # Parse initial branches
        reasoning_output = strategy.parse_response(response.content)

        # Select best path (simplified - would normally iterate deeper)
        best_path = strategy.select_best_path() if strategy.root else []

        self.logger.info(
            f"Applied Tree of Thoughts reasoning with "
            f"{reasoning_output.get('branches', 0)} branches explored"
        )

        return {
            "response": response,
            "reasoning_applied": True,
            "reasoning_strategy": "tree_of_thoughts",
            "reasoning_output": reasoning_output,
            "best_path": [node.thought for node in best_path]
        }

    def _execute_self_consistency(
        self,
        messages: List[LLMMessage],
        strategy: SelfConsistencyStrategy,
        config: ReasoningConfig,
        model: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int]
    ) -> Dict[str, Any]:
        """Execute Self-Consistency with multiple samples"""
        samples = []
        total_tokens = 0

        # Generate multiple samples
        for i in range(config.sc_num_samples):
            response = self.base_client.complete(
                messages=messages,
                model=model,
                temperature=temperature or config.temperature,
                max_tokens=max_tokens or config.max_tokens
            )

            samples.append(response.content)
            total_tokens += response.usage['total_tokens']

            # Parse each sample
            strategy.parse_response(response.content)

        # Get consistent answer
        consistent_answer = strategy.get_consistent_answer()

        self.logger.info(
            f"Applied Self-Consistency reasoning with {config.sc_num_samples} samples "
            f"(total tokens: {total_tokens})"
        )

        # Return last response with consistency metadata
        return {
            "response": response,
            "reasoning_applied": True,
            "reasoning_strategy": "self_consistency",
            "samples": samples,
            "consistent_answer": consistent_answer,
            "total_tokens": total_tokens
        }


class ReasoningPromptEnhancer:
    """
    Enhances PromptManager prompts with reasoning strategies.

    Integrates with PromptManager to add reasoning instructions to prompts.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @wrap_exception(LLMClientError, "Failed to enhance prompt with reasoning")
    def enhance_prompt_with_reasoning(
        self,
        base_prompt: Dict[str, str],
        reasoning_config: ReasoningConfig
    ) -> Dict[str, str]:
        """
        Enhance a prompt with reasoning strategy instructions.

        Args:
            base_prompt: Dict with 'system' and 'user' messages
            reasoning_config: Reasoning configuration

        Returns:
            Enhanced prompt dict

        Example:
            enhancer = ReasoningPromptEnhancer()
            enhanced = enhancer.enhance_prompt_with_reasoning(
                base_prompt={"system": "...", "user": "..."},
                reasoning_config=ReasoningConfig(strategy=ReasoningStrategy.CHAIN_OF_THOUGHT)
            )
        """
        if not reasoning_config.enabled:
            return base_prompt

        enhanced = base_prompt.copy()

        # Add reasoning instructions to system message
        reasoning_instructions = self._get_reasoning_instructions(reasoning_config)
        enhanced["system"] = f"{base_prompt['system']}\n\n{reasoning_instructions}"

        # Add reasoning template to user message if applicable
        if reasoning_config.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT:
            cot_template = self._get_cot_template()
            enhanced["user"] = f"{base_prompt['user']}\n\n{cot_template}"
        elif reasoning_config.strategy == ReasoningStrategy.LOGIC_OF_THOUGHTS:
            lot_template = self._get_lot_template(reasoning_config.lot_axioms)
            enhanced["user"] = f"{base_prompt['user']}\n\n{lot_template}"

        self.logger.info(f"Enhanced prompt with {reasoning_config.strategy.value} reasoning")

        return enhanced

    def _get_reasoning_instructions(self, config: ReasoningConfig) -> str:
        """Get reasoning strategy instructions for system message"""
        instructions = {
            ReasoningStrategy.CHAIN_OF_THOUGHT: """
**Reasoning Strategy: Chain of Thought**

You must think through this problem step-by-step, showing all intermediate reasoning.
Break down complex problems into logical steps and explain each step clearly.
""",
            ReasoningStrategy.TREE_OF_THOUGHTS: """
**Reasoning Strategy: Tree of Thoughts**

Explore multiple approaches in parallel. For each approach:
1. Describe the core idea
2. List advantages and challenges
3. Score from 0-10

Present alternatives as JSON array with thought, advantages, challenges, and score.
""",
            ReasoningStrategy.LOGIC_OF_THOUGHTS: """
**Reasoning Strategy: Logic of Thoughts**

Use formal logical reasoning and deductions. Apply logical rules:
- Modus Ponens: If P then Q, P is true, therefore Q
- Modus Tollens: If P then Q, Q is false, therefore P is false
- Syllogism: If P then Q, Q then R, therefore P then R

Show each deduction explicitly and verify conclusions logically.
""",
            ReasoningStrategy.SELF_CONSISTENCY: """
**Reasoning Strategy: Self-Consistency**

Solve this problem and show your complete reasoning.
Your answer will be compared with multiple samples to ensure consistency.
"""
        }

        return instructions.get(config.strategy, "")

    def _get_cot_template(self) -> str:
        """Get Chain of Thought template"""
        return """
Please think through this step by step:
1. First, identify what information we have
2. Then, determine what we need to find
3. Next, break down the solution into logical steps
4. Work through each step carefully
5. Finally, verify the answer makes sense
"""

    def _get_lot_template(self, axioms: Optional[List[str]]) -> str:
        """Get Logic of Thoughts template"""
        template = "\n**Apply Formal Logic:**\n"
        template += "1. Identify all given premises\n"
        template += "2. State any assumptions clearly\n"
        template += "3. Apply logical rules step by step\n"
        template += "4. Show each deduction explicitly\n"
        template += "5. Verify conclusion follows logically\n"

        if axioms:
            template += "\n**Known Facts (Axioms):**\n"
            for i, axiom in enumerate(axioms, 1):
                template += f"{i}. {axiom}\n"

        return template


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_reasoning_enhanced_client(
    provider: str = "openai",
    api_key: Optional[str] = None
) -> ReasoningEnhancedLLMClient:
    """
    Create reasoning-enhanced LLM client.

    Args:
        provider: "openai" or "anthropic"
        api_key: API key (optional)

    Returns:
        ReasoningEnhancedLLMClient

    Example:
        client = create_reasoning_enhanced_client("openai")
        response = client.complete_with_reasoning(
            messages=[...],
            reasoning_config=ReasoningConfig(strategy=ReasoningStrategy.CHAIN_OF_THOUGHT)
        )
    """
    from llm_client import create_llm_client

    base_client = create_llm_client(provider, api_key)
    return ReasoningEnhancedLLMClient(base_client)


def get_default_reasoning_config(task_type: str) -> ReasoningConfig:
    """
    Get default reasoning configuration for task type.

    Args:
        task_type: Type of task (e.g., "coding", "analysis", "planning")

    Returns:
        ReasoningConfig

    Example:
        config = get_default_reasoning_config("coding")
    """
    configs = {
        "coding": ReasoningConfig(
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            enabled=True
        ),
        "architecture": ReasoningConfig(
            strategy=ReasoningStrategy.TREE_OF_THOUGHTS,
            enabled=True,
            tot_branching_factor=3,
            tot_max_depth=4
        ),
        "analysis": ReasoningConfig(
            strategy=ReasoningStrategy.LOGIC_OF_THOUGHTS,
            enabled=True
        ),
        "testing": ReasoningConfig(
            strategy=ReasoningStrategy.SELF_CONSISTENCY,
            enabled=True,
            sc_num_samples=3
        )
    }

    return configs.get(task_type, ReasoningConfig(
        strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
        enabled=True
    ))


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Reasoning Integration Demo")
    parser.add_argument("--provider", default="openai", choices=["openai", "anthropic"],
                       help="LLM provider")
    parser.add_argument("--strategy", required=True,
                       choices=["cot", "tot", "lot", "sc"],
                       help="Reasoning strategy")
    parser.add_argument("--task", required=True, help="Task to solve")
    parser.add_argument("--context", help="Additional context")

    args = parser.parse_args()

    # Map CLI args to enum
    strategy_map = {
        "cot": ReasoningStrategy.CHAIN_OF_THOUGHT,
        "tot": ReasoningStrategy.TREE_OF_THOUGHTS,
        "lot": ReasoningStrategy.LOGIC_OF_THOUGHTS,
        "sc": ReasoningStrategy.SELF_CONSISTENCY
    }

    try:
        # Create reasoning-enhanced client
        client = create_reasoning_enhanced_client(args.provider)

        # Build messages
        messages = [
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content=args.task)
        ]

        if args.context:
            messages.insert(1, LLMMessage(role="system", content=args.context))

        # Create reasoning config
        config = ReasoningConfig(
            strategy=strategy_map[args.strategy],
            enabled=True,
            sc_num_samples=3 if args.strategy == "sc" else 5
        )

        print("=" * 80)
        print(f"REASONING STRATEGY: {args.strategy.upper()}")
        print("=" * 80)
        print(f"\nTask: {args.task}")
        if args.context:
            print(f"Context: {args.context}")
        print("\nExecuting with reasoning enhancement...")
        print("-" * 80)

        # Execute with reasoning
        result = client.complete_with_reasoning(
            messages=messages,
            reasoning_config=config
        )

        print("\nRESPONSE:")
        print("-" * 80)
        print(result["response"].content)
        print("-" * 80)

        print("\nREASONING METADATA:")
        print(f"Strategy Applied: {result['reasoning_strategy']}")
        print(f"Total Tokens: {result['response'].usage['total_tokens']}")

        if "reasoning_output" in result:
            print("\nREASONING OUTPUT:")
            print(json.dumps(result["reasoning_output"], indent=2))

        if "consistent_answer" in result:
            print("\nCONSISTENT ANSWER:")
            print(json.dumps(result["consistent_answer"], indent=2))

        print("=" * 80)

    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
