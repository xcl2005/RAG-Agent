from types import SimpleNamespace

import pytest

from rag_agent.config import Settings
from rag_agent.llm.client import LLMClient, LLMRequestError, QueryPlan, _json_from_text


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        text = next(self.outputs)
        return SimpleNamespace(
            output_text=text,
            id="resp_test",
            model=kwargs["model"],
            usage=SimpleNamespace(input_tokens=11, output_tokens=7),
        )


def client_with_responses(*outputs: str) -> tuple[LLMClient, FakeResponses]:
    client = LLMClient(Settings(openai_api_key="", llm_api_mode="responses", _env_file=None))
    responses = FakeResponses(outputs)
    client.enabled = True
    client.client = SimpleNamespace(responses=responses)
    return client, responses


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
    assert responses.calls[0]["store"] is False
    assert responses.calls[0]["max_output_tokens"] == client.settings.max_answer_output_tokens
    assert "messages" not in responses.calls[0]


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
