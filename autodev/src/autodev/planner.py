from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from autodev.acceptance_criteria import AcceptanceCriteriaError, normalize_backlog_acceptance_criteria
from autodev.generated_artifacts import (
    command_installs_dependencies,
    command_is_manifestly_wide,
    infer_targeted_test_paths,
    is_dependency_manifest,
)
from autodev.path_rules import normalize_repo_relative_path


class PlanningError(RuntimeError):
    """Erreur pendant la génération ou la validation du backlog."""


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=current,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise PlanningError("Le répertoire courant n'appartient pas à un dépôt Git.")

    return Path(result.stdout.strip()).resolve()


def load_json(path: Path) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except FileNotFoundError as exc:
        raise PlanningError(f"Fichier introuvable : {path}") from exc
    except json.JSONDecodeError as exc:
        raise PlanningError(
            f"JSON invalide dans {path}, ligne {exc.lineno}, colonne {exc.colno}."
        ) from exc

    if not isinstance(data, dict):
        raise PlanningError(f"Le fichier {path} doit contenir un objet JSON.")

    return data


def validate_agent_assignment(task: dict[str, Any]) -> None:
    """Détecte quelques erreurs d'affectation manifestes."""
    agent = task["agent"]
    text = f'{task["title"]} {task["description"]}'.lower()

    tauri_backend_terms = (
        "commande tauri",
        "tauri command",
        "invoke_handler",
        "contrat tauri",
        "src-tauri",
        "rust",
        "cargo",
        "tauri::command",
    )
    tauri_terms = (
        "commande tauri",
        "tauri command",
        "invoke_handler",
        "contrat tauri",
    )
    mapping_terms = (
        "cartograph",
        "géométr",
        "coordonnée",
        "plan du cimetière",
        "spatial",
        "mapping",
    )

    if agent == "mapping":
        concerns_tauri = any(term in text for term in tauri_backend_terms)
        concerns_mapping = any(term in text for term in mapping_terms)

        if concerns_tauri and not concerns_mapping:
            raise PlanningError(
                f'{task["id"]} est affectée à mapping alors que son objet '
                "principal semble relever du backend Tauri."
            )

    if agent == "backend":
        concerns_tauri = any(term in text for term in tauri_terms)
        concerns_mapping = any(term in text for term in mapping_terms)

        if concerns_mapping and not concerns_tauri:
            raise PlanningError(
                f'{task["id"]} est affectée à backend alors que son objet '
                "principal semble relever du mapping."
            )


def validate_backlog_consistency(backlog: dict[str, Any]) -> None:
    try:
        normalized_backlog = normalize_backlog_acceptance_criteria(backlog)
    except AcceptanceCriteriaError as exc:
        raise PlanningError(str(exc)) from exc

    requirements = normalized_backlog.get("requirements", [])
    tasks = backlog.get("tasks", [])

    requirement_ids = {
        requirement["id"]
        for requirement in requirements
        if isinstance(requirement, dict) and "id" in requirement
    }

    task_ids = [
        task["id"]
        for task in tasks
        if isinstance(task, dict) and "id" in task
    ]
    task_id_set = set(task_ids)

    if len(task_ids) != len(task_id_set):
        raise PlanningError("Le backlog contient des identifiants de tâches dupliqués.")

    for task in tasks:
        task_id = task["id"]

        if task_id in task["depends_on"]:
            raise PlanningError(f"{task_id} dépend de lui-même.")

        unknown_dependencies = set(task["depends_on"]) - task_id_set
        if unknown_dependencies:
            dependencies = ", ".join(sorted(unknown_dependencies))
            raise PlanningError(
                f"{task_id} référence des dépendances inconnues : {dependencies}"
            )

        unknown_requirements = set(task["requirement_ids"]) - requirement_ids
        if unknown_requirements:
            requirements_list = ", ".join(sorted(unknown_requirements))
            raise PlanningError(
                f"{task_id} référence des exigences inconnues : {requirements_list}"
            )

        validate_shared_requirement_justifications(task, requirement_ids)
        validate_allowed_paths(task)
        validate_dependency_reproducibility(task)
        validate_targeted_validations(task)
        validate_agent_assignment(task)

    covered_requirements: set[str] = set()

    for task in tasks:
        covered_requirements.update(task["requirement_ids"])

    uncovered = requirement_ids - covered_requirements
    if uncovered:
        missing = ", ".join(sorted(uncovered))
        raise PlanningError(f"Exigences non couvertes par les tâches : {missing}")

    validate_requirement_allocations(backlog, normalized_backlog)
    _validate_no_dependency_cycle(tasks)


