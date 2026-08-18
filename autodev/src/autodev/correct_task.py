from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autodev.generated_artifacts import filter_generated_artifacts
from autodev.git_context import GitContextError, build_current_task_git_state
from autodev.git_tools import (
    GitError,
    amend_head_commit,
    branch_exists,
    changed_paths_since,
    commit_count_since,
    create_commit,
    dirty_paths,
    git_status_porcelain,
    git_status_with_branch,
    head_commit,
    is_path_tracked,
    restore_paths,
    stage_all,
)
from autodev.path_rules import normalize_repo_relative_path
from autodev.planner import PlanningError, find_repo_root, load_json, validate_backlog_consistency
from autodev.task_runner import (
    RunTaskError,
    build_prompt,
    ensure_dependency_changes_allowed,
    ensure_claude_completed_successfully,
    is_relative_to,
    find_task,
    run_claude_non_interactive,
    run_validation_commands,
    summarize_validations,
    write_json,
)
from autodev.task_report import build_task_report_payload, write_task_report


class CorrectTaskError(RuntimeError):
    """Erreur pendant la correction automatique d'une tâche."""


def correct_task(
    backlog_json: Path,
    task_id: str,
    *,
    guidance: str | None = None,
    claude_runner: Any | None = None,
) -> dict[str, Any]:
    repo_root = find_repo_root(backlog_json.parent)
    backlog = load_and_validate_backlog(backlog_json)
    task = resolve_task(backlog, task_id)
    branch = f"autodev/{task_id}"

    if not branch_exists(repo_root, branch):
        raise CorrectTaskError(f"Branche de tâche absente : {branch}")

    run_dir = repo_root / ".autodev" / "runs" / task_id
    review_result = load_required_json(run_dir / "review" / "review-result.json")
    run_result = load_required_json(run_dir / "result.json")
    task_record = load_required_json(run_dir / "task.json")
    worktree = resolve_worktree(repo_root, task_id, run_result, task_record)
    base_commit = resolve_base_commit(run_result, task_record)

    if not worktree.exists():
        raise CorrectTaskError(f"Worktree introuvable pour la correction : {worktree}")

    current_head = resolve_current_head(repo_root, worktree)
    before_status = git_status(repo_root, worktree)
    before_status_full = git_status_full(repo_root, worktree)
    before_dirty_paths = dirty_paths(repo_root, cwd=worktree)
    correction_index = next_correction_index(run_dir)
    correction_dir = run_dir / "corrections" / f"{correction_index:02d}"
    correction_dir.mkdir(parents=True, exist_ok=True)
    (correction_dir / "before-commit.txt").write_text(current_head + "\n", encoding="utf-8")
    (correction_dir / "before-status.txt").write_text(before_status_full, encoding="utf-8")

    result: dict[str, Any] = {
        "task_id": task_id,
        "status": "running",
        "branch": branch,
        "worktree": str(worktree),
        "base_commit": base_commit,
        "before_commit": current_head,
        "starting_commit": current_head,
        "produced_commit": None,
        "modified_paths": [],
        "restored_paths": [],
        "remaining_allowed_paths": [],
        "validations": [],
        "validation_summary": [],
        "error": None,
        "correction_number": correction_index,
    }

    if claude_runner is None:
        claude_runner = lambda *, worktree, prompt: run_claude_non_interactive(
            worktree, prompt, heartbeat_path=run_dir / "heartbeat.json"
        )

    try:
        attempt = run_correction_attempt(
            repo_root=repo_root,
            backlog_json=backlog_json,
            backlog=backlog,
            task=task,
            task_id=task_id,
            review_result=review_result,
            correction_dir=correction_dir,
            correction_index=correction_index,
            worktree=worktree,
            current_head=current_head,
            before_status=before_status,
            before_dirty_paths=before_dirty_paths,
            guidance=guidance,
            claude_runner=claude_runner,
        )

        result["modified_paths"] = attempt["modified_paths"]
        result["restored_paths"] = attempt["restored_paths"]
        result["remaining_allowed_paths"] = attempt["remaining_allowed_paths"]
        result["claude_exit_code"] = attempt["claude_exit_code"]

        if result["remaining_allowed_paths"]:
            validations = run_validation_commands(worktree, task["validation_commands"])
            result["validations"] = validations
            result["validation_summary"] = summarize_validations(validations)

            stage_all(repo_root, cwd=worktree)
            if commit_count_since(repo_root, worktree, base_commit) > 0:
                amend_head_commit(repo_root, cwd=worktree)
            else:
                create_commit(repo_root, f"autodev correct-task {task_id}", cwd=worktree)

            result["produced_commit"] = head_commit(repo_root, worktree)
            result["status"] = "success"
        else:
            result["produced_commit"] = run_result.get("produced_commit")
            result["status"] = "no_allowed_changes"
    except (CorrectTaskError, GitError, RunTaskError) as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        write_correction_result(correction_dir, result)
        raise CorrectTaskError(str(exc)) from exc

    if result["produced_commit"] is not None:
        run_result["produced_commit"] = result["produced_commit"]
    run_result["modified_paths"] = result["remaining_allowed_paths"]
    run_result["validations"] = result["validations"]
    run_result["validation_summary"] = result["validation_summary"]
    run_result["status"] = "success"
    write_json(run_dir / "result.json", run_result)

    if result["status"] == "success":
        try:
            current_git_state = build_current_task_git_state(repo_root, task_id)
        except GitContextError as exc:
            raise CorrectTaskError(str(exc)) from exc
        _, unexpected_paths = partition_paths(task["allowed_paths"], current_git_state.modified_paths)
        task_report = build_task_report_payload(
            backlog=backlog,
            task=task,
            git_state={"modified_paths": current_git_state.modified_paths},
            validations=result["validations"],
            problems=unexpected_paths,
        )
        write_task_report(report_dir=run_dir, payload=task_report)

    write_correction_result(correction_dir, result)
    return result


