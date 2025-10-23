#!/usr/bin/env python3
"""
Standalone Developer Agent - Uses LLM APIs to generate code

This replaces the Claude Code Task tool with direct LLM API calls,
making Artemis fully standalone and independent of Claude Code.

Single Responsibility: Execute developer prompts using LLM APIs
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from llm_client import create_llm_client, LLMMessage, LLMResponse
from artemis_stage_interface import LoggerInterface
from artemis_exceptions import (
    LLMClientError,
    LLMResponseParsingError,
    DeveloperExecutionError,
    RAGQueryError,
    FileReadError,
    wrap_exception
)


class StandaloneDeveloperAgent:
    """
    Standalone developer agent that uses LLM APIs

    Single Responsibility: Execute TDD workflow using LLM API calls
    """

    def __init__(
        self,
        developer_name: str,
        developer_type: str,
        llm_provider: str = "openai",
        llm_model: Optional[str] = None,
        logger: Optional[LoggerInterface] = None
    ):
        """
        Initialize standalone developer agent

        Args:
            developer_name: "developer-a" or "developer-b"
            developer_type: "conservative" or "aggressive"
            llm_provider: "openai" or "anthropic"
            llm_model: Specific model (optional, uses default)
            logger: Logger implementation
        """
        self.developer_name = developer_name
        self.developer_type = developer_type
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.logger = logger

        # Create LLM client
        try:
            self.llm_client = create_llm_client(llm_provider)
            if self.logger:
                self.logger.log(f"✅ {developer_name} initialized with {llm_provider}", "INFO")
        except Exception as e:
            if self.logger:
                self.logger.log(f"❌ Failed to initialize LLM client: {e}", "ERROR")
            raise wrap_exception(
                e,
                LLMClientError,
                f"Failed to initialize LLM client for {developer_name}",
                {"developer_name": developer_name, "llm_provider": llm_provider}
            )

    def execute(
        self,
        task_title: str,
        task_description: str,
        adr_content: str,
        adr_file: str,
        output_dir: Path,
        developer_prompt_file: str,
        card_id: str = "",
        rag_agent = None
    ) -> Dict:
        """
        Execute the full TDD workflow using LLM API

        Args:
            task_title: Title of task
            task_description: Task description
            adr_content: ADR content
            adr_file: Path to ADR file
            output_dir: Output directory for implementation
            developer_prompt_file: Path to developer prompt file
            card_id: Card ID for querying RAG feedback (optional)
            rag_agent: RAG Agent for querying feedback (optional)

        Returns:
            Dict with implementation results
        """
        if self.logger:
            self.logger.log(f"🚀 {self.developer_name} starting implementation...", "INFO")

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Read developer prompt
        developer_prompt = self._read_developer_prompt(developer_prompt_file)

        # Query RAG for code review feedback (if available)
        code_review_feedback = None
        if rag_agent and card_id:
            code_review_feedback = self._query_code_review_feedback(rag_agent, card_id)

        # Read example HTML slides if task involves creating slides
        # Extract example file path from ADR content (if specified)
        example_slides = None
        if "slide" in task_description.lower() or "html" in task_description.lower():
            example_slides = self._load_example_slides(adr_content)

        # Build full prompt
        full_prompt = self._build_execution_prompt(
            developer_prompt=developer_prompt,
            task_title=task_title,
            task_description=task_description,
            adr_content=adr_content,
            output_dir=output_dir,
            code_review_feedback=code_review_feedback,
            example_slides=example_slides
        )

        # Call LLM to generate implementation
        try:
            response = self._call_llm(full_prompt)

            # Parse implementation from response
            implementation = self._parse_implementation(response.content)

            # Write implementation files
            files_written = self._write_implementation_files(implementation, output_dir)

            # Generate solution report
            solution_report = self._generate_solution_report(
                implementation=implementation,
                files_written=files_written,
                llm_response=response
            )

            # Write solution report
            report_path = output_dir / "solution_report.json"
            with open(report_path, 'w') as f:
                json.dump(solution_report, f, indent=2)

            if self.logger:
                self.logger.log(f"✅ {self.developer_name} completed implementation", "SUCCESS")

            return solution_report

        except Exception as e:
            if self.logger:
                self.logger.log(f"❌ {self.developer_name} failed: {e}", "ERROR")
            raise wrap_exception(
                e,
                DeveloperExecutionError,
                f"Developer {self.developer_name} execution failed",
                {
                    "developer_name": self.developer_name,
                    "developer_type": self.developer_type,
                    "task_title": task_title,
                    "card_id": card_id
                }
            )

    def _query_code_review_feedback(self, rag_agent, card_id: str) -> Optional[str]:
        """
        Query RAG for code review feedback from previous attempts

        This implements the proper DAO pattern:
        - Developer queries RAG Agent (not ChromaDB directly)
        - RAG Agent handles all database operations
        - Returns formatted feedback for LLM prompt

        Args:
            rag_agent: RAG Agent instance
            card_id: Card ID to query feedback for

        Returns:
            Formatted feedback string or None
        """
        try:
            if self.logger:
                self.logger.log(f"🔍 Querying RAG for code review feedback (card: {card_id})...", "INFO")

            # Query RAG for code review artifacts
            query_text = f"code review feedback for {card_id}"
            results = rag_agent.query_similar(
                query_text=query_text,
                artifact_type="code_review",
                top_k=3  # Get up to 3 most recent feedback items
            )

            if not results or len(results) == 0:
                if self.logger:
                    self.logger.log("No code review feedback found in RAG", "INFO")
                return None

            # Format feedback for LLM prompt
            feedback_lines = ["# PREVIOUS CODE REVIEW FEEDBACK\n"]
            feedback_lines.append("The following issues were found in previous implementation attempt(s):\n")

            for i, result in enumerate(results, 1):
                content = result.get('content', '')
                metadata = result.get('metadata', {})
                score = result.get('score', 0)

                feedback_lines.append(f"\n## Feedback #{i} (Attempt {metadata.get('retry_count', 'N/A')})")
                feedback_lines.append(f"Score: {metadata.get('code_review_score', 'N/A')}")
                feedback_lines.append(f"Status: {metadata.get('status', 'FAILED')}")
                feedback_lines.append(f"\n{content}\n")

            feedback_text = "\n".join(feedback_lines)

            if self.logger:
                self.logger.log(f"✅ Found {len(results)} feedback item(s) from RAG", "INFO")

            return feedback_text

        except Exception as e:
            if self.logger:
                self.logger.log(f"⚠️  Error querying RAG for feedback: {e}", "WARNING")
            # Don't raise, just log and return None - feedback is optional
            # But wrap the exception for proper context tracking
            wrapped_exception = wrap_exception(
                e,
                RAGQueryError,
                f"Failed to query RAG for code review feedback",
                {"card_id": card_id, "developer_name": self.developer_name}
            )
            if self.logger:
                self.logger.log(f"Details: {wrapped_exception}", "DEBUG")
            return None

    def _load_example_slides(self, adr_content: str) -> Optional[str]:
        """
        Load example HTML slide presentations to use as reference

        Extracts the example file path from the ADR content (specified by Project Analysis Agent).
        The ADR should contain a reference like "Example: /path/to/example.html" or similar.

        Args:
            adr_content: ADR content to parse for example file path

        Returns:
            Formatted example slides content or None
        """
        try:
            # Extract example file path from ADR
            # Look for patterns like "Example:", "Reference:", "Template:", etc.
            import re
            example_patterns = [
                r'Example:\s*([/\w.-]+\.html)',
                r'Reference:\s*([/\w.-]+\.html)',
                r'Template:\s*([/\w.-]+\.html)',
                r'example file:\s*([/\w.-]+\.html)',
                r'reference file:\s*([/\w.-]+\.html)',
            ]

            example_file_path = None
            for pattern in example_patterns:
                match = re.search(pattern, adr_content, re.IGNORECASE)
                if match:
                    example_file_path = match.group(1)
                    break

            if not example_file_path:
                if self.logger:
                    self.logger.log("No example file specified in ADR", "INFO")
                return None

            example_file = Path(example_file_path)

            if not example_file.exists():
                if self.logger:
                    self.logger.log(f"⚠️  Example file not found: {example_file}", "WARNING")
                return None

            # Read first 500 lines of example (enough to show structure/styling)
            with open(example_file, 'r') as f:
                lines = f.readlines()[:500]
                example_content = ''.join(lines)

            example_text = f"""
