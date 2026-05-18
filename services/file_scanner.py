import os
import shutil
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional, Callable, List
from models.file_item import FileItem
from utils.config_manager import ConfigManager
from utils.path_utils import normalize_directory_path


def format_created_at(path: str) -> str:
    stat = os.stat(path)
    timestamp = getattr(stat, "st_ctime", None)
    if timestamp is None:
        return "未获取"
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

class FileScanner:
    """文件扫描器类"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.stopped = False
        self._dir_info_cache: dict[str, tuple[tuple[int, int], int, int]] = {}

    def clear_calculation_cache(self):
        """清空目录计算缓存。"""
        self._dir_info_cache.clear()

    def _get_directory_signature(self, path: str) -> Optional[tuple[int, int]]:
        try:
            stat = os.stat(path)
            return stat.st_mtime_ns, getattr(stat, "st_ctime_ns", int(stat.st_ctime * 1_000_000_000))
        except Exception as e:
            self.logger.error(f"Error getting directory signature for {path}: {str(e)}")
            return None

    def _calculate_directory_info_uncached(self, path: str) -> tuple[int, int]:
        total_size = 0
        file_count = 0
        pending = [path]

        while pending and not self.stopped:
            current = pending.pop()

            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        if self.stopped:
                            break
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                pending.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                total_size += entry.stat(follow_symlinks=False).st_size
                                file_count += 1
                        except Exception as e:
                            self.logger.error(f"Error scanning entry {entry.path}: {str(e)}")
            except Exception as e:
                self.logger.error(f"Error scanning directory {current}: {str(e)}")

        return total_size, file_count
        
    def stop(self):
        """停止扫描"""
        self.stopped = True

    def validate_backup_request(self, src_paths: List[str], dest_path: str) -> str:
        normalized_dest = os.path.abspath(dest_path)
        dest_dir = Path(normalized_dest)

        if not src_paths:
            raise ValueError("请先选择要备份的文件夹")

        if not dest_path:
            raise ValueError("请选择备份目标目录")

        if not dest_dir.exists() or not dest_dir.is_dir():
            raise ValueError("备份目标目录不存在")

        for src_path in src_paths:
            normalized_src = os.path.abspath(src_path)
            source_dir = Path(normalized_src)

            if not source_dir.exists() or not source_dir.is_dir():
                raise ValueError(f"源目录不存在：{src_path}")

            try:
                dest_dir.relative_to(source_dir)
                raise ValueError("目标目录不能位于源目录内部")
            except ValueError as exc:
                if str(exc) == "目标目录不能位于源目录内部":
                    raise

            target_dir = dest_dir / source_dir.name
            if target_dir.exists():
                raise ValueError(f"已存在同名备份目录：{target_dir}")

        return normalized_dest
        
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
            path = normalize_directory_path(path)
            for entry in os.scandir(path):
                if self.stopped:
                    break
                    
                if entry.is_dir():
                    try:
                        item = FileItem(
                            name=entry.name,
                            path=normalize_directory_path(entry.path),
                            is_directory=True,
                            created_at=format_created_at(entry.path),
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
            signature = self._get_directory_signature(item.path)
            cached = self._dir_info_cache.get(item.path)

            if signature is not None and cached is not None and cached[0] == signature:
                total_size, file_count = cached[1], cached[2]
            else:
                total_size, file_count = self._calculate_directory_info_uncached(item.path)
                if signature is not None and not self.stopped:
                    self._dir_info_cache[item.path] = (signature, total_size, file_count)
            
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
            path = normalize_directory_path(path)
            dest_path = self.validate_backup_request(src_paths, dest_path)
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
            start_time = time.time()
            
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
                        elapsed = time.time() - start_time
                        bytes_per_second = copied / elapsed if elapsed > 0 else 0
                        callback(src, current, total, bytes_per_second, file_size)
                        
            # 复制文件属性
            shutil.copystat(src, dst)
            
        except Exception as e:
            self.logger.error(f"Error copying {src} to {dst}: {str(e)}")
            raise 
