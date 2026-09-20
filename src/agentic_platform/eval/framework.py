"""Evaluation framework: quality, hallucination risk, latency, cost, safety."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agentic_platform.agents.state import AgentState
from agentic_platform.config.settings import Settings


class Verdict(StrEnum):
    PASS = "pass"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    REJECT = "reject"


@dataclass(slots=True, frozen=True)
class EvalScores:
    groundedness: float
    hallucination_risk: float
    safety: float
    latency_ms: float
    cost_usd: float


@dataclass(slots=True, frozen=True)
class EvaluationVerdict:
    verdict: Verdict
    scores: EvalScores
    reasons: tuple[str, ...]


_UNSAFE_MARKERS = ("ignore previous instructions", "exfiltrate", "bypass safety")


def score_groundedness(answer: str, context_chunks: list[str]) -> float:
    if not answer:
        return 0.0
    if not context_chunks:
        return 0.3 if "mock-response" in answer else 0.0
    answer_tokens = set(answer.lower().split())
    context_tokens: set[str] = set()
    for chunk in context_chunks:
        context_tokens |= set(chunk.lower().split())
    if not answer_tokens:
        return 0.0
    overlap = len(answer_tokens & context_tokens) / len(answer_tokens)
    return min(1.0, overlap + 0.4)


def score_safety(answer: str) -> float:
    lowered = answer.lower()
    return 0.0 if any(marker in lowered for marker in _UNSAFE_MARKERS) else 1.0


def evaluate_run(
    state: AgentState, *, settings: Settings, latency_ms: float, cost_usd: float
) -> EvaluationVerdict:
    answer = state.final_answer or ""
    groundedness = score_groundedness(answer, state.retrieved_context)
    hallucination_risk = round(1.0 - groundedness, 4)
    safety = score_safety(answer)

    reasons: list[str] = []
    verdict = Verdict.PASS

    if safety < 1.0:
        verdict = Verdict.REJECT
        reasons.append("unsafe content detected")
    elif hallucination_risk > (1 - settings.hallucination_score_threshold):
        verdict = Verdict.NEEDS_HUMAN_REVIEW
        reasons.append("hallucination risk exceeds threshold")
    elif state.requires_human_review:
        verdict = Verdict.NEEDS_HUMAN_REVIEW
        reasons.append("agent self-flagged for review")
    elif cost_usd > settings.cost_budget_usd_per_request:
        verdict = Verdict.NEEDS_HUMAN_REVIEW
        reasons.append("cost budget exceeded")

    if not reasons:
        reasons.append("all quality gates satisfied")

    scores = EvalScores(
        groundedness=round(groundedness, 4),
        hallucination_risk=hallucination_risk,
        safety=safety,
        latency_ms=round(latency_ms, 3),
        cost_usd=round(cost_usd, 6),
    )
    return EvaluationVerdict(verdict=verdict, scores=scores, reasons=tuple(reasons))
