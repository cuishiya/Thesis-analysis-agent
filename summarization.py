"""
总结模块 - 调用本地 LLM 生成科研调研报告（Markdown 文本）
HTML 渲染由 LangGraph 的 render_node 负责，此模块只负责生成内容。
"""

from local_llm import LocalLLM


class ResearchSummarizer:
    """科研调研总结类"""

    def __init__(self):
        self.model = "local"
        self.client = LocalLLM()

    def _build_prompt(self, user_query: str, context: str) -> str:
        """构建报告生成 Prompt"""
        return f'''
你是一个专业的科研助手。请根据用户的问题和检索到的信息，给出最合适的回答。

## 用户问题
{user_query}

## 检索到的信息
{context}

## 回答规则（严格遵守）

**判断问题类型，选择对应格式：**

1. **定义/解释类**（"X是什么"、"定义"、"概念"）
   → 直接给出定义，2-4句话，引用文献中的具体表述，不需要章节标题

2. **方法/技术类**（"如何做"、"算法"、"方法有哪些"）
   → 分点列出主要方法，每点1-3句描述，附来源文献

3. **对比分析类**（"区别"、"对比"、"优缺点"）
   → 简洁对比，可以用表格，聚焦差异点

4. **综述调研类**（"研究现状"、"综述"、"发展趋势"）
   → 结构化报告：研究现状 → 主要方法 → 趋势与建议

## 重要原则
- 直接回答问题，不要凑字数
- 只引用检索信息中实际存在的内容，不编造
- 如果检索信息不足以回答问题，直接说明"文献中未找到直接答案"并给出已有线索
- 不强制套用固定章节模板
'''

    def generate_report(self, user_query: str, context: str) -> str:
        """
        生成 Markdown 格式调研报告（纯文本输出，不触发渲染）

        Args:
            user_query: 用户原始查询
            context:    所有检索结果拼接的上下文

        Returns:
            Markdown 格式报告字符串
        """
        prompt = self._build_prompt(user_query, context)
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的科研调研分析专家，擅长总结和分析学术研究进展。"},
                    {"role": "user",   "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            return completion.choices[0].message.content
        except Exception as e:
            return self._fallback_report(user_query, context)

    def _fallback_report(self, user_query: str, context: str) -> str:
        """LLM 调用失败时的简化版报告"""
        return f"# {user_query}\n\n{context}\n\n*（LLM 调用失败，以上为原始检索内容）*"