# AI Coding Tool Strategy: Economic Viability vs. Productivity

This repository is wired to work under **any** of three engineering-team
tool decisions, without code or config rewrites. Pick a scenario below
based on budget, team size, and workload shape; the shared
`AGENTS.md` / `.agents/skills/` / `.mcp.json` layer works identically in
all three.

## Capability matrix

| Feature / Attribute | Claude Code | OpenAI Codex (2026 Engine) | GitHub Copilot / Workspace |
|---|---|---|---|
| Primary interface | Terminal-native CLI / shell agent | Cloud sandbox / autonomous worker | Inline IDE integration & chat panels |
| Operational paradigm | Command-line agent loops & file edits | "Long-horizon" project execution | Real-time predictive pair programming |
| Model access | Locked to Anthropic (Sonnet/Opus) | Locked to OpenAI (GPT/Codex engines) | Multi-model switcher (OpenAI, Anthropic, Google) |
| Best for | Deep repo-wide reasoning, local automation | Fire-and-forget async tasks, massive migrations | Inline autocomplete, real-time collaboration |
| Cost shape | Per-session/API usage, local compute | Cloud compute + async job budget | Flat per-seat subscription |

### Where each tool shines

**Claude Code** — deep reasoning on massive systems (tracing bugs and
dependencies across a large repo), terminal-native automation (`/init`,
autonomous test-fix loops: run tests → read stack trace → patch → re-run),
local scripting (migrations, DB checks, piping straight into `git`).

**OpenAI Codex** — asynchronous "fire-and-forget" operations (hand it a
goal from a ticket, walk away, it opens a finished PR), heavy cloud
computation for sprawling parallel refactors, massive structural
migrations (Python 2→3, legacy-language ports) needing multi-hour isolated
execution.

**GitHub Copilot** — frictionless inline autocomplete during active typing,
flexible model arbitrage (switch the IDE chat backend between OpenAI,
Anthropic, Google per-problem), ecosystem-wide collaboration via
Copilot Workspace + MCP pulling live context from Slack/Projects/docs.

## The three supported scenarios

This repo's config layer (`AGENTS.md`, `.agents/skills/`, `.mcp.json`,
`.claude/`, `.codex/`, `.github/instructions/`) supports all three without
modification — each tool simply reads the subset of files it understands
and ignores the rest. Nothing needs to be deleted or toggled to switch
scenarios; unused per-tool folders are simply dormant.

### Scenario 1 — Claude Code + OpenAI Codex + GitHub Copilot (maximum capability)

**Choose when:** productivity and iteration speed matter more than
per-seat cost — well-funded teams, high-complexity systems, or a
transitional period evaluating all three before standardizing.

- **Claude Code** for repo-wide reasoning, terminal-native automation, and
  the `reviewer` custom agent (`.claude/agents/reviewer.md`) gating
  sensitive changes locally before commit.
- **OpenAI Codex** for async, fire-and-forget work: hand it a GitHub issue
  (`.codex/agents/reviewer.toml` mirrors the same review gate), let it run
  in its cloud sandbox, come back to a PR.
- **GitHub Copilot** in the IDE for moment-to-moment autocomplete and
  quick multi-model chat during active development.
- **Cost:** highest — three subscriptions/usage tiers running in parallel.
  Justify by measuring: PR cycle time, time-to-first-passing-test, and
  developer-reported flow-state interruptions before vs. after.

### Scenario 2 — Claude Code + GitHub Copilot (balanced default)

**Choose when:** you want strong autonomous terminal capability plus
in-editor velocity, without paying for a second cloud-agent product.

- **Claude Code** covers everything Codex would have covered for teams
  not yet running fully-autonomous cloud/async workflows: deep debugging,
  test-fix loops, migration scripting — just triggered manually rather
  than fire-and-forget.
- **GitHub Copilot** covers inline completion and quick chat, with the
  option to point its chat panel at Claude models too (model arbitrage),
  narrowing the capability gap versus Scenario 1 at lower cost.
- **This is the recommended default** for most teams: it covers the two
  highest-frequency workflows (autonomous terminal work, inline
  assistance) at two-thirds the tool cost of Scenario 1.
- Delete or ignore `.codex/` if your org wants a visibly leaner repo —
  it is inert without the Codex CLI installed regardless.

### Scenario 3 — OpenAI Codex + GitHub Copilot (cloud-first, lean local footprint)

**Choose when:** the team is optimizing for minimal local/terminal AI
footprint and prefers async, ticket-driven agent workflows over
interactive terminal sessions — e.g., a team already running most of its
engineering process through GitHub Issues/PRs rather than local CLI loops.

- **OpenAI Codex** takes ticket-shaped, well-scoped async work end-to-end
  (migrations, sprawling refactors, "fix this and open a PR").
  `.codex/agents/reviewer.toml` still enforces the human-in-the-loop gate
  from `AGENTS.md` for sensitive changes.
  `project_doc_max_bytes` is already raised in `.codex/config.toml` to
  avoid the 32 KiB `AGENTS.md` truncation trap.
- **GitHub Copilot** covers the interactive/inline gap Claude Code would
  otherwise fill — day-to-day autocomplete and IDE chat, with model
  arbitrage available if Codex's suggestions stall.
- **Cost:** lower local compute/session overhead than Scenario 1 or 2
  since there's no long-running local terminal-agent loop; cost shifts to
  Codex's cloud/async job budget, which is usage-metered rather than
  interactive-session-metered — cheaper for bursty, ticket-driven work.
- Delete or ignore `.claude/` if your org wants a visibly leaner repo — it
  is inert without the Claude Code CLI installed regardless.

## Decision heuristic

```
                     Is most AI-assisted work interactive/local (terminal)?
                                  /                            \
                               YES                              NO
                                /                                 \
                Budget allows 3 tools?                 GitHub Copilot +
                    /            \                      OpenAI Codex
                  YES             NO                    (Scenario 3)
                   |               |
        Claude Code + Codex   Claude Code +
          + Copilot            Copilot
        (Scenario 1)          (Scenario 2, default)
```

## Switching scenarios

No code changes are required. To narrow the repo's visible footprint after
deciding:

```bash
# Scenario 2 only (drop Codex config)
rm -rf .codex

# Scenario 3 only (drop Claude Code config)
rm -rf .claude CLAUDE.md
```

`AGENTS.md`, `.agents/skills/`, and `.mcp.json` are shared across all three
scenarios and are never removed.
