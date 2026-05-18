from PyQt5.QtCore import QThread, pyqtSignal
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    def _get_max_workers(self, total: int) -> int:
        return max(1, min(6, total))
        
    def run(self):
        """运行计算任务"""
        try:
            total = len(self.items)
            if total == 0:
                self.finished.emit()
                return

            completed = 0
            max_workers = self._get_max_workers(total)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {}
                for item in self.items:
                    if self.scanner.stopped:
                        break
                    start_time = time.time()
                    future = executor.submit(self.scanner.calculate_directory_info, item)
                    future_map[future] = (item, start_time)

                for future in as_completed(future_map):
                    if self.scanner.stopped:
                        break

                    item, start_time = future_map[future]
                    result = future.result()
                    elapsed = time.time() - start_time
                    speed = 1.0 / elapsed if elapsed > 0 else 0
                    completed += 1

                    self.progress.emit(result or item, completed, total, speed)
                
            self.finished.emit()
            
        except Exception as e:
            self.logger.error(f"Error in calculate worker: {str(e)}")
            self.error.emit("计算错误", str(e)) 
