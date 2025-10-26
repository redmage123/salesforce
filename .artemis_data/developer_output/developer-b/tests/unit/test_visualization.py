
from visualization import generate_interactive_notebook
import unittest

class TestVisualization(unittest.TestCase):

    def test_generate_interactive_notebook_success(self):
        # Test successful generation of a Jupyter notebook
        analysis_results = {'average_execution_time': 20}
        notebook = generate_interactive_notebook(analysis_results)
        self.assertIsInstance(notebook, str)
        self.assertIn('notebook', notebook)

    def test_generate_interactive_notebook_empty_results(self):
        # Test handling of empty analysis results
        analysis_results = {}
        with self.assertRaises(ValueError):
            generate_interactive_notebook(analysis_results)
