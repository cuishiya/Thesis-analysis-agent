# 科研论文调研分析助手

基于 **LangGraph + Plan-and-Execute** 架构的本地化科研论文调研智能体。全程使用本地 LLM 和本地向量模型，无需外部 API，数据完全私有。

## 功能特性

- **智能调研规划**：自动分析问题复杂度，制定多轮检索策略（简单/中等/复杂三级）
- **混合检索**：BGE-M3 密集向量 + BM25 稀疏向量加权融合，兼顾语义匹配和关键词精确匹配
- **网络检索补充**：Semantic Scholar API 优先、DuckDuckGo 备选，支持 arXiv 专项搜索
- **迭代反思**：信息不足时自动重规划，最多 3 轮迭代，确保调研充分性
- **自适应报告**：根据问题类型（定义/方法/对比/综述）自动选择不同报告风格
- **HTML 报告渲染**：学术风格暗色主题，无外部 CSS/JS 依赖
- **完全本地化**：本地 LLM（Qwen3-8B）+ 本地向量模型（BGE-M3），零外部 API 调用

## 系统架构

```
用户问题
   │
   ▼
┌──────┐    ┌─────────┐    ┌─────────┐
│ plan │───▶│ execute │───▶│ replan  │
└──────┘    └─────────┘    └────┬────┘
                               │
                    信息不足，回到 execute
                    信息充分，进入总结
                               │
                               ▼
                      ┌────────────┐    ┌────────┐
                      │ summarize  │───▶│ render │───▶ HTML 报告
                      └────────────┘    └────────┘
```

## 项目结构

```
科研论文分析研究助手/
├── main.py               # 入口，支持交互模式和命令行模式
├── graph.py              # LangGraph 状态机，5 节点工作流定义
├── reasoning.py          # 推理规划，LLM 强制输出 JSON 检索计划
├── summarization.py      # 报告生成，按问题类型自适应输出
├── local_llm.py          # 本地 LLM 单例封装，OpenAI 兼容接口
├── report_renderer.py    # HTML 渲染，学术风格暗色主题
├── tools/
│   ├── rag_retrieval.py  # RAG 混合检索（BGE-M3 + BM25）
│   └── web_search.py     # 网络检索（Semantic Scholar + DuckDuckGo）
├── data/                 # 向量数据库和 BM25 索引（自动生成）
├── zotero_storage/       # Zotero 管理的 PDF 文献
├── reports/              # 生成的 HTML 报告
├── .env.example          # 环境变量模板
└── requirements.txt      # Python 依赖
```

## 环境要求

- Python 3.10+
- CUDA（GPU 推理，推荐显存 ≥ 8GB）
- 本地 LLM 模型文件（如 Qwen3-8B）
- 本地向量模型文件（如 BGE-M3）

## 快速开始

### 1. 克隆项目并安装依赖

```bash
git clone <仓库地址>
cd 科研论文分析研究助手

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，设置模型路径：

```env
# LLM 模型路径
LLM_MODEL_PATH=/path/to/your/Qwen3-8B

# 向量模型路径
BGE_MODEL_PATH=/path/to/your/BGE_M3

# Zotero PDF 存储路径
ZOTERO_PDF_STORAGE_PATH=/path/to/your/zotero/storage
```

### 3. 构建向量索引

将 PDF 论文放入 `zotero_storage/` 目录后，执行：

```bash
python main.py --build-index
```

也可指定自定义 PDF 目录：

```bash
python main.py --build-index /path/to/pdf/folder
```

### 4. 开始使用

**交互模式**（推荐）：

```bash
python main.py
```

**命令行单次查询**：

```bash
python main.py "低空交通调度有什么常用方法？"
```

## 使用示例

```
请输入调研问题: Transformer 的最新进展是什么？

【规划节点】分析调研意图，制定检索计划...
  生成 4 个动作

【执行节点】执行 4 个动作（第 1 轮）...
  [1/4] RAG检索: Transformer 架构最新变体
  [2/4] 网络检索: Transformer 2024 最新论文
  [3/4] RAG检索: 注意力机制改进方法
  [4/4] 网络检索: arXiv Transformer recent advances

【重规划节点】评估信息充分性...
  信息充分，无需补充

【总结节点】生成调研报告...
【渲染节点】生成 HTML 报告...
报告已保存: reports/20260509_202708_transformer的最新进展.html
```

## 模型切换

修改 `.env` 中的模型路径即可切换，代码无需任何改动：

```env
# 可选 LLM 模型
LLM_MODEL_PATH=/path/to/Qwen3-4B
LLM_MODEL_PATH=/path/to/Llama3-8B
LLM_MODEL_PATH=/path/to/DeepSeek-R1-Distill-Qwen-7B
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 工作流引擎 | LangGraph |
| LLM 推理 | transformers + vLLM（OpenAI 兼容接口） |
| 向量模型 | BGE-M3（BAAI） |
| 向量数据库 | Milvus Lite（本地模式） |
| 稀疏检索 | BM25 |
| PDF 解析 | pdfplumber |
| 网络检索 | Semantic Scholar API + DuckDuckGo |
