
import unittest
from presentation import FeaturesSlide

class TestFeaturesSlide(unittest.TestCase):

    def test_features_slide_cost_tracking_chart(self):
        slide = FeaturesSlide()
        self.assertTrue(slide.has_cost_tracking_chart())

    def test_features_slide_sandboxing_metrics(self):
        slide = FeaturesSlide()
        self.assertTrue(slide.displays_sandboxing_metrics())

    def test_features_slide_learning_metrics(self):
        slide = FeaturesSlide()
        self.assertTrue(slide.displays_learning_metrics())
