# File: tests/unit/test_artemis_demo_chartjs.py
import unittest
from artemis_demo import ArtemisDemo

class TestArtemisDemo(unittest.TestCase):

    def setUp(self):
        self.demo = ArtemisDemo()

    def test_hero_slide_content(self):
        # Test that the HERO slide content is correctly initialized
        self.assertEqual(self.demo.hero_slide_content(), 'What is Artemis? (Autonomous AI Development System)')

    def test_pipeline_chart_initialization(self):
        # Test that the pipeline chart is initialized with 8 stages
        pipeline_chart = self.demo.initialize_pipeline_chart()
        self.assertEqual(len(pipeline_chart.data['labels']), 8)

    def test_real_time_dashboard_initialization(self):
        # Test that real-time dashboard initializes line, bar, and area charts
        dashboard = self.demo.initialize_real_time_dashboard()
        self.assertTrue('LLM cost over time' in dashboard)
        self.assertTrue('Stage completion rates' in dashboard)
        self.assertTrue('Success rate trends' in dashboard)

    def test_integration_pie_chart(self):
        # Test that the integration pie chart is initialized
        pie_chart = self.demo.initialize_integration_pie_chart()
        self.assertTrue('Supervisor Integration' in pie_chart.data['labels'])

    def test_code_quality_radar_chart(self):
        # Test that the code quality radar chart is initialized with TDD and SOLID principles
        radar_chart = self.demo.initialize_code_quality_radar_chart()
        self.assertTrue('TDD compliance' in radar_chart.data['labels'])
        self.assertTrue('SOLID principles' in radar_chart.data['labels'])

    def test_results_real_metrics_display(self):
        # Test that the results display real metrics from recent runs
        metrics = self.demo.display_real_metrics()
        self.assertGreater(len(metrics), 0)

if __name__ == '__main__':
    unittest.main()
