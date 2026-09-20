from agentic_platform.eval.framework import EvalScores, EvaluationVerdict, Verdict
from agentic_platform.eval.mlflow_tracking import NullRunTracker


def test_null_tracker_records_calls() -> None:
    tracker = NullRunTracker()
    verdict = EvaluationVerdict(
        verdict=Verdict.PASS,
        scores=EvalScores(1.0, 0.0, 1.0, 5.0, 0.001),
        reasons=("ok",),
    )
    tracker.log_run(task="t", verdict=verdict)
    assert tracker.calls == [("t", verdict)]
