from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from shutil import rmtree

import pytest

from autodev.integrate_task import IntegrateTaskError, integrate_task

from test_task_runner import commit_all, init_repo, make_task, write_backlog


def write_quality_gates(
    repo: Path,
    *,
    smoke_commands: list[str] | None = None,
    full_commands: list[str] | None = None,
) -> None:
    smoke_lines = smoke_commands or [f'{sys.executable} -c "print(\'smoke-ok\')"']
    full_lines = full_commands or [f'{sys.executable} -c "print(\'full-ok\')"']
    payload = [
        "task:",
        "  required: true",
        "smoke:",
        "  commands:",
        *[f"    - {json.dumps(command)}" for command in smoke_lines],
        "full:",
        "  commands:",
        *[f"    - {json.dumps(command)}" for command in full_lines],
        "",
    ]
    (repo / "autodev" / "config" / "quality-gates.yaml").write_text("\n".join(payload), encoding="utf-8")


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


def read_validation_results(repo: Path, task_id: str, artifact: str) -> dict[str, object]:
    path = repo / ".autodev" / "runs" / task_id / "integration" / artifact / "validation-results.json"
    return json.loads(path.read_text(encoding="utf-8"))


def git_head(repo: Path, ref: str = "HEAD", *, cwd: Path | None = None) -> str:
    return subprocess.run(
        ["git", "rev-parse", ref],
        cwd=cwd or repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


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


def test_integrate_rejects_missing_task_worktree_before_pre_merge_validation(tmp_path: Path) -> None:
    _, backlog, worktree, _, _ = prepare_repo_for_integration(tmp_path, task_id="TASK-NO-WORKTREE")
    rmtree(worktree)

    with pytest.raises(IntegrateTaskError, match="Worktree de tâche introuvable pour la validation pré-fusion"):
        integrate_task(backlog, "TASK-NO-WORKTREE")


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

    task_pre = read_validation_results(repo, "TASK-SUCCESS", "task-pre-merge")
    baseline = read_validation_results(repo, "TASK-SUCCESS", "baseline")
    task_post = read_validation_results(repo, "TASK-SUCCESS", "task-post-merge")
    post_merge = read_validation_results(repo, "TASK-SUCCESS", "post-merge")
    assert task_pre["execution_context"] == "TASK_WORKTREE"
    assert baseline["execution_context"] == "TARGET_BRANCH"
    assert task_post["execution_context"] == "POST_MERGE_TARGET"
    assert post_merge["execution_context"] == "POST_MERGE_TARGET"
    assert task_pre["cwd"] != baseline["cwd"]
    assert baseline["cwd"] == post_merge["cwd"]


def test_integrate_runs_pre_merge_task_validation_in_worktree_only(tmp_path: Path) -> None:
    repo, backlog, worktree, _, _ = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-WORKTREE-ONLY",
        task_file="src/__tests__/DiagnosticCard.test.tsx",
        task_content="test-only file\n",
        validation_commands=[
            f'{sys.executable} -c "from pathlib import Path\nimport sys\nraise SystemExit(0 if Path(\'src/__tests__/DiagnosticCard.test.tsx\').exists() else 1)"'
        ],
    )

    result = integrate_task(backlog, "TASK-WORKTREE-ONLY")

    assert result["status"] == "INTEGRATED"
    pre_merge = read_validation_results(repo, "TASK-WORKTREE-ONLY", "task-pre-merge")
    post_merge = read_validation_results(repo, "TASK-WORKTREE-ONLY", "task-post-merge")
    baseline = read_validation_results(repo, "TASK-WORKTREE-ONLY", "baseline")
    assert pre_merge["status"] == "PASS"
    assert pre_merge["execution_context"] == "TASK_WORKTREE"
    assert pre_merge["cwd"] == str(worktree.resolve())
    assert pre_merge["results"][0]["cwd"] == str(worktree.resolve())
    assert pre_merge["results"][0]["execution_context"] == "TASK_WORKTREE"
    assert post_merge["status"] == "PASS"
    assert baseline["cwd"] == str(repo.resolve())


