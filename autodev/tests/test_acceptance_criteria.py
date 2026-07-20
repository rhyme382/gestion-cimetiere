from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from autodev.acceptance_criteria import (
    AcceptanceCriteriaError,
    build_coverage_matrix,
    migrate_backlog_acceptance_criteria,
    render_coverage_text,
)
from autodev.cli import app
from autodev.monitor import render_monitor
from autodev.monitor_state import read_feature_state
from autodev.planner import PlanningError, validate_backlog_consistency
from autodev.review_task import review_task

from test_task_runner import commit_all, init_repo, make_task, write_backlog


def structured_requirements() -> list[dict[str, object]]:
    return [
        {
            "id": "R2",
            "description": "Règles métier des concessions",
            "acceptance_criteria": [
                {
                    "id": "R2-AC1",
                    "text": "Le type et la durée sont cohérents.",
                    "owner_task_id": "T2",
                },
                {
                    "id": "R2-AC2",
                    "text": "L'échéance est calculée par le backend.",
                    "owner_task_id": "T2",
                },
                {
                    "id": "R2-AC3",
                    "text": "L'occupation incompatible d'un emplacement est refusée.",
                    "owner_task_id": "T3",
                },
            ],
        }
    ]


def structured_backlog(repo: Path) -> Path:
    return write_backlog(
        repo,
        [
            make_task("T2", requirement_ids=["R2"]),
            make_task("T3", requirement_ids=["R2"]),
        ],
        requirements=structured_requirements(),
    )


