import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from views.main_window import MainWindow
from utils.config_manager import ConfigManager
from utils.logger import LogManager

# 获取当前脚本的父目录的父目录 (即项目根目录)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 将项目根目录添加到 Python 的 sys.path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def setup_environment():
    """设置运行环境"""
    try:
        # 创建必要的目录
        required_dirs = [
            'logs',
            'resources',
            'resources/icons',
            'resources/styles',
            'auto_saves'
        ]
        
        for directory in required_dirs:
            if not os.path.exists(directory):
                os.makedirs(directory)
                
        # 设置应用程序信息
        QApplication.setApplicationName("文件夹大小扫描器")
        QApplication.setApplicationVersion("1.0.0")
        QApplication.setOrganizationName("YourCompany")
        QApplication.setOrganizationDomain("yourcompany.com")
        
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
        style_file = "resources/styles/main.qss"
        if not os.path.exists(style_file):
            # 如果样式文件不存在，创建默认样式文件
            from shutil import copyfile
            default_style = "resources/styles.qss"
            if os.path.exists(default_style):
                copyfile(default_style, style_file)
            else:
                print(f"Warning: Default style file not found: {default_style}")
        
        # 检查图标文件
        required_icons = [
            'folder', 'play', 'stop', 'calculate', 
            'export', 'backup'
        ]
        
        icon_dir = "resources/icons"
        missing_icons = [
            icon for icon in required_icons 
            if not os.path.exists(f"{icon_dir}/{icon}.png")
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