#!/usr/bin/env python3
"""
Generate Artemis demo notebook using OpenAI API.
This simulates what the Artemis developer agents should be doing.
"""

import json
import os
from pathlib import Path
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Read the Artemis prompts
artemis_path = Path(__file__).parent.parent.parent.parent / '.agents' / 'agile'

# Load requirements from Kanban card
kanban_file = artemis_path / 'kanban_board.json'
with open(kanban_file, 'r') as f:
    kanban_data = json.load(f)

# Get the demo card requirements
card = None
for column in kanban_data.get('columns', {}).values():
    for c in column.get('cards', []):
        if 'chart.js' in c.get('description', '').lower():
            card = c
            break
    if card:
        break

if not card:
    # Fallback to basic requirements
    requirements = """
    Create a comprehensive Jupyter notebook demonstrating the Artemis pipeline with:
    - Real-time metrics visualization using Chart.js
    - Pipeline stage success rates
    - Multi-agent performance comparison
    - Code quality metrics
    - Sprint progress tracking
    - Integration ecosystem
    - Cost and performance analysis

    Use Plotly for Python-based visualizations.
    Load real data from the Artemis kanban_board.json file.
    """
else:
    requirements = f"""
    Title: {card.get('title', 'Artemis Demo')}
    Description: {card.get('description', '')}

    Additional context:
    - Use Plotly for interactive visualizations in Python
    - Load real data from /home/bbrelin/src/repos/salesforce/.agents/agile/kanban_board.json
    - Include 8 pipeline stages: Sprint Planning, Project Analysis, Development, Code Review, Arbitration, Validation, Integration, Retrospective
    - Show multi-agent collaboration (Conservative Developer A vs Aggressive Developer B)
    - Include cost analysis and performance metrics
    """

# Create the prompt for OpenAI
system_prompt = """You are an expert Python developer creating Jupyter notebooks for data visualization and analysis.
You create comprehensive, production-ready notebooks with real data integration and interactive visualizations.
Always use Plotly for visualizations in Python notebooks.
Generate complete, executable code with proper imports, data loading, and visualizations.
"""

user_prompt = f"""Create a comprehensive Jupyter notebook for the Artemis AI Pipeline demo.

Requirements:
{requirements}

The notebook should have:
1. Title and introduction cell (markdown)
2. Import libraries cell (pandas, plotly, json, pathlib)
3. Load real Artemis data from kanban_board.json
4. Multiple visualization cells with:
   - Funnel chart for pipeline stages
   - Bar charts for agent performance
   - Radar chart for code quality
   - Line chart for sprint progress
   - Pie/Doughnut chart for integrations
   - Cost analysis by stage
5. Key findings and recommendations (markdown)

Generate the notebook as a JSON structure with cells array.
Each cell should have:
- cell_type: "code" or "markdown"
- source: array of strings (lines of code/markdown)

Return ONLY valid JSON, no markdown formatting."""

print("🤖 Calling OpenAI API to generate notebook...")
print(f"Model: gpt-4o")
print(f"Prompt length: {len(user_prompt)} chars")
print("-" * 80)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    temperature=0.7,
    max_tokens=4000
)

# Extract the generated notebook
notebook_json = response.choices[0].message.content

# Clean up if wrapped in markdown code blocks
if notebook_json.startswith("```"):
    lines = notebook_json.split("\n")
    notebook_json = "\n".join(lines[1:-1])

print("\n📝 Generated notebook JSON:")
print(f"Response length: {len(notebook_json)} chars")
print("-" * 80)

# Parse and validate JSON
try:
    notebook_data = json.loads(notebook_json)
    print(f"✅ Valid JSON with {len(notebook_data.get('cells', []))} cells")
except json.JSONDecodeError as e:
    print(f"❌ Invalid JSON: {e}")
    # Save raw response for debugging
    debug_file = Path(__file__).parent / 'openai_response_debug.txt'
    with open(debug_file, 'w') as f:
        f.write(notebook_json)
    print(f"💾 Raw response saved to {debug_file}")
    exit(1)

# Create proper Jupyter notebook structure
full_notebook = {
    "cells": notebook_data.get("cells", []),
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

# Save the notebook
output_file = Path(__file__).parent / 'artemis_openai_generated_demo.ipynb'
with open(output_file, 'w') as f:
    json.dump(full_notebook, f, indent=2)

print(f"\n✅ Notebook saved to: {output_file}")

# Generate quality report
print("\n" + "=" * 80)
print("📊 QUALITY ANALYSIS")
print("=" * 80)

num_cells = len(full_notebook['cells'])
num_code = sum(1 for c in full_notebook['cells'] if c.get('cell_type') == 'code')
num_markdown = sum(1 for c in full_notebook['cells'] if c.get('cell_type') == 'markdown')

print(f"Total cells: {num_cells}")
print(f"Code cells: {num_code}")
print(f"Markdown cells: {num_markdown}")

# Check for key components
has_imports = any('import' in str(c.get('source', [])) for c in full_notebook['cells'])
has_plotly = any('plotly' in str(c.get('source', [])) for c in full_notebook['cells'])
has_data_loading = any('json' in str(c.get('source', [])) and 'open' in str(c.get('source', [])) for c in full_notebook['cells'])
has_visualizations = any('Figure' in str(c.get('source', [])) or 'chart' in str(c.get('source', [])).lower() for c in full_notebook['cells'])

print(f"\nKey components:")
print(f"  ✓ Imports: {has_imports}")
print(f"  ✓ Plotly usage: {has_plotly}")
print(f"  ✓ Data loading: {has_data_loading}")
print(f"  ✓ Visualizations: {has_visualizations}")

# Calculate quality score
quality_score = 0
if num_cells >= 8: quality_score += 2
if num_code >= 5: quality_score += 2
if has_imports: quality_score += 1
if has_plotly: quality_score += 2
if has_data_loading: quality_score += 2
if has_visualizations: quality_score += 1

grade_map = {
    10: 'A+', 9: 'A', 8: 'A-', 7: 'B+', 6: 'B', 5: 'B-',
    4: 'C', 3: 'D', 2: 'D', 1: 'F', 0: 'F'
}
grade = grade_map.get(quality_score, 'F')

print(f"\n🎯 Quality Score: {quality_score}/10 - Grade: {grade}")

# Compare to manual creation
print("\n" + "=" * 80)
print("📈 COMPARISON TO MANUAL CREATION")
print("=" * 80)
print("Manual notebook: 17 cells, 7 visualizations, Grade A (9/10)")
print(f"OpenAI notebook: {num_cells} cells, Grade {grade} ({quality_score}/10)")

if quality_score >= 8:
    print("\n✅ SUCCESS: OpenAI matches/exceeds manual quality!")
elif quality_score >= 5:
    print("\n⚠️  PARTIAL: OpenAI is acceptable but below manual quality")
else:
    print("\n❌ FAILURE: OpenAI significantly underperforms manual creation")

print("\n" + "=" * 80)

# Token usage stats
print(f"\n💰 API Usage:")
print(f"  Prompt tokens: {response.usage.prompt_tokens}")
print(f"  Completion tokens: {response.usage.completion_tokens}")
print(f"  Total tokens: {response.usage.total_tokens}")
