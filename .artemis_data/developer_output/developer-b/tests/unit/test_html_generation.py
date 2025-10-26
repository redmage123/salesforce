import unittest
from html_generator import generate_html_presentation

class TestHtmlGeneration(unittest.TestCase):
    def test_html_generation_creates_file(self):
        """Test that the HTML generation function creates a file at the specified path."""
        output_path = '/tmp/artemis_demo_chartjs.html'
        # Assume generate_html_presentation returns True if file creation is successful
        result = generate_html_presentation(output_path)
        self.assertTrue(result)

    def test_html_contains_required_sections(self):
        """Test that the generated HTML contains all required sections."""
        output_path = '/tmp/artemis_demo_chartjs_test.html'
        generate_html_presentation(output_path)
        with open(output_path, 'r') as file:
            content = file.read()
        self.assertIn('HERO: What is Artemis?', content)
        self.assertIn('PIPELINE', content)
        self.assertIn('FEATURES', content)
        self.assertIn('LIVE METRICS', content)
        self.assertIn('INTEGRATION', content)
        self.assertIn('CODE QUALITY', content)
        self.assertIn('RESULTS', content)

    def test_invalid_output_path(self):
        """Test that an invalid output path raises an appropriate exception."""
        with self.assertRaises(ValueError):
            generate_html_presentation('invalid_path')

if __name__ == '__main__':
    unittest.main()