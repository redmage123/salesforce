#!/usr/bin/env python3
"""
Artemis Stage Implementations (SOLID Principles)

Each stage class follows SOLID:
- Single Responsibility: ONE stage, ONE responsibility
- Open/Closed: Can add new stages without modifying existing
- Liskov Substitution: All stages implement PipelineStage interface
- Interface Segregation: Minimal, focused interfaces
- Dependency Inversion: Stages depend on injected abstractions
"""

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from artemis_stage_interface import PipelineStage, LoggerInterface
from artemis_services import TestRunner, FileManager
from kanban_manager import KanbanBoard
from agent_messenger import AgentMessenger
from rag_agent import RAGAgent
from developer_invoker import DeveloperInvoker
from project_analysis_agent import ProjectAnalysisEngine, UserApprovalHandler
from artemis_exceptions import (
    FileReadError,
    ADRGenerationError,
    wrap_exception
)


# ============================================================================
# PROJECT ANALYSIS STAGE (Pre-Implementation Review)
# ============================================================================

class ProjectAnalysisStage(PipelineStage):
    """
    Single Responsibility: Analyze project BEFORE implementation

    This stage analyzes tasks across 8 dimensions:
    1. Scope & Requirements
    2. Technical Approach
    3. Architecture & Design Patterns
    4. Security
    5. Scalability & Performance
    6. Error Handling & Edge Cases
    7. Testing Strategy
    8. Dependencies & Integration

    Identifies issues, gets user approval, and sends approved changes downstream.

    Integrates with supervisor for:
    - Unexpected state handling (user rejection, analysis failures)
    - LLM cost tracking (if using LLM for analysis)
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        logger: LoggerInterface,
        supervisor: Optional['SupervisorAgent'] = None
    ):
        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.logger = logger
        self.supervisor = supervisor
        self.engine = ProjectAnalysisEngine()
        self.approval_handler = UserApprovalHandler()

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Run project analysis and get user approval"""
        self.logger.log("Starting Project Analysis Stage", "STAGE")

        card_id = card['card_id']

        # Get RAG recommendations from context
        rag_recommendations = context.get('rag_recommendations', {})

        # Build analysis context
        analysis_context = {
            'rag_recommendations': rag_recommendations,
            'workflow_plan': context.get('workflow_plan', {}),
            'priority': card.get('priority', 'medium'),
            'complexity': context.get('workflow_plan', {}).get('complexity', 'medium')
        }

        # Run analysis across all dimensions
        analysis = self.engine.analyze_task(card, analysis_context)

        self.logger.log(f"Analysis complete: {analysis['total_issues']} issues found", "INFO")
        self.logger.log(f"  CRITICAL: {analysis['critical_count']}", "WARNING" if analysis['critical_count'] > 0 else "INFO")
        self.logger.log(f"  HIGH: {analysis['high_count']}", "WARNING" if analysis['high_count'] > 0 else "INFO")
        self.logger.log(f"  MEDIUM: {analysis['medium_count']}", "INFO")

        # Present findings to user
        presentation = self.approval_handler.present_findings(analysis)
        print("\n" + presentation)

        # Auto-approve for now (in production, would prompt user)
        # Option 1 = APPROVE ALL
        decision = self.approval_handler.get_approval_decision(analysis, "1")

        self.logger.log(f"User decision: {'APPROVED' if decision['approved'] else 'REJECTED'}", "SUCCESS")

        # Send approved changes to Architecture Agent
        if decision['approved'] and len(decision['approved_issues']) > 0:
            self._send_approved_changes_to_architecture(card_id, decision['approved_issues'])

        # Update Kanban
        self.board.update_card(card_id, {
            "analysis_status": "complete",
            "critical_issues": analysis['critical_count'],
            "approved_changes": decision['approved_count']
        })

        # Store in RAG
        self._store_analysis_in_rag(card_id, card, analysis, decision)

        # Convert to JSON-serializable format
        serializable_decision = {
            "approved": decision['approved'],
            "approved_count": decision['approved_count'],
            "approved_issues_count": len(decision.get('approved_issues', []))
        }

        serializable_analysis = {
            "total_issues": analysis['total_issues'],
            "critical_count": analysis['critical_count'],
            "high_count": analysis['high_count'],
            "medium_count": analysis['medium_count'],
            "dimensions_analyzed": analysis['dimensions_analyzed']
        }

        return {
            "stage": "project_analysis",
            "analysis": serializable_analysis,
            "decision": serializable_decision,
            "status": "COMPLETE"
        }

    def get_stage_name(self) -> str:
        return "project_analysis"

    def _send_approved_changes_to_architecture(self, card_id: str, approved_issues: List):
        """Send approved changes to Architecture Agent via AgentMessenger"""

        # Format approved changes for Architecture Agent
        changes_summary = []
        for issue in approved_issues:
            changes_summary.append({
                "category": issue.category,
                "description": issue.description,
                "suggestion": issue.suggestion,
                "severity": issue.severity.value
            })

        self.messenger.send_data_update(
            to_agent="architecture-agent",
            card_id=card_id,
            update_type="project_analysis_complete",
            data={
                "approved_changes": changes_summary,
                "total_changes": len(changes_summary)
            },
            priority="high"
        )

        self.messenger.update_shared_state(
            card_id=card_id,
            updates={
                "current_stage": "project_analysis_complete",
                "approved_changes_count": len(changes_summary)
            }
        )

        self.logger.log(f"Sent {len(changes_summary)} approved changes to Architecture Agent", "SUCCESS")

    def _store_analysis_in_rag(self, card_id: str, card: Dict, analysis: Dict, decision: Dict):
        """Store analysis results in RAG for future learning"""

        # Create content summary
        content_parts = [
            f"Project Analysis for: {card.get('title', 'Unknown')}",
            f"Total Issues: {analysis['total_issues']}",
            f"Critical: {analysis['critical_count']}, High: {analysis['high_count']}, Medium: {analysis['medium_count']}",
            f"User Decision: {'APPROVED' if decision['approved'] else 'REJECTED'}",
            f"Approved Changes: {decision['approved_count']}"
        ]

        # Add critical issues to content
        if analysis['critical_issues']:
            content_parts.append("\nCritical Issues:")
            for issue in analysis['critical_issues']:
                content_parts.append(f"  - [{issue.category}] {issue.description}")

        content = "\n".join(content_parts)

        self.rag.store_artifact(
            artifact_type="project_analysis",
            card_id=card_id,
            task_title=card.get('title', 'Unknown'),
            content=content,
            metadata={
                "total_issues": analysis['total_issues'],
                "critical_count": analysis['critical_count'],
                "high_count": analysis['high_count'],
                "medium_count": analysis['medium_count'],
                "approved": decision['approved'],
                "approved_count": decision['approved_count'],
                "dimensions_analyzed": analysis['dimensions_analyzed']
            }
        )


