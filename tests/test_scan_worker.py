import tempfile
import unittest
from pathlib import Path

from services.file_scanner import FileScanner
from utils.config_manager import ConfigManager
from workers.scan_worker import ScanWorker


class ScanWorkerTests(unittest.TestCase):
    def test_scan_worker_lists_directories_without_auto_calculation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder = root / "demo"
            folder.mkdir()
            (folder / "a.txt").write_bytes(b"a" * 10)
            (folder / "b.txt").write_bytes(b"b" * 20)

            scanner = FileScanner(ConfigManager(str(root / "config.json")))
            worker = ScanWorker(scanner, str(root))

            events = []
            found_items = []
            finished = []

            worker.file_found.connect(lambda item: (events.append("found"), found_items.append(item)))
            worker.finished.connect(lambda success: (events.append("finished"), finished.append(success)))

            worker.run()

            self.assertEqual(events, ["found", "finished"])
            self.assertEqual(len(found_items), 1)
            self.assertEqual(finished, [True])

            item = found_items[0]
            self.assertEqual(item.file_count, 0)
            self.assertIsNone(item.size)
            self.assertEqual(item.status, "未计算")
            self.assertIsNotNone(item.created_at)


if __name__ == "__main__":
    unittest.main()
