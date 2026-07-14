from __future__ import annotations

from pathlib import Path
from typing import Any

from autodev.git_tools import (
    GitError,
    branch_exists,
    branch_head,
    changed_paths_between,
    commit_merge,
    current_branch,
    current_head,
    diff_patch_between,
    ensure_clean_worktree,
    git_output,
    git_status_porcelain,
    hard_reset,
    has_merge_conflicts,
    is_ancestor,
    merge_abort,
    merge_no_commit,
    name_status_between,
    remove_worktree,
    worktree_registered,
)
from autodev.planner import PlanningError, find_repo_root, load_json, validate_backlog_consistency
from autodev.task_runner import (
    RunTaskError,
    ensure_paths_allowed,
    find_task,
    summarize_validations,
    write_json,
)
from autodev.validation_baseline import (
    ENVIRONMENT_ERROR,
    FAIL_NEW_REGRESSION,
    INDETERMINATE,
    PASS,
    PASS_IMPROVED,
    PASS_WITH_BASELINE_FAILURES,
    compare_validation_results,
    load_quality_gates,
    run_validation_set,
)

APPROVED_VERDICT = "APPROVED"
INTEGRATION_STATUSES = {"INTEGRATED", "FAILED", "CONFLICT", "HUMAN_REVIEW_REQUIRED"}


class IntegrateTaskError(RuntimeError):
    """Erreur pendant l'intégration contrôlée d'une tâche."""


