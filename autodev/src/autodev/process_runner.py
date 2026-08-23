from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from autodev.provider_incidents import ProviderIncidentEvent, detect_provider_incident


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


@dataclass(frozen=True)
class ProviderProcessResult:
    """Process evidence plus a provider-only wait decision; never a correction action."""

    stdout: str
    stderr: str
    provider_incident: ProviderIncidentEvent | None
    wait_state: str | None


def classify_provider_result(
    result: ProcessExecutionResult,
    *,
    provider_name: str | None = None,
    declared_providers: Iterable[str] | None = None,
    now: datetime | None = None,
) -> ProviderProcessResult:
    """Classify captured output without changing business-correction state or executing commands."""
    raw_message = result.stderr or result.stdout
    incident = detect_provider_incident(
        raw_message,
        stderr=result.stderr,
        provider_name=provider_name,
        declared_providers=declared_providers,
        now=now,
    ) if raw_message else None
    return ProviderProcessResult(
        stdout=result.stdout,
        stderr=result.stderr,
        provider_incident=incident,
        wait_state="WAITING_PROVIDER_RESET" if incident is not None else None,
    )


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
    heartbeat_path: Path | None = None,
    heartbeat_phase: str | None = None,
    heartbeat_interval: float = 5.0,
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

    stop_heartbeat = threading.Event()
    heartbeat_thread = None
    if heartbeat_path is not None:
        heartbeat_thread = threading.Thread(
            target=_heartbeat_loop,
            args=(heartbeat_path, heartbeat_phase or "PROCESS", process.pid, stop_heartbeat, heartbeat_interval),
            daemon=True,
        )
        heartbeat_thread.start()
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
    finally:
        stop_heartbeat.set()
        if heartbeat_thread is not None:
            heartbeat_thread.join(timeout=max(heartbeat_interval, 0.1) + 0.5)
        if heartbeat_path is not None:
            heartbeat_path.unlink(missing_ok=True)


def _heartbeat_loop(path: Path, phase: str, pid: int, stop: threading.Event, interval: float) -> None:
    started_at = datetime.now(timezone.utc).isoformat()
    while True:
        payload = {"phase": phase, "pid": pid, "started_at": started_at,
                   "updated_at": datetime.now(timezone.utc).isoformat()}
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        if stop.wait(max(interval, 0.05)):
            return


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
