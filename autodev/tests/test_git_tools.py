from __future__ import annotations

import subprocess
from pathlib import Path

from autodev.git_tools import changed_paths_between, changed_paths_since

from test_task_runner import commit_all, init_repo


def test_changed_paths_since_keeps_first_character_for_untracked_report(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    base_commit = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )

    report_path = repo / "reports" / "dev" / "TASK-PILOT-002.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("rapport\n", encoding="utf-8")

    modified_paths = changed_paths_since(repo, repo, base_commit)

    assert "reports/dev/TASK-PILOT-002.md" in modified_paths
    assert "eports/dev/TASK-PILOT-002.md" not in modified_paths


def test_changed_paths_between_keeps_expected_relative_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    base_commit = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )

    target = repo / "src" / "lib" / "tauri.ts"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("export const value = 1;\n", encoding="utf-8")
    commit_all(repo, "add tauri helper")
    head_commit = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )

    modified_paths = changed_paths_between(repo, base_commit, head_commit)

    assert modified_paths == ["src/lib/tauri.ts"]
