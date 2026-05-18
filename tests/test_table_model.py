import unittest

from models.file_item import FileItem
from viewmodels.main_viewmodel import FileTableModel
from utils.size_formatter import format_bytes


class TableModelTests(unittest.TestCase):
    def test_headers_and_created_time_display(self):
        from PyQt5.QtCore import Qt

        model = FileTableModel()
        model.add_item(FileItem(name="demo", path="demo", created_at="2026-05-11 10:20:30"))

        self.assertEqual(model.headerData(2, Qt.Horizontal, Qt.DisplayRole), "创建时间")
        self.assertEqual(model.data(model.index(0, 2), Qt.DisplayRole), "2026-05-11 10:20:30")

    def test_size_tooltip_and_uncomputed_file_count_use_clean_text(self):
        from PyQt5.QtCore import Qt

        model = FileTableModel()
        model.add_item(FileItem(name="demo", path="demo", size=1536, file_count=None, status="未计算"))

        self.assertEqual(model.data(model.index(0, 3), Qt.ToolTipRole), "1.5 KB")
        self.assertEqual(model.data(model.index(0, 4), Qt.ToolTipRole), "未计算")

    def test_size_formatter_keeps_auto_units_with_fewer_decimals(self):
        self.assertEqual(format_bytes(1536), "1.5 KB")
        self.assertEqual(format_bytes(50 * 1024**2), "50.0 MB")
        self.assertEqual(format_bytes(6 * 1024**3), "6.0 GB")

    def test_total_size_uses_same_formatter(self):
        model = FileTableModel()
        model.add_item(FileItem(name="a", path="a", size=1024))
        model.add_item(FileItem(name="b", path="b", size=512))

        total_size, formatted = model.get_total_size()

        self.assertEqual(total_size, 1536)
        self.assertEqual(formatted, format_bytes(1536))

    def test_sort_size_column_uses_numeric_order(self):
        from PyQt5.QtCore import Qt

        model = FileTableModel()
        model.add_item(FileItem(name="b", path="b", size=2 * 1024**3, file_count=1, status="已计算"))
        model.add_item(FileItem(name="a", path="a", size=500 * 1024**2, file_count=1, status="已计算"))
        model.add_item(FileItem(name="c", path="c", size=10 * 1024**3, file_count=1, status="已计算"))

        model.sort(3, Qt.AscendingOrder)
        self.assertEqual([model.get_item(i).name for i in range(3)], ["a", "b", "c"])

        model.sort(3, Qt.DescendingOrder)
        self.assertEqual([model.get_item(i).name for i in range(3)], ["c", "b", "a"])

    def test_row_count_for_child_index_is_zero_in_flat_table(self):
        model = FileTableModel()
        model.add_item(FileItem(name="first", path="/tmp/first"))

        child_parent = model.index(0, 0)

        self.assertTrue(child_parent.isValid())
        self.assertEqual(model.rowCount(child_parent), 0)


if __name__ == "__main__":
    unittest.main()
