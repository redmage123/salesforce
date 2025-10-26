#!/usr/bin/env python3
"""
Supervisor Learning System - Dynamic Problem Solving

Enables the supervisor to learn from unexpected states by:
1. Detecting unknown/unexpected states
2. Querying LLM for solutions
3. Generating new recovery workflows dynamically
4. Storing solutions in RAG for future reuse
5. Evolving recovery strategies over time

SOLID Principles:
- Single Responsibility: Only handles learning and workflow generation
- Open/Closed: Extensible with new learning strategies
- Dependency Inversion: Depends on abstractions (LLM interface, RAG interface)
"""

import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum


class LearningStrategy(Enum):
    """Learning strategy types"""
    LLM_CONSULTATION = "llm_consultation"      # Ask LLM for solution
    SIMILAR_CASE_ADAPTATION = "similar_case"   # Adapt from similar past cases
    HUMAN_IN_LOOP = "human_in_loop"            # Ask human for guidance
    EXPERIMENTAL_TRIAL = "experimental"        # Try experimental solutions


@dataclass
class UnexpectedState:
    """Represents an unexpected system state"""
    state_id: str
    timestamp: str
    card_id: str
    stage_name: Optional[str]
    error_message: Optional[str]
    context: Dict[str, Any]
    stack_trace: Optional[str]
    previous_state: Optional[str]
    current_state: str
    expected_states: List[str]  # What states were expected
    severity: str  # low, medium, high, critical


@dataclass
class LearnedSolution:
    """Represents a learned solution to a problem"""
    solution_id: str
    timestamp: str
    unexpected_state_id: str
    problem_description: str
    solution_description: str
    workflow_steps: List[Dict[str, Any]]
    success_rate: float
    times_applied: int
    times_successful: int
    learning_strategy: str
    llm_model_used: Optional[str]
    human_validated: bool
    metadata: Dict[str, Any]


