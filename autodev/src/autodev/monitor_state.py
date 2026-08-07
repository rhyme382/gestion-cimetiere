from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autodev.acceptance_criteria import build_coverage_matrix
from autodev.git_context import GitContextError, build_current_task_git_state
from autodev.git_tools import GitError, branch_exists, dirty_paths, git_output, worktree_registered
from autodev.planner import PlanningError, find_repo_root, load_json, validate_backlog_consistency
from autodev.run_feature import determine_task_resume_action
from autodev.task_dependencies import get_unfinished_dependencies

DISPLAY_STATUSES = {
    "PENDING",
    "READY",
    "IMPLEMENTING",
    "REVIEWING",
    "CORRECTING",
    "APPROVED",
    "INTEGRATING",
    "INTEGRATED",
    "FAILED",
    "TIMEOUT",
    "HUMAN_REVIEW_REQUIRED",
    "COMPLETED",
}
FEATURE_TERMINAL_STATUSES = {"COMPLETED", "FAILED", "TIMEOUT", "HUMAN_REVIEW_REQUIRED", "INTERRUPTED"}
TASK_PROGRESS = {
    "PENDING": 0, "READY": 0, "IMPLEMENTING": 25, "REVIEWING": 50,
    "CORRECTING": 60, "APPROVED": 75, "INTEGRATING": 90,
    "INTEGRATED": 100, "COMPLETED": 100,
}
ACTION_LOG_CANDIDATES = {
    "IMPLEMENT": ("claude.stdout.log", "claude.stderr.log"),
    "REVIEW": ("review/codex.stdout.log", "review/codex.stderr.log", "review/validation-results.json"),
    "CORRECT": (
        "corrections/latest/claude.stdout.log",
        "corrections/latest/claude.stderr.log",
        "corrections/latest/result.json",
    ),
    "INTEGRATE": ("integration/stdout.log", "integration/stderr.log", "integration/validation-results.json"),
}


class MonitorStateError(RuntimeError):
    """Erreur pendant la lecture déterministe de l'état monitoré."""


def read_feature_state(
    backlog_json: Path,
    *,
    include_logs: bool = False,
    log_lines: int = 20,
    now: datetime | None = None,
) -> dict[str, Any]:
    repo_root = find_repo_root(backlog_json.parent)
    backlog = _load_and_validate_backlog(backlog_json)
    feature_id = backlog["feature_id"]
    feature_run_dir = repo_root / ".autodev" / "runs" / "features" / feature_id
    feature_result = _load_json_if_exists(feature_run_dir / "run-feature-result.json")
    last_state = _load_json_if_exists(feature_run_dir / "last-state.json")

    tasks = [
        read_task_state(
            repo_root=repo_root,
            task=task,
            current_task_id=last_state.get("current_task_id"),
            current_action=last_state.get("task_action"),
            now=now or datetime.now(timezone.utc),
        )
        for task in backlog["tasks"]
    ]
    coverage = build_coverage_matrix(backlog, repo_root)
    task_coverage = coverage["tasks"]
    for task_state in tasks:
        counts = task_coverage.get(task_state["task_id"], {})
        task_state["owned_criteria"] = counts.get("owned", 0)
        task_state["approved_criteria"] = counts.get("approved", 0)
    current_task = determine_current_task(last_state=last_state, tasks=tasks)
    current_task_id = current_task["task_id"] if current_task else None
    current_action = last_state.get("task_action") or (current_task.get("action_current") if current_task else None)
    feature_status = determine_feature_display_status(feature_result=feature_result, last_state=last_state, tasks=tasks)
    last_updated = determine_last_updated(feature_run_dir, tasks)
    started_at = last_state.get("started_at") or feature_result.get("started_at")
    finished_at = feature_result.get("finished_at")
    elapsed_seconds = compute_elapsed_seconds(
        started_at=started_at,
        finished_at=finished_at,
        status=feature_status,
        now=now or datetime.now(timezone.utc),
    )

    integrated_count = sum(1 for task in tasks if task["status"] in {"INTEGRATED", "COMPLETED"})
    total_count = len(tasks)
    percentage = int((integrated_count / total_count) * 100) if total_count else 0
    estimated_percentage = int(sum(task["progress_percentage"] for task in tasks) / total_count) if total_count else 0
    checkpoints_path = feature_result.get("checkpoints_path") or str(repo_root / ".autodev" / "state" / "checkpoints.sqlite")
    reports_path = feature_result.get("reports_path") or str(feature_run_dir)
    intervention_required = (
        last_state.get("error")
        or last_state.get("last_error")
        or next((task["last_error"] for task in tasks if task["status"] == "HUMAN_REVIEW_REQUIRED"), None)
    )

    current_task_payload = {
        "task_id": current_task_id or "—",
        "task_action": current_action or "—",
        "status": current_task["status"] if current_task else "—",
        "correction_count": current_task["correction_count"] if current_task else "—",
        "last_error": (last_state.get("last_error") or (current_task.get("last_error") if current_task else None) or "—"),
        "started_at": started_at or "—",
        "elapsed_seconds": elapsed_seconds if elapsed_seconds is not None else "—",
        "git": current_task["git"] if current_task else {},
    }

    logs = []
    if include_logs and current_task_id:
        logs = get_recent_logs(
            repo_root=repo_root,
            task_id=current_task_id,
            action=current_action,
            log_lines=log_lines,
        )

    return build_render_model(
        feature_id=feature_id,
        feature_title=backlog["feature_title"],
        feature_status=feature_status,
        integrated_count=integrated_count,
        total_count=total_count,
        percentage=percentage,
        estimated_percentage=estimated_percentage,
        coverage=coverage,
        current_task_id=current_task_id,
        current_action=current_action,
        last_updated=last_updated,
        checkpoints_path=checkpoints_path,
        reports_path=reports_path,
        intervention_required=intervention_required or "—",
        current_task=current_task_payload,
        tasks=tasks,
        logs=logs,
    )


