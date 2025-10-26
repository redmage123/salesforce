
from presentation import CodeQualitySection
import unittest

class TestCodeQualitySection(unittest.TestCase):
    def setUp(self):
        self.code_quality_section = CodeQualitySection()

    def test_tdd_compliance_chart_exists(self):
        chart = self.code_quality_section.render_tdd_compliance_chart()
        self.assertIsNotNone(chart, "TDD compliance chart should be rendered")

    def test_solid_principles_chart_exists(self):
        chart = self.code_quality_section.render_solid_principles_chart()
        self.assertIsNotNone(chart, "SOLID principles chart should be rendered")

if __name__ == '__main__':
    unittest.main()
