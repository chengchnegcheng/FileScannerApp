from PyQt5.QtCore import QThread, pyqtSignal
import logging
from models.file_item import FileItem

class ScanWorker(QThread):
    """扫描工作线程"""
    
    file_found = pyqtSignal(FileItem)  # 发现文件项
    finished = pyqtSignal(bool)  # 是否成功完成
    error = pyqtSignal(str, str)  # 错误标题, 错误消息
    
    def __init__(self, scanner, path: str):
        super().__init__()
        self.scanner = scanner
        self.path = path
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """运行扫描任务"""
        try:
            for item in self.scanner.scan_directory(self.path):
                if self.scanner.stopped:
                    break
                self.file_found.emit(item)
                
            self.finished.emit(not self.scanner.stopped)
            
        except Exception as e:
            self.logger.error(f"Error in scan worker: {str(e)}")
            self.error.emit("扫描错误", str(e))
            self.finished.emit(False) 