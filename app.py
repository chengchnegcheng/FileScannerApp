import sys
import os
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from views.main_window import MainWindow
from utils.config_manager import ConfigManager
from utils.logger import LogManager
from utils.path_utils import get_app_data_dir, get_resource_path, get_runtime_base_dir

def setup_environment():
    """设置运行环境"""
    try:
        runtime_base_dir = get_runtime_base_dir()
        app_data_dir = get_app_data_dir()

        # 创建必要的目录
        required_dirs = [
            app_data_dir,
            app_data_dir / 'logs',
            app_data_dir / 'auto_saves',
            runtime_base_dir / 'resources',
            runtime_base_dir / 'resources/icons',
            runtime_base_dir / 'resources/styles',
        ]
        
        for directory in required_dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)
                
        # 设置应用程序信息
        QApplication.setApplicationName("文件夹大小扫描器")
        QApplication.setApplicationVersion("1.0.0")
        QApplication.setOrganizationName("FileScanner")
        QApplication.setOrganizationDomain("filescanner.local")
        
        # 设置高DPI支持
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        
    except Exception as e:
        print(f"Error setting up environment: {str(e)}")
        sys.exit(1)

def check_resources():
    """检查必要的资源文件"""
    try:
        # 检查样式文件
        style_file = get_resource_path("resources/styles/main.qss")
        if not style_file.exists():
            print(f"Warning: Style file not found: {style_file}")
        
        # 检查图标文件
        required_icons = [
            'folder', 'play', 'stop', 'calculate', 
            'export', 'backup'
        ]
        
        icon_dir = get_resource_path("resources/icons")
        missing_icons = [
            icon for icon in required_icons 
            if not (icon_dir / f"{icon}.png").exists()
        ]
        
        if missing_icons:
            print(f"Warning: Missing icons: {', '.join(missing_icons)}")
            
    except Exception as e:
        print(f"Error checking resources: {str(e)}")

def main():
    """主函数"""
    try:
        # 设置运行环境
        setup_environment()
        
        # 检查资源
        check_resources()
        
        # 创建应用程序实例
        app = QApplication(sys.argv)

        app_icon = get_resource_path("resources/icons/app.png")
        if app_icon.exists():
            app.setWindowIcon(QIcon(str(app_icon)))
        
        # 初始化配置管理器
        config = ConfigManager()
        
        # 初始化日志管理器
        LogManager()
        
        # 创建并显示主窗口
        window = MainWindow(config)
        window.show()
        
        # 启动应用程序
        sys.exit(app.exec_())
        
    except Exception as e:
        logging.critical(f"Application failed to start: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 
