
import unittest
from presentation import CodeQualitySlide

class TestCodeQualitySlide(unittest.TestCase):

    def test_tdd_compliance_radar_chart(self):
        slide = CodeQualitySlide()
        self.assertTrue(slide.has_tdd_radar_chart())

    def test_solid_principles_radar_chart(self):
        slide = CodeQualitySlide()
        self.assertTrue(slide.has_solid_principles_radar_chart())
