import unittest
from chart_generator import generate_pipeline_chart, generate_cost_chart, generate_completion_rate_chart

class TestChartGeneration(unittest.TestCase):
    def test_generate_pipeline_chart(self):
        """Test pipeline chart generation with valid input data."""
        data = [100, 200, 300, 400, 500, 600, 700, 800]
        result = generate_pipeline_chart(data)
        self.assertIsNotNone(result)

    def test_generate_pipeline_chart_invalid_data(self):
        """Test pipeline chart generation with invalid input data raises exception."""
        data = 'invalid'
        with self.assertRaises(TypeError):
            generate_pipeline_chart(data)

    def test_generate_cost_chart(self):
        """Test cost chart generation with valid input data."""
        data = [10, 20, 30, 40, 50]
        result = generate_cost_chart(data)
        self.assertIsNotNone(result)

    def test_generate_completion_rate_chart(self):
        """Test completion rate chart generation with valid input data."""
        data = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = generate_completion_rate_chart(data)
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()