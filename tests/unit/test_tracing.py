import pytest

from agentic_platform.observability.tracing import get_recorder, traced_span


def test_traced_span_records_success() -> None:
    with traced_span("unit.test", foo="bar") as span:
        span.attributes["extra"] = 1
    recorder = get_recorder()
    assert recorder.spans[-1].name == "unit.test"
    assert recorder.spans[-1].error is None
    assert recorder.total_duration_ms() >= 0


def test_traced_span_records_error_and_reraises() -> None:
    with pytest.raises(ValueError), traced_span("unit.error"):
        raise ValueError("boom")
    recorder = get_recorder()
    assert recorder.spans[-1].error == "boom"
