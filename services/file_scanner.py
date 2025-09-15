import os
import shutil
import logging
from typing import Generator, Optional, Callable, List
from models.file_item import FileItem
from utils.config_manager import ConfigManager

class FileScanner:
    """文件扫描器类"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.stopped = False
        
    def stop(self):
        """停止扫描"""
        self.stopped = True
        
    def scan_directory(self, path: str) -> Generator[FileItem, None, None]:
        """扫描目录
        
        Args:
            path: 要扫描的目录路径
            
        Yields:
            FileItem: 扫描到的文件项
        """
        try:
            self.stopped = False
            
            # 遍历目录
            for entry in os.scandir(path):
                if self.stopped:
                    break
                    
                if entry.is_dir():
                    try:
                        item = FileItem(
                            name=entry.name,
                            path=entry.path,
                            is_directory=True
                        )
                        yield item
                    except Exception as e:
                        self.logger.error(f"Error scanning {entry.path}: {str(e)}")
                        
        except Exception as e:
            self.logger.error(f"Error scanning directory {path}: {str(e)}")
            raise
            
    def calculate_directory_info(self, item: FileItem) -> FileItem:
        """计算目录信息
        
        Args:
            item: 要计算的文件项
            
        Returns:
            FileItem: 更新后的文件项
        """
        try:
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(item.path):
                if self.stopped:
                    break
                    
                # 计算文件大小
                for file in files:
                    if self.stopped:
                        break
                    try:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                    except Exception as e:
                        self.logger.error(f"Error getting size of {file_path}: {str(e)}")
            
            # 更新文件项信息
            item.size = total_size
            item.file_count = file_count
            item.status = "已计算" if not self.stopped else "已取消"
            
            return item
            
        except Exception as e:
            self.logger.error(f"Error calculating info for {item.path}: {str(e)}")
            item.status = "计算错误"
            return item
            
    def backup_directories(
        self,
        src_paths: List[str],
        dest_path: str,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """备份目录
        
        Args:
            src_paths: 源目录路径列表
            dest_path: 目标目录路径
            progress_callback: 进度回调函数
            
        Returns:
            bool: 是否成功
        """
        try:
            self.stopped = False
            total_items = len(src_paths)
            
            for index, src_path in enumerate(src_paths, 1):
                if self.stopped:
                    return False
                    
                try:
                    # 创建目标目录
                    name = os.path.basename(src_path)
                    target_path = os.path.join(dest_path, name)
                    
                    # 复制目录
                    shutil.copytree(
                        src_path,
                        target_path,
                        symlinks=True,
                        ignore=None,
                        copy_function=lambda src, dst: self._copy_with_progress(
                            src, dst, progress_callback, index, total_items
                        ) if progress_callback else shutil.copy2(src, dst)
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error backing up {src_path}: {str(e)}")
                    return False
                    
            return not self.stopped
            
        except Exception as e:
            self.logger.error(f"Error backing up directories: {str(e)}")
            return False
            
    def _copy_with_progress(
        self,
        src: str,
        dst: str,
        callback: Callable,
        current: int,
        total: int
    ) -> None:
        """带进度的文件复制
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            callback: 进度回调函数
            current: 当前项目索引
            total: 总项目数
        """
        try:
            # 获取文件大小
            file_size = os.path.getsize(src)
            
            # 复制文件并报告进度
            with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
                copied = 0
                while True:
                    if self.stopped:
                        raise Exception("Operation cancelled")
                        
                    buf = fsrc.read(8192)
                    if not buf:
                        break
                        
                    fdst.write(buf)
                    copied += len(buf)
                    
                    if callback:
                        callback(src, current, total, copied)
                        
            # 复制文件属性
            shutil.copystat(src, dst)
            
        except Exception as e:
            self.logger.error(f"Error copying {src} to {dst}: {str(e)}")
            raise 