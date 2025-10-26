"""
Prompt Management System for Artemis

Stores all agent prompts in RAG database with DEPTH framework applied.
Allows agents to query and retrieve context-specific prompts.

DEPTH Framework:
- D: Define Multiple Perspectives
- E: Establish Clear Success Metrics
- P: Provide Context Layers
- T: Task Breakdown
- H: Human Feedback Loop (Self-Critique)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json
import hashlib

# Import shared coding standards (DRY principle)
from coding_standards import CODING_STANDARDS_ALL_LANGUAGES
from debug_mixin import DebugMixin


class ReasoningStrategyType(Enum):
    """Reasoning strategy types"""
    NONE = "none"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    LOGIC_OF_THOUGHTS = "logic_of_thoughts"
    SELF_CONSISTENCY = "self_consistency"


@dataclass
class PromptTemplate:
    """
    A structured prompt template following DEPTH framework
    """
    prompt_id: str
    name: str
    category: str  # developer, supervisor, stage, learning, etc.
    version: str

    # DEPTH Framework Components
    perspectives: List[str]  # Multiple expert perspectives
    success_metrics: List[str]  # Clear, measurable criteria
    context_layers: Dict[str, Any]  # Rich context information
    task_breakdown: List[str]  # Step-by-step sub-tasks
    self_critique: str  # Self-validation instructions

    # Prompt Content
    system_message: str
    user_template: str  # Template with {placeholders}

    # Metadata
    tags: List[str]
    created_at: str
    updated_at: str
    performance_score: float  # Track effectiveness over time
    usage_count: int
    success_rate: float  # % of successful outcomes

    # Reasoning Strategy (with defaults - must come after required fields)
    reasoning_strategy: ReasoningStrategyType = ReasoningStrategyType.NONE
    reasoning_config: Optional[Dict[str, Any]] = None  # Strategy-specific config


class PromptManager(DebugMixin):
    """
    Manages prompt templates in RAG database

    Responsibilities:
    - Store/retrieve prompts with DEPTH framework
    - Version control for prompts
    - Query prompts by category, tags, context
    - Track prompt performance metrics
    """

    PROMPT_CATEGORIES = [
        "developer_agent",
        "supervisor_agent",
        "project_analysis_stage",
        "architecture_stage",
        "code_review_stage",
        "testing_stage",
        "learning_engine",
        "arbitration",
        "recovery_workflow"
    ]

    def __init__(self, rag_agent, verbose: bool = True):
        """
        Initialize PromptManager

        Args:
            rag_agent: RAG agent instance for storage
            verbose: Enable verbose logging
        """
        DebugMixin.__init__(self, component_name="prompt")
        self.rag = rag_agent
        self.verbose = verbose

        self.debug_log("PromptManager initialized", rag_available=rag_agent is not None)

        # Add prompt_template to RAG artifact types if not exists
        if "prompt_template" not in self.rag.ARTIFACT_TYPES:
            self.rag.ARTIFACT_TYPES.append("prompt_template")
            # Reinitialize collections to include prompts
            if hasattr(self.rag, 'client') and self.rag.client:
                self.rag._initialize_collections()

    def store_prompt(
        self,
        name: str,
        category: str,
        perspectives: List[str],
        success_metrics: List[str],
        context_layers: Dict[str, Any],
        task_breakdown: List[str],
        self_critique: str,
        system_message: str,
        user_template: str,
        tags: Optional[List[str]] = None,
        version: str = "1.0",
        reasoning_strategy: ReasoningStrategyType = ReasoningStrategyType.NONE,
        reasoning_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a prompt template with DEPTH framework applied

        Args:
            name: Prompt name (e.g., "developer_conservative_implementation")
            category: Prompt category
            perspectives: List of expert perspectives to apply
            success_metrics: Clear success criteria
            context_layers: Rich context dict
            task_breakdown: Step-by-step breakdown
            self_critique: Self-validation instructions
            system_message: System role message
            user_template: User prompt template with placeholders
            tags: Optional tags for categorization
            version: Version string
            reasoning_strategy: Reasoning strategy to apply (CoT, ToT, LoT, etc.)
            reasoning_config: Strategy-specific configuration

        Returns:
            Prompt ID
        """
        self.debug_log("Storing prompt", name=name, category=category, version=version, strategy=reasoning_strategy.value)

        if category not in self.PROMPT_CATEGORIES:
            if self.verbose:
                print(f"[PromptManager] ⚠️  Unknown category: {category}")

        # Generate prompt ID
        prompt_id = self._generate_prompt_id(name, version)

        # Create prompt template
        prompt = PromptTemplate(
            prompt_id=prompt_id,
            name=name,
            category=category,
            version=version,
            perspectives=perspectives,
            success_metrics=success_metrics,
            context_layers=context_layers,
            task_breakdown=task_breakdown,
            self_critique=self_critique,
            system_message=system_message,
            user_template=user_template,
            reasoning_strategy=reasoning_strategy,
            reasoning_config=reasoning_config or {},
            tags=tags or [],
            created_at=datetime.utcnow().isoformat() + 'Z',
            updated_at=datetime.utcnow().isoformat() + 'Z',
            performance_score=0.0,
            usage_count=0,
            success_rate=0.0
        )

        # Convert to dict for storage
        prompt_dict = self._prompt_to_dict(prompt)

        # Store in RAG
        content = self._build_searchable_content(prompt)
        metadata = {
            "category": category,
            "version": version,
            "tags": json.dumps(tags or []),
            "performance_score": 0.0
        }

        artifact_id = self.rag.store_artifact(
            artifact_type="prompt_template",
            card_id="system",  # System-level prompts
            task_title=name,
            content=content,
            metadata={**metadata, "prompt_data": json.dumps(prompt_dict)}
        )

        if self.verbose:
            print(f"[PromptManager] ✅ Stored prompt: {name} (v{version})")

        return prompt_id

    def get_prompt(
        self,
        name: str,
        version: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[PromptTemplate]:
        """
        Retrieve a prompt template by name

        Args:
            name: Prompt name
            version: Specific version (None = latest)
            context: Optional context for customization

        Returns:
            PromptTemplate or None
        """
        self.debug_log("Getting prompt", name=name, version=version or "latest")

        # Query RAG for prompt
        filters = {"task_title": name}
        if version:
            filters["version"] = version

        results = self.rag.query_similar(
            query_text=name,
            artifact_types=["prompt_template"],
            top_k=1,
            filters=filters
        )

        if not results:
            self.debug_log("Prompt not found", name=name)
            if self.verbose:
                print(f"[PromptManager] ⚠️  Prompt not found: {name}")
            return None

        # Parse prompt from result
        prompt_data = results[0]["metadata"]["prompt_data"]
        # If it's already a dict (from RAG deserialization), use it directly
        if isinstance(prompt_data, str):
            prompt_data = json.loads(prompt_data)
        prompt = self._dict_to_prompt(prompt_data)

        # Increment usage count
        self._increment_usage(prompt.prompt_id)

        if self.verbose:
            print(f"[PromptManager] 📝 Retrieved prompt: {name} (v{prompt.version})")

        return prompt

    def query_prompts(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_performance: float = 0.0,
        top_k: int = 5
    ) -> List[PromptTemplate]:
        """
        Query prompts by category, tags, or performance

        Args:
            category: Filter by category
            tags: Filter by tags
            min_performance: Minimum performance score
            top_k: Number of results

        Returns:
            List of PromptTemplates
        """
        filters = {}
        if category:
            filters["category"] = category

        query_text = f"{category or ''} {' '.join(tags or [])}"

        results = self.rag.query_similar(
            query_text=query_text,
            artifact_types=["prompt_template"],
            top_k=top_k,
            filters=filters if filters else None
        )

        prompts = []
        for result in results:
            prompt_data = result["metadata"]["prompt_data"]
            # If it's already a dict (from RAG deserialization), use it directly
            if isinstance(prompt_data, str):
                prompt_data = json.loads(prompt_data)
            prompt = self._dict_to_prompt(prompt_data)

            # Filter by performance
            if prompt.performance_score >= min_performance:
                prompts.append(prompt)

        return prompts

    def render_prompt(
        self,
        prompt: PromptTemplate,
        variables: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Render a prompt template with variables and reasoning strategy

        Args:
            prompt: PromptTemplate
            variables: Variables to fill in template

        Returns:
            Dict with 'system' and 'user' messages
        """
        self.debug_log("Rendering prompt", prompt_name=prompt.name, variables_count=len(variables))

        # Build system message with DEPTH framework
        system_parts = [prompt.system_message]

        # Add perspectives
        if prompt.perspectives:
            perspectives_text = "\n".join([
                f"- {p}" for p in prompt.perspectives
            ])
            system_parts.append(f"\n**Multiple Expert Perspectives:**\n{perspectives_text}")

        # Add success metrics
        if prompt.success_metrics:
            metrics_text = "\n".join([
                f"- {m}" for m in prompt.success_metrics
            ])
            system_parts.append(f"\n**Success Criteria:**\n{metrics_text}")

        # Add reasoning strategy instructions
        if prompt.reasoning_strategy != ReasoningStrategyType.NONE:
            reasoning_instructions = self._get_reasoning_instructions(prompt.reasoning_strategy)
            system_parts.append(f"\n**Reasoning Strategy:**\n{reasoning_instructions}")

        # Add self-critique
        if prompt.self_critique:
            system_parts.append(f"\n**Self-Validation:**\n{prompt.self_critique}")

        system_message = "\n".join(system_parts)

        # Render user template with variables
        user_message = prompt.user_template
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            user_message = user_message.replace(placeholder, str(value))

        # Add context layers
        if prompt.context_layers:
            context_text = "\n\n**Context:**\n"
            for key, value in prompt.context_layers.items():
                context_text += f"- {key}: {value}\n"
            user_message += context_text

        # Add reasoning-specific templates
        if prompt.reasoning_strategy == ReasoningStrategyType.CHAIN_OF_THOUGHT:
            user_message += self._get_cot_template(prompt.reasoning_config)
        elif prompt.reasoning_strategy == ReasoningStrategyType.TREE_OF_THOUGHTS:
            user_message += self._get_tot_template(prompt.reasoning_config)
        elif prompt.reasoning_strategy == ReasoningStrategyType.LOGIC_OF_THOUGHTS:
            user_message += self._get_lot_template(prompt.reasoning_config)

        # Add task breakdown
        if prompt.task_breakdown:
            tasks_text = "\n\n**Task Breakdown:**\n"
            for i, task in enumerate(prompt.task_breakdown, 1):
                tasks_text += f"{i}. {task}\n"
            user_message += tasks_text

        return {
            "system": system_message,
            "user": user_message
        }

    def _get_reasoning_instructions(self, strategy: ReasoningStrategyType) -> str:
        """Get reasoning strategy instructions"""
        instructions = {
            ReasoningStrategyType.CHAIN_OF_THOUGHT: """
You MUST think through this problem step-by-step, showing all intermediate reasoning.
Break down complex problems into logical steps and explain each step clearly.
""",
            ReasoningStrategyType.TREE_OF_THOUGHTS: """
Explore multiple approaches in parallel. For each approach:
1. Describe the core idea
2. List advantages and challenges
3. Score from 0-10
Present alternatives as JSON array.
""",
            ReasoningStrategyType.LOGIC_OF_THOUGHTS: """
Use formal logical reasoning and deductions. Apply logical rules:
- Modus Ponens: If P then Q, P is true, therefore Q
- Modus Tollens: If P then Q, Q is false, therefore P is false
- Syllogism: If P then Q, Q then R, therefore P then R
Show each deduction explicitly.
""",
            ReasoningStrategyType.SELF_CONSISTENCY: """
Solve this problem and show your complete reasoning.
Your answer will be sampled multiple times to ensure consistency.
"""
        }
        return instructions.get(strategy, "")

    def _get_cot_template(self, config: Dict[str, Any]) -> str:
        """Get Chain of Thought template"""
        template = "\n\n**Think Step by Step:**\n"
        template += "1. First, identify what information we have\n"
        template += "2. Then, determine what we need to find\n"
        template += "3. Next, break down the solution into logical steps\n"
        template += "4. Work through each step carefully\n"
        template += "5. Finally, verify the answer makes sense\n"

        # Add examples if provided
        examples = config.get("examples", [])
        if examples:
            template += "\n**Example Reasoning:**\n"
            for i, ex in enumerate(examples, 1):
                template += f"\nExample {i}:\n"
                template += f"Q: {ex.get('question', '')}\n"
                template += f"Reasoning: {ex.get('reasoning', '')}\n"
                template += f"A: {ex.get('answer', '')}\n"

        return template

    def _get_tot_template(self, config: Dict[str, Any]) -> str:
        """Get Tree of Thoughts template"""
        branching = config.get("branching_factor", 3)
        template = f"\n\n**Explore {branching} Different Approaches:**\n"
        template += "For each approach provide:\n"
        template += "- Core idea\n"
        template += "- Advantages\n"
        template += "- Challenges\n"
        template += "- Score (0-10)\n"
        return template

    def _get_lot_template(self, config: Dict[str, Any]) -> str:
        """Get Logic of Thoughts template"""
        template = "\n\n**Apply Formal Logic:**\n"
        template += "1. Identify all given premises\n"
        template += "2. State any assumptions clearly\n"
        template += "3. Apply logical rules step by step\n"
        template += "4. Show each deduction explicitly\n"
        template += "5. Verify conclusion follows logically\n"

        # Add axioms if provided
        axioms = config.get("axioms", [])
        if axioms:
            template += "\n**Known Facts (Axioms):**\n"
            for i, axiom in enumerate(axioms, 1):
                template += f"{i}. {axiom}\n"

        return template

    def update_performance(
        self,
        prompt_id: str,
        success: bool
    ):
        """
        Update prompt performance metrics

        Args:
            prompt_id: Prompt ID
            success: Whether the prompt led to successful outcome
        """
        # This would update the prompt in RAG with new metrics
        # For now, we'll just log it
        if self.verbose:
            outcome = "✅ Success" if success else "❌ Failure"
            print(f"[PromptManager] {outcome} for prompt: {prompt_id}")

    # Helper methods

    def _generate_prompt_id(self, name: str, version: str) -> str:
        """Generate unique prompt ID"""
        content = f"{name}-{version}-{datetime.utcnow().isoformat()}"
        return f"prompt-{hashlib.md5(content.encode()).hexdigest()[:8]}"

    def _build_searchable_content(self, prompt: PromptTemplate) -> str:
        """Build searchable content from prompt"""
        parts = [
            f"Name: {prompt.name}",
            f"Category: {prompt.category}",
            f"Perspectives: {', '.join(prompt.perspectives)}",
            f"Success Metrics: {', '.join(prompt.success_metrics)}",
            f"System Message: {prompt.system_message}",
            f"User Template: {prompt.user_template}",
            f"Tags: {', '.join(prompt.tags)}"
        ]
        return "\n\n".join(parts)

    def _prompt_to_dict(self, prompt: PromptTemplate) -> Dict:
        """Convert PromptTemplate to dict"""
        return {
            "prompt_id": prompt.prompt_id,
            "name": prompt.name,
            "category": prompt.category,
            "version": prompt.version,
            "perspectives": prompt.perspectives,
            "success_metrics": prompt.success_metrics,
            "context_layers": prompt.context_layers,
            "task_breakdown": prompt.task_breakdown,
            "self_critique": prompt.self_critique,
            "system_message": prompt.system_message,
            "user_template": prompt.user_template,
            "tags": prompt.tags,
            "created_at": prompt.created_at,
            "updated_at": prompt.updated_at,
            "performance_score": prompt.performance_score,
            "usage_count": prompt.usage_count,
            "success_rate": prompt.success_rate
        }

    def _dict_to_prompt(self, data: Dict) -> PromptTemplate:
        """Convert dict to PromptTemplate"""
        return PromptTemplate(**data)

    def _increment_usage(self, prompt_id: str):
        """Increment usage count for prompt"""
        # This would update the RAG entry
        pass


# ============================================================================
# EXAMPLE PROMPTS WITH DEPTH FRAMEWORK
# ============================================================================

def create_default_prompts(prompt_manager: PromptManager):
    """
    Create default prompts for Artemis agents with DEPTH framework applied
    """

    # 1. Developer Agent - Conservative Implementation
    prompt_manager.store_prompt(
        name="developer_conservative_implementation",
        category="developer_agent",
        perspectives=[
            "Senior Software Engineer with 15+ years focusing on reliability and maintainability",
            "QA Engineer who prioritizes testability and edge case handling",
            "Tech Lead who reviews code for SOLID principles and best practices"
        ],
        success_metrics=[
            "Code compiles without syntax errors",
            "Returns valid JSON matching expected schema",
            "Includes comprehensive unit tests (85%+ coverage)",
            "Follows SOLID principles (validated against checklist)",
            "No generic AI clichés like 'robust', 'delve into', 'leverage'",
            "Clear, production-ready implementation (not placeholder code)"
        ],
        context_layers={
            "developer_type": "conservative",
            "approach": "Proven patterns, stability over innovation",
            "code_quality": "Production-ready, battle-tested solutions",
            "testing": "TDD with comprehensive test coverage",
            "principles": "SOLID, DRY, KISS, YAGNI"
        },
        task_breakdown=[
            "Analyze the task requirements and ADR architectural decisions",
            "Identify all edge cases and error conditions that need handling",
            "Design the solution using proven design patterns",
            "Write failing tests first (TDD approach)",
            "Implement the solution to make tests pass",
            "Refactor for SOLID principles and code clarity",
            "Self-validate: Check JSON format, test coverage, and code quality"
        ],
        self_critique="""Before responding, validate your implementation:
1. Does the JSON parse without errors?
2. Are all required fields present in the JSON response?
3. Is test coverage >= 85%?
4. Did you avoid AI clichés and generic language?
5. Is this production-ready code (not TODO placeholders)?
6. Does it follow SOLID principles?

If any answer is NO, revise your implementation.""",
        system_message=f"""You are {{developer_name}}, a conservative senior software developer with 15+ years of experience.

Your core principles:
- Stability and reliability over clever tricks
- Proven patterns over experimental approaches
- Comprehensive testing and error handling
- SOLID principles strictly applied
- Production-ready code (no TODOs or placeholders)

{CODING_STANDARDS_ALL_LANGUAGES}

You MUST respond with valid JSON only - no explanations, no markdown, just pure JSON.""",
        user_template="""Implement the following task:

**Task:** {task_title}

**Architecture Decision (ADR):**
{adr_content}

**Code Review Feedback (if available):**
{code_review_feedback}

**Response Format:**
Return a JSON object with this exact structure:
{{
  "approach": "Brief description of your approach",
  "implementation": {{
    "filename": "your_solution.py",
    "content": "Complete implementation code"
  }},
  "tests": {{
    "filename": "test_your_solution.py",
    "content": "Complete test code"
  }},
  "explanation": "Brief explanation of key decisions"
}}""",
        tags=["developer", "conservative", "production-ready", "TDD"],
        version="1.0"
    )

    print("[PromptManager] ✅ Created default prompts with DEPTH framework")


if __name__ == "__main__":
    # Example usage
    from rag_agent import RAGAgent

    rag = RAGAgent(db_path="db", verbose=True)
    pm = PromptManager(rag, verbose=True)

    # Create default prompts
    create_default_prompts(pm)

    # Retrieve and render a prompt
    prompt = pm.get_prompt("developer_conservative_implementation")
    if prompt:
        rendered = pm.render_prompt(prompt, {
            "developer_name": "developer-a",
            "task_title": "Create user authentication module",
            "adr_content": "Use JWT tokens with RS256 signing...",
            "code_review_feedback": "No previous feedback"
        })

        print("\n" + "=" * 70)
        print("RENDERED PROMPT:")
        print("=" * 70)
        print("\nSYSTEM MESSAGE:")
        print(rendered["system"])
        print("\nUSER MESSAGE:")
        print(rendered["user"][:500] + "...")
