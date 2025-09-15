from PyQt5.QtCore import QThread, pyqtSignal
import logging
import time
from typing import List

class BackupWorker(QThread):
    """备份工作线程"""
    
    progress = pyqtSignal(str, int, int, float, int)  # 当前文件, 当前数量, 总数量, 速度, 总字节数
    finished = pyqtSignal(bool)  # 是否成功完成
    error = pyqtSignal(str, str)  # 错误标题, 错误消息
    
    def __init__(self, scanner, src_paths: List[str], dest_path: str):
        super().__init__()
        self.scanner = scanner
        self.src_paths = src_paths
        self.dest_path = dest_path
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """运行备份任务"""
        try:
            def progress_callback(current_file, current, total, speed):
                self.progress.emit(current_file, current, total, speed, 0)
                
            success = self.scanner.backup_directories(
                self.src_paths,
                self.dest_path,
                progress_callback
            )
            
            self.finished.emit(success)
            
        except Exception as e:
            self.logger.error(f"Error in backup worker: {str(e)}")
            self.error.emit("备份错误", str(e))
            self.finished.emit(False) 