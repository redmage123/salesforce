#!/usr/bin/env python3
"""
Requirements-Driven Validation System

Analyzes requirements → Selects workflow → Validates with appropriate criteria.
Eliminates "one-size-fits-all TDD" problem.
"""

from typing import Dict, Optional
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict


class WorkflowType(Enum):
    """Workflow strategies"""
    TDD = "tdd"  # Test-Driven: tests first, minimal code
    QUALITY_DRIVEN = "quality_driven"  # Requirements first, comprehensive output
    VISUAL_TEST = "visual_test"  # Visual + accessibility
    CONTENT_VALIDATION = "content_validation"  # Structure + content


class ArtifactType(Enum):
    """Artifact types"""
    CODE = "code"
    NOTEBOOK = "notebook"
    UI = "ui"
    DOCUMENTATION = "documentation"
    DEMO = "demo"
    VISUALIZATION = "visualization"


@dataclass
class ValidationStrategy:
    """Complete validation strategy from requirements"""
    artifact_type: ArtifactType
    workflow: WorkflowType
    quality_criteria: Dict
    validator_class: str

    def to_dict(self):
        return {
            'artifact_type': self.artifact_type.value,
            'workflow': self.workflow.value,
            'quality_criteria': self.quality_criteria,
            'validator_class': self.validator_class
        }


class RequirementsDrivenValidator:
    """
    Core component: Requirements → Workflow → Validation

    Replaces hardcoded TDD with intelligent workflow selection.
    """

    def __init__(self, logger=None):
        self.logger = logger

        # Artifact detection keywords (priority order)
        self.keywords = {
            ArtifactType.NOTEBOOK: ['jupyter', '.ipynb', 'notebook', 'data analysis'],
            ArtifactType.UI: ['react', 'vue', 'component', 'frontend', 'ui'],
            ArtifactType.VISUALIZATION: ['chart', 'plotly', 'dashboard', 'viz'],
            ArtifactType.DEMO: ['demo', 'presentation', 'showcase'],
            ArtifactType.DOCUMENTATION: ['documentation', 'readme', 'guide'],
        }

        # Workflow mappings
        self.workflow_map = {
            ArtifactType.CODE: WorkflowType.TDD,
            ArtifactType.NOTEBOOK: WorkflowType.QUALITY_DRIVEN,
            ArtifactType.UI: WorkflowType.VISUAL_TEST,
            ArtifactType.DOCUMENTATION: WorkflowType.CONTENT_VALIDATION,
            ArtifactType.DEMO: WorkflowType.QUALITY_DRIVEN,
            ArtifactType.VISUALIZATION: WorkflowType.QUALITY_DRIVEN,
        }

        # Validator mappings
        self.validator_map = {
            ArtifactType.CODE: 'CodeQualityValidator',
            ArtifactType.NOTEBOOK: 'NotebookQualityValidator',
            ArtifactType.UI: 'UIQualityValidator',
            ArtifactType.DOCUMENTATION: 'DocumentationValidator',
            ArtifactType.DEMO: 'DemoValidator',
            ArtifactType.VISUALIZATION: 'VisualizationValidator',
        }

    def analyze_requirements(self,
                           task_title: str,
                           task_description: str,
                           parsed_requirements: Optional[Dict] = None) -> ValidationStrategy:
        """
        Main entry point: Analyze requirements and return validation strategy.

        Args:
            task_title: Task title
            task_description: Task description
            parsed_requirements: Optional parsed requirements from requirements_parser_agent

        Returns:
            ValidationStrategy with artifact type, workflow, criteria, validator
        """
        # Detect artifact type
        artifact_type = self._detect_artifact_type(
            task_title, task_description, parsed_requirements
        )

        # Extract quality criteria
        quality_criteria = self._extract_quality_criteria(
            artifact_type, task_title, task_description, parsed_requirements
        )

        # Get workflow and validator
        workflow = self.workflow_map.get(artifact_type, WorkflowType.TDD)
        validator_class = self.validator_map.get(artifact_type, 'CodeQualityValidator')

        strategy = ValidationStrategy(
            artifact_type=artifact_type,
            workflow=workflow,
            quality_criteria=quality_criteria,
            validator_class=validator_class
        )

        if self.logger:
            self.logger.log(f"📋 Validation Strategy: {artifact_type.value} → {workflow.value}", "INFO")

        return strategy

    def _detect_artifact_type(self, title: str, description: str, requirements: Optional[Dict]) -> ArtifactType:
        """Detect artifact type from requirements"""
        combined = f"{title} {description}".lower()

        # Check parsed requirements first
        if requirements and 'artifact_type' in requirements:
            return ArtifactType(requirements['artifact_type'])

        # Keyword matching (priority order)
        for artifact_type in [
            ArtifactType.NOTEBOOK,
            ArtifactType.UI,
            ArtifactType.VISUALIZATION,
            ArtifactType.DEMO,
            ArtifactType.DOCUMENTATION,
        ]:
            keywords = self.keywords.get(artifact_type, [])
            if any(kw in combined for kw in keywords):
                return artifact_type

        return ArtifactType.CODE  # Default

    def _extract_quality_criteria(self,
                                  artifact_type: ArtifactType,
                                  title: str,
                                  description: str,
                                  requirements: Optional[Dict]) -> Dict:
        """Extract quality criteria based on artifact type"""
        import re
        combined = f"{title} {description}".lower()
        criteria = {}

        # Notebook criteria
        if artifact_type == ArtifactType.NOTEBOOK:
            # Cell count
            match = re.search(r'(\d+)\+?\s*cells?', combined)
            criteria['min_cells'] = int(match.group(1)) if match else 8

            # Visualizations
            criteria['requires_visualizations'] = any(
                w in combined for w in ['chart', 'graph', 'plot', 'viz']
            )

            # Visualization library
            for lib in ['plotly', 'matplotlib', 'chart.js']:
                if lib in combined:
                    criteria['visualization_library'] = lib
                    break

            # Data source
            match = re.search(r'([\w_]+\.(?:json|csv|xlsx))', combined)
            if match:
                criteria['data_source'] = match.group(1)

        # UI criteria
        elif artifact_type == ArtifactType.UI:
            criteria['accessibility_required'] = any(
                w in combined for w in ['accessibility', 'wcag', 'a11y']
            )
            criteria['responsive_required'] = 'responsive' in combined

        # Code criteria
        elif artifact_type == ArtifactType.CODE:
            criteria['min_test_coverage'] = 0.8
            criteria['requires_unit_tests'] = True

        # Merge with parsed requirements if available
        if requirements and 'quality_criteria' in requirements:
            criteria.update(requirements['quality_criteria'])

        return criteria
