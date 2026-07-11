from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import uuid4

import yaml

from orchestrator.graph.build_graph import build_initial_run_state, build_orchestrator_graph, create_sqlite_checkpointer
from orchestrator.models.task import TaskStatus
from orchestrator.storage.task_store import TaskStore


DEFAULT_BACKLOG_PATH = Path("orchestrator/runtime/backlog.json")
DEFAULT_DB_PATH = Path("orchestrator/runtime/langgraph.sqlite")
DEFAULT_CONFIG_PATH = Path("orchestrator/config.yaml")


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gestion-cimetiere-orchestrator")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--backlog", default=str(DEFAULT_BACKLOG_PATH))
    init_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))

    for name in ("audit", "run", "resume", "status", "cleanup"):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("--backlog", default=str(DEFAULT_BACKLOG_PATH))
        command_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))

    for name in ("approve", "reject"):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("task_id")
        command_parser.add_argument("--backlog", default=str(DEFAULT_BACKLOG_PATH))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    command = args.command

    if command == "init":
        return command_init(Path(args.backlog), Path(args.db), config)
    if command == "audit":
        return command_audit(Path(args.backlog), Path(args.db), config)
    if command == "run":
        return command_run(Path(args.backlog), Path(args.db), config)
    if command == "resume":
        return command_resume(Path(args.backlog), Path(args.db), config)
    if command == "status":
        return command_status(Path(args.backlog), Path(args.db), config)
    if command == "approve":
        return command_set_status(Path(args.backlog), args.task_id, TaskStatus.APPROVED)
    if command == "reject":
        return command_set_status(Path(args.backlog), args.task_id, TaskStatus.REJECTED)
    if command == "cleanup":
        return command_cleanup(Path(args.backlog), Path(args.db))
    parser.error(f"Unknown command: {command}")
    return 2


def command_init(backlog_path: Path, db_path: Path, config: dict) -> int:
    backlog_store = TaskStore(backlog_path)
    if not backlog_store.exists():
        backlog_store.save_tasks([])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.touch(exist_ok=True)
    output = {
        "status": "initialized",
        "backlog_path": str(backlog_path),
        "db_path": str(db_path),
        "project": config.get("project", {}),
    }
    print(json.dumps(output, ensure_ascii=True))
    return 0


def command_audit(backlog_path: Path, db_path: Path, config: dict) -> int:
    tasks = TaskStore(backlog_path).load_tasks()
    output = {
        "status": "ok",
        "backlog_exists": backlog_path.exists(),
        "db_exists": db_path.exists(),
        "task_count": len(tasks),
        "max_parallel_agents": config.get("execution", {}).get("max_parallel_agents"),
    }
    print(json.dumps(output, ensure_ascii=True))
    return 0


def command_run(backlog_path: Path, db_path: Path, config: dict) -> int:
    store = TaskStore(backlog_path)
    graph = build_orchestrator_graph(
        task_store=store,
        max_parallel_tasks=config.get("execution", {}).get("max_parallel_agents", 1),
        checkpointer=create_sqlite_checkpointer(db_path),
    )
    run_id = str(uuid4())
    result = graph.invoke(
        build_initial_run_state(run_id),
        config={"configurable": {"thread_id": run_id}},
    )
    print(json.dumps({"status": "completed", "run_id": run_id, "phase": result.get("phase")}, ensure_ascii=True))
    return 0


def command_resume(backlog_path: Path, db_path: Path, config: dict) -> int:
    return command_run(backlog_path, db_path, config)


def command_status(backlog_path: Path, db_path: Path, config: dict) -> int:
    tasks = TaskStore(backlog_path).load_tasks()
    counts = {status.value: 0 for status in TaskStatus}
    for task in tasks:
        counts[task.status.value] += 1
    output = {
        "backlog_path": str(backlog_path),
        "db_path": str(db_path),
        "task_counts": counts,
        "project": config.get("project", {}),
    }
    print(json.dumps(output, ensure_ascii=True))
    return 0


def command_set_status(backlog_path: Path, task_id: str, status: TaskStatus) -> int:
    store = TaskStore(backlog_path)
    tasks = store.load_tasks()
    for index, task in enumerate(tasks):
        if task.id == task_id:
            tasks[index] = task.model_copy(update={"status": status})
            store.save_tasks(tasks)
            print(json.dumps({"task_id": task_id, "status": status.value}, ensure_ascii=True))
            return 0
    print(json.dumps({"task_id": task_id, "status": "not_found"}, ensure_ascii=True))
    return 1


def command_cleanup(backlog_path: Path, db_path: Path) -> int:
    removed = []
    for path in (backlog_path, db_path):
        if path.exists():
            path.unlink()
            removed.append(str(path))
    print(json.dumps({"status": "cleaned", "removed": removed}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
