"""Tests for fine-grained worktree reconciliation with content fingerprints.

AC-R22: Réconciliation fine du worktree et empreintes de contenu
AC-R11: Réconciliation après interruption
"""
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from autodev.git_context import (
    ContentFingerprints,
    ExecutionMutationMetadata,
    GitContextError,
    GitSnapshot,
    ModificationChange,
    ModificationClassification,
    ReconciliationDiagnostic,
    analyze_mutations,
    capture_content_fingerprints,
    capture_git_snapshot,
    capture_git_snapshot_triple_with_lifecycle,
    classify_modifications,
    detect_content_changes,
    diagnose_reconciliation,
)
from autodev.git_tools import (
    GitError,
    create_commit,
    create_branch,
    add_worktree,
    git_output,
    restore_paths,
    run_git,
)
from autodev.correct_task import partition_paths
from test_correct_task import make_claude_runner, prepare_correction_case


@pytest.fixture
def temp_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        # Initialize repo
        run_git(repo_root, ["init"])
        run_git(repo_root, ["config", "user.email", "test@example.com"])
        run_git(repo_root, ["config", "user.name", "Test User"])

        # Create initial commit
        initial_file = repo_root / "README.md"
        initial_file.write_text("# Initial\n")
        run_git(repo_root, ["add", "README.md"])
        run_git(repo_root, ["commit", "-m", "Initial commit"])

        yield repo_root


@pytest.fixture
def task_worktree(temp_repo):
    """Create a task worktree for testing."""
    create_branch(temp_repo, "autodev/task-001", "HEAD")
    worktree_path = temp_repo / ".autodev" / "worktrees" / "task-001"
    add_worktree(temp_repo, worktree_path, "autodev/task-001")
    yield worktree_path


def write_product_run_proof(repo_root: Path, task_id: str, run_dir: Path, run_id: str) -> None:
    """Create explicit product-run state proof and link it from task result."""
    from autodev.product_state import ProductRunState, ProductStateManager

    state_manager = ProductStateManager(repo_root, run_id)
    state = ProductRunState(
        run_id=run_id,
        plan_id="plan-001",
        product_key="plan-001",
        schema_version="1.0",
        plan_hash="hash-001",
        started_at=datetime.now(timezone.utc).isoformat(),
        run_namespace=state_manager.run_namespace,
        task_states={task_id: {"status": "RUNNING"}},
    )
    state_manager.reserve_run_namespace(plan_id=state.plan_id, plan_hash=state.plan_hash)
    with state_manager.bootstrap_writes():
        state_manager.write_state(state)

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "result.json").write_text(
        json.dumps({"task_id": task_id, "run_id": run_id}, indent=2),
        encoding="utf-8",
    )


class TestContentFingerprints:
    """Tests for content fingerprint capture and comparison."""

    def test_capture_fingerprints_empty_snapshot(self, temp_repo):
        """AC-R22-3: Capture fingerprints from clean worktree."""
        snapshot = capture_git_snapshot(temp_repo, timestamp_label="test")
        fingerprints = capture_content_fingerprints(snapshot)

        assert fingerprints.timestamp_label == "test"
        assert len(fingerprints.indexed_blob_hashes) == 0
        assert len(fingerprints.worktree_content_hashes) == 0
        assert len(fingerprints.untracked_file_hashes) == 0

    def test_capture_fingerprints_with_dirty_files(self, temp_repo, task_worktree):
        """Capture fingerprints with dirty tracked files."""
        # Modify tracked file
        test_file = task_worktree / "README.md"
        test_file.write_text("# Modified\n")

        snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        fingerprints = capture_content_fingerprints(snapshot)

        assert len(fingerprints.worktree_content_hashes) > 0
        assert "README.md" in fingerprints.worktree_content_hashes

    def test_capture_fingerprints_with_untracked_files(self, temp_repo, task_worktree):
        """Capture fingerprints with untracked files."""
        # Create untracked file
        untracked = task_worktree / "untracked.txt"
        untracked.write_text("untracked content\n")

        snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        fingerprints = capture_content_fingerprints(snapshot)

        assert len(fingerprints.untracked_file_hashes) > 0
        assert "untracked.txt" in fingerprints.untracked_file_hashes

    def test_capture_fingerprints_with_staged_files(self, temp_repo, task_worktree):
        """Capture fingerprints with staged files."""
        # Modify and stage
        test_file = task_worktree / "README.md"
        test_file.write_text("# Staged\n")
        run_git(temp_repo, ["add", "README.md"], cwd=task_worktree)

        snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        fingerprints = capture_content_fingerprints(snapshot)

        assert len(fingerprints.indexed_blob_hashes) > 0
        assert "README.md" in fingerprints.indexed_blob_hashes

    def test_capture_fingerprints_staged_and_dirty(self, temp_repo, task_worktree):
        """AC-R22-3: Capture separate fingerprints for staged blob and dirty content."""
        # Stage a file with one content
        test_file = task_worktree / "README.md"
        test_file.write_text("# Staged content\n")
        run_git(temp_repo, ["add", "README.md"], cwd=task_worktree)

        # Then modify it to different content (making it both staged and dirty)
        test_file.write_text("# Dirty content different from staged\n")

        snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        fingerprints = capture_content_fingerprints(snapshot)

        # AC-R22-3: Should have both indexed blob and worktree content hashes
        # for the same file when it's both staged and dirty with different content
        has_indexed = "README.md" in fingerprints.indexed_blob_hashes
        has_dirty = "README.md" in fingerprints.worktree_content_hashes

        # Both should be present to distinguish staged vs dirty
        assert has_indexed, "Should capture indexed blob hash for staged file"
        assert has_dirty, "Should capture worktree content hash for dirty file"

        # The hashes should differ (staged vs dirty have different content)
        indexed_hash = fingerprints.indexed_blob_hashes.get("README.md")
        dirty_hash = fingerprints.worktree_content_hashes.get("README.md")
        assert indexed_hash != dirty_hash, "Staged and dirty hashes should differ"