def test_target_branch_would_fail_same_command_before_merge_but_is_not_used_for_pre_merge(tmp_path: Path) -> None:
    repo, backlog, _, _, _ = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-PREMERGE-CWD",
        task_file="src/__tests__/DiagnosticCard.test.tsx",
        task_content="test-only file\n",
        validation_commands=[
            f'{sys.executable} -c "from pathlib import Path\nraise SystemExit(0 if Path(\'src/__tests__/DiagnosticCard.test.tsx\').exists() else 1)"'
        ],
    )

    target_probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pathlib import Path\nraise SystemExit(0 if Path('src/__tests__/DiagnosticCard.test.tsx').exists() else 1)",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    assert target_probe.returncode == 1

    result = integrate_task(backlog, "TASK-PREMERGE-CWD")

    assert result["status"] == "INTEGRATED"
    pre_merge = read_validation_results(repo, "TASK-PREMERGE-CWD", "task-pre-merge")
    assert pre_merge["status"] == "PASS"
    assert pre_merge["cwd"] != str(repo.resolve())


def test_integrate_uses_current_branch_diff_after_amended_commit(tmp_path: Path) -> None:
    repo, backlog, worktree, base_commit, original_commit = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-AMENDED",
    )
    legacy_path = worktree / "tests" / "e2e" / "10-diagnostic.spec.ts"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text("legacy\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=worktree, check=True)
    subprocess.run(
        ["git", "commit", "--amend", "--no-edit"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    )
    stale_commit = git_head(repo, cwd=worktree)

    run_dir = repo / ".autodev" / "runs" / "TASK-AMENDED"
    stale_result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    stale_result["produced_commit"] = stale_commit
    stale_result["modified_paths"] = [
        "src/feature.txt",
        "tests/e2e/10-diagnostic.spec.ts",
    ]
    (run_dir / "result.json").write_text(
        json.dumps(stale_result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "diff.patch").write_text(
        "diff --git a/tests/e2e/10-diagnostic.spec.ts b/tests/e2e/10-diagnostic.spec.ts\n",
        encoding="utf-8",
    )

    legacy_path.unlink()
    subprocess.run(["git", "add", "-A"], cwd=worktree, check=True)
    subprocess.run(
        ["git", "commit", "--amend", "--no-edit"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    )
    current_commit = git_head(repo, cwd=worktree)
    assert current_commit != stale_commit

    commit_all(repo, "record stale diff artifacts")

    result = integrate_task(backlog, "TASK-AMENDED")

    integration_dir = run_dir / "integration"
    current_paths = json.loads((integration_dir / "current-paths.json").read_text(encoding="utf-8"))
    current_name_status = (integration_dir / "current-name-status.txt").read_text(encoding="utf-8")
    current_patch = (integration_dir / "current-diff.patch").read_text(encoding="utf-8")

    assert result["status"] == "INTEGRATED"
    assert result["produced_commit"] == current_commit
    assert result["produced_commit"] != stale_commit
    assert current_paths["produced_commit"] == current_commit
    assert current_paths["modified_paths"] == ["src/feature.txt"]
    assert "tests/e2e/10-diagnostic.spec.ts" not in current_name_status
    assert "tests/e2e/10-diagnostic.spec.ts" not in current_patch
    assert "src/feature.txt" in current_name_status


def test_integrate_rejects_current_out_of_scope_diff_even_if_old_artifacts_are_clean(tmp_path: Path) -> None:
    repo, backlog, worktree, base_commit, _ = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-OOS-CURRENT",
    )
    current_forbidden = worktree / "src-tauri" / "tests" / "integration_diagnostic.rs"
    current_forbidden.parent.mkdir(parents=True, exist_ok=True)
    current_forbidden.write_text("forbidden\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=worktree, check=True)
    subprocess.run(
        ["git", "commit", "--amend", "--no-edit"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    )

    run_dir = repo / ".autodev" / "runs" / "TASK-OOS-CURRENT"
    clean_result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    clean_result["base_commit"] = base_commit
    clean_result["produced_commit"] = git_head(repo, cwd=worktree)
    clean_result["modified_paths"] = ["src/feature.txt"]
    (run_dir / "result.json").write_text(
        json.dumps(clean_result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    commit_all(repo, "record misleading clean artifacts")

    with pytest.raises(IntegrateTaskError, match="hors périmètre"):
        integrate_task(backlog, "TASK-OOS-CURRENT")

    current_paths = json.loads(
        (run_dir / "integration" / "current-paths.json").read_text(encoding="utf-8")
    )
    assert "src-tauri/tests/integration_diagnostic.rs" in current_paths["modified_paths"]


def test_integrate_rolls_back_when_post_validation_fails(tmp_path: Path) -> None:
    repo, backlog, worktree, _, _ = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-VALIDATION-FAIL",
        validation_commands=[
            f'{sys.executable} -c "import subprocess\nbranch = subprocess.run([\'git\', \'rev-parse\', \'--abbrev-ref\', \'HEAD\'], check=True, capture_output=True, text=True).stdout.strip()\nraise SystemExit(0 if branch.startswith(\'autodev/\') else 1)"'
        ],
    )
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    with pytest.raises(IntegrateTaskError, match="validation TASK a échoué après la fusion temporaire"):
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


def test_integrate_accepts_identical_baseline_failures(tmp_path: Path) -> None:
    repo, backlog, _, _, _ = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-BASELINE-PERSISTENT",
    )
    write_quality_gates(
        repo,
        full_commands=[
            f'{sys.executable} -c "import sys\nsys.stderr.write(\'Error: Cannot find module \\\\\'@testing-library/dom\\\\\'\\\\n\')\nraise SystemExit(1)"'
        ],
    )
    commit_all(repo, "configure persistent baseline failure")

    result = integrate_task(backlog, "TASK-BASELINE-PERSISTENT")

    assert result["status"] == "INTEGRATED"
    assert result["comparison_status"] == "PASS_WITH_BASELINE_FAILURES"
    assert result["new_regression_count"] == 0


def test_integrate_rolls_back_on_new_full_regression(tmp_path: Path) -> None:
    repo, backlog, _, _, _ = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-NEW-REGRESSION",
    )
    write_quality_gates(
        repo,
        full_commands=[
            f'{sys.executable} -c "from pathlib import Path\nimport sys\nsys.stderr.write(\'FAIL merged regression\\\\n\' if Path(\'src/feature.txt\').exists() else \'\')\nraise SystemExit(1 if Path(\'src/feature.txt\').exists() else 0)"'
        ],
    )
    commit_all(repo, "configure new regression detector")
    head_before = git_head(repo)

    with pytest.raises(IntegrateTaskError, match="nouvelle signature d'échec"):
        integrate_task(backlog, "TASK-NEW-REGRESSION")

    assert git_head(repo) == head_before
    result = integration_result(repo, "TASK-NEW-REGRESSION")
    assert result["status"] == "FAILED"
    assert result["comparison_status"] == "FAIL_NEW_REGRESSION"
    assert result["new_regression_count"] == 1


def test_integrate_rejects_when_task_validation_fails_even_with_same_baseline(tmp_path: Path) -> None:
    repo, backlog, _, _, _ = prepare_repo_for_integration(
        tmp_path,
        task_id="TASK-POST-TASK-FAIL",
        validation_commands=[
            f'{sys.executable} -c "import subprocess\nbranch = subprocess.run([\'git\', \'rev-parse\', \'--abbrev-ref\', \'HEAD\'], check=True, capture_output=True, text=True).stdout.strip()\nraise SystemExit(0 if branch.startswith(\'autodev/\') else 1)"'
        ],
    )
    write_quality_gates(
        repo,
        full_commands=[
            f'{sys.executable} -c "import sys\nsys.stderr.write(\'Error: Cannot find module \\\\\'@testing-library/dom\\\\\'\\\\n\')\nraise SystemExit(1)"'
        ],
    )
    commit_all(repo, "configure stable baseline and task failure")
    head_before = git_head(repo)

    with pytest.raises(IntegrateTaskError, match="validation TASK a échoué après la fusion temporaire"):
        integrate_task(backlog, "TASK-POST-TASK-FAIL")

    assert git_head(repo) == head_before
    result = integration_result(repo, "TASK-POST-TASK-FAIL")
    assert result["status"] == "FAILED"
    assert result["task_validation_status"] == "FAIL"


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
