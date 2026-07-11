from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class CommandRunner(Protocol):
    def __call__(self, args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        ...


def _default_runner(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=True,
        text=True,
        capture_output=True,
        **kwargs,
    )


@dataclass(slots=True)
class WorktreeInfo:
    path: str
    head: str | None = None
    branch: str | None = None
    bare: bool = False
    detached: bool = False
    locked: bool = False
    prunable: bool = False


def create_worktree(
    repo_path: str | Path,
    worktree_path: str | Path,
    branch_name: str,
    base_ref: str,
    *,
    runner: CommandRunner = _default_runner,
) -> WorktreeInfo:
    runner(
        [
            "git",
            "-C",
            str(repo_path),
            "worktree",
            "add",
            str(worktree_path),
            "-b",
            branch_name,
            base_ref,
        ]
    )
    return WorktreeInfo(path=str(worktree_path), branch=branch_name)


def remove_worktree(
    repo_path: str | Path,
    worktree_path: str | Path,
    *,
    force: bool = False,
    runner: CommandRunner = _default_runner,
) -> None:
    command = ["git", "-C", str(repo_path), "worktree", "remove", str(worktree_path)]
    if force:
        command.append("--force")
    runner(command)


def list_worktrees(
    repo_path: str | Path,
    *,
    runner: CommandRunner = _default_runner,
) -> list[WorktreeInfo]:
    completed = runner(["git", "-C", str(repo_path), "worktree", "list", "--porcelain"])
    entries: list[WorktreeInfo] = []
    current: dict[str, str | bool | None] | None = None
    for raw_line in completed.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                entries.append(WorktreeInfo(**current))
                current = None
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            if current:
                entries.append(WorktreeInfo(**current))
            current = {"path": value, "head": None, "branch": None, "bare": False, "detached": False, "locked": False, "prunable": False}
            continue
        if current is None:
            continue
        if key in {"bare", "detached", "locked", "prunable"}:
            current[key] = True
        elif key == "HEAD":
            current["head"] = value
        elif key == "branch":
            current["branch"] = value.removeprefix("refs/heads/")
    if current:
        entries.append(WorktreeInfo(**current))
    return entries


def verify_clean(
    repo_path: str | Path,
    *,
    runner: CommandRunner = _default_runner,
) -> bool:
    completed = runner(["git", "-C", str(repo_path), "status", "--porcelain"])
    return completed.stdout.strip() == ""


def get_commit(
    repo_path: str | Path,
    ref: str = "HEAD",
    *,
    runner: CommandRunner = _default_runner,
) -> str:
    completed = runner(["git", "-C", str(repo_path), "rev-parse", ref])
    return completed.stdout.strip()


def push_branch(
    repo_path: str | Path,
    branch_name: str,
    *,
    remote: str = "origin",
    set_upstream: bool = True,
    runner: CommandRunner = _default_runner,
) -> None:
    command = ["git", "-C", str(repo_path), "push"]
    if set_upstream:
        command.append("-u")
    command.extend([remote, branch_name])
    runner(command)
