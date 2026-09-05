from __future__ import annotations

from dataclasses import dataclass
from time import sleep

from pydantic import BaseModel, ConfigDict, Field

from rag_agent.agent.tooling import (
    BoundedToolAgent,
    ToolDecision,
    ToolDefinition,
    ToolRegistry,
    build_knowledge_tool_registry,
)
from rag_agent.schemas import Candidate


class EchoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=20)


@dataclass
class DummyCall:
    marker: str

    def usage_dict(self):
        return {"marker": self.marker}


class FakeLLM:
    def __init__(self, decisions):
        self.decisions = list(decisions)

    def generate_structured(self, instructions, user_input, schema_model):
        del instructions, user_input, schema_model
        decision = self.decisions.pop(0)
        return decision, DummyCall(marker=decision.action)


class FakeRetriever:
    def retrieve(self, query, rerank_top_k=None):
        assert query == "timeout policy"
        assert rerank_top_k == 2
        return [
            Candidate(
                chunk_id="c1",
                text="The API timeout is 30 seconds.",
                metadata={"source": "api.md"},
                score=0.91,
                dense_score=0.84,
                sparse_score=0.70,
            ),
            Candidate(
                chunk_id="c2",
                text="Retries use bounded exponential backoff.",
                metadata={"source": "reliability.md"},
                score=0.82,
            ),
        ]


def test_registry_validates_arguments_and_unknown_tools():
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="echo_text",
            description="Echo validated text.",
            args_model=EchoArgs,
            handler=lambda args: {"echo": args.text},
        )
    )
    try:
        ok = registry.execute("echo_text", {"text": "hello"})
        assert ok.status == "ok"
        assert '"hello"' in ok.output

        invalid = registry.execute("echo_text", {"text": "", "extra": 1})
        assert invalid.status == "invalid_arguments"
        assert invalid.error_type == "ValidationError"

        unknown = registry.execute("missing_tool", {})
        assert unknown.status == "unknown_tool"
    finally:
        registry.close()


def test_registry_classifies_timeout():
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="slow_tool",
            description="Intentionally slow test tool.",
            args_model=EchoArgs,
            handler=lambda args: (sleep(0.05), args.text)[1],
            timeout_seconds=0.001,
        )
    )
    try:
        result = registry.execute("slow_tool", {"text": "hello"})
        assert result.status == "timeout"
        assert result.error_type == "TimeoutError"
    finally:
        registry.close()


def test_knowledge_search_tool_exposes_bounded_read_only_results():
    registry = build_knowledge_tool_registry(FakeRetriever())
    try:
        result = registry.execute(
            "search_knowledge_base",
            {"query": "timeout policy", "top_k": 2},
        )
        assert result.status == "ok"
        assert "api.md" in result.output
        assert "30 seconds" in result.output
    finally:
        registry.close()


def test_bounded_tool_agent_executes_tool_then_finishes():
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="echo_text",
            description="Echo validated text.",
            args_model=EchoArgs,
            handler=lambda args: {"echo": args.text},
        )
    )
    llm = FakeLLM(
        [
            ToolDecision(
                action="tool",
                tool_name="echo_text",
                arguments_json='{"text":"evidence"}',
                final_answer="",
            ),
            ToolDecision(
                action="final",
                tool_name="",
                arguments_json="{}",
                final_answer="Used the validated tool result.",
            ),
        ]
    )
    try:
        result = BoundedToolAgent(llm, registry, max_steps=3).run("test question")  # type: ignore[arg-type]
        assert result.failure_kind is None
        assert result.answer == "Used the validated tool result."
        assert result.steps[0]["status"] == "ok"
        assert result.steps[0]["tool_name"] == "echo_text"
        assert len(result.llm_calls) == 2
    finally:
        registry.close()


def test_bounded_tool_agent_rejects_bad_argument_json_and_stops():
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="echo_text",
            description="Echo validated text.",
            args_model=EchoArgs,
            handler=lambda args: {"echo": args.text},
        )
    )
    llm = FakeLLM(
        [
            ToolDecision(
                action="tool",
                tool_name="echo_text",
                arguments_json="[]",
                final_answer="",
            )
        ]
    )
    try:
        result = BoundedToolAgent(llm, registry, max_steps=1).run("test question")  # type: ignore[arg-type]
        assert result.failure_kind == "tool_step_limit"
        assert result.steps[0]["status"] == "invalid_arguments"
        assert result.steps[0]["error_type"] == "invalid_arguments_json"
    finally:
        registry.close()