class SupervisorLearningEngine:
    """
    Learning engine for supervisor agent

    Enables supervisor to learn from unexpected states and generate
    new recovery workflows dynamically.
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        rag_agent: Optional[Any] = None,
        verbose: bool = True
    ):
        """
        Initialize learning engine

        Args:
            llm_client: LLM client for querying solutions
            rag_agent: RAG agent for storing/retrieving learned solutions
            verbose: Enable verbose logging
        """
        self.llm_client = llm_client
        self.rag_agent = rag_agent
        self.verbose = verbose

        # Storage for learned solutions (in-memory cache)
        self.learned_solutions: Dict[str, LearnedSolution] = {}

        # Statistics
        self.stats = {
            "unexpected_states_detected": 0,
            "solutions_learned": 0,
            "solutions_applied": 0,
            "llm_consultations": 0,
            "successful_applications": 0,
            "failed_applications": 0
        }

    def detect_unexpected_state(
        self,
        card_id: str,
        current_state: str,
        expected_states: List[str],
        context: Dict[str, Any]
    ) -> Optional[UnexpectedState]:
        """
        Detect if current state is unexpected

        Args:
            card_id: Card ID
            current_state: Current pipeline state
            expected_states: List of expected states
            context: Context information

        Returns:
            UnexpectedState if state is unexpected, None otherwise
        """
        if current_state in expected_states:
            return None  # State is expected

        # State is unexpected!
        self.stats["unexpected_states_detected"] += 1

        unexpected = UnexpectedState(
            state_id=f"unexpected-{card_id}-{datetime.utcnow().timestamp()}",
            timestamp=datetime.utcnow().isoformat() + 'Z',
            card_id=card_id,
            stage_name=context.get("stage_name"),
            error_message=context.get("error_message"),
            context=context,
            stack_trace=context.get("stack_trace"),
            previous_state=context.get("previous_state"),
            current_state=current_state,
            expected_states=expected_states,
            severity=self._assess_severity(current_state, context)
        )

        if self.verbose:
            print(f"[Learning] 🚨 Unexpected state detected!")
            print(f"[Learning]    Current: {current_state}")
            print(f"[Learning]    Expected: {expected_states}")
            print(f"[Learning]    Severity: {unexpected.severity}")

        return unexpected

    def learn_solution(
        self,
        unexpected_state: UnexpectedState,
        strategy: LearningStrategy = LearningStrategy.LLM_CONSULTATION
    ) -> Optional[LearnedSolution]:
        """
        Learn a solution for an unexpected state

        Args:
            unexpected_state: The unexpected state
            strategy: Learning strategy to use

        Returns:
            LearnedSolution if solution found, None otherwise
        """
        if self.verbose:
            print(f"[Learning] 🧠 Learning solution using strategy: {strategy.value}")

        # Try to find existing similar solutions first
        similar_solutions = self._find_similar_solutions(unexpected_state)

        if similar_solutions and strategy == LearningStrategy.SIMILAR_CASE_ADAPTATION:
            # Adapt from similar case
            return self._adapt_from_similar(unexpected_state, similar_solutions[0])

        # No similar solution, consult LLM
        if strategy == LearningStrategy.LLM_CONSULTATION:
            return self._consult_llm_for_solution(unexpected_state)

        # Human in the loop
        if strategy == LearningStrategy.HUMAN_IN_LOOP:
            return self._request_human_guidance(unexpected_state)

        return None

    def _consult_llm_for_solution(
        self,
        unexpected_state: UnexpectedState
    ) -> Optional[LearnedSolution]:
        """
        Consult LLM for solution to unexpected state

        Args:
            unexpected_state: The unexpected state

        Returns:
            LearnedSolution from LLM
        """
        if not self.llm_client:
            if self.verbose:
                print(f"[Learning] ⚠️  No LLM client available for consultation")
            return None

        self.stats["llm_consultations"] += 1

        # Build detailed prompt for LLM
        prompt = self._build_llm_prompt(unexpected_state)

        if self.verbose:
            print(f"[Learning] 💬 Consulting LLM for solution...")

        try:
            # Query LLM (this is the key learning step!)
            # Convert string prompt to message format
            from llm_client import LLMMessage
            messages = [LLMMessage(role="user", content=prompt)]
            response = self.llm_client.complete(messages, max_tokens=2000, temperature=0.7)

            # Parse LLM response into workflow steps
            workflow_steps = self._parse_llm_response(response.content)

            # Create learned solution
            solution = LearnedSolution(
                solution_id=f"learned-{unexpected_state.state_id}",
                timestamp=datetime.utcnow().isoformat() + 'Z',
                unexpected_state_id=unexpected_state.state_id,
                problem_description=self._describe_problem(unexpected_state),
                solution_description=self._extract_solution_description(response.content),
                workflow_steps=workflow_steps,
                success_rate=0.0,  # Unknown yet
                times_applied=0,
                times_successful=0,
                learning_strategy=LearningStrategy.LLM_CONSULTATION.value,
                llm_model_used=getattr(response, 'model', 'unknown'),
                human_validated=False,
                metadata={
                    "llm_tokens_input": getattr(response.usage, 'prompt_tokens', 0),
                    "llm_tokens_output": getattr(response.usage, 'completion_tokens', 0),
                    "llm_response_raw": response.content
                }
            )

            # Store in memory
            self.learned_solutions[solution.solution_id] = solution

            # Store in RAG for future retrieval
            if self.rag_agent:
                self._store_solution_in_rag(solution, unexpected_state)

            self.stats["solutions_learned"] += 1

            if self.verbose:
                print(f"[Learning] ✅ Solution learned from LLM!")
                print(f"[Learning]    Solution ID: {solution.solution_id}")
                print(f"[Learning]    Workflow steps: {len(solution.workflow_steps)}")

            return solution

        except Exception as e:
            if self.verbose:
                print(f"[Learning] ❌ LLM consultation failed: {e}")
            return None

    def apply_learned_solution(
        self,
        solution: LearnedSolution,
        context: Dict[str, Any]
    ) -> bool:
        """
        Apply a learned solution

        Args:
            solution: The learned solution
            context: Execution context

        Returns:
            True if solution succeeded
        """
        self.stats["solutions_applied"] += 1
        solution.times_applied += 1

        if self.verbose:
            print(f"[Learning] 🔧 Applying learned solution: {solution.solution_id}")
            print(f"[Learning]    Description: {solution.solution_description}")

        try:
            # Execute workflow steps
            for i, step in enumerate(solution.workflow_steps, 1):
                if self.verbose:
                    print(f"[Learning]    Step {i}/{len(solution.workflow_steps)}: {step.get('action', 'unknown')}")

                # Execute step (this would integrate with state machine/workflows)
                success = self._execute_workflow_step(step, context)

                if not success:
                    if self.verbose:
                        print(f"[Learning]    ❌ Step {i} failed")
                    solution.times_successful += 0
                    self.stats["failed_applications"] += 1
                    return False

            # All steps succeeded
            solution.times_successful += 1
            solution.success_rate = solution.times_successful / solution.times_applied
            self.stats["successful_applications"] += 1

            if self.verbose:
                print(f"[Learning] ✅ Solution applied successfully!")
                print(f"[Learning]    Success rate: {solution.success_rate*100:.1f}% ({solution.times_successful}/{solution.times_applied})")

            # Update in RAG
            if self.rag_agent:
                self._update_solution_in_rag(solution)

            return True

        except Exception as e:
            if self.verbose:
                print(f"[Learning] ❌ Solution application failed: {e}")

            solution.times_successful += 0
            self.stats["failed_applications"] += 1
            return False

    def _build_llm_prompt(self, unexpected_state: UnexpectedState) -> str:
        """Build detailed prompt for LLM consultation"""

        prompt = f"""You are an expert DevOps/SRE engineer helping debug an autonomous AI development pipeline called Artemis.

