# 科研论文调研分析系统

基于 **Agent + RAG 架构**的智能科研调研分析系统，帮助研究人员快速分析学术领域的热点、文献和发展趋势。

## 功能特点

### 1. 智能规划模块
- 理解自然语言科研调研意图
- 自动选择合适的检索工具（RAG/网络搜索）
- 智能拆解复杂调研任务
- 支持自我反思和迭代优化

### 2. 多源检索工具
- **RAG检索**: 基于本地Zotero文献库的深度检索
  - 支持语义搜索
  - 检索论文标题、摘要、引用关系
  - 智能相关性排序

- **网络检索**: 补充最新科研动态
  - 集成多个搜索引擎
  - 专门支持arXiv论文搜索
  - 获取顶会最新信息

### 3. 记忆管理模块
- 持久化存储调研上下文
- 支持多轮对话和回溯
- 自动保存会话记录
- 提供历史调研加载

### 4. 智能执行模块
- 自动调用检索工具
- 支持批量任务执行
- 错误处理和重试机制
- 执行进度追踪

### 5. 报告生成模块
- 生成结构化Markdown报告
- 包含热点总结、文献清单、趋势分析
- 支持关键点提取
- 自动生成参考文献

## 项目结构

```
科研论文调研分析系统/
├── main.py                      # 项目主入口
├── planning.py                  # 规划模块
├── memory.py                    # 记忆管理模块
├── execution.py                 # 执行模块
├── summarization.py             # 总结模块
├── requirements.txt             # 依赖清单
├── .env.example                 # 环境变量示例
├── tools/                       # 工具模块
│   ├── rag_retrieval.py        # RAG检索工具
│   └── web_search.py           # 网络检索工具
├── memory/                      # 记忆存储目录
└── README.md                    # 项目说明文档
```

## 安装步骤

### 1. 环境要求
- Python 3.8+
- pip
- Zotero（可选，用于本地文献管理）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并配置相关参数：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的API密钥：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 4. 配置Zotero数据库（可选）

如果你有Zotero文献库，可以在 `.env` 文件中配置路径：

```env
# 只需要指定Zotero目录路径，系统会自动找到数据库文件
ZOTERO_DB_PATH=C:\Users\YourName\Zotero
ZOTERO_PDF_STORAGE_PATH=C:\Users\YourName\Zotero\storage
```

**Windows用户示例**:
```env
ZOTERO_DB_PATH=C:\Users\Administrator\Zotero
ZOTERO_PDF_STORAGE_PATH=C:\Users\Administrator\Zotero\storage
```

**注意**: 如果不配置，系统会尝试自动检测默认路径。

## 使用方法

### 交互式模式

直接运行主程序：

```bash
python main.py
```

然后输入你的科研调研问题，例如：

```
请输入调研问题: 分析计算机视觉领域2025年的研究热点
```

### 命令行模式

```bash
python main.py "分析大模型在医疗影像应用的最新进展"
```

### 编程接口

```python
from main import ResearchPaperSystem

# 创建系统实例
system = ResearchPaperSystem()

# 执行调研
user_query = "分析深度学习在自然语言处理的应用"
report = system.run_research(user_query)

# 保存报告
with open("research_report.md", "w", encoding="utf-8") as f:
    f.write(report)
```

## 使用示例

### 示例1：领域热点分析

```python
system = ResearchPaperSystem()
report = system.run_research("分析强化学习在机器人控制领域的最新研究热点")
print(report)
```

### 示例2：特定技术调研

```python
system = ResearchPaperSystem()
report = system.run_research("Transformer模型在时间序列预测中的应用和发展")
```

### 示例3：对比分析

```python
system = ResearchPaperSystem()
report = system.run_research("对比CNN和Transformer在图像分类任务中的优劣势")
```

## 模块详解

### 规划模块 (planning.py)

负责理解用户意图和制定调研计划：

- 意图识别：分析用户查询的科研目标
- 工具选择：根据查询类型选择RAG或网络搜索
- 任务拆解：将复杂问题分解为具体步骤
- 反思优化：基于已有信息判断是否需要补充

### 记忆模块 (memory.py)

管理调研过程中的上下文：

