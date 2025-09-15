import sys
import os

# 获取项目根目录并添加到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtCore import Qt, QAbstractTableModel
from PyQt5.QtGui import QColor
import pandas as pd
import logging
from typing import List, Any
from models.file_item import FileItem

class FileTableModel(QAbstractTableModel):
    """文件表格数据模型"""
    
    # 列定义
    COLUMNS = ['选择', '名称', '大小', '文件数', '状态']
    
    def __init__(self):
        super().__init__()
        self._data: List[FileItem] = []
        self._cache = {}  # 缓存计算结果
        self.logger = logging.getLogger(__name__)

    def rowCount(self, parent=None) -> int:
        return len(self._data)

    def columnCount(self, parent=None) -> int:
        return len(self.COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
            
        item = self._data[index.row()]
        col = index.column()
        
        if role == Qt.DisplayRole:
            if col == 0:
                return None  # 复选框列不显示文本
            elif col == 1:
                return item.name
            elif col == 2:
                return item.format_size()
            elif col == 3:
                return str(item.file_count) if item.file_count is not None else "未计算"
            elif col == 4:
                return item.status
                
        elif role == Qt.CheckStateRole and col == 0:
            return Qt.Checked if item.checked else Qt.Unchecked
            
        elif role == Qt.TextAlignmentRole:
            if col in [2, 3]:  # 大小和文件数列右对齐
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter
            
        elif role == Qt.BackgroundRole:
            if item.status == "计算错误":
                return QColor("#fee2e2")  # 浅红色
            elif item.status == "已计算":
                return QColor("#dcfce7")  # 浅绿色
                
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.COLUMNS[section]
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
            
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == 0:
            flags |= Qt.ItemIsUserCheckable
            
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False
            
        if role == Qt.CheckStateRole and index.column() == 0:
            self._data[index.row()].checked = bool(value == Qt.Checked)
            self.dataChanged.emit(index, index, [role])
            return True
            
        return False

    def clear(self):
        """清空数据"""
        self.beginResetModel()
        self._data.clear()
        self._cache.clear()
        self.endResetModel()

    def add_item(self, item: FileItem):
        """添加项目"""
        self.beginInsertRows(self.index(0, 0), len(self._data), len(self._data))
        self._data.append(item)
        self.endInsertRows()

    def get_item(self, row: int) -> FileItem:
        """获取指定行的项目"""
        return self._data[row]

    def get_checked_items(self) -> List[FileItem]:
        """获取选中的项目"""
        return [item for item in self._data if item.checked]

    def get_total_size(self) -> tuple[int, str]:
        """获取总大小"""
        total_size = sum(item.size or 0 for item in self._data if item.size is not None)
        
        # 格式化大小
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(total_size)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
            
        return total_size, f"{size:.2f} {units[unit_index]}"

    def get_total_files(self) -> int:
        """获取总文件数"""
        return sum(item.file_count or 0 for item in self._data if item.file_count is not None)

    def export_to_excel(self, filepath: str, items: List[FileItem] = None):
        """导出到Excel"""
        try:
            # 使用指定项目或所有项目
            items = items or self._data
            
            # 准备数据
            data = []
            for item in items:
                data.append({
                    '名称': item.name,
                    '路径': item.path,
                    '大小': item.format_size(),
                    '文件数': item.file_count or 0,
                    '状态': item.status
                })
            
            # 创建DataFrame并导出
            df = pd.DataFrame(data)
            df.to_excel(filepath, index=False, engine='openpyxl')
            
        except Exception as e:
            self.logger.error(f"Error exporting to Excel: {str(e)}")
            raise 

    def update_system_resources(self, cpu_usage, memory_usage):
        # 假设 self.main_window 是对 views.main_window 的引用
        if self.main_window.cpu_label:  # 检查 cpu_label 是否存在
            self.main_window.cpu_label.setText(f"CPU 使用率: {cpu_usage}%")
        else:
            self.logger.error("CPU 标签未初始化")

        if self.main_window.memory_label:  # 检查 memory_label 是否存在
            self.main_window.memory_label.setText(f"内存使用率: {memory_usage}%")
        else:
            self.logger.error("内存标签未初始化") 