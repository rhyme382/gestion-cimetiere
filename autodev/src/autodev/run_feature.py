from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from autodev.correct_task import CorrectTaskError, correct_task as correct_single_task
from autodev.git_context import GitContextError, resolve_base_commit, resolve_task_metadata, resolve_worktree
from autodev.git_tools import GitError, branch_exists, branch_head, git_output, worktree_registered
from autodev.integrate_task import IntegrateTaskError, integrate_task as integrate_single_task
from autodev.planner import PlanningError, find_repo_root, load_json, validate_backlog_consistency
from autodev.task_dependencies import get_unfinished_dependencies, is_task_integrated
from autodev.review_task import ReviewTaskError, review_task as review_single_task
from autodev.task_runner import RunTaskError, run_task as run_single_task, write_json

TERMINAL_STATUSES = {"COMPLETED", "FAILED", "HUMAN_REVIEW_REQUIRED", "INTERRUPTED"}
MAX_WORKFLOW_TRANSITIONS = 100
RESUME_ACTIONS = {
    "IMPLEMENT",
    "REVIEW",
    "CORRECT",
    "INTEGRATE",
    "COMPLETED",
    "HUMAN_REVIEW",
    "INVALID_STATE",
}


class RunFeatureError(RuntimeError):
    """Erreur pendant l'exécution d'une fonctionnalité complète."""


@dataclass(frozen=True)
class ResumeDecision:
    action: str
    reason: str | None = None


class RunFeatureState(TypedDict, total=False):
    backlog_path: str
    feature_id: str
    current_task_id: str | None
    completed_task_ids: list[str]
    pending_task_ids: list[str]
    correction_count: int
    max_corrections: int
    last_verdict: str | None
    task_action: str | None
    status: str
    error: str | None
    last_error: str | None
    transition_count: int
    max_transitions: int
    selection_signatures: list[str]
    started_at: str


ProgressCallback = Callable[[str], None]


def run_feature(
    backlog_json: Path,
    *,
    resume: bool = False,
    max_corrections: int = 3,
    run_task_fn: Callable[..., dict[str, Any]] | None = None,
    review_task_fn: Callable[..., dict[str, Any]] | None = None,
    correct_task_fn: Callable[..., dict[str, Any]] | None = None,
    integrate_task_fn: Callable[..., dict[str, Any]] | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    repo_root = find_repo_root(backlog_json.parent)
    backlog = load_and_validate_backlog(backlog_json)
    feature_id = backlog["feature_id"]
    checkpoints_path = repo_root / ".autodev" / "state" / "checkpoints.sqlite"
    checkpoints_path.parent.mkdir(parents=True, exist_ok=True)
    run_dir = repo_root / ".autodev" / "runs" / "features" / feature_id
    run_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc)

    thread_id = build_thread_id(feature_id)
    config = {"configurable": {"thread_id": thread_id}}

    with SqliteSaver.from_conn_string(str(checkpoints_path)) as checkpointer:
        graph = build_graph(
            backlog_json=backlog_json,
            checkpointer=checkpointer,
            run_task_fn=run_task_fn or run_single_task,
            review_task_fn=review_task_fn or review_single_task,
            correct_task_fn=correct_task_fn or correct_single_task,
            integrate_task_fn=integrate_task_fn or integrate_single_task,
            progress=progress,
        )

        existing = load_checkpoint_state(graph, config)
        if resume:
            if existing is None:
                raise RunFeatureError(
                    f"Aucun checkpoint existant pour {feature_id}, reprise impossible."
                )
            initial_state = reset_invocation_guards(existing)
        else:
            if existing is not None and existing.get("status") == "COMPLETED":
                return write_run_summary(
                    repo_root=repo_root,
                    run_dir=run_dir,
                    checkpoints_path=checkpoints_path,
                    state=existing,
                    started_at=started_at,
                )
            if existing is not None and existing.get("status") not in TERMINAL_STATUSES:
                raise RunFeatureError(
                    f"Une exécution inachevée existe déjà pour {feature_id}. Utiliser --resume."
                )
            if existing is not None:
                checkpointer.delete_thread(thread_id)
            initial_state = build_initial_state(
                backlog_json=backlog_json,
                feature_id=feature_id,
                max_corrections=max_corrections,
                started_at=started_at,
            )

        try:
            final_state = graph.invoke(initial_state, config=config)
        except KeyboardInterrupt as exc:
            interrupted_state = build_terminal_state(
                state=initial_state,
                status="INTERRUPTED",
                error="Exécution interrompue par l'utilisateur.",
            )
            write_run_summary(
                repo_root=repo_root,
                run_dir=run_dir,
                checkpoints_path=checkpoints_path,
                state=interrupted_state,
                started_at=started_at,
            )
            raise RunFeatureError(str(exc)) from exc

    summary = write_run_summary(
        repo_root=repo_root,
        run_dir=run_dir,
        checkpoints_path=checkpoints_path,
        state=final_state,
        started_at=started_at,
    )
    return summary


