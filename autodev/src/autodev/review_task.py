from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from autodev.git_tools import (
    GitError,
    branch_exists,
    changed_paths_between,
    diff_patch_between,
    git_status_porcelain,
    head_commit,
)
from autodev.path_rules import normalize_repo_relative_path
from autodev.planner import PlanningError, find_repo_root, load_json, validate_backlog_consistency
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
    base_commit = resolve_base_commit(run_result, task_record)
    worktree = resolve_worktree(repo_root, task_id, run_result, task_record)
    produced_commit = resolve_produced_commit(repo_root, worktree, run_result)

    modified_paths = changed_paths_between(repo_root, base_commit, produced_commit)
    unexpected_paths = find_unexpected_paths(task["allowed_paths"], modified_paths)

    validation_results, validation_source = load_or_rerun_validations(
        repo_root=repo_root,
        worktree=worktree,
        task=task,
        run_result=run_result,
    )
    validation_payload = {
        "task_id": task_id,
        "source": validation_source,
        "results": validation_results,
    }
    write_json(review_dir / "validation-results.json", validation_payload)

    spec_path = resolve_specification_path(repo_root, backlog)
    prompt = build_review_prompt(
        repo_root=repo_root,
        backlog_json=backlog_json,
        backlog=backlog,
        task=task,
        spec_path=spec_path,
        base_commit=base_commit,
        produced_commit=produced_commit,
        modified_paths=modified_paths,
        unexpected_paths=unexpected_paths,
        validation_payload=validation_payload,
        diff_text=diff_patch_between(repo_root, base_commit, produced_commit),
    )
    (review_dir / "review-prompt.md").write_text(prompt, encoding="utf-8")

    schema_path = repo_root / "autodev" / "schemas" / "review-result.schema.json"
    output_path = review_dir / "review-result.json"
    codex_runner = codex_runner or run_codex_review
    codex_result = codex_runner(
        cwd=worktree if worktree.exists() else repo_root,
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


def resolve_base_commit(run_result: dict[str, Any], task_record: dict[str, Any]) -> str:
    base_commit = run_result.get("base_commit") or task_record.get("base_commit")
    if not isinstance(base_commit, str) or not base_commit.strip():
        raise ReviewTaskError("Commit de départ introuvable dans les artefacts run-task.")
    return base_commit


def resolve_worktree(
    repo_root: Path,
    task_id: str,
    run_result: dict[str, Any],
    task_record: dict[str, Any],
) -> Path:
    worktree_value = (
        run_result.get("worktree")
        or task_record.get("worktree")
        or str(repo_root / ".autodev" / "worktrees" / task_id)
    )
    return Path(str(worktree_value))


def resolve_produced_commit(
    repo_root: Path,
    worktree: Path,
    run_result: dict[str, Any],
) -> str:
    produced_commit = run_result.get("produced_commit")
    if isinstance(produced_commit, str) and produced_commit.strip():
        return produced_commit
    if worktree.exists():
        try:
            return head_commit(repo_root, worktree)
        except GitError as exc:
            raise ReviewTaskError(str(exc)) from exc
    raise ReviewTaskError("Commit produit introuvable pour la revue.")


def find_unexpected_paths(allowed_paths: list[str], modified_paths: list[str]) -> list[str]:
    allowed = [normalize_allowed_path(item) for item in allowed_paths]
    unexpected: list[str] = []
    for modified_path in modified_paths:
        candidate = Path(modified_path)
        if not any(is_relative_to(candidate, allowed_path) for allowed_path in allowed):
            unexpected.append(modified_path)
    return unexpected


def normalize_allowed_path(allowed_path: str) -> Path:
    try:
        return normalize_repo_relative_path(allowed_path)
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
    unexpected_paths: list[str],
    validation_payload: dict[str, Any],
    diff_text: str,
) -> str:
    specification = spec_path.read_text(encoding="utf-8")
    requirements = [
        requirement
        for requirement in backlog["requirements"]
        if requirement["id"] in set(task["requirement_ids"])
    ]
    requirement_blob = json.dumps(requirements, ensure_ascii=False, indent=2)
    task_blob = json.dumps(task, ensure_ascii=False, indent=2)
    validation_blob = json.dumps(validation_payload, ensure_ascii=False, indent=2)
    modified_blob = "\n".join(f"- {path}" for path in modified_paths) or "- Aucun"
    unexpected_blob = "\n".join(f"- {path}" for path in unexpected_paths) or "- Aucun"

    return f"""# Revue automatique de tâche autodev

Tu agis comme reviewer strict en lecture seule.

Contraintes impératives :

- ne modifier aucun fichier ;
- ne proposer aucun merge ;
- t'appuyer uniquement sur les informations fournies ;
- appliquer strictement les règles de verdict ci-dessous.

Backlog : `{backlog_json}`
Feature : `{backlog["feature_id"]}` — {backlog["feature_title"]}
Tâche revue : `{task["id"]}`
Commit de départ : `{base_commit}`
Commit produit : `{produced_commit}`

# Règles de verdict

- `APPROVED` uniquement si toutes les exigences liées sont `PASS`, tous les critères d'acceptation sont `PASS`, les tests requis réussissent, aucun fichier hors périmètre n'est modifié et aucun problème `blocking` ou `major` n'est présent.
- `CORRECTION_REQUIRED` si un critère ou une exigence est `FAIL`, si un test échoue, si un fichier hors périmètre est modifié ou si un problème `blocking` ou `major` est trouvé.
- `HUMAN_REVIEW_REQUIRED` uniquement si une ambiguïté métier, une information manquante ou une impossibilité d'évaluer automatiquement empêche la décision.

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

# Fichiers hors périmètre détectés

{unexpected_blob}

# Résultats des validations

```json
{validation_blob}
```

# Diff Git complet

```diff
{diff_text}
```

# Attendu pour la réponse

La réponse doit respecter exactement le schéma JSON fourni par `--output-schema`.
"""


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
    result = subprocess.run(
        command,
        cwd=cwd,
        input=prompt,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


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
        raise ReviewTaskError("Résultat Codex invalide : task_id incohérent.")
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
