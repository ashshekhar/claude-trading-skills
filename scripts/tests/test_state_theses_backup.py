"""Exercise the documented state/theses archive and restore flow synthetically."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def test_state_theses_archive_restores_synthetic_file(tmp_path: Path) -> None:
    tar = shutil.which("tar")
    if tar is None:
        pytest.skip("tar is required for the documented backup procedure")

    repo_root = tmp_path / "repo"
    source = repo_root / "state" / "theses"
    source.mkdir(parents=True)
    synthetic = source / "synthetic-example.yaml"
    synthetic.write_text("id: synthetic-only\nnotes: no user data\n", encoding="utf-8")

    archive = tmp_path / "state-theses.tar.gz"
    subprocess.run(
        [tar, "-czf", str(archive), "-C", str(repo_root), "state/theses"],
        check=True,
        capture_output=True,
    )

    restore_root = tmp_path / "restore"
    restore_root.mkdir()
    subprocess.run(
        [tar, "-xzf", str(archive), "-C", str(restore_root)],
        check=True,
        capture_output=True,
    )

    restored = restore_root / "state" / "theses" / synthetic.name
    assert restored.read_bytes() == synthetic.read_bytes()
    assert "synthetic-only" in restored.read_text(encoding="utf-8")
