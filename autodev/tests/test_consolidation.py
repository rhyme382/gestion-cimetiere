from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autodev.cli import app
from autodev.planner import PlanningError, validate_backlog_consistency
from autodev.process_runner import TIMEOUTS_SECONDS, run_process_capturing_timeout
from autodev.review_task import ReviewTaskError, review_task
from autodev.run_feature import run_feature
from autodev.task_runner import run_task

from test_review_task import fake_claude_success_factory, write_codex_result
from test_run_feature import build_runners, prepare_backlog
from test_task_runner import commit_all, init_repo, make_task, write_backlog


def test_process_runner_marks_timeout_and_captures_streams(tmp_path: Path) -> None:
    result = run_process_capturing_timeout(
        command=[
            sys.executable,
            "-c",
            "import subprocess,time,sys; subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); print('start'); sys.stdout.flush(); time.sleep(30)",
        ],
        cwd=tmp_path,
        timeout_seconds=1,
    )

    assert result.timed_out is True
    assert result.returncode is None
    assert "start" in result.stdout


def test_validate_backlog_rejects_manifest_change_without_reason(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-DEPS")])
    data = json.loads(backlog.read_text(encoding="utf-8"))
    data["tasks"][0]["allowed_paths"] = ["src", "package.json"]
    backlog.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(PlanningError, match="dependency_change_reason"):
        validate_backlog_consistency(json.loads(backlog.read_text(encoding="utf-8")))


def test_validate_backlog_rejects_overly_broad_validation_without_justification(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    task = make_task("TASK-TEST")
    task["allowed_paths"] = ["src/components/App.test.tsx"]
    task["validation_commands"] = ["npm run test"]
    backlog = write_backlog(repo, [task])

    with pytest.raises(PlanningError, match="validation trop large"):
        validate_backlog_consistency(json.loads(backlog.read_text(encoding="utf-8")))


def test_review_task_rejects_misleading_report(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-REPORT")])
    commit_all(repo, "add backlog")
    run_task(backlog, "TASK-REPORT", dry_run=False, claude_runner=fake_claude_success_factory())
    run_dir = repo / ".autodev" / "runs" / "TASK-REPORT"
    (run_dir / "task-report.json").write_text(
        json.dumps(
            {
                "task_id": "TASK-REPORT",
                "feature_id": "FEATURE-TEST",
                "objective": "mensonge",
                "modified_files": [],
                "validations": [],
                "problems": [],
                "next_task": None,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    def fake_codex_runner(*_: object, **kwargs: object) -> dict[str, object]:
        write_codex_result(
            Path(kwargs["output_path"]),
            {
                "task_id": "TASK-REPORT",
                "verdict": "APPROVED",
                "summary": "ok",
                "requirement_checks": [{"requirement_id": "REQ-001", "status": "PASS", "evidence": []}],
                "acceptance_checks": [{"criterion": "Accepter", "status": "PASS", "evidence": []}],
                "issues": [],
                "tests": {"status": "PASS", "details": []},
                "scope": {"status": "PASS", "unexpected_paths": []},
            },
        )
        return {"command": ["codex", "exec"], "returncode": 0, "stdout": "", "stderr": ""}

    with pytest.raises(ReviewTaskError, match="rapport de tâche courant est incohérent"):
        review_task(backlog, "TASK-REPORT", codex_runner=fake_codex_runner)


def test_run_feature_writes_final_reports_and_does_not_replay_completed_feature(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-ONE")])
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(repo)

    first = run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )
    second = run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    assert first["status"] == "COMPLETED"
    assert second["status"] == "COMPLETED"
    assert capture["run"] == ["TASK-ONE"]
    assert (repo / ".autodev" / "runs" / "features" / "FEATURE-TEST" / "final-report.json").is_file()
    assert (repo / "reports" / "dev" / "FEATURE-TEST.md").is_file()


def test_status_command_reports_current_state_without_llm(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-STATE")])
    runner = CliRunner()

    result = runner.invoke(app, ["status", str(backlog)], catch_exceptions=False)

    assert result.exit_code == 0
    assert "FEATURE-TEST" in result.stdout
    assert "NOT_STARTED" in result.stdout


def test_codex_and_claude_timeout_profiles_are_fixed() -> None:
    assert TIMEOUTS_SECONDS["codex_plan"] == 900
    assert TIMEOUTS_SECONDS["codex_review"] == 900
    assert TIMEOUTS_SECONDS["claude_task"] == 1800