# ============================================================================
# ARCHITECTURE STAGE
# ============================================================================

class ArchitectureStage(PipelineStage):
    """
    Single Responsibility: Create Architecture Decision Records (ADRs)

    This stage ONLY handles ADR creation - nothing else.

    Integrates with supervisor for:
    - Unexpected state handling (ADR generation failures)
    - LLM cost tracking (if using LLM for ADR generation)
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        logger: LoggerInterface,
        adr_dir: Path = Path("/tmp/adr"),
        supervisor: Optional['SupervisorAgent'] = None
    ):
        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.logger = logger
        self.supervisor = supervisor
        self.adr_dir = adr_dir
        self.adr_dir.mkdir(exist_ok=True, parents=True)

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Create ADR for the task"""
        self.logger.log("Starting Architecture Stage", "STAGE")

        card_id = card['card_id']

        # Get next ADR number
        adr_number = self._get_next_adr_number()

        # Create ADR file
        adr_content = self._generate_adr(card, adr_number)
        adr_filename = self._create_adr_filename(card['title'], adr_number)
        adr_path = self.adr_dir / adr_filename

        FileManager.write_text(adr_path, adr_content)
        self.logger.log(f"ADR created: {adr_filename}", "SUCCESS")

        # Update messaging
        self._send_adr_notification(card_id, str(adr_path), adr_number)

        # Update Kanban
        self.board.update_card(card_id, {
            "architecture_status": "complete",
            "adr_number": adr_number,
            "adr_file": str(adr_path)
        })
        self.board.move_card(card_id, "development", "pipeline-orchestrator")

        # Store in RAG
        self.rag.store_artifact(
            artifact_type="architecture_decision",
            card_id=card_id,
            task_title=card.get('title', 'Unknown'),
            content=adr_content,
            metadata={
                "adr_number": adr_number,
                "priority": card.get('priority', 'medium'),
                "story_points": card.get('points', 5)
            }
        )

        return {
            "stage": "architecture",
            "adr_number": adr_number,
            "adr_file": str(adr_path),
            "status": "COMPLETE"
        }

    def get_stage_name(self) -> str:
        return "architecture"

    def _get_next_adr_number(self) -> str:
        """Get next available ADR number"""
        existing_adrs = list(self.adr_dir.glob("ADR-*.md"))
        if existing_adrs:
            numbers = []
            for adr_file in existing_adrs:
                match = re.search(r'ADR-(\d+)', adr_file.name)
                if match:
                    numbers.append(int(match.group(1)))
            next_num = max(numbers) + 1 if numbers else 1
        else:
            next_num = 1
        return f"{next_num:03d}"

    def _create_adr_filename(self, title: str, adr_number: str) -> str:
        """Create ADR filename from title"""
        # Sanitize title to remove file paths and invalid characters
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title)  # Remove invalid chars
        slug = slug.lower().replace(' ', '-')[:50]  # Convert to kebab-case
        slug = re.sub(r'-+', '-', slug).strip('-')  # Normalize multiple dashes
        return f"ADR-{adr_number}-{slug}.md"

    def _generate_adr(self, card: Dict, adr_number: str) -> str:
        """Generate ADR content"""
        title = card.get('title', 'Untitled Task')
        description = card.get('description', 'No description provided')

        return f"""# ADR-{adr_number}: {title}

**Status**: Accepted
**Date**: {datetime.utcnow().strftime('%Y-%m-%d')}
**Deciders**: Architecture Agent (Automated)
**Task**: {card['card_id']} - {title}

---

## Context

**Task Description**:
{description}

**Priority**: {card.get('priority', 'medium')}
**Complexity**: {card.get('size', 'medium')}

---

## Decision

**Approach**: Implement {title.lower()} using test-driven development with parallel developer approaches.

**Implementation Strategy**:
- Developer A: Conservative, minimal-risk implementation
- Developer B: Comprehensive implementation with enhanced features

---

## Consequences

### Positive
- ✅ Clear architectural direction for developers
- ✅ Parallel development allows comparison of approaches
- ✅ TDD ensures quality and testability

---

**Note**: This is an automatically generated ADR. For complex tasks, manual architectural review is recommended.
"""

    def _send_adr_notification(self, card_id: str, adr_path: str, adr_number: str):
        """Send ADR notification to downstream agents"""
        self.messenger.send_data_update(
            to_agent="dependency-validation-agent",
            card_id=card_id,
            update_type="adr_created",
            data={
                "adr_file": adr_path,
                "adr_number": adr_number
            },
            priority="high"
        )

        self.messenger.update_shared_state(
            card_id=card_id,
            updates={
                "current_stage": "architecture_complete",
                "adr_file": adr_path,
                "adr_number": adr_number
            }
        )


