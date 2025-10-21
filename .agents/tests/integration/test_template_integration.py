#!/usr/bin/env python3
"""
Integration Test Template

Use this template for testing interactions between components.
Integration tests should:
- Test component interactions
- Test file I/O operations
- Test external command execution
- Test data flow through multiple functions
- Be reasonably fast (< 10 seconds each)
"""

import pytest
import os
import json
import subprocess
import tempfile
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestComponentIntegration:
    """Integration tests for component interactions"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        """Setup and teardown for each test"""
        # Setup: Create test environment
        self.test_dir = tmp_path / "integration_test"
        self.test_dir.mkdir()

        yield

        # Teardown: Clean up test environment
        # (tmp_path is automatically cleaned by pytest)

    # FILE I/O INTEGRATION TESTS
    def test_read_write_json_file(self, tmp_path):
        """Test reading and writing JSON files"""
        # Arrange
        test_file = tmp_path / "test_data.json"
        test_data = {"key": "value", "number": 42}

        # Act - Write
        with open(test_file, 'w') as f:
            json.dump(test_data, f)

        # Act - Read
        with open(test_file, 'r') as f:
            loaded_data = json.load(f)

        # Assert
        assert loaded_data == test_data
        assert test_file.exists()

    def test_file_creation_and_modification(self, tmp_path):
        """Test creating and modifying files"""
        # Arrange
        test_file = tmp_path / "test.txt"

        # Act - Create
        test_file.write_text("initial content")

        # Act - Modify
        content = test_file.read_text()
        test_file.write_text(content + "\nmodified")

        # Assert
        final_content = test_file.read_text()
        assert "initial content" in final_content
        assert "modified" in final_content

    # COMMAND EXECUTION INTEGRATION TESTS
    def test_execute_bash_command(self):
        """Test executing bash commands"""
        # Act
        result = subprocess.run(
            ["echo", "test"],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Assert
        assert result.returncode == 0
        assert "test" in result.stdout

    def test_execute_python_script(self, tmp_path):
        """Test executing a Python script"""
        # Arrange - Create a test script
        script_file = tmp_path / "test_script.py"
        script_file.write_text("print('Script executed')")

        # Act
        result = subprocess.run(
            ["python3", str(script_file)],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Assert
        assert result.returncode == 0
        assert "Script executed" in result.stdout

    # WORKFLOW INTEGRATION TESTS
    def test_multi_step_workflow(self, tmp_path):
        """Test a complete workflow with multiple steps"""
        # Step 1: Create input file
        input_file = tmp_path / "input.json"
        input_data = {"value": 10}
        input_file.write_text(json.dumps(input_data))

        # Step 2: Process the file (example: multiply value by 2)
        data = json.loads(input_file.read_text())
        data['value'] *= 2

        # Step 3: Write output file
        output_file = tmp_path / "output.json"
        output_file.write_text(json.dumps(data))

        # Step 4: Verify results
        result = json.loads(output_file.read_text())
        assert result['value'] == 20

    def test_error_handling_in_workflow(self, tmp_path):
        """Test error handling across component interactions"""
        # Arrange - Create a file that will cause an error
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json")

        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            with open(bad_file, 'r') as f:
                json.load(f)

    # BACKUP AND ROLLBACK INTEGRATION TESTS
    def test_backup_and_restore(self, tmp_path):
        """Test backup and restore functionality"""
        # Arrange
        original_file = tmp_path / "original.txt"
        original_content = "original content"
        original_file.write_text(original_content)

        # Act - Create backup
        backup_file = tmp_path / "original.txt.backup"
        backup_file.write_text(original_file.read_text())

        # Act - Modify original
        original_file.write_text("modified content")

        # Act - Restore from backup
        original_file.write_text(backup_file.read_text())

        # Assert
        assert original_file.read_text() == original_content

    # VALIDATION INTEGRATION TESTS
    def test_multi_layer_validation(self, tmp_path):
        """Test multiple validation layers"""
        # Arrange
        test_file = tmp_path / "validate.json"
        test_data = {
            "name": "test",
            "value": 42,
            "items": [1, 2, 3]
        }
        test_file.write_text(json.dumps(test_data))

        # Act - Validation Layer 1: File exists
        assert test_file.exists()

        # Act - Validation Layer 2: Valid JSON
        data = json.loads(test_file.read_text())

        # Act - Validation Layer 3: Required fields present
        assert "name" in data
        assert "value" in data

        # Act - Validation Layer 4: Field types correct
        assert isinstance(data['name'], str)
        assert isinstance(data['value'], int)
        assert isinstance(data['items'], list)

        # Act - Validation Layer 5: Value ranges
        assert len(data['items']) > 0

    # ERROR RECOVERY INTEGRATION TESTS
    def test_command_timeout_handling(self):
        """Test handling of command timeouts"""
        # Act & Assert
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess.run(
                ["sleep", "10"],
                timeout=1  # Will timeout after 1 second
            )

    def test_file_permission_error_handling(self, tmp_path):
        """Test handling of file permission errors"""
        # Arrange
        readonly_file = tmp_path / "readonly.txt"
        readonly_file.write_text("content")
        readonly_file.chmod(0o444)  # Read-only

        # Act & Assert
        with pytest.raises(PermissionError):
            readonly_file.write_text("new content")

        # Cleanup
        readonly_file.chmod(0o644)


class TestPipelineIntegration:
    """Integration tests for pipeline components"""

    def test_orchestrator_to_developer_flow(self, tmp_path):
        """Test task flow from Orchestrator to Developer"""
        # Arrange - Orchestrator creates task spec
        task_spec_file = tmp_path / "task_spec.json"
        task_spec = {
            "task_id": "test-001",
            "title": "Test Task",
            "acceptance_criteria": [
                {"criterion": "Works correctly", "status": "pending"}
            ]
        }
        task_spec_file.write_text(json.dumps(task_spec, indent=2))

        # Act - Developer reads task spec
        spec = json.loads(task_spec_file.read_text())

        # Act - Developer creates solution
        solution_file = tmp_path / "solution.json"
        solution = {
            "task_id": spec['task_id'],
            "implementation": "code here",
            "tests_passing": True
        }
        solution_file.write_text(json.dumps(solution, indent=2))

        # Assert
        assert solution_file.exists()
        loaded_solution = json.loads(solution_file.read_text())
        assert loaded_solution['task_id'] == task_spec['task_id']

    def test_notebook_execution_pipeline(self, tmp_path):
        """Test notebook execution and HTML generation"""
        # This is a simplified example - real test would use actual notebook
        # Arrange
        notebook_file = tmp_path / "test.ipynb"
        notebook_data = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print('hello')"]
                }
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5
        }
        notebook_file.write_text(json.dumps(notebook_data))

        # Act - Simulate notebook execution
        # (In real test, would use jupyter nbconvert)
        html_file = tmp_path / "output.html"
        html_file.write_text("<html><body>hello</body></html>")

        # Assert - Validate HTML output
        assert html_file.exists()
        html_content = html_file.read_text()
        assert "<html>" in html_content
        assert "hello" in html_content

    def test_kanban_board_integration(self, tmp_path):
        """Test Kanban board operations"""
        # Arrange - Create minimal board structure
        board_file = tmp_path / "kanban_board.json"
        board_data = {
            "columns": [
                {"column_id": "backlog", "cards": []},
                {"column_id": "development", "cards": []}
            ]
        }
        board_file.write_text(json.dumps(board_data, indent=2))

        # Act - Add card to backlog
        board = json.loads(board_file.read_text())
        card = {"card_id": "card-001", "title": "Test Card"}
        board['columns'][0]['cards'].append(card)

        # Act - Move card to development
        card = board['columns'][0]['cards'].pop(0)
        board['columns'][1]['cards'].append(card)

        # Act - Save updated board
        board_file.write_text(json.dumps(board, indent=2))

        # Assert
        updated_board = json.loads(board_file.read_text())
        assert len(updated_board['columns'][0]['cards']) == 0  # Backlog empty
        assert len(updated_board['columns'][1]['cards']) == 1  # Development has card


# FIXTURES FOR INTEGRATION TESTS
@pytest.fixture
def sample_notebook(tmp_path):
    """Create a sample Jupyter notebook for testing"""
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "source": ["# Test Notebook"]
            },
            {
                "cell_type": "code",
                "source": ["x = 1 + 1\nprint(x)"],
                "outputs": []
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5
    }

    notebook_file = tmp_path / "test_notebook.ipynb"
    notebook_file.write_text(json.dumps(notebook, indent=2))
    return notebook_file


@pytest.fixture
def sample_directory_structure(tmp_path):
    """Create a sample directory structure for testing"""
    structure = tmp_path / "project"
    structure.mkdir()

    (structure / "src").mkdir()
    (structure / "tests").mkdir()
    (structure / "docs").mkdir()

    (structure / "src" / "main.py").write_text("print('main')")
    (structure / "tests" / "test_main.py").write_text("def test(): pass")

    return structure
