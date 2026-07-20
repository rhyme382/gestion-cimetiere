from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autodev.git_context import GitContextError, build_current_task_git_state
from autodev.git_tools import (
    branch_exists,
    git_status_porcelain,
)
from autodev.path_rules import normalize_repo_relative_path
from autodev.planner import PlanningError, find_repo_root, load_json, validate_backlog_consistency
from autodev.process_runner import TIMEOUTS_SECONDS, run_process_capturing_timeout
from autodev.task_report import TaskReportError, build_task_report_payload, verify_task_report
from autodev.task_runner import (
    RunTaskError,
    find_task,
    run_validation_commands,
    validate_command_safe,
    write_json,
)

REVIEW_VERDICTS = {"APPROVED", "CORRECTION_REQUIRED", "HUMAN_REVIEW_REQUIRED"}
CHECK_STATUSES = {"PASS", "FAIL", "UNCERTAIN"}
ISSUE_SEVERITIES = {"blocking", "major", "minor"}
TEST_STATUSES = {"PASS", "FAIL"}
SCOPE_STATUSES = {"PASS", "FAIL"}


class ReviewTaskError(RuntimeError):
    """Erreur pendant la revue automatique d'une tâche."""


def review_task(
    backlog_json: Path,
    task_id: str,
    codex_runner: Any | None = None,
) -> dict[str, Any]:
    repo_root = find_repo_root(backlog_json.parent)
    backlog = load_and_validate_backlog(backlog_json)
    try:
        task = find_task(backlog, task_id)
    except RunTaskError as exc:
        raise ReviewTaskError(str(exc)) from exc

    branch = f"autodev/{task_id}"
    if not branch_exists(repo_root, branch):
        raise ReviewTaskError(f"Branche de tâche absente : {branch}")

    run_dir = repo_root / ".autodev" / "runs" / task_id
    review_dir = run_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    run_result = load_optional_json(run_dir / "result.json")
    task_record = load_optional_json(run_dir / "task.json")
    try:
        git_state = build_current_task_git_state(repo_root, task_id)
    except GitContextError as exc:
        raise ReviewTaskError(str(exc)) from exc
    review_delivery = collect_review_delivery(repo_root, review_dir, git_state)
    modified_paths = review_delivery["modified_paths"]
    unexpected_paths = find_unexpected_paths(task["allowed_paths"], modified_paths)

    validation_results, validation_source = load_or_rerun_validations(
        repo_root=repo_root,
        worktree=git_state.worktree,
        task=task,
        run_result=run_result,
    )
    validation_payload = {
        "task_id": task_id,
        "source": validation_source,
        "results": validation_results,
    }
    write_json(review_dir / "validation-results.json", validation_payload)

    expected_report = build_task_report_payload(
        backlog=backlog,
        task=task,
        git_state=review_delivery,
        validations=validation_results,
        problems=unexpected_paths,
    )
    try:
        verify_task_report(run_dir, expected_report)
    except TaskReportError as exc:
        raise ReviewTaskError(str(exc)) from exc

    spec_path = resolve_specification_path(repo_root, backlog)
    prompt = build_review_prompt(
        repo_root=repo_root,
        backlog_json=backlog_json,
        backlog=backlog,
        task=task,
        spec_path=spec_path,
        base_commit=git_state.base_commit,
        produced_commit=git_state.produced_commit,
        modified_paths=modified_paths,
        name_status_lines=review_delivery["name_status"],
        unexpected_paths=unexpected_paths,
        validation_payload=validation_payload,
        dependency_context=collect_integrated_dependency_context(repo_root, backlog, task),
        diff_text=review_delivery["diff_text"],
    )
    (review_dir / "review-prompt.md").write_text(prompt, encoding="utf-8")

    schema_path = repo_root / "autodev" / "schemas" / "review-result.schema.json"
    output_path = review_dir / "review-result.json"
    codex_runner = codex_runner or run_codex_review
    codex_result = codex_runner(
        cwd=git_state.worktree if git_state.worktree.exists() else repo_root,
        prompt=prompt,
        schema_path=schema_path,
        output_path=output_path,
    )
    (review_dir / "codex.stdout.log").write_text(codex_result["stdout"], encoding="utf-8")
    (review_dir / "codex.stderr.log").write_text(codex_result["stderr"], encoding="utf-8")

    if codex_result["returncode"] != 0:
        raise ReviewTaskError(
            f"Codex a échoué (code {codex_result['returncode']}) : "
            f"{codex_result['stderr'].strip() or codex_result['stdout'].strip() or 'erreur inconnue'}"
        )

    review_result = load_json(output_path)
    validate_review_result(review_result, task_id)
    review_result = enforce_review_constraints(
        review_result=review_result,
        task_id=task_id,
        unexpected_paths=unexpected_paths,
        validation_results=validation_results,
    )
    write_json(output_path, review_result)
    return review_result


