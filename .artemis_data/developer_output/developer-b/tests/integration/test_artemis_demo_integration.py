
import unittest
from artemis_demo import ArtemisDemo

class TestArtemisDemoIntegration(unittest.TestCase):
    def setUp(self):
        self.demo = ArtemisDemo()

    def test_full_demo_execution(self):
        # Test full execution of the demo
        success = self.demo.run_full_demo()
        self.assertTrue(success)

    def test_chart_interactivity(self):
        # Test chart interactivity and responsiveness
        self.demo.render_all_charts()
        self.assertTrue(self.demo.charts_interactive)

if __name__ == '__main__':
    unittest.main()
