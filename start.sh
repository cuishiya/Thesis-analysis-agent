#!/bin/bash
echo "========================================"
echo " 科研论文调研分析系统 - 快速启动"
echo "========================================"
echo ""

# 检查 conda 是否安装
if ! command -v conda &> /dev/null; then
    echo "错误: 未找到 conda，请先安装 Anaconda 或 Miniconda"
    exit 1
fi

# 检查 cui_rag1 环境是否存在
if ! conda env list | grep -q "cui_rag1"; then
    echo "错误: 未找到 cui_rag1 环境，请先创建:"
    echo "  conda create -n cui_rag1 python=3.11"
    exit 1
fi

# 检查 .env 文件
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo ""
    echo "========================================"
    echo " 首次运行：正在创建 .env 配置文件"
    echo "========================================"
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo ""
    echo "已生成 .env 文件，请确认以下配置正确后重新运行："
    echo "  LLM_MODEL_PATH      本地 LLM 模型路径"
    echo "  BGE_MODEL_PATH      本地 BGE-M3 模型路径"
    echo "  ZOTERO_PDF_STORAGE_PATH  Zotero PDF 目录路径"
    echo ""
    exit 0
fi

# 启动系统
echo ""
echo "启动科研论文调研分析系统..."
echo "使用环境: cui_rag1"
echo ""
conda run -n cui_rag1 python "$SCRIPT_DIR/main.py"
