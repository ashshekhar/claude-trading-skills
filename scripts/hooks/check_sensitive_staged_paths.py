#!/usr/bin/env python3
"""Reject sensitive or ignored paths staged with ordinary or forced git add."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ALLOWED_IGNORED_SENTINELS = {
    "state/journal/.gitkeep",
    "state/theses/.gitkeep",
}
PRIVATE_KEY_NAMES = {"id_rsa", "id_ed25519"}
PRIVATE_KEY_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
PRIVATE_DATA_DIRS = {".cache", ".staging", "logs", "reports", "reviews", "state"}
PRIVATE_EXACT_PATHS = {
    ".envrc",
    ".mcp.json",
    "scripts/weekly_portfolio_review_fetch.py",
}


def _explicit_sensitive_reason(path: str) -> str | None:
    """Return a reason for paths that must never be committed."""
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    name = normalized.rsplit("/", 1)[-1]
    if normalized in PRIVATE_EXACT_PATHS or name == ".envrc":
        return "local private configuration or fetch script"
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return "environment file"
    if name == ".mcp.json":
        return "local tool configuration"
    if name in PRIVATE_KEY_NAMES or Path(name).suffix.lower() in PRIVATE_KEY_SUFFIXES:
        return "private key or certificate file"

    parts = normalized.split("/")
    if parts[0] in PRIVATE_DATA_DIRS:
        return f"local data directory ({parts[0]})"
    if Path(name).suffix.lower() in {".log", ".tmp"}:
        return "runtime log or temporary file"
    return None


def _git(
    repo_root: Path, args: list[str], input_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        input=input_bytes,
        capture_output=True,
        check=False,
    )


def _is_empty_regular_staged_file(repo_root: Path, path: str) -> bool:
    """Check the index entry, not the worktree, for an empty regular file."""
    listing = _git(repo_root, ["ls-files", "--stage", "-z", "--", path])
    if listing.returncode != 0:
        return False
    records = [record for record in listing.stdout.split(b"\0") if record]
    if len(records) != 1:
        return False

    try:
        metadata, staged_path = records[0].split(b"\t", maxsplit=1)
        mode, object_id, stage = metadata.split()
    except ValueError:
        return False
    if os.fsdecode(staged_path) != path or mode not in {b"100644", b"100755"} or stage != b"0":
        return False

    size = _git(repo_root, ["cat-file", "-s", object_id.decode("ascii")])
    if size.returncode != 0:
        return False
    try:
        return int(size.stdout.strip()) == 0
    except ValueError:
        return False


def inspect_staged_paths(repo_root: Path) -> tuple[list[tuple[str, str]], str | None]:
    """Return protected staged paths and a diagnostic if git inspection fails."""
    staged = _git(repo_root, ["diff", "--cached", "--name-only", "-z"])
    if staged.returncode != 0:
        return [], staged.stderr.decode(errors="replace").strip() or "git diff failed"

    paths = [os.fsdecode(item) for item in staged.stdout.split(b"\0") if item]
    if not paths:
        return [], None

    # --no-index evaluates the checked-out .gitignore rules even for paths
    # already present in the staged index. NUL separators preserve spaces.
    ignored = _git(
        repo_root,
        ["check-ignore", "--no-index", "--stdin", "-z"],
        input_bytes=staged.stdout,
    )
    if ignored.returncode not in (0, 1):
        return [], ignored.stderr.decode(errors="replace").strip() or "git check-ignore failed"
    ignored_paths = {os.fsdecode(item) for item in ignored.stdout.split(b"\0") if item}

    protected: list[tuple[str, str]] = []
    for path in paths:
        if path in ALLOWED_IGNORED_SENTINELS:
            if not _is_empty_regular_staged_file(repo_root, path):
                protected.append((path, "state placeholder must be an empty regular file"))
            continue
        reason = _explicit_sensitive_reason(path)
        if reason is None and path in ignored_paths and path not in ALLOWED_IGNORED_SENTINELS:
            reason = "matches .gitignore"
        if reason:
            protected.append((path, reason))
    return protected, None


def main() -> int:
    repo_root = Path.cwd()
    protected, error = inspect_staged_paths(repo_root)
    if error:
        print(f"Could not inspect staged paths: {error}", file=sys.stderr)
        return 2
    if not protected:
        return 0

    print("Refusing to commit protected paths:", file=sys.stderr)
    for path, reason in protected:
        print(f"  {path!r}: {reason}", file=sys.stderr)
    print("Remove these paths from the index; do not bypass this hook.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
