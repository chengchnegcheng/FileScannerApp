from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


MAX_BACKUP_HISTORY = 20

STATUS_LABELS = {
    "success": "成功",
    "cancelled": "已取消",
    "failed": "失败",
}


@dataclass(frozen=True)
class BackupHistoryEntry:
    timestamp: str
    dest_path: str
    source_names: list[str]
    status: str
    files_copied: int = 0
    bytes_copied: int = 0
    duration_seconds: float = 0.0
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "dest_path": self.dest_path,
            "source_names": list(self.source_names),
            "status": self.status,
            "files_copied": self.files_copied,
            "bytes_copied": self.bytes_copied,
            "duration_seconds": self.duration_seconds,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BackupHistoryEntry:
        source_names = data.get("source_names") or []
        if isinstance(source_names, str):
            source_names = [source_names]
        return cls(
            timestamp=str(data.get("timestamp") or ""),
            dest_path=str(data.get("dest_path") or ""),
            source_names=[str(name) for name in source_names if name],
            status=str(data.get("status") or "failed"),
            files_copied=int(data.get("files_copied") or 0),
            bytes_copied=int(data.get("bytes_copied") or 0),
            duration_seconds=float(data.get("duration_seconds") or 0),
            detail=str(data.get("detail") or ""),
        )


def create_backup_history_entry(
    *,
    dest_path: str,
    source_names: list[str],
    status: str,
    files_copied: int = 0,
    bytes_copied: int = 0,
    duration_seconds: float = 0.0,
    detail: str = "",
    timestamp: Optional[datetime] = None,
) -> BackupHistoryEntry:
    moment = timestamp or datetime.now()
    return BackupHistoryEntry(
        timestamp=moment.strftime("%Y-%m-%d %H:%M:%S"),
        dest_path=dest_path,
        source_names=source_names,
        status=status,
        files_copied=files_copied,
        bytes_copied=bytes_copied,
        duration_seconds=duration_seconds,
        detail=detail,
    )


def parse_backup_history(records: Optional[list[Any]]) -> list[BackupHistoryEntry]:
    if not records:
        return []

    entries: list[BackupHistoryEntry] = []
    for record in records:
        if isinstance(record, dict):
            try:
                entries.append(BackupHistoryEntry.from_dict(record))
            except (TypeError, ValueError):
                continue
    return entries


def format_history_item(entry: BackupHistoryEntry) -> str:
    status_text = STATUS_LABELS.get(entry.status, entry.status)
    source_text = "、".join(entry.source_names[:3])
    if len(entry.source_names) > 3:
        source_text += f" 等{len(entry.source_names)}项"
    if not source_text:
        source_text = "未记录源目录"

    return (
        f"{entry.timestamp} | {status_text} | {entry.dest_path}\n"
        f"源：{source_text}"
    )
