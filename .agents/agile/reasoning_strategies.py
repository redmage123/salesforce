#!/usr/bin/env python3
"""
Advanced Reasoning Strategies for Artemis

Implements Chain of Thought (CoT), Tree of Thoughts (ToT), and Logic of Thoughts (LoT)
prompting strategies to enhance LLM reasoning capabilities.

Design Patterns:
- Strategy Pattern: Different reasoning strategies
- Template Method: Base reasoning flow
- Factory Pattern: Strategy selection
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json
import logging


class ReasoningStrategy(Enum):
    """Available reasoning strategies"""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    LOGIC_OF_THOUGHTS = "logic_of_thoughts"
    SELF_CONSISTENCY = "self_consistency"
    LEAST_TO_MOST = "least_to_most"


@dataclass
class ReasoningStep:
    """Single step in reasoning chain"""
    step_number: int
    description: str
    reasoning: str
    output: Optional[str] = None
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_number,
            "description": self.description,
            "reasoning": self.reasoning,
            "output": self.output,
            "confidence": self.confidence
        }


@dataclass
class ThoughtNode:
    """Node in tree of thoughts"""
    thought: str
    depth: int
    score: float
    children: List['ThoughtNode'] = field(default_factory=list)
    parent: Optional['ThoughtNode'] = None
    path_score: float = 0.0

    def add_child(self, child: 'ThoughtNode') -> 'ThoughtNode':
        """Add child node"""
        child.parent = self
        self.children.append(child)
        return child

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thought": self.thought,
            "depth": self.depth,
            "score": self.score,
            "path_score": self.path_score,
            "children": [c.to_dict() for c in self.children]
        }


@dataclass
class LogicRule:
    """Logical rule for LoT"""
    premise: str
    conclusion: str
    rule_type: str  # deduction, induction, abduction
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "premise": self.premise,
            "conclusion": self.conclusion,
            "rule_type": self.rule_type,
            "confidence": self.confidence
        }


class ReasoningStrategyBase(ABC):
    """Base class for reasoning strategies"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.steps: List[ReasoningStep] = []

    @abstractmethod
    def generate_prompt(self, task: str, context: Optional[str] = None) -> str:
        """Generate prompt with reasoning strategy"""
        pass

    @abstractmethod
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response"""
        pass


class ChainOfThoughtStrategy(ReasoningStrategyBase):
    """
    Chain of Thought (CoT) prompting strategy.

    Encourages step-by-step reasoning with explicit intermediate steps.

    Example:
        cot = ChainOfThoughtStrategy()
        prompt = cot.generate_prompt("Solve: If a train travels 120 miles in 2 hours...")
    """

    def generate_prompt(
        self,
        task: str,
        context: Optional[str] = None,
        examples: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate CoT prompt.

        Args:
            task: The task to solve
            context: Additional context
            examples: Few-shot examples with reasoning

        Returns:
            Formatted prompt with CoT instructions
        """
        prompt = "Let's solve this step by step.\n\n"

        if context:
            prompt += f"Context:\n{context}\n\n"

        # Add few-shot examples if provided
        if examples:
            prompt += "Here are some examples of step-by-step reasoning:\n\n"
            for i, example in enumerate(examples, 1):
                prompt += f"Example {i}:\n"
                prompt += f"Question: {example['question']}\n"
                prompt += f"Reasoning: {example['reasoning']}\n"
                prompt += f"Answer: {example['answer']}\n\n"

        prompt += f"Task: {task}\n\n"
        prompt += "Please think through this step by step:\n"
        prompt += "1. First, identify what information we have\n"
        prompt += "2. Then, determine what we need to find\n"
        prompt += "3. Next, break down the solution into logical steps\n"
        prompt += "4. Work through each step carefully\n"
        prompt += "5. Finally, verify the answer makes sense\n\n"
        prompt += "Your step-by-step reasoning:"

        return prompt

    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse CoT response into structured steps.

        Args:
            response: LLM response with step-by-step reasoning

        Returns:
            Structured reasoning with steps
        """
        # Extract steps (simple heuristic - can be improved)
        lines = response.strip().split('\n')
        steps = []
        current_step = None
        step_num = 0

        for line in lines:
            # Detect step markers (1., Step 1:, etc.)
            if line.strip() and (line[0].isdigit() or line.lower().startswith('step')):
                if current_step:
                    steps.append(current_step)
                step_num += 1
                current_step = ReasoningStep(
                    step_number=step_num,
                    description=line.strip(),
                    reasoning=""
                )
            elif current_step:
                current_step.reasoning += line + "\n"

        if current_step:
            steps.append(current_step)

        self.steps = steps

        return {
            "strategy": "chain_of_thought",
            "steps": [s.to_dict() for s in steps],
            "total_steps": len(steps)
        }


class TreeOfThoughtsStrategy(ReasoningStrategyBase):
    """
    Tree of Thoughts (ToT) prompting strategy.

    Explores multiple reasoning paths in parallel and selects the best.

    Example:
        tot = TreeOfThoughtsStrategy(branching_factor=3, max_depth=4)
        prompt = tot.generate_prompt("Design a database schema for an e-commerce platform")
    """

    def __init__(
        self,
        branching_factor: int = 3,
        max_depth: int = 4,
        logger: Optional[logging.Logger] = None
    ):
        super().__init__(logger)
        self.branching_factor = branching_factor
        self.max_depth = max_depth
        self.root: Optional[ThoughtNode] = None

    def generate_prompt(
        self,
        task: str,
        context: Optional[str] = None,
        depth: int = 0
    ) -> str:
        """
        Generate ToT prompt for exploring thought branches.

        Args:
            task: The task to solve
            context: Additional context
            depth: Current depth in thought tree

        Returns:
            Formatted prompt for generating thought branches
        """
        prompt = "Let's explore multiple approaches to solve this problem.\n\n"

        if context:
            prompt += f"Context:\n{context}\n\n"

        prompt += f"Task: {task}\n\n"

        if depth == 0:
            prompt += f"Generate {self.branching_factor} different high-level approaches to solve this problem.\n"
            prompt += "For each approach:\n"
            prompt += "1. Describe the core idea\n"
            prompt += "2. List key advantages\n"
            prompt += "3. Identify potential challenges\n"
            prompt += "4. Rate the approach from 0-10\n\n"
        else:
            prompt += f"For the current approach, generate {self.branching_factor} different next steps.\n"
            prompt += "For each step:\n"
            prompt += "1. Describe the specific action\n"
            prompt += "2. Explain the reasoning\n"
            prompt += "3. Predict the outcome\n"
            prompt += "4. Rate the step from 0-10\n\n"

        prompt += f"Provide {self.branching_factor} alternatives in JSON format:\n"
        prompt += "[\n"
        prompt += '  {"thought": "...", "advantages": [...], "challenges": [...], "score": X},\n'
        prompt += "  ...\n"
        prompt += "]"

        return prompt

    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse ToT response into thought tree.

        Args:
            response: LLM response with multiple thought branches

        Returns:
            Structured thought tree
        """
        try:
            # Extract JSON (simple extraction - can be improved)
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end > start:
                thoughts_data = json.loads(response[start:end])
            else:
                thoughts_data = []

            # Build tree if root doesn't exist
            if not self.root:
                self.root = ThoughtNode(
                    thought="Root",
                    depth=0,
                    score=0.0
                )

            # Add thoughts as nodes
            nodes = []
            for data in thoughts_data:
                node = ThoughtNode(
                    thought=data.get("thought", ""),
                    depth=1,
                    score=data.get("score", 0.0)
                )
                nodes.append(node)

            return {
                "strategy": "tree_of_thoughts",
                "branches": len(thoughts_data),
                "thoughts": thoughts_data,
                "best_score": max((t.get("score", 0) for t in thoughts_data), default=0)
            }

        except json.JSONDecodeError:
            self.logger.warning("Failed to parse ToT response as JSON")
            return {
                "strategy": "tree_of_thoughts",
                "error": "parse_error",
                "raw_response": response
            }

    def select_best_path(self) -> List[ThoughtNode]:
        """
        Select the best path through the thought tree.

        Returns:
            List of nodes representing the best path
        """
        if not self.root:
            return []

        # DFS to find path with highest cumulative score
        def dfs(node: ThoughtNode, current_score: float) -> tuple[float, List[ThoughtNode]]:
            node.path_score = current_score + node.score

            if not node.children:
                return node.path_score, [node]

            best_score = node.path_score
            best_path = [node]

            for child in node.children:
                child_score, child_path = dfs(child, node.path_score)
                if child_score > best_score:
                    best_score = child_score
                    best_path = [node] + child_path

            return best_score, best_path

        _, best_path = dfs(self.root, 0.0)
        return best_path


