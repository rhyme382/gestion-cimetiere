from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from autodev.integrate_task import IntegrateTaskError, integrate_task

from test_task_runner import commit_all, init_repo, make_task, write_backlog


def prepare_repo_for_integration(
    tmp_path: Path,
    *,
    task_id: str = "TASK-INTEGRATE",
    verdict: str = "APPROVED",
    validation_commands: list[str] | None = None,
    task_file: str = "src/feature.txt",
    task_content: str = "feature branch change\n",
    base_file: str = "src/base.txt",
    base_content: str = "base\n",
) -> tuple[Path, Path, Path, str, str]:
    repo = init_repo(tmp_path)
    (repo / base_file).write_text(base_content, encoding="utf-8")

    task = make_task(task_id)
    task["validation_commands"] = validation_commands or [f'{sys.executable} -c "print(\'validated\')"']
    task["allowed_paths"] = ["src", "reports/dev"]
    backlog = write_backlog(repo, [task])
    commit_all(repo, "prepare backlog")

    base_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    worktree = tmp_path / f"{task_id.lower()}-worktree"
    branch = f"autodev/{task_id}"
    subprocess.run(["git", "branch", branch, base_commit], cwd=repo, check=True)
    subprocess.run(["git", "worktree", "add", str(worktree), branch], cwd=repo, check=True)

    target = worktree / task_file
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(task_content, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=worktree, check=True)
    subprocess.run(
        ["git", "commit", "-m", "task implementation"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    )
    produced_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    write_run_artifacts(
        repo=repo,
        task_id=task_id,
        backlog=backlog,
        worktree=worktree,
        base_commit=base_commit,
        produced_commit=produced_commit,
        verdict=verdict,
    )
    commit_all(repo, "record task review")
    return repo, backlog, worktree, base_commit, produced_commit


def write_run_artifacts(
    *,
    repo: Path,
    task_id: str,
    backlog: Path,
    worktree: Path,
    base_commit: str,
    produced_commit: str | None,
    verdict: str,
) -> None:
    run_dir = repo / ".autodev" / "runs" / task_id
    review_dir = run_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "task.json").write_text(
        json.dumps(
            {
                "backlog": str(backlog),
                "task": {"id": task_id},
                "branch": f"autodev/{task_id}",
                "worktree": str(worktree),
                "base_commit": base_commit,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "result.json").write_text(
        json.dumps(
            {
                "task_id": task_id,
                "status": "success",
                "branch": f"autodev/{task_id}",
                "worktree": str(worktree),
                "run_dir": str(run_dir),
                "base_commit": base_commit,
                "produced_commit": produced_commit,
                "modified_paths": ["src/feature.txt"],
                "validations": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "review-result.json").write_text(
        json.dumps(
            {
                "task_id": task_id,
                "verdict": verdict,
                "summary": "ok",
                "requirement_checks": [],
                "acceptance_checks": [],
                "issues": [],
                "tests": {"status": "PASS", "details": []},
                "scope": {"status": "PASS", "unexpected_paths": []},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def integration_result(repo: Path, task_id: str) -> dict[str, object]:
    path = repo / ".autodev" / "runs" / task_id / "integration" / "integration-result.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_integrate_unknown_task_raises(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-KNOWN")])
    commit_all(repo, "add backlog")

    with pytest.raises(IntegrateTaskError, match="Tâche inconnue"):
        integrate_task(backlog, "TASK-MISSING")


def test_integrate_missing_review_raises(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-NO-REVIEW")])
    commit_all(repo, "prepare backlog")
    base_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "branch", "autodev/TASK-NO-REVIEW", base_commit], cwd=repo, check=True)

    with pytest.raises(IntegrateTaskError, match="review-result.json"):
        integrate_task(backlog, "TASK-NO-REVIEW")


def test_integrate_rejects_non_approved_verdict(tmp_path: Path) -> None:
    _, backlog, _, _, _ = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-REJECTED",
        verdict="CORRECTION_REQUIRED",
    )

    with pytest.raises(IntegrateTaskError, match="Verdict de revue incompatible"):
        integrate_task(backlog, "TASK-REJECTED")


def test_integrate_rejects_dirty_main_repo(tmp_path: Path) -> None:
    repo, backlog, _, _, _ = prepare_repo_for_integration(tmp_path, task_id="TASK-DIRTY-MAIN")
    (repo / "README.md").write_text("dirty main\n", encoding="utf-8")

    with pytest.raises(IntegrateTaskError, match="dépôt principal contient des modifications non enregistrées"):
        integrate_task(backlog, "TASK-DIRTY-MAIN")


def test_integrate_rejects_dirty_task_worktree(tmp_path: Path) -> None:
    _, backlog, worktree, _, _ = prepare_repo_for_integration(tmp_path, task_id="TASK-DIRTY-WT")
    (worktree / "src" / "feature.txt").write_text("dirty worktree\n", encoding="utf-8")

    with pytest.raises(IntegrateTaskError, match="worktree de la tâche contient des modifications non commitées"):
        integrate_task(backlog, "TASK-DIRTY-WT")


def test_integrate_rejects_missing_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-NO-BRANCH")])
    commit_all(repo, "prepare backlog")

    with pytest.raises(IntegrateTaskError, match="Branche de tâche absente"):
        integrate_task(backlog, "TASK-NO-BRANCH")


def test_integrate_reports_git_conflict(tmp_path: Path) -> None:
    repo, backlog, _, _, _ = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-CONFLICT",
        task_file="src/shared.txt",
        task_content="feature side\n",
        base_file="src/shared.txt",
        base_content="base\n",
    )
    (repo / "src" / "shared.txt").write_text("main side\n", encoding="utf-8")
    commit_all(repo, "main branch conflicting change")

    with pytest.raises(IntegrateTaskError, match="Intégration refusée"):
        integrate_task(backlog, "TASK-CONFLICT")

    result = integration_result(repo, "TASK-CONFLICT")
    assert result["status"] == "CONFLICT"


def test_integrate_success_creates_merge_commit_and_reports(tmp_path: Path) -> None:
    repo, backlog, worktree, _, produced_commit = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-SUCCESS",
    )
    before_remote = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    result = integrate_task(backlog, "TASK-SUCCESS")

    assert result["status"] == "INTEGRATED"
    assert result["pre_review_verdict"] == "APPROVED"
    assert result["produced_commit"] == produced_commit
    assert result["integration_commit"]
    assert result["worktree_removed"] is True
    assert not worktree.exists()
    assert "validated" in (repo / ".autodev" / "runs" / "TASK-SUCCESS" / "integration" / "stdout.log").read_text(
        encoding="utf-8"
    )
    merge_message = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert merge_message == "autodev integrate-task TASK-SUCCESS"
    assert before_remote != result["integration_commit"]


