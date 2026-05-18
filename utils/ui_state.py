from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionState:
    select_enabled: bool
    start_enabled: bool
    stop_enabled: bool
    calculate_enabled: bool
    export_enabled: bool
    backup_enabled: bool


def build_action_state(
    *,
    is_busy: bool,
    has_directory: bool,
    has_items: bool,
    has_checked: bool,
    cancel_requested: bool = False,
) -> ActionState:
    if is_busy:
        return ActionState(
            select_enabled=False,
            start_enabled=False,
            stop_enabled=not cancel_requested,
            calculate_enabled=False,
            export_enabled=False,
            backup_enabled=False,
        )

    return ActionState(
        select_enabled=True,
        start_enabled=has_directory,
        stop_enabled=False,
        calculate_enabled=has_checked,
        export_enabled=has_checked,
        backup_enabled=has_checked,
    )
