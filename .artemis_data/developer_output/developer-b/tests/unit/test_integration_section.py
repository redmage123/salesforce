
from presentation import IntegrationSection
import unittest

class TestIntegrationSection(unittest.TestCase):
    def setUp(self):
        self.integration_section = IntegrationSection()

    def test_supervisor_integration_pie_chart_exists(self):
        chart = self.integration_section.render_pie_chart()
        self.assertIsNotNone(chart, "Supervisor integration pie chart should be rendered")

if __name__ == '__main__':
    unittest.main()
