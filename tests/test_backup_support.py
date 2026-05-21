import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.backup_support import (
    BackupCancelled,
    BackupRollbackSession,
    check_backup_disk_space,
    estimate_backup_bytes,
    estimate_backup_bytes_for_request,
    format_disk_space_error,
)
from services.file_scanner import FileScanner
from utils.config_manager import ConfigManager


class BackupSupportTests(unittest.TestCase):
    def test_estimate_backup_bytes_uses_known_sizes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source"
            source.mkdir()
            (source / "large.bin").write_bytes(b"x" * 50)

            estimated = estimate_backup_bytes(
                [str(source)],
                {str(source): 99},
            )

        self.assertEqual(estimated, 99)

    def test_check_backup_disk_space_compares_required_and_free(self):
        with patch("services.backup_support.shutil.disk_usage", return_value=(0, 0, 100)):
            ok, free_bytes, needed = check_backup_disk_space("C:\\backup", 80)

        self.assertTrue(ok)
        self.assertEqual(free_bytes, 100)
        self.assertEqual(needed, 84)

    def test_format_disk_space_error_includes_sizes(self):
        message = format_disk_space_error(1000, 100, 1050)

        self.assertIn("空间不足", message)
        self.assertIn("预计需要", message)
        self.assertIn("当前可用", message)

    def test_estimate_backup_bytes_for_request_uses_incremental_size_for_merge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source = temp_path / "source"
            source.mkdir()
            (source / "new.txt").write_bytes(b"12345")
            (source / "same.txt").write_bytes(b"abc")

            destination = temp_path / "backup"
            destination.mkdir()
            target = destination / "source"
            target.mkdir()
            (target / "same.txt").write_bytes(b"abc")

            required = estimate_backup_bytes_for_request([str(source)], str(destination))

        self.assertEqual(required, 5)

    def test_estimate_backup_bytes_for_request_uses_known_size_for_merge_without_walk(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source = temp_path / "source"
            source.mkdir()
            (source / "a.txt").write_bytes(b"x" * 100)

            destination = temp_path / "backup"
            destination.mkdir()
            (destination / "source").mkdir()

            with patch(
                "services.backup_support._estimate_merge_incremental_bytes",
                side_effect=AssertionError("should not walk when size is known"),
            ):
                required = estimate_backup_bytes_for_request(
                    [str(source)],
                    str(destination),
                    {str(source): 4096},
                )

        self.assertEqual(required, 4096)

    def test_estimate_backup_bytes_for_request_honours_cancel_callback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source"
            source.mkdir()
            (source / "a.txt").write_bytes(b"x" * 10)
            destination = Path(temp_dir) / "backup"
            destination.mkdir()
            cancelled = {"value": False}

            def should_stop():
                cancelled["value"] = True
                return True

            with self.assertRaises(BackupCancelled):
                estimate_backup_bytes_for_request(
                    [str(source)],
                    str(destination),
                    should_stop=should_stop,
                )

            self.assertTrue(cancelled["value"])


class BackupRollbackIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.scanner = FileScanner(ConfigManager(str(self.temp_path / "config.json")))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_backup_failure_restores_overwritten_file(self):
        source = self.temp_path / "source"
        source.mkdir()
        (source / "keep.txt").write_text("new-keep", encoding="utf-8")
        (source / "fail.txt").write_text("boom", encoding="utf-8")

        destination = self.temp_path / "backup"
        destination.mkdir()
        target = destination / "source"
        target.mkdir()
        (target / "keep.txt").write_text("old-keep", encoding="utf-8")

        original_copy = self.scanner._copy_with_progress

        def failing_copy(src, dst, callback, progress_state):
            if dst.endswith("fail.txt"):
                raise OSError("simulated failure")
            return original_copy(src, dst, callback, progress_state)

        self.scanner._copy_with_progress = failing_copy  # type: ignore[method-assign]

        result = self.scanner.backup_directories([str(source)], str(destination))

        self.assertFalse(result)
        stats = self.scanner.last_backup_stats
        self.assertIsNotNone(stats)
        assert stats is not None
        self.assertTrue(stats.rolled_back)
        self.assertEqual((target / "keep.txt").read_text(encoding="utf-8"), "old-keep")
        self.assertFalse((target / "fail.txt").exists())

    def test_backup_failure_removes_new_top_level_directory(self):
        source = self.temp_path / "source"
        source.mkdir()
        (source / "one.txt").write_text("1", encoding="utf-8")
        (source / "two.txt").write_text("2", encoding="utf-8")

        destination = self.temp_path / "backup"
        destination.mkdir()

        original_copy = self.scanner._copy_with_progress

        def failing_copy(src, dst, callback, progress_state):
            if dst.endswith("two.txt"):
                raise OSError("simulated failure")
            return original_copy(src, dst, callback, progress_state)

        self.scanner._copy_with_progress = failing_copy  # type: ignore[method-assign]

        result = self.scanner.backup_directories([str(source)], str(destination))

        self.assertFalse(result)
        self.assertFalse((destination / "source").exists())

    def test_backup_directories_does_not_clear_stop_flag(self):
        source = self.temp_path / "source"
        source.mkdir()
        (source / "demo.txt").write_text("hello", encoding="utf-8")
        destination = self.temp_path / "backup"
        destination.mkdir()

        self.scanner.stopped = True
        result = self.scanner.backup_directories(
            [str(source)],
            str(destination),
            required_bytes=16,
        )

        self.assertFalse(result)
        self.assertTrue(self.scanner.stopped)

    def test_validate_backup_disk_space_rejects_insufficient_space(self):
        source = self.temp_path / "source"
        source.mkdir()
        (source / "big.bin").write_bytes(b"x" * 2048)
        destination = self.temp_path / "backup"
        destination.mkdir()

        with patch(
            "services.backup_support.shutil.disk_usage",
            return_value=(0, 0, 1024),
        ):
            with self.assertRaises(ValueError) as ctx:
                self.scanner.validate_backup_disk_space([str(source)], str(destination))

        self.assertIn("空间不足", str(ctx.exception))

    def test_multi_source_failure_only_rolls_back_failed_source(self):
        first_source = self.temp_path / "first"
        second_source = self.temp_path / "second"
        first_source.mkdir()
        second_source.mkdir()
        (first_source / "ok.txt").write_text("first-ok", encoding="utf-8")
        (second_source / "bad.txt").write_text("second-bad", encoding="utf-8")

        destination = self.temp_path / "backup"
        destination.mkdir()

        original_copy = self.scanner._copy_with_progress
        call_targets: list[str] = []

        def failing_copy(src, dst, callback, progress_state):
            call_targets.append(dst)
            if "second" in dst.replace("\\", "/"):
                raise OSError("simulated failure on second source")
            return original_copy(src, dst, callback, progress_state)

        self.scanner._copy_with_progress = failing_copy  # type: ignore[method-assign]

        result = self.scanner.backup_directories(
            [str(first_source), str(second_source)],
            str(destination),
        )

        self.assertFalse(result)
        self.assertTrue((destination / "first" / "ok.txt").exists())
        self.assertEqual(
            (destination / "first" / "ok.txt").read_text(encoding="utf-8"),
            "first-ok",
        )
        self.assertFalse((destination / "second").exists())


class BackupRollbackSessionTests(unittest.TestCase):
    def test_rollback_restores_overwritten_and_removes_created(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "dest"
            dest.mkdir()
            target = dest / "project"
            target.mkdir()
            original = target / "a.txt"
            original.write_text("old", encoding="utf-8")
            created = target / "b.txt"

            session = BackupRollbackSession(str(dest))
            session.begin_source_target(str(target))
            session.before_copy(str(original))
            original.write_text("new", encoding="utf-8")
            session.before_copy(str(created))
            created.write_text("added", encoding="utf-8")

            session.rollback()

            self.assertEqual(original.read_text(encoding="utf-8"), "old")
            self.assertFalse(created.exists())


if __name__ == "__main__":
    unittest.main()