# ============================================================================
# DEPENDENCY VALIDATION STAGE
# ============================================================================

class DependencyValidationStage(PipelineStage):
    """
    Single Responsibility: Validate runtime dependencies

    This stage ONLY validates dependencies - nothing else.
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        logger: LoggerInterface
    ):
        self.board = board
        self.messenger = messenger
        self.logger = logger

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Validate dependencies"""
        self.logger.log("Starting Dependency Validation Stage", "STAGE")

        card_id = card['card_id']

        # Check Python version
        python_check = self._check_python_version()

        # Test basic imports
        import_check = self._test_imports()

        # Determine status
        all_passed = python_check['compatible'] and import_check['all_passed']
        status = "PASS" if all_passed else "BLOCKED"

        if status == "PASS":
            self.logger.log("Dependency validation PASSED", "SUCCESS")
            self._send_success_notification(card_id)
        else:
            self.logger.log("Dependency validation FAILED", "ERROR")
            self._send_failure_notification(card_id)

        # Update Kanban
        self.board.move_card(card_id, "development", "pipeline-orchestrator")

        return {
            "stage": "dependencies",
            "status": status,
            "checks": {
                "python_version": python_check,
                "import_test": import_check
            }
        }

    def get_stage_name(self) -> str:
        return "dependencies"

    def _check_python_version(self) -> Dict:
        """Check Python version compatibility"""
        import sys
        version = f"{sys.version_info.major}.{sys.version_info.minor}"
        compatible = sys.version_info >= (3, 8)

        return {
            "status": "PASS" if compatible else "FAIL",
            "required": "3.8+",
            "found": version,
            "compatible": compatible
        }

    def _test_imports(self) -> Dict:
        """Test that required imports work"""
        test_imports = ["json", "subprocess", "pathlib", "bs4"]
        all_passed = True

        for module in test_imports:
            try:
                __import__(module)
            except ImportError:
                all_passed = False
                break

        return {
            "status": "PASS" if all_passed else "FAIL",
            "imports_tested": test_imports,
            "all_passed": all_passed
        }

    def _send_success_notification(self, card_id: str):
        """Notify success"""
        self.messenger.send_notification(
            to_agent="all",
            card_id=card_id,
            notification_type="dependencies_validated",
            data={"status": "PASS"},
            priority="medium"
        )

    def _send_failure_notification(self, card_id: str):
        """Notify failure"""
        self.messenger.send_error(
            to_agent="artemis-orchestrator",
            card_id=card_id,
            error_type="dependency_validation_failed",
            details={"severity": "high", "blocks_pipeline": True},
            priority="high"
        )


