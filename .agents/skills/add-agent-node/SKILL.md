---
name: add-agent-node
description: Add a new node (agent role) to the multi-agent SimpleGraph in agentic-platform, with routing and tests.
---

# Add a new agent node to the graph

Use this when asked to add a new step/role to the multi-agent pipeline
(e.g. a "fact-checker" node, a "summarizer" node, a "translator" node).

## Steps

1. **Add the role** to `AgentRole` in `src/agentic_platform/agents/state.py`
   if the new node represents a distinct conceptual role (not just a helper
   function).

2. **Write the node function** in `src/agentic_platform/agents/graph.py`
   inside `build_research_writer_graph` (or a new `build_*_graph` factory if
   this is a genuinely different pipeline shape). A node function has the
   signature `(state: AgentState) -> AgentState` — it must be pure with
   respect to everything except `state` (no hidden global mutation), and
   should call `state.add(role, content)` to log what it did.

3. **Wire it into `nodes` and `routers`** in the returned `SimpleGraph`.
   Routers are `(state: AgentState) -> str` functions returning the next
   node's key or `END`. Keep routing logic explicit and testable — avoid
   deeply nested conditionals in a router; extract a helper function if the
   condition is non-trivial.

4. **Respect `max_steps`.** The graph raises `GraphExecutionError` if
   `max_steps` is exceeded — this is a deliberate safety rail against
   infinite agent loops. Don't raise `max_steps` casually; if a legitimate
   workflow needs more steps, that's a signal to reconsider the graph shape.

5. **Write tests** (see skill `write-tests-100-coverage`):
   - A unit test if the node has meaningful logic in isolation.
   - An integration test in `tests/integration/test_graph.py` exercising the
     new node as part of a full graph run.
   - Cover both the "happy path" and any error/edge branch your node
     introduces (e.g. what happens when its dependency returns nothing).

6. **Run `make ci`** before considering the task done. 100% coverage is
   enforced — a new node with an untested branch will fail the build.

## Anti-patterns to avoid

- Don't call `llm.complete()` or any tool directly from a router function —
  routers should only inspect `state`, not perform side effects.
- Don't introduce a new sensitive tool call without registering it with
  `sensitive=True` in the `ToolRegistry` and confirming the human-in-the-loop
  path is tested (see `HumanApprovalRequiredError`).
