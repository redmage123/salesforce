
from presentation import ResultsSection
import unittest

class TestResultsSection(unittest.TestCase):
    def setUp(self):
        self.results_section = ResultsSection()

    def test_real_metrics_data_exists(self):
        data = self.results_section.get_real_metrics_data()
        self.assertIsNotNone(data, "Real metrics data should not be None")

    def test_results_chart_rendering(self):
        chart = self.results_section.render_results_chart()
        self.assertIsNotNone(chart, "Results chart should be rendered")

if __name__ == '__main__':
    unittest.main()
