#!/usr/bin/env bash
# PreToolUse hook (Claude Code / Copilot CLI hook format; also registered
# for Codex via .codex/hooks.json). Blocks obviously destructive shell
# commands from being run by an agent without a human present.
set -euo pipefail

cmd="${1:-}"

blocked_patterns=(
  "rm -rf /"
  "git push --force"
  "DROP TABLE"
  "DROP DATABASE"
  ":(){ :|:& };:"
)

for pattern in "${blocked_patterns[@]}"; do
  if [[ "$cmd" == *"$pattern"* ]]; then
    echo "BLOCKED by guard-sensitive-commands.sh: command matches '$pattern'. Requires human execution." >&2
    exit 1
  fi
done

exit 0
