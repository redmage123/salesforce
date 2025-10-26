#!/usr/bin/env python3
"""
Exception Handling Analyzer for Artemis Stage Files

Analyzes stage files for:
1. Methods that can raise exceptions but lack @wrap_exception decorator
2. Bare except clauses (except: or except Exception:)
3. Silent failures (pass in except blocks)
"""

import ast
import json
from pathlib import Path
from typing import Dict, List, Set


class ExceptionHandlingAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze exception handling patterns"""

    def __init__(self, filename: str):
        self.filename = filename
        self.current_class = None
        self.current_method = None
        self.method_decorators = {}

        # Results
        self.methods_without_wrap = []
        self.bare_excepts = []
        self.silent_failures = []
        self.all_methods = []
        self.protected_methods = []

    def visit_ClassDef(self, node):
        """Track current class"""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        """Analyze function/method definitions"""
        old_method = self.current_method
        self.current_method = node.name

        # Only analyze methods (not module-level functions)
        if self.current_class:
            method_key = f"{self.current_class}.{node.name}"

            # Track all methods
            self.all_methods.append(f"{method_key}:{node.lineno}")

            # Check decorators
            has_wrap_exception = any(
                self._is_wrap_exception_decorator(dec)
                for dec in node.decorator_list
            )

            if has_wrap_exception:
                self.protected_methods.append(method_key)

            self.method_decorators[method_key] = has_wrap_exception

            # Check if method can raise exceptions but lacks decorator
            can_raise = self._can_raise_exceptions(node)
            is_private = node.name.startswith('_')
            is_init = node.name in ('__init__', 'get_stage_name')

            # Public methods that can raise exceptions should have @wrap_exception
            if can_raise and not has_wrap_exception and not is_private and not is_init:
                self.methods_without_wrap.append(f"{method_key}:{node.lineno}")

        self.generic_visit(node)
        self.current_method = old_method

    def visit_ExceptHandler(self, node):
        """Analyze except blocks"""
        # Check for bare except
        if node.type is None:
            # except:
            self.bare_excepts.append(node.lineno)
        elif isinstance(node.type, ast.Name) and node.type.id == 'Exception':
            # except Exception:
            self.bare_excepts.append(node.lineno)

        # Check for silent failure (pass in except block)
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.silent_failures.append(node.lineno)

        self.generic_visit(node)

    def _is_wrap_exception_decorator(self, decorator) -> bool:
        """Check if decorator is @wrap_exception"""
        if isinstance(decorator, ast.Name):
            return decorator.id == 'wrap_exception'
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id == 'wrap_exception'
        return False

    def _can_raise_exceptions(self, node) -> bool:
        """Check if method can raise exceptions (has try/except, raise, or calls methods)"""
        for child in ast.walk(node):
            # Has try/except blocks
            if isinstance(child, ast.Try):
                return True
            # Has raise statements
            if isinstance(child, ast.Raise):
                return True
            # Calls wrap_exception (explicit exception handling)
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == 'wrap_exception':
                    return True
        return False


def analyze_file(file_path: Path) -> Dict:
    """Analyze a single file for exception handling issues"""
    try:
        with open(file_path, 'r') as f:
            source = f.read()

        tree = ast.parse(source, filename=str(file_path))
        analyzer = ExceptionHandlingAnalyzer(str(file_path))
        analyzer.visit(tree)

        total_methods = len(analyzer.all_methods)
        protected_methods = len(analyzer.protected_methods)
        coverage_percent = round((protected_methods / total_methods * 100) if total_methods > 0 else 0, 1)

        return {
            "file": file_path.name,
            "missing_wrap_exception": analyzer.methods_without_wrap,
            "bare_excepts": analyzer.bare_excepts,
            "silent_failures": analyzer.silent_failures,
            "total_methods": total_methods,
            "protected_methods": protected_methods,
            "coverage_percent": coverage_percent,
            "analysis_success": True
        }
    except Exception as e:
        return {
            "file": file_path.name,
            "error": str(e),
            "analysis_success": False
        }


def main():
    """Analyze all stage files"""
    base_dir = Path("/home/bbrelin/src/repos/salesforce/.agents/agile")

    stage_files = [
        "artemis_stages.py",
        "code_review_stage.py",
        "arbitration_stage.py",
        "sprint_planning_stage.py",
        "project_review_stage.py",
        "uiux_stage.py",
        "requirements_stage.py",
        "bdd_scenario_generation_stage.py",
        "bdd_test_generation_stage.py",
        "bdd_validation_stage.py"
    ]

    results = []

    for filename in stage_files:
        file_path = base_dir / filename
        if file_path.exists():
            print(f"Analyzing {filename}...")
            result = analyze_file(file_path)
            results.append(result)
        else:
            print(f"File not found: {filename}")
            results.append({
                "file": filename,
                "error": "File not found",
                "analysis_success": False
            })

    # Output JSON report
    output_file = base_dir / "exception_handling_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Analysis complete. Report saved to: {output_file}")

    # Print summary
    print("\n" + "="*80)
    print("EXCEPTION HANDLING ANALYSIS SUMMARY")
    print("="*80)

    for result in results:
        if result.get('analysis_success'):
            print(f"\n📄 {result['file']}")
            print(f"   Total Methods: {result['total_methods']}")
            print(f"   Protected Methods: {result['protected_methods']}")
            print(f"   Coverage: {result['coverage_percent']}%")
            print(f"   Missing @wrap_exception: {len(result['missing_wrap_exception'])}")
            print(f"   Bare except clauses: {len(result['bare_excepts'])}")
            print(f"   Silent failures: {len(result['silent_failures'])}")
        else:
            print(f"\n❌ {result['file']}: {result.get('error', 'Unknown error')}")


if __name__ == '__main__':
    main()
