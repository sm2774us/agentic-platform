# Ubuntu setup — Claude Code, GitHub Copilot, OpenAI Codex

## 1. Install the three CLIs

```bash
# Claude Code
curl -fsSL https://claude.ai/install.sh | bash
claude --version

# GitHub Copilot CLI (requires an active Copilot subscription + gh CLI)
sudo apt install gh -y
gh auth login
gh extension install github/gh-copilot
# For VS Code agent mode, install the "GitHub Copilot" and
# "GitHub Copilot Chat" extensions from the Extensions view.

# OpenAI Codex CLI
npm install -g @openai/codex
codex --version
```

## 2. Drop this kit into your repo

```bash
cd /path/to/agentic-platform
unzip /path/to/agentic-platform-ai-tooling.zip -d .
```

This adds `AGENTS.md`, `CLAUDE.md`, `.mcp.json`, `.agents/skills/`,
`.claude/`, `.codex/`, `.github/instructions/`, and `scripts/hooks/` to the
repo root — none of it overwrites `src/`, `tests/`, or your application code.

```bash
chmod +x scripts/hooks/guard-sensitive-commands.sh
```

## 3. Trust the project (Codex)

Codex only merges `.codex/config.toml` and `.codex/hooks.json` for
repositories marked trusted. Run any Codex command in the repo root once
and accept the trust prompt:

```bash
cd agentic-platform
codex
# accept the "trust this folder" prompt
codex mcp list   # confirm filesystem + fetch servers appear
```

## 4. Verify each tool loads the shared instructions

```bash
# Claude Code
claude
> what does AGENTS.md say about the human-in-the-loop requirements?

# Copilot CLI
gh copilot suggest "what test coverage threshold does this repo enforce?"

# Codex — verify it didn't silently truncate AGENTS.md (32 KiB default limit;
# this kit already raises project_doc_max_bytes to 128 KiB in .codex/config.toml)
codex
> quote the last bullet point in AGENTS.md without opening the file
```

If Codex can't quote it, it truncated the file — re-check
`project_doc_max_bytes` in `.codex/config.toml` and `~/.codex/config.toml`.

## 5. VS Code workspace MCP (1.118+)

VS Code 1.118+ reads the root `.mcp.json` directly. On older versions,
mirror it to `.vscode/mcp.json` with a `servers` key instead of
`mcpServers`:

```bash
mkdir -p .vscode
python3 - << 'PY'
import json
cfg = json.load(open(".mcp.json"))
json.dump({"servers": cfg["mcpServers"]}, open(".vscode/mcp.json", "w"), indent=2)
PY
```

## 6. Enable nested AGENTS.md in VS Code (optional, experimental)

Settings → search `chat.useNestedAgentsMdFiles` → enable, if you add
per-directory `AGENTS.md` files (e.g. `src/agentic_platform/api/AGENTS.md`
for API-specific conventions).
