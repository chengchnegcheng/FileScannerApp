# 文件夹大小扫描器（File Scanner）

一个基于 `PyQt5` 的 Windows 桌面工具，用于快速扫描目录下的一级文件夹，统计文件数量和占用空间，并支持导出与备份操作。

## 功能特性

- 扫描指定目录下的一级文件夹
- 实时显示扫描、计算、备份状态
- 支持导出选中结果到 Excel
- 支持把选中的文件夹备份到目标目录
- 提供最近目录、右键菜单、拖放目录等便捷操作
- 自动保存最近一次扫描结果
- 现代化桌面界面与统一图标风格

## 运行环境

- Windows 10 / 11
- Python 3.9+

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动方式

```bash
python app.py
```

## 使用说明

1. 点击 `选择目录` 选择要扫描的目录，或直接把目录拖到主界面
2. 点击 `开始扫描` 加载一级文件夹列表
3. 勾选需要处理的文件夹
4. 点击 `计算大小` 获取文件夹大小和文件数
5. 点击 `导出结果` 导出选中结果到 Excel
6. 点击 `备份目录` 将选中的文件夹复制到目标目录

## 项目结构

```text
FileScannerApp/
├── app.py
├── models/
├── services/
├── utils/
├── viewmodels/
├── views/
├── workers/
├── resources/
│   ├── icons/
│   └── styles/
├── Docs/
└── requirements.txt
```

## 主要依赖

- `PyQt5`：桌面界面
- `pandas`：导出表格数据
- `openpyxl`：写入 Excel
- `psutil`：显示 CPU / 内存使用情况

## 构建可执行文件

```bash
pyinstaller app.spec
```

## 日志与配置

- 日志目录：`logs/`
- 自动保存目录：`auto_saves/`
- 用户配置文件：`config.json`

## 当前版本说明

当前版本已包含以下改进：

- 统一资源路径与日志初始化逻辑
- 修复备份进度语义
- 改进停止操作与按钮状态控制
- 优化主界面、菜单、弹窗和图标风格

## License

MIT


## 发布构建

```powershell
# 仅构建 EXE（会先运行测试）
./scripts/build_release.ps1

# 构建 EXE 并尝试生成安装包（需安装 Inno Setup 的 iscc）
./scripts/build_release.ps1 -BuildInstaller
```

- 可执行文件输出：`dist/FileScanner_Win11.exe`
- 安装脚本：`installer/FileScanner_Win11.iss`
- 一键脚本：`scripts/build_release.ps1`
