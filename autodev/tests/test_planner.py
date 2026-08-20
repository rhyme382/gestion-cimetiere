from __future__ import annotations

import json
from pathlib import Path

import pytest

from autodev.planner import PlanningError, validate_backlog_consistency

from test_task_runner import init_repo, make_task, write_backlog


def _backlog_output_schema() -> dict:
    schema_path = Path(__file__).parents[1] / "schemas" / "backlog.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _walk_schema(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk_schema(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_schema(child)


def test_backlog_output_schema_uses_structured_acceptance_criteria() -> None:
    schema = _backlog_output_schema()
    criterion = schema["properties"]["requirements"]["items"]["properties"][
        "acceptance_criteria"
    ]["items"]

    assert criterion["type"] == "object"
    assert criterion["additionalProperties"] is False
    assert set(criterion["required"]) == {"id", "text", "owner_task_id"}
    assert set(criterion["properties"]) == {"id", "text", "owner_task_id"}


def test_backlog_output_schema_has_no_composition_keywords() -> None:
    schema = _backlog_output_schema()

    for node in _walk_schema(schema):
        if isinstance(node, dict):
            assert not ({"oneOf", "anyOf", "allOf"} & node.keys())


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
