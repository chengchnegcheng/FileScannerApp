from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QProgressBar, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
import os
import logging

class BackupDialog(QDialog):
    """备份对话框"""
    
    backup_started = pyqtSignal(str)  # 发送目标路径
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._setup_ui()
        
    def _setup_ui(self):
        """设置UI"""
        try:
            self.setWindowTitle("备份文件夹")
            self.setMinimumWidth(500)
            
            # 创建主布局
            layout = QVBoxLayout(self)
            layout.setSpacing(10)
            
            # 目标路径选择
            path_layout = QHBoxLayout()
            self.path_label = QLabel("目标路径:")
            self.path_edit = QLineEdit()
            self.path_edit.setReadOnly(True)
            self.browse_btn = QPushButton("浏览...")
            self.browse_btn.clicked.connect(self._browse_directory)
            
            path_layout.addWidget(self.path_label)
            path_layout.addWidget(self.path_edit)
            path_layout.addWidget(self.browse_btn)
            
            # 进度显示
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            
            # 状态标签
            self.status_label = QLabel()
            self.status_label.setAlignment(Qt.AlignCenter)
            
            # 按钮布局
            button_layout = QHBoxLayout()
            self.start_btn = QPushButton("开始备份")
            self.start_btn.clicked.connect(self._start_backup)
            self.start_btn.setEnabled(False)
            
            self.cancel_btn = QPushButton("取消")
            self.cancel_btn.clicked.connect(self.reject)
            
            button_layout.addWidget(self.start_btn)
            button_layout.addWidget(self.cancel_btn)
            
            # 添加所有组件到主布局
            layout.addLayout(path_layout)
            layout.addWidget(self.progress_bar)
            layout.addWidget(self.status_label)
            layout.addLayout(button_layout)
            
        except Exception as e:
            self.logger.error(f"Error setting up backup dialog UI: {str(e)}")
            raise
            
    def _browse_directory(self):
        """浏览选择目标目录"""
        try:
            path = QFileDialog.getExistingDirectory(
                self,
                "选择备份目标文件夹",
                os.path.expanduser("~"),
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            if path:
                # 检查目录是否为空
                if os.listdir(path):
                    result = QMessageBox.warning(
                        self,
                        "警告",
                        "选择的目录不为空，是否继续？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if result != QMessageBox.Yes:
                        return
                
                self.path_edit.setText(path)
                self.start_btn.setEnabled(True)
                
        except Exception as e:
            self.logger.error(f"Error browsing directory: {str(e)}")
            QMessageBox.critical(self, "错误", f"选择目录时出错：{str(e)}")
            
    def _start_backup(self):
        """开始备份"""
        try:
            path = self.path_edit.text()
            if not path:
                QMessageBox.warning(self, "警告", "请先选择备份目标文件夹")
                return
                
            # 发送开始备份信号
            self.backup_started.emit(path)
            
            # 更新UI状态
            self.progress_bar.setVisible(True)
            self.start_btn.setEnabled(False)
            self.browse_btn.setEnabled(False)
            self.cancel_btn.setText("关闭")
            
        except Exception as e:
            self.logger.error(f"Error starting backup: {str(e)}")
            QMessageBox.critical(self, "错误", f"开始备份时出错：{str(e)}")
            
    def update_progress(self, current_file: str, current: int, total: int, speed: float, total_bytes: int):
        """更新进度显示"""
        try:
            # 更新进度条
            progress = int(current * 100 / total)
            self.progress_bar.setValue(progress)
            
            # 更新状态标签
            status = (
                f"正在备份: {os.path.basename(current_file)}\n"
                f"进度: {current}/{total} ({progress}%)\n"
                f"速度: {self._format_speed(speed)}"
            )
            self.status_label.setText(status)
            
        except Exception as e:
            self.logger.error(f"Error updating backup progress: {str(e)}")
            
    def backup_finished(self, success: bool):
        """处理备份完成"""
        try:
            self.progress_bar.setVisible(False)
            
            if success:
                self.status_label.setText("备份完成")
                QMessageBox.information(self, "完成", "备份已完成")
            else:
                self.status_label.setText("备份已取消")
            
            self.close()
            
        except Exception as e:
            self.logger.error(f"Error handling backup finished: {str(e)}")
            
    def _format_speed(self, bytes_per_second: float) -> str:
        """格式化速度显示"""
        try:
            units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
            speed = bytes_per_second
            unit_index = 0
            
            while speed >= 1024 and unit_index < len(units) - 1:
                speed /= 1024
                unit_index += 1
                
            return f"{speed:.1f} {units[unit_index]}"
            
        except Exception as e:
            self.logger.error(f"Error formatting speed: {str(e)}")
            return "0 B/s" 