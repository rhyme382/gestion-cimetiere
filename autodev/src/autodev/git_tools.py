from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    """Erreur liée aux opérations Git."""


def run_git(repo_root: Path, args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd or repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result


def git_output(repo_root: Path, args: list[str], cwd: Path | None = None) -> str:
    result = run_git(repo_root, args, cwd=cwd)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "erreur Git inconnue"
        raise GitError(stderr)
    return result.stdout.strip()


def ensure_clean_worktree(repo_root: Path) -> None:
    status = git_output(repo_root, ["status", "--short"])
    if status:
        raise GitError("Le dépôt principal contient des modifications non enregistrées.")


def current_head(repo_root: Path) -> str:
    return git_output(repo_root, ["rev-parse", "HEAD"])


def branch_exists(repo_root: Path, branch: str) -> bool:
    result = run_git(repo_root, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"])
    return result.returncode == 0


def worktree_registered(repo_root: Path, worktree_path: Path) -> bool:
    listed = git_output(repo_root, ["worktree", "list", "--porcelain"])
    needle = f"worktree {worktree_path.resolve()}"
    return needle in listed.splitlines()


def create_branch(repo_root: Path, branch: str, start_point: str) -> None:
    result = run_git(repo_root, ["branch", branch, start_point])
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"Impossible de créer la branche {branch}: {stderr}")


def add_worktree(repo_root: Path, worktree_path: Path, branch: str) -> None:
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    result = run_git(repo_root, ["worktree", "add", str(worktree_path), branch])
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"Impossible de créer le worktree {worktree_path}: {stderr}")


def changed_paths_since(repo_root: Path, worktree_path: Path, base_commit: str) -> list[str]:
    tracked = git_output(
        repo_root,
        ["diff", "--name-only", base_commit, "HEAD"],
        cwd=worktree_path,
    )
    status = git_output(repo_root, ["status", "--short"], cwd=worktree_path)

    paths: set[str] = {line.strip() for line in tracked.splitlines() if line.strip()}
    for raw_line in status.splitlines():
        if not raw_line.strip():
            continue
        path_part = raw_line[3:]
        if " -> " in path_part:
            path_part = path_part.split(" -> ", maxsplit=1)[1]
        paths.add(path_part.strip())
    return sorted(paths)


def changed_paths_between(repo_root: Path, start_commit: str, end_commit: str) -> list[str]:
    output = git_output(repo_root, ["diff", "--name-only", start_commit, end_commit])
    return sorted(line.strip() for line in output.splitlines() if line.strip())


def commit_count_since(repo_root: Path, worktree_path: Path, base_commit: str) -> int:
    count = git_output(repo_root, ["rev-list", "--count", f"{base_commit}..HEAD"], cwd=worktree_path)
    return int(count)


def head_commit(repo_root: Path, worktree_path: Path) -> str:
    return git_output(repo_root, ["rev-parse", "HEAD"], cwd=worktree_path)


def diff_patch(repo_root: Path, worktree_path: Path, base_commit: str) -> str:
    return git_output(repo_root, ["diff", "--binary", base_commit, "HEAD"], cwd=worktree_path)


def diff_patch_between(repo_root: Path, start_commit: str, end_commit: str) -> str:
    return git_output(repo_root, ["diff", "--binary", start_commit, end_commit])


def git_status_porcelain(repo_root: Path, cwd: Path | None = None) -> str:
    return git_output(repo_root, ["status", "--short"], cwd=cwd)
