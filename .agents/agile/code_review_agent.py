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
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the code review agent.

        Args:
            developer_name: Name of the developer whose code to review (e.g., "developer-a")
            llm_provider: LLM provider ("openai" or "anthropic")
            llm_model: Specific model to use (optional)
            logger: Logger instance (optional)
        """
        self.developer_name = developer_name
        self.llm_provider = llm_provider or os.getenv("ARTEMIS_LLM_PROVIDER", "openai")
        self.llm_model = llm_model or os.getenv("ARTEMIS_LLM_MODEL")
        self.logger = logger or self._setup_logger()

        # Initialize LLM client
        self.llm_client = create_llm_client(
            provider=self.llm_provider
        )

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
        Perform comprehensive code review on an implementation.

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
            # Step 1: Read implementation files
            implementation_files = self._read_implementation_files(implementation_dir)
            if not implementation_files:
                return self._create_error_result("No implementation files found")

            self.logger.info(f"📁 Read {len(implementation_files)} implementation files")

            # Step 2: Read code review prompt
            review_prompt = self._read_review_prompt()

            # Step 3: Build complete review request
            review_request = self._build_review_request(
                review_prompt=review_prompt,
                implementation_files=implementation_files,
                task_title=task_title,
                task_description=task_description
            )

            # Step 4: Call LLM API for code review
            self.logger.info("🤖 Requesting code review from LLM...")
            review_response = self._call_llm_for_review(review_request)

            # Step 5: Parse review JSON
            review_data = self._parse_review_response(review_response.content)

            # Step 6: Add metadata
            review_data['metadata'] = {
                'developer_name': self.developer_name,
                'task_title': task_title,
                'reviewed_at': datetime.now().isoformat(),
                'llm_provider': self.llm_provider,
                'llm_model': review_response.model,  # Use model from response
                'tokens_used': review_response.usage
            }

            # Step 7: Write review report
            report_file = self._write_review_report(review_data, output_dir)

            # Step 8: Return results
            return {
                'status': 'COMPLETED',
                'developer_name': self.developer_name,
                'review_status': review_data['review_summary']['overall_status'],
                'total_issues': review_data['review_summary']['total_issues'],
                'critical_issues': review_data['review_summary']['critical_issues'],
                'high_issues': review_data['review_summary']['high_issues'],
                'overall_score': review_data['review_summary']['score']['overall'],
                'report_file': report_file,
                'tokens_used': review_response.usage
            }

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

    def _read_implementation_files(self, implementation_dir: str) -> List[Dict[str, str]]:
        """Read all implementation files from directory."""
        files = []
        impl_path = Path(implementation_dir)

        if not impl_path.exists():
            self.logger.warning(f"Implementation directory not found: {implementation_dir}")
            return files

        # Read all .py, .js, .html, .css files
        extensions = ['.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.java', '.go', '.rb']

        for ext in extensions:
            for file_path in impl_path.rglob(f'*{ext}'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        relative_path = file_path.relative_to(impl_path)
                        line_count = len(content.split('\n'))
                        files.append({
                            'path': str(relative_path),
                            'content': content,
                            'lines': line_count
                        })
                        self.logger.debug(f"  Read {relative_path} ({line_count} lines)")
                except Exception as e:
                    raise wrap_exception(
                        e,
                        FileReadError,
                        "Failed to read implementation file",
                        {
                            "file_path": str(file_path),
                            "implementation_dir": implementation_dir,
                            "developer_name": self.developer_name
                        }
                    )

        return files

    def _read_review_prompt(self) -> str:
        """Read the code review agent prompt."""
        prompt_file = Path(__file__).parent / "prompts" / "code_review_agent_prompt.md"

        if not prompt_file.exists():
            raise FileReadError(
                f"Code review prompt not found: {prompt_file}",
                context={"prompt_file": str(prompt_file)}
            )

        try:
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
        implementation_files: List[Dict[str, str]],
        task_title: str,
        task_description: str
    ) -> List[LLMMessage]:
        """Build the complete review request for the LLM."""

        # Build files content
        files_content = []
        for file_info in implementation_files:
            files_content.append(f"## File: {file_info['path']}")
            files_content.append(f"```")
            files_content.append(file_info['content'])
            files_content.append(f"```\n")

        user_prompt = f"""
# Code Review Request

## Task Context

**Task Title:** {task_title}

**Task Description:** {task_description}

**Developer:** {self.developer_name}

## Implementation to Review

{chr(10).join(files_content)}

## Your Task

Perform a comprehensive code review following the guidelines in your system prompt. Analyze for:

1. **Code Quality** - Anti-patterns, optimization opportunities
2. **Security** - OWASP Top 10 vulnerabilities, secure coding practices
3. **GDPR Compliance** - Data privacy, consent, user rights
4. **Accessibility** - WCAG 2.1 AA standards

Return your review as structured JSON exactly matching the format specified in your prompt.

Focus on being thorough, specific, and actionable. Include file paths, line numbers, code snippets, and clear recommendations.
"""

        return [
            LLMMessage(role="system", content=review_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]

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

            # Remove markdown code blocks if present
            if content.startswith('```json'):
                content = content[7:]
            elif content.startswith('```'):
                content = content[3:]

            if content.endswith('```'):
                content = content[:-3]

            content = content.strip()

            # Parse JSON
            review_data = json.loads(content)

            # Validate required fields
            required_fields = ['review_summary', 'issues']
            for field in required_fields:
                if field not in review_data:
                    raise LLMResponseParsingError(
                        f"Missing required field in code review response: {field}",
                        context={"missing_field": field, "available_fields": list(review_data.keys())}
                    )

            self.logger.info("✅ Review response parsed successfully")
            self.logger.info(f"   Total issues: {review_data['review_summary']['total_issues']}")
            self.logger.info(f"   Critical: {review_data['review_summary']['critical_issues']}")
            self.logger.info(f"   Overall status: {review_data['review_summary']['overall_status']}")

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

        # Add critical issues
        critical = [i for i in issues if i['severity'] == 'CRITICAL']
        if critical:
            for issue in critical:
                md_content += f"""
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
        else:
            md_content += "_No critical issues found._\n\n"

        # Add high issues
        md_content += "## High Priority Issues\n\n"
        high = [i for i in issues if i['severity'] == 'HIGH']
        if high:
            for issue in high[:5]:  # Top 5 high issues
                md_content += f"- **{issue['category']}** ({issue['file']}:{issue['line']}): {issue['description']}\n"
        else:
            md_content += "_No high priority issues found._\n\n"

        # Add positive findings
        if 'positive_findings' in review_data and review_data['positive_findings']:
            md_content += "\n## Positive Findings\n\n"
            for finding in review_data['positive_findings']:
                md_content += f"- {finding}\n"

        # Add recommendations
        if 'recommendations' in review_data and review_data['recommendations']:
            md_content += "\n## Recommendations\n\n"
            for rec in review_data['recommendations']:
                md_content += f"- {rec}\n"

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

        self.logger.info(f"📄 Review summary written to: {summary_file}")

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
