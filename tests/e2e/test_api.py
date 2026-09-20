"""End-to-end tests against the FastAPI app via TestClient (in-process, no network)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agentic_platform.api.main import app, get_pipeline
from agentic_platform.config.settings import Settings
from agentic_platform.orchestration.llm_client import MockLLMClient
from agentic_platform.orchestration.pipeline import AgenticPipeline

pytestmark = pytest.mark.e2e

client = TestClient(app)


def _override_pipeline():
    settings = Settings(max_agent_turns=3)
    llm = MockLLMClient(settings, canned_responses={"refund": "Refunds take five days."})
    pipeline = AgenticPipeline(settings=settings, llm=llm)
    pipeline.seed_knowledge_base({"policy": "Refunds take five business days to process."})
    yield pipeline


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz() -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_config_summary() -> None:
    response = client.get("/v1/config")
    assert response.status_code == 200
    assert "llm_provider" in response.json()


def test_run_agent_end_to_end() -> None:
    app.dependency_overrides[get_pipeline] = _override_pipeline
    try:
        response = client.post("/v1/agent/run", json={"task": "what is the refund policy"})
        assert response.status_code == 200
        body = response.json()
        assert body["final_answer"]
        assert body["verdict"] in {"pass", "needs_human_review", "reject"}
        assert "groundedness" in body["scores"]
    finally:
        app.dependency_overrides.clear()


def test_run_agent_rejects_empty_task() -> None:
    response = client.post("/v1/agent/run", json={"task": ""})
    assert response.status_code == 422


def test_run_agent_returns_409_when_human_approval_required() -> None:
    from agentic_platform.tools.registry import HumanApprovalRequiredError

    class _RaisingPipeline:
        settings = Settings()

        def run(self, task: str):
            raise HumanApprovalRequiredError("blocked")

    def _override():
        yield _RaisingPipeline()

    app.dependency_overrides[get_pipeline] = _override
    try:
        response = client.post("/v1/agent/run", json={"task": "sensitive op"})
        assert response.status_code == 409
    finally:
        app.dependency_overrides.clear()
