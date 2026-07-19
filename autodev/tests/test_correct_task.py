from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pytest

import autodev.git_tools as git_tools_module
from autodev.correct_task import correct_task
from autodev.run_feature import run_feature

from test_run_feature import create_task_workspace, git_head
from test_task_runner import commit_all, init_repo, make_task, write_backlog


def write_review_result(repo: Path, task_id: str, verdict: str = "CORRECTION_REQUIRED") -> None:
    path = repo / ".autodev" / "runs" / task_id / "review" / "review-result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": task_id,
        "verdict": verdict,
        "summary": verdict,
        "issues": [{"severity": "medium", "message": "Corriger le périmètre et les tests."}],
        "requirement_checks": [],
        "acceptance_checks": [],
        "tests": {"status": "FAIL", "details": []},
        "scope": {"status": "FAIL", "unexpected_paths": ["package.json"]},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_correction_case(
    tmp_path: Path,
    *,
    allowed_paths: list[str] | None = None,
) -> tuple[Path, Path, Path, str]:
    repo = init_repo(tmp_path)
    (repo / "package.json").write_text('{"name":"demo","version":"1.0.0"}\n', encoding="utf-8")
    (repo / "package-lock.json").write_text('{"lockfileVersion":3}\n', encoding="utf-8")
    (repo / "tests" / "e2e").mkdir(parents=True, exist_ok=True)
    (repo / "tests" / "e2e" / "10-diagnostic.spec.ts").write_text("// e2e\n", encoding="utf-8")
    (repo / "src-tauri" / "tests").mkdir(parents=True, exist_ok=True)
    (repo / "src-tauri" / "tests" / "integration_diagnostic.rs").write_text("// rust\n", encoding="utf-8")

    tasks = [
        make_task("TASK-PILOT-002"),
        make_task("TASK-PILOT-003"),
    ]
    tasks[0]["allowed_paths"] = allowed_paths or ["src"]
    if "package.json" in tasks[0]["allowed_paths"] or "package-lock.json" in tasks[0]["allowed_paths"]:
        tasks[0]["dependency_change_reason"] = (
            "Ce scénario de test couvre explicitement une évolution de manifeste déclarée."
        )
    tasks[1]["title"] = "Étape suivante"
    backlog = write_backlog(repo, tasks)
    commit_all(repo, "prepare correction fixture")

    base_commit, worktree, produced_commit = create_task_workspace(
        repo,
        backlog,
        "TASK-PILOT-002",
        make_commit=True,
    )
    assert produced_commit is not None
    write_review_result(repo, "TASK-PILOT-002")
    return repo, backlog, worktree, produced_commit


def make_claude_runner(
    actions: list[Callable[[Path], None]],
    prompts: list[str] | None = None,
) -> Callable[..., dict[str, object]]:
    prompts = prompts if prompts is not None else []
    call_index = 0

    def runner(*, worktree: Path, prompt: str) -> dict[str, object]:
        nonlocal call_index
        prompts.append(prompt)
        if call_index >= len(actions):
            raise AssertionError("Aucune action Claude simulée restante")
        actions[call_index](worktree)
        call_index += 1
        return {
            "command": ["fake-claude"],
            "returncode": 0,
            "stdout": f"attempt {call_index}",
            "stderr": "",
        }

    return runner


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_correction_within_scope_only_succeeds_and_writes_artifacts(tmp_path: Path) -> None:
    repo, backlog, worktree, produced_commit = prepare_correction_case(tmp_path)

    def change_src(target: Path) -> None:
        (target / "src" / "task-pilot-002.py").write_text("fixed\n", encoding="utf-8")

    result = correct_task(backlog, "TASK-PILOT-002", claude_runner=make_claude_runner([change_src]))

    correction_dir = repo / ".autodev" / "runs" / "TASK-PILOT-002" / "corrections" / "01"
    correction_result = read_json(correction_dir / "correction-result.json")
    assert result["status"] == "success"
    assert result["produced_commit"] != produced_commit
    assert result["restored_paths"] == []
    assert result["remaining_allowed_paths"] == ["src/task-pilot-002.py"]
    assert correction_result["before_commit"] == produced_commit
    assert (correction_dir / "before-commit.txt").read_text(encoding="utf-8").strip() == produced_commit
    assert (correction_dir / "modified-paths.json").is_file()
    assert (correction_dir / "out-of-scope-paths.json").is_file()
    assert (correction_dir / "restored-paths.json").is_file()


def test_correction_with_authorized_and_out_of_scope_restores_only_out_of_scope(tmp_path: Path) -> None:
    _, backlog, worktree, _ = prepare_correction_case(tmp_path)

    def mixed_changes(target: Path) -> None:
        (target / "src" / "task-pilot-002.py").write_text("allowed update\n", encoding="utf-8")
        (target / "package.json").write_text('{"name":"demo","version":"2.0.0"}\n', encoding="utf-8")

    result = correct_task(backlog, "TASK-PILOT-002", claude_runner=make_claude_runner([mixed_changes]))

    assert result["status"] == "success"
    assert result["restored_paths"] == ["package.json"]
    assert result["modified_paths"] == ["package.json", "src/task-pilot-002.py"]
    assert result["remaining_allowed_paths"] == ["src/task-pilot-002.py"]
    assert (worktree / "package.json").read_text(encoding="utf-8") == '{"name":"demo","version":"1.0.0"}\n'
    assert (worktree / "src" / "task-pilot-002.py").read_text(encoding="utf-8") == "allowed update\n"


