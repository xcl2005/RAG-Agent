"""LLM transport with a current Responses API path and a compatibility path.

LangGraph owns orchestration in this project. The model client deliberately does
not implement another agent loop; it performs small, typed model calls requested
by graph nodes.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from typing import Annotated, Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from rag_agent.config import Settings, settings

StructuredT = TypeVar("StructuredT", bound=BaseModel)
QueryText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class LLMRequestError(RuntimeError):
    """Raised when a configured provider cannot complete a model request."""


class QueryPlan(BaseModel):
    """Structured output produced by the query-planning node."""

    # OpenAI strict JSON Schema requires closed objects and every property in
    # ``required``. Keeping this contract on the model makes both Responses and
    # Chat Completions transports emit an accepted schema.
    model_config = ConfigDict(extra="forbid")

    search_queries: list[QueryText] = Field(min_length=1, max_length=6)
    strategy: str = Field(
        max_length=120,
        description="Short label describing how the query variants differ.",
    )


@dataclass(slots=True)
class LLMCall:
    """Observable metadata for one provider call."""

    text: str
    response_id: str | None
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float

    def usage_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("text")
        return value


def _json_from_text(text: str) -> dict[str, Any]:
    """Parse JSON even when a compatibility model wraps it in a code fence."""

    cleaned = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1)
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("structured model output must be a JSON object")
    return value


class LLMClient:
    """Thin OpenAI/compatible-provider adapter.

    - ``responses`` is the default and current OpenAI transport.
    - ``chat_completions`` keeps DeepSeek/Qwen/other compatible endpoints usable.
    - provider retries and timeouts are bounded by the official SDK.
    """

    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings
        self.enabled = app_settings.llm_enabled
        self.client: OpenAI | None = None
        if self.enabled:
            self.client = OpenAI(
                api_key=app_settings.openai_api_key,
                base_url=app_settings.openai_base_url,
                timeout=60.0,
                max_retries=2,
            )

    def generate(
        self,
        instructions: str,
        user_input: str,
        *,
        max_output_tokens: int | None = None,
    ) -> LLMCall:
        """Generate text through the configured API mode."""

        if not self.enabled or self.client is None:
            raise LLMRequestError("OPENAI_API_KEY is not configured")

        started = time.perf_counter()
        token_limit = max_output_tokens or self.settings.max_answer_output_tokens
        try:
            if self.settings.llm_api_mode == "responses":
                response = self.client.responses.create(
                    model=self.settings.chat_model,
                    instructions=instructions,
                    input=user_input,
                    max_output_tokens=token_limit,
                    # RAG questions may contain confidential enterprise data.
                    store=self.settings.llm_store_responses,
                )
                usage = getattr(response, "usage", None)
                return LLMCall(
                    text=response.output_text or "",
                    response_id=getattr(response, "id", None),
                    model=getattr(response, "model", self.settings.chat_model),
                    input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                    output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                )

            completion = self.client.chat.completions.create(
                model=self.settings.chat_model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": user_input},
                ],
                temperature=0.1,
                max_tokens=token_limit,
            )
            usage = completion.usage
            return LLMCall(
                text=completion.choices[0].message.content or "",
                response_id=completion.id,
                model=completion.model,
                input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
        except Exception as exc:  # SDK exception classes vary across providers.
            # Provider messages may echo request data or internal endpoints.
            # The exception class is enough for API diagnostics; full SDK
            # details remain available through the chained server exception.
            raise LLMRequestError(f"model request failed ({type(exc).__name__})") from exc

    def generate_structured(
        self,
        instructions: str,
        user_input: str,
        schema_model: type[StructuredT],
        *,
        max_output_tokens: int | None = None,
    ) -> tuple[StructuredT, LLMCall]:
        """Generate JSON constrained by a Pydantic schema.

        Some OpenAI-compatible providers do not implement JSON Schema. For that
        compatibility path we retry once with an explicit JSON-only prompt and
        still validate the result locally before it enters graph state.
        """

        if not self.enabled or self.client is None:
            raise LLMRequestError("OPENAI_API_KEY is not configured")

        schema = schema_model.model_json_schema()
        schema_name = schema_model.__name__.lower()
        started = time.perf_counter()
        token_limit = max_output_tokens or self.settings.max_plan_output_tokens
        try:
            if self.settings.llm_api_mode == "responses":
                response = self.client.responses.create(
                    model=self.settings.chat_model,
                    instructions=instructions,
                    input=user_input,
                    max_output_tokens=token_limit,
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": schema_name,
                            "strict": True,
                            "schema": schema,
                        }
                    },
                    store=self.settings.llm_store_responses,
                )
                usage = getattr(response, "usage", None)
                call = LLMCall(
                    text=response.output_text or "",
                    response_id=getattr(response, "id", None),
                    model=getattr(response, "model", self.settings.chat_model),
                    input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                    output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                )
                return schema_model.model_validate_json(call.text), call

            completion = self.client.chat.completions.create(
                model=self.settings.chat_model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": user_input},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "strict": True,
                        "schema": schema,
                    },
                },
                temperature=0.0,
                max_tokens=token_limit,
            )
            usage = completion.usage
            call = LLMCall(
                text=completion.choices[0].message.content or "",
                response_id=completion.id,
                model=completion.model,
                input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return schema_model.model_validate(_json_from_text(call.text)), call
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            raise LLMRequestError("model returned invalid structured output") from exc
        except Exception:
            # Conservative compatibility fallback for providers that reject
            # response_format/text.format but can still produce valid JSON.
            try:
                schema_text = json.dumps(schema, ensure_ascii=False)
                fallback = self.generate(
                    instructions + "\n只输出一个 JSON 对象，不要使用 Markdown 代码块。",
                    f"{user_input}\n\n必须满足此 JSON Schema：\n{schema_text}",
                    max_output_tokens=token_limit,
                )
                return schema_model.model_validate(_json_from_text(fallback.text)), fallback
            except Exception as fallback_exc:
                raise LLMRequestError(
                    "structured request and compatibility fallback both failed"
                ) from fallback_exc

    def plan_queries(
        self,
        question: str,
        *,
        history: list[dict[str, str]],
        attempt: int,
        max_variants: int,
    ) -> tuple[QueryPlan, LLMCall]:
        """Create complementary semantic and lexical search formulations."""

        history_text = "\n".join(
            f"用户：{turn.get('question', '')}\n助手：{turn.get('answer', '')[:300]}" for turn in history[-2:]
        )
        prompt = (
            f"当前问题：{question}\n"
            f"检索尝试：{attempt}\n"
            f"最近对话（可能为空）：\n{history_text or '无'}\n\n"
            f"生成 1 到 {max_variants} 个互补查询。第一个查询保留用户原意；"
            "其他查询可补充同义词、英文缩写、精确实体或错误码。"
        )
        plan, call = self.generate_structured(
            "你是企业知识库的检索规划器。不要回答问题，只规划搜索查询；不要引入用户未表达的事实。",
            prompt,
            QueryPlan,
            max_output_tokens=self.settings.max_plan_output_tokens,
        )
        cleaned = [query.strip() for query in plan.search_queries if query.strip()]
        plan.search_queries = list(dict.fromkeys(cleaned))[:max_variants] or [question]
        return plan, call