UNEXPECTED STATE DETECTED:

Current State: {unexpected_state.current_state}
Expected States: {', '.join(unexpected_state.expected_states)}
Severity: {unexpected_state.severity}

CONTEXT:
Card ID: {unexpected_state.card_id}
Stage: {unexpected_state.stage_name or 'Unknown'}
Previous State: {unexpected_state.previous_state or 'Unknown'}

ERROR INFORMATION:
{unexpected_state.error_message or 'No error message'}

ADDITIONAL CONTEXT:
{json.dumps(unexpected_state.context, indent=2)}

TASK:
Analyze this unexpected state and provide a step-by-step recovery workflow to fix the problem.

Your response MUST be in the following JSON format:

{{
  "problem_analysis": "Brief analysis of what went wrong",
  "root_cause": "Most likely root cause",
  "solution_description": "High-level description of the fix",
  "workflow_steps": [
    {{
      "step": 1,
      "action": "action_type",
      "description": "What this step does",
      "parameters": {{"key": "value"}}
    }},
    ...
  ],
  "confidence": "high|medium|low",
  "risks": ["potential risk 1", "potential risk 2"],
  "alternative_approaches": ["alternative 1", "alternative 2"]
}}

AVAILABLE ACTIONS:
- "retry_stage": Retry the failed stage
- "rollback_to_state": Rollback to a previous state
- "skip_stage": Skip the current stage
- "reset_state": Reset to a clean state
- "cleanup_resources": Clean up stuck resources
- "restart_process": Restart a stuck process
- "manual_intervention": Request human intervention