def build_graph(
    *,
    backlog_json: Path,
    checkpointer: Any,
    run_task_fn: Callable[..., dict[str, Any]],
    review_task_fn: Callable[..., dict[str, Any]],
    correct_task_fn: Callable[..., dict[str, Any]],
    integrate_task_fn: Callable[..., dict[str, Any]],
    progress: ProgressCallback | None,
) -> Any:
    builder = StateGraph(RunFeatureState)

    builder.add_node(
        "load_backlog",
        lambda state: node_load_backlog(state, backlog_json=backlog_json, progress=progress),
    )
    builder.add_node(
        "select_next_task",
        lambda state: node_select_next_task(state, backlog_json=backlog_json, progress=progress),
    )
    builder.add_node(
        "run_task",
        lambda state: node_run_task(
            state,
            backlog_json=backlog_json,
            run_task_fn=run_task_fn,
            progress=progress,
        ),
    )
    builder.add_node(
        "review_task",
        lambda state: node_review_task(
            state,
            backlog_json=backlog_json,
            review_task_fn=review_task_fn,
            progress=progress,
        ),
    )
    builder.add_node(
        "decide_review",
        lambda state: node_decide_review(state, progress=progress),
    )
    builder.add_node(
        "correct_task",
        lambda state: node_correct_task(
            state,
            backlog_json=backlog_json,
            correct_task_fn=correct_task_fn,
            progress=progress,
        ),
    )
    builder.add_node(
        "integrate_task",
        lambda state: node_integrate_task(
            state,
            backlog_json=backlog_json,
            integrate_task_fn=integrate_task_fn,
            progress=progress,
        ),
    )
    builder.add_node("finish", lambda state: state)

    builder.add_edge(START, "load_backlog")
    builder.add_edge("load_backlog", "select_next_task")
    builder.add_conditional_edges(
        "select_next_task",
        route_after_select,
        {
            "run_task": "run_task",
            "review_task": "review_task",
            "correct_task": "correct_task",
            "integrate_task": "integrate_task",
            "finish": "finish",
        },
    )
    builder.add_conditional_edges(
        "run_task",
        route_after_execution_step,
        {
            "review_task": "review_task",
            "finish": "finish",
        },
    )
    builder.add_edge("review_task", "decide_review")
    builder.add_conditional_edges(
        "decide_review",
        route_after_decision,
        {
            "integrate_task": "integrate_task",
            "correct_task": "correct_task",
            "finish": "finish",
        },
    )
    builder.add_conditional_edges(
        "correct_task",
        route_after_execution_step,
        {
            "review_task": "review_task",
            "finish": "finish",
        },
    )
    builder.add_conditional_edges(
        "integrate_task",
        route_after_integration,
        {
            "load_backlog": "load_backlog",
            "finish": "finish",
        },
    )
    builder.add_edge("finish", END)

    return builder.compile(checkpointer=checkpointer)


