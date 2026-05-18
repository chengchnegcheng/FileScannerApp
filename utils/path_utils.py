from __future__ import annotations

import sys
import os
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return get_project_root()


def get_app_data_dir(app_name: str = "FileScannerApp") -> Path:
    base_dir = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if base_dir:
        return Path(base_dir) / app_name

    home_dir = Path.home()
    windows_local = home_dir / "AppData" / "Local"
    if windows_local.exists() or os.name == "nt":
        return windows_local / app_name

    return home_dir / f".{app_name}"


def get_resource_base_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return get_project_root()


def get_resource_path(relative_path: str) -> Path:
    return get_resource_base_dir() / relative_path


def normalize_directory_path(path: str) -> str:
    if not path:
        return path

    normalized = path
    if os.name == "nt":
        normalized = normalized.replace("/", "\\")

    return os.path.normpath(normalized)
