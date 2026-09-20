# Windows 11 setup — Claude Code, GitHub Copilot, OpenAI Codex

## 1. Install the three CLIs (PowerShell, as your normal user)

```powershell
# Claude Code (requires Node.js 18+; install from nodejs.org first if needed)
npm install -g @anthropic-ai/claude-code
claude --version

# GitHub CLI + Copilot extension
winget install --id GitHub.cli
gh auth login
gh extension install github/gh-copilot
# For VS Code agent mode: install the "GitHub Copilot" and
# "GitHub Copilot Chat" extensions from the Extensions view.

# OpenAI Codex CLI
npm install -g @openai/codex
codex --version
```

## 2. Drop this kit into your repo

```powershell
cd C:\path\to\agentic-platform
Expand-Archive -Path C:\path\to\agentic-platform-ai-tooling.zip -DestinationPath . -Force
```

This adds `AGENTS.md`, `CLAUDE.md`, `.mcp.json`, `.agents\skills\`,
`.claude\`, `.codex\`, `.github\instructions\`, and `scripts\hooks\` to the
repo root.

The hook script (`scripts/hooks/guard-sensitive-commands.sh`) is a bash
script. Run agent CLIs from **WSL2** or **Git Bash** so hooks execute
correctly — plain `cmd.exe`/PowerShell cannot run it directly. If you're
Windows-native only, either:
- Install WSL2 (`wsl --install`) and run all three CLIs inside it (this
  also sidesteps the symlink/Developer-Mode caveats below entirely), **or**
- Port the hook to a `.ps1` equivalent and update `.claude/settings.json`
  and `.codex/hooks.json` to call it instead.

## 3. Trust the project (Codex)

```powershell
cd agentic-platform
codex
# accept the "trust this folder" prompt
codex mcp list   # confirm filesystem + fetch servers appear
```

## 4. Symlink caveat (Windows-specific)

The upstream pattern this kit follows sometimes uses symlinks (e.g.
`.claude/skills/<name>` → `.agents/skills/<name>`) as an alternative to the
thin-stub approach. **This kit ships with thin stub files instead of
symlinks specifically because Windows symlinks require Developer Mode or
admin privileges.** If you'd prefer real symlinks:

```powershell
# Enable Developer Mode first: Settings > Privacy & Security > For developers
New-Item -ItemType SymbolicLink -Path ".claude\skills\add-agent-node" `
  -Target ".agents\skills\add-agent-node"
```

Otherwise, leave the stub `.claude/skills/*/SKILL.md` files as-is — Claude
Code follows the `@../../../.agents/skills/<name>/SKILL.md` reference at
the prompt level reliably without needing a real symlink.

## 5. Verify each tool loads the shared instructions

```powershell
claude
> what does AGENTS.md say about the human-in-the-loop requirements?

gh copilot suggest "what test coverage threshold does this repo enforce?"

codex
> quote the last bullet point in AGENTS.md without opening the file
```

If Codex can't quote the last bullet, it truncated `AGENTS.md` — this kit
already sets `project_doc_max_bytes = 131072` in `.codex/config.toml` to
avoid Codex's 32 KiB default silent-truncation limit.

## 6. VS Code workspace MCP (1.118+)

VS Code 1.118+ reads the root `.mcp.json` directly. On older versions,
mirror it to `.vscode\mcp.json` with a `servers` key:

```powershell
$cfg = Get-Content .mcp.json | ConvertFrom-Json
@{ servers = $cfg.mcpServers } | ConvertTo-Json -Depth 5 | Set-Content .vscode\mcp.json
```
