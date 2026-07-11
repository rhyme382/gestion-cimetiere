from __future__ import annotations

import subprocess

from orchestrator.git.worktree_manager import (
    create_worktree,
    get_commit,
    list_worktrees,
    push_branch,
    verify_clean,
)


class RecordingRunner:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], **kwargs):
        self.calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=self.stdout, stderr="")


def test_create_worktree_uses_git_worktree_add():
    runner = RecordingRunner()

    info = create_worktree("/repo", "/repo/worktrees/T-1", "task/T-1", "main", runner=runner)

    assert info.branch == "task/T-1"
    assert runner.calls[0] == [
        "git",
        "-C",
        "/repo",
        "worktree",
        "add",
        "/repo/worktrees/T-1",
        "-b",
        "task/T-1",
        "main",
    ]


def test_list_worktrees_parses_porcelain_output():
    runner = RecordingRunner(
        stdout=(
            "worktree /repo\n"
            "HEAD abc123\n"
            "branch refs/heads/main\n\n"
            "worktree /repo/worktrees/T-1\n"
            "HEAD def456\n"
            "branch refs/heads/task/T-1\n"
            "locked\n\n"
        )
    )

    worktrees = list_worktrees("/repo", runner=runner)

    assert [item.path for item in worktrees] == ["/repo", "/repo/worktrees/T-1"]
    assert worktrees[1].branch == "task/T-1"
    assert worktrees[1].locked is True


def test_verify_clean_and_get_commit_and_push_branch():
    clean_runner = RecordingRunner(stdout="")
    dirty_runner = RecordingRunner(stdout=" M file.py\n")
    commit_runner = RecordingRunner(stdout="abc123\n")
    push_runner = RecordingRunner()

    assert verify_clean("/repo", runner=clean_runner) is True
    assert verify_clean("/repo", runner=dirty_runner) is False
    assert get_commit("/repo", runner=commit_runner) == "abc123"

    push_branch("/repo", "task/T-1", runner=push_runner)
    assert push_runner.calls[0] == ["git", "-C", "/repo", "push", "-u", "origin", "task/T-1"]
