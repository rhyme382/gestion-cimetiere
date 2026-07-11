from __future__ import annotations

import json
import subprocess

import pytest

from orchestrator.models.task import AgentExecutionStatus
from orchestrator.runners.claude_runner import ClaudeRunner, detect_claude_status
from orchestrator.runners.codex_runner import CodexRunner
from orchestrator.runners.qa_runner import QARunner


class FakeRunner:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], **kwargs):
        self.calls.append(args)
        return subprocess.CompletedProcess(args, self.returncode, stdout=self.stdout, stderr=self.stderr)


@pytest.mark.parametrize(
    ("stdout", "stderr", "returncode", "expected"),
    [
        ("SUCCESS", "", 0, AgentExecutionStatus.SUCCESS),
        ("BLOCKED", "", 0, AgentExecutionStatus.BLOCKED),
        ("", "TOKEN LIMIT reached", 1, AgentExecutionStatus.TOKEN_LIMIT),
        ("", "RATE_LIMIT", 1, AgentExecutionStatus.RATE_LIMIT),
        ("NEEDS_HUMAN", "", 0, AgentExecutionStatus.NEEDS_HUMAN),
        ("FAILED", "", 1, AgentExecutionStatus.FAILED),
    ],
)
def test_detect_claude_status(stdout, stderr, returncode, expected):
    assert detect_claude_status(stdout, stderr, returncode) == expected


def test_codex_runner_parses_json_payload():
    runner = FakeRunner(stdout=json.dumps({"status": "accepted"}))
    codex = CodexRunner(runner=runner)

    result = codex.run("prompt", cwd="/tmp", expect_json=True)

    assert result.json_payload == {"status": "accepted"}
    assert runner.calls[0][:2] == ["codex", "exec"]


def test_claude_runner_builds_non_interactive_command():
    runner = FakeRunner(stdout="SUCCESS")
    claude = ClaudeRunner(runner=runner)

    result = claude.run("Do work", cwd="/tmp")

    assert result.ok is True
    assert runner.calls[0][:2] == ["claude", "--print"]


def test_qa_runner_returns_structured_result():
    runner = FakeRunner(stdout=json.dumps({"status": "accepted", "summary": "Looks good", "issues": []}))
    qa_runner = QARunner(CodexRunner(runner=runner))

    result = qa_runner.run(task_id="T-1", prompt="Review this", cwd="/tmp")

    assert result.task_id == "T-1"
    assert result.status == "accepted"
    assert result.raw_json["summary"] == "Looks good"
