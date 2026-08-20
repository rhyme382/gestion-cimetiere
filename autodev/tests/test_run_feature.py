from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from autodev.run_feature import (
    RunFeatureError,
    determine_task_resume_action,
    detect_selection_cycle,
    run_feature,
)

from test_task_runner import commit_all, init_repo, make_task, write_backlog


def write_integration_result(repo: Path, task_id: str, status: str = "INTEGRATED") -> None:
    path = repo / ".autodev" / "runs" / task_id / "integration" / "integration-result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"task_id": task_id, "status": status}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_review_result(repo: Path, task_id: str, verdict: str) -> None:
    path = repo / ".autodev" / "runs" / task_id / "review" / "review-result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"task_id": task_id, "verdict": verdict}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_run_result(
    repo: Path,
    task_id: str,
    *,
    base_commit: str,
    worktree: Path | None = None,
    produced_commit: str | None = None,
) -> None:
    path = repo / ".autodev" / "runs" / task_id / "result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": task_id,
        "status": "success",
        "base_commit": base_commit,
        "worktree": str(worktree or (repo / ".autodev" / "worktrees" / task_id)),
        "produced_commit": produced_commit,
        "modified_paths": ["src/example.py"] if produced_commit else [],
        "validations": [],
        "validation_summary": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_task_record(repo: Path, task_id: str, *, backlog: Path, base_commit: str, worktree: Path) -> None:
    path = repo / ".autodev" / "runs" / task_id / "task.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "backlog": str(backlog),
        "task": make_task(task_id),
        "branch": f"autodev/{task_id}",
        "worktree": str(worktree),
        "base_commit": base_commit,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_head(repo: Path, ref: str = "HEAD", *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=cwd or repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def create_task_workspace(
    repo: Path,
    backlog: Path,
    task_id: str,
    *,
    create_branch: bool = True,
    create_worktree: bool = True,
    make_commit: bool = False,
    write_result_artifact: bool = True,
    produced_commit_in_result: bool = True,
) -> tuple[str, Path, str | None]:
    branch = f"autodev/{task_id}"
    worktree = repo / ".autodev" / "worktrees" / task_id
    base_commit = git_head(repo)

    if create_branch:
        subprocess.run(["git", "branch", branch, base_commit], cwd=repo, check=True)
    if create_worktree:
        subprocess.run(["git", "worktree", "add", str(worktree), branch], cwd=repo, check=True)
    elif worktree.exists():
        raise AssertionError("create_worktree=False suppose un chemin absent")

    produced_commit = None
    if make_commit:
        target = worktree if create_worktree else repo
        (target / "src").mkdir(parents=True, exist_ok=True)
        (target / "src" / f"{task_id.lower()}.py").write_text(f"{task_id}\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=target, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"task {task_id}"],
            cwd=target,
            check=True,
            capture_output=True,
            text=True,
        )
        produced_commit = git_head(repo, branch)

    write_task_record(repo, task_id, backlog=backlog, base_commit=base_commit, worktree=worktree)
    if write_result_artifact:
        write_run_result(
            repo,
            task_id,
            base_commit=base_commit,
            worktree=worktree,
            produced_commit=produced_commit if produced_commit_in_result else None,
        )

    return base_commit, worktree, produced_commit


def summary_path(repo: Path, feature_id: str = "FEATURE-TEST") -> Path:
    return repo / ".autodev" / "runs" / "features" / feature_id / "run-feature-result.json"


def make_review_payload(task_id: str, verdict: str) -> dict[str, object]:
    return {
        "task_id": task_id,
        "verdict": verdict,
        "summary": verdict,
        "requirement_checks": [],
        "acceptance_checks": [],
        "issues": [],
        "tests": {"status": "PASS", "details": []},
        "scope": {"status": "PASS", "unexpected_paths": []},
    }


def build_runners(
    repo: Path,
    *,
    review_sequences: dict[str, list[str]] | None = None,
    fail_run_task: str | None = None,
    capture: dict[str, list[str]] | None = None,
):
    capture = capture or {"run": [], "review": [], "correct": [], "integrate": []}
    review_indices = {task_id: 0 for task_id in (review_sequences or {})}

    def fake_run_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        capture["run"].append(task_id)
        if fail_run_task == task_id:
            raise RuntimeError(f"boom {task_id}")
        return {"task_id": task_id, "status": "success"}

    def fake_review_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        capture["review"].append(task_id)
        verdicts = (review_sequences or {}).get(task_id, ["APPROVED"])
        index = review_indices.get(task_id, 0)
        if index >= len(verdicts):
            verdict = verdicts[-1]
        else:
            verdict = verdicts[index]
        review_indices[task_id] = index + 1
        write_review_result(repo, task_id, verdict)
        return make_review_payload(task_id, verdict)

    def fake_correct_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        capture["correct"].append(task_id)
        return {"task_id": task_id, "status": "success"}

    def fake_integrate_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        capture["integrate"].append(task_id)
        write_integration_result(repo, task_id)
        return {"task_id": task_id, "status": "INTEGRATED"}

    return capture, fake_run_task, fake_review_task, fake_correct_task, fake_integrate_task


def prepare_backlog(tmp_path: Path, tasks: list[dict[str, object]]) -> tuple[Path, Path]:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, tasks)
    commit_all(repo, "add backlog")
    return repo, backlog


