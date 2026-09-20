---
name: add-fastapi-endpoint
description: Add a new endpoint to the agentic-platform FastAPI service in src/agentic_platform/api/main.py.
---

# Add a new FastAPI endpoint

## Steps

1. Define request/response models as pydantic `BaseModel` subclasses near
   the top of `api/main.py`, following the existing `TaskRequest` /
   `TaskResponse` pattern. Use `Field(min_length=..., max_length=...)` or
   similar validation constraints — don't accept unvalidated free text where
   a bound makes sense.

2. Use `Depends(get_pipeline)` (or a new dependency function, following the
   same generator pattern with `Iterator[...]`) to inject collaborators —
   never construct an `AgenticPipeline` or reach for global state directly
   inside a route handler. This is what makes routes testable via
   `app.dependency_overrides`.

3. Translate domain exceptions to HTTP status codes explicitly — see how
   `HumanApprovalRequiredError` maps to `409 Conflict`. Don't let internal
   exception types leak as unhandled 500s if there's a more meaningful
   status code.

4. Add the route with an explicit `response_model=...` so the OpenAPI schema
   and response validation stay accurate.

5. Write an e2e test in `tests/e2e/test_api.py` using `TestClient` and
   `app.dependency_overrides` to inject a fake/deterministic collaborator —
   never hit a real LLM or external service in e2e tests. Always clear
   `app.dependency_overrides` in a `finally` block so tests don't leak state
   into each other.

6. Run `make ci`.
