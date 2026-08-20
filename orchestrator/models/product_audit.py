from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class AuditTask(StrictModel):
    id: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    title: str = Field(min_length=1)
    user_story: str = Field(min_length=1)
    priority: Literal["low", "medium", "high", "critical"]
    status: str = Field(min_length=1)
    dependencies: list[str] = Field(default_factory=list)
    recommended_agent: str = Field(min_length=1)
    likely_files: list[str] = Field(default_factory=list, min_length=1)
    acceptance_criteria: list[str] = Field(default_factory=list, min_length=1)
    required_unit_tests: list[str] = Field(default_factory=list, min_length=1)
    required_e2e_test: str = Field(min_length=1)
    required_ui_evidence: str = Field(min_length=1)
    definition_of_done: list[str] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def validate_task_semantics(self) -> "AuditTask":
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError(f"Task {self.id} contains duplicate dependencies.")

        technical_keywords = ("refactor", "cleanup", "migration", "architecture", "infra", "tooling")
        user_keywords = ("utilisateur", "mairie", "agent", "peut", "depuis", "ecran", "interface", "application")
        criteria_blob = " ".join(self.acceptance_criteria).lower()
        if any(keyword in criteria_blob for keyword in technical_keywords) and not any(
            keyword in criteria_blob for keyword in user_keywords
        ):
            raise ValueError(
                f"Task {self.id} has acceptance criteria that are not observable by an end user."
            )

        title_blob = f"{self.title} {self.user_story}".lower()
        if " et " in title_blob and len(self.likely_files) > 8:
            raise ValueError(f"Task {self.id} does not appear atomic enough.")

        if self.status.lower() in {"done", "completed", "accepted", "approved"} and any(
            keyword in title_blob for keyword in technical_keywords
        ):
            raise ValueError(
                f"Task {self.id} is marked completed while being described as a technical-only backlog item."
            )

        return self


class AuditBacklog(StrictModel):
    schema_version: Literal["1.0"]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tasks: list[AuditTask] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_backlog(self) -> "AuditBacklog":
        if not self.tasks:
            raise ValueError("Backlog must contain at least one task.")

        ids = [task.id for task in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("Backlog contains duplicate task IDs.")

        known_ids = set(ids)
        adjacency: dict[str, list[str]] = {}
        for task in self.tasks:
            for dependency in task.dependencies:
                if dependency not in known_ids:
                    raise ValueError(f"Task {task.id} references unknown dependency {dependency}.")
                if dependency == task.id:
                    raise ValueError(f"Task {task.id} cannot depend on itself.")
            adjacency[task.id] = list(task.dependencies)

        visited: set[str] = set()
        stack: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in stack:
                raise ValueError(f"Circular dependency detected around {task_id}.")
            if task_id in visited:
                return
            stack.add(task_id)
            for dependency in adjacency[task_id]:
                visit(dependency)
            stack.remove(task_id)
            visited.add(task_id)

        for task_id in adjacency:
            visit(task_id)

        return self