- 查询记录：保存用户的所有查询
- 动作追踪：记录执行的每一个检索动作
- 结果存储：保存检索到的论文和信息
- 结论管理：存储中间分析结论
- 会话持久化：支持保存和加载历史会话

### 执行模块 (execution.py)

协调工具调用和任务执行：

- 动作调度：按计划执行检索任务
- 工具调用：调用RAG或网络搜索工具
- 结果处理：格式化和存储执行结果
- 错误处理：处理执行过程中的异常
- 统计分析：提供执行统计信息

### 总结模块 (summarization.py)

生成结构化的调研报告：

- 热点总结：提炼研究领域的前沿方向
- 文献整理：整理核心论文和重要文献
- 方法分析：分析主要技术方法
- 趋势预测：预测未来发展方向
- 建议提供：给出具体的研究建议

### RAG检索工具 (tools/rag_retrieval.py)

基于本地Zotero数据库的论文检索：

- 数据库连接：连接Zotero SQLite数据库
- 多字段搜索：在标题、摘要、作者中检索
- 语义排序：使用LLM进行相关性排序
- 详情获取：获取论文的完整元数据
- 统计信息：提供文献库统计

### 网络检索工具 (tools/web_search.py)

多引擎网络搜索：

- 多引擎支持：DuckDuckGo、Google等
- arXiv专项：专门搜索学术预印本
- Scholar搜索：Google学术论文检索
- 会议信息：获取顶会最新论文
- 结果综合：智能整合多个搜索结果

## 高级功能

### 自定义工具

你可以添加自定义的检索工具：

```python
from execution import ResearchExecutor

class CustomSearchTool:
    def search(self, query: str) -> str:
        # 实现你的搜索逻辑
        return "搜索结果"

# 在初始化时使用
system = ResearchPaperSystem()
system.executor.custom_tool = CustomSearchTool()
```

### 批量调研

```python
queries = [
    "计算机视觉领域热点",
    "自然语言处理进展",
    "强化学习应用"
]

for query in queries:
    report = system.run_research(query)
    # 保存报告
    filename = f"report_{query.replace(' ', '_')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)
```

### 会话管理

```python
# 保存会话
system.memory.save_session("my_research_session.json")

# 加载会话
system.memory.load_session("my_research_session.json")

# 查看会话摘要
summary = system.memory.get_session_summary()
print(summary)
```

## 常见问题

### Q: Zotero数据库找不到怎么办？

A: 系统会自动检测常见的Zotero安装路径。如果找不到，可以在 `.env` 文件中手动指定路径，或者不使用Zotero，仅使用网络检索功能。

### Q: API调用失败怎么办？

A: 请检查：
1. API密钥是否正确配置
2. 网络连接是否正常
3. API额度是否充足
4. BASE_URL是否正确

### Q: 如何提高检索质量？

A: 可以：
1. 优化查询表述，使用更具体的学术术语
2. 增加Zotero文献库的论文数量
3. 调整检索的迭代次数
4. 使用更专业的查询词汇

### Q: 支持哪些语言？

A: 系统主要针对中文学术环境优化，但也能处理英文查询和英文文献。

## 技术栈

- **语言**: Python 3.8+
- **LLM**: OpenAI GPT-4o / DeepSeek-R1
- **向量数据库**: Milvus (可选)
- **文献管理**: Zotero
- **文档处理**: LlamaParse, PyPDF2
- **网络搜索**: Requests, BeautifulSoup

## 性能优化建议

1. **缓存机制**: 启用本地缓存减少重复检索
2. **批量处理**: 使用批量接口减少API调用
3. **并发控制**: 合理设置并发数避免API限流
4. **数据库优化**: 定期清理和优化Zotero数据库

## 未来计划

- [ ] 支持更多文献管理软件（Mendeley, EndNote）
- [ ] 添加可视化分析功能
- [ ] 支持多语言界面
- [ ] 集成更多学术数据库（Web of Science, IEEE Xplore）
- [ ] 添加协作功能
- [ ] 开发Web界面

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交GitHub Issue
- 发送邮件至项目维护者

## 致谢

感谢开源社区的贡献，特别是以下项目：

- LlamaIndex
- Milvus
- OpenAI
- Zotero

---

**注意**: 本系统仅供学术研究使用，请遵守相关API的使用条款和学术规范。