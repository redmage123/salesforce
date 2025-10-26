#!/usr/bin/env python3
"""
Code Review Agent - Comprehensive Security & Quality Analysis

Performs automated code review checking for:
- Code quality and anti-patterns
- Security vulnerabilities (OWASP Top 10)
- GDPR compliance
- Accessibility (WCAG 2.1 AA)

Uses LLM APIs (OpenAI/Anthropic) for intelligent code analysis.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_client import create_llm_client, LLMMessage
from artemis_exceptions import (
    CodeReviewExecutionError,
    FileReadError,
    LLMAPIError,
    LLMResponseParsingError,
    FileWriteError,
    wrap_exception
)
from review_request_builder import (
    ReviewRequestBuilder,
    ImplementationFile,
    read_implementation_files,
    create_review_request
)
from environment_context import get_environment_context_short

# Import PromptManager for RAG-based prompts
try:
    from prompt_manager import PromptManager
    from rag_agent import RAGAgent
    PROMPT_MANAGER_AVAILABLE = True
except ImportError:
    PROMPT_MANAGER_AVAILABLE = False

# Import centralized AI Query Service
from ai_query_service import (
    AIQueryService,
    create_ai_query_service,
    QueryType,
    AIQueryResult
)


class CodeReviewAgent:
    """
    Autonomous code review agent that analyzes implementations for quality,
    security, GDPR compliance, and accessibility.
    """

    def __init__(
        self,
        developer_name: str,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        rag_agent: Optional[Any] = None,
        ai_service: Optional[AIQueryService] = None
    ):
        """
        Initialize the code review agent.

        Args:
            developer_name: Name of the developer whose code to review (e.g., "developer-a")
            llm_provider: LLM provider ("openai" or "anthropic")
            llm_model: Specific model to use (optional)
            logger: Logger instance (optional)
            rag_agent: RAG agent for prompt management (optional)
            ai_service: Centralized AI Query Service (optional)
        """
        self.developer_name = developer_name
        self.llm_provider = llm_provider or os.getenv("ARTEMIS_LLM_PROVIDER", "openai")
        self.llm_model = llm_model or os.getenv("ARTEMIS_LLM_MODEL")
        self.logger = logger or self._setup_logger()

        # Initialize LLM client
        self.llm_client = create_llm_client(
            provider=self.llm_provider
        )

        # Initialize PromptManager if RAG is available
        self.prompt_manager = None
        if PROMPT_MANAGER_AVAILABLE and rag_agent:
            try:
                self.prompt_manager = PromptManager(rag_agent, verbose=False)
                self.logger.info("✅ Prompt manager initialized (RAG-based prompts)")
            except Exception as e:
                self.logger.warning(f"⚠️  Could not initialize PromptManager: {e}")

        # Initialize centralized AI Query Service
        try:
            if ai_service:
                self.ai_service = ai_service
                self.logger.info("✅ Using provided AI Query Service")
            else:
                self.ai_service = create_ai_query_service(
                    llm_client=self.llm_client,
                    rag=rag_agent,
                    logger=self.logger,
                    verbose=False
                )
                self.logger.info("✅ AI Query Service initialized (KG→RAG→LLM)")
        except Exception as e:
            self.logger.warning(f"⚠️  Could not initialize AI Query Service: {e}")
            self.ai_service = None

        self.logger.info(f"🔍 Code Review Agent initialized for {developer_name}")
        self.logger.info(f"   LLM Provider: {self.llm_provider}")
        if self.llm_model:
            self.logger.info(f"   Model: {self.llm_model}")
        else:
            self.logger.info(f"   Model: default for {self.llm_provider}")

    def _setup_logger(self) -> logging.Logger:
        """Setup default logger."""
        logger = logging.getLogger(f"CodeReviewAgent-{self.developer_name}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def review_implementation(
        self,
        implementation_dir: str,
        task_title: str,
        task_description: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Perform comprehensive code review using AIQueryService (KG→RAG→LLM pipeline).

        Uses centralized AIQueryService to automatically query Knowledge Graph
        for similar code reviews, get RAG recommendations, and call LLM with
        enhanced context, reducing token usage by 30-40%.

        Args:
            implementation_dir: Directory containing implementation files
            task_title: Title of the task
            task_description: Description of what was implemented
            output_dir: Directory to write review report

        Returns:
            Dictionary with review results
        """
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"🔍 Starting Code Review for {self.developer_name}")
        self.logger.info(f"{'='*80}")

        try:
            # Prepare review context
            review_context = self._prepare_review_context(
                implementation_dir, task_title, task_description
            )

            # Execute review using AI service or fallback
            review_response_data = self._execute_review_analysis(review_context)

            # Process and finalize review
            return self._finalize_review_results(
                review_response_data, task_title, output_dir
            )

        except CodeReviewExecutionError:
            raise
        except Exception as e:
            raise wrap_exception(
                e,
                CodeReviewExecutionError,
                f"Code review execution failed for {self.developer_name}",
                {
                    "developer_name": self.developer_name,
                    "implementation_dir": implementation_dir,
                    "task_title": task_title
                }
            )

    def _extract_file_types(self, implementation_files: List[ImplementationFile]) -> List[str]:
        """Extract file types for KG query"""
        # Map file extensions to language types
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'javascript',
            '.tsx': 'javascript',
            '.java': 'java',
            '.go': 'go'
        }

        # Use set comprehension to extract unique file types
        file_types = {
            extension_map[ext]
            for file in implementation_files
            for ext in extension_map
            if file.path.endswith(ext)
        }

        return list(file_types)

    def _build_base_review_prompt(
        self,
        review_prompt: str,
        implementation_files: List[ImplementationFile],
        task_title: str,
        task_description: str
    ) -> str:
        """Build base review prompt without KG context (AIQueryService will add it)"""
        files_content = "\n\n".join(
            f"## File: {file.path}\n```{file.language}\n{file.content}\n```"
            for file in implementation_files
        )

        return f"""{review_prompt}

**Task**: {task_title}
**Description**: {task_description}

{get_environment_context_short()}

**Implementation Files**:
{files_content}

Perform a comprehensive code review and return results in JSON format."""

    def _build_review_request_legacy(self, prompt: str) -> List[LLMMessage]:
        """Legacy review request builder for fallback"""
        return [
            LLMMessage(role="system", content="You are an expert code reviewer."),
            LLMMessage(role="user", content=prompt)
        ]

    def _prepare_review_context(self, implementation_dir, task_title, task_description):
        """
        Prepare all context needed for code review

        Returns:
            Dict with implementation files, prompts, and base prompt
        """
        # Step 1: Read implementation files
        implementation_files = self._read_implementation_files(implementation_dir)
        if not implementation_files:
            raise CodeReviewExecutionError(
                "No implementation files found",
                context={"implementation_dir": implementation_dir}
            )

        self.logger.info(f"📁 Read {len(implementation_files)} implementation files")

        # Step 2: Read code review prompt
        review_prompt = self._read_review_prompt()

        # Step 3: Build base review prompt
        base_prompt = self._build_base_review_prompt(
            review_prompt=review_prompt,
            implementation_files=implementation_files,
            task_title=task_title,
            task_description=task_description
        )

        return {
            'implementation_files': implementation_files,
            'review_prompt': review_prompt,
            'base_prompt': base_prompt
        }

    def _execute_review_analysis(self, review_context):
        """
        Execute code review analysis using AI service or fallback

        Returns:
            Dict with review_content, tokens_used, and model_used
        """
        if self.ai_service:
            return self._execute_review_with_ai_service(review_context)
        else:
            return self._execute_review_legacy(review_context)

    def _execute_review_with_ai_service(self, review_context):
        """Execute review using AI Query Service (KG→RAG→LLM pipeline)"""
        self.logger.info("🔄 Using AI Query Service for KG→RAG→LLM pipeline")

        # Extract file types for KG query
        file_types = self._extract_file_types(review_context['implementation_files'])

        result = self.ai_service.query(
            query_type=QueryType.CODE_REVIEW,
            prompt=review_context['base_prompt'],
            kg_query_params={'file_types': file_types},
            temperature=0.2,
            max_tokens=4000
        )

        if not result.success:
            raise CodeReviewExecutionError(
                f"AI Query Service failed: {result.error}",
                context={"developer_name": self.developer_name}
            )

        # Log token savings
        if result.kg_context and result.kg_context.pattern_count > 0:
            self.logger.info(
                f"📊 KG found {result.kg_context.pattern_count} review patterns, "
                f"saved ~{result.llm_response.tokens_saved} tokens"
            )

        return {
            'review_content': result.llm_response.content,
            'tokens_used': result.llm_response.tokens_used,
            'model_used': result.llm_response.model
        }

    def _execute_review_legacy(self, review_context):
        """Execute review using direct LLM call (fallback)"""
        self.logger.warning("⚠️  AI Query Service unavailable - using direct LLM call")

        review_request = self._build_review_request_legacy(review_context['base_prompt'])
        review_response = self._call_llm_for_review(review_request)

        return {
            'review_content': review_response.content,
            'tokens_used': review_response.usage,
            'model_used': review_response.model
        }

    def _finalize_review_results(self, review_response_data, task_title, output_dir):
        """
        Parse review response, add metadata, write report, and return results

        Returns:
            Dict with review results for the stage
        """
        # Parse review JSON
        review_data = self._parse_review_response(review_response_data['review_content'])

        # Add metadata
        review_data['metadata'] = {
            'developer_name': self.developer_name,
            'task_title': task_title,
            'reviewed_at': datetime.now().isoformat(),
            'llm_provider': self.llm_provider,
            'llm_model': review_response_data['model_used'],
            'tokens_used': review_response_data['tokens_used']
        }

        # Write review report
        report_file = self._write_review_report(review_data, output_dir)

        # Return results
        return {
            'status': 'COMPLETED',
            'developer_name': self.developer_name,
            'review_status': review_data['review_summary']['overall_status'],
            'total_issues': review_data['review_summary']['total_issues'],
            'critical_issues': review_data['review_summary']['critical_issues'],
            'high_issues': review_data['review_summary']['high_issues'],
            'overall_score': review_data['review_summary']['score']['overall'],
            'report_file': report_file,
            'tokens_used': review_response_data['tokens_used']
        }

    def _read_implementation_files(self, implementation_dir: str) -> List[ImplementationFile]:
        """
        Read all implementation files from directory using Builder pattern

        Returns:
            List of ImplementationFile value objects
        """
        try:
            files = read_implementation_files(implementation_dir)

            # Log file details
            for file in files:
                self.logger.debug(f"  Read {file.path} ({file.lines} lines)")

            return files
        except FileNotFoundError:
            self.logger.warning(f"Implementation directory not found: {implementation_dir}")
            return []
        except Exception as e:
            raise wrap_exception(
                e,
                FileReadError,
                "Failed to read implementation files",
                {
                    "implementation_dir": implementation_dir,
                    "developer_name": self.developer_name
                }
            )

    def _read_review_prompt(self) -> str:
        """Read the code review agent prompt from RAG or fallback to file."""
        # Try to get prompt from RAG first
        if self.prompt_manager:
            try:
                self.logger.info("📝 Loading code review prompt from RAG")
                prompt_template = self.prompt_manager.get_prompt("code_review_analysis")

                if prompt_template:
                    # Render the prompt (no variables needed for system message)
                    rendered = self.prompt_manager.render_prompt(
                        prompt=prompt_template,
                        variables={}
                    )
                    self.logger.info(f"✅ Loaded RAG prompt with {len(prompt_template.perspectives)} perspectives")
                    # Return combined system and user template
                    return f"{rendered['system']}\n\n{rendered['user']}"
            except Exception as e:
                self.logger.warning(f"⚠️  Error loading RAG prompt: {e} - falling back to file")

        # Fallback to reading from file
        prompt_file = Path(__file__).parent / "prompts" / "code_review_agent_prompt.md"

        if not prompt_file.exists():
            raise FileReadError(
                f"Code review prompt not found: {prompt_file}",
                context={"prompt_file": str(prompt_file)}
            )

        try:
            self.logger.info("📝 Loading code review prompt from file (fallback)")
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise wrap_exception(
                e,
                FileReadError,
                f"Failed to read code review prompt",
                context={"prompt_file": str(prompt_file)}
            )

    def _build_review_request(
        self,
        review_prompt: str,
        implementation_files: List[ImplementationFile],
        task_title: str,
        task_description: str,
        kg_context: Optional[Dict] = None
    ) -> List[LLMMessage]:
        """
        Build the complete review request for the LLM using Builder pattern

        Uses ReviewRequestBuilder for fluent interface and validation.
        Enhanced with KG context to reduce LLM workload.

        Args:
            review_prompt: System prompt for code review
            implementation_files: List of ImplementationFile value objects
            task_title: Task title
            task_description: Task description
            kg_context: Optional KG context with known issue patterns

        Returns:
            List of LLMMessage instances
        """
        # Use Builder pattern for clean, fluent construction
        builder = ReviewRequestBuilder()

        messages = (builder
            .set_developer(self.developer_name)
            .set_task(task_title, task_description)
            .add_files(implementation_files)
            .set_review_prompt(review_prompt)
            .build())

        # Enhance with KG context if available
        if kg_context and kg_context.get('common_issues'):
            kg_hints = "\n\n**Knowledge Graph Context - Known Issue Patterns:**\n"
            kg_hints += f"Based on {kg_context['similar_reviews_count']} similar reviews, focus on:\n"
            for issue in kg_context['common_issues'][:5]:
                kg_hints += f"- {issue['category']}: {issue['pattern']}\n"
            kg_hints += "\nPrioritize these patterns in your review.\n"

            # Append KG hints to user message
            if messages and len(messages) > 1:
                messages[-1] = LLMMessage(
                    role="user",
                    content=messages[-1].content + kg_hints
                )

        # Log construction details
        self.logger.debug(f"Built review request:")
        self.logger.debug(f"  Files: {builder.get_file_count()}")
        self.logger.debug(f"  Total lines: {builder.get_total_lines()}")
        if kg_context:
            self.logger.debug(f"  KG patterns: {len(kg_context.get('common_issues', []))}")

        return messages

    def _call_llm_for_review(self, messages: List[LLMMessage]):
        """Call LLM API to perform code review."""
        try:
            # Prepare kwargs for LLM call
            kwargs = {
                "messages": messages,
                "temperature": 0.3,  # Lower temperature for more consistent analysis
                "max_tokens": 4000  # Large enough for detailed review
            }

            # Only pass model if explicitly specified
            if self.llm_model:
                kwargs["model"] = self.llm_model

            response = self.llm_client.complete(**kwargs)

            self.logger.info(f"✅ LLM review completed")
            self.logger.info(f"   Tokens used: {response.usage.get('total_tokens', 'unknown')}")

            return response

        except Exception as e:
            raise wrap_exception(
                e,
                LLMAPIError,
                "LLM API call failed during code review",
                {
                    "developer_name": self.developer_name,
                    "llm_provider": self.llm_provider,
                    "llm_model": self.llm_model
                }
            )

    def _parse_review_response(self, response_content: str) -> Dict[str, Any]:
        """Parse the LLM's review response (JSON format)."""
        try:
            # Try to extract JSON from markdown code blocks if present
            content = response_content.strip()

            # Check if content contains markdown code blocks (```json or ```)
            # The LLM might add descriptive text before/after the code block
            import re

            # Try to extract JSON from ```json code block
            json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1).strip()
            else:
                # Try to extract from generic ``` code block
                code_match = re.search(r'```\s*\n(.*?)\n```', content, re.DOTALL)
                if code_match:
                    content = code_match.group(1).strip()
                else:
                    # No code blocks found - try as-is
                    # But still remove leading/trailing code block markers if present
                    if content.startswith('```json'):
                        content = content[7:]
                    elif content.startswith('```'):
                        content = content[3:]

                    if content.endswith('```'):
                        content = content[:-3]

                    content = content.strip()

            # Parse JSON
            review_data = json.loads(content)

            # Normalize the schema - convert category-based format to expected format
            # The LLM might return different schemas depending on the prompt version
            if 'review_summary' not in review_data:
                # New format - normalize to old format
                review_data = self._normalize_review_schema(review_data)

            self.logger.info("✅ Review response parsed successfully")

            # Extract summary info for logging
            summary = review_data.get('review_summary', {})
            if isinstance(summary, dict):
                self.logger.info(f"   Total issues: {summary.get('total_issues', 0)}")
                self.logger.info(f"   Critical: {summary.get('critical_issues', 0)}")
                self.logger.info(f"   Overall status: {summary.get('overall_status', 'UNKNOWN')}")

            return review_data

        except json.JSONDecodeError as e:
            raise wrap_exception(
                e,
                LLMResponseParsingError,
                "Failed to parse LLM review response as JSON",
                {
                    "developer_name": self.developer_name,
                    "response_preview": response_content[:200]
                }
            )
        except Exception as e:
            raise wrap_exception(
                e,
                LLMResponseParsingError,
                "Failed to process LLM review response",
                {
                    "developer_name": self.developer_name
                }
            )

    def _normalize_review_schema(self, category_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize category-based schema to expected review_summary/issues format.

        Args:
            category_data: Dict with category keys (security, solid_principles, etc.)

        Returns:
            Normalized dict with review_summary and issues keys
        """
        # Collect all issues from all categories
        all_issues = []
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0

        for category, data in category_data.items():
            if not isinstance(data, dict):
                continue

            # Extract issues from this category
            category_issues = data.get('issues', [])
            if isinstance(category_issues, list):
                for issue in category_issues:
                    if isinstance(issue, dict):
                        # Add category to issue if not present
                        if 'category' not in issue:
                            issue['category'] = category

                        # Count by severity
                        severity = issue.get('severity', 'low').lower()
                        if severity == 'critical':
                            critical_count += 1
                        elif severity == 'high':
                            high_count += 1
                        elif severity == 'medium':
                            medium_count += 1
                        else:
                            low_count += 1

                        all_issues.append(issue)

        # Calculate scores (default to 100 if no issues)
        total_issues = len(all_issues)
        overall_score = max(0, 100 - (critical_count * 20 + high_count * 10 + medium_count * 5 + low_count * 2))

        # Determine overall status
        if critical_count > 0:
            overall_status = "REJECTED"
        elif high_count > 3:
            overall_status = "NEEDS_IMPROVEMENT"
        elif total_issues == 0:
            overall_status = "APPROVED"
        else:
            overall_status = "CONDITIONAL_APPROVAL"

        # Build normalized structure
        return {
            'review_summary': {
                'overall_status': overall_status,
                'total_issues': total_issues,
                'critical_issues': critical_count,
                'high_issues': high_count,
                'medium_issues': medium_count,
                'low_issues': low_count,
                'score': {
                    'overall': overall_score,
                    'code_quality': 100,  # Default scores
                    'security': 100,
                    'gdpr_compliance': 100,
                    'accessibility': 100
                }
            },
            'issues': all_issues,
            'categories': category_data  # Preserve original category data
        }

    def _write_review_report(self, review_data: Dict[str, Any], output_dir: str) -> str:
        """Write the review report to a JSON file."""
        os.makedirs(output_dir, exist_ok=True)

        report_file = os.path.join(output_dir, f"code_review_{self.developer_name}.json")

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(review_data, f, indent=2)

        self.logger.info(f"📄 Review report written to: {report_file}")

        # Also write a human-readable summary
        summary_file = os.path.join(output_dir, f"code_review_{self.developer_name}_summary.md")
        self._write_review_summary(review_data, summary_file)

        return report_file

    def _write_review_summary(self, review_data: Dict[str, Any], summary_file: str):
        """Write a human-readable markdown summary."""
        summary = review_data['review_summary']
        issues = review_data['issues']

        md_content = f"""# Code Review Summary - {self.developer_name}

## Overall Assessment

**Status:** {summary['overall_status']}

**Overall Score:** {summary['score']['overall']}/100

### Category Scores

- **Code Quality:** {summary['score']['code_quality']}/100
- **Security:** {summary['score']['security']}/100
- **GDPR Compliance:** {summary['score']['gdpr_compliance']}/100
- **Accessibility:** {summary['score']['accessibility']}/100

### Issues Summary

- **Critical:** {summary['critical_issues']}
- **High:** {summary['high_issues']}
- **Medium:** {summary['medium_issues']}
- **Low:** {summary['low_issues']}
- **Total:** {summary['total_issues']}

## Critical Issues

"""

        # Categorize issues by severity (Performance: Single-pass O(n) vs O(2n))
        from collections import defaultdict
        issues_by_severity = defaultdict(list)
        for issue in issues:
            issues_by_severity[issue['severity']].append(issue)

        critical = issues_by_severity['CRITICAL']
        high = issues_by_severity['HIGH']

        # Add critical issues using join with generator expression
        if critical:
            md_content += '\n'.join(
                f"""
### {issue['category']} - {issue['subcategory']}

**File:** `{issue['file']}:{issue['line']}`

**Description:** {issue['description']}

**Code:**
```
{issue['code_snippet']}
```

**Recommendation:** {issue['recommendation']}

---
"""
                for issue in critical
            )
        else:
            md_content += "_No critical issues found._\n\n"

        # Add high issues using join
        md_content += "## High Priority Issues\n\n"
        if high:
            md_content += '\n'.join(
                f"- **{issue['category']}** ({issue['file']}:{issue['line']}): {issue['description']}"
                for issue in high[:5]  # Top 5 high issues
            ) + '\n'
        else:
            md_content += "_No high priority issues found._\n\n"

        # Add positive findings using join
        if 'positive_findings' in review_data and review_data['positive_findings']:
            md_content += "\n## Positive Findings\n\n"
            md_content += '\n'.join(
                f"- {finding}"
                for finding in review_data['positive_findings']
            ) + '\n'

        # Add recommendations using join
        if 'recommendations' in review_data and review_data['recommendations']:
            md_content += "\n## Recommendations\n\n"
            md_content += '\n'.join(
                f"- {rec}"
                for rec in review_data['recommendations']
            ) + '\n'

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

        self.logger.info(f"📄 Review summary written to: {summary_file}")

    # REMOVED: _query_kg_for_review_patterns() - now handled by AIQueryService
    # The centralized AIQueryService (ai_query_service.py) handles all
    # KG queries via the CodeReviewKGStrategy class.

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create an error result dictionary."""
        return {
            'status': 'ERROR',
            'developer_name': self.developer_name,
            'error': error_message,
            'review_status': 'FAIL',
            'total_issues': 0,
            'critical_issues': 0,
            'high_issues': 0,
            'overall_score': 0
        }


def main():
    """Test the code review agent."""
    import argparse

    parser = argparse.ArgumentParser(description="Code Review Agent")
    parser.add_argument("--developer", required=True, help="Developer name (e.g., developer-a)")
    parser.add_argument("--implementation-dir", required=True, help="Directory with implementation")
    parser.add_argument("--output-dir", required=True, help="Output directory for review report")
    parser.add_argument("--task-title", default="Test Task", help="Task title")
    parser.add_argument("--task-description", default="Test implementation", help="Task description")

    args = parser.parse_args()

    agent = CodeReviewAgent(developer_name=args.developer)

    result = agent.review_implementation(
        implementation_dir=args.implementation_dir,
        task_title=args.task_title,
        task_description=args.task_description,
        output_dir=args.output_dir
    )

    print(f"\n{'='*80}")
    print(f"Review Result: {result['review_status']}")
    print(f"Overall Score: {result.get('overall_score', 0)}/100")
    print(f"Total Issues: {result['total_issues']}")
    print(f"  Critical: {result['critical_issues']}")
    print(f"  High: {result['high_issues']}")
    print(f"Report: {result.get('report_file', 'N/A')}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
