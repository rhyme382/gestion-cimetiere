from __future__ import annotations

from pathlib import Path

from orchestrator.models.task import QAResult
from orchestrator.runners.codex_runner import CodexRunner


class QARunner:
    def __init__(self, codex_runner: CodexRunner | None = None) -> None:
        self.codex_runner = codex_runner or CodexRunner()

    def run(
        self,
        *,
        task_id: str,
        prompt: str,
        cwd: str | Path,
        timeout: int | None = None,
    ) -> QAResult:
        strict_prompt = (
            "Return only valid JSON with keys "
            '"status", "summary", "issues", and optional "report_path".\n\n'
            f"{prompt}"
        )
        result = self.codex_runner.run(
            strict_prompt,
            cwd=cwd,
            timeout=timeout,
            expect_json=True,
        )
        if result.json_payload is None:
            raise ValueError("Codex QA runner did not return JSON output.")
        payload = dict(result.json_payload)
        payload["task_id"] = task_id
        payload.setdefault("raw_json", dict(result.json_payload))
        return QAResult.model_validate(payload)
