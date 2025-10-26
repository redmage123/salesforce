import unittest
from artemis_demo import FeatureMetrics

class TestFeatureMetrics(unittest.TestCase):
    def test_cost_tracking_chart(self):
        feature_metrics = FeatureMetrics()
        chart = feature_metrics.render_cost_chart()
        self.assertIsNotNone(chart)
        self.assertEqual(chart.type, 'line')

    def test_sandboxing_data_chart(self):
        feature_metrics = FeatureMetrics()
        chart = feature_metrics.render_sandboxing_chart()
        self.assertIsInstance(chart.data, dict)
        self.assertGreater(len(chart.data['datasets']), 0)

    def test_learning_metrics_error_handling(self):
        feature_metrics = FeatureMetrics(data=None)
        with self.assertRaises(ValueError):
            feature_metrics.render_learning_chart()

if __name__ == '__main__':
    unittest.main()