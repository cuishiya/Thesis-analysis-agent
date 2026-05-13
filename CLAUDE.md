# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言偏好

- 使用中文（简体）进行所有交流和说明。

## Python 虚拟环境

- 运行任何 Python 脚本或安装依赖库之前，必须先激活虚拟环境 `cui_rag1`。
- 激活命令：`source ~/cui_rag1/bin/activate`
- 安装依赖：`pip install -r requirements.txt`（在虚拟环境已激活的前提下）

## 常用命令

```bash
# 交互模式运行
source ~/cui_rag1/bin/activate && python main.py

# 单次查询（命令行模式）
source ~/cui_rag1/bin/activate && python main.py "查询内容"

# 重建向量索引（添加新论文后执行）
source ~/cui_rag1/bin/activate && python main.py --build-index
```

## 架构概述

LangGraph + Plan-and-Execute 架构的本地化科研论文调研智能体。全程使用本地 LLM（Qwen3-8B）和本地向量模型（BGE-M3），无需外部 API。

### LangGraph 5 节点工作流（graph.py）

```
plan → execute → replan → summarize → render
           ↑         │
           └─────────┘  (信息不足时重规划，最多 max_iterations 轮)
```

- **plan_node**：分析问题复杂度，一次性生成完整检索计划（简单/中等/复杂三级策略）
- **execute_node**：按计划批量调用 RAG 或网络检索工具，累积结果到 `context_items`
- **replan_node**：评估信息充分性，决定生成补充查询或进入总结
- **summarize_node**：根据问题类型生成不同风格的 Markdown 报告
- **render_node**：纯 Python 实现 Markdown→HTML 转换，学术风格暗色主题

### 共享状态（ResearchState）

`user_query` → `planned_actions` → `context_items`（跨轮累积）→ `iteration`/`max_iterations` → `final_report` → `html_path`

### 核心模块

| 文件 | 职责 |
|------|------|
| `main.py` | 入口，初始化 LLM/工具/图，支持交互模式和 `--build-index` |
| `graph.py` | LangGraph 状态机定义，节点连接与路由逻辑 |
| `reasoning.py` | 推理规划，LLM 强制输出 JSON 格式的检索计划 |
| `summarization.py` | 报告生成，按问题类型（定义/方法/对比/综述）自适应输出 |
| `local_llm.py` | 本地 LLM 单例封装，OpenAI 兼容接口 |
| `report_renderer.py` | HTML 渲染，无外部 CSS/JS 依赖 |
| `tools/rag_retrieval.py` | RAG 混合检索：BGE-M3 密集向量 + BM25 稀疏向量，加权融合（sparse=0.7, dense=1.0） |
| `tools/web_search.py` | 网络检索：Semantic Scholar API 优先，DuckDuckGo 备选，支持 arXiv 专项搜索 |

### 数据目录

- `zotero_storage/`：Zotero 管理的 PDF 文献（子目录结构）
- `data/milvus_rag.db`：Milvus 本地向量数据库
- `data/bm25_model.json`：BM25 索引参数
- `reports/`：生成的 HTML 报告（时间戳命名）

## 模型切换

修改 `.env` 中的 `LLM_MODEL_PATH` 和 `BGE_MODEL_PATH` 即可切换模型，代码无需改动。模型文件位于 `/home/ubuntu/桌面/model_download/`。