def read_task_state(
    *,
    repo_root: Path,
    task: dict[str, Any],
    current_task_id: str | None,
    current_action: str | None,
    now: datetime,
) -> dict[str, Any]:
    task_id = task["id"]
    run_dir = repo_root / ".autodev" / "runs" / task_id
    run_result = _load_json_if_exists(run_dir / "result.json")
    review_result = _load_json_if_exists(run_dir / "review" / "review-result.json")
    integration_result = _load_json_if_exists(run_dir / "integration" / "integration-result.json")
    correction_count = count_corrections(run_dir / "corrections")
    branch = f"autodev/{task_id}"
    worktree = Path(
        str(
            run_result.get("worktree")
            or _load_json_if_exists(run_dir / "task.json").get("worktree")
            or (repo_root / ".autodev" / "worktrees" / task_id)
        )
    )
    branch_present = safe_branch_exists(repo_root, branch)
    worktree_exists = worktree.exists()
    worktree_present = worktree_exists or safe_worktree_registered(repo_root, worktree)
    action_current = current_action if current_task_id == task_id else infer_task_action(repo_root=repo_root, task=task)
    git_state = get_git_state(
        repo_root=repo_root,
        task_id=task_id,
        branch=branch,
        worktree=worktree,
        branch_present=branch_present,
        worktree_present=worktree_present,
    )
    status = determine_display_status(
        task=task,
        run_result=run_result,
        review_result=review_result,
        integration_result=integration_result,
        branch_present=branch_present,
        worktree_present=worktree_present,
        is_current=current_task_id == task_id,
        current_action=current_action,
        repo_root=repo_root,
        task_id=task_id,
    )
    if status not in DISPLAY_STATUSES:
        raise MonitorStateError(f"Statut d'affichage invalide pour {task_id} : {status}")

    latest_error = find_last_error(run_result, review_result, integration_result, run_dir)
    progress_percentage = TASK_PROGRESS.get(status, 0)
    activity = read_heartbeat(
        run_dir / "heartbeat.json",
        now=now,
        active=status in {"IMPLEMENTING", "REVIEWING", "CORRECTING", "INTEGRATING"},
    )
    return {
        "task_id": task_id,
        "agent": task["agent"],
        "title": shorten_text(task["title"], 40),
        "depends_on": ", ".join(task["depends_on"]) or "—",
        "status": status,
        "action_current": action_current or "—",
        "review_verdict": review_result.get("verdict") or "—",
        "correction_count": correction_count,
        "branch": branch,
        "worktree_exists": "yes" if worktree_present else "no",
        "produced_commit": git_state["head"] or run_result.get("produced_commit") or "—",
        "integration_status": integration_result.get("status") or "—",
        "last_error": latest_error or "—",
        "owned_criteria": 0,
        "approved_criteria": 0,
        "git": git_state,
        "run_dir": str(run_dir),
        "progress_percentage": progress_percentage,
        "activity": activity,
    }