def _validate_no_dependency_cycle(tasks: list[dict[str, Any]]) -> None:
    dependencies = {
        task["id"]: set(task["depends_on"])
        for task in tasks
    }

    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in permanent:
            return

        if task_id in temporary:
            raise PlanningError(
                f"Cycle détecté dans les dépendances autour de {task_id}."
            )

        temporary.add(task_id)

        for dependency_id in dependencies[task_id]:
            visit(dependency_id)

        temporary.remove(task_id)
        permanent.add(task_id)

    for current_task_id in dependencies:
        visit(current_task_id)


def validate_allowed_paths(task: dict[str, Any]) -> None:
    task_id = task["id"]
    for allowed_path in task["allowed_paths"]:
        try:
            normalize_repo_relative_path(allowed_path)
        except ValueError as exc:
            raise PlanningError(
                f"{task_id} contient un allowed_path invalide : {exc}"
            ) from exc


def validate_dependency_reproducibility(task: dict[str, Any]) -> None:
    task_id = task["id"]
    allowed_paths = task.get("allowed_paths", [])
    reason = str(task.get("dependency_change_reason", "")).strip()
    for allowed_path in allowed_paths:
        if is_dependency_manifest(allowed_path) and not reason:
            raise PlanningError(
                f"{task_id} modifie {allowed_path} sans dependency_change_reason explicite."
            )
    for command in task.get("validation_commands", []):
        if command_installs_dependencies(command):
            raise PlanningError(
                f"{task_id} contient une commande interdite de modification des dépendances : {command}"
            )


def validate_targeted_validations(task: dict[str, Any]) -> None:
    task_id = task["id"]
    commands = task.get("validation_commands", [])
    justification = str(task.get("validation_scope_justification", "")).strip()
    targeted_tests = infer_targeted_test_paths(task.get("allowed_paths", []))
    if not targeted_tests:
        return
    for command in commands:
        if command_is_manifestly_wide(command) and not justification:
            tests = ", ".join(targeted_tests)
            raise PlanningError(
                f"{task_id} utilise une validation trop large ({command}) alors que des tests ciblés sont déductibles : {tests}"
            )


def validate_shared_requirement_justifications(
    task: dict[str, Any],
    requirement_ids: set[str],
) -> None:
    task_id = task.get("id", "<tâche inconnue>")
    raw = task.get("shared_requirement_justifications", [])

    if not isinstance(raw, list):
        raise PlanningError(
            f"{task_id} contient shared_requirement_justifications invalide."
        )

    seen_requirement_ids: set[str] = set()

    for item in raw:
        if not isinstance(item, dict):
            raise PlanningError(
                f"{task_id} contient une justification partagée invalide."
            )

        requirement_id = item.get("requirement_id")
        justification = item.get("justification")

        if not isinstance(requirement_id, str) or not requirement_id.strip():
            raise PlanningError(
                f"{task_id} contient un requirement_id partagé invalide."
            )

        if requirement_id not in requirement_ids:
            raise PlanningError(
                f"{task_id} justifie une exigence inconnue : {requirement_id}."
            )

        if requirement_id in seen_requirement_ids:
            raise PlanningError(
                f"{task_id} contient plusieurs justifications pour "
                f"{requirement_id}."
            )

        if not isinstance(justification, str) or len(justification.strip()) < 10:
            raise PlanningError(
                f"{task_id} contient une justification insuffisante pour "
                f"{requirement_id}."
            )

        seen_requirement_ids.add(requirement_id)