def load_and_validate_backlog(backlog_json: Path) -> dict[str, Any]:
    try:
        backlog = load_json(backlog_json)
        validate_backlog_consistency(backlog)
    except PlanningError as exc:
        raise CorrectTaskError(str(exc)) from exc
    return backlog


def resolve_task(backlog: dict[str, Any], task_id: str) -> dict[str, Any]:
    try:
        return find_task(backlog, task_id)
    except RunTaskError as exc:
        raise CorrectTaskError(str(exc)) from exc


def load_required_json(path: Path) -> dict[str, Any]:
    try:
        return load_json(path)
    except PlanningError as exc:
        raise CorrectTaskError(str(exc)) from exc


def resolve_worktree(
    repo_root: Path,
    task_id: str,
    run_result: dict[str, Any],
    task_record: dict[str, Any],
) -> Path:
    raw_value = (
        run_result.get("worktree")
        or task_record.get("worktree")
        or str(repo_root / ".autodev" / "worktrees" / task_id)
    )
    return Path(str(raw_value))


def resolve_base_commit(run_result: dict[str, Any], task_record: dict[str, Any]) -> str:
    base_commit = run_result.get("base_commit") or task_record.get("base_commit")
    if not isinstance(base_commit, str) or not base_commit.strip():
        raise CorrectTaskError("Commit de départ introuvable dans les artefacts run-task.")
    return base_commit


def resolve_current_head(repo_root: Path, worktree: Path) -> str:
    try:
        return head_commit(repo_root, worktree)
    except GitError as exc:
        raise CorrectTaskError(str(exc)) from exc


def git_status(repo_root: Path, worktree: Path) -> str:
    try:
        return git_status_porcelain(repo_root, cwd=worktree)
    except GitError as exc:
        raise CorrectTaskError(str(exc)) from exc


def git_status_full(repo_root: Path, worktree: Path) -> str:
    try:
        return git_status_with_branch(repo_root, cwd=worktree)
    except GitError as exc:
        raise CorrectTaskError(str(exc)) from exc


def next_correction_index(run_dir: Path) -> int:
    corrections_dir = run_dir / "corrections"
    if not corrections_dir.is_dir():
        return 1

    highest = 0
    for child in corrections_dir.iterdir():
        if not child.is_dir():
            continue
        try:
            highest = max(highest, int(child.name))
        except ValueError:
            continue
    return highest + 1


