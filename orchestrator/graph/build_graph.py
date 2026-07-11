from __future__ import annotations

from pathlib import Path
import sqlite3
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from orchestrator.graph.state import OrchestratorState, initial_state, make_event
from orchestrator.models.task import QAResult, Task, TaskStatus
from orchestrator.runners.qa_runner import QARunner
from orchestrator.storage.task_store import TaskStore


def create_sqlite_checkpointer(db_path: str | Path) -> SqliteSaver:
    connection = sqlite3.connect(str(db_path), check_same_thread=False)
    return SqliteSaver(connection)


def build_orchestrator_graph(
    *,
    task_store: TaskStore,
    qa_runner: QARunner | None = None,
    max_parallel_tasks: int = 1,
    checkpointer: SqliteSaver | None = None,
):
    qa_runner = qa_runner or QARunner()
    graph = StateGraph(OrchestratorState)

    def load_backlog(state: OrchestratorState) -> OrchestratorState:
        tasks = task_store.load_tasks()
        pending = [task for task in tasks if task.status == TaskStatus.PENDING]
        completed = [task for task in tasks if task.status in {TaskStatus.COMPLETED, TaskStatus.APPROVED}]
        failed = [task for task in tasks if task.status == TaskStatus.FAILED]
        blocked = [task for task in tasks if task.status in {TaskStatus.BLOCKED, TaskStatus.REJECTED}]
        return {
            "phase": "load_backlog",
            "pending_tasks": pending,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "blocked_tasks": blocked,
            "event_log": [make_event("load_backlog", f"Loaded {len(tasks)} tasks from backlog.")],
        }

    def select_tasks(state: OrchestratorState) -> OrchestratorState:
        selected = state.get("pending_tasks", [])[:max_parallel_tasks]
        return {
            "phase": "select_tasks",
            "current_task_ids": [task.id for task in selected],
            "running_tasks": selected,
            "event_log": [make_event("select_tasks", f"Selected {len(selected)} task(s).")],
        }

    def create_worktrees(state: OrchestratorState) -> OrchestratorState:
        updated: list[Task] = []
        for task in state.get("running_tasks", []):
            worktree_path = task.worktree_path or f"worktrees/{task.id}"
            updated.append(
                task.model_copy(
                    update={
                        "branch_name": task.branch_name or f"task/{task.id}",
                        "worktree_path": worktree_path,
                        "status": TaskStatus.RUNNING,
                    }
                )
            )
        return {
            "phase": "create_worktrees",
            "running_tasks": updated,
            "event_log": [make_event("create_worktrees", "Prepared worktree assignments for selected tasks.")],
        }

    def dispatch_agents(state: OrchestratorState) -> OrchestratorState:
        return {
            "phase": "dispatch_agents",
            "event_log": [make_event("dispatch_agents", "Dispatch plan prepared for development agents.")],
        }

    def collect_results(state: OrchestratorState) -> OrchestratorState:
        running = state.get("running_tasks", [])
        return {
            "phase": "collect_results",
            "completed_tasks": running,
            "running_tasks": [],
            "event_log": [make_event("collect_results", f"Collected {len(running)} mocked agent result(s).")],
        }

    def qa_review(state: OrchestratorState) -> OrchestratorState:
        results: list[QAResult] = []
        for task in state.get("completed_tasks", []):
            if task.status == TaskStatus.REJECTED:
                continue
            results.append(
                qa_runner.run(
                    task_id=task.id,
                    prompt=f"Review task {task.id}: {task.title}",
                    cwd=task.worktree_path or ".",
                )
            )
        return {
            "phase": "qa_review",
            "qa_results": results,
            "event_log": [make_event("qa_review", f"Generated {len(results)} QA result(s).")],
        }

    def route_accepted_or_rejected(state: OrchestratorState) -> OrchestratorState:
        needs_human = any(result.status != "accepted" for result in state.get("qa_results", []))
        return {
            "phase": "route_accepted_or_rejected",
            "human_approval_required": needs_human,
            "event_log": [make_event("route_accepted_or_rejected", f"Human approval required: {needs_human}.")],
        }

    def request_human_merge_approval(state: OrchestratorState) -> OrchestratorState:
        return {
            "phase": "request_human_merge_approval",
            "event_log": [make_event("request_human_merge_approval", "Waiting for human merge approval.")],
        }

    def decide_next_step(state: OrchestratorState) -> str:
        return "request_human_merge_approval" if state.get("human_approval_required", False) else END

    graph.add_node("load_backlog", load_backlog)
    graph.add_node("select_tasks", select_tasks)
    graph.add_node("create_worktrees", create_worktrees)
    graph.add_node("dispatch_agents", dispatch_agents)
    graph.add_node("collect_results", collect_results)
    graph.add_node("qa_review", qa_review)
    graph.add_node("route_accepted_or_rejected", route_accepted_or_rejected)
    graph.add_node("request_human_merge_approval", request_human_merge_approval)

    graph.add_edge(START, "load_backlog")
    graph.add_edge("load_backlog", "select_tasks")
    graph.add_edge("select_tasks", "create_worktrees")
    graph.add_edge("create_worktrees", "dispatch_agents")
    graph.add_edge("dispatch_agents", "collect_results")
    graph.add_edge("collect_results", "qa_review")
    graph.add_edge("qa_review", "route_accepted_or_rejected")
    graph.add_conditional_edges(
        "route_accepted_or_rejected",
        decide_next_step,
        {
            "request_human_merge_approval": "request_human_merge_approval",
            END: END,
        },
    )
    graph.add_edge("request_human_merge_approval", END)

    return graph.compile(checkpointer=checkpointer)


def build_initial_run_state(run_id: str | None = None) -> OrchestratorState:
    return initial_state(run_id or str(uuid4()))
