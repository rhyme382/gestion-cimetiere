from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from autodev.cli import app
from autodev.monitor import monitor_feature
from autodev.monitor_state import MonitorStateError, read_feature_state, read_last_lines

from test_run_feature import (
    create_task_workspace,
    write_integration_result,
    write_review_result,
    write_run_result,
)
from test_task_runner import commit_all, init_repo, make_task, write_backlog


def write_feature_last_state(repo: Path, feature_id: str, payload: dict[str, object]) -> None:
    path = repo / ".autodev" / "runs" / "features" / feature_id / "last-state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_feature_result(repo: Path, feature_id: str, payload: dict[str, object]) -> None:
    path = repo / ".autodev" / "runs" / "features" / feature_id / "run-feature-result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_task_result(repo: Path, task_id: str, payload: dict[str, object]) -> None:
    path = repo / ".autodev" / "runs" / task_id / "result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        snapshot[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def prepare_single_task_repo(tmp_path: Path, task_id: str = "TASK-MON") -> tuple[Path, Path]:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task(task_id)])
    commit_all(repo, "prepare backlog")
    return repo, backlog


def test_feature_without_any_run_is_not_started(tmp_path: Path) -> None:
    _, backlog = prepare_single_task_repo(tmp_path)

    state = read_feature_state(backlog)

    assert state["feature_status"] == "NOT_STARTED"
    assert state["tasks"][0]["status"] == "READY"
    assert state["current_task_id"] == "—"


