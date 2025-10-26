import unittest
from artemis_demo import LiveMetricsDashboard

class TestLiveMetricsDashboard(unittest.TestCase):
    def test_llm_cost_line_chart(self):
        dashboard = LiveMetricsDashboard()
        chart = dashboard.render_llm_cost_chart()
        self.assertEqual(chart.type, 'line')
        self.assertIn('LLM Cost Over Time', chart.options.title.text)

    def test_stage_completion_bar_chart(self):
        dashboard = LiveMetricsDashboard()
        chart = dashboard.render_stage_completion_chart()
        self.assertEqual(chart.type, 'bar')
        self.assertIn('Stage Completion Rates', chart.options.title.text)

    def test_success_rate_area_chart(self):
        dashboard = LiveMetricsDashboard()
        chart = dashboard.render_success_rate_chart()
        self.assertEqual(chart.type, 'area')
        self.assertIn('Success Rate Trends', chart.options.title.text)

    def test_invalid_data_handling(self):
        dashboard = LiveMetricsDashboard(data=None)
        with self.assertRaises(ValueError):
            dashboard.render_llm_cost_chart()

if __name__ == '__main__':
    unittest.main()