import unittest
from artemis_demo import HeroSection

class TestHeroSection(unittest.TestCase):
    def test_render_hero_content(self):
        hero_section = HeroSection()
        content = hero_section.render()
        self.assertIn('Autonomous AI Development System', content)
        self.assertIn('<div class="hero">', content)

    def test_hero_content_structure(self):
        hero_section = HeroSection()
        content = hero_section.render()
        self.assertTrue(content.startswith('<div'))
        self.assertTrue(content.endswith('</div>'))

    def test_hero_content_fail_on_empty(self):
        hero_section = HeroSection(content="")
        with self.assertRaises(ValueError):
            hero_section.render()

if __name__ == '__main__':
    unittest.main()