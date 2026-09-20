"""Lightweight tracing and structured logging for agentic workflows."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger("agentic_platform")


@dataclass(slots=True)
class SpanRecord:
    name: str
    duration_ms: float
    attributes: dict[str, object] = field(default_factory=dict)
    error: str | None = None


class InMemorySpanRecorder:
    def __init__(self) -> None:
        self._spans: list[SpanRecord] = []

    def record(self, span: SpanRecord) -> None:
        self._spans.append(span)

    @property
    def spans(self) -> tuple[SpanRecord, ...]:
        return tuple(self._spans)

    def total_duration_ms(self) -> float:
        return sum(s.duration_ms for s in self._spans)

    def clear(self) -> None:
        self._spans.clear()


_recorder = InMemorySpanRecorder()


def get_recorder() -> InMemorySpanRecorder:
    return _recorder


@contextmanager
def traced_span(name: str, **attributes: object) -> Iterator[SpanRecord]:
    start = time.perf_counter()
    record = SpanRecord(name=name, duration_ms=0.0, attributes=dict(attributes))
    try:
        yield record
    except Exception as exc:
        record.error = str(exc)
        raise
    finally:
        record.duration_ms = (time.perf_counter() - start) * 1000
        _recorder.record(record)
        logger.info(
            "span.completed",
            name=record.name,
            duration_ms=round(record.duration_ms, 3),
            error=record.error,
            **record.attributes,
        )
