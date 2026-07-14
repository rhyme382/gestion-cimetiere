from __future__ import annotations

from pathlib import Path

from autodev.planner import PlanningError, load_json

INTEGRATED_STATUS = "INTEGRATED"


def integration_result_path(repo_root: Path, task_id: str) -> Path:
    return repo_root / ".autodev" / "runs" / task_id / "integration" / "integration-result.json"


def is_task_integrated(repo_root: Path, task_id: str) -> bool:
    path = integration_result_path(repo_root, task_id)
    if not path.is_file():
        return False
    try:
        payload = load_json(path)
    except PlanningError:
        return False
    return payload.get("status") == INTEGRATED_STATUS


def get_unfinished_dependencies(repo_root: Path, task: dict[str, object]) -> list[str]:
    dependencies = task.get("depends_on", [])
    if not isinstance(dependencies, list):
        return []
    return [
        dependency_id
        for dependency_id in dependencies
        if isinstance(dependency_id, str) and not is_task_integrated(repo_root, dependency_id)
    ]
