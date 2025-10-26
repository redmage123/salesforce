#!/usr/bin/env python3
"""Dead simple OpenAI test - just call the API with Artemis requirements"""

import os
from openai import OpenAI

# Load API key from .env
with open('/home/bbrelin/src/repos/salesforce/.agents/agile/.env', 'r') as f:
    for line in f:
        if line.startswith('OPENAI_API_KEY='):
            api_key = line.split('=', 1)[1].strip()
            break

# Initialize client
client = OpenAI(api_key=api_key)

# Exact requirements from Artemis kanban board
prompt = """Create a comprehensive Jupyter notebook demonstrating the Artemis AI Pipeline.

Requirements from Sprint 2 - Chart.js Visualizations:
- Integrate Chart.js to display various metrics and data visualizations
- Pipeline metrics visualized using Chart.js
- Cost tracking and success rates displayed with charts
- Charts include line, bar, area, pie, and radar types

Requirements from Sprint 2 - Showcase Real Metrics:
- Metrics are up-to-date and accurate
- Data presented in clear and understandable manner
- Charts and graphs reflect actual performance data

Technical Requirements:
- Use Plotly for Python visualizations (notebook version of Chart.js)
- Load real data from kanban_board.json
- Include pandas, plotly.graph_objects, plotly.express imports
- Generate 8+ cells with executable code
- Include markdown cells for documentation

Pipeline Stages (8 total):
1. Sprint Planning
2. Project Analysis
3. Development
4. Code Review
5. Arbitration
6. Validation
7. Integration
8. Retrospective

Return ONLY a valid JSON object with this structure:
{
  "cells": [
    {"cell_type": "markdown", "source": ["# Title"]},
    {"cell_type": "code", "source": ["import pandas as pd"]}
  ]
}

NO markdown code blocks, just raw JSON."""

print("Calling OpenAI API...")
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are an expert Python developer creating production-ready Jupyter notebooks with real data integration and interactive visualizations."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.7,
    max_tokens=4000
)

print(f"Tokens used: {response.usage.total_tokens}")
print(f"Response length: {len(response.choices[0].message.content)} chars")

# Save raw response
import json
with open('/tmp/openai_notebook_response.txt', 'w') as f:
    f.write(response.choices[0].message.content)

print("Saved to /tmp/openai_notebook_response.txt")

# Try to parse and save as notebook
content = response.choices[0].message.content.strip()
if content.startswith("```"):
    lines = content.split("\n")
    content = "\n".join(lines[1:-1])
if content.startswith("json"):
    content = content[4:].strip()

try:
    notebook_data = json.loads(content)
    notebook = {
        "cells": notebook_data.get("cells", []),
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 4
    }

    with open('/tmp/openai_generated_notebook.ipynb', 'w') as f:
        json.dump(notebook, f, indent=2)

    print(f"✅ Generated notebook with {len(notebook['cells'])} cells")
    print("Saved to /tmp/openai_generated_notebook.ipynb")

    # Quick quality check
    code_cells = sum(1 for c in notebook['cells'] if c.get('cell_type') == 'code')
    has_plotly = any('plotly' in str(c) for c in notebook['cells'])
    has_pandas = any('pandas' in str(c) for c in notebook['cells'])

    print(f"\nQuick Quality Check:")
    print(f"  Total cells: {len(notebook['cells'])}")
    print(f"  Code cells: {code_cells}")
    print(f"  Has Plotly: {has_plotly}")
    print(f"  Has Pandas: {has_pandas}")

except Exception as e:
    print(f"❌ Failed to parse JSON: {e}")
