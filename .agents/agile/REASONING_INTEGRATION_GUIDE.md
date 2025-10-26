# Reasoning Strategy Integration Guide

This guide explains how to use Chain of Thought (CoT), Tree of Thoughts (ToT), Logic of Thoughts (LoT), and Self-Consistency reasoning strategies in Artemis.

## Overview

Artemis now supports advanced reasoning strategies that enhance LLM outputs:

- **Chain of Thought (CoT)**: Step-by-step explicit reasoning
- **Tree of Thoughts (ToT)**: Explore multiple solution paths in parallel
- **Logic of Thoughts (LoT)**: Formal logical deductions with axioms
- **Self-Consistency**: Multiple samples with majority voting

## Architecture

### Components

1. **reasoning_strategies.py** - Core reasoning strategy implementations
2. **reasoning_integration.py** - Integration with LLM client and PromptManager

### Design Patterns

- **Strategy Pattern**: Different reasoning approaches with common interface
- **Decorator Pattern**: Enhance LLM calls without modifying base client
- **Factory Pattern**: Strategy selection and creation

## Usage

### Basic Usage - Standalone

```python
from reasoning_strategies import (
    ReasoningStrategy,
    ReasoningStrategyFactory,
    ChainOfThoughtStrategy
)

# Create a reasoning strategy
cot = ChainOfThoughtStrategy()

# Generate reasoning-enhanced prompt
prompt = cot.generate_prompt(
    task="Calculate the total cost if 3 apples cost $1.50 each",
    context="You are a math tutor helping a student",
    examples=[
        {
            "question": "If 2 oranges cost $1.00 each, what is the total?",
            "reasoning": "Step 1: We have 2 oranges at $1.00 each. Step 2: Total = 2 × $1.00 = $2.00",
            "answer": "$2.00"
        }
    ]
)

# Send prompt to LLM (using your LLM client)
# Parse response
result = cot.parse_response(llm_response)
print(result)
```

### Usage with LLM Client Integration

```python
from reasoning_integration import (
    ReasoningEnhancedLLMClient,
    ReasoningConfig,
    create_reasoning_enhanced_client
)
from reasoning_strategies import ReasoningStrategy
from llm_client import LLMMessage

# Create reasoning-enhanced client
client = create_reasoning_enhanced_client("openai")

# Configure reasoning strategy
config = ReasoningConfig(
    strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
    enabled=True,
    temperature=0.7
)

# Build messages
messages = [
    LLMMessage(role="system", content="You are a helpful coding assistant"),
    LLMMessage(role="user", content="Write a function to check if a number is prime")
]

# Execute with reasoning
result = client.complete_with_reasoning(
    messages=messages,
    reasoning_config=config
)

print(result["response"].content)
print(f"Reasoning applied: {result['reasoning_applied']}")
print(f"Strategy: {result['reasoning_strategy']}")
```

### Usage with PromptManager

```python
from reasoning_integration import ReasoningPromptEnhancer, ReasoningConfig
from reasoning_strategies import ReasoningStrategy

# Create enhancer
enhancer = ReasoningPromptEnhancer()

# Base prompt from PromptManager
base_prompt = {
    "system": "You are a senior developer...",
    "user": "Implement user authentication..."
}

# Enhance with reasoning
config = ReasoningConfig(
    strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
    enabled=True
)

enhanced_prompt = enhancer.enhance_prompt_with_reasoning(
    base_prompt=base_prompt,
    reasoning_config=config
)

# Use enhanced prompt with LLM
print(enhanced_prompt["system"])
print(enhanced_prompt["user"])
```

## Reasoning Strategies in Detail

### 1. Chain of Thought (CoT)

Best for: Coding tasks, mathematical problems, step-by-step analysis

```python
from reasoning_integration import get_default_reasoning_config

config = get_default_reasoning_config("coding")
# Returns: ReasoningConfig(strategy=CHAIN_OF_THOUGHT, enabled=True)

# With custom examples
config.cot_examples = [
    {
        "question": "How do you implement a binary search?",
        "reasoning": "Step 1: Start with sorted array. Step 2: Compare middle element...",
        "answer": "def binary_search(arr, target): ..."
    }
]
```

