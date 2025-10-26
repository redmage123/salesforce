
import unittest
from presentation import HeroSlide

class TestHeroSlide(unittest.TestCase):

    def test_hero_slide_content(self):
        slide = HeroSlide()
        self.assertIn('Autonomous AI Development System', slide.content)

    def test_hero_slide_transition(self):
        slide = HeroSlide()
        self.assertTrue(slide.has_smooth_transition())

    def test_hero_slide_background(self):
        slide = HeroSlide()
        self.assertTrue(slide.has_professional_gradient_background())