class TestDetectContentChanges:
    """Tests for detecting content changes via fingerprints.

    AC-R22-4: Détecte une nouvelle modification sur un fichier déjà modifié.
    """

    def test_detect_no_changes(self, temp_repo, task_worktree):
        """Detect when content hasn't changed."""
        snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        fingerprints = capture_content_fingerprints(snapshot)

        changes = detect_content_changes(fingerprints, fingerprints)

        assert len(changes) == 0

    def test_detect_content_change_on_dirty_file(self, temp_repo, task_worktree):
        """AC-R22-4: Detect when dirty file content changes."""
        # Modify file first time
        test_file = task_worktree / "README.md"
        test_file.write_text("# First modification\n")

        after1_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        after1_fingerprints = capture_content_fingerprints(after1_snapshot)

        # Modify again (same file, second change)
        test_file.write_text("# Second modification\n")

        after2_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        after2_fingerprints = capture_content_fingerprints(after2_snapshot)

        # Detect second change - both before and after have the file modified
        changes = detect_content_changes(after1_fingerprints, after2_fingerprints)
        assert len(changes) > 0
        assert any(c.path == "README.md" and c.hash_changed for c in changes)

    def test_detect_file_creation(self, temp_repo, task_worktree):
        """Detect when new untracked file is created."""
        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        before_fingerprints = capture_content_fingerprints(before_snapshot)

        # Create new file
        new_file = task_worktree / "new.txt"
        new_file.write_text("new content\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        after_fingerprints = capture_content_fingerprints(after_snapshot)

        changes = detect_content_changes(before_fingerprints, after_fingerprints)
        assert len(changes) > 0
        assert any(c.path == "new.txt" and c.presence_changed for c in changes)

    def test_detect_file_deletion(self, temp_repo, task_worktree):
        """Detect when file is deleted."""
        # Create and modify a tracked file (so it appears in fingerprints)
        test_file = task_worktree / "README.md"
        test_file.write_text("# Content\n")

        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        before_fingerprints = capture_content_fingerprints(before_snapshot)
        assert "README.md" in before_fingerprints.worktree_content_hashes

        # Delete the file
        test_file.unlink()

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        after_fingerprints = capture_content_fingerprints(after_snapshot)

        changes = detect_content_changes(before_fingerprints, after_fingerprints)
        assert len(changes) > 0
        assert any(c.path == "README.md" and c.presence_changed for c in changes)


class TestModificationClassification:
    """Tests for classifying modifications as allowed vs out-of-scope.

    AC-R11-3: Classe les modifications en autorisées, partielles ou hors scope.
    """

    def test_classify_allowed_modifications(self, temp_repo, task_worktree):
        """Classify modifications within allowed scope."""
        # Capture initial state (before hooks)
        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Simulate agent modification
        test_file = task_worktree / "README.md"
        test_file.write_text("# Modified\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Analyze mutations (no hooks, only agent phase)
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        modified_paths = ["README.md"]
        classifications = classify_modifications(after_snapshot, modified_paths, mutations)

        readme_class = next((c for c in classifications if c.path == "README.md"), None)
        assert readme_class is not None
        assert readme_class.is_allowed is True
        assert readme_class.classification == "allowed"

    def test_classify_out_of_scope_modifications(self, temp_repo, task_worktree):
        """Classify modifications outside allowed scope."""
        # Capture initial state
        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Create untracked file (simulating agent action)
        untracked = task_worktree / "untracked.txt"
        untracked.write_text("untracked\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Analyze mutations
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        modified_paths = []  # Empty allowed paths
        classifications = classify_modifications(after_snapshot, modified_paths, mutations)

        untracked_class = next(
            (c for c in classifications if c.path == "untracked.txt"), None
        )
        assert untracked_class is not None
        assert untracked_class.is_allowed is False
        assert untracked_class.classification == "out_of_scope"

    def test_classify_preexisting_modifications(self, temp_repo, task_worktree):
        """Classify modifications that existed before process start."""
        # Create dirty file
        test_file = task_worktree / "README.md"
        test_file.write_text("# Pre-existing\n")

        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, before_snapshot, before_snapshot)

        modified_paths = []
        classifications = classify_modifications(before_snapshot, modified_paths, mutations)

        readme_class = next((c for c in classifications if c.path == "README.md"), None)
        assert readme_class is not None
        assert readme_class.is_preexisting is True


class TestReconciliationDiagnostic:
    """Tests for reconciliation diagnostics.

    AC-R11-5: Diagnostic structuré précède toute reprise.
    AC-R22-9: Produit des preuves vérifiables.
    """

    def test_diagnose_safe_allowed_changes_only(self, temp_repo, task_worktree):
        """Diagnose as safe when only allowed changes present."""
        # Capture initial
        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Agent modifies allowed file
        test_file = task_worktree / "README.md"
        test_file.write_text("# Modified\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Analyze with proper before/after
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        modified_paths = ["README.md"]
        diagnostic = diagnose_reconciliation(before_snapshot, after_snapshot, modified_paths, mutations)

        assert diagnostic.verdict == "safe_to_recover"
        assert len(diagnostic.allowed_changes) > 0
        assert len(diagnostic.out_of_scope_changes) == 0

    def test_diagnose_requires_review_with_out_of_scope(self, temp_repo, task_worktree):
        """Diagnose as requires_review when out-of-scope changes present."""
        # Capture initial
        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Create untracked file (simulating agent action)
        untracked = task_worktree / "untracked.txt"
        untracked.write_text("untracked\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Analyze mutations
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        modified_paths = []  # Empty allowed paths
        diagnostic = diagnose_reconciliation(before_snapshot, after_snapshot, modified_paths, mutations)

        assert diagnostic.verdict in ("requires_review", "request_human")
        assert len(diagnostic.out_of_scope_changes) > 0

    def test_diagnose_produces_evidence(self, temp_repo, task_worktree):
        """AC-R22-9: Diagnostic produces verifiable evidence."""
        test_file = task_worktree / "README.md"
        test_file.write_text("# Modified\n")

        snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(snapshot, snapshot, snapshot)

        modified_paths = ["README.md"]
        diagnostic = diagnose_reconciliation(snapshot, snapshot, modified_paths, mutations)

        assert diagnostic.evidence is not None
        assert "classification_summary" in diagnostic.evidence
        assert "content_changes" in diagnostic.evidence
        assert isinstance(diagnostic.evidence["content_changes"], list)


class TestFP004T03Scenario:
    """Test FP004-T03: modified_paths empty, four real files modified.

    AC-R11-7: Un test reproduit FP004-T03 : Claude code 1, `modified_paths` vide,
    quatre fichiers réellement modifiés et préservés s'ils sont autorisés.
    """

    def test_fp004_t03_scenario(self, temp_repo, task_worktree):
        """AC-R11-7: Reproduce FP004-T03 with preservation logic."""
        # Capture initial state
        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Agent creates four files (simulating modifications outside scope)
        files = {
            "file1.txt": "content 1\n",
            "file2.py": "# content 2\n",
            "file3.md": "## content 3\n",
            "file4.json": '{"key": "value"}\n',
        }

        for name, content in files.items():
            (task_worktree / name).write_text(content)

        # Capture after agent phase
        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        # modified_paths is empty (as per FP004-T03)
        modified_paths = []

        # Diagnose situation
        diagnostic = diagnose_reconciliation(before_snapshot, after_snapshot, modified_paths, mutations)

        # All files should be classified as out_of_scope
        assert len(diagnostic.out_of_scope_changes) == 4
        out_of_scope_names = {oc.path for oc in diagnostic.out_of_scope_changes}
        assert out_of_scope_names == set(files.keys())

        # Verdict should be requires_review or request_human
        assert diagnostic.verdict in ("requires_review", "request_human")

    def test_fp004_t03_scenario_with_allowed_paths(self, temp_repo, task_worktree):
        """AC-R11-7: FP004-T03 variant where files are allowed and should be preserved."""
        # Capture initial state
        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Agent creates four files with same paths as previous test
        files = {
            "file1.txt": "content 1\n",
            "file2.py": "# content 2\n",
            "file3.md": "## content 3\n",
            "file4.json": '{"key": "value"}\n',
        }

        for name, content in files.items():
            (task_worktree / name).write_text(content)

        # Capture after agent phase
        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        # modified_paths includes all four files (they are allowed)
        modified_paths = list(files.keys())

        # Diagnose situation
        diagnostic = diagnose_reconciliation(before_snapshot, after_snapshot, modified_paths, mutations)

        # All files should be classified as allowed (not out_of_scope)
        assert len(diagnostic.allowed_changes) == 4
        allowed_names = {ac.path for ac in diagnostic.allowed_changes}
        assert allowed_names == set(files.keys())

        # Verdict should be safe_to_recover (no out_of_scope divergence)
        assert diagnostic.verdict == "safe_to_recover"

        # Verify that can_safely_restore_out_of_scope returns True
        assert diagnostic.can_safely_restore_out_of_scope() is True


class TestInterruptionRecovery:
    """Tests for safe recovery after interruption.

    AC-R11-5: Reprise du commit et du worktree réels.
    """

    def test_recovery_with_preexisting_dirty_files(self, temp_repo, task_worktree):
        """AC-R11-9: Don't overwrite preexisting modifications."""
        # Create preexisting dirty state
        test_file = task_worktree / "README.md"
        test_file.write_text("# Pre-existing dirty\n")

        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Simulate process modification
        test_file.write_text("# Pre-existing + process modification\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, after_snapshot, after_snapshot)

        # Check that preexisting flag is set
        readme_mutation = mutations.get("README.md")
        assert readme_mutation is not None
        assert readme_mutation.before_hooks is True

    def test_recovery_preserves_allowed_changes(self, temp_repo, task_worktree):
        """AC-R11-4: Preserve allowed modifications."""
        # Capture initial
        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Agent modifies allowed file
        test_file = task_worktree / "allowed.py"
        test_file.write_text("# Allowed modification\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        modified_paths = ["allowed.py"]
        diagnostic = diagnose_reconciliation(before_snapshot, after_snapshot, modified_paths, mutations)

        allowed = [c for c in diagnostic.allowed_changes if c.path == "allowed.py"]
        assert len(allowed) > 0
        assert diagnostic.can_safely_restore_out_of_scope() is True


class TestIdempotentRecovery:
    """Tests for idempotent recovery operations.

    AC-R22-11: Tests reproduisent la reprise idempotente après crash.
    """

    def test_idempotent_recovery_same_state(self, temp_repo, task_worktree):
        """Recovery should produce same result when called multiple times."""
        test_file = task_worktree / "README.md"
        test_file.write_text("# Modified\n")

        snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(snapshot, snapshot, snapshot)

        modified_paths = ["README.md"]

        # First recovery diagnostic
        diag1 = diagnose_reconciliation(snapshot, snapshot, modified_paths, mutations)

        # Second recovery diagnostic (no state changes)
        diag2 = diagnose_reconciliation(snapshot, snapshot, modified_paths, mutations)

        # Results should be identical
        assert diag1.verdict == diag2.verdict
        assert len(diag1.allowed_changes) == len(diag2.allowed_changes)
        assert len(diag1.out_of_scope_changes) == len(diag2.out_of_scope_changes)

    def test_idempotent_recovery_after_partial_restoration(self, temp_repo, task_worktree):
        """Recovery should handle partial restoration state idempotently."""
        # Capture initial
        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Agent modifies only allowed file
        file1 = task_worktree / "file1.txt"
        file1.write_text("content 1\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        # Only file1 is allowed
        modified_paths = ["file1.txt"]

        # First diagnostic
        diagnostic1 = diagnose_reconciliation(before_snapshot, after_snapshot, modified_paths, mutations)

        # Should identify file1 as allowed
        file1_allowed = next(
            (c for c in diagnostic1.allowed_changes if c.path == "file1.txt"), None
        )
        assert file1_allowed is not None

        # No out-of-scope changes
        assert len(diagnostic1.out_of_scope_changes) == 0

        # Recovery should be safe
        assert diagnostic1.verdict == "safe_to_recover"

        # Second recovery diagnostic (same state) should be identical
        diagnostic2 = diagnose_reconciliation(before_snapshot, after_snapshot, modified_paths, mutations)
        assert diagnostic1.verdict == diagnostic2.verdict
        assert len(diagnostic1.allowed_changes) == len(diagnostic2.allowed_changes)


class TestHierarchicalScopeMatching:
    """AC-CORRECTION-1: Tests for hierarchical scope matching in allowed_paths.

    Verifies that allowed_paths uses hierarchical scope semantics:
    - Exact path match is allowed
    - Children of allowed directory are allowed
    - Siblings/unrelated paths are not allowed
    """

    def test_exact_file_path_allowed(self, temp_repo, task_worktree):
        """allowed_paths with exact file is allowed."""
        # Capture before
        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Agent modifies exact file
        file1 = task_worktree / "file1.txt"
        file1.write_text("content 1\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        # allowed_paths contains exact file
        allowed_paths = ["file1.txt"]

        diagnostic = diagnose_reconciliation(before_snapshot, after_snapshot, allowed_paths, mutations)

        # file1.txt should be in allowed_changes
        file1_allowed = next(
            (c for c in diagnostic.allowed_changes if c.path == "file1.txt"), None
        )
        assert file1_allowed is not None
        assert len(diagnostic.out_of_scope_changes) == 0

    def test_file_scope_does_not_allow_descendants(self, temp_repo, task_worktree):
        """allowed_paths with a file scope allows only the exact file."""
        src_dir = task_worktree / "src"
        src_dir.mkdir()
        scoped_file = src_dir / "file.py"
        scoped_file.write_text("# original\n")
        run_git(temp_repo, ["add", "src/file.py"], cwd=task_worktree)
        run_git(temp_repo, ["commit", "-m", "add scoped file"], cwd=task_worktree)

        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        scoped_file.unlink()
        scoped_file.mkdir()
        scoped_file.joinpath("evil.txt").write_text("out of scope\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        diagnostic = diagnose_reconciliation(
            before_snapshot,
            after_snapshot,
            ["src/file.py"],
            mutations,
        )

        assert any(c.path == "src/file.py" for c in diagnostic.allowed_changes)
        assert any(c.path == "src/file.py/evil.txt" for c in diagnostic.out_of_scope_changes)

    def test_partition_paths_file_scope_does_not_allow_descendants(self, temp_repo, task_worktree):
        """partition_paths uses the same file-scope semantics as reconciliation."""
        src_dir = task_worktree / "src"
        src_dir.mkdir()
        scoped_file = src_dir / "file.py"
        scoped_file.write_text("# original\n")
        run_git(temp_repo, ["add", "src/file.py"], cwd=task_worktree)
        run_git(temp_repo, ["commit", "-m", "add scoped file"], cwd=task_worktree)

        scope_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        allowed, out_of_scope = partition_paths(
            ["src/file.py"],
            ["src/file.py", "src/file.py/evil.txt"],
            scope_snapshot=scope_snapshot,
        )

        assert allowed == ["src/file.py"]
        assert out_of_scope == ["src/file.py/evil.txt"]

    def test_directory_scope_allows_children(self, temp_repo, task_worktree):
        """allowed_paths with directory scope allows child files."""
        # Create src directory and add file
        src_dir = task_worktree / "src"
        src_dir.mkdir()
        src_dir.joinpath("module.py").write_text("# original\n")
        run_git(temp_repo, ["add", "src/module.py"], cwd=task_worktree)
        run_git(temp_repo, ["commit", "-m", "add module"], cwd=task_worktree)

        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Agent modifies file under src/
        src_dir.joinpath("module.py").write_text("# modified\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        # allowed_paths contains only directory
        allowed_paths = ["src"]

        diagnostic = diagnose_reconciliation(before_snapshot, after_snapshot, allowed_paths, mutations)

        # src/module.py should be in allowed_changes
        module_allowed = next(
            (c for c in diagnostic.allowed_changes if c.path == "src/module.py"), None
        )
        assert module_allowed is not None
        assert len(diagnostic.out_of_scope_changes) == 0

    def test_partition_paths_directory_scope_allows_descendants(self, temp_repo, task_worktree):
        """partition_paths preserves directory scope descendant matching."""
        src_dir = task_worktree / "src"
        src_dir.mkdir()
        src_dir.joinpath("module.py").write_text("# original\n")
        run_git(temp_repo, ["add", "src/module.py"], cwd=task_worktree)
        run_git(temp_repo, ["commit", "-m", "add module"], cwd=task_worktree)

        scope_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        allowed, out_of_scope = partition_paths(
            ["src"],
            ["src", "src/module.py", "src2/module.py"],
            scope_snapshot=scope_snapshot,
        )

        assert allowed == ["src", "src/module.py"]
        assert out_of_scope == ["src2/module.py"]

    def test_nested_directory_allows_deep_children(self, temp_repo, task_worktree):
        """allowed_paths with directory scope allows deeply nested children."""
        # Create nested directory structure
        nested_dir = task_worktree / "src" / "nested" / "deep"
        nested_dir.mkdir(parents=True)
        nested_dir.joinpath("file.py").write_text("# original\n")
        run_git(temp_repo, ["add", "src"], cwd=task_worktree)
        run_git(temp_repo, ["commit", "-m", "add nested"], cwd=task_worktree)

        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Agent modifies deeply nested file
        nested_dir.joinpath("file.py").write_text("# modified\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        # allowed_paths contains only top directory
        allowed_paths = ["src"]

        diagnostic = diagnose_reconciliation(before_snapshot, after_snapshot, allowed_paths, mutations)

        # src/nested/deep/file.py should be in allowed_changes
        nested_allowed = next(
            (c for c in diagnostic.allowed_changes if "src/nested/deep/file.py" in c.path), None
        )
        assert nested_allowed is not None
        assert len(diagnostic.out_of_scope_changes) == 0

    def test_scope_does_not_match_similar_name(self, temp_repo, task_worktree):
        """Allowed scope "src" does NOT match "src2" prefix."""
        # Create src and src2 directories
        src_dir = task_worktree / "src"
        src2_dir = task_worktree / "src2"
        src_dir.mkdir()
        src2_dir.mkdir()

        src_dir.joinpath("file.py").write_text("# src\n")
        src2_dir.joinpath("file.py").write_text("# src2\n")

        run_git(temp_repo, ["add", "src", "src2"], cwd=task_worktree)
        run_git(temp_repo, ["commit", "-m", "add dirs"], cwd=task_worktree)

        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Agent modifies both
        src_dir.joinpath("file.py").write_text("# src modified\n")
        src2_dir.joinpath("file.py").write_text("# src2 modified\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        # allowed_paths contains only "src"
        allowed_paths = ["src"]

        diagnostic = diagnose_reconciliation(before_snapshot, after_snapshot, allowed_paths, mutations)

        # src/file.py should be allowed
        src_allowed = next(
            (c for c in diagnostic.allowed_changes if c.path == "src/file.py"), None
        )
        assert src_allowed is not None

        # src2/file.py should be out_of_scope
        src2_out_of_scope = next(
            (c for c in diagnostic.out_of_scope_changes if c.path == "src2/file.py"), None
        )
        assert src2_out_of_scope is not None

    def test_multiple_scopes_combined(self, temp_repo, task_worktree):
        """allowed_paths with multiple scopes works correctly."""
        # Create multiple directories
        for dir_name in ["src", "tests", "docs"]:
            d = task_worktree / dir_name
            d.mkdir()
            d.joinpath("file.txt").write_text(f"# {dir_name}\n")

        run_git(temp_repo, ["add", "src", "tests", "docs"], cwd=task_worktree)
        run_git(temp_repo, ["commit", "-m", "add dirs"], cwd=task_worktree)

        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Modify all directories
        for dir_name in ["src", "tests", "docs"]:
            d = task_worktree / dir_name
            d.joinpath("file.txt").write_text(f"# {dir_name} modified\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        # allowed_paths contains src and tests, but not docs
        allowed_paths = ["src", "tests"]

        diagnostic = diagnose_reconciliation(before_snapshot, after_snapshot, allowed_paths, mutations)

        # src and tests should be allowed
        assert any(c.path == "src/file.txt" and c.classification == "allowed" for c in diagnostic.allowed_changes)
        assert any(c.path == "tests/file.txt" and c.classification == "allowed" for c in diagnostic.allowed_changes)

        # docs should be out_of_scope
        assert any(c.path == "docs/file.txt" and c.classification == "out_of_scope" for c in diagnostic.out_of_scope_changes)

    def test_ac_r22_7_directory_scope_matches_children_no_ambiguity(self, temp_repo, task_worktree):
        """AC-R22-7: Directory scope allows children without false ambiguity.

        Regression test for fix: diagnose_reconciliation() must use hierarchical
        scope matching (path_matches_allowed_scope) instead of strict equality.

        Reproduces: allowed_paths = ["src"], change = "src/module.py"
        - src/module.py is allowed by directory scope "src"
        - Change MUST NOT be marked ambiguous due to path inequality
        - Verdict MUST NOT be request_human for this reason
        """
        # Create src directory with a file
        src_dir = task_worktree / "src"
        src_dir.mkdir()
        src_dir.joinpath("module.py").write_text("# original\n")
        run_git(temp_repo, ["add", "src/module.py"], cwd=task_worktree)
        run_git(temp_repo, ["commit", "-m", "add module"], cwd=task_worktree)

        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Agent modifies the file under src/ (coherent, allowed change)
        src_dir.joinpath("module.py").write_text("# modified by agent\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        # allowed_paths contains only directory "src"
        allowed_paths = ["src"]

        diagnostic = diagnose_reconciliation(before_snapshot, after_snapshot, allowed_paths, mutations)

        # Core assertions for AC-R22-7
        # 1. src/module.py must be classified as allowed (not out_of_scope)
        assert any(
            c.path == "src/module.py" and c.classification == "allowed"
            for c in diagnostic.allowed_changes
        ), "src/module.py must be allowed by directory scope 'src'"

        # 2. No out-of-scope changes should be detected
        assert len(diagnostic.out_of_scope_changes) == 0, \
            "No out-of-scope changes should exist when all changes are within allowed directory"

        # 3. Verdict must be safe_to_recover (not request_human)
        # This would be request_human if path matching was done by strict equality
        assert diagnostic.verdict == "safe_to_recover", \
            "Verdict must be safe_to_recover for allowed coherent changes. " \
            "Got request_human because diagnose_reconciliation() used strict equality " \
            "instead of hierarchical scope matching."

    def test_ac_r22_7_file_scope_does_not_match_descendants_in_ambiguity_check(self, temp_repo, task_worktree):
        """AC-R22-7: File scope MUST NOT allow descendants in ambiguity checking.

        Verifies that file-scope semantics are preserved: allowed_paths = ["src/file.py"]
        must NOT authorize "src/file.py/evil.txt" (where a directory replaced the file).
        """
        src_dir = task_worktree / "src"
        src_dir.mkdir()
        scoped_file = src_dir / "file.py"
        scoped_file.write_text("# original file\n")
        run_git(temp_repo, ["add", "src/file.py"], cwd=task_worktree)
        run_git(temp_repo, ["commit", "-m", "add scoped file"], cwd=task_worktree)

        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Simulate malicious transformation: file becomes directory with evil content
        scoped_file.unlink()
        scoped_file.mkdir()
        scoped_file.joinpath("evil.txt").write_text("payload\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        diagnostic = diagnose_reconciliation(
            before_snapshot,
            after_snapshot,
            ["src/file.py"],
            mutations,
        )

        # src/file.py (the file itself) is allowed
        assert any(
            c.path == "src/file.py" and c.classification == "allowed"
            for c in diagnostic.allowed_changes
        ), "Original file path must be in allowed changes"

        # src/file.py/evil.txt is NOT allowed (file scope does not permit descendants)
        assert any(
            c.path == "src/file.py/evil.txt" and c.classification == "out_of_scope"
            for c in diagnostic.out_of_scope_changes
        ), "Pseudo-descendant of file scope must be out_of_scope"


def test_untracked_file_content_preservation(temp_repo):
    """Point 2: Verify untracked file content is properly preserved with hash.
    AC-R11-11: Untracked files must be saved with content and hash for reconstitution.
    """
    from autodev.correct_task import _save_out_of_scope_patch
    from pathlib import Path
    import json
    import base64
    import hashlib

    task_worktree = temp_repo / ".autodev" / "worktrees" / "test-task"
    task_worktree.mkdir(parents=True, exist_ok=True)
    run_git(temp_repo, ["worktree", "add", str(task_worktree), "autodev/test-task"])

    try:
        # Create untracked files
        untracked_text = task_worktree / "untracked-text.txt"
        untracked_text.write_text("This is untracked content\n", encoding="utf-8")

        untracked_binary = task_worktree / "untracked.bin"
        untracked_binary.write_bytes(b"\x00\x01\x02\xff\xfe\xfd")

        correction_dir = temp_repo / ".autodev" / "corrections" / "01"
        correction_dir.mkdir(parents=True, exist_ok=True)
        run_dir = temp_repo / ".autodev" / "runs" / "test-task"
        write_product_run_proof(temp_repo, "test-task", run_dir, "product-run-test-task")

        # Run the save function
        _save_out_of_scope_patch(
            temp_repo,
            task_worktree,
            "HEAD",
            ["untracked-text.txt", "untracked.bin"],
            correction_dir,
            run_dir=run_dir,
            task_id="test-task",
        )

        # Verify untracked content file exists and contains base64-encoded content
        untracked_content_file = correction_dir / "patches" / "out-of-scope-untracked-content.json"
        assert untracked_content_file.exists(), "Untracked content file not saved"

        content_data = json.loads(untracked_content_file.read_text(encoding="utf-8"))
        assert "untracked_files" in content_data
        assert "untracked-text.txt" in content_data["untracked_files"]
        assert "untracked.bin" in content_data["untracked_files"]

        # Verify text file content
        text_entry = content_data["untracked_files"]["untracked-text.txt"]
        assert text_entry["size"] == len("This is untracked content\n")
        assert text_entry["encoding"] == "base64"
        assert "content_b64" in text_entry
        assert "content_hash" in text_entry
        decoded_content = base64.b64decode(text_entry["content_b64"])
        assert decoded_content == b"This is untracked content\n"

        # Verify binary file content
        binary_entry = content_data["untracked_files"]["untracked.bin"]
        assert binary_entry["size"] == 6
        assert binary_entry["encoding"] == "base64"
        decoded_binary = base64.b64decode(binary_entry["content_b64"])
        assert decoded_binary == b"\x00\x01\x02\xff\xfe\xfd"

        # Verify deterministic hashes
        expected_text_hash = hashlib.sha256(b"This is untracked content\n").hexdigest()
        assert text_entry["content_hash"] == expected_text_hash
        expected_binary_hash = hashlib.sha256(b"\x00\x01\x02\xff\xfe\xfd").hexdigest()
        assert binary_entry["content_hash"] == expected_binary_hash

        # Verify manifest also has hash
        manifest_file = correction_dir / "patches" / "out-of-scope-untracked.json"
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert manifest_data["untracked_files"]["untracked-text.txt"]["content_hash"] == expected_text_hash
    finally:
        run_git(temp_repo, ["worktree", "remove", str(task_worktree)])


def test_git_reconstruction_branch_verification(temp_repo):
    """Point 5: Verify branch exists and points to correct commit.
    AC-R2.2, AC-R2.3: Compare persisted state to Git reality.
    """
    from autodev.git_context import verify_branch_exists, verify_branch_head
    from autodev.git_tools import current_head

    # Create a branch
    run_git(temp_repo, ["checkout", "-b", "test/reconstruction-branch"])
    test_file = temp_repo / "test-reconstruction.txt"
    test_file.write_text("content for reconstruction\n")
    run_git(temp_repo, ["add", "."])
    run_git(temp_repo, ["commit", "-m", "test reconstruction"])
    expected_commit = current_head(temp_repo)

    # Verify branch exists
    incident = verify_branch_exists(temp_repo, "test/reconstruction-branch")
    assert incident is None, f"Branch should exist but got incident: {incident}"

    # Verify branch points to correct commit
    incident = verify_branch_head(temp_repo, "test/reconstruction-branch", expected_commit)
    assert incident is None, f"Branch HEAD should match but got incident: {incident}"

    # Verify detection of divergence
    wrong_commit = "0000000000000000000000000000000000000000"
    incident = verify_branch_head(temp_repo, "test/reconstruction-branch", wrong_commit)
    assert incident is not None
    assert incident.code == "BRANCH_HEAD_DIVERGENCE"
    assert incident.expected_value == wrong_commit
    assert incident.actual_value == expected_commit

    # Verify detection of non-existent branch
    incident = verify_branch_exists(temp_repo, "nonexistent/branch")
    assert incident is not None
    assert incident.code == "BRANCH_NOT_FOUND"


def test_git_reconstruction_worktree_verification(temp_repo):
    """Point 5: Verify worktree state (path, registration, branch, HEAD).
    AC-R2.2, AC-R2.3: Comprehensive Git reality check.
    """
    from autodev.git_context import verify_worktree_state
    from autodev.git_tools import head_commit, current_branch

    task_worktree = temp_repo / ".autodev" / "worktrees" / "test-reconstruction"
    create_branch(temp_repo, "autodev/test-task", "HEAD")
    add_worktree(temp_repo, task_worktree, "autodev/test-task")

    try:
        actual_branch = current_branch(temp_repo, cwd=task_worktree)
        actual_head = head_commit(temp_repo, task_worktree)

        # Verify correct state - no incidents
        incidents = verify_worktree_state(temp_repo, task_worktree, actual_branch, actual_head)
        assert len(incidents) == 0, f"Should have no incidents but got: {incidents}"

        # Verify detection of wrong branch
        incidents = verify_worktree_state(temp_repo, task_worktree, "wrong-branch", actual_head)
        assert len(incidents) == 1
        assert incidents[0].code == "WORKTREE_BRANCH_DIVERGENCE"

        # Verify detection of wrong HEAD
        wrong_commit = "0000000000000000000000000000000000000000"
        incidents = verify_worktree_state(temp_repo, task_worktree, actual_branch, wrong_commit)
        assert len(incidents) == 1
        assert incidents[0].code == "WORKTREE_HEAD_DIVERGENCE"

        # Verify detection of non-existent worktree path
        nonexistent_path = temp_repo / ".autodev" / "worktrees" / "nonexistent"
        incidents = verify_worktree_state(temp_repo, nonexistent_path)
        assert len(incidents) == 1
        assert incidents[0].code == "WORKTREE_PATH_NOT_FOUND"
    finally:
        run_git(temp_repo, ["worktree", "remove", str(task_worktree)])


def test_reconstruction_idempotent_repeated_verification(temp_repo):
    """Point 5: Verify that repeated reconstruction checks yield identical results.
    AC-R2.2: Idempotent reconciliation without Git mutations.
    """
    from autodev.git_context import verify_branch_exists, verify_worktree_state
    from autodev.git_tools import head_commit, current_branch

    task_worktree = temp_repo / ".autodev" / "worktrees" / "test-idempotent"
    create_branch(temp_repo, "autodev/test-task", "HEAD")
    add_worktree(temp_repo, task_worktree, "autodev/test-task")

    try:
        actual_branch = current_branch(temp_repo, cwd=task_worktree)
        actual_head = head_commit(temp_repo, task_worktree)

        # Run verification multiple times
        results = []
        for i in range(3):
            incidents = verify_worktree_state(temp_repo, task_worktree, actual_branch, actual_head)
            results.append(len(incidents) == 0)

        # All runs should yield same result
        assert all(results), "Reconstruction should be idempotent"
    finally:
        run_git(temp_repo, ["worktree", "remove", str(task_worktree)])


def test_reconciliation_requires_review_signal(temp_repo):
    """Point 4: Verify that reconciliation_requires_review signal is properly set.
    AC-R22-10: Relancer validations et revue si changements significatifs détectés.
    This test verifies a real post-snapshot mutation is detected and routed
    through the orchestrator as a fresh validation/review cycle.
    """
    from autodev.git_context import (
        analyze_mutations,
        capture_git_snapshot,
        diagnose_reconciliation,
    )

    # Setup a task worktree
    task_worktree = temp_repo / ".autodev" / "worktrees" / "test-review-signal"
    task_worktree.mkdir(parents=True, exist_ok=True)
    run_git(temp_repo, ["worktree", "add", str(task_worktree), "autodev/test-task"])

    try:
        # Capture snapshots
        before_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Create out-of-scope modifications after the baseline snapshot,
        # simulating a mutation attributable to the supervised attempt.
        out_of_scope_file = task_worktree / "out-of-scope-file.txt"
        out_of_scope_file.write_text("This file is out of scope\n")

        after_snapshot = capture_git_snapshot(temp_repo, worktree_path=task_worktree)

        # Analyze mutations
        mutations = analyze_mutations(before_snapshot, before_snapshot, after_snapshot)

        # Diagnose with restricted allowed_paths to trigger requires_review
        allowed_paths = ["src", "tests"]  # Deliberately exclude out-of-scope-file.txt
        diagnostic = diagnose_reconciliation(before_snapshot, after_snapshot, allowed_paths, mutations)

        # Out-of-scope file should trigger requires_review verdict
        assert diagnostic.verdict == "requires_review", \
            f"Expected 'requires_review' verdict for out-of-scope changes, got '{diagnostic.verdict}'"

        # Should have out-of-scope changes
        assert len(diagnostic.out_of_scope_changes) > 0, "Should detect out-of-scope changes"

        # Evidence should document the divergence
        assert diagnostic.has_divergence is True, "Should detect divergence"

    finally:
        run_git(temp_repo, ["worktree", "remove", str(task_worktree)])


def test_run_feature_reruns_review_after_reconciliation_requires_review(tmp_path: Path) -> None:
    """AC-R22-10: Significant reconciliation changes rerun validation/review."""
    from test_run_feature import build_runners, make_review_payload, prepare_backlog
    from autodev.run_feature import run_feature
    from test_task_runner import make_task

    repo, backlog = prepare_backlog(tmp_path, [make_task("TASK-R22-10")])
    capture, run_fn, review_fn, _correct_fn, integrate_fn = build_runners(
        repo,
        review_sequences={"TASK-R22-10": ["CORRECTION_REQUIRED", "APPROVED"]},
    )

    def significant_correction(*, backlog_json: Path, task_id: str) -> dict[str, object]:
        capture["correct"].append(task_id)
        return {
            "task_id": task_id,
            "status": "success",
            "reconciliation_requires_review": True,
            "reconciliation_verdict": "requires_review",
        }

    result = run_feature(
        backlog,
        run_task_fn=run_fn,
        review_task_fn=review_fn,
        correct_task_fn=significant_correction,
        integrate_task_fn=integrate_fn,
    )

    assert result["status"] == "COMPLETED"
    assert capture["review"] == ["TASK-R22-10", "TASK-R22-10"]
    assert capture["correct"] == ["TASK-R22-10"]
    assert capture["integrate"] == ["TASK-R22-10"]


def test_patch_inventory_metadata_preparation(temp_repo):
    """Point 3: Verify that patch inventory metadata is correctly prepared.
    AC-R22-6: Le superviseur conserve un inventaire des patchs.
    """
    from autodev.correct_task import _save_out_of_scope_patch
    import json

    task_worktree = temp_repo / ".autodev" / "worktrees" / "test-inventory"
    task_worktree.mkdir(parents=True, exist_ok=True)
    run_git(temp_repo, ["worktree", "add", str(task_worktree), "autodev/test-task"])

    try:
        # Create out-of-scope files
        out_of_scope_file = task_worktree / "out-of-scope.txt"
        out_of_scope_file.write_text("out of scope content\n")

        correction_dir = temp_repo / ".autodev" / "corrections" / "01"
        correction_dir.mkdir(parents=True, exist_ok=True)

        run_dir = temp_repo / ".autodev" / "runs" / "test-inventory"
        write_product_run_proof(temp_repo, "test-inventory", run_dir, "product-run-test-inventory")

        # Run the save function
        _save_out_of_scope_patch(
            temp_repo,
            task_worktree,
            "HEAD",
            ["out-of-scope.txt"],
            correction_dir,
            run_dir=run_dir,
            task_id="test-inventory",
        )

        # Verify metadata file exists and contains required inventory fields
        metadata_file = correction_dir / "patches" / "out-of-scope-metadata.json"
        assert metadata_file.exists(), "Metadata file not saved"

        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        assert metadata["reason"] == "out_of_scope_restoration"
        assert metadata["restored_paths"] == ["out-of-scope.txt"]
        assert "artifacts" in metadata
        assert "purpose" in metadata
        assert "restoration_command" in metadata

        # Verify that the artifacts dictionary references the correct patch files
        artifacts = metadata["artifacts"]
        assert "staged_patch" in artifacts
        assert "unstaged_patch" in artifacts
        assert "untracked_manifest" in artifacts

        # Verify all artifact files exist
        patches_dir = correction_dir / "patches"
        assert (patches_dir / artifacts["staged_patch"]).exists()
        assert (patches_dir / artifacts["unstaged_patch"]).exists()
        assert (patches_dir / artifacts["untracked_manifest"]).exists()

    finally:
        run_git(temp_repo, ["worktree", "remove", str(task_worktree)])


def test_out_of_scope_patch_inventory_uses_real_product_run_id(temp_repo):
    """AC-R22-6: Persistent inventory is attached to an explicit product run."""
    from autodev.correct_task import _save_out_of_scope_patch
    from autodev.product_state import ProductRunState, ProductStateManager
    import json

    task_worktree = temp_repo / ".autodev" / "worktrees" / "inventory-real-run"
    task_worktree.mkdir(parents=True, exist_ok=True)
    run_git(temp_repo, ["worktree", "add", str(task_worktree), "autodev/test-task"])

    try:
        product_run_id = "product-run-real"
        state_manager = ProductStateManager(temp_repo, product_run_id)
        state = ProductRunState(
            run_id=product_run_id,
            plan_id="plan-001",
            product_key="plan-001",
            schema_version="1.0",
            plan_hash="hash-001",
            started_at=datetime.now(timezone.utc).isoformat(),
            run_namespace=state_manager.run_namespace,
        )
        state_manager.reserve_run_namespace(plan_id=state.plan_id, plan_hash=state.plan_hash)
        with state_manager.bootstrap_writes():
            state_manager.write_state(state)

        out_of_scope_file = task_worktree / "out-of-scope.txt"
        out_of_scope_file.write_text("out of scope content\n", encoding="utf-8")

        correction_dir = temp_repo / ".autodev" / "runs" / "TASK-AC-R22-6" / "corrections" / "01"
        run_dir = temp_repo / ".autodev" / "runs" / "TASK-AC-R22-6"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "result.json").write_text(
            json.dumps({"task_id": "TASK-AC-R22-6", "run_id": product_run_id}, indent=2),
            encoding="utf-8",
        )

        _save_out_of_scope_patch(
            temp_repo,
            task_worktree,
            "HEAD",
            ["out-of-scope.txt"],
            correction_dir,
            run_dir=run_dir,
            task_id="TASK-AC-R22-6",
        )
        restore_paths(temp_repo, task_worktree, "HEAD", ["out-of-scope.txt"])

        inventory = ProductStateManager(temp_repo, product_run_id).get_patches_inventory()
        assert len(inventory) == 1
        entry = inventory[0]
        assert entry.run_id == product_run_id
        assert entry.task_id == "TASK-AC-R22-6"
        assert entry.paths_affected == ["out-of-scope.txt"]
        assert entry.reason == "out_of_scope_restoration"
        assert entry.metadata["restored_paths"] == ["out-of-scope.txt"]
        assert entry.metadata["artifacts"]["untracked_content"] == "out-of-scope-untracked-content.json"
        assert entry.metadata["untracked_metadata"]["untracked_files"]["out-of-scope.txt"]["content_hash"]
        assert entry.metadata["untracked_content"]["untracked_files"]["out-of-scope.txt"]["content_b64"]
        assert not (temp_repo / ".autodev" / "runs" / "products" / "TASK-AC-R22-6").exists()
        assert not (task_worktree / "out-of-scope.txt").exists()

    finally:
        run_git(temp_repo, ["worktree", "remove", str(task_worktree)])


def test_out_of_scope_patch_inventory_missing_run_id_blocks_restoration(temp_repo, monkeypatch):
    """AC-R22-6: Missing product run proof blocks automatic restoration."""
    from autodev.correct_task import CorrectTaskError, _save_out_of_scope_patch
    import autodev.correct_task as correct_task_module
    import json

    task_worktree = temp_repo / ".autodev" / "worktrees" / "inventory-missing-run"
    task_worktree.mkdir(parents=True, exist_ok=True)
    run_git(temp_repo, ["worktree", "add", str(task_worktree), "autodev/test-task"])

    try:
        out_of_scope_file = task_worktree / "out-of-scope.txt"
        out_of_scope_file.write_text("out of scope content\n", encoding="utf-8")

        correction_dir = temp_repo / ".autodev" / "runs" / "TASK-NO-RUN" / "corrections" / "01"
        run_dir = temp_repo / ".autodev" / "runs" / "TASK-NO-RUN"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "result.json").write_text(
            json.dumps({"task_id": "TASK-NO-RUN"}, indent=2),
            encoding="utf-8",
        )

        restore_spy = Mock()
        monkeypatch.setattr(correct_task_module, "restore_paths", restore_spy)

        with pytest.raises(CorrectTaskError, match="run_id produit"):
            _save_out_of_scope_patch(
                temp_repo,
                task_worktree,
                "HEAD",
                ["out-of-scope.txt"],
                correction_dir,
                run_dir=run_dir,
                task_id="TASK-NO-RUN",
            )

        restore_spy.assert_not_called()
        assert not (temp_repo / ".autodev" / "runs" / "products" / "TASK-NO-RUN").exists()
        assert out_of_scope_file.exists()

    finally:
        run_git(temp_repo, ["worktree", "remove", str(task_worktree)])


def test_staged_patch_capture_failure_blocks_restoration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from autodev.correct_task import CorrectTaskError, correct_task
    import autodev.correct_task as correct_task_module

    repo, backlog, worktree, _ = prepare_correction_case(tmp_path)
    original_run_git = correct_task_module.run_git

    def fail_staged_diff(repo_root: Path, args: list[str], cwd: Path | None = None):
        if args[:3] == ["diff", "--cached", "HEAD"]:
            return subprocess.CompletedProcess(["git", *args], 129, "", "fatal staged capture")
        return original_run_git(repo_root, args, cwd=cwd)

    restore_spy = Mock()
    monkeypatch.setattr(correct_task_module, "run_git", fail_staged_diff)
    monkeypatch.setattr(correct_task_module, "restore_paths", restore_spy)

    def out_of_scope_change(target: Path) -> None:
        (target / "package.json").write_text('{"name":"demo","version":"8.0.0"}\n', encoding="utf-8")

    with pytest.raises(CorrectTaskError, match="staged"):
        correct_task(backlog, "TASK-PILOT-002", claude_runner=make_claude_runner([out_of_scope_change]))

    restore_spy.assert_not_called()
    assert (worktree / "package.json").read_text(encoding="utf-8") == '{"name":"demo","version":"8.0.0"}\n'


def test_unstaged_patch_capture_failure_blocks_restoration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from autodev.correct_task import CorrectTaskError, correct_task
    import autodev.correct_task as correct_task_module

    repo, backlog, worktree, _ = prepare_correction_case(tmp_path)
    original_run_git = correct_task_module.run_git

    def fail_unstaged_diff(repo_root: Path, args: list[str], cwd: Path | None = None):
        if args[:2] == ["diff", "--"] or (len(args) > 1 and args[0] == "diff" and args[1] == "--"):
            return subprocess.CompletedProcess(["git", *args], 129, "", "fatal unstaged capture")
        return original_run_git(repo_root, args, cwd=cwd)

    restore_spy = Mock()
    monkeypatch.setattr(correct_task_module, "run_git", fail_unstaged_diff)
    monkeypatch.setattr(correct_task_module, "restore_paths", restore_spy)

    def out_of_scope_change(target: Path) -> None:
        (target / "package.json").write_text('{"name":"demo","version":"8.0.0"}\n', encoding="utf-8")

    with pytest.raises(CorrectTaskError, match="unstaged"):
        correct_task(backlog, "TASK-PILOT-002", claude_runner=make_claude_runner([out_of_scope_change]))

    restore_spy.assert_not_called()
    assert (worktree / "package.json").read_text(encoding="utf-8") == '{"name":"demo","version":"8.0.0"}\n'


def test_untracked_capture_failure_blocks_restoration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from autodev.correct_task import CorrectTaskError, correct_task
    import autodev.correct_task as correct_task_module

    repo, backlog, worktree, _ = prepare_correction_case(tmp_path)
    original_git_output = correct_task_module.git_output

    def fail_untracked_probe(repo_root: Path, args: list[str], cwd: Path | None = None) -> str:
        if args == ["ls-files", "--cached", "--", "generated.txt"]:
            raise GitError("fatal untracked probe")
        return original_git_output(repo_root, args, cwd=cwd)

    restore_spy = Mock()
    monkeypatch.setattr(correct_task_module, "git_output", fail_untracked_probe)
    monkeypatch.setattr(correct_task_module, "restore_paths", restore_spy)

    def mixed_out_of_scope_change(target: Path) -> None:
        (target / "package.json").write_text('{"name":"demo","version":"8.0.0"}\n', encoding="utf-8")
        (target / "generated.txt").write_text("untracked proof required\n", encoding="utf-8")

    with pytest.raises(CorrectTaskError, match="generated.txt"):
        correct_task(backlog, "TASK-PILOT-002", claude_runner=make_claude_runner([mixed_out_of_scope_change]))

    restore_spy.assert_not_called()
    assert (worktree / "package.json").read_text(encoding="utf-8") == '{"name":"demo","version":"8.0.0"}\n'
    assert (worktree / "generated.txt").read_text(encoding="utf-8") == "untracked proof required\n"


def test_allowed_preexisting_dirty_file_with_new_fingerprint_delta_is_current_attempt(
    tmp_path: Path,
) -> None:
    """AC-R22-4/5: A new delta on an already-dirty allowed file is kept."""
    from autodev.correct_task import correct_task

    _, backlog, worktree, _ = prepare_correction_case(
        tmp_path,
        allowed_paths=["src/task-pilot-002.py"],
    )
    target_file = worktree / "src" / "task-pilot-002.py"
    target_file.write_text("preexisting dirty\n", encoding="utf-8")

    def update_preexisting_allowed_file(target: Path) -> None:
        (target / "src" / "task-pilot-002.py").write_text(
            "preexisting dirty plus correction\n",
            encoding="utf-8",
        )

    result = correct_task(
        backlog,
        "TASK-PILOT-002",
        claude_runner=make_claude_runner([update_preexisting_allowed_file]),
    )

    assert result["status"] == "success"
    assert result["remaining_allowed_paths"] == ["src/task-pilot-002.py"]
    assert result["modified_paths"] == ["src/task-pilot-002.py"]
    assert result["reconciliation_verdict"] == "safe_to_recover"
    assert target_file.read_text(encoding="utf-8") == "preexisting dirty plus correction\n"


def test_allowed_preexisting_dirty_file_without_fingerprint_delta_is_not_current_attempt(
    tmp_path: Path,
) -> None:
    """AC-R22-4: An unchanged preexisting dirty file is not attributed to the attempt."""
    from autodev.correct_task import correct_task

    _, backlog, worktree, produced_commit = prepare_correction_case(
        tmp_path,
        allowed_paths=["src/task-pilot-002.py"],
    )
    target_file = worktree / "src" / "task-pilot-002.py"
    target_file.write_text("preexisting dirty only\n", encoding="utf-8")

    result = correct_task(
        backlog,
        "TASK-PILOT-002",
        claude_runner=make_claude_runner([lambda _: None, lambda _: None]),
    )

    assert result["status"] == "no_allowed_changes"
    assert result["produced_commit"] == produced_commit
    assert result["remaining_allowed_paths"] == []
    assert result["modified_paths"] == []
    assert target_file.read_text(encoding="utf-8") == "preexisting dirty only\n"


def test_preexisting_dirty_state_is_never_restored_or_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-R11-9: Preexisting dirty content is protected from destructive restore."""
    from autodev.correct_task import CorrectTaskError, correct_task
    import autodev.correct_task as correct_task_module

    _, backlog, worktree, _ = prepare_correction_case(tmp_path, allowed_paths=["src"])
    package_file = worktree / "package.json"
    package_file.write_text('{"name":"demo","version":"preexisting"}\n', encoding="utf-8")

    restore_spy = Mock()
    monkeypatch.setattr(correct_task_module, "restore_paths", restore_spy)

    def update_preexisting_out_of_scope_file(target: Path) -> None:
        (target / "package.json").write_text(
            '{"name":"demo","version":"preexisting-plus-attempt"}\n',
            encoding="utf-8",
        )

    with pytest.raises(CorrectTaskError):
        correct_task(
            backlog,
            "TASK-PILOT-002",
            claude_runner=make_claude_runner([update_preexisting_out_of_scope_file]),
        )

    restore_spy.assert_not_called()
    assert package_file.read_text(encoding="utf-8") == (
        '{"name":"demo","version":"preexisting-plus-attempt"}\n'
    )


def test_missing_product_state_support_blocks_out_of_scope_restoration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from autodev.correct_task import CorrectTaskError, correct_task
    import autodev.correct_task as correct_task_module

    repo, backlog, worktree, _ = prepare_correction_case(tmp_path)
    restore_spy = Mock()
    monkeypatch.setattr(correct_task_module, "HAS_PRODUCT_STATE", False)
    monkeypatch.setattr(correct_task_module, "ProductStateManager", None)
    monkeypatch.setattr(correct_task_module, "restore_paths", restore_spy)

    def out_of_scope_change(target: Path) -> None:
        (target / "package.json").write_text('{"name":"demo","version":"8.0.0"}\n', encoding="utf-8")

    with pytest.raises(CorrectTaskError, match="ProductStateManager"):
        correct_task(backlog, "TASK-PILOT-002", claude_runner=make_claude_runner([out_of_scope_change]))

    restore_spy.assert_not_called()
    assert (worktree / "package.json").read_text(encoding="utf-8") == '{"name":"demo","version":"8.0.0"}\n'


def test_out_of_scope_patch_inventory_save_patch_failure_blocks_restoration(
    temp_repo,
    monkeypatch,
):
    """AC-R22-6: save_patch() failures are not silent and block restoration."""
    from autodev.correct_task import CorrectTaskError, _save_out_of_scope_patch
    from autodev.product_state import ProductRunState, ProductStateManager
    import autodev.correct_task as correct_task_module
    import json

    task_worktree = temp_repo / ".autodev" / "worktrees" / "inventory-save-fails"
    task_worktree.mkdir(parents=True, exist_ok=True)
    run_git(temp_repo, ["worktree", "add", str(task_worktree), "autodev/test-task"])

    try:
        product_run_id = "product-run-save-fails"
        state_manager = ProductStateManager(temp_repo, product_run_id)
        state = ProductRunState(
            run_id=product_run_id,
            plan_id="plan-001",
            product_key="plan-001",
            schema_version="1.0",
            plan_hash="hash-001",
            started_at=datetime.now(timezone.utc).isoformat(),
            run_namespace=state_manager.run_namespace,
        )
        state_manager.reserve_run_namespace(plan_id=state.plan_id, plan_hash=state.plan_hash)
        with state_manager.bootstrap_writes():
            state_manager.write_state(state)

        out_of_scope_file = task_worktree / "out-of-scope.txt"
        out_of_scope_file.write_text("out of scope content\n", encoding="utf-8")

        correction_dir = temp_repo / ".autodev" / "runs" / "TASK-SAVE-FAILS" / "corrections" / "01"
        run_dir = temp_repo / ".autodev" / "runs" / "TASK-SAVE-FAILS"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "result.json").write_text(
            json.dumps({"task_id": "TASK-SAVE-FAILS", "run_id": product_run_id}, indent=2),
            encoding="utf-8",
        )

        def fail_save_patch(self, *args, **kwargs):
            raise OSError("inventory unavailable")

        restore_spy = Mock()
        monkeypatch.setattr(ProductStateManager, "save_patch", fail_save_patch)
        monkeypatch.setattr(correct_task_module, "restore_paths", restore_spy)

        with pytest.raises(CorrectTaskError, match="inventory unavailable"):
            _save_out_of_scope_patch(
                temp_repo,
                task_worktree,
                "HEAD",
                ["out-of-scope.txt"],
                correction_dir,
                run_dir=run_dir,
                task_id="TASK-SAVE-FAILS",
            )

        restore_spy.assert_not_called()
        assert out_of_scope_file.exists()

    finally:
        run_git(temp_repo, ["worktree", "remove", str(task_worktree)])


def test_reconciliation_with_untracked_restoration(temp_repo):
    """Test complete reconciliation cycle: capture -> save -> restore -> verify.

    AC-R22-3: Capture and compare content via fingerprints.
    AC-R11-11: Save untracked file content for reconstitution before restore.
    AC-R22-5: Untracked files in allowed_paths should prevent "no_allowed_changes" verdict.

    This test verifies:
    1. Untracked files are properly captured in snapshots
    2. Content is saved byte-for-byte (base64 encoded)
    3. SHA-256 hashes match before and after restoration
    4. Restoration can be reversed using saved content
    """
    from autodev.correct_task import _save_out_of_scope_patch
    from autodev.git_context import (
        capture_git_snapshot,
        capture_content_fingerprints,
        detect_content_changes,
        classify_modifications,
        analyze_mutations,
    )
    import json
    import base64
    import hashlib

    task_worktree = temp_repo / ".autodev" / "worktrees" / "reconcile-test"
    task_worktree.mkdir(parents=True, exist_ok=True)
    run_git(temp_repo, ["worktree", "add", str(task_worktree), "autodev/test-task"])

    try:
        # Phase 1: Create test files (untracked and tracked)
        untracked_text = task_worktree / "out-of-scope-generated.txt"
        untracked_text.write_text("Generated by agent\n", encoding="utf-8")

        untracked_binary = task_worktree / "out-of-scope-data.bin"
        untracked_binary.write_bytes(b"\x42\x43\x44\xff\xfe")

        tracked_file = task_worktree / "tracked.py"
        tracked_file.write_text("print('hello')\n", encoding="utf-8")
        run_git(temp_repo, ["add", str(tracked_file)], cwd=task_worktree)
        run_git(temp_repo, ["commit", "-m", "tracked file"], cwd=task_worktree)

        # Phase 2: Capture initial snapshot
        snapshot_before = capture_git_snapshot(
            temp_repo,
            worktree_path=task_worktree,
            timestamp_label="before_modifications"
        )

        fingerprints_before = capture_content_fingerprints(snapshot_before)

        # Verify untracked files are captured
        assert "out-of-scope-generated.txt" in snapshot_before.untracked
        assert "out-of-scope-data.bin" in snapshot_before.untracked
        assert fingerprints_before.untracked_file_hashes["out-of-scope-generated.txt"] is not None
        assert fingerprints_before.untracked_file_hashes["out-of-scope-data.bin"] is not None

        # Phase 3: Save patches before restoration (simulating out-of-scope restoration)
        correction_dir = temp_repo / ".autodev" / "corrections" / "01"
        correction_dir.mkdir(parents=True, exist_ok=True)
        run_dir = temp_repo / ".autodev" / "runs" / "reconcile-test"
        write_product_run_proof(temp_repo, "reconcile-test", run_dir, "product-run-reconcile-test")

        out_of_scope_paths = ["out-of-scope-generated.txt", "out-of-scope-data.bin"]
        _save_out_of_scope_patch(
            temp_repo,
            task_worktree,
            "HEAD",
            out_of_scope_paths,
            correction_dir,
            run_dir=run_dir,
            task_id="reconcile-test",
        )

        # Verify content was saved with correct encoding
        untracked_content_file = correction_dir / "patches" / "out-of-scope-untracked-content.json"
        assert untracked_content_file.exists()

        content_data = json.loads(untracked_content_file.read_text(encoding="utf-8"))

        # Verify text file
        text_entry = content_data["untracked_files"]["out-of-scope-generated.txt"]
        assert text_entry["encoding"] == "base64"
        decoded_text = base64.b64decode(text_entry["content_b64"])
        assert decoded_text == b"Generated by agent\n"
        expected_text_hash = hashlib.sha256(b"Generated by agent\n").hexdigest()
        assert text_entry["content_hash"] == expected_text_hash

        # Verify binary file
        binary_entry = content_data["untracked_files"]["out-of-scope-data.bin"]
        decoded_binary = base64.b64decode(binary_entry["content_b64"])
        assert decoded_binary == b"\x42\x43\x44\xff\xfe"
        expected_binary_hash = hashlib.sha256(b"\x42\x43\x44\xff\xfe").hexdigest()
        assert binary_entry["content_hash"] == expected_binary_hash

        # Phase 4: Restore out-of-scope paths through Autodev's bounded primitive.
        restore_paths(
            temp_repo,
            task_worktree,
            "HEAD",
            ["out-of-scope-generated.txt", "out-of-scope-data.bin"],
        )

        # Verify files are gone (restored to HEAD state: not in tree)
        assert not (task_worktree / "out-of-scope-generated.txt").exists()
        assert not (task_worktree / "out-of-scope-data.bin").exists()

        # Phase 5: Verify content can be reconstituted from saved artifacts
        # This demonstrates that AC-R11-11 requirement is met: content is permanently recoverable
        reconstituted_text = base64.b64decode(text_entry["content_b64"])
        assert reconstituted_text == b"Generated by agent\n"

        reconstituted_binary = base64.b64decode(binary_entry["content_b64"])
        assert reconstituted_binary == b"\x42\x43\x44\xff\xfe"

        # Verify hashes match what was saved
        actual_text_hash = hashlib.sha256(reconstituted_text).hexdigest()
        actual_binary_hash = hashlib.sha256(reconstituted_binary).hexdigest()
        assert actual_text_hash == expected_text_hash
        assert actual_binary_hash == expected_binary_hash

        # Phase 6: Verify manifest also preserved hashes for quick lookup
        manifest_file = correction_dir / "patches" / "out-of-scope-untracked.json"
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert manifest_data["untracked_files"]["out-of-scope-generated.txt"]["content_hash"] == expected_text_hash
        assert manifest_data["untracked_files"]["out-of-scope-data.bin"]["content_hash"] == expected_binary_hash

        from autodev.product_state import ProductStateManager

        inventory = ProductStateManager(temp_repo, "product-run-reconcile-test").get_patches_inventory()
        assert len(inventory) == 1
        inventory_entry = inventory[0]
        assert inventory_entry.reason == "out_of_scope_restoration"
        assert inventory_entry.paths_affected == ["out-of-scope-generated.txt", "out-of-scope-data.bin"]
        assert (
            inventory_entry.metadata["untracked_content"]["untracked_files"]
            ["out-of-scope-data.bin"]["content_b64"]
            == binary_entry["content_b64"]
        )

    finally:
        run_git(temp_repo, ["worktree", "remove", str(task_worktree)])