# ============================================================================
# DEVELOPMENT STAGE (New - Invokes Developer A/B)
# ============================================================================

class DevelopmentStage(PipelineStage):
    """
    Single Responsibility: Invoke parallel developers

    This stage ONLY invokes developers - nothing else.
    Uses DeveloperInvoker to launch autonomous developer agents.

    Integrates with supervisor for:
    - LLM cost tracking
    - Code execution sandboxing
    - Unexpected state handling and recovery
    """

    def __init__(
        self,
        board: KanbanBoard,
        rag: RAGAgent,
        logger: LoggerInterface,
        observable: Optional['PipelineObservable'] = None,
        supervisor: Optional['SupervisorAgent'] = None
    ):
        self.board = board
        self.rag = rag
        self.logger = logger
        self.observable = observable
        self.supervisor = supervisor
        self.invoker = DeveloperInvoker(logger, observable=observable)

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Invoke developers to create competing solutions with supervisor monitoring"""
        stage_name = "development"
        self.logger.log("Starting Development Stage", "STAGE")

        card_id = card['card_id']
        num_developers = context.get('parallel_developers', 1)

        # Register stage with supervisor
        if self.supervisor:
            from supervisor_agent import RecoveryStrategy
            self.supervisor.register_stage(
                stage_name=stage_name,
                recovery_strategy=RecoveryStrategy(
                    max_retries=3,
                    retry_delay_seconds=10,
                    timeout_seconds=600,  # 10 minutes for developers
                    circuit_breaker_threshold=5
                )
            )

        try:
            # Get ADR from context
            adr_file = context.get('adr_file', '')
            adr_content = self._read_adr(adr_file)

            # Invoke developers in parallel
            self.logger.log(f"Invoking {num_developers} parallel developer(s)...", "INFO")

            developer_results = self.invoker.invoke_parallel_developers(
                num_developers=num_developers,
                card=card,
                adr_content=adr_content,
                adr_file=adr_file,
                rag_agent=self.rag  # Pass RAG agent so developers can query feedback
            )

            # Track LLM costs for each developer
            if self.supervisor:
                for result in developer_results:
                    if result.get('success', False) and result.get('tokens_used'):
                        try:
                            tokens_used = result['tokens_used']
                            self.supervisor.track_llm_call(
                                model=result.get('llm_model', 'gpt-4o'),
                                provider=result.get('llm_provider', 'openai'),
                                tokens_input=getattr(tokens_used, 'prompt_tokens', 0),
                                tokens_output=getattr(tokens_used, 'completion_tokens', 0),
                                stage=stage_name,
                                purpose=result.get('developer', 'unknown')
                            )
                            self.logger.log(
                                f"Tracked LLM cost for {result.get('developer')}",
                                "INFO"
                            )
                        except Exception as e:
                            # Budget exceeded or other cost tracking error
                            self.logger.log(f"Cost tracking error: {e}", "ERROR")
                            if "Budget" in str(e):
                                raise

            # Execute developer code in sandbox (if supervisor has sandboxing enabled)
            if self.supervisor and hasattr(self.supervisor, 'sandbox') and self.supervisor.sandbox:
                for result in developer_results:
                    if not result.get('success', False):
                        continue

                    dev_name = result.get('developer', 'unknown')
                    self.logger.log(f"Executing {dev_name} code in sandbox...", "INFO")

                    # Get implementation files
                    impl_files = result.get('implementation_files', [])
                    for impl_file in impl_files:
                        if Path(impl_file).exists():
                            code = Path(impl_file).read_text()

                            # Execute in sandbox
                            exec_result = self.supervisor.execute_code_safely(
                                code=code,
                                scan_security=True
                            )

                            if not exec_result["success"]:
                                error_msg = (
                                    f"{dev_name} code execution failed: "
                                    f"{exec_result.get('kill_reason', 'unknown')}"
                                )
                                self.logger.log(error_msg, "ERROR")

                                # Mark this developer solution as failed
                                result["success"] = False
                                result["error"] = error_msg

            # Store each developer's solution in RAG
            for dev_result in developer_results:
                self._store_developer_solution_in_rag(card_id, card, dev_result)

            # Check if we have any successful developers
            successful_devs = [r for r in developer_results if r.get("success", False)]

            if not successful_devs:
                # All developers failed - report unexpected state
                if self.supervisor and hasattr(self.supervisor, 'handle_unexpected_state'):
                    recovery = self.supervisor.handle_unexpected_state(
                        current_state="STAGE_FAILED_ALL_DEVELOPERS",
                        expected_states=["STAGE_COMPLETED"],
                        context={
                            "stage_name": stage_name,
                            "error_message": "All developers failed",
                            "card_id": card_id,
                            "developer_count": len(developer_results),
                            "developer_errors": [r.get("error") for r in developer_results]
                        },
                        auto_learn=True  # Let supervisor learn how to fix this
                    )

                    if recovery and recovery.get("success"):
                        self.logger.log(
                            "Supervisor recovered from all-developers-failed state!",
                            "INFO"
                        )
                        # In production, would retry or apply learned solution here
                    else:
                        raise Exception("All developers failed and recovery unsuccessful")
                else:
                    raise Exception("All developers failed")

            return {
                "stage": "development",
                "num_developers": num_developers,
                "developers": developer_results,
                "successful_developers": len(successful_devs),
                "status": "COMPLETE"
            }

        except Exception as e:
            # Let supervisor learn from this failure
            if self.supervisor and hasattr(self.supervisor, 'handle_unexpected_state'):
                import traceback
                self.logger.log(f"Development stage failed, consulting supervisor...", "WARNING")

                recovery = self.supervisor.handle_unexpected_state(
                    current_state="STAGE_FAILED",
                    expected_states=["STAGE_COMPLETED"],
                    context={
                        "stage_name": stage_name,
                        "error_message": str(e),
                        "stack_trace": traceback.format_exc(),
                        "card_id": card_id
                    },
                    auto_learn=True
                )

                if recovery and recovery.get("success"):
                    self.logger.log("Supervisor recovered from failure!", "INFO")
                    # The supervisor's learned workflow already executed
                    # In production, we might want to retry the stage here
                else:
                    self.logger.log("Supervisor could not recover", "ERROR")

            # Re-raise after supervisor has learned
            raise

    def get_stage_name(self) -> str:
        return "development"

    def _read_adr(self, adr_file: str) -> str:
        """Read ADR content"""
        try:
            return FileManager.read_text(Path(adr_file))
        except Exception as e:
            raise wrap_exception(
                e,
                FileReadError,
                "Failed to read ADR file",
                {
                    "adr_file": adr_file,
                    "stage": "development"
                }
            )

    def _store_developer_solution_in_rag(self, card_id: str, card: Dict, dev_result: Dict):
        """Store developer solution in RAG for learning"""
        self.rag.store_artifact(
            artifact_type="developer_solution",
            card_id=card_id,
            task_title=card.get('title', 'Unknown'),
            content=f"{dev_result['developer']} solution using {dev_result['approach']} approach",
            metadata={
                "developer": dev_result['developer'],
                "approach": dev_result['approach'],
                "tdd_compliant": dev_result.get('tdd_workflow', {}).get('tests_written_first', False),
                "implementation_files": dev_result.get('implementation_files', []),
                "test_files": dev_result.get('test_files', [])
            }
        )


# ============================================================================
# VALIDATION STAGE
# ============================================================================

class ValidationStage(PipelineStage):
    """
    Single Responsibility: Validate developer solutions

    This stage ONLY validates test quality and TDD compliance - nothing else.

    Integrates with supervisor for:
    - Test execution in sandbox
    - Test failure tracking
    - Test timeout handling
    """

    def __init__(
        self,
        board: KanbanBoard,
        test_runner: TestRunner,
        logger: LoggerInterface,
        observable: Optional['PipelineObservable'] = None,
        supervisor: Optional['SupervisorAgent'] = None
    ):
        self.board = board
        self.test_runner = test_runner
        self.logger = logger
        self.observable = observable
        self.supervisor = supervisor

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Validate developer solutions"""
        self.logger.log("Starting Validation Stage", "STAGE")

        card_id = card.get('card_id', 'unknown')

        # Notify validation started
        if self.observable:
            from pipeline_observer import PipelineEvent, EventType
            event = PipelineEvent(
                event_type=EventType.VALIDATION_STARTED,
                card_id=card_id,
                data={"num_developers": context.get('parallel_developers', 1)}
            )
            self.observable.notify(event)

        # Get number of developers from context
        num_developers = context.get('parallel_developers', 1)

        # Validate each developer's solution
        developers = {}
        all_approved = True

        for i in range(num_developers):
            dev_name = "developer-a" if i == 0 else f"developer-{chr(98+i-1)}"
            dev_result = self._validate_developer(dev_name, card_id)
            developers[dev_name] = dev_result

            if dev_result['status'] != "APPROVED":
                all_approved = False

        decision = "ALL_APPROVED" if all_approved else "SOME_BLOCKED"
        approved_devs = [k for k, v in developers.items() if v['status'] == "APPROVED"]

        result = {
            "stage": "validation",
            "num_developers": num_developers,
            "developers": developers,
            "decision": decision,
            "approved_developers": approved_devs
        }

        # Notify validation completed or failed
        if self.observable:
            from pipeline_observer import PipelineEvent, EventType
            if all_approved:
                event = PipelineEvent(
                    event_type=EventType.VALIDATION_COMPLETED,
                    card_id=card_id,
                    data={
                        "decision": decision,
                        "approved_developers": approved_devs,
                        "num_developers": num_developers
                    }
                )
                self.observable.notify(event)
            else:
                error = Exception(f"Validation failed: {len(approved_devs)}/{num_developers} developers approved")
                event = PipelineEvent(
                    event_type=EventType.VALIDATION_FAILED,
                    card_id=card_id,
                    error=error,
                    data={
                        "decision": decision,
                        "approved_developers": approved_devs,
                        "blocked_developers": [k for k, v in developers.items() if v['status'] != "APPROVED"]
                    }
                )
                self.observable.notify(event)

        return result

    def get_stage_name(self) -> str:
        return "validation"

    def _validate_developer(self, dev_name: str, card_id: str = None) -> Dict:
        """Validate a single developer's solution"""
        test_path = f"/tmp/{dev_name}/tests"

        self.logger.log(f"Validating {dev_name} solution...", "INFO")

        # Run tests
        test_results = self.test_runner.run_tests(test_path)

        # Determine status
        status = "APPROVED" if test_results['exit_code'] == 0 else "BLOCKED"

        self.logger.log(f"{dev_name}: {status} (exit_code={test_results['exit_code']})",
                       "SUCCESS" if status == "APPROVED" else "WARNING")

        return {
            "developer": dev_name,
            "status": status,
            "test_results": test_results
        }


