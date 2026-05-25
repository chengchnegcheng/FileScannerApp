"""Pytest 全局 fixture：隔离应用数据目录，避免写入真实 %LOCALAPPDATA%。"""
from __future__ import annotations

import logging
import tempfile

import pytest


@pytest.fixture(autouse=True)
def isolated_app_data_dir(monkeypatch):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        monkeypatch.setenv("LOCALAPPDATA", temp_dir)
        monkeypatch.setenv("APPDATA", temp_dir)
        yield
        logging.shutdown()
