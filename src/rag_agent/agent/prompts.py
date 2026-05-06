
"""Prompt 模板与来源格式化。

RAG 项目控制幻觉，主要靠三件事：
1. 检索阶段尽量找到相关证据。
2. Prompt 里明确要求“只能基于 CONTEXT 回答”。
3. 回答时强制引用来源 [S1]、[S2]，没有证据就拒答。
"""

from __future__ import annotations

from rag_agent.schemas import Candidate

# 系统提示词：约束模型角色和回答规则。
SYSTEM_PROMPT = """你是一个企业知识库 RAG 问答助手。
你必须严格遵守：
1. 只能基于提供的 CONTEXT 回答，不要使用外部知识自行补全。
2. 每个关键结论后必须标注来源，例如 [S1]、[S2]。
3. 如果 CONTEXT 中没有足够证据，必须明确说“根据当前资料无法确认”，不要编造。
4. 回答要清晰、具体、面向工程实现。
5. 如果资料之间冲突，要指出冲突来源。
"""

# Query rewrite：把用户口语化问题改写成更适合检索的查询。
# 例如用户问“这个怎么防止胡说”，可以改写成“幻觉控制 证据不足 拒答 引用来源”。
REWRITE_PROMPT = """请把用户问题改写成适合知识库检索的查询语句。
要求：
- 保留专有名词、技术词、错误码、英文缩写。
- 补充同义词，但不要改变问题含义。
- 只输出改写后的查询，不要解释。

用户问题：{question}
"""

# 最终回答 Prompt：把 question 和检索到的 context 一起给模型。
ANSWER_PROMPT = """用户问题：
{question}

CONTEXT：
{context}

请基于 CONTEXT 回答用户问题。关键结论必须带来源引用。
"""


def format_sources(candidates: list[Candidate], max_chars: int) -> str:
    """把检索到的 Candidate 格式化成 LLM 能读懂的 CONTEXT。

    输出格式大概是：
    [S1] data/raw/a.pdf, page=3, chunk=5
    这里是 chunk 原文

    [S2] ...

    这样模型回答时可以引用 [S1]、[S2]。
    """

    blocks: list[str] = []
    used = 0
    for i, c in enumerate(candidates, start=1):
        source = c.metadata.get("source", "unknown")
        page = c.metadata.get("page")
        chunk_index = c.metadata.get("chunk_index")
        location = f"{source}"
        if page is not None:
            location += f", page={page}"
        if chunk_index is not None:
            location += f", chunk={chunk_index}"

        text = c.text.strip()
        block = f"[S{i}] {location}\n{text}\n"

        # 控制总上下文长度，避免一次塞太多内容导致慢、贵、甚至超过模型上下文。
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
    return "\n---\n".join(blocks)


def source_list(candidates: list[Candidate]) -> list[dict]:
    """把来源信息整理成 API 可返回的结构。"""

    sources = []
    for i, c in enumerate(candidates, start=1):
        sources.append(
            {
                "id": f"S{i}",
                "source": c.metadata.get("source"),
                "page": c.metadata.get("page"),
                "chunk_index": c.metadata.get("chunk_index"),
                "score": c.score,
                "dense_score": c.dense_score,
                "sparse_score": c.sparse_score,
                "rerank_score": c.rerank_score,
                "preview": c.text[:220],
            }
        )
    return sources
