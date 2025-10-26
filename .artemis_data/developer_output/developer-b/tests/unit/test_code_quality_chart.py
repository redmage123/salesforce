import unittest
from artemis_demo import CodeQualityChart

class TestCodeQualityChart(unittest.TestCase):
    def test_code_quality_chart_initialization(self):
        code_quality_chart = CodeQualityChart()
        chart_config = code_quality_chart.get_chart_config()
        self.assertEqual(chart_config['type'], 'radar')

    def test_tdd_solid_compliance_data(self):
        code_quality_chart = CodeQualityChart()
        data = code_quality_chart.get_data()
        self.assertIn('TDD', data)
        self.assertIn('SOLID', data)

if __name__ == '__main__':
    unittest.main()