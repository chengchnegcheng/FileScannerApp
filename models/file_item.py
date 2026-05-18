from dataclasses import dataclass
from typing import Optional

from utils.size_formatter import format_bytes

@dataclass
class FileItem:
    """文件项数据类"""
    name: str
    path: str
    is_directory: bool = True
    created_at: Optional[str] = None
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
        return format_bytes(self.size)

    def format_created_at(self) -> str:
        """格式化创建时间显示"""
        return self.created_at or "未获取"
