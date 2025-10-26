#!/usr/bin/env python3
"""
Shared types for code examples system.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class CodeExample:
    """Structured code example for storage"""
    language: str
    pattern: str
    title: str
    description: str
    code: str
    quality_score: int  # 1-100
    tags: List[str]
    complexity: str  # beginner, intermediate, advanced
    demonstrates: List[str]  # Concepts demonstrated
    prevents: List[str]  # Anti-patterns prevented
