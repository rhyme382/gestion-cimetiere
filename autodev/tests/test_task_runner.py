from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from autodev.path_rules import normalize_repo_relative_path
from autodev.task_runner import (
    RunTaskError,
    ensure_paths_allowed,
    run_claude_non_interactive,
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
    (repo / "autodev" / "config").mkdir()
    (repo / "autodev" / "prompts").mkdir()
    smoke_command = f"{sys.executable} -c \"print('smoke-ok')\""
    full_command = f"{sys.executable} -c \"print('full-ok')\""
    (repo / "autodev" / "config" / "quality-gates.yaml").write_text(
        "task:\n"
        "  required: true\n"
        "smoke:\n"
        "  commands:\n"
        f"    - {json.dumps(smoke_command)}\n"
        "full:\n"
        "  commands:\n"
        f"    - {json.dumps(full_command)}\n",
        encoding="utf-8",
    )
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
        "specification_path": "SPEC.md",
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


def write_integration_result(repo: Path, task_id: str, status: str = "INTEGRATED") -> None:
    path = repo / ".autodev" / "runs" / task_id / "integration" / "integration-result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"task_id": task_id, "status": status}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def make_task(task_id: str, *, depends_on: list[str] | None = None) -> dict[str, object]:
    task: dict[str, object] = {
        "id": task_id,
        "title": f"Titre {task_id}",
        "description": "Description de tâche suffisamment longue.",
        "agent": "documentation",
        "depends_on": depends_on or [],
        "requirement_ids": ["REQ-001"],
        "allowed_paths": ["src", "reports/dev"],
        "validation_commands": [f'{sys.executable} -c "print(\'ok\')"'],
        "acceptance_criteria": ["Accepter"],
    }
    return task


def adapt_allowed_paths(repo: Path, backlog_path: Path) -> None:
    data = json.loads(backlog_path.read_text(encoding="utf-8"))
    for task in data["tasks"]:
        task["allowed_paths"] = [
            "src",
            "reports/dev",
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
            make_task("TASK-DEP"),
            make_task("TASK-MAIN", depends_on=["TASK-DEP"]),
        ],
    )
    adapt_allowed_paths(repo, backlog)

    with pytest.raises(RunTaskError, match="Dépendances non terminées"):
        run_task(backlog, "TASK-MAIN", dry_run=True)


