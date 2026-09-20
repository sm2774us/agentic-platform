"""MLflow integration for experiment tracking and run lineage."""

from __future__ import annotations

from typing import Protocol

from agentic_platform.eval.framework import EvaluationVerdict


class RunTracker(Protocol):
    def log_run(self, *, task: str, verdict: EvaluationVerdict) -> None: ...  # pragma: no cover


class NullRunTracker:
    """No-op tracker for tests and offline execution."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, EvaluationVerdict]] = []

    def log_run(self, *, task: str, verdict: EvaluationVerdict) -> None:
        self.calls.append((task, verdict))


class MlflowRunTracker:
    """Production tracker backed by the `mlflow` SDK (install the `mlflow` extra)."""

    def __init__(
        self, tracking_uri: str, experiment_name: str = "agentic-platform"
    ) -> None:  # pragma: no cover - requires optional dependency
        import mlflow

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        self._mlflow = mlflow

    def log_run(self, *, task: str, verdict: EvaluationVerdict) -> None:  # pragma: no cover
        with self._mlflow.start_run():
            self._mlflow.log_param("task", task)
            self._mlflow.log_metric("groundedness", verdict.scores.groundedness)
            self._mlflow.log_metric("hallucination_risk", verdict.scores.hallucination_risk)
            self._mlflow.log_metric("safety", verdict.scores.safety)
            self._mlflow.log_metric("latency_ms", verdict.scores.latency_ms)
            self._mlflow.log_metric("cost_usd", verdict.scores.cost_usd)
            self._mlflow.log_param("verdict", verdict.verdict.value)
