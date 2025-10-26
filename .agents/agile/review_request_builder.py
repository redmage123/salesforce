#!/usr/bin/env python3
"""
Review Request Builder - Builder Pattern for Code Review Requests

This module provides a fluent interface for building complex code review
requests using the Builder pattern.

Benefits:
- Fluent interface (method chaining)
- Step-by-step construction
- Validation before building
- Immutable result
- Easy to extend with new review criteria

Usage:
    builder = ReviewRequestBuilder()
    messages = (builder
        .set_developer("developer-a")
        .set_task("Implement user auth", "Add JWT authentication")
        .add_file("auth.py", "def login():\\n    pass")
        .add_file("jwt.py", "import jwt")
        .set_review_prompt(prompt_text)
        .build())
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from pathlib import Path

from llm_client import LLMMessage
from artemis_exceptions import CodeReviewExecutionError


@dataclass(frozen=True)
class ImplementationFile:
    """
    Value Object: Represents a single implementation file

    Benefits:
    - Immutable
    - Type-safe
    - Self-documenting
    - Validation at construction
    """
    path: str
    content: str
    lines: int
    language: str = field(default="")

    def __post_init__(self):
        """Validate file data and infer language if not set"""
        if not self.path:
            raise ValueError("File path cannot be empty")
        if self.lines < 0:
            raise ValueError(f"Line count must be non-negative, got {self.lines}")

        # If language is not set, infer from file extension
        if not self.language:
            object.__setattr__(self, 'language', self._infer_language())

    def _infer_language(self) -> str:
        """Infer programming language from file extension"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.java': 'java',
            '.go': 'go',
            '.rb': 'ruby',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.sh': 'bash',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.md': 'markdown',
            '.sql': 'sql'
        }

        # Extract extension from path
        from pathlib import Path
        ext = Path(self.path).suffix.lower()
        return ext_map.get(ext, '')

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            'path': self.path,
            'content': self.content,
            'lines': self.lines,
            'language': self.language
        }

    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> 'ImplementationFile':
        """Create from dictionary"""
        return cls(
            path=data['path'],
            content=data['content'],
            lines=data['lines'],
            language=data.get('language', '')
        )

    @classmethod
    def from_file_path(cls, file_path: Path, base_path: Path) -> 'ImplementationFile':
        """
        Create ImplementationFile from file path

        Args:
            file_path: Path to the file
            base_path: Base path for relative path calculation

        Returns:
            ImplementationFile instance
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        relative_path = file_path.relative_to(base_path)
        line_count = len(content.split('\n'))

        return cls(
            path=str(relative_path),
            content=content,
            lines=line_count
        )

    def format_for_review(self) -> str:
        """Format file content for code review"""
        return f"""## File: {self.path}
```
{self.content}
```
"""


@dataclass
class ReviewRequestBuilder:
    """
    Builder for constructing code review requests

    Uses Builder pattern for step-by-step construction of complex review requests.

    Example:
        builder = ReviewRequestBuilder()
        messages = (builder
            .set_developer("developer-a")
            .set_task("Implement auth", "Add JWT authentication")
            .add_file("auth.py", "code here", 50)
            .set_review_prompt(prompt)
            .build())
    """

    # Mutable state during building (reset after build)
    _developer_name: Optional[str] = None
    _task_title: Optional[str] = None
    _task_description: Optional[str] = None
    _implementation_files: List[ImplementationFile] = field(default_factory=list)
    _review_prompt: Optional[str] = None
    _review_focus_areas: List[str] = field(default_factory=lambda: [
        "Code Quality - Anti-patterns, optimization opportunities",
        "Security - OWASP Top 10 vulnerabilities, secure coding practices",
        "GDPR Compliance - Data privacy, consent, user rights",
        "Accessibility - WCAG 2.1 AA standards"
    ])

    def set_developer(self, developer_name: str) -> 'ReviewRequestBuilder':
        """
        Set the developer name

        Args:
            developer_name: Name of the developer (e.g., "developer-a")

        Returns:
            Self for method chaining
        """
        if not developer_name or not developer_name.strip():
            raise ValueError("Developer name cannot be empty")
        self._developer_name = developer_name
        return self

    def set_task(self, title: str, description: str) -> 'ReviewRequestBuilder':
        """
        Set the task details

        Args:
            title: Task title
            description: Task description

        Returns:
            Self for method chaining
        """
        if not title or not title.strip():
            raise ValueError("Task title cannot be empty")
        if not description or not description.strip():
            raise ValueError("Task description cannot be empty")

        self._task_title = title
        self._task_description = description
        return self

    def add_file(self, path: str, content: str, lines: Optional[int] = None) -> 'ReviewRequestBuilder':
        """
        Add an implementation file

        Args:
            path: File path (relative)
            content: File content
            lines: Number of lines (auto-calculated if None)

        Returns:
            Self for method chaining
        """
        if lines is None:
            lines = len(content.split('\n'))

        impl_file = ImplementationFile(path=path, content=content, lines=lines)
        self._implementation_files.append(impl_file)
        return self

    def add_file_object(self, impl_file: ImplementationFile) -> 'ReviewRequestBuilder':
        """
        Add an ImplementationFile object

        Args:
            impl_file: ImplementationFile instance

        Returns:
            Self for method chaining
        """
        self._implementation_files.append(impl_file)
        return self

    def add_files(self, files: List[ImplementationFile]) -> 'ReviewRequestBuilder':
        """
        Add multiple implementation files

        Args:
            files: List of ImplementationFile instances

        Returns:
            Self for method chaining
        """
        self._implementation_files.extend(files)
        return self

    def set_review_prompt(self, prompt: str) -> 'ReviewRequestBuilder':
        """
        Set the system prompt for code review

        Args:
            prompt: System prompt text

        Returns:
            Self for method chaining
        """
        if not prompt or not prompt.strip():
            raise ValueError("Review prompt cannot be empty")
        self._review_prompt = prompt
        return self

    def set_focus_areas(self, focus_areas: List[str]) -> 'ReviewRequestBuilder':
        """
        Set custom review focus areas

        Args:
            focus_areas: List of focus area descriptions

        Returns:
            Self for method chaining
        """
        if not focus_areas:
            raise ValueError("Focus areas cannot be empty")
        self._review_focus_areas = focus_areas
        return self

    def add_focus_area(self, focus_area: str) -> 'ReviewRequestBuilder':
        """
        Add a single focus area

        Args:
            focus_area: Focus area description

        Returns:
            Self for method chaining
        """
        self._review_focus_areas.append(focus_area)
        return self

    def validate(self) -> bool:
        """
        Validate that all required fields are set

        Returns:
            True if valid

        Raises:
            CodeReviewExecutionError: If validation fails
        """
        errors = []

        if not self._developer_name:
            errors.append("Developer name is required")
        if not self._task_title:
            errors.append("Task title is required")
        if not self._task_description:
            errors.append("Task description is required")
        if not self._implementation_files:
            errors.append("At least one implementation file is required")
        if not self._review_prompt:
            errors.append("Review prompt is required")

        if errors:
            raise CodeReviewExecutionError(
                "Review request validation failed",
                context={
                    "errors": errors,
                    "developer_name": self._developer_name,
                    "files_count": len(self._implementation_files)
                }
            )

        return True

    def build(self) -> List[LLMMessage]:
        """
        Build the review request messages

        Returns:
            List of LLMMessage instances (system + user prompts)

        Raises:
            CodeReviewExecutionError: If validation fails
        """
        # Validate before building
        self.validate()

        # Build files content (using list comprehension - Pythonic!)
        files_content = [
            file.format_for_review()
            for file in self._implementation_files
        ]

        # Build focus areas (using list comprehension with enumerate)
        focus_areas_text = '\n'.join([
            f"{i+1}. **{area}**"
            for i, area in enumerate(self._review_focus_areas)
        ])

        # Build user prompt
        user_prompt = f"""# Code Review Request

