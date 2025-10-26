import unittest
from visualizer import plot_pipeline_performance

class TestVisualizer(unittest.TestCase):
    def test_plot_pipeline_performance_success(self):
        # Test that valid plots are created
        self.assertTrue(plot_pipeline_performance({'data': 'valid_data'}))

    def test_plot_pipeline_performance_no_data(self):
        # Test plot creation with no data
        with self.assertRaises(ValueError):
            plot_pipeline_performance({})

    def test_plot_pipeline_performance_invalid_data(self):
        # Test plot creation with invalid data
        with self.assertRaises(TypeError):
            plot_pipeline_performance('invalid_data')