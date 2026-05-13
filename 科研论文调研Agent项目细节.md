## 科研论文调研分析 Agent 项目细节

本项目是基于 **LangGraph + Plan-and-Execute** 的本地化科研调研智能体。全程使用本地 LLM（Qwen3-8B）和本地向量模型（BGE-M3），无需任何外部 API 密钥。

---

### 整体架构

流程由 `graph.py` 中的 LangGraph `StateGraph` 驱动，共 5 个节点：

```
用户查询
   ↓
[plan_node]      reasoning.py     → LLM 分析复杂度，一次性生成完整检索计划（JSON）
   ↓ (有计划)
[execute_node]   graph.py         → 按计划批量调用 RAG / 网络检索，结果写入状态
   ↓
[replan_node]    reasoning.py     → 评估信息充分性，决定是否生成补充查询计划
   ↓ (充分 or 超限)
[summarize_node] summarization.py → 生成 Markdown 报告
   ↓
[render_node]    report_renderer.py → 渲染 HTML，保存到 reports/
```

**共享状态**（`ResearchState`，贯穿所有节点）：

```python
class ResearchState(TypedDict):
    user_query:      str        # 用户原始问题
    planned_actions: List[dict] # 当前待执行动作
    context_items:   List[str]  # 累积的检索结果（跨轮持久）
    iteration:       int        # 已完成的执行轮次
    max_iterations:  int        # 执行上限（默认 3）
    final_report:    str        # Markdown 报告
    html_path:       str        # HTML 文件路径
```

---

### 项目文件结构

```
科研论文分析研究助手/
├── main.py               # 入口：初始化 + 构建图 + CLI
├── graph.py              # LangGraph 状态机（5 节点 + 路由）
├── reasoning.py          # plan() + replan()
├── summarization.py      # generate_report()（纯文本生成）
├── local_llm.py          # 本地 Qwen3-8B 单例（OpenAI 兼容接口）
├── report_renderer.py    # Markdown → HTML 渲染 + ReportRendererSkill
├── tools/
│   ├── rag_retrieval.py  # BGE-M3 + Milvus 混合检索
│   └── web_search.py     # Semantic Scholar / DuckDuckGo
├── data/
│   ├── milvus_rag.db     # Milvus 本地向量数据库
│   └── bm25_model.json   # BM25 语料参数
├── reports/              # HTML 报告输出目录
├── zotero_storage/       # PDF 文献目录（RAG 索引来源）
└── .env                  # 本地模型路径配置
```

---

### 各模块说明

#### `graph.py` — LangGraph 状态机

项目核心。`build_graph()` 接受所有工具和模块实例（依赖注入），在内部定义 5 个节点函数和 2 个路由函数，编译为 `CompiledGraph`：

```python
graph = build_graph(rag_tool, web_tool, renderer, planner, summarizer)
result = graph.invoke(initial_state)
```

路由规则：

| 判断点 | 条件 | 去向 |
|--------|------|------|
| `plan` 之后 | `planned_actions` 非空 | `execute` |
| `plan` 之后 | `planned_actions` 为空（如闲聊） | `END` |
| `replan` 之后 | 有补充查询 且 未超限 | `execute`（继续） |
| `replan` 之后 | 信息充分 或 达到上限 | `summarize` |

---

#### `reasoning.py` — 推理规划

**`plan(user_query)`**：根据问题复杂度自适应生成检索计划，避免简单问题生成冗余子查询：

| 问题类型 | 策略 |
|----------|------|
| 简单（定义/解释） | RAG × 1，不拆子问题，不做网络检索 |
| 中等（方法/对比） | RAG × 1 + 网络检索 × 1 |
| 复杂（综述/趋势） | RAG × 2-3 + 网络检索 × 1-2 |

LLM 强制输出 JSON，示例：

```json
[{"action_name": "RAG检索", "prompts": ["低空交通的定义"]}]
```

**`replan(user_query, context)`**：评估当前上下文充分性，返回补充查询计划或 `null`。

---

#### `tools/rag_retrieval.py` — 本地 RAG 检索

基于 **BGE-M3 密集向量（1024维）+ BM25 稀疏向量** 混合检索，向量库为 Milvus Lite 本地文件：

```
扫描 zotero_storage/ → pdfplumber 提取文本 → 切块（400字/块）
   ↓
BGE-M3 → 密集向量    BM25.fit() → 稀疏向量
   ↓
Milvus Collection（批量写入）
```

检索时用 `WeightedRanker(sparse=0.7, dense=1.0)` 融合两路结果，带 `[1][2]` 引用编号送入 LLM 生成答案。

---

#### `tools/web_search.py` — 网络检索

主引擎 **Semantic Scholar API**（学术数据库，国内可访问），DuckDuckGo 作备用。结果摘要送入 LLM 生成带引用的综合回答。

---

#### `summarization.py` — 报告生成

调用本地 LLM，根据问题类型自适应生成 Markdown 报告（不触发渲染，渲染由 `render_node` 负责）：

| 问题类型 | 输出格式 |
|----------|----------|
| 定义/解释类 | 2-4 句直接回答，引用文献原文 |
| 方法/技术类 | 分点列出，每点附来源 |
| 对比分析类 | 简洁对比表格 |
| 综述调研类 | 现状 → 方法 → 趋势 → 建议 |

---

#### `report_renderer.py` — HTML 渲染

纯 Python 实现 Markdown → HTML 转换（无外部依赖），输出暗色主题精美报告，保存到 `reports/YYYYMMDD_HHMMSS_关键词.html`。`ReportRendererSkill` 类封装 `render(query, markdown)` 接口供图节点调用。

---

#### `local_llm.py` — 本地 LLM

以单例模式加载 Qwen3-8B，提供与 OpenAI SDK 完全兼容的接口，各模块直接调用，切换模型只需改 `.env`。

---

### 环境配置

**`.env` 文件**：

```bash
LLM_MODEL_PATH=/home/ubuntu/桌面/model_download/Qwen3-8B
BGE_MODEL_PATH=/home/ubuntu/桌面/model_download/BGE_M3
ZOTERO_PDF_STORAGE_PATH=/home/ubuntu/桌面/cui/科研论文分析研究助手/zotero_storage
# SEMANTIC_SCHOLAR_API_KEY=your_key  # 可选，提升速率限额
```

---

### 启动与运维命令

```bash
# 交互式问答
python main.py

# 命令行单次查询
python main.py "Transformer 在路径规划中的应用"

# 构建 / 重建向量索引（新增或删除 PDF 后执行）
python main.py --build-index

# 一键启动（含虚拟环境激活）
bash start.sh
```
