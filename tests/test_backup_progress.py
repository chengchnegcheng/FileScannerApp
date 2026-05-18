import tempfile
import unittest
from pathlib import Path

from services.file_scanner import FileScanner
from utils.config_manager import ConfigManager


class BackupProgressTests(unittest.TestCase):
    def test_copy_progress_reports_speed_and_total_bytes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            src = temp_path / "source.bin"
            dst = temp_path / "dest.bin"
            content = b"a" * 32768
            src.write_bytes(content)

            scanner = FileScanner(ConfigManager(str(temp_path / "config.json")))
            events = []

            def callback(current_file, current, total, bytes_per_second, total_bytes):
                events.append((current_file, current, total, bytes_per_second, total_bytes))

            scanner._copy_with_progress(str(src), str(dst), callback, 1, 1)

            self.assertTrue(events)
            self.assertEqual(events[-1][0], str(src))
            self.assertEqual(events[-1][1:3], (1, 1))
            self.assertGreaterEqual(events[-1][3], 0)
            self.assertEqual(events[-1][4], len(content))
            self.assertEqual(dst.read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
