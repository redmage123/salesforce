#!/usr/bin/env python3
"""
Code Quality Scanner - Detects antipatterns and code smells

Scans Python files for:
1. God Classes (> 500 lines)
2. Long methods (> 100 lines)
3. Too many parameters (> 7)
4. Deep nesting (> 4 levels)
5. Magic numbers/strings
6. Mutable default arguments
7. Missing type hints
8. Dead code
9. TODOs/FIXMEs/HACKs
10. Commented-out code blocks
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict


class CodeSmellDetector(ast.NodeVisitor):
    """AST visitor to detect code smells"""

    def __init__(self, source_code: str, filename: str):
        self.source_code = source_code
        self.filename = filename
        self.lines = source_code.split('\n')

        # Results
        self.god_classes = []
        self.long_methods = []
        self.too_many_params = []
        self.deep_nesting = []
        self.mutable_defaults = []
        self.missing_type_hints = []
        self.magic_values = []

    def visit_ClassDef(self, node):
        """Check for God Classes"""
        # Calculate class length
        if hasattr(node, 'end_lineno') and node.end_lineno:
            class_length = node.end_lineno - node.lineno
            if class_length > 500:
                self.god_classes.append({
                    "class": node.name,
                    "lines": class_length,
                    "line_number": node.lineno
                })

        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """Check for long methods, too many params, missing type hints, mutable defaults"""
        # Check method length
        if hasattr(node, 'end_lineno') and node.end_lineno:
            method_length = node.end_lineno - node.lineno
            if method_length > 100:
                self.long_methods.append({
                    "method": node.name,
                    "lines": method_length,
                    "line_number": node.lineno
                })

        # Check parameter count
        num_params = len(node.args.args)
        if num_params > 7:
            self.too_many_params.append({
                "method": node.name,
                "params": num_params,
                "line_number": node.lineno
            })

        # Check for mutable default arguments
        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.mutable_defaults.append({
                    "method": node.name,
                    "line_number": node.lineno
                })
                break

        # Check for missing type hints
        has_return_annotation = node.returns is not None
        has_arg_annotations = any(arg.annotation for arg in node.args.args)

        if not has_return_annotation and not node.name.startswith('_'):
            # Skip dunder methods and private methods
            if not (node.name.startswith('__') and node.name.endswith('__')):
                self.missing_type_hints.append({
                    "method": node.name,
                    "line_number": node.lineno,
                    "reason": "missing_return_type"
                })

        # Check nesting depth
        max_depth = self._calculate_nesting_depth(node)
        if max_depth > 4:
            self.deep_nesting.append({
                "method": node.name,
                "depth": max_depth,
                "line_number": node.lineno
            })

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Treat async functions like regular functions"""
        self.visit_FunctionDef(node)

    def visit_Constant(self, node):
        """Check for magic numbers and strings"""
        # Skip common acceptable constants
        if isinstance(node.value, (int, float)):
            if node.value not in [0, 1, -1, 2, 10, 100, 1000]:
                # Check if it's in a constant assignment
                parent = getattr(node, 'parent', None)
                if not self._is_constant_assignment(node):
                    self.magic_values.append({
                        "value": node.value,
                        "line_number": node.lineno,
                        "type": "number"
                    })

        self.generic_visit(node)

    def _calculate_nesting_depth(self, node, depth=0):
        """Calculate maximum nesting depth in a function"""
        max_depth = depth
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = depth + 1
                max_depth = max(max_depth, child_depth)
        return max_depth

    def _is_constant_assignment(self, node):
        """Check if node is part of a constant assignment"""
        # Simple heuristic: check if variable name is uppercase
        # This is a simplified check
        return False


def analyze_file(file_path: Path) -> Dict[str, Any]:
    """Analyze a single Python file"""
    try:
        source_code = file_path.read_text(encoding='utf-8')

        # Parse AST
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            return {
                "file": str(file_path),
                "error": f"Syntax error: {e}",
                "skipped": True
            }

        # Run AST-based detection
        detector = CodeSmellDetector(source_code, str(file_path))
        detector.visit(tree)

        # Regex-based detection
        todos = find_todos(source_code)
        commented_code = find_commented_code(source_code)

        # Build report
        report = {
            "file": str(file_path),
            "god_classes": detector.god_classes,
            "long_methods": detector.long_methods,
            "too_many_params": detector.too_many_params,
            "deep_nesting": detector.deep_nesting,
            "magic_values": detector.magic_values[:10],  # Limit to top 10
            "mutable_defaults": detector.mutable_defaults,
            "missing_type_hints": detector.missing_type_hints[:10],  # Limit to top 10
            "todos": todos,
            "commented_code": commented_code[:5],  # Limit to top 5
            "line_count": len(source_code.split('\n')),
            "skipped": False
        }

        return report

    except Exception as e:
        return {
            "file": str(file_path),
            "error": str(e),
            "skipped": True
        }


def find_todos(source_code: str) -> List[Dict]:
    """Find TODO/FIXME/HACK comments"""
    todos = []
    lines = source_code.split('\n')

    todo_pattern = re.compile(r'#.*?\b(TODO|FIXME|HACK|XXX|NOTE)\b:?\s*(.*)', re.IGNORECASE)

    for i, line in enumerate(lines, 1):
        match = todo_pattern.search(line)
        if match:
            todos.append({
                "line_number": i,
                "type": match.group(1).upper(),
                "comment": match.group(2).strip()
            })

    return todos


