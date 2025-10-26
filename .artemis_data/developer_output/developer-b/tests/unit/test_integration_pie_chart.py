import unittest
from artemis_demo import IntegrationChart

class TestIntegrationChart(unittest.TestCase):
    def test_integration_pie_chart_initialization(self):
        integration_chart = IntegrationChart()
        chart_config = integration_chart.get_chart_config()
        self.assertEqual(chart_config['type'], 'pie')

    def test_integration_data_completeness(self):
        integration_chart = IntegrationChart()
        data = integration_chart.get_data()
        self.assertGreater(len(data), 0)

if __name__ == '__main__':
    unittest.main()