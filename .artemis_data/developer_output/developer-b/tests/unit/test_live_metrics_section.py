import unittest
from artemis_demo import LiveMetricsSection

class TestLiveMetricsSection(unittest.TestCase):
    def setUp(self):
        self.live_metrics_section = LiveMetricsSection()

    def test_llm_cost_over_time_chart(self):
        self.assertTrue(self.live_metrics_section.render_llm_cost_chart())

    def test_stage_completion_rates_chart(self):
        self.assertTrue(self.live_metrics_section.render_stage_completion_chart())

    def test_success_rate_trends_chart(self):
        self.assertTrue(self.live_metrics_section.render_success_rate_trends_chart())

if __name__ == '__main__':
    unittest.main()