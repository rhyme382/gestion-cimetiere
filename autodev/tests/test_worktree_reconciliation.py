"""Tests for fine-grained worktree reconciliation with content fingerprints.

AC-R22: Réconciliation fine du worktree et empreintes de contenu
AC-R11: Réconciliation après interruption
"""
import tempfile
from datetime import datetime, timezone
from pathlib import Path

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
    run_git,
)


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
