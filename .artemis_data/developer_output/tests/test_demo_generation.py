#!/usr/bin/env python3
"""
Test: Demo Generation Quality Comparison
Compare OpenAI API generation vs manual creation using Artemis LLM client
"""

import sys
import json
import os
from pathlib import Path

# Load environment variables from .env file
env_file = Path(__file__).parent.parent.parent.parent / '.agents' / 'agile' / '.env'
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Add Artemis modules to path
artemis_path = Path(__file__).parent.parent.parent.parent / '.agents' / 'agile'
sys.path.insert(0, str(artemis_path))

try:
    from llm_client import get_llm_client, LLMMessage
except Exception as e:
    print(f"❌ Error importing Artemis modules: {e}")
    print(f"   Artemis path: {artemis_path}")
    sys.exit(1)

def load_artemis_context():
    """Load context data that Artemis would use"""
    kanban_file = artemis_path / 'kanban_board.json'
    with open(kanban_file, 'r') as f:
        kanban_data = json.load(f)

    requirements = """
Create a comprehensive Jupyter notebook demonstrating the Artemis AI Pipeline.

Requirements:
- Title: "Artemis Pipeline - Live Demo & Analysis"
- Real-time metrics visualization
- Pipeline stage success rates (8 stages)
- Multi-agent performance comparison (Conservative vs Aggressive developers)
- Code quality radar chart with 6 dimensions
- Sprint progress tracking over time
- Integration ecosystem visualization
- Cost and performance analysis

Technical:
- Use Plotly for Python interactive visualizations
- Load real data from kanban_board.json
- Include pandas, plotly.graph_objects, plotly.express imports
- Generate 8+ cells with executable code
- Include markdown cells for documentation

8 Pipeline Stages:
1. Sprint Planning
2. Project Analysis
3. Development
4. Code Review
5. Arbitration
6. Validation
7. Integration
8. Retrospective

Return the notebook as a JSON structure with cells array.
Each cell: {"cell_type": "code"|"markdown", "source": ["line1", "line2", ...]}
Return ONLY valid JSON, no markdown code blocks.
"""
    return requirements

