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

        with self.assertRaises(ValueError):
            self.scanner.validate_backup_request([str(source)], str(nested_dest))

    def test_validate_backup_allows_existing_target_folder_for_merge(self):
        source = self.temp_path / "source"
        source.mkdir()
        destination = self.temp_path / "backup"
        destination.mkdir()
        (destination / source.name).mkdir()

        result = self.scanner.validate_backup_request([str(source)], str(destination))

        self.assertEqual(result, os.path.abspath(str(destination)))

    def test_validate_backup_accepts_distinct_existing_destination(self):
        source = self.temp_path / "source"
        source.mkdir()
        destination = self.temp_path / "backup"
        destination.mkdir()

        result = self.scanner.validate_backup_request([str(source)], str(destination))

        self.assertEqual(result, os.path.abspath(str(destination)))

    def test_validate_backup_rejects_duplicate_source_folder_names(self):
        first_source = self.temp_path / "a" / "project"
        second_source = self.temp_path / "b" / "project"
        first_source.mkdir(parents=True)
        second_source.mkdir(parents=True)
        destination = self.temp_path / "backup"
        destination.mkdir()

        with self.assertRaises(ValueError) as ctx:
            self.scanner.validate_backup_request(
                [str(first_source), str(second_source)],
                str(destination),
            )

        self.assertIn("同名文件夹", str(ctx.exception))
        self.assertIn("project", str(ctx.exception))

    def test_validate_backup_rejects_existing_file_at_target_location(self):
        source = self.temp_path / "source"
        source.mkdir()
        destination = self.temp_path / "backup"
        destination.mkdir()
        conflicting_file = destination / source.name
        conflicting_file.write_text("blocker", encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            self.scanner.validate_backup_request([str(source)], str(destination))

        self.assertIn("同名文件", str(ctx.exception))

    def test_backup_directories_copies_selected_folder_into_destination(self):
        source = self.temp_path / "source"
        source.mkdir()
        file_path = source / "demo.txt"
        file_path.write_text("hello", encoding="utf-8")
        destination = self.temp_path / "backup"
        destination.mkdir()

        result = self.scanner.backup_directories([str(source)], str(destination))

        self.assertTrue(result)
        copied_file = destination / source.name / "demo.txt"
        self.assertTrue(copied_file.exists())
        self.assertEqual(copied_file.read_text(encoding="utf-8"), "hello")

    def test_backup_directories_merges_existing_folder_and_overwrites_conflicting_files(self):
        source = self.temp_path / "source"
        source.mkdir()
        (source / "demo.txt").write_text("new-content", encoding="utf-8")
        nested_source_dir = source / "nested"
        nested_source_dir.mkdir()
        (nested_source_dir / "add.txt").write_text("added", encoding="utf-8")

        destination = self.temp_path / "backup"
        destination.mkdir()
        existing_target = destination / source.name
        existing_target.mkdir()
        (existing_target / "demo.txt").write_text("old-content", encoding="utf-8")
        (existing_target / "keep.txt").write_text("keep-me", encoding="utf-8")

        result = self.scanner.backup_directories([str(source)], str(destination))

        self.assertTrue(result)
        self.assertEqual((existing_target / "demo.txt").read_text(encoding="utf-8"), "new-content")
        self.assertEqual((existing_target / "keep.txt").read_text(encoding="utf-8"), "keep-me")
        self.assertEqual((existing_target / "nested" / "add.txt").read_text(encoding="utf-8"), "added")

    def test_successful_backup_records_stats(self):
        source = self.temp_path / "source"
        source.mkdir()
        (source / "demo.txt").write_text("hello", encoding="utf-8")
        destination = self.temp_path / "backup"
        destination.mkdir()

        result = self.scanner.backup_directories([str(source)], str(destination))

        self.assertTrue(result)
        stats = self.scanner.last_backup_stats
        self.assertIsNotNone(stats)
        assert stats is not None
        self.assertEqual(stats.files_copied, 1)
        self.assertGreater(stats.bytes_copied, 0)
        self.assertGreater(stats.duration_seconds, 0)
        self.assertFalse(stats.rolled_back)


if __name__ == "__main__":
    unittest.main()
