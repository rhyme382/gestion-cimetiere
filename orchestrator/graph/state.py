from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal, TypedDict
import operator

from orchestrator.models.task import QAResult, Task

OrchestratorPhase = Literal[
    "idle",
    "load_backlog",
    "select_tasks",
    "create_worktrees",
    "dispatch_agents",
    "collect_results",
    "qa_review",
    "route_accepted_or_rejected",
    "request_human_merge_approval",
    "completed",
    "error",
]


class EventLogEntry(TypedDict):
    timestamp: str
    phase: str
    message: str
    level: Literal["info", "warning", "error"]


class OrchestratorState(TypedDict, total=False):
    run_id: str
    phase: OrchestratorPhase
    current_task_ids: list[str]
    pending_tasks: list[Task]
    running_tasks: list[Task]
    completed_tasks: list[Task]
    failed_tasks: list[Task]
    blocked_tasks: list[Task]
    qa_results: list[QAResult]
    human_approval_required: bool
    last_error: str | None
    event_log: Annotated[list[EventLogEntry], operator.add]


def make_event(
    phase: str,
    message: str,
    *,
    level: Literal["info", "warning", "error"] = "info",
) -> EventLogEntry:
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "phase": phase,
        "message": message,
        "level": level,
    }


def initial_state(run_id: str) -> OrchestratorState:
    return {
        "run_id": run_id,
        "phase": "idle",
        "current_task_ids": [],
        "pending_tasks": [],
        "running_tasks": [],
        "completed_tasks": [],
        "failed_tasks": [],
        "blocked_tasks": [],
        "qa_results": [],
        "human_approval_required": False,
        "last_error": None,
        "event_log": [make_event("idle", "Orchestrator state initialized.")],
    }
