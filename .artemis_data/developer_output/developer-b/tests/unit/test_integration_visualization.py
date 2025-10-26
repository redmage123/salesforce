import unittest
from artemis_demo import IntegrationVisualization

class TestIntegrationVisualization(unittest.TestCase):
    def test_supervisor_integration_pie_chart(self):
        integration = IntegrationVisualization()
        chart = integration.render_supervisor_integration_chart()
        self.assertEqual(chart.type, 'pie')
        self.assertIn('Supervisor Integration', chart.options.title.text)

    def test_integration_data_validation(self):
        integration = IntegrationVisualization(data=None)
        with self.assertRaises(ValueError):
            integration.render_supervisor_integration_chart()

if __name__ == '__main__':
    unittest.main()