def load_and_validate_backlog(backlog_json: Path) -> dict[str, Any]:
    try:
        backlog = load_json(backlog_json)
        validate_backlog_consistency(backlog)
    except PlanningError as exc:
        raise ReviewTaskError(str(exc)) from exc
    return backlog


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return load_json(path)
    except PlanningError as exc:
        raise ReviewTaskError(str(exc)) from exc


def collect_review_delivery(
    repo_root: Path,
    review_dir: Path,
    git_state: Any,
) -> dict[str, Any]:
    write_json(
        review_dir / "current-paths.json",
        {
            "base_commit": git_state.base_commit,
            "produced_commit": git_state.produced_commit,
            "modified_paths": git_state.modified_paths,
            "name_status": git_state.name_status,
        },
    )
    (review_dir / "current-name-status.txt").write_text(
        "\n".join(git_state.name_status) + ("\n" if git_state.name_status else ""),
        encoding="utf-8",
    )
    (review_dir / "current-diff.patch").write_text(git_state.diff_text, encoding="utf-8")
    return {
        "base_commit": git_state.base_commit,
        "produced_commit": git_state.produced_commit,
        "modified_paths": git_state.modified_paths,
        "name_status": git_state.name_status,
        "diff_text": git_state.diff_text,
    }


def find_unexpected_paths(allowed_paths: list[str], modified_paths: list[str]) -> list[str]:
    allowed = [normalize_allowed_path(item) for item in allowed_paths]
    unexpected: list[str] = []
    for modified_path in modified_paths:
        candidate = normalize_modified_path(modified_path)
        if not any(is_relative_to(candidate, allowed_path) for allowed_path in allowed):
            unexpected.append(candidate.as_posix())
    return unexpected


def normalize_allowed_path(allowed_path: str) -> Path:
    try:
        return normalize_repo_relative_path(allowed_path)
    except ValueError as exc:
        raise ReviewTaskError(str(exc)) from exc


