import unittest

from utils.table_status import get_status_style


class TableStatusTests(unittest.TestCase):
    def test_computed_status_uses_success_palette(self):
        style = get_status_style("已计算")

        self.assertEqual(style.label, "已计算")
        self.assertEqual(style.foreground, "#166534")
        self.assertEqual(style.background, "#dcfce7")

    def test_error_status_uses_error_palette(self):
        style = get_status_style("计算错误")

        self.assertEqual(style.foreground, "#991b1b")
        self.assertEqual(style.background, "#fee2e2")

    def test_unknown_status_falls_back_to_neutral_palette(self):
        style = get_status_style("未计算")

        self.assertEqual(style.foreground, "#475569")
        self.assertEqual(style.background, "#f1f5f9")


if __name__ == "__main__":
    unittest.main()
