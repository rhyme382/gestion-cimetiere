from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from orchestrator.models.task import Task


class TaskStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def exists(self) -> bool:
        return self.path.exists()

    def load_payload(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "tasks": []}
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        payload.setdefault("version", 1)
        payload.setdefault("tasks", [])
        return payload

    def load_tasks(self) -> list[Task]:
        payload = self.load_payload()
        return [Task.model_validate(item) for item in payload["tasks"]]

    def save_tasks(self, tasks: list[Task], *, metadata: dict[str, Any] | None = None) -> None:
        payload = {"version": 1, "tasks": [task.model_dump(mode="json") for task in tasks]}
        if metadata:
            payload["metadata"] = metadata
        self._atomic_write(payload)

    def append_task(self, task: Task) -> None:
        tasks = self.load_tasks()
        tasks.append(task)
        self.save_tasks(tasks)

    def update_task(self, task: Task) -> None:
        tasks = self.load_tasks()
        updated = False
        for index, current in enumerate(tasks):
            if current.id == task.id:
                tasks[index] = task
                updated = True
                break
        if not updated:
            tasks.append(task)
        self.save_tasks(tasks)

    def _atomic_write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.path.parent,
            delete=False,
        ) as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2)
            handle.write("\n")
            temp_path = Path(handle.name)
        os.replace(temp_path, self.path)
