from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from autodev.monitor_state import MonitorStateError, read_feature_state

STATUS_STYLES = {
    "PENDING": "white",
    "READY": "cyan",
    "IMPLEMENTING": "yellow",
    "REVIEWING": "magenta",
    "CORRECTING": "bright_yellow",
    "APPROVED": "green",
    "INTEGRATING": "blue",
    "INTEGRATED": "green",
    "FAILED": "red",
    "TIMEOUT": "red",
    "HUMAN_REVIEW_REQUIRED": "bold red",
    "COMPLETED": "green",
    "NOT_STARTED": "white",
}


def monitor_feature(
    backlog_json: Path,
    *,
    refresh: float = 2.0,
    once: bool = False,
    include_logs: bool = False,
    log_lines: int = 20,
    no_clear: bool = False,
    console: Console | None = None,
    sleep_fn: Any = time.sleep,
) -> None:
    target_console = console or Console()
    if once:
        model = read_feature_state(backlog_json, include_logs=include_logs, log_lines=log_lines)
        target_console.print(render_monitor(model))
        return

    while True:
        try:
            model = read_feature_state(backlog_json, include_logs=include_logs, log_lines=log_lines)
            if not no_clear:
                target_console.clear()
            target_console.print(render_monitor(model))
            sleep_fn(refresh)
        except KeyboardInterrupt:
            return


def render_monitor(model: dict[str, Any]) -> Group:
    sections = [
        render_feature_summary(model),
        render_current_task(model["current_task"]),
        render_tasks_table(model["tasks"]),
    ]
    if model["logs"]:
        sections.append(render_logs(model["logs"]))
    return Group(*sections)


def render_feature_summary(model: dict[str, Any]) -> Panel:
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Feature", model["feature_id"])
    summary.add_row("Titre", model["feature_title"])
    summary.add_row("État", style_status(model["feature_status"]))
    summary.add_row(
        "Progression",
        f'{model["progress"]["integrated"]}/{model["progress"]["total"]} ({model["progress"]["percentage"]}%)',
    )
    summary.add_row(
        "Couverture critères",
        (
            f'{model["coverage"]["summary"]["approved"]}/{model["coverage"]["summary"]["total"]} '
            f'({model["coverage"]["summary"]["coverage_percentage"]}%)'
        ),
    )
    summary.add_row("Critères intégrés", str(model["coverage"]["summary"]["integrated"]))
    summary.add_row("Tâche courante", model["current_task_id"])
    summary.add_row("Action courante", model["current_action"])
    summary.add_row("Dernière mise à jour", model["last_updated"])
    summary.add_row("Checkpoints", model["checkpoints_path"])
    summary.add_row("Rapports", model["reports_path"])
    summary.add_row("Intervention requise", str(model["intervention_required"]))
    return Panel(summary, title="Feature", border_style="cyan")


def render_current_task(current_task: dict[str, Any]) -> Panel:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Task", str(current_task["task_id"]))
    table.add_row("Action", str(current_task["task_action"]))
    table.add_row("Statut", style_status(str(current_task["status"])))
    table.add_row("Corrections", str(current_task["correction_count"]))
    table.add_row("Erreur", str(current_task["last_error"]))
    table.add_row("Started at", str(current_task["started_at"]))
    table.add_row("Elapsed", str(current_task["elapsed_seconds"]))
    git_state = current_task.get("git", {})
    table.add_row("Branche", str(git_state.get("branch", "—")))
    table.add_row("Worktree", str(git_state.get("worktree", "—")))
    table.add_row("HEAD", str(git_state.get("head") or "—"))
    table.add_row("Fichiers modifiés", str(git_state.get("modified_count", "—")))
    table.add_row("Worktree sale", format_dirty(git_state.get("is_dirty")))
    if git_state.get("modified_paths"):
        table.add_row("Chemins", ", ".join(git_state["modified_paths"]))
    return Panel(table, title="Tâche Courante", border_style="magenta")


def render_tasks_table(tasks: list[dict[str, Any]]) -> Table:
    table = Table(title="Tâches", expand=True)
    table.add_column("ID", no_wrap=True)
    table.add_column("Agent", no_wrap=True)
    table.add_column("Titre")
    table.add_column("Deps")
    table.add_column("État", no_wrap=True)
    table.add_column("Crit.", justify="right", no_wrap=True)
    table.add_column("OK", justify="right", no_wrap=True)
    table.add_column("Action")
    table.add_column("Review", no_wrap=True)
    table.add_column("Corr.", justify="right", no_wrap=True)
    table.add_column("Branche")
    table.add_column("Worktree", no_wrap=True)
    table.add_column("Commit")
    table.add_column("Intégration", no_wrap=True)
    table.add_column("Erreur")
    for task in tasks:
        table.add_row(
            task["task_id"],
            task["agent"],
            task["title"],
            task["depends_on"],
            style_status(task["status"]),
            str(task["owned_criteria"]),
            str(task["approved_criteria"]),
            task["action_current"],
            task["review_verdict"],
            str(task["correction_count"]),
            task["branch"],
            task["worktree_exists"],
            shorten_commit(task["produced_commit"]),
            task["integration_status"],
            task["last_error"],
        )
    return table


def render_logs(logs: list[dict[str, Any]]) -> Panel:
    body = Table.grid()
    body.add_column()
    for entry in logs:
        lines = "\n".join(entry["lines"]) if entry["lines"] else "—"
        body.add_row(Text(f"[{entry['label']}]\n{lines}"))
    return Panel(body, title="Logs", border_style="yellow")


def style_status(status: str) -> Text:
    return Text(status, style=STATUS_STYLES.get(status, "white"))


def shorten_commit(value: str) -> str:
    if value in {"—", ""}:
        return "—"
    return value[:12]


def format_dirty(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "—"
