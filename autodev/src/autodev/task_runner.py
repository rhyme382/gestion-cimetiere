from __future__ import annotations

import json
import os
import re
import shlex
from pathlib import Path
from typing import Any

from autodev.acceptance_criteria import owned_criteria_by_task
from autodev.generated_artifacts import (
    filter_generated_artifacts,
    is_dependency_manifest,
)
from autodev.git_tools import (
    GitError,
    add_worktree,
    branch_exists,
    changed_paths_since,
    commit_count_since,
    create_branch,
    current_head,
    diff_patch,
    ensure_clean_worktree,
    head_commit,
    is_path_tracked,
    worktree_registered,
)
from autodev.path_rules import normalize_repo_relative_path
from autodev.task_dependencies import get_unfinished_dependencies
from autodev.planner import PlanningError, find_repo_root, load_json, validate_backlog_consistency
from autodev.process_runner import TIMEOUTS_SECONDS, run_process_capturing_timeout, timeout_for_command

FORBIDDEN_COMMAND_TOKENS = (";", "&&", "||", ">", ">>", "<", "|", "`", "$(")
CLAUDE_ALLOWED_TOOLS = "Bash,Edit,Write,Read,Glob,Grep"
CLAUDE_PERMISSION_WARNING_PATTERNS = (
    re.compile(r"\b(?:missing|need|request(?:ing)?|requires?)\b.{0,80}\bpermission", re.IGNORECASE | re.DOTALL),
    re.compile(r"\b(?:do(?:es)? not|don't|doesn't)\b.{0,40}\b(?:have|possess)\b.{0,40}\bpermissions?\b", re.IGNORECASE | re.DOTALL),
)


class RunTaskError(RuntimeError):
    """Erreur pendant la préparation ou l'exécution d'une tâche."""


def run_task(
    backlog_json: Path,
    task_id: str,
    dry_run: bool = False,
    claude_runner: Any | None = None,
) -> dict[str, Any]:
    repo_root = find_repo_root(backlog_json.parent)
    backlog = load_and_validate_backlog(backlog_json)
    task = find_task(backlog, task_id)
    ensure_dependencies_completed(repo_root, task)

    branch = f"autodev/{task_id}"
    worktree = repo_root / ".autodev" / "worktrees" / task_id
    run_dir = repo_root / ".autodev" / "runs" / task_id
    prompt = build_prompt(repo_root, backlog_json, backlog, task)

    if dry_run:
        return {
            "task_id": task_id,
            "branch": branch,
            "worktree": str(worktree),
            "run_dir": str(run_dir),
            "prompt_preview": prompt,
            "modified_paths": [],
            "validation_summary": [],
            "produced_commit": None,
        }

    try:
        ensure_clean_worktree(repo_root)
    except GitError as exc:
        raise RunTaskError(str(exc)) from exc
    base_commit = current_head(repo_root)
    prepare_isolated_workspace(repo_root, branch, worktree, base_commit)
    run_dir.mkdir(parents=True, exist_ok=True)

    task_record = {
        "backlog": str(backlog_json),
        "task": task,
        "branch": branch,
        "worktree": str(worktree),
        "base_commit": base_commit,
    }
    write_json(run_dir / "task.json", task_record)
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")

    result: dict[str, Any] = {
        "task_id": task_id,
        "status": "running",
        "claude_exit_code": None,
        "error": None,
        "branch": branch,
        "worktree": str(worktree),
        "run_dir": str(run_dir),
        "base_commit": base_commit,
        "produced_commit": None,
        "modified_paths": [],
        "validations": [],
        "validation_summary": [],
    }
    if claude_runner is None:
        claude_runner = lambda *, worktree, prompt: run_claude_non_interactive(
            worktree, prompt, heartbeat_path=run_dir / "heartbeat.json"
        )
    try:
        claude_result = claude_runner(worktree=worktree, prompt=prompt)
        result["claude"] = claude_result
        result["claude_exit_code"] = claude_result["returncode"]
        result["claude_timeout"] = claude_result.get("timed_out", False)
        (run_dir / "claude.stdout.log").write_text(claude_result["stdout"], encoding="utf-8")
        (run_dir / "claude.stderr.log").write_text(claude_result["stderr"], encoding="utf-8")

        ensure_claude_completed_successfully(claude_result)

        modified_paths = filter_generated_artifacts(
            changed_paths_since(repo_root, worktree, base_commit),
            is_tracked=lambda path: is_path_tracked(repo_root, path, cwd=worktree),
        )
        result["modified_paths"] = modified_paths
        ensure_changes_present(repo_root, worktree, base_commit, modified_paths)
        ensure_dependency_changes_allowed(task, modified_paths)
        ensure_paths_allowed(repo_root, task["allowed_paths"], modified_paths)

        if commit_count_since(repo_root, worktree, base_commit) <= 0:
            raise RunTaskError("Aucun commit final n'existe au-dessus du commit de départ.")
        result["produced_commit"] = head_commit(repo_root, worktree)

        validations = run_validation_commands(worktree, task["validation_commands"])
        result["validations"] = validations
        result["validation_summary"] = summarize_validations(validations)
        (run_dir / "diff.patch").write_text(diff_patch(repo_root, worktree, base_commit), encoding="utf-8")
    except RunTaskError as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        write_json(run_dir / "result.json", result)
        raise

    result["status"] = "success"
    write_json(run_dir / "result.json", result)
    return result


