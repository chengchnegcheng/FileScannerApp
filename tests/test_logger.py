import logging
import shutil
import tempfile
import unittest
from unittest.mock import patch

from utils.logger import LogManager


class LogManagerTests(unittest.TestCase):
    def test_setup_logging_is_idempotent_for_same_logger(self):
        logger = logging.Logger("test-root")
        temp_dir = tempfile.mkdtemp()

        try:
            with patch("utils.logger.logging.getLogger", return_value=logger):
                LogManager(log_dir=temp_dir)
                first_count = len(logger.handlers)

                LogManager(log_dir=temp_dir)
                second_count = len(logger.handlers)
        finally:
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(first_count, 2)
        self.assertEqual(second_count, first_count)


if __name__ == "__main__":
    unittest.main()
