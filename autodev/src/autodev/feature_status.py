from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autodev.git_tools import branch_exists, git_output, worktree_registered
from autodev.planner import PlanningError, find_repo_root, load_json, validate_backlog_consistency
from autodev.run_feature import determine_task_resume_action
from autodev.task_dependencies import is_task_integrated


class FeatureStatusError(RuntimeError):
    """Erreur pendant le calcul du statut."""


def read_feature_status(backlog_json: Path) -> dict[str, Any]:
    repo_root = find_repo_root(backlog_json.parent)
    try:
        backlog = load_json(backlog_json)
        validate_backlog_consistency(backlog)
    except PlanningError as exc:
        raise FeatureStatusError(str(exc)) from exc

    feature_id = backlog["feature_id"]
    run_dir = repo_root / ".autodev" / "runs" / "features" / feature_id
    summary = _load_json_if_exists(run_dir / "run-feature-result.json")
    last_state = _load_json_if_exists(run_dir / "last-state.json")
    integrated = [task["id"] for task in backlog["tasks"] if is_task_integrated(repo_root, task["id"])]
    historical_status = summary.get("status") or last_state.get("status")
    all_tasks_integrated = bool(backlog["tasks"]) and len(integrated) == len(backlog["tasks"])
    current_task = _infer_current_task(repo_root, backlog)
    worktrees = _list_worktrees(repo_root)

    inconsistencies: list[str] = []
    for task in backlog["tasks"]:
        task_id = task["id"]
        decision = determine_task_resume_action(repo_root=repo_root, task_id=task_id)
        if decision.action == "INVALID_STATE":
            inconsistencies.append(decision.reason or task_id)

    return {
        "feature_id": feature_id,
        "feature_title": backlog["feature_title"],
        "feature_status": "COMPLETED" if all_tasks_integrated else historical_status or "NOT_STARTED",
        "historical_feature_status": historical_status,
        "tasks_integrated": integrated,
        "current_task_id": current_task,
        "last_action": last_state.get("task_action"),
        "last_verdict": last_state.get("last_verdict"),
        "correction_count": last_state.get("correction_count", 0),
        "worktrees": worktrees,
        "inconsistencies": inconsistencies,
        "reports_path": str(run_dir),
    }


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _infer_current_task(repo_root: Path, backlog: dict[str, Any]) -> str | None:
    for task in backlog["tasks"]:
        task_id = task["id"]
        if is_task_integrated(repo_root, task_id):
            continue
        branch = f"autodev/{task_id}"
        worktree = repo_root / ".autodev" / "worktrees" / task_id
        if branch_exists(repo_root, branch) or worktree.exists() or worktree_registered(repo_root, worktree):
            return task_id
    return None


def _list_worktrees(repo_root: Path) -> list[str]:
    output = git_output(repo_root, ["worktree", "list", "--porcelain"])
    paths: list[str] = []
    for line in output.splitlines():
        if line.startswith("worktree "):
            paths.append(line.removeprefix("worktree ").strip())
    return paths
