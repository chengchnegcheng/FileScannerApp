import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

from utils.backup_history import create_backup_history_entry
from utils.config_manager import ConfigManager
from views.backup_dialog import BackupDialog


class BackupDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dialog = BackupDialog()

    def tearDown(self):
        self.dialog.close()

    def test_start_backup_only_emits_request_until_begin_backup(self):
        received = []
        self.dialog.path_edit.setText(r"C:\backup")
        self.dialog.backup_started.connect(received.append)

        self.dialog._start_backup()

        self.assertEqual(received, [r"C:\backup"])
        self.assertFalse(self.dialog.start_btn.isEnabled())
        self.assertIn("正在准备备份", self.dialog.status_label.text())

    def test_abort_prepare_restores_start_button(self):
        self.dialog.path_edit.setText(r"C:\backup")
        self.dialog.begin_backup()
        self.dialog.abort_prepare()

        self.assertTrue(self.dialog.start_btn.isEnabled())
        self.assertEqual(self.dialog.cancel_btn.text(), "取消")
        self.assertTrue(self.dialog.browse_btn.isEnabled())
        self.assertFalse(self.dialog.progress_bar.isVisible())

    def test_begin_backup_uses_busy_progress_while_waiting_for_first_file(self):
        self.dialog.begin_backup()

        self.assertEqual(self.dialog.progress_bar.minimum(), 0)
        self.assertEqual(self.dialog.progress_bar.maximum(), 0)
        self.assertFalse(self.dialog.start_btn.isEnabled())
        self.assertFalse(self.dialog.browse_btn.isEnabled())
        self.assertTrue(self.dialog.cancel_btn.isEnabled())
        self.assertEqual(self.dialog.cancel_btn.text(), "停止备份")

    def test_cancel_before_backup_closes_dialog(self):
        with patch.object(self.dialog, "reject") as reject_mock:
            self.dialog._on_cancel_clicked()

        reject_mock.assert_called_once()

    def test_cancel_during_backup_requests_stop_instead_of_closing(self):
        stops = []
        self.dialog.backup_stop_requested.connect(lambda: stops.append(True))
        self.dialog.begin_backup()

        with patch.object(self.dialog, "reject") as reject_mock:
            self.dialog._on_cancel_clicked()

        self.assertEqual(stops, [True])
        reject_mock.assert_not_called()
        self.assertIn("正在停止备份", self.dialog.status_label.text())
        self.assertTrue(self.dialog.cancel_btn.isEnabled())

    def test_dialog_hides_title_bar_context_help_button(self):
        self.assertFalse(bool(self.dialog.windowFlags() & Qt.WindowContextHelpButtonHint))

    def test_history_click_applies_destination_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConfigManager(str(Path(temp_dir) / "config.json"))
            destination = Path(temp_dir) / "history-dest"
            destination.mkdir()
            config.add_backup_history(
                create_backup_history_entry(
                    dest_path=str(destination),
                    source_names=["demo"],
                    status="success",
                )
            )

            dialog = BackupDialog(config=config)
            item = dialog.history_list.item(0)
            dialog._on_history_item_clicked(item)

            self.assertEqual(dialog.path_edit.text(), str(destination))
            self.assertTrue(dialog.start_btn.isEnabled())

    def test_browse_directory_shows_merge_overwrite_summary_for_empty_destination(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "views.backup_dialog.QFileDialog.getExistingDirectory",
            return_value=temp_dir,
        ):
            self.dialog._browse_directory()

        self.assertEqual(self.dialog.path_edit.text(), temp_dir)
        self.assertTrue(self.dialog.start_btn.isEnabled())
        self.assertIn(f"将备份到：{temp_dir}", self.dialog.status_label.text())
        self.assertIn("备份方式：合并已有目录，覆盖同名文件", self.dialog.status_label.text())

    def test_browse_directory_warns_with_merge_overwrite_copy_for_non_empty_destination(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            open(os.path.join(temp_dir, "existing.txt"), "w", encoding="utf-8").close()

            with patch(
                "views.backup_dialog.QFileDialog.getExistingDirectory",
                return_value=temp_dir,
            ), patch(
                "views.backup_dialog.QMessageBox.warning",
                return_value=QMessageBox.Yes,
            ) as warning_mock:
                self.dialog._browse_directory()

        warning_message = warning_mock.call_args.args[2]
        self.assertIn("目标目录不是空文件夹", warning_message)
        self.assertIn("合并并覆盖", warning_message)
        self.assertIn("同名文件会被覆盖", warning_message)
        self.assertIn("其他文件会保留", warning_message)

    def test_backup_finished_does_not_auto_close(self):
        with patch.object(self.dialog, "close") as close_mock, patch(
            "views.backup_dialog.QMessageBox.information"
        ):
            self.dialog.backup_finished(True)

        close_mock.assert_not_called()
        self.assertTrue(self.dialog.cancel_btn.isEnabled())

    def test_backup_finished_shows_merge_overwrite_success_message(self):
        with patch("views.backup_dialog.QMessageBox.information") as information_mock:
            self.dialog.backup_finished(True)

        self.assertIn("备份已完成（合并并覆盖）", self.dialog.status_label.text())
        self.assertEqual(information_mock.call_args.args[0], self.dialog)
        self.assertEqual(information_mock.call_args.args[1], "完成")
        self.assertIn("已合并已有目录，并覆盖同名文件", information_mock.call_args.args[2])

    def test_update_progress_uses_processed_bytes_for_percentage(self):
        self.dialog.update_progress(r"C:\demo\file.txt", 1, 2, 1024.0, 25, 100)

        self.assertEqual(self.dialog.progress_bar.value(), 25)
        self.assertIn("1/2", self.dialog.status_label.text())
        self.assertIn("25 B / 100 B", self.dialog.status_label.text())

    def test_update_progress_keeps_busy_indicator_when_totals_unknown(self):
        self.dialog.update_progress(r"C:\demo\file.txt", 1, 0, 1024.0, 25, 0)

        self.assertEqual(self.dialog.progress_bar.minimum(), 0)
        self.assertEqual(self.dialog.progress_bar.maximum(), 0)
        self.assertIn("1/?", self.dialog.status_label.text())
        self.assertIn("进行中", self.dialog.status_label.text())
        self.assertIn("25 B", self.dialog.status_label.text())

    def test_backup_failed_status_is_not_overwritten_by_finished(self):
        self.dialog.begin_backup()

        self.dialog.backup_failed("备份错误", "权限不足")
        self.dialog.backup_finished(False)

        self.assertIn("备份失败", self.dialog.status_label.text())
        self.assertIn("权限不足", self.dialog.status_label.text())
        self.assertTrue(self.dialog.start_btn.isEnabled())

    def test_backup_finished_shows_cancelled_message_when_not_successful(self):
        self.dialog.begin_backup()

        self.dialog.backup_finished(False)

        self.assertIn("备份已取消，已保留已复制内容", self.dialog.status_label.text())
        self.assertTrue(self.dialog.start_btn.isEnabled())
        self.assertEqual(self.dialog.cancel_btn.text(), "关闭")

    def test_backup_finished_resets_cancel_button_after_success(self):
        self.dialog.begin_backup()

        with patch("views.backup_dialog.QMessageBox.information"):
            self.dialog.backup_finished(True)

        self.assertEqual(self.dialog.cancel_btn.text(), "关闭")

    def test_set_sources_need_calculate_shows_hint(self):
        self.dialog.set_sources_need_calculate(True)

        self.assertFalse(self.dialog.calc_hint_label.isHidden())
        self.assertIn("尚未计算", self.dialog.calc_hint_label.text())

    def test_remove_history_item_updates_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConfigManager(str(Path(temp_dir) / "config.json"))
            config.add_backup_history(
                create_backup_history_entry(
                    dest_path=r"D:\keep",
                    source_names=["keep"],
                    status="success",
                )
            )
            config.add_backup_history(
                create_backup_history_entry(
                    dest_path=r"D:\drop",
                    source_names=["drop"],
                    status="failed",
                )
            )

            dialog = BackupDialog(config=config)
            item = dialog.history_list.item(0)
            dialog._remove_history_item(item)

            self.assertEqual(len(dialog._history_entries), 1)
            self.assertEqual(dialog._history_entries[0].dest_path, r"D:\keep")

    def test_clear_all_history_empties_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConfigManager(str(Path(temp_dir) / "config.json"))
            config.add_backup_history(
                create_backup_history_entry(
                    dest_path=r"D:\one",
                    source_names=["one"],
                    status="success",
                )
            )

            dialog = BackupDialog(config=config)
            with patch("views.backup_dialog.QMessageBox.question", return_value=QMessageBox.Yes):
                dialog._clear_all_history()

            self.assertEqual(config.get_backup_history(), [])
            self.assertEqual(dialog.history_list.count(), 1)
            self.assertIn("暂无备份记录", dialog.history_list.item(0).text())

    def test_esc_during_backup_requests_stop(self):
        stops = []
        self.dialog.backup_stop_requested.connect(lambda: stops.append(True))
        self.dialog.begin_backup()

        self.dialog._on_cancel_clicked()

        self.assertEqual(stops, [True])


if __name__ == "__main__":
    unittest.main()
