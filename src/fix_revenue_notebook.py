#!/usr/bin/env python3
"""
Fix the revenue intelligence notebook by removing problematic cells
"""
import json
import shutil
from datetime import datetime

notebook_path = '/home/bbrelin/src/repos/salesforce/src/salesforce_ai_revenue_intelligence.ipynb'

# Backup the original
backup_path = notebook_path.replace('.ipynb', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.ipynb')
shutil.copy(notebook_path, backup_path)
print(f"✅ Created backup: {backup_path}")

# Read notebook
with open(notebook_path, 'r') as f:
    nb = json.load(f)

print(f"Original notebook has {len(nb['cells'])} cells")

# Find and remove problematic cells
cells_to_remove = []
for i, cell in enumerate(nb['cells']):
    source = ''.join(cell.get('source', []))

    # Mark cells with missing file references
    if '%run src/rag_backend' in source or 'sys.path.insert(0, \'src/rag_backend\')' in source:
        cells_to_remove.append(i)
        print(f"Removing cell {i}: {source[:80]}...")

# Remove cells (in reverse order to maintain indices)
for i in reversed(cells_to_remove):
    del nb['cells'][i]

print(f"✅ Removed {len(cells_to_remove)} problematic cells")
print(f"New notebook has {len(nb['cells'])} cells")

# Write fixed notebook
with open(notebook_path, 'w') as f:
    json.dump(nb, f, indent=1)

print(f"✅ Fixed notebook saved to: {notebook_path}")
print("\n✨ The notebook should now work correctly!")
print("   The demo presentation launch cell is still there and should work.")
