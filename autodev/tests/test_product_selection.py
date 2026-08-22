"""Tests for feature selection and Git dependency verification."""

from __future__ import annotations

import subprocess
from pathlib import Path

from autodev.product_plan import Feature, ProductPlan
from autodev.product_selection import (
    DependencyIncident,
    select_next_feature,
    verify_dependency_integration,
)


def init_git_repo(tmp_path: Path) -> Path:
    """Initialize a Git repository for testing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)

    # Create initial commit
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)

    return repo


def commit_file(repo: Path, name: str, message: str) -> str:
    """Create a commit with a file and return the commit hash."""
    (repo / name).write_text(f"Content of {name}\n")
    subprocess.run(["git", "add", name], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True, capture_output=True)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def make_plan(features: list[tuple[str, int, list[str]]]) -> ProductPlan:
    """Create a test ProductPlan. Tuple: (feature_id, priority, depends_on)."""
    feature_list = [
        Feature(
            feature_id=fid,
            title=f"Feature {fid}",
            specification_path=f"spec/{fid}.md",
            required=True,
            priority=priority,
            depends_on=deps,
            validations=[],
        )
        for fid, priority, deps in features
    ]
    return ProductPlan(
        schema_version="1.0",
        plan_id="test-plan",
        generated_at="2025-01-01T00:00:00Z",
        integration_branch="main",
        specification_policy="approved-only",
        features=feature_list,
        global_validations=[],
        plan_hash="test-hash",
    )


def test_select_next_feature_orders_by_priority(tmp_path: Path) -> None:
    """AC-R4-1: Selection orders by dependencies, priority, then ID."""
    repo = init_git_repo(tmp_path)
    base_commit = commit_file(repo, "base.txt", "base")

    plan = make_plan([
        ("FEATURE-A", 1, []),
        ("FEATURE-B", 2, []),
        ("FEATURE-C", 1, []),
    ])

    result = select_next_feature(
        plan=plan,
        product_base_commit=base_commit,
        repo_root=repo,
        feature_statuses={},
        integrated_commits={},
    )

    assert result.selected_feature is not None
    assert result.selected_feature.feature_id == "FEATURE-B"
    assert len(result.eligible_features) == 3


def test_select_next_feature_orders_by_id_when_priority_equal(tmp_path: Path) -> None:
    """AC-R4-1: When priority equal, order by feature_id (stable)."""
    repo = init_git_repo(tmp_path)
    base_commit = commit_file(repo, "base.txt", "base")

    plan = make_plan([
        ("FEATURE-C", 1, []),
        ("FEATURE-A", 1, []),
        ("FEATURE-B", 1, []),
    ])

    result = select_next_feature(
        plan=plan,
        product_base_commit=base_commit,
        repo_root=repo,
        feature_statuses={},
        integrated_commits={},
    )

    assert result.selected_feature is not None
    assert result.selected_feature.feature_id == "FEATURE-A"


def test_select_next_feature_respects_dependencies(tmp_path: Path) -> None:
    """AC-R4-1: Dependencies are checked before priority."""
    repo = init_git_repo(tmp_path)
    base_commit = commit_file(repo, "base.txt", "base")

    plan = make_plan([
        ("FEATURE-A", 1, []),
        ("FEATURE-B", 10, ["FEATURE-A"]),  # High priority but depends on A
    ])

    # Feature-A is not integrated
    result = select_next_feature(
        plan=plan,
        product_base_commit=base_commit,
        repo_root=repo,
        feature_statuses={},
        integrated_commits={},
    )

    assert result.selected_feature is not None
    assert result.selected_feature.feature_id == "FEATURE-A"


def test_verify_dependency_integration_checks_git_ancestor(tmp_path: Path) -> None:
    """AC-R4-3: Dependency verification uses Git ancestor relationship."""
    repo = init_git_repo(tmp_path)
    commit1 = commit_file(repo, "dep.txt", "dependency feature")
    commit2 = commit_file(repo, "main.txt", "main feature")

    plan = make_plan([
        ("FEATURE-DEP", 1, []),
        ("FEATURE-MAIN", 1, ["FEATURE-DEP"]),
    ])

    feature = plan.features[1]  # FEATURE-MAIN
    satisfied, incidents = verify_dependency_integration(
        repo_root=repo,
        feature=feature,
        plan=plan,
        product_base_commit=commit2,
        integrated_commits={"FEATURE-DEP": commit1},
    )

    assert satisfied is True
    assert len(incidents) == 0


def test_verify_dependency_integration_detects_missing_commit(tmp_path: Path) -> None:
    """AC-R4-3: Incident when dependency commit is not ancestor."""
    repo = init_git_repo(tmp_path)

    # Create two branches without ancestry
    commit1 = commit_file(repo, "branch1.txt", "branch 1")

    # Reset and create another branch
    subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=repo, check=True, capture_output=True)
    commit2 = commit_file(repo, "branch2.txt", "branch 2")

    plan = make_plan([
        ("FEATURE-A", 1, []),
        ("FEATURE-B", 1, ["FEATURE-A"]),
    ])

    feature = plan.features[1]  # FEATURE-B
    satisfied, incidents = verify_dependency_integration(
        repo_root=repo,
        feature=feature,
        plan=plan,
        product_base_commit=commit2,
        integrated_commits={"FEATURE-A": commit1},
    )

    assert satisfied is False
    assert len(incidents) == 1
    assert incidents[0].code == "DEPENDENCY_COMMIT_NOT_ANCESTOR"


def test_verify_dependency_integration_unknown_dependency(tmp_path: Path) -> None:
    """AC-R4-4: Incident when feature depends on unknown feature."""
    repo = init_git_repo(tmp_path)
    base_commit = commit_file(repo, "base.txt", "base")

    plan = make_plan([
        ("FEATURE-A", 1, ["UNKNOWN-FEATURE"]),
    ])

    feature = plan.features[0]
    satisfied, incidents = verify_dependency_integration(
        repo_root=repo,
        feature=feature,
        plan=plan,
        product_base_commit=base_commit,
        integrated_commits={},
    )

    assert satisfied is False
    assert len(incidents) == 1
    assert incidents[0].code == "UNKNOWN_DEPENDENCY"


def test_select_next_feature_rejects_completed(tmp_path: Path) -> None:
    """AC-R4-4: Completed features are not relaunched."""
    repo = init_git_repo(tmp_path)
    base_commit = commit_file(repo, "base.txt", "base")

    plan = make_plan([
        ("FEATURE-A", 1, []),
        ("FEATURE-B", 1, []),
    ])

    # Mark FEATURE-A as completed
    feature_statuses = {
        "FEATURE-A": {"status": "COMPLETED"},
    }

    result = select_next_feature(
        plan=plan,
        product_base_commit=base_commit,
        repo_root=repo,
        feature_statuses=feature_statuses,
        integrated_commits={},
    )

    assert result.selected_feature is not None
    assert result.selected_feature.feature_id == "FEATURE-B"
    assert len([inc for inc in result.incidents if inc.code == "FEATURE_ALREADY_COMPLETED"]) == 1


def test_select_next_feature_no_eligible(tmp_path: Path) -> None:
    """Selection returns None when no features are eligible."""
    repo = init_git_repo(tmp_path)
    base_commit = commit_file(repo, "base.txt", "base")

    plan = make_plan([
        ("FEATURE-A", 1, []),
    ])

    feature_statuses = {
        "FEATURE-A": {"status": "COMPLETED"},
    }

    result = select_next_feature(
        plan=plan,
        product_base_commit=base_commit,
        repo_root=repo,
        feature_statuses=feature_statuses,
        integrated_commits={},
    )

    assert result.selected_feature is None
    assert len(result.eligible_features) == 0


def test_select_next_feature_complex_dependency_graph(tmp_path: Path) -> None:
    """Test feature selection with complex dependencies respects depth ordering."""
    repo = init_git_repo(tmp_path)
    commit_a = commit_file(repo, "a.txt", "feature-a")
    commit_b = commit_file(repo, "b.txt", "feature-b")
    commit_c = commit_file(repo, "c.txt", "feature-c")

    plan = make_plan([
        ("FEATURE-A", 1, []),
        ("FEATURE-B", 2, ["FEATURE-A"]),
        ("FEATURE-C", 3, ["FEATURE-A", "FEATURE-B"]),
        ("FEATURE-D", 1, []),
    ])

    integrated = {
        "FEATURE-A": commit_a,
        "FEATURE-B": commit_b,
    }

    result = select_next_feature(
        plan=plan,
        product_base_commit=commit_c,
        repo_root=repo,
        feature_statuses={},
        integrated_commits=integrated,
    )

    # FEATURE-D has depth 0 (no dependencies), so it should be selected first
    # even though FEATURE-C has higher priority (depth ordering takes precedence)
    # Eligible features: D (depth 0, priority 1), B (depth 1, priority 2), C (depth 2, priority 3)
    # D is selected as it has lowest depth
    assert result.selected_feature is not None
    assert result.selected_feature.feature_id == "FEATURE-D"


def test_verify_dependency_integration_missing_integration_record(tmp_path: Path) -> None:
    """AC-R4-4: Incident when dependency has no integration record."""
    repo = init_git_repo(tmp_path)
    base_commit = commit_file(repo, "base.txt", "base")

    plan = make_plan([
        ("FEATURE-A", 1, []),
        ("FEATURE-B", 1, ["FEATURE-A"]),
    ])

    feature = plan.features[1]  # FEATURE-B
    # Intentionally omit FEATURE-A from integrated_commits
    satisfied, incidents = verify_dependency_integration(
        repo_root=repo,
        feature=feature,
        plan=plan,
        product_base_commit=base_commit,
        integrated_commits={},
    )

    assert satisfied is False
    assert len(incidents) == 1
    assert incidents[0].code == "DEPENDENCY_NOT_INTEGRATED"


def test_dependency_incident_has_correct_properties(tmp_path: Path) -> None:
    """Test that DependencyIncident has correct severity and scope."""
    incident = DependencyIncident(
        code="TEST_CODE",
        reason="Test reason",
        feature_id="FEATURE-TEST",
    )

    assert incident.code == "TEST_CODE"
    assert incident.severity.value == "high"
    assert incident.scope.value == "dependency"
    assert incident.retryable is False
    assert incident.terminal is False
    assert any("FEATURE-TEST" in proof for proof in incident.proofs)


def test_select_next_feature_empty_plan(tmp_path: Path) -> None:
    """Empty plan results in no selection."""
    repo = init_git_repo(tmp_path)
    base_commit = commit_file(repo, "base.txt", "base")

    plan = make_plan([])

    result = select_next_feature(
        plan=plan,
        product_base_commit=base_commit,
        repo_root=repo,
        feature_statuses={},
        integrated_commits={},
    )

    assert result.selected_feature is None
    assert len(result.eligible_features) == 0


def test_select_next_feature_rationale_includes_incidents(tmp_path: Path) -> None:
    """Rationale includes incident information."""
    repo = init_git_repo(tmp_path)
    base_commit = commit_file(repo, "base.txt", "base")

    plan = make_plan([
        ("FEATURE-A", 1, ["UNKNOWN"]),
    ])

    result = select_next_feature(
        plan=plan,
        product_base_commit=base_commit,
        repo_root=repo,
        feature_statuses={},
        integrated_commits={},
    )

    assert "Incidents detected" in result.rationale
    assert result.selected_feature is None


def test_select_next_feature_orders_by_dependency_depth(tmp_path: Path) -> None:
    """AC-R4-1: Features are ordered by dependency depth before priority and ID."""
    repo = init_git_repo(tmp_path)
    commit_a = commit_file(repo, "a.txt", "feature-a")
    commit_b = commit_file(repo, "b.txt", "feature-b")
    commit_c = commit_file(repo, "c.txt", "feature-c")
    commit_d = commit_file(repo, "d.txt", "feature-d")

    # Create a dependency hierarchy:
    # FEATURE-D (depth 0, priority 10) - no dependencies
    # FEATURE-C (depth 0, priority 5) - no dependencies
    # FEATURE-A (depth 0, priority 1) - no dependencies, but integrated
    # FEATURE-B (depth 1 - depends on A, priority 100) - high priority but depends on integrated A
    # Selection should prefer depth 0 features over depth 1 features
    plan = make_plan([
        ("FEATURE-A", 1, []),
        ("FEATURE-B", 100, ["FEATURE-A"]),  # High priority but depth 1 (depends on A)
        ("FEATURE-C", 5, []),
        ("FEATURE-D", 10, []),
    ])

    integrated = {
        "FEATURE-A": commit_a,
    }

    result = select_next_feature(
        plan=plan,
        product_base_commit=commit_d,
        repo_root=repo,
        feature_statuses={},
        integrated_commits=integrated,
    )

    # Eligible features: B (depth 1, deps satisfied), C (depth 0), D (depth 0)
    # Among depth 0: D (priority 10) > C (priority 5)
    # Depth 0 features are preferred, so D is selected
    assert result.selected_feature is not None
    assert result.selected_feature.feature_id == "FEATURE-D"
    # Check that eligible list includes B, C, D (A is already integrated)
    assert len(result.eligible_features) == 3
    eligible_ids = [f.feature_id for f in result.eligible_features]
    assert "FEATURE-B" in eligible_ids
    assert "FEATURE-C" in eligible_ids
    assert "FEATURE-D" in eligible_ids
    # Verify order respects depth: depth 0 features come before depth 1
    b_idx = eligible_ids.index("FEATURE-B")  # depth 1
    d_idx = eligible_ids.index("FEATURE-D")  # depth 0
    c_idx = eligible_ids.index("FEATURE-C")  # depth 0
    # D and C (depth 0) should come before B (depth 1)
    assert d_idx < b_idx and c_idx < b_idx


def test_select_next_feature_detects_incoherent_integrated_feature(tmp_path: Path) -> None:
    """AC-R4-4: Incident when feature is integrated but not marked COMPLETED."""
    repo = init_git_repo(tmp_path)
    commit_a = commit_file(repo, "a.txt", "feature-a")
    commit_b = commit_file(repo, "b.txt", "feature-b")

    plan = make_plan([
        ("FEATURE-A", 1, []),
        ("FEATURE-B", 1, []),
    ])

    # FEATURE-A is integrated but only marked as IN_PROGRESS (not COMPLETED)
    feature_statuses = {
        "FEATURE-A": {"status": "IN_PROGRESS"},
    }
    integrated_commits = {
        "FEATURE-A": commit_a,
    }

    result = select_next_feature(
        plan=plan,
        product_base_commit=commit_b,
        repo_root=repo,
        feature_statuses=feature_statuses,
        integrated_commits=integrated_commits,
    )

    # FEATURE-A should be ineligible with an incident
    assert result.selected_feature is not None
    assert result.selected_feature.feature_id == "FEATURE-B"
    incoherence_incidents = [inc for inc in result.incidents if inc.code == "FEATURE_INCOHERENT_STATUS"]
    assert len(incoherence_incidents) == 1
    assert "FEATURE-A" in incoherence_incidents[0].description
    # FEATURE-A should be in ineligible list
    assert any(f.feature_id == "FEATURE-A" for f in result.ineligible_features)
