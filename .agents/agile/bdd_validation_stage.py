#!/usr/bin/env python3
"""
BDD Scenario Validation Stage

Executes BDD scenarios using pytest-bdd to validate behavior.
Ensures implementation meets business requirements.

Integration Points:
- Runs after DevelopmentStage (or ValidationStage)
- Validates BDD scenarios pass
- Provides coverage metrics
"""

from typing import Dict, Optional
from pathlib import Path
import subprocess
import re

from artemis_stage_interface import PipelineStage, LoggerInterface
from supervised_agent_mixin import SupervisedStageMixin
from kanban_manager import KanbanBoard
from rag_agent import RAGAgent
from artemis_exceptions import PipelineStageError, wrap_exception


class BDDValidationStage(PipelineStage, SupervisedStageMixin):
    """
    Execute BDD scenarios and validate business behavior.

    Single Responsibility: Run pytest-bdd tests and report scenario coverage

    Integrates with supervisor for:
    - Test execution monitoring
    - Scenario validation tracking
    - Coverage reporting
    """

    def __init__(
        self,
        board: KanbanBoard,
        rag: RAGAgent,
        logger: LoggerInterface,
        observable: Optional['PipelineObservable'] = None,
        supervisor: Optional['SupervisorAgent'] = None
    ):
        PipelineStage.__init__(self)
        SupervisedStageMixin.__init__(
            self,
            supervisor=supervisor,
            stage_name="BDDValidationStage",
            heartbeat_interval=30
        )

        self.board = board
        self.rag = rag
        self.logger = logger
        self.observable = observable
        self.supervisor = supervisor

    def execute(self, card: Dict, context: Dict) -> Dict:
        """Execute with supervisor monitoring"""
        metadata = {
            "task_id": card.get('card_id'),
            "stage": "bdd_validation"
        }

        with self.supervised_execution(metadata):
            result = self._do_work(card, context)

        return result

    def _do_work(self, card: Dict, context: Dict) -> Dict:
        """Execute BDD scenarios and validate behavior"""
        self.logger.log("✅ Starting BDD Scenario Validation Stage", "STAGE")

        card_id = card.get('card_id', 'unknown')
        title = card.get('title', 'Unknown Task')

        # Update progress
        self.update_progress({"step": "starting", "progress_percent": 10})

        # Get winner's implementation directory
        winner = context.get('winner', 'developer-a')
        impl_dir = Path(f"/tmp/{winner}")

        # Check if BDD tests exist
        bdd_test_dir = impl_dir / "tests" / "bdd"
        feature_dir = impl_dir / "features"

        if not bdd_test_dir.exists() or not feature_dir.exists():
            self.logger.log("⚠️  No BDD tests or features found - skipping validation", "WARNING")
            return {
                "stage": "bdd_validation",
                "status": "SKIPPED",
                "reason": "No BDD tests or features available"
            }

        self.logger.log(f"🧪 Running BDD scenarios for: {title}", "INFO")

        # Update progress
        self.update_progress({"step": "running_scenarios", "progress_percent": 30})

        # Run pytest-bdd tests
        test_results = self._run_bdd_tests(impl_dir, bdd_test_dir)

        # Update progress
        self.update_progress({"step": "analyzing_results", "progress_percent": 70})

        # Analyze results
        validation_report = self._analyze_bdd_results(test_results)

        # Update progress
        self.update_progress({"step": "storing_results", "progress_percent": 90})

        # Store results in RAG
        self.rag.store_artifact(
            artifact_type="bdd_validation",
            card_id=card_id,
            task_title=title,
            content=validation_report,
            metadata={
                "scenarios_passed": test_results.get('passed', 0),
                "scenarios_failed": test_results.get('failed', 0),
                "scenario_pass_rate": validation_report.get('pass_rate', 0),
                "status": validation_report.get('status', 'UNKNOWN')
            }
        )

        # Update progress
        self.update_progress({"step": "complete", "progress_percent": 100})

        # Determine overall status
        status = validation_report.get('status', 'FAILED')
        pass_rate = validation_report.get('pass_rate', 0)

        if status == "PASS":
            self.logger.log(f"✅ All BDD scenarios passing ({pass_rate}% coverage)", "SUCCESS")
        else:
            failed_count = test_results.get('failed', 0)
            self.logger.log(f"❌ {failed_count} BDD scenarios failing ({pass_rate}% coverage)", "ERROR")

        return {
            "stage": "bdd_validation",
            "status": status,
            "scenarios_passed": test_results.get('passed', 0),
            "scenarios_failed": test_results.get('failed', 0),
            "pass_rate": pass_rate,
            "validation_report": validation_report,
            "test_output": test_results.get('output', '')
        }

    def _run_bdd_tests(self, impl_dir: Path, test_dir: Path) -> Dict:
        """Run pytest-bdd tests"""
        try:
            # Run pytest with BDD tests
            result = subprocess.run(
                [
                    "pytest",
                    str(test_dir),
                    "-v",
                    "--tb=short",
                    "--color=yes"
                ],
                cwd=str(impl_dir),
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for BDD tests
            )

            # Parse pytest output
            output = result.stdout + result.stderr

            # Count scenarios (Performance: Single-pass parsing O(n) vs O(3n))
            import re
            from collections import Counter
            pattern = re.compile(r' (PASSED|FAILED|SKIPPED)')
            matches = pattern.findall(output)
            counts = Counter(matches)

            passed = counts.get('PASSED', 0)
            failed = counts.get('FAILED', 0)
            skipped = counts.get('SKIPPED', 0)

            return {
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "exit_code": result.returncode,
                "output": output
            }

        except subprocess.TimeoutExpired:
            self.logger.log("⚠️  BDD tests timed out after 120 seconds", "WARNING")
            return {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "exit_code": 1,
                "error": "timeout",
                "output": ""
            }
        except Exception as e:
            self.logger.log(f"⚠️  Error running BDD tests: {e}", "WARNING")
            return {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "exit_code": 1,
                "error": str(e),
                "output": ""
            }

    def _analyze_bdd_results(self, test_results: Dict) -> Dict:
        """Analyze BDD test results and generate report"""
        passed = test_results.get('passed', 0)
        failed = test_results.get('failed', 0)
        skipped = test_results.get('skipped', 0)
        total = passed + failed + skipped

        if total == 0:
            pass_rate = 0
            status = "NO_TESTS"
        else:
            pass_rate = round((passed / total) * 100, 1)
            status = "PASS" if failed == 0 else "FAIL"

        # Extract failing scenario details from output
        output = test_results.get('output', '')
        failing_scenarios = self._extract_failing_scenarios(output)

        report = {
            "status": status,
            "total_scenarios": total,
            "scenarios_passed": passed,
            "scenarios_failed": failed,
            "scenarios_skipped": skipped,
            "pass_rate": pass_rate,
            "failing_scenarios": failing_scenarios,
            "summary": self._generate_summary(status, passed, failed, skipped, pass_rate)
        }

        return report

    def _extract_failing_scenarios(self, output: str) -> list:
        """Extract details about failing scenarios from pytest output"""
        failing_scenarios = []

        # Look for FAILED lines in pytest output
        # Format: tests/bdd/test_feature.py::test_scenario_name FAILED
        failed_pattern = re.compile(r'(tests/bdd/\S+)::(test_\w+)\s+FAILED')

        for match in failed_pattern.finditer(output):
            file_path, test_name = match.groups()
            # Convert test name to scenario name (remove test_ prefix, replace _ with space)
            scenario_name = test_name.replace('test_', '').replace('_', ' ').title()

            failing_scenarios.append({
                "file": file_path,
                "test": test_name,
                "scenario": scenario_name
            })

        return failing_scenarios

    def _generate_summary(
        self,
        status: str,
        passed: int,
        failed: int,
        skipped: int,
        pass_rate: float
    ) -> str:
        """Generate human-readable summary"""
        total = passed + failed + skipped

        if status == "NO_TESTS":
            return "No BDD scenarios found"
        elif status == "PASS":
            return f"All {total} BDD scenarios passing ({pass_rate}% coverage)"
        else:
            return f"{failed} of {total} BDD scenarios failing ({pass_rate}% coverage)"

    def get_stage_name(self) -> str:
        return "bdd_validation"