def normalize_modified_path(modified_path: str) -> Path:
    try:
        return normalize_repo_relative_path(modified_path)
    except ValueError as exc:
        raise ReviewTaskError(str(exc)) from exc


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def load_or_rerun_validations(
    repo_root: Path,
    worktree: Path,
    task: dict[str, Any],
    run_result: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    recorded = run_result.get("validations")
    if isinstance(recorded, list) and recorded:
        return recorded, "recorded"
    if not worktree.exists():
        raise ReviewTaskError(
            "Aucun résultat de validation enregistré et worktree introuvable pour relancer les tests."
        )
    return rerun_validations(repo_root, worktree, task["validation_commands"]), "rerun"


def rerun_validations(
    repo_root: Path,
    worktree: Path,
    commands: list[str],
) -> list[dict[str, Any]]:
    for command in commands:
        validate_command_safe(command)

    before_status = git_status_porcelain(repo_root, cwd=worktree)
    try:
        results = run_validation_commands(
            worktree,
            commands,
            extra_env={"PYTHONDONTWRITEBYTECODE": "1"},
        )
    except RunTaskError as exc:
        raise ReviewTaskError(str(exc)) from exc
    after_status = git_status_porcelain(repo_root, cwd=worktree)
    if before_status != after_status:
        raise ReviewTaskError("Les validations ont modifié le worktree, revue annulée.")
    return results


def resolve_specification_path(repo_root: Path, backlog: dict[str, Any]) -> Path:
    raw_path = backlog.get("specification_path", "SPEC.md")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ReviewTaskError("Champ specification_path manquant ou invalide dans le backlog.")
    try:
        relative_path = normalize_repo_relative_path(raw_path)
    except ValueError as exc:
        raise ReviewTaskError(f"specification_path invalide : {exc}") from exc
    spec_path = repo_root / relative_path
    if not spec_path.is_file():
        raise ReviewTaskError(f"Spécification introuvable : {spec_path}")
    return spec_path


def build_review_prompt(
    repo_root: Path,
    backlog_json: Path,
    backlog: dict[str, Any],
    task: dict[str, Any],
    spec_path: Path,
    base_commit: str,
    produced_commit: str,
    modified_paths: list[str],
    name_status_lines: list[str],
    unexpected_paths: list[str],
    validation_payload: dict[str, Any],
    dependency_context: list[dict[str, Any]],
    diff_text: str,
) -> str:
    specification = spec_path.read_text(encoding="utf-8")
    exact_task_id = task["id"]
    requirements = [
        requirement
        for requirement in backlog["requirements"]
        if requirement["id"] in set(task["requirement_ids"])
    ]
    requirement_blob = json.dumps(requirements, ensure_ascii=False, indent=2)
    task_blob = json.dumps(task, ensure_ascii=False, indent=2)
    validation_blob = json.dumps(validation_payload, ensure_ascii=False, indent=2)
    dependency_blob = json.dumps(dependency_context, ensure_ascii=False, indent=2)
    modified_blob = "\n".join(f"- {path}" for path in modified_paths) or "- Aucun"
    name_status_blob = "\n".join(f"- {line}" for line in name_status_lines) or "- Aucun"
    unexpected_blob = "\n".join(f"- {path}" for path in unexpected_paths) or "- Aucun"

    return f"""# Revue automatique de tâche autodev

Tu agis comme reviewer strict en lecture seule.

Contraintes impératives :

- ne modifier aucun fichier ;
- ne proposer aucun merge ;
- t'appuyer uniquement sur les informations fournies ;
- évaluer la tâche courante avec son propre périmètre de preuve ;
- appliquer strictement les règles de verdict ci-dessous.

Backlog : `{backlog_json}`
Feature : `{backlog["feature_id"]}` — {backlog["feature_title"]}
Tâche revue : `{exact_task_id}`
Commit de départ : `{base_commit}`
Commit produit : `{produced_commit}`

# Identifiant exact à restituer

L'identifiant exact de la tâche est : `{exact_task_id}`
Retourne exactement cette valeur dans `task_id`.
Ne la préfixe pas, ne la normalise pas et ne la transforme pas.

# Règles de verdict

- `APPROVED` uniquement si toutes les exigences liées sont `PASS`, tous les critères d'acceptation sont `PASS`, les tests requis réussissent, aucun fichier hors périmètre n'est modifié et aucun problème `blocking` ou `major` n'est présent.
- `CORRECTION_REQUIRED` si un critère ou une exigence est `FAIL`, si un test échoue, si un fichier hors périmètre est modifié ou si un problème `blocking` ou `major` est trouvé.
- `HUMAN_REVIEW_REQUIRED` uniquement si une ambiguïté métier, une information manquante ou une impossibilité d'évaluer automatiquement empêche la décision.

# Règles spécifiques aux dépendances intégrées

- Les tâches dans `depends_on` déjà intégrées fournissent un contexte de preuve complémentaire.
- N'exige jamais que les fichiers d'une dépendance intégrée réapparaissent dans le diff Git courant.
- Si un livrable requis pour une exigence provient uniquement d'une dépendance déjà intégrée, utilise son artefact d'intégration et sa revue `APPROVED` comme preuve héritée.
- Une tâche dépendante ne doit pas être pénalisée pour ne pas réimplémenter ni reprouver les exigences déjà satisfaites par ses dépendances intégrées.
- Évalue les critères d'acceptation propres à la tâche courante avec le diff courant ; utilise les preuves héritées uniquement pour les livrables dépendants déjà intégrés.

# Spécification source complète

Chemin : `{spec_path.relative_to(repo_root).as_posix()}`

```md
{specification}
```

# Tâche complète

```json
{task_blob}
```

# Exigences liées

```json
{requirement_blob}
```

# Critères d'acceptation de la tâche

{chr(10).join(f"- {criterion}" for criterion in task["acceptance_criteria"])}

# Fichiers modifiés

{modified_blob}

# Git name-status

{name_status_blob}

# Fichiers hors périmètre détectés

{unexpected_blob}

# Résultats des validations

```json
{validation_blob}
```

# Dépendances intégrées et preuves héritées

```json
{dependency_blob}
```

# Diff Git complet

```diff
{diff_text}
```

# Attendu pour la réponse

La réponse doit respecter exactement le schéma JSON fourni par `--output-schema`.
Le champ `task_id` doit reprendre exactement `{exact_task_id}`.
"""


def collect_integrated_dependency_context(
    repo_root: Path,
    backlog: dict[str, Any],
    task: dict[str, Any],
) -> list[dict[str, Any]]:
    task_index = {
        candidate["id"]: candidate
        for candidate in backlog.get("tasks", [])
        if isinstance(candidate, dict) and "id" in candidate
    }
    requirement_index = {
        requirement["id"]: requirement
        for requirement in backlog.get("requirements", [])
        if isinstance(requirement, dict) and "id" in requirement
    }

    context: list[dict[str, Any]] = []
    for dependency_id in task.get("depends_on", []):
        if not isinstance(dependency_id, str):
            continue
        run_dir = repo_root / ".autodev" / "runs" / dependency_id
        integration_result = load_optional_json(run_dir / "integration" / "integration-result.json")
        if integration_result.get("status") != "INTEGRATED":
            continue

        dependency_task = task_index.get(dependency_id, {"id": dependency_id})
        review_result = load_optional_json(run_dir / "review" / "review-result.json")
        run_result = load_optional_json(run_dir / "result.json")
        shared_requirements = sorted(
            set(task.get("requirement_ids", [])) & set(dependency_task.get("requirement_ids", []))
        )

        context.append(
            {
                "task_id": dependency_id,
                "integration_status": integration_result.get("status"),
                "integration_commit": integration_result.get("integration_commit"),
                "produced_commit": run_result.get("produced_commit"),
                "review_verdict": review_result.get("verdict"),
                "modified_paths": run_result.get("modified_paths", []),
                "shared_requirements_with_current_task": shared_requirements,
                "dependency_requirements": [
                    requirement_index[requirement_id]
                    for requirement_id in dependency_task.get("requirement_ids", [])
                    if requirement_id in requirement_index
                ],
                "requirement_checks": review_result.get("requirement_checks", []),
                "acceptance_checks": review_result.get("acceptance_checks", []),
                "summary": review_result.get("summary", ""),
            }
        )
    return context


def run_codex_review(
    cwd: Path,
    prompt: str,
    schema_path: Path,
    output_path: Path,
) -> dict[str, Any]:
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
    ]
    result = run_process_capturing_timeout(
        command=command,
        cwd=cwd,
        input_text=prompt,
        timeout_seconds=TIMEOUTS_SECONDS["codex_review"],
    )
    return result.to_dict()


