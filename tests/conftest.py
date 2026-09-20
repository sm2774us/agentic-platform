from __future__ import annotations

import pytest

from agentic_platform.observability.tracing import get_recorder


@pytest.fixture(autouse=True)
def _clear_span_recorder() -> None:
    get_recorder().clear()
