from __future__ import annotations

import json
from pathlib import Path

from autodev.run_feature import run_feature

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


def test_resume_after_checkpoint_continues_remaining_tasks(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-1"), make_task("TASK-2")])
    first_capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(
        repo,
        review_sequences={"TASK-1": ["APPROVED"], "TASK-2": ["HUMAN_REVIEW_REQUIRED"]},
    )

    first = run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )
    assert first["status"] == "HUMAN_REVIEW_REQUIRED"
    assert first_capture["run"] == ["TASK-1", "TASK-2"]

    second_capture, run_fn2, review_fn2, correct_fn2, integrate_fn2 = build_runners(
        repo,
        review_sequences={"TASK-2": ["APPROVED"]},
    )
    resumed = run_feature(
        backlog,
        resume=True,
        run_task_fn=run_fn2,
        review_task_fn=review_fn2,
        correct_task_fn=correct_fn2,
        integrate_task_fn=integrate_fn2,
    )

    assert second_capture["run"] == ["TASK-2"]
    assert resumed["status"] == "COMPLETED"


def test_integrated_task_is_not_replayed_after_resume(tmp_path: Path) -> None:
    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-A"), make_task("TASK-B")])
    write_integration_result(repo, "TASK-A")

    first_capture, run_fn, review_fn, correct_fn, integrate_fn = build_runners(
        repo,
        review_sequences={"TASK-B": ["HUMAN_REVIEW_REQUIRED"]},
    )

    first = run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=correct_fn,
        integrate_task_fn=integrate_fn,
    )
    assert first["status"] == "HUMAN_REVIEW_REQUIRED"
    assert first_capture["run"] == ["TASK-B"]

    capture, run_fn2, review_fn2, correct_fn2, integrate_fn2 = build_runners(
        repo,
        review_sequences={"TASK-B": ["APPROVED"]},
    )

    result = run_feature(
        backlog,
        resume=True,
        run_task_fn=run_fn2,
        review_task_fn=review_fn2,
        correct_task_fn=correct_fn2,
        integrate_task_fn=integrate_fn2,
    )

    assert capture["run"] == ["TASK-B"]
    assert result["tasks_integrated"] == ["TASK-A", "TASK-B"]


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
