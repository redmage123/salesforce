
from data_analyzer import analyze_pipeline_metrics
import unittest

class TestDataAnalyzer(unittest.TestCase):

    def test_analyze_pipeline_metrics_success(self):
        # Test successful analysis of valid metrics data
        metrics_data = {'execution_time': [10, 20, 30]}
        result = analyze_pipeline_metrics(metrics_data)
        self.assertIn('average_execution_time', result)

    def test_analyze_pipeline_metrics_missing_data(self):
        # Test handling of missing metrics data
        metrics_data = {}
        with self.assertRaises(KeyError):
            analyze_pipeline_metrics(metrics_data)

    def test_analyze_pipeline_metrics_invalid_data_type(self):
        # Test handling of invalid data types
        metrics_data = 'invalid_data'
        with self.assertRaises(TypeError):
            analyze_pipeline_metrics(metrics_data)
