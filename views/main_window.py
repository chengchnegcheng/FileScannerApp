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
    QCheckBox, QApplication, QFrame, QStyle, QSizePolicy, QHeaderView
)
from PyQt5.QtCore import (
    QThread, pyqtSignal, Qt, QDir, QTimer, QUrl, QItemSelectionModel, 
    QSize, QPoint
)
from PyQt5.QtGui import QIcon, QKeySequence, QColor, QCursor

from services.file_scanner import FileScanner
from utils.config_manager import ConfigManager
from utils.logger import LogManager
from models.file_item import FileItem
from viewmodels.main_viewmodel import FileTableModel
from workers.backup_worker import BackupWorker
from workers.calculate_worker import CalculateWorker
from workers.scan_worker import ScanWorker
from views.backup_dialog import BackupDialog

# 应用程序常量
APP_NAME = "文件夹大小扫描器"
APP_VERSION = "1.0.0"
APP_ORGANIZATION = "YourCompany"
APP_DOMAIN = "yourcompany.com"

# UI常量
UI_UPDATE_INTERVAL = 100  # ms
AUTOSAVE_INTERVAL = 300000  # 5分钟
MIN_WINDOW_SIZE = QSize(900, 600)  # 更合适的最小窗口大小
DEFAULT_BUTTON_SIZE = QSize(100, 30)  # 更紧凑的按钮大小
TOOLBAR_HEIGHT = 36  # 更紧凑的工具栏高度
STATS_PANEL_HEIGHT = 50  # 统计面板高度
BOTTOM_PANEL_HEIGHT = 40  # 更紧凑的底部面板高度

