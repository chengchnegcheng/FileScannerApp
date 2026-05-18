import tempfile
import unittest
from pathlib import Path

from models.file_item import FileItem
from services.file_scanner import FileScanner
from utils.config_manager import ConfigManager


class FileScannerCacheTests(unittest.TestCase):
    def test_calculate_directory_info_reuses_cache_for_unchanged_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder = root / "demo"
            folder.mkdir()
            (folder / "a.txt").write_bytes(b"a" * 10)

            scanner = FileScanner(ConfigManager(str(root / "config.json")))
            item = FileItem(name="demo", path=str(folder))

            scanner.calculate_directory_info(item)
            self.assertEqual(item.size, 10)
            self.assertEqual(item.file_count, 1)

            original = scanner._calculate_directory_info_uncached

            def fail_if_called(path):
                raise AssertionError("uncached calculation should not run")

            scanner._calculate_directory_info_uncached = fail_if_called

            cached_item = FileItem(name="demo", path=str(folder))
            scanner.calculate_directory_info(cached_item)

            self.assertEqual(cached_item.size, 10)
            self.assertEqual(cached_item.file_count, 1)
            self.assertEqual(cached_item.status, "已计算")

            scanner._calculate_directory_info_uncached = original

    def test_clear_calculation_cache_forces_recalculation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder = root / "demo"
            folder.mkdir()
            file_path = folder / "a.txt"
            file_path.write_bytes(b"a" * 10)

            scanner = FileScanner(ConfigManager(str(root / "config.json")))
            item = FileItem(name="demo", path=str(folder))
            scanner.calculate_directory_info(item)

            file_path.write_bytes(b"a" * 20)
            scanner.clear_calculation_cache()

            refreshed = FileItem(name="demo", path=str(folder))
            scanner.calculate_directory_info(refreshed)

            self.assertEqual(refreshed.size, 20)
            self.assertEqual(refreshed.file_count, 1)


if __name__ == "__main__":
    unittest.main()
