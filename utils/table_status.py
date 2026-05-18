from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StatusStyle:
    label: str
    foreground: str
    background: str


def get_status_style(status: str) -> StatusStyle:
    mapping = {
        "已计算": StatusStyle("已计算", "#166534", "#dcfce7"),
        "计算错误": StatusStyle("计算错误", "#991b1b", "#fee2e2"),
        "已取消": StatusStyle("已取消", "#92400e", "#fef3c7"),
    }

    return mapping.get(status, StatusStyle(status, "#475569", "#f1f5f9"))
