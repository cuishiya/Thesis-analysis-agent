"""
科研论文调研分析系统 - 主入口
基于 LangGraph + RAG 架构实现
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入各个模块
from reasoning import ResearchPlanner
from summarization import ResearchSummarizer
from tools.rag_retrieval import RAGRetrieval
from tools.web_search import WebSearch
from report_renderer import ReportRendererSkill
from graph import build_graph


class ResearchPaperSystem:
    """科研论文调研分析系统主类（基于 LangGraph 状态机）"""

    def __init__(self):
        """初始化系统，构建 LangGraph 状态机"""
        print("初始化科研论文调研分析系统...")

        # 初始化所有工具和模块
        self.rag_tool  = RAGRetrieval()
        self.web_tool  = WebSearch()
        self.renderer  = ReportRendererSkill()
        self.planner   = ResearchPlanner()
        self.summarizer = ResearchSummarizer()

        # 构建 LangGraph 图（依赖注入）
        self.graph = build_graph(
            rag_tool   = self.rag_tool,
            web_tool   = self.web_tool,
            renderer   = self.renderer,
            planner    = self.planner,
            summarizer = self.summarizer,
        )

        print("系统初始化完成！")

    def run_research(self, user_query: str, max_iterations: int = 3) -> str:
        """
        执行科研调研分析（通过 LangGraph 图驱动 Plan-and-Execute 流程）

        Args:
            user_query:     用户的调研查询
            max_iterations: 最大反思迭代次数

        Returns:
            Markdown 格式的调研报告
        """
        print(f"\n{'='*60}")
        print(f"开始科研调研分析")
        print(f"用户查询: {user_query}")
        print(f"{'='*60}")

        # 初始状态（每次查询独立，无历史污染）
        initial_state = {
            "user_query":      user_query,
            "planned_actions": [],
            "context_items":   [],
            "iteration":       0,
            "max_iterations":  max_iterations,
            "final_report":    "",
            "html_path":       "",
        }

        result = self.graph.invoke(initial_state)
        return result["final_report"]

    def interactive_mode(self):
        """交互式模式"""
        print("\n" + "="*60)
        print("科研论文调研分析系统 - 交互模式")
        print("="*60)
        print("输入您的科研调研问题，或输入 'exit' 退出\n")

        while True:
            try:
                user_query = input("请输入调研问题: ").strip()

                if user_query.lower() in ['exit', 'quit', '退出']:
                    print("感谢使用科研论文调研分析系统！")
                    break

                if not user_query:
                    print("请输入有效的问题！")
                    continue

                # 执行调研
                report = self.run_research(user_query)

                # 显示报告
                print(f"\n{'='*60}")
                print("调研分析报告")
                print(f"{'='*60}")
                print(report)
                print(f"{'='*60}\n")

            except KeyboardInterrupt:
                print("\n\n感谢使用科研论文调研分析系统！")
                break
            except Exception as e:
                print(f"发生错误: {e}")
                continue

def main():
    """主函数"""
    try:
        # --build-index [pdf目录]：构建或重建向量知识库索引
        if len(sys.argv) > 1 and sys.argv[1] == '--build-index':
            pdf_dir = sys.argv[2] if len(sys.argv) > 2 else None
            system = ResearchPaperSystem()
            system.rag_tool.build_index(pdf_dir)
            return

        # 创建系统实例
        system = ResearchPaperSystem()

        # 检查命令行参数
        if len(sys.argv) > 1:
            # 命令行模式：直接传入查询
            query = ' '.join(sys.argv[1:])
            report = system.run_research(query)
            print(report)
        else:
            # 交互式模式
            system.interactive_mode()

    except Exception as e:
        import traceback
        print(f"系统启动失败: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()