def load_and_validate_backlog(backlog_json: Path) -> dict[str, Any]:
    try:
        backlog = load_json(backlog_json)
        validate_backlog_consistency(backlog)
    except PlanningError as exc:
        raise RunFeatureError(str(exc)) from exc
    return backlog


def build_initial_state(
    *,
    backlog_json: Path,
    feature_id: str,
    max_corrections: int,
    started_at: datetime,
) -> RunFeatureState:
    return {
        "backlog_path": str(backlog_json),
        "feature_id": feature_id,
        "current_task_id": None,
        "completed_task_ids": [],
        "pending_task_ids": [],
        "correction_count": 0,
        "max_corrections": max_corrections,
        "last_verdict": None,
        "task_action": None,
        "status": "RUNNING",
        "error": None,
        "last_error": None,
        "transition_count": 0,
        "max_transitions": MAX_WORKFLOW_TRANSITIONS,
        "selection_signatures": [],
        "started_at": started_at.isoformat(),
    }


def build_thread_id(feature_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in feature_id)
    return f"run-feature:{safe}"


def reset_invocation_guards(state: RunFeatureState) -> RunFeatureState:
    return {
        **state,
        "selection_signatures": [],
        "transition_count": 0,
        "max_transitions": state.get("max_transitions", MAX_WORKFLOW_TRANSITIONS),
        "last_error": None,
    }


def node_load_backlog(
    state: RunFeatureState,
    *,
    backlog_json: Path,
    progress: ProgressCallback | None,
) -> RunFeatureState:
    guarded = guard_transition(state, "load_backlog")
    if guarded is not None:
        return guarded
    state = advance_transition(state)

    backlog = load_and_validate_backlog(backlog_json)
    repo_root = find_repo_root(backlog_json.parent)
    completed = [
        task["id"]
        for task in backlog["tasks"]
        if is_task_integrated(repo_root, task["id"])
    ]
    pending = [
        task["id"]
        for task in backlog["tasks"]
        if task["id"] not in completed
    ]

    if progress is not None:
        progress(
            f"Chargement backlog {backlog['feature_id']} : {len(completed)} intégrée(s), {len(pending)} restante(s)."
        )

    return {
        "backlog_path": str(backlog_json),
        "feature_id": backlog["feature_id"],
        "completed_task_ids": completed,
        "pending_task_ids": pending,
        "current_task_id": state.get("current_task_id")
        if state.get("current_task_id") in pending
        else None,
        "max_corrections": state.get("max_corrections", 3),
        "correction_count": state.get("correction_count", 0),
        "last_verdict": state.get("last_verdict"),
        "task_action": state.get("task_action"),
        "status": "RUNNING",
        "error": None,
        "last_error": state.get("last_error"),
        "transition_count": state.get("transition_count", 0),
        "max_transitions": state.get("max_transitions", MAX_WORKFLOW_TRANSITIONS),
        "selection_signatures": list(state.get("selection_signatures", [])),
    }


