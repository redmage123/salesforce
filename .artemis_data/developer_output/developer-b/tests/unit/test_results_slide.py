
import unittest
from presentation import ResultsSlide

class TestResultsSlide(unittest.TestCase):

    def test_results_slide_metrics_display(self):
        slide = ResultsSlide()
        self.assertTrue(slide.displays_real_metrics())

    def test_results_slide_data_accuracy(self):
        slide = ResultsSlide()
        self.assertTrue(slide.data_is_accurate())