def load_and_validate_backlog(backlog_json: Path) -> dict[str, Any]:
    try:
        backlog = load_json(backlog_json)
        validate_backlog_consistency(backlog)
    except PlanningError as exc:
        raise RunTaskError(str(exc)) from exc
    return backlog


def find_task(backlog: dict[str, Any], task_id: str) -> dict[str, Any]:
    for task in backlog.get("tasks", []):
        if task.get("id") == task_id:
            return task
    raise RunTaskError(f"Tâche inconnue : {task_id}")


def ensure_dependencies_completed(repo_root: Path, task: dict[str, Any]) -> None:
    incomplete = get_unfinished_dependencies(repo_root, task)
    if incomplete:
        dependencies = ", ".join(incomplete)
        raise RunTaskError(
            f"Dépendances non terminées pour {task['id']} : {dependencies}."
        )


def build_prompt(
    repo_root: Path,
    backlog_json: Path,
    backlog: dict[str, Any],
    task: dict[str, Any],
) -> str:
    spec_path = repo_root / "SPEC.md"
    owned_criteria = owned_criteria_by_task(backlog).get(task["id"], [])
    requirement_context: dict[str, list[dict[str, str]]] = {}
    requirement_descriptions: dict[str, str] = {}
    for criterion in owned_criteria:
        requirement_context.setdefault(criterion["requirement_id"], []).append(criterion)
        requirement_descriptions[criterion["requirement_id"]] = criterion["requirement_description"]

    requirement_lines = "\n".join(
        f"- {requirement_id} : {requirement_descriptions[requirement_id]}\n"
        + "\n".join(
            f"  - {criterion['acceptance_criterion_id']} : {criterion['text']}"
            for criterion in requirement_context[requirement_id]
        )
        for requirement_id in sorted(requirement_context)
    )
    task_acceptance = "\n".join(f"- {criterion}" for criterion in task["acceptance_criteria"])
    validation_commands = "\n".join(f"- {command}" for command in task["validation_commands"])
    allowed_paths = "\n".join(f"- {path}" for path in task["allowed_paths"])
    specification = spec_path.read_text(encoding="utf-8")

    return f"""# Contexte

Tu travailles dans un worktree Git isolé créé pour la tâche `{task["id"]}`.

Backlog source : `{backlog_json}`
Feature : `{backlog["feature_id"]}` — {backlog["feature_title"]}
Résumé feature : {backlog["summary"]}

# Spécification source

Chemin : `{spec_path}`

```md
{specification}
```

# Tâche complète

ID : `{task["id"]}`
Titre : {task["title"]}
Agent cible : {task["agent"]}
Description : {task["description"]}

# Exigences liées

{requirement_lines}

# Critères d'acceptation de la tâche

{task_acceptance}

# Chemins autorisés

Tu peux modifier uniquement les chemins suivants :
{allowed_paths}

Interdiction absolue de modifier des chemins hors de cette liste.

# Validation

Commandes à exécuter et faire passer :
{validation_commands}

# Contraintes obligatoires

- Ajouter ou adapter les tests nécessaires.
- Ne pas modifier les spécifications.
- Ne pas faire de merge.
- Produire un commit final au-dessus du commit de départ.
- Ne pas écrire dans le dépôt principal hors du worktree.
- Respecter strictement les chemins autorisés.
"""


def prepare_isolated_workspace(repo_root: Path, branch: str, worktree: Path, base_commit: str) -> None:
    if branch_exists(repo_root, branch):
        raise RunTaskError(f"La branche existe déjà : {branch}")
    if worktree.exists() or worktree_registered(repo_root, worktree):
        raise RunTaskError(f"Le worktree existe déjà : {worktree}")

    try:
        create_branch(repo_root, branch, base_commit)
        add_worktree(repo_root, worktree, branch)
    except GitError as exc:
        raise RunTaskError(str(exc)) from exc


