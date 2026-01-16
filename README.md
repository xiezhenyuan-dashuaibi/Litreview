# litreview

AI 文献综述生成工具（FastAPI 后端 + React/Vite 前端）。

本 README 面向“从 GitHub 克隆后在 Windows 上用 cmd 跑起来”的使用者：包含 Git/Python/Node(npm) 安装、依赖构建、前端构建、配置与启动。

重要提示：本项目目前仅在 Windows 10/11 上适配与测试。启动脚本（.bat）以及部分系统能力（如弹出目录选择对话框）依赖 Windows 组件，macOS/Linux 暂不可用。

## 1. 前置软件（一次性安装）
打开“命令提示符（cmd）”执行以下检查：

```bat
git --version
python --version
node -v
npm -v
```

如果缺任意一项，建议用 winget 安装（Win10/11 通常自带）：

```bat
winget --version
winget install -e --id Git.Git
winget install -e --id Python.Python.3.11
winget install -e --id OpenJS.NodeJS.LTS
```

安装完成后请重新打开一个新的 cmd 窗口，再次执行版本检查。

## 2. 克隆仓库

```bat
git clone <你的仓库地址>
cd litreview
```

## 3. 后端：创建虚拟环境 + 安装依赖

```bat
cd /d C:\path\to\litreview
python -m venv .venv
.venv\Scripts\python.exe -m pip install -U pip setuptools wheel
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .
```


## 4. 前端：安装依赖 + 构建

```bat
cd /d C:\path\to\litreview\frontend
npm install
```

生产构建（生成 `frontend\dist`）：

```bat
cd /d C:\path\to\litreview\frontend
set NODE_OPTIONS=--max-old-space-size=4096
npm run build
```

## 5. 启动

简单方案：直接在文件夹中双击“start_litreview.bat”

### 5.1 Prod（推荐：一个进程，后端 8001 托管前端 dist）

```bat
cd /d C:\path\to\litreview
start_litreview.bat prod
```

访问： http://127.0.0.1:8001/

### 5.2 Dev（开发调试：两个进程，前端 3000 + 后端 8001）

```bat
cd /d C:\path\to\litreview
start_litreview.bat dev
```

访问： http://127.0.0.1:3000/


