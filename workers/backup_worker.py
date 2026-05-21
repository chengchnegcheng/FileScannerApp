from PyQt5.QtCore import QThread, pyqtSignal
import logging
from typing import List, Optional

from services.backup_support import BackupCancelled

class BackupWorker(QThread):
    """备份工作线程"""
    
    progress = pyqtSignal(str, int, int, float, int, int)  # 当前文件, 当前数量, 总数量, 速度, 总字节数
    finished = pyqtSignal(bool)  # 是否成功完成
    error = pyqtSignal(str, str)  # 错误标题, 错误消息
    
    def __init__(
        self,
        scanner,
        src_paths: List[str],
        dest_path: str,
        progress_state: Optional[dict[str, int]] = None,
        known_sizes: Optional[dict[str, int]] = None,
        required_bytes: Optional[int] = None,
    ):
        super().__init__()
        self.scanner = scanner
        self.src_paths = src_paths
        self.dest_path = dest_path
        self.progress_state = progress_state
        self.known_sizes = known_sizes
        self.required_bytes = required_bytes
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """运行备份任务（含磁盘预检，避免阻塞界面线程）。"""
        try:
            def progress_callback(current_file, current, total, speed, processed_bytes, total_bytes):
                self.progress.emit(current_file, current, total, speed, processed_bytes, total_bytes)

            self.progress.emit("", 0, 0, 0.0, 0, 0)

            normalized_dest = self.scanner.validate_backup_request(
                self.src_paths,
                self.dest_path,
            )
            if self.scanner.stopped:
                self.finished.emit(False)
                return

            required_bytes = self.required_bytes
            if required_bytes is None:
                required_bytes = self.scanner.validate_backup_disk_space(
                    self.src_paths,
                    normalized_dest,
                    self.known_sizes,
                )

            if self.scanner.stopped:
                self.finished.emit(False)
                return

            success = self.scanner.backup_directories(
                self.src_paths,
                normalized_dest,
                progress_callback,
                self.progress_state,
                self.known_sizes,
                required_bytes,
            )

            if not success and not self.scanner.stopped and self.scanner.last_backup_error:
                self.error.emit("备份错误", self.scanner.last_backup_error)

            self.finished.emit(success)

        except BackupCancelled:
            self.logger.info("Backup cancelled by user")
            self.finished.emit(False)
        except ValueError as e:
            self.logger.error(f"Backup validation failed: {str(e)}")
            self.error.emit("备份错误", str(e))
            self.finished.emit(False)
        except Exception as e:
            self.logger.error(f"Error in backup worker: {str(e)}")
            self.error.emit("备份错误", str(e))
            self.finished.emit(False)
