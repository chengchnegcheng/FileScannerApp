import unittest

from utils.ui_layout import get_minimal_workflow_layout


class UiLayoutTests(unittest.TestCase):
    def test_primary_actions_focus_on_scan_flow(self):
        layout = get_minimal_workflow_layout()

        self.assertEqual(layout.primary_actions, ["select", "scan", "stop"])

    def test_secondary_actions_hold_post_scan_tools(self):
        layout = get_minimal_workflow_layout()

        self.assertEqual(layout.secondary_actions, ["select_all", "calculate", "export", "backup"])

    def test_footer_stats_are_compact_and_ordered(self):
        layout = get_minimal_workflow_layout()

        self.assertEqual(layout.footer_stats, ["folders", "selected", "files", "size"])


if __name__ == "__main__":
    unittest.main()