**Output Structure:**
```json
{
  "strategy": "chain_of_thought",
  "steps": [
    {
      "step": 1,
      "description": "Identify what we need",
      "reasoning": "We need to check divisibility...",
      "output": null,
      "confidence": null
    }
  ],
  "total_steps": 5
}
```

### 2. Tree of Thoughts (ToT)

Best for: Architecture decisions, design patterns, exploring alternatives

```python
config = get_default_reasoning_config("architecture")
# Returns: ReasoningConfig(strategy=TREE_OF_THOUGHTS, tot_branching_factor=3)

# Customize branching
config.tot_branching_factor = 5  # Explore 5 alternatives
config.tot_max_depth = 3         # Up to 3 levels deep
```

**Output Structure:**
```json
{
  "strategy": "tree_of_thoughts",
  "branches": 3,
  "thoughts": [
    {
      "thought": "Use microservices architecture",
      "advantages": ["Scalability", "Independent deployment"],
      "challenges": ["Complexity", "Network overhead"],
      "score": 8.5
    }
  ],
  "best_score": 8.5,
  "best_path": ["Root", "Microservices", "Event-driven"]
}
```

### 3. Logic of Thoughts (LoT)

Best for: Requirements analysis, constraint solving, formal reasoning

```python
config = get_default_reasoning_config("analysis")
# Returns: ReasoningConfig(strategy=LOGIC_OF_THOUGHTS)

# Add axioms (known facts)
config.lot_axioms = [
    "All user inputs must be validated",
    "Passwords must be hashed before storage",
    "GDPR requires consent for data processing"
]
```

**Output Structure:**
```json
{
  "strategy": "logic_of_thoughts",
  "rules": [
    {
      "premise": "User submits password",
      "conclusion": "Password must be hashed before storage",
      "rule_type": "deduction",
      "confidence": 1.0
    }
  ],
  "total_rules": 3
}
```

### 4. Self-Consistency

Best for: Critical decisions, test case generation, quality validation

```python
config = get_default_reasoning_config("testing")
# Returns: ReasoningConfig(strategy=SELF_CONSISTENCY, sc_num_samples=3)

# Increase samples for higher confidence
config.sc_num_samples = 5  # Generate 5 independent solutions
```

**Output Structure:**
```json
{
  "strategy": "self_consistency",
  "samples": ["Sample 1...", "Sample 2...", "Sample 3..."],
  "consistent_answer": {
    "answer": "The function should return True",
    "frequency": 4,
    "confidence": 0.8,
    "total_samples": 5
  },
  "total_tokens": 12500
}
```

## Integration with Artemis Agents

### Developer Agent Integration

```python
# In developer_invoker.py or agent implementation
from reasoning_integration import ReasoningEnhancedLLMClient, ReasoningConfig
from reasoning_strategies import ReasoningStrategy

class DeveloperAgent:
    def __init__(self, llm_client):
        # Wrap existing client with reasoning
        self.llm_client = ReasoningEnhancedLLMClient(llm_client)

    def implement_feature(self, task_description):
        # Use Chain of Thought for implementation
        config = ReasoningConfig(
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            enabled=True
        )

        messages = [
            LLMMessage(role="system", content=self.system_prompt),
            LLMMessage(role="user", content=task_description)
        ]

        result = self.llm_client.complete_with_reasoning(
            messages=messages,
            reasoning_config=config
        )

        return result["response"].content
```

### Supervisor Agent Integration

```python
# In supervisor_agent.py
class SupervisorAgent:
    def evaluate_approach(self, task, developer_proposals):
        # Use Tree of Thoughts to evaluate alternatives
        config = ReasoningConfig(
            strategy=ReasoningStrategy.TREE_OF_THOUGHTS,
            enabled=True,
            tot_branching_factor=len(developer_proposals)
        )

        # Build evaluation prompt
        messages = [...]

        result = self.llm_client.complete_with_reasoning(
            messages=messages,
            reasoning_config=config
        )

        # Get best path
        best_approach = result.get("best_path", [])
        return best_approach
```

### Architecture Stage Integration