def validate_requirement_allocations(
    original_backlog: dict[str, Any],
    normalized_backlog: dict[str, Any],
) -> None:
    tasks = normalized_backlog.get("tasks", [])
    requirements = normalized_backlog.get("requirements", [])
    original_requirements = {
        requirement["id"]: requirement
        for requirement in original_backlog.get("requirements", [])
        if isinstance(requirement, dict) and "id" in requirement
    }
    assignments: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        for requirement_id in task["requirement_ids"]:
            assignments.setdefault(requirement_id, []).append(task)

    duplicated = {
        requirement_id: attached_tasks
        for requirement_id, attached_tasks in assignments.items()
        if len(attached_tasks) > 1
    }

    for requirement_id, attached_tasks in duplicated.items():
        original_requirement = original_requirements.get(requirement_id, {})
        raw_criteria = original_requirement.get("acceptance_criteria", [])
        if raw_criteria and all(isinstance(item, dict) for item in raw_criteria):
            owners = {
                criterion["owner_task_id"]
                for requirement in requirements
                if requirement["id"] == requirement_id
                for criterion in requirement["acceptance_criteria"]
            }
            missing_owner = sorted(task["id"] for task in attached_tasks if task["id"] not in owners)
            if missing_owner:
                missing_list = ", ".join(missing_owner)
                raise PlanningError(
                    f"Exigence {requirement_id} répartie sans critère propriétaire pour : {missing_list}"
                )
            continue

        missing_justification = [
            task["id"]
            for task in attached_tasks
            if not str(
                next(
                    (
                        item.get("justification", "")
                        for item in task.get(
                            "shared_requirement_justifications", []
                        )
                        if isinstance(item, dict)
                        and item.get("requirement_id") == requirement_id
                    ),
                    "",
                )
            ).strip()
        ]
        if missing_justification:
            task_list = ", ".join(sorted(task["id"] for task in attached_tasks))
            missing_list = ", ".join(sorted(missing_justification))
            raise PlanningError(
                f"Exigence {requirement_id} rattachée à plusieurs tâches ({task_list}) "
                f"sans justification explicite pour : {missing_list}"
            )

    for requirement in requirements:
        if not requirement["acceptance_criteria"]:
            raise PlanningError(f"{requirement['id']} doit conserver au moins un critère.")


def plan_feature(spec_path: Path) -> tuple[Path, dict[str, Any]]:
    repo_root = find_repo_root()
    absolute_spec = (
        spec_path if spec_path.is_absolute() else repo_root / spec_path
    ).resolve()

    if not absolute_spec.is_file():
        raise PlanningError(f"Spécification introuvable : {absolute_spec}")

    try:
        relative_spec = absolute_spec.relative_to(repo_root)
    except ValueError as exc:
        raise PlanningError(
            "La spécification doit se trouver dans le dépôt Git."
        ) from exc

    prompt_path = repo_root / "autodev/prompts/plan-feature.md"
    schema_path = repo_root / "autodev/schemas/backlog.schema.json"
    output_dir = repo_root / ".autodev/plans"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{absolute_spec.stem}.backlog.json"

    static_prompt = prompt_path.read_text(encoding="utf-8")

    dynamic_prompt = f"""
{static_prompt}

SPÉCIFICATION À ANALYSER
========================

Chemin : {relative_spec}

Lis intégralement ce fichier dans le dépôt.

Inspecte également uniquement les fichiers du dépôt nécessaires pour comprendre :

- l'architecture existante ;
- les commandes de build ;
- les commandes de tests ;
- les chemins réels du frontend ;
- les chemins réels du backend Rust/Tauri ;
- les conventions déjà utilisées.

Le backlog doit correspondre au dépôt réel, pas à une arborescence théorique.

Contraintes supplémentaires sur `allowed_paths` :

- utiliser uniquement des chemins relatifs à la racine du dépôt ;
- ne jamais inclure de chemin absolu ;
- ne jamais inclure `/home/...` ni aucun chemin dépendant de la machine ;
- ne jamais inclure de segment `..`.
""".strip()

    command = [
        "codex",
        "exec",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "--output-schema",
        str(schema_path),
        "-o",
        str(output_path),
        dynamic_prompt,
    ]

    result = subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise PlanningError(
            f"Codex a échoué avec le code de sortie {result.returncode}."
        )

    backlog = load_json(output_path)
    backlog["specification_path"] = relative_spec.as_posix()
    validate_backlog_consistency(backlog)

    formatted = json.dumps(
        backlog,
        ensure_ascii=False,
        indent=2,
    )
    output_path.write_text(formatted + "\n", encoding="utf-8")

    return output_path, backlog
