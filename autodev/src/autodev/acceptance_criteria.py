from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


class AcceptanceCriteriaError(RuntimeError):
    """Erreur pendant la normalisation ou la couverture des critères."""


def normalize_backlog_acceptance_criteria(backlog: dict[str, Any]) -> dict[str, Any]:
    """Retourne une copie du backlog avec des critères structurés et propriétaires."""
    normalized = copy.deepcopy(backlog)
    tasks = normalized.get("tasks", [])
    requirements = normalized.get("requirements", [])
    task_ids = {
        task["id"]
        for task in tasks
        if isinstance(task, dict) and isinstance(task.get("id"), str)
    }
    task_index = {
        task["id"]: task
        for task in tasks
        if isinstance(task, dict) and isinstance(task.get("id"), str)
    }
    criterion_ids: set[str] = set()

    for requirement in requirements:
        requirement_id = str(requirement.get("id", "")).strip()
        raw_criteria = requirement.get("acceptance_criteria", [])
        if not isinstance(raw_criteria, list) or not raw_criteria:
            raise AcceptanceCriteriaError(
                f"{requirement_id or 'Une exigence'} doit contenir au moins un critère."
            )
        if all(isinstance(item, str) for item in raw_criteria):
            requirement["acceptance_criteria"] = _normalize_legacy_requirement(
                requirement_id=requirement_id,
                raw_criteria=raw_criteria,
                tasks=tasks,
                criterion_ids=criterion_ids,
            )
            continue
        if not all(isinstance(item, dict) for item in raw_criteria):
            raise AcceptanceCriteriaError(
                f"{requirement_id} mélange des critères textuels et structurés."
            )
        structured: list[dict[str, str]] = []
        for item in raw_criteria:
            keys = set(item.keys())
            expected = {"id", "text", "owner_task_id"}
            if keys != expected:
                raise AcceptanceCriteriaError(
                    f"{requirement_id} contient un critère structuré invalide."
                )
            criterion_id = _require_non_empty_string(item["id"], f"{requirement_id} contient un id de critère invalide.")
            criterion_text = _require_non_empty_string(
                item["text"],
                f"{criterion_id} contient un texte de critère invalide.",
                min_length=3,
            )
            owner_task_id = _require_non_empty_string(
                item["owner_task_id"],
                f"{criterion_id} contient un owner_task_id invalide.",
            )
            if owner_task_id not in task_ids:
                raise AcceptanceCriteriaError(
                    f"{criterion_id} référence une tâche propriétaire inconnue : {owner_task_id}."
                )
            owner_task = task_index[owner_task_id]
            if requirement_id not in owner_task.get("requirement_ids", []):
                raise AcceptanceCriteriaError(
                    f"{criterion_id} appartient à {owner_task_id} mais {owner_task_id} ne référence pas {requirement_id}."
                )
            if criterion_id in criterion_ids:
                raise AcceptanceCriteriaError(f"Identifiant de critère dupliqué : {criterion_id}.")
            criterion_ids.add(criterion_id)
            structured.append(
                {
                    "id": criterion_id,
                    "text": criterion_text,
                    "owner_task_id": owner_task_id,
                }
            )
        requirement["acceptance_criteria"] = structured

    return normalized


def migrate_backlog_acceptance_criteria(backlog: dict[str, Any]) -> dict[str, Any]:
    """Convertit un backlog legacy en critères structurés si l'attribution est non ambiguë."""
    migrated = copy.deepcopy(backlog)
    tasks = migrated.get("tasks", [])
    criterion_ids: set[str] = set()
    task_ids = {
        task["id"]
        for task in tasks
        if isinstance(task, dict) and isinstance(task.get("id"), str)
    }

    for requirement in migrated.get("requirements", []):
        requirement_id = str(requirement.get("id", "")).strip()
        raw_criteria = requirement.get("acceptance_criteria", [])
        if not isinstance(raw_criteria, list) or not raw_criteria:
            raise AcceptanceCriteriaError(
                f"{requirement_id or 'Une exigence'} doit contenir au moins un critère."
            )
        if all(isinstance(item, str) for item in raw_criteria):
            owner_task_id = _single_legacy_owner_for_migration(requirement_id, tasks)
            structured: list[dict[str, str]] = []
            for index, criterion_text in enumerate(raw_criteria, start=1):
                criterion_id = _legacy_criterion_id(requirement_id, index)
                if criterion_id in criterion_ids:
                    raise AcceptanceCriteriaError(f"Identifiant de critère dupliqué : {criterion_id}.")
                criterion_ids.add(criterion_id)
                structured.append(
                    {
                        "id": criterion_id,
                        "text": _require_non_empty_string(
                            criterion_text,
                            f"{requirement_id} contient un texte de critère invalide.",
                            min_length=3,
                        ),
                        "owner_task_id": owner_task_id,
                    }
                )
            requirement["acceptance_criteria"] = structured
            continue
        if not all(isinstance(item, dict) for item in raw_criteria):
            raise AcceptanceCriteriaError(
                f"{requirement_id} mélange des critères textuels et structurés."
            )
        for item in raw_criteria:
            if set(item.keys()) != {"id", "text", "owner_task_id"}:
                raise AcceptanceCriteriaError(
                    f"{requirement_id} contient un critère structuré invalide."
                )
            owner_task_id = _require_non_empty_string(
                item["owner_task_id"],
                f"{requirement_id} contient un owner_task_id invalide.",
            )
            if owner_task_id not in task_ids:
                raise AcceptanceCriteriaError(
                    f"{requirement_id} référence une tâche propriétaire inconnue : {owner_task_id}."
                )
            criterion_id = _require_non_empty_string(
                item["id"],
                f"{requirement_id} contient un id de critère invalide.",
            )
            if criterion_id in criterion_ids:
                raise AcceptanceCriteriaError(f"Identifiant de critère dupliqué : {criterion_id}.")
            criterion_ids.add(criterion_id)

    return normalize_backlog_acceptance_criteria(migrated)


