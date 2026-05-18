import unittest

from utils.fluent_theme import get_fluent_theme


class FluentThemeTests(unittest.TestCase):
    def test_uses_soft_neutral_window_background(self):
        theme = get_fluent_theme()

        self.assertEqual(theme.window_background, "#f3f3f3")

    def test_uses_single_blue_primary_accent(self):
        theme = get_fluent_theme()

        self.assertEqual(theme.primary_accent, "#0f6cbd")
        self.assertEqual(theme.selection_fill, "#cfe8ff")

    def test_uses_elevated_surface_layers(self):
        theme = get_fluent_theme()

        self.assertEqual(theme.surface_primary, "#ffffff")
        self.assertEqual(theme.surface_secondary, "#fafafa")
        self.assertEqual(theme.stroke_subtle, "#e5e5e5")


if __name__ == "__main__":
    unittest.main()
