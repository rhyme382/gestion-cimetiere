from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from autodev.task_runner import (
    RunTaskError,
    ensure_paths_allowed,
    run_task,
    validate_command_safe,
)


def init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)

    (repo / "SPEC.md").write_text("# Spec\n\nBase.\n", encoding="utf-8")
    (repo / "autodev").mkdir()
    (repo / "autodev" / "prompts").mkdir()
    (repo / "src").mkdir()
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True, text=True)
    return repo


def write_backlog(repo: Path, tasks: list[dict[str, object]]) -> Path:
    backlog_dir = repo / ".autodev" / "plans"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    backlog = {
        "feature_id": "FEATURE-TEST",
        "feature_title": "Feature test",
        "summary": "Résumé de test suffisant pour le backlog.",
        "requirements": [
            {
                "id": "REQ-001",
                "description": "Description requirement",
                "acceptance_criteria": ["Critère 1"],
            }
        ],
        "tasks": tasks,
    }
    path = backlog_dir / "test.backlog.json"
    path.write_text(json.dumps(backlog, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def make_task(task_id: str, *, depends_on: list[str] | None = None, status: str | None = None) -> dict[str, object]:
    task: dict[str, object] = {
        "id": task_id,
        "title": f"Titre {task_id}",
        "description": "Description de tâche suffisamment longue.",
        "agent": "documentation",
        "depends_on": depends_on or [],
        "requirement_ids": ["REQ-001"],
        "allowed_paths": ["/repo/src/", "/repo/reports/dev/"],
        "validation_commands": [f"{sys.executable} -c print('ok')"],
        "acceptance_criteria": ["Accepter"],
    }
    if status is not None:
        task["status"] = status
    return task


def adapt_allowed_paths(repo: Path, backlog_path: Path) -> None:
    data = json.loads(backlog_path.read_text(encoding="utf-8"))
    for task in data["tasks"]:
        task["allowed_paths"] = [
            str(repo / "src"),
            str(repo / "reports" / "dev"),
        ]
    backlog_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def commit_all(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True, capture_output=True, text=True)


def test_unknown_task_raises(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-ONE")])
    adapt_allowed_paths(repo, backlog)

    with pytest.raises(RunTaskError, match="Tâche inconnue"):
        run_task(backlog, "TASK-MISSING", dry_run=True)


def test_dependency_not_completed_raises(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(
        repo,
        [
            make_task("TASK-DEP", status="todo"),
            make_task("TASK-MAIN", depends_on=["TASK-DEP"]),
        ],
    )
    adapt_allowed_paths(repo, backlog)

    with pytest.raises(RunTaskError, match="Dépendances non terminées"):
        run_task(backlog, "TASK-MAIN", dry_run=True)


def test_validate_command_safe_rejects_dangerous_commands() -> None:
    with pytest.raises(RunTaskError, match="dangereuse"):
        validate_command_safe("pytest && rm -rf /tmp/x")


def test_allowed_paths_detection_rejects_outside_changes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    with pytest.raises(RunTaskError, match="hors périmètre autorisé"):
        ensure_paths_allowed(
            repo,
            [str(repo / "src")],
            ["README.md", "src/ok.py"],
        )


def test_dry_run_does_not_call_claude_or_create_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-DRY")])
    adapt_allowed_paths(repo, backlog)

    called = False

    def fake_claude_runner(*_: object, **__: object) -> dict[str, object]:
        nonlocal called
        called = True
        return {}

    result = run_task(backlog, "TASK-DRY", dry_run=True, claude_runner=fake_claude_runner)

    assert called is False
    assert result["branch"] == "autodev/TASK-DRY"
    assert not (repo / ".autodev" / "worktrees" / "TASK-DRY").exists()
    assert not (repo / ".autodev" / "runs" / "TASK-DRY").exists()


def test_dirty_repository_is_refused(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-DIRTY")])
    adapt_allowed_paths(repo, backlog)
    commit_all(repo, "add backlog")
    (repo / "README.md").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(RunTaskError, match="modifications non enregistrées"):
        run_task(backlog, "TASK-DIRTY", dry_run=False)
