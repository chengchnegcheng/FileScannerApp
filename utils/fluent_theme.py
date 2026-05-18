from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FluentTheme:
    window_background: str
    surface_primary: str
    surface_secondary: str
    primary_accent: str
    selection_fill: str
    stroke_subtle: str


def get_fluent_theme() -> FluentTheme:
    return FluentTheme(
        window_background="#f3f3f3",
        surface_primary="#ffffff",
        surface_secondary="#fafafa",
        primary_accent="#0f6cbd",
        selection_fill="#cfe8ff",
        stroke_subtle="#e5e5e5",
    )