def validate_review_result(review_result: dict[str, Any], expected_task_id: str) -> None:
    required_keys = {
        "task_id",
        "verdict",
        "summary",
        "requirement_checks",
        "acceptance_checks",
        "issues",
        "tests",
        "scope",
    }
    if set(review_result.keys()) != required_keys:
        raise ReviewTaskError("Résultat Codex invalide : structure JSON inattendue.")
    if review_result["task_id"] != expected_task_id:
        raise ReviewTaskError(
            "Résultat Codex invalide : "
            f"task_id incohérent (attendu: {expected_task_id}, reçu: {review_result['task_id']})."
        )
    if review_result["verdict"] not in REVIEW_VERDICTS:
        raise ReviewTaskError("Résultat Codex invalide : verdict inconnu.")
    if not isinstance(review_result["summary"], str):
        raise ReviewTaskError("Résultat Codex invalide : summary doit être une chaîne.")

    validate_checks(review_result["requirement_checks"], "requirement_id")
    validate_checks(review_result["acceptance_checks"], "criterion")
    validate_issues(review_result["issues"])
    validate_tests(review_result["tests"])
    validate_scope(review_result["scope"])


def validate_checks(items: Any, label_key: str) -> None:
    if not isinstance(items, list):
        raise ReviewTaskError("Résultat Codex invalide : liste de contrôles attendue.")
    for item in items:
        if not isinstance(item, dict):
            raise ReviewTaskError("Résultat Codex invalide : entrée de contrôle invalide.")
        if set(item.keys()) != {label_key, "status", "evidence"}:
            raise ReviewTaskError("Résultat Codex invalide : clés de contrôle inattendues.")
        if not isinstance(item[label_key], str):
            raise ReviewTaskError("Résultat Codex invalide : identifiant de contrôle invalide.")
        if item["status"] not in CHECK_STATUSES:
            raise ReviewTaskError("Résultat Codex invalide : statut de contrôle inconnu.")
        if not isinstance(item["evidence"], list) or not all(
            isinstance(value, str) for value in item["evidence"]
        ):
            raise ReviewTaskError("Résultat Codex invalide : evidence doit être une liste de chaînes.")


