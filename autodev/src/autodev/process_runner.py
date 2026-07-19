from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path


TIMEOUTS_SECONDS = {
    "codex_plan": 15 * 60,
    "codex_review": 15 * 60,
    "claude_task": 30 * 60,
    "claude_correct": 30 * 60,
    "validation": 15 * 60,
    "playwright": 10 * 60,
    "packaging": 45 * 60,
}


class ProcessRunnerError(RuntimeError):
    """Erreur pendant l'exécution d'un processus externe."""


class ProcessTimeoutError(ProcessRunnerError):
    """Timeout d'un processus externe."""


@dataclass(frozen=True)
class ProcessExecutionResult:
    command: list[str]
    cwd: str
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    timeout_seconds: int
    duration_seconds: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def timeout_for_command(command: str) -> int:
    normalized = command.casefold()
    if "playwright" in normalized:
        return TIMEOUTS_SECONDS["playwright"]
    if "npm pack" in normalized or "tauri build" in normalized or "cargo build" in normalized:
        return TIMEOUTS_SECONDS["packaging"]
    return TIMEOUTS_SECONDS["validation"]


def run_process(
    *,
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
    input_text: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> ProcessExecutionResult:
    env = None if extra_env is None else {**os.environ, **extra_env}
    started_at = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        start_new_session=True,
    )

    try:
        stdout, stderr = process.communicate(input=input_text, timeout=timeout_seconds)
        return ProcessExecutionResult(
            command=list(command),
            cwd=str(cwd.resolve()),
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=False,
            timeout_seconds=timeout_seconds,
            duration_seconds=round(time.monotonic() - started_at, 3),
        )
    except subprocess.TimeoutExpired:
        _terminate_process_group(process.pid)
        stdout, stderr = process.communicate()
        raise ProcessTimeoutError(
            f"Timeout après {timeout_seconds}s pour: {' '.join(command)}"
        ) from None
    except OSError as exc:
        raise ProcessRunnerError(str(exc)) from exc


def run_process_capturing_timeout(
    *,
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
    input_text: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> ProcessExecutionResult:
    env = None if extra_env is None else {**os.environ, **extra_env}
    started_at = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        start_new_session=True,
    )

    try:
        stdout, stderr = process.communicate(input=input_text, timeout=timeout_seconds)
        return ProcessExecutionResult(
            command=list(command),
            cwd=str(cwd.resolve()),
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=False,
            timeout_seconds=timeout_seconds,
            duration_seconds=round(time.monotonic() - started_at, 3),
        )
    except subprocess.TimeoutExpired:
        _terminate_process_group(process.pid)
        stdout, stderr = process.communicate()
        return ProcessExecutionResult(
            command=list(command),
            cwd=str(cwd.resolve()),
            returncode=None,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
            timeout_seconds=timeout_seconds,
            duration_seconds=round(time.monotonic() - started_at, 3),
        )
    except OSError as exc:
        raise ProcessRunnerError(str(exc)) from exc


def _terminate_process_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)

    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