class LogicOfThoughtsStrategy(ReasoningStrategyBase):
    """
    Logic of Thoughts (LoT) prompting strategy.

    Uses formal logical rules and deductions.

    Example:
        lot = LogicOfThoughtsStrategy()
        prompt = lot.generate_prompt("If all programmers are problem solvers...")
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.rules: List[LogicRule] = []

    def generate_prompt(
        self,
        task: str,
        context: Optional[str] = None,
        axioms: Optional[List[str]] = None
    ) -> str:
        """
        Generate LoT prompt with logical reasoning.

        Args:
            task: The task to solve
            context: Additional context
            axioms: Known facts/axioms

        Returns:
            Formatted prompt with logical reasoning instructions
        """
        prompt = "Let's solve this using logical reasoning and formal deduction.\n\n"

        if context:
            prompt += f"Context:\n{context}\n\n"

        if axioms:
            prompt += "Known Facts (Axioms):\n"
            for i, axiom in enumerate(axioms, 1):
                prompt += f"{i}. {axiom}\n"
            prompt += "\n"

        prompt += f"Task: {task}\n\n"
        prompt += "Please reason through this using formal logic:\n\n"
        prompt += "1. Identify all given premises\n"
        prompt += "2. State any assumptions clearly\n"
        prompt += "3. Apply logical rules step by step:\n"
        prompt += "   - Modus Ponens: If P then Q, P is true, therefore Q is true\n"
        prompt += "   - Modus Tollens: If P then Q, Q is false, therefore P is false\n"
        prompt += "   - Syllogism: If P then Q, Q then R, therefore P then R\n"
        prompt += "   - Contrapositive: If P then Q is equivalent to If not Q then not P\n"
        prompt += "4. Show each deduction explicitly\n"
        prompt += "5. State your conclusion and verify it follows logically\n\n"
        prompt += "Your logical reasoning:"

        return prompt

    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LoT response into logical rules and deductions.

        Args:
            response: LLM response with logical reasoning

        Returns:
            Structured logical reasoning
        """
        # Extract logical rules (simplified heuristic)
        rules = []
        lines = response.strip().split('\n')

        for line in lines:
            # Detect logical implications
            if 'therefore' in line.lower() or '=>' in line or '→' in line:
                parts = line.split('therefore')
                if len(parts) == 2:
                    rule = LogicRule(
                        premise=parts[0].strip(),
                        conclusion=parts[1].strip(),
                        rule_type="deduction"
                    )
                    rules.append(rule)

        self.rules = rules

        return {
            "strategy": "logic_of_thoughts",
            "rules": [r.to_dict() for r in rules],
            "total_rules": len(rules)
        }


