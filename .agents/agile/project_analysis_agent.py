#!/usr/bin/env python3
"""
Project Analysis Agent (SOLID-Compliant)

Analyzes tasks BEFORE implementation across 8 dimensions to identify
issues, suggest improvements, and get user approval.

SOLID Principles Applied:
- Single Responsibility: Each analyzer handles ONE dimension only
- Open/Closed: Can add new analyzers without modifying core
- Liskov Substitution: All analyzers implement DimensionAnalyzer interface
- Interface Segregation: Minimal, focused interfaces
- Dependency Inversion: Depends on abstractions (DimensionAnalyzer)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================

class Severity(Enum):
    """Issue severity levels"""
    CRITICAL = "CRITICAL"  # Must address before implementation
    HIGH = "HIGH"          # Strongly recommended
    MEDIUM = "MEDIUM"      # Nice to have


@dataclass
class Issue:
    """Represents an identified issue"""
    category: str
    severity: Severity
    description: str
    impact: str
    suggestion: str
    reasoning: str
    user_approval_needed: bool


@dataclass
class AnalysisResult:
    """Result from analyzing one dimension"""
    dimension: str
    issues: List[Issue]
    recommendations: List[str]


# ============================================================================
# INTERFACES (Interface Segregation Principle)
# ============================================================================

class DimensionAnalyzer(ABC):
    """
    Abstract base class for dimension analyzers

    Each analyzer implements ONE dimension analysis (SRP)
    """

    @abstractmethod
    def analyze(self, card: Dict, context: Dict) -> AnalysisResult:
        """Analyze task in this dimension"""
        pass

    @abstractmethod
    def get_dimension_name(self) -> str:
        """Return dimension name"""
        pass


# ============================================================================
# DIMENSION ANALYZERS (Single Responsibility Principle)
# ============================================================================

class ScopeAnalyzer(DimensionAnalyzer):
    """Single Responsibility: Analyze scope & requirements"""

    def analyze(self, card: Dict, context: Dict) -> AnalysisResult:
        issues = []
        recommendations = []

        # Check if description is clear
        description = card.get('description', '')
        if not description or len(description) < 20:
            issues.append(Issue(
                category="Scope & Requirements",
                severity=Severity.HIGH,
                description="Task description is too vague or missing",
                impact="Implementation may not meet actual requirements",
                suggestion="Add detailed description explaining what needs to be done and why",
                reasoning="Clear requirements prevent rework and misunderstandings",
                user_approval_needed=True
            ))

        # Check for acceptance criteria
        acceptance_criteria = card.get('acceptance_criteria', [])
        if not acceptance_criteria:
            issues.append(Issue(
                category="Scope & Requirements",
                severity=Severity.HIGH,
                description="No acceptance criteria defined",
                impact="No clear definition of 'done'",
                suggestion="Add measurable acceptance criteria (Given-When-Then format)",
                reasoning="Acceptance criteria define success and enable proper testing",
                user_approval_needed=True
            ))

        recommendations.append("Define clear success metrics")

        return AnalysisResult(
            dimension="Scope & Requirements",
            issues=issues,
            recommendations=recommendations
        )

    def get_dimension_name(self) -> str:
        return "scope"


class SecurityAnalyzer(DimensionAnalyzer):
    """Single Responsibility: Analyze security concerns"""

    def analyze(self, card: Dict, context: Dict) -> AnalysisResult:
        issues = []
        recommendations = []

        title = card.get('title', '').lower()
        description = card.get('description', '').lower()
        combined = f"{title} {description}"

        # Check for authentication/authorization
        if any(kw in combined for kw in ['auth', 'login', 'user', 'password', 'token']):
            issues.append(Issue(
                category="Security",
                severity=Severity.CRITICAL,
                description="Task involves authentication/authorization - security review needed",
                impact="Potential security vulnerabilities (auth bypass, token leaks)",
                suggestion="Add security requirements: token encryption, session management, OWASP compliance",
                reasoning="Authentication bugs are critical security vulnerabilities",
                user_approval_needed=True
            ))

        # Check for data storage
        if any(kw in combined for kw in ['store', 'save', 'database', 'data']):
            issues.append(Issue(
                category="Security",
                severity=Severity.HIGH,
                description="Task involves data storage - encryption and validation needed",
                impact="Data exposure, SQL injection, insecure storage",
                suggestion="Add requirements: input validation, parameterized queries, encryption at rest",
                reasoning="Data storage requires protection against common attacks",
                user_approval_needed=True
            ))

        # Check for API endpoints
        if any(kw in combined for kw in ['api', 'endpoint', 'rest', 'graphql']):
            recommendations.append("Add rate limiting and authentication to API endpoints")
            recommendations.append("Implement input validation and sanitization")

        return AnalysisResult(
            dimension="Security",
            issues=issues,
            recommendations=recommendations
        )

    def get_dimension_name(self) -> str:
        return "security"


class PerformanceAnalyzer(DimensionAnalyzer):
    """Single Responsibility: Analyze scalability & performance"""

    def analyze(self, card: Dict, context: Dict) -> AnalysisResult:
        issues = []
        recommendations = []

        description = card.get('description', '').lower()

        # Check for performance requirements
        if any(kw in description for kw in ['dashboard', 'report', 'analytics', 'search']):
            issues.append(Issue(
                category="Scalability & Performance",
                severity=Severity.MEDIUM,
                description="No performance requirements defined",
                impact="Slow user experience under load",
                suggestion="Add performance target: <200ms response time, <2s page load",
                reasoning="Performance expectations prevent slowdowns in production",
                user_approval_needed=False
            ))

        # Check for caching needs
        if any(kw in description for kw in ['report', 'analytics', 'dashboard']):
            recommendations.append("Consider caching strategy for expensive queries")

        # Check for pagination
        if any(kw in description for kw in ['list', 'search', 'display']):
            recommendations.append("Implement pagination for large result sets")

        return AnalysisResult(
            dimension="Scalability & Performance",
            issues=issues,
            recommendations=recommendations
        )

    def get_dimension_name(self) -> str:
        return "performance"


class TestingAnalyzer(DimensionAnalyzer):
    """Single Responsibility: Analyze testing strategy"""

    def analyze(self, card: Dict, context: Dict) -> AnalysisResult:
        issues = []
        recommendations = []

        # Always recommend TDD
        recommendations.append("Use TDD: Write tests BEFORE implementation (Red-Green-Refactor)")
        recommendations.append("Target 85%+ test coverage (unit + integration + acceptance)")

        # Check for testing strategy
        description = card.get('description', '')
        if 'test' not in description.lower():
            issues.append(Issue(
                category="Testing Strategy",
                severity=Severity.HIGH,
                description="No testing approach mentioned in requirements",
                impact="Untested code leads to bugs in production",
                suggestion="Add testing requirements: unit tests (85%), integration tests, E2E tests",
                reasoning="TDD and comprehensive tests ensure quality and prevent regressions",
                user_approval_needed=True
            ))

        return AnalysisResult(
            dimension="Testing Strategy",
            issues=issues,
            recommendations=recommendations
        )

    def get_dimension_name(self) -> str:
        return "testing"


class ErrorHandlingAnalyzer(DimensionAnalyzer):
    """Single Responsibility: Analyze error handling & edge cases"""

    def analyze(self, card: Dict, context: Dict) -> AnalysisResult:
        issues = []
        recommendations = []

        description = card.get('description', '').lower()

        # Check for error handling requirements
        if 'error' not in description and 'fail' not in description:
            issues.append(Issue(
                category="Error Handling",
                severity=Severity.MEDIUM,
                description="No error handling strategy defined",
                impact="Poor user experience when things go wrong",
                suggestion="Add error handling: try-catch blocks, user-friendly messages, logging",
                reasoning="Graceful error handling improves user experience and debuggability",
                user_approval_needed=False
            ))

        recommendations.append("Define failure scenarios and recovery strategies")
        recommendations.append("Add logging for debugging and monitoring")

        return AnalysisResult(
            dimension="Error Handling & Edge Cases",
            issues=issues,
            recommendations=recommendations
        )

    def get_dimension_name(self) -> str:
        return "error_handling"


# ============================================================================
# PROJECT ANALYSIS ENGINE
# ============================================================================

class ProjectAnalysisEngine:
    """
    Coordinates analysis across all dimensions

    Single Responsibility: Orchestrate analyzers
    Open/Closed: Can add new analyzers without modification
    Dependency Inversion: Depends on DimensionAnalyzer abstraction
    """

    def __init__(self, analyzers: Optional[List[DimensionAnalyzer]] = None):
        """
        Initialize with dependency injection

        Args:
            analyzers: List of dimension analyzers (injected)
        """
        if analyzers is None:
            # Default analyzers
            self.analyzers = [
                ScopeAnalyzer(),
                SecurityAnalyzer(),
                PerformanceAnalyzer(),
                TestingAnalyzer(),
                ErrorHandlingAnalyzer()
            ]
        else:
            self.analyzers = analyzers

    def analyze_task(self, card: Dict, context: Dict) -> Dict:
        """
        Analyze task across all dimensions

        Args:
            card: Kanban card with task details
            context: Pipeline context (RAG recommendations, etc.)

        Returns:
            Dict with complete analysis results
        """
        results = []
        all_issues = []

        # Run each analyzer (Open/Closed: can add analyzers without changing this)
        for analyzer in self.analyzers:
            result = analyzer.analyze(card, context)
            results.append(result)
            all_issues.extend(result.issues)

        # Categorize issues by severity
        critical_issues = [i for i in all_issues if i.severity == Severity.CRITICAL]
        high_issues = [i for i in all_issues if i.severity == Severity.HIGH]
        medium_issues = [i for i in all_issues if i.severity == Severity.MEDIUM]

        # Generate summary
        summary = {
            "total_issues": len(all_issues),
            "critical_count": len(critical_issues),
            "high_count": len(high_issues),
            "medium_count": len(medium_issues),
            "dimensions_analyzed": len(self.analyzers),
            "results": results,
            "critical_issues": critical_issues,
            "high_issues": high_issues,
            "medium_issues": medium_issues
        }

        return summary


# ============================================================================
# USER APPROVAL HANDLER
# ============================================================================

class ApprovalOptions(Enum):
    """User approval options"""
    APPROVE_ALL = "approve_all"
    APPROVE_CRITICAL = "approve_critical"
    CUSTOM = "custom"
    REJECT = "reject"
    MODIFY = "modify"


class UserApprovalHandler:
    """
    Single Responsibility: Handle user approval flow

    Presents findings to user and collects approval decision
    """

    def present_findings(self, analysis: Dict) -> str:
        """
        Format analysis results for user presentation

        Args:
            analysis: Analysis summary from ProjectAnalysisEngine

        Returns:
            Formatted string for display
        """
        output = []
        output.append("=" * 60)
        output.append("PROJECT ANALYSIS COMPLETE")
        output.append("=" * 60)
        output.append("")
        output.append("SUMMARY:")
        output.append(f"  ⚠️  {analysis['critical_count']} CRITICAL issues found")
        output.append(f"  ⚠️  {analysis['high_count']} HIGH-PRIORITY improvements")
        output.append(f"  💡 {analysis['medium_count']} MEDIUM-PRIORITY enhancements")
        output.append("")

        # Show critical issues
        if analysis['critical_issues']:
            output.append("CRITICAL ISSUES (Must Address):")
            for i, issue in enumerate(analysis['critical_issues'], 1):
                output.append(f"{i}. [{issue.category}] {issue.description}")
                output.append(f"   → {issue.suggestion}")
                output.append(f"   Impact: {issue.impact}")
                output.append("")

        # Show high priority
        if analysis['high_issues']:
            output.append("HIGH-PRIORITY IMPROVEMENTS:")
            for i, issue in enumerate(analysis['high_issues'], 1):
                output.append(f"{i}. [{issue.category}] {issue.description}")
                output.append(f"   → {issue.suggestion}")
                output.append("")

        output.append("=" * 60)
        output.append("USER APPROVAL REQUIRED")
        output.append("=" * 60)
        output.append("")
        output.append("What would you like to do?")
        output.append("1. APPROVE ALL - Accept all critical and high-priority changes")
        output.append("2. APPROVE CRITICAL ONLY - Accept only critical security/compliance fixes")
        output.append("3. CUSTOM - Let me choose which suggestions to approve")
        output.append("4. REJECT - Proceed with original task as-is")
        output.append("5. MODIFY - I want to suggest different changes")
        output.append("")

        return "\n".join(output)

    def get_approval_decision(self, analysis: Dict, user_choice: str) -> Dict:
        """
        Process user's approval decision

        Args:
            analysis: Analysis summary
            user_choice: User's selection (1-5)

        Returns:
            Dict with approved changes
        """
        if user_choice == "1":  # APPROVE ALL
            approved_issues = analysis['critical_issues'] + analysis['high_issues']
        elif user_choice == "2":  # APPROVE CRITICAL ONLY
            approved_issues = analysis['critical_issues']
        elif user_choice == "4":  # REJECT
            approved_issues = []
        else:
            # CUSTOM or MODIFY would require interactive flow
            approved_issues = analysis['critical_issues']  # Default to critical

        return {
            "approved": len(approved_issues) > 0,
            "approved_issues": approved_issues,
            "approved_count": len(approved_issues)
        }


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def analyze_project(card: Dict, context: Optional[Dict] = None) -> Dict:
    """
    Convenience function to analyze a project

    Args:
        card: Kanban card with task details
        context: Optional pipeline context

    Returns:
        Complete analysis results
    """
    context = context or {}
    engine = ProjectAnalysisEngine()
    return engine.analyze_task(card, context)


if __name__ == "__main__":
    # Example usage
    print("Project Analysis Agent - Example")
    print("=" * 60)

    # Sample task
    card = {
        "card_id": "test-001",
        "title": "Add user authentication",
        "description": "Add login functionality",
        "priority": "high",
        "points": 8
    }

    # Run analysis
    analysis = analyze_project(card)

    # Present findings
    handler = UserApprovalHandler()
    presentation = handler.present_findings(analysis)
    print(presentation)
