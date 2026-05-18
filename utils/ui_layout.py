from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MinimalWorkflowLayout:
    primary_actions: list[str]
    secondary_actions: list[str]
    footer_stats: list[str]


def get_minimal_workflow_layout() -> MinimalWorkflowLayout:
    return MinimalWorkflowLayout(
        primary_actions=["select", "scan", "stop"],
        secondary_actions=["select_all", "calculate", "export", "backup"],
        footer_stats=["folders", "selected", "files", "size"],
    )
