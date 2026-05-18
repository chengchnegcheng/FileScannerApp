import threading
import time
import unittest

from models.file_item import FileItem
from workers.calculate_worker import CalculateWorker


class _ConcurrentScanner:
    def __init__(self):
        self.stopped = False
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def calculate_directory_info(self, item):
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)

        time.sleep(0.12)
        item.size = 1
        item.file_count = 1
        item.status = "已计算"

        with self.lock:
            self.active -= 1

        return item


class CalculateWorkerTests(unittest.TestCase):
    def test_calculate_worker_processes_items_concurrently(self):
        scanner = _ConcurrentScanner()
        items = [FileItem(name=f"item{i}", path=str(i)) for i in range(4)]
        worker = CalculateWorker(scanner, items)

        progress = []
        worker.progress.connect(lambda item, current, total, speed: progress.append((item, current, total, speed)))

        started = time.perf_counter()
        worker.run()
        elapsed = time.perf_counter() - started

        self.assertEqual(len(progress), 4)
        self.assertGreater(scanner.max_active, 1)
        self.assertLess(elapsed, 0.40)
        self.assertTrue(all(item.status == "已计算" for item in items))


if __name__ == "__main__":
    unittest.main()
