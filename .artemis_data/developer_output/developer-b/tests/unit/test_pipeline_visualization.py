import unittest
from artemis_demo import PipelineVisualization

class TestPipelineVisualization(unittest.TestCase):
    def test_pipeline_stages_render_correctly(self):
        pipeline = PipelineVisualization()
        stages = pipeline.render_stages()
        self.assertEqual(len(stages), 8)
        self.assertIn('Stage 1', stages)
        self.assertIn('Stage 8', stages)

    def test_pipeline_chart_initialization(self):
        pipeline = PipelineVisualization()
        chart = pipeline.initialize_chart()
        self.assertIsNotNone(chart)
        self.assertEqual(chart.type, 'bar')

    def test_pipeline_data_validation(self):
        pipeline = PipelineVisualization(data=None)
        with self.assertRaises(ValueError):
            pipeline.render_stages()

if __name__ == '__main__':
    unittest.main()