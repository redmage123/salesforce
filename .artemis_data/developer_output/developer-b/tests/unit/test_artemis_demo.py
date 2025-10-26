
import unittest
from unittest.mock import patch, MagicMock
from artemis_demo import ArtemisDemo

class TestArtemisDemo(unittest.TestCase):
    def setUp(self):
        self.demo = ArtemisDemo()

    @patch('artemis_demo.Chart')
    def test_initialize_charts(self, MockChart):
        # Test that charts are initialized correctly
        self.demo.initialize_charts()
        self.assertTrue(MockChart.called)

    @patch('artemis_demo.load_template')
    def test_load_templates(self, mock_load_template):
        # Test that templates are loaded correctly
        mock_load_template.side_effect = Exception('Template not found')
        with self.assertRaises(Exception):
            self.demo.load_templates()

    def test_slide_auto_advance(self):
        # Test if slides auto-advance correctly
        self.demo.current_slide = 0
        self.demo.auto_advance_slides()
        self.assertEqual(self.demo.current_slide, 1)

    @patch('artemis_demo.Chart')
    def test_render_pipeline_chart(self, MockChart):
        # Test pipeline chart rendering
        self.demo.render_pipeline_chart()
        self.assertTrue(MockChart.return_value.render.called)

    def test_navigation_controls(self):
        # Test navigation controls behavior
        self.demo.current_slide = 1
        self.demo.navigate('next')
        self.assertEqual(self.demo.current_slide, 2)
        self.demo.navigate('previous')
        self.assertEqual(self.demo.current_slide, 1)

if __name__ == '__main__':
    unittest.main()
