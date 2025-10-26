#!/usr/bin/env python3
"""
Script to split artemis_stages.py into separate files for strict SRP compliance

Each stage class will be extracted to stages/<stage_name>.py
"""

import re
from pathlib import Path

def extract_stage_class(content: str, class_name: str) -> tuple[str, int, int]:
    """Extract a stage class from the content"""
    # Find the class definition
    pattern = rf'^class {class_name}\('
    lines = content.split('\n')

    start_idx = None
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            start_idx = i
            break

    if start_idx is None:
        return None, None, None

    # Find the end of the class (next class or end of file)
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        if re.match(r'^class \w+', lines[i]):
            end_idx = i
            break

    # Extract the class
    class_lines = lines[start_idx:end_idx]
    return '\n'.join(class_lines), start_idx, end_idx

def create_stage_file(stage_name: str, class_content: str, imports: str):
    """Create a stage file with proper imports and content"""
    file_content = f'''#!/usr/bin/env python3
"""
{stage_name}

Extracted from artemis_stages.py for strict Single Responsibility Principle compliance.
Each stage has its own file for independent testing and evolution.
"""

{imports}

{class_content}
'''
    return file_content

def main():
    # Read original file
    with open('artemis_stages.py', 'r') as f:
        content = f.read()

    # Extract imports (everything before first class)
    lines = content.split('\n')
    import_end_idx = None
    for i, line in enumerate(lines):
        if re.match(r'^class \w+', line):
            import_end_idx = i
            break

    imports = '\n'.join(lines[:import_end_idx])

    # Stages to extract
    stages = [
        ('ProjectAnalysisStage', 'project_analysis_stage.py'),
        ('ArchitectureStage', 'architecture_stage.py'),
        ('DependencyValidationStage', 'dependency_validation_stage.py'),
        ('DevelopmentStage', 'development_stage.py'),
        ('ValidationStage', 'validation_stage.py'),
        ('IntegrationStage', 'integration_stage.py'),
        ('TestingStage', 'testing_stage.py')
    ]

    # Extract and write each stage
    for class_name, filename in stages:
        class_content, start, end = extract_stage_class(content, class_name)

        if class_content:
            file_content = create_stage_file(class_name, class_content, imports)

            output_path = Path('stages') / filename
            with open(output_path, 'w') as f:
                f.write(file_content)

            print(f"✅ Created {output_path} ({end - start} lines)")
        else:
            print(f"❌ Could not find {class_name}")

    # Create __init__.py
    init_content = '''#!/usr/bin/env python3
"""
Artemis Pipeline Stages

Each stage has Single Responsibility and is independently testable.
All stages implement the PipelineStage interface.
"""

from .project_analysis_stage import ProjectAnalysisStage
from .architecture_stage import ArchitectureStage
from .dependency_validation_stage import DependencyValidationStage
from .development_stage import DevelopmentStage
from .validation_stage import ValidationStage
from .integration_stage import IntegrationStage
from .testing_stage import TestingStage

__all__ = [
    'ProjectAnalysisStage',
    'ArchitectureStage',
    'DependencyValidationStage',
    'DevelopmentStage',
    'ValidationStage',
    'IntegrationStage',
    'TestingStage'
]
'''

    with open('stages/__init__.py', 'w') as f:
        f.write(init_content)

    print("✅ Created stages/__init__.py")

    # Create compatibility shim
    shim_content = '''#!/usr/bin/env python3
"""
Backward compatibility shim for artemis_stages.py

All stages have been moved to stages/ directory.
This file maintains import compatibility.
"""

from stages import (
    ProjectAnalysisStage,
    ArchitectureStage,
    DependencyValidationStage,
    DevelopmentStage,
    ValidationStage,
    IntegrationStage,
    TestingStage
)

__all__ = [
    'ProjectAnalysisStage',
    'ArchitectureStage',
    'DependencyValidationStage',
    'DevelopmentStage',
    'ValidationStage',
    'IntegrationStage',
    'TestingStage'
]

# Deprecated warning
import warnings
warnings.warn(
    "artemis_stages.py is deprecated. Import from 'stages' package instead.",
    DeprecationWarning,
    stacklevel=2
)
'''

    with open('artemis_stages_compat.py', 'w') as f:
        f.write(shim_content)

    print("✅ Created artemis_stages_compat.py (compatibility shim)")
    print("\n✅ Split complete! Run syntax validation next.")

if __name__ == '__main__':
    main()