def test_authorized_changes_are_preserved_after_restoration(tmp_path: Path) -> None:
    repo, backlog, worktree, _ = prepare_correction_case(tmp_path)

    def mixed_changes(target: Path) -> None:
        (target / "src" / "task-pilot-002.py").write_text("kept\n", encoding="utf-8")
        (target / "package-lock.json").write_text('{"lockfileVersion":4}\n', encoding="utf-8")

    correct_task(backlog, "TASK-PILOT-002", claude_runner=make_claude_runner([mixed_changes]))

    branch_head = git_head(repo, "autodev/TASK-PILOT-002")
    assert branch_head == git_head(repo, cwd=worktree)
    assert (worktree / "src" / "task-pilot-002.py").read_text(encoding="utf-8") == "kept\n"
    assert (worktree / "package-lock.json").read_text(encoding="utf-8") == '{"lockfileVersion":3}\n'


def test_correction_never_uses_global_git_reset_hard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, backlog, _, _ = prepare_correction_case(tmp_path)
    original_run_git = git_tools_module.run_git
    recorded_args: list[list[str]] = []

    def recording_run_git(repo_root: Path, args: list[str], cwd: Path | None = None):
        recorded_args.append(args)
        return original_run_git(repo_root, args, cwd=cwd)

    monkeypatch.setattr(git_tools_module, "run_git", recording_run_git)

    def out_of_scope_only(target: Path) -> None:
        (target / "package.json").write_text('{"name":"demo","version":"9.0.0"}\n', encoding="utf-8")

    correct_task(
        backlog,
        "TASK-PILOT-002",
        claude_runner=make_claude_runner([out_of_scope_only, lambda _: None]),
    )

    assert not any(args[:2] == ["reset", "--hard"] for args in recorded_args)


def test_no_allowed_changes_after_restore_triggers_single_retry_with_strict_prompt(tmp_path: Path) -> None:
    _, backlog, worktree, _ = prepare_correction_case(tmp_path)
    prompts: list[str] = []

    def first_attempt(target: Path) -> None:
        (target / "package.json").write_text('{"name":"demo","version":"5.0.0"}\n', encoding="utf-8")

    def second_attempt(target: Path) -> None:
        (target / "src" / "task-pilot-002.py").write_text("retry success\n", encoding="utf-8")

    result = correct_task(
        backlog,
        "TASK-PILOT-002",
        claude_runner=make_claude_runner([first_attempt, second_attempt], prompts),
    )

    assert result["status"] == "success"
    assert len(prompts) == 2
    assert "PÉRIMÈTRE STRICT" in prompts[0]
    assert "TASK-PILOT-003 : Étape suivante" in prompts[0]
    assert "Ces tâches seront exécutées séparément. Ne les implémente pas maintenant." in prompts[0]
    assert "Des fichiers hors périmètre ont été restaurés automatiquement" in prompts[1]
    assert "- package.json" in prompts[1]
    assert (worktree / "src" / "task-pilot-002.py").read_text(encoding="utf-8") == "retry success\n"


def test_package_json_is_rejected_when_not_allowed(tmp_path: Path) -> None:
    _, backlog, worktree, produced_commit = prepare_correction_case(tmp_path)

    def package_only(target: Path) -> None:
        (target / "package.json").write_text('{"name":"demo","version":"7.0.0"}\n', encoding="utf-8")

    result = correct_task(
        backlog,
        "TASK-PILOT-002",
        claude_runner=make_claude_runner([package_only, lambda _: None]),
    )

    assert result["status"] == "no_allowed_changes"
    assert result["produced_commit"] == produced_commit
    assert result["restored_paths"] == ["package.json"]
    assert result["remaining_allowed_paths"] == []
    assert (worktree / "package.json").read_text(encoding="utf-8") == '{"name":"demo","version":"1.0.0"}\n'


def test_package_json_is_accepted_when_explicitly_allowed(tmp_path: Path) -> None:
    _, backlog, worktree, _ = prepare_correction_case(tmp_path, allowed_paths=["src", "package.json"])

    def package_update(target: Path) -> None:
        (target / "package.json").write_text('{"name":"demo","version":"3.0.0"}\n', encoding="utf-8")

    result = correct_task(backlog, "TASK-PILOT-002", claude_runner=make_claude_runner([package_update]))

    assert result["status"] == "success"
    assert result["restored_paths"] == []
    assert result["remaining_allowed_paths"] == ["package.json"]
    assert (worktree / "package.json").read_text(encoding="utf-8") == '{"name":"demo","version":"3.0.0"}\n'


def test_run_feature_returns_human_review_required_after_max_corrections(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-LOOP")])
    commit_all(repo, "prepare backlog")

    review_calls = 0

    def fake_run_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        return {"task_id": task_id, "status": "success"}

    def fake_review_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        nonlocal review_calls
        review_calls += 1
        verdict = "CORRECTION_REQUIRED"
        path = repo / ".autodev" / "runs" / task_id / "review" / "review-result.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"task_id": task_id, "verdict": verdict}) + "\n", encoding="utf-8")
        return {"task_id": task_id, "verdict": verdict}

    def fake_correct_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        return {"task_id": task_id, "status": "no_allowed_changes"}

    def fake_integrate_task(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        return {"task_id": task_id, "status": "INTEGRATED"}

    result = run_feature(
        backlog,
        max_corrections=1,
        run_task_fn=fake_run_task,
        review_task_fn=fake_review_task,
        correct_task_fn=fake_correct_task,
        integrate_task_fn=fake_integrate_task,
    )

    assert result["status"] == "HUMAN_REVIEW_REQUIRED"
    assert result["current_task_id"] == "TASK-LOOP"
    assert review_calls == 2
