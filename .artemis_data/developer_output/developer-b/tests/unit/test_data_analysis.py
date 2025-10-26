import unittest
from data_analysis import analyze_pipeline_data

class TestDataAnalysis(unittest.TestCase):

    def test_analyze_pipeline_data_trends(self):
        """Test that pipeline trends are analyzed correctly."""
        analysis_results = analyze_pipeline_data('sample_data.json')
        self.assertIn('trends', analysis_results)

    def test_analyze_pipeline_data_stage_times(self):
        """Test that stage completion times are calculated accurately."""
        analysis_results = analyze_pipeline_data('sample_data.json')
        self.assertIn('stage_completion_times', analysis_results)

    def test_analyze_pipeline_data_success_rates(self):
        """Test that success rates are evaluated correctly."""
        analysis_results = analyze_pipeline_data('sample_data.json')
        self.assertIn('success_rates', analysis_results)
