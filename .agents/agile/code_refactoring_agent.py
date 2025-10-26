#!/usr/bin/env python3
"""
Code Refactoring Agent - Automated Code Quality Improvements

Applies refactoring patterns based on code review feedback:
- Loop to comprehension conversion
- If/elif chain to dictionary mapping
- Long method extraction
- Code duplication removal
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RefactoringRule:
    """A refactoring rule with pattern and fix"""
    name: str
    pattern_type: str  # 'loop', 'if_elif', 'long_method', 'duplication'
    description: str
    priority: int  # 1=critical, 2=high, 3=medium, 4=low


class CodeRefactoringAgent:
    """
    Automated code refactoring agent

    Applies refactoring patterns identified in code review
    """

    REFACTORING_RULES = [
        RefactoringRule(
            name="loop_to_comprehension",
            pattern_type="loop",
            description="Convert simple for loops to list/dict comprehensions",
            priority=2
        ),
        RefactoringRule(
            name="if_elif_to_mapping",
            pattern_type="if_elif",
            description="Convert long if/elif chains to dictionary mapping",
            priority=2
        ),
        RefactoringRule(
            name="extract_long_method",
            pattern_type="long_method",
            description="Extract methods longer than 50 lines",
            priority=1
        ),
        RefactoringRule(
            name="use_next_for_first_match",
            pattern_type="loop",
            description="Use next() with generator for first-match patterns",
            priority=3
        ),
        RefactoringRule(
            name="use_collections_module",
            pattern_type="loop",
            description="Use defaultdict, Counter, chain from collections",
            priority=3
        ),
    ]

    def __init__(self, logger=None, verbose: bool = True):
        """
        Initialize refactoring agent

        Args:
            logger: Logger instance
            verbose: Enable verbose logging
        """
        self.logger = logger
        self.verbose = verbose

    def log(self, message: str, level: str = "INFO"):
        """Log message"""
        if self.verbose:
            if self.logger:
                self.logger.log(message, level)
            else:
                print(f"[Refactoring] {message}")

    def analyze_file_for_refactoring(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a Python file for refactoring opportunities

        Args:
            file_path: Path to Python file

        Returns:
            Dict with refactoring suggestions
        """
        self.log(f"Analyzing {file_path.name} for refactoring opportunities...")

        try:
            with open(file_path, 'r') as f:
                source = f.read()
                tree = ast.parse(source)

            suggestions = {
                'file': str(file_path),
                'long_methods': self._find_long_methods(tree),
                'simple_loops': self._find_simple_loops(tree, source),
                'if_elif_chains': self._find_if_elif_chains(tree, source),
                'total_issues': 0
            }

            suggestions['total_issues'] = (
                len(suggestions['long_methods']) +
                len(suggestions['simple_loops']) +
                len(suggestions['if_elif_chains'])
            )

            return suggestions

        except Exception as e:
            self.log(f"Error analyzing {file_path}: {e}", "ERROR")
            return {'file': str(file_path), 'error': str(e), 'total_issues': 0}

    def _find_long_methods(self, tree: ast.AST) -> List[Dict]:
        """Find methods longer than 50 lines"""
        long_methods = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                    length = node.end_lineno - node.lineno
                    if length > 50:
                        long_methods.append({
                            'name': node.name,
                            'line': node.lineno,
                            'length': length,
                            'suggestion': f'Extract helper methods from {node.name} ({length} lines)'
                        })

        return long_methods

    def _find_simple_loops(self, tree: ast.AST, source: str) -> List[Dict]:
        """Find simple for loops that can be comprehensions"""
        simple_loops = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # Check if loop body is simple (append, extend, etc.)
                if len(node.body) == 1:
                    stmt = node.body[0]
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                        if isinstance(stmt.value.func, ast.Attribute):
                            method_name = stmt.value.func.attr
                            if method_name in ['append', 'add', 'update']:
                                simple_loops.append({
                                    'line': node.lineno,
                                    'suggestion': f'Convert for loop to list/set/dict comprehension'
                                })

        return simple_loops

    def _find_if_elif_chains(self, tree: ast.AST, source: str) -> List[Dict]:
        """Find long if/elif chains that can use dictionary mapping"""
        if_elif_chains = []

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Count elif branches
                elif_count = 0
                current = node
                while hasattr(current, 'orelse') and len(current.orelse) == 1:
                    if isinstance(current.orelse[0], ast.If):
                        elif_count += 1
                        current = current.orelse[0]
                    else:
                        break

                # If 3+ elif branches, suggest dictionary
                if elif_count >= 3:
                    if_elif_chains.append({
                        'line': node.lineno,
                        'elif_count': elif_count,
                        'suggestion': f'Convert {elif_count+1}-branch if/elif to dictionary mapping'
                    })

        return if_elif_chains

    def generate_refactoring_instructions(
        self,
        analysis: Dict[str, Any],
        code_review_issues: List[Dict] = None
    ) -> str:
        """
        Generate detailed refactoring instructions for developer

        Args:
            analysis: Refactoring analysis results
            code_review_issues: Issues from code review

        Returns:
            Formatted refactoring instructions
        """
        instructions = []

        instructions.append("# Refactoring Instructions\n")
        instructions.append(f"File: {analysis['file']}\n")
        instructions.append(f"Total Issues: {analysis['total_issues']}\n\n")

        # Long methods
        if analysis.get('long_methods'):
            instructions.append("## Long Methods (Extract Helper Methods)\n")
            for method in analysis['long_methods']:
                instructions.append(f"- Line {method['line']}: {method['suggestion']}\n")
            instructions.append("\n")

        # Simple loops
        if analysis.get('simple_loops'):
            instructions.append("## Loops → Comprehensions\n")
            for loop in analysis['simple_loops']:
                instructions.append(f"- Line {loop['line']}: {loop['suggestion']}\n")
            instructions.append("\n")

        # If/elif chains
        if analysis.get('if_elif_chains'):
            instructions.append("## If/Elif Chains → Dictionary Mapping\n")
            for chain in analysis['if_elif_chains']:
                instructions.append(f"- Line {chain['line']}: {chain['suggestion']}\n")
            instructions.append("\n")

        # Add code review issues if provided
        if code_review_issues:
            instructions.append("## Code Review Issues to Fix\n")
            for issue in code_review_issues:
                severity = issue.get('severity', 'UNKNOWN')
                category = issue.get('category', 'Unknown')
                description = issue.get('description', 'No description')
                instructions.append(f"- [{severity}] {category}: {description}\n")
            instructions.append("\n")

        # Add best practices
        instructions.append("## Refactoring Best Practices\n")
        instructions.append("1. Use list/dict/set comprehensions for simple loops\n")
        instructions.append("2. Use next() with generator for first-match patterns\n")
        instructions.append("3. Replace if/elif chains (3+ branches) with dict.get()\n")
        instructions.append("4. Extract methods longer than 50 lines\n")
        instructions.append("5. Use collections module: defaultdict, Counter, chain\n")
        instructions.append("6. Prefer composition over inheritance\n")
        instructions.append("7. Follow Single Responsibility Principle\n")

        return "".join(instructions)

    def apply_automated_refactoring(
        self,
        file_path: Path,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply automated refactoring to a file

        Args:
            file_path: Path to file
            analysis: Refactoring analysis

        Returns:
            Dict with refactoring results
        """
        self.log(f"Applying automated refactoring to {file_path.name}...")

        # For now, return suggestions only
        # Full automation would require AST transformation
        return {
            'file': str(file_path),
            'status': 'SUGGESTIONS_ONLY',
            'message': 'Automated refactoring requires LLM or manual intervention',
            'suggestions': analysis
        }


def create_refactoring_agent(logger=None, verbose: bool = True) -> CodeRefactoringAgent:
    """
    Create refactoring agent instance

    Args:
        logger: Logger instance
        verbose: Enable verbose logging

    Returns:
        CodeRefactoringAgent instance
    """
    return CodeRefactoringAgent(logger=logger, verbose=verbose)


if __name__ == "__main__":
    # Example usage
    import sys

    agent = create_refactoring_agent()

    # Analyze this file
    file_path = Path(__file__)
    analysis = agent.analyze_file_for_refactoring(file_path)

    print("\nRefactoring Analysis:")
    print(f"File: {analysis['file']}")
    print(f"Total Issues: {analysis['total_issues']}")

    if analysis.get('long_methods'):
        print(f"\nLong Methods: {len(analysis['long_methods'])}")
        for method in analysis['long_methods']:
            print(f"  - {method['name']} ({method['length']} lines)")

    # Generate instructions
    instructions = agent.generate_refactoring_instructions(analysis)
    print("\n" + instructions)
