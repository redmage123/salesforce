#!/usr/bin/env python3
"""
WCAG 2.1 AA Accessibility Evaluator

Evaluates web implementations for WCAG 2.1 Level AA compliance.
Uses static analysis and pattern matching to detect common accessibility issues.

For production use, integrate with:
- axe-core (Deque Systems)
- pa11y
- Lighthouse accessibility audit
"""

import re
import json
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class AccessibilityIssue:
    """Represents a single accessibility issue"""
    rule: str  # WCAG rule violated (e.g., "1.4.3" for contrast)
    severity: str  # "critical", "serious", "moderate", "minor"
    element: str  # HTML element or selector
    description: str  # Human-readable description
    suggestion: str  # How to fix
    wcag_criterion: str  # WCAG criterion name


class WCAGEvaluator:
    """
    WCAG 2.1 AA Accessibility Evaluator

    Checks for common accessibility violations through static analysis.
    For production, should be supplemented with automated testing tools.
    """

    def __init__(self):
        self.issues: List[AccessibilityIssue] = []

    def evaluate_directory(self, implementation_dir: str) -> Dict:
        """
        Evaluate all HTML/JSX/TSX files in directory for WCAG compliance

        Args:
            implementation_dir: Path to implementation directory

        Returns:
            Dict with evaluation results
        """
        self.issues = []
        impl_path = Path(implementation_dir)

        if not impl_path.exists():
            return self._create_result(skipped=True, reason="Directory not found")

        # Find all relevant files
        html_files = list(impl_path.rglob("*.html"))
        jsx_files = list(impl_path.rglob("*.jsx"))
        tsx_files = list(impl_path.rglob("*.tsx"))
        vue_files = list(impl_path.rglob("*.vue"))

        all_files = html_files + jsx_files + tsx_files + vue_files

        if not all_files:
            return self._create_result(skipped=True, reason="No UI files found")

        # Evaluate each file
        for file_path in all_files:
            self._evaluate_file(file_path)

        return self._create_result()

    def _evaluate_file(self, file_path: Path):
        """Evaluate a single file for accessibility issues"""
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return  # Skip files that can't be read

        # Run all WCAG checks
        self._check_images_alt_text(content, str(file_path))
        self._check_form_labels(content, str(file_path))
        self._check_button_text(content, str(file_path))
        self._check_heading_hierarchy(content, str(file_path))
        self._check_color_contrast(content, str(file_path))
        self._check_keyboard_navigation(content, str(file_path))
        self._check_aria_labels(content, str(file_path))
        self._check_lang_attribute(content, str(file_path))
        self._check_focus_indicators(content, str(file_path))
        self._check_link_text(content, str(file_path))

    def _check_images_alt_text(self, content: str, file_path: str):
        """
        WCAG 1.1.1 (Level A) - Non-text Content
        Images must have alt text
        """
        # Find img tags without alt attribute
        img_pattern = r'<img[^>]*(?<!alt=)[^>]*>'
        matches = re.finditer(img_pattern, content, re.IGNORECASE)

        for match in matches:
            img_tag = match.group(0)
            if 'alt=' not in img_tag.lower():
                self.issues.append(AccessibilityIssue(
                    rule="1.1.1",
                    severity="serious",
                    element=img_tag[:50] + "...",
                    description="Image missing alt attribute",
                    suggestion="Add alt='description' to provide text alternative",
                    wcag_criterion="Non-text Content (Level A)"
                ))

    def _check_form_labels(self, content: str, file_path: str):
        """
        WCAG 1.3.1 (Level A) - Info and Relationships
        WCAG 3.3.2 (Level A) - Labels or Instructions
        Form inputs must have labels
        """
        # Find input elements
        input_pattern = r'<input[^>]*type=["\'](?!hidden)[^"\']*["\'][^>]*>'
        matches = re.finditer(input_pattern, content, re.IGNORECASE)

        for match in matches:
            input_tag = match.group(0)
            # Check if input has id and corresponding label exists
            id_match = re.search(r'id=["\']([^"\']+)["\']', input_tag)
            if id_match:
                input_id = id_match.group(1)
                label_pattern = f'<label[^>]*for=["\']{ input_id}["\']'
                if not re.search(label_pattern, content, re.IGNORECASE):
                    # Check for aria-label or aria-labelledby
                    if 'aria-label' not in input_tag.lower() and 'aria-labelledby' not in input_tag.lower():
                        self.issues.append(AccessibilityIssue(
                            rule="3.3.2",
                            severity="serious",
                            element=input_tag[:50] + "...",
                            description="Form input missing associated label",
                            suggestion="Add <label for='id'> or aria-label attribute",
                            wcag_criterion="Labels or Instructions (Level A)"
                        ))

    def _check_button_text(self, content: str, file_path: str):
        """
        WCAG 4.1.2 (Level A) - Name, Role, Value
        Buttons must have accessible text
        """
        # Find buttons without text content or aria-label
        button_pattern = r'<button[^>]*>(?:\s*)</button>'
        matches = re.finditer(button_pattern, content, re.IGNORECASE)

        for match in matches:
            button_tag = match.group(0)
            if 'aria-label' not in button_tag.lower() and 'aria-labelledby' not in button_tag.lower():
                self.issues.append(AccessibilityIssue(
                    rule="4.1.2",
                    severity="serious",
                    element=button_tag,
                    description="Button has no accessible text",
                    suggestion="Add text content or aria-label to button",
                    wcag_criterion="Name, Role, Value (Level A)"
                ))

    def _check_heading_hierarchy(self, content: str, file_path: str):
        """
        WCAG 1.3.1 (Level A) - Info and Relationships
        Heading levels should not skip
        """
        heading_pattern = r'<h([1-6])[^>]*>'
        matches = re.finditer(heading_pattern, content, re.IGNORECASE)

        heading_levels = [int(m.group(1)) for m in matches]

        if heading_levels:
            # Check if h1 exists
            if 1 not in heading_levels:
                self.issues.append(AccessibilityIssue(
                    rule="1.3.1",
                    severity="moderate",
                    element="Page structure",
                    description="Page missing h1 heading",
                    suggestion="Add h1 as main page heading",
                    wcag_criterion="Info and Relationships (Level A)"
                ))

            # Check for skipped levels
            for i in range(len(heading_levels) - 1):
                if heading_levels[i + 1] - heading_levels[i] > 1:
                    self.issues.append(AccessibilityIssue(
                        rule="1.3.1",
                        severity="moderate",
                        element=f"h{heading_levels[i]} to h{heading_levels[i+1]}",
                        description=f"Heading level skipped from h{heading_levels[i]} to h{heading_levels[i+1]}",
                        suggestion="Use sequential heading levels (h1, h2, h3...)",
                        wcag_criterion="Info and Relationships (Level A)"
                    ))

    def _check_color_contrast(self, content: str, file_path: str):
        """
        WCAG 1.4.3 (Level AA) - Contrast (Minimum)
        Check for potential low contrast patterns
        """
        # Look for inline styles with color (basic check)
        low_contrast_patterns = [
            (r'color:\s*#[a-f0-9]{3,6}.*background.*#[a-f0-9]{3,6}', 'Potential low contrast in inline styles'),
            (r'color:\s*gray.*background.*white', 'Gray on white may have low contrast'),
            (r'color:\s*#ccc', 'Light gray text may have low contrast')
        ]

        for pattern, description in low_contrast_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.issues.append(AccessibilityIssue(
                    rule="1.4.3",
                    severity="serious",
                    element="Color styles",
                    description=description,
                    suggestion="Ensure 4.5:1 contrast ratio for normal text, 3:1 for large text",
                    wcag_criterion="Contrast (Minimum) (Level AA)"
                ))
                break  # Only report once per file

    def _check_keyboard_navigation(self, content: str, file_path: str):
        """
        WCAG 2.1.1 (Level A) - Keyboard
        Interactive elements must be keyboard accessible
        """
        # Check for onClick without keyboard handlers
        onclick_pattern = r'onClick(?!=).*(?!onKeyDown|onKeyPress|onKeyUp)'
        if re.search(onclick_pattern, content):
            # Check if there's any keyboard handler nearby
            if 'onKeyDown' not in content and 'onKeyPress' not in content:
                self.issues.append(AccessibilityIssue(
                    rule="2.1.1",
                    severity="serious",
                    element="Interactive element",
                    description="onClick handler without keyboard equivalent",
                    suggestion="Add onKeyDown or onKeyPress handler for keyboard users",
                    wcag_criterion="Keyboard (Level A)"
                ))

    def _check_aria_labels(self, content: str, file_path: str):
        """
        WCAG 4.1.2 (Level A) - Name, Role, Value
        Check for proper ARIA usage
        """
        # Check for aria-labelledby pointing to non-existent IDs
        aria_labelledby_pattern = r'aria-labelledby=["\']([^"\']+)["\']'
        matches = re.finditer(aria_labelledby_pattern, content, re.IGNORECASE)

        for match in matches:
            label_id = match.group(1)
            id_pattern = f'id=["\']{ label_id}["\']'
            if not re.search(id_pattern, content):
                self.issues.append(AccessibilityIssue(
                    rule="4.1.2",
                    severity="serious",
                    element=f"aria-labelledby='{label_id}'",
                    description=f"aria-labelledby references non-existent id '{label_id}'",
                    suggestion=f"Add element with id='{label_id}' or fix aria-labelledby",
                    wcag_criterion="Name, Role, Value (Level A)"
                ))

    def _check_lang_attribute(self, content: str, file_path: str):
        """
        WCAG 3.1.1 (Level A) - Language of Page
        HTML must have lang attribute
        """
        html_pattern = r'<html[^>]*>'
        match = re.search(html_pattern, content, re.IGNORECASE)

        if match:
            html_tag = match.group(0)
            if 'lang=' not in html_tag.lower():
                self.issues.append(AccessibilityIssue(
                    rule="3.1.1",
                    severity="serious",
                    element="<html>",
                    description="HTML element missing lang attribute",
                    suggestion="Add lang='en' (or appropriate language code) to <html>",
                    wcag_criterion="Language of Page (Level A)"
                ))

    def _check_focus_indicators(self, content: str, file_path: str):
        """
        WCAG 2.4.7 (Level AA) - Focus Visible
        Check for removal of focus outlines
        """
        # Look for outline:none or outline:0 without custom focus styles
        outline_none_pattern = r'(outline\s*:\s*(none|0))|(:focus.*outline\s*:\s*(none|0))'

        if re.search(outline_none_pattern, content, re.IGNORECASE):
            # Check if there's a custom focus style
            custom_focus_pattern = r':focus.*{[^}]*(border|box-shadow|background)[^}]*}'
            if not re.search(custom_focus_pattern, content, re.IGNORECASE):
                self.issues.append(AccessibilityIssue(
                    rule="2.4.7",
                    severity="serious",
                    element="Focus styles",
                    description="Focus outline removed without alternative focus indicator",
                    suggestion="Provide visible focus indicator (border, box-shadow, etc.)",
                    wcag_criterion="Focus Visible (Level AA)"
                ))

    def _check_link_text(self, content: str, file_path: str):
        """
        WCAG 2.4.4 (Level A) - Link Purpose (In Context)
        Links should have descriptive text
        """
        # Find links with generic text
        generic_link_texts = ['click here', 'read more', 'more', 'here', 'link']
        link_pattern = r'<a[^>]*>([^<]+)</a>'
        matches = re.finditer(link_pattern, content, re.IGNORECASE)

        for match in matches:
            link_text = match.group(1).strip().lower()
            if link_text in generic_link_texts:
                self.issues.append(AccessibilityIssue(
                    rule="2.4.4",
                    severity="moderate",
                    element=match.group(0)[:50] + "...",
                    description=f"Link has generic text: '{link_text}'",
                    suggestion="Use descriptive link text that explains destination",
                    wcag_criterion="Link Purpose (In Context) (Level A)"
                ))

    def _create_result(self, skipped: bool = False, reason: str = "") -> Dict:
        """Create evaluation result dictionary"""
        if skipped:
            return {
                "wcag_aa_compliance": None,
                "accessibility_issues": 0,
                "skipped": True,
                "skip_reason": reason,
                "accessibility_details": {
                    "contrast_ratio": "NOT_EVALUATED",
                    "keyboard_navigation": "NOT_EVALUATED",
                    "screen_reader_support": "NOT_EVALUATED",
                    "aria_labels": "NOT_EVALUATED",
                    "focus_indicators": "NOT_EVALUATED"
                },
                "issues": []
            }

        # Categorize issues (Pattern #11: Single-pass categorization for O(n) vs O(4n))
        from collections import defaultdict
        issues_by_severity = defaultdict(list)
        for issue in self.issues:
            issues_by_severity[issue.severity].append(issue)

        critical_issues = issues_by_severity["critical"]
        serious_issues = issues_by_severity["serious"]
        moderate_issues = issues_by_severity["moderate"]
        minor_issues = issues_by_severity["minor"]

        # Determine compliance
        total_issues = len(self.issues)
        wcag_aa_compliance = total_issues == 0 or (len(critical_issues) == 0 and len(serious_issues) == 0)

        # Determine individual check status
        rule_checks = {
            "contrast_ratio": self._has_rule("1.4.3"),
            "keyboard_navigation": self._has_rule("2.1.1"),
            "screen_reader_support": self._has_rule("1.1.1") or self._has_rule("4.1.2"),
            "aria_labels": self._has_rule("4.1.2"),
            "focus_indicators": self._has_rule("2.4.7")
        }

        accessibility_details = {
            key: "FAIL" if has_issue else "PASS"
            for key, has_issue in rule_checks.items()
        }

        return {
            "wcag_aa_compliance": wcag_aa_compliance,
            "accessibility_issues": total_issues,
            "critical_count": len(critical_issues),
            "serious_count": len(serious_issues),
            "moderate_count": len(moderate_issues),
            "minor_count": len(minor_issues),
            "accessibility_details": accessibility_details,
            "issues": [asdict(issue) for issue in self.issues]
        }

    def _has_rule(self, rule: str) -> bool:
        """Check if any issue matches the given WCAG rule"""
        return any(issue.rule == rule for issue in self.issues)