def validate_issues(items: Any) -> None:
    if not isinstance(items, list):
        raise ReviewTaskError("Résultat Codex invalide : issues doit être une liste.")
    for item in items:
        if not isinstance(item, dict):
            raise ReviewTaskError("Résultat Codex invalide : issue invalide.")
        if set(item.keys()) != {"severity", "description", "file", "suggested_fix"}:
            raise ReviewTaskError("Résultat Codex invalide : clés d'issue inattendues.")
        if item["severity"] not in ISSUE_SEVERITIES:
            raise ReviewTaskError("Résultat Codex invalide : sévérité inconnue.")
        if not all(isinstance(item[key], str) for key in ("description", "file", "suggested_fix")):
            raise ReviewTaskError("Résultat Codex invalide : champs d'issue invalides.")


def validate_tests(payload: Any) -> None:
    if not isinstance(payload, dict) or set(payload.keys()) != {"status", "details"}:
        raise ReviewTaskError("Résultat Codex invalide : bloc tests invalide.")
    if payload["status"] not in TEST_STATUSES:
        raise ReviewTaskError("Résultat Codex invalide : statut de tests inconnu.")
    if not isinstance(payload["details"], list) or not all(
        isinstance(value, str) for value in payload["details"]
    ):
        raise ReviewTaskError("Résultat Codex invalide : détails de tests invalides.")


def validate_scope(payload: Any) -> None:
    if not isinstance(payload, dict) or set(payload.keys()) != {"status", "unexpected_paths"}:
        raise ReviewTaskError("Résultat Codex invalide : bloc scope invalide.")
    if payload["status"] not in SCOPE_STATUSES:
        raise ReviewTaskError("Résultat Codex invalide : statut de scope inconnu.")
    if not isinstance(payload["unexpected_paths"], list) or not all(
        isinstance(value, str) for value in payload["unexpected_paths"]
    ):
        raise ReviewTaskError("Résultat Codex invalide : unexpected_paths invalide.")


def enforce_review_constraints(
    review_result: dict[str, Any],
    task_id: str,
    unexpected_paths: list[str],
    validation_results: list[dict[str, Any]],
) -> dict[str, Any]:
    result = json.loads(json.dumps(review_result))
    result["task_id"] = task_id
    result["scope"] = {
        "status": "FAIL" if unexpected_paths else "PASS",
        "unexpected_paths": unexpected_paths,
    }
    result["tests"] = {
        "status": "PASS" if all(item.get("returncode") == 0 for item in validation_results) else "FAIL",
        "details": summarize_validation_details(validation_results),
    }

    requirement_failed = any(item["status"] != "PASS" for item in result["requirement_checks"])
    acceptance_failed = any(item["status"] != "PASS" for item in result["acceptance_checks"])
    has_blocking_issue = any(item["severity"] in {"blocking", "major"} for item in result["issues"])
    has_uncertain = any(
        item["status"] == "UNCERTAIN"
        for item in [*result["requirement_checks"], *result["acceptance_checks"]]
    )

    if requirement_failed or acceptance_failed or result["tests"]["status"] == "FAIL" or result["scope"]["status"] == "FAIL" or has_blocking_issue:
        result["verdict"] = "CORRECTION_REQUIRED"
    elif has_uncertain:
        result["verdict"] = "HUMAN_REVIEW_REQUIRED"
    else:
        result["verdict"] = "APPROVED"

    return result


def summarize_validation_details(validation_results: list[dict[str, Any]]) -> list[str]:
    details: list[str] = []
    for item in validation_results:
        status = "OK" if item.get("returncode") == 0 else "ECHEC"
        excerpt = str(item.get("stderr") or item.get("stdout") or "").strip()
        summary = f"{item.get('command', '')}={status}"
        if excerpt:
            summary = f"{summary} :: {excerpt.splitlines()[0]}"
        details.append(summary)
    return details
