"""
网络检索工具 - 搜索科研论文和学术动态
"""

import re
import requests
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from ddgs import DDGS


class WebSearch:
    """网络检索类：DuckDuckGo 通用搜索 + arXiv 论文搜索"""

    def __init__(self):
        print("网络检索工具初始化完成")

    def search(self, query: str, num_results: int = 5) -> str:
        """执行网络搜索，返回格式化的结果文本"""
        print(f"网络搜索: {query}")

        results = self._duckduckgo_search(query, num_results)
        if results:
            print(f"  → 使用 DuckDuckGo，返回 {len(results)} 条结果")

        if not results:
            return "未找到相关搜索结果。"

        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r['title']}")
            lines.append(f"    来源: {r['url']}")
            lines.append(f"    摘要: {r['snippet']}")
            lines.append("")
        return "\n".join(lines)

    # ── DuckDuckGo ──────────────────────────────────────────────────────────

    def _duckduckgo_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        try:
            results = []
            with DDGS() as ddgs:
                for item in ddgs.text(query, max_results=num_results):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("href", ""),
                        "snippet": item.get("body", ""),
                        "source": "DuckDuckGo",
                    })
            return results[:num_results]
        except Exception as e:
            print(f"DuckDuckGo 搜索失败: {e}")
            return []

    # ── arXiv ───────────────────────────────────────────────────────────────

    def search_arxiv(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """搜索 arXiv 预印本论文"""
        try:
            url = "http://export.arxiv.org/api/query"
            params = {"search_query": f"all:{query}", "start": 0, "max_results": max_results}

            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.content, "xml")
            papers = []
            for entry in soup.find_all("entry"):
                authors = [a.find("name").text for a in entry.find_all("author")]
                summary = re.sub(r"\s+", " ", entry.find("summary").text.strip())
                papers.append({
                    "title": entry.find("title").text.strip(),
                    "authors": authors,
                    "published": entry.find("published").text,
                    "abstract": summary,
                    "url": entry.find("id").text,
                    "categories": [c.get("term") for c in entry.find_all("category")],
                    "source": "arXiv",
                })
            return papers
        except Exception as e:
            print(f"arXiv 搜索失败: {e}")
            return []