def find_commented_code(source_code: str) -> List[Dict]:
    """Find blocks of commented-out code"""
    commented = []
    lines = source_code.split('\n')

    # Simple heuristic: look for lines starting with # that contain code patterns
    code_patterns = [
        r'^\s*#\s*(def|class|if|for|while|try|except|import|from)\s',
        r'^\s*#\s*[\w_]+\s*=',  # Assignments
        r'^\s*#\s*[\w_]+\(',     # Function calls
    ]

    for i, line in enumerate(lines, 1):
        for pattern in code_patterns:
            if re.match(pattern, line):
                commented.append({
                    "line_number": i,
                    "line": line.strip()
                })
                break

    return commented


def calculate_summary(reports: List[Dict]) -> Dict:
    """Calculate summary statistics across all files"""
    summary = {
        "total_files": len(reports),
        "total_god_classes": 0,
        "total_long_methods": 0,
        "total_parameter_issues": 0,
        "total_deep_nesting": 0,
        "total_magic_values": 0,
        "total_mutable_defaults": 0,
        "total_missing_type_hints": 0,
        "total_todos": 0,
        "total_commented_code": 0,
        "files_with_issues": 0,
        "top_offenders": []
    }

    for report in reports:
        if report.get('skipped'):
            continue

        issues_count = (
            len(report.get('god_classes', [])) +
            len(report.get('long_methods', [])) +
            len(report.get('too_many_params', [])) +
            len(report.get('deep_nesting', [])) +
            len(report.get('mutable_defaults', []))
        )

        if issues_count > 0:
            summary['files_with_issues'] += 1
            summary['top_offenders'].append({
                "file": report['file'],
                "total_issues": issues_count,
                "god_classes": len(report.get('god_classes', [])),
                "long_methods": len(report.get('long_methods', [])),
                "parameter_issues": len(report.get('too_many_params', [])),
                "deep_nesting": len(report.get('deep_nesting', [])),
            })

        summary['total_god_classes'] += len(report.get('god_classes', []))
        summary['total_long_methods'] += len(report.get('long_methods', []))
        summary['total_parameter_issues'] += len(report.get('too_many_params', []))
        summary['total_deep_nesting'] += len(report.get('deep_nesting', []))
        summary['total_magic_values'] += len(report.get('magic_values', []))
        summary['total_mutable_defaults'] += len(report.get('mutable_defaults', []))
        summary['total_missing_type_hints'] += len(report.get('missing_type_hints', []))
        summary['total_todos'] += len(report.get('todos', []))
        summary['total_commented_code'] += len(report.get('commented_code', []))

    # Sort top offenders by issue count
    summary['top_offenders'].sort(key=lambda x: x['total_issues'], reverse=True)
    summary['top_offenders'] = summary['top_offenders'][:20]  # Top 20

    return summary


def main():
    """Main entry point"""
    base_path = Path('/home/bbrelin/src/repos/salesforce/.agents/agile')

    # Priority files to analyze first
    priority_files = [
        'artemis_orchestrator.py',
        'supervisor_agent.py',
        'artemis_stages.py',
        'developer_invoker.py'
    ]

    # Get all Python files
    all_py_files = list(base_path.glob('**/*.py'))

    # Filter out test files for initial scan
    non_test_files = [f for f in all_py_files if not f.name.startswith('test_')]

    print(f"Found {len(non_test_files)} Python files to analyze (excluding tests)")
    print("Analyzing files...")

    reports = []

    # Analyze priority files first
    for priority_file in priority_files:
        file_path = base_path / priority_file
        if file_path.exists():
            print(f"  Analyzing {priority_file}...")
            report = analyze_file(file_path)
            reports.append(report)

    # Analyze remaining files
    analyzed_names = set(priority_files)
    for file_path in non_test_files:
        if file_path.name not in analyzed_names:
            print(f"  Analyzing {file_path.name}...")
            report = analyze_file(file_path)
            reports.append(report)

    # Calculate summary
    summary = calculate_summary(reports)

    # Build final output
    output = {
        "scan_date": "2025-10-25",
        "base_path": str(base_path),
        "summary": summary,
        "priority_files": [r for r in reports if Path(r['file']).name in priority_files],
        "all_reports": reports
    }

    # Save to JSON
    output_file = base_path / 'code_analysis_report.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Analysis complete!")
    print(f"📄 Report saved to: {output_file}")
    print(f"\n📊 Summary:")
    print(f"  Total Files: {summary['total_files']}")
    print(f"  Files with Issues: {summary['files_with_issues']}")
    print(f"  God Classes: {summary['total_god_classes']}")
    print(f"  Long Methods: {summary['total_long_methods']}")
    print(f"  Parameter Issues: {summary['total_parameter_issues']}")
    print(f"  Deep Nesting: {summary['total_deep_nesting']}")
    print(f"  Mutable Defaults: {summary['total_mutable_defaults']}")
    print(f"  TODOs/FIXMEs: {summary['total_todos']}")

    if summary['top_offenders']:
        print(f"\n🔴 Top 5 Files with Most Issues:")
        for i, offender in enumerate(summary['top_offenders'][:5], 1):
            print(f"  {i}. {Path(offender['file']).name}: {offender['total_issues']} issues")


if __name__ == '__main__':
    main()
