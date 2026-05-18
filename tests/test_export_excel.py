import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd

from models.file_item import FileItem
from viewmodels.main_viewmodel import FileTableModel


class ExportExcelTests(unittest.TestCase):
    def test_export_includes_raw_datetime_and_size_bytes(self):
        model = FileTableModel()
        model.add_item(
            FileItem(
                name="demo",
                path="C:/demo",
                created_at="2026-05-11 10:20:30",
                size=1536,
                file_count=3,
                status="已计算",
            )
        )

        captured = {}
        original_to_excel = pd.DataFrame.to_excel

        def capture_to_excel(self, filepath, *args, **kwargs):
            captured["filepath"] = filepath
            captured["dataframe"] = self.copy()
            return None

        with patch.object(pd.DataFrame, "to_excel", new=capture_to_excel):
            model.export_to_excel("dummy.xlsx")

        self.assertEqual(captured["filepath"], "dummy.xlsx")
        dataframe = captured["dataframe"]

        self.assertIn("创建时间", dataframe.columns)
        self.assertIn("创建时间原值", dataframe.columns)
        self.assertIn("大小", dataframe.columns)
        self.assertIn("大小(字节)", dataframe.columns)

        row = dataframe.iloc[0]
        self.assertEqual(row["创建时间"], "2026-05-11 10:20:30")
        self.assertEqual(row["大小"], "1.5 KB")
        self.assertEqual(row["大小(字节)"], 1536)
        self.assertIsInstance(row["创建时间原值"], datetime)
        self.assertEqual(row["创建时间原值"], datetime(2026, 5, 11, 10, 20, 30))


if __name__ == "__main__":
    unittest.main()
