from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from autodev.planner import PlanningError, validate_backlog_consistency
from autodev.review_task import ReviewTaskError, review_task
from autodev.task_runner import run_task

from test_task_runner import commit_all, init_repo, make_task, write_backlog


def fake_claude_success_factory(filename: str = "src/reviewed.txt"):
    def fake_claude_runner(*_: object, **kwargs: object) -> dict[str, object]:
        worktree = Path(kwargs["worktree"])
        target = worktree / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("implemented\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=worktree, check=True)
        subprocess.run(
            ["git", "commit", "-m", "implement"],
            cwd=worktree,
            check=True,
            capture_output=True,
            text=True,
        )
        return {
            "command": ["claude", "-p"],
            "returncode": 0,
            "stdout": "done",
            "stderr": "",
        }

    return fake_claude_runner


def prepare_reviewable_task(tmp_path: Path, task_id: str = "TASK-REVIEW") -> tuple[Path, Path]:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task(task_id)])
    commit_all(repo, "add backlog")
    run_task(backlog, task_id, dry_run=False, claude_runner=fake_claude_success_factory())
    return repo, backlog


def write_codex_result(output_path: Path, payload: dict[str, object]) -> None:
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_review_unknown_task_raises(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-KNOWN")])
    commit_all(repo, "add backlog")

    with pytest.raises(ReviewTaskError, match="Tâche inconnue"):
        review_task(backlog, "TASK-MISSING", codex_runner=lambda **_: {})


def test_review_missing_branch_raises(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-BRANCH")])
    commit_all(repo, "add backlog")

    with pytest.raises(ReviewTaskError, match="Branche de tâche absente"):
        review_task(backlog, "TASK-BRANCH", codex_runner=lambda **_: {})


def test_review_task_records_approved_result(tmp_path: Path) -> None:
    repo, backlog = prepare_reviewable_task(tmp_path, "TASK-APPROVED")

    def fake_codex_runner(*_: object, **kwargs: object) -> dict[str, object]:
        write_codex_result(
            Path(kwargs["output_path"]),
            {
                "task_id": "TASK-APPROVED",
                "verdict": "APPROVED",
                "summary": "Tout est conforme.",
                "requirement_checks": [
                    {
                        "requirement_id": "REQ-001",
                        "status": "PASS",
                        "evidence": ["src/reviewed.txt couvre la demande."],
                    }
                ],
                "acceptance_checks": [
                    {
                        "criterion": "Accepter",
                        "status": "PASS",
                        "evidence": ["Le fichier attendu est présent."],
                    }
                ],
                "issues": [],
                "tests": {"status": "FAIL", "details": ["sera recalculé"]},
                "scope": {"status": "FAIL", "unexpected_paths": ["sera recalculé"]},
            },
        )
        return {"command": ["codex", "exec"], "returncode": 0, "stdout": "ok", "stderr": ""}

    result = review_task(backlog, "TASK-APPROVED", codex_runner=fake_codex_runner)

    assert result["verdict"] == "APPROVED"
    assert result["tests"]["status"] == "PASS"
    assert result["scope"] == {"status": "PASS", "unexpected_paths": []}
    review_dir = repo / ".autodev" / "runs" / "TASK-APPROVED" / "review"
    assert (review_dir / "review-prompt.md").is_file()
    assert (review_dir / "review-result.json").is_file()
    assert (review_dir / "codex.stdout.log").read_text(encoding="utf-8") == "ok"
    validation_results = json.loads((review_dir / "validation-results.json").read_text(encoding="utf-8"))
    assert validation_results["source"] == "recorded"


def test_review_task_forces_correction_required_when_codex_reports_failure(tmp_path: Path) -> None:
    _, backlog = prepare_reviewable_task(tmp_path, "TASK-CORRECT")

    def fake_codex_runner(*_: object, **kwargs: object) -> dict[str, object]:
        write_codex_result(
            Path(kwargs["output_path"]),
            {
                "task_id": "TASK-CORRECT",
                "verdict": "APPROVED",
                "summary": "Une correction est requise.",
                "requirement_checks": [
                    {
                        "requirement_id": "REQ-001",
                        "status": "FAIL",
                        "evidence": ["Un écart subsiste."],
                    }
                ],
                "acceptance_checks": [
                    {
                        "criterion": "Accepter",
                        "status": "PASS",
                        "evidence": ["Partiellement respecté."],
                    }
                ],
                "issues": [],
                "tests": {"status": "PASS", "details": []},
                "scope": {"status": "PASS", "unexpected_paths": []},
            },
        )
        return {"command": ["codex", "exec"], "returncode": 0, "stdout": "", "stderr": ""}

    result = review_task(backlog, "TASK-CORRECT", codex_runner=fake_codex_runner)

    assert result["verdict"] == "CORRECTION_REQUIRED"
    assert result["requirement_checks"][0]["status"] == "FAIL"


def test_review_task_reports_codex_error(tmp_path: Path) -> None:
    repo, backlog = prepare_reviewable_task(tmp_path, "TASK-CODEX-ERR")

    def fake_codex_runner(*_: object, **kwargs: object) -> dict[str, object]:
        Path(kwargs["output_path"]).write_text("", encoding="utf-8")
        return {
            "command": ["codex", "exec"],
            "returncode": 5,
            "stdout": "",
            "stderr": "codex failed",
        }

    with pytest.raises(ReviewTaskError, match="Codex a échoué"):
        review_task(backlog, "TASK-CODEX-ERR", codex_runner=fake_codex_runner)

    review_dir = repo / ".autodev" / "runs" / "TASK-CODEX-ERR" / "review"
    assert (review_dir / "codex.stderr.log").read_text(encoding="utf-8") == "codex failed"


def test_review_task_rejects_invalid_schema(tmp_path: Path) -> None:
    _, backlog = prepare_reviewable_task(tmp_path, "TASK-BAD-SCHEMA")

    def fake_codex_runner(*_: object, **kwargs: object) -> dict[str, object]:
        write_codex_result(
            Path(kwargs["output_path"]),
            {
                "task_id": "TASK-BAD-SCHEMA",
                "verdict": "APPROVED",
                "summary": "invalide",
            },
        )
        return {"command": ["codex", "exec"], "returncode": 0, "stdout": "", "stderr": ""}

    with pytest.raises(ReviewTaskError, match="structure JSON inattendue"):
        review_task(backlog, "TASK-BAD-SCHEMA", codex_runner=fake_codex_runner)


def test_review_task_reruns_validations_without_real_codex(tmp_path: Path) -> None:
    repo, backlog = prepare_reviewable_task(tmp_path, "TASK-RERUN")
    result_path = repo / ".autodev" / "runs" / "TASK-RERUN" / "result.json"
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    result_payload["validations"] = []
    result_path.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    data = json.loads(backlog.read_text(encoding="utf-8"))
    data["tasks"][0]["validation_commands"] = [f'{sys.executable} -c "print(\'rerun-ok\')"']
    backlog.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def fake_codex_runner(*_: object, **kwargs: object) -> dict[str, object]:
        write_codex_result(
            Path(kwargs["output_path"]),
            {
                "task_id": "TASK-RERUN",
                "verdict": "APPROVED",
                "summary": "ok",
                "requirement_checks": [
                    {
                        "requirement_id": "REQ-001",
                        "status": "PASS",
                        "evidence": [],
                    }
                ],
                "acceptance_checks": [
                    {
                        "criterion": "Accepter",
                        "status": "PASS",
                        "evidence": [],
                    }
                ],
                "issues": [],
                "tests": {"status": "PASS", "details": []},
                "scope": {"status": "PASS", "unexpected_paths": []},
            },
        )
        return {"command": ["codex", "exec"], "returncode": 0, "stdout": "", "stderr": ""}

    result = review_task(backlog, "TASK-RERUN", codex_runner=fake_codex_runner)

    assert result["tests"]["status"] == "PASS"
    validation_results = json.loads(
        (repo / ".autodev" / "runs" / "TASK-RERUN" / "review" / "validation-results.json").read_text(encoding="utf-8")
    )
    assert validation_results["source"] == "rerun"
    assert validation_results["results"][0]["stdout"].strip() == "rerun-ok"


def test_review_task_rebuilds_review_scope_from_current_branch_head(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-AMEND-REVIEW")])
    commit_all(repo, "add backlog")
    base_commit = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )

    branch = "autodev/TASK-AMEND-REVIEW"
    subprocess.run(["git", "checkout", "-b", branch], cwd=repo, check=True, capture_output=True, text=True)

    allowed = repo / "src" / "reviewed.txt"
    allowed.parent.mkdir(parents=True, exist_ok=True)
    allowed.write_text("current\n", encoding="utf-8")
    obsolete = repo / "tests" / "e2e" / "10-diagnostic.spec.ts"
    obsolete.parent.mkdir(parents=True, exist_ok=True)
    obsolete.write_text("obsolete\n", encoding="utf-8")
    commit_all(repo, "introduce stale review scope")
    stale_commit = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )

    subprocess.run(["git", "rm", "--", str(obsolete.relative_to(repo))], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "--amend", "--no-edit"], cwd=repo, check=True, capture_output=True, text=True)
    current_commit = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )

    run_dir = repo / ".autodev" / "runs" / "TASK-AMEND-REVIEW"
    review_dir = run_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "task.json").write_text(
        json.dumps(
            {
                "backlog": str(backlog),
                "task": make_task("TASK-AMEND-REVIEW"),
                "branch": branch,
                "worktree": str(repo / ".autodev" / "worktrees" / "TASK-AMEND-REVIEW"),
                "base_commit": base_commit,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "result.json").write_text(
        json.dumps(
            {
                "task_id": "TASK-AMEND-REVIEW",
                "status": "success",
                "branch": branch,
                "worktree": str(repo / ".autodev" / "worktrees" / "TASK-AMEND-REVIEW"),
                "base_commit": base_commit,
                "produced_commit": stale_commit,
                "modified_paths": ["src/reviewed.txt", "tests/e2e/10-diagnostic.spec.ts"],
                "validations": [
                    {
                        "command": "pytest -q",
                        "returncode": 0,
                        "stdout": "ok\n",
                        "stderr": "",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "diff.patch").write_text(
        "diff --git a/tests/e2e/10-diagnostic.spec.ts b/tests/e2e/10-diagnostic.spec.ts\n",
        encoding="utf-8",
    )
    (review_dir / "current-diff.patch").write_text(
        "stale review artifact referencing tests/e2e/10-diagnostic.spec.ts\n",
        encoding="utf-8",
    )

    prompt_holder: dict[str, str] = {}

    def fake_codex_runner(*_: object, **kwargs: object) -> dict[str, object]:
        prompt_holder["prompt"] = str(kwargs["prompt"])
        write_codex_result(
            Path(kwargs["output_path"]),
            {
                "task_id": "TASK-AMEND-REVIEW",
                "verdict": "APPROVED",
                "summary": "ok",
                "requirement_checks": [
                    {
                        "requirement_id": "REQ-001",
                        "status": "PASS",
                        "evidence": [],
                    }
                ],
                "acceptance_checks": [
                    {
                        "criterion": "Accepter",
                        "status": "PASS",
                        "evidence": [],
                    }
                ],
                "issues": [],
                "tests": {"status": "PASS", "details": []},
                "scope": {"status": "PASS", "unexpected_paths": []},
            },
        )
        return {"command": ["codex", "exec"], "returncode": 0, "stdout": "ok", "stderr": ""}

    result = review_task(backlog, "TASK-AMEND-REVIEW", codex_runner=fake_codex_runner)

    assert result["verdict"] == "APPROVED"
    assert current_commit != stale_commit
    prompt = prompt_holder["prompt"]
    assert current_commit in prompt
    assert stale_commit not in prompt
    assert "- src/reviewed.txt" in prompt
    assert "tests/e2e/10-diagnostic.spec.ts" not in prompt
    assert "- A\tsrc/reviewed.txt" in prompt

    current_paths = json.loads((review_dir / "current-paths.json").read_text(encoding="utf-8"))
    assert current_paths["produced_commit"] == current_commit
    assert current_paths["modified_paths"] == ["src/reviewed.txt"]
    assert current_paths["name_status"] == ["A\tsrc/reviewed.txt"]
    assert "10-diagnostic.spec.ts" not in (review_dir / "current-diff.patch").read_text(encoding="utf-8")
    assert (review_dir / "current-name-status.txt").read_text(encoding="utf-8").strip() == "A\tsrc/reviewed.txt"


def test_validate_backlog_rejects_absolute_allowed_path() -> None:
    backlog = {
        "feature_id": "FEATURE-TEST",
        "feature_title": "Feature test",
        "summary": "Résumé de test suffisant pour le backlog.",
        "specification_path": "SPEC.md",
        "requirements": [
            {
                "id": "REQ-001",
                "description": "Description requirement",
                "acceptance_criteria": ["Critère 1"],
            }
        ],
        "tasks": [
            {
                "id": "TASK-ABS",
                "title": "Titre",
                "description": "Description de tâche suffisamment longue.",
                "agent": "documentation",
                "depends_on": [],
                "requirement_ids": ["REQ-001"],
                "allowed_paths": ["/home/user/project/src"],
                "validation_commands": ["pytest"],
                "acceptance_criteria": ["Accepter"],
            }
        ],
    }

    with pytest.raises(PlanningError, match="Chemin absolu interdit"):
        validate_backlog_consistency(backlog)


def test_validate_backlog_rejects_parent_segment_allowed_path() -> None:
    backlog = {
        "feature_id": "FEATURE-TEST",
        "feature_title": "Feature test",
        "summary": "Résumé de test suffisant pour le backlog.",
        "specification_path": "SPEC.md",
        "requirements": [
            {
                "id": "REQ-001",
                "description": "Description requirement",
                "acceptance_criteria": ["Critère 1"],
            }
        ],
        "tasks": [
            {
                "id": "TASK-DOTDOT",
                "title": "Titre",
                "description": "Description de tâche suffisamment longue.",
                "agent": "documentation",
                "depends_on": [],
                "requirement_ids": ["REQ-001"],
                "allowed_paths": ["src/../secret"],
                "validation_commands": ["pytest"],
                "acceptance_criteria": ["Accepter"],
            }
        ],
    }

    with pytest.raises(PlanningError, match="Chemin avec '\\.\\.' interdit"):
        validate_backlog_consistency(backlog)
