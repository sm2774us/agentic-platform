"""FastAPI service exposing the agentic pipeline as an HTTP API."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import asdict
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from agentic_platform.config.settings import get_settings
from agentic_platform.orchestration.pipeline import AgenticPipeline
from agentic_platform.tools.registry import HumanApprovalRequiredError

app = FastAPI(
    title="Agentic Platform API",
    version="0.1.0",
    description="Production multi-agent orchestration, RAG, and evaluation service.",
)


@lru_cache(maxsize=1)
def _default_pipeline() -> AgenticPipeline:
    pipeline = AgenticPipeline()
    pipeline.seed_knowledge_base(
        {
            "onboarding": "New engineers should read the architecture overview and runbooks.",
            "refunds": "Refunds are processed within five business days of approval.",
        }
    )
    return pipeline


def get_pipeline() -> Iterator[AgenticPipeline]:
    yield _default_pipeline()


class TaskRequest(BaseModel):
    task: str = Field(min_length=1, max_length=4000)


class ScoreResponse(BaseModel):
    groundedness: float
    hallucination_risk: float
    safety: float
    latency_ms: float
    cost_usd: float


class TaskResponse(BaseModel):
    final_answer: str
    verdict: str
    requires_human_review: bool
    scores: ScoreResponse


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz(pipeline: AgenticPipeline = Depends(get_pipeline)) -> dict[str, str]:  # noqa: B008
    return {"status": "ready", "provider": pipeline.settings.llm_provider.value}


@app.post("/v1/agent/run", response_model=TaskResponse)
def run_agent(
    request: TaskRequest, pipeline: AgenticPipeline = Depends(get_pipeline)  # noqa: B008
) -> TaskResponse:
    try:
        result = pipeline.run(request.task)
    except HumanApprovalRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return TaskResponse(
        final_answer=result.state.final_answer or "",
        verdict=result.verdict.verdict.value,
        requires_human_review=result.state.requires_human_review,
        scores=ScoreResponse(**asdict(result.verdict.scores)),
    )


@app.get("/v1/config")
def config_summary() -> dict[str, str | int | float | bool]:
    settings = get_settings()
    return {
        "environment": settings.environment.value,
        "llm_provider": settings.llm_provider.value,
        "max_agent_turns": settings.max_agent_turns,
        "hallucination_score_threshold": settings.hallucination_score_threshold,
        "human_in_the_loop_enabled": settings.enable_human_in_the_loop,
    }
