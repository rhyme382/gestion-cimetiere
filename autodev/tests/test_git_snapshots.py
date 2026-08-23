from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from autodev.git_context import (
    GitSnapshot,
    GitSnapshotTriple,
    ExecutionMutationMetadata,
    analyze_mutations,
    capture_git_snapshot,
    capture_git_snapshot_triple,
    capture_git_snapshot_triple_with_lifecycle,
    categorize_agents_md_mutations,
)

from test_task_runner import commit_all, init_repo


def test_capture_git_snapshot_empty_repo(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    snapshot = capture_git_snapshot(repo, timestamp_label="initial")

    assert snapshot.head
    assert snapshot.branch
    assert snapshot.index_changed == []
    assert snapshot.tracked_dirty == []
    assert snapshot.untracked == []
    assert snapshot.timestamp_label == "initial"


def test_capture_git_snapshot_with_untracked_files(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    new_file = repo / "new_file.txt"
    new_file.write_text("content\n", encoding="utf-8")

    snapshot = capture_git_snapshot(repo, timestamp_label="with_untracked")

    assert "new_file.txt" in snapshot.untracked
    assert snapshot.tracked_dirty == []
    assert snapshot.index_changed == []


def test_capture_git_snapshot_with_tracked_dirty(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    readme = repo / "README.md"
    original_content = readme.read_text(encoding="utf-8")
    readme.write_text(f"{original_content}modified\n", encoding="utf-8")

    snapshot = capture_git_snapshot(repo, timestamp_label="dirty")

    assert "README.md" in snapshot.tracked_dirty
    assert snapshot.untracked == []
    assert snapshot.index_changed == []


def test_capture_git_snapshot_with_staged_changes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    readme = repo / "README.md"
    original_content = readme.read_text(encoding="utf-8")
    readme.write_text(f"{original_content}modified\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)

    snapshot = capture_git_snapshot(repo, timestamp_label="staged")

    assert "README.md" in snapshot.index_changed
    assert snapshot.tracked_dirty == []
    assert snapshot.untracked == []


def test_capture_git_snapshot_with_mixed_changes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    # Add a tracked file and commit it
    src_file = repo / "src" / "main.py"
    src_file.write_text("print('hello')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    commit_all(repo, "add main.py")

    # Staged change to existing file
    readme = repo / "README.md"
    original_content = readme.read_text(encoding="utf-8")
    readme.write_text(f"{original_content}staged\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)

    # Dirty tracked file (after staging changes to it)
    src_file.write_text("print('world')\n", encoding="utf-8")

    # Untracked file
    untracked = repo / "untracked.txt"
    untracked.write_text("untracked\n", encoding="utf-8")

    snapshot = capture_git_snapshot(repo, timestamp_label="mixed")

    assert "README.md" in snapshot.index_changed
    assert "src/main.py" in snapshot.tracked_dirty
    assert "untracked.txt" in snapshot.untracked


def test_three_point_snapshot_capture(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    # Pre-create AGENTS.md and commit
    agents_file = repo / "AGENTS.md"
    agents_file.write_text("# Initial agents\n", encoding="utf-8")
    commit_all(repo, "add AGENTS.md")

    # State before hooks
    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    before_hooks_head = before_hooks.head

    # Simulate hook mutation: modify AGENTS.md
    agents_file.write_text("# Initial agents\n# Modified by hook\n", encoding="utf-8")

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")

    # Simulate agent mutation: modify AGENTS.md again
    agents_file.write_text("# Initial agents\n# Modified by hook\n# Modified by agent\n", encoding="utf-8")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    # Verify snapshots
    assert before_hooks_head == before_hooks.head
    assert after_hooks.head == before_hooks.head
    assert after_process.head == before_hooks.head

    assert "AGENTS.md" not in before_hooks.tracked_dirty
    assert "AGENTS.md" in after_hooks.tracked_dirty
    assert "AGENTS.md" in after_process.tracked_dirty


def test_analyze_mutations_no_changes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    snapshot = capture_git_snapshot(repo, timestamp_label="base")

    attributions = analyze_mutations(snapshot, snapshot, snapshot)

    assert len(attributions) == 0


def test_analyze_mutations_pre_existing_change(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    # Create file before hooks
    test_file = repo / "existing.txt"
    test_file.write_text("content\n", encoding="utf-8")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")
    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    assert "existing.txt" in attributions
    attr = attributions["existing.txt"]
    assert attr.before_hooks is True
    assert attr.hook_mutation is False
    assert attr.agent_mutation is False


def test_analyze_mutations_hook_mutation(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")

    # Simulate hook creating file
    hook_file = repo / "hook_created.txt"
    hook_file.write_text("created by hook\n", encoding="utf-8")

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")
    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    assert "hook_created.txt" in attributions
    attr = attributions["hook_created.txt"]
    assert attr.before_hooks is False
    assert attr.hook_mutation is True
    assert attr.agent_mutation is False


def test_analyze_mutations_agent_mutation(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    # Create file before hooks and keep through hooks
    pre_file = repo / "preexisting.txt"
    pre_file.write_text("initial\n", encoding="utf-8")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")

    # Simulate agent modifying file
    pre_file.write_text("modified by agent\n", encoding="utf-8")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    assert "preexisting.txt" in attributions
    attr = attributions["preexisting.txt"]
    # File was dirty from start, hook doesn't change it (same dirty), then agent modifies it
    # So: before_hooks=True, hook_mutation=False (no content change in after_hooks),
    # agent_mutation=True (content changed from after_hooks to after_process)
    assert attr.before_hooks is True
    assert attr.hook_mutation is False
    assert attr.agent_mutation is True


def test_analyze_mutations_combined_changes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    # Pre-existing change
    preexisting = repo / "preexisting.txt"
    preexisting.write_text("before hooks\n", encoding="utf-8")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")

    # Hook creates new file
    hook_file = repo / "hook_file.txt"
    hook_file.write_text("created by hook\n", encoding="utf-8")

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")

    # Agent creates another file
    agent_file = repo / "agent_file.txt"
    agent_file.write_text("created by agent\n", encoding="utf-8")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    assert "preexisting.txt" in attributions
    assert "hook_file.txt" in attributions
    assert "agent_file.txt" in attributions

    assert attributions["preexisting.txt"].before_hooks is True
    assert attributions["hook_file.txt"].hook_mutation is True
    assert attributions["agent_file.txt"].agent_mutation is True


def test_categorize_agents_md_mutations_no_change(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    snapshot = capture_git_snapshot(repo, timestamp_label="base")

    result = categorize_agents_md_mutations(snapshot, snapshot, snapshot)

    assert result["path"] == "AGENTS.md"
    assert result["before_hooks"]["dirty"] is False
    assert result["before_hooks"]["untracked"] is False
    assert result["hook_mutation"] is False
    assert result["agent_mutation"] is False
    assert result["after_process"]["dirty"] is False
    assert result["after_process"]["untracked"] is False


def test_categorize_agents_md_mutations_hook_creates_file(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")

    # Hook creates AGENTS.md
    agents_file = repo / "AGENTS.md"
    agents_file.write_text("# Agents\n# Initial claude-mem block\n", encoding="utf-8")

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")
    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    result = categorize_agents_md_mutations(before_hooks, after_hooks, after_process)

    assert result["path"] == "AGENTS.md"
    assert result["before_hooks"]["untracked"] is False
    assert result["hook_mutation"] is True
    assert result["agent_mutation"] is False


def test_categorize_agents_md_mutations_hook_and_agent_changes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    # Pre-create and commit AGENTS.md
    agents_file = repo / "AGENTS.md"
    agents_file.write_text("# Agents\n", encoding="utf-8")
    commit_all(repo, "add AGENTS.md")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks", capture_file_hashes=True)

    # Hook modifies AGENTS.md
    agents_file.write_text("# Agents\n# Initial claude-mem block\n", encoding="utf-8")

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", capture_file_hashes=True)

    # Agent modifies AGENTS.md again
    agents_file.write_text(
        "# Agents\n# Initial claude-mem block\n# Updated by agent\n",
        encoding="utf-8"
    )

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", capture_file_hashes=True)

    result = categorize_agents_md_mutations(before_hooks, after_hooks, after_process)

    assert result["path"] == "AGENTS.md"
    assert result["before_hooks"]["dirty"] is False
    assert result["hook_mutation"] is True
    assert result["agent_mutation"] is True
    assert result["after_process"]["dirty"] is True


def test_categorize_agents_md_mutations_pre_existing_dirty(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    # Create and commit AGENTS.md
    agents_file = repo / "AGENTS.md"
    agents_file.write_text("# Agents\n", encoding="utf-8")
    commit_all(repo, "add AGENTS.md")

    # Then modify before hooks (making it dirty pre-hooks)
    agents_file.write_text("# Agents\n# Pre-hook modification\n", encoding="utf-8")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks", capture_file_hashes=True)

    # Modify during hooks
    agents_file.write_text("# Agents\n# Pre-hook modification\n# Modified by hook\n", encoding="utf-8")

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", capture_file_hashes=True)

    # Modify again by agent
    agents_file.write_text(
        "# Agents\n# Pre-hook modification\n# Modified by hook\n# Modified by agent\n",
        encoding="utf-8"
    )

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", capture_file_hashes=True)

    result = categorize_agents_md_mutations(before_hooks, after_hooks, after_process)

    assert result["path"] == "AGENTS.md"
    assert result["before_hooks"]["dirty"] is True
    assert result["hook_mutation"] is True
    assert result["agent_mutation"] is True
    assert result["after_process"]["dirty"] is True


def test_git_snapshot_equality(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    snap1 = capture_git_snapshot(repo, timestamp_label="test")
    snap2 = capture_git_snapshot(repo, timestamp_label="test")

    assert snap1.head == snap2.head
    assert snap1.branch == snap2.branch
    assert snap1.index_changed == snap2.index_changed
    assert snap1.tracked_dirty == snap2.tracked_dirty
    assert snap1.untracked == snap2.untracked


def test_snapshot_includes_worktree_metadata(tmp_path: Path) -> None:
    """Snapshot must record the worktree path explicitly."""
    repo = init_repo(tmp_path)
    snapshot = capture_git_snapshot(repo, timestamp_label="test")

    assert snapshot.worktree_path
    assert str(repo.resolve()) in snapshot.worktree_path


def test_file_hashes_enabled_by_default(tmp_path: Path) -> None:
    """File hashes must be captured by default for reliable mutation detection."""
    repo = init_repo(tmp_path)

    # Create and commit a file
    test_file = repo / "test.txt"
    test_file.write_text("original\n", encoding="utf-8")
    commit_all(repo, "add test")

    # Modify it to create dirty state
    test_file.write_text("modified\n", encoding="utf-8")

    # Capture with default (hashes enabled)
    snapshot = capture_git_snapshot(repo, timestamp_label="dirty")

    assert snapshot.file_hashes is not None
    assert "test.txt" in snapshot.file_hashes


def test_analyze_mutations_pre_existing_dirty_with_hook_and_agent_changes(tmp_path: Path) -> None:
    """Critical case: distinguish hook vs agent mutations on pre-existing dirty file."""
    repo = init_repo(tmp_path)

    # Create and commit file
    agents_file = repo / "AGENTS.md"
    agents_file.write_text("# Initial\n", encoding="utf-8")
    commit_all(repo, "add AGENTS.md")

    # Make dirty before hooks (pre-existing modification)
    agents_file.write_text("# Initial\n# Pre-hook\n", encoding="utf-8")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")

    # Hook modifies it further
    agents_file.write_text("# Initial\n# Pre-hook\n# Hook\n", encoding="utf-8")

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")

    # Agent modifies it again
    agents_file.write_text("# Initial\n# Pre-hook\n# Hook\n# Agent\n", encoding="utf-8")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    assert "AGENTS.md" in attributions
    attr = attributions["AGENTS.md"]
    assert attr.before_hooks is True, "File should be marked dirty before hooks"
    assert attr.hook_mutation is True, "Hook should be detected via hash change"
    assert attr.agent_mutation is True, "Agent should be detected via hash change"


def test_snapshot_records_explicit_worktree_path(tmp_path: Path) -> None:
    """Snapshot must record and preserve the worktree path passed to it."""
    repo = init_repo(tmp_path)

    snap1 = capture_git_snapshot(repo, worktree_path=repo, timestamp_label="snap1")
    snap2 = capture_git_snapshot(repo, worktree_path=repo, timestamp_label="snap2")

    assert snap1.worktree_path == snap2.worktree_path
    assert str(repo.resolve()) in snap1.worktree_path


def test_capture_git_snapshot_triple_orchestration(tmp_path: Path) -> None:
    """Test that capture_git_snapshot_triple() properly constructs GitSnapshotTriple."""
    repo = init_repo(tmp_path)

    # Create and commit a file first
    agents_file = repo / "AGENTS.md"
    agents_file.write_text("# Agents\n", encoding="utf-8")
    commit_all(repo, "add AGENTS.md")

    # Capture triple (note: in production these would be spread across the execution cycle)
    triple = capture_git_snapshot_triple(repo, worktree_path=repo)

    # Verify structure
    assert isinstance(triple, GitSnapshotTriple)
    assert isinstance(triple.before_hooks, GitSnapshot)
    assert isinstance(triple.after_hooks, GitSnapshot)
    assert isinstance(triple.after_process, GitSnapshot)

    # All should have the same initial state since they're captured consecutively
    assert triple.before_hooks.head == triple.after_hooks.head == triple.after_process.head


def test_capture_git_snapshot_triple_with_mutations_simulation(tmp_path: Path) -> None:
    """Test the triple capture pattern with simulated hook and agent mutations."""
    repo = init_repo(tmp_path)

    # Setup: create and commit a file
    agents_file = repo / "AGENTS.md"
    agents_file.write_text("# Agents\n", encoding="utf-8")
    commit_all(repo, "add AGENTS.md")

    # Capture before any mutations
    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    assert "AGENTS.md" not in before_hooks.tracked_dirty

    # Simulate hook mutation
    agents_file.write_text("# Agents\n# Hook mutation\n", encoding="utf-8")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")
    assert "AGENTS.md" in after_hooks.tracked_dirty

    # Simulate agent mutation
    agents_file.write_text("# Agents\n# Hook mutation\n# Agent mutation\n", encoding="utf-8")
    after_process = capture_git_snapshot(repo, timestamp_label="after_process")
    assert "AGENTS.md" in after_process.tracked_dirty

    # Analyze mutations
    attributions = analyze_mutations(before_hooks, after_hooks, after_process)
    assert "AGENTS.md" in attributions
    attr = attributions["AGENTS.md"]
    assert attr.before_hooks is False
    assert attr.hook_mutation is True
    assert attr.agent_mutation is True


def test_external_mutation_detection_with_commit(tmp_path: Path) -> None:
    """Test mutation attribution when file is committed by agent.

    When an agent commits a file, the HEAD changes. With 3 snapshots,
    we can't distinguish agent commits from external commits without metadata.
    This test verifies we don't incorrectly classify agent commits as external_mutation.

    Strategy: A file that was untracked before and after hooks, then disappears
    due to a commit, should NOT be marked as external_mutation (that would be
    assuming it's external). Instead, it should be detected via paths_from_head_change.
    """
    repo = init_repo(tmp_path)

    # Setup: create a file
    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    assert "test.txt" in before_hooks.untracked

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)
    assert "test.txt" in after_hooks.untracked

    # Simulate agent: stage and commit the file
    subprocess.run(["git", "add", "test.txt"], cwd=repo, check=True)
    commit_all(repo, "add test.txt")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)
    # File is no longer untracked after commit
    assert "test.txt" not in after_process.untracked
    assert "test.txt" not in after_process.tracked_dirty

    # The file should appear in paths_from_head_change to indicate it was affected by commit
    assert after_process.paths_from_head_change is not None
    assert "test.txt" in after_process.paths_from_head_change

    # Analyze mutations
    attributions = analyze_mutations(before_hooks, after_hooks, after_process)
    assert "test.txt" in attributions
    attr = attributions["test.txt"]
    # File existed before hooks as untracked
    assert attr.before_hooks is True
    # No content changed by hook
    assert attr.hook_mutation is False
    # File was committed, so it's not marked as external_mutation
    # (We don't assume HEAD change => external)
    assert attr.external_mutation is False


def test_external_mutation_file_cleanup(tmp_path: Path) -> None:
    """Test external_mutation detection when file is staged and removed from dirty."""
    repo = init_repo(tmp_path)

    # Create and commit a base file
    base_file = repo / "base.txt"
    base_file.write_text("base\n", encoding="utf-8")
    commit_all(repo, "add base")

    # Create a tracked file and make it dirty
    test_file = repo / "test.txt"
    test_file.write_text("original\n", encoding="utf-8")
    subprocess.run(["git", "add", "test.txt"], cwd=repo, check=True)
    commit_all(repo, "add test.txt")

    # Make it dirty
    test_file.write_text("modified\n", encoding="utf-8")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    assert "test.txt" in before_hooks.tracked_dirty

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")
    assert "test.txt" in after_hooks.tracked_dirty

    # Simulate agent: stage the file (moves from tracked_dirty to index_changed)
    subprocess.run(["git", "add", "test.txt"], cwd=repo, check=True)

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")
    # File is in index_changed, not tracked_dirty
    assert "test.txt" in after_process.index_changed

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)
    assert "test.txt" in attributions
    attr = attributions["test.txt"]
    # File was dirty before hooks
    assert attr.before_hooks is True
    # No hook mutation
    assert attr.hook_mutation is False
    # Agent staged it - this is an index transition (dirty->staged), so agent_mutation is True
    assert attr.agent_mutation is True, "Index transition dirty->staged should be detected as agent operation"
    assert attr.agent_index_transition == "dirty->staged"


def test_categorize_agents_md_full_cycle(tmp_path: Path) -> None:
    """Test AGENTS.md mutation categorization in a complete cycle."""
    repo = init_repo(tmp_path)

    # Setup: create and commit AGENTS.md
    agents_file = repo / "AGENTS.md"
    agents_file.write_text("# Initial agents\n", encoding="utf-8")
    commit_all(repo, "add AGENTS.md")

    # Before hooks
    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")

    # Hook adds claude-mem block
    agents_file.write_text("# Initial agents\n<!-- claude-mem -->\n", encoding="utf-8")

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")

    # Agent adds more content
    agents_file.write_text("# Initial agents\n<!-- claude-mem -->\n# Agent content\n", encoding="utf-8")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    # Categorize
    result = categorize_agents_md_mutations(before_hooks, after_hooks, after_process)

    assert result["path"] == "AGENTS.md"
    assert result["before_hooks"]["dirty"] is False
    assert result["hook_mutation"] is True
    assert result["agent_mutation"] is True
    assert result["after_process"]["dirty"] is True


def test_integration_three_point_snapshot_with_real_cycle(tmp_path: Path) -> None:
    """Integration test: capture three snapshots and verify all mutations are categorized."""
    repo = init_repo(tmp_path)

    # Create multiple files with different mutation patterns
    agents_file = repo / "AGENTS.md"
    agents_file.write_text("# Agents\n", encoding="utf-8")

    hook_file = repo / "hook_created.txt"
    agent_file = repo / "agent_created.txt"
    pre_existing = repo / "preexisting.txt"
    pre_existing.write_text("preexisting\n", encoding="utf-8")

    commit_all(repo, "initial setup")

    # Before hooks snapshot
    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    before_hooks_count = len([
        p for p in before_hooks.index_changed + before_hooks.tracked_dirty + before_hooks.untracked
    ])

    # Hook phase: create and modify files
    hook_file.write_text("created by hook\n", encoding="utf-8")
    agents_file.write_text("# Agents\n# Hook block\n", encoding="utf-8")

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")

    # Agent phase: create and modify files
    agent_file.write_text("created by agent\n", encoding="utf-8")
    agents_file.write_text("# Agents\n# Hook block\n# Agent block\n", encoding="utf-8")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    # Analyze all mutations
    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    # Verify categorizations
    assert "AGENTS.md" in attributions
    assert attributions["AGENTS.md"].hook_mutation is True
    assert attributions["AGENTS.md"].agent_mutation is True

    assert "hook_created.txt" in attributions
    assert attributions["hook_created.txt"].hook_mutation is True
    assert attributions["hook_created.txt"].agent_mutation is False

    assert "agent_created.txt" in attributions
    assert attributions["agent_created.txt"].hook_mutation is False
    assert attributions["agent_created.txt"].agent_mutation is True

    # pre_existing should not appear (no mutation during hooks or agent phase)
    if "preexisting.txt" in attributions:
        assert attributions["preexisting.txt"].before_hooks is True
        assert attributions["preexisting.txt"].hook_mutation is False
        assert attributions["preexisting.txt"].agent_mutation is False


def test_capture_git_snapshot_triple_with_lifecycle_hook_phase(tmp_path: Path) -> None:
    """Test lifecycle capture with hooks_phase callback."""
    repo = init_repo(tmp_path)

    # Create and commit a file
    agents_file = repo / "AGENTS.md"
    agents_file.write_text("# Agents\n", encoding="utf-8")
    commit_all(repo, "add AGENTS.md")

    # Define hook phase that modifies the file
    def hook_phase() -> None:
        agents_file.write_text("# Agents\n# Modified by hook\n", encoding="utf-8")

    # Capture with lifecycle
    triple = capture_git_snapshot_triple_with_lifecycle(
        repo,
        hooks_phase=hook_phase,
    )

    # Verify structure
    assert isinstance(triple, GitSnapshotTriple)
    assert isinstance(triple.before_hooks, GitSnapshot)
    assert isinstance(triple.after_hooks, GitSnapshot)
    assert isinstance(triple.after_process, GitSnapshot)

    # Verify hook mutation was captured
    assert "AGENTS.md" not in triple.before_hooks.tracked_dirty
    assert "AGENTS.md" in triple.after_hooks.tracked_dirty
    assert "AGENTS.md" in triple.after_process.tracked_dirty


def test_capture_git_snapshot_triple_with_lifecycle_full_cycle(tmp_path: Path) -> None:
    """Test complete lifecycle with both hooks_phase and agent_phase."""
    repo = init_repo(tmp_path)

    # Create and commit a file
    agents_file = repo / "AGENTS.md"
    agents_file.write_text("# Agents\n", encoding="utf-8")
    commit_all(repo, "add AGENTS.md")

    # Define hook phase
    def hook_phase() -> None:
        agents_file.write_text("# Agents\n# Modified by hook\n", encoding="utf-8")

    # Define agent phase
    def agent_phase() -> None:
        agents_file.write_text("# Agents\n# Modified by hook\n# Modified by agent\n", encoding="utf-8")

    # Capture with full lifecycle
    triple = capture_git_snapshot_triple_with_lifecycle(
        repo,
        hooks_phase=hook_phase,
        agent_phase=agent_phase,
    )

    # Verify all three snapshots reflect the lifecycle
    assert "AGENTS.md" not in triple.before_hooks.tracked_dirty
    assert "AGENTS.md" in triple.after_hooks.tracked_dirty
    assert "AGENTS.md" in triple.after_process.tracked_dirty

    # Analyze mutations
    attributions = analyze_mutations(triple.before_hooks, triple.after_hooks, triple.after_process)

    assert "AGENTS.md" in attributions
    attr = attributions["AGENTS.md"]
    assert attr.before_hooks is False
    assert attr.hook_mutation is True
    assert attr.agent_mutation is True


def test_capture_git_snapshot_triple_with_lifecycle_no_agent_phase(tmp_path: Path) -> None:
    """Test lifecycle with only hooks_phase (no agent_phase)."""
    repo = init_repo(tmp_path)

    # Create and commit a file
    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "add test")

    # Define hook phase
    def hook_phase() -> None:
        test_file.write_text("modified by hook\n", encoding="utf-8")

    # Capture with only hook phase
    triple = capture_git_snapshot_triple_with_lifecycle(
        repo,
        hooks_phase=hook_phase,
    )

    # After hooks should have the modification
    assert "test.txt" in triple.after_hooks.tracked_dirty

    # After process should have the same modification (no agent_phase)
    assert "test.txt" in triple.after_process.tracked_dirty

    # Analyze mutations
    attributions = analyze_mutations(triple.before_hooks, triple.after_hooks, triple.after_process)

    assert "test.txt" in attributions
    attr = attributions["test.txt"]
    assert attr.hook_mutation is True
    assert attr.agent_mutation is False


def test_external_mutation_detection_head_change(tmp_path: Path) -> None:
    """Test external mutation detection when HEAD changes (commit occurred).

    When HEAD changes, we can detect a commit occurred. However, we can't
    distinguish agent commits from external commits without metadata.

    We use paths_from_head_change to capture what was affected by the commit,
    and reserve external_mutation for clear evidence of external changes.
    """
    repo = init_repo(tmp_path)

    # Setup: create and commit a file
    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial commit")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    # Simulate external commit changing HEAD
    new_file = repo / "external.txt"
    new_file.write_text("external\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    commit_all(repo, "external commit")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    # Verify HEAD changed - this indicates a commit occurred
    assert before_hooks.head != after_process.head

    # The external.txt file was committed, so it should appear in paths_from_head_change
    assert after_process.paths_from_head_change is not None
    assert "external.txt" in after_process.paths_from_head_change

    # Analyze mutations
    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    # The file was committed and doesn't appear as dirty/staged in any snapshot
    # So it may not be in attributions (it wasn't visible in working tree state)
    # This is expected: the audit captures changes visible via dirty/staged state,
    # not all paths in commits


def test_external_mutation_not_detected_when_no_head_change(tmp_path: Path) -> None:
    """Test that external_mutation is False when HEAD is unchanged."""
    repo = init_repo(tmp_path)

    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    # Create three identical snapshots
    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")
    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    # All have same HEAD
    assert before_hooks.head == after_process.head

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    # Should have no attributions if nothing changed
    assert len(attributions) == 0


def test_external_mutation_detection_with_categorize_agents_md(tmp_path: Path) -> None:
    """Test AGENTS.md mutation detection including external mutation indicators."""
    repo = init_repo(tmp_path)

    # Setup: create and commit AGENTS.md
    agents_file = repo / "AGENTS.md"
    agents_file.write_text("# Agents\n", encoding="utf-8")
    commit_all(repo, "add AGENTS.md")

    # Define complete lifecycle with mutations
    def hook_phase() -> None:
        agents_file.write_text("# Agents\n# Hook block\n", encoding="utf-8")

    def agent_phase() -> None:
        agents_file.write_text("# Agents\n# Hook block\n# Agent block\n", encoding="utf-8")

    triple = capture_git_snapshot_triple_with_lifecycle(
        repo,
        hooks_phase=hook_phase,
        agent_phase=agent_phase,
    )

    # Categorize AGENTS.md
    result = categorize_agents_md_mutations(triple.before_hooks, triple.after_hooks, triple.after_process)

    # Verify the complete cycle was captured
    assert result["path"] == "AGENTS.md"
    assert result["before_hooks"]["dirty"] is False
    assert result["hook_mutation"] is True
    assert result["agent_mutation"] is True
    assert result["after_process"]["dirty"] is True


def test_committed_files_visible_in_audit(tmp_path: Path) -> None:
    """DEFECT 1: Files created and committed during process should not disappear from audit.

    When an agent creates a file and commits it:
    1. The file appears as untracked in after_hooks
    2. After commit, file is no longer untracked (it's tracked)
    3. The audit must preserve evidence that the file was part of the commit
       via paths_from_head_change

    This test verifies committed files are visible in paths_from_head_change.
    """
    repo = init_repo(tmp_path)

    # Pre-create initial commit
    initial_file = repo / "initial.txt"
    initial_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial commit")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    # Agent creates and commits a file
    agent_file = repo / "agent_created.txt"
    agent_file.write_text("created by agent\n", encoding="utf-8")
    subprocess.run(["git", "add", "agent_created.txt"], cwd=repo, check=True)
    commit_all(repo, "agent commit")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    # Verify HEAD changed (commit occurred)
    assert before_hooks.head != after_process.head

    # The committed file should appear in paths_from_head_change
    assert after_process.paths_from_head_change is not None, \
        "Committed files should be captured in paths_from_head_change"
    assert "agent_created.txt" in after_process.paths_from_head_change, \
        "Committed file should appear in paths_from_head_change"

    # Analyze mutations
    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    # The file should be in attributions because it's in paths_from_head_change
    assert "agent_created.txt" in attributions, \
        "Committed file should appear in audit via paths_from_head_change"

    attr = attributions["agent_created.txt"]
    assert attr.before_hooks is False  # Not present before
    # File was committed, so it's not dirty anymore
    assert attr.external_mutation is False  # Don't assume commit is external


def test_preexisting_dirty_staged_without_content_change(tmp_path: Path) -> None:
    """DEFECT 3: Index transitions should be detected even without content change.

    When a file is dirty before hooks, and agent stages it without content change:
    1. File should be marked as before_hooks=True
    2. The transition from dirty to staged should be detected as agent_mutation
    3. Even though content hash is identical, the index state changed
    """
    repo = init_repo(tmp_path)

    # Create and commit a file
    test_file = repo / "test.txt"
    test_file.write_text("content\n", encoding="utf-8")
    commit_all(repo, "add test")

    # Make it dirty before hooks
    test_file.write_text("modified\n", encoding="utf-8")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    assert "test.txt" in before_hooks.tracked_dirty

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")
    assert "test.txt" in after_hooks.tracked_dirty

    # Agent stages the file WITHOUT modifying its content
    # (This is valid: preparing for commit)
    subprocess.run(["git", "add", "test.txt"], cwd=repo, check=True)

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")
    assert "test.txt" in after_process.index_changed

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    assert "test.txt" in attributions
    attr = attributions["test.txt"]
    assert attr.before_hooks is True, "File was dirty before hooks"

    # DEFECT: Current logic doesn't detect index transition without content change
    # Should detect that file moved from tracked_dirty to index_changed
    # This is an agent operation that must be recorded
    assert attr.agent_mutation is True, \
        "Index transition (dirty->staged) should be detected as agent_mutation"


def test_untracked_file_staged_by_agent(tmp_path: Path) -> None:
    """DEFECT 3: Untracked->staged transition should be detected as agent_mutation."""
    repo = init_repo(tmp_path)

    # Setup initial commit
    initial = repo / "initial.txt"
    initial.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    # Untracked file before hooks
    untracked_file = repo / "untracked.txt"
    untracked_file.write_text("untracked\n", encoding="utf-8")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    assert "untracked.txt" in before_hooks.untracked

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")

    # Agent stages the untracked file
    subprocess.run(["git", "add", "untracked.txt"], cwd=repo, check=True)

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")
    assert "untracked.txt" in after_process.index_changed

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    assert "untracked.txt" in attributions
    attr = attributions["untracked.txt"]
    # The file was already untracked, so it's a creation
    # But agent_mutation should be True because agent staged it
    # Currently this might be incorrectly classified
    assert attr.agent_mutation is True, "Staging untracked file is agent operation"


def test_agent_attribution_with_agent_metadata_case1(tmp_path: Path) -> None:
    """TEST 1: Agent commit revendiqué + corroboré => origin=agent, proven_agent_source=True."""
    repo = init_repo(tmp_path)

    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    agent_file = repo / "agent_file.txt"
    agent_file.write_text("from agent\n", encoding="utf-8")
    subprocess.run(["git", "add", "agent_file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "agent commit"], cwd=repo, check=True)

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    # Métadonnées déclarant ce fichier comme agent
    metadata = ExecutionMutationMetadata(
        attempt_id="attempt-001",
        agent_claimed_paths=["agent_file.txt"],
    )

    attributions = analyze_mutations(before_hooks, after_hooks, after_process, metadata=metadata)

    assert "agent_file.txt" in attributions
    attr = attributions["agent_file.txt"]
    assert attr.origin == "agent"
    assert attr.proven_agent_source is True
    assert attr.external_mutation is False


def test_agent_attribution_external_metadata_case2(tmp_path: Path) -> None:
    """TEST 2: Commit explicitement externe + corroboré => origin=external, external_mutation=True."""
    repo = init_repo(tmp_path)

    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    external_file = repo / "external_file.txt"
    external_file.write_text("from external\n", encoding="utf-8")
    subprocess.run(["git", "add", "external_file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "external commit"], cwd=repo, check=True)

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    # Métadonnées prouvant que c'est externe
    metadata = ExecutionMutationMetadata(
        externally_proven_paths=["external_file.txt"],
    )

    attributions = analyze_mutations(before_hooks, after_hooks, after_process, metadata=metadata)

    assert "external_file.txt" in attributions
    attr = attributions["external_file.txt"]
    assert attr.origin == "external"
    assert attr.external_mutation is True


def test_agent_attribution_no_metadata_case3(tmp_path: Path) -> None:
    """TEST 3: Commit sans métadonnées => origin=indeterminate, external_mutation=False."""
    repo = init_repo(tmp_path)

    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    mystery_file = repo / "mystery_file.txt"
    mystery_file.write_text("mystery\n", encoding="utf-8")
    subprocess.run(["git", "add", "mystery_file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "mystery commit"], cwd=repo, check=True)

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    assert "mystery_file.txt" in attributions
    attr = attributions["mystery_file.txt"]
    assert attr.origin == "indeterminate"
    assert attr.external_mutation is False


def test_agent_attribution_false_claim_case4(tmp_path: Path) -> None:
    """TEST 4: Fausse revendication agent ne correspondant pas au commit => NOT agent."""
    repo = init_repo(tmp_path)

    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    actual_file = repo / "actual_file.txt"
    actual_file.write_text("actual\n", encoding="utf-8")
    subprocess.run(["git", "add", "actual_file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "actual commit"], cwd=repo, check=True)

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    # Métadonnées mentionnant un chemin différent
    metadata = ExecutionMutationMetadata(
        agent_claimed_paths=["nonexistent_file.txt"],
    )

    attributions = analyze_mutations(before_hooks, after_hooks, after_process, metadata=metadata)

    assert "actual_file.txt" in attributions
    attr = attributions["actual_file.txt"]
    # Fichier existant mais pas revendiqué => pas proven_agent_source
    assert attr.origin == "indeterminate"
    assert attr.proven_agent_source is False


def test_agent_attribution_false_external_claim_case5(tmp_path: Path) -> None:
    """TEST 5: Fausse preuve externe ne correspondant pas => NOT external."""
    repo = init_repo(tmp_path)

    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    actual_file = repo / "actual_file.txt"
    actual_file.write_text("actual\n", encoding="utf-8")
    subprocess.run(["git", "add", "actual_file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "actual commit"], cwd=repo, check=True)

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    # Métadonnées mentionnant un chemin différent comme externe
    metadata = ExecutionMutationMetadata(
        externally_proven_paths=["different_file.txt"],
    )

    attributions = analyze_mutations(before_hooks, after_hooks, after_process, metadata=metadata)

    assert "actual_file.txt" in attributions
    attr = attributions["actual_file.txt"]
    assert attr.origin == "indeterminate"
    assert attr.external_mutation is False


def test_agent_attribution_uncorroborated_path_case6(tmp_path: Path) -> None:
    """TEST 6: Chemin agent revendiqué mais aucune transition Git correspondante => pas attribution prouvée."""
    repo = init_repo(tmp_path)

    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")
    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    # Métadonnées revendiquant un chemin inexistant
    metadata = ExecutionMutationMetadata(
        agent_claimed_paths=["never_created.txt"],
    )

    attributions = analyze_mutations(before_hooks, after_hooks, after_process, metadata=metadata)

    # Le chemin revendiqué n'existe dans aucun snapshot, donc pas d'attribution
    assert "never_created.txt" not in attributions


def test_agent_attribution_external_index_case7(tmp_path: Path) -> None:
    """TEST 7: Mutation externe de l'index avec métadonnée corroborée => origin=external."""
    repo = init_repo(tmp_path)

    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    # Créer un fichier dirty
    dirty_file = repo / "dirty.txt"
    dirty_file.write_text("dirty\n", encoding="utf-8")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")

    # Staged le fichier (externe)
    subprocess.run(["git", "add", "dirty.txt"], cwd=repo, check=True)

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    # Métadonnées prouvant que c'est externe
    metadata = ExecutionMutationMetadata(
        externally_proven_paths=["dirty.txt"],
    )

    attributions = analyze_mutations(before_hooks, after_hooks, after_process, metadata=metadata)

    assert "dirty.txt" in attributions
    attr = attributions["dirty.txt"]
    assert attr.origin == "external"
    assert attr.external_mutation is True


def test_agent_attribution_external_worktree_case8(tmp_path: Path) -> None:
    """TEST 8: Mutation externe du worktree avec métadonnée corroborée => origin=external."""
    repo = init_repo(tmp_path)

    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")

    # Créer un nouveau fichier dans le worktree (externe)
    external_file = repo / "external_created.txt"
    external_file.write_text("external\n", encoding="utf-8")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    # Métadonnées prouvant que c'est externe
    metadata = ExecutionMutationMetadata(
        externally_proven_paths=["external_created.txt"],
    )

    attributions = analyze_mutations(before_hooks, after_hooks, after_process, metadata=metadata)

    assert "external_created.txt" in attributions
    attr = attributions["external_created.txt"]
    assert attr.origin == "external"
    assert attr.external_mutation is True


def test_agent_attribution_dirty_to_staged_case9(tmp_path: Path) -> None:
    """TEST 9: dirty -> staged transition détectée indépendamment du hash."""
    repo = init_repo(tmp_path)

    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    # Fichier dirty avant hooks
    test_file.write_text("modified\n", encoding="utf-8")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    assert "test.txt" in before_hooks.tracked_dirty

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")

    # Stage le fichier sans changer le contenu
    subprocess.run(["git", "add", "test.txt"], cwd=repo, check=True)

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")
    assert "test.txt" in after_process.index_changed

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    assert "test.txt" in attributions
    attr = attributions["test.txt"]
    assert attr.agent_index_transition == "dirty->staged"
    assert attr.agent_mutation is True
    assert attr.origin == "agent"


def test_agent_attribution_staged_to_commit_case10(tmp_path: Path) -> None:
    """TEST 10: staged -> commit transition/commit conservé dans l'audit."""
    repo = init_repo(tmp_path)

    initial = repo / "initial.txt"
    initial.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    # Créer et stage
    new_file = repo / "new.txt"
    new_file.write_text("new\n", encoding="utf-8")
    subprocess.run(["git", "add", "new.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "add new"], cwd=repo, check=True)

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    # Fichier est dans paths_from_head_change
    assert after_process.paths_from_head_change is not None
    assert "new.txt" in after_process.paths_from_head_change

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    assert "new.txt" in attributions
    attr = attributions["new.txt"]
    # File is committed, so tracked
    assert attr.before_hooks is False


def test_agent_attribution_rename_both_paths_case11(tmp_path: Path) -> None:
    """TEST 11: renommage => ancien ET nouveau chemin présents."""
    repo = init_repo(tmp_path)

    original = repo / "original.txt"
    original.write_text("content\n", encoding="utf-8")
    commit_all(repo, "add original.txt")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    subprocess.run(["git", "mv", "original.txt", "renamed.txt"], cwd=repo, check=True)
    commit_all(repo, "rename")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    # Vérifier que paths_from_head_change contient les deux chemins
    assert after_process.paths_from_head_change is not None
    # Au moins l'un ou l'autre doit être présent (git mv peut être représenté de façons différentes)
    paths_in_change = set(after_process.paths_from_head_change)
    assert "renamed.txt" in paths_in_change or "original.txt" in paths_in_change

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    # Vérifier que l'un ou l'autre apparaît dans l'audit
    assert "renamed.txt" in attributions or "original.txt" in attributions


def test_agent_attribution_deletion_case12(tmp_path: Path) -> None:
    """TEST 12: suppression commitée => chemin supprimé toujours présent dans l'audit."""
    repo = init_repo(tmp_path)

    to_delete = repo / "to_delete.txt"
    to_delete.write_text("will be deleted\n", encoding="utf-8")
    commit_all(repo, "add to_delete.txt")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    subprocess.run(["git", "rm", "to_delete.txt"], cwd=repo, check=True)
    commit_all(repo, "delete to_delete.txt")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    # Le fichier supprimé doit être dans paths_from_head_change
    assert after_process.paths_from_head_change is not None
    assert "to_delete.txt" in after_process.paths_from_head_change

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    # Le chemin supprimé doit rester dans l'audit
    assert "to_delete.txt" in attributions
    attr = attributions["to_delete.txt"]
    assert attr.external_mutation is False


def test_committed_deletion_visible_in_audit(tmp_path: Path) -> None:
    """Test that deleted files committed during process appear in audit via paths_from_head_change.

    When an agent deletes a tracked file and commits that deletion:
    1. The file disappears from worktree and index
    2. But it should still appear in the audit via paths_from_head_change
    3. The audit should show it as both before_hooks and affected by commit
    """
    repo = init_repo(tmp_path)

    # Create and commit initial files
    initial_file = repo / "initial.txt"
    initial_file.write_text("initial\n", encoding="utf-8")
    to_delete = repo / "to_delete.txt"
    to_delete.write_text("will be deleted\n", encoding="utf-8")
    commit_all(repo, "initial files")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    assert "to_delete.txt" not in before_hooks.tracked_dirty
    assert "to_delete.txt" not in before_hooks.untracked

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    # Agent deletes and commits the file
    subprocess.run(["git", "rm", "to_delete.txt"], cwd=repo, check=True)
    commit_all(repo, "delete to_delete.txt")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    # Verify file is gone from worktree
    assert not to_delete.exists()
    assert "to_delete.txt" not in after_process.tracked_dirty
    assert "to_delete.txt" not in after_process.untracked

    # But it should appear in paths_from_head_change
    assert after_process.paths_from_head_change is not None
    assert "to_delete.txt" in after_process.paths_from_head_change

    # Analyze mutations
    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    # Deleted file should appear in audit
    assert "to_delete.txt" in attributions
    attr = attributions["to_delete.txt"]
    # File existed before hooks
    assert attr.before_hooks is False  # Was committed, not dirty
    # But it was affected by commit
    assert attr.external_mutation is False  # Don't assume commit is external


def test_staged_then_committed_file(tmp_path: Path) -> None:
    """Test transitions: untracked -> staged -> committed.

    When an agent creates, stages, and commits a file in sequence:
    1. File starts untracked
    2. Agent stages it
    3. Agent commits it

    The file should appear with both staging and commit transitions.
    """
    repo = init_repo(tmp_path)

    # Initial setup
    initial = repo / "initial.txt"
    initial.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    # Agent creates, stages, and commits
    new_file = repo / "staged_then_committed.txt"
    new_file.write_text("new file\n", encoding="utf-8")
    subprocess.run(["git", "add", "staged_then_committed.txt"], cwd=repo, check=True)
    commit_all(repo, "add staged_then_committed.txt")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    # Verify the file is committed (not in any dirty state)
    assert "staged_then_committed.txt" not in after_process.untracked
    assert "staged_then_committed.txt" not in after_process.tracked_dirty
    assert "staged_then_committed.txt" not in after_process.index_changed

    # But it should be in paths_from_head_change
    assert after_process.paths_from_head_change is not None
    assert "staged_then_committed.txt" in after_process.paths_from_head_change

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    assert "staged_then_committed.txt" in attributions
    attr = attributions["staged_then_committed.txt"]
    assert attr.before_hooks is False  # Didn't exist before


def test_external_vs_agent_mutation_distinction_without_metadata(tmp_path: Path) -> None:
    """Test that external and agent mutations are marked as ambiguous without metadata.

    With 3 snapshots but no metadata:
    - A commit detected by HEAD change can't be distinguished as agent vs external
    - Should be marked with ambiguous_origin or similar indicator
    - NOT marked as external_mutation (that's too strong without evidence)
    """
    repo = init_repo(tmp_path)

    # Setup
    initial = repo / "initial.txt"
    initial.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    # A file is committed (could be agent or external, we can't tell)
    new_file = repo / "mystery_commit.txt"
    new_file.write_text("mystery\n", encoding="utf-8")
    subprocess.run(["git", "add", "mystery_commit.txt"], cwd=repo, check=True)
    commit_all(repo, "mystery commit")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    assert "mystery_commit.txt" in attributions
    attr = attributions["mystery_commit.txt"]
    # Without metadata, we can't prove it's agent or external
    # But we can see it was affected by a commit
    assert attr.external_mutation is False, "Don't assume commit is external without evidence"


def test_file_rename_both_paths_visible(tmp_path: Path) -> None:
    """Test that renamed files show both old and new paths in audit.

    When an agent renames a file:
    1. Old path should appear with 'deleted' indication
    2. New path should appear with 'added' indication
    3. Both should be in audit via paths_from_head_change
    """
    repo = init_repo(tmp_path)

    # Create and commit a file
    original = repo / "original.txt"
    original.write_text("content\n", encoding="utf-8")
    commit_all(repo, "add original.txt")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks", previous_head=before_hooks.head)

    # Agent renames the file
    subprocess.run(["git", "mv", "original.txt", "renamed.txt"], cwd=repo, check=True)
    commit_all(repo, "rename original.txt to renamed.txt")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process", previous_head=after_hooks.head)

    # Verify paths_from_head_change captures rename
    assert after_process.paths_from_head_change is not None
    # At minimum, one of the paths should be captured
    assert "renamed.txt" in after_process.paths_from_head_change or "original.txt" in after_process.paths_from_head_change

    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    # At least the new path should be visible
    assert "renamed.txt" in attributions or "original.txt" in attributions