def write_review_result(
    repo: Path,
    task_id: str,
    *,
    verdict: str,
    requirement_checks: list[dict[str, object]],
) -> None:
    review_dir = repo / ".autodev" / "runs" / task_id / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    (review_dir / "review-result.json").write_text(
        json.dumps(
            {
                "task_id": task_id,
                "verdict": verdict,
                "summary": "review",
                "requirement_checks": requirement_checks,
                "acceptance_checks": [{"criterion": "Accepter", "status": "PASS", "evidence": []}],
                "issues": [],
                "tests": {"status": "PASS", "details": []},
                "scope": {"status": "PASS", "unexpected_paths": []},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_integration_result(repo: Path, task_id: str, status: str = "INTEGRATED") -> None:
    integration_dir = repo / ".autodev" / "runs" / task_id / "integration"
    integration_dir.mkdir(parents=True, exist_ok=True)
    (integration_dir / "integration-result.json").write_text(
        json.dumps({"task_id": task_id, "status": status}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_legacy_backlog_simple_is_accepted(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-LEGACY")])

    validate_backlog_consistency(json.loads(backlog.read_text(encoding="utf-8")))


def test_structured_backlog_is_accepted(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = structured_backlog(repo)

    validate_backlog_consistency(json.loads(backlog.read_text(encoding="utf-8")))


def test_missing_owner_is_rejected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = structured_backlog(repo)
    payload = json.loads(backlog.read_text(encoding="utf-8"))
    del payload["requirements"][0]["acceptance_criteria"][0]["owner_task_id"]

    with pytest.raises(PlanningError, match="critère structuré invalide"):
        validate_backlog_consistency(payload)


def test_unknown_owner_is_rejected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = structured_backlog(repo)
    payload = json.loads(backlog.read_text(encoding="utf-8"))
    payload["requirements"][0]["acceptance_criteria"][0]["owner_task_id"] = "T404"

    with pytest.raises(PlanningError, match="tâche propriétaire inconnue"):
        validate_backlog_consistency(payload)


def test_duplicate_criterion_id_is_rejected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = structured_backlog(repo)
    payload = json.loads(backlog.read_text(encoding="utf-8"))
    payload["requirements"][0]["acceptance_criteria"][1]["id"] = "R2-AC1"

    with pytest.raises(PlanningError, match="Identifiant de critère dupliqué"):
        validate_backlog_consistency(payload)


def test_requirement_without_criteria_is_rejected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = structured_backlog(repo)
    payload = json.loads(backlog.read_text(encoding="utf-8"))
    payload["requirements"][0]["acceptance_criteria"] = []

    with pytest.raises(PlanningError, match="au moins un critère"):
        validate_backlog_consistency(payload)


def test_review_prompt_excludes_other_task_criteria_for_t2(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = structured_backlog(repo)
    commit_all(repo, "add backlog")

    branch = "autodev/T2"
    (repo / "src" / "reviewed.txt").write_text("ok\n", encoding="utf-8")
    import subprocess

    subprocess.run(["git", "checkout", "-b", branch], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "src/reviewed.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "t2"], cwd=repo, check=True, capture_output=True, text=True)

    run_dir = repo / ".autodev" / "runs" / "T2"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "task.json").write_text(
        json.dumps(
            {
                "backlog": str(backlog),
                "task": make_task("T2", requirement_ids=["R2"]),
                "branch": branch,
                "worktree": str(repo),
                "base_commit": subprocess.run(
                    ["git", "rev-parse", "HEAD~1"],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "result.json").write_text(
        json.dumps(
            {
                "task_id": "T2",
                "status": "success",
                "branch": branch,
                "worktree": str(repo),
                "base_commit": subprocess.run(
                    ["git", "rev-parse", "HEAD~1"],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip(),
                "produced_commit": subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip(),
                "modified_paths": ["src/reviewed.txt"],
                "validations": [],
                "validation_summary": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    prompt_holder: dict[str, str] = {}

    def fake_codex_runner(*_: object, **kwargs: object) -> dict[str, object]:
        prompt_holder["prompt"] = str(kwargs["prompt"])
        Path(kwargs["output_path"]).write_text(
            json.dumps(
                {
                    "task_id": "T2",
                    "verdict": "APPROVED",
                    "summary": "ok",
                    "requirement_checks": [
                        {
                            "requirement_id": "R2",
                            "acceptance_criterion_id": "R2-AC1",
                            "criterion": "Le type et la durée sont cohérents.",
                            "status": "PASS",
                            "evidence": [],
                        },
                        {
                            "requirement_id": "R2",
                            "acceptance_criterion_id": "R2-AC2",
                            "criterion": "L'échéance est calculée par le backend.",
                            "status": "PASS",
                            "evidence": [],
                        },
                    ],
                    "acceptance_checks": [{"criterion": "Accepter", "status": "PASS", "evidence": []}],
                    "issues": [],
                    "tests": {"status": "PASS", "details": []},
                    "scope": {"status": "PASS", "unexpected_paths": []},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {"command": ["codex"], "returncode": 0, "stdout": "ok", "stderr": ""}

    review_task(backlog, "T2", codex_runner=fake_codex_runner)

    prompt = prompt_holder["prompt"]
    assert "R2-AC1" in prompt
    assert "R2-AC2" in prompt
    assert "R2-AC3" not in prompt


def test_migration_non_ambiguous_is_deterministic(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-MIGRATE")])

    migrated = migrate_backlog_acceptance_criteria(json.loads(backlog.read_text(encoding="utf-8")))

    assert migrated["requirements"][0]["acceptance_criteria"] == [
        {
            "id": "REQ-001-AC1",
            "text": "Critère 1",
            "owner_task_id": "TASK-MIGRATE",
        }
    ]


def test_migration_ambiguous_is_rejected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(
        repo,
        [
            make_task("T2", requirement_ids=["REQ-001"]),
            make_task("T3", requirement_ids=["REQ-001"]),
        ],
        requirements=[
            {
                "id": "REQ-001",
                "description": "Description requirement",
                "acceptance_criteria": ["Critère 1"],
            }
        ],
    )

    with pytest.raises(AcceptanceCriteriaError, match="HUMAN_REVIEW_REQUIRED"):
        migrate_backlog_acceptance_criteria(json.loads(backlog.read_text(encoding="utf-8")))


def test_coverage_text_and_json_and_monitor_include_ownership(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = structured_backlog(repo)
    commit_all(repo, "add backlog")
    write_review_result(
        repo,
        "T2",
        verdict="APPROVED",
        requirement_checks=[
            {
                "requirement_id": "R2",
                "acceptance_criterion_id": "R2-AC1",
                "criterion": "Le type et la durée sont cohérents.",
                "status": "PASS",
                "evidence": [],
            },
            {
                "requirement_id": "R2",
                "acceptance_criterion_id": "R2-AC2",
                "criterion": "L'échéance est calculée par le backend.",
                "status": "PASS",
                "evidence": [],
            },
        ],
    )
    write_integration_result(repo, "T2")

    coverage = build_coverage_matrix(json.loads(backlog.read_text(encoding="utf-8")), repo)
    rendered = render_coverage_text(coverage)
    assert "R2-AC1  T2  APPROVED" in rendered
    assert "R2-AC3  T3  PENDING" in rendered
    assert coverage["requirements"][0]["status"] == "PARTIAL"

    write_review_result(
        repo,
        "T3",
        verdict="APPROVED",
        requirement_checks=[
            {
                "requirement_id": "R2",
                "acceptance_criterion_id": "R2-AC3",
                "criterion": "L'occupation incompatible d'un emplacement est refusée.",
                "status": "PASS",
                "evidence": [],
            }
        ],
    )
    write_integration_result(repo, "T3")
    coverage = build_coverage_matrix(json.loads(backlog.read_text(encoding="utf-8")), repo)
    assert coverage["requirements"][0]["status"] == "PASS"

    state = read_feature_state(backlog)
    output = Console(file=StringIO(), force_terminal=False)
    output.print(render_monitor(state))
    text = output.file.getvalue()
    assert "Couverture critères" in text
    assert "100%" in text

    runner = CliRunner()
    result = runner.invoke(app, ["coverage", str(backlog)], catch_exceptions=False)
    assert result.exit_code == 0
    assert "Total critères" in result.stdout

    result = runner.invoke(app, ["coverage", str(backlog), "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    assert '"coverage_percentage"' in result.stdout


def test_migrate_backlog_command_writes_output(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    backlog = write_backlog(repo, [make_task("TASK-MIGRATE")])
    output = repo / ".autodev" / "plans" / "migrated.backlog.json"

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["migrate-backlog", str(backlog), "--output", str(output)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    migrated = json.loads(output.read_text(encoding="utf-8"))
    assert migrated["requirements"][0]["acceptance_criteria"][0]["owner_task_id"] == "TASK-MIGRATE"
