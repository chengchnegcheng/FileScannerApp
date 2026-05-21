from __future__ import annotations

import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from utils.size_formatter import format_bytes

DISK_SPACE_MARGIN_RATIO = 1.05


class BackupCancelled(Exception):
    """用户取消备份时抛出。"""


@dataclass
class BackupStats:
    dest_path: str = ""
    src_paths: list[str] = field(default_factory=list)
    files_copied: int = 0
    bytes_copied: int = 0
    duration_seconds: float = 0.0
    rolled_back: bool = False
    rollback_error: Optional[str] = None

    def format_summary(self) -> str:
        lines = [
            f"目标：{self.dest_path}",
            f"源目录：{len(self.src_paths)} 个",
            f"已复制：{self.files_copied} 个文件，{format_bytes(self.bytes_copied)}",
            f"耗时：{self._format_duration()}",
        ]
        if self.rolled_back:
            lines.append("失败后已自动回滚目标目录中的本次变更")
            if self.rollback_error:
                lines.append(f"回滚说明：{self.rollback_error}")
        return "\n".join(lines)

    def _format_duration(self) -> str:
        seconds = max(self.duration_seconds, 0.0)
        if seconds < 60:
            return f"{seconds:.1f} 秒"
        minutes = int(seconds // 60)
        remain = seconds % 60
        return f"{minutes} 分 {remain:.0f} 秒"


def estimate_backup_bytes(
    src_paths: list[str],
    known_sizes: Optional[dict[str, int]] = None,
) -> int:
    total = 0
    for src_path in src_paths:
        total += _estimate_single_source_bytes(src_path, known_sizes)
    return total


def estimate_backup_bytes_for_request(
    src_paths: list[str],
    dest_path: str,
    known_sizes: Optional[dict[str, int]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> int:
    """估算备份所需空间；目标已有同名目录时按增量估算，避免误拦合并备份。"""
    normalized_dest = os.path.abspath(dest_path)
    total = 0

    for src_path in src_paths:
        _raise_if_cancelled(should_stop)
        normalized_src = os.path.abspath(src_path)
        target_dir = os.path.join(normalized_dest, Path(normalized_src).name)
        if os.path.isdir(target_dir):
            known_size = None
            if known_sizes:
                known_size = known_sizes.get(normalized_src) or known_sizes.get(src_path)
            if known_size is not None:
                # 已计算过大小：用源目录总大小做保守估计，避免合并前再全盘遍历
                total += max(known_size, 0)
            else:
                total += _estimate_merge_incremental_bytes(
                    normalized_src,
                    target_dir,
                    should_stop,
                )
        else:
            total += _estimate_single_source_bytes(src_path, known_sizes, should_stop)

    return total


def _estimate_single_source_bytes(
    src_path: str,
    known_sizes: Optional[dict[str, int]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> int:
    normalized = os.path.abspath(src_path)
    if known_sizes and normalized in known_sizes:
        return max(known_sizes[normalized], 0)
    if known_sizes and src_path in known_sizes:
        return max(known_sizes[src_path], 0)
    return _walk_directory_bytes(normalized, should_stop)


def _estimate_merge_incremental_bytes(
    source_dir: str,
    target_dir: str,
    should_stop: Optional[Callable[[], bool]] = None,
) -> int:
    needed = 0

    for root, _, files in os.walk(source_dir):
        _raise_if_cancelled(should_stop)
        for file_name in files:
            source_file = os.path.join(root, file_name)
            rel_path = os.path.relpath(source_file, source_dir)
            target_file = os.path.join(target_dir, rel_path)

            try:
                source_size = os.path.getsize(source_file)
            except OSError:
                continue

            if not os.path.exists(target_file):
                needed += source_size
                continue

            try:
                if os.path.getsize(target_file) < source_size:
                    needed += source_size
            except OSError:
                needed += source_size

    return needed


def _raise_if_cancelled(should_stop: Optional[Callable[[], bool]]) -> None:
    if should_stop and should_stop():
        raise BackupCancelled("Operation cancelled")


def _walk_directory_bytes(
    path: str,
    should_stop: Optional[Callable[[], bool]] = None,
) -> int:
    total = 0
    for root, _, files in os.walk(path):
        _raise_if_cancelled(should_stop)
        for file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                total += os.path.getsize(file_path)
            except OSError:
                continue
    return total


def check_backup_disk_space(
    dest_path: str,
    required_bytes: int,
    margin_ratio: float = DISK_SPACE_MARGIN_RATIO,
) -> tuple[bool, int, int]:
    usage = shutil.disk_usage(dest_path)
    free_bytes = int(getattr(usage, "free", usage[2]))
    needed = int(required_bytes * margin_ratio)
    return free_bytes >= needed, free_bytes, needed


def format_disk_space_error(required_bytes: int, free_bytes: int, needed_bytes: int) -> str:
    return (
        "目标磁盘空间不足，无法开始备份。\n"
        f"预计需要：{format_bytes(needed_bytes)}（含 {int((DISK_SPACE_MARGIN_RATIO - 1) * 100)}% 余量）\n"
        f"当前可用：{format_bytes(free_bytes)}\n"
        f"备份数据约：{format_bytes(required_bytes)}"
    )


class BackupRollbackSession:
    """记录备份中的新建与覆盖，失败时回滚（用户取消不回滚）。"""

    def __init__(self, dest_path: str):
        self.dest_path = os.path.abspath(dest_path)
        self._staging_dir = tempfile.mkdtemp(prefix="filescanner_backup_")
        self._overwritten: dict[str, str] = {}
        self._created_files: list[str] = []
        self._new_top_level_dirs: list[str] = []
        self._snapshots: dict[str, set[str]] = {}

    def begin_source_target(self, target_path: str) -> None:
        normalized_target = os.path.abspath(target_path)
        if not os.path.exists(normalized_target):
            self._new_top_level_dirs.append(normalized_target)
            self._snapshots[normalized_target] = set()
            return

        self._snapshots[normalized_target] = _snapshot_relative_files(normalized_target)

    def before_copy(self, dst: str) -> None:
        normalized_dst = os.path.abspath(dst)
        if os.path.isfile(normalized_dst):
            self._backup_overwritten_file(normalized_dst)
            return

        if not os.path.lexists(normalized_dst):
            self._created_files.append(normalized_dst)

    def after_copy(self, dst: str, bytes_copied: int, stats: BackupStats) -> None:
        stats.files_copied += 1
        stats.bytes_copied += max(bytes_copied, 0)

    def rollback(self) -> Optional[str]:
        errors: list[str] = []

        for dst in sorted(self._created_files, key=len, reverse=True):
            try:
                if os.path.isfile(dst):
                    os.remove(dst)
            except OSError as exc:
                errors.append(f"删除 {dst} 失败：{exc}")

        for dst, staging_path in self._overwritten.items():
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(staging_path, dst)
            except OSError as exc:
                errors.append(f"恢复 {dst} 失败：{exc}")

        for target_path in self._new_top_level_dirs:
            if os.path.isdir(target_path):
                try:
                    shutil.rmtree(target_path)
                except OSError as exc:
                    errors.append(f"移除 {target_path} 失败：{exc}")
            else:
                self._prune_empty_dirs(target_path, errors)

        for target_path, snapshot in self._snapshots.items():
            if target_path in self._new_top_level_dirs:
                continue
            self._prune_new_paths_under_target(target_path, snapshot, errors)

        self.cleanup()
        if not errors:
            return None
        return "；".join(errors)

    def _prune_new_paths_under_target(
        self,
        target_path: str,
        snapshot: set[str],
        errors: list[str],
    ) -> None:
        current_files = _snapshot_relative_files(target_path)
        new_rel_paths = sorted(current_files - snapshot, key=len, reverse=True)
        for rel_path in new_rel_paths:
            full_path = os.path.join(target_path, rel_path.replace("/", os.sep))
            try:
                if os.path.isfile(full_path):
                    os.remove(full_path)
                elif os.path.isdir(full_path):
                    shutil.rmtree(full_path)
            except OSError as exc:
                errors.append(f"移除 {full_path} 失败：{exc}")

        self._prune_empty_dirs(target_path, errors)

    def _prune_empty_dirs(self, target_path: str, errors: list[str]) -> None:
        for root, dirs, _ in os.walk(target_path, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if os.path.isdir(dir_path) and not os.listdir(dir_path):
                        os.rmdir(dir_path)
                except OSError as exc:
                    errors.append(f"清理目录 {dir_path} 失败：{exc}")

    def _backup_overwritten_file(self, dst: str) -> None:
        rel_path = os.path.relpath(dst, self.dest_path)
        staging_path = os.path.join(self._staging_dir, rel_path)
        os.makedirs(os.path.dirname(staging_path), exist_ok=True)
        shutil.copy2(dst, staging_path)
        self._overwritten[dst] = staging_path

    def cleanup(self) -> None:
        if os.path.isdir(self._staging_dir):
            shutil.rmtree(self._staging_dir, ignore_errors=True)


def _snapshot_relative_files(root: str) -> set[str]:
    files: set[str] = set()
    if not os.path.isdir(root):
        return files

    for dirpath, _, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        for file_name in filenames:
            if rel_dir == ".":
                rel_file = file_name
            else:
                rel_file = os.path.join(rel_dir, file_name)
            files.add(rel_file.replace("\\", "/"))
    return files
