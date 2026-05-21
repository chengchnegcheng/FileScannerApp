import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
from PyQt5.QtWidgets import QApplication

from models.file_item import FileItem
from utils.config_manager import ConfigManager
from viewmodels.main_viewmodel import FileTableModel
from views.main_window import MainWindow


NAME_COLUMN = "\u540d\u79f0"
PATH_COLUMN = "\u8def\u5f84"
CREATED_AT_COLUMN = "\u521b\u5efa\u65f6\u95f4"
CREATED_AT_RAW_COLUMN = "\u521b\u5efa\u65f6\u95f4\u539f\u503c"
SIZE_COLUMN = "\u5927\u5c0f"
SIZE_BYTES_COLUMN = "\u5927\u5c0f(\u5b57\u8282)"
FILE_COUNT_COLUMN = "\u6587\u4ef6\u6570"
STATUS_COLUMN = "\u72b6\u6001"
EXPORT_COLUMNS = [
    NAME_COLUMN,
    PATH_COLUMN,
    CREATED_AT_COLUMN,
    CREATED_AT_RAW_COLUMN,
    SIZE_COLUMN,
    SIZE_BYTES_COLUMN,
    FILE_COUNT_COLUMN,
    STATUS_COLUMN,
]


class ExportExcelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _make_item(self, name: str, *, checked: bool = False, size: int = 1536) -> FileItem:
        return FileItem(
            name=name,
            path=f"C:/{name}",
            created_at="2026-05-11 10:20:30",
            size=size,
            file_count=3,
            status="\u5df2\u8ba1\u7b97",
            checked=checked,
        )

    def test_export_includes_raw_datetime_and_size_bytes(self):
        model = FileTableModel()
        model.add_item(self._make_item("demo"))

        captured = {}

        def capture_to_excel(self, filepath, *args, **kwargs):
            captured["filepath"] = filepath
            captured["dataframe"] = self.copy()
            return None

        with patch.object(pd.DataFrame, "to_excel", new=capture_to_excel):
            export_path = model.export_to_excel("dummy.xlsx")

        self.assertEqual(export_path, "dummy.xlsx")
        self.assertEqual(captured["filepath"], "dummy.xlsx")
        dataframe = captured["dataframe"]

        self.assertIn(CREATED_AT_COLUMN, dataframe.columns)
        self.assertIn(CREATED_AT_RAW_COLUMN, dataframe.columns)
        self.assertIn(SIZE_COLUMN, dataframe.columns)
        self.assertIn(SIZE_BYTES_COLUMN, dataframe.columns)

        row = dataframe.iloc[0]
        self.assertEqual(row[CREATED_AT_COLUMN], "2026-05-11 10:20:30")
        self.assertEqual(row[SIZE_COLUMN], "1.5 KB")
        self.assertEqual(row[SIZE_BYTES_COLUMN], 1536)
        self.assertIsInstance(row[CREATED_AT_RAW_COLUMN], datetime)
        self.assertEqual(row[CREATED_AT_RAW_COLUMN], datetime(2026, 5, 11, 10, 20, 30))

    def test_export_with_explicit_empty_items_does_not_fall_back_to_all_rows(self):
        model = FileTableModel()
        model.add_item(self._make_item("demo-a"))
        model.add_item(self._make_item("demo-b", size=2048))

        captured = {}

        def capture_to_excel(self, filepath, *args, **kwargs):
            captured["filepath"] = filepath
            captured["dataframe"] = self.copy()
            return None

        with patch.object(pd.DataFrame, "to_excel", new=capture_to_excel):
            model.export_to_excel("empty.xlsx", [])

        dataframe = captured["dataframe"]
        self.assertEqual(captured["filepath"], "empty.xlsx")
        self.assertEqual(list(dataframe.columns), EXPORT_COLUMNS)
        self.assertEqual(len(dataframe), 0)

    def test_export_appends_xlsx_extension_when_missing(self):
        model = FileTableModel()
        model.add_item(self._make_item("demo"))

        captured = {}

        def capture_to_excel(self, filepath, *args, **kwargs):
            captured["filepath"] = filepath
            return None

        with patch.object(pd.DataFrame, "to_excel", new=capture_to_excel):
            export_path = model.export_to_excel("dummy", [model.get_item(0)])

        self.assertEqual(export_path, "dummy.xlsx")
        self.assertEqual(captured["filepath"], "dummy.xlsx")

    def test_main_window_export_uses_appended_extension_in_status_message(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")
            window = MainWindow(ConfigManager(config_path))
            try:
                window.table_model.add_item(self._make_item("demo", checked=True))
                save_path = os.path.join(temp_dir, "scan_result")

                with patch(
                    "views.main_window.QFileDialog.getSaveFileName",
                    return_value=(save_path, "Excel Files (*.xlsx)"),
                ):
                    window.export_to_excel()

                self.assertEqual(window._status_message, f"\u5df2\u5bfc\u51fa\u5230: {save_path}.xlsx")
                self.assertTrue(os.path.exists(f"{save_path}.xlsx"))
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
