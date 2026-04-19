@echo off
chcp 65001 >nul
echo ========================================
echo 科研论文调研分析系统 - 快速启动
echo ========================================
echo.

REM 检查conda是否安装
conda --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到conda，请先安装Anaconda或Miniconda
    pause
    exit /b 1
)

REM 检查llm_env环境是否存在
conda env list | findstr /C:"llm_env" >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到llm_env环境，请先创建: conda create -n llm_env python=3.11
    pause
    exit /b 1
)

REM 检查环境变量文件
if not exist ".env" (
    echo.
    echo ========================================
    echo 首次运行需要配置API密钥
    echo ========================================
    echo.
    echo 请在 .env 文件中配置以下内容:
    echo DASHSCOPE_API_KEY=your_dashscope_api_key_here
    echo OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
    echo.
    echo 正在创建 .env 文件...
    copy .env.example .env >nul
    echo.
    echo 请编辑 .env 文件，填入正确的API密钥后重新运行
    echo.
    pause
    exit /b 0
)

REM 启动系统
echo.
echo 启动科研论文调研分析系统...
echo 使用环境: llm_env
echo.
conda run -n llm_env python main.py

pause