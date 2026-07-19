from __future__ import annotations

import json

import pytest

from autodev.planner import PlanningError, validate_backlog_consistency

from test_task_runner import init_repo, make_task, write_backlog


def test_single_requirement_assigned_to_one_task_is_valid(tmp_path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-SOLO")])

    validate_backlog_consistency(json.loads(backlog.read_text(encoding="utf-8")))


def test_duplicate_requirement_without_explicit_justification_is_rejected(tmp_path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(
        repo,
        [
            make_task("TASK-CONTRACT", requirement_ids=["REQ-001"]),
            make_task("TASK-UI", requirement_ids=["REQ-001"]),
        ],
        requirements=[
            {
                "id": "REQ-001",
                "description": "Description requirement",
                "acceptance_criteria": ["Critère 1"],
            }
        ],
    )

    with pytest.raises(PlanningError, match="REQ-001 rattachée à plusieurs tâches"):
        validate_backlog_consistency(json.loads(backlog.read_text(encoding="utf-8")))


def test_duplicate_requirement_with_explicit_justification_is_accepted(tmp_path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(
        repo,
        [
            make_task(
                "TASK-CONTRACT",
                requirement_ids=["REQ-001"],
                shared_requirement_justifications=[
                    {
                        "requirement_id": "REQ-001",
                        "justification": "Cette tâche livre le contrat TypeScript partagé avec la couche UI.",
                    }
                ],
            ),
            make_task(
                "TASK-UI",
                depends_on=["TASK-CONTRACT"],
                requirement_ids=["REQ-001"],
                shared_requirement_justifications=[
                    {
                        "requirement_id": "REQ-001",
                        "justification": "Cette tâche couvre explicitement la partie affichage de la même exigence transverse.",
                    }
                ],
            ),
        ],
        requirements=[
            {
                "id": "REQ-001",
                "description": "Description requirement",
                "acceptance_criteria": ["Critère 1"],
            }
        ],
    )

    validate_backlog_consistency(json.loads(backlog.read_text(encoding="utf-8")))