```python
# In project_analysis_stage or architecture stage
def design_architecture(self, requirements):
    # Use Logic of Thoughts with requirements as axioms
    config = ReasoningConfig(
        strategy=ReasoningStrategy.LOGIC_OF_THOUGHTS,
        enabled=True,
        lot_axioms=requirements  # Known constraints
    )

    result = self.llm_client.complete_with_reasoning(
        messages=[...],
        reasoning_config=config
    )

    # Extract logical rules and architecture decisions
    rules = result["reasoning_output"]["rules"]
    return self._build_architecture_from_rules(rules)
```

## Configuration Best Practices

### Task-Specific Configurations

```python
REASONING_CONFIGS = {
    # Code implementation
    "implement_feature": ReasoningConfig(
        strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
        enabled=True,
        temperature=0.7
    ),

    # Architecture design
    "design_system": ReasoningConfig(
        strategy=ReasoningStrategy.TREE_OF_THOUGHTS,
        enabled=True,
        tot_branching_factor=4,
        tot_max_depth=3,
        temperature=0.8
    ),

    # Security analysis
    "security_audit": ReasoningConfig(
        strategy=ReasoningStrategy.LOGIC_OF_THOUGHTS,
        enabled=True,
        lot_axioms=[
            "All inputs must be validated",
            "Sensitive data must be encrypted",
            "Authentication required for protected resources"
        ],
        temperature=0.5
    ),

    # Test generation
    "generate_tests": ReasoningConfig(
        strategy=ReasoningStrategy.SELF_CONSISTENCY,
        enabled=True,
        sc_num_samples=3,
        temperature=0.9  # Higher for diversity
    )
}
```

### Hydra Configuration

Add to `conf/reasoning/default.yaml`:

```yaml
reasoning:
  enabled: true
  default_strategy: chain_of_thought

  strategies:
    chain_of_thought:
      temperature: 0.7
      max_tokens: 4000

    tree_of_thoughts:
      branching_factor: 3
      max_depth: 4
      temperature: 0.8

    logic_of_thoughts:
      temperature: 0.5
      axioms: []

    self_consistency:
      num_samples: 3
      temperature: 0.9

  task_mappings:
    coding: chain_of_thought
    architecture: tree_of_thoughts
    analysis: logic_of_thoughts
    testing: self_consistency
```

## CLI Usage

### Direct Strategy Testing

```bash
# Test Chain of Thought
python3 reasoning_strategies.py cot --task "Implement quicksort algorithm"

# Test Tree of Thoughts
python3 reasoning_strategies.py tot --task "Design e-commerce database schema"

# Test Logic of Thoughts
python3 reasoning_strategies.py lot --task "Analyze authentication requirements"

# Test Self-Consistency
python3 reasoning_strategies.py sc --task "Generate edge cases for input validation"
```

### Integrated Testing

```bash
# Test with OpenAI
python3 reasoning_integration.py \
    --provider openai \
    --strategy cot \
    --task "Write a function to validate email addresses"

# Test with Anthropic
python3 reasoning_integration.py \
    --provider anthropic \
    --strategy tot \
    --task "Design a caching strategy for web application"

# With context
python3 reasoning_integration.py \
    --provider openai \
    --strategy lot \
    --task "Implement GDPR-compliant user data deletion" \
    --context "Must comply with EU regulations and maintain audit trail"
```

## Performance Considerations

### Token Usage

- **CoT**: ~1.5-2x base tokens (adds reasoning steps)
- **ToT**: ~3-5x base tokens (multiple branches)
- **LoT**: ~1.3-1.8x base tokens (logical structure)
- **Self-Consistency**: N × base tokens (N samples)

### When to Enable Reasoning

**Always Enable:**
- Critical security implementations
- Complex algorithm design
- Architecture decisions
- Production-critical code

**Conditionally Enable:**
- Simple CRUD operations (CoT only if needed)
- Routine refactoring (disable for speed)
- Documentation generation (disable unless complex)

**Configuration:**
```python
# Enable only for complex tasks
if task_complexity > COMPLEXITY_THRESHOLD:
    config.enabled = True
else:
    config.enabled = False
```

## Monitoring and Metrics

Track reasoning effectiveness:

