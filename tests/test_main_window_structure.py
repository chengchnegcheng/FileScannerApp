import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QAbstractItemView, QLabel, QMessageBox

from models.file_item import FileItem
from utils.config_manager import ConfigManager
from utils.path_utils import normalize_directory_path
from views.main_window import MainWindow, NoFocusItemDelegate
from views.backup_dialog import BackupDialog


class MainWindowStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        config_path = os.path.join(self.temp_dir.name, "config.json")
        self.window = MainWindow(ConfigManager(config_path))

    def tearDown(self):
        self.window.close()
        self.temp_dir.cleanup()

    def test_toolbar_uses_compact_scan_actions(self):
        self.assertEqual(self.window.select_btn.text(), "\u9009\u62e9\u76ee\u5f55")
        self.assertEqual(self.window.start_btn.text(), "\u5f00\u59cb\u626b\u63cf")
        self.assertEqual(self.window.stop_btn.text(), "\u505c\u6b62")
        self.assertEqual(self.window.calculate_btn.text(), "\u8ba1\u7b97")

    def test_secondary_actions_bar_sits_above_results_table(self):
        main_layout = self.window.centralWidget().layout()

        self.assertIs(main_layout.itemAt(1).widget(), self.window._secondary_actions_container)
        self.assertIs(main_layout.itemAt(2).widget(), self.window._table_container)

    def test_runtime_progress_bar_hides_text_for_slim_style(self):
        self.assertFalse(self.window.progress_bar.isTextVisible())

    def test_table_view_enables_custom_context_menu(self):
        self.assertEqual(self.window.table_view.contextMenuPolicy(), Qt.CustomContextMenu)

    def test_scan_finished_keeps_size_column_readable(self):
        from models.file_item import FileItem

        self.window.table_model.add_item(
            FileItem(name="demo", path="/tmp/demo", size=6 * 1024**3, file_count=12, status="已计算")
        )

        self.window._on_scan_finished(True)

        self.assertGreaterEqual(self.window.table_view.columnWidth(3), 140)

    def test_menu_bar_contains_expected_top_level_menus(self):
        actions = self.window.menuBar().actions()
        self.assertEqual(len(actions), 4)
        self.assertEqual(self.window.menuBar().objectName(), "appMenuBar")

    def test_about_dialog_omits_feature_and_support_copy(self):
        captured_texts = []
        original_label = QLabel

        def spy_label(*args, **kwargs):
            if args and isinstance(args[0], str):
                captured_texts.append(args[0])
            return original_label(*args, **kwargs)

        with patch("views.main_window.QLabel", side_effect=spy_label), patch(
            "views.main_window.QDialog.exec_",
            return_value=0,
        ):
            self.window._show_about_dialog()

        combined = "\n".join(captured_texts)
        self.assertNotIn("?????????", combined)
        self.assertNotIn("????", combined)
        self.assertNotIn("YourCompany", combined)
        self.assertNotIn("yourcompany.com", combined)

    def test_browse_directory_starts_scan_immediately(self):
        chosen = os.path.join(self.temp_dir.name, "chosen")
        os.makedirs(chosen, exist_ok=True)

        with patch("views.main_window.QFileDialog.getExistingDirectory", return_value=chosen), patch.object(
            self.window,
            "_scan_directory",
        ) as scan_mock:
            self.window._browse_directory()

        self.assertEqual(self.window.current_directory, chosen)
        self.assertEqual(self.window.current_path_label.toolTip(), chosen)
        scan_mock.assert_called_once_with(chosen)

    def test_start_scan_uses_selected_directory(self):
        chosen = os.path.join(self.temp_dir.name, "chosen")

        self.window._set_selected_directory(chosen, auto_scan=False)

        with patch.object(self.window, "_scan_directory") as scan_mock:
            self.window.start_scan()

        scan_mock.assert_called_once_with(chosen)

    def test_select_directory_shows_recent_menu_when_recent_exists(self):
        self.window.config.set_setting("recent_directories", [r"C:\recent-a", r"C:\recent-b"])

        with patch.object(self.window, "_browse_directory") as browse_mock, patch.object(
            self.window,
            "_show_directory_menu",
        ) as menu_mock:
            self.window.select_directory()

        browse_mock.assert_not_called()
        menu_mock.assert_called_once_with()

    def test_set_selected_directory_without_auto_scan_still_updates_recent_history(self):
        chosen = os.path.join(self.temp_dir.name, "chosen")
        os.makedirs(chosen, exist_ok=True)

        self.window._set_selected_directory(chosen, auto_scan=False)

        self.assertEqual(self.window.config.get_recent_directories(), [chosen])
        self.assertEqual(self.window.config.get_setting("last_directory"), chosen)

    def test_selected_long_path_is_elided_with_full_tooltip(self):
        long_path = os.path.join(
            self.temp_dir.name,
            "very-long-folder-name" * 8,
            "child-folder" * 4,
        )
        self.window.current_path_label.setFixedWidth(180)

        self.window._set_selected_directory(long_path, auto_scan=False)

        self.assertEqual(self.window.current_path_label.toolTip(), long_path)
        self.assertNotEqual(self.window.current_path_label.text(), long_path)

    def test_checking_single_row_keeps_partial_select_all_state(self):
        self.window.table_model.add_item(FileItem(name="a", path="/tmp/a"))
        self.window.table_model.add_item(FileItem(name="b", path="/tmp/b"))

        first_checkbox = self.window.table_model.index(0, 0)
        self.window.table_model.setData(first_checkbox, Qt.Checked, Qt.CheckStateRole)

        self.assertTrue(self.window.table_model.get_item(0).checked)
        self.assertFalse(self.window.table_model.get_item(1).checked)
        self.assertEqual(self.window.select_all_checkbox.checkState(), Qt.PartiallyChecked)

    def test_select_all_checkbox_toggles_all_rows(self):
        self.window.table_model.add_item(FileItem(name="a", path="/tmp/a"))
        self.window.table_model.add_item(FileItem(name="b", path="/tmp/b"))

        self.window.select_all_checkbox.setChecked(True)

        self.assertTrue(self.window.table_model.get_item(0).checked)
        self.assertTrue(self.window.table_model.get_item(1).checked)
        self.assertEqual(self.window.select_all_checkbox.checkState(), Qt.Checked)

        self.window.select_all_checkbox.setChecked(False)

        self.assertFalse(self.window.table_model.get_item(0).checked)
        self.assertFalse(self.window.table_model.get_item(1).checked)
        self.assertEqual(self.window.select_all_checkbox.checkState(), Qt.Unchecked)

    def test_select_all_checkbox_click_from_partial_selects_everything(self):
        self.window.table_model.add_item(FileItem(name="a", path="/tmp/a"))
        self.window.table_model.add_item(FileItem(name="b", path="/tmp/b"))
        self.window.table_model.setData(self.window.table_model.index(0, 0), Qt.Checked, Qt.CheckStateRole)

        self.assertEqual(self.window.select_all_checkbox.checkState(), Qt.PartiallyChecked)

        self.window.select_all_checkbox.click()

        self.assertTrue(self.window.table_model.get_item(0).checked)
        self.assertTrue(self.window.table_model.get_item(1).checked)
        self.assertEqual(self.window.select_all_checkbox.checkState(), Qt.Checked)

    def test_select_all_checkbox_click_from_checked_clears_everything(self):
        self.window.table_model.add_item(FileItem(name="a", path="/tmp/a"))
        self.window.table_model.add_item(FileItem(name="b", path="/tmp/b"))
        self.window.select_all_checkbox.setChecked(True)

        self.window.select_all_checkbox.click()

        self.assertFalse(self.window.table_model.get_item(0).checked)
        self.assertFalse(self.window.table_model.get_item(1).checked)
        self.assertEqual(self.window.select_all_checkbox.checkState(), Qt.Unchecked)

    def test_select_all_checkbox_is_embedded_in_first_header_cell(self):
        header = self.window.table_view.horizontalHeader()

        self.assertIs(self.window.select_all_checkbox.parentWidget(), header.viewport())
        self.assertEqual(self.window.table_model.headerData(0, Qt.Horizontal), "")
        self.assertEqual(self.window.select_all_checkbox.text(), "")

    def test_select_all_checkbox_is_left_biased_but_vertically_centered(self):
        self.window.show()
        self.app.processEvents()

        header = self.window.table_view.horizontalHeader()
        checkbox = self.window.select_all_checkbox
        centered_x = header.sectionViewportPosition(0) + max(0, (header.sectionSize(0) - checkbox.width()) // 2)
        centered_y = max(0, (header.height() - checkbox.height()) // 2)

        self.assertGreaterEqual(centered_x - checkbox.x(), 2)
        self.assertLessEqual(centered_x - checkbox.x(), 6)
        self.assertLessEqual(abs(checkbox.y() - centered_y), 1)

    def test_select_all_checkbox_tooltip_reflects_selected_count(self):
        self.window.table_model.add_item(FileItem(name="a", path="/tmp/a"))
        self.window.table_model.add_item(FileItem(name="b", path="/tmp/b"))
        self.window.table_model.setData(self.window.table_model.index(0, 0), Qt.Checked, Qt.CheckStateRole)

        self.assertIn("1/2", self.window.select_all_checkbox.toolTip())

    def test_start_backup_switches_main_and_dialog_to_busy_indeterminate_state(self):
        source = os.path.join(self.temp_dir.name, "source")
        destination = os.path.join(self.temp_dir.name, "dest")
        os.makedirs(source, exist_ok=True)
        os.makedirs(destination, exist_ok=True)
        with open(os.path.join(source, "demo.txt"), "w", encoding="utf-8") as handle:
            handle.write("hello")

        item = FileItem(name="source", path=source, size=5, file_count=1, checked=True)
        self.window._backup_dialog = BackupDialog(self.window, self.window.config)

        with patch.object(self.window, "_start_worker", return_value=True) as start_worker_mock:
            self.window._start_backup([item], destination)

        start_worker_mock.assert_called_once()
        self.assertTrue(self.window.progress_bar.isHidden())
        self.assertEqual(self.window._backup_dialog.progress_bar.minimum(), 0)
        self.assertEqual(self.window._backup_dialog.progress_bar.maximum(), 0)
        self.assertFalse(self.window._backup_dialog.start_btn.isEnabled())
        self.assertEqual(self.window._backup_dialog.cancel_btn.text(), "停止备份")

    def test_backup_dialog_stop_button_triggers_stop_scan(self):
        self.window._is_busy = True
        self.window._backup_dialog = BackupDialog(self.window, self.window.config)
        self.window._backup_dialog.backup_stop_requested.connect(self.window.stop_scan)
        self.window._backup_dialog.begin_backup()

        with patch.object(self.window.scanner, "stop") as stop_mock:
            self.window._backup_dialog.backup_stop_requested.emit()

        stop_mock.assert_called_once()

    def test_on_backup_error_with_dialog_does_not_show_global_error(self):
        self.window._backup_dialog = BackupDialog(self.window, self.window.config)

        with patch.object(self.window, "show_error") as show_error_mock:
            self.window._on_backup_error("备份错误", "磁盘空间不足")

        show_error_mock.assert_not_called()
        self.assertTrue(self.window._backup_failed)

    def test_on_backup_error_without_dialog_shows_global_error(self):
        self.window._backup_dialog = None

        with patch.object(self.window, "show_error") as show_error_mock:
            self.window._on_backup_error("备份错误", "磁盘空间不足")

        show_error_mock.assert_called_once_with("备份错误", "磁盘空间不足")

    def test_copy_checked_paths_writes_to_clipboard(self):
        self.window.table_model.add_item(FileItem(name="a", path="/tmp/a", checked=True))
        self.window.table_model.add_item(FileItem(name="b", path="/tmp/b"))

        self.window._copy_checked_paths()

        self.assertEqual(QApplication.clipboard().text(), "/tmp/a")
        self.assertIn("已复制 1 条路径", self.window._status_message)

    def test_empty_state_label_shows_workflow_hint(self):
        self.assertIn("选择目录", self.window.empty_state_label.text())
        self.assertIn("计算", self.window.empty_state_label.text())

    def test_on_backup_finished_success_uses_merge_overwrite_copy(self):
        self.window._is_busy = True
        self.window._backup_failed = False
        self.window.scanner.stopped = False
        self.window._cancel_requested = False

        self.window._on_backup_finished(True)

        self.assertIn("合并并覆盖", self.window._status_message)

    def test_select_all_checkbox_is_disabled_when_table_is_empty(self):
        self.window._update_select_all_state()

        self.assertFalse(self.window.select_all_checkbox.isEnabled())
        self.assertEqual(self.window.select_all_checkbox.text(), "")


    @patch("views.main_window.os.startfile", create=True)
    def test_open_item_in_file_explorer_opens_existing_path(self, startfile_mock):
        folder = os.path.join(self.temp_dir.name, "folder")
        os.makedirs(folder, exist_ok=True)
        item = FileItem(name="folder", path=folder)

        with patch.object(self.window, "show_error") as show_error_mock:
            result = self.window._open_item_in_file_explorer(item)

        self.assertTrue(result)
        startfile_mock.assert_called_once_with(folder)
        show_error_mock.assert_not_called()

    @patch("views.main_window.os.startfile", create=True)
    def test_open_item_in_file_explorer_missing_path_shows_error(self, startfile_mock):
        missing_path = os.path.join(self.temp_dir.name, "missing")
        item = FileItem(name="missing", path=missing_path)

        with patch.object(self.window, "show_error") as show_error_mock:
            result = self.window._open_item_in_file_explorer(item)

        self.assertFalse(result)
        startfile_mock.assert_not_called()
        show_error_mock.assert_called_once()
        self.assertEqual(show_error_mock.call_args.args[0], "打开失败")
        self.assertIn("不存在", show_error_mock.call_args.args[1])

    @patch("views.main_window.os.startfile", create=True)
    def test_open_item_in_file_explorer_normalizes_unc_path(self, startfile_mock):
        mixed_path = "//172.16.51.56/project backup\\30667"
        normalized_path = normalize_directory_path(mixed_path)
        item = FileItem(name="folder", path=mixed_path)

        with patch("views.main_window.os.path.exists", side_effect=lambda path: path == normalized_path), patch.object(
            self.window,
            "show_error",
        ) as show_error_mock:
            result = self.window._open_item_in_file_explorer(item)

        self.assertTrue(result)
        startfile_mock.assert_called_once_with(normalized_path)
        show_error_mock.assert_not_called()

    def test_clicking_row_name_cell_toggles_checked_state(self):
        self.window.table_model.add_item(FileItem(name="a", path="/tmp/a"))
        self.window.table_model.add_item(FileItem(name="b", path="/tmp/b"))

        self.window.table_view.clicked.emit(self.window.table_model.index(0, 1))

        self.assertTrue(self.window.table_model.get_item(0).checked)
        self.assertFalse(self.window.table_model.get_item(1).checked)
        self.assertEqual(self.window.select_all_checkbox.checkState(), Qt.PartiallyChecked)

    def test_clicking_same_row_name_cell_twice_clears_checked_state(self):
        self.window.table_model.add_item(FileItem(name="a", path="/tmp/a"))

        index = self.window.table_model.index(0, 1)
        self.window.table_view.clicked.emit(index)
        self.window.table_view.clicked.emit(index)

        self.assertFalse(self.window.table_model.get_item(0).checked)
        self.assertEqual(self.window.select_all_checkbox.checkState(), Qt.Unchecked)

    def test_table_uses_single_selection_highlight_mode(self):
        self.assertEqual(self.window.table_view.selectionMode(), QAbstractItemView.SingleSelection)

    def test_table_uses_no_focus_delegate(self):
        self.assertIsInstance(self.window.table_view.itemDelegate(), NoFocusItemDelegate)

    def test_name_column_uses_folder_icon_decoration(self):
        self.window.table_model.add_item(FileItem(name="a", path="/tmp/a"))

        icon = self.window.table_model.data(self.window.table_model.index(0, 1), Qt.DecorationRole)

        self.assertIsNotNone(icon)
        self.assertFalse(icon.isNull())

    def test_error_dialog_buttons_are_localized(self):
        message_box = QMessageBox(self.window)
        message_box.setText("error")
        message_box.setDetailedText("details")
        message_box.addButton(QMessageBox.Ok)

        self.window._localize_message_box_buttons(message_box)

        button_texts = {button.text() for button in message_box.buttons()}
        self.assertIn("确定", button_texts)
        self.assertIn("显示详情", button_texts)


if __name__ == "__main__":
    unittest.main()
