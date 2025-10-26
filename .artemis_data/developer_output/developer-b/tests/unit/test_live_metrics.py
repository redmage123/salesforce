import unittest
from artemis_demo import LiveMetrics

class TestLiveMetrics(unittest.TestCase):
    def test_llm_cost_chart(self):
        live_metrics = LiveMetrics()
        llm_cost_chart = live_metrics.get_llm_cost_chart()
        self.assertEqual(llm_cost_chart['type'], 'line')

    def test_completion_rates_chart(self):
        live_metrics = LiveMetrics()
        completion_rates_chart = live_metrics.get_completion_rates_chart()
        self.assertEqual(completion_rates_chart['type'], 'bar')

    def test_success_rate_trends_chart(self):
        live_metrics = LiveMetrics()
        success_rate_trends_chart = live_metrics.get_success_rate_trends_chart()
        self.assertEqual(success_rate_trends_chart['type'], 'line')

if __name__ == '__main__':
    unittest.main()