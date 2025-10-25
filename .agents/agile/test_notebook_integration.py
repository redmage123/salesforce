#!/usr/bin/env python3
"""
Test Jupyter Notebook Integration

Tests the complete notebook functionality:
- JupyterNotebookReader
- JupyterNotebookWriter
- NotebookBuilder
- DocumentReader integration
- Notebook generation stage
"""

import os
import json
import tempfile
from pathlib import Path

# Import modules to test
from jupyter_notebook_handler import (
    NotebookBuilder,
    JupyterNotebookReader,
    JupyterNotebookWriter,
    create_data_analysis_notebook,
    create_ml_notebook
)
from document_reader import DocumentReader
from notebook_generation_stage import NotebookGenerationStage


def test_notebook_builder():
    """Test NotebookBuilder creates valid notebooks"""
    print("Testing NotebookBuilder...")

    builder = NotebookBuilder("Test Notebook")

    # Add various cell types (title cell added automatically)
    builder.add_markdown("## Introduction\n\nThis is a test.")
    builder.add_code("import numpy as np\nprint('Hello')")
    builder.add_section("Analysis", "Data analysis section")
    builder.add_code("data = [1, 2, 3]\nprint(data)")

    notebook = builder.build()

    # Validate structure
    assert 'cells' in notebook, "Notebook missing cells"
    assert 'metadata' in notebook, "Notebook missing metadata"
    assert 'nbformat' in notebook, "Notebook missing nbformat"
    # 1 title + 1 intro + 1 code + 1 section + 1 code = 5 cells
    assert len(notebook['cells']) == 5, f"Expected 5 cells, got {len(notebook['cells'])}"

    # Validate cell types
    assert notebook['cells'][0]['cell_type'] == 'markdown', "First cell should be markdown"
    assert notebook['cells'][2]['cell_type'] == 'code', "Third cell should be code"

    print("✅ NotebookBuilder test passed")
    return True


def test_notebook_write_read():
    """Test writing and reading notebooks"""
    print("\nTesting write/read cycle...")

    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.ipynb', delete=False, mode='w') as f:
        temp_path = f.name

    try:
        # Create a notebook (title added automatically)
        builder = NotebookBuilder("Read/Write Test")
        builder.add_code("x = 42")
        builder.add_code("print(x)")

        notebook = builder.build()

        # Write it
        writer = JupyterNotebookWriter()
        writer.write_notebook(notebook, temp_path)

        assert os.path.exists(temp_path), "Notebook file not created"

        # Read it back
        reader = JupyterNotebookReader()
        loaded_notebook = reader.read_notebook(temp_path)

        # Validate (1 title + 2 code = 3 cells)
        assert len(loaded_notebook['cells']) == 3, f"Expected 3 cells, got {len(loaded_notebook['cells'])}"
        assert loaded_notebook['cells'][0]['source'][0].startswith('#'), "Markdown content mismatch"

        # Test summary
        summary = reader.get_notebook_summary(loaded_notebook)
        assert summary['total_cells'] == 3, "Summary cell count wrong"
        assert summary['code_cells'] == 2, "Summary code cell count wrong"
        assert summary['markdown_cells'] == 1, "Summary markdown cell count wrong"

        print("✅ Write/Read test passed")
        return True

    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_document_reader_integration():
    """Test DocumentReader can read .ipynb files"""
    print("\nTesting DocumentReader integration...")

    # Create a test notebook
    with tempfile.NamedTemporaryFile(suffix='.ipynb', delete=False, mode='w') as f:
        temp_path = f.name

    try:
        # Create notebook with content
        builder = NotebookBuilder("DocumentReader Test")
        builder.add_markdown("# Document Reader Test\n\nTesting notebook reading")
        builder.add_code("import pandas as pd\ndf = pd.DataFrame({'a': [1, 2, 3]})")
        builder.add_markdown("## Results\n\nSome analysis results")

        notebook = builder.build()

        writer = JupyterNotebookWriter()
        writer.write_notebook(notebook, temp_path)

        # Read with DocumentReader
        doc_reader = DocumentReader(verbose=False)
        text = doc_reader.read_document(temp_path)

        # Validate extracted text
        assert len(text) > 0, "No text extracted"
        assert "JUPYTER NOTEBOOK" in text, "Missing notebook header"
        assert "DocumentReader Test" in text or "Document Reader Test" in text, "Missing title"
        assert "import pandas" in text, "Missing code content"
        assert "NOTEBOOK SUMMARY" in text, "Missing summary"

        # Check supported formats
        supported = doc_reader.get_supported_formats()
        assert '.ipynb' in supported['Always Supported'], "Jupyter notebooks not in supported formats"

        print("✅ DocumentReader integration test passed")
        return True

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_template_functions():
    """Test template notebook generation functions"""
    print("\nTesting template functions...")

    # Test data analysis template
    notebook = create_data_analysis_notebook(
        title="Test Analysis",
        data_source="test.csv",
        analysis_steps=["Load data", "Clean data", "Analyze"]
    )

    assert notebook is not None, "Data analysis notebook is None"
    assert len(notebook['cells']) > 0, "No cells in data analysis notebook"

    # Test ML template
    notebook = create_ml_notebook(
        title="Test ML",
        model_type="classification",
        features=["feature1", "feature2"]
    )

    assert notebook is not None, "ML notebook is None"
    assert len(notebook['cells']) > 0, "No cells in ML notebook"

    print("✅ Template function tests passed")
    return True