Provide a practical, actionable recovery workflow.
"""
        return prompt

    def _parse_llm_response(self, llm_response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into workflow steps"""
        try:
            # Try to parse as JSON
            response_data = json.loads(llm_response)

            if "workflow_steps" in response_data:
                return response_data["workflow_steps"]

            # If no workflow_steps, try to extract from text
            return self._extract_workflow_from_text(llm_response)

        except json.JSONDecodeError:
            # Not JSON, try to extract workflow from text
            return self._extract_workflow_from_text(llm_response)

    def _extract_workflow_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract workflow steps from unstructured text"""
        # Simple heuristic: look for numbered steps
        steps = []
        lines = text.split('\n')

        for line in lines:
            # Look for patterns like "1. ", "Step 1:", etc.
            if any(pattern in line.lower() for pattern in ["1.", "2.", "3.", "step 1", "step 2"]):
                steps.append({
                    "step": len(steps) + 1,
                    "action": "manual_intervention",  # Default to manual
                    "description": line.strip(),
                    "parameters": {}
                })

        return steps if steps else [
            {
                "step": 1,
                "action": "manual_intervention",
                "description": "Consult LLM response for guidance",
                "parameters": {"llm_response": text[:500]}
            }
        ]

    def _execute_workflow_step(
        self,
        step: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Execute a single workflow step

        Args:
            step: Workflow step to execute
            context: Execution context

        Returns:
            True if step succeeded
        """
        action = step.get("action", "unknown")

        # This would integrate with the state machine's workflow execution
        # For now, we'll simulate execution

        if action == "manual_intervention":
            if self.verbose:
                print(f"[Learning]       Action: {action} - {step.get('description')}")
            # Would trigger human notification
            return True

        elif action == "retry_stage":
            if self.verbose:
                print(f"[Learning]       Action: Retry stage")
            # Would trigger stage retry
            return True

        elif action == "rollback_to_state":
            state = step.get("parameters", {}).get("target_state")
            if self.verbose:
                print(f"[Learning]       Action: Rollback to {state}")
            # Would trigger rollback
            return True

        elif action == "cleanup_resources":
            if self.verbose:
                print(f"[Learning]       Action: Cleanup resources")
            # Would trigger resource cleanup
            return True

        else:
            if self.verbose:
                print(f"[Learning]       Action: {action} (simulated)")
            return True

    def _find_similar_solutions(
        self,
        unexpected_state: UnexpectedState
    ) -> List[LearnedSolution]:
        """Find similar solutions from past cases"""

        if not self.rag_agent:
            return []

        try:
            # Build query from unexpected state
            query = f"""
            Unexpected state: {unexpected_state.current_state}
            Stage: {unexpected_state.stage_name}
            Error: {unexpected_state.error_message}
            """.strip()

            # Query RAG for similar past solutions
            results = self.rag_agent.query_similar(
                query_text=query,
                artifact_types=["learned_solution", "recovery_workflow"],
                top_k=3
            )

            if self.verbose and results:
                print(f"[Learning] 📚 Found {len(results)} similar past solutions")

            return results

        except Exception as e:
            if self.verbose:
                print(f"[Learning] ⚠️  Failed to query similar solutions: {e}")
            return []

    def _adapt_from_similar(
        self,
        unexpected_state: UnexpectedState,
        similar_solution: Dict[str, Any]
    ) -> LearnedSolution:
        """Adapt a solution from a similar past case"""

        # Extract workflow from similar solution
        original_workflow = similar_solution.get("metadata", {}).get("workflow_steps", [])

        # Create adapted solution
        solution = LearnedSolution(
            solution_id=f"adapted-{unexpected_state.state_id}",
            timestamp=datetime.utcnow().isoformat() + 'Z',
            unexpected_state_id=unexpected_state.state_id,
            problem_description=self._describe_problem(unexpected_state),
            solution_description=f"Adapted from similar case: {similar_solution.get('content', '')[:100]}",
            workflow_steps=original_workflow,
            success_rate=similar_solution.get("metadata", {}).get("success_rate", 0.0),
            times_applied=0,
            times_successful=0,
            learning_strategy=LearningStrategy.SIMILAR_CASE_ADAPTATION.value,
            llm_model_used=None,
            human_validated=False,
            metadata={
                "adapted_from": similar_solution.get("artifact_id"),
                "similarity_score": similar_solution.get("score", 0.0)
            }
        )

        self.learned_solutions[solution.solution_id] = solution
        self.stats["solutions_learned"] += 1

        if self.verbose:
            print(f"[Learning] ♻️  Solution adapted from similar case")

        return solution

    def _request_human_guidance(
        self,
        unexpected_state: UnexpectedState
    ) -> Optional[LearnedSolution]:
        """Request human guidance for unexpected state"""

        if self.verbose:
            print(f"[Learning] 👤 Requesting human guidance...")
            print(f"[Learning]    Problem: {self._describe_problem(unexpected_state)}")

        # This would integrate with a human-in-the-loop system
        # For now, return None to indicate human intervention needed
        return None

    def _describe_problem(self, unexpected_state: UnexpectedState) -> str:
        """Generate human-readable problem description"""
        parts = [f"Unexpected state: {unexpected_state.current_state}"]

        if unexpected_state.stage_name:
            parts.append(f"in stage '{unexpected_state.stage_name}'")

        if unexpected_state.error_message:
            parts.append(f"- Error: {unexpected_state.error_message}")

        return " ".join(parts)

    def _extract_solution_description(self, llm_response: str) -> str:
        """Extract solution description from LLM response"""
        try:
            data = json.loads(llm_response)
            return data.get("solution_description", "LLM-generated solution")
        except:
            # Extract first sentence or first 100 chars
            return llm_response.split('.')[0][:100]

    def _assess_severity(
        self,
        current_state: str,
        context: Dict[str, Any]
    ) -> str:
        """Assess severity of unexpected state"""

        # Simple heuristic based on state and context
        if "FAILED" in current_state.upper() or "CRITICAL" in current_state.upper():
            return "critical"
        elif "ERROR" in current_state.upper():
            return "high"
        elif context.get("error_message"):
            return "medium"
        else:
            return "low"

    def _store_solution_in_rag(
        self,
        solution: LearnedSolution,
        unexpected_state: UnexpectedState
    ) -> None:
        """Store learned solution in RAG"""

        if not self.rag_agent:
            return

        try:
            content = f"""
LEARNED SOLUTION

Problem: {solution.problem_description}
Solution: {solution.solution_description}

Unexpected State: {unexpected_state.current_state}
Expected States: {', '.join(unexpected_state.expected_states)}
Stage: {unexpected_state.stage_name or 'Unknown'}

Workflow Steps:
{json.dumps(solution.workflow_steps, indent=2)}

Learning Strategy: {solution.learning_strategy}
Success Rate: {solution.success_rate*100:.1f}%
Times Applied: {solution.times_applied}
            """.strip()

            self.rag_agent.store_artifact(
                artifact_type="learned_solution",
                card_id=unexpected_state.card_id,
                task_title=f"Solution: {solution.problem_description[:50]}",
                content=content,
                metadata={
                    "solution_id": solution.solution_id,
                    "unexpected_state_id": solution.unexpected_state_id,
                    "workflow_steps": solution.workflow_steps,
                    "success_rate": solution.success_rate,
                    "learning_strategy": solution.learning_strategy,
                    "llm_model_used": solution.llm_model_used,
                    "timestamp": solution.timestamp
                }
            )

            if self.verbose:
                print(f"[Learning] 📝 Solution stored in RAG for future learning")

        except Exception as e:
            if self.verbose:
                print(f"[Learning] ⚠️  Failed to store in RAG: {e}")

    def _update_solution_in_rag(self, solution: LearnedSolution) -> None:
        """Update solution success rate in RAG"""
        # Would update the artifact in RAG with new success rate
        # For now, just log
        if self.verbose:
            print(f"[Learning] 📝 Updated solution success rate: {solution.success_rate*100:.1f}%")

    def get_statistics(self) -> Dict[str, Any]:
        """Get learning statistics"""
        return {
            **self.stats,
            "total_learned_solutions": len(self.learned_solutions),
            "average_success_rate": self._calculate_average_success_rate()
        }

    def _calculate_average_success_rate(self) -> float:
        """Calculate average success rate across all solutions"""
        if not self.learned_solutions:
            return 0.0

        total_rate = sum(s.success_rate for s in self.learned_solutions.values())
        return total_rate / len(self.learned_solutions)


if __name__ == "__main__":
    """Example usage and testing"""

    print("Supervisor Learning Engine - Example Usage")
    print("=" * 70)

    # Create learning engine (without real LLM for demo)
    learning = SupervisorLearningEngine(
        llm_client=None,
        rag_agent=None,
        verbose=True
    )

    # Simulate unexpected state
    print("\n1. Detecting unexpected state...")
    unexpected = learning.detect_unexpected_state(
        card_id="card-001",
        current_state="STAGE_STUCK",
        expected_states=["STAGE_RUNNING", "STAGE_COMPLETED"],
        context={
            "stage_name": "development",
            "error_message": "Developer agents not responding",
            "previous_state": "STAGE_RUNNING"
        }
    )

    if unexpected:
        print(f"   Unexpected state ID: {unexpected.state_id}")
        print(f"   Severity: {unexpected.severity}")

        # Would normally consult LLM here, but we'll simulate
        print("\n2. Would consult LLM for solution (simulated)...")
        print("   (In production, this would query GPT-4o/Claude for recovery steps)")

    # Show statistics
    print("\n3. Learning statistics:")
    stats = learning.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 70)
    print("✅ Learning engine initialized and ready!")
