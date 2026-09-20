# AGENTS.md — agentic-platform

Canonical, shared instructions for **Claude Code**, **GitHub Copilot** (agent
mode, VS Code + CLI), and **OpenAI Codex** (CLI, IDE extension, ChatGPT
desktop app working in this repo). This file is the single source of truth;
`CLAUDE.md` imports it with `@AGENTS.md`. Do not duplicate this content
elsewhere — edit here only.

## Project

`agentic-platform` is a production multi-agent orchestration platform:
a supervisor→researcher→writer→reviewer agent graph, hybrid RAG retrieval,
an auditable tool registry, an LLMOps evaluation gate, and a FastAPI service.
Stack: Python 3.12+, FastAPI, pydantic v2, pytest, ruff, mypy --strict.

## Non-negotiable engineering bar

- **100% branch test coverage is enforced** (`pyproject.toml`,
  `--cov-fail-under=100`). Any change to `src/` must ship with tests that
  keep coverage at 100%. Run `make test` before considering a task done.
- **`ruff check .` and `mypy src` must be clean** before any commit. Run
  `make ci` (lint + typecheck + test) as your final self-check.
- **Never weaken a test to make it pass.** If a test fails, fix the code or
  fix a genuinely wrong test expectation — never delete assertions to get
  green.
- Every module, function, and class needs a docstring explaining *why*, not
  just *what* — see existing files in `src/agentic_platform/` for the
  expected tone and depth.
- Prefer editing/extending existing modules over creating parallel ones.
  Check `src/agentic_platform/` structure below before adding a new file.

## Architecture map (read before editing)

```
src/agentic_platform/
├── agents/          # AgentState + SimpleGraph (LangGraph-shaped multi-agent engine)
├── orchestration/   # LLMClient protocol + AgenticPipeline facade
├── rag/             # chunking + hybrid (dense/lexical) retrieval
├── tools/           # auditable ToolRegistry, human-in-the-loop gating
├── eval/            # evaluation gate (groundedness/hallucination/safety/cost) + MLflow
├── observability/   # span tracing / structured logging
├── config/          # pydantic-settings, env-driven
└── api/             # FastAPI service
```

Full architecture rationale is in `README.md` — read it before making
structural changes.

## Human-in-the-loop requirements (STRICT)

The following categories of change require an explicit human review and
approval **before** being merged, regardless of which AI tool authored them:

- Any change to `src/agentic_platform/tools/registry.py`'s `sensitive`
  flags, or to what counts as a "sensitive" tool.
- Any database schema migration or migration tooling.
- Any change to authentication, authorization, or secrets handling.
- Any change to `.github/workflows/ci.yml` that removes or weakens a
  required check.
- Any change to `pyproject.toml`'s `--cov-fail-under` threshold.

An AI agent must **stop and ask for explicit human approval** before
proposing changes in these areas — do not just implement and open a PR.

## AI tool strategy (read this if you're deciding which agent to run)

This repo supports three engineering-team tool decisions — Claude Code +
Codex + Copilot, Claude Code + Copilot, or Codex + Copilot — without any
config changes. See `docs/AI_TOOL_STRATEGY.md` for the full capability
matrix, cost tradeoffs, and a decision heuristic. Whichever tool is driving
this session, this `AGENTS.md` is your shared source of truth regardless.

## Common workflows (see `.agents/skills/` for full playbooks)

- **Add a new agent node to the graph** → skill `add-agent-node`
- **Add a new RAG data source** → skill `add-rag-source`
- **Write tests to keep 100% coverage** → skill `write-tests-100-coverage`
- **Add a new FastAPI endpoint** → skill `add-fastapi-endpoint`

## Commands

- Install: `pip install -e ".[dev]"`
- Test: `make test` (or `python -m pytest`)
- Lint: `make lint` (or `ruff check .`)
- Type check: `make typecheck` (or `mypy src`)
- Full gate: `make ci`
- Run locally: `make run` (http://localhost:8000)

## Style

- Line length 100 (ruff-enforced). `from __future__ import annotations` at
  the top of every module. Modern typing (`str | None`, not `Optional[str]`).
  `@dataclass(slots=True)` for internal value objects; pydantic `BaseModel`
  only at API/config boundaries.
- No bare `except Exception` outside `observability/tracing.py`'s
  `traced_span` context manager, which intentionally re-raises after
  recording.