def generate_with_artemis_llm():
    """Generate notebook using Artemis LLM client (same as developers use)"""
    print("=" * 80)
    print("GENERATING NOTEBOOK USING ARTEMIS LLM CLIENT")
    print("=" * 80)

    try:
        # Get LLM client (uses same config as Artemis developers)
        llm = get_llm_client()
        print(f"✅ LLM client initialized: {llm.__class__.__name__}")
    except Exception as e:
        print(f"❌ Error initializing LLM client: {e}")
        return None, None

    # Load context
    requirements = load_artemis_context()

    # Create messages using Artemis pattern
    messages = [
        LLMMessage(
            role="system",
            content="You are an expert Python developer creating production-ready Jupyter notebooks. Create comprehensive, executable notebooks with real data integration and interactive visualizations. Always use Plotly for Python visualizations. Generate complete, working code."
        ),
        LLMMessage(
            role="user",
            content=requirements
        )
    ]

    print(f"\n📤 Sending request to LLM...")
    print(f"Prompt length: {len(requirements)} chars\n")

    try:
        # Call LLM
        response = llm.complete(
            messages=messages,
            temperature=0.7,
            max_tokens=4000
        )

        print(f"✅ Response received")
        print(f"Model: {response.model}")
        print(f"Provider: {response.provider}")
        print(f"Usage: {response.usage}")
        print(f"Content length: {len(response.content)} chars\n")

    except Exception as e:
        print(f"❌ Error calling LLM: {e}")
        import traceback
        traceback.print_exc()
        return None, None

    # Parse response
    content = response.content.strip()

    # Clean up markdown code blocks if present
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

    if content.startswith("json"):
        content = content[4:].strip()

    try:
        notebook_data = json.loads(content)
        print(f"✅ Valid JSON parsed")
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        # Save for debugging
        debug_file = Path(__file__).parent / 'llm_response_debug.txt'
        with open(debug_file, 'w') as f:
            f.write(content)
        print(f"💾 Raw response saved to {debug_file}")
        return None, response.usage

    # Build full notebook structure
    notebook = {
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

    # Save generated notebook
    output_file = Path(__file__).parent / 'artemis_llm_generated_demo.ipynb'
    with open(output_file, 'w') as f:
        json.dump(notebook, f, indent=2)

    print(f"💾 Notebook saved to: {output_file}\n")

    return notebook, response.usage

def evaluate_notebook(notebook, name="Notebook"):
    """Evaluate notebook quality"""
    print("=" * 80)
    print(f"QUALITY EVALUATION: {name}")
    print("=" * 80)

    if not notebook:
        print("❌ No notebook to evaluate (generation failed)\n")
        return 0, 'F'

    cells = notebook.get('cells', [])
    num_cells = len(cells)
    num_code = sum(1 for c in cells if c.get('cell_type') == 'code')
    num_markdown = sum(1 for c in cells if c.get('cell_type') == 'markdown')

    print(f"📊 Cell counts:")
    print(f"  Total: {num_cells}")
    print(f"  Code: {num_code}")
    print(f"  Markdown: {num_markdown}")

    # Check for key components
    cell_contents = ' '.join(str(c.get('source', [])) for c in cells)

    has_imports = 'import' in cell_contents
    has_plotly = 'plotly' in cell_contents.lower()
    has_pandas = 'pandas' in cell_contents.lower()
    has_data_loading = 'json' in cell_contents and ('open' in cell_contents or 'read' in cell_contents)
    has_kanban = 'kanban' in cell_contents.lower()
    has_visualizations = sum(1 for c in cells if 'Figure' in str(c.get('source', [])) or 'chart' in str(c.get('source', [])).lower())

    print(f"\n✓ Key components:")
    print(f"  Imports: {'✅' if has_imports else '❌'}")
    print(f"  Plotly: {'✅' if has_plotly else '❌'}")
    print(f"  Pandas: {'✅' if has_pandas else '❌'}")
    print(f"  Data loading: {'✅' if has_data_loading else '❌'}")
    print(f"  Kanban integration: {'✅' if has_kanban else '❌'}")
    print(f"  Visualizations: {has_visualizations}")

    # Calculate quality score
    score = 0
    if num_cells >= 8: score += 2
    if num_code >= 5: score += 2
    if has_imports: score += 1
    if has_plotly: score += 2
    if has_pandas: score += 1
    if has_data_loading: score += 1
    if has_kanban: score += 1
    if has_visualizations >= 3: score += 1
    if has_visualizations >= 5: score += 1

    # Grade mapping
    grade_map = {
        10: 'A+', 9: 'A', 8: 'A-', 7: 'B+', 6: 'B', 5: 'B-',
        4: 'C', 3: 'D', 2: 'D', 1: 'F', 0: 'F'
    }
    grade = grade_map.get(min(score, 10), 'F')

    print(f"\n🎯 Quality Score: {score}/10")
    print(f"📝 Grade: {grade}")
    print()

    return score, grade

def compare_to_manual():
    """Compare to the manually created notebook"""
    print("=" * 80)
    print("BASELINE: MANUAL CREATION")
    print("=" * 80)

    manual_file = Path(__file__).parent.parent / 'demo' / 'artemis_pipeline_demo.ipynb'
    if manual_file.exists():
        with open(manual_file, 'r') as f:
            manual_notebook = json.load(f)

        manual_score, manual_grade = evaluate_notebook(manual_notebook, "Manual Creation")
        return manual_score, manual_grade
    else:
        print(f"⚠️  Manual notebook not found at {manual_file}")
        print(f"Using known baseline: Score 9/10 - Grade A\n")
        return 9, 'A'

def main():
    """Run the comparison test"""
    print("\n" + "=" * 80)
    print("ARTEMIS DEMO GENERATION QUALITY TEST")
    print("=" * 80)
    print("Comparing LLM-generated vs manual notebook creation\n")

    # Baseline: Manual creation
    manual_score, manual_grade = compare_to_manual()

    # Test: LLM generation using Artemis client
    llm_notebook, llm_usage = generate_with_artemis_llm()
    llm_score, llm_grade = evaluate_notebook(llm_notebook, "LLM Generated")

    # Final comparison
    print("=" * 80)
    print("FINAL COMPARISON")
    print("=" * 80)
    print(f"Manual Creation:  Score {manual_score}/10 - Grade {manual_grade}")
    print(f"LLM Generated:    Score {llm_score}/10 - Grade {llm_grade}")

    if llm_usage:
        print(f"\n💰 LLM API Usage:")
        print(f"  Prompt tokens: {llm_usage.get('prompt_tokens', 0)}")
        print(f"  Completion tokens: {llm_usage.get('completion_tokens', 0)}")
        print(f"  Total tokens: {llm_usage.get('total_tokens', 0)}")

    print(f"\n🎯 Result:")
    if llm_score >= manual_score:
        print("✅ SUCCESS: LLM matches/exceeds manual quality!")
        result = True
    elif llm_score >= manual_score - 2:
        print("⚠️  PARTIAL: LLM is close to manual quality")
        result = True
    else:
        print("❌ FAILURE: LLM significantly underperforms manual creation")
        print(f"   Gap: {manual_score - llm_score} points")
        result = False

    print("=" * 80 + "\n")

    return result

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