```python
from reasoning_integration import ReasoningEnhancedLLMClient

class MetricsCollector:
    def __init__(self):
        self.reasoning_metrics = {
            "total_calls": 0,
            "reasoning_enabled": 0,
            "strategy_usage": {},
            "token_overhead": []
        }

    def track_call(self, result):
        self.reasoning_metrics["total_calls"] += 1

        if result["reasoning_applied"]:
            self.reasoning_metrics["reasoning_enabled"] += 1

            strategy = result["reasoning_strategy"]
            self.reasoning_metrics["strategy_usage"][strategy] = \
                self.reasoning_metrics["strategy_usage"].get(strategy, 0) + 1

            tokens = result["response"].usage["total_tokens"]
            self.reasoning_metrics["token_overhead"].append(tokens)

    def report(self):
        print(f"Reasoning enabled: {self.reasoning_metrics['reasoning_enabled']} / {self.reasoning_metrics['total_calls']}")
        print(f"Strategy usage: {self.reasoning_metrics['strategy_usage']}")
        print(f"Avg tokens: {sum(self.reasoning_metrics['token_overhead']) / len(self.reasoning_metrics['token_overhead'])}")
```

## Examples

### Example 1: Feature Implementation with CoT

```python
from reasoning_integration import create_reasoning_enhanced_client, ReasoningConfig
from reasoning_strategies import ReasoningStrategy
from llm_client import LLMMessage

client = create_reasoning_enhanced_client("openai")

messages = [
    LLMMessage(
        role="system",
        content="You are a senior Python developer implementing production-ready code."
    ),
    LLMMessage(
        role="user",
        content="Implement a rate limiter using the token bucket algorithm"
    )
]

config = ReasoningConfig(
    strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
    enabled=True
)

result = client.complete_with_reasoning(messages=messages, reasoning_config=config)

# Result includes step-by-step reasoning
print("Implementation with reasoning:")
print(result["response"].content)

print("\nReasoning steps:")
for step in result["reasoning_output"]["steps"]:
    print(f"Step {step['step']}: {step['description']}")
```

### Example 2: Architecture Decision with ToT

```python
config = ReasoningConfig(
    strategy=ReasoningStrategy.TREE_OF_THOUGHTS,
    enabled=True,
    tot_branching_factor=4
)

messages = [
    LLMMessage(
        role="system",
        content="You are a solutions architect designing scalable systems."
    ),
    LLMMessage(
        role="user",
        content="Design a notification system that handles 1M users with email, SMS, and push notifications"
    )
]

result = client.complete_with_reasoning(messages=messages, reasoning_config=config)

# Explore multiple approaches
print("Explored approaches:")
for thought in result["reasoning_output"]["thoughts"]:
    print(f"- {thought['thought']} (score: {thought['score']})")

print(f"\nBest path: {' → '.join(result['best_path'])}")
```

## Troubleshooting

### Issue: Reasoning not applying

**Check:**
1. `config.enabled = True`
2. Base LLM client configured correctly
3. API keys set in environment

### Issue: Poor quality reasoning

**Solutions:**
1. Add few-shot examples (CoT)
2. Increase branching factor (ToT)
3. Add more axioms (LoT)
4. Increase samples (Self-Consistency)

### Issue: High token usage

**Solutions:**
1. Use CoT instead of ToT/Self-Consistency for simple tasks
2. Reduce branching factor: `tot_branching_factor=2`
3. Reduce samples: `sc_num_samples=2`
4. Disable for routine tasks

## Future Enhancements

Planned improvements:

1. **Adaptive Strategy Selection**: Auto-select strategy based on task complexity
2. **Hybrid Strategies**: Combine CoT + ToT for complex problems
3. **Reasoning Cache**: Cache reasoning patterns for similar tasks
4. **Fine-tuning**: Train on reasoning examples to improve quality
5. **Reasoning Validation**: Verify logical consistency of outputs

## References

- [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903)
- [Tree of Thoughts: Deliberate Problem Solving with Large Language Models](https://arxiv.org/abs/2305.10601)
- [Self-Consistency Improves Chain of Thought Reasoning](https://arxiv.org/abs/2203.11171)

## Support

For issues or questions:
1. Check this guide
2. Review example code in `reasoning_integration.py`
3. Run CLI demos: `python3 reasoning_integration.py --help`
