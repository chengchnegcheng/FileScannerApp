from __future__ import annotations
import sys
import os
import json
import logging
import traceback
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Callable
from pathlib import Path
import psutil

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QTableView, 
    QFileDialog, QProgressBar, QStatusBar, QHBoxLayout, QMessageBox, 
    QLabel, QMenu, QLineEdit, QListWidget, QDialog, QShortcut, 
    QCheckBox, QApplication, QFrame, QStyle, QSizePolicy, QHeaderView,
    QStyledItemDelegate, QStyleOptionViewItem
)
from PyQt5.QtCore import (
    QThread, pyqtSignal, Qt, QDir, QTimer, QUrl, QItemSelectionModel, 
    QSize, QPoint, QSignalBlocker
)
from PyQt5.QtGui import QIcon, QKeySequence, QColor, QCursor

from services.file_scanner import FileScanner
from utils.config_manager import ConfigManager
from utils.logger import LogManager
from utils.path_utils import get_app_data_dir, normalize_directory_path
from models.file_item import FileItem
from viewmodels.main_viewmodel import FileTableModel
from workers.backup_worker import BackupWorker
from workers.calculate_worker import CalculateWorker
from workers.scan_worker import ScanWorker
from views.backup_dialog import BackupDialog
from utils.path_utils import get_resource_path as resolve_resource_path
from utils.ui_state import build_action_state
from utils.ui_layout import get_minimal_workflow_layout
from utils.fluent_theme import get_fluent_theme
from utils.size_formatter import format_bytes
from utils.backup_history import create_backup_history_entry

# 应用程序常量
APP_NAME = "文件夹大小扫描器"
APP_VERSION = "1.0.0"
APP_ORGANIZATION = "FileScanner"
APP_DOMAIN = "filescanner.local"

# UI常量
UI_UPDATE_INTERVAL = 100  # ms
AUTOSAVE_INTERVAL = 300000  # 5分钟
MIN_WINDOW_SIZE = QSize(1120, 760)
DEFAULT_BUTTON_SIZE = QSize(112, 36)
TOOLBAR_HEIGHT = 96
STATS_PANEL_HEIGHT = 64
BOTTOM_PANEL_HEIGHT = 44
TABLE_MIN_READABLE_WIDTHS = {
    2: 168,
    3: 140,
    4: 96,
    5: 88,
}
SELECT_ALL_HEADER_LEFT_BIAS = 3

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    return str(resolve_resource_path(relative_path))


class SelectAllCheckBox(QCheckBox):
    """为全选控件提供更符合直觉的三态切换行为。"""

    def nextCheckState(self) -> None:
        if self.checkState() == Qt.PartiallyChecked:
            self.setCheckState(Qt.Checked)
            return

        super().nextCheckState()


class NoFocusItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        option = QStyleOptionViewItem(option)
        option.state &= ~QStyle.State_HasFocus
        super().paint(painter, option, index)

