#!/usr/bin/env python3
"""
Script to automatically update all stages to use RAGStorageHelper

Replaces direct self.rag.store_artifact() calls with RAGStorageHelper.store_stage_artifact()
"""

import re
from pathlib import Path

# Files to update
files_to_update = [
    'stages/architecture_stage.py',
    'stages/development_stage.py',
    'stages/integration_stage.py',
    'stages/testing_stage.py',
    'requirements_stage.py',
    'sprint_planning_stage.py',
    'code_review_stage.py',
    'uiux_stage.py',
    'project_review_stage.py',
]

def add_import(content: str) -> str:
    """Add RAGStorageHelper import if not present"""
    if 'from rag_storage_helper import' in content:
        return content  # Already has import

    # Find a good place to add import (after other imports)
    lines = content.split('\n')

    # Find last import or from statement
    last_import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i

    # Insert import after last import
    lines.insert(last_import_idx + 1, 'from rag_storage_helper import RAGStorageHelper')

    return '\n'.join(lines)

def replace_rag_store_artifact(content: str) -> str:
    """Replace self.rag.store_artifact() with RAGStorageHelper.store_stage_artifact()"""

    # Pattern to match self.rag.store_artifact( calls
    pattern = r'(\s+)self\.rag\.store_artifact\('

    def replacement(match):
        indent = match.group(1)
        # Add comment about using helper
        return f'{indent}# Store in RAG using helper (DRY)\n{indent}RAGStorageHelper.store_stage_artifact(\n{indent}    rag=self.rag,'

    # Replace pattern
    content = re.sub(pattern, replacement, content)

    # Also need to update the parameters
    # artifact_type="..." -> stage_name="..."
    content = content.replace('artifact_type=', 'stage_name=')

    # Add logger parameter if missing (before closing paren)
    # This is trickier - for now just add comment

    return content

def update_file(filepath: str):
    """Update a single file"""
    path = Path(filepath)

    if not path.exists():
        print(f"⚠️  Skipping {filepath} (not found)")
        return

    print(f"📝 Updating {filepath}...")

    # Read file
    with open(path, 'r') as f:
        content = f.read()

    # Check if file has rag.store_artifact calls
    if 'self.rag.store_artifact(' not in content:
        print(f"   ℹ️  No rag.store_artifact calls found")
        return

    # Add import
    content = add_import(content)

    # Replace calls
    content = replace_rag_store_artifact(content)

    # Write back
    with open(path, 'w') as f:
        f.write(content)

    print(f"   ✅ Updated {filepath}")

def main():
    """Update all files"""
    print("🔧 Updating stages to use RAGStorageHelper...")
    print()

    for filepath in files_to_update:
        update_file(filepath)

    print()
    print("✅ Update complete!")
    print()
    print("Next steps:")
    print("1. Run syntax validation: python3 -m py_compile <file>")
    print("2. Review changes manually")
    print("3. Add logger=self.logger to calls that need it")

if __name__ == '__main__':
    main()
