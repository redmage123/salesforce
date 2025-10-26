import unittest
from artemis_demo import CodeQualityMetrics

class TestCodeQualityMetrics(unittest.TestCase):
    def test_tdd_solid_compliance_radar_chart(self):
        code_quality = CodeQualityMetrics()
        chart = code_quality.render_compliance_chart()
        self.assertEqual(chart.type, 'radar')
        self.assertIn('TDD & SOLID Compliance', chart.options.title.text)

    def test_compliance_data_error_handling(self):
        code_quality = CodeQualityMetrics(data=None)
        with self.assertRaises(ValueError):
            code_quality.render_compliance_chart()

if __name__ == '__main__':
    unittest.main()