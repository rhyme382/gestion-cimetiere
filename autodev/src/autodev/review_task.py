from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autodev.acceptance_criteria import owned_criteria_by_task
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
    summarize_validations,
    validate_command_safe,
    write_json,
)

REVIEW_VERDICTS = {"APPROVED", "CORRECTION_REQUIRED", "HUMAN_REVIEW_REQUIRED"}
CHECK_STATUSES = {"PASS", "FAIL", "UNCERTAIN"}
ISSUE_SEVERITIES = {"blocking", "major", "minor"}
TEST_STATUSES = {"PASS", "FAIL"}
SCOPE_STATUSES = {"PASS", "FAIL"}

NON_AUTHORITATIVE_REPORT_MARKER = (
    "Contenu narratif historique omis du prompt de preuve ; "
    "le chemin reste contrôlé par Git name-status."
)


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

    try:
        git_state = build_current_task_git_state(repo_root, task_id)
    except GitContextError as exc:
        raise ReviewTaskError(str(exc)) from exc
    review_delivery = collect_review_delivery(repo_root, review_dir, git_state)
    modified_paths = review_delivery["modified_paths"]
    unexpected_paths = find_unexpected_paths(task["allowed_paths"], modified_paths)

    validation_results, validation_summary = rerun_current_validations(
        repo_root=repo_root,
        worktree=git_state.worktree,
        task=task,
    )
    validation_payload = {
        "task_id": task_id,
        "source": "review-task",
        "results": validation_results,
        "summary": validation_summary,
    }
    write_json(review_dir / "validation-results.json", validation_payload)
    write_current_task_state(
        review_dir=review_dir,
        task_id=task_id,
        git_state=git_state,
        validation_commands=task["validation_commands"],
        validation_results=validation_results,
        validation_summary=validation_summary,
    )

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
    if codex_runner is None:
        codex_runner = lambda **kwargs: run_codex_review(
            **kwargs, heartbeat_path=run_dir / "heartbeat.json"
        )
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
    expected_owned_criteria = owned_criteria_by_task(backlog).get(task_id, [])
    validate_review_result(review_result, task_id, expected_owned_criteria)
    review_result = enforce_review_constraints(
        review_result=review_result,
        task_id=task_id,
        unexpected_paths=unexpected_paths,
        validation_results=validation_results,
        expected_owned_criteria=expected_owned_criteria,
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


def rerun_current_validations(
    repo_root: Path,
    worktree: Path,
    task: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    if not worktree.exists():
        raise ReviewTaskError("Worktree introuvable pour relancer les validations de revue.")
    results = rerun_validations(repo_root, worktree, task["validation_commands"])
    return results, summarize_validations(results)


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


def write_current_task_state(
    *,
    review_dir: Path,
    task_id: str,
    git_state: Any,
    validation_commands: list[str],
    validation_results: list[dict[str, Any]],
    validation_summary: list[str],
) -> None:
    write_json(
        review_dir / "current-task-state.json",
        {
            "task_id": task_id,
            "base_commit": git_state.base_commit,
            "current_commit": git_state.produced_commit,
            "current_paths": git_state.modified_paths,
            "validation_commands": list(validation_commands),
            "validation_results": validation_results,
            "validation_summary": validation_summary,
        },
    )


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
    exact_task_id = task["id"]
    owned_criteria = owned_criteria_by_task(backlog).get(task["id"], [])
    requirement_context: dict[str, dict[str, Any]] = {}
    for criterion in owned_criteria:
        bucket = requirement_context.setdefault(
            criterion["requirement_id"],
            {
                "id": criterion["requirement_id"],
                "description": criterion["requirement_description"],
                "owned_acceptance_criteria": [],
            },
        )
        bucket["owned_acceptance_criteria"].append(
            {
                "id": criterion["acceptance_criterion_id"],
                "text": criterion["text"],
            }
        )
    requirements = [requirement_context[key] for key in sorted(requirement_context)]
    requirement_blob = json.dumps(requirements, ensure_ascii=False, indent=2)
    task_blob = json.dumps(task, ensure_ascii=False, indent=2)
    validation_blob = json.dumps(validation_payload, ensure_ascii=False, indent=2)
    dependency_blob = json.dumps(dependency_context, ensure_ascii=False, indent=2)
    modified_blob = "\n".join(f"- {path}" for path in modified_paths) or "- Aucun"
    name_status_blob = "\n".join(f"- {line}" for line in name_status_lines) or "- Aucun"
    unexpected_blob = "\n".join(f"- {path}" for path in unexpected_paths) or "- Aucun"
    owned_criteria_lines = "\n".join(
        f"- {criterion['acceptance_criterion_id']} ({criterion['requirement_id']}) : {criterion['text']}"
        for criterion in owned_criteria
    ) or "- Aucun"
    review_diff_text = filter_diff_for_review(diff_text)

    return f"""# Revue automatique de tâche autodev

Tu agis comme reviewer strict en lecture seule.

Contraintes impératives :

- ne modifier aucun fichier ;
- ne proposer aucun merge ;
- t'appuyer uniquement sur les informations fournies ;
- évaluer la tâche courante avec son propre périmètre de preuve ;
- considérer le contrat propriétaire ci-dessous comme exhaustif : toute exigence ou tout critère absent de ce contrat appartient hors du périmètre de cette revue ;
- ne créer aucune `issue` à partir d'une exigence absente du contrat propriétaire, même si le diff suggère qu'elle sera traitée par une autre tâche ;
- traiter le code et les tests du commit courant comme preuves techniques autoritatives ;
- ne jamais utiliser un rapport de correction, de vérification ou de validation narratif pour contredire le code ou les tests courants : ces rapports peuvent décrire une tentative antérieure ;
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

- `APPROVED` uniquement si tous les critères propriétaires de requirement_checks sont `PASS`, tous les critères d'acceptation de la tâche sont `PASS`, les tests requis réussissent, aucun fichier hors périmètre n'est modifié et aucun problème `blocking` ou `major` n'est présent.
- `CORRECTION_REQUIRED` si un critère propriétaire ou un critère d'acceptation de la tâche est `FAIL`, si un test échoue, si un fichier hors périmètre est modifié ou si un problème `blocking` ou `major` est trouvé.
- `HUMAN_REVIEW_REQUIRED` uniquement si une ambiguïté métier, une information manquante ou une impossibilité d'évaluer automatiquement empêche la décision.

# Règles spécifiques aux dépendances intégrées

- Les tâches dans `depends_on` déjà intégrées fournissent un contexte de preuve complémentaire.
- N'exige jamais que les fichiers d'une dépendance intégrée réapparaissent dans le diff Git courant.
- Si un livrable requis pour une exigence provient uniquement d'une dépendance déjà intégrée, utilise son artefact d'intégration et sa revue `APPROVED` comme preuve héritée.
- Une tâche dépendante ne doit pas être pénalisée pour ne pas réimplémenter ni reprouver les exigences déjà satisfaites par ses dépendances intégrées.
- Évalue les critères d'acceptation propres à la tâche courante avec le diff courant ; utilise les preuves héritées uniquement pour les livrables dépendants déjà intégrés.

# Source du contrat

Chemin : `{spec_path.relative_to(repo_root).as_posix()}`

La spécification complète n'est volontairement pas incluse : seuls les exigences et critères attribués à la tâche courante sont normatifs pour cette revue.

# Tâche complète

```json
{task_blob}
```

# Contexte des exigences parentes

```json
{requirement_blob}
```

# Critères propriétaires de la tâche au titre des exigences

{owned_criteria_lines}

# Critères d'acceptation propres à la tâche

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

Le contenu des rapports narratifs de correction ou de vérification est volontairement omis : leurs chemins restent visibles ci-dessus pour le contrôle de périmètre, mais leurs affirmations ne constituent pas une preuve technique.

```diff
{review_diff_text}
```

# Attendu pour la réponse

La réponse doit respecter exactement le schéma JSON fourni par `--output-schema`.
Le champ `task_id` doit reprendre exactement `{exact_task_id}`.
- `requirement_checks` doit contenir uniquement les critères propriétaires listés ci-dessus, jamais un critère appartenant à une autre tâche.
- Recopie exactement `requirement_id` et `acceptance_criterion_id` pour chaque entrée, sans les reformuler ni les permuter.
- Suis strictement l'ordre des critères propriétaires fourni ci-dessus.
- Ne génère jamais le texte du critère propriétaire et ne le reformule jamais.
- Chaque entrée de `requirement_checks` doit contenir `requirement_id`, `acceptance_criterion_id`, `status`, `evidence`. Le champ legacy `criterion` est toléré mais ignoré.
"""


def filter_diff_for_review(diff_text: str) -> str:
    """Retire du prompt les récits de correction historiques, sans masquer leurs chemins Git."""
    if not diff_text:
        return diff_text

    blocks: list[list[str]] = []
    current: list[str] = []
    for line in diff_text.splitlines(keepends=True):
        if line.startswith("diff --git ") and current:
            blocks.append(current)
            current = []
        current.append(line)
    if current:
        blocks.append(current)

    filtered: list[str] = []
    for block in blocks:
        path = _diff_block_path(block[0]) if block else None
        if path is not None and _is_historical_narrative_report(path):
            newline = "\n" if block[0].endswith("\n") else ""
            filtered.append(block[0])
            filtered.append(f"# {NON_AUTHORITATIVE_REPORT_MARKER}{newline}")
            continue
        filtered.extend(block)
    return "".join(filtered)


def _diff_block_path(header: str) -> str | None:
    prefix = "diff --git a/"
    if not header.startswith(prefix):
        return None
    remainder = header[len(prefix):].rstrip("\n")
    _, separator, destination = remainder.partition(" b/")
    return destination if separator else None


def _is_historical_narrative_report(path: str) -> bool:
    normalized = path.lower()
    if not normalized.startswith(("reports/dev/", "agents/reports/")):
        return False
    filename = Path(normalized).name
    return (
        "correction" in filename
        or "verification" in filename
        or filename in {"validation_evidence.md", "correction_summary.md"}
    )


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
    heartbeat_path: Path | None = None,
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
        heartbeat_path=heartbeat_path,
        heartbeat_phase="REVIEW",
    )
    return result.to_dict()


def validate_review_result(
    review_result: dict[str, Any],
    expected_task_id: str,
    expected_owned_criteria: list[dict[str, str]],
) -> None:
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

    validate_requirement_checks(review_result["requirement_checks"])
    validate_checks(review_result["acceptance_checks"], {"criterion", "status", "evidence"})
    validate_issues(review_result["issues"])
    validate_tests(review_result["tests"])
    validate_scope(review_result["scope"])
    _validate_owned_requirement_checks(
        review_result["requirement_checks"],
        expected_owned_criteria,
    )


def validate_checks(items: Any, required_keys: set[str]) -> None:
    if not isinstance(items, list):
        raise ReviewTaskError("Résultat Codex invalide : liste de contrôles attendue.")
    for item in items:
        if not isinstance(item, dict):
            raise ReviewTaskError("Résultat Codex invalide : entrée de contrôle invalide.")
        if set(item.keys()) != required_keys:
            raise ReviewTaskError("Résultat Codex invalide : clés de contrôle inattendues.")
        for key in required_keys - {"status", "evidence"}:
            if not isinstance(item[key], str):
                raise ReviewTaskError("Résultat Codex invalide : identifiant de contrôle invalide.")
        if item["status"] not in CHECK_STATUSES:
            raise ReviewTaskError("Résultat Codex invalide : statut de contrôle inconnu.")
        if not isinstance(item["evidence"], list) or not all(
            isinstance(value, str) for value in item["evidence"]
        ):
            raise ReviewTaskError("Résultat Codex invalide : evidence doit être une liste de chaînes.")


def validate_requirement_checks(items: Any) -> None:
    if not isinstance(items, list):
        raise ReviewTaskError("Résultat Codex invalide : liste de contrôles attendue.")
    allowed_keysets = (
        {"requirement_id", "acceptance_criterion_id", "status", "evidence"},
        {"requirement_id", "acceptance_criterion_id", "criterion", "status", "evidence"},
        {"requirement_id", "status", "evidence"},
    )
    for item in items:
        if not isinstance(item, dict):
            raise ReviewTaskError("Résultat Codex invalide : entrée de contrôle invalide.")
        if set(item.keys()) not in allowed_keysets:
            raise ReviewTaskError("Résultat Codex invalide : clés de contrôle inattendues.")
        if not isinstance(item["requirement_id"], str):
            raise ReviewTaskError("Résultat Codex invalide : identifiant de contrôle invalide.")
        for key in ("acceptance_criterion_id", "criterion"):
            if key in item and not isinstance(item[key], str):
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


def _validate_owned_requirement_checks(
    requirement_checks: list[dict[str, Any]],
    expected_owned_criteria: list[dict[str, str]],
) -> None:
    if all(
        "acceptance_criterion_id" not in item and "criterion" not in item
        for item in requirement_checks
    ):
        if len(expected_owned_criteria) != len(requirement_checks):
            raise ReviewTaskError(
                "Résultat Codex invalide : format legacy insuffisant pour mapper les critères propriétaires."
            )
        for item, expected_item in zip(requirement_checks, expected_owned_criteria, strict=True):
            if item["requirement_id"] != expected_item["requirement_id"]:
                raise ReviewTaskError(
                    "Résultat Codex invalide : contrôle d'exigence legacy incohérent."
                )
        return

    expected_by_id = {
        item["acceptance_criterion_id"]: item
        for item in expected_owned_criteria
    }
    expected_ids = [item["acceptance_criterion_id"] for item in expected_owned_criteria]
    seen_ids: set[str] = set()
    actual_ids: list[str] = []

    for item in requirement_checks:
        criterion_id = item.get("acceptance_criterion_id")
        if not isinstance(criterion_id, str):
            raise ReviewTaskError(
                "Résultat Codex invalide : acceptance_criterion_id manquant pour un critère propriétaire."
            )
        if criterion_id in seen_ids:
            raise ReviewTaskError(
                f"Résultat Codex invalide : critère propriétaire dupliqué pour {criterion_id}."
            )
        expected_item = expected_by_id.get(criterion_id)
        if expected_item is None:
            raise ReviewTaskError(
                f"Résultat Codex invalide : critère propriétaire inconnu ou hors tâche pour {criterion_id}."
            )
        if item["requirement_id"] != expected_item["requirement_id"]:
            raise ReviewTaskError(
                f"Résultat Codex invalide : exigence parente incohérente pour {criterion_id}."
            )
        seen_ids.add(criterion_id)
        actual_ids.append(criterion_id)

    if actual_ids != expected_ids:
        missing_ids = [criterion_id for criterion_id in expected_ids if criterion_id not in seen_ids]
        if missing_ids:
            raise ReviewTaskError(
                "Résultat Codex invalide : critères propriétaires manquants : "
                + ", ".join(missing_ids)
                + "."
            )
        raise ReviewTaskError(
            "Résultat Codex invalide : l'ordre des critères propriétaires ne correspond pas au backlog."
        )


def normalize_requirement_checks(
    requirement_checks: list[dict[str, Any]],
    expected_owned_criteria: list[dict[str, str]],
) -> list[dict[str, Any]]:
    if all(
        "acceptance_criterion_id" not in item and "criterion" not in item
        for item in requirement_checks
    ):
        normalized: list[dict[str, Any]] = []
        for item, expected_item in zip(requirement_checks, expected_owned_criteria, strict=True):
            normalized.append(
                {
                    "requirement_id": expected_item["requirement_id"],
                    "acceptance_criterion_id": expected_item["acceptance_criterion_id"],
                    "criterion": expected_item["text"],
                    "status": item["status"],
                    "evidence": list(item["evidence"]),
                }
            )
        return normalized

    expected_by_id = {
        item["acceptance_criterion_id"]: item
        for item in expected_owned_criteria
    }
    normalized = []
    for item in requirement_checks:
        expected_item = expected_by_id[item["acceptance_criterion_id"]]
        normalized.append(
            {
                "requirement_id": expected_item["requirement_id"],
                "acceptance_criterion_id": expected_item["acceptance_criterion_id"],
                "criterion": expected_item["text"],
                "status": item["status"],
                "evidence": list(item["evidence"]),
            }
        )
    return normalized


def enforce_review_constraints(
    review_result: dict[str, Any],
    task_id: str,
    unexpected_paths: list[str],
    validation_results: list[dict[str, Any]],
    expected_owned_criteria: list[dict[str, str]],
) -> dict[str, Any]:
    result = json.loads(json.dumps(review_result))
    result["task_id"] = task_id
    result["requirement_checks"] = normalize_requirement_checks(
        result["requirement_checks"],
        expected_owned_criteria,
    )
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
