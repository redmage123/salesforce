#!/usr/bin/env python3
"""
Project Analysis Agent (SOLID-Compliant)

Analyzes tasks BEFORE implementation across 8 dimensions to identify
issues, suggest improvements, and get user approval.

Now enhanced with LLM-powered analysis using DEPTH framework:
- D: Define Multiple Perspectives (security, performance, testing, architecture)
- E: Establish Clear Success Metrics (severity levels, approval criteria)
- P: Provide Context Layers (card details, RAG context, historical data)
- T: Task Breakdown (dimension-by-dimension analysis)
- H: Human Feedback Loop (self-critique and validation)

SOLID Principles Applied:
- Single Responsibility: Each analyzer handles ONE dimension only
- Open/Closed: Can add new analyzers without modifying core
- Liskov Substitution: All analyzers implement DimensionAnalyzer interface
- Interface Segregation: Minimal, focused interfaces
- Dependency Inversion: Depends on abstractions (DimensionAnalyzer)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
from environment_context import get_environment_context_short
from debug_mixin import DebugMixin

# Import AIQueryService for centralized KG→RAG→LLM pipeline
try:
    from ai_query_service import (
        AIQueryService,
        create_ai_query_service,
        QueryType,
        AIQueryResult
    )
    AI_QUERY_SERVICE_AVAILABLE = True
except ImportError:
    AI_QUERY_SERVICE_AVAILABLE = False


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


class LLMPoweredAnalyzer(DimensionAnalyzer):
    """
    LLM-Powered Comprehensive Analyzer using DEPTH Framework

    Uses LLM to perform intelligent, context-aware analysis across all dimensions.
    Complements rule-based analyzers with deeper insights.

    Now uses AIQueryService for KG-First approach (token savings ~750 tokens/task).
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        config: Optional[Any] = None,
        ai_service: Optional['AIQueryService'] = None
    ):
        """
        Initialize with LLM client

        Args:
            llm_client: LLM client instance (LLMClientInterface)
            config: Configuration agent for settings
            ai_service: AI Query Service for KG-First queries (optional)
        """
        self.llm_client = llm_client
        self.config = config
        self.ai_service = ai_service

    def analyze(self, card: Dict, context: Dict) -> AnalysisResult:
        """
        Analyze task using LLM with DEPTH framework

        Now uses AIQueryService for KG-First approach to reduce token usage.

        Args:
            card: Kanban card with task details
            context: Pipeline context (RAG recommendations, etc.)

        Returns:
            AnalysisResult with LLM-generated insights
        """
        if not self.ai_service and not self.llm_client:
            # Fallback to empty result if no LLM available
            return AnalysisResult(
                dimension="LLM-Powered Analysis",
                issues=[],
                recommendations=["LLM client not available - using rule-based analysis only"]
            )

        # Build DEPTH-conforming prompt
        system_message = self._build_system_message()
        user_message = self._build_user_message(card, context)
        full_prompt = f"{system_message}\n\n{user_message}"

        try:
            # Use AIQueryService if available (KG-First approach)
            if self.ai_service:
                keywords = card.get('title', '').lower().split()[:3]
                result = self.ai_service.query(
                    query_type=QueryType.PROJECT_ANALYSIS,
                    prompt=full_prompt,
                    kg_query_params={
                        'task_title': card.get('title', ''),
                        'keywords': keywords
                    },
                    temperature=0.3,  # Lower temperature for analytical consistency
                    max_tokens=2000
                )

                if not result.success:
                    raise Exception(f"AI query failed: {result.error}")

                response = result.llm_response.content
            else:
                # Fallback to direct LLM call
                response = self.llm_client.generate_text(
                    system_message=system_message,
                    user_message=user_message,
                    temperature=0.3,
                    max_tokens=2000
                )

            # Parse LLM response (expecting JSON)
            analysis_data = self._parse_llm_response(response)

            # Convert to AnalysisResult
            issues = self._extract_issues(analysis_data)
            recommendations = analysis_data.get("recommendations", [])

            return AnalysisResult(
                dimension="LLM-Powered Comprehensive Analysis",
                issues=issues,
                recommendations=recommendations
            )

        except Exception as e:
            # Fallback on error
            return AnalysisResult(
                dimension="LLM-Powered Analysis",
                issues=[],
                recommendations=[f"LLM analysis failed: {str(e)}"]
            )

    def get_dimension_name(self) -> str:
        return "llm_powered"

    def _build_system_message(self) -> str:
        """Build system message with DEPTH framework"""
        return """You are an expert Project Analysis AI specializing in identifying issues before implementation.

**Multiple Expert Perspectives:**
Apply the viewpoints of:
- Senior Software Architect (15+ years) - focusing on architectural soundness and scalability
- Security Engineer - identifying potential vulnerabilities and compliance issues
- QA Lead - considering testability, edge cases, and quality assurance
- DevOps Engineer - evaluating deployment, monitoring, and operational concerns
- UX Designer - assessing user experience and accessibility requirements

**Success Criteria:**
Your analysis MUST:
1. Identify CRITICAL issues (security, compliance, data loss risks)
2. Highlight HIGH-priority improvements (testing, performance, scalability)
3. Suggest MEDIUM-priority enhancements (code quality, maintainability)
4. Provide specific, actionable recommendations (not generic advice)
5. Return valid JSON matching the expected schema
6. Avoid AI clichés like "robust", "delve", "leverage"

**Self-Validation:**
Before responding, ask yourself:
1. Did I identify all security vulnerabilities?
2. Are my recommendations specific and actionable?
3. Did I consider all edge cases and failure scenarios?
4. Is my JSON properly formatted?
5. Did I avoid generic advice and AI clichés?

If any answer is NO, revise your analysis."""

    def _build_user_message(self, card: Dict, context: Dict) -> str:
        """Build user message with context layers"""
        card_summary = f"""
**Task Title:** {card.get('title', 'Unknown')}
**Description:** {card.get('description', 'No description provided')}
**Priority:** {card.get('priority', 'Not set')}
**Story Points:** {card.get('points', 'Not estimated')}
**Acceptance Criteria:** {card.get('acceptance_criteria', [])}
"""

        context_summary = ""
        if context:
            rag_recommendations = context.get('rag_recommendations', [])
            # Handle both dict and list formats
            if isinstance(rag_recommendations, dict):
                # Convert dict values to list
                rag_list = list(rag_recommendations.values()) if rag_recommendations else []
            elif isinstance(rag_recommendations, list):
                rag_list = rag_recommendations
            else:
                rag_list = []

            if rag_list:
                context_summary = f"\n**Historical Context (RAG):**\n"
                for rec in rag_list[:3]:  # Top 3 recommendations
                    context_summary += f"- {rec}\n"

        return f"""Analyze the following task BEFORE implementation across these dimensions:

1. **Scope & Requirements**: Are requirements clear and complete?
2. **Security**: Any security vulnerabilities or compliance issues?
3. **Performance & Scalability**: Performance concerns or bottlenecks?
4. **Testing Strategy**: Is testing approach comprehensive?
5. **Error Handling**: Are edge cases and failures addressed?
6. **Architecture**: Architectural concerns or design issues?
7. **Dependencies**: External dependencies or integration risks?
8. **Accessibility**: WCAG compliance and UX considerations?

{card_summary}
{context_summary}

{get_environment_context_short()}

**Task Breakdown:**
1. Read the task requirements carefully
2. Analyze each dimension systematically
3. Identify issues categorized by severity (CRITICAL/HIGH/MEDIUM)
4. Provide specific, actionable recommendations
5. Self-validate your analysis before responding

**Response Format (JSON only):**
{{
  "issues": [
    {{
      "category": "Security|Performance|Testing|Architecture|Dependencies|Accessibility|Scope|Error Handling",
      "severity": "CRITICAL|HIGH|MEDIUM",
      "description": "Brief issue description",
      "impact": "What happens if not addressed",
      "suggestion": "Specific actionable fix",
      "reasoning": "Why this matters",
      "user_approval_needed": true|false
    }}
  ],
  "recommendations": [
    "Specific recommendation 1",
    "Specific recommendation 2"
  ],
  "overall_assessment": "Brief 1-2 sentence summary",
  "recommendation_action": "APPROVE_ALL|APPROVE_CRITICAL|REJECT"
}}

Return ONLY valid JSON, no markdown, no explanations."""

    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response JSON"""
        # Strip markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            # Fallback: try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

    def _extract_issues(self, analysis_data: Dict) -> List[Issue]:
        """Extract issues from LLM analysis data"""
        issues = []
        for issue_data in analysis_data.get("issues", []):
            severity_str = issue_data.get("severity", "MEDIUM").upper()
            severity = Severity[severity_str] if severity_str in Severity.__members__ else Severity.MEDIUM

            issues.append(Issue(
                category=issue_data.get("category", "General"),
                severity=severity,
                description=issue_data.get("description", ""),
                impact=issue_data.get("impact", ""),
                suggestion=issue_data.get("suggestion", ""),
                reasoning=issue_data.get("reasoning", ""),
                user_approval_needed=issue_data.get("user_approval_needed", False)
            ))

        return issues


# ============================================================================
# PROJECT ANALYSIS ENGINE
# ============================================================================

class ProjectAnalysisEngine(DebugMixin):
    """
    Coordinates analysis across all dimensions

    Single Responsibility: Orchestrate analyzers
    Open/Closed: Can add new analyzers without modification
    Dependency Inversion: Depends on DimensionAnalyzer abstraction
    """

    def __init__(
        self,
        analyzers: Optional[List[DimensionAnalyzer]] = None,
        llm_client: Optional[Any] = None,
        config: Optional[Any] = None,
        enable_llm_analysis: bool = True,
        ai_service: Optional['AIQueryService'] = None,
        rag: Optional[Any] = None
    ):
        """
        Initialize with dependency injection

        Args:
            analyzers: List of dimension analyzers (injected)
            llm_client: LLM client for AI-powered analysis
            config: Configuration agent
            enable_llm_analysis: Enable LLM-powered analysis (default: True)
            ai_service: AI Query Service for KG-First queries (optional)
            rag: RAG agent for pattern retrieval (optional)
        """
        DebugMixin.__init__(self, component_name="project_analysis")
        # Initialize AI Query Service if not provided
        if not ai_service and llm_client and AI_QUERY_SERVICE_AVAILABLE:
            try:
                ai_service = create_ai_query_service(
                    llm_client=llm_client,
                    rag=rag,
                    logger=None,
                    verbose=False
                )
            except Exception:
                ai_service = None

        self.ai_service = ai_service

        if analyzers is None:
            # Default analyzers (rule-based)
            self.analyzers = [
                ScopeAnalyzer(),
                SecurityAnalyzer(),
                PerformanceAnalyzer(),
                TestingAnalyzer(),
                ErrorHandlingAnalyzer()
            ]

            # Add LLM-powered analyzer if available and enabled
            if enable_llm_analysis and llm_client:
                self.analyzers.append(LLMPoweredAnalyzer(llm_client, config, ai_service))
        else:
            self.analyzers = analyzers

        self.llm_client = llm_client
        self.config = config
        self.debug_log("ProjectAnalysisEngine initialized",
                      analyzer_count=len(self.analyzers),
                      llm_enabled=enable_llm_analysis)

    def analyze_task(self, card: Dict, context: Dict) -> Dict:
        """
        Analyze task across all dimensions

        Args:
            card: Kanban card with task details
            context: Pipeline context (RAG recommendations, etc.)

        Returns:
            Dict with complete analysis results
        """
        self.debug_trace("analyze_task", task_title=card.get('title', 'Unknown'))
        results = []
        all_issues = []

        # Run each analyzer (Open/Closed: can add analyzers without changing this)
        for analyzer in self.analyzers:
            result = analyzer.analyze(card, context)
            results.append(result)
            all_issues.extend(result.issues)

        # Categorize issues by severity (Performance: Single-pass O(n) vs O(3n))
        from collections import defaultdict
        issues_by_severity = defaultdict(list)
        for issue in all_issues:
            issues_by_severity[issue.severity].append(issue)

        critical_issues = issues_by_severity[Severity.CRITICAL]
        high_issues = issues_by_severity[Severity.HIGH]
        medium_issues = issues_by_severity[Severity.MEDIUM]

        # Generate recommendation based on severity
        # Recommend REJECT if any critical issues, otherwise APPROVE_ALL
        if critical_issues:
            recommendation = "REJECT"
            recommendation_reason = f"Found {len(critical_issues)} CRITICAL issues that must be fixed"
        elif len(high_issues) > 5:
            recommendation = "APPROVE_CRITICAL"
            recommendation_reason = f"Found {len(high_issues)} HIGH-priority issues - consider fixing"
        else:
            recommendation = "APPROVE_ALL"
            recommendation_reason = f"No critical issues found - {len(high_issues)} high, {len(medium_issues)} medium priority improvements suggested"

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
            "medium_issues": medium_issues,
            "recommendation": recommendation,  # Agent's recommendation
            "recommendation_reason": recommendation_reason
        }

        self.debug_dump_if_enabled("analysis_summary", "Analysis Summary", {
            "total_issues": len(all_issues),
            "critical": len(critical_issues),
            "high": len(high_issues),
            "recommendation": recommendation
        })

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
