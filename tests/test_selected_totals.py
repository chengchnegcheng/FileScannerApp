import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow

from models.file_item import FileItem
from utils.size_formatter import format_bytes
from viewmodels.main_viewmodel import FileTableModel
from views.main_window import MainWindow


class SelectedTotalsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_checked_totals_only_sum_selected_items(self):
        model = FileTableModel()
        model.add_item(FileItem(name="a", path="a", size=1024, file_count=10, checked=True))
        model.add_item(FileItem(name="b", path="b", size=2048, file_count=20, checked=False))
        model.add_item(FileItem(name="c", path="c", size=512, file_count=5, checked=True))

        checked_size, checked_size_text = model.get_checked_total_size()
        checked_files = model.get_checked_total_files()

        self.assertEqual(checked_size, 1536)
        self.assertEqual(checked_size_text, format_bytes(1536))
        self.assertEqual(checked_files, 15)

    def test_status_bar_shows_selected_totals_beside_global_totals(self):
        model = FileTableModel()
        model.add_item(FileItem(name="a", path="a", size=1024, file_count=10, checked=True))
        model.add_item(FileItem(name="b", path="b", size=2048, file_count=20, checked=False))
        model.add_item(FileItem(name="c", path="c", size=512, file_count=5, checked=True))

        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)
        window.table_model = model
        window.folder_count_label = QLabel()
        window.selection_label = QLabel()
        window.file_count_label = QLabel()
        window.size_label = QLabel()
        window.selected_file_count_label = QLabel()
        window.selected_size_label = QLabel()
        window.current_directory = None
        window._is_busy = False
        window._cancel_requested = False
        window.logger = type("L", (), {"error": lambda *args, **kwargs: None})()
        window._set_status_message = lambda message, timeout_ms=0: None
        window._update_current_path_label = lambda path: None
        window._pinned_until = 0.0

        window._update_status_bar()

        self.assertEqual(window.file_count_label.text(), "文件数: 35")
        self.assertEqual(window.size_label.text(), f"总大小: {format_bytes(3584)}")
        self.assertEqual(window.selected_file_count_label.text(), "已选文件数: 15")
        self.assertEqual(window.selected_size_label.text(), f"已选总大小: {format_bytes(1536)}")


if __name__ == "__main__":
    unittest.main()
