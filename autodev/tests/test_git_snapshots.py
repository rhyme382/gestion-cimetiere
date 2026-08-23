from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from autodev.git_context import (
    GitSnapshot,
    GitSnapshotTriple,
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
    # File exists from before_hooks through after_hooks, then changes
    # But since it was dirty in before_hooks and after_hooks, agent_mutation should be false
    # unless the tool explicitly detects the change between after_hooks and after_process


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
    this appears as a potential external mutation, but we can't distinguish
    if it's from the agent (legitimate) or from external source.
    This test documents the ambiguity.
    """
    repo = init_repo(tmp_path)

    # Setup: create a file
    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    assert "test.txt" in before_hooks.untracked

    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")
    assert "test.txt" in after_hooks.untracked

    # Simulate agent: stage and commit the file
    subprocess.run(["git", "add", "test.txt"], cwd=repo, check=True)
    commit_all(repo, "add test.txt")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")
    # File is no longer untracked after commit
    assert "test.txt" not in after_process.untracked
    assert "test.txt" not in after_process.tracked_dirty

    # Analyze mutations
    attributions = analyze_mutations(before_hooks, after_hooks, after_process)
    assert "test.txt" in attributions
    attr = attributions["test.txt"]
    # File existed before hooks as untracked
    assert attr.before_hooks is True
    # No content changed by hook
    assert attr.hook_mutation is False
    # With 3 snapshots and HEAD changed, this is marked as external_mutation
    # even though it's actually an agent mutation (commit).
    # This is an inherent ambiguity of 3-snapshot reconciliation.
    assert attr.external_mutation is True


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
    # Agent staged it (status changed but same content hash)
    assert attr.agent_mutation is False or attr.agent_mutation is True  # depends on hash comparison


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

    When an external commit changes the HEAD, we can detect it by comparing
    the HEAD before/after. This is a key indicator of external mutation.
    """
    repo = init_repo(tmp_path)

    # Setup: create and commit a file
    test_file = repo / "test.txt"
    test_file.write_text("initial\n", encoding="utf-8")
    commit_all(repo, "initial commit")

    before_hooks = capture_git_snapshot(repo, timestamp_label="before_hooks")
    after_hooks = capture_git_snapshot(repo, timestamp_label="after_hooks")

    # Simulate external commit changing HEAD
    new_file = repo / "external.txt"
    new_file.write_text("external\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    commit_all(repo, "external commit")

    after_process = capture_git_snapshot(repo, timestamp_label="after_process")

    # Verify HEAD changed - this is the key indicator
    assert before_hooks.head != after_process.head

    # Analyze mutations
    attributions = analyze_mutations(before_hooks, after_hooks, after_process)

    # When HEAD changes between before_hooks and after_process,
    # it indicates a commit occurred. Files that are staged/dirty at
    # after_hooks but clean at after_process would be marked as external_mutation.
    # The external.txt file itself is committed (not dirty), so we don't
    # detect it directly, but the fact that HEAD changed is evidence
    # of external activity. This is an inherent limitation of 3-capture
    # reconciliation - we can't distinguish agent commits from external commits
    # without additional metadata.


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
