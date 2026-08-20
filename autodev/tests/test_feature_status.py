from __future__ import annotations

import json
from pathlib import Path

from autodev.feature_status import read_feature_status

from test_run_feature import create_task_workspace, write_integration_result, write_review_result
from test_task_runner import commit_all, init_repo, make_task, write_backlog


def test_status_reconciles_stale_feature_result_with_integrated_tasks(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-STATUS")])
    commit_all(repo, "prepare backlog")
    create_task_workspace(repo, backlog, "TASK-STATUS", make_commit=True)
    write_review_result(repo, "TASK-STATUS", "APPROVED")
    write_integration_result(repo, "TASK-STATUS", "INTEGRATED")

    run_dir = repo / ".autodev" / "runs" / "features" / "FEATURE-TEST"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run-feature-result.json").write_text(
        json.dumps({"status": "HUMAN_REVIEW_REQUIRED"}), encoding="utf-8"
    )

    status = read_feature_status(backlog)

    assert status["feature_status"] == "COMPLETED"
    assert status["historical_feature_status"] == "HUMAN_REVIEW_REQUIRED"
    assert status["tasks_integrated"] == ["TASK-STATUS"]