def run_claude_non_interactive(worktree: Path, prompt: str, *, heartbeat_path: Path | None = None) -> dict[str, Any]:
    command = [
        "claude",
        "-p",
        "--permission-mode",
        "bypassPermissions",
        "--tools",
        CLAUDE_ALLOWED_TOOLS,
        "--output-format",
        "text",
    ]
    result = run_process_capturing_timeout(
        command=command,
        cwd=worktree,
        input_text=prompt,
        timeout_seconds=TIMEOUTS_SECONDS["claude_task"],
        heartbeat_path=heartbeat_path,
        heartbeat_phase="IMPLEMENT",
    )
    return result.to_dict()


def ensure_claude_completed_successfully(claude_result: dict[str, Any]) -> None:
    if claude_result.get("timed_out"):
        raise RunTaskError("Claude a expiré : statut TIMEOUT.")
    if claude_result["returncode"] != 0:
        raise RunTaskError(format_claude_failure(claude_result))
    if claude_requested_permissions(claude_result):
        raise RunTaskError(
            "Claude a signalé un faux succès : code 0 retourné mais demande de permissions détectée dans la sortie."
        )


def format_claude_failure(claude_result: dict[str, Any]) -> str:
    if claude_result.get("timed_out"):
        return "Claude a expiré : statut TIMEOUT."
    stderr = str(claude_result.get("stderr", "")).strip()
    stdout = str(claude_result.get("stdout", "")).strip()
    detail = stderr or stdout or "erreur Claude inconnue"
    return f"Claude a échoué (code {claude_result['returncode']}) : {detail}"


def claude_requested_permissions(claude_result: dict[str, Any]) -> bool:
    combined_output = "\n".join(
        part.strip()
        for part in (
            str(claude_result.get("stdout", "")),
            str(claude_result.get("stderr", "")),
        )
        if part.strip()
    )
    if not combined_output:
        return False
    if not any(pattern.search(combined_output) for pattern in CLAUDE_PERMISSION_WARNING_PATTERNS):
        return False

    allowed_tool_names = [tool.casefold() for tool in CLAUDE_ALLOWED_TOOLS.split(",")]
    normalized_output = combined_output.casefold()
    return any(tool_name in normalized_output for tool_name in allowed_tool_names)


def ensure_changes_present(
    repo_root: Path,
    worktree: Path,
    base_commit: str,
    modified_paths: list[str],
) -> None:
    try:
        commits = commit_count_since(repo_root, worktree, base_commit)
    except GitError as exc:
        raise RunTaskError(str(exc)) from exc

    if commits <= 0 and not modified_paths:
        raise RunTaskError("Le worktree ne contient ni modification ni nouveau commit.")


def ensure_paths_allowed(repo_root: Path, allowed_paths: list[str], modified_paths: list[str]) -> None:
    allowed = [normalize_allowed_path(item) for item in allowed_paths]
    unauthorized: list[str] = []

    for modified_path in modified_paths:
        candidate = normalize_modified_path(modified_path)
        if not any(is_relative_to(candidate, allowed_path) for allowed_path in allowed):
            unauthorized.append(candidate.as_posix())

    if unauthorized:
        joined = ", ".join(unauthorized)
        raise RunTaskError(f"Chemins modifiés hors périmètre autorisé : {joined}")


def normalize_allowed_path(allowed_path: str) -> Path:
    try:
        return normalize_repo_relative_path(allowed_path)
    except ValueError as exc:
        raise RunTaskError(str(exc)) from exc


def normalize_modified_path(modified_path: str) -> Path:
    try:
        return normalize_repo_relative_path(modified_path)
    except ValueError as exc:
        raise RunTaskError(str(exc)) from exc


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_command_safe(command: str) -> list[str]:
    if any(token in command for token in FORBIDDEN_COMMAND_TOKENS):
        raise RunTaskError(f"Commande de validation dangereuse refusée : {command}")
    return shlex.split(command)


def run_validation_commands(
    worktree: Path,
    commands: list[str],
    extra_env: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in commands:
        argv = validate_command_safe(command)
        result = run_process_capturing_timeout(
            command=argv,
            cwd=worktree,
            timeout_seconds=timeout_for_command(command),
            extra_env=extra_env,
        )
        results.append(
            {
                "command": command,
                "argv": argv,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timed_out": result.timed_out,
            }
        )
    return results


def summarize_validations(validations: list[dict[str, Any]]) -> list[str]:
    return [
        f"{item['command']}={'OK' if item['returncode'] == 0 else 'ECHEC'}"
        for item in validations
    ]


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def ensure_dependency_changes_allowed(task: dict[str, Any], modified_paths: list[str]) -> None:
    if not any(is_dependency_manifest(path) for path in modified_paths):
        return
    reason = str(task.get("dependency_change_reason", "")).strip()
    if not reason:
        raise RunTaskError(
            "Changement de dépendances détecté hors scope autorisé. Retourner HUMAN_REVIEW_REQUIRED avec une tâche préalable dédiée."
        )