# REFERENCE EXAMPLE: High-Quality HTML Slide Presentation

Below is a COMPLETE example of a professional HTML slide presentation that meets our quality standards.
Study this example carefully - your implementation should match this level of quality and completeness.

Example source: {example_file}

Key features to replicate:
- Complete HTML structure with embedded CSS and JavaScript
- Glassmorphism styling (backdrop-filter, transparency)
- Smooth slide transitions with animations
- Navigation controls (Previous/Next buttons)
- Keyboard navigation support (arrow keys, space)
- Auto-advance functionality (8 seconds per slide)
- Slide counter (e.g., "1/7")
- Responsive design
- Professional gradient backgrounds
- Multiple complete slides (not just 1!)

```html
{example_content}
... (truncated for brevity, but your implementation should be COMPLETE)
```

**CRITICAL**: Your implementation must be COMPLETE like this example, not a partial prototype!
"""

            if self.logger:
                self.logger.log(f"✅ Loaded example slides from: {example_file}", "INFO")

            return example_text

        except Exception as e:
            if self.logger:
                self.logger.log(f"⚠️  Error loading example slides: {e}", "WARNING")
            # Don't raise, just log and return None - example slides are optional
            # But wrap the exception for proper context tracking
            wrapped_exception = wrap_exception(
                e,
                FileReadError,
                f"Failed to load example slides from ADR",
                {"developer_name": self.developer_name, "adr_length": len(adr_content)}
            )
            if self.logger:
                self.logger.log(f"Details: {wrapped_exception}", "DEBUG")
            return None

    def _read_developer_prompt(self, prompt_file: str) -> str:
        """Read developer prompt from file"""
        try:
            with open(prompt_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            if self.logger:
                self.logger.log(f"⚠️  Prompt file not found: {prompt_file}, using default", "WARNING")
            return self._get_default_developer_prompt()

    def _get_default_developer_prompt(self) -> str:
        """Get default developer prompt if file not found"""
        return f"""You are {self.developer_name.upper()} - a {self.developer_type} software developer.

