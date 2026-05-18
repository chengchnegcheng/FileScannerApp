import logging
import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from utils.size_formatter import format_bytes


class BackupDialog(QDialog):
    """\u5907\u4efd\u76ee\u5f55\u5bf9\u8bdd\u6846\u3002"""

    backup_started = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._setup_ui()

    def _setup_ui(self):
        try:
            self.setWindowTitle("\u5907\u4efd\u76ee\u5f55")
            self.setMinimumWidth(560)
            self.setModal(True)

            layout = QVBoxLayout(self)
            layout.setSpacing(12)
            layout.setContentsMargins(16, 16, 16, 16)

            card = QFrame()
            card.setObjectName("dialogCard")
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(10)
            card_layout.setContentsMargins(14, 14, 14, 14)

            self.path_label = QLabel("\u76ee\u6807\u8def\u5f84")
            self.path_label.setObjectName("dialogLabel")

            path_layout = QHBoxLayout()
            path_layout.setSpacing(8)
            self.path_edit = QLineEdit()
            self.path_edit.setReadOnly(True)
            self.path_edit.setPlaceholderText("\u9009\u62e9\u5907\u4efd\u76ee\u6807\u76ee\u5f55")

            self.browse_btn = QPushButton("\u6d4f\u89c8")
            self.browse_btn.setObjectName("dialogSecondaryButton")
            self.browse_btn.clicked.connect(self._browse_directory)

            path_layout.addWidget(self.path_edit)
            path_layout.addWidget(self.browse_btn)

            self.progress_bar = QProgressBar()
            self.progress_bar.setObjectName("dialogProgressBar")
            self.progress_bar.setVisible(False)

            self.status_label = QLabel("\u9009\u62e9\u76ee\u5f55\u540e\u5f00\u59cb\u5907\u4efd")
            self.status_label.setObjectName("dialogStatusLabel")
            self.status_label.setWordWrap(True)
            self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            card_layout.addWidget(self.path_label)
            card_layout.addLayout(path_layout)
            card_layout.addWidget(self.progress_bar)
            card_layout.addWidget(self.status_label)
            layout.addWidget(card)

            button_layout = QHBoxLayout()
            button_layout.addStretch(1)

            self.start_btn = QPushButton("\u5f00\u59cb")
            self.start_btn.setObjectName("dialogPrimaryButton")
            self.start_btn.clicked.connect(self._start_backup)
            self.start_btn.setEnabled(False)

            self.cancel_btn = QPushButton("\u53d6\u6d88")
            self.cancel_btn.setObjectName("dialogSecondaryButton")
            self.cancel_btn.clicked.connect(self.reject)

            button_layout.addWidget(self.cancel_btn)
            button_layout.addWidget(self.start_btn)
            layout.addLayout(button_layout)

        except Exception as e:
            self.logger.error(f"Error setting up backup dialog UI: {str(e)}")
            raise

    def _browse_directory(self):
        try:
            path = QFileDialog.getExistingDirectory(
                self,
                "\u9009\u62e9\u5907\u4efd\u76ee\u6807\u76ee\u5f55",
                os.path.expanduser("~"),
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
            )

            if path:
                if os.listdir(path):
                    result = QMessageBox.warning(
                        self,
                        "\u63d0\u793a",
                        "\u6240\u9009\u76ee\u5f55\u975e\u7a7a\uff0c\u662f\u5426\u7ee7\u7eed\u5907\u4efd\u5230\u8be5\u76ee\u5f55\uff1f",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No,
                    )
                    if result != QMessageBox.Yes:
                        return

                self.path_edit.setText(path)
                self.status_label.setText(f"\u5c06\u5907\u4efd\u5230\uff1a{path}")
                self.start_btn.setEnabled(True)

        except Exception as e:
            self.logger.error(f"Error browsing directory: {str(e)}")
            QMessageBox.critical(self, "\u9519\u8bef", f"\u9009\u62e9\u76ee\u5f55\u65f6\u51fa\u9519\uff1a{str(e)}")

    def _start_backup(self):
        try:
            path = self.path_edit.text().strip()
            if not path:
                QMessageBox.warning(self, "\u63d0\u793a", "\u8bf7\u5148\u9009\u62e9\u5907\u4efd\u76ee\u6807\u76ee\u5f55")
                return

            self.backup_started.emit(path)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.start_btn.setEnabled(False)
            self.browse_btn.setEnabled(False)
            self.cancel_btn.setEnabled(True)
            self.cancel_btn.setText("关闭")
            self.status_label.setText("\u6b63\u5728\u51c6\u5907\u5907\u4efd...")

        except Exception as e:
            self.logger.error(f"Error starting backup: {str(e)}")
            QMessageBox.critical(self, "\u9519\u8bef", f"\u5f00\u59cb\u5907\u4efd\u65f6\u51fa\u9519\uff1a{str(e)}")

    def update_progress(self, current_file: str, current: int, total: int, speed: float, total_bytes: int):
        try:
            progress = int(current * 100 / total) if total else 0
            self.progress_bar.setValue(progress)
            self.status_label.setText(
                f"\u6b63\u5728\u5907\u4efd\uff1a{os.path.basename(current_file)}\n"
                f"\u8fdb\u5ea6\uff1a{current}/{total}\uff08{progress}%\uff09\n"
                f"\u901f\u5ea6\uff1a{self._format_speed(speed)} | \u5df2\u5904\u7406\uff1a{self._format_size(total_bytes)}"
            )

        except Exception as e:
            self.logger.error(f"Error updating backup progress: {str(e)}")

    def backup_finished(self, success: bool):
        try:
            self.progress_bar.setVisible(False)
            self.browse_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
            self.cancel_btn.setText("关闭")

            if success:
                self.status_label.setText("\u5907\u4efd\u5b8c\u6210")
                QMessageBox.information(self, "\u5b8c\u6210", "\u5907\u4efd\u5df2\u5b8c\u6210")
                self.start_btn.setEnabled(False)
            else:
                self.status_label.setText("\u5907\u4efd\u5df2\u53d6\u6d88")
                self.start_btn.setEnabled(True)

        except Exception as e:
            self.logger.error(f"Error handling backup finished: {str(e)}")

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
