from datetime import datetime
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt5.QtGui import QColor, QFont, QIcon
import pandas as pd
import logging
from typing import List, Any
from models.file_item import FileItem
from utils.path_utils import get_resource_path
from utils.size_formatter import format_bytes
from utils.table_status import get_status_style

class FileTableModel(QAbstractTableModel):
    """文件表格数据模型"""
    
    # 列定义
    COLUMNS = ['选择', '名称', '创建时间', '大小', '文件数', '状态']
    
    def __init__(self):
        super().__init__()
        self._data: List[FileItem] = []
        self.logger = logging.getLogger(__name__)
        self._folder_icon = QIcon(str(get_resource_path("resources/icons/folder.png")))

    def rowCount(self, parent=None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(self._data)

    def columnCount(self, parent=None) -> int:
        if parent is not None and parent.isValid():
            return 0
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
                return item.format_created_at()
            elif col == 3:
                return item.format_size()
            elif col == 4:
                return str(item.file_count) if item.file_count is not None else "未计算"
            elif col == 5:
                return item.status
                
        elif role == Qt.CheckStateRole and col == 0:
            return Qt.Checked if item.checked else Qt.Unchecked

        elif role == Qt.DecorationRole and col == 1:
            return self._folder_icon if item.is_directory else None
            
        elif role == Qt.TextAlignmentRole:
            if col in [3, 4]:  # 大小和文件数列右对齐
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter
            
        elif role == Qt.BackgroundRole:
            if col == 5:
                return QColor(get_status_style(item.status).background)

        elif role == Qt.ForegroundRole:
            if col == 5:
                return QColor(get_status_style(item.status).foreground)

        elif role == Qt.FontRole:
            if col == 5:
                font = QFont()
                font.setBold(True)
                return font

        elif role == Qt.ToolTipRole:
            if col == 1:
                return item.path
            if col == 2:
                return item.format_created_at()
            if col == 3:
                return item.format_size()
            if col == 4:
                return str(item.file_count) if item.file_count is not None else "未计算"
            if col == 5:
                return item.status
                
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return ""
            return self.COLUMNS[section]
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
            
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == 0:
            flags |= Qt.ItemIsUserCheckable
            
        return flags

    def sort(self, column, order=Qt.AscendingOrder):
        """按列升序或降序排序。"""
        reverse = order == Qt.DescendingOrder

        def sort_key(item: FileItem):
            if column == 0:
                return int(item.checked)
            if column == 1:
                return item.name.lower()
            if column == 2:
                return item.format_created_at()
            if column == 3:
                return -1 if item.size is None else item.size
            if column == 4:
                return -1 if item.file_count is None else item.file_count
            if column == 5:
                return item.status
            return item.name.lower()

        self.layoutAboutToBeChanged.emit()
        self._data.sort(key=sort_key, reverse=reverse)
        self.layoutChanged.emit()

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False
            
        if role == Qt.CheckStateRole and index.column() == 0:
            self._data[index.row()].checked = bool(value == Qt.Checked)
            self.dataChanged.emit(index, index, [role])
            return True
            
        return False

    def toggle_checked(self, row: int) -> bool:
        """Toggle the checked state for a single row."""
        if row < 0 or row >= len(self._data):
            return False

        item = self._data[row]
        item.checked = not item.checked
        index = self.index(row, 0)
        self.dataChanged.emit(index, index, [Qt.CheckStateRole])
        return True

    def set_all_checked(self, checked: bool) -> bool:
        """批量更新所有项目的勾选状态，并发出最小化模型通知。"""
        changed_rows = [row for row, item in enumerate(self._data) if item.checked != checked]
        if not changed_rows:
            return False

        for row in changed_rows:
            self._data[row].checked = checked

        top_left = self.index(changed_rows[0], 0)
        bottom_right = self.index(changed_rows[-1], 0)
        self.dataChanged.emit(top_left, bottom_right, [Qt.CheckStateRole])
        return True

    def clear(self):
        """清空数据"""
        self.beginResetModel()
        self._data.clear()
        self.endResetModel()

    def add_item(self, item: FileItem):
        """添加项目"""
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append(item)
        self.endInsertRows()

    def notify_item_updated(self, item: FileItem):
        """通知视图指定项目的显示内容已更新。"""
        try:
            row = self._data.index(item)
        except ValueError:
            return

        left = self.index(row, 0)
        right = self.index(row, self.columnCount() - 1)
        self.dataChanged.emit(
            left,
            right,
            [Qt.DisplayRole, Qt.ToolTipRole, Qt.ForegroundRole, Qt.BackgroundRole, Qt.FontRole],
        )

    def get_item(self, row: int) -> FileItem:
        """获取指定行的项目"""
        return self._data[row]

    def get_checked_items(self) -> List[FileItem]:
        """获取选中的项目"""
        return [item for item in self._data if item.checked]

    def get_checked_count(self) -> int:
        """获取当前勾选项目数量。"""
        return sum(1 for item in self._data if item.checked)

    def get_total_size(self) -> tuple[int, str]:
        """获取总大小"""
        total_size = sum(item.size or 0 for item in self._data if item.size is not None)

        return total_size, format_bytes(total_size, empty_text="0 B")

    def get_total_files(self) -> int:
        """获取总文件数"""
        return sum(item.file_count or 0 for item in self._data if item.file_count is not None)

    def get_checked_total_size(self) -> tuple[int, str]:
        """获取选中项目总大小"""
        total_size = sum(item.size or 0 for item in self._data if item.checked and item.size is not None)

        return total_size, format_bytes(total_size, empty_text="0 B")

    def get_checked_total_files(self) -> int:
        """获取选中项目总文件数"""
        return sum(item.file_count or 0 for item in self._data if item.checked and item.file_count is not None)

    @staticmethod
    def _parse_excel_datetime(value: str):
        if not value:
            return None

        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        return None

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
                    '创建时间': item.format_created_at(),
                    '创建时间原值': self._parse_excel_datetime(item.created_at),
                    '大小': item.format_size(),
                    '大小(字节)': item.size,
                    '文件数': item.file_count or 0,
                    '状态': item.status
                })
            
            # 创建DataFrame并导出
            df = pd.DataFrame(data)
            df.to_excel(filepath, index=False, engine='openpyxl')
            
        except Exception as e:
            self.logger.error(f"Error exporting to Excel: {str(e)}")
            raise
