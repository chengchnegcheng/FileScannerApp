import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from views.backup_dialog import BackupDialog


class BackupDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dialog = BackupDialog()

    def tearDown(self):
        self.dialog.close()

    def test_start_backup_keeps_cancel_enabled(self):
        self.dialog.path_edit.setText(r"C:\backup")

        self.dialog._start_backup()

        self.assertFalse(self.dialog.start_btn.isEnabled())
        self.assertFalse(self.dialog.browse_btn.isEnabled())
        self.assertTrue(self.dialog.cancel_btn.isEnabled())

    def test_backup_finished_does_not_auto_close(self):
        with patch.object(self.dialog, "close") as close_mock, patch(
            "views.backup_dialog.QMessageBox.information"
        ):
            self.dialog.backup_finished(True)

        close_mock.assert_not_called()
        self.assertTrue(self.dialog.cancel_btn.isEnabled())


if __name__ == "__main__":
    unittest.main()