# 主题颜色
THEME_COLORS = {
    'primary': '#3b82f6',      # 主色调（蓝色）
    'primary_light': '#60a5fa', # 浅蓝色
    'success': '#10b981',      # 成功（绿色）
    'success_light': '#34d399', # 浅绿色
    'warning': '#f59e0b',      # 警告（橙色）
    'warning_light': '#fbbf24', # 浅橙色
    'danger': '#ef4444',       # 危险（红色）
    'danger_light': '#f87171', # 浅红色
    'background': '#f8fafc',   # 背景色
    'surface': '#ffffff',      # 表面色
    'border': '#e2e8f0',      # 边框色
    'text': '#1e293b',        # 文本色
    'text_secondary': '#64748b', # 次要文本色
}

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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
            
            # 表格和进度组件
            self.table_view = None
            self.progress_bar = None
            self.status_bar = None
            
            # 统计标签
            self.folder_count_label = None
            self.file_count_label = None
            self.size_label = None
            self.speed_label = None
            self.memory_label = None
            self.cpu_label = None
            
            # 其他控件
            self.select_all_checkbox = None
            
            # 自动保存设置
            self._auto_save_dir = 'auto_saves'
            self._auto_save_max_files = 5
            
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
            icon_path = "resources/icons/folder.png"
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
            main_layout.setSpacing(2)  # 减小间距
            main_layout.setContentsMargins(2, 2, 2, 2)  # 减小边距
            
            # 添加主要组件
            main_layout.addWidget(self._create_toolbar())
            main_layout.addWidget(self._create_table_view())
            main_layout.addWidget(self._create_bottom_panel())
            
            # 设置状态栏提示
            self.status_bar.showMessage("就绪")
            
        except Exception as e:
            self.logger.error(f"Error setting up UI: {str(e)}")
            raise

    def _setup_styles(self):
        """设置样式"""
        try:
            # 加载QSS样式文件
            style_file = "resources/styles/main.qss"
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
            QShortcut(QKeySequence("Ctrl+C"), self, self.calculate_selected)
            QShortcut(QKeySequence("Ctrl+E"), self, self.export_to_excel)
            QShortcut(QKeySequence("Ctrl+B"), self, self.backup_directory)
            
            # 其他快捷键
            QShortcut(QKeySequence("Ctrl+A"), self, lambda: self.select_all_checkbox.setChecked(True))
            QShortcut(QKeySequence("Ctrl+D"), self, lambda: self.select_all_checkbox.setChecked(False))
            
        except Exception as e:
            self.logger.error(f"Error setting up shortcuts: {str(e)}")

    def _start_services(self):
        """启动服务"""
        try:
            # 启动定时器
            self._update_timer.start()
            self._autosave_timer.start()
            
            # 设置状态栏初始消息
            self.status_bar.showMessage("就绪")
            
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
            self.memory_label.setText(f"内存: {memory.percent}%")
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
        """创建工具栏"""
        try:
            self._toolbar_container = container = QFrame()
            container.setObjectName("toolbarContainer")
            container.setFixedHeight(TOOLBAR_HEIGHT)
            
            layout = QHBoxLayout(container)
            layout.setSpacing(2)  # 减小按钮间距
            layout.setContentsMargins(2, 0, 2, 0)  # 减小边距
            
            # 创建基本按钮
            self.select_btn = self._create_button("选择", "folder", self.select_directory)
            self.start_btn = self._create_button("扫描", "play", self.start_scan)
            self.stop_btn = self._create_button("停止", "stop", self.stop_scan)
            self.calculate_btn = self._create_button("计算", "calculate", self.calculate_selected)
            self.export_btn = self._create_button("导出", "export", self.export_to_excel)
            self.backup_btn = self._create_button("备份", "backup", self.backup_directory)
            
            # 设置按钮状态
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.calculate_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.backup_btn.setEnabled(False)
            
            # 添加按钮到布局
            for btn in [self.select_btn, self.start_btn, self.stop_btn, 
                       self.calculate_btn, self.export_btn, self.backup_btn]:
                layout.addWidget(btn)
            
            layout.addStretch()
            return container
            
        except Exception as e:
            self.logger.error(f"Error creating toolbar: {str(e)}")
            raise

    def _create_stats_panel(self) -> QWidget:
        """创建统计面板"""
        try:
            container = QFrame()
            container.setObjectName("statsPanel")
            
            layout = QHBoxLayout(container)
            layout.setSpacing(20)
            layout.setContentsMargins(10, 5, 10, 5)
            
            # 左侧统计组
            left_group = QWidget()
            left_layout = QHBoxLayout(left_group)
            left_layout.setSpacing(15)
            left_layout.setContentsMargins(0, 0, 0, 0)
            
            # 全选复选框
            self.select_all_checkbox = QCheckBox("全选")
            self.select_all_checkbox.stateChanged.connect(self._on_select_all_changed)
            left_layout.addWidget(self.select_all_checkbox)
            
            # 基本统计信息
            self.folder_count_label = QLabel("文件夹: 0")
            self.file_count_label = QLabel("文件数: 0")
            self.size_label = QLabel("总大小: 0 B")
            
            for label in [self.folder_count_label, self.file_count_label, self.size_label]:
                label.setObjectName("statsLabel")
                left_layout.addWidget(label)
            
            left_group.setLayout(left_layout)
            
            # 右侧性能组
            right_group = QWidget()
            right_layout = QHBoxLayout(right_group)
            right_layout.setSpacing(15)
            right_layout.setContentsMargins(0, 0, 0, 0)
            
            # 性能统计信息
            self.speed_label = QLabel("速度: 0 B/s")
            self.memory_label = QLabel("内存: 0%")
            self.cpu_label = QLabel("CPU: 0%")
            
            for label in [self.speed_label, self.memory_label, self.cpu_label]:
                label.setObjectName("statsLabel")
                right_layout.addWidget(label)
            
            right_group.setLayout(right_layout)
            
            # 组装面板
            layout.addWidget(left_group)
            layout.addStretch(1)
            layout.addWidget(right_group)
            
            return container
            
        except Exception as e:
            self.logger.error(f"Error creating stats panel: {str(e)}")
            raise

    def _create_table_view(self) -> QWidget:
        """创建表格视图"""
        try:
            container = QFrame()
            container.setObjectName("tableContainer")
            
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            
            # 创建表格视图
            self.table_view = QTableView()
            self.table_view.setModel(self.table_model)
            
            # 设置表格属性
            self.table_view.setSelectionBehavior(QTableView.SelectRows)
            self.table_view.setSelectionMode(QTableView.ExtendedSelection)
            self.table_view.setAlternatingRowColors(True)
            self.table_view.setSortingEnabled(True)
            self.table_view.setShowGrid(False)
            self.table_view.verticalHeader().setVisible(False)
            
            # 设置表头
            header = self.table_view.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Fixed)  # 复选框列
            header.setSectionResizeMode(1, QHeaderView.Interactive)  # 名称列
            header.setSectionResizeMode(2, QHeaderView.Interactive)  # 大小列
            header.setSectionResizeMode(3, QHeaderView.Interactive)  # 文件数列
            header.setSectionResizeMode(4, QHeaderView.Interactive)  # 状态列
            
            # 设置列宽
            self.table_view.setColumnWidth(0, 30)  # 复选框列
            self.table_view.setColumnWidth(1, 300)  # 名称列
            self.table_view.setColumnWidth(2, 100)  # 大小列
            self.table_view.setColumnWidth(3, 80)  # 文件数列
            self.table_view.setColumnWidth(4, 80)  # 状态列
            
            # 连接信号
            self.table_model.dataChanged.connect(self._on_data_changed)
            self.table_view.doubleClicked.connect(self._on_item_double_clicked)
            
            layout.addWidget(self.table_view)
            return container
            
        except Exception as e:
            self.logger.error(f"Error creating table view: {str(e)}")
            raise

    def _create_bottom_panel(self) -> QWidget:
        """创建底部面板"""
        try:
            container = QFrame()
            container.setFixedHeight(BOTTOM_PANEL_HEIGHT)
            
            layout = QVBoxLayout(container)
            layout.setContentsMargins(2, 0, 2, 0)  # 减小边距
            layout.setSpacing(0)
            
            # 创建进度条
            self.progress_bar = QProgressBar()
            self.progress_bar.setFixedHeight(4)  # 更细的进度条
            self.progress_bar.setVisible(False)
            layout.addWidget(self.progress_bar)
            
            # 创建状态栏
            self.status_bar = QStatusBar()
            self.status_bar.setFixedHeight(BOTTOM_PANEL_HEIGHT - 4)  # 减去进度条高度
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
            
            # 设置图标
            icon_path = f"resources/icons/{icon_name}.png"
            if os.path.exists(icon_path):
                button.setIcon(QIcon(icon_path))
            
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
            
            result = msg.exec_()
            
            # 处理复制按钮点击
            if msg.clickedButton() == copy_button and details:
                QApplication.clipboard().setText(details)
                self.status_bar.showMessage("错误详情已复制到剪贴板", 3000)
            
        except Exception as e:
            self.logger.error(f"Error showing error dialog: {str(e)}")

    def select_directory(self):
        """选择目录"""
        try:
            # 如果有最近使用的目录，显示菜单
            if self.config.get_setting('recent_directories'):
                self._show_directory_menu()
            else:
                # 否则直接打开浏览对话框
                self._browse_directory()
        except Exception as e:
            self.logger.error(f"Error selecting directory: {str(e)}")

    def _show_directory_menu(self):
        """显示最近目录菜单"""
        try:
            menu = QMenu(self)
            recent_dirs = self.config.get_setting('recent_directories', [])
            
            for path in recent_dirs:
                action = menu.addAction(path)
                action.triggered.connect(lambda checked, p=path: self._scan_directory(p))
                
            menu.addSeparator()
            menu.addAction("浏览...", self._browse_directory)
            
            # 显示菜单
            menu.exec_(QCursor.pos())
            
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
                self._scan_directory(path)
                
        except Exception as e:
            self.logger.error(f"Error browsing directory: {str(e)}")
            self.show_error("选择错误", str(e))

    def _scan_directory(self, path: str):
        """扫描目录"""
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"目录不存在: {path}")
            
            # 更新当前目录
            self.current_directory = path
            
            # 清空现有数据
            self.table_model.clear()
            
            # 创建扫描工作线程
            worker = ScanWorker(self.scanner, path)
            worker.file_found.connect(self.table_model.add_item)
            worker.finished.connect(lambda success: self._on_scan_finished(success))
            worker.error.connect(self.show_error)
            
            # 开始扫描
            self._start_worker(worker)
            
            # 更新UI状态
            self.progress_bar.setVisible(True)
            self.progress_bar.setFormat("正在扫描...")
            self.status_bar.showMessage(f"正在扫描: {path}")
            
            # 保存到最近使用的目录
            self.config.add_recent_directory(path)
            
        except Exception as e:
            self.logger.error(f"Error scanning directory: {str(e)}")
            self.show_error("扫描错误", str(e))

    def _start_worker(self, worker: QThread) -> None:
        """启动工作线程"""
        try:
            # 停止当前工作线程
            if self._current_worker and self._current_worker.isRunning():
                self._current_worker.quit()
                self._current_worker.wait()
            
            # 设置新的工作线程
            self._current_worker = worker
            self._workers.append(worker)
            
            # 清理已完成的工作线程
            self._cleanup_workers()
            
            # 更新UI状态
            self._update_button_states(scanning=True)
            
            # 启动工作线程
            worker.start()
            
        except Exception as e:
            self.logger.error(f"Error starting worker: {str(e)}")
            self.show_error("线程错误", f"启动工作线程失败: {str(e)}")

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
            
            # 更新UI状态
            self.progress_bar.setVisible(False)
            self._update_button_states(scanning=False)
            
            if success:
                # 更新状态栏
                total_items = self.table_model.rowCount()
                total_files = self.table_model.get_total_files()
                total_size, size_formatted = self.table_model.get_total_size()
                
                status_text = (
                    f"扫描完成，共发现 {total_items} 个文件夹，"
                    f"{total_files} 个文件，"
                    f"总大小: {size_formatted}"
                )
                self.status_bar.showMessage(status_text)
                
                # 更新表格显示
                self.table_view.resizeColumnsToContents()
                self.table_view.resizeRowsToContents()
                
                # 自动保存结果
                self._auto_save_results()
            else:
                self.status_bar.showMessage("扫描已取消")
                
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
            # 停止扫描器
            self.scanner.stop()
            
            # 停止当前工作线程
            if self._current_worker and self._current_worker.isRunning():
                self._current_worker.quit()
                self._current_worker.wait()
            
            # 更新UI状态
            self.progress_bar.setVisible(False)
            self._update_button_states(scanning=False)
            self.status_bar.showMessage("操作已停止")
            
        except Exception as e:
            self.logger.error(f"Error stopping operation: {str(e)}")

    def calculate_selected(self):
        """计算选中项目的大小"""
        try:
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
            self._start_worker(worker)
            
            # 更新UI状态
            self.progress_bar.setVisible(True)
            self.progress_bar.setFormat("正在计算: %p%")
            self.status_bar.showMessage("正在计算文件夹大小...")
            
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
            self.table_model.export_to_excel(file_path, items)
            self.status_bar.showMessage(f"已导出到: {file_path}")
            
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
            dialog = BackupDialog(self)
            dialog.backup_started.connect(lambda dest_path: self._start_backup(items, dest_path))
            dialog.exec_()
            
        except Exception as e:
            self.logger.error(f"Error backing up directories: {str(e)}")
            self.show_error("备份错误", str(e))

    def _start_backup(self, items: List[FileItem], dest_path: str):
        """开始备份操作"""
        try:
            # 创建备份工作线程
            worker = BackupWorker(
                self.scanner,
                [item.path for item in items],
                dest_path
            )
            worker.progress.connect(self._on_backup_progress)
            worker.finished.connect(self._on_backup_finished)
            worker.error.connect(self.show_error)
            
            # 开始备份
            self._start_worker(worker)
            
            # 更新UI状态
            self.progress_bar.setVisible(True)
            self.progress_bar.setFormat("正在备份: %p%")
            self.status_bar.showMessage("正在备份文件夹...")
            
        except Exception as e:
            self.logger.error(f"Error starting backup: {str(e)}")
            self.show_error("备份错误", str(e))

    def _on_calculate_progress(self, item: FileItem, current: int, total: int, speed: float):
        """处理计算进度"""
        try:
            # 更新进度条
            progress = int(current * 100 / total)
            self.progress_bar.setValue(progress)
            
            # 更新状态栏
            self.status_bar.showMessage(
                f"正在计算: {item.name} ({current}/{total})"
            )
            
            # 更新速度标签
            self.speed_label.setText(f"速度: {speed:.1f} 项/秒")
            
        except Exception as e:
            self.logger.error(f"Error updating calculate progress: {str(e)}")

    def _on_calculate_finished(self):
        """处理计算完成"""
        try:
            # 更新UI状态
            self.progress_bar.setVisible(False)
            self._update_button_states(scanning=False)
            self.status_bar.showMessage("计算完成")
            self.speed_label.setText("速度: 0 项/秒")
            
        except Exception as e:
            self.logger.error(f"Error handling calculate finished: {str(e)}")

    def _on_backup_progress(self, current_file: str, current: int, total: int, speed: float, total_bytes: int):
        """处理备份进度"""
        try:
            # 更新进度条
            progress = int(current * 100 / total)
            self.progress_bar.setValue(progress)
            
            # 更新状态栏
            self.status_bar.showMessage(
                f"正在备份: {os.path.basename(current_file)} ({current}/{total})"
            )
            
            # 更新速度标签
            self.speed_label.setText(f"速度: {self._format_speed(speed)}")
            
        except Exception as e:
            self.logger.error(f"Error updating backup progress: {str(e)}")

    def _on_backup_finished(self, success: bool):
        """处理备份完成"""
        try:
            # 更新UI状态
            self.progress_bar.setVisible(False)
            self._update_button_states(scanning=False)
            
            if success:
                self.status_bar.showMessage("备份完成")
            else:
                self.status_bar.showMessage("备份已取消")
                
            self.speed_label.setText("速度: 0 B/s")
            
        except Exception as e:
            self.logger.error(f"Error handling backup finished: {str(e)}")

    def _update_select_all_state(self) -> None:
        """更新全选复选框状态"""
        try:
            if not self.table_model.rowCount():
                self.select_all_checkbox.setChecked(False)
                return
                
            checked_count = len(self.table_model.get_checked_items())
            total_count = self.table_model.rowCount()
            
            if checked_count == 0:
                self.select_all_checkbox.setChecked(False)
            elif checked_count == total_count:
                self.select_all_checkbox.setChecked(True)
            else:
                # 部分选中状态
                self.select_all_checkbox.setTristate(True)
                self.select_all_checkbox.setCheckState(Qt.PartiallyChecked)
                
        except Exception as e:
            self.logger.error(f"Error updating select all state: {str(e)}")

    def _update_button_states(self, scanning: bool = False) -> None:
        """更新按钮状态"""
        try:
            has_items = bool(self.table_model.rowCount())
            has_checked = bool(self.table_model.get_checked_items())
            
            # 更新扫描相关按钮
            self.select_btn.setEnabled(not scanning)
            self.start_btn.setEnabled(not scanning and has_items)
            self.stop_btn.setEnabled(scanning)
            
            # 更新操作按钮
            for btn in [self.calculate_btn, self.export_btn, self.backup_btn]:
                btn.setEnabled(not scanning and has_checked)
                
        except Exception as e:
            self.logger.error(f"Error updating button states: {str(e)}")

    def _update_status_bar(self) -> None:
        """更新状态栏"""
        try:
            total_items = self.table_model.rowCount()
            if total_items > 0:
                total_size, size_formatted = self.table_model.get_total_size()
                total_files = self.table_model.get_total_files()
                
                status_text = (
                    f"总文件夹: {total_items:,} | "
                    f"总文件数: {total_files:,} | "
                    f"总大小: {size_formatted}"
                )
                
                if self.current_directory:
                    status_text += f" | 当前目录: {self.current_directory}"
                    
                self.status_bar.showMessage(status_text)
                
                # 更新标签
                self.folder_count_label.setText(f"文件夹: {total_items:,}")
                self.file_count_label.setText(f"文件数: {total_files:,}")
                self.size_label.setText(f"总大小: {size_formatted}")
                
        except Exception as e:
            self.logger.error(f"Error updating status bar: {str(e)}")

    def _on_select_all_changed(self, state):
        """处理全选状态变化
        
        Args:
            state: Qt.CheckState 状态值
        """
        try:
            # 开始批量更新
            self.table_model.beginResetModel()
            
            # 更新所有项的选中状态
            for item in self.table_model._data:
                item.checked = bool(state == Qt.Checked)
            
            # 结束批量更新
            self.table_model.endResetModel()
            
            # 更新按钮状态
            self._update_button_states()
            
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
            
            # 更新状态栏
            self._update_status_bar()
            
        except Exception as e:
            self.logger.error(f"Error handling data changed: {str(e)}")

    def _on_item_double_clicked(self, index):
        """处理项目双击事件
        
        Args:
            index: 项目索引
        """
        try:
            if not index.isValid():
                return
            
            item = self.table_model.get_item(index.row())
            if item and os.path.exists(item.path):
                os.startfile(item.path)
            
        except Exception as e:
            self.logger.error(f"Error handling item double click: {str(e)}")

    def _center_window(self):
        """将窗口居中显示"""
        try:
            # 获取屏幕几何信息
            screen = QApplication.primaryScreen().geometry()
            # 获取窗口几何信息
            window = self.geometry()
            # 计算居中位置
            x = (screen.width() - window.width()) // 2
            y = (screen.height() - window.height()) // 2
            # 移动窗口
            self.move(x, y)
        except Exception as e:
            self.logger.error(f"Error centering window: {str(e)}")

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        try:
            # 获取点击位置的项目
            index = self.table_view.indexAt(pos)
            if not index.isValid():
                return
            
            item = self.table_model.get_item(index.row())
            if not item:
                return
            
            # 创建菜单
            menu = QMenu(self)
            
            # 添加菜单项
            open_action = menu.addAction("打开文件夹")
            open_action.triggered.connect(lambda: os.startfile(item.path))
            
            copy_path_action = menu.addAction("复制路径")
            copy_path_action.triggered.connect(
                lambda: QApplication.clipboard().setText(item.path)
            )
            
            menu.addSeparator()
            
            calculate_action = menu.addAction("计算大小")
            calculate_action.triggered.connect(
                lambda: self._calculate_single_item(item)
            )
            
            # 显示菜单
            menu.exec_(self.table_view.viewport().mapToGlobal(pos))
            
        except Exception as e:
            self.logger.error(f"Error showing context menu: {str(e)}")

    def _calculate_single_item(self, item: FileItem):
        """计算单个项目的大小
        
        Args:
            item: 要计算的文件项目
        """
        try:
            # 创建计算工作线程
            worker = CalculateWorker(self.scanner, [item])
            worker.progress.connect(self._on_calculate_progress)
            worker.finished.connect(lambda: self._on_calculate_finished())
            worker.error.connect(self.show_error)
            
            # 开始计算
            self._start_worker(worker)
            
            # 更新UI状态
            self.progress_bar.setVisible(True)
            self.progress_bar.setFormat("正在计算: %p%")
            self.status_bar.showMessage(f"正在计算: {item.name}")
            
        except Exception as e:
            self.logger.error(f"Error calculating single item: {str(e)}")
            self.show_error("计算错误", str(e))

    def dragEnterEvent(self, event):
        """处理拖入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """处理放下事件"""
        try:
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if os.path.isdir(path):
                    self._scan_directory(path)
                else:
                    self.show_error("错误", "请拖放文件夹而不是文件")
        except Exception as e:
            self.logger.error(f"Error handling drop event: {str(e)}")

    def _create_menu_bar(self):
        """创建菜单栏"""
        try:
            menubar = self.menuBar()
            
            # 文件菜单
            file_menu = menubar.addMenu("文件(&F)")
            
            select_action = file_menu.addAction("选择目录(&O)")
            select_action.setShortcut("Ctrl+O")
            select_action.triggered.connect(self.select_directory)
            
            scan_action = file_menu.addAction("开始扫描(&S)")
            scan_action.setShortcut("Ctrl+S")
            scan_action.triggered.connect(self.start_scan)
            
            stop_action = file_menu.addAction("停止(&T)")
            stop_action.setShortcut("Esc")
            stop_action.triggered.connect(self.stop_scan)
            
            file_menu.addSeparator()
            
            exit_action = file_menu.addAction("退出(&X)")
            exit_action.setShortcut("Alt+F4")
            exit_action.triggered.connect(self.close)
            
            # 操作菜单
            operation_menu = menubar.addMenu("操作(&O)")
            
            calc_action = operation_menu.addAction("计算大小(&C)")
            calc_action.setShortcut("Ctrl+C")
            calc_action.triggered.connect(self.calculate_selected)
            
            export_action = operation_menu.addAction("导出Excel(&E)")
            export_action.setShortcut("Ctrl+E")
            export_action.triggered.connect(self.export_to_excel)
            
            backup_action = operation_menu.addAction("备份(&B)")
            backup_action.setShortcut("Ctrl+B")
            backup_action.triggered.connect(self.backup_directory)
            
            # 视图菜单
            view_menu = menubar.addMenu("视图(&V)")
            
            toolbar_action = view_menu.addAction("工具栏")
            toolbar_action.setCheckable(True)
            toolbar_action.setChecked(True)
            toolbar_action.triggered.connect(lambda checked: self._toggle_toolbar(checked))
            
            statusbar_action = view_menu.addAction("状态栏")
            statusbar_action.setCheckable(True)
            statusbar_action.setChecked(True)
            statusbar_action.triggered.connect(lambda checked: self.statusBar().setVisible(checked))
            
            # 帮助菜单
            help_menu = menubar.addMenu("帮助(&H)")
            
            about_action = help_menu.addAction("关于(&A)")
            about_action.triggered.connect(self._show_about_dialog)
            
        except Exception as e:
            self.logger.error(f"Error creating menu bar: {str(e)}")

    def _toggle_toolbar(self, checked: bool):
        """切换工具栏显示状态"""
        try:
            if hasattr(self, '_toolbar_container'):
                self._toolbar_container.setVisible(checked)
        except Exception as e:
            self.logger.error(f"Error toggling toolbar: {str(e)}")

    def _show_about_dialog(self):
        """显示关于对话框"""
        try:
            about_text = f"""
            <h3>{APP_NAME} v{APP_VERSION}</h3>
            <p>一个用于扫描和分析文件夹大小的工具</p>
            <p>
                <b>功能特点：</b><br>
                - 快速扫描文件夹结构<br>
                - 计算文件夹大小<br>
                - 导出扫描结果<br>
                - 文件夹备份
            </p>
            <p>
                <b>技术支持：</b><br>
                {APP_ORGANIZATION}<br>
                {APP_DOMAIN}
            </p>
            """
            
            QMessageBox.about(self, f"关于 {APP_NAME}", about_text)
        except Exception as e:
            self.logger.error(f"Error showing about dialog: {str(e)}")

