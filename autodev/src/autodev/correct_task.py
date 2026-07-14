from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autodev.git_tools import (
    GitError,
    amend_head_commit,
    branch_exists,
    changed_paths_since,
    commit_count_since,
    create_commit,
    git_status_porcelain,
    head_commit,
    stage_all,
)
from autodev.planner import PlanningError, find_repo_root, load_json, validate_backlog_consistency
from autodev.review_task import ReviewTaskError
from autodev.task_runner import (
    RunTaskError,
    build_prompt,
    ensure_changes_present,
    ensure_claude_completed_successfully,
    ensure_paths_allowed,
    find_task,
    run_claude_non_interactive,
    run_validation_commands,
    summarize_validations,
    write_json,
)


class CorrectTaskError(RuntimeError):
    """Erreur pendant la correction automatique d'une tâche."""


def correct_task(
    backlog_json: Path,
    task_id: str,
    *,
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
    correction_index = next_correction_index(run_dir)
    correction_dir = run_dir / "corrections" / f"{correction_index:02d}"
    correction_dir.mkdir(parents=True, exist_ok=True)

    prompt = build_correction_prompt(
        repo_root=repo_root,
        backlog_json=backlog_json,
        backlog=backlog,
        task=task,
        review_result=review_result,
    )
    (correction_dir / "prompt.md").write_text(prompt, encoding="utf-8")

    result: dict[str, Any] = {
        "task_id": task_id,
        "status": "running",
        "branch": branch,
        "worktree": str(worktree),
        "base_commit": base_commit,
        "starting_commit": current_head,
        "produced_commit": None,
        "modified_paths": [],
        "validations": [],
        "validation_summary": [],
        "error": None,
        "correction_number": correction_index,
    }

    claude_runner = claude_runner or run_claude_non_interactive

    try:
        claude_result = claude_runner(worktree=worktree, prompt=prompt)
        result["claude_exit_code"] = claude_result["returncode"]
        (correction_dir / "claude.stdout.log").write_text(claude_result["stdout"], encoding="utf-8")
        (correction_dir / "claude.stderr.log").write_text(claude_result["stderr"], encoding="utf-8")
        ensure_claude_completed_successfully(claude_result)

        current_status = git_status(repo_root, worktree)
        current_head_after_claude = resolve_current_head(repo_root, worktree)
        if current_head_after_claude != current_head:
            raise CorrectTaskError(
                "Claude a créé ou modifié l'historique Git pendant la correction ; opération refusée."
            )
        if not current_status and not before_status:
            raise CorrectTaskError("Claude a terminé sans produire aucune modification.")

        modified_paths = changed_paths_since(repo_root, worktree, base_commit)
        result["modified_paths"] = modified_paths
        ensure_changes_present(repo_root, worktree, base_commit, modified_paths)
        ensure_paths_allowed(repo_root, task["allowed_paths"], modified_paths)

        validations = run_validation_commands(worktree, task["validation_commands"])
        result["validations"] = validations
        result["validation_summary"] = summarize_validations(validations)

        stage_all(repo_root, cwd=worktree)
        if commit_count_since(repo_root, worktree, base_commit) > 0:
            amend_head_commit(repo_root, cwd=worktree)
        else:
            create_commit(repo_root, f"autodev correct-task {task_id}", cwd=worktree)

        result["produced_commit"] = head_commit(repo_root, worktree)
    except (CorrectTaskError, GitError, RunTaskError) as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        write_json(correction_dir / "result.json", result)
        raise CorrectTaskError(str(exc)) from exc

    run_result["produced_commit"] = result["produced_commit"]
    run_result["modified_paths"] = result["modified_paths"]
    run_result["validations"] = result["validations"]
    run_result["validation_summary"] = result["validation_summary"]
    run_result["status"] = "success"
    write_json(run_dir / "result.json", run_result)

    result["status"] = "success"
    write_json(correction_dir / "result.json", result)
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
) -> str:
    spec_path = repo_root / backlog.get("specification_path", "SPEC.md")
    specification = spec_path.read_text(encoding="utf-8")
    original_prompt = build_prompt(repo_root, backlog_json, backlog, task)
    review_blob = json.dumps(review_result, ensure_ascii=False, indent=2)

    issues = review_result.get("issues", [])
    issue_lines = "\n".join(
        f"- {issue.get('severity', 'unknown')} : {issue.get('message', '')}".rstrip()
        for issue in issues
    ) or "- Aucun détail fourni."

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

    return f"""# Correction automatique d'une tâche autodev

Tu interviens uniquement pour corriger la tâche `{task["id"]}` dans le worktree existant.

Interdictions absolues :
- ne pas faire de merge ;
- ne pas modifier la spécification ;
- ne pas traiter les tâches suivantes ;
- ne pas modifier `autodev` sauf si cette tâche l'autorise explicitement ;
- ne pas créer de commit ; laisse les modifications non commitées pour l'outil de correction ;
- ne pas modifier de chemin hors périmètre autorisé.

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
