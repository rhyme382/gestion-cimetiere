from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    APPROVED = "approved"
    REJECTED = "rejected"


class AgentExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    TOKEN_LIMIT = "TOKEN_LIMIT"
    RATE_LIMIT = "RATE_LIMIT"
    NEEDS_HUMAN = "NEEDS_HUMAN"


class TaskDependency(StrictModel):
    task_id: str = Field(min_length=1)
    kind: Literal["blocks", "relates_to", "duplicates"] = "blocks"
    required: bool = True


class AcceptanceCriterion(StrictModel):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    mandatory: bool = True
    satisfied: bool | None = None
    notes: str | None = None


class Task(StrictModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    task_type: str = "development"
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    status: TaskStatus = TaskStatus.PENDING
    dependencies: list[TaskDependency] = Field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    branch_name: str | None = None
    worktree_path: str | None = None
    assignee: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    attempts: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentResult(StrictModel):
    task_id: str = Field(min_length=1)
    agent: Literal["codex", "claude", "qa", "human"]
    status: AgentExecutionStatus
    summary: str = ""
    branch_name: str | None = None
    worktree_path: str | None = None
    report_path: str | None = None
    commit_sha: str | None = None
    stdout: str = ""
    stderr: str = ""
    structured_report: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class QAResult(StrictModel):
    task_id: str = Field(min_length=1)
    status: Literal["accepted", "rejected", "needs_human"]
    summary: str = Field(min_length=1)
    issues: list[str] = Field(default_factory=list)
    reviewer: str = "codex"
    report_path: str | None = None
    raw_json: dict[str, Any] = Field(default_factory=dict)