def build_correction_prompt(
    *,
    repo_root: Path,
    backlog_json: Path,
    backlog: dict[str, Any],
    task: dict[str, Any],
    review_result: dict[str, Any],
    guidance: str | None = None,
    restored_paths: list[str] | None = None,
    retry_after_restore: bool = False,
) -> str:
    spec_path = repo_root / backlog.get("specification_path", "SPEC.md")
    specification = spec_path.read_text(encoding="utf-8")
    original_prompt = build_prompt(repo_root, backlog_json, backlog, task)
    review_blob = json.dumps(review_result, ensure_ascii=False, indent=2)

    issues = review_result.get("issues", [])
    issue_lines = "\n".join(
        (
            f"- {issue.get('severity', 'unknown')} : "
            f"{issue.get('description') or issue.get('message', '')}"
        ).rstrip()
        for issue in issues
    ) or "- Aucun détail fourni."
    normalized_guidance = guidance.strip() if guidance else ""
    guidance_block = ""
    if normalized_guidance:
        guidance_block = f"""
# Consignes complémentaires du superviseur

Ces consignes précisent la manière de traiter la revue sans remplacer la spécification,
le backlog, les critères propriétaires ni les chemins autorisés. En cas de contradiction,
la spécification et le contrat de la tâche restent prioritaires.

{normalized_guidance}
"""

    suggestions = []
    for check in review_result.get("requirement_checks", []):
        if check.get("status") == "FAIL":
            suggestions.append(f"- Corriger l'exigence {check.get('requirement_id')}.")
    for check in review_result.get("acceptance_checks", []):
        if check.get("status") == "FAIL":
            suggestions.append(f"- Corriger le critère d'acceptation : {check.get('criterion')}.")
    if review_result.get("scope", {}).get("unexpected_paths"):
        suggestions.append("- Supprimer tout changement hors allowed_paths.")
    if review_result.get("tests", {}).get("status") == "FAIL":
        suggestions.append("- Faire passer toutes les validations configurées.")
    suggestion_lines = "\n".join(suggestions) or "- Répondre strictement aux problèmes listés par la revue."

    validation_lines = "\n".join(f"- {command}" for command in task["validation_commands"])
    allowed_paths = "\n".join(f"- {path}" for path in task["allowed_paths"])
    next_tasks = list_upcoming_tasks(backlog, task["id"])
    next_task_lines = "\n".join(f"- {item['id']} : {item['title']}" for item in next_tasks) or "- Aucune tâche suivante."
    restored_lines = "\n".join(f"- {path}" for path in restored_paths or []) or "- Aucun fichier restauré."
    retry_block = ""
    if retry_after_restore:
        retry_block = f"""
# Relance après restauration

Des fichiers hors périmètre ont été restaurés automatiquement :
{restored_lines}

La première tentative n'a laissé aucune modification autorisée exploitable.
Tu dois corriger uniquement la tâche courante en respectant strictement le périmètre ci-dessous.
"""

    return f"""# Correction automatique d'une tâche autodev

Tu interviens uniquement pour corriger la tâche `{task["id"]}` dans le worktree existant.

{retry_block}

# PÉRIMÈTRE STRICT

Tu travailles uniquement sur la tâche courante.
Tu ne dois pas implémenter les tâches suivantes.
Tu ne dois modifier que les chemins listés dans allowed_paths.
Toute autre modification sera automatiquement annulée.
Ne modifie pas les dépendances du projet, les fichiers package.json/package-lock.json,
le backend, les tests E2E ou les specs, sauf s’ils figurent explicitement dans allowed_paths.

Interdictions absolues :
- ne pas faire de merge ;
- ne pas modifier la spécification ;
- ne pas traiter les tâches suivantes ;
- ne pas modifier `autodev` sauf si cette tâche l'autorise explicitement ;
- ne pas créer de commit ; laisse les modifications non commitées pour l'outil de correction ;
- ne pas modifier de chemin hors périmètre autorisé.

# Tâches suivantes du backlog

{next_task_lines}

Ces tâches seront exécutées séparément. Ne les implémente pas maintenant.

# Tâche initiale

{original_prompt}

# Spécification source

Chemin : `{spec_path}`

```md
{specification}
```

# Verdict complet Codex

```json
{review_blob}
```

{guidance_block}

# Problèmes détectés

{issue_lines}

# Corrections suggérées

{suggestion_lines}

# Chemins autorisés

{allowed_paths}

# Commandes de validation à faire passer

{validation_lines}

# Résultat attendu

Corrige uniquement les écarts relevés par la revue, mets à jour les tests nécessaires, puis arrête-toi sans créer de commit.
"""


