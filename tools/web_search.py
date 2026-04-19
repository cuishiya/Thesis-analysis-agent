"""
网络检索工具 - 搜索最新的科研动态和论文信息
"""

import sys
import os
import requests
import re
import time
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ddgs import DDGS

# 将项目根目录加入路径，以便导入 local_llm
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from local_llm import LocalLLM

class WebSearch:
    """网络检索类，用于搜索最新的科研动态"""

    def __init__(self, api_key: str = None, search_engine: str = "semantic_scholar"):
        """
        初始化网络检索工具

        Args:
            api_key: 搜索API密钥（如果需要）
            search_engine: 搜索引擎类型 ("duckduckgo", "google", "bing")
        """
        self.search_engine = search_engine
        self.api_key = api_key

        # 使用本地模型，model 参数仅作占位
        self.model = "local"
        self.client = LocalLLM()

        print(f"网络检索工具初始化完成 (搜索引擎: {search_engine})")

    def search(self, query: str, num_results: int = 5) -> str:
        """
        执行网络搜索并生成综合回答

        Args:
            query: 搜索查询
            num_results: 返回结果数量

        Returns:
            搜索结果的综合回答
        """
        print(f"开始网络搜索: {query}")

        # 执行搜索
        search_results = self._perform_search(query, num_results)

        if not search_results:
            return "抱歉，未找到相关的网络搜索结果。"

        # 提取搜索结果内容
        search_content = self._format_search_results(search_results)

        # 生成综合回答
        answer = self._generate_answer(query, search_content, search_results)

        return answer

    def _perform_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """
        执行实际的搜索操作

        Args:
            query: 搜索查询
            num_results: 结果数量

        Returns:
            搜索结果列表
        """
        if self.search_engine == "semantic_scholar":
            results = self._semantic_scholar_search(query, num_results)
            if not results:  # 失败时回退 DuckDuckGo
                results = self._duckduckgo_search(query, num_results)
            return results
        elif self.search_engine == "duckduckgo":
            return self._duckduckgo_search(query, num_results)
        elif self.search_engine == "google":
            return self._google_search(query, num_results)
        else:
            return self._semantic_scholar_search(query, num_results)

    def _semantic_scholar_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """
        使用 Semantic Scholar API 搜索学术论文（对中国服务器友好）

        Args:
            query: 搜索查询
            num_results: 结果数量

        Returns:
            搜索结果列表
        """
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                'query': query,
                'limit': num_results,
                'fields': 'title,abstract,year,authors,url'
            }
            headers = {}
            api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
            if api_key:
                headers['x-api-key'] = api_key

            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

            results = []
            for paper in data.get('data', []):
                authors = [a.get('name', '') for a in paper.get('authors', [])[:3]]
                abstract = paper.get('abstract') or ''
                results.append({
                    'title': paper.get('title', ''),
                    'url': paper.get('url', ''),
                    'snippet': f"[{paper.get('year', '')}] {', '.join(authors)}. {abstract[:300]}",
                    'source': 'Semantic Scholar'
                })
            return results

        except Exception as e:
            print(f"Semantic Scholar搜索失败: {e}")
            return []

    def _duckduckgo_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """
        使用DuckDuckGo进行搜索（使用duckduckgo-search库）

        Args:
            query: 搜索查询
            num_results: 结果数量

        Returns:
            搜索结果列表
        """
        try:
            results = []
            with DDGS() as ddgs:
                for item in ddgs.text(query, max_results=num_results):
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('href', ''),
                        'snippet': item.get('body', ''),
                        'source': 'DuckDuckGo'
                    })
            return results[:num_results]

        except Exception as e:
            print(f"DuckDuckGo搜索失败: {e}")
            return []

    def _google_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """
        使用Google进行搜索（需要API密钥）

        Args:
            query: 搜索查询
            num_results: 结果数量

        Returns:
            搜索结果列表
        """
        if not self.api_key:
            print("Google搜索需要API密钥")
            return self._duckduckgo_search(query, num_results)

        try:
            # Google Custom Search API
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.api_key,
                'cx': os.getenv("GOOGLE_SEARCH_ENGINE_ID", ""),  # 搜索引擎ID
                'q': query,
                'num': num_results
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get('items', []):
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'source': 'Google'
                })

            return results

        except Exception as e:
            print(f"Google搜索失败: {e}")
            return []

    def _format_search_results(self, results: List[Dict[str, str]]) -> str:
        """
        格式化搜索结果为文本

        Args:
            results: 搜索结果列表

        Returns:
            格式化的文本
        """
        if not results:
            return "无搜索结果"

        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(f"[{i}] {result.get('title', '未知标题')}")
            formatted.append(f"    网址: {result.get('url', '')}")
            formatted.append(f"    摘要: {result.get('snippet', '')}")
            formatted.append("")

        return "\n".join(formatted)

    def _generate_answer(self, query: str, search_content: str, results: List[Dict[str, str]]) -> str:
        """
        基于搜索结果生成回答

        Args:
            query: 用户查询
            search_content: 格式化的搜索内容
            results: 原始搜索结果

        Returns:
            生成的回答
        """
        prompt = f'''
你是一个专业的科研信息助手。请基于提供的网络搜索结果回答用户的问题。

用户问题: {query}

网络搜索结果:
{search_content}

请按照以下要求回答:
1. 基于搜索结果提供准确、最新的信息
2. 在回答中标注引用来源，格式为 [1], [2] 等
3. 如果搜索结果信息不足，请明确说明
4. 保持客观性和专业性
5. 特别关注科研相关的信息（如论文、会议、技术进展等）
6. 回答要简洁明了，重点突出
'''

        try:
            completion = self.client.chat.completions.create(
                model=self.model,  # 使用配置的模型
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的科研信息助手，擅长搜索和分析最新的科研动态。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1500,
                temperature=0.3
            )

            answer = completion.choices[0].message.content
            return answer

        except Exception as e:
            print(f"生成回答失败: {e}")
            # 返回原始搜索结果
            return f"基于搜索结果找到以下信息:\n\n{search_content}"

    def search_arxiv(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        专门搜索arXiv论文

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            arXiv论文列表
        """
        try:
            # arXiv API
            url = "http://export.arxiv.org/api/query"
            params = {
                'search_query': f'all:{query}',
                'start': 0,
                'max_results': max_results
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            # 解析XML响应
            soup = BeautifulSoup(response.content, 'xml')
            entries = soup.find_all('entry')

            papers = []
            for entry in entries:
                # 提取作者信息
                authors = [author.find('name').text for author in entry.find_all('author')]

                # 提取摘要（移除HTML标签）
                summary = entry.find('summary').text.strip()
                summary = re.sub(r'\s+', ' ', summary)

                papers.append({
                    'title': entry.find('title').text.strip(),
                    'authors': authors,
                    'published': entry.find('published').text,
                    'abstract': summary,
                    'url': entry.find('id').text,
                    'categories': [cat.get('term') for cat in entry.find_all('category')],
                    'source': 'arXiv'
                })

            return papers

        except Exception as e:
            print(f"arXiv搜索失败: {e}")
            return []

    def search_scholar(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        搜索Google Scholar（简化版，通过解析）

        Args:
            query: 搜索查询
            num_results: 结果数量

        Returns:
            学术论文信息列表
        """
        try:
            # 注意：这只是一个简化的实现，实际使用可能需要处理验证码等
            url = "https://scholar.google.com/scholar"
            params = {
                'q': query,
                'hl': 'zh-CN',
                'num': num_results
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code != 200:
                print(f"Google Scholar访问受限，状态码: {response.status_code}")
                return []

            soup = BeautifulSoup(response.content, 'html.parser')
            results = []

            # 解析搜索结果
            for div in soup.find_all('div', class_='gs_ri')[:num_results]:
                title_tag = div.find('h3', class_='gs_rt')
                if title_tag:
                    title = title_tag.get_text()
                    link = title_tag.find('a')['href'] if title_tag.find('a') else ''

                    snippet_tag = div.find('div', class_='gs_rs')
                    snippet = snippet_tag.get_text() if snippet_tag else ''

                    results.append({
                        'title': title,
                        'url': link,
                        'snippet': snippet,
                        'source': 'Google Scholar'
                    })

            return results

        except Exception as e:
            print(f"Google Scholar搜索失败: {e}")
            return []

    def get_latest_conference_papers(self, conference: str, year: int = 2025) -> List[Dict[str, Any]]:
        """
        获取特定会议的最新论文信息

        Args:
            conference: 会议名称（如CVPR, ICML, NeurIPS）
            year: 年份

        Returns:
            论文信息列表
        """
        query = f"{conference} {year} papers accepted"
        arxiv_results = self.search_arxiv(query, max_results=10)

        return arxiv_results