def determine_feature_display_status(
    *,
    feature_result: dict[str, Any],
    last_state: dict[str, Any],
    tasks: list[dict[str, Any]],
) -> str:
    raw_status = feature_result.get("status") or last_state.get("status")
    if raw_status == "INTERRUPTED":
        return "FAILED"
    if raw_status in DISPLAY_STATUSES:
        return raw_status
    if raw_status:
        return raw_status
    if tasks and all(task["status"] in {"INTEGRATED", "COMPLETED"} for task in tasks):
        return "COMPLETED"
    if any(task["status"] == "FAILED" for task in tasks):
        return "FAILED"
    if any(task["status"] == "HUMAN_REVIEW_REQUIRED" for task in tasks):
        return "HUMAN_REVIEW_REQUIRED"
    return "NOT_STARTED"


def determine_current_task(*, last_state: dict[str, Any], tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    current_task_id = last_state.get("current_task_id")
    if current_task_id:
        for task in tasks:
            if task["task_id"] == current_task_id:
                return task
    for task in tasks:
        if task["status"] in {"IMPLEMENTING", "REVIEWING", "CORRECTING", "APPROVED", "INTEGRATING"}:
            return task
    return None


def determine_display_status(
    *,
    task: dict[str, Any],
    run_result: dict[str, Any],
    review_result: dict[str, Any],
    integration_result: dict[str, Any],
    branch_present: bool,
    worktree_present: bool,
    is_current: bool,
    current_action: str | None,
    repo_root: Path,
    task_id: str,
) -> str:
    integration_status = integration_result.get("status")
    if integration_status == "INTEGRATED":
        return "INTEGRATED"
    if integration_status == "HUMAN_REVIEW_REQUIRED":
        return "HUMAN_REVIEW_REQUIRED"
    if integration_status in {"FAILED", "CONFLICT"}:
        return "FAILED"

    review_verdict = review_result.get("verdict")
    if review_verdict == "APPROVED":
        return "APPROVED" if not is_current or current_action != "INTEGRATE" else "INTEGRATING"
    if review_verdict == "CORRECTION_REQUIRED":
        return "CORRECTING"
    if review_verdict == "HUMAN_REVIEW_REQUIRED":
        return "HUMAN_REVIEW_REQUIRED"

    if run_result.get("claude_timeout") or "TIMEOUT" in str(run_result.get("error") or ""):
        return "TIMEOUT"
    if run_result.get("status") == "failed":
        return "FAILED"
    if run_result.get("status") == "running":
        return "IMPLEMENTING"

    if is_current:
        action_map = {
            "IMPLEMENT": "IMPLEMENTING",
            "REVIEW": "REVIEWING",
            "CORRECT": "CORRECTING",
            "INTEGRATE": "INTEGRATING",
        }
        if current_action in action_map:
            return action_map[current_action]

    decision = determine_task_resume_action(repo_root=repo_root, task_id=task_id)
    if decision.action == "COMPLETED":
        return "COMPLETED"
    if decision.action == "INTEGRATE":
        return "APPROVED"
    if decision.action == "REVIEW":
        return "REVIEWING"
    if decision.action == "CORRECT":
        return "CORRECTING"
    if decision.action == "HUMAN_REVIEW":
        return "HUMAN_REVIEW_REQUIRED"
    if decision.action == "INVALID_STATE":
        return "FAILED"

    unfinished_dependencies = get_unfinished_dependencies(repo_root, task)
    if branch_present or worktree_present or run_result.get("status") == "running":
        return "IMPLEMENTING"
    return "PENDING" if unfinished_dependencies else "READY"


def infer_task_action(*, repo_root: Path, task: dict[str, Any]) -> str | None:
    decision = determine_task_resume_action(repo_root=repo_root, task_id=task["id"])
    mapping = {
        "IMPLEMENT": "IMPLEMENT",
        "REVIEW": "REVIEW",
        "CORRECT": "CORRECT",
        "INTEGRATE": "INTEGRATE",
    }
    return mapping.get(decision.action)


def get_recent_logs(
    *,
    repo_root: Path,
    task_id: str,
    action: str | None,
    log_lines: int,
) -> list[dict[str, Any]]:
    run_dir = repo_root / ".autodev" / "runs" / task_id
    candidates = resolve_log_candidates(run_dir, action)
    logs: list[dict[str, Any]] = []
    for label, path in candidates:
        if not path.is_file():
            continue
        lines = read_last_lines(path, log_lines)
        logs.append({"label": label, "path": str(path), "lines": lines})
    return logs


def resolve_log_candidates(run_dir: Path, action: str | None) -> list[tuple[str, Path]]:
    selected = ACTION_LOG_CANDIDATES.get(action or "", ())
    candidates: list[tuple[str, Path]] = []
    for relative in selected:
        if relative.startswith("corrections/latest/"):
            latest = latest_correction_dir(run_dir / "corrections")
            if latest is None:
                continue
            actual_relative = relative.replace("corrections/latest/", f"corrections/{latest.name}/")
            candidates.append((actual_relative, run_dir / actual_relative))
        else:
            candidates.append((relative, run_dir / relative))

    if not candidates:
        fallbacks = [
            "claude.stdout.log",
            "claude.stderr.log",
            "review/codex.stdout.log",
            "review/codex.stderr.log",
            "integration/stdout.log",
            "integration/stderr.log",
        ]
        for relative in fallbacks:
            candidates.append((relative, run_dir / relative))
    return candidates


def get_git_state(
    *,
    repo_root: Path,
    task_id: str,
    branch: str,
    worktree: Path,
    branch_present: bool,
    worktree_present: bool,
) -> dict[str, Any]:
    head: str | None = None
    modified_paths: list[str] = []
    is_dirty: bool | None = None

    if branch_present:
        try:
            git_state = build_current_task_git_state(repo_root, task_id)
            head = git_state.produced_commit
            modified_paths = git_state.modified_paths
            if git_state.worktree.exists():
                current_dirty_paths = dirty_paths(repo_root, cwd=git_state.worktree)
                if current_dirty_paths:
                    modified_paths = sorted(set(modified_paths) | set(current_dirty_paths))
                is_dirty = bool(current_dirty_paths)
        except GitContextError:
            head = safe_git_output(repo_root, ["rev-parse", branch])

    if worktree_present and worktree.exists():
        if head is None:
            head = safe_git_output(repo_root, ["rev-parse", "HEAD"], cwd=worktree)
        current_dirty_paths = safe_dirty_paths(repo_root, worktree)
        if current_dirty_paths is not None:
            modified_paths = sorted(set(modified_paths) | set(current_dirty_paths))
            is_dirty = bool(current_dirty_paths)

    return {
        "branch": branch,
        "worktree": str(worktree),
        "worktree_exists": worktree_present,
        "head": head,
        "modified_paths": modified_paths,
        "modified_count": len(modified_paths),
        "is_dirty": is_dirty,
    }


def build_render_model(
    *,
    feature_id: str,
    feature_title: str,
    feature_status: str,
    integrated_count: int,
    total_count: int,
    percentage: int,
    estimated_percentage: int,
    coverage: dict[str, Any],
    current_task_id: str | None,
    current_action: str | None,
    last_updated: str,
    checkpoints_path: str,
    reports_path: str,
    intervention_required: str,
    current_task: dict[str, Any],
    tasks: list[dict[str, Any]],
    logs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "feature_id": feature_id,
        "feature_title": feature_title,
        "feature_status": feature_status,
        "progress": {
            "integrated": integrated_count,
            "total": total_count,
            "percentage": percentage,
            "estimated_percentage": estimated_percentage,
        },
        "coverage": coverage,
        "current_task_id": current_task_id or "—",
        "current_action": current_action or "—",
        "last_updated": last_updated,
        "checkpoints_path": checkpoints_path,
        "reports_path": reports_path,
        "intervention_required": intervention_required,
        "current_task": current_task,
        "tasks": tasks,
        "logs": logs,
    }


def read_heartbeat(path: Path, *, now: datetime, active: bool) -> dict[str, Any]:
    payload = _load_json_if_exists(path)
    updated = parse_datetime(payload.get("updated_at"))
    if updated is None:
        return {"status": "INCONNU" if active else "—", "age_seconds": None, "phase": "—"}
    age = max(0, int((now - updated).total_seconds()))
    status = "ACTIF" if age < 120 else "CALME" if age < 600 else "SUSPECT"
    return {"status": status, "age_seconds": age, "phase": payload.get("phase") or "—"}


def read_last_lines(path: Path, line_count: int) -> list[str]:
    if line_count <= 0:
        return []
    with path.open("rb") as stream:
        stream.seek(0, 2)
        position = stream.tell()
        buffer = bytearray()
        chunk_size = 4096
        newline_target = line_count + 1
        while position > 0 and buffer.count(b"\n") < newline_target:
            read_size = min(chunk_size, position)
            position -= read_size
            stream.seek(position)
            buffer[:0] = stream.read(read_size)
        text = buffer.decode("utf-8", errors="replace")
    lines = text.splitlines()
    return lines[-line_count:]


def count_corrections(corrections_dir: Path) -> int:
    if not corrections_dir.is_dir():
        return 0
    return len([child for child in corrections_dir.iterdir() if child.is_dir()])


def latest_correction_dir(corrections_dir: Path) -> Path | None:
    if not corrections_dir.is_dir():
        return None
    directories = sorted((child for child in corrections_dir.iterdir() if child.is_dir()), key=lambda path: path.name)
    return directories[-1] if directories else None


def determine_last_updated(feature_run_dir: Path, tasks: list[dict[str, Any]]) -> str:
    candidates: list[Path] = [
        feature_run_dir / "last-state.json",
        feature_run_dir / "run-feature-result.json",
    ]
    for task in tasks:
        run_dir = Path(task["run_dir"])
        candidates.extend(
            [
                run_dir / "result.json",
                run_dir / "review" / "review-result.json",
                run_dir / "integration" / "integration-result.json",
            ]
        )
    timestamps = [datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat() for path in candidates if path.is_file()]
    return max(timestamps) if timestamps else "—"


def compute_elapsed_seconds(
    *,
    started_at: str | None,
    finished_at: str | None,
    status: str,
    now: datetime,
) -> int | None:
    start = parse_datetime(started_at)
    if start is None:
        return None
    end = parse_datetime(finished_at) if status in FEATURE_TERMINAL_STATUSES else now
    if end is None:
        end = now
    return max(0, int((end - start).total_seconds()))


def parse_datetime(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    try:
        normalized = raw_value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def find_last_error(
    run_result: dict[str, Any],
    review_result: dict[str, Any],
    integration_result: dict[str, Any],
    run_dir: Path,
) -> str | None:
    latest_correction = latest_correction_dir(run_dir / "corrections")
    correction_result = _load_json_if_exists(latest_correction / "result.json") if latest_correction else {}
    review_summary = review_result.get("summary") if review_result.get("verdict") == "HUMAN_REVIEW_REQUIRED" else None
    return (
        integration_result.get("error")
        or correction_result.get("error")
        or review_summary
        or run_result.get("error")
    )


def shorten_text(value: str, size: int) -> str:
    if len(value) <= size:
        return value
    return value[: size - 1] + "…"


def _load_and_validate_backlog(backlog_json: Path) -> dict[str, Any]:
    try:
        backlog = load_json(backlog_json)
        validate_backlog_consistency(backlog)
        return backlog
    except PlanningError as exc:
        raise MonitorStateError(str(exc)) from exc


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MonitorStateError(f"JSON invalide : {path}") from exc


def safe_branch_exists(repo_root: Path, branch: str) -> bool:
    try:
        return branch_exists(repo_root, branch)
    except GitError:
        return False


def safe_worktree_registered(repo_root: Path, worktree: Path) -> bool:
    try:
        return worktree_registered(repo_root, worktree)
    except GitError:
        return False


def safe_git_output(repo_root: Path, args: list[str], cwd: Path | None = None) -> str | None:
    try:
        return git_output(repo_root, args, cwd=cwd)
    except GitError:
        return None


def safe_dirty_paths(repo_root: Path, worktree: Path) -> list[str] | None:
    try:
        return dirty_paths(repo_root, cwd=worktree)
    except GitError:
        return None