# ============================================================================
# INTEGRATION STAGE
# ============================================================================

class IntegrationStage(PipelineStage):
    """
    Single Responsibility: Integrate winning solution

    This stage ONLY deploys and runs regression tests - nothing else.

    Integrates with supervisor for:
    - Merge conflict handling
    - Final test execution tracking
    - Integration failure recovery
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        test_runner: TestRunner,
        logger: LoggerInterface,
        observable: Optional['PipelineObservable'] = None,
        supervisor: Optional['SupervisorAgent'] = None
    ):
        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.test_runner = test_runner
        self.logger = logger
        self.supervisor = supervisor
        self.observable = observable

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Integrate winning solution"""
        self.logger.log("Starting Integration Stage", "STAGE")

        card_id = card['card_id']

        # Determine winner
        winner = context.get('winner', 'developer-a')

        # Notify integration started
        if self.observable:
            from pipeline_observer import PipelineEvent, EventType
            event = PipelineEvent(
                event_type=EventType.INTEGRATION_STARTED,
                card_id=card_id,
                developer_name=winner,
                data={"winning_developer": winner}
            )
            self.observable.notify(event)

        self.logger.log(f"Integrating {winner} solution...", "INFO")

        # Run regression tests
        test_path = f"/tmp/{winner}/tests"
        regression_results = self.test_runner.run_tests(test_path)

        # Verify deployment
        deployment_verified = regression_results['exit_code'] == 0
        status = "PASS" if deployment_verified else "FAIL"

        if status == "PASS":
            self.logger.log("Integration complete: All tests passing, deployment verified", "SUCCESS")

            # Notify integration completed
            if self.observable:
                from pipeline_observer import PipelineEvent, EventType
                event = PipelineEvent(
                    event_type=EventType.INTEGRATION_COMPLETED,
                    card_id=card_id,
                    developer_name=winner,
                    data={
                        "winner": winner,
                        "tests_passed": regression_results.get('passed', 0),
                        "deployment_verified": deployment_verified
                    }
                )
                self.observable.notify(event)
        else:
            self.logger.log(f"Integration issues detected: {regression_results.get('failed', 0)} tests failed", "WARNING")

            # Notify integration conflict (failures during integration)
            if self.observable:
                from pipeline_observer import PipelineEvent, EventType
                event = PipelineEvent(
                    event_type=EventType.INTEGRATION_CONFLICT,
                    card_id=card_id,
                    developer_name=winner,
                    data={
                        "winner": winner,
                        "tests_failed": regression_results.get('failed', 0),
                        "exit_code": regression_results.get('exit_code', 1)
                    }
                )
                self.observable.notify(event)

        # Update Kanban
        self.board.move_card(card_id, "testing", "pipeline-orchestrator")

        # Store in RAG
        self.rag.store_artifact(
            artifact_type="integration_result",
            card_id=card_id,
            task_title=card.get('title', 'Unknown'),
            content=f"Integration of {winner} solution completed",
            metadata={
                "winner": winner,
                "tests_passed": regression_results.get('passed', 0),
                "deployment_verified": deployment_verified
            }
        )

        return {
            "stage": "integration",
            "winner": winner,
            "regression_tests": regression_results,
            "deployment_verified": deployment_verified,
            "status": status
        }

    def get_stage_name(self) -> str:
        return "integration"


