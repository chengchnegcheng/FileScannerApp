import logging
from datetime import datetime

class ErrorHandler:
    def __init__(self, logger):
        self.logger = logger
        self.error_count = 0
        self.last_error_time = None
        
    def handle_error(self, error_type: str, error: Exception, context: str = None):
        """统一错误处理"""
        current_time = datetime.now()
        self.error_count += 1
        
        # 记录错误
        error_msg = f"{error_type}: {str(error)}"
        if context:
            error_msg = f"{error_msg} | Context: {context}"
            
        self.logger.error(error_msg)
        
        # 检查错误频率
        if self.last_error_time:
            time_diff = (current_time - self.last_error_time).total_seconds()
            if time_diff < 60 and self.error_count > 10:
                self.logger.critical("Too many errors occurring! Consider stopping operations.")
                return False
                
        self.last_error_time = current_time
        return True

    def reset_error_count(self):
        """重置错误计数"""
        self.error_count = 0
        self.last_error_time = None
        
    def get_error_status(self) -> tuple[int, datetime]:
        """获取当前错误状态"""
        return self.error_count, self.last_error_time 