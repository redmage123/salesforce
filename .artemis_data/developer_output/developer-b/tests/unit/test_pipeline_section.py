import unittest
from artemis_demo import PipelineSection

class TestPipelineSection(unittest.TestCase):
    def setUp(self):
        self.pipeline_section = PipelineSection()

    def test_pipeline_stages(self):
        self.assertEqual(len(self.pipeline_section.get_stages()), 8)

    def test_pipeline_chart_render(self):
        self.assertTrue(self.pipeline_section.render_chart())

if __name__ == '__main__':
    unittest.main()