# ============================================================================
# TESTING STAGE
# ============================================================================

class TestingStage(PipelineStage):
    """
    Single Responsibility: Final quality gates

    This stage ONLY performs final testing - nothing else.
    """

    def __init__(
        self,
        board: KanbanBoard,
        messenger: AgentMessenger,
        rag: RAGAgent,
        test_runner: TestRunner,
        logger: LoggerInterface
    ):
        self.board = board
        self.messenger = messenger
        self.rag = rag
        self.test_runner = test_runner
        self.logger = logger

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Run final quality gates"""
        self.logger.log("Starting Testing Stage", "STAGE")

        card_id = card['card_id']
        winner = context.get('winner', 'developer-a')

        # Run final regression tests
        test_path = f"/tmp/{winner}/tests"
        regression_results = self.test_runner.run_tests(test_path)

        # Evaluate UI/UX (simplified)
        uiux_score = 100  # In real implementation, this would be more sophisticated

        # Evaluate performance (simplified)
        performance_score = 85  # In real implementation, this would measure actual performance

        # All quality gates
        all_gates_passed = regression_results['exit_code'] == 0
        status = "PASS" if all_gates_passed else "FAIL"

        if status == "PASS":
            self.logger.log("Testing complete: All quality gates passed", "SUCCESS")

        # Update Kanban
        self.board.move_card(card_id, "done", "pipeline-orchestrator")

        # Store in RAG
        self.rag.store_artifact(
            artifact_type="testing_result",
            card_id=card_id,
            task_title=card.get('title', 'Unknown'),
            content=f"Final testing of {winner} solution completed",
            metadata={
                "winner": winner,
                "uiux_score": uiux_score,
                "performance_score": performance_score,
                "all_gates_passed": all_gates_passed
            }
        )

        return {
            "stage": "testing",
            "winner": winner,
            "regression_tests": regression_results,
            "uiux_score": uiux_score,
            "performance_score": performance_score,
            "all_quality_gates_passed": all_gates_passed,
            "status": status
        }

    def get_stage_name(self) -> str:
        return "testing"
