from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from autodev.correct_task import CorrectTaskError, correct_task as correct_single_task
from autodev.integrate_task import IntegrateTaskError, integrate_task as integrate_single_task
from autodev.planner import PlanningError, find_repo_root, load_json, validate_backlog_consistency
from autodev.review_task import ReviewTaskError, review_task as review_single_task
from autodev.task_runner import RunTaskError, run_task as run_single_task, write_json

TERMINAL_STATUSES = {"COMPLETED", "FAILED", "HUMAN_REVIEW_REQUIRED", "INTERRUPTED"}


class RunFeatureError(RuntimeError):
    """Erreur pendant l'exécution d'une fonctionnalité complète."""


class RunFeatureState(TypedDict, total=False):
    backlog_path: str
    feature_id: str
    current_task_id: str | None
    completed_task_ids: list[str]
    pending_task_ids: list[str]
    correction_count: int
    max_corrections: int
    last_verdict: str | None
    status: str
    error: str | None


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
            initial_state = existing
        else:
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
            )
            raise RunFeatureError(str(exc)) from exc

    summary = write_run_summary(
        repo_root=repo_root,
        run_dir=run_dir,
        checkpoints_path=checkpoints_path,
        state=final_state,
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
    builder.add_edge("integrate_task", "load_backlog")
    builder.add_edge("finish", END)

    return builder.compile(checkpointer=checkpointer)


def load_and_validate_backlog(backlog_json: Path) -> dict[str, Any]:
    try:
        backlog = load_json(backlog_json)
        validate_backlog_consistency(backlog)
    except PlanningError as exc:
        raise RunFeatureError(str(exc)) from exc
    return backlog


def build_initial_state(*, backlog_json: Path, feature_id: str, max_corrections: int) -> RunFeatureState:
    return {
        "backlog_path": str(backlog_json),
        "feature_id": feature_id,
        "current_task_id": None,
        "completed_task_ids": [],
        "pending_task_ids": [],
        "correction_count": 0,
        "max_corrections": max_corrections,
        "last_verdict": None,
        "status": "RUNNING",
        "error": None,
    }


def build_thread_id(feature_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in feature_id)
    return f"run-feature:{safe}"


def node_load_backlog(
    state: RunFeatureState,
    *,
    backlog_json: Path,
    progress: ProgressCallback | None,
) -> RunFeatureState:
    backlog = load_and_validate_backlog(backlog_json)
    completed = [
        task["id"]
        for task in backlog["tasks"]
        if is_task_integrated(backlog_json, task["id"])
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
        "status": "RUNNING",
        "error": None,
    }


def node_select_next_task(
    state: RunFeatureState,
    *,
    backlog_json: Path,
    progress: ProgressCallback | None,
) -> RunFeatureState:
    if state.get("status") in TERMINAL_STATUSES:
        return state

    backlog = load_and_validate_backlog(backlog_json)
    pending = list(state.get("pending_task_ids", []))
    ready_task_id = select_ready_task(backlog, pending, backlog_json)

    if ready_task_id is None:
        if not pending:
            if progress is not None:
                progress("Aucune tâche restante, fonctionnalité terminée.")
            return {**state, "current_task_id": None, "status": "COMPLETED", "error": None}

        waiting = ", ".join(pending)
        message = (
            "Aucune tâche exécutable trouvée alors qu'il reste des tâches non intégrées : "
            f"{waiting}."
        )
        if progress is not None:
            progress(message)
        return {**state, "status": "FAILED", "error": message}

    if progress is not None:
        progress(
            f"Tâche sélectionnée : {ready_task_id} "
            f"({len(state.get('completed_task_ids', []))}/{len(backlog['tasks'])} intégrée(s))."
        )

    return {
        **state,
        "current_task_id": ready_task_id,
        "correction_count": 0,
        "last_verdict": None,
        "status": "TASK_SELECTED",
        "error": None,
    }


def node_run_task(
    state: RunFeatureState,
    *,
    backlog_json: Path,
    run_task_fn: Callable[..., dict[str, Any]],
    progress: ProgressCallback | None,
) -> RunFeatureState:
    task_id = require_current_task(state)
    try:
        if progress is not None:
            progress(f"Implémentation lancée : {task_id}.")
        run_task_fn(backlog_json=backlog_json, task_id=task_id)
    except (RunTaskError, RuntimeError) as exc:
        return fail_state(state, str(exc), progress)
    return {**state, "status": "TASK_IMPLEMENTED", "error": None}


def node_review_task(
    state: RunFeatureState,
    *,
    backlog_json: Path,
    review_task_fn: Callable[..., dict[str, Any]],
    progress: ProgressCallback | None,
) -> RunFeatureState:
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
    }