def owned_criteria_by_task(backlog: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    normalized = normalize_backlog_acceptance_criteria(backlog)
    owned: dict[str, list[dict[str, str]]] = {}
    for requirement in normalized.get("requirements", []):
        requirement_id = requirement["id"]
        requirement_description = requirement["description"]
        for criterion in requirement["acceptance_criteria"]:
            owned.setdefault(criterion["owner_task_id"], []).append(
                {
                    "requirement_id": requirement_id,
                    "requirement_description": requirement_description,
                    "acceptance_criterion_id": criterion["id"],
                    "text": criterion["text"],
                }
            )
    for criteria in owned.values():
        criteria.sort(key=lambda item: (item["requirement_id"], item["acceptance_criterion_id"]))
    return owned


def build_coverage_matrix(backlog: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    normalized = normalize_backlog_acceptance_criteria(backlog)
    task_review_data = _load_task_review_data(repo_root, normalized.get("tasks", []))
    rows: list[dict[str, Any]] = []
    requirement_summaries: list[dict[str, Any]] = []

    for requirement in normalized.get("requirements", []):
        requirement_rows: list[dict[str, Any]] = []
        for criterion in requirement["acceptance_criteria"]:
            review_data = task_review_data.get(criterion["owner_task_id"], {})
            review_checks = review_data.get("requirement_checks", {})
            check = review_checks.get(criterion["id"])
            check_status = str(check.get("status") if check else "PENDING")
            criterion_status = _criterion_status(
                check_status=check_status,
                last_verdict=review_data.get("review_verdict"),
                owner_integrated=bool(review_data.get("owner_integrated")),
            )
            row = {
                "requirement_id": requirement["id"],
                "requirement_description": requirement["description"],
                "acceptance_criterion_id": criterion["id"],
                "text": criterion["text"],
                "owner_task_id": criterion["owner_task_id"],
                "owner_integrated": bool(review_data.get("owner_integrated")),
                "last_verdict": review_data.get("review_verdict") or "PENDING",
                "check_status": check_status,
                "criterion_status": criterion_status,
                "evidence": list(check.get("evidence", [])) if check else [],
            }
            rows.append(row)
            requirement_rows.append(row)
        requirement_summaries.append(
            {
                "requirement_id": requirement["id"],
                "description": requirement["description"],
                "status": _requirement_status(requirement_rows),
            }
        )

    approved = sum(1 for row in rows if row["criterion_status"] == "APPROVED")
    integrated = sum(1 for row in rows if row["owner_integrated"])
    pending = sum(1 for row in rows if row["criterion_status"] == "PENDING")
    failed = sum(1 for row in rows if row["criterion_status"] == "FAILED")
    coverage_percentage = int((approved / len(rows)) * 100) if rows else 0

    return {
        "rows": rows,
        "requirements": requirement_summaries,
        "summary": {
            "total": len(rows),
            "approved": approved,
            "integrated": integrated,
            "pending": pending,
            "failed": failed,
            "coverage_percentage": coverage_percentage,
        },
        "tasks": _build_task_coverage(rows),
    }


def render_coverage_text(coverage: dict[str, Any]) -> str:
    lines: list[str] = []
    current_requirement_id: str | None = None
    for row in coverage["rows"]:
        if row["requirement_id"] != current_requirement_id:
            current_requirement_id = row["requirement_id"]
            lines.append(current_requirement_id)
        lines.append(
            f"  {row['acceptance_criterion_id']}  {row['owner_task_id']}  {row['criterion_status']}"
        )
    summary = coverage["summary"]
    lines.extend(
        [
            "",
            f"Total critères : {summary['total']}",
            f"Critères approuvés : {summary['approved']}",
            f"Critères intégrés : {summary['integrated']}",
            f"Critères en attente : {summary['pending']}",
            f"Critères en échec : {summary['failed']}",
            f"Couverture : {summary['coverage_percentage']}%",
        ]
    )
    return "\n".join(lines)


def _normalize_legacy_requirement(
    *,
    requirement_id: str,
    raw_criteria: list[str],
    tasks: list[dict[str, Any]],
    criterion_ids: set[str],
) -> list[dict[str, str]]:
    owners = _legacy_requirement_owners(requirement_id, tasks)
    structured: list[dict[str, str]] = []
    for owner_task_id in owners:
        for index, criterion_text in enumerate(raw_criteria, start=1):
            criterion_id = _legacy_criterion_id(requirement_id, index, owner_task_id if len(owners) > 1 else None)
            if criterion_id in criterion_ids:
                raise AcceptanceCriteriaError(f"Identifiant de critère dupliqué : {criterion_id}.")
            criterion_ids.add(criterion_id)
            structured.append(
                {
                    "id": criterion_id,
                    "text": _require_non_empty_string(
                        criterion_text,
                        f"{requirement_id} contient un texte de critère invalide.",
                        min_length=3,
                    ),
                    "owner_task_id": owner_task_id,
                }
            )
    return structured


def _legacy_requirement_owners(requirement_id: str, tasks: list[dict[str, Any]]) -> list[str]:
    owners = [
        task["id"]
        for task in tasks
        if isinstance(task, dict)
        and isinstance(task.get("id"), str)
        and requirement_id in task.get("requirement_ids", [])
    ]
    if not owners:
        raise AcceptanceCriteriaError(
            f"Exigence non couverte par les tâches : {requirement_id}."
        )
    if len(owners) == 1:
        return owners
    if any(not _has_shared_requirement_justification(task, requirement_id) for task in tasks if task.get("id") in owners):
        owner_list = ", ".join(sorted(owners))
        raise AcceptanceCriteriaError(
            f"HUMAN_REVIEW_REQUIRED: exigence {requirement_id} rattachée à plusieurs tâches ({owner_list}) sans justification exploitable."
        )
    return sorted(owners)


def _single_legacy_owner_for_migration(requirement_id: str, tasks: list[dict[str, Any]]) -> str:
    owners = _legacy_requirement_owners(requirement_id, tasks)
    if len(owners) != 1:
        owner_list = ", ".join(owners)
        raise AcceptanceCriteriaError(
            f"HUMAN_REVIEW_REQUIRED: migration ambiguë pour {requirement_id}, propriétaires possibles : {owner_list}."
        )
    return owners[0]


def _has_shared_requirement_justification(task: dict[str, Any], requirement_id: str) -> bool:
    for item in task.get("shared_requirement_justifications", []):
        if (
            isinstance(item, dict)
            and item.get("requirement_id") == requirement_id
            and isinstance(item.get("justification"), str)
            and len(item["justification"].strip()) >= 10
        ):
            return True
    return False


def _legacy_criterion_id(requirement_id: str, index: int, owner_task_id: str | None = None) -> str:
    base = f"{requirement_id}-AC{index}"
    if owner_task_id:
        return f"{base}-{owner_task_id}"
    return base


def _require_non_empty_string(value: Any, message: str, *, min_length: int = 1) -> str:
    if not isinstance(value, str) or len(value.strip()) < min_length:
        raise AcceptanceCriteriaError(message)
    return value.strip()


def _load_task_review_data(repo_root: Path, tasks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = {}
    for task in tasks:
        task_id = task["id"]
        run_dir = repo_root / ".autodev" / "runs" / task_id
        review_result = _load_json_if_exists(run_dir / "review" / "review-result.json")
        integration_result = _load_json_if_exists(run_dir / "integration" / "integration-result.json")
        requirement_checks = {
            item["acceptance_criterion_id"]: item
            for item in review_result.get("requirement_checks", [])
            if isinstance(item, dict) and isinstance(item.get("acceptance_criterion_id"), str)
        }
        data[task_id] = {
            "review_verdict": review_result.get("verdict"),
            "owner_integrated": integration_result.get("status") == "INTEGRATED",
            "requirement_checks": requirement_checks,
        }
    return data


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _criterion_status(*, check_status: str, last_verdict: Any, owner_integrated: bool) -> str:
    if check_status == "FAIL":
        return "FAILED"
    if check_status == "PASS":
        return "APPROVED"
    if last_verdict == "HUMAN_REVIEW_REQUIRED":
        return "PENDING"
    if owner_integrated:
        return "APPROVED"
    return "PENDING"


def _requirement_status(rows: list[dict[str, Any]]) -> str:
    if any(row["criterion_status"] == "FAILED" for row in rows):
        return "FAIL"
    if rows and all(row["criterion_status"] == "APPROVED" and row["owner_integrated"] for row in rows):
        return "PASS"
    return "PARTIAL"


def _build_task_coverage(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    task_summary: dict[str, dict[str, int]] = {}
    for row in rows:
        summary = task_summary.setdefault(
            row["owner_task_id"],
            {"owned": 0, "approved": 0, "integrated": 0},
        )
        summary["owned"] += 1
        if row["criterion_status"] == "APPROVED":
            summary["approved"] += 1
        if row["owner_integrated"]:
            summary["integrated"] += 1
    return task_summary
