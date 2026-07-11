from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


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
class CodexRunResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    json_payload: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class CodexRunner:
    def __init__(
        self,
        *,
        binary: str = "codex",
        runner: ExecRunner = _default_exec_runner,
        base_args: list[str] | None = None,
    ) -> None:
        self.binary = binary
        self.runner = runner
        self.base_args = base_args or []

    def run(
        self,
        prompt: str,
        *,
        cwd: str | Path,
        extra_args: list[str] | None = None,
        timeout: int | None = None,
        expect_json: bool = False,
    ) -> CodexRunResult:
        command = [self.binary, "exec", *self.base_args, *(extra_args or []), prompt]
        completed = self.runner(command, cwd=str(cwd), timeout=timeout)
        payload = None
        if expect_json and completed.stdout.strip():
            payload = json.loads(completed.stdout)
        return CodexRunResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            json_payload=payload,
        )
