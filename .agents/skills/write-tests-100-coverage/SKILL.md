---
name: write-tests-100-coverage
description: Write tests that keep agentic-platform at 100% branch coverage without gaming the metric.
---

# Write tests to maintain 100% branch coverage

This repo enforces `--cov-fail-under=100` with `branch = true`. This skill
describes how to hit that bar honestly.

## Process

1. After writing/changing code, run:
   ```bash
   python -m pytest --cov-report=term-missing
   ```
   The `Missing` column shows exact uncovered line numbers and, for
   partial branches, `line->line` branch pairs (e.g. `67->76` means the
   branch from line 67 to line 76 was never taken).

2. **For a missing line**: write a test that exercises that code path
   directly. Prefer the smallest, most targeted test — one assertion, one
   scenario — over a large end-to-end test that happens to touch the line.

3. **For a missing branch** (`X->Y` in the report): you need a test where
   the condition takes the *other* path than your existing tests cover.
   Common cases in this codebase:
   - An `if`/`elif`/`else` chain in `eval/framework.py` — write one test
     per branch (see `test_eval_framework.py` for the pattern: one test per
     verdict path).
   - A `try`/`except` — write a test that triggers the exception (e.g.
     `test_graph_handles_blocked_tool_call` in `test_graph.py`).
   - A loop that sometimes runs zero times — test the empty-input case.

4. **When a branch is genuinely unreachable** (defensive code that cannot
   be triggered given the function's own invariants — e.g. see the comment
   above the `while` loop in `rag/pipeline.py`), mark it explicitly:
   ```python
   while start < len(words):  # pragma: no branch - loop always exits via the break below
   ```
   Always include a one-line justification in the pragma comment. **Never**
   add a blanket `# pragma: no cover` to a function just to make coverage
   pass — that hides real gaps. Only use it on lines you can justify are
   truly unreachable or untestable (e.g. an optional dependency's import
   line in `eval/mlflow_tracking.py`).

5. **Test placement**:
   - `tests/unit/` — one module in isolation, all collaborators faked/mocked.
   - `tests/integration/` — two or more real modules wired together (e.g.
     the graph + a real `HybridRetriever` + `MockLLMClient`).
   - `tests/e2e/` — through the FastAPI `TestClient`, full HTTP round-trip.

6. Use `MockLLMClient(settings, canned_responses={...})` for deterministic
   LLM behavior in tests — never call a real LLM API in the test suite.

7. Run `make ci` (lint + typecheck + test) before finishing — a change
   that hits 100% coverage but fails ruff/mypy is not done.
