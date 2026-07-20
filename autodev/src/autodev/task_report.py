from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autodev.task_dependencies import get_next_task_id


class TaskReportError(RuntimeError):
    """Rapport de tâche incohérent."""


def build_task_report_payload(
    *,
    backlog: dict[str, Any],
    task: dict[str, Any],
    git_state: dict[str, Any],
    validations: list[dict[str, Any]],
    problems: list[str],
) -> dict[str, Any]:
    return {
        "task_id": task["id"],
        "feature_id": backlog["feature_id"],
        "objective": task["title"],
        "modified_files": list(git_state["modified_paths"]),
        "validations": [
            {
                "command": item.get("command"),
                "returncode": item.get("returncode"),
            }
            for item in validations
        ],
        "problems": list(problems),
        "next_task": get_next_task_id(backlog, task["id"]),
    }


def write_task_report(
    *,
    report_dir: Path,
    payload: dict[str, Any],
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "task-report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def verify_task_report(report_dir: Path, expected_payload: dict[str, Any]) -> None:
    report_path = report_dir / "task-report.json"
    if not report_path.is_file():
        write_task_report(report_dir=report_dir, payload=expected_payload)
        return
    actual = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(actual, dict):
        raise TaskReportError("Le rapport de tâche courant est incohérent avec le diff et les validations actuels.")

    expected_modified_files = expected_payload["modified_files"]
    actual_modified_files = actual.get("modified_files")
    if actual_modified_files != expected_modified_files:
        raise TaskReportError("Le rapport de tâche courant est incohérent avec le diff et les validations actuels.")

    expected_validations = expected_payload["validations"]
    actual_validations = actual.get("validations")
    if actual_validations != expected_validations:
        raise TaskReportError("Le rapport de tâche courant est incohérent avec le diff et les validations actuels.")

    expected_problems = expected_payload["problems"]
    actual_problems = actual.get("problems")
    if actual_problems != expected_problems:
        raise TaskReportError("Le rapport de tâche courant est incohérent avec le diff et les validations actuels.")

    expected_next_task = expected_payload["next_task"]
    actual_next_task = actual.get("next_task")
    if actual_next_task != expected_next_task:
        raise TaskReportError("Le rapport de tâche courant est incohérent avec le diff et les validations actuels.")