def node_select_next_task(
    state: RunFeatureState,
    *,
    backlog_json: Path,
    progress: ProgressCallback | None,
) -> RunFeatureState:
    if state.get("status") in TERMINAL_STATUSES:
        return state
    guarded = guard_transition(state, "select_next_task")
    if guarded is not None:
        return guarded
    state = advance_transition(state)

    backlog = load_and_validate_backlog(backlog_json)
    repo_root = find_repo_root(backlog_json.parent)
    pending = list(state.get("pending_task_ids", []))
    current_task_id = state.get("current_task_id")
    if current_task_id in pending:
        ready_task_id = current_task_id
    else:
        ready_task_id = select_ready_task(backlog, pending, repo_root)

    if ready_task_id is None:
        if not pending:
            if progress is not None:
                progress("Aucune tâche restante, fonctionnalité terminée.")
            return {
                **state,
                "current_task_id": None,
                "task_action": "COMPLETED",
                "status": "COMPLETED",
                "error": None,
            }

        waiting = ", ".join(pending)
        message = (
            "Aucune tâche exécutable trouvée alors qu'il reste des tâches non intégrées : "
            f"{waiting}."
        )
        if progress is not None:
            progress(message)
        return {**state, "status": "FAILED", "error": message}

    decision = determine_task_resume_action(repo_root=repo_root, task_id=ready_task_id)
    if progress is not None:
        progress(
            f"Tâche sélectionnée : {ready_task_id} "
            f"({len(state.get('completed_task_ids', []))}/{len(backlog['tasks'])} intégrée(s)) "
            f"-> {decision.action}."
        )

    signature_error = state.get("last_error")
    cycle_error = detect_selection_cycle(
        state=state,
        task_id=ready_task_id,
        action=decision.action,
        error=signature_error,
    )
    if cycle_error is not None:
        return fail_state(state, cycle_error, progress)

    next_signatures = list(state.get("selection_signatures", []))
    next_signatures.append(build_selection_signature(ready_task_id, decision.action, signature_error))

    if decision.action == "INVALID_STATE":
        return {
            **state,
            "current_task_id": ready_task_id,
            "task_action": decision.action,
            "status": "FAILED",
            "error": decision.reason,
            "last_error": decision.reason,
            "selection_signatures": next_signatures,
        }

    if decision.action == "HUMAN_REVIEW":
        return {
            **state,
            "current_task_id": ready_task_id,
            "task_action": decision.action,
            "last_verdict": "HUMAN_REVIEW_REQUIRED",
            "status": "HUMAN_REVIEW_REQUIRED",
            "error": decision.reason or f"Revue humaine requise pour {ready_task_id}.",
            "last_error": decision.reason or f"Revue humaine requise pour {ready_task_id}.",
            "selection_signatures": next_signatures,
        }

    return {
        **state,
        "current_task_id": ready_task_id,
        "correction_count": 0,
        "last_verdict": "APPROVED" if decision.action == "INTEGRATE" else None,
        "task_action": decision.action,
        "status": "TASK_SELECTED",
        "error": None,
        "selection_signatures": next_signatures,
    }


def node_run_task(
    state: RunFeatureState,
    *,
    backlog_json: Path,
    run_task_fn: Callable[..., dict[str, Any]],
    progress: ProgressCallback | None,
) -> RunFeatureState:
    guarded = guard_transition(state, "run_task")
    if guarded is not None:
        return guarded
    state = advance_transition(state)
    task_id = require_current_task(state)
    try:
        if progress is not None:
            progress(f"Implémentation lancée : {task_id}.")
        run_task_fn(backlog_json=backlog_json, task_id=task_id)
    except (RunTaskError, RuntimeError) as exc:
        return fail_state(state, str(exc), progress)
    return {**state, "status": "TASK_IMPLEMENTED", "error": None, "last_error": None}


def node_review_task(
    state: RunFeatureState,
    *,
    backlog_json: Path,
    review_task_fn: Callable[..., dict[str, Any]],
    progress: ProgressCallback | None,
) -> RunFeatureState:
    guarded = guard_transition(state, "review_task")
    if guarded is not None:
        return guarded
    state = advance_transition(state)
    task_id = require_current_task(state)
    try:
        if progress is not None:
            progress(f"Validations et revue lancées : {task_id}.")
        result = review_task_fn(backlog_json=backlog_json, task_id=task_id)
    except (ReviewTaskError, RuntimeError) as exc:
        return fail_state(state, str(exc), progress)

    verdict = result.get("verdict")
    if progress is not None:
        progress(f"Verdict Codex : {task_id} -> {verdict}.")
    return {
        **state,
        "last_verdict": str(verdict) if verdict is not None else None,
        "status": "REVIEWED",
        "error": None,
        "last_error": None,
    }


