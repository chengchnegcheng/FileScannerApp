import unittest

from utils.ui_state import build_action_state


class UiStateTests(unittest.TestCase):
    def test_idle_state_enables_primary_actions_by_context(self):
        state = build_action_state(is_busy=False, has_directory=True, has_items=True, has_checked=True)

        self.assertTrue(state.select_enabled)
        self.assertTrue(state.start_enabled)
        self.assertFalse(state.stop_enabled)
        self.assertTrue(state.calculate_enabled)
        self.assertTrue(state.export_enabled)
        self.assertTrue(state.backup_enabled)

    def test_busy_state_locks_actions_and_keeps_stop_enabled(self):
        state = build_action_state(is_busy=True, has_directory=True, has_items=True, has_checked=True)

        self.assertFalse(state.select_enabled)
        self.assertFalse(state.start_enabled)
        self.assertTrue(state.stop_enabled)
        self.assertFalse(state.calculate_enabled)
        self.assertFalse(state.export_enabled)
        self.assertFalse(state.backup_enabled)

    def test_cancel_requested_disables_stop_button(self):
        state = build_action_state(
            is_busy=True,
            has_directory=True,
            has_items=True,
            has_checked=True,
            cancel_requested=True,
        )

        self.assertFalse(state.stop_enabled)

    def test_idle_state_keeps_scan_disabled_without_directory(self):
        state = build_action_state(is_busy=False, has_directory=False, has_items=False, has_checked=False)

        self.assertTrue(state.select_enabled)
        self.assertFalse(state.start_enabled)
        self.assertFalse(state.calculate_enabled)


if __name__ == "__main__":
    unittest.main()