def test_notebook_generation_stage():
    """Test NotebookGenerationStage"""
    print("\nTesting NotebookGenerationStage...")

    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        stage = NotebookGenerationStage(output_dir=temp_dir)

        # Test data analysis card
        card = {
            'id': 'test-001',
            'title': 'Analyze Sales Data',
            'description': 'Perform data analysis on sales dataset using pandas and matplotlib',
            'story_points': 5
        }

        result = stage.execute(card, context={'data_source': 'sales.csv'})

        assert result['status'] == 'success', "Stage execution failed"
        assert 'notebook_path' in result, "No notebook path in result"
        assert os.path.exists(result['notebook_path']), "Notebook file not created"
        assert result['notebook_type'] == 'data_analysis', f"Wrong type: {result['notebook_type']}"

        # Verify the notebook is valid JSON
        with open(result['notebook_path'], 'r') as f:
            notebook = json.load(f)
            assert 'cells' in notebook, "Invalid notebook structure"

        print(f"✅ NotebookGenerationStage test passed - created {result['notebook_path']}")
        return True


def test_notebook_type_detection():
    """Test notebook type detection from card content"""
    print("\nTesting notebook type detection...")

    with tempfile.TemporaryDirectory() as temp_dir:
        stage = NotebookGenerationStage(output_dir=temp_dir)

        # Test ML detection
        ml_card = {
            'id': 'ml-001',
            'title': 'Train Classification Model',
            'description': 'Build and train a machine learning model for classification'
        }

        notebook_type = stage._determine_notebook_type(ml_card, {})
        assert notebook_type == 'machine_learning', f"Expected ML type, got {notebook_type}"

        # Test API demo detection
        api_card = {
            'id': 'api-001',
            'title': 'API Demo',
            'description': 'Create demo for REST API endpoint usage'
        }

        notebook_type = stage._determine_notebook_type(api_card, {})
        assert notebook_type == 'api_demo', f"Expected API demo type, got {notebook_type}"

        # Test general fallback
        general_card = {
            'id': 'gen-001',
            'title': 'General Task',
            'description': 'Some general implementation'
        }

        notebook_type = stage._determine_notebook_type(general_card, {})
        assert notebook_type == 'general', f"Expected general type, got {notebook_type}"

        print("✅ Notebook type detection test passed")
        return True


def run_all_tests():
    """Run all notebook integration tests"""
    print("=" * 80)
    print("JUPYTER NOTEBOOK INTEGRATION TESTS")
    print("=" * 80)

    tests = [
        ("NotebookBuilder", test_notebook_builder),
        ("Write/Read Cycle", test_notebook_write_read),
        ("DocumentReader Integration", test_document_reader_integration),
        ("Template Functions", test_template_functions),
        ("Notebook Generation Stage", test_notebook_generation_stage),
        ("Notebook Type Detection", test_notebook_type_detection)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
