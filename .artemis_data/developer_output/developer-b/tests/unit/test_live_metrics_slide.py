
import unittest
from presentation import LiveMetricsSlide

class TestLiveMetricsSlide(unittest.TestCase):

    def test_llm_cost_over_time_chart(self):
        slide = LiveMetricsSlide()
        self.assertTrue(slide.has_llm_cost_line_chart())

    def test_stage_completion_rates_chart(self):
        slide = LiveMetricsSlide()
        self.assertTrue(slide.has_stage_completion_bar_chart())

    def test_success_rate_trends_chart(self):
        slide = LiveMetricsSlide()
        self.assertTrue(slide.has_success_rate_area_chart())
