import json
import os
import logging
from typing import Any, Optional, List

from utils.path_utils import get_app_data_dir, normalize_directory_path
from utils.backup_history import (
    MAX_BACKUP_HISTORY,
    BackupHistoryEntry,
    parse_backup_history,
)

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str | None = None):
        self.config_file = config_file or str(get_app_data_dir() / "config.json")
        self.logger = logging.getLogger(__name__)
        self._config = self._load_config()
        
    def _load_config(self) -> dict:
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            return {}
            
    def save_config(self):
        """保存配置"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving config: {str(e)}")
            
    def get_setting(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self._config.get(key, default)
        
    def set_setting(self, key: str, value: Any):
        """设置配置项"""
        self._config[key] = value
        
    def _dedupe_normalized_paths(self, paths: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for path in paths:
            if not path:
                continue

            normalized = normalize_directory_path(path)
            key = normalized.casefold() if os.name == "nt" else normalized
            if key in seen:
                continue

            seen.add(key)
            result.append(normalized)

        return result

    def get_recent_directories(self) -> list[str]:
        return self._dedupe_normalized_paths(self.get_setting("recent_directories", []))

    def add_recent_directory(self, path: str):
        """添加最近使用的目录"""
        try:
            if not path:
                return

            normalized = normalize_directory_path(path)
            recent_dirs = self._dedupe_normalized_paths(self.get_setting("recent_directories", []))
            key = normalized.casefold() if os.name == "nt" else normalized
            recent_dirs = [
                existing
                for existing in recent_dirs
                if (existing.casefold() if os.name == "nt" else existing) != key
            ]
            recent_dirs.insert(0, normalized)

            self.set_setting("recent_directories", recent_dirs[:10])
            self.set_setting("last_directory", normalized)
            self.save_config()

        except Exception as e:
            self.logger.error(f"Error adding recent directory: {str(e)}")

    def get_backup_history(self) -> list[BackupHistoryEntry]:
        return parse_backup_history(self.get_setting("backup_history", []))

    def add_backup_history(self, entry: BackupHistoryEntry) -> None:
        try:
            history = [record.to_dict() for record in self.get_backup_history()]
            history.insert(0, entry.to_dict())
            self.set_setting("backup_history", history[:MAX_BACKUP_HISTORY])
            self.add_recent_backup_destination(entry.dest_path)
            self.save_config()
        except Exception as e:
            self.logger.error(f"Error adding backup history: {str(e)}")

    def get_recent_backup_destinations(self) -> list[str]:
        return self._dedupe_normalized_paths(self.get_setting("recent_backup_destinations", []))

    def remove_backup_history_at(self, index: int) -> None:
        try:
            history = [record.to_dict() for record in self.get_backup_history()]
            if 0 <= index < len(history):
                history.pop(index)
                self.set_setting("backup_history", history)
                self.save_config()
        except Exception as e:
            self.logger.error(f"Error removing backup history: {str(e)}")

    def clear_backup_history(self) -> None:
        try:
            self.set_setting("backup_history", [])
            self.save_config()
        except Exception as e:
            self.logger.error(f"Error clearing backup history: {str(e)}")

    def add_recent_backup_destination(self, path: str) -> None:
        try:
            if not path:
                return

            normalized = normalize_directory_path(path)
            destinations = self._dedupe_normalized_paths(
                self.get_setting("recent_backup_destinations", [])
            )
            key = normalized.casefold() if os.name == "nt" else normalized
            destinations = [
                existing
                for existing in destinations
                if (existing.casefold() if os.name == "nt" else existing) != key
            ]
            destinations.insert(0, normalized)
            self.set_setting("recent_backup_destinations", destinations[:10])
            self.set_setting("last_backup_destination", normalized)
            self.save_config()
        except Exception as e:
            self.logger.error(f"Error adding recent backup destination: {str(e)}")
