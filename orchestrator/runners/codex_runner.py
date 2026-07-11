from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
import re
import time


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
    prompt: str
    returncode: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    session_id: str | None = None
    log_dir: str | None = None
    json_payload: dict[str, Any] | None = None
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


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
        log_dir: str | Path | None = None,
        sandbox: str = "workspace-write",
    ) -> CodexRunResult:
        command = [
            self.binary,
            "exec",
            "--sandbox",
            sandbox,
            "--cd",
            str(cwd),
            *self.base_args,
            *(extra_args or []),
            prompt,
        ]
        started_at = datetime.now(UTC)
        start = time.monotonic()
        completed = None
        timeout_error: subprocess.TimeoutExpired | None = None
        try:
            completed = self.runner(command, cwd=str(cwd), timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            timeout_error = exc
        duration = time.monotonic() - start
        stdout = ""
        stderr = ""
        returncode: int | None = None
        timed_out = False
        if completed is not None:
            stdout = completed.stdout
            stderr = completed.stderr
            returncode = completed.returncode
        elif timeout_error is not None:
            stdout = _coerce_timeout_stream(timeout_error.stdout)
            stderr = _coerce_timeout_stream(timeout_error.stderr)
            returncode = None
            timed_out = True

        payload = None
        if expect_json and stdout.strip():
            payload = json.loads(stdout)
        session_id = _extract_session_id(stdout, stderr)
        result = CodexRunResult(
            command=command,
            prompt=prompt,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            session_id=session_id,
            log_dir=str(log_dir) if log_dir else None,
            json_payload=payload,
            timed_out=timed_out,
        )
        if log_dir:
            _write_logs(Path(log_dir), result, started_at)
        return result


def _coerce_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


def _extract_session_id(stdout: str, stderr: str) -> str | None:
    content = f"{stdout}\n{stderr}"
    match = re.search(r"session(?:[_\s-]*id)?\s*[:=]\s*([A-Za-z0-9._-]+)", content, flags=re.IGNORECASE)
    return match.group(1) if match else None


def _write_logs(log_dir: Path, result: CodexRunResult, started_at: datetime) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "prompt.md").write_text(result.prompt, encoding="utf-8")
    (log_dir / "stdout.log").write_text(result.stdout, encoding="utf-8")
    (log_dir / "stderr.log").write_text(result.stderr, encoding="utf-8")
    payload = {
        "command": result.command,
        "returncode": result.returncode,
        "duration_seconds": result.duration_seconds,
        "session_id": result.session_id,
        "timed_out": result.timed_out,
        "started_at": started_at.isoformat(),
        "log_dir": result.log_dir,
    }
    (log_dir / "result.json").write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
