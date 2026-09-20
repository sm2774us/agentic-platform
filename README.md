# Agentic Platform

[![CI](https://github.com/sm2774us/agentic-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/sm2774us/agentic-platform/actions)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://codecov.io/gh/sm2774us/agentic-platform)
[![Python](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/)
[![Type checked: mypy strict](https://img.shields.io/badge/mypy-strict-blue)](https://github.com/sm2774us/agentic-platform/blob/main/pyproject.toml)
[![Linting: ruff](https://img.shields.io/badge/lint-ruff-orange)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)](https://github.com/sm2774us/agentic-platform/blob/main/LICENSE)

A production-grade **multi-agent orchestration platform**: a supervisor/worker
agent graph (LangGraph-shaped API), a hybrid retrieval-augmented-generation
(RAG) pipeline, an auditable tool registry with human-in-the-loop gating, an
LLMOps evaluation framework (groundedness, hallucination risk, safety,
latency, cost), MLflow experiment tracking, OpenTelemetry-style tracing, and
a FastAPI service layer — all fully typed, 100%-tested, and CI/CD-ready.

This repository is designed as a **reference implementation** for the kind
of agentic AI systems built at scale by senior/lead AI engineering teams: it
demonstrates end-to-end ownership from proof-of-concept agent logic through
production deployment concerns (fault tolerance, observability, evaluation
gates, containerization, and branch-protected CI).

---

## Table of Contents

- [Architecture](#architecture)
- [Why these design choices](#why-these-design-choices)
- [Getting Started (complete, no prior setup assumed)](#getting-started-complete-no-prior-setup-assumed)
  - [Windows 11 (native PowerShell)](#windows-11-native-powershell)
  - [Windows 11 (WSL2 + Ubuntu)](#windows-11-wsl2--ubuntu-recommended)
  - [Ubuntu (native / bare metal / VM)](#ubuntu-native--bare-metal--vm)
  - [Troubleshooting quick reference](#troubleshooting-quick-reference)
- [Project layout](#project-layout)
- [Running the service](#running-the-service)
- [Testing, linting, type-checking](#testing-linting-type-checking)
- [Evaluation framework](#evaluation-framework)
- [Observability](#observability)
- [Extending to a real LLM provider](#extending-to-a-real-llm-provider)
- [Extending to LangGraph / CrewAI / AutoGen](#extending-to-langgraph--crewai--autogen)
- [CI/CD and branch protection](#cicd-and-branch-protection)
- [Docker](#docker)
- [AI-assisted development setup](#ai-assisted-development-setup)
- [Roadmap](#roadmap)

---

## Architecture

```
                         ┌─────────────────────────┐
                         │   FastAPI Service Layer   │
                         │  /healthz /readyz /v1/*   │
                         └────────────┬─────────────┘
                                      │
                         ┌────────────▼─────────────┐
                         │      AgenticPipeline       │  orchestration/pipeline.py
                         │  (facade: wires everything)│
                         └────────────┬─────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
┌───────▼────────┐          ┌─────────▼─────────┐          ┌────────▼────────┐
│  Multi-Agent     │          │   Hybrid RAG        │          │  Tool Registry   │
│  Graph (Simple-  │◄────────►│   Pipeline           │          │  (audited, HITL-  │
│  Graph engine,   │  context │   (dense + lexical   │          │  gated for        │
│  LangGraph-shaped│          │   retrieval)         │          │  sensitive ops)   │
│  API)            │          └──────────────────────┘          └──────────────────┘
│                  │
│  supervisor      │
│    ↓             │
│  researcher      │──► search_knowledge_base tool, RAG retrieval
│    ↓             │
│  writer          │──► LLMClient.complete() (provider-agnostic)
│    ↓             │
│  reviewer        │──► groundedness self-check, HITL flag
└──────────────────┘
        │
        ▼
┌──────────────────┐        ┌──────────────────────┐
│  Evaluation Gate   │───────►│  MLflow Run Tracker    │
│  groundedness,     │        │  (experiment lineage,  │
│  hallucination,    │        │   metrics per run)      │
│  safety, cost,      │        └──────────────────────┘
│  latency            │
└──────────────────┘
        │
        ▼
   PASS / NEEDS_HUMAN_REVIEW / REJECT
```

Every arrow above is a real, tested code path — not aspirational
documentation. Run `make test` to see it exercised end-to-end.

## Why these design choices

| Decision | Rationale |
|---|---|
| **Protocol-based `LLMClient`** instead of a hard SDK dependency | Swapping Anthropic ↔ OpenAI ↔ a fine-tuned local model touches zero business logic. Tests run hermetically with `MockLLMClient` — no API keys, no network, no flakiness in CI. |
| **`SimpleGraph` engine mirroring LangGraph's API** | The node/edge/conditional-routing shape is identical to `langgraph.graph.StateGraph`. Swapping in real LangGraph for production scale (checkpointing, streaming, human-in-the-loop interrupts) is a drop-in change — node functions already take/return `AgentState`. |
| **Auditable `ToolRegistry` with sensitivity flags** | Every tool call is logged; sensitive tools (schema migrations, auth changes, payments) are blocked pending human approval by default. This directly encodes the "rigorous human-in-the-loop review for database schema migrations and auth logic" requirement common to platform/infra-adjacent agentic systems. |
| **Hybrid dense+lexical retrieval** | Pure embedding search misses exact-match terms (IDs, SKUs, error codes). Pure lexical search misses semantic paraphrase. Combining both is standard production practice; the `dense_weight` is tunable per use case. |
| **Deterministic hashing-based embeddings in the reference impl** | Keeps the whole platform dependency-light and 100%-testable offline. The `HybridRetriever` interface is unchanged when you swap in `text-embedding-3-large` / Voyage / Cohere + pgvector/Pinecone. |
| **Explicit `EvaluationVerdict` gate (`PASS` / `NEEDS_HUMAN_REVIEW` / `REJECT`)** | LLM outputs are probabilistic; shipping them safely at scale requires an automated quality bar, not vibes. This mirrors the evaluation-gate pattern used before any agent response reaches a customer. |
| **Structured span tracing (`traced_span`)** | Every agent step, tool call, and LLM invocation is independently observable — latency, errors, and attributes are captured per unit of work, the same shape as an OpenTelemetry span, so swapping in a real OTLP exporter is a one-file change (`observability/tracing.py`). |
| **100% branch coverage, not just line coverage** | `pyproject.toml` sets `--cov-fail-under=100` with `branch = true`. A few genuinely unreachable defensive lines are marked `# pragma: no cover` with an explanation — coverage should measure real risk, not be gamed. |

## Getting Started (complete, no prior setup assumed)

This section assumes **nothing** is installed yet. Pick the path that
matches your machine: [Windows 11 (native PowerShell)](#windows-11-native-powershell),
[Windows 11 (WSL2 + Ubuntu)](#windows-11-wsl2--ubuntu-recommended), or
[Ubuntu (native / bare metal / VM)](#ubuntu-native--bare-metal--vm).

If you don't know which to pick: **use WSL2** (second option). Nearly all
production Python tooling, the AI CLI agents (Claude Code, Codex), and this
project's `Makefile` and hook scripts are built Linux-first — WSL2 gets you
that environment while still using your normal Windows desktop, VS Code,
and files. Pure-Windows PowerShell works too, but a few conveniences
(`make`, bash hooks) need extra steps documented below.

Every path below installs the exact same three prerequisites:
**Git**, **Python 3.12 or 3.13**, and (optionally but recommended)
**`make`**. Nothing else is required to run the platform — no database,
no external API keys, no cloud account. The default configuration uses a
fully offline, deterministic mock LLM so `make test` and `make run` work
with zero setup.

---

### Windows 11 (native PowerShell)

**1. Install prerequisites with `winget`** (winget ships with Windows 11 by
default — open PowerShell and check with `winget --version`; if missing,
install "App Installer" from the Microsoft Store first).

```powershell
# Git
winget install --id Git.Git -e --source winget

# Python 3.12 (or use 3.13 — both are supported; see note below)
winget install --id Python.Python.3.12 -e --source winget

# GNU Make (the Makefile shortcuts like `make test` won't work without this)
winget install --id GnuWin32.Make -e --source winget
```

**Close and reopen PowerShell** after installing so your `PATH` picks up
the new tools. Verify each one:

```powershell
git --version      # e.g. git version 2.47.0
py --list          # should show -V:3.12 (and 3.13 if you installed it)
make --version     # e.g. GNU Make 3.81
```

> **If `make` still isn't found after reopening the terminal:** winget's
> GnuWin32 package sometimes doesn't add itself to `PATH` automatically.
> Add `C:\Program Files (x86)\GnuWin32\bin` to your PATH manually
> (Start → "Edit the system environment variables" → Environment
> Variables → select `Path` under your user account → New → paste that
> folder → OK → reopen PowerShell). Alternatively, skip `make` entirely —
> see [Running commands without `make`](#running-commands-without-make-windows-native)
> below.

**2. Clone the repo and set up the virtual environment:**

```powershell
git clone <your-fork-url> agentic-platform
cd agentic-platform
py -3.12 -m venv .venv
.venv\Scripts\activate
```

Your prompt should now show `(.venv)` at the start of the line. If
PowerShell blocks the activation script with an "execution policy" error,
run this once (as your normal user, not admin) and try activating again:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**3. Install the project and run the checks:**

```powershell
pip install -e ".[dev]"
make test          # 65 tests, must show "100% coverage"
make lint          # ruff — should print "All checks passed!"
make typecheck     # mypy --strict — should print "Success: no issues found"
make run           # starts the API at http://localhost:8000
```

#### Running commands without `make` (Windows-native)

If you'd rather not install `make`, every `make <target>` has a direct
equivalent — these are exactly what CI runs, so there's no ambiguity:

| `make` target | Direct command |
|---|---|
| `make install` | `pip install -e ".[dev]"` |
| `make test` | `python -m pytest` |
| `make lint` | `ruff check .` |
| `make typecheck` | `mypy src` |
| `make ci` | `ruff check . ; mypy src ; python -m pytest` |
| `make run` | `uvicorn agentic_platform.api.main:app --reload --port 8000` |
| `make docker-build` | `docker build -t agentic-platform:local .` |

**4. Try the API** (in a second PowerShell window, with `.venv` activated
and `make run` / `uvicorn` still running in the first):

```powershell
curl.exe -X POST http://localhost:8000/v1/agent/run `
  -H "Content-Type: application/json" `
  -d '{\"task\": \"what is the refund policy\"}'
```

(Use `curl.exe` explicitly on Windows — plain `curl` is often aliased to
PowerShell's `Invoke-WebRequest`, which uses different flag syntax.)

---

### Windows 11 (WSL2 + Ubuntu) — recommended

This gives you a real Ubuntu Linux environment running inside Windows 11,
with full access to your Windows files, VS Code, and browser — while every
command below matches the [Ubuntu section](#ubuntu-native--bare-metal--vm)
exactly. This is also the easiest path to running the **Claude Code** and
**OpenAI Codex** CLIs from `docs/AI_TOOL_STRATEGY.md`, since both are
Linux/macOS-first tools.

**1. Install WSL2** (one-time, requires a restart):

```powershell
wsl --install
```

This installs WSL2 and Ubuntu by default. Restart your PC when prompted.
After restarting, Ubuntu will finish setting up and ask you to create a
Linux username and password (separate from your Windows login — pick
anything, you'll use it for `sudo` commands).

If `wsl --install` reports WSL is already installed but you have no Linux
distro yet:

```powershell
wsl --install -d Ubuntu
```

Verify it worked:

```powershell
wsl --list --verbose
# should show "Ubuntu" with VERSION 2
```

**2. Open your Ubuntu terminal.** Click Start → type "Ubuntu" → open it (or
just type `wsl` in PowerShell). From here on, **every command is identical
to the [Ubuntu (native)](#ubuntu-native--bare-metal--vm) section below** —
jump there and follow it exactly, then come back here for the two
Windows-specific notes below.

**Note A — where to put the project:** clone the repo inside the Linux
filesystem (e.g. `~/projects/agentic-platform`), **not** under `/mnt/c/...`.
Files on the Windows drive accessed from WSL are dramatically slower for
things like `pip install` and `pytest`. You can still open the folder in
VS Code with `code .` from inside WSL (installs the "WSL" extension
automatically), and VS Code will edit the Linux-side files directly.

**Note B — accessing the API from Windows:** WSL2 automatically forwards
`localhost` between Windows and Ubuntu, so once `make run` is running
inside WSL, `http://localhost:8000` works from your normal Windows browser
or from a Windows PowerShell `curl.exe` — no extra networking setup needed.

---

### Ubuntu (native / bare metal / VM)

Works identically whether this is a real Ubuntu machine, a VM, or your WSL2
Ubuntu terminal from above. Tested on Ubuntu 22.04/24.04.

**1. Update package lists and install prerequisites:**

```bash
sudo apt update
sudo apt install -y git make python3.12 python3.12-venv python3-pip
```

> **If `python3.12` isn't available** (older Ubuntu releases only ship
> 3.10 or 3.11 by default), add the deadsnakes PPA first:
> ```bash
> sudo apt install -y software-properties-common
> sudo add-apt-repository -y ppa:deadsnakes/ppa
> sudo apt update
> sudo apt install -y python3.12 python3.12-venv
> ```

Verify:

```bash
git --version
python3.12 --version
make --version
```

**2. Clone the repo and set up the virtual environment:**

```bash
git clone <your-fork-url> agentic-platform
cd agentic-platform
python3.12 -m venv .venv
source .venv/bin/activate
```

Your prompt should now show `(.venv)` at the start of the line.

**3. Install the project and run the checks:**

```bash
pip install --upgrade pip
pip install -e ".[dev]"
make test          # 65 tests, must show "100% coverage"
make lint          # ruff — should print "All checks passed!"
make typecheck     # mypy --strict — should print "Success: no issues found"
make run           # starts the API at http://localhost:8000
```

**4. Try the API** (open a second terminal, `source .venv/bin/activate`
is not needed for `curl` since it's just an HTTP call):

```bash
curl -X POST http://localhost:8000/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{"task": "what is the refund policy"}'
```

You should get back a JSON response with a `final_answer`, a `verdict`
(`pass` / `needs_human_review` / `reject`), and quality scores. Press
`Ctrl+C` in the first terminal to stop the server when you're done.

---

### Python 3.12 vs 3.13

`pyproject.toml` declares `requires-python = ">=3.12"`, so **Python 3.13
works too** — swap `python3.12` → `python3.13` (Ubuntu/WSL2) or
`py -3.13` (Windows native) in every command above. This project's CI
(`.github/workflows/ci.yml`) currently pins 3.12 as the tested version;
nothing in the codebase relies on a 3.12-only feature, but if you hit a
dependency-wheel issue on 3.13 (occasionally a transitive package hasn't
published 3.13 wheels yet), fall back to 3.12.

### Troubleshooting quick reference

| Symptom | Fix |
|---|---|
| `'make' is not recognized...` (Windows) | Install via `winget install GnuWin32.Make`, reopen terminal, or use the [no-`make` command table](#running-commands-without-make-windows-native) above. |
| PowerShell: `.venv\Scripts\activate` fails with an execution-policy error | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once, then retry. |
| `python3.12: command not found` (Ubuntu) | Add the deadsnakes PPA — see step 1 above. |
| `pip install -e ".[dev]"` fails on 3.13 with a build error for one dependency | Retry with `python3.12`/`py -3.12` instead — a transitive dependency may not have 3.13 wheels yet. |
| WSL2: `pytest` is very slow | You likely cloned the repo under `/mnt/c/...`. Move it into the Linux filesystem (`~/projects/...`) instead — see Note A above. |
| `curl` on Windows gives a syntax/parameter error | Use `curl.exe` explicitly, not bare `curl` (which PowerShell aliases to `Invoke-WebRequest`). |
| Port 8000 already in use | Run on a different port: `uvicorn agentic_platform.api.main:app --port 8001`. |

## Project layout

```
agentic-platform/
├── src/agentic_platform/
│   ├── agents/          # AgentState contract + multi-agent SimpleGraph (LangGraph-shaped)
│   ├── orchestration/   # LLMClient protocol + AgenticPipeline facade
│   ├── rag/             # chunking + hybrid (dense/lexical) retrieval
│   ├── tools/           # auditable ToolRegistry with HITL gating
│   ├── eval/            # evaluation gate (groundedness/hallucination/safety/cost) + MLflow
│   ├── observability/   # span tracing / structured logging
│   ├── config/          # pydantic-settings, env-driven, fail-fast
│   └── api/             # FastAPI service (health/ready/run/config endpoints)
├── tests/
│   ├── unit/            # one module under test at a time, fully isolated
│   ├── integration/     # graph + pipeline wired together
│   └── e2e/             # FastAPI TestClient, full HTTP round-trip
├── .github/workflows/ci.yml     # lint, typecheck, test, build, docker — all gated
├── .github/branch-protection.md # exact settings + `gh api` command to enforce them
├── .github/instructions/        # Copilot path-scoped rules (applyTo:)
├── Dockerfile            # multi-stage, non-root, healthcheck
├── Makefile
├── pyproject.toml        # ruff + mypy strict + pytest 100%-coverage gate, single source of truth
│
│   ── AI coding tool configuration (works under Scenarios 1, 2, or 3) ──
├── AGENTS.md             # canonical instructions for Codex + Copilot + Claude Code
├── CLAUDE.md             # one line: @AGENTS.md
├── .mcp.json             # MCP servers — Claude Code, Copilot CLI, VS Code 1.118+
├── .agents/skills/       # canonical skills (Codex + Copilot read natively)
├── .claude/              # Claude Code: settings.json, agents/, rules/, skills/ (stubs)
├── .codex/               # Codex: config.toml (MCP mirror), hooks.json, agents/ (TOML)
├── docs/AI_TOOL_STRATEGY.md  # capability matrix + cost tradeoffs + decision heuristic
├── ubuntu/SETUP.md       # Ubuntu install steps for all three tools
└── win11/SETUP.md        # Windows 11 install steps (incl. symlink/WSL2 caveats)
```

## Running the service

```bash
uvicorn agentic_platform.api.main:app --reload --port 8000
```

| Endpoint | Method | Purpose |
|---|---|---|
| `/healthz` | GET | Liveness probe |
| `/readyz` | GET | Readiness probe (confirms pipeline construction succeeded) |
| `/v1/config` | GET | Non-secret runtime configuration summary |
| `/v1/agent/run` | POST | Run the multi-agent graph on a task, return the graded answer |

`POST /v1/agent/run` request/response:

```jsonc
// request
{ "task": "what is the refund policy" }

// response
{
  "final_answer": "...",
  "verdict": "pass",                 // pass | needs_human_review | reject
  "requires_human_review": false,
  "scores": {
    "groundedness": 0.76,
    "hallucination_risk": 0.24,
    "safety": 1.0,
    "latency_ms": 0.66,
    "cost_usd": 0.0003
  }
}
```

A `409 Conflict` is returned if the agent attempts a sensitive tool call
that requires human approval (see `HumanApprovalRequiredError`).

## Testing, linting, type-checking

```bash
make test        # pytest: unit + integration + e2e, 100% branch coverage gate
make lint         # ruff check .
make typecheck    # mypy --strict src
make ci           # all three, exactly as CI runs them
```

Coverage is enforced in `pyproject.toml` (`--cov-fail-under=100`,
`branch = true`) — a PR that drops coverage fails CI outright, not just a
warning.

## Evaluation framework

`agentic_platform.eval.framework.evaluate_run` scores every completed agent
run on:

- **Groundedness** — lexical-overlap proxy between the answer and retrieved
  context (swap for an NLI/LLM-judge model in production; interface unchanged).
- **Hallucination risk** — `1 - groundedness`, gated against
  `Settings.hallucination_score_threshold`.
- **Safety** — flags known unsafe/prompt-injection markers; extend
  `_UNSAFE_MARKERS` or swap in a moderation-API-backed check.
- **Latency & cost** — measured directly from the graph run and gated
  against `Settings.cost_budget_usd_per_request`.

The result is a single `EvaluationVerdict.verdict`: `PASS`,
`NEEDS_HUMAN_REVIEW`, or `REJECT` — the same three-way gate used to decide
whether an agent's output can ship automatically, needs a human in the
loop, or must be blocked.

## Observability

Every agent step, tool call, and LLM invocation is wrapped in
`traced_span(...)`, which records duration, attributes, and errors to an
`InMemorySpanRecorder` (swappable for a real OTLP exporter without touching
call sites) and emits a structured `structlog` log line. This gives full
request-level tracing for latency/cost/error debugging in production.

## Extending to a real LLM provider

`orchestration/llm_client.py` defines `LLMClient` as a `Protocol`. To wire
in Anthropic:

```python
import anthropic
from agentic_platform.orchestration.llm_client import LLMClient, LLMResponse


class AnthropicLLMClient:
    def __init__(self, settings: Settings) -> None:
        self._client = anthropic.Anthropic()
        self._model = settings.llm_model_name

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResponse:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )
        return LLMResponse(
            text=msg.content[0].text,
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
            model=self._model,
        )
```

Then add a branch in `build_llm_client()`. No other file changes.

## Extending to LangGraph / CrewAI / AutoGen

`agents/graph.py`'s node functions already take/return `AgentState` and are
engine-agnostic. To move to real LangGraph:

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(AgentState)
graph.add_node("supervisor", supervisor)
graph.add_node("researcher", researcher)
graph.add_node("writer", writer)
graph.add_node("reviewer", reviewer)
graph.set_entry_point("supervisor")
graph.add_conditional_edges(
    "supervisor", route_after_supervisor, {"researcher": "researcher", END: END}
)
graph.add_edge("researcher", "writer")
graph.add_edge("writer", "reviewer")
graph.add_edge("reviewer", END)
compiled = graph.compile()
```

This unlocks LangGraph's checkpointing, streaming, and interrupt-based
human-in-the-loop primitives for larger production deployments. Install
with `pip install -e ".[langgraph]"`.

## CI/CD and branch protection

`.github/workflows/ci.yml` runs four gated jobs on every PR: **lint**
(ruff), **typecheck** (mypy --strict), **test** (100% coverage gate), and
**build** (wheel + Docker image). `.github/branch-protection.md` documents
the exact settings — and the `gh api` command — to require all of them
before merge to `main`, including admin enforcement and signed commits.

`.pre-commit-config.yaml` runs the same ruff/mypy/pytest checks locally
before a commit is even made:

```bash
pip install pre-commit
pre-commit install
```

## Docker

```bash
make docker-build
docker run -p 8000:8000 agentic-platform:local
```

Multi-stage build, non-root user, health check, and `mlflow` extra baked
into the runtime image for out-of-the-box experiment tracking.

## AI-assisted development setup

This repository is a **single consolidated project**: the production
multi-agent platform *and* the cross-tool AI coding configuration
(Claude Code, GitHub Copilot, OpenAI Codex) ship together, wired to work
under any of three engineering-team tool decisions without any code or
config changes:

| Scenario | Tools | Best for |
|---|---|---|
| 1 | Claude Code + OpenAI Codex + GitHub Copilot | Maximum capability, well-funded teams |
| 2 (default) | Claude Code + GitHub Copilot | Balanced autonomy + inline velocity at 2/3 the cost |
| 3 | OpenAI Codex + GitHub Copilot | Lean local footprint, async/ticket-driven workflows |

See **[`docs/AI_TOOL_STRATEGY.md`](docs/AI_TOOL_STRATEGY.md)** for the full
capability matrix (terminal-native reasoning vs. cloud-sandbox long-horizon
execution vs. inline predictive pair programming), cost tradeoffs, and a
decision heuristic — then **[`ubuntu/SETUP.md`](ubuntu/SETUP.md)** or
**[`win11/SETUP.md`](win11/SETUP.md)** for exact install commands on your OS.

The shared layer every scenario uses:

- **`AGENTS.md`** (repo root) — single source of truth for project
  instructions, read natively by Codex and Copilot; imported by
  **`CLAUDE.md`** (`@AGENTS.md`) for Claude Code.
- **`.agents/skills/`** — canonical, codebase-specific skills
  (`add-agent-node`, `add-rag-source`, `write-tests-100-coverage`,
  `add-fastapi-endpoint`), read natively by Codex and Copilot; thin stubs
  in `.claude/skills/` point Claude Code at the same canonical files.
- **`.mcp.json`** — one MCP server config, read by Claude Code, Copilot
  CLI, and VS Code 1.118+; mirrored by hand into `.codex/config.toml`'s
  TOML tables for Codex (which doesn't read `.mcp.json` or interpolate
  `${VAR}` — see `env_vars` there for secrets).
- **`scripts/hooks/guard-sensitive-commands.sh`** — one shared
  pre-tool-use hook script, registered separately in
  `.claude/settings.json` (Claude Code + Copilot CLI) and
  `.codex/hooks.json` (Codex), blocking destructive commands
  (`rm -rf /`, `git push --force`, `DROP TABLE`, etc.) from unattended
  agent execution.
- **Per-tool custom agents** enforcing the same human-in-the-loop rules
  from `AGENTS.md`: `.claude/agents/reviewer.md` (Markdown/YAML, also read
  by Copilot) and `.codex/agents/reviewer.toml` (Codex's TOML format).
- **Path-scoped rules** for `tests/**` in both formats:
  `.claude/rules/tests.md` (`paths:` frontmatter) and
  `.github/instructions/tests.instructions.md` (`applyTo:` frontmatter,
  Copilot's broadest-coverage format including code review).

Nothing here needs to be toggled to switch scenarios — each tool simply
reads the subset of files it understands. To visibly lean out the repo
after deciding, `rm -rf .codex` (Scenario 2) or `rm -rf .claude CLAUDE.md`
(Scenario 3); `AGENTS.md`, `.agents/skills/`, and `.mcp.json` stay either way.

## Roadmap

- [ ] Real vector store backend (pgvector / Pinecone) behind the same `HybridRetriever` interface
- [ ] LangGraph checkpointing for durable, resumable multi-turn agent sessions
- [ ] LLM-judge-based groundedness scoring (Ragas/DeepEval) behind the same `evaluate_run` signature
- [ ] OpenTelemetry OTLP exporter wired to `traced_span`
- [ ] Streaming responses (SSE) from `/v1/agent/run`
- [ ] Per-tenant cost budgets and rate limiting middleware

---

**License:** MIT — see [LICENSE](LICENSE).
