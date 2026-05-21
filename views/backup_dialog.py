import logging
import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QKeySequence
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QShortcut,
    QVBoxLayout,
)

from utils.backup_history import BackupHistoryEntry, format_history_item
from utils.config_manager import ConfigManager
from utils.size_formatter import format_bytes


_HISTORY_INDEX_ROLE = Qt.UserRole + 1


class BackupDialog(QDialog):
    """备份目录对话框。"""

    backup_started = pyqtSignal(str)
    backup_stop_requested = pyqtSignal()

    def __init__(self, parent=None, config: ConfigManager | None = None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.config = config
        self._backup_failed = False
        self._backup_in_progress = False
        self._history_entries: list[BackupHistoryEntry] = []
        self._setup_ui()
        self._load_history()

    def _setup_ui(self):
        try:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            self.setWindowTitle("备份目录")
            self.setMinimumWidth(560)
            self.setMinimumHeight(420)
            self.setModal(True)

            layout = QVBoxLayout(self)
            layout.setSpacing(12)
            layout.setContentsMargins(16, 16, 16, 16)

            card = QFrame()
            card.setObjectName("dialogCard")
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(10)
            card_layout.setContentsMargins(14, 14, 14, 14)

            self.path_label = QLabel("目标路径")
            self.path_label.setObjectName("dialogLabel")

            path_layout = QHBoxLayout()
            path_layout.setSpacing(8)
            self.path_edit = QLineEdit()
            self.path_edit.setReadOnly(True)
            self.path_edit.setPlaceholderText("选择备份目标目录")

            self.browse_btn = QPushButton("浏览")
            self.browse_btn.setObjectName("dialogSecondaryButton")
            self.browse_btn.clicked.connect(self._browse_directory)

            path_layout.addWidget(self.path_edit)
            path_layout.addWidget(self.browse_btn)

            history_header = QHBoxLayout()
            self.history_label = QLabel("历史记录")
            self.history_label.setObjectName("dialogLabel")
            self.clear_history_btn = QPushButton("清空")
            self.clear_history_btn.setObjectName("dialogSecondaryButton")
            self.clear_history_btn.clicked.connect(self._clear_all_history)
            history_header.addWidget(self.history_label)
            history_header.addStretch(1)
            history_header.addWidget(self.clear_history_btn)

            self.history_list = QListWidget()
            self.history_list.setObjectName("dialogHistoryList")
            self.history_list.setMaximumHeight(140)
            self.history_list.itemClicked.connect(self._on_history_item_clicked)
            self.history_list.itemDoubleClicked.connect(self._on_history_item_clicked)
            self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
            self.history_list.customContextMenuRequested.connect(self._show_history_context_menu)

            self.progress_bar = QProgressBar()
            self.progress_bar.setObjectName("dialogProgressBar")
            self.progress_bar.setVisible(False)

            self.calc_hint_label = QLabel()
            self.calc_hint_label.setObjectName("dialogHintLabel")
            self.calc_hint_label.setWordWrap(True)
            self.calc_hint_label.setVisible(False)

            self.status_label = QLabel("选择目录后开始备份")
            self.status_label.setObjectName("dialogStatusLabel")
            self.status_label.setWordWrap(True)
            self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            card_layout.addWidget(self.path_label)
            card_layout.addLayout(path_layout)
            card_layout.addLayout(history_header)
            card_layout.addWidget(self.history_list)
            card_layout.addWidget(self.calc_hint_label)
            card_layout.addWidget(self.progress_bar)
            card_layout.addWidget(self.status_label)
            layout.addWidget(card)

            QShortcut(QKeySequence("Esc"), self, self._on_cancel_clicked)

            button_layout = QHBoxLayout()
            button_layout.addStretch(1)

            self.start_btn = QPushButton("开始")
            self.start_btn.setObjectName("dialogPrimaryButton")
            self.start_btn.clicked.connect(self._start_backup)
            self.start_btn.setEnabled(False)

            self.cancel_btn = QPushButton("取消")
            self.cancel_btn.setObjectName("dialogSecondaryButton")
            self.cancel_btn.clicked.connect(self._on_cancel_clicked)

            button_layout.addWidget(self.cancel_btn)
            button_layout.addWidget(self.start_btn)
            layout.addLayout(button_layout)

        except Exception as e:
            self.logger.error(f"Error setting up backup dialog UI: {str(e)}")
            raise

    def _load_history(self):
        try:
            self.history_list.clear()
            if not self.config:
                self.history_list.addItem(QListWidgetItem("暂无备份记录"))
                return

            self._history_entries = self.config.get_backup_history()
            if not self._history_entries:
                item = QListWidgetItem("暂无备份记录")
                item.setFlags(Qt.NoItemFlags)
                self.history_list.addItem(item)
                return

            for index, entry in enumerate(self._history_entries):
                list_item = QListWidgetItem(format_history_item(entry))
                list_item.setData(Qt.UserRole, entry.dest_path)
                list_item.setData(_HISTORY_INDEX_ROLE, index)
                list_item.setToolTip(entry.detail or entry.dest_path)
                self.history_list.addItem(list_item)

            self.clear_history_btn.setEnabled(bool(self._history_entries))

            last_dest = self.config.get_setting("last_backup_destination")
            if last_dest and os.path.isdir(last_dest):
                self._apply_destination(last_dest, show_summary=False)

        except Exception as e:
            self.logger.error(f"Error loading backup history: {str(e)}")

    def _on_history_item_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if not path:
            return
        self._apply_destination(path)

    def _apply_destination(self, path: str, show_summary: bool = True):
        self.path_edit.setText(path)
        if show_summary:
            self.status_label.setText(self._build_destination_summary(path))
        self.start_btn.setEnabled(True)

    def _browse_directory(self):
        try:
            if self.config and self.config.get_recent_backup_destinations():
                self._show_destination_menu()
                return

            self._open_directory_picker()

        except Exception as e:
            self.logger.error(f"Error browsing directory: {str(e)}")
            QMessageBox.critical(self, "错误", f"选择目录时出错：{str(e)}")

    def _show_destination_menu(self):
        menu = QMenu(self)
        for path in self.config.get_recent_backup_destinations():
            action = menu.addAction(path)
            action.triggered.connect(lambda checked=False, selected=path: self._select_destination(selected))

        menu.addSeparator()
        browse_action = menu.addAction("浏览其他目录...")
        browse_action.triggered.connect(self._open_directory_picker)
        menu.exec_(self.browse_btn.mapToGlobal(self.browse_btn.rect().bottomLeft()))

    def _open_directory_picker(self):
        initial_dir = os.path.expanduser("~")
        if self.config:
            initial_dir = self.config.get_setting(
                "last_backup_destination",
                initial_dir,
            )

        path = QFileDialog.getExistingDirectory(
            self,
            "选择备份目标目录",
            initial_dir,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if path:
            self._select_destination(path)

    def _select_destination(self, path: str):
        try:
            if os.listdir(path):
                result = QMessageBox.warning(
                    self,
                    "提示",
                    self._build_non_empty_directory_warning(path),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if result != QMessageBox.Yes:
                    return
        except OSError:
            QMessageBox.warning(self, "提示", "无法读取目标目录内容，请换一个目录")
            return

        self._apply_destination(path)
        if self.config:
            self.config.add_recent_backup_destination(path)

    def reload_history(self):
        self._load_history()

    def set_sources_need_calculate(self, need_calculate: bool) -> None:
        if need_calculate:
            self.calc_hint_label.setText(
                "提示：部分选中文件夹尚未计算大小，备份进度可能不准确。"
                "建议先在主窗口点击「计算」(F5) 后再备份。"
            )
            self.calc_hint_label.setVisible(True)
        else:
            self.calc_hint_label.setVisible(False)

    def _show_history_context_menu(self, position):
        item = self.history_list.itemAt(position)
        if item is None or item.data(_HISTORY_INDEX_ROLE) is None:
            return

        menu = QMenu(self)
        delete_action = menu.addAction("删除此条")
        delete_action.triggered.connect(lambda: self._remove_history_item(item))
        menu.exec_(self.history_list.mapToGlobal(position))

    def _remove_history_item(self, item: QListWidgetItem) -> None:
        index = item.data(_HISTORY_INDEX_ROLE)
        if self.config is None or index is None:
            return

        self.config.remove_backup_history_at(index)
        self.reload_history()

    def _clear_all_history(self) -> None:
        if not self.config or not self._history_entries:
            return

        result = QMessageBox.question(
            self,
            "清空历史",
            "确定要清空全部备份历史记录吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            return

        self.config.clear_backup_history()
        self.reload_history()

    def _start_backup(self):
        try:
            path = self.path_edit.text().strip()
            if not path:
                QMessageBox.warning(self, "提示", "请先选择备份目标目录")
                return

            self.start_btn.setEnabled(False)
            self.status_label.setText("正在准备备份...")
            self.backup_started.emit(path)

        except Exception as e:
            self.logger.error(f"Error starting backup: {str(e)}")
            QMessageBox.critical(self, "错误", f"开始备份时出错：{str(e)}")

    def abort_prepare(self):
        """启动备份失败时恢复对话框到可重试状态。"""
        self._backup_in_progress = False
        self._backup_failed = False
        self.progress_bar.setVisible(False)
        self.browse_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("取消")
        self.start_btn.setEnabled(bool(self.path_edit.text().strip()))
        path = self.path_edit.text().strip()
        if path:
            self.status_label.setText(self._build_destination_summary(path))
        else:
            self.status_label.setText("选择目录后开始备份")

    def begin_backup(self):
        self._backup_failed = False
        self._backup_in_progress = True
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.history_list.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("停止备份")
        self.status_label.setText("正在准备备份...")

    def _on_cancel_clicked(self):
        if self._backup_in_progress:
            self.set_stopping_state()
            self.backup_stop_requested.emit()
            return

        self.reject()

    def set_stopping_state(self):
        """用户请求停止备份时的即时反馈。"""
        self.status_label.setText("正在停止备份...\n请稍候，正在等待当前步骤结束")

    def closeEvent(self, event: QCloseEvent):
        if self._backup_in_progress:
            if self.cancel_btn.isEnabled():
                self._on_cancel_clicked()
            event.ignore()
            return

        super().closeEvent(event)

    def _reset_after_backup(self):
        self._backup_in_progress = False
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("关闭")
        self.history_list.setEnabled(True)

    def update_progress(self, current_file: str, current: int, total: int, speed: float, processed_bytes: int, total_bytes: int):
        try:
            if total_bytes > 0:
                progress = min(100, int(processed_bytes * 100 / total_bytes))
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(progress)
                file_text = f"{current}/{total}" if total else str(current)
                processed_text = f"{self._format_size(processed_bytes)} / {self._format_size(total_bytes)}"
                progress_text = f"{progress}%"
            elif total > 0:
                progress = min(100, int(current * 100 / total))
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(progress)
                file_text = f"{current}/{total}"
                processed_text = self._format_size(processed_bytes)
                progress_text = f"{progress}%"
            else:
                self.progress_bar.setRange(0, 0)
                file_text = f"{current}/?" if current else "扫描中"
                processed_text = self._format_size(processed_bytes)
                progress_text = "进行中"

            current_name = os.path.basename(current_file) if current_file else "准备中"
            self.status_label.setText(
                f"正在备份：{current_name}\n"
                f"文件：{file_text}（{progress_text}）\n"
                f"速度：{self._format_speed(speed)} | 已处理：{processed_text}"
            )

        except Exception as e:
            self.logger.error(f"Error updating backup progress: {str(e)}")

    def backup_failed(self, _title: str, message: str, summary: str = ""):
        try:
            self._backup_failed = True
            self.progress_bar.setVisible(False)
            self.browse_btn.setEnabled(True)
            self._reset_after_backup()
            self.start_btn.setEnabled(True)
            status = f"备份失败：{message}"
            if summary:
                status = f"{status}\n{summary}"
            self.status_label.setText(status)

        except Exception as e:
            self.logger.error(f"Error handling backup failure: {str(e)}")

    def backup_finished(self, success: bool, summary: str = ""):
        try:
            self.progress_bar.setVisible(False)
            self.browse_btn.setEnabled(True)
            self._reset_after_backup()

            if self._backup_failed:
                self.start_btn.setEnabled(True)
            elif success:
                status = "备份已完成（合并并覆盖）"
                if summary:
                    status = f"{status}\n{summary}"
                self.status_label.setText(status)
                dialog_message = "备份已完成：已合并已有目录，并覆盖同名文件。"
                if summary:
                    dialog_message = f"{dialog_message}\n\n{summary}"
                QMessageBox.information(self, "完成", dialog_message)
                self.start_btn.setEnabled(False)
            else:
                status = "备份已取消，已保留已复制内容"
                if summary:
                    status = f"{status}\n{summary}"
                self.status_label.setText(status)
                self.start_btn.setEnabled(True)

            if self.config:
                self.reload_history()

        except Exception as e:
            self.logger.error(f"Error handling backup finished: {str(e)}")

    def _build_destination_summary(self, path: str) -> str:
        return f"将备份到：{path}\n备份方式：合并已有目录，覆盖同名文件"

    def _build_non_empty_directory_warning(self, path: str) -> str:
        return (
            "目标目录不是空文件夹。\n\n"
            f"目标路径：{path}\n"
            "继续后将按“合并并覆盖”方式备份：\n"
            "- 已有同名文件会被覆盖\n"
            "- 其他文件会保留\n\n"
            "是否继续？"
        )

    def _format_speed(self, bytes_per_second: float) -> str:
        try:
            units = ["B/s", "KB/s", "MB/s", "GB/s"]
            speed = bytes_per_second
            unit_index = 0

            while speed >= 1024 and unit_index < len(units) - 1:
                speed /= 1024
                unit_index += 1

            return f"{speed:.1f} {units[unit_index]}"

        except Exception as e:
            self.logger.error(f"Error formatting speed: {str(e)}")
            return "0 B/s"

    def _format_size(self, size_in_bytes: int) -> str:
        try:
            return format_bytes(size_in_bytes, empty_text="0 B")
        except Exception as e:
            self.logger.error(f"Error formatting size: {str(e)}")
            return "0 B"
