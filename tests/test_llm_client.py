from types import SimpleNamespace

import pytest

from rag_agent.config import Settings
from rag_agent.llm.client import (
    LLMClient,
    LLMOutputError,
    LLMRequestError,
    QueryPlan,
    _json_from_text,
)


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        output = next(self.outputs)
        if not isinstance(output, str):
            return output
        return SimpleNamespace(
            output_text=output,
            id="resp_test",
            model=kwargs["model"],
            status="completed",
            incomplete_details=None,
            usage=SimpleNamespace(
                input_tokens=11,
                output_tokens=7,
                output_tokens_details=SimpleNamespace(reasoning_tokens=2),
            ),
        )


class FakeChatCompletions:
    def __init__(self, completion):
        self.completion = completion
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.completion


def client_with_responses(
    *outputs: object,
    **setting_overrides: object,
) -> tuple[LLMClient, FakeResponses]:
    app_settings = Settings(
        openai_api_key="",
        llm_api_mode="responses",
        _env_file=None,
        **setting_overrides,
    )
    client = LLMClient(app_settings)
    responses = FakeResponses(outputs)
    client.enabled = True
    client.client = SimpleNamespace(responses=responses)
    return client, responses


def client_with_chat(completion, **setting_overrides: object):
    app_settings = Settings(
        openai_api_key="",
        llm_api_mode="chat_completions",
        _env_file=None,
        **setting_overrides,
    )
    client = LLMClient(app_settings)
    completions = FakeChatCompletions(completion)
    client.enabled = True
    client.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return client, completions


def test_json_parser_accepts_fenced_object_and_rejects_array():
    assert _json_from_text('```json\n{"queries": ["RAG"]}\n```')["queries"] == ["RAG"]

    with pytest.raises(ValueError, match="JSON object"):
        _json_from_text("[1, 2]")


def test_disabled_client_never_attempts_network():
    client = LLMClient(Settings(openai_api_key="", _env_file=None))

    with pytest.raises(LLMRequestError, match="OPENAI_API_KEY"):
        client.generate("instructions", "input")


def test_responses_transport_collects_usage_and_disables_storage():
    client, responses = client_with_responses("grounded answer [S1]")

    call = client.generate("use evidence", "question")

    assert call.text == "grounded answer [S1]"
    assert call.input_tokens == 11
    assert call.output_tokens == 7
    assert call.finish_reason == "stop"
    assert call.reasoning_tokens == 2
    assert responses.calls[0]["store"] is False
    assert responses.calls[0]["max_output_tokens"] == client.settings.max_answer_output_tokens
    assert "extra_body" not in responses.calls[0]
    assert "messages" not in responses.calls[0]


@pytest.mark.parametrize(
    ("mode", "enabled"),
    [("disabled", False), ("enabled", True)],
)
def test_thinking_mode_is_forwarded_through_extra_body(mode: str, enabled: bool):
    client, responses = client_with_responses(
        "answer",
        llm_thinking_mode=mode,
    )

    client.generate("instructions", "question")

    assert responses.calls[0]["extra_body"] == {"enable_thinking": enabled}


def test_empty_and_length_limited_outputs_raise_diagnostic_errors():
    empty_response = SimpleNamespace(
        output_text="",
        id="resp_empty",
        model="fake",
        status="completed",
        incomplete_details=None,
        usage=SimpleNamespace(
            input_tokens=5,
            output_tokens=99,
            output_tokens_details=SimpleNamespace(reasoning_tokens=99),
        ),
    )
    client, _ = client_with_responses(empty_response)

    with pytest.raises(LLMOutputError, match="empty text") as empty_error:
        client.generate("instructions", "question")

    assert empty_error.value.call.reasoning_tokens == 99
    assert empty_error.value.call.finish_reason == "stop"

    length_response = SimpleNamespace(
        output_text="partial",
        id="resp_length",
        model="fake",
        status="incomplete",
        incomplete_details=SimpleNamespace(reason="max_output_tokens"),
        usage=SimpleNamespace(
            input_tokens=5,
            output_tokens=100,
            output_tokens_details=SimpleNamespace(reasoning_tokens=80),
        ),
    )
    client, _ = client_with_responses(length_response)

    with pytest.raises(LLMOutputError, match="truncated") as length_error:
        client.generate("instructions", "question")

    assert length_error.value.call.finish_reason == "length"


def test_chat_transport_records_finish_reason_and_reasoning_tokens():
    completion = SimpleNamespace(
        id="chat_test",
        model="fake",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="answer"),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=8,
            completion_tokens=12,
            completion_tokens_details=SimpleNamespace(reasoning_tokens=4),
        ),
    )
    client, completions = client_with_chat(
        completion,
        llm_thinking_mode="disabled",
    )

    call = client.generate("instructions", "question")

    assert call.finish_reason == "stop"
    assert call.reasoning_tokens == 4
    assert completions.calls[0]["extra_body"] == {"enable_thinking": False}


def test_structured_response_uses_json_schema_and_query_plan_is_deduplicated():
    client, responses = client_with_responses(
        '{"search_queries":["原问题","原问题","RAG citation"],"strategy":"hybrid"}'
    )

    plan, call = client.plan_queries(
        "原问题",
        history=[{"question": "上一问", "answer": "上一答"}],
        attempt=1,
        max_variants=2,
    )

    assert isinstance(plan, QueryPlan)
    assert plan.search_queries == ["原问题", "RAG citation"]
    assert call.response_id == "resp_test"
    assert responses.calls[0]["text"]["format"]["type"] == "json_schema"
    assert responses.calls[0]["text"]["format"]["strict"] is True
    schema = responses.calls[0]["text"]["format"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"search_queries", "strategy"}


@pytest.mark.parametrize(
    "invalid_output",
    [
        "not-json",
        '{"search_queries":[],"strategy":"invalid"}',
    ],
)
def test_invalid_structured_output_gets_one_json_only_fallback(invalid_output: str):
    client, responses = client_with_responses(
        invalid_output,
        '{"search_queries":["RAG"],"strategy":"fallback"}',
    )

    plan, call = client.generate_structured(
        "plan searches",
        "find RAG",
        QueryPlan,
    )

    assert plan.search_queries == ["RAG"]
    assert plan.strategy == "fallback"
    assert call.response_id == "resp_test"
    assert len(responses.calls) == 2
    assert responses.calls[0]["text"]["format"]["type"] == "json_schema"
    assert "text" not in responses.calls[1]
    assert "Return exactly one JSON object" in responses.calls[1]["instructions"]