def integrate_task(backlog_json: Path, task_id: str) -> dict[str, Any]:
    repo_root = find_repo_root(backlog_json.parent)
    backlog = load_and_validate_backlog(backlog_json)
    task = resolve_task(backlog, task_id)
    branch = f"autodev/{task_id}"

    if not branch_exists(repo_root, branch):
        raise IntegrateTaskError(f"Branche de tâche absente : {branch}")

    run_dir = repo_root / ".autodev" / "runs" / task_id
    integration_dir = run_dir / "integration"
    integration_dir.mkdir(parents=True, exist_ok=True)

    result = build_initial_result(task_id=task_id, repo_root=repo_root, branch=branch)
    stdout_log = ""
    stderr_log = ""

    try:
        review_result = load_required_json(run_dir / "review" / "review-result.json")
        verdict = review_result.get("verdict")
        result["pre_review_verdict"] = verdict
        if verdict != APPROVED_VERDICT:
            raise IntegrateTaskError(
                f"Verdict de revue incompatible avec l'intégration : {verdict!r}."
            )

        ensure_clean_worktree(repo_root)

        run_result = load_optional_json(run_dir / "result.json")
        task_record = load_optional_json(run_dir / "task.json")
        quality_gates = load_quality_gates(repo_root)
        full_commands = list(quality_gates["full"].get("commands", []))
        if not full_commands:
            raise IntegrateTaskError("Aucune commande FULL configurée dans quality-gates.yaml.")
        base_commit = resolve_base_commit(run_result, task_record)
        worktree = resolve_worktree(repo_root, task_id, run_result, task_record)
        produced_commit = resolve_produced_commit(repo_root, branch)
        target_branch = current_branch(repo_root)
        target_before = current_head(repo_root)

        result["target_branch"] = target_branch
        result["base_commit"] = base_commit
        result["produced_commit"] = produced_commit

        record_text(integration_dir / "git-before.txt", build_git_snapshot(repo_root))

        if worktree.exists():
            ensure_worktree_clean(repo_root, worktree)
        if not is_ancestor(repo_root, base_commit, produced_commit):
            raise IntegrateTaskError(
                "Le commit produit ne descend pas du base_commit enregistré."
            )

        current_diff = collect_current_diff(
            repo_root=repo_root,
            base_commit=base_commit,
            produced_commit=produced_commit,
        )
        write_current_diff_artifacts(
            integration_dir=integration_dir,
            base_commit=base_commit,
            produced_commit=produced_commit,
            current_diff=current_diff,
        )

        modified_paths = current_diff["modified_paths"]
        ensure_paths_allowed(repo_root, task["allowed_paths"], modified_paths)

        if is_ancestor(repo_root, produced_commit, target_before):
            raise IntegrateTaskError(
                f"Le commit produit {produced_commit} est déjà intégré dans {target_branch}."
            )

        task_pre_merge = run_validation_set(
            repo_root,
            list(task["validation_commands"]),
            integration_dir / "task-pre-merge",
            label="TASK_PRE_MERGE",
        )
        result["task_validation_status"] = task_pre_merge["status"]
        if task_pre_merge["status"] != PASS:
            write_json(integration_dir / "validation-results.json", task_pre_merge)
            stdout_log += (integration_dir / "task-pre-merge" / "stdout.log").read_text(encoding="utf-8")
            stderr_log += (integration_dir / "task-pre-merge" / "stderr.log").read_text(encoding="utf-8")
            raise IntegrateTaskError("Une validation TASK a échoué avant la fusion temporaire.")

        baseline_results = run_validation_set(
            repo_root,
            full_commands,
            integration_dir / "baseline",
            label="FULL_BASELINE",
        )
        result["baseline_status"] = baseline_results["status"]
        stdout_log += (integration_dir / "baseline" / "stdout.log").read_text(encoding="utf-8")
        stderr_log += (integration_dir / "baseline" / "stderr.log").read_text(encoding="utf-8")

        merge_result = merge_no_commit(repo_root, branch)
        stdout_log += merge_result.stdout
        stderr_log += merge_result.stderr

        if merge_result.returncode != 0:
            had_conflict = handle_failed_merge(repo_root, result, integration_dir)
            result["status"] = "CONFLICT" if had_conflict else "FAILED"
            detail = merge_result.stderr.strip() or merge_result.stdout.strip() or "échec Git inconnu"
            raise IntegrateTaskError(f"Intégration refusée : {detail}")

        task_post_merge = run_validation_set(
            repo_root,
            list(task["validation_commands"]),
            integration_dir / "task-post-merge",
            label="TASK_POST_MERGE",
        )
        result["task_validation_status"] = task_post_merge["status"]
        write_json(integration_dir / "validation-results.json", task_post_merge)
        stdout_log += (integration_dir / "task-post-merge" / "stdout.log").read_text(encoding="utf-8")
        stderr_log += (integration_dir / "task-post-merge" / "stderr.log").read_text(encoding="utf-8")
        result["validations"] = summarize_validations(list(task_post_merge["results"]))

        if task_post_merge["status"] != PASS:
            hard_reset(repo_root, target_before)
            result["status"] = "FAILED"
            result["error"] = "Une validation TASK a échoué après la fusion temporaire."
            raise IntegrateTaskError(result["error"])

        post_merge_results = run_validation_set(
            repo_root,
            full_commands,
            integration_dir / "post-merge",
            label="FULL_POST_MERGE",
        )
        stdout_log += (integration_dir / "post-merge" / "stdout.log").read_text(encoding="utf-8")
        stderr_log += (integration_dir / "post-merge" / "stderr.log").read_text(encoding="utf-8")

        comparison = compare_validation_results(baseline_results, post_merge_results)
        result["comparison_status"] = comparison["status"]
        result["new_regression_count"] = len(comparison["new_failures"])
        result["persistent_failure_count"] = len(comparison["persistent_failures"])
        write_json(integration_dir / "comparison.json", comparison)

        if comparison["status"] in {FAIL_NEW_REGRESSION, INDETERMINATE}:
            hard_reset(repo_root, target_before)
            result["status"] = "FAILED"
            result["error"] = comparison["summary"]
            raise IntegrateTaskError(result["error"])

        if comparison["status"] == ENVIRONMENT_ERROR:
            hard_reset(repo_root, target_before)
            result["status"] = "HUMAN_REVIEW_REQUIRED"
            result["error"] = comparison["summary"]
            raise IntegrateTaskError(result["error"])

        if comparison["status"] not in {PASS, PASS_WITH_BASELINE_FAILURES, PASS_IMPROVED}:
            hard_reset(repo_root, target_before)
            result["status"] = "FAILED"
            result["error"] = comparison["summary"]
            raise IntegrateTaskError(result["error"])

        commit_message = f"autodev integrate-task {task_id}"
        commit_merge(repo_root, commit_message)
        integration_commit = current_head(repo_root)
        result["integration_commit"] = integration_commit

        cleanup_worktree(repo_root, worktree, result)
        result["status"] = "INTEGRATED"
        record_text(integration_dir / "git-after.txt", build_git_snapshot(repo_root))
        record_text(integration_dir / "stdout.log", stdout_log)
        record_text(integration_dir / "stderr.log", stderr_log)
        write_json(integration_dir / "integration-result.json", result)
        return result
    except (IntegrateTaskError, GitError, RunTaskError, PlanningError) as exc:
        if not result["error"]:
            result["error"] = str(exc)
        if result["status"] not in INTEGRATION_STATUSES:
            result["status"] = "FAILED"
        ensure_validation_file(integration_dir, task_id, result["target_branch"])
        finalize_failure_artifacts(
            repo_root=repo_root,
            integration_dir=integration_dir,
            result=result,
            stdout_log=stdout_log,
            stderr_log=stderr_log,
        )
        raise IntegrateTaskError(str(exc)) from exc


def load_and_validate_backlog(backlog_json: Path) -> dict[str, Any]:
    try:
        backlog = load_json(backlog_json)
        validate_backlog_consistency(backlog)
    except PlanningError as exc:
        raise IntegrateTaskError(str(exc)) from exc
    return backlog


def resolve_task(backlog: dict[str, Any], task_id: str) -> dict[str, Any]:
    try:
        return find_task(backlog, task_id)
    except RunTaskError as exc:
        raise IntegrateTaskError(str(exc)) from exc


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return load_json(path)
    except PlanningError as exc:
        raise IntegrateTaskError(str(exc)) from exc


def load_required_json(path: Path) -> dict[str, Any]:
    try:
        return load_json(path)
    except PlanningError as exc:
        raise IntegrateTaskError(str(exc)) from exc


