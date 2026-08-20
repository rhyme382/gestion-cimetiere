from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autodev.git_tools import (
    GitError,
    branch_head,
    changed_paths_between,
    count_tracked_commits_between,
    diff_patch_between,
    name_status_between,
)
from autodev.planner import PlanningError, load_json


class GitContextError(RuntimeError):
    """État Git de tâche invalide ou incomplet."""


@dataclass(frozen=True)
class CurrentTaskGitState:
    task_id: str
    branch: str
    worktree: Path
    base_commit: str
    produced_commit: str
    modified_paths: list[str]
    name_status: list[str]
    diff_text: str


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return load_json(path)
    except PlanningError as exc:
        raise GitContextError(str(exc)) from exc


def resolve_task_metadata(repo_root: Path, task_id: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    run_dir = repo_root / ".autodev" / "runs" / task_id
    run_result = load_optional_json(run_dir / "result.json")
    task_record = load_optional_json(run_dir / "task.json")
    return run_dir, run_result, task_record


def resolve_base_commit(task_id: str, run_result: dict[str, Any], task_record: dict[str, Any]) -> str:
    base_commit = run_result.get("base_commit") or task_record.get("base_commit")
    if not isinstance(base_commit, str) or not base_commit.strip():
        raise GitContextError(f"Commit de départ introuvable pour {task_id}.")
    return base_commit


def resolve_worktree(repo_root: Path, task_id: str, run_result: dict[str, Any], task_record: dict[str, Any]) -> Path:
    raw_value = (
        run_result.get("worktree")
        or task_record.get("worktree")
        or str(repo_root / ".autodev" / "worktrees" / task_id)
    )
    return Path(str(raw_value))


def resolve_produced_commit(repo_root: Path, task_id: str, branch: str, base_commit: str) -> str:
    try:
        produced_commit = branch_head(repo_root, branch)
        if count_tracked_commits_between(repo_root, base_commit, branch) <= 0:
            raise GitContextError(f"Aucun commit produit courant détecté pour {task_id}.")
        return produced_commit
    except GitError as exc:
        raise GitContextError(str(exc)) from exc


def build_current_task_git_state(repo_root: Path, task_id: str) -> CurrentTaskGitState:
    branch = f"autodev/{task_id}"
    _, run_result, task_record = resolve_task_metadata(repo_root, task_id)
    base_commit = resolve_base_commit(task_id, run_result, task_record)
    worktree = resolve_worktree(repo_root, task_id, run_result, task_record)
    produced_commit = resolve_produced_commit(repo_root, task_id, branch, base_commit)

    try:
        modified_paths = changed_paths_between(repo_root, base_commit, produced_commit)
        name_status = name_status_between(repo_root, base_commit, produced_commit)
        diff_text = diff_patch_between(repo_root, base_commit, produced_commit)
    except GitError as exc:
        raise GitContextError(str(exc)) from exc

    return CurrentTaskGitState(
        task_id=task_id,
        branch=branch,
        worktree=worktree,
        base_commit=base_commit,
        produced_commit=produced_commit,
        modified_paths=modified_paths,
        name_status=name_status,
        diff_text=diff_text,
    )