def test_task_in_implementation_is_reported(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    _, worktree, _ = create_task_workspace(
        repo,
        backlog,
        "TASK-MON",
        create_branch=True,
        create_worktree=True,
        make_commit=False,
        write_result_artifact=False,
    )
    write_task_result(
        repo,
        "TASK-MON",
        {
            "task_id": "TASK-MON",
            "status": "running",
            "branch": "autodev/TASK-MON",
            "worktree": str(worktree),
            "produced_commit": None,
            "modified_paths": [],
            "validations": [],
            "validation_summary": [],
        },
    )
    write_feature_last_state(
        repo,
        "FEATURE-TEST",
        {
            "current_task_id": "TASK-MON",
            "task_action": "IMPLEMENT",
            "status": "RUNNING",
            "correction_count": 0,
        },
    )

    state = read_feature_state(backlog)

    assert state["tasks"][0]["status"] == "IMPLEMENTING"
    assert state["current_task"]["task_action"] == "IMPLEMENT"


def test_task_progress_and_recent_heartbeat_are_reported(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    _, worktree, _ = create_task_workspace(
        repo, backlog, "TASK-MON", create_branch=True, create_worktree=True,
        make_commit=False, write_result_artifact=False,
    )
    write_task_result(repo, "TASK-MON", {"task_id": "TASK-MON", "status": "running", "worktree": str(worktree)})
    write_feature_last_state(repo, "FEATURE-TEST", {
        "current_task_id": "TASK-MON", "task_action": "IMPLEMENT", "status": "RUNNING"
    })
    heartbeat = repo / ".autodev" / "runs" / "TASK-MON" / "heartbeat.json"
    heartbeat.write_text(json.dumps({"phase": "IMPLEMENT", "updated_at": "2026-08-07T10:00:00+00:00"}), encoding="utf-8")

    state = read_feature_state(backlog, now=datetime(2026, 8, 7, 10, 0, 30, tzinfo=timezone.utc))

    assert state["tasks"][0]["progress_percentage"] == 25
    assert state["progress"]["estimated_percentage"] == 25
    assert state["tasks"][0]["activity"] == {"status": "ACTIF", "age_seconds": 30, "phase": "IMPLEMENT"}


def test_stale_heartbeat_is_suspect(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    _, worktree, _ = create_task_workspace(
        repo, backlog, "TASK-MON", create_branch=True, create_worktree=True,
        make_commit=False, write_result_artifact=False,
    )
    write_task_result(repo, "TASK-MON", {"task_id": "TASK-MON", "status": "running", "worktree": str(worktree)})
    heartbeat = repo / ".autodev" / "runs" / "TASK-MON" / "heartbeat.json"
    heartbeat.write_text(json.dumps({"phase": "IMPLEMENT", "updated_at": "2026-08-07T09:49:00+00:00"}), encoding="utf-8")

    state = read_feature_state(backlog, now=datetime(2026, 8, 7, 10, 0, tzinfo=timezone.utc))

    assert state["tasks"][0]["activity"]["status"] == "SUSPECT"


def test_task_in_review_is_reported(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    _, _, produced_commit = create_task_workspace(repo, backlog, "TASK-MON", make_commit=True)
    write_feature_last_state(
        repo,
        "FEATURE-TEST",
        {
            "current_task_id": "TASK-MON",
            "task_action": "REVIEW",
            "status": "RUNNING",
            "correction_count": 0,
        },
    )

    state = read_feature_state(backlog)

    assert produced_commit is not None
    assert state["tasks"][0]["status"] == "REVIEWING"
    assert state["tasks"][0]["produced_commit"] == produced_commit


def test_task_in_correction_is_reported(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    create_task_workspace(repo, backlog, "TASK-MON", make_commit=True)
    write_review_result(repo, "TASK-MON", "CORRECTION_REQUIRED")
    write_feature_last_state(
        repo,
        "FEATURE-TEST",
        {
            "current_task_id": "TASK-MON",
            "task_action": "CORRECT",
            "status": "RUNNING",
            "correction_count": 1,
        },
    )

    state = read_feature_state(backlog)

    assert state["tasks"][0]["status"] == "CORRECTING"


def test_task_approved_is_reported(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    create_task_workspace(repo, backlog, "TASK-MON", make_commit=True)
    write_review_result(repo, "TASK-MON", "APPROVED")

    state = read_feature_state(backlog)

    assert state["tasks"][0]["status"] == "APPROVED"


def test_task_integrated_is_reported(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    create_task_workspace(repo, backlog, "TASK-MON", make_commit=True)
    write_review_result(repo, "TASK-MON", "APPROVED")
    write_integration_result(repo, "TASK-MON", "INTEGRATED")

    state = read_feature_state(backlog)

    assert state["tasks"][0]["status"] == "INTEGRATED"


def test_feature_completed_is_reported(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    create_task_workspace(repo, backlog, "TASK-MON", make_commit=True)
    write_review_result(repo, "TASK-MON", "APPROVED")
    write_integration_result(repo, "TASK-MON", "INTEGRATED")
    write_feature_result(
        repo,
        "FEATURE-TEST",
        {
            "feature_id": "FEATURE-TEST",
            "status": "COMPLETED",
            "started_at": "2026-07-20T08:00:00+00:00",
            "finished_at": "2026-07-20T08:10:00+00:00",
        },
    )

    state = read_feature_state(backlog)

    assert state["feature_status"] == "COMPLETED"
    assert state["progress"]["percentage"] == 100


def test_integrated_tasks_override_stale_human_review_result(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    create_task_workspace(repo, backlog, "TASK-MON", make_commit=True)
    write_review_result(repo, "TASK-MON", "APPROVED")
    write_integration_result(repo, "TASK-MON", "INTEGRATED")
    write_feature_result(repo, "FEATURE-TEST", {
        "feature_id": "FEATURE-TEST", "status": "HUMAN_REVIEW_REQUIRED"
    })
    write_feature_last_state(repo, "FEATURE-TEST", {
        "current_task_id": "TASK-MON",
        "task_action": "IMPLEMENT",
        "status": "HUMAN_REVIEW_REQUIRED",
        "last_error": "ancien blocage",
    })

    state = read_feature_state(backlog)

    assert state["feature_status"] == "COMPLETED"
    assert state["historical_feature_status"] == "HUMAN_REVIEW_REQUIRED"
    assert state["current_task_id"] == "—"
    assert state["current_action"] == "—"
    assert state["intervention_required"] == "—"


def test_feature_failed_is_reported(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    write_feature_result(repo, "FEATURE-TEST", {"feature_id": "FEATURE-TEST", "status": "FAILED"})

    state = read_feature_state(backlog)

    assert state["feature_status"] == "FAILED"


def test_timeout_is_reported(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    _, worktree, _ = create_task_workspace(
        repo,
        backlog,
        "TASK-MON",
        create_branch=True,
        create_worktree=True,
        make_commit=False,
        write_result_artifact=False,
    )
    write_task_result(
        repo,
        "TASK-MON",
        {
            "task_id": "TASK-MON",
            "status": "failed",
            "branch": "autodev/TASK-MON",
            "worktree": str(worktree),
            "claude_timeout": True,
            "error": "Claude a expiré : statut TIMEOUT.",
        },
    )

    state = read_feature_state(backlog)

    assert state["tasks"][0]["status"] == "TIMEOUT"


def test_human_review_required_is_reported(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    create_task_workspace(repo, backlog, "TASK-MON", make_commit=True)
    write_review_result(repo, "TASK-MON", "HUMAN_REVIEW_REQUIRED")

    state = read_feature_state(backlog)

    assert state["tasks"][0]["status"] == "HUMAN_REVIEW_REQUIRED"


def test_logs_absent_returns_empty_section(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    _, worktree, _ = create_task_workspace(
        repo,
        backlog,
        "TASK-MON",
        create_branch=True,
        create_worktree=True,
        make_commit=False,
        write_result_artifact=False,
    )
    write_task_result(
        repo,
        "TASK-MON",
        {"task_id": "TASK-MON", "status": "running", "worktree": str(worktree)},
    )
    write_feature_last_state(
        repo,
        "FEATURE-TEST",
        {"current_task_id": "TASK-MON", "task_action": "IMPLEMENT", "status": "RUNNING"},
    )

    state = read_feature_state(backlog, include_logs=True)

    assert state["logs"] == []


def test_logs_existing_are_reported(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    _, worktree, _ = create_task_workspace(
        repo,
        backlog,
        "TASK-MON",
        create_branch=True,
        create_worktree=True,
        make_commit=False,
        write_result_artifact=False,
    )
    write_task_result(
        repo,
        "TASK-MON",
        {"task_id": "TASK-MON", "status": "running", "worktree": str(worktree)},
    )
    run_dir = repo / ".autodev" / "runs" / "TASK-MON"
    (run_dir / "claude.stdout.log").write_text("l1\nl2\nl3\n", encoding="utf-8")
    write_feature_last_state(
        repo,
        "FEATURE-TEST",
        {"current_task_id": "TASK-MON", "task_action": "IMPLEMENT", "status": "RUNNING"},
    )

    state = read_feature_state(backlog, include_logs=True, log_lines=2)

    assert state["logs"][0]["lines"] == ["l2", "l3"]


def test_read_last_lines_reads_only_tail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "tail.log"
    prefix = ("x" * 5000 + "\n") * 50
    suffix = "\n".join([f"line-{index}" for index in range(20)]) + "\n"
    path.write_text(prefix + suffix, encoding="utf-8")
    total_size = path.stat().st_size
    original_open = Path.open
    stats = {"bytes": 0}

    def spy_open(self: Path, *args: object, **kwargs: object):  # type: ignore[override]
        stream = original_open(self, *args, **kwargs)
        if self != path:
            return stream

        class Wrapper:
            def __init__(self, inner):
                self.inner = inner

            def read(self, size: int = -1):
                data = self.inner.read(size)
                stats["bytes"] += len(data)
                return data

            def __getattr__(self, name: str):
                return getattr(self.inner, name)

            def __enter__(self):
                self.inner.__enter__()
                return self

            def __exit__(self, exc_type, exc, tb):
                return self.inner.__exit__(exc_type, exc, tb)

        return Wrapper(stream)

    monkeypatch.setattr(Path, "open", spy_open)

    lines = read_last_lines(path, 5)

    assert lines == [f"line-{index}" for index in range(15, 20)]
    assert stats["bytes"] < total_size


def test_worktree_absent_is_reported(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    base_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "branch", "autodev/TASK-MON", base_commit], cwd=repo, check=True)
    write_run_result(
        repo,
        "TASK-MON",
        base_commit=base_commit,
        worktree=repo / ".autodev" / "worktrees" / "TASK-MON",
        produced_commit=None,
    )

    state = read_feature_state(backlog)

    assert state["tasks"][0]["worktree_exists"] == "no"


def test_worktree_present_and_dirty_is_reported(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    _, worktree, _ = create_task_workspace(repo, backlog, "TASK-MON", make_commit=True)
    (worktree / "src" / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    write_feature_last_state(
        repo,
        "FEATURE-TEST",
        {"current_task_id": "TASK-MON", "task_action": "REVIEW", "status": "RUNNING"},
    )

    state = read_feature_state(backlog)

    assert state["current_task"]["git"]["is_dirty"] is True
    assert state["current_task"]["git"]["modified_count"] >= 1


def test_invalid_backlog_raises(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-1"), make_task("TASK-1")])
    commit_all(repo, "invalid backlog")

    with pytest.raises(MonitorStateError, match="dupliqués"):
        read_feature_state(backlog)


def test_monitor_loop_stops_cleanly_on_keyboard_interrupt(tmp_path: Path) -> None:
    _, backlog = prepare_single_task_repo(tmp_path)
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)

    def interrupt(_: float) -> None:
        raise KeyboardInterrupt

    monitor_feature(backlog, once=False, console=console, sleep_fn=interrupt)

    assert "FEATURE-TEST" in output.getvalue()


def test_monitor_once_cli_exits_zero(tmp_path: Path) -> None:
    _, backlog = prepare_single_task_repo(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["monitor", str(backlog), "--once"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "FEATURE-TEST" in result.stdout


def test_monitor_uses_only_git_subprocess_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    create_task_workspace(repo, backlog, "TASK-MON", make_commit=True)
    commands: list[list[str]] = []
    real_run = subprocess.run

    def spy_run(*args: object, **kwargs: object):
        command = list(args[0])
        commands.append(command)
        return real_run(*args, **kwargs)

    monkeypatch.setattr("autodev.planner.subprocess.run", spy_run)
    monkeypatch.setattr("autodev.git_tools.subprocess.run", spy_run)

    read_feature_state(backlog)

    assert commands
    assert all(command[0] == "git" for command in commands)


def test_monitor_does_not_modify_files(tmp_path: Path) -> None:
    repo, backlog = prepare_single_task_repo(tmp_path)
    before = file_snapshot(repo)

    monitor_feature(backlog, once=True, console=Console(file=StringIO(), force_terminal=False))

    after = file_snapshot(repo)
    assert after == before


def test_monitor_help_mentions_options() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["monitor", "--help"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "--refresh" in result.stdout
    assert "--once" in result.stdout
    assert "--logs" in result.stdout
