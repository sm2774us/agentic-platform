"""Validates the cross-tool AI configuration layer shipped alongside the
platform code (AGENTS.md, .mcp.json, .claude/, .codex/, skill stubs).

These files are read by external CLIs (Claude Code, Codex, Copilot) rather
than imported as Python, so `mypy`/`ruff` never touch them — this test
suite is their equivalent quality gate: valid JSON/TOML, and every
`.claude/skills/*/SKILL.md` stub resolves to a real canonical file under
`.agents/skills/`.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_agents_md_exists_and_nonempty() -> None:
    agents_md = REPO_ROOT / "AGENTS.md"
    assert agents_md.is_file()
    assert len(agents_md.read_text(encoding="utf-8")) > 100


def test_claude_md_imports_agents_md() -> None:
    claude_md = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8").strip()
    assert claude_md == "@AGENTS.md"


def test_mcp_json_is_valid_and_has_servers() -> None:
    data = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    assert "mcpServers" in data
    assert len(data["mcpServers"]) > 0


def test_codex_config_toml_is_valid() -> None:
    with (REPO_ROOT / ".codex" / "config.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert "mcp_servers" in data
    assert data.get("project_doc_max_bytes", 0) > 32 * 1024  # raised above Codex's default


def test_codex_hooks_json_is_valid() -> None:
    data = json.loads((REPO_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    assert "hooks" in data


def test_codex_reviewer_agent_toml_is_valid() -> None:
    with (REPO_ROOT / ".codex" / "agents" / "reviewer.toml").open("rb") as fh:
        data = tomllib.load(fh)
    assert data["name"] == "reviewer"


def test_claude_settings_json_is_valid() -> None:
    data = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "hooks" in data
    assert "permissions" in data


def test_claude_skill_stubs_resolve_to_canonical_skills() -> None:
    stub_dir = REPO_ROOT / ".claude" / "skills"
    canonical_dir = REPO_ROOT / ".agents" / "skills"
    assert canonical_dir.is_dir()

    stub_paths = sorted(stub_dir.glob("*/SKILL.md"))
    assert len(stub_paths) >= 4

    for stub_path in stub_paths:
        text = stub_path.read_text(encoding="utf-8")
        match = re.search(r"@([^\s]+SKILL\.md)", text)
        assert match, f"{stub_path} has no @import line"
        resolved = (stub_path.parent / match.group(1)).resolve()
        assert resolved.is_file(), f"{stub_path} points at missing file {resolved}"
        assert resolved.is_relative_to(canonical_dir.resolve())


def test_every_canonical_skill_has_a_claude_stub() -> None:
    canonical_names = {p.parent.name for p in (REPO_ROOT / ".agents" / "skills").glob("*/SKILL.md")}
    stub_names = {p.parent.name for p in (REPO_ROOT / ".claude" / "skills").glob("*/SKILL.md")}
    assert canonical_names == stub_names


def test_hook_script_is_executable_and_blocks_destructive_commands() -> None:
    hook_path = REPO_ROOT / "scripts" / "hooks" / "guard-sensitive-commands.sh"
    assert hook_path.is_file()
    import os
    import shutil
    import stat
    import subprocess

    # The executable bit is not guaranteed to survive every path a checkout can
    # take (zip extraction on a non-POSIX tool, a fresh `git clone` on a system
    # with core.fileMode quirks, etc.). Self-heal it here rather than asserting
    # on a bit whose presence depends on how this repo happened to be obtained --
    # what actually matters for the hook to work is that it *runs*, which the
    # subprocess calls below verify directly.
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    assert os.access(hook_path, os.X_OK)

    # Use a forward-slash path for the bash invocation: on Windows, str(hook_path)
    # is backslash-separated, and bash (Git Bash/MSYS2) treats backslash as a shell
    # escape character in argv, stripping every single backslash and mangling the
    # path (e.g. "C:\Users\x" -> "C:Usersx"). Path.as_posix() sidesteps this and is
    # understood natively by both Windows and POSIX shells.
    hook_path_posix = hook_path.as_posix()

    bash_path = shutil.which("bash")
    if bash_path is None:  # pragma: no cover - CI (Ubuntu) always has a real bash
        pytest.skip("no bash on PATH -- native Windows cmd.exe without Git Bash/WSL")

    # A `bash` resolved on PATH is not necessarily a usable POSIX shell: Windows
    # ships a legacy launcher shim at C:\Windows\System32\bash.exe whenever the
    # "Windows Subsystem for Linux" optional feature is enabled -- even with no
    # distro installed or intended for use. That shim reinterprets its argv
    # inside its own Linux filesystem, so a real Windows path like
    # "C:/Users/x/repo/script.sh" doesn't exist from its point of view, and every
    # invocation fails with a misleading "No such file or directory". Probe for
    # that here rather than letting the real check below fail confusingly.
    probe = subprocess.run(
        [bash_path, "-c", f"test -f '{hook_path_posix}'"],
        capture_output=True,
        check=False,
    )
    if probe.returncode != 0:  # pragma: no cover - CI (Ubuntu) always has a real bash
        pytest.skip(
            "bash on PATH cannot see this repo at its own path -- likely the "
            "legacy WSL bash.exe launcher shim, not a real POSIX shell; skipping "
            "the subprocess-based hook check on this native Windows environment"
        )

    blocked = subprocess.run(
        [bash_path, hook_path_posix, "rm -rf / --no-preserve-root"],
        capture_output=True,
        check=False,
    )
    assert blocked.returncode != 0

    allowed = subprocess.run(
        [bash_path, hook_path_posix, "pytest -q"],
        capture_output=True,
        check=False,
    )
    assert allowed.returncode == 0


def test_ai_tool_strategy_doc_covers_all_three_scenarios() -> None:
    text = (REPO_ROOT / "docs" / "AI_TOOL_STRATEGY.md").read_text(encoding="utf-8")
    assert "Scenario 1" in text
    assert "Scenario 2" in text
    assert "Scenario 3" in text


def test_setup_guides_exist_for_both_platforms() -> None:
    assert (REPO_ROOT / "ubuntu" / "SETUP.md").is_file()
    assert (REPO_ROOT / "win11" / "SETUP.md").is_file()
