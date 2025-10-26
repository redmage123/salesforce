import unittest
from artemis_demo import ResultsMetrics

class TestResultsMetrics(unittest.TestCase):
    def test_real_metrics_rendering(self):
        results_metrics = ResultsMetrics()
        data = results_metrics.render_real_metrics()
        self.assertTrue('Recent Run Metrics' in data)

    def test_results_data_validation(self):
        results_metrics = ResultsMetrics(data=None)
        with self.assertRaises(ValueError):
            results_metrics.render_real_metrics()

if __name__ == '__main__':
    unittest.main()