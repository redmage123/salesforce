#!/usr/bin/env python3
"""
Standalone test: Generate demo using OpenAI API directly
No Artemis dependencies - pure OpenAI test
"""

import sys
import json
import os
from pathlib import Path

def main():
    print("\n" + "=" * 80)
    print("OPENAI DEMO GENERATION TEST (Standalone)")
    print("=" * 80)

    # Load API key
    env_file = Path(__file__).parent.parent.parent.parent / '.agents' / 'agile' / '.env'
    api_key = None

    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('OPENAI_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    break

    if not api_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        return False

    print(f"✅ API key loaded: {api_key[:20]}...")

    # Import OpenAI
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
    except ImportError:
        print("❌ OpenAI library not installed: pip install openai")
        return False
    except Exception as e:
        print(f"❌ Error initializing OpenAI: {e}")
        return False

    # Create prompt
    prompt = """Create a comprehensive Jupyter notebook demonstrating the Artemis AI Pipeline.

Requirements:
- Title: "Artemis Pipeline - Live Demo & Analysis"
- Real-time metrics visualization
- Pipeline stage success rates (8 stages)
- Multi-agent performance comparison
- Code quality radar chart
- Sprint progress tracking
- Integration ecosystem visualization
- Cost and performance analysis

Technical:
- Use Plotly for Python visualizations
- Include pandas, plotly imports
- Generate 8+ cells with executable code
- Include markdown cells

8 Pipeline Stages:
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

Return ONLY the JSON, no markdown code blocks."""

    print(f"\n📤 Sending request to OpenAI...")
    print(f"Model: gpt-4o")
    print(f"Prompt length: {len(prompt)} chars\n")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert Python developer creating production-ready Jupyter notebooks. Generate complete, executable code with real data integration."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )

        print(f"✅ Response received")
        print(f"Usage: {response.usage.total_tokens} tokens")
        print(f"Content length: {len(response.choices[0].message.content)} chars\n")

    except Exception as e:
        print(f"❌ OpenAI API error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Parse response
    content = response.choices[0].message.content.strip()

    # Clean markdown code blocks
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
    if content.startswith("json"):
        content = content[4:].strip()

    # Parse JSON
    try:
        notebook_data = json.loads(content)
        print(f"✅ Valid JSON parsed")
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        debug_file = Path(__file__).parent / 'openai_response_raw.txt'
        with open(debug_file, 'w') as f:
            f.write(content)
        print(f"💾 Raw response saved to {debug_file}")
        return False

    # Build notebook
    notebook = {
        "cells": notebook_data.get("cells", []),
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"}
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    # Save notebook
    output_file = Path(__file__).parent / 'openai_generated_demo.ipynb'
    with open(output_file, 'w') as f:
        json.dump(notebook, f, indent=2)

    print(f"💾 Notebook saved to: {output_file}\n")

    # Evaluate quality
    cells = notebook['cells']
    num_cells = len(cells)
    num_code = sum(1 for c in cells if c.get('cell_type') == 'code')
    num_markdown = sum(1 for c in cells if c.get('cell_type') == 'markdown')

    cell_contents = ' '.join(str(c.get('source', [])) for c in cells)
    has_imports = 'import' in cell_contents
    has_plotly = 'plotly' in cell_contents.lower()
    has_pandas = 'pandas' in cell_contents.lower()
    has_visualizations = sum(1 for c in cells if 'Figure' in str(c.get('source', [])) or 'chart' in str(c.get('source', [])).lower())

    print("=" * 80)
    print("QUALITY EVALUATION: OpenAI Generated")
    print("=" * 80)
    print(f"📊 Cell counts:")
    print(f"  Total: {num_cells}")
    print(f"  Code: {num_code}")
    print(f"  Markdown: {num_markdown}")
    print(f"\n✓ Key components:")
    print(f"  Imports: {'✅' if has_imports else '❌'}")
    print(f"  Plotly: {'✅' if has_plotly else '❌'}")
    print(f"  Pandas: {'✅' if has_pandas else '❌'}")
    print(f"  Visualizations: {has_visualizations}")

    # Score
    score = 0
    if num_cells >= 8: score += 2
    if num_code >= 5: score += 2
    if has_imports: score += 1
    if has_plotly: score += 2
    if has_pandas: score += 1
    if has_visualizations >= 3: score += 1
    if has_visualizations >= 5: score += 1

    grade_map = {
        10: 'A+', 9: 'A', 8: 'A-', 7: 'B+', 6: 'B', 5: 'B-',
        4: 'C', 3: 'D', 2: 'D', 1: 'F', 0: 'F'
    }
    grade = grade_map.get(min(score, 10), 'F')

    print(f"\n🎯 Quality Score: {score}/10")
    print(f"📝 Grade: {grade}\n")

    # Compare to manual and Artemis
    print("=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print(f"Manual Creation:     Score 9/10 - Grade A")
    print(f"OpenAI Direct:       Score {score}/10 - Grade {grade}")
    print(f"Artemis Developers:  Score 2/10 - Grade D")

    print(f"\n💰 API Usage:")
    print(f"  Prompt tokens: {response.usage.prompt_tokens}")
    print(f"  Completion tokens: {response.usage.completion_tokens}")
    print(f"  Total tokens: {response.usage.total_tokens}")

    print(f"\n🎯 Result:")
    if score >= 7:
        print("✅ SUCCESS: OpenAI produces good quality notebooks!")
        print(f"   This proves Artemis has a {score - 2} point quality gap")
    elif score >= 5:
        print("⚠️  PARTIAL: OpenAI is acceptable but could be better")
    else:
        print("❌ FAILURE: Even direct OpenAI underperforms")

    print("=" * 80 + "\n")

    return score >= 5

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
