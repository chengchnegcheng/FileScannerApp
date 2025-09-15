import json
import os
import logging
from typing import Any, Optional, List

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
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
        
    def add_recent_directory(self, path: str):
        """添加最近使用的目录"""
        try:
            recent_dirs = self.get_setting('recent_directories', [])
            
            # 移除已存在的路径
            if path in recent_dirs:
                recent_dirs.remove(path)
                
            # 添加到开头
            recent_dirs.insert(0, path)
            
            # 限制数量
            recent_dirs = recent_dirs[:10]
            
            self.set_setting('recent_directories', recent_dirs)
            self.set_setting('last_directory', path)
            self.save_config()
            
        except Exception as e:
            self.logger.error(f"Error adding recent directory: {str(e)}") 