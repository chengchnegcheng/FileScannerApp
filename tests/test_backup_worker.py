import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from services.backup_support import BackupCancelled
from workers.backup_worker import BackupWorker


class FakeScanner:
    def __init__(self, success: bool, stopped: bool = False, last_backup_error: str | None = None):
        self.success = success
        self.stopped = stopped
        self.last_backup_error = last_backup_error
        self.calls = []

    def validate_backup_request(self, src_paths, dest_path):
        return dest_path

    def validate_backup_disk_space(self, src_paths, dest_path, known_sizes=None, required_bytes=None):
        if self.stopped:
            raise BackupCancelled("cancelled")
        return 1024

    def backup_directories(
        self,
        src_paths,
        dest_path,
        progress_callback,
        progress_state,
        known_sizes=None,
        required_bytes=None,
    ):
        self.calls.append((src_paths, dest_path, progress_state, known_sizes, required_bytes))
        return self.success


class BackupWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_run_emits_error_for_failed_non_cancelled_backup(self):
        scanner = FakeScanner(False, stopped=False, last_backup_error="disk full")
        worker = BackupWorker(scanner, ["/tmp/source"], "/tmp/dest")
        errors = []
        finished = []

        worker.error.connect(lambda title, message: errors.append((title, message)))
        worker.finished.connect(finished.append)

        worker.run()

        self.assertEqual(errors, [("备份错误", "disk full")])
        self.assertEqual(finished, [False])

    def test_run_treats_backup_cancelled_as_silent_cancel(self):
        scanner = FakeScanner(False, stopped=False)
        scanner.validate_backup_disk_space = lambda *args, **kwargs: (_ for _ in ()).throw(BackupCancelled())  # type: ignore[method-assign]
        worker = BackupWorker(scanner, ["/tmp/source"], "/tmp/dest")
        errors = []
        finished = []

        worker.error.connect(lambda title, message: errors.append((title, message)))
        worker.finished.connect(finished.append)

        worker.run()

        self.assertEqual(errors, [])
        self.assertEqual(finished, [False])

    def test_run_does_not_emit_error_for_cancelled_backup(self):
        scanner = FakeScanner(False, stopped=True, last_backup_error="should stay silent")
        worker = BackupWorker(scanner, ["/tmp/source"], "/tmp/dest")
        errors = []
        finished = []

        worker.error.connect(lambda title, message: errors.append((title, message)))
        worker.finished.connect(finished.append)

        worker.run()

        self.assertEqual(errors, [])
        self.assertEqual(finished, [False])


if __name__ == "__main__":
    unittest.main()
