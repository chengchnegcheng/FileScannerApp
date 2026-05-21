import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from services.file_scanner import FileScanner
from utils.config_manager import ConfigManager


class BackupProgressTests(unittest.TestCase):
    def test_backup_directories_does_not_pre_scan_unknown_totals_before_copying(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            (source_dir / "a.txt").write_bytes(b"hello")
            destination_dir = temp_path / "dest"
            destination_dir.mkdir()

            scanner = FileScanner(ConfigManager(str(temp_path / "config.json")))
            events = []

            with patch.object(
                scanner,
                "_build_backup_progress_state",
                side_effect=AssertionError("should not pre-scan before backup progress starts"),
            ):
                result = scanner.backup_directories([str(source_dir)], str(destination_dir), lambda *args: events.append(args))

            self.assertTrue(result)
            self.assertTrue(events)

    def test_backup_directories_reports_file_and_byte_progress_for_single_selected_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            first_file = source_dir / "a.txt"
            second_file = source_dir / "b.txt"
            first_file.write_bytes(b"hello")
            second_file.write_bytes(b"world!!!")
            destination_dir = temp_path / "dest"
            destination_dir.mkdir()

            scanner = FileScanner(ConfigManager(str(temp_path / "config.json")))
            events = []

            def callback(*args):
                events.append(args)

            result = scanner.backup_directories(
                [str(source_dir)],
                str(destination_dir),
                callback,
                {"total_files": 2, "total_bytes": len(b"hello") + len(b"world!!!")},
            )

            self.assertTrue(result)
            self.assertTrue(events)
            self.assertEqual(len(events[-1]), 6)
            self.assertEqual(events[-1][1:3], (2, 2))
            self.assertGreaterEqual(events[-1][3], 0)
            self.assertEqual(events[-1][4:6], (len(b"hello") + len(b"world!!!"), len(b"hello") + len(b"world!!!")))
            self.assertEqual((destination_dir / "source" / "a.txt").read_bytes(), b"hello")
            self.assertEqual((destination_dir / "source" / "b.txt").read_bytes(), b"world!!!")


if __name__ == "__main__":
    unittest.main()
