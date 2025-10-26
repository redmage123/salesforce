#!/usr/bin/env python3
"""
Research Strategy Pattern Implementation

Implements Strategy Pattern for different research sources.
Uses Factory Pattern for strategy creation.
No nested loops, no elif chains - uses dictionary dispatch and comprehensions.
"""

import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache

from research_exceptions import ResearchSourceError, ResearchTimeoutError


@dataclass
class ResearchExample:
    """Represents a code example found during research"""
    title: str
    content: str
    source: str
    url: Optional[str]
    language: str
    tags: List[str]
    relevance_score: float


class ResearchStrategy(ABC):
    """
    Abstract base class for research strategies (Strategy Pattern).
    Each concrete strategy implements a different research source.
    """

    def __init__(self, timeout_seconds: int = 30):
        """
        Initialize research strategy.

        Args:
            timeout_seconds: Timeout for HTTP requests
        """
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def search(self, query: str, technologies: List[str], max_results: int = 5) -> List[ResearchExample]:
        """
        Search for code examples.

        Args:
            query: Search query describing what to find
            technologies: List of technologies/frameworks to search for
            max_results: Maximum number of results to return

        Returns:
            List of ResearchExample objects

        Raises:
            ResearchSourceError: If search fails
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of this research source"""
        pass

    def _build_queries(self, query: str, technologies: List[str]) -> List[str]:
        """
        Build search queries from base query and technologies.
        Uses comprehension instead of nested loop.

        Args:
            query: Base query
            technologies: List of technologies

        Returns:
            List of search query strings
        """
        # Use comprehension instead of nested loop
        return [f"{query} {tech}" for tech in technologies] if technologies else [query]

    def _fetch_url(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Fetch URL with timeout and error handling.

        Args:
            url: URL to fetch
            headers: Optional HTTP headers

        Returns:
            Parsed JSON response

        Raises:
            ResearchSourceError: If fetch fails
        """
        try:
            request = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.URLError as e:
            raise ResearchSourceError(
                self.get_source_name(),
                f"Failed to fetch {url}",
                cause=e
            )
        except json.JSONDecodeError as e:
            raise ResearchSourceError(
                self.get_source_name(),
                f"Invalid JSON response from {url}",
                cause=e
            )
        except TimeoutError as e:
            raise ResearchTimeoutError(
                f"fetch {url}",
                self.timeout_seconds,
                cause=e
            )


class GitHubResearchStrategy(ResearchStrategy):
    """
    Research strategy for GitHub API.
    Searches GitHub repositories for code examples.
    """

    def get_source_name(self) -> str:
        return "GitHub"

    def search(self, query: str, technologies: List[str], max_results: int = 5) -> List[ResearchExample]:
        """
        Search GitHub for code examples.

        Args:
            query: Search query
            technologies: Technologies to search for
            max_results: Maximum results

        Returns:
            List of ResearchExample objects
        """
        # Build queries using comprehension (no nested loop)
        queries = self._build_queries(query, technologies)

        # Search each query and flatten results (no nested loop)
        all_results = [
            self._search_github_code(q, max_results // len(queries) + 1)
            for q in queries
        ]

        # Flatten and sort by relevance
        examples = [example for results in all_results for example in results]
        examples.sort(key=lambda x: x.relevance_score, reverse=True)

        return examples[:max_results]

    def _search_github_code(self, query: str, limit: int) -> List[ResearchExample]:
        """
        Search GitHub code API.

        Args:
            query: Search query
            limit: Result limit

        Returns:
            List of ResearchExample objects
        """
        try:
            # GitHub API endpoint
            url = f"https://api.github.com/search/code?q={urllib.parse.quote(query)}&per_page={limit}"

            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Artemis-Research-Agent"
            }

            data = self._fetch_url(url, headers)

            # Convert to ResearchExample objects using comprehension
            return [
                ResearchExample(
                    title=item.get('name', 'Unknown'),
                    content=self._fetch_file_content(item.get('url', '')),
                    source="GitHub",
                    url=item.get('html_url'),
                    language=item.get('language', 'Unknown'),
                    tags=[item.get('repository', {}).get('name', '')],
                    relevance_score=item.get('score', 0.0)
                )
                for item in data.get('items', [])
            ]

        except ResearchSourceError:
            raise
        except Exception as e:
            raise ResearchSourceError(
                self.get_source_name(),
                f"GitHub search failed for query: {query}",
                cause=e
            )

    def _fetch_file_content(self, url: str) -> str:
        """
        Fetch file content from GitHub API.

        Args:
            url: API URL for file

        Returns:
            File content as string
        """
        # Guard clause: early return if no URL
        if not url:
            return ""

        try:
            headers = {
                "Accept": "application/vnd.github.v3.raw",
                "User-Agent": "Artemis-Research-Agent"
            }
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read().decode('utf-8', errors='ignore')[:5000]  # Limit size
        except Exception:
            return ""  # Return empty on error


class HuggingFaceResearchStrategy(ResearchStrategy):
    """
    Research strategy for HuggingFace datasets/models.
    Searches HuggingFace Hub for relevant examples.
    """

    def get_source_name(self) -> str:
        return "HuggingFace"

    def search(self, query: str, technologies: List[str], max_results: int = 5) -> List[ResearchExample]:
        """
        Search HuggingFace Hub.

        Args:
            query: Search query
            technologies: Technologies to search for
            max_results: Maximum results

        Returns:
            List of ResearchExample objects
        """
        # Build queries using comprehension
        queries = self._build_queries(query, technologies)

        # Search each query (no nested loop)
        all_results = [
            self._search_huggingface(q, max_results // len(queries) + 1)
            for q in queries
        ]

        # Flatten and sort
        examples = [example for results in all_results for example in results]
        examples.sort(key=lambda x: x.relevance_score, reverse=True)

        return examples[:max_results]

    def _search_huggingface(self, query: str, limit: int) -> List[ResearchExample]:
        """
        Search HuggingFace API.

        Args:
            query: Search query
            limit: Result limit

        Returns:
            List of ResearchExample objects
        """
        try:
            # HuggingFace API endpoint
            url = f"https://huggingface.co/api/models?search={urllib.parse.quote(query)}&limit={limit}"

            data = self._fetch_url(url)

            # Convert to ResearchExample objects
            return [
                ResearchExample(
                    title=item.get('modelId', 'Unknown'),
                    content=self._fetch_readme(item.get('modelId', '')),
                    source="HuggingFace",
                    url=f"https://huggingface.co/{item.get('modelId', '')}",
                    language="Python",  # Most HF models use Python
                    tags=item.get('tags', []),
                    relevance_score=item.get('downloads', 0) / 1000.0  # Normalize downloads
                )
                for item in data[:limit]
            ]

        except ResearchSourceError:
            raise
        except Exception as e:
            raise ResearchSourceError(
                self.get_source_name(),
                f"HuggingFace search failed for query: {query}",
                cause=e
            )

    def _fetch_readme(self, model_id: str) -> str:
        """Fetch model README content"""
        # Guard clause
        if not model_id:
            return ""

        try:
            url = f"https://huggingface.co/{model_id}/raw/main/README.md"
            request = urllib.request.Request(url)
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read().decode('utf-8', errors='ignore')[:5000]
        except Exception:
            return ""


class LocalExamplesResearchStrategy(ResearchStrategy):
    """
    Research strategy for local filesystem.
    Searches local directories for example code.
    """

    def __init__(self, search_paths: Optional[List[str]] = None, timeout_seconds: int = 30):
        """
        Initialize with search paths.

        Args:
            search_paths: Directories to search (default: current + src)
            timeout_seconds: Timeout (not used for local search)
        """
        super().__init__(timeout_seconds)
        self.search_paths = search_paths or [".", "src", "examples"]

    def get_source_name(self) -> str:
        return "Local"

    def search(self, query: str, technologies: List[str], max_results: int = 5) -> List[ResearchExample]:
        """
        Search local filesystem.

        Args:
            query: Search query
            technologies: Technologies to search for
            max_results: Maximum results

        Returns:
            List of ResearchExample objects
        """
        # Build file patterns from technologies
        extensions = self._get_extensions_for_technologies(technologies)

        # Search all paths (no nested loop - use comprehension)
        all_files = [
            self._find_files_in_path(Path(path), extensions)
            for path in self.search_paths
            if Path(path).exists()
        ]

        # Flatten file list
        files = [f for file_list in all_files for f in file_list]

        # Filter by query and convert to examples
        examples = [
            self._create_example_from_file(f, query)
            for f in files
            if self._file_matches_query(f, query)
        ]

        # Sort by relevance and limit
        examples.sort(key=lambda x: x.relevance_score, reverse=True)
        return examples[:max_results]

    @lru_cache(maxsize=128)
    def _get_extensions_for_technologies(self, technologies_tuple: tuple) -> List[str]:
        """
        Get file extensions for technologies.
        Uses LRU cache for logarithmic performance.

        Args:
            technologies_tuple: Technologies as tuple (for caching)

        Returns:
            List of file extensions
        """
        # Dictionary dispatch instead of elif chain
        extension_map = {
            "python": [".py", ".ipynb"],
            "javascript": [".js", ".jsx", ".ts", ".tsx"],
            "java": [".java"],
            "rust": [".rs"],
            "go": [".go"],
            "ruby": [".rb"],
            "php": [".php"],
        }

        # Use comprehension to collect extensions
        extensions = [
            ext
            for tech in technologies_tuple
            for ext in extension_map.get(tech.lower(), [f".{tech}"])
        ]

        return extensions if extensions else [".py", ".js", ".java"]  # Default

    def _find_files_in_path(self, path: Path, extensions: List[str]) -> List[Path]:
        """
        Find files with given extensions in path.

        Args:
            path: Directory to search
            extensions: File extensions to find

        Returns:
            List of file paths
        """
        # Guard clause
        if not path.is_dir():
            return []

        # Use comprehension instead of nested loop
        return [
            f for f in path.rglob("*")
            if f.is_file() and f.suffix in extensions
        ][:20]  # Limit for performance

    def _file_matches_query(self, file_path: Path, query: str) -> bool:
        """Check if file matches query"""
        query_lower = query.lower()
        return query_lower in file_path.name.lower() or query_lower in str(file_path.parent).lower()

    def _create_example_from_file(self, file_path: Path, query: str) -> ResearchExample:
        """Create ResearchExample from file"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')[:5000]
            relevance = self._calculate_relevance(content, query)

            return ResearchExample(
                title=file_path.name,
                content=content,
                source="Local",
                url=str(file_path),
                language=file_path.suffix[1:],  # Remove dot from extension
                tags=[file_path.parent.name],
                relevance_score=relevance
            )
        except Exception:
            return ResearchExample(
                title=file_path.name,
                content="",
                source="Local",
                url=str(file_path),
                language=file_path.suffix[1:],
                tags=[],
                relevance_score=0.0
            )

    def _calculate_relevance(self, content: str, query: str) -> float:
        """Calculate relevance score based on query matches"""
        content_lower = content.lower()
        query_words = query.lower().split()

        # Count matches
        matches = sum(1 for word in query_words if word in content_lower)

        # Normalize to 0-1 range
        return matches / len(query_words) if query_words else 0.0


class ResearchStrategyFactory:
    """
    Factory Pattern for creating research strategies.
    Uses dictionary dispatch instead of elif chain.
    """

    # Strategy registry (dictionary dispatch)
    _STRATEGY_REGISTRY = {
        "github": GitHubResearchStrategy,
        "huggingface": HuggingFaceResearchStrategy,
        "local": LocalExamplesResearchStrategy,
    }

    @classmethod
    def create_strategy(cls, source_name: str, **kwargs) -> ResearchStrategy:
        """
        Create research strategy by name.

        Args:
            source_name: Name of strategy (github, huggingface, local)
            **kwargs: Arguments to pass to strategy constructor

        Returns:
            ResearchStrategy instance

        Raises:
            ValueError: If source_name is unknown
        """
        # Guard clause for unknown strategy
        if source_name.lower() not in cls._STRATEGY_REGISTRY:
            raise ValueError(f"Unknown research source: {source_name}")

        # Dictionary dispatch - no elif chain
        strategy_class = cls._STRATEGY_REGISTRY[source_name.lower()]
        return strategy_class(**kwargs)

    @classmethod
    def create_all_strategies(cls, **kwargs) -> List[ResearchStrategy]:
        """
        Create all available strategies.

        Args:
            **kwargs: Arguments to pass to strategy constructors

        Returns:
            List of all research strategies
        """
        # Use comprehension instead of loop
        return [
            strategy_class(**kwargs)
            for strategy_class in cls._STRATEGY_REGISTRY.values()
        ]

    @classmethod
    def get_available_sources(cls) -> List[str]:
        """Get list of available research source names"""
        return list(cls._STRATEGY_REGISTRY.keys())