Your approach:
- {"Conservative: Use proven patterns, prioritize stability" if self.developer_type == "conservative" else "Aggressive: Use modern patterns, prioritize innovation"}
- Follow TDD workflow strictly (RED → GREEN → REFACTOR)
- Write comprehensive tests BEFORE implementation
- Apply SOLID principles throughout
- Provide clear documentation
"""

    def _build_execution_prompt(
        self,
        developer_prompt: str,
        task_title: str,
        task_description: str,
        adr_content: str,
        output_dir: Path,
        code_review_feedback: Optional[str] = None,
        example_slides: Optional[str] = None
    ) -> str:
        """
        Build complete execution prompt for LLM

        Includes:
        - Developer-specific prompt
        - Task details
        - ADR architectural guidance
        - Code review feedback from previous attempts (if retry)
        - Example code/slides (if specified in ADR)
        """
        # Start with developer-specific prompt
        prompt_parts = [developer_prompt]

        # Add code review feedback prominently at the top if this is a retry
        if code_review_feedback:
            prompt_parts.append("\n" + "="*80)
            prompt_parts.append(code_review_feedback)
            prompt_parts.append("="*80)
            prompt_parts.append("\n**CRITICAL**: Address ALL issues above in your implementation!\n")

        # Add task details
        prompt_parts.append(f"""
# TASK TO IMPLEMENT

**Title**: {task_title}

**Description**: {task_description}

# ARCHITECTURAL DECISION RECORD (ADR)

{adr_content}
""")

        # Add example slides if provided
        if example_slides:
            prompt_parts.append("\n" + "="*80)
            prompt_parts.append(example_slides)
            prompt_parts.append("="*80 + "\n")

        # Add instructions
        prompt_parts.append("""
# INSTRUCTIONS

Implement this task following Test-Driven Development (TDD) methodology:

## Phase 1: RED (Write Failing Tests)
1. Create test files FIRST
2. Write tests that capture all requirements
3. Tests should FAIL initially (feature not implemented)

## Phase 2: GREEN (Implement Minimum Code)
1. Write implementation to make tests pass
2. Use MINIMUM code necessary
3. Focus on functionality first

## Phase 3: REFACTOR (Improve Quality)
1. Refactor for SOLID principles
2. Add documentation and type hints
3. Ensure tests still pass

# OUTPUT FORMAT

Provide your implementation in the following JSON format:

```json
{{
  "implementation_files": [
    {{
      "path": "relative/path/to/file.py",
      "content": "# Full file content here...",
      "description": "Brief description of this file"
    }}
  ],
  "test_files": [
    {{
      "path": "tests/unit/test_feature.py",
      "content": "# Full test file content...",
      "description": "Unit tests for feature"
    }}
  ],
  "tdd_workflow": {{
    "red_phase_notes": "Description of tests written first",
    "green_phase_notes": "Description of implementation",
    "refactor_phase_notes": "Description of refactorings applied"
  }},
  "solid_principles_applied": [
    "Single Responsibility: Explanation...",
    "Open/Closed: Explanation...",
    "Liskov Substitution: Explanation...",
    "Interface Segregation: Explanation...",
    "Dependency Inversion: Explanation..."
  ],
  "approach_summary": "Summary of your {self.developer_type} approach"
}}
```

**IMPORTANT**:
- Provide COMPLETE, working code (not pseudocode)
- Include ALL necessary imports
- Follow Python best practices
- Apply SOLID principles rigorously
- Your code will be executed and tested