def test_selects_first_task_without_dependency(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(
        tmp_path,
        [make_task("TASK-1"), make_task("TASK-2", depends_on=["TASK-1"])],
    )
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(repo)

    result = run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    assert capture["run"] == ["TASK-1", "TASK-2"]
    assert result["status"] == "COMPLETED"


def test_dependent_task_is_not_selected_too_early(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(
        tmp_path,
        [make_task("TASK-DEP"), make_task("TASK-MAIN", depends_on=["TASK-DEP"])],
    )
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(repo)

    run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    assert capture["run"] == ["TASK-DEP", "TASK-MAIN"]


def test_run_feature_selects_dependent_task_when_dependency_is_already_integrated(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(
        tmp_path,
        [make_task("TASK-DEP"), make_task("TASK-MAIN", depends_on=["TASK-DEP"])],
    )
    write_integration_result(repo, "TASK-DEP")
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(repo)

    result = run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    assert capture["run"] == ["TASK-MAIN"]
    assert result["tasks_integrated"] == ["TASK-DEP", "TASK-MAIN"]


def test_already_integrated_task_is_skipped(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(
        tmp_path,
        [make_task("TASK-DONE"), make_task("TASK-TODO")],
    )
    write_integration_result(repo, "TASK-DONE")
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(repo)

    result = run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    assert capture["run"] == ["TASK-TODO"]
    assert result["tasks_integrated"] == ["TASK-DONE", "TASK-TODO"]


def test_failed_integration_artifact_does_not_mark_task_done(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(
        tmp_path,
        [make_task("TASK-DEP"), make_task("TASK-MAIN", depends_on=["TASK-DEP"])],
    )
    write_integration_result(repo, "TASK-DEP", status="FAILED")
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(repo)

    result = run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    assert capture["run"] == ["TASK-DEP", "TASK-MAIN"]
    assert result["tasks_integrated"] == ["TASK-DEP", "TASK-MAIN"]


def test_approved_leads_to_integration(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-OK")])
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(repo)

    result = run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    assert capture["integrate"] == ["TASK-OK"]
    assert result["status"] == "COMPLETED"


def test_correction_required_leads_to_correct_task(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-FIX")])
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(
        repo,
        review_sequences={"TASK-FIX": ["CORRECTION_REQUIRED", "HUMAN_REVIEW_REQUIRED"]},
    )

    result = run_feature(
        backlog,
        max_corrections=3,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    assert capture["correct"] == ["TASK-FIX"]
    assert result["status"] == "HUMAN_REVIEW_REQUIRED"


def test_correction_then_approved_integrates_task(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-LOOP")])
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(
        repo,
        review_sequences={"TASK-LOOP": ["CORRECTION_REQUIRED", "APPROVED"]},
    )

    result = run_feature(
        backlog,
        max_corrections=3,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    assert capture["correct"] == ["TASK-LOOP"]
    assert capture["integrate"] == ["TASK-LOOP"]
    assert result["status"] == "COMPLETED"


def test_max_corrections_exceeded_stops_with_human_review(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-MAX")])
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(
        repo,
        review_sequences={"TASK-MAX": ["CORRECTION_REQUIRED", "CORRECTION_REQUIRED"]},
    )

    result = run_feature(
        backlog,
        max_corrections=1,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    assert capture["correct"] == ["TASK-MAX"]
    assert result["status"] == "HUMAN_REVIEW_REQUIRED"


def test_human_review_required_stops_graph(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-HUMAN")])
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(
        repo,
        review_sequences={"TASK-HUMAN": ["HUMAN_REVIEW_REQUIRED"]},
    )

    result = run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    assert capture["integrate"] == []
    assert result["status"] == "HUMAN_REVIEW_REQUIRED"


def test_determine_resume_action_for_new_task_is_implement(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-NEW")])

    decision = determine_task_resume_action(repo_root=repo, task_id="TASK-NEW")

    assert backlog.exists()
    assert decision.action == "IMPLEMENT"


def test_determine_resume_action_branch_worktree_commit_without_review_is_review(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-REVIEW")])
    create_task_workspace(repo, backlog, "TASK-REVIEW", make_commit=True, produced_commit_in_result=False)

    decision = determine_task_resume_action(repo_root=repo, task_id="TASK-REVIEW")

    assert decision.action == "REVIEW"


def test_determine_resume_action_correction_required_is_correct(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-FIX")])
    create_task_workspace(repo, backlog, "TASK-FIX", make_commit=True)
    write_review_result(repo, "TASK-FIX", "CORRECTION_REQUIRED")

    decision = determine_task_resume_action(repo_root=repo, task_id="TASK-FIX")

    assert decision.action == "CORRECT"


def test_determine_resume_action_approved_is_integrate(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-APPROVED")])
    create_task_workspace(repo, backlog, "TASK-APPROVED", make_commit=True)
    write_review_result(repo, "TASK-APPROVED", "APPROVED")

    decision = determine_task_resume_action(repo_root=repo, task_id="TASK-APPROVED")

    assert decision.action == "INTEGRATE"


def test_determine_resume_action_integrated_is_completed(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-DONE")])
    create_task_workspace(repo, backlog, "TASK-DONE", make_commit=True)
    write_review_result(repo, "TASK-DONE", "APPROVED")
    write_integration_result(repo, "TASK-DONE")

    decision = determine_task_resume_action(repo_root=repo, task_id="TASK-DONE")

    assert decision.action == "COMPLETED"


def test_determine_resume_action_human_review_required_stops(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-HUMAN")])
    create_task_workspace(repo, backlog, "TASK-HUMAN", make_commit=True)
    write_review_result(repo, "TASK-HUMAN", "HUMAN_REVIEW_REQUIRED")

    decision = determine_task_resume_action(repo_root=repo, task_id="TASK-HUMAN")

    assert decision.action == "HUMAN_REVIEW"


def test_resume_does_not_rerun_task_when_branch_exists(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-RESUME")])
    call_order: list[str] = []

    def fake_run_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        call_order.append(f"run:{task_id}")
        create_task_workspace(repo, backlog, task_id, make_commit=True)
        return {"task_id": task_id, "status": "success"}

    def fake_review_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        call_order.append(f"review:{task_id}")
        verdict = "HUMAN_REVIEW_REQUIRED" if call_order.count(f"review:{task_id}") == 1 else "APPROVED"
        write_review_result(repo, task_id, verdict)
        return make_review_payload(task_id, verdict)

    def fake_correct_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        raise AssertionError("correct-task ne doit pas être appelé")

    def fake_integrate_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        call_order.append(f"integrate:{task_id}")
        write_integration_result(repo, task_id)
        return {"task_id": task_id, "status": "INTEGRATED"}

    first = run_feature(
        backlog,
        run_task_fn=fake_run_task,
        review_task_fn=fake_review_task,
        correct_task_fn=fake_correct_task,
        integrate_task_fn=fake_integrate_task,
    )
    assert first["status"] == "HUMAN_REVIEW_REQUIRED"

    resumed = run_feature(
        backlog,
        resume=True,
        run_task_fn=lambda **_: (_ for _ in ()).throw(AssertionError("run-task ne doit pas être rejoué")),
        review_task_fn=fake_review_task,
        correct_task_fn=fake_correct_task,
        integrate_task_fn=fake_integrate_task,
    )

    assert resumed["status"] == "HUMAN_REVIEW_REQUIRED"
    assert call_order == ["run:TASK-RESUME", "review:TASK-RESUME"]


def test_resume_routes_to_review_without_rerunning_task(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-REVIEW-RESUME")])
    call_order: list[str] = []

    def failing_run_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        call_order.append(f"run:{task_id}")
        create_task_workspace(repo, backlog, task_id, make_commit=True, produced_commit_in_result=False)
        raise RuntimeError("implémentation interrompue après commit")

    first = run_feature(
        backlog,
        run_task_fn=failing_run_task,
        review_task_fn=lambda **_: (_ for _ in ()).throw(AssertionError("review ne doit pas tourner au premier passage")),
        correct_task_fn=lambda **_: {"task_id": "TASK-REVIEW-RESUME", "status": "success"},
        integrate_task_fn=lambda **_: {"task_id": "TASK-REVIEW-RESUME", "status": "INTEGRATED"},
    )
    assert first["status"] == "FAILED"

    def review_on_resume(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        call_order.append(f"review:{task_id}")
        write_review_result(repo, task_id, "APPROVED")
        return make_review_payload(task_id, "APPROVED")

    def integrate_on_resume(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        call_order.append(f"integrate:{task_id}")
        write_integration_result(repo, task_id)
        return {"task_id": task_id, "status": "INTEGRATED"}

    resumed = run_feature(
        backlog,
        resume=True,
        run_task_fn=lambda **_: (_ for _ in ()).throw(AssertionError("run-task ne doit pas être rejoué")),
        review_task_fn=review_on_resume,
        correct_task_fn=lambda **_: {"task_id": "TASK-REVIEW-RESUME", "status": "success"},
        integrate_task_fn=integrate_on_resume,
    )

    assert resumed["status"] == "COMPLETED"
    assert call_order == [
        "run:TASK-REVIEW-RESUME",
        "review:TASK-REVIEW-RESUME",
        "integrate:TASK-REVIEW-RESUME",
    ]


def test_correction_then_review_then_integration(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-LOOP")])
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(
        repo,
        review_sequences={"TASK-LOOP": ["CORRECTION_REQUIRED", "APPROVED"]},
    )

    result = run_feature(
        backlog,
        max_corrections=3,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    assert capture["run"] == ["TASK-LOOP"]
    assert capture["review"] == ["TASK-LOOP", "TASK-LOOP"]
    assert capture["correct"] == ["TASK-LOOP"]
    assert capture["integrate"] == ["TASK-LOOP"]
    assert result["status"] == "COMPLETED"


def test_determine_resume_action_inconsistent_state_is_explicit_error(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-BROKEN")])
    base_commit, worktree, _ = create_task_workspace(
        repo,
        backlog,
        "TASK-BROKEN",
        create_worktree=False,
        make_commit=False,
    )
    assert worktree == repo / ".autodev" / "worktrees" / "TASK-BROKEN"
    write_run_result(repo, "TASK-BROKEN", base_commit=base_commit, worktree=worktree)
    write_review_result(repo, "TASK-BROKEN", "CORRECTION_REQUIRED")

    decision = determine_task_resume_action(repo_root=repo, task_id="TASK-BROKEN")

    assert decision.action == "INVALID_STATE"
    assert "worktree absent" in str(decision.reason)


def test_resume_invalid_json_fails_cleanly(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-JSON")])
    review_written = False

    def fake_run_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        create_task_workspace(repo, backlog, task_id, make_commit=True)
        return {"task_id": task_id, "status": "success"}

    def fake_review_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        nonlocal review_written
        if not review_written:
            write_review_result(repo, task_id, "HUMAN_REVIEW_REQUIRED")
            review_written = True
        return make_review_payload(task_id, "HUMAN_REVIEW_REQUIRED")

    first = run_feature(
        backlog,
        run_task_fn=fake_run_task,
        review_task_fn=fake_review_task,
        correct_task_fn=lambda **_: {"task_id": "TASK-JSON", "status": "success"},
        integrate_task_fn=lambda **_: {"task_id": "TASK-JSON", "status": "INTEGRATED"},
    )
    assert first["status"] == "HUMAN_REVIEW_REQUIRED"

    review_path = repo / ".autodev" / "runs" / "TASK-JSON" / "review" / "review-result.json"
    review_path.write_text("{ invalid json\n", encoding="utf-8")

    with pytest.raises(RunFeatureError, match="JSON invalide"):
        run_feature(
            backlog,
            resume=True,
            run_task_fn=lambda **_: {"task_id": "TASK-JSON", "status": "success"},
            review_task_fn=lambda **_: {"task_id": "TASK-JSON", "verdict": "APPROVED"},
            correct_task_fn=lambda **_: {"task_id": "TASK-JSON", "status": "success"},
            integrate_task_fn=lambda **_: {"task_id": "TASK-JSON", "status": "INTEGRATED"},
        )


def test_approved_without_commit_is_invalid_state(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-NOCOMMIT")])
    create_task_workspace(repo, backlog, "TASK-NOCOMMIT", make_commit=False)
    write_review_result(repo, "TASK-NOCOMMIT", "APPROVED")

    decision = determine_task_resume_action(repo_root=repo, task_id="TASK-NOCOMMIT")

    assert decision.action == "INVALID_STATE"
    assert "sans commit produit" in str(decision.reason)


def test_worktree_without_branch_is_invalid_state(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-WT")])
    worktree = repo / ".autodev" / "worktrees" / "TASK-WT"
    worktree.mkdir(parents=True)
    base_commit = git_head(repo)
    write_task_record(repo, "TASK-WT", backlog=backlog, base_commit=base_commit, worktree=worktree)
    write_run_result(repo, "TASK-WT", base_commit=base_commit, worktree=worktree)

    decision = determine_task_resume_action(repo_root=repo, task_id="TASK-WT")

    assert decision.action == "INVALID_STATE"
    assert "branche absente" in str(decision.reason)


def test_node_error_is_recorded(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-ERR")])
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(
        repo,
        fail_run_task="TASK-ERR",
    )

    result = run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    payload = json.loads(summary_path(repo).read_text(encoding="utf-8"))
    assert capture["review"] == []
    assert result["status"] == "FAILED"
    assert payload["status"] == "FAILED"
    assert "boom TASK-ERR" in payload["error"]


def test_integration_failure_stops_run_feature_after_single_attempt(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-INTEGRATE-FAIL")])
    call_order: list[str] = []

    def fake_run_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        call_order.append(f"run:{task_id}")
        create_task_workspace(repo, backlog, task_id, make_commit=True)
        return {"task_id": task_id, "status": "success"}

    def fake_review_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        call_order.append(f"review:{task_id}")
        write_review_result(repo, task_id, "APPROVED")
        return make_review_payload(task_id, "APPROVED")

    def fake_integrate_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        call_order.append(f"integrate:{task_id}")
        return {"task_id": task_id, "status": "FAILED", "error": "merge blocked"}

    result = run_feature(
        backlog,
        run_task_fn=fake_run_task,
        review_task_fn=fake_review_task,
        correct_task_fn=lambda **_: {"task_id": "TASK-INTEGRATE-FAIL", "status": "success"},
        integrate_task_fn=fake_integrate_task,
    )

    assert result["status"] == "FAILED"
    assert result["current_task_id"] == "TASK-INTEGRATE-FAIL"
    assert call_order == [
        "run:TASK-INTEGRATE-FAIL",
        "review:TASK-INTEGRATE-FAIL",
        "integrate:TASK-INTEGRATE-FAIL",
    ]


def test_resume_can_retry_failed_integration_in_new_invocation(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-RESUME-INTEGRATE")])
    call_order: list[str] = []

    def fake_run_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        call_order.append(f"run:{task_id}")
        create_task_workspace(repo, backlog, task_id, make_commit=True)
        return {"task_id": task_id, "status": "success"}

    def fake_review_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        call_order.append(f"review:{task_id}")
        write_review_result(repo, task_id, "APPROVED")
        return make_review_payload(task_id, "APPROVED")

    def failing_integrate(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        call_order.append(f"integrate-fail:{task_id}")
        return {"task_id": task_id, "status": "FAILED", "error": "merge blocked"}

    first = run_feature(
        backlog,
        run_task_fn=fake_run_task,
        review_task_fn=fake_review_task,
        correct_task_fn=lambda **_: {"task_id": "TASK-RESUME-INTEGRATE", "status": "success"},
        integrate_task_fn=failing_integrate,
    )
    assert first["status"] == "FAILED"

    def passing_integrate(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        call_order.append(f"integrate-ok:{task_id}")
        write_integration_result(repo, task_id)
        return {"task_id": task_id, "status": "INTEGRATED"}

    resumed = run_feature(
        backlog,
        resume=True,
        run_task_fn=lambda **_: (_ for _ in ()).throw(AssertionError("run-task ne doit pas être rejoué")),
        review_task_fn=lambda **_: (_ for _ in ()).throw(AssertionError("review ne doit pas être rejouée")),
        correct_task_fn=lambda **_: {"task_id": "TASK-RESUME-INTEGRATE", "status": "success"},
        integrate_task_fn=passing_integrate,
    )

    assert resumed["status"] == "COMPLETED"
    assert call_order == [
        "run:TASK-RESUME-INTEGRATE",
        "review:TASK-RESUME-INTEGRATE",
        "integrate-fail:TASK-RESUME-INTEGRATE",
        "integrate-ok:TASK-RESUME-INTEGRATE",
    ]


def test_detect_selection_cycle_reports_repeated_task_action_error() -> None:
    message = detect_selection_cycle(
        state={
            "selection_signatures": ["TASK-X|INTEGRATE|merge blocked"],
        },
        task_id="TASK-X",
        action="INTEGRATE",
        error="merge blocked",
    )

    assert message == "Cycle de workflow détecté pour TASK-X à l'étape INTEGRATE."


def test_injected_runners_avoid_real_agent_execution(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-INJECTED")])
    capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(repo)

    result = run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )

    assert capture["run"] == ["TASK-INJECTED"]
    assert capture["review"] == ["TASK-INJECTED"]
    assert result["status"] == "COMPLETED"