def test_dependency_with_integrated_artifact_allows_run(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(
        repo,
        [
            make_task("TASK-DEP"),
            make_task("TASK-MAIN", depends_on=["TASK-DEP"]),
        ],
    )
    adapt_allowed_paths(repo, backlog)
    write_integration_result(repo, "TASK-DEP")

    result = run_task(backlog, "TASK-MAIN", dry_run=True)

    assert result["task_id"] == "TASK-MAIN"


def test_dependency_with_failed_artifact_blocks_run(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(
        repo,
        [
            make_task("TASK-DEP"),
            make_task("TASK-MAIN", depends_on=["TASK-DEP"]),
        ],
    )
    adapt_allowed_paths(repo, backlog)
    write_integration_result(repo, "TASK-DEP", status="FAILED")

    with pytest.raises(RunTaskError, match="Dépendances non terminées pour TASK-MAIN : TASK-DEP"):
        run_task(backlog, "TASK-MAIN", dry_run=True)


def test_task_without_dependencies_can_start(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-SOLO")])
    adapt_allowed_paths(repo, backlog)

    result = run_task(backlog, "TASK-SOLO", dry_run=True)

    assert result["task_id"] == "TASK-SOLO"


def test_validate_command_safe_rejects_dangerous_commands() -> None:
    with pytest.raises(RunTaskError, match="dangereuse"):
        validate_command_safe("pytest && rm -rf /tmp/x")


def test_allowed_paths_detection_rejects_outside_changes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    with pytest.raises(RunTaskError, match="hors périmètre autorisé"):
        ensure_paths_allowed(
            repo,
            ["src"],
            ["README.md", "src/ok.py"],
        )


def test_allowed_paths_accept_expected_report_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    ensure_paths_allowed(
        repo,
        ["reports/dev/"],
        ["reports/dev/TASK-PILOT-002.md"],
    )


def test_allowed_paths_do_not_confuse_src_and_src_tauri(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    with pytest.raises(RunTaskError, match="src-tauri/app\\.ts"):
        ensure_paths_allowed(
            repo,
            ["src/"],
            ["src-tauri/app.ts"],
        )


def test_allowed_paths_for_specific_file_only_allow_that_file(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    with pytest.raises(RunTaskError, match="reports/dev/OTHER\\.md"):
        ensure_paths_allowed(
            repo,
            ["reports/dev/TASK-PILOT-002.md"],
            ["reports/dev/OTHER.md"],
        )


def test_normalize_repo_relative_path_preserves_first_character() -> None:
    assert normalize_repo_relative_path("reports/dev/TASK-PILOT-002.md").as_posix() == "reports/dev/TASK-PILOT-002.md"
    assert normalize_repo_relative_path("./reports/dev/TASK-PILOT-002.md").as_posix() == "reports/dev/TASK-PILOT-002.md"
    assert normalize_repo_relative_path("src/lib/tauri.ts").as_posix() == "src/lib/tauri.ts"


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


def test_run_claude_non_interactive_sends_prompt_via_stdin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    captured: dict[str, object] = {}

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args[0], 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_claude_non_interactive(worktree, "prompt complet")

    command = captured["args"][0]
    kwargs = captured["kwargs"]
    assert command == [
        "claude",
        "-p",
        "--permission-mode",
        "bypassPermissions",
        "--tools",
        "Bash,Edit,Write,Read,Glob,Grep",
        "--output-format",
        "text",
    ]
    assert "dontAsk" not in command
    assert kwargs["cwd"] == worktree
    assert kwargs["input"] == "prompt complet"
    assert kwargs["text"] is True
    assert kwargs["capture_output"] is True
    assert kwargs["check"] is False
    assert "shell" not in kwargs
    assert result["returncode"] == 0


def test_claude_failure_writes_result_and_logs(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-FAIL")])
    adapt_allowed_paths(repo, backlog)
    commit_all(repo, "add backlog")

    def fake_claude_runner(*_: object, **__: object) -> dict[str, object]:
        return {
            "command": ["claude", "-p"],
            "returncode": 42,
            "stdout": "",
            "stderr": "Input must be provided either through stdin or as a prompt argument when using --print",
        }

    with pytest.raises(RunTaskError, match="Claude a échoué \\(code 42\\)"):
        run_task(backlog, "TASK-FAIL", dry_run=False, claude_runner=fake_claude_runner)

    run_dir = repo / ".autodev" / "runs" / "TASK-FAIL"
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))

    assert result["task_id"] == "TASK-FAIL"
    assert result["status"] == "failed"
    assert result["claude_exit_code"] == 42
    assert result["produced_commit"] is None
    assert result["branch"] == "autodev/TASK-FAIL"
    assert result["worktree"] == str(repo / ".autodev" / "worktrees" / "TASK-FAIL")
    assert result["base_commit"]
    assert "Input must be provided either through stdin" in result["error"]
    assert (run_dir / "claude.stdout.log").read_text(encoding="utf-8") == ""
    assert "Input must be provided either through stdin" in (run_dir / "claude.stderr.log").read_text(encoding="utf-8")


def test_claude_permission_false_success_is_marked_failed(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-PERMS")])
    adapt_allowed_paths(repo, backlog)
    commit_all(repo, "add backlog")

    def fake_claude_runner(*_: object, **__: object) -> dict[str, object]:
        return {
            "command": ["claude", "-p"],
            "returncode": 0,
            "stdout": "I do not possess permissions for Read, Bash and Edit/Write in this session.",
            "stderr": "",
        }

    with pytest.raises(RunTaskError, match="faux succès"):
        run_task(backlog, "TASK-PERMS", dry_run=False, claude_runner=fake_claude_runner)

    run_dir = repo / ".autodev" / "runs" / "TASK-PERMS"
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))

    assert result["status"] == "failed"
    assert result["claude_exit_code"] == 0
    assert "demande de permissions détectée" in result["error"]
    assert "permissions for Read, Bash and Edit/Write" in (run_dir / "claude.stdout.log").read_text(encoding="utf-8")
