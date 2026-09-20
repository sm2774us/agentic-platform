import pytest

from agentic_platform.config.settings import LLMProvider, Settings
from agentic_platform.orchestration.llm_client import (
    LLMError,
    LLMResponse,
    MockLLMClient,
    build_llm_client,
)


def test_mock_client_returns_canned_response() -> None:
    client = MockLLMClient(Settings(), canned_responses={"hello": "hi there"})
    response = client.complete("hello world")
    assert response.text == "hi there"
    assert response.model == "mock-model-large"


def test_mock_client_skips_non_matching_trigger_before_match() -> None:
    client = MockLLMClient(
        Settings(), canned_responses={"zzz_no_match": "nope", "hello": "hi there"}
    )
    response = client.complete("hello world")
    assert response.text == "hi there"


def test_mock_client_default_fallback() -> None:
    client = MockLLMClient(Settings())
    response = client.complete("anything else")
    assert response.text.startswith("[mock-response]")


def test_llm_response_estimated_cost() -> None:
    response = LLMResponse(text="x", input_tokens=1000, output_tokens=1000, model="m")
    assert response.estimated_cost_usd == pytest.approx(0.018)


def test_build_llm_client_mock() -> None:
    client = build_llm_client(Settings(llm_provider=LLMProvider.MOCK))
    assert isinstance(client, MockLLMClient)


def test_build_llm_client_unconfigured_provider_raises() -> None:
    with pytest.raises(LLMError):
        build_llm_client(Settings(llm_provider=LLMProvider.ANTHROPIC))