def node_decide_review(
    state: RunFeatureState,
    *,
    progress: ProgressCallback | None,
) -> RunFeatureState:
    guarded = guard_transition(state, "decide_review")
    if guarded is not None:
        return guarded
    state = advance_transition(state)
    verdict = state.get("last_verdict")
    task_id = require_current_task(state)

    if verdict == "APPROVED":
        return {**state, "status": "APPROVED", "error": None, "last_error": None}

    if verdict == "CORRECTION_REQUIRED":
        attempt = state.get("correction_count", 0) + 1
        max_corrections = state.get("max_corrections", 3)
        if attempt > max_corrections:
            message = (
                f"Nombre maximal de corrections dépassé pour {task_id} "
                f"({max_corrections}). Revue humaine requise."
            )
            if progress is not None:
                progress(message)
            return {
                **state,
                "status": "HUMAN_REVIEW_REQUIRED",
                "error": message,
                "last_error": message,
            }
        if progress is not None:
            progress(f"Correction requise #{attempt} pour {task_id}.")
        return {**state, "status": "CORRECTION_REQUIRED", "error": None, "last_error": None}

    if verdict == "HUMAN_REVIEW_REQUIRED":
        message = f"Revue humaine requise pour {task_id}."
        if progress is not None:
            progress(message)
        return {**state, "status": "HUMAN_REVIEW_REQUIRED", "error": message, "last_error": message}

    message = f"Verdict inattendu pour {task_id} : {verdict!r}."
    return fail_state(state, message, progress)


def node_correct_task(
    state: RunFeatureState,
    *,
    backlog_json: Path,
    correct_task_fn: Callable[..., dict[str, Any]],
    progress: ProgressCallback | None,
) -> RunFeatureState:
    guarded = guard_transition(state, "correct_task")
    if guarded is not None:
        return guarded
    state = advance_transition(state)
    task_id = require_current_task(state)
    next_count = state.get("correction_count", 0) + 1
    try:
        if progress is not None:
            progress(f"Correction automatique #{next_count} : {task_id}.")
        correct_task_fn(backlog_json=backlog_json, task_id=task_id)
    except (CorrectTaskError, RuntimeError) as exc:
        return fail_state(state, str(exc), progress)
    return {
        **state,
        "correction_count": next_count,
        "status": "CORRECTED",
        "error": None,
        "last_error": None,
    }


def node_integrate_task(
    state: RunFeatureState,
    *,
    backlog_json: Path,
    integrate_task_fn: Callable[..., dict[str, Any]],
    progress: ProgressCallback | None,
) -> RunFeatureState:
    guarded = guard_transition(state, "integrate_task")
    if guarded is not None:
        return guarded
    state = advance_transition(state)
    task_id = require_current_task(state)
    try:
        if progress is not None:
            progress(f"Intégration : {task_id}.")
        result = integrate_task_fn(backlog_json=backlog_json, task_id=task_id)
    except (IntegrateTaskError, RuntimeError) as exc:
        return fail_state(state, str(exc), progress)
    integration_status = result.get("status")
    if integration_status != "INTEGRATED":
        error = str(result.get("error") or f"Intégration refusée pour {task_id}.")
        if integration_status == "HUMAN_REVIEW_REQUIRED":
            if progress is not None:
                progress(f"Échec du workflow : {error}")
            return {
                **state,
                "status": "HUMAN_REVIEW_REQUIRED",
                "error": error,
                "last_error": error,
            }
        return fail_state(state, error, progress)
    return {
        **state,
        "current_task_id": None,
        "last_verdict": "APPROVED",
        "status": "INTEGRATED",
        "error": None,
        "last_error": None,
    }


def route_after_select(state: RunFeatureState) -> str:
    if state.get("status") in TERMINAL_STATUSES:
        return "finish"
    action = state.get("task_action")
    if action == "IMPLEMENT":
        return "run_task"
    if action in {"REVIEW", "CORRECT"}:
        return "review_task" if action == "REVIEW" else "correct_task"
    if action == "INTEGRATE":
        return "integrate_task"
    return "finish"


def route_after_decision(state: RunFeatureState) -> str:
    status = state.get("status")
    if status == "APPROVED":
        return "integrate_task"
    if status == "CORRECTION_REQUIRED":
        return "correct_task"
    return "finish"


