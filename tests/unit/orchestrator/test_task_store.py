from __future__ import annotations

import json

from orchestrator.models.task import Task
from orchestrator.storage.task_store import TaskStore


def test_task_store_round_trip(tmp_path):
    path = tmp_path / "backlog.json"
    store = TaskStore(path)
    task = Task(id="T-1", title="Init", description="Create orchestrator foundation")

    store.save_tasks([task])

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert store.load_tasks()[0].id == "T-1"


def test_task_store_update_existing_task(tmp_path):
    path = tmp_path / "backlog.json"
    store = TaskStore(path)
    task = Task(id="T-1", title="Init", description="Initial")
    store.save_tasks([task])

    updated = task.model_copy(update={"title": "Updated"})
    store.update_task(updated)

    tasks = store.load_tasks()
    assert len(tasks) == 1
    assert tasks[0].title == "Updated"
