from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class FileItem:
    """文件项数据类"""
    name: str
    path: str
    is_directory: bool = True
    size: Optional[int] = None
    file_count: Optional[int] = 0
    status: str = "未计算"
    checked: bool = False

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'name': self.name,
            'path': self.path,
            'is_directory': self.is_directory,
            'size': self.size,
            'file_count': self.file_count,
            'status': self.status,
            'checked': self.checked
        }

    @staticmethod
    def from_dict(data: dict) -> 'FileItem':
        """从字典创建实例"""
        return FileItem(**data)

    def format_size(self) -> str:
        """格式化大小显示"""
        if self.size is None:
            return "未计算"
            
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(self.size)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
            
        return f"{size:.2f} {units[unit_index]}" 