def route_after_execution_step(state: RunFeatureState) -> str:
    if state.get("status") == "FAILED":
        return "finish"
    return "review_task"


def route_after_integration(state: RunFeatureState) -> str:
    if state.get("status") == "INTEGRATED":
        return "load_backlog"
    return "finish"


def select_ready_task(
    backlog: dict[str, Any],
    pending_task_ids: list[str],
    repo_root: Path,
) -> str | None:
    tasks_by_id = {task["id"]: task for task in backlog["tasks"]}
    for task_id in pending_task_ids:
        task = tasks_by_id[task_id]
        if not get_unfinished_dependencies(repo_root, task):
            return task_id
    return None


def require_current_task(state: RunFeatureState) -> str:
    task_id = state.get("current_task_id")
    if not task_id:
        raise RuntimeError("Aucune tâche courante dans l'état du graphe.")
    return task_id


def fail_state(state: RunFeatureState, error: str, progress: ProgressCallback | None) -> RunFeatureState:
    if progress is not None:
        progress(f"Échec du workflow : {error}")
    return {**state, "status": "FAILED", "error": error, "last_error": error}


def build_terminal_state(
    *,
    state: RunFeatureState,
    status: str,
    error: str | None,
) -> RunFeatureState:
    return {
        **state,
        "status": status,
        "error": error,
        "last_error": error,
    }


def advance_transition(state: RunFeatureState) -> RunFeatureState:
    return {
        **state,
        "transition_count": state.get("transition_count", 0) + 1,
        "max_transitions": state.get("max_transitions", MAX_WORKFLOW_TRANSITIONS),
    }


def guard_transition(state: RunFeatureState, node_name: str) -> RunFeatureState | None:
    next_count = state.get("transition_count", 0) + 1
    max_transitions = state.get("max_transitions", MAX_WORKFLOW_TRANSITIONS)
    if next_count > max_transitions:
        message = f"Nombre maximal de transitions atteint ({max_transitions}) avant {node_name}."
        return {
            **state,
            "status": "FAILED",
            "error": message,
            "last_error": message,
            "transition_count": next_count,
        }
    return None


def build_selection_signature(task_id: str, action: str, error: str | None) -> str:
    return f"{task_id}|{action}|{error or ''}"


def detect_selection_cycle(
    *,
    state: RunFeatureState,
    task_id: str,
    action: str,
    error: str | None,
) -> str | None:
    signature = build_selection_signature(task_id, action, error)
    if signature in state.get("selection_signatures", []):
        return f"Cycle de workflow détecté pour {task_id} à l'étape {action}."
    return None


