
import unittest
from presentation import IntegrationSlide

class TestIntegrationSlide(unittest.TestCase):

    def test_supervisor_integration_pie_chart(self):
        slide = IntegrationSlide()
        self.assertTrue(slide.has_supervisor_integration_pie_chart())