def test_integrate_rolls_back_when_post_validation_fails(tmp_path: Path) -> None:
    repo, backlog, worktree, _, _ = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-VALIDATION-FAIL",
        validation_commands=[f'{sys.executable} -c "raise SystemExit(1)"'],
    )
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    with pytest.raises(IntegrateTaskError, match="validation post-intégration a échoué"):
        integrate_task(backlog, "TASK-VALIDATION-FAIL")

    head_after = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert head_after == head_before
    assert worktree.exists()
    result = integration_result(repo, "TASK-VALIDATION-FAIL")
    assert result["status"] == "FAILED"


def test_integrate_does_not_push_remote(tmp_path: Path) -> None:
    repo, backlog, _, _, _ = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-NO-PUSH",
    )
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True, text=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True)
    subprocess.run(["git", "push", "-u", "origin", "master"], cwd=repo, check=True, capture_output=True, text=True)
    remote_before = subprocess.run(
        ["git", "rev-parse", "refs/heads/master"],
        cwd=remote,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    integrate_task(backlog, "TASK-NO-PUSH")

    remote_after = subprocess.run(
        ["git", "rev-parse", "refs/heads/master"],
        cwd=remote,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert remote_after == remote_before


def test_integrate_removes_worktree_after_success(tmp_path: Path) -> None:
    repo, backlog, worktree, _, _ = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-CLEANUP",
    )

    integrate_task(backlog, "TASK-CLEANUP")

    assert not worktree.exists()
    worktree_list = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert str(worktree) not in worktree_list
