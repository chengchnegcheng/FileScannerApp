import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

class LogManager:
    """日志管理器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self._setup_logging()
        
    def _setup_logging(self):
        """设置日志"""
        try:
            # 创建日志目录
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)
            
            # 设置日志文件路径
            log_file = os.path.join(
                self.log_dir,
                f"app_{datetime.now().strftime('%Y%m%d')}.log"
            )
            
            # 配置根日志记录器
            logger = logging.getLogger()
            logger.setLevel(logging.INFO)
            
            # 创建文件处理器
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            
            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 设置格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理器
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            
        except Exception as e:
            print(f"Error setting up logging: {str(e)}")
            raise
            
    def log_operation(self, operation: str, details: str, result: str, level: str = "info"):
        """记录操作日志
        
        Args:
            operation: 操作名称
            details: 操作详情
            result: 操作结果
            level: 日志级别
        """
        try:
            logger = logging.getLogger(__name__)
            log_func = getattr(logger, level)
            log_func(
                f"Operation: {operation}\n"
                f"Details: {details}\n"
                f"Result: {result}"
            )
        except Exception as e:
            print(f"Error logging operation: {str(e)}") 