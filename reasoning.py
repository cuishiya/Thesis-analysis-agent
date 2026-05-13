"""
规划模块 - 理解用户科研调研意图，制定调研计划
"""

import json
import re
from typing import List, Dict, Any, Optional
from local_llm import LocalLLM

class ResearchPlanner:
    """科研调研规划类"""

    def __init__(self):
        """
        初始化规划器，使用本地 DeepSeek-R1-Distill-Qwen-7B 模型
        """
        # 使用本地模型，model 参数仅作占位
        self.model = "local"
        self.client = LocalLLM()

    def _call_llm(self, prompt: str, response_format: Optional[Dict] = None) -> str:
        """
        调用大语言模型

        Args:
            prompt: 提示词
            response_format: 响应格式（如 {"type": "json_object"}）

        Returns:
            模型响应
        """
        kwargs = {
            "model": self.model,  # 根据配置选择模型
            "messages": [{"role": "user", "content": prompt}]
        }

        if response_format:
            kwargs["response_format"] = response_format

        completion = self.client.chat.completions.create(**kwargs)
        return completion.choices[0].message.content

    def _extract_json(self, text: str) -> Optional[Dict]:
        """
        从文本中提取JSON

        Args:
            text: 包含JSON的文本

        Returns:
            解析后的JSON字典，如果解析失败则返回None
        """
        try:
            # 尝试直接解析
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            json_pattern = r'\[[\s\S]*\]'
            match = re.search(json_pattern, text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    return None
            return None

    def plan(self, user_query: str) -> List[Dict[str, Any]]:
        """
        制定初始调研计划

        Args:
            user_query: 用户的调研查询

        Returns:
            动作列表，每个动作包含action_name和prompt
        """
        prompt = f'''
你是一个科研调研规划助手。根据用户问题的复杂度，制定最精简有效的检索计划。

## 用户问题
{user_query}

## 可用工具
- **RAG检索**: 检索本地Zotero文献库（论文全文、定义、方法等）
- **网络检索**: 搜索最新学术论文（适合"最新进展"、"当前趋势"类问题）

## 计划规则（重要）

**简单问题**（定义、解释、是什么、某个概念/方法）：
- 只用 RAG检索，1-2个查询，直接查原始问题即可
- 不拆解子问题，不做网络检索
- 示例：
  [{{"action_name": "RAG检索", "prompts": ["{user_query}"]}}]

**中等问题**（某领域的方法/技术对比、某篇论文的内容）：
- RAG检索 1 个查询 + 网络检索 1 个查询
- 示例：
  [
    {{"action_name": "RAG检索", "prompts": ["{user_query}"]}},
    {{"action_name": "网络检索", "prompts": ["{user_query}"]}}
  ]

**复杂调研**（某领域全面综述、研究现状与趋势）：
- RAG检索 2-3 个查询 + 网络检索 1-2 个查询
- 示例：
  [
    {{"action_name": "RAG检索", "prompts": ["{user_query}", "该领域经典方法"]}},
    {{"action_name": "网络检索", "prompts": ["{user_query} 2025最新进展"]}}
  ]

## 输出要求
- 只输出 JSON，不输出任何解释文字
- 如果是闲聊/问候，输出: null
- 查询数量宁少勿多，聚焦用户真正想知道的内容
'''

        try:
            response = self._call_llm(prompt, response_format={"type": "json_object"})
            plan_data = self._extract_json(response)

            if plan_data and isinstance(plan_data, list):
                # 转换格式，使每个action_name只对应一个prompt
                adjusted_plan = []
                for item in plan_data:
                    action_name = item.get('action_name', '')
                    prompts = item.get('prompts', [])

                    for prompt in prompts:
                        adjusted_plan.append({
                            'action_name': action_name,
                            'prompt': prompt
                        })
                return adjusted_plan

            return []

        except Exception as e:
            print(f"规划过程出错: {e}")
            return []

    def replan(self, user_query: str, context: str) -> List[Dict[str, Any]]:
        """
        重规划：评估已有信息充分性，决定是否生成补充查询计划

        Args:
            user_query: 原始用户查询
            context: 当前已获取的上下文信息

        Returns:
            需要补充的动作列表，如果不需要则返回空列表
        """
        prompt = f'''
你是一个专业的科研调研分析助手。你的任务是：

1. 回顾原始查询: {user_query}
2. 分析已有的信息
3. 判断是否需要更多信息来完善调研

## 已有信息
{context}

## 判断标准

需要更多信息的情况：
- 核心理论基础不够清晰
- 缺少代表性论文的具体方法描述
- 没有涵盖该领域的主要研究方向
- 缺少最新的研究进展
- 没有对比不同的技术路线
- 缺少实际应用案例

不需要更多信息的情况：
- 已经涵盖了核心理论和经典方法
- 有足够多的代表性论文
- 已经了解了最新进展和趋势
- 信息足够全面和深入

## 输出格式

如果需要更多信息，输出JSON格式的补充计划：
[
  {{
    "action_name": "RAG检索"或"网络检索",
    "prompts": ["需要补充查询的问题"]
  }}
]

如果不需要更多信息，输出: null

## 重要限制

- 最多补充3个问题
- 问题应该具体且有针对性
- 避免重复已有的查询
- 专注于填补信息空白

只输出JSON部分，不要包含任何其他文字。
'''

        try:
            response = self._call_llm(prompt, response_format={"type": "json_object"})
            plan_data = self._extract_json(response)

            if plan_data and isinstance(plan_data, list):
                adjusted_plan = []
                for item in plan_data:
                    action_name = item.get('action_name', '')
                    prompts = item.get('prompts', [])
                    for p in prompts:
                        adjusted_plan.append({
                            'action_name': action_name,
                            'prompt': p
                        })
                return adjusted_plan

            return []

        except Exception as e:
            print(f"重规划出错: {e}")
            return []