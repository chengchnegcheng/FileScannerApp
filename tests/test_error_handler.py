import logging
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from utils.error_handler import ErrorHandler


class ErrorHandlerTests(unittest.TestCase):
    def setUp(self):
        self.handler = ErrorHandler(logging.getLogger("test"))

    def test_sliding_window_resets_count_after_window_expires(self):
        old_time = datetime.now() - timedelta(seconds=61)

        with patch("utils.error_handler.datetime") as dt_mock:
            dt_mock.now.return_value = old_time
            self.assertTrue(self.handler.handle_error("E1", Exception("a")))

            dt_mock.now.return_value = datetime.now()
            self.assertTrue(self.handler.handle_error("E2", Exception("b")))

        count, _ = self.handler.get_error_status()
        self.assertEqual(count, 1)

    def test_too_many_errors_in_window_returns_false(self):
        for index in range(11):
            if index == 10:
                self.assertFalse(
                    self.handler.handle_error("E", Exception(f"err-{index}"))
                )
            else:
                self.assertTrue(
                    self.handler.handle_error("E", Exception(f"err-{index}"))
                )


if __name__ == "__main__":
    unittest.main()