Begin implementation now:
""")

        # Join all parts into final prompt
        return "\n".join(prompt_parts)

    def _call_llm(self, prompt: str) -> LLMResponse:
        """Call LLM API with prompt"""
        messages = [
            LLMMessage(
                role="system",
                content=f"You are {self.developer_name}, a {self.developer_type} software developer. You follow TDD strictly and apply SOLID principles. You write production-quality, complete code. You MUST respond with valid JSON only - no explanations, no markdown, just pure JSON."
            ),
            LLMMessage(
                role="user",
                content=prompt
            )
        ]

        if self.logger:
            self.logger.log(f"📡 Calling {self.llm_provider} API...", "INFO")

        # Enable JSON mode for OpenAI (Anthropic uses prompt engineering)
        response_format = None
        if self.llm_provider == "openai":
            response_format = {"type": "json_object"}

        response = self.llm_client.complete(
            messages=messages,
            model=self.llm_model,
            temperature=0.7,
            max_tokens=8000,  # Allow longer responses for complete implementations
            response_format=response_format
        )

        if self.logger:
            self.logger.log(
                f"✅ Received response ({response.usage['total_tokens']} tokens)",
                "INFO"
            )

        return response

    def _parse_implementation(self, content: str) -> Dict:
        """
        Parse implementation from LLM response

        Extracts JSON from response (handles markdown code blocks)
        """
        # Try to find JSON in markdown code block
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            json_str = content[json_start:json_end].strip()
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.find("```", json_start)
            json_str = content[json_start:json_end].strip()
        else:
            # Assume entire content is JSON
            json_str = content.strip()

        try:
            implementation = json.loads(json_str)
            return implementation
        except json.JSONDecodeError as e:
            if self.logger:
                self.logger.log(f"❌ Failed to parse JSON: {e}", "ERROR")
                self.logger.log(f"Raw content:\n{content[:500]}...", "DEBUG")
            raise wrap_exception(
                e,
                LLMResponseParsingError,
                f"Failed to parse implementation JSON from LLM response",
                context={"developer": self.developer_name, "error": str(e)}
            )

    def _write_implementation_files(
        self,
        implementation: Dict,
        output_dir: Path
    ) -> List[str]:
        """Write implementation and test files to disk"""
        files_written = []

        # Write implementation files
        for file_info in implementation.get("implementation_files", []):
            file_path = output_dir / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w') as f:
                f.write(file_info["content"])

            files_written.append(str(file_path))

            if self.logger:
                self.logger.log(f"  ✅ Wrote: {file_path}", "INFO")

        # Write test files
        for file_info in implementation.get("test_files", []):
            file_path = output_dir / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w') as f:
                f.write(file_info["content"])

            files_written.append(str(file_path))

            if self.logger:
                self.logger.log(f"  ✅ Wrote: {file_path}", "INFO")

        return files_written

    def _generate_solution_report(
        self,
        implementation: Dict,
        files_written: List[str],
        llm_response: LLMResponse
    ) -> Dict:
        """Generate solution report"""
        return {
            "developer": self.developer_name,
            "approach": self.developer_type,
            "status": "COMPLETED",
            "timestamp": datetime.now().isoformat(),
            "llm_provider": self.llm_provider,
            "llm_model": llm_response.model,
            "tokens_used": llm_response.usage,
            "implementation_files": [
                f["path"] for f in implementation.get("implementation_files", [])
            ],
            "test_files": [
                f["path"] for f in implementation.get("test_files", [])
            ],
            "files_written": files_written,
            "tdd_workflow": implementation.get("tdd_workflow", {}),
            "solid_principles_applied": implementation.get("solid_principles_applied", []),
            "approach_summary": implementation.get("approach_summary", ""),
            "full_implementation": implementation
        }


# ============================================================================
# MAIN - TESTING
# ============================================================================

if __name__ == "__main__":
    """Test standalone developer agent"""
    from artemis_services import PipelineLogger

    # Test with a simple task
    logger = PipelineLogger(verbose=True)

    agent = StandaloneDeveloperAgent(
        developer_name="developer-a",
        developer_type="conservative",
        llm_provider="openai",
        logger=logger
    )

    output_dir = Path("/tmp/test_developer_output")

    result = agent.execute(
        task_title="Create a simple calculator",
        task_description="Create a Python calculator with add, subtract, multiply, divide operations",
        adr_content="Use simple functions, apply SRP, include error handling",
        adr_file="/tmp/adr/test.md",
        output_dir=output_dir,
        developer_prompt_file="nonexistent.md"  # Will use default
    )

    print(f"\n✅ Implementation completed!")
    print(f"Files written: {len(result['files_written'])}")
    print(f"Tokens used: {result['tokens_used']['total_tokens']}")
