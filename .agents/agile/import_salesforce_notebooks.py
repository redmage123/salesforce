#!/usr/bin/env python3
"""
Import Salesforce demo notebooks into RAG for developer examples.

These notebooks demonstrate the proper pattern for creating
interactive demonstrations with Jupyter:
1. Import libraries and set up data
2. Load/generate data
3. Perform analysis
4. Create visualizations
5. Generate HTML demo
6. Open demo in browser
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from rag_agent import RAGAgent
from document_reader import DocumentReader


def import_salesforce_notebooks():
    """Import Salesforce demo notebooks into RAG"""

    # Initialize RAG
    rag = RAGAgent()
    reader = DocumentReader()

    # Salesforce notebooks to import
    notebooks = [
        "../../src/agent_assist_rag_salesforce.ipynb",
        "../../src/salesforce_ai_revenue_intelligence.ipynb",
        "../../src/ai_integration_guide.ipynb",
        "../../src/contract_summarization.ipynb",
    ]

    imported_count = 0

    for notebook_path in notebooks:
        full_path = Path(__file__).parent / notebook_path

        if not full_path.exists():
            print(f"⚠️  Skipping {notebook_path} (not found)")
            continue

        try:
            # Read notebook content
            content = reader.read_document(str(full_path))

            # Store in RAG
            rag.store_artifact(
                artifact_type="notebook_example",
                card_id="salesforce-demo-examples",
                task_title=f"Salesforce Demo: {full_path.stem}",
                content=content,
                metadata={
                    "file_path": str(full_path),
                    "file_name": full_path.name,
                    "category": "salesforce_demo",
                    "description": f"Salesforce demonstration notebook showing proper demo creation pattern",
                    "tags": ["jupyter", "notebook", "demo", "visualization", "html", "chart.js", "plotly", "pandas"]
                }
            )

            print(f"✅ Imported: {full_path.name}")
            imported_count += 1

        except Exception as e:
            print(f"❌ Error importing {notebook_path}: {e}")

    print(f"\n✅ Imported {imported_count}/{len(notebooks)} notebooks to RAG")
    return imported_count


if __name__ == "__main__":
    print("Importing Salesforce demo notebooks into RAG...")
    print("=" * 60)
    count = import_salesforce_notebooks()
    print("=" * 60)
    print(f"✅ Import complete: {count} notebooks added to RAG")
    print("\nDevelopers can now query RAG for notebook examples:")
    print('  rag.query_similar("jupyter notebook demo", artifact_type="notebook_example")')
