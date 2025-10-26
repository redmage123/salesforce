import unittest
from data_loader import load_execution_data
from data_analysis import analyze_pipeline_data
from visualization import create_visualizations

class TestPipelineAnalysisWorkflow(unittest.TestCase):

    def test_full_workflow_success(self):
        """Test the full pipeline analysis workflow from loading data to visualizing results."""
        data = load_execution_data('sample_data.json')
        analysis_results = analyze_pipeline_data(data)
        result = create_visualizations(analysis_results)
        self.assertTrue(result)

    def test_workflow_with_invalid_data(self):
        """Test the workflow handling with invalid data input."""
        data = load_execution_data('invalid_data.json')
        with self.assertRaises(ValueError):
            analyze_pipeline_data(data)