## Task Context

**Task Title:** {self._task_title}

**Task Description:** {self._task_description}

**Developer:** {self._developer_name}

## Implementation to Review

{chr(10).join(files_content)}

## Your Task

Perform a comprehensive code review following the guidelines in your system prompt. Analyze for:

{focus_areas_text}

Return your review as structured JSON exactly matching the format specified in your prompt.

Focus on being thorough, specific, and actionable. Include file paths, line numbers, code snippets, and clear recommendations.
"""

        # Build messages
        messages = [
            LLMMessage(role="system", content=self._review_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]

        return messages

    def get_file_count(self) -> int:
        """Get the number of files added"""
        return len(self._implementation_files)

    def get_total_lines(self) -> int:
        """Get total lines across all files"""
        return sum(file.lines for file in self._implementation_files)

    def get_files(self) -> List[ImplementationFile]:
        """Get the list of implementation files"""
        return self._implementation_files.copy()  # Return copy to prevent mutation

    def reset(self) -> 'ReviewRequestBuilder':
        """
        Reset the builder to initial state

        Returns:
            Self for method chaining
        """
        self._developer_name = None
        self._task_title = None
        self._task_description = None
        self._implementation_files = []
        self._review_prompt = None
        self._review_focus_areas = [
            "Code Quality - Anti-patterns, optimization opportunities",
            "Security - OWASP Top 10 vulnerabilities, secure coding practices",
            "GDPR Compliance - Data privacy, consent, user rights",
            "Accessibility - WCAG 2.1 AA standards"
        ]
        return self


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def read_implementation_files(implementation_dir: str) -> List[ImplementationFile]:
    """
    Read all implementation files from a directory

    Args:
        implementation_dir: Directory containing implementation files

    Returns:
        List of ImplementationFile instances

    Raises:
        FileNotFoundError: If directory doesn't exist
    """
    impl_path = Path(implementation_dir)

    if not impl_path.exists():
        raise FileNotFoundError(f"Implementation directory not found: {implementation_dir}")

    # Read all supported file types
    extensions = ['.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.java', '.go', '.rb']

    # Use list comprehension to gather all files (Pythonic!)
    files = [
        ImplementationFile.from_file_path(file_path, impl_path)
        for ext in extensions
        for file_path in impl_path.rglob(f'*{ext}')
    ]

    return files


def create_review_request(
    developer_name: str,
    task_title: str,
    task_description: str,
    implementation_dir: str,
    review_prompt: str
) -> List[LLMMessage]:
    """
    Convenience function to create a review request in one call

    Args:
        developer_name: Name of the developer
        task_title: Task title
        task_description: Task description
        implementation_dir: Directory with implementation files
        review_prompt: System prompt for review

    Returns:
        List of LLMMessage instances

    Example:
        messages = create_review_request(
            developer_name="developer-a",
            task_title="Implement authentication",
            task_description="Add JWT-based authentication",
            implementation_dir="/tmp/developer-a",
            review_prompt=prompt_text
        )
    """
    # Read files
    files = read_implementation_files(implementation_dir)

    # Build request
    builder = ReviewRequestBuilder()
    messages = (builder
        .set_developer(developer_name)
        .set_task(task_title, task_description)
        .add_files(files)
        .set_review_prompt(review_prompt)
        .build())

    return messages
