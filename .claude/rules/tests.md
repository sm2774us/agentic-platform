---
paths: ["tests/**"]
---

- Never call a real LLM API or make a real network request in any test.
- Use `MockLLMClient` for deterministic LLM behavior.
- Clear `app.dependency_overrides` in a `finally` block in e2e tests.
- One assertion focus per test function; prefer several small tests over
  one large test with many unrelated assertions.
