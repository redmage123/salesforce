#!/usr/bin/env python3
"""
Requirements Data Models

Structured data models for parsed user requirements.
Converts free-form text into structured YAML/JSON format.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum
import yaml
import json

from artemis_exceptions import (
    RequirementsExportError,
    RequirementsValidationError,
    wrap_exception
)


class Priority(Enum):
    """Requirement priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NICE_TO_HAVE = "nice_to_have"


class RequirementType(Enum):
    """Types of requirements"""
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    USABILITY = "usability"
    ACCESSIBILITY = "accessibility"
    INTEGRATION = "integration"
    DATA = "data"
    BUSINESS = "business"


@dataclass
class Stakeholder:
    """Stakeholder information"""
    name: str
    role: str
    contact: Optional[str] = None
    concerns: List[str] = field(default_factory=list)


@dataclass
class Constraint:
    """Project constraint"""
    type: str  # technical, business, regulatory, timeline, budget
    description: str
    impact: str  # high, medium, low
    mitigation: Optional[str] = None


@dataclass
class Assumption:
    """Project assumption"""
    description: str
    risk_if_false: str
    validation_needed: bool = True


@dataclass
class FunctionalRequirement:
    """Individual functional requirement"""
    id: str  # REQ-F-001, REQ-F-002, etc.
    title: str
    description: str
    priority: Priority
    user_story: Optional[str] = None  # As a [user], I want [goal], so that [benefit]
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # IDs of dependent requirements
    estimated_effort: Optional[str] = None  # small, medium, large, xl
    tags: List[str] = field(default_factory=list)


@dataclass
class NonFunctionalRequirement:
    """Non-functional requirement (performance, security, etc.)"""
    id: str  # REQ-NF-001, REQ-NF-002, etc.
    title: str
    description: str
    type: RequirementType
    priority: Priority
    metric: Optional[str] = None  # How to measure compliance
    target: Optional[str] = None  # Target value (e.g., "< 200ms", "> 99.9% uptime")
    acceptance_criteria: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class UseCase:
    """Use case scenario"""
    id: str  # UC-001, UC-002, etc.
    title: str
    actor: str  # Who performs this use case
    preconditions: List[str] = field(default_factory=list)
    main_flow: List[str] = field(default_factory=list)
    alternate_flows: Dict[str, List[str]] = field(default_factory=dict)
    postconditions: List[str] = field(default_factory=list)
    related_requirements: List[str] = field(default_factory=list)


@dataclass
class DataRequirement:
    """Data and data model requirement"""
    id: str  # REQ-D-001, REQ-D-002, etc.
    entity_name: str
    description: str
    attributes: List[Dict[str, str]] = field(default_factory=list)  # [{name, type, required}]
    relationships: List[str] = field(default_factory=list)
    volume: Optional[str] = None  # Expected data volume
    retention: Optional[str] = None  # Data retention policy
    compliance: List[str] = field(default_factory=list)  # GDPR, CCPA, etc.


@dataclass
class IntegrationRequirement:
    """External system integration requirement"""
    id: str  # REQ-I-001, REQ-I-002, etc.
    system_name: str
    description: str
    direction: str  # inbound, outbound, bidirectional
    protocol: Optional[str] = None  # REST, GraphQL, gRPC, SOAP, etc.
    data_format: Optional[str] = None  # JSON, XML, CSV, etc.
    frequency: Optional[str] = None  # real-time, batch, scheduled
    authentication: Optional[str] = None  # OAuth, API key, etc.
    sla: Optional[str] = None