def resolve_base_commit(run_result: dict[str, Any], task_record: dict[str, Any]) -> str:
    base_commit = run_result.get("base_commit") or task_record.get("base_commit")
    if not isinstance(base_commit, str) or not base_commit.strip():
        raise IntegrateTaskError("Commit de départ introuvable dans les artefacts run-task.")
    return base_commit


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


def resolve_produced_commit(
    repo_root: Path,
    branch: str,
) -> str:
    try:
        return branch_head(repo_root, branch)
    except GitError as exc:
        raise IntegrateTaskError(str(exc)) from exc


def collect_current_diff(
    *,
    repo_root: Path,
    base_commit: str,
    produced_commit: str,
) -> dict[str, Any]:
    try:
        return {
            "modified_paths": changed_paths_between(repo_root, base_commit, produced_commit),
            "name_status": name_status_between(repo_root, base_commit, produced_commit),
            "patch": diff_patch_between(repo_root, base_commit, produced_commit),
        }
    except GitError as exc:
        raise IntegrateTaskError(str(exc)) from exc


def write_current_diff_artifacts(
    *,
    integration_dir: Path,
    base_commit: str,
    produced_commit: str,
    current_diff: dict[str, Any],
) -> None:
    record_text(integration_dir / "current-diff.patch", str(current_diff["patch"]))
    write_json(
        integration_dir / "current-paths.json",
        {
            "base_commit": base_commit,
            "produced_commit": produced_commit,
            "modified_paths": list(current_diff["modified_paths"]),
        },
    )
    name_status = "\n".join(str(line) for line in current_diff["name_status"])
    record_text(
        integration_dir / "current-name-status.txt",
        f"{name_status}\n" if name_status else "",
    )


def ensure_worktree_clean(repo_root: Path, worktree: Path) -> None:
    try:
        status = git_status_porcelain(repo_root, cwd=worktree)
    except GitError as exc:
        raise IntegrateTaskError(str(exc)) from exc
    if status:
        raise IntegrateTaskError("Le worktree de la tâche contient des modifications non commitées.")


def handle_failed_merge(repo_root: Path, result: dict[str, Any], integration_dir: Path) -> bool:
    had_conflict = has_merge_conflicts(repo_root)
    if had_conflict:
        try:
            merge_abort(repo_root)
        except GitError as exc:
            result["status"] = "HUMAN_REVIEW_REQUIRED"
            result["error"] = str(exc)
            record_text(integration_dir / "git-after.txt", build_git_snapshot(repo_root))
            raise IntegrateTaskError(str(exc)) from exc
    else:
        if git_status_porcelain(repo_root):
            try:
                merge_abort(repo_root)
            except GitError:
                pass
    record_text(integration_dir / "git-after.txt", build_git_snapshot(repo_root))
    return had_conflict


def cleanup_worktree(repo_root: Path, worktree: Path, result: dict[str, Any]) -> None:
    if not worktree.exists() and not worktree_registered(repo_root, worktree):
        return
    try:
        remove_worktree(repo_root, worktree)
        result["worktree_removed"] = True
    except GitError as exc:
        result["worktree_removed"] = False
        raise IntegrateTaskError(str(exc)) from exc


def build_initial_result(task_id: str, repo_root: Path, branch: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "status": "FAILED",
        "pre_review_verdict": None,
        "target_branch": safe_current_branch(repo_root),
        "task_branch": branch,
        "base_commit": None,
        "produced_commit": None,
        "integration_commit": None,
        "task_validation_status": None,
        "baseline_status": None,
        "comparison_status": None,
        "new_regression_count": 0,
        "persistent_failure_count": 0,
        "validations": [],
        "error": None,
        "worktree_removed": False,
    }


def safe_current_branch(repo_root: Path) -> str | None:
    try:
        return current_branch(repo_root)
    except GitError:
        return None


def ensure_validation_file(integration_dir: Path, task_id: str, target_branch: str | None) -> None:
    path = integration_dir / "validation-results.json"
    if path.exists():
        return
    write_json(
        path,
        {
            "task_id": task_id,
            "target_branch": target_branch,
            "results": [],
        },
    )


def finalize_failure_artifacts(
    repo_root: Path,
    integration_dir: Path,
    result: dict[str, Any],
    stdout_log: str,
    stderr_log: str,
) -> None:
    record_text(integration_dir / "git-after.txt", build_git_snapshot(repo_root))
    record_text(integration_dir / "stdout.log", stdout_log)
    record_text(integration_dir / "stderr.log", stderr_log)
    write_json(integration_dir / "integration-result.json", result)


def build_git_snapshot(repo_root: Path) -> str:
    status = git_output(repo_root, ["status", "--short", "--branch"])
    worktrees = git_output(repo_root, ["worktree", "list", "--porcelain"])
    head = current_head(repo_root)
    branch = safe_current_branch(repo_root) or "DETACHED"
    return (
        f"branch: {branch}\n"
        f"head: {head}\n\n"
        f"[status]\n{status}\n\n"
        f"[worktrees]\n{worktrees}\n"
    )


def record_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
