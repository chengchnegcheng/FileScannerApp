from PyQt5.QtCore import QThread, pyqtSignal
import logging
import time
from typing import List
from models.file_item import FileItem

class CalculateWorker(QThread):
    """计算大小工作线程"""
    
    progress = pyqtSignal(FileItem, int, int, float)  # 当前项目, 当前数量, 总数量, 速度
    finished = pyqtSignal()
    error = pyqtSignal(str, str)  # 错误标题, 错误消息
    
    def __init__(self, scanner, items: List[FileItem]):
        super().__init__()
        self.scanner = scanner
        self.items = items
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """运行计算任务"""
        try:
            total = len(self.items)
            for i, item in enumerate(self.items, 1):
                if self.scanner.stopped:
                    break
                    
                start_time = time.time()
                self.scanner.calculate_directory_info(item)
                elapsed = time.time() - start_time
                
                # 计算速度 (items/s)
                speed = 1.0 / elapsed if elapsed > 0 else 0
                
                self.progress.emit(item, i, total, speed)
                
            self.finished.emit()
            
        except Exception as e:
            self.logger.error(f"Error in calculate worker: {str(e)}")
            self.error.emit("计算错误", str(e)) 