@dataclass
class StructuredRequirements:
    """
    Complete structured requirements document

    This is the output format from the requirements parser.
    Architects can use this to generate ADRs.
    """
    # Metadata
    project_name: str
    version: str = "1.0"
    created_date: Optional[str] = None
    last_updated: Optional[str] = None

    # Overview
    executive_summary: Optional[str] = None
    business_goals: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)

    # Stakeholders
    stakeholders: List[Stakeholder] = field(default_factory=list)

    # Constraints and Assumptions
    constraints: List[Constraint] = field(default_factory=list)
    assumptions: List[Assumption] = field(default_factory=list)

    # Requirements
    functional_requirements: List[FunctionalRequirement] = field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = field(default_factory=list)

    # Use Cases
    use_cases: List[UseCase] = field(default_factory=list)

    # Data Requirements
    data_requirements: List[DataRequirement] = field(default_factory=list)

    # Integration Requirements
    integration_requirements: List[IntegrationRequirement] = field(default_factory=list)

    # Additional Context
    glossary: Dict[str, str] = field(default_factory=dict)  # Term definitions
    references: List[str] = field(default_factory=list)  # External documents

    def to_yaml(self, file_path: str):
        """Export to YAML file"""
        try:
            data = self._prepare_for_export()
            with open(file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        except Exception as e:
            raise wrap_exception(
                e,
                RequirementsExportError,
                f"Failed to export requirements to YAML: {file_path}",
                context={"file_path": file_path, "project_name": self.project_name}
            )

    def to_json(self, file_path: str):
        """Export to JSON file"""
        try:
            data = self._prepare_for_export()
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise wrap_exception(
                e,
                RequirementsExportError,
                f"Failed to export requirements to JSON: {file_path}",
                context={"file_path": file_path, "project_name": self.project_name}
            )

    def _prepare_for_export(self) -> Dict[str, Any]:
        """Prepare data for export (convert enums to strings)"""
        data = asdict(self)

        # Convert Priority and RequirementType enums to strings
        for req in data.get('functional_requirements', []):
            if 'priority' in req and hasattr(req['priority'], 'value'):
                req['priority'] = req['priority'].value

        for req in data.get('non_functional_requirements', []):
            if 'priority' in req and hasattr(req['priority'], 'value'):
                req['priority'] = req['priority'].value
            if 'type' in req and hasattr(req['type'], 'value'):
                req['type'] = req['type'].value

        return data

    @classmethod
    def from_yaml(cls, file_path: str) -> 'StructuredRequirements':
        """Load from YAML file"""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data)

    @classmethod
    def from_json(cls, file_path: str) -> 'StructuredRequirements':
        """Load from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> 'StructuredRequirements':
        """Convert dict to StructuredRequirements (handle enums)"""
        # Convert priority strings to Priority enums
        for req in data.get('functional_requirements', []):
            if 'priority' in req and isinstance(req['priority'], str):
                req['priority'] = Priority(req['priority'])

        for req in data.get('non_functional_requirements', []):
            if 'priority' in req and isinstance(req['priority'], str):
                req['priority'] = Priority(req['priority'])
            if 'type' in req and isinstance(req['type'], str):
                req['type'] = RequirementType(req['type'])

        # Convert nested dicts to dataclasses
        if 'stakeholders' in data:
            data['stakeholders'] = [Stakeholder(**s) for s in data['stakeholders']]

        if 'constraints' in data:
            data['constraints'] = [Constraint(**c) for c in data['constraints']]

        if 'assumptions' in data:
            data['assumptions'] = [Assumption(**a) for a in data['assumptions']]

        if 'functional_requirements' in data:
            data['functional_requirements'] = [FunctionalRequirement(**r) for r in data['functional_requirements']]

        if 'non_functional_requirements' in data:
            data['non_functional_requirements'] = [NonFunctionalRequirement(**r) for r in data['non_functional_requirements']]

        if 'use_cases' in data:
            data['use_cases'] = [UseCase(**u) for u in data['use_cases']]

        if 'data_requirements' in data:
            data['data_requirements'] = [DataRequirement(**d) for d in data['data_requirements']]

        if 'integration_requirements' in data:
            data['integration_requirements'] = [IntegrationRequirement(**i) for i in data['integration_requirements']]

        return cls(**data)

    def get_summary(self) -> str:
        """Get a human-readable summary"""
        summary = f"# {self.project_name} - Requirements Summary\n\n"
        summary += f"**Version:** {self.version}\n\n"

        if self.executive_summary:
            summary += f"## Executive Summary\n{self.executive_summary}\n\n"

        summary += f"## Requirements Overview\n"
        summary += f"- Functional Requirements: {len(self.functional_requirements)}\n"
        summary += f"- Non-Functional Requirements: {len(self.non_functional_requirements)}\n"
        summary += f"- Use Cases: {len(self.use_cases)}\n"
        summary += f"- Data Requirements: {len(self.data_requirements)}\n"
        summary += f"- Integration Requirements: {len(self.integration_requirements)}\n"
        summary += f"- Stakeholders: {len(self.stakeholders)}\n"
        summary += f"- Constraints: {len(self.constraints)}\n\n"

        # Priority breakdown
        priority_counts = {}
        for req in self.functional_requirements:
            p = req.priority.value
            priority_counts[p] = priority_counts.get(p, 0) + 1

        if priority_counts:
            summary += "## Priority Breakdown\n"
            for priority, count in sorted(priority_counts.items()):
                summary += f"- {priority.capitalize()}: {count}\n"

        return summary
