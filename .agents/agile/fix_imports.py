#!/usr/bin/env python3
"""Fix RAGStorageHelper imports placement"""

from pathlib import Path

files = [
    'stages/development_stage.py',
    'stages/integration_stage.py',
    'stages/testing_stage.py',
    'requirements_stage.py',
    'sprint_planning_stage.py',
    'code_review_stage.py',
    'uiux_stage.py',
    'project_review_stage.py'
]

for filepath in files:
    path = Path(filepath)
    if not path.exists():
        continue

    with open(path, 'r') as f:
        lines = f.readlines()

    # Remove any existing RAGStorageHelper imports
    lines = [line for line in lines if 'from rag_storage_helper import' not in line]

    # Find last import line
    last_import_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith(('import ', 'from ')) and 'rag_storage_helper' not in line:
            last_import_idx = i

    # Insert import after last import, with blank line
    lines.insert(last_import_idx + 1, 'from rag_storage_helper import RAGStorageHelper\n')

    # Write back
    with open(path, 'w') as f:
        f.writelines(lines)

    print(f"Fixed {filepath}")

print("Done!")
