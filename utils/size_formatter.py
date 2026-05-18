from __future__ import annotations

from typing import Optional


SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]


def format_bytes(size_in_bytes: Optional[float], empty_text: str = "未计算") -> str:
    if size_in_bytes is None:
        return empty_text

    size = max(float(size_in_bytes), 0.0)
    unit_index = 0

    while size >= 1024 and unit_index < len(SIZE_UNITS) - 1:
        size /= 1024
        unit_index += 1

    precision = 0 if unit_index == 0 else 1
    return f"{size:.{precision}f} {SIZE_UNITS[unit_index]}"
