
import unittest
from presentation import PipelineSlide

class TestPipelineSlide(unittest.TestCase):

    def test_pipeline_chart_presence(self):
        slide = PipelineSlide()
        self.assertTrue(slide.contains_chart())

    def test_pipeline_chart_data(self):
        slide = PipelineSlide()
        self.assertEqual(len(slide.chart_data), 8)

    def test_pipeline_chart_animation(self):
        slide = PipelineSlide()
        self.assertTrue(slide.chart_has_animation())
