from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from orchestrator.models.task import AgentExecutionStatus


class ExecRunner(Protocol):
    def __call__(self, args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        ...


def _default_exec_runner(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=False,
        text=True,
        capture_output=True,
        **kwargs,
    )


@dataclass(slots=True)
class ClaudeRunResult:
    command: list[str]
    status: AgentExecutionStatus
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.status == AgentExecutionStatus.SUCCESS


class ClaudeRunner:
    def __init__(
        self,
        *,
        binary: str = "claude",
        runner: ExecRunner = _default_exec_runner,
        base_args: list[str] | None = None,
    ) -> None:
        self.binary = binary
        self.runner = runner
        self.base_args = base_args or ["--print"]

    def run(
        self,
        prompt: str,
        *,
        cwd: str | Path,
        extra_args: list[str] | None = None,
        timeout: int | None = None,
    ) -> ClaudeRunResult:
        command = [self.binary, *self.base_args, *(extra_args or []), prompt]
        completed = self.runner(command, cwd=str(cwd), timeout=timeout)
        status = detect_claude_status(completed.stdout, completed.stderr, completed.returncode)
        return ClaudeRunResult(
            command=command,
            status=status,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def detect_claude_status(stdout: str, stderr: str, returncode: int) -> AgentExecutionStatus:
    content = f"{stdout}\n{stderr}".upper()
    if "TOKEN_LIMIT" in content or "TOKEN LIMIT" in content:
        return AgentExecutionStatus.TOKEN_LIMIT
    if "RATE_LIMIT" in content or "RATE LIMIT" in content:
        return AgentExecutionStatus.RATE_LIMIT
    if "NEEDS_HUMAN" in content or "NEEDS HUMAN" in content:
        return AgentExecutionStatus.NEEDS_HUMAN
    if "BLOCKED" in content:
        return AgentExecutionStatus.BLOCKED
    if returncode == 0 and "SUCCESS" in content:
        return AgentExecutionStatus.SUCCESS
    if returncode == 0 and "FAILED" not in content:
        return AgentExecutionStatus.SUCCESS
    return AgentExecutionStatus.FAILED
