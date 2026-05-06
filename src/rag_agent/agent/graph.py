
"""LangGraph Agent 工作流。

普通 RAG 往往是固定链路：问题 -> 检索 -> 回答。
本项目用 LangGraph 写成 Agentic RAG 流程：
rewrite_query -> retrieve -> grade_evidence -> generate_answer

虽然这个 Agent 还不是复杂多智能体，但已经体现了 Agent 项目常见的：
- 状态流转
- 节点拆分
- 条件判断/证据门控
- 工具化检索
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from rag_agent.agent.prompts import ANSWER_PROMPT, REWRITE_PROMPT, SYSTEM_PROMPT, format_sources, source_list
from rag_agent.config import settings
from rag_agent.llm.client import LLMClient
from rag_agent.retrieval.hybrid import HybridRetriever
from rag_agent.schemas import Candidate


class AgentState(TypedDict, total=False):
    """LangGraph 在节点之间传递的状态。

    每个节点接收 state，返回部分字段，LangGraph 会把字段合并回整体 state。
    """

    question: str
    query: str
    candidates: list[Candidate]
    evidence_ok: bool
    answer: str
    sources: list[dict]


class RAGAgent:
    """RAG Agent 主类。"""

    def __init__(self):
        self.llm = LLMClient()
        self.retriever = HybridRetriever(settings)
        self.graph = self._build_graph()

    def _build_graph(self):
        """构建 LangGraph 状态图。"""

        workflow = StateGraph(AgentState)

        # 每个 node 对应一个函数，也就是 Agent 工作流中的一步。
        workflow.add_node("rewrite_query", self.rewrite_query)
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("grade_evidence", self.grade_evidence)
        workflow.add_node("generate_answer", self.generate_answer)

        # 当前版本是线性流程。以后可以扩展成：
        # evidence 不足 -> 换关键词重新 retrieve -> 再判断。
        workflow.set_entry_point("rewrite_query")
        workflow.add_edge("rewrite_query", "retrieve")
        workflow.add_edge("retrieve", "grade_evidence")
        workflow.add_edge("grade_evidence", "generate_answer")
        workflow.add_edge("generate_answer", END)
        return workflow.compile()

    def rewrite_query(self, state: AgentState) -> AgentState:
        """节点 1：查询改写。

        作用：把用户自然语言问题改写成更适合检索的 query。
        没配置 LLM 时，直接用原问题，保证项目仍能跑检索。
        """

        question = state["question"]
        if not self.llm.enabled:
            return {"query": question}

        rewritten = self.llm.chat(
            [
                {"role": "system", "content": "你是搜索查询改写助手。"},
                {"role": "user", "content": REWRITE_PROMPT.format(question=question)},
            ],
            temperature=0.0,
        ).strip()
        return {"query": rewritten or question}

    def retrieve(self, state: AgentState) -> AgentState:
        """节点 2：调用混合检索器。"""

        query = state.get("query") or state["question"]
        candidates = self.retriever.retrieve(query)
        return {"candidates": candidates, "sources": source_list(candidates)}

    def grade_evidence(self, state: AgentState) -> AgentState:
        """节点 3：证据门控。

        如果没有候选证据，或者最高分低于阈值，就认为证据不足。
        这样可以避免 LLM 在没有资料时强行编答案。
        """

        candidates = state.get("candidates", [])
        if not candidates:
            return {"evidence_ok": False}
        best_score = max(c.score for c in candidates)
        return {"evidence_ok": best_score >= settings.min_relevance_score}

    def generate_answer(self, state: AgentState) -> AgentState:
        """节点 4：生成最终回答。"""

        question = state["question"]
        candidates = state.get("candidates", [])

        # 证据不足时直接拒答，而不是把空 context 交给 LLM 胡编。
        if not state.get("evidence_ok"):
            return {
                "answer": "根据当前资料无法确认。系统没有检索到足够相关的证据，因此不应编造答案。",
                "sources": source_list(candidates),
            }

        context = format_sources(candidates, max_chars=settings.max_context_chars)
        answer = self.llm.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": ANSWER_PROMPT.format(question=question, context=context)},
            ],
            temperature=settings.temperature,
        )
        return {"answer": answer, "sources": source_list(candidates)}

    def ask(self, question: str) -> dict:
        """对外暴露的问答入口。"""

        result = self.graph.invoke({"question": question})
        return {
            "question": question,
            "query": result.get("query", question),
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
        }