class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self, config: ConfigManager) -> None:
        """初始化主窗口"""
        super().__init__()
        self._init_services(config)
        self._init_components()
        self._init_timers()
        self._setup_ui()
        self._setup_styles()
        self._setup_shortcuts()
        self._start_services()
        
        # 启用拖放
        self.setAcceptDrops(True)

    def _init_services(self, config: ConfigManager) -> None:
        """初始化服务"""
        try:
            # 基础服务
            self.config = config
            self.logger = logging.getLogger(__name__)
            self.log_manager = LogManager()
            self.scanner = FileScanner(config)
            
            # 错误处理器
            from utils.error_handler import ErrorHandler
            self.error_handler = ErrorHandler(self.logger)
            
            # 工作线程管理
            self._workers: List[QThread] = []
            self._current_worker: Optional[QThread] = None
            self.current_directory: Optional[str] = None
            
            # 性能监控
            self._performance_monitor = {
                'last_update': time.time(),
                'update_interval': 1.0,
                'speed_samples': [],
                'max_samples': 5
            }
            
        except Exception as e:
            self.logger.error(f"Error initializing services: {str(e)}")
            raise

    def _init_components(self) -> None:
        """初始化UI组件"""
        try:
            # 数据模型
            self.table_model = FileTableModel()
            
            # 按钮组件
            self.select_btn = None
            self.start_btn = None
            self.stop_btn = None
            self.calculate_btn = None
            self.export_btn = None
            self.backup_btn = None
            self._secondary_actions_container = None
            self._table_container = None
            
            # 表格和进度组件
            self.table_view = None
            self.progress_bar = None
            self.status_bar = None
            
            # 统计标签
            self.folder_count_label = None
            self.file_count_label = None
            self.size_label = None
            self.selection_label = None
            self.selected_file_count_label = None
            self.selected_size_label = None
            self.speed_label = None
            self.runtime_state_label = None
            self.memory_label = None
            self.cpu_label = None
            self.current_path_label = None
            self.page_title_label = None
            self.page_subtitle_label = None
            self.table_title_label = None
            self.table_hint_label = None
            self.scan_card_title_label = None
            
            # 其他控件
            self.select_all_checkbox = None
            self.empty_state_label = None
            self._backup_dialog = None
            
            # 自动保存设置
            self._auto_save_dir = str(get_app_data_dir() / 'auto_saves')
            self._auto_save_max_files = 5
            self._is_busy = False
            self._cancel_requested = False
            self._backup_failed = False
            self._last_backup_dest_path = None
            self._last_backup_source_names: List[str] = []
            self._current_operation = "idle"
            self._status_message = "就绪"
            self._layout_config = get_minimal_workflow_layout()
            self._theme = get_fluent_theme()
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {str(e)}")
            raise

    def _init_timers(self) -> None:
        """初始化定时器"""
        try:
            # UI更新定时器
            self._update_timer = QTimer(self)
            self._update_timer.setInterval(UI_UPDATE_INTERVAL)
            self._update_timer.timeout.connect(self._update_ui)
            
            # 自动保存定时器
            self._autosave_timer = QTimer(self)
            self._autosave_timer.setInterval(AUTOSAVE_INTERVAL)
            self._autosave_timer.timeout.connect(self._auto_save_results)
            
        except Exception as e:
            self.logger.error(f"Error initializing timers: {str(e)}")
            raise

    def _setup_ui(self) -> None:
        """设置UI"""
        try:
            # 设置窗口基本属性
            self.setWindowTitle(APP_NAME)
            self.setMinimumSize(MIN_WINDOW_SIZE)
            
            # 设置窗口图标
            icon_path = get_resource_path("resources/icons/app.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            
            # 设置窗口大小为屏幕大小的75%并居中
            screen = QApplication.primaryScreen().size()
            window_width = min(int(screen.width() * 0.75), 1280)  # 最大宽度1280
            window_height = min(int(screen.height() * 0.75), 800)  # 最大高度800
            self.resize(window_width, window_height)
            self._center_window()
            
            # 创建中心部件和主布局
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QVBoxLayout(central_widget)
            main_layout.setSpacing(14)
            main_layout.setContentsMargins(18, 16, 18, 16)
            
            # 添加主要组件
            main_layout.addWidget(self._create_toolbar())
            main_layout.addWidget(self._create_secondary_actions_bar())
            main_layout.addWidget(self._create_table_view(), 1)
            main_layout.addWidget(self._create_stats_panel())
            main_layout.addWidget(self._create_bottom_panel())
            
            # 设置状态栏提示
            self.status_bar.showMessage(self._status_message)
            self._create_menu_bar()
            
        except Exception as e:
            self.logger.error(f"Error setting up UI: {str(e)}")
            raise

    def _create_page_header(self) -> QWidget:
        """创建页面头部。"""
        container = QWidget()
        container.setVisible(False)
        return container

    def _setup_styles(self):
        """设置样式"""
        try:
            # 加载QSS样式文件
            style_file = get_resource_path("resources/styles/main.qss")
            if os.path.exists(style_file):
                with open(style_file, 'r', encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
            else:
                self.logger.warning(f"Style file not found: {style_file}")
            
        except Exception as e:
            self.logger.error(f"Error loading styles: {str(e)}")

    def _setup_shortcuts(self):
        """设置快捷键"""
        try:
            # 文件操作快捷键
            QShortcut(QKeySequence("Ctrl+O"), self, self.select_directory)
            QShortcut(QKeySequence("Ctrl+S"), self, self.start_scan)
            QShortcut(QKeySequence("Esc"), self, self.stop_scan)
            
            # 功能快捷键
            QShortcut(QKeySequence("F5"), self, self.calculate_selected)
            QShortcut(QKeySequence("Ctrl+Shift+C"), self, self.calculate_selected)
            QShortcut(QKeySequence("Ctrl+C"), self, self._copy_checked_paths)
            QShortcut(QKeySequence("Ctrl+E"), self, self.export_to_excel)
            QShortcut(QKeySequence("Ctrl+B"), self, self.backup_directory)
            
            # 其他快捷键
            QShortcut(QKeySequence("Ctrl+A"), self, self._select_all_items)
            QShortcut(QKeySequence("Ctrl+D"), self, self._clear_selected_items)
            
        except Exception as e:
            self.logger.error(f"Error setting up shortcuts: {str(e)}")

    def _start_services(self):
        """启动服务"""
        try:
            # 启动定时器
            self._update_timer.start()
            self._autosave_timer.start()
            
            # 设置状态栏初始消息
            self._set_status_message("就绪")
            
        except Exception as e:
            self.logger.error(f"Error starting services: {str(e)}")
            raise

    def _update_ui(self) -> None:
        """更新UI状态"""
        try:
            # 限制更新频率
            current_time = time.time()
            if not hasattr(self, '_last_ui_update'):
                self._last_ui_update = 0
            if current_time - self._last_ui_update < 0.1:
                return
                
            # 更新性能统计
            self._monitor_system_resources()
            
            # 更新按钮状态
            self._update_button_states()
            
            # 更新状态栏
            self._update_status_bar()
            
            self._last_ui_update = current_time
            
        except Exception as e:
            self.logger.error(f"Error updating UI: {str(e)}")

    def _monitor_system_resources(self) -> None:
        """监控系统资源使用情况"""
        try:
            # 获取内存使用情况
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                self.logger.warning(f"High memory usage: {memory.percent}%")
                
            # 获取CPU使用情况
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if cpu_percent > 90:
                self.logger.warning(f"High CPU usage: {cpu_percent}%")
                
            # 更新标签
            if self.memory_label is not None:
                self.memory_label.setText(f"内存: {memory.percent}%")
            if self.cpu_label is not None:
                self.cpu_label.setText(f"CPU: {cpu_percent}%")
            
        except Exception as e:
            self.logger.error(f"Error monitoring system resources: {str(e)}")

    def _auto_save_results(self) -> None:
        """自动保存扫描结果"""
        try:
            if not self.table_model.rowCount():
                return
                
            # 创建自动保存目录
            if not os.path.exists(self._auto_save_dir):
                os.makedirs(self._auto_save_dir)
                
            # 生成保存文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(
                self._auto_save_dir,
                f"auto_save_{timestamp}.xlsx"
            )
            
            # 导出数据
            self.table_model.export_to_excel(save_path)
            
            # 清理旧的自动保存文件
            self._cleanup_auto_saves()
            
        except Exception as e:
            self.logger.error(f"Error auto saving results: {str(e)}")

    def _cleanup_auto_saves(self) -> None:
        """清理旧的自动保存文件"""
        try:
            files = sorted([
                f for f in os.listdir(self._auto_save_dir)
                if f.startswith("auto_save_") and f.endswith(".xlsx")
            ], key=lambda x: os.path.getctime(
                os.path.join(self._auto_save_dir, x)
            ))
            
            # 保留最新的5个文件
            while len(files) > self._auto_save_max_files:
                os.remove(os.path.join(self._auto_save_dir, files.pop(0)))
                
        except Exception as e:
            self.logger.error(f"Error cleaning up auto saves: {str(e)}")

    def _create_toolbar(self) -> QWidget:
        """创建统计与操作区域。"""
        try:
            self._toolbar_container = container = QFrame()
            container.setObjectName("toolbarContainer")

            layout = QHBoxLayout(container)
            layout.setSpacing(10)
            layout.setContentsMargins(12, 10, 12, 10)

            path_group = QFrame()
            path_group.setObjectName("pathGroup")
            path_layout = QVBoxLayout(path_group)
            path_layout.setSpacing(2)
            path_layout.setContentsMargins(10, 6, 10, 6)

            path_title = QLabel("\u8def\u5f84")
            path_title.setObjectName("groupCaptionLabel")
            self.current_path_label = QLabel("\u672a\u9009\u62e9\u76ee\u5f55")
            self.current_path_label.setObjectName("currentPathLabel")
            self.current_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            path_layout.addWidget(path_title)
            path_layout.addWidget(self.current_path_label)

            command_group = QFrame()
            command_group.setObjectName("commandGroup")
            command_layout = QHBoxLayout(command_group)
            command_layout.setSpacing(8)
            command_layout.setContentsMargins(8, 8, 8, 8)

            self.select_btn = self._create_button(
                "\u9009\u62e9\u76ee\u5f55",
                "folder",
                self.select_directory,
                "\u9009\u62e9\u8981\u626b\u63cf\u7684\u76ee\u5f55\uff08\u652f\u6301\u6700\u8fd1\u8bb0\u5f55\uff09 (Ctrl+O)",
            )
            self.start_btn = self._create_button(
                "\u5f00\u59cb\u626b\u63cf",
                "play",
                self.start_scan,
                "\u626b\u63cf\u5f53\u524d\u76ee\u5f55\u4e0b\u7684\u4e00\u7ea7\u5b50\u6587\u4ef6\u5939 (Ctrl+S)",
            )
            self.stop_btn = self._create_button(
                "\u505c\u6b62",
                "stop",
                self.stop_scan,
                "\u505c\u6b62\u6b63\u5728\u8fdb\u884c\u7684\u626b\u63cf\u3001\u8ba1\u7b97\u6216\u5907\u4efd (Esc)",
            )

            self.select_btn.setProperty("buttonRole", "secondary")
            self.start_btn.setProperty("buttonRole", "primary")
            self.stop_btn.setProperty("buttonRole", "danger")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

            for btn in [self.select_btn, self.start_btn, self.stop_btn]:
                command_layout.addWidget(btn)

            layout.addWidget(path_group, 1)
            layout.addWidget(command_group, 0)
            return container
        except Exception as e:
            self.logger.error(f"Error creating toolbar: {str(e)}")
            raise

    def _create_secondary_actions_bar(self) -> QWidget:
        """创建表格上方的二级操作行。"""
        try:
            self._secondary_actions_container = container = QFrame()
            container.setObjectName("secondaryActionsContainer")

            layout = QHBoxLayout(container)
            layout.setSpacing(10)
            layout.setContentsMargins(12, 8, 12, 8)

            action_group = QFrame()
            action_group.setObjectName("commandGroup")
            action_layout = QHBoxLayout(action_group)
            action_layout.setSpacing(8)
            action_layout.setContentsMargins(8, 8, 8, 8)

            self.calculate_btn = self._create_button(
                "计算",
                "calculate",
                self.calculate_selected,
                "\u8ba1\u7b97\u9009\u4e2d\u6587\u4ef6\u5939\u7684\u5927\u5c0f\u4e0e\u6587\u4ef6\u6570 (F5)",
            )
            self.export_btn = self._create_button(
                "导出",
                "export",
                self.export_to_excel,
                "\u5c06\u9009\u4e2d\u7ed3\u679c\u5bfc\u51fa\u4e3a Excel (Ctrl+E)",
            )
            self.backup_btn = self._create_button(
                "备份",
                "backup",
                self.backup_directory,
                "\u5c06\u9009\u4e2d\u6587\u4ef6\u5939\u5907\u4efd\u5230\u76ee\u6807\u4f4d\u7f6e (Ctrl+B)",
            )

            secondary_action_buttons = {
                "calculate": self.calculate_btn,
                "export": self.export_btn,
                "backup": self.backup_btn,
            }
            for action_name in self._layout_config.secondary_actions:
                if action_name == "select_all":
                    continue

                button = secondary_action_buttons[action_name]
                button.setProperty("buttonRole", "ghost")
                button.setEnabled(False)
                action_layout.addWidget(button)

            action_layout.addStretch(1)

            self.select_all_checkbox = SelectAllCheckBox("")
            self.select_all_checkbox.stateChanged.connect(self._on_select_all_changed)
            self.select_all_checkbox.setEnabled(False)
            self.select_all_checkbox.setToolTip("\u5f53\u524d\u6ca1\u6709\u53ef\u9009\u62e9\u7684\u9879\u76ee")

            layout.addWidget(action_group, 1)
            return container
        except Exception as e:
            self.logger.error(f"Error creating secondary actions bar: {str(e)}")
            raise

    def _create_stats_panel(self) -> QWidget:
        """创建结果表格视图。"""
        try:
            container = QFrame()
            container.setObjectName("statsPanel")

            layout = QHBoxLayout(container)
            layout.setSpacing(10)
            layout.setContentsMargins(12, 8, 12, 8)

            stats_group = QFrame()
            stats_group.setObjectName("commandGroup")
            stats_layout = QHBoxLayout(stats_group)
            stats_layout.setSpacing(8)
            stats_layout.setContentsMargins(8, 8, 8, 8)

            self.folder_count_label = QLabel("\u6587\u4ef6\u5939: 0")
            self.selection_label = QLabel("\u5df2\u9009: 0")
            self.file_count_label = QLabel("\u6587\u4ef6\u6570: \u672a\u8ba1\u7b97")
            self.size_label = QLabel("\u603b\u5927\u5c0f: \u672a\u8ba1\u7b97")
            self.selected_file_count_label = QLabel("\u5df2\u9009\u6587\u4ef6\u6570: \u672a\u8ba1\u7b97")
            self.selected_size_label = QLabel("\u5df2\u9009\u603b\u5927\u5c0f: \u672a\u8ba1\u7b97")

            for label in [
                self.folder_count_label,
                self.selection_label,
                self.file_count_label,
                self.size_label,
                self.selected_file_count_label,
                self.selected_size_label,
            ]:
                label.setObjectName("statsLabel")
                stats_layout.addWidget(label)

            runtime_group = QFrame()
            runtime_group.setObjectName("runtimeGroup")
            runtime_layout = QVBoxLayout(runtime_group)
            runtime_layout.setSpacing(6)
            runtime_layout.setContentsMargins(10, 8, 10, 8)

            self.runtime_state_label = QLabel("\u672a\u5f00\u59cb")
            self.runtime_state_label.setObjectName("runtimeStateLabel")
            self.speed_label = QLabel("\u7b49\u5f85\u64cd\u4f5c")
            self.speed_label.setObjectName("runtimeMetaLabel")

            self.progress_bar = QProgressBar()
            self.progress_bar.setObjectName("progressBar")
            self.progress_bar.setFixedHeight(4)
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setVisible(False)

            runtime_layout.addWidget(self.runtime_state_label)
            runtime_layout.addWidget(self.speed_label)
            runtime_layout.addWidget(self.progress_bar)

            layout.addWidget(stats_group, 1)
            layout.addWidget(runtime_group, 0)
            return container
        except Exception as e:
            self.logger.error(f"Error creating stats panel: {str(e)}")
            raise

    def _create_table_view(self) -> QWidget:
        """创建底部状态区域。"""
        try:
            self._table_container = container = QFrame()
            container.setObjectName("tableContainer")

            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            self.table_view = QTableView()
            self.table_view.setModel(self.table_model)
            self.table_view.setObjectName("resultsTable")
            self.table_view.setSelectionBehavior(QTableView.SelectRows)
            self.table_view.setSelectionMode(QTableView.SingleSelection)
            self.table_view.setAlternatingRowColors(True)
            self.table_view.setSortingEnabled(True)
            self.table_view.setShowGrid(False)
            self.table_view.verticalHeader().setVisible(False)
            self.table_view.verticalHeader().setDefaultSectionSize(40)
            self.table_view.setWordWrap(False)
            self.table_view.setIconSize(QSize(18, 18))
            self.table_view.setItemDelegate(NoFocusItemDelegate(self.table_view))

            header = self.table_view.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.Interactive)
            header.setSectionResizeMode(3, QHeaderView.Interactive)
            header.setSectionResizeMode(4, QHeaderView.Interactive)
            header.setSectionResizeMode(5, QHeaderView.Interactive)
            header.setMinimumSectionSize(60)

            self._attach_select_all_checkbox_to_header(header)

            self.table_view.setColumnWidth(0, 36)
            self.table_view.setColumnWidth(1, 420)
            self.table_view.setColumnWidth(2, 180)
            self.table_view.setColumnWidth(3, 180)
            self.table_view.setColumnWidth(4, 110)
            self.table_view.setColumnWidth(5, 90)
            self._enforce_table_column_widths()

            self.table_model.dataChanged.connect(self._on_data_changed)
            self.table_view.setSortingEnabled(True)
            self.table_model.rowsInserted.connect(lambda *_: self._on_model_rows_changed())
            self.table_model.modelReset.connect(lambda: self._on_model_rows_changed())
            self.table_view.clicked.connect(self._on_table_clicked)
            self.table_view.doubleClicked.connect(self._on_item_double_clicked)
            self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
            self.table_view.customContextMenuRequested.connect(self._show_context_menu)

            self.empty_state_label = QLabel(
                "\u70b9\u51fb\u300c\u9009\u62e9\u76ee\u5f55\u300d\u6216\u5c06\u6587\u4ef6\u5939\u62d6\u653e\u5230\u6b64\u5904\n"
                "\u9009\u62e9\u540e\u4f1a\u81ea\u52a8\u626b\u63cf\u4e00\u7ea7\u5b50\u6587\u4ef6\u5939\uff1b\u52fe\u9009\u540e\u53ef\u8ba1\u7b97\u3001\u5bfc\u51fa\u6216\u5907\u4efd"
            )
            self.empty_state_label.setObjectName("emptyStateLabel")
            self.empty_state_label.setAlignment(Qt.AlignCenter)

            layout.addWidget(self.empty_state_label)
            layout.addWidget(self.table_view)
            self._refresh_empty_state()
            return container
        except Exception as e:
            self.logger.error(f"Error creating table view: {str(e)}")
            raise

    def _attach_select_all_checkbox_to_header(self, header: QHeaderView) -> None:
        if self.select_all_checkbox is None:
            return

        self.select_all_checkbox.setParent(header.viewport())
        self.select_all_checkbox.raise_()
        self.select_all_checkbox.show()

        header.sectionResized.connect(self._reposition_select_all_checkbox)
        header.sectionMoved.connect(self._reposition_select_all_checkbox)
        header.geometriesChanged.connect(self._reposition_select_all_checkbox)
        self.table_view.horizontalScrollBar().valueChanged.connect(self._reposition_select_all_checkbox)

        self._reposition_select_all_checkbox()
        QTimer.singleShot(0, self._reposition_select_all_checkbox)

    def _reposition_select_all_checkbox(self, *_args) -> None:
        if self.select_all_checkbox is None or self.table_view is None:
            return

        header = self.table_view.horizontalHeader()
        if header is None or header.count() == 0:
            return

        indicator_size = self.select_all_checkbox.sizeHint()
        section_width = header.sectionSize(0)
        section_height = header.height()
        section_left = header.sectionViewportPosition(0)

        x = section_left + max(0, ((section_width - indicator_size.width()) // 2) - SELECT_ALL_HEADER_LEFT_BIAS)
        y = max(0, (section_height - indicator_size.height()) // 2)

        self.select_all_checkbox.setGeometry(x, y, indicator_size.width(), indicator_size.height())
        self.select_all_checkbox.raise_()

    def _build_select_all_tooltip(self, checked_count: int, total_count: int) -> str:
        if total_count == 0:
            return "\u5f53\u524d\u6ca1\u6709\u53ef\u9009\u62e9\u7684\u9879\u76ee"

        if checked_count == total_count:
            return f"\u53d6\u6d88\u5168\u9009\uff08{checked_count}/{total_count}\uff09"

        return f"\u5168\u9009\uff08{checked_count}/{total_count}\uff09"

    def _enforce_table_column_widths(self) -> None:
        """保持关键列的最小可读宽度。"""
        if not self.table_view:
            return

        for column, min_width in TABLE_MIN_READABLE_WIDTHS.items():
            if self.table_view.columnWidth(column) < min_width:
                self.table_view.setColumnWidth(column, min_width)

    def _create_bottom_panel(self) -> QWidget:
        """创建底部面板"""
        try:
            container = QFrame()
            container.setObjectName("bottomPanel")
            container.setFixedHeight(34)
            
            layout = QVBoxLayout(container)
            layout.setContentsMargins(10, 2, 10, 2)
            layout.setSpacing(0)
            
            # 创建状态栏
            self.status_bar = QStatusBar()
            self.status_bar.setObjectName("statusBar")
            self.status_bar.setFixedHeight(28)
            layout.addWidget(self.status_bar)
            
            return container
            
        except Exception as e:
            self.logger.error(f"Error creating bottom panel: {str(e)}")
            raise

    def _create_button(
        self, 
        text: str, 
        icon_name: str, 
        slot: Callable, 
        tooltip: Optional[str] = None
    ) -> QPushButton:
        """创建统一样式的按钮"""
        try:
            button = QPushButton(text)
            button.setObjectName("toolbarButton")
            
            # 设置图标
            button.setIcon(QIcon())
            
            # 设置大小和样式
            button.setMinimumSize(DEFAULT_BUTTON_SIZE)
            button.setCursor(Qt.PointingHandCursor)
            
            if tooltip:
                button.setToolTip(tooltip)
            
            button.clicked.connect(slot)
            return button
            
        except Exception as e:
            self.logger.error(f"Error creating button: {str(e)}")
            return QPushButton(text)  # 返回一个基本按钮作为后备

    def _get_button_icon(self, icon_name: str) -> QIcon:
        """获取统一风格的按钮图标"""
        standard_icons = {
            "folder": QStyle.SP_DirOpenIcon,
            "play": QStyle.SP_MediaPlay,
            "stop": QStyle.SP_BrowserStop,
            "calculate": QStyle.SP_DialogApplyButton,
            "export": QStyle.SP_DialogSaveButton,
            "backup": QStyle.SP_DriveHDIcon,
        }

        if icon_name in standard_icons:
            return self.style().standardIcon(standard_icons[icon_name])

        icon_path = get_resource_path(f"resources/icons/{icon_name}.png")
        if os.path.exists(icon_path):
            return QIcon(icon_path)

        return QIcon()

    def _format_speed(self, bytes_per_second: float) -> str:
        """格式化速度显示"""
        try:
            units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
            speed = bytes_per_second
            unit_index = 0
            
            while speed >= 1024 and unit_index < len(units) - 1:
                speed /= 1024
                unit_index += 1
                
            return f"{speed:.1f} {units[unit_index]}"
            
        except Exception as e:
            self.logger.error(f"Error formatting speed: {str(e)}")
            return "0 B/s"

    def _format_bytes(self, size_in_bytes: float) -> str:
        try:
            return format_bytes(size_in_bytes, empty_text="0 B")
        except Exception as e:
            self.logger.error(f"Error formatting bytes: {str(e)}")
            return "0 B"

    def _build_known_backup_progress_state(self, items: List[FileItem]) -> dict[str, int] | None:
        if not items or any(item.size is None for item in items):
            return None

        return {
            "copied_files": 0,
            "copied_bytes": 0,
            "total_files": sum(max(item.file_count or 0, 0) for item in items),
            "total_bytes": sum(max(item.size or 0, 0) for item in items),
        }

    def _build_known_backup_sizes(self, items: List[FileItem]) -> dict[str, int] | None:
        if not items or any(item.size is None for item in items):
            return None

        known_sizes: dict[str, int] = {}
        for item in items:
            known_sizes[os.path.abspath(item.path)] = max(item.size or 0, 0)
        return known_sizes

    def _format_backup_result_summary(self) -> str:
        stats = self.scanner.last_backup_stats
        if stats is None:
            return ""
        return stats.format_summary()

    def _set_status_message(self, message: str) -> None:
        self._status_message = message
        if self.status_bar:
            self.status_bar.showMessage(message)

    def _set_runtime_state(self, state: str, detail: str | None = None) -> None:
        if self.runtime_state_label is not None:
            self.runtime_state_label.setText(state)
        if detail is not None and self.speed_label is not None:
            self.speed_label.setText(detail)

    def _set_operation_state(self, operation: str, busy: bool, message: str) -> None:
        self._current_operation = operation
        self._is_busy = busy
        self._cancel_requested = False if busy else self._cancel_requested
        self._set_status_message(message)
        if busy:
            state_map = {
                "scan": "扫描中",
                "calculate": "计算中",
                "backup": "备份中",
            }
            self._set_runtime_state(state_map.get(operation, "处理中"), "请稍候")
        self._update_button_states()

    def _refresh_empty_state(self) -> None:
        if not self.empty_state_label or not self.table_view:
            return

        has_items = bool(self.table_model.rowCount())
        self.empty_state_label.setVisible(not has_items)
        self.table_view.setVisible(has_items)

    def show_error(self, title: str, message: str, details: str = None):
        """显示错误对话框"""
        try:
            # 使用错误处理器记录错误
            if not self.error_handler.handle_error(title, Exception(message), details):
                # 如果错误太频繁，显示警告
                QMessageBox.warning(
                    self,
                    "警告",
                    "错误发生太频繁，请检查程序状态！"
                )
                return
            
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle(title)
            msg.setText(message)
            
            if details:
                msg.setDetailedText(details)
            
            # 添加复制按钮
            copy_button = msg.addButton("复制详情", QMessageBox.ActionRole)
            msg.addButton(QMessageBox.Ok)
            self._localize_message_box_buttons(msg)
            
            result = msg.exec_()
            
            # 处理复制按钮点击
            if msg.clickedButton() == copy_button and details:
                QApplication.clipboard().setText(details)
                self.status_bar.showMessage("错误详情已复制到剪贴板", 3000)
            
        except Exception as e:
            self.logger.error(f"Error showing error dialog: {str(e)}")

    def _localize_message_box_buttons(self, message_box: QMessageBox) -> None:
        button_text_map = {
            "OK": "确定",
            "&OK": "确定",
            "Show Details...": "显示详情",
            "Hide Details...": "隐藏详情",
            "&Show Details...": "显示详情",
            "&Hide Details...": "隐藏详情",
        }

        def apply_button_labels() -> None:
            for button in message_box.buttons():
                translated = button_text_map.get(button.text())
                if translated:
                    button.setText(translated)

        apply_button_labels()
        for button in message_box.buttons():
            button.clicked.connect(lambda *_: QTimer.singleShot(0, apply_button_labels))

    def select_directory(self):
        """选择目录"""
        try:
            recent_dirs = [path for path in self.config.get_setting('recent_directories', []) if path]
            if recent_dirs:
                self._show_directory_menu()
            else:
                self._browse_directory()
        except Exception as e:
            self.logger.error(f"Error selecting directory: {str(e)}")

    def _show_directory_menu(self):
        """显示最近目录菜单"""
        try:
            menu = QMenu(self)
            recent_dirs = [path for path in self.config.get_setting('recent_directories', []) if path]
            
            for path in recent_dirs:
                action = menu.addAction(path)
                action.triggered.connect(lambda checked, p=path: self._set_selected_directory(p))
                
            menu.addSeparator()
            browse_action = menu.addAction("浏览...")
            browse_action.triggered.connect(self._browse_directory)
            
            # 显示菜单
            anchor = self.select_btn.mapToGlobal(self.select_btn.rect().bottomLeft()) if self.select_btn else QCursor.pos()
            menu.exec_(anchor)
            
        except Exception as e:
            self.logger.error(f"Error showing directory menu: {str(e)}")

    def _browse_directory(self):
        """浏览并选择目录"""
        try:
            # 获取上次的目录
            last_dir = self.config.get_setting('last_directory', os.path.expanduser('~'))
            
            # 打开目录选择对话框
            path = QFileDialog.getExistingDirectory(
                self,
                "选择要扫描的文件夹",
                last_dir,
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            if path:
                self._set_selected_directory(path)
                
        except Exception as e:
            self.logger.error(f"Error browsing directory: {str(e)}")
            self.show_error("选择错误", str(e))

    def _set_selected_directory(self, path: str, auto_scan: bool = True) -> None:
        """设置当前目录，并按需立即开始扫描。"""
        path = normalize_directory_path(path)
        self.current_directory = path
        self.scanner.clear_calculation_cache()
        self._update_current_path_label(path)

        self.table_model.clear()
        self._refresh_empty_state()
        self._update_button_states()
        self._set_status_message("已选择目录，正在准备扫描")

        self.config.add_recent_directory(path)

        if auto_scan:
            self._scan_directory(path)

    def _scan_directory(self, path: str):
        """扫描目录"""
        try:
            path = normalize_directory_path(path)
            if not os.path.exists(path):
                raise FileNotFoundError(f"目录不存在: {path}")

            if self._is_busy:
                self.show_error("操作进行中", "请等待当前任务完成后再开始新的扫描")
                return
            
            # 更新当前目录
            self.current_directory = path
            self.scanner.clear_calculation_cache()
            self._update_current_path_label(path)
            
            # 清空现有数据
            self.table_model.clear()
            self._refresh_empty_state()
            
            # 创建扫描工作线程
            worker = ScanWorker(self.scanner, path)
            worker.file_found.connect(self.table_model.add_item)
            worker.finished.connect(lambda success: self._on_scan_finished(success))
            worker.error.connect(self.show_error)
            
            # 开始扫描
            if not self._start_worker(worker, "scan", f"正在扫描: {path}"):
                return
            
            # 更新UI状态
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat("正在扫描...")
            
        except Exception as e:
            self.logger.error(f"Error scanning directory: {str(e)}")
            self.show_error("扫描错误", str(e))

    def _start_worker(self, worker: QThread, operation: str, message: str) -> bool:
        """启动工作线程"""
        try:
            if self._current_worker and self._current_worker.isRunning():
                self.show_error("操作进行中", "请先停止当前任务，或等待其完成")
                return False

            self.scanner.stopped = False
            self._cancel_requested = False
            
            # 设置新的工作线程
            self._current_worker = worker
            self._workers.append(worker)
            worker.finished.connect(lambda *_: self._cleanup_workers())
            
            # 清理已完成的工作线程
            self._cleanup_workers()
            
            # 更新UI状态
            self._set_operation_state(operation, True, message)
            
            # 启动工作线程
            worker.start()
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting worker: {str(e)}")
            self.show_error("线程错误", f"启动工作线程失败: {str(e)}")
            return False

    def _cleanup_workers(self) -> None:
        """清理已完成的工作线程"""
        try:
            # 移除已完成的线程
            self._workers = [
                worker for worker in self._workers 
                if worker.isRunning()
            ]
        except Exception as e:
            self.logger.error(f"Error cleaning up workers: {str(e)}")

    def _on_scan_finished(self, success: bool):
        """处理扫描完成"""
        try:
            # 停止工作线程
            self._current_worker = None
            self._is_busy = False
            was_cancelled = self.scanner.stopped or self._cancel_requested
            self._cancel_requested = False
            
            # 更新UI状态
            self.progress_bar.setVisible(False)
            self.progress_bar.setRange(0, 100)
            self._update_button_states()
            self._refresh_empty_state()
            
            if success and not was_cancelled:
                # 更新状态栏
                total_items = self.table_model.rowCount()
                status_text = f"扫描完成，已列出 {total_items} 个文件夹，勾选后点击计算查看大小"
                self._set_status_message(status_text)
                self._set_runtime_state("扫描完成", f"已列出 {total_items} 个文件夹")
                
                # 更新表格显示
                self.table_view.resizeColumnsToContents()
                self._enforce_table_column_widths()
                self.table_view.resizeRowsToContents()
                
                # 自动保存结果
                self._auto_save_results()
            else:
                self._set_status_message("扫描已取消")
                self._set_runtime_state("扫描已取消", "未执行计算")
                
        except Exception as e:
            self.logger.error(f"Error handling scan finished: {str(e)}")

    def start_scan(self):
        """开始扫描"""
        try:
            if not self.current_directory:
                self.show_error("扫描错误", "请先选择要扫描的目录")
                return
                
            self._scan_directory(self.current_directory)
            
        except Exception as e:
            self.logger.error(f"Error starting scan: {str(e)}")
            self.show_error("扫描错误", str(e))

    def stop_scan(self):
        """停止当前操作"""
        try:
            if self._backup_dialog and self._backup_dialog._backup_in_progress:
                self._request_stop_backup()
                return

            if not self._is_busy:
                self._set_status_message("当前没有正在运行的任务")
                return

            self._cancel_requested = True
            self.scanner.stop()
            self._set_status_message("正在停止当前任务...")
            self._update_button_states()

        except Exception as e:
            self.logger.error(f"Error stopping operation: {str(e)}")

    def _request_stop_backup(self):
        """停止备份（对话框与主窗口停止按钮统一入口）。"""
        try:
            if self._backup_dialog:
                self._backup_dialog.set_stopping_state()

            self._cancel_requested = True
            self.scanner.stop()

            if self._is_busy:
                self._set_status_message("正在停止备份...")
                self._set_runtime_state("备份中", "正在取消")
                self._update_button_states()
            elif self._backup_dialog and self._backup_dialog._backup_in_progress:
                self._set_status_message("正在停止备份...")

        except Exception as e:
            self.logger.error(f"Error stopping backup: {str(e)}")

    def calculate_selected(self):
        """计算选中项目的大小"""
        try:
            if self._is_busy:
                self.show_error("操作进行中", "请等待当前任务完成后再开始新的计算")
                return

            items = self.table_model.get_checked_items()
            if not items:
                self.show_error("计算错误", "请先选择要计算的文件夹")
                return
                
            # 创建计算工作线程
            worker = CalculateWorker(self.scanner, items)
            worker.progress.connect(self._on_calculate_progress)
            worker.finished.connect(lambda: self._on_calculate_finished())
            worker.error.connect(self.show_error)
            
            # 开始计算
            if not self._start_worker(worker, "calculate", "正在计算文件夹大小..."):
                return
            
            # 更新UI状态
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setFormat("正在计算: %p%")
            
        except Exception as e:
            self.logger.error(f"Error calculating sizes: {str(e)}")
            self.show_error("计算错误", str(e))

    def export_to_excel(self):
        """导出到Excel"""
        try:
            items = self.table_model.get_checked_items()
            if not items:
                self.show_error("导出错误", "请先选择要导出的文件夹")
                return
                
            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出Excel",
                os.path.join(os.path.expanduser("~"), "扫描结果.xlsx"),
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
                
            # 导出数据
            export_path = self.table_model.export_to_excel(file_path, items)
            self._set_status_message(f"已导出到: {export_path}")
            
        except Exception as e:
            self.logger.error(f"Error exporting to Excel: {str(e)}")
            self.show_error("导出错误", str(e))

    def backup_directory(self):
        """备份选中的文件夹"""
        try:
            items = self.table_model.get_checked_items()
            if not items:
                self.show_error("备份错误", "请先选择要备份的文件夹")
                return
                
            # 创建备份对话框
            self._backup_dialog = BackupDialog(self, self.config)
            self._backup_dialog.set_sources_need_calculate(self._has_uncalculated_checked_items())
            self._backup_dialog.backup_started.connect(lambda dest_path: self._start_backup(items, dest_path))
            self._backup_dialog.backup_stop_requested.connect(self._request_stop_backup)
            self._backup_dialog.exec_()
            
        except Exception as e:
            self.logger.error(f"Error backing up directories: {str(e)}")
            self.show_error("备份错误", str(e))

    def _start_backup(self, items: List[FileItem], dest_path: str):
        """开始备份操作"""
        try:
            if self._is_busy:
                if self._backup_dialog:
                    self._backup_dialog.abort_prepare()
                self.show_error("操作进行中", "请等待当前任务完成后再开始新的备份")
                return

            src_paths = [item.path for item in items]
            known_sizes = self._build_known_backup_sizes(items)

            normalized_dest_path = self.scanner.validate_backup_request(
                src_paths,
                dest_path,
            )

            if any(item.size is None for item in items):
                proceed = QMessageBox.warning(
                    self,
                    "提示",
                    "选中的文件夹尚未计算大小，备份进度可能无法显示百分比。\n\n是否继续备份？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if proceed != QMessageBox.Yes:
                    if self._backup_dialog:
                        self._backup_dialog.abort_prepare()
                    return

            self._backup_failed = False
            self._last_backup_dest_path = normalized_dest_path
            self._last_backup_source_names = [os.path.basename(path) for path in src_paths]
            if self._backup_dialog:
                self._backup_dialog.begin_backup()

            # 创建备份工作线程（磁盘预检在后台线程执行）
            worker = BackupWorker(
                self.scanner,
                src_paths,
                normalized_dest_path,
                self._build_known_backup_progress_state(items),
                known_sizes,
            )
            worker.progress.connect(self._on_backup_progress)
            worker.finished.connect(self._on_backup_finished)
            worker.error.connect(self._on_backup_error)

            if self._backup_dialog:
                worker.progress.connect(self._backup_dialog.update_progress)
                worker.finished.connect(
                    lambda success: self._backup_dialog.backup_finished(
                        success,
                        self._format_backup_result_summary(),
                    )
                )
                worker.error.connect(
                    lambda title, message: self._backup_dialog.backup_failed(
                        title,
                        message,
                        self._format_backup_result_summary(),
                    )
                )
            
            if not self._start_worker(worker, "backup", "\u6b63\u5728\u5907\u4efd\u6587\u4ef6\u5939..."):
                if self._backup_dialog:
                    self._backup_dialog.abort_prepare()
                return

            self.progress_bar.setVisible(False)

        except Exception as e:
            self.logger.error(f"Error starting backup: {str(e)}")
            if self._backup_dialog:
                self._backup_dialog.abort_prepare()
            self.show_error("备份错误", str(e))

    def _on_calculate_progress(self, item: FileItem, current: int, total: int, speed: float):
        """处理计算进度"""
        try:
            # 更新进度条
            progress = int(current * 100 / total)
            self.progress_bar.setValue(progress)
            
            # 更新状态栏
            self._set_status_message(f"正在计算: {item.name} ({current}/{total})")
            
            # 更新速度标签
            self.speed_label.setText(f"速度: {speed:.1f} 项/秒")
            
        except Exception as e:
            self.logger.error(f"Error updating calculate progress: {str(e)}")

    def _on_calculate_finished(self):
        """处理计算完成"""
        try:
            # 更新UI状态
            self._current_worker = None
            self._is_busy = False
            was_cancelled = self.scanner.stopped or self._cancel_requested
            self._cancel_requested = False
            self.progress_bar.setVisible(False)
            self._update_button_states()
            self._set_status_message("计算已取消" if was_cancelled else "计算完成")
            self._set_runtime_state("计算已取消" if was_cancelled else "计算完成", "等待下一步操作")
            
        except Exception as e:
            self.logger.error(f"Error handling calculate finished: {str(e)}")

    def _on_backup_progress(self, current_file: str, current: int, total: int, speed: float, processed_bytes: int, total_bytes: int):
        """处理备份进度"""
        try:
            if self._backup_dialog and self._backup_dialog._backup_in_progress:
                self.progress_bar.setVisible(False)
                current_name = os.path.basename(current_file) if current_file else "准备中"
                self._set_status_message(f"正在备份: {current_name}（详见备份窗口）")
                self._set_runtime_state("备份中", "进度请查看备份对话框")
                return

            if total_bytes > 0:
                progress = min(100, int(processed_bytes * 100 / total_bytes))
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(progress)
                status_suffix = f"{current}/{total}, {progress}%" if total else f"{progress}%"
                detail = f"{self._format_speed(speed)} | {self._format_bytes(processed_bytes)} / {self._format_bytes(total_bytes)}"
            elif total > 0:
                progress = min(100, int(current * 100 / total))
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(progress)
                status_suffix = f"{current}/{total}, {progress}%"
                detail = f"{self._format_speed(speed)} | 已处理 {self._format_bytes(processed_bytes)}"
            else:
                self.progress_bar.setRange(0, 0)
                status_suffix = f"{current}/?" if current else "进行中"
                detail = f"{self._format_speed(speed)} | 已处理 {self._format_bytes(processed_bytes)}"

            self._set_status_message(f"正在备份: {os.path.basename(current_file)} ({status_suffix})")
            self._set_runtime_state("备份中", detail)

        except Exception as e:
            self.logger.error(f"Error updating backup progress: {str(e)}")

    def _on_backup_error(self, title: str, message: str):
        self._backup_failed = True
        self.error_handler.handle_error(title, Exception(message))
        if not self._backup_dialog:
            self.show_error(title, message)

    def _on_backup_finished(self, success: bool):
        """处理备份完成"""
        try:
            self._current_worker = None
            self._is_busy = False
            was_cancelled = self.scanner.stopped or self._cancel_requested
            self._cancel_requested = False
            failed = self._backup_failed or (not success and not was_cancelled and bool(self.scanner.last_backup_error))
            self.progress_bar.setVisible(False)
            self._update_button_states()

            summary = self._format_backup_result_summary()

            if success and not was_cancelled:
                detail = summary or "已合并已有目录，并覆盖同名文件"
                self._set_status_message("备份已完成（合并并覆盖）")
                self._set_runtime_state("备份完成", detail.split("\n")[0] if detail else "等待下一步操作")
            elif failed:
                stats = self.scanner.last_backup_stats
                if stats and stats.rolled_back:
                    self._set_status_message("备份失败，已自动回滚")
                    detail = self.scanner.last_backup_error or summary or "请查看错误详情"
                else:
                    self._set_status_message("备份失败")
                    detail = self.scanner.last_backup_error or "请查看错误详情"
                self._set_runtime_state("备份失败", detail.split("\n")[0] if detail else "请查看错误详情")
            else:
                self._set_status_message("备份已取消，已保留已复制内容")
                self._set_runtime_state("备份已取消", summary.split("\n")[0] if summary else "等待下一步操作")

            self._record_backup_history(
                success=success,
                was_cancelled=was_cancelled,
                failed=failed,
                summary=summary,
            )

        except Exception as e:
            self.logger.error(f"Error handling backup finished: {str(e)}")

    def _record_backup_history(
        self,
        *,
        success: bool,
        was_cancelled: bool,
        failed: bool,
        summary: str,
    ) -> None:
        dest_path = getattr(self, "_last_backup_dest_path", None)
        if not dest_path:
            return

        if success and not was_cancelled:
            status = "success"
        elif was_cancelled:
            status = "cancelled"
        else:
            status = "failed"

        stats = self.scanner.last_backup_stats
        entry = create_backup_history_entry(
            dest_path=dest_path,
            source_names=getattr(self, "_last_backup_source_names", []),
            status=status,
            files_copied=stats.files_copied if stats else 0,
            bytes_copied=stats.bytes_copied if stats else 0,
            duration_seconds=stats.duration_seconds if stats else 0.0,
            detail=summary or self.scanner.last_backup_error or "",
        )
        self.config.add_backup_history(entry)

    def _update_select_all_state(self) -> None:
        """根据表格勾选情况更新表头全选复选框状态。"""
        try:
            if self.select_all_checkbox is None:
                return

            blocker = QSignalBlocker(self.select_all_checkbox)

            total_count = self.table_model.rowCount()
            checked_count = self.table_model.get_checked_count()

            self.select_all_checkbox.setText("")

            if total_count == 0:
                self.select_all_checkbox.setEnabled(False)
                self.select_all_checkbox.setTristate(False)
                self.select_all_checkbox.setCheckState(Qt.Unchecked)
                self.select_all_checkbox.setToolTip(self._build_select_all_tooltip(checked_count, total_count))
                return

            self.select_all_checkbox.setEnabled(True)

            if checked_count == 0:
                self.select_all_checkbox.setTristate(False)
                self.select_all_checkbox.setCheckState(Qt.Unchecked)
                self.select_all_checkbox.setToolTip(self._build_select_all_tooltip(checked_count, total_count))
            elif checked_count == total_count:
                self.select_all_checkbox.setTristate(False)
                self.select_all_checkbox.setCheckState(Qt.Checked)
                self.select_all_checkbox.setToolTip(self._build_select_all_tooltip(checked_count, total_count))
            else:
                self.select_all_checkbox.setTristate(True)
                self.select_all_checkbox.setCheckState(Qt.PartiallyChecked)
                self.select_all_checkbox.setToolTip(self._build_select_all_tooltip(checked_count, total_count))

        except Exception as e:
            self.logger.error(f"Error updating select all state: {str(e)}")

    def _select_all_items(self) -> None:
        if self.select_all_checkbox is not None and self.select_all_checkbox.isEnabled():
            self.select_all_checkbox.setCheckState(Qt.Checked)

    def _clear_selected_items(self) -> None:
        if self.select_all_checkbox is not None and self.select_all_checkbox.isEnabled():
            self.select_all_checkbox.setCheckState(Qt.Unchecked)

    def _copy_checked_paths(self) -> None:
        try:
            items = self.table_model.get_checked_items()
            if not items:
                self._set_status_message("请先勾选要复制路径的文件夹")
                return

            QApplication.clipboard().setText("\n".join(item.path for item in items))
            self._set_status_message(f"已复制 {len(items)} 条路径到剪贴板")
        except Exception as e:
            self.logger.error(f"Error copying checked paths: {str(e)}")

    def _has_uncalculated_checked_items(self) -> bool:
        return any(item.size is None for item in self.table_model.get_checked_items())

    def _update_button_states(self, scanning: bool = False) -> None:
        """更新按钮状态"""
        try:
            has_items = bool(self.table_model.rowCount())
            has_checked = bool(self.table_model.get_checked_items())

            action_state = build_action_state(
                is_busy=self._is_busy,
                has_directory=bool(self.current_directory),
                has_items=has_items,
                has_checked=has_checked,
                cancel_requested=self._cancel_requested,
            )

            self.select_btn.setEnabled(action_state.select_enabled)
            self.start_btn.setEnabled(action_state.start_enabled)
            self.stop_btn.setEnabled(action_state.stop_enabled)
            self.calculate_btn.setEnabled(action_state.calculate_enabled)
            self.export_btn.setEnabled(action_state.export_enabled)
            self.backup_btn.setEnabled(action_state.backup_enabled)
            if action_state.backup_enabled and self._has_uncalculated_checked_items():
                self.backup_btn.setToolTip(
                    "将选中文件夹备份到目标位置 (Ctrl+B)\n建议先点击「计算」以显示准确进度"
                )
            elif action_state.backup_enabled:
                self.backup_btn.setToolTip("将选中文件夹备份到目标位置 (Ctrl+B)")

            for action_name, enabled in (
                ("_select_action", action_state.select_enabled),
                ("_scan_action", action_state.start_enabled),
                ("_stop_action", action_state.stop_enabled),
                ("_calc_action", action_state.calculate_enabled),
                ("_export_action", action_state.export_enabled),
                ("_backup_action", action_state.backup_enabled),
            ):
                action = getattr(self, action_name, None)
                if action is not None:
                    action.setEnabled(enabled)
                
        except Exception as e:
            self.logger.error(f"Error updating button states: {str(e)}")

    def _on_model_rows_changed(self) -> None:
        self._refresh_empty_state()
        self._update_select_all_state()
        self._update_button_states()
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        """更新状态栏"""
        try:
            total_items = self.table_model.rowCount()
            checked_items = len(self.table_model.get_checked_items())
            has_computed = any(
                self.table_model.get_item(i).size is not None
                for i in range(total_items)
            )

            self.folder_count_label.setText(f"\u6587\u4ef6\u5939: {total_items:,}")
            self.selection_label.setText(f"\u5df2\u9009: {checked_items:,}")

            checked_has_computed = any(
                self.table_model.get_item(i).checked and self.table_model.get_item(i).size is not None
                for i in range(total_items)
            )

            if total_items > 0:
                if has_computed:
                    total_size, size_formatted = self.table_model.get_total_size()
                    total_files = self.table_model.get_total_files()
                    status_text = (
                        f"\u603b\u6587\u4ef6\u5939\u6570: {total_items:,} | "
                        f"\u603b\u6587\u4ef6\u6570: {total_files:,} | "
                        f"\u603b\u5927\u5c0f: {size_formatted}"
                    )
                    self.file_count_label.setText(f"\u6587\u4ef6\u6570: {total_files:,}")
                    self.size_label.setText(f"\u603b\u5927\u5c0f: {size_formatted}")
                else:
                    status_text = f"\u603b\u6587\u4ef6\u5939\u6570: {total_items:,} | \u52fe\u9009\u540e\u70b9\u51fb\u8ba1\u7b97\u67e5\u770b\u5927\u5c0f"
                    self.file_count_label.setText("\u6587\u4ef6\u6570: \u672a\u8ba1\u7b97")
                    self.size_label.setText("\u603b\u5927\u5c0f: \u672a\u8ba1\u7b97")

                if checked_has_computed:
                    checked_total_size, checked_size_formatted = self.table_model.get_checked_total_size()
                    checked_total_files = self.table_model.get_checked_total_files()
                    self.selected_file_count_label.setText(f"\u5df2\u9009\u6587\u4ef6\u6570: {checked_total_files:,}")
                    self.selected_size_label.setText(f"\u5df2\u9009\u603b\u5927\u5c0f: {checked_size_formatted}")
                else:
                    self.selected_file_count_label.setText("\u5df2\u9009\u6587\u4ef6\u6570: \u672a\u8ba1\u7b97")
                    self.selected_size_label.setText("\u5df2\u9009\u603b\u5927\u5c0f: \u672a\u8ba1\u7b97")

                if self.current_directory:
                    status_text += f" | \u5f53\u524d\u76ee\u5f55: {self.current_directory}"

                if not self._is_busy and not self._cancel_requested:
                    self._set_status_message(status_text)
            else:
                self.file_count_label.setText("\u6587\u4ef6\u6570: \u672a\u8ba1\u7b97")
                self.size_label.setText("\u603b\u5927\u5c0f: \u672a\u8ba1\u7b97")
                self.selected_file_count_label.setText("\u5df2\u9009\u6587\u4ef6\u6570: \u672a\u8ba1\u7b97")
                self.selected_size_label.setText("\u5df2\u9009\u603b\u5927\u5c0f: \u672a\u8ba1\u7b97")

                if self.current_directory:
                    self._update_current_path_label(self.current_directory)
                else:
                    self._update_current_path_label(None)

                if not self._is_busy and not self._cancel_requested:
                    self._set_status_message("\u8bf7\u9009\u62e9\u76ee\u5f55\u5f00\u59cb\u626b\u63cf\uff0c\u6216\u76f4\u63a5\u62d6\u653e\u6587\u4ef6\u5939\u5230\u8fd9\u91cc")
                    self._set_runtime_state("\u672a\u5f00\u59cb", "\u9009\u62e9\u76ee\u5f55\u540e\u81ea\u52a8\u626b\u63cf")

        except Exception as e:
            self.logger.error(f"Error updating status bar: {str(e)}")

    def _update_current_path_label(self, path: Optional[str]) -> None:
        if not self.current_path_label:
            return

        if not path:
            self.current_path_label.setText("\u672a\u9009\u62e9\u76ee\u5f55")
            self.current_path_label.setToolTip("")
            return

        available_width = max(self.current_path_label.width() - 12, 40)
        display_text = self.current_path_label.fontMetrics().elidedText(
            path,
            Qt.ElideMiddle,
            available_width,
        )
        self.current_path_label.setText(display_text)
        self.current_path_label.setToolTip(path)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._reposition_select_all_checkbox)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_current_path_label(self.current_directory)
        self._reposition_select_all_checkbox()

    def _on_select_all_changed(self, state):
        """处理表头全选复选框状态变化。

        Args:
            state: Qt 复选框状态
        """
        try:
            if state == Qt.PartiallyChecked:
                return

            changed = self.table_model.set_all_checked(state == Qt.Checked)
            if not changed:
                self._update_select_all_state()

        except Exception as e:
            self.logger.error(f"Error handling select all change: {str(e)}")

    def _on_data_changed(self, topLeft, bottomRight, roles):
        """处理数据变化事件
        
        Args:
            topLeft: 左上角索引
            bottomRight: 右下角索引
            roles: 改变的角色列表
        """
        try:
            # 更新全选状态
            self._update_select_all_state()
            
            # 更新按钮状态
            self._update_button_states()
            self._refresh_empty_state()
            
            # 更新状态栏
            self._update_status_bar()
            
        except Exception as e:
            self.logger.error(f"Error handling data changed: {str(e)}")

    def _on_table_clicked(self, index):
        """Handle row clicks by toggling the processing checkbox state."""
        try:
            if not index.isValid() or index.column() == 0:
                return

            self.table_model.toggle_checked(index.row())
        except Exception as e:
            self.logger.error(f"Error handling table click: {str(e)}")

    def _on_item_double_clicked(self, index):
        """处理表格项双击，在资源管理器中打开对应文件夹。
        
        Args:
            index: 被双击的模型索引
        """
        try:
            if not index.isValid():
                return
            
            item = self.table_model.get_item(index.row())
            if item:
                self._open_item_in_file_explorer(item)
            
        except Exception as e:
            self.logger.error(f"Error handling item double click: {str(e)}")

    def _open_item_in_file_explorer(self, item: Optional[FileItem]) -> bool:
        """在资源管理器中打开指定文件夹。"""
        if not item or not item.path:
            self.show_error("打开失败", "未找到可打开的文件夹路径")
            return False

        folder_path = normalize_directory_path(item.path)

        if not os.path.exists(folder_path):
            self.show_error(
                "打开失败",
                f"文件夹不存在或已被移动: {folder_path}",
            )
            return False

        try:
            os.startfile(folder_path)
            return True
        except Exception as e:
            self.logger.error(f"Error opening item folder '{folder_path}': {str(e)}")
            self.show_error(
                "打开失败",
                f"无法打开文件夹: {folder_path}",
                str(e),
            )
            return False

    def _center_window(self):
        """处理表格项双击事件。"""
        try:
            screen = QApplication.primaryScreen().geometry()
            window = self.geometry()
            x = (screen.width() - window.width()) // 2
            y = (screen.height() - window.height()) // 2
            self.move(x, y)
        except Exception as e:
            self.logger.error(f"Error centering window: {str(e)}")

    def _show_context_menu(self, pos):
        """\u663e\u793a\u7ed3\u679c\u8868\u53f3\u952e\u83dc\u5355"""
        try:
            index = self.table_view.indexAt(pos)
            if not index.isValid():
                return

            item = self.table_model.get_item(index.row())
            if not item:
                return

            selection_model = self.table_view.selectionModel()
            if selection_model and not selection_model.isRowSelected(index.row(), index.parent()):
                selection_model.select(
                    index,
                    QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
                )

            menu = QMenu(self)
            menu.setObjectName("appMenu")
            menu.addSection("\u5feb\u901f\u64cd\u4f5c")

            open_action = menu.addAction("\u6253\u5f00\u6587\u4ef6\u5939")
            open_action.triggered.connect(lambda: self._open_item_in_file_explorer(item))

            copy_path_action = menu.addAction("\u590d\u5236\u8def\u5f84")
            copy_path_action.triggered.connect(
                lambda: QApplication.clipboard().setText(item.path)
            )

            menu.addSeparator()
            menu.addSection("\u5904\u7406")

            calculate_action = menu.addAction("\u8ba1\u7b97\u5927\u5c0f")
            calculate_action.setEnabled(not self._is_busy)
            calculate_action.triggered.connect(
                lambda: self._calculate_single_item(item)
            )

            menu.exec_(self.table_view.viewport().mapToGlobal(pos))
        except Exception as e:
            self.logger.error(f"Error showing context menu: {str(e)}")

    def _calculate_single_item(self, item: FileItem):
        """计算单个项目的大小
        
        Args:
            item: 要计算的文件项目
        """
        try:
            if self._is_busy:
                self.show_error("操作进行中", "请等待当前任务完成后再开始新的计算")
                return

            # 创建计算工作线程
            worker = CalculateWorker(self.scanner, [item])
            worker.progress.connect(self._on_calculate_progress)
            worker.finished.connect(lambda: self._on_calculate_finished())
            worker.error.connect(self.show_error)
            
            # 开始计算
            if not self._start_worker(worker, "calculate", f"正在计算: {item.name}"):
                return
            
            # 更新UI状态
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setFormat("正在计算: %p%")
            
        except Exception as e:
            self.logger.error(f"Error calculating single item: {str(e)}")
            self.show_error("计算错误", str(e))

    def dragEnterEvent(self, event):
        """\u5904\u7406\u62d6\u5165\u4e8b\u4ef6"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """\u5904\u7406\u653e\u4e0b\u4e8b\u4ef6"""
        try:
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if os.path.isdir(path):
                    self._set_selected_directory(path)
                else:
                    self.show_error("\u9519\u8bef", "\u8bf7\u62d6\u653e\u6587\u4ef6\u5939\u800c\u4e0d\u662f\u6587\u4ef6")
        except Exception as e:
            self.logger.error(f"Error handling drop event: {str(e)}")

    def _create_menu_bar(self):
        """\u521b\u5efa\u83dc\u5355\u680f"""
        try:
            menubar = self.menuBar()
            menubar.clear()
            menubar.setObjectName("appMenuBar")

            file_menu = menubar.addMenu("\u6587\u4ef6(&F)")
            file_menu.setObjectName("appMenu")

            self._select_action = file_menu.addAction("\u9009\u62e9\u76ee\u5f55(&O)")
            self._select_action.setShortcut("Ctrl+O")
            self._select_action.triggered.connect(self.select_directory)

            self._scan_action = file_menu.addAction("\u5f00\u59cb\u626b\u63cf(&S)")
            self._scan_action.setShortcut("Ctrl+S")
            self._scan_action.triggered.connect(self.start_scan)

            self._stop_action = file_menu.addAction("\u505c\u6b62(&T)")
            self._stop_action.setShortcut("Esc")
            self._stop_action.triggered.connect(self.stop_scan)

            file_menu.addSeparator()
            exit_action = file_menu.addAction("\u9000\u51fa(&X)")
            exit_action.setShortcut("Alt+F4")
            exit_action.triggered.connect(self.close)

            operation_menu = menubar.addMenu("\u64cd\u4f5c(&O)")
            operation_menu.setObjectName("appMenu")

            self._calc_action = operation_menu.addAction("\u8ba1\u7b97\u5927\u5c0f(&C)")
            self._calc_action.setShortcut("F5")
            self._calc_action.triggered.connect(self.calculate_selected)

            self._export_action = operation_menu.addAction("\u5bfc\u51fa Excel(&E)")
            self._export_action.setShortcut("Ctrl+E")
            self._export_action.triggered.connect(self.export_to_excel)

            self._backup_action = operation_menu.addAction("\u5907\u4efd\u76ee\u5f55(&B)")
            self._backup_action.setShortcut("Ctrl+B")
            self._backup_action.triggered.connect(self.backup_directory)

            view_menu = menubar.addMenu("\u89c6\u56fe(&V)")
            view_menu.setObjectName("appMenu")

            self._toolbar_toggle_action = view_menu.addAction("\u547d\u4ee4\u533a")
            self._toolbar_toggle_action.setCheckable(True)
            self._toolbar_toggle_action.setChecked(True)
            self._toolbar_toggle_action.triggered.connect(self._toggle_toolbar)

            self._bottom_panel_toggle_action = view_menu.addAction("\u72b6\u6001\u533a")
            self._bottom_panel_toggle_action.setCheckable(True)
            self._bottom_panel_toggle_action.setChecked(True)
            self._bottom_panel_toggle_action.triggered.connect(self._toggle_bottom_panel)

            help_menu = menubar.addMenu("\u5e2e\u52a9(&H)")
            help_menu.setObjectName("appMenu")
            about_action = help_menu.addAction("\u5173\u4e8e(&A)")
            about_action.triggered.connect(self._show_about_dialog)

            self._update_button_states()
        except Exception as e:
            self.logger.error(f"Error creating menu bar: {str(e)}")

    def _toggle_toolbar(self, checked: bool):
        """\u5207\u6362\u547d\u4ee4\u533a\u663e\u793a\u72b6\u6001"""
        try:
            if hasattr(self, "_toolbar_container"):
                self._toolbar_container.setVisible(checked)
            if hasattr(self, "_secondary_actions_container"):
                self._secondary_actions_container.setVisible(checked)
        except Exception as e:
            self.logger.error(f"Error toggling toolbar: {str(e)}")

    def _toggle_bottom_panel(self, checked: bool):
        """\u5207\u6362\u5e95\u90e8\u72b6\u6001\u533a\u663e\u793a\u72b6\u6001"""
        try:
            if self.status_bar is not None:
                bottom_panel = self.status_bar.parentWidget()
                if bottom_panel is not None:
                    bottom_panel.setVisible(checked)
        except Exception as e:
            self.logger.error(f"Error toggling bottom panel: {str(e)}")

    def _show_about_dialog(self):
        """\u663e\u793a\u5173\u4e8e\u5bf9\u8bdd\u6846"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"\u5173\u4e8e {APP_NAME}")
            dialog.setModal(True)
            dialog.setMinimumWidth(520)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(18, 18, 18, 18)
            layout.setSpacing(12)

            card = QFrame()
            card.setObjectName("dialogCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            card_layout.setSpacing(10)

            title_label = QLabel(f"{APP_NAME} {APP_VERSION}")
            title_label.setObjectName("dialogHeaderLabel")
            summary_label = QLabel("Windows \u684c\u9762\u6587\u4ef6\u5939\u626b\u63cf\u3001\u7edf\u8ba1\u3001\u5bfc\u51fa\u4e0e\u5907\u4efd\u5de5\u5177\u3002")
            summary_label.setObjectName("dialogStatusLabel")
            summary_label.setWordWrap(True)

            card_layout.addWidget(title_label)
            card_layout.addWidget(summary_label)
            layout.addWidget(card)

            button_layout = QHBoxLayout()
            button_layout.addStretch()
            close_button = QPushButton("\u5173\u95ed")
            close_button.setObjectName("dialogPrimaryButton")
            close_button.clicked.connect(dialog.accept)
            button_layout.addWidget(close_button)
            layout.addLayout(button_layout)

            dialog.exec_()
        except Exception as e:
            self.logger.error(f"Error showing about dialog: {str(e)}")
