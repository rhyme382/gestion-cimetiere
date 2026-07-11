from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import uuid4

import yaml

from orchestrator.audit import (
    AUDIT_STATUSES,
    archive_existing_outputs,
    build_audit_prompt,
    collect_source_inventory,
    detect_repo_root,
    detect_unauthorized_changes,
    ensure_outputs_absent,
    required_output_paths,
    resolve_output_root,
    snapshot_git_status,
    validate_backlog_file,
    validate_required_outputs,
    parse_critical_gap_count,
    parse_domain_count,
)
from orchestrator.graph.build_graph import build_initial_run_state, build_orchestrator_graph, create_sqlite_checkpointer
from orchestrator.models.task import TaskStatus
from orchestrator.runners.codex_runner import CodexRunner
from orchestrator.storage.task_store import TaskStore


DEFAULT_BACKLOG_PATH = Path("orchestrator/runtime/backlog.json")
DEFAULT_DB_PATH = Path("orchestrator/runtime/langgraph.sqlite")
DEFAULT_CONFIG_PATH = Path("orchestrator/config.yaml")
DEFAULT_AUDIT_PROMPT_PATH = Path("orchestrator/prompts/product_audit.md")


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

    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--backlog", default=str(DEFAULT_BACKLOG_PATH))
    audit_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    audit_parser.add_argument("--dry-run", action="store_true")
    audit_parser.add_argument("--force", action="store_true")
    audit_parser.add_argument("--timeout", type=int, default=1800)
    audit_parser.add_argument("--verbose", action="store_true")
    audit_parser.add_argument("--prompt", default=str(DEFAULT_AUDIT_PROMPT_PATH))
    audit_parser.add_argument("--output-root")

    for name in ("run", "resume", "status", "cleanup"):
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
        return command_audit(
            Path(args.backlog),
            Path(args.db),
            config,
            dry_run=args.dry_run,
            force=args.force,
            timeout=args.timeout,
            verbose=args.verbose,
            prompt_path=Path(args.prompt),
            output_root=Path(args.output_root).resolve() if args.output_root else None,
        )
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


def command_audit(
    backlog_path: Path,
    db_path: Path,
    config: dict,
    *,
    dry_run: bool = False,
    force: bool = False,
    timeout: int = 1800,
    verbose: bool = False,
    prompt_path: Path = DEFAULT_AUDIT_PROMPT_PATH,
    output_root: Path | None = None,
    codex_runner: CodexRunner | None = None,
) -> int:
    del config
    del backlog_path, db_path
    repo_root = detect_repo_root(Path.cwd())
    resolved_output_root = resolve_output_root(repo_root, output_root)
    prompt_file = (repo_root / prompt_path).resolve() if not prompt_path.is_absolute() else prompt_path
    run_id = str(uuid4())
    inventory = collect_source_inventory(repo_root)
    template = prompt_file.read_text(encoding="utf-8")
    full_prompt = build_audit_prompt(template, inventory, resolved_output_root)
    required_outputs = required_output_paths(resolved_output_root)
    log_dir = repo_root / "orchestrator" / "logs" / "audit" / run_id
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "prompt.md").write_text(full_prompt, encoding="utf-8")
    (log_dir / "sources.json").write_text(
        json.dumps({"summary": inventory.summary(), "categories": inventory.categories}, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )

    if dry_run:
        output = {
            "status": AUDIT_STATUSES["dry_run"],
            "run_id": run_id,
            "repo_root": str(repo_root),
            "prompt_path": str(prompt_file),
            "log_dir": str(log_dir),
            "required_outputs": list(required_outputs),
        }
        if verbose:
            output["source_summary"] = inventory.summary()
            output["sources"] = inventory.categories
        print(json.dumps(output, ensure_ascii=True))
        return 0

    try:
        if force:
            archive_root = resolved_output_root / "reports" / "product" / "archive"
            archive_path = archive_existing_outputs(resolved_output_root, archive_root, required_outputs)
        else:
            archive_path = None
            ensure_outputs_absent(required_outputs)
    except Exception as exc:
        output = _render_audit_error(exc, run_id=run_id, log_dir=log_dir)
        print(json.dumps(output, ensure_ascii=True))
        return 1

    before = snapshot_git_status(repo_root)
    runner = codex_runner or CodexRunner()
    result = runner.run(
        full_prompt,
        cwd=repo_root,
        timeout=timeout,
        log_dir=log_dir,
    )
    after = snapshot_git_status(repo_root)
    unauthorized_changes = detect_unauthorized_changes(before, after)
    if unauthorized_changes:
        output = {
            "status": AUDIT_STATUSES["unauthorized_changes"],
            "run_id": run_id,
            "unauthorized_changes": unauthorized_changes,
            "log_dir": str(log_dir),
        }
        print(json.dumps(output, ensure_ascii=True))
        return 1

    if result.timed_out:
        output = {
            "status": AUDIT_STATUSES["timeout"],
            "run_id": run_id,
            "returncode": result.returncode,
            "log_dir": str(log_dir),
        }
        print(json.dumps(output, ensure_ascii=True))
        return 1

    if not result.ok:
        output = {
            "status": AUDIT_STATUSES["codex_failed"],
            "run_id": run_id,
            "returncode": result.returncode,
            "log_dir": str(log_dir),
        }
        print(json.dumps(output, ensure_ascii=True))
        return 1

    try:
        validate_required_outputs(required_outputs)
        backlog = validate_backlog_file(required_outputs["tasks/backlog.json"])
    except Exception as exc:
        output = _render_audit_error(exc, run_id=run_id, log_dir=log_dir)
        print(json.dumps(output, ensure_ascii=True))
        return 1

    output = {
        "status": AUDIT_STATUSES["completed"],
        "run_id": run_id,
        "task_count": len(backlog.tasks),
        "domain_count": parse_domain_count(backlog),
        "critical_gap_count": parse_critical_gap_count(backlog),
        "outputs": [str(path) for path in required_outputs.values()],
        "log_dir": str(log_dir),
    }
    if archive_path is not None:
        output["archive_path"] = str(archive_path)
    if verbose:
        output["source_summary"] = inventory.summary()
        output["session_id"] = result.session_id
        output["duration_seconds"] = result.duration_seconds
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


def _render_audit_error(exc: Exception, *, run_id: str, log_dir: Path) -> dict:
    status = getattr(exc, "status", "AUDIT_FAILED_CODEX")
    output = {
        "status": status,
        "run_id": run_id,
        "log_dir": str(log_dir),
        "error": str(exc),
    }
    details = getattr(exc, "details", None)
    if details:
        output.update(details)
    return output


if __name__ == "__main__":
    raise SystemExit(main())
