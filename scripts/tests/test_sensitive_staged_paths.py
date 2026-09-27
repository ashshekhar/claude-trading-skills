"""Regression tests for the pre-commit sensitive staged path guard."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "scripts" / "hooks" / "check_sensitive_staged_paths.py"
OUTER_GIT_ENV = {
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
    "GIT_CEILING_DIRECTORIES",
}


def _isolated_git_env() -> dict[str, str]:
    """Do not let a pre-commit/pre-push hook redirect temp-repo Git commands."""
    return {key: value for key, value in os.environ.items() if key not in OUTER_GIT_ENV}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        env=_isolated_git_env(),
    )


def _init_repo(repo: Path) -> None:
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Privacy Guard Test")
    _git(repo, "config", "user.email", "privacy-guard@example.invalid")
    shutil.copyfile(ROOT / ".gitignore", repo / ".gitignore")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-qm", "test fixture")


def _force_stage(repo: Path, relative_path: str, contents: str = "synthetic\n") -> None:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
    _git(repo, "add", "-f", "--", relative_path)


def _run_guard(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=_isolated_git_env(),
    )


def test_guard_allows_safe_files_and_the_two_state_sentinels(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / ".env.example").write_text("API_KEY=replace-me\n", encoding="utf-8")
    _git(tmp_path, "add", ".env.example")
    for relative_path in (
        "state/journal/.gitkeep",
        "state/theses/.gitkeep",
    ):
        _force_stage(tmp_path, relative_path, "")

    result = _run_guard(tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


def test_guard_rejects_force_added_ignored_and_sensitive_paths(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    protected_paths = (
        ".env.local",
        ".mcp.json",
        "logs/weekly run.log",
        "reports/raw_candidates.yaml",
        "state/theses/private.yaml",
        "keys/provider.pem",
    )
    for relative_path in protected_paths:
        _force_stage(tmp_path, relative_path)

    result = _run_guard(tmp_path)

    assert result.returncode == 1
    for relative_path in protected_paths:
        assert repr(relative_path) in result.stderr


def test_guard_rejects_nonempty_state_placeholder(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _force_stage(tmp_path, "state/theses/.gitkeep", "synthetic secret\n")

    result = _run_guard(tmp_path)

    assert result.returncode == 1
    assert "state placeholder must be an empty regular file" in result.stderr


def test_guard_rejects_symlink_state_placeholder(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    target = tmp_path / "synthetic-target.txt"
    target.write_text("synthetic\n", encoding="utf-8")
    placeholder = tmp_path / "state" / "theses" / ".gitkeep"
    placeholder.parent.mkdir(parents=True)
    try:
        placeholder.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    _git(tmp_path, "add", "-f", "--", "state/theses/.gitkeep")

    result = _run_guard(tmp_path)

    assert result.returncode == 1
    assert "state placeholder must be an empty regular file" in result.stderr


def test_guard_explicitly_blocks_private_paths_when_ignore_rules_change(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    gitignore = tmp_path / ".gitignore"
    contents = gitignore.read_text(encoding="utf-8")
    contents = contents.replace(".envrc\n", "").replace(
        "scripts/weekly_portfolio_review_fetch.py\n", ""
    )
    gitignore.write_text(contents, encoding="utf-8")
    _git(tmp_path, "add", ".gitignore")
    _force_stage(tmp_path, ".envrc")
    _force_stage(tmp_path, "scripts/weekly_portfolio_review_fetch.py")

    result = _run_guard(tmp_path)

    assert result.returncode == 1
    assert repr(".envrc") in result.stderr
    assert repr("scripts/weekly_portfolio_review_fetch.py") in result.stderr
