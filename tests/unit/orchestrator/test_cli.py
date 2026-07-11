from __future__ import annotations

import json

from orchestrator import cli
from orchestrator.models.task import Task
from orchestrator.storage.task_store import TaskStore


def test_cli_init_and_status(tmp_path, capsys):
    backlog_path = tmp_path / "backlog.json"
    db_path = tmp_path / "langgraph.sqlite"
    config_path = tmp_path / "config.yaml"
    config_path.write_text("project:\n  name: test\n", encoding="utf-8")

    assert cli.main(["--config", str(config_path), "init", "--backlog", str(backlog_path), "--db", str(db_path)]) == 0
    init_output = json.loads(capsys.readouterr().out)
    assert init_output["status"] == "initialized"

    TaskStore(backlog_path).save_tasks([Task(id="T-1", title="Task", description="Task description")])
    assert cli.main(["--config", str(config_path), "status", "--backlog", str(backlog_path), "--db", str(db_path)]) == 0
    status_output = json.loads(capsys.readouterr().out)
    assert status_output["task_counts"]["pending"] == 1


def test_cli_approve_and_reject(tmp_path, capsys):
    backlog_path = tmp_path / "backlog.json"
    config_path = tmp_path / "config.yaml"
    config_path.write_text("project:\n  name: test\n", encoding="utf-8")
    TaskStore(backlog_path).save_tasks([Task(id="T-1", title="Task", description="Task description")])

    assert cli.main(["--config", str(config_path), "approve", "T-1", "--backlog", str(backlog_path)]) == 0
    approve_output = json.loads(capsys.readouterr().out)
    assert approve_output["status"] == "approved"

    assert cli.main(["--config", str(config_path), "reject", "T-2", "--backlog", str(backlog_path)]) == 1
    reject_output = json.loads(capsys.readouterr().out)
    assert reject_output["status"] == "not_found"
