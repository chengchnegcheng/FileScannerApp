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
from utils.path_utils import get_app_data_dir, get_resource_path

def setup_environment():
    """设置运行环境"""
    try:
        app_data_dir = get_app_data_dir()

        # 创建必要的目录
        required_dirs = [
            app_data_dir,
            app_data_dir / "logs",
            app_data_dir / "auto_saves",
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

def main():
    """主函数"""
    try:
        # 设置运行环境
        setup_environment()
        
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
