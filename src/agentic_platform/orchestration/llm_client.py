"""Provider-agnostic LLM client with retries and cost accounting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from tenacity import retry, stop_after_attempt, wait_exponential

from agentic_platform.config.settings import Settings
from agentic_platform.observability.tracing import traced_span


class LLMError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str

    @property
    def estimated_cost_usd(self) -> float:
        rate_in, rate_out = 0.003, 0.015
        return (self.input_tokens / 1000) * rate_in + (self.output_tokens / 1000) * rate_out


@runtime_checkable
class LLMClient(Protocol):
    def complete(  # pragma: no cover
        self, prompt: str, *, system: str | None = None
    ) -> LLMResponse: ...


class MockLLMClient:
    """Deterministic, offline LLM stand-in used for tests and local dev."""

    def __init__(
        self, settings: Settings, *, canned_responses: dict[str, str] | None = None
    ) -> None:
        self._settings = settings
        self._canned = canned_responses or {}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.01, max=0.1))
    def complete(self, prompt: str, *, system: str | None = None) -> LLMResponse:
        with traced_span("llm.complete", model=self._settings.llm_model_name) as span:
            for trigger, response in self._canned.items():
                if trigger.lower() in prompt.lower():
                    span.attributes["matched"] = trigger
                    return LLMResponse(
                        text=response,
                        input_tokens=len(prompt.split()),
                        output_tokens=len(response.split()),
                        model=self._settings.llm_model_name,
                    )
            text = f"[mock-response] acknowledged: {prompt[:80]}"
            return LLMResponse(
                text=text,
                input_tokens=len(prompt.split()),
                output_tokens=len(text.split()),
                model=self._settings.llm_model_name,
            )


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == settings.llm_provider.MOCK:
        return MockLLMClient(settings)
    raise LLMError(
        f"Provider {settings.llm_provider!r} requires a configured SDK client; "
        "wire it in build_llm_client()."
    )
