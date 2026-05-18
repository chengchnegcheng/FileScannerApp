import os
import tempfile
import unittest
from pathlib import Path

from services.file_scanner import FileScanner
from utils.config_manager import ConfigManager


class BackupValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.scanner = FileScanner(ConfigManager(str(self.temp_path / "config.json")))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_validate_backup_rejects_destination_inside_source(self):
        source = self.temp_path / "source"
        source.mkdir()
        nested_dest = source / "child"
        nested_dest.mkdir()

        with self.assertRaisesRegex(ValueError, "目标目录不能位于源目录内部"):
            self.scanner.validate_backup_request([str(source)], str(nested_dest))

    def test_validate_backup_rejects_existing_target_folder_conflict(self):
        source = self.temp_path / "source"
        source.mkdir()
        destination = self.temp_path / "backup"
        destination.mkdir()
        (destination / source.name).mkdir()

        with self.assertRaisesRegex(ValueError, "已存在同名备份目录"):
            self.scanner.validate_backup_request([str(source)], str(destination))

    def test_validate_backup_accepts_distinct_existing_destination(self):
        source = self.temp_path / "source"
        source.mkdir()
        destination = self.temp_path / "backup"
        destination.mkdir()

        result = self.scanner.validate_backup_request([str(source)], str(destination))

        self.assertEqual(result, os.path.abspath(str(destination)))


if __name__ == "__main__":
    unittest.main()