def run_correction_attempt(
    *,
    repo_root: Path,
    backlog_json: Path,
    backlog: dict[str, Any],
    task: dict[str, Any],
    task_id: str,
    review_result: dict[str, Any],
    correction_dir: Path,
    correction_index: int,
    worktree: Path,
    current_head: str,
    before_status: str,
    before_dirty_paths: list[str],
    guidance: str | None,
    claude_runner: Any,
) -> dict[str, Any]:
    restored_union: set[str] = set()
    out_of_scope_union: set[str] = set()
    modified_union: set[str] = set()
    latest_exit_code: int | None = None
    restored_from_previous_attempt: list[str] = []

    for attempt_number in (1, 2):
        prompt = build_correction_prompt(
            repo_root=repo_root,
            backlog_json=backlog_json,
            backlog=backlog,
            task=task,
            review_result=review_result,
            guidance=guidance,
            restored_paths=restored_from_previous_attempt,
            retry_after_restore=attempt_number == 2,
        )
        prompt_name = "prompt.md" if attempt_number == 1 else "prompt-retry.md"
        (correction_dir / prompt_name).write_text(prompt, encoding="utf-8")

        claude_result = claude_runner(worktree=worktree, prompt=prompt)
        latest_exit_code = claude_result["returncode"]
        suffix = "" if attempt_number == 1 else ".retry"
        (correction_dir / f"claude{suffix}.stdout.log").write_text(claude_result["stdout"], encoding="utf-8")
        (correction_dir / f"claude{suffix}.stderr.log").write_text(claude_result["stderr"], encoding="utf-8")
        ensure_claude_completed_successfully(claude_result)

        current_head_after_claude = resolve_current_head(repo_root, worktree)
        if current_head_after_claude != current_head:
            raise CorrectTaskError(
                "Claude a créé ou modifié l'historique Git pendant la correction ; opération refusée."
            )

        after_paths = filter_generated_artifacts(
            changed_paths_since(repo_root, worktree, current_head),
            is_tracked=lambda path: is_path_tracked(repo_root, path, cwd=worktree),
        )
        correction_paths = sorted(set(after_paths) - set(before_dirty_paths))
        modified_union.update(correction_paths)

        allowed_paths, out_of_scope_paths = partition_paths(task["allowed_paths"], correction_paths)
        out_of_scope_union.update(out_of_scope_paths)
        if out_of_scope_paths:
            restore_paths(repo_root, worktree, current_head, out_of_scope_paths)
            restored_union.update(out_of_scope_paths)

        remaining_paths = sorted(
            set(
                filter_generated_artifacts(
                    changed_paths_since(repo_root, worktree, current_head),
                    is_tracked=lambda path: is_path_tracked(repo_root, path, cwd=worktree),
                )
            )
            - set(before_dirty_paths)
        )
        remaining_allowed_paths, remaining_out_of_scope_paths = partition_paths(task["allowed_paths"], remaining_paths)

        write_json(correction_dir / "modified-paths.json", sorted(modified_union))
        write_json(correction_dir / "out-of-scope-paths.json", sorted(out_of_scope_union))
        write_json(correction_dir / "restored-paths.json", sorted(restored_union))

        if remaining_out_of_scope_paths:
            joined = ", ".join(remaining_out_of_scope_paths)
            raise CorrectTaskError(f"Des chemins hors périmètre subsistent après restauration : {joined}")

        if remaining_allowed_paths:
            ensure_dependency_changes_allowed(task, remaining_allowed_paths)
            return {
                "claude_exit_code": latest_exit_code,
                "modified_paths": sorted(modified_union),
                "restored_paths": sorted(restored_union),
                "remaining_allowed_paths": remaining_allowed_paths,
            }

        if attempt_number == 2:
            return {
                "claude_exit_code": latest_exit_code,
                "modified_paths": sorted(modified_union),
                "restored_paths": sorted(restored_union),
                "remaining_allowed_paths": [],
            }

        restored_from_previous_attempt = sorted(restored_union)

    raise CorrectTaskError(f"Échec inattendu de la correction {task_id} #{correction_index}.")


def partition_paths(allowed_paths: list[str], modified_paths: list[str]) -> tuple[list[str], list[str]]:
    normalized_allowed = [normalize_allowed_path(item) for item in allowed_paths]
    allowed: list[str] = []
    unauthorized: list[str] = []

    for modified_path in modified_paths:
        candidate = normalize_modified_path(modified_path)
        if any(is_relative_to(candidate, allowed_path) for allowed_path in normalized_allowed):
            allowed.append(candidate.as_posix())
        else:
            unauthorized.append(candidate.as_posix())

    return sorted(allowed), sorted(unauthorized)


def normalize_allowed_path(raw_path: str) -> Path:
    try:
        return normalize_repo_relative_path(raw_path)
    except ValueError as exc:
        raise CorrectTaskError(str(exc)) from exc


def normalize_modified_path(raw_path: str) -> Path:
    try:
        return normalize_repo_relative_path(raw_path)
    except ValueError as exc:
        raise CorrectTaskError(str(exc)) from exc


def list_upcoming_tasks(backlog: dict[str, Any], task_id: str) -> list[dict[str, str]]:
    tasks = backlog.get("tasks", [])
    found_current = False
    upcoming: list[dict[str, str]] = []
    for task in tasks:
        if found_current:
            upcoming.append(
                {
                    "id": str(task.get("id", "")),
                    "title": str(task.get("title", "")),
                }
            )
        elif task.get("id") == task_id:
            found_current = True
    return upcoming


def write_correction_result(correction_dir: Path, payload: dict[str, Any]) -> None:
    write_json(correction_dir / "correction-result.json", payload)
    write_json(correction_dir / "result.json", payload)