class SelfConsistencyStrategy(ReasoningStrategyBase):
    """
    Self-Consistency strategy.

    Generates multiple reasoning paths and selects the most consistent answer.
    """

    def __init__(
        self,
        num_samples: int = 5,
        logger: Optional[logging.Logger] = None
    ):
        super().__init__(logger)
        self.num_samples = num_samples
        self.samples: List[str] = []

    def generate_prompt(
        self,
        task: str,
        context: Optional[str] = None
    ) -> str:
        """Generate prompt for self-consistency sampling"""
        prompt = f"Task: {task}\n\n"

        if context:
            prompt += f"Context: {context}\n\n"

        prompt += "Please solve this problem and show your reasoning."
        return prompt

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse response and track for consistency"""
        self.samples.append(response)

        return {
            "strategy": "self_consistency",
            "samples_collected": len(self.samples),
            "target_samples": self.num_samples
        }

    def get_consistent_answer(self) -> Dict[str, Any]:
        """
        Analyze samples and return most consistent answer.

        Returns:
            Most frequent answer with confidence
        """
        # Simple frequency count (can be improved with semantic similarity)
        answer_counts: Dict[str, int] = {}

        for sample in self.samples:
            # Extract final answer (simple heuristic)
            if "answer:" in sample.lower():
                answer = sample.lower().split("answer:")[-1].strip()
                answer_counts[answer] = answer_counts.get(answer, 0) + 1

        if answer_counts:
            best_answer = max(answer_counts.items(), key=lambda x: x[1])
            return {
                "answer": best_answer[0],
                "frequency": best_answer[1],
                "confidence": best_answer[1] / len(self.samples),
                "total_samples": len(self.samples)
            }

        return {
            "answer": None,
            "error": "No consistent answer found"
        }


class ReasoningStrategyFactory:
    """
    Factory for creating reasoning strategies.

    Example:
        factory = ReasoningStrategyFactory()
        strategy = factory.create(ReasoningStrategy.CHAIN_OF_THOUGHT)
    """

    @staticmethod
    def create(
        strategy_type: ReasoningStrategy,
        **kwargs
    ) -> ReasoningStrategyBase:
        """
        Create reasoning strategy instance.

        Args:
            strategy_type: Type of reasoning strategy
            **kwargs: Strategy-specific parameters

        Returns:
            Reasoning strategy instance
        """
        if strategy_type == ReasoningStrategy.CHAIN_OF_THOUGHT:
            return ChainOfThoughtStrategy(**kwargs)

        elif strategy_type == ReasoningStrategy.TREE_OF_THOUGHTS:
            return TreeOfThoughtsStrategy(**kwargs)

        elif strategy_type == ReasoningStrategy.LOGIC_OF_THOUGHTS:
            return LogicOfThoughtsStrategy(**kwargs)

        elif strategy_type == ReasoningStrategy.SELF_CONSISTENCY:
            return SelfConsistencyStrategy(**kwargs)

        else:
            raise ValueError(f"Unknown reasoning strategy: {strategy_type}")


# CLI interface
if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Reasoning Strategy Demo")
    parser.add_argument("strategy", choices=["cot", "tot", "lot", "sc"],
                       help="Reasoning strategy to demonstrate")
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

    # Create strategy
    factory = ReasoningStrategyFactory()
    strategy = factory.create(strategy_map[args.strategy])

    # Generate prompt
    prompt = strategy.generate_prompt(args.task, args.context)

    print("="*80)
    print(f"REASONING STRATEGY: {args.strategy.upper()}")
    print("="*80)
    print("\nGENERATED PROMPT:")
    print("-"*80)
    print(prompt)
    print("="*80)