def node_decide_review(
    state: RunFeatureState,
    *,
    progress: ProgressCallback | None,
) -> RunFeatureState:
    verdict = state.get("last_verdict")
    task_id = require_current_task(state)

    if verdict == "APPROVED":
        return {**state, "status": "APPROVED", "error": None}

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
            }
        if progress is not None:
            progress(f"Correction requise #{attempt} pour {task_id}.")
        return {**state, "status": "CORRECTION_REQUIRED", "error": None}

    if verdict == "HUMAN_REVIEW_REQUIRED":
        message = f"Revue humaine requise pour {task_id}."
        if progress is not None:
            progress(message)
        return {**state, "status": "HUMAN_REVIEW_REQUIRED", "error": message}

    message = f"Verdict inattendu pour {task_id} : {verdict!r}."
    return fail_state(state, message, progress)


def node_correct_task(
    state: RunFeatureState,
    *,
    backlog_json: Path,
    correct_task_fn: Callable[..., dict[str, Any]],
    progress: ProgressCallback | None,
) -> RunFeatureState:
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
    }


def node_integrate_task(
    state: RunFeatureState,
    *,
    backlog_json: Path,
    integrate_task_fn: Callable[..., dict[str, Any]],
    progress: ProgressCallback | None,
) -> RunFeatureState:
    task_id = require_current_task(state)
    try:
        if progress is not None:
            progress(f"Intégration : {task_id}.")
        integrate_task_fn(backlog_json=backlog_json, task_id=task_id)
    except (IntegrateTaskError, RuntimeError) as exc:
        return fail_state(state, str(exc), progress)
    return {
        **state,
        "current_task_id": None,
        "last_verdict": "APPROVED",
        "status": "INTEGRATED",
        "error": None,
    }


def route_after_select(state: RunFeatureState) -> str:
    if state.get("status") in TERMINAL_STATUSES:
        return "finish"
    return "run_task"


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


def select_ready_task(
    backlog: dict[str, Any],
    pending_task_ids: list[str],
    backlog_json: Path,
) -> str | None:
    tasks_by_id = {task["id"]: task for task in backlog["tasks"]}
    for task_id in pending_task_ids:
        task = tasks_by_id[task_id]
        if all(is_task_integrated(backlog_json, dep_id) for dep_id in task["depends_on"]):
            return task_id
    return None


def is_task_integrated(backlog_json: Path, task_id: str) -> bool:
    repo_root = find_repo_root(backlog_json.parent)
    path = repo_root / ".autodev" / "runs" / task_id / "integration" / "integration-result.json"
    if not path.is_file():
        return False
    try:
        payload = load_json(path)
    except PlanningError:
        return False
    return payload.get("status") == "INTEGRATED"


def require_current_task(state: RunFeatureState) -> str:
    task_id = state.get("current_task_id")
    if not task_id:
        raise RuntimeError("Aucune tâche courante dans l'état du graphe.")
    return task_id


def fail_state(state: RunFeatureState, error: str, progress: ProgressCallback | None) -> RunFeatureState:
    if progress is not None:
        progress(f"Échec du workflow : {error}")
    return {**state, "status": "FAILED", "error": error}


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
    }


def write_run_summary(
    *,
    repo_root: Path,
    run_dir: Path,
    checkpoints_path: Path,
    state: RunFeatureState,
) -> dict[str, Any]:
    backlog_path = Path(state["backlog_path"])
    backlog = load_and_validate_backlog(backlog_path)
    completed = [
        task["id"]
        for task in backlog["tasks"]
        if is_task_integrated(backlog_path, task["id"])
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
    }
    write_json(run_dir / "run-feature-result.json", summary)
    write_json(run_dir / "last-state.json", state)
    return summary


def load_checkpoint_state(graph: Any, config: dict[str, Any]) -> RunFeatureState | None:
    snapshot = graph.get_state(config)
    values = getattr(snapshot, "values", None)
    if not values:
        return None
    return dict(values)
