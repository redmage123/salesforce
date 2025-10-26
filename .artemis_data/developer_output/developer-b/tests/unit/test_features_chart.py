import unittest
from artemis_demo import FeaturesChart

class TestFeaturesChart(unittest.TestCase):
    def test_features_chart_initialization(self):
        features_chart = FeaturesChart()
        chart_config = features_chart.get_chart_config()
        self.assertEqual(chart_config['type'], 'line')

    def test_cost_tracking_data(self):
        features_chart = FeaturesChart()
        cost_data = features_chart.get_cost_data()
        self.assertGreater(len(cost_data), 0)

if __name__ == '__main__':
    unittest.main()