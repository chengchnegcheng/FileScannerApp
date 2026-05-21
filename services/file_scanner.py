import os
import shutil
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional, Callable, List
from models.file_item import FileItem
from services.backup_support import (
    BackupCancelled,
    BackupRollbackSession,
    BackupStats,
    check_backup_disk_space,
    estimate_backup_bytes_for_request,
    format_disk_space_error,
)
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
        self.last_backup_error: Optional[str] = None
        self.last_backup_stats: Optional[BackupStats] = None
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
        """停止当前正在运行的扫描、计算或备份任务。"""
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

        seen_source_names: dict[str, str] = {}
        for src_path in src_paths:
            source_name = Path(os.path.abspath(src_path)).name
            previous_path = seen_source_names.get(source_name)
            if previous_path is not None:
                raise ValueError(
                    f"选中了多个同名文件夹“{source_name}”，将备份到同一目标位置并互相覆盖："
                    f"{previous_path} 与 {src_path}"
                )
            seen_source_names[source_name] = src_path

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
            if target_dir.exists() and not target_dir.is_dir():
                raise ValueError(f"备份目标位置已存在同名文件：{target_dir}")

        return normalized_dest

    def validate_backup_disk_space(
        self,
        src_paths: List[str],
        dest_path: str,
        known_sizes: Optional[dict[str, int]] = None,
        required_bytes: Optional[int] = None,
    ) -> int:
        normalized_dest = self.validate_backup_request(src_paths, dest_path)
        if self.stopped:
            raise BackupCancelled("Operation cancelled")

        if required_bytes is None:
            required_bytes = estimate_backup_bytes_for_request(
                src_paths,
                normalized_dest,
                known_sizes,
                should_stop=lambda: self.stopped,
            )

        if self.stopped:
            raise BackupCancelled("Operation cancelled")

        has_space, free_bytes, needed_bytes = check_backup_disk_space(
            normalized_dest,
            required_bytes,
        )
        if not has_space:
            raise ValueError(
                format_disk_space_error(required_bytes, free_bytes, needed_bytes)
            )
        return required_bytes
        
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
        progress_callback: Optional[Callable] = None,
        progress_state: Optional[dict[str, int]] = None,
        known_sizes: Optional[dict[str, int]] = None,
        required_bytes: Optional[int] = None,
    ) -> bool:
        """备份选中的目录到目标位置（合并并覆盖）。"""
        started_at = time.perf_counter()
        stats = BackupStats(dest_path=dest_path, src_paths=list(src_paths))
        self.last_backup_stats = stats

        try:
            if self.stopped:
                return False

            self.last_backup_error = None
            dest_path = normalize_directory_path(dest_path)
            dest_path = self.validate_backup_request(src_paths, dest_path)
            if required_bytes is None:
                required_bytes = self.validate_backup_disk_space(
                    src_paths,
                    dest_path,
                    known_sizes,
                )
            stats.dest_path = dest_path

            progress_state = self._normalize_backup_progress_state(progress_state) if progress_callback else None
            self._backup_stats = stats

            for src_path in src_paths:
                if self.stopped:
                    return False

                rollback_session = BackupRollbackSession(dest_path)
                self._backup_rollback_session = rollback_session

                try:
                    name = os.path.basename(src_path)
                    target_path = os.path.join(dest_path, name)
                    rollback_session.begin_source_target(target_path)

                    shutil.copytree(
                        src_path,
                        target_path,
                        dirs_exist_ok=True,
                        symlinks=True,
                        ignore=None,
                        copy_function=lambda src, dst: self._copy_with_progress(
                            src,
                            dst,
                            progress_callback,
                            progress_state,
                        ),
                    )
                    rollback_session.cleanup()

                except Exception as e:
                    if not self.stopped:
                        self.last_backup_error = str(e)
                        stats.rolled_back = True
                        stats.rollback_error = rollback_session.rollback()
                    else:
                        rollback_session.cleanup()
                    self.logger.error(f"Error backing up {src_path}: {str(e)}")
                    return False
                finally:
                    self._backup_rollback_session = None

            return not self.stopped

        except Exception as e:
            if not self.stopped:
                self.last_backup_error = str(e)
            self.logger.error(f"Error backing up directories: {str(e)}")
            return False
        finally:
            stats.duration_seconds = time.perf_counter() - started_at
            self._backup_stats = None

    def _build_backup_progress_state(self, src_paths: List[str]) -> dict[str, int]:
        total_files = 0
        total_bytes = 0

        for src_path in src_paths:
            for root, _, files in os.walk(src_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    total_files += 1
                    total_bytes += os.path.getsize(file_path)

        return {
            "copied_files": 0,
            "copied_bytes": 0,
            "total_files": total_files,
            "total_bytes": total_bytes,
        }

    def _normalize_backup_progress_state(self, progress_state: Optional[dict[str, int]]) -> dict[str, int]:
        progress_state = progress_state or {}
        return {
            "copied_files": int(progress_state.get("copied_files", 0) or 0),
            "copied_bytes": int(progress_state.get("copied_bytes", 0) or 0),
            "total_files": int(progress_state.get("total_files", 0) or 0),
            "total_bytes": int(progress_state.get("total_bytes", 0) or 0),
        }

    def _copy_with_backup_tracking(self, src: str, dst: str) -> None:
        session = getattr(self, "_backup_rollback_session", None)
        stats = getattr(self, "_backup_stats", None)
        if session is not None:
            session.before_copy(dst)
        shutil.copy2(src, dst)
        if session is not None and stats is not None:
            session.after_copy(dst, os.path.getsize(dst), stats)

    def _copy_with_progress(
        self,
        src: str,
        dst: str,
        callback: Callable,
        progress_state: Optional[dict[str, int]],
    ) -> None:
        """复制单个文件并上报备份进度。"""
        try:
            session = getattr(self, "_backup_rollback_session", None)
            stats = getattr(self, "_backup_stats", None)
            if session is not None:
                session.before_copy(dst)

            file_size = os.path.getsize(src)
            start_time = time.time()

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
                    if progress_state is not None:
                        progress_state["copied_bytes"] += len(buf)

                    if callback and progress_state is not None:
                        elapsed = time.time() - start_time
                        bytes_per_second = copied / elapsed if elapsed > 0 else 0
                        current_file_index = progress_state["copied_files"] + 1
                        callback(
                            src,
                            current_file_index,
                            progress_state["total_files"],
                            bytes_per_second,
                            progress_state["copied_bytes"],
                            progress_state["total_bytes"],
                        )

            shutil.copystat(src, dst)
            if progress_state is not None:
                progress_state["copied_files"] += 1
            if session is not None and stats is not None:
                session.after_copy(dst, file_size, stats)

            if callback and progress_state is not None and file_size == 0:
                callback(
                    src,
                    progress_state["copied_files"],
                    progress_state["total_files"],
                    0.0,
                    progress_state["copied_bytes"],
                    progress_state["total_bytes"],
                )

        except Exception as e:
            self.logger.error(f"Error copying {src} to {dst}: {str(e)}")
            raise 
