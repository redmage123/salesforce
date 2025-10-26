import unittest
from presentation import CodeQualityRadarChart

class TestCodeQualityRadarChart(unittest.TestCase):
    def setUp(self):
        self.quality_chart = CodeQualityRadarChart()

    def test_radar_chart_render(self):
        chart = self.quality_chart.render()
        self.assertIn('Chart.js', chart)

if __name__ == '__main__':
    unittest.main()