def determine_task_resume_action(*, repo_root: Path, task_id: str) -> ResumeDecision:
    run_dir = repo_root / ".autodev" / "runs" / task_id
    integration_result = load_optional_json(run_dir / "integration" / "integration-result.json")
    integration_status = integration_result.get("status")
    if integration_status == "INTEGRATED":
        return ResumeDecision("COMPLETED", "Tâche déjà intégrée.")

    review_result = load_optional_json(run_dir / "review" / "review-result.json")
    review_verdict = review_result.get("verdict")

    branch = f"autodev/{task_id}"
    branch_present = branch_exists(repo_root, branch)
    worktree = resolve_task_worktree(repo_root=repo_root, task_id=task_id, run_dir=run_dir)
    worktree_exists = worktree.exists()
    worktree_present = worktree_exists or worktree_registered(repo_root, worktree)
    produced_commit = resolve_resume_produced_commit(
        repo_root=repo_root,
        task_id=task_id,
        branch=branch,
        run_dir=run_dir,
        branch_present=branch_present,
        worktree=worktree,
        worktree_exists=worktree_exists,
    )

    if not branch_present and not worktree_present:
        return ResumeDecision("IMPLEMENT", "Aucun artefact Git détecté.")
    if branch_present and not worktree_present:
        return ResumeDecision(
            "INVALID_STATE",
            f"État incohérent pour {task_id} : branche présente mais worktree absent.",
        )
    if worktree_present and not branch_present:
        return ResumeDecision(
            "INVALID_STATE",
            f"État incohérent pour {task_id} : worktree présent mais branche absente.",
        )

    if review_verdict == "APPROVED":
        if produced_commit is None:
            return ResumeDecision(
                "INVALID_STATE",
                f"État incohérent pour {task_id} : revue APPROVED sans commit produit.",
            )
        return ResumeDecision("INTEGRATE", "Revue approuvée, intégration à relancer.")

    if review_verdict == "CORRECTION_REQUIRED":
        if not worktree_exists:
            return ResumeDecision(
                "INVALID_STATE",
                f"État incohérent pour {task_id} : correction requise mais worktree introuvable.",
            )
        return ResumeDecision("CORRECT", "Correction automatique à reprendre.")

    if review_verdict == "HUMAN_REVIEW_REQUIRED":
        return ResumeDecision("HUMAN_REVIEW", f"Revue humaine requise pour {task_id}.")

    if review_verdict is not None:
        return ResumeDecision(
            "INVALID_STATE",
            f"Verdict de revue invalide pour {task_id} : {review_verdict!r}.",
        )

    if produced_commit is not None:
        return ResumeDecision("REVIEW", "Implémentation détectée, revue à lancer.")

    return ResumeDecision(
        "INVALID_STATE",
        (
            f"Implémentation incomplète pour {task_id} : branche/worktree existants "
            "mais aucun commit produit détecté."
        ),
    )


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return load_json(path)
    except PlanningError as exc:
        raise RunFeatureError(str(exc)) from exc


def resolve_task_worktree(*, repo_root: Path, task_id: str, run_dir: Path) -> Path:
    _, run_result, task_record = resolve_task_metadata(repo_root, task_id)
    return resolve_worktree(repo_root, task_id, run_result, task_record)


def resolve_resume_produced_commit(
    *,
    repo_root: Path,
    task_id: str,
    branch: str,
    run_dir: Path,
    branch_present: bool,
    worktree: Path,
    worktree_exists: bool,
) -> str | None:
    run_result = load_optional_json(run_dir / "result.json")
    produced_commit = run_result.get("produced_commit")
    if isinstance(produced_commit, str) and produced_commit.strip():
        return produced_commit

    try:
        _, _, task_record = resolve_task_metadata(repo_root, task_id)
        base_commit = resolve_base_commit(task_id, run_result, task_record)
    except GitContextError:
        return None

    try:
        if branch_present and count_commits_between(repo_root, base_commit, branch) > 0:
            return branch_head(repo_root, branch)
        if worktree_exists and count_commits_between(repo_root, base_commit, "HEAD", cwd=worktree) > 0:
            return git_output(repo_root, ["rev-parse", "HEAD"], cwd=worktree)
    except GitError as exc:
        raise RunFeatureError(str(exc)) from exc

    return None


def count_commits_between(
    repo_root: Path,
    base_commit: str,
    end_ref: str,
    *,
    cwd: Path | None = None,
) -> int:
    try:
        count = git_output(repo_root, ["rev-list", "--count", f"{base_commit}..{end_ref}"], cwd=cwd)
    except GitError as exc:
        raise RunFeatureError(str(exc)) from exc
    return int(count)


def write_run_summary(
    *,
    repo_root: Path,
    run_dir: Path,
    checkpoints_path: Path,
    state: RunFeatureState,
    started_at: datetime,
) -> dict[str, Any]:
    backlog_path = Path(state["backlog_path"])
    backlog = load_and_validate_backlog(backlog_path)
    repo_root = find_repo_root(backlog_path.parent)
    completed = [
        task["id"]
        for task in backlog["tasks"]
        if is_task_integrated(repo_root, task["id"])
    ]
    pending = [
        task["id"]
        for task in backlog["tasks"]
        if task["id"] not in completed
    ]
    summary = {
        "feature_id": state["feature_id"],
        "tasks_integrated": completed,
        "tasks_remaining": pending,
        "status": state.get("status", "FAILED"),
        "error": state.get("error"),
        "current_task_id": state.get("current_task_id"),
        "last_verdict": state.get("last_verdict"),
        "correction_count": state.get("correction_count", 0),
        "max_corrections": state.get("max_corrections", 3),
        "checkpoints_path": str(checkpoints_path),
        "reports_path": str(run_dir),
        "started_at": state.get("started_at", started_at.isoformat()),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(run_dir / "run-feature-result.json", summary)
    write_json(run_dir / "last-state.json", state)
    if summary["status"] == "COMPLETED":
        write_feature_final_reports(repo_root=repo_root, backlog=backlog, run_dir=run_dir, summary=summary)
    return summary


def write_feature_final_reports(
    *,
    repo_root: Path,
    backlog: dict[str, Any],
    run_dir: Path,
    summary: dict[str, Any],
) -> None:
    tasks_payload: list[dict[str, Any]] = []
    for task in backlog["tasks"]:
        task_id = task["id"]
        task_run_dir = repo_root / ".autodev" / "runs" / task_id
        result = load_optional_json(task_run_dir / "result.json")
        review = load_optional_json(task_run_dir / "review" / "review-result.json")
        integration = load_optional_json(task_run_dir / "integration" / "integration-result.json")
        corrections_dir = task_run_dir / "corrections"
        correction_count = len([child for child in corrections_dir.iterdir() if child.is_dir()]) if corrections_dir.is_dir() else 0
        tasks_payload.append(
            {
                "task_id": task_id,
                "title": task["title"],
                "branch": f"autodev/{task_id}",
                "produced_commit": result.get("produced_commit"),
                "integration_commit": integration.get("integration_commit"),
                "review_verdict": review.get("verdict"),
                "integration_status": integration.get("status"),
                "correction_count": correction_count,
                "validations": result.get("validation_summary", []),
                "delivered_files": result.get("modified_paths", []),
            }
        )

    final_report = {
        "feature_id": backlog["feature_id"],
        "feature_title": backlog["feature_title"],
        "specification_path": backlog.get("specification_path", "SPEC.md"),
        "summary": backlog["summary"],
        "tasks": tasks_payload,
        "status": summary["status"],
        "started_at": summary["started_at"],
        "finished_at": summary["finished_at"],
        "tasks_integrated": summary["tasks_integrated"],
        "tasks_remaining": summary["tasks_remaining"],
        "baseline_comparison": "Voir les artefacts d'intégration de chaque tâche.",
        "incidents": [item for item in [summary.get("error")] if item],
        "business_files_delivered": sorted(
            {
                path
                for task in tasks_payload
                for path in task["delivered_files"]
                if not str(path).startswith("autodev/")
            }
        ),
    }
    write_json(run_dir / "final-report.json", final_report)
    report_path = repo_root / "reports" / "dev" / f"{backlog['feature_id']}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {backlog['feature_id']}",
        "",
        f"- spécification source : `{final_report['specification_path']}`",
        f"- statut final : `{final_report['status']}`",
        f"- tâches intégrées : {', '.join(summary['tasks_integrated']) or '—'}",
        f"- corrections totales : {sum(task['correction_count'] for task in tasks_payload)}",
        f"- fichiers métier livrés : {', '.join(final_report['business_files_delivered']) or '—'}",
        "",
        "## Tâches",
        "",
    ]
    for task in tasks_payload:
        lines.extend(
            [
                f"- `{task['task_id']}` : verdict `{task['review_verdict']}`, intégration `{task['integration_status']}`, corrections `{task['correction_count']}`",
            ]
        )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_checkpoint_state(graph: Any, config: dict[str, Any]) -> RunFeatureState | None:
    snapshot = graph.get_state(config)
    values = getattr(snapshot, "values", None)
    if not values:
        return None
    return dict(values)
