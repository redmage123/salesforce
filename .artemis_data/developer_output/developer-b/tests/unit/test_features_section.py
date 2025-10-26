
from presentation import FeaturesSection
import unittest

class TestFeaturesSection(unittest.TestCase):
    def setUp(self):
        self.features_section = FeaturesSection()

    def test_features_metrics_exist(self):
        metrics = self.features_section.get_metrics()
        self.assertIsNotNone(metrics, "Metrics should not be None")

    def test_features_chart_rendering(self):
        chart = self.features_section.render_chart()
        self.assertIsNotNone(chart, "Features chart should be rendered")

if __name__ == '__main__':
    unittest.main()
