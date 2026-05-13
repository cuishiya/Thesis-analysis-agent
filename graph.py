"""
LangGraph 状态机 - 科研调研 Plan-and-Execute 图
节点：plan → execute → replan → summarize → render
"""

from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END


# ─── 共享状态定义 ──────────────────────────────────────────────────────────────

class ResearchState(TypedDict):
    user_query: str               # 用户原始问题
    planned_actions: List[dict]   # 当前待执行动作列表（每轮由 plan/replan 填充）
    context_items: List[str]      # 累积的检索结果文本（跨轮持久化）
    iteration: int                # 已完成的执行轮次
    max_iterations: int           # 最大执行轮次上限
    final_report: str             # 总结节点生成的 Markdown 报告
    html_path: str                # 渲染节点输出的 HTML 文件路径


# ─── 图构建函数（依赖注入，避免全局单例）────────────────────────────────────────

def build_graph(rag_tool, web_tool, renderer, planner, summarizer):
    """
    构建并编译科研调研 Plan-and-Execute 状态机。

    流程：plan(整体规划) → execute(批量执行) → replan(评估+补充规划)
          → 不充分则回到 execute，充分则进入 summarize → render

    Args:
        rag_tool:    RAGRetrieval 实例
        web_tool:    WebSearch 实例
        renderer:    ReportRendererSkill 实例
        planner:     ResearchPlanner 实例
        summarizer:  ResearchSummarizer 实例

    Returns:
        已编译的 CompiledGraph，调用 .invoke(initial_state) 执行
    """

    # ── 节点函数 ──────────────────────────────────────────────────────────────

    def plan_node(state: ResearchState) -> dict:
        """规划节点：调用 LLM 分析问题复杂度，一次性生成完整检索计划"""
        print("\n【规划节点】分析调研意图，制定检索计划...")
        actions = planner.plan(state["user_query"])
        print(f"  生成 {len(actions)} 个动作")
        return {"planned_actions": actions}

    def execute_node(state: ResearchState) -> dict:
        """执行节点：按计划逐条调用 RAG / 网络检索工具，结果追加到 context_items"""
        actions = state["planned_actions"]
        print(f"\n【执行节点】执行 {len(actions)} 个动作（第 {state['iteration'] + 1} 轮）...")
        new_items = list(state["context_items"])

        for i, action in enumerate(actions, 1):
            name   = action.get("action_name", "")
            prompt = action.get("prompt", "")
            print(f"  [{i}/{len(actions)}] {name}: {prompt}")
            try:
                if name == "RAG检索":
                    refs, answer = rag_tool.retrieve(prompt)
                    refs_text = "\n".join(refs) if refs else ""
                    new_items.append(
                        f"[RAG检索] 查询: {prompt}\n回答: {answer}\n参考: {refs_text}"
                    )
                elif name == "网络检索":
                    result = web_tool.search(prompt)
                    new_items.append(f"[网络检索] 查询: {prompt}\n结果: {result}")
                else:
                    print(f"  未知动作类型: {name}，跳过")
            except Exception as e:
                print(f"  执行失败 ({name}): {e}")

        return {
            "context_items": new_items,
            "iteration": state["iteration"] + 1,
        }

    def replan_node(state: ResearchState) -> dict:
        """重规划节点：评估已有信息充分性，决定是否生成补充查询计划"""
        print("\n【重规划节点】评估信息充分性...")
        context = "\n\n".join(state["context_items"])
        additional = planner.replan(state["user_query"], context)
        if additional:
            print(f"  需要补充 {len(additional)} 个查询")
        else:
            print("  信息充分，无需补充")
        return {"planned_actions": additional or []}

    def summarize_node(state: ResearchState) -> dict:
        """总结节点：整合所有检索结果，生成 Markdown 格式调研报告"""
        print("\n【总结节点】生成调研报告...")
        context = "\n\n".join(state["context_items"])
        report  = summarizer.generate_report(state["user_query"], context)
        return {"final_report": report}

    def render_node(state: ResearchState) -> dict:
        """渲染节点：将 Markdown 报告渲染为 HTML 并保存到 reports/"""
        print("\n【渲染节点】生成 HTML 报告...")
        path = renderer.render(state["user_query"], state["final_report"])
        print(f"报告已保存: {path}")
        return {"html_path": path}

    # ── 路由函数 ──────────────────────────────────────────────────────────────

    def after_plan(state: ResearchState) -> str:
        """plan() 后：有待执行动作则进入执行节点，否则直接结束（如闲聊类问题）"""
        return "execute" if state["planned_actions"] else END

    def after_replan(state: ResearchState) -> str:
        """replan() 后：有补充查询且未超过迭代上限则继续执行，否则进入总结"""
        if state["planned_actions"] and state["iteration"] < state["max_iterations"]:
            return "execute"
        return "summarize"

    # ── 构建图 ────────────────────────────────────────────────────────────────

    builder = StateGraph(ResearchState)

    builder.add_node("plan",      plan_node)
    builder.add_node("execute",   execute_node)
    builder.add_node("replan",    replan_node)
    builder.add_node("summarize", summarize_node)
    builder.add_node("render",    render_node)

    builder.add_edge(START, "plan")
    builder.add_conditional_edges("plan", after_plan)
    builder.add_edge("execute", "replan")
    builder.add_conditional_edges("replan", after_replan)
    builder.add_edge("summarize", "render")
    builder.add_edge("render", END)

    return builder.compile()
