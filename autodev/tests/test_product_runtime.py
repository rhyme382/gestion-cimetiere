import json
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from autodev.product_runtime import (
    DurableDecision,
    DurableDecisionStore,
    ProductRuntime,
    ProductRuntimeError,
)
from autodev.product_state import IdempotenceKey


def make_plan_dict(
    plan_id: str = "plan-001",
    plan_hash: str = "abc123",
    integration_branch: str = "main",
    features: list[dict[str, object]] | None = None,
    global_validations: list[str] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "plan_id": plan_id,
        "generated_at": "2026-08-22T10:00:00+00:00",
        "integration_branch": integration_branch,
        "specification_policy": "approved-only",
        "global_validations": global_validations or ["pytest"],
        "features": features
        or [
            {
                "feature_id": "feature-001",
                "title": "Feature 001",
                "specification_path": "specs/feature-001.md",
                "required": True,
                "priority": 1,
                "depends_on": [],
                "validations": ["unit"],
            }
        ],
        "plan_hash": plan_hash,
    }


def persist_runtime_state(runtime: ProductRuntime, state) -> None:
    lock_id = runtime.acquire_product_lock()
    try:
        runtime.state_manager.write_state(state)
    finally:
        runtime.release_lock(lock_id, reason="test-state-update")


def persist_runtime_checkpoint(runtime: ProductRuntime, checkpoint: dict[str, object]) -> None:
    lock_id = runtime.acquire_product_lock()
    try:
        runtime.state_manager.write_checkpoint(dict(checkpoint))
    finally:
        runtime.release_lock(lock_id, reason="test-checkpoint-update")


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        (repo_root / ".autodev").mkdir(parents=True)
        yield repo_root


@pytest.fixture
def runtime(temp_repo):
    return ProductRuntime(temp_repo, "run-001")


class TestDurableDecision:
    def test_creates_decision(self):
        decision = DurableDecision(
            decision_id="dec-001",
            product_key="plan-001",
            run_id="run-001",
            feature_id="feature-001",
            task_id="task-001",
            decision_type="SCOPE_EXTENSION",
            content={"scope": "extended", "reason": "user request"},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        assert decision.decision_id == "dec-001"
        assert decision.status == "pending"

    def test_converts_to_dict(self):
        decision = DurableDecision(
            decision_id="dec-001",
            product_key="plan-001",
            run_id="run-001",
            feature_id="feature-001",
            task_id="task-001",
            decision_type="SCOPE_EXTENSION",
            content={"scope": "extended"},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        data = decision.to_dict()
        assert data["decision_id"] == "dec-001"
        assert data["decision_type"] == "SCOPE_EXTENSION"
        assert data["status"] == "pending"

    def test_creates_from_dict(self):
        data = {
            "decision_id": "dec-001",
            "product_key": "plan-001",
            "run_id": "run-001",
            "feature_id": "feature-001",
            "task_id": "task-001",
            "decision_type": "SCOPE_EXTENSION",
            "content": {"scope": "extended"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }
        decision = DurableDecision.from_dict(data)
        assert decision.decision_id == "dec-001"


class TestDurableDecisionStore:
    def test_creates_store(self, temp_repo):
        store = DurableDecisionStore(temp_repo, "plan-001")
        assert store.product_key == "plan-001"

    def test_records_decision(self, temp_repo):
        store = DurableDecisionStore(temp_repo, "plan-001")
        decision = DurableDecision(
            decision_id="dec-001",
            product_key="plan-001",
            run_id="run-001",
            feature_id="feature-001",
            task_id="task-001",
            decision_type="SCOPE_EXTENSION",
            content={"scope": "extended"},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        store.record_decision(decision)
        assert store.store_path.exists()

    def test_reads_all_decisions(self, temp_repo):
        store = DurableDecisionStore(temp_repo, "plan-001")
        for i in range(3):
            decision = DurableDecision(
                decision_id=f"dec-{i:03d}",
                product_key="plan-001",
                run_id="run-001",
                feature_id="feature-001",
                task_id="task-001",
                decision_type="SCOPE_EXTENSION",
                content={"index": i},
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            store.record_decision(decision)

        decisions = store.read_all_decisions()
        assert len(decisions) == 3

    def test_gets_decisions_for_feature(self, temp_repo):
        store = DurableDecisionStore(temp_repo, "plan-001")
        for feature_id in ["feature-001", "feature-002", "feature-001"]:
            decision = DurableDecision(
                decision_id=f"dec-{feature_id}",
                product_key="plan-001",
                run_id="run-001",
                feature_id=feature_id,
                task_id="task-001",
                decision_type="SCOPE_EXTENSION",
                content={"feature": feature_id},
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            store.record_decision(decision)

        decisions = store.get_decisions_for_feature("feature-001")
        assert len(decisions) == 2
        assert all(d.feature_id == "feature-001" for d in decisions)

    def test_gets_approved_decisions(self, temp_repo):
        store = DurableDecisionStore(temp_repo, "plan-001")
        decision = DurableDecision(
            decision_id="dec-001",
            product_key="plan-001",
            run_id="run-001",
            feature_id="feature-001",
            task_id="task-001",
            decision_type="SCOPE_EXTENSION",
            content={"scope": "extended"},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        store.record_decision(decision)

        store.approve_decision("dec-001")

        approved = store.get_approved_decisions()
        assert len(approved) == 1
        assert approved[0].decision_id == "dec-001"

    def test_approves_decision(self, temp_repo):
        store = DurableDecisionStore(temp_repo, "plan-001")
        decision = DurableDecision(
            decision_id="dec-001",
            product_key="plan-001",
            run_id="run-001",
            feature_id="feature-001",
            task_id="task-001",
            decision_type="SCOPE_EXTENSION",
            content={"scope": "extended"},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        store.record_decision(decision)

        store.approve_decision("dec-001")

        decisions = store.read_all_decisions()
        approved_decision = next(d for d in decisions if d.decision_id == "dec-001")
        assert approved_decision.status == "approved"
        assert approved_decision.approved_at is not None

    def test_rejects_approval_of_missing_decision(self, temp_repo):
        store = DurableDecisionStore(temp_repo, "plan-001")

        with pytest.raises(ProductRuntimeError, match="Decision not found"):
            store.approve_decision("dec-missing")


class TestProductRuntime:
    def test_create_generates_unique_run_ids(self, temp_repo):
        runtime1 = ProductRuntime.create(temp_repo)
        runtime2 = ProductRuntime.create(temp_repo)

        assert runtime1.run_id != runtime2.run_id
        assert runtime1.state_manager.run_namespace != runtime2.state_manager.run_namespace

    def test_create_retries_when_generated_run_id_collides(self, temp_repo, monkeypatch):
        existing = ProductRuntime(temp_repo, "product-run-collision")
        existing.initialize_run("plan-001", "hash-existing")

        generated_ids = iter(["product-run-collision", "product-run-fresh"])

        monkeypatch.setattr(
            "autodev.product_runtime.ProductRuntime._generate_candidate_run_id",
            classmethod(lambda cls: next(generated_ids)),
        )

        runtime = ProductRuntime.create(temp_repo)

        assert runtime.run_id == "product-run-fresh"

    def test_initialize_run_rejects_namespace_collision_without_resume_proof(self, temp_repo):
        namespace = temp_repo / ".autodev" / "runs" / "products" / "run-001"
        namespace.mkdir(parents=True, exist_ok=True)
        (namespace / "journal.jsonl").write_text("", encoding="utf-8")

        runtime = ProductRuntime(temp_repo, "run-001")

        with pytest.raises(ProductRuntimeError, match="namespace collision"):
            runtime.initialize_run("plan-001", "abc123")

    def test_rejects_feature_graph_id_reused_by_product_graph(self, runtime):
        state = runtime.initialize_run("plan-001", "hash1")

        with pytest.raises(ProductRuntimeError, match="reserved for the product graph"):
            runtime.register_feature_graph_id("feature-001", state.product_graph_id or "")

    def test_rejects_feature_graph_id_reused_across_runs(self, temp_repo):
        runtime1 = ProductRuntime(temp_repo, "run-001")
        runtime1.initialize_run("plan-001", "hash1")
        runtime1.register_feature_graph_id("feature-001", "feature-graph-shared")

        runtime2 = ProductRuntime(temp_repo, "run-002")
        runtime2.initialize_run("plan-002", "hash2")

        with pytest.raises(ProductRuntimeError, match="already used by run run-001"):
            runtime2.register_feature_graph_id("feature-002", "feature-graph-shared")

    def test_feature_graph_id_registration_persists_across_runtime_instances(self, temp_repo):
        runtime1 = ProductRuntime(temp_repo, "run-001")
        runtime1.initialize_run("plan-001", "hash1")
        runtime1.register_feature_graph_id("feature-001", "feature-graph-001")

        runtime2 = ProductRuntime(temp_repo, "run-001")
        assert runtime2.get_feature_graph_id("feature-001") == "feature-graph-001"

    def test_initializes_run(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123")
        assert state.run_id == "run-001"
        assert state.plan_id == "plan-001"
        assert state.status == "RUNNING"

    def test_initialize_run_materializes_required_namespace_artifacts(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123")

        state_path = runtime.state_manager.get_state_path()
        journal_path = runtime.state_manager.get_journal_path()
        checkpoint_path = runtime.state_manager.get_checkpoints_path()
        locks_dir = runtime.state_manager.get_locks_dir()

        assert state_path.exists()
        assert journal_path.exists()
        assert checkpoint_path.exists()
        assert locks_dir.exists()
        assert locks_dir.is_dir()

        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        assert checkpoint["run_id"] == state.run_id
        assert checkpoint["plan_id"] == state.plan_id
        assert checkpoint["plan_hash"] == state.plan_hash
        assert checkpoint["status"] == state.status
        assert checkpoint["product_graph_id"] == state.product_graph_id

        journal_lines = journal_path.read_text(encoding="utf-8").splitlines()
        assert len(journal_lines) == 1
        run_start = json.loads(journal_lines[0])
        assert run_start["entry_type"] == "run_start"
        assert run_start["run_id"] == state.run_id
        assert run_start["timezone"]

    def test_initialize_run_reuses_existing_namespace_without_overwriting_artifacts(self, runtime):
        first_state = runtime.initialize_run("plan-001", "abc123")
        journal_path = runtime.state_manager.get_journal_path()
        checkpoint_path = runtime.state_manager.get_checkpoints_path()

        sentinel_entry = {
            "entry_id": "sentinel-entry",
            "entry_type": "action_completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "timezone": "UTC",
            "run_id": first_state.run_id,
            "data": {"sentinel": True},
        }
        with journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sentinel_entry) + "\n")

        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        checkpoint["sentinel"] = "preserved"
        checkpoint_path.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")

        lock_id = runtime.acquire_product_lock()
        lock_path = runtime.state_manager.get_locks_dir() / f"{lock_id}.json"
        assert lock_path.exists()

        second_state = runtime.initialize_run("plan-001", "abc123")

        assert second_state.product_graph_id == first_state.product_graph_id
        assert second_state.started_at == first_state.started_at
        assert lock_path.exists()

        journal_lines = journal_path.read_text(encoding="utf-8").splitlines()
        assert len(journal_lines) == 3
        assert any(json.loads(line)["entry_id"] == "sentinel-entry" for line in journal_lines)

        resumed_checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        assert resumed_checkpoint["sentinel"] == "preserved"

    def test_initialize_run_rejects_collision_with_different_plan_identity(self, runtime):
        runtime.initialize_run("plan-001", "abc123")

        with pytest.raises(ProductRuntimeError, match="already initialized"):
            runtime.initialize_run("plan-002", "different-hash")

    def test_initialize_run_persists_plan_snapshot_once_on_initial_creation(self, runtime):
        plan = make_plan_dict()
        expected_snapshot = runtime._normalize_plan(plan, plan_id="plan-001", plan_hash="abc123")

        runtime.initialize_run("plan-001", "abc123", plan=plan)

        persisted = runtime.state_manager.read_state("plan-001", "abc123")
        assert persisted.plan_snapshot == expected_snapshot

    def test_initialize_run_resumes_with_identical_plan_without_mutating_snapshot(self, runtime):
        plan = make_plan_dict()
        expected_snapshot = runtime._normalize_plan(plan, plan_id="plan-001", plan_hash="abc123")
        runtime.initialize_run("plan-001", "abc123", plan=plan)
        state_path = runtime.state_manager.get_state_path()
        before_resume = state_path.read_text(encoding="utf-8")

        resumed = runtime.initialize_run("plan-001", "abc123", plan=plan)

        after_resume = state_path.read_text(encoding="utf-8")
        assert resumed.plan_snapshot == expected_snapshot
        assert after_resume == before_resume

    def test_initialize_run_rejects_resuming_with_modified_feature_without_overwriting_snapshot(
        self, runtime
    ):
        initial_plan = make_plan_dict()
        runtime.initialize_run("plan-001", "abc123", plan=initial_plan)
        state_path = runtime.state_manager.get_state_path()
        before_resume = state_path.read_text(encoding="utf-8")

        changed_plan = make_plan_dict(
            features=[
                {
                    "feature_id": "feature-001",
                    "title": "Feature 001 changed",
                    "specification_path": "specs/feature-001-v2.md",
                    "required": False,
                    "priority": 9,
                    "depends_on": [],
                    "validations": ["unit"],
                }
            ]
        )

        with pytest.raises(ProductRuntimeError, match="PLAN_FEATURE_CONFIG_DIVERGENCE"):
            runtime.initialize_run("plan-001", "abc123", plan=changed_plan)

        after_resume = state_path.read_text(encoding="utf-8")
        assert after_resume == before_resume

    def test_initialize_run_rejects_resuming_with_modified_dependencies_without_overwriting_snapshot(
        self, runtime
    ):
        initial_plan = make_plan_dict()
        runtime.initialize_run("plan-001", "abc123", plan=initial_plan)
        state_path = runtime.state_manager.get_state_path()
        before_resume = state_path.read_text(encoding="utf-8")

        changed_plan = make_plan_dict(
            features=[
                {
                    "feature_id": "feature-001",
                    "title": "Feature 001",
                    "specification_path": "specs/feature-001.md",
                    "required": True,
                    "priority": 1,
                    "depends_on": ["feature-999"],
                    "validations": ["unit"],
                }
            ]
        )

        with pytest.raises(ProductRuntimeError, match="PLAN_FEATURE_CONFIG_DIVERGENCE"):
            runtime.initialize_run("plan-001", "abc123", plan=changed_plan)

        after_resume = state_path.read_text(encoding="utf-8")
        assert after_resume == before_resume

    def test_initialize_run_rejects_resuming_with_modified_validations_without_overwriting_snapshot(
        self, runtime
    ):
        initial_plan = make_plan_dict()
        runtime.initialize_run("plan-001", "abc123", plan=initial_plan)
        state_path = runtime.state_manager.get_state_path()
        before_resume = state_path.read_text(encoding="utf-8")

        changed_plan = make_plan_dict(global_validations=["pytest", "ruff"])

        with pytest.raises(ProductRuntimeError, match="PLAN_GLOBAL_VALIDATIONS_DIVERGENCE"):
            runtime.initialize_run("plan-001", "abc123", plan=changed_plan)

        after_resume = state_path.read_text(encoding="utf-8")
        assert after_resume == before_resume

    def test_initialize_run_legacy_state_without_snapshot_refuses_safe_resume(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123", plan=make_plan_dict())
        state.plan_snapshot = {}
        persist_runtime_state(runtime, state)
        state_path = runtime.state_manager.get_state_path()
        before_resume = state_path.read_text(encoding="utf-8")

        with pytest.raises(ProductRuntimeError, match="MISSING_PLAN_SNAPSHOT_PROOF"):
            runtime.initialize_run("plan-001", "abc123", plan=make_plan_dict())

        after_resume = state_path.read_text(encoding="utf-8")
        assert after_resume == before_resume

    def test_reconstructs_clean_state(self, runtime):
        plan = make_plan_dict()
        runtime.initialize_run("plan-001", "abc123", plan=plan)

        result = runtime.reconstruct_state("plan-001", "abc123", plan=plan)
        assert result.is_clean
        assert len(result.incidents) == 0
        assert len(result.divergences) == 0

    def test_detects_plan_hash_divergence(self, runtime):
        runtime.initialize_run("plan-001", "abc123")

        result = runtime.reconstruct_state("plan-001", "different-hash")
        assert not result.is_clean
        assert len(result.divergences) > 0

    def test_records_idempotent_action_intention(self, runtime):
        key = runtime.record_idempotent_action(
            feature_id="feature-001",
            task_id="task-001",
            action="IMPLEMENT",
            attempt=1,
            intention_data={"test": "data"},
        )
        assert key.run_id == "run-001"
        assert key.action == "IMPLEMENT"

        entries = runtime.state_manager.read_journal()
        assert [entry.entry_type.value for entry in entries[-3:]] == [
            "lock_acquired",
            "intention_start",
            "lock_released",
        ]

    def test_completes_idempotent_action(self, runtime):
        key = runtime.record_idempotent_action(
            feature_id="feature-001",
            task_id="task-001",
            action="IMPLEMENT",
            attempt=1,
        )
        runtime.complete_idempotent_action(key, success=True, result={"result": "ok"})

        action_entries = [
            entry.entry_type.value
            for entry in runtime.state_manager.read_journal()
            if entry.action == "IMPLEMENT"
        ]
        assert action_entries == [
            "intention_start",
            "action_applied",
            "action_completed",
        ]

    def test_checks_action_completion_status(self, runtime):
        key = runtime.record_idempotent_action(
            feature_id="feature-001",
            task_id="task-001",
            action="IMPLEMENT",
            attempt=1,
        )
        assert not runtime.is_action_already_completed(key)

        runtime.complete_idempotent_action(key, success=True)
        assert runtime.is_action_already_completed(key)

    def test_ensures_idempotence_prevents_duplication(self, runtime):
        key = IdempotenceKey(
            run_id="run-001",
            feature_id="feature-001",
            task_id="task-001",
            action="IMPLEMENT",
            attempt=1,
        )

        assert not runtime.is_action_already_completed(key)

        runtime.complete_idempotent_action(key, success=True, result={"value": 1})
        assert runtime.is_action_already_completed(key)

        assert runtime.is_action_already_completed(key)

    def test_records_durable_decision(self, runtime):
        decision_id = runtime.record_durable_decision(
            feature_id="feature-001",
            decision_type="SCOPE_EXTENSION",
            content={"scope": "extended", "reason": "user request"},
            task_id="task-001",
        )
        assert decision_id is not None

        decisions = runtime.get_durable_decisions_for_feature("feature-001")
        assert len(decisions) == 1
        assert decisions[0].decision_id == decision_id

    def test_approves_durable_decision(self, runtime):
        decision_id = runtime.record_durable_decision(
            feature_id="feature-001",
            decision_type="SCOPE_EXTENSION",
            content={"scope": "extended"},
        )
        runtime.approve_durable_decision(decision_id)

        approved = runtime.get_approved_durable_decisions()
        assert len(approved) == 1
        assert approved[0].decision_id == decision_id

    def test_finish_run_journals_intention_action_and_result_in_order(self, runtime):
        runtime.initialize_run("plan-001", "abc123")

        runtime.finish_run(success=True)

        entries = runtime.state_manager.read_journal()
        assert [entry.entry_type.value for entry in entries[-5:]] == [
            "lock_acquired",
            "intention_start",
            "action_applied",
            "action_completed",
            "lock_released",
        ]
        assert entries[-4].action == "finish_run"
        assert entries[-3].action == "finish_run"
        assert entries[-2].action == "finish_run"

    def test_finish_run_journals_intention_then_failure_on_error(self, runtime, monkeypatch):
        runtime.initialize_run("plan-001", "abc123")
        original_write_state = runtime.state_manager.write_state
        call_count = {"count": 0}

        def fail_on_second_write(state):
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise ProductRuntimeError("boom")
            return original_write_state(state)

        monkeypatch.setattr(runtime.state_manager, "write_state", fail_on_second_write)

        with pytest.raises(ProductRuntimeError, match="boom"):
            runtime.finish_run(success=True)

        entries = runtime.state_manager.read_journal()
        assert [entry.entry_type.value for entry in entries[-4:]] == [
            "lock_acquired",
            "intention_start",
            "action_failed",
            "lock_released",
        ]
        assert entries[-2].action == "finish_run"
        assert entries[-2].data["error"] == "boom"

    def test_complete_idempotent_action_is_not_double_counted_on_resume(self, runtime):
        key = runtime.record_idempotent_action(
            feature_id="feature-001",
            task_id="task-001",
            action="IMPLEMENT",
            attempt=1,
        )

        runtime.complete_idempotent_action(key, success=True, result={"result": "ok"})
        runtime.complete_idempotent_action(key, success=True, result={"result": "duplicate"})

        entries = [
            entry
            for entry in runtime.state_manager.read_journal()
            if entry.action == "IMPLEMENT" and entry.entry_type.value == "action_completed"
        ]
        assert len(entries) == 1

    def test_finish_run_reuses_existing_product_lock_without_deadlock(self, runtime):
        runtime.initialize_run("plan-001", "abc123")
        lock_id = runtime.acquire_product_lock()

        runtime.finish_run(success=True)

        state = runtime.state_manager.read_state("plan-001", "abc123")
        assert state.status == "COMPLETED"
        remaining_locks = runtime.state_manager.list_locks()
        assert [lock.lock_id for lock in remaining_locks] == [lock_id]

    def test_finishes_successful_run(self, runtime):
        runtime.initialize_run("plan-001", "abc123")
        runtime.finish_run(success=True)

        state = runtime.state_manager.read_state("plan-001", "abc123")
        assert state.status == "COMPLETED"
        assert state.finished_at is not None

    def test_finishes_failed_run_with_error(self, runtime):
        runtime.initialize_run("plan-001", "abc123")
        runtime.finish_run(success=False, error_message="Test error")

        state = runtime.state_manager.read_state("plan-001", "abc123")
        assert state.status == "FAILED"
        assert state.error_message == "Test error"

    def test_updates_feature_state(self, runtime):
        runtime.initialize_run("plan-001", "abc123")
        feature_state = {"status": "COMPLETED", "tasks_completed": 5}
        runtime.update_feature_state("feature-001", feature_state)

        state = runtime.state_manager.read_state("plan-001", "abc123")
        assert state.feature_states["feature-001"]["status"] == "COMPLETED"

    def test_updates_task_state(self, runtime):
        runtime.initialize_run("plan-001", "abc123")
        task_state = {"status": "INTEGRATED", "produced_commit": "abc123"}
        runtime.update_task_state("task-001", task_state)

        state = runtime.state_manager.read_state("plan-001", "abc123")
        assert state.task_states["task-001"]["status"] == "INTEGRATED"

    def test_creates_run_checkpoint(self, runtime):
        runtime.initialize_run("plan-001", "abc123")
        checkpoint_data = {"features_completed": ["feature-001"], "status": "IN_PROGRESS"}
        runtime.create_run_checkpoint(checkpoint_data)

        checkpoint = runtime.get_run_checkpoint()
        assert checkpoint is not None
        assert checkpoint["features_completed"] == ["feature-001"]
        assert checkpoint["run_id"] == "run-001"

    def test_acquires_product_lock(self, runtime):
        lock_id = runtime.acquire_product_lock()
        assert lock_id is not None

        locks = runtime.state_manager.list_locks()
        assert len(locks) == 1
        assert locks[0].lock_type == "product"

    def test_acquires_feature_lock(self, runtime):
        lock_id = runtime.acquire_feature_lock("feature-001")
        assert lock_id is not None

        locks = runtime.state_manager.list_locks()
        assert len(locks) == 1
        assert locks[0].lock_type == "feature"
        assert locks[0].locked_entity_id == "feature-001"

    def test_releases_lock(self, runtime):
        lock_id = runtime.acquire_product_lock()
        runtime.release_lock(lock_id, reason="Test release")

        locks = runtime.state_manager.list_locks()
        assert len(locks) == 0

    def test_updates_lock_heartbeat(self, runtime):
        lock_id = runtime.acquire_product_lock()
        runtime.update_lock_heartbeat(lock_id)

    def test_checks_concurrent_access_no_conflict(self, runtime, temp_repo):
        lock_id = runtime.acquire_product_lock()

        blocking = runtime.check_concurrent_access("product")
        assert blocking is None

        runtime.release_lock(lock_id)

    def test_checks_concurrent_access_with_conflict(self, runtime, temp_repo):
        lock_id = runtime.acquire_product_lock()

        other_runtime = ProductRuntime(temp_repo, "run-002")
        blocking = other_runtime.check_concurrent_access("product")
        assert blocking == lock_id

        runtime.release_lock(lock_id)

    def test_checks_concurrent_access_detects_expired_lock(self, runtime, temp_repo):
        past = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        lock = runtime.state_manager.acquire_lock("product")

        lock_path = runtime.state_manager.get_locks_dir() / f"{lock.lock_id}.json"
        import json

        lock_data = json.loads(lock_path.read_text())
        lock_data["heartbeat_at"] = past
        lock_data["owner_pid"] = 999999
        lock_data["owner_host"] = socket.gethostname()
        lock_path.write_text(json.dumps(lock_data))

        other_runtime = ProductRuntime(temp_repo, "run-002")
        blocking = other_runtime.check_concurrent_access("product")
        assert blocking is None

        locks = runtime.state_manager.list_locks()
        assert len(locks) == 0

    def test_durable_decisions_persist_across_runtime_instances(self, temp_repo):
        runtime1 = ProductRuntime(temp_repo, "run-001")
        runtime1.initialize_run("plan-001", "hash1")
        decision_id = runtime1.record_durable_decision(
            feature_id="feature-001",
            decision_type="SCOPE_EXTENSION",
            content={"extended": True},
        )

        runtime2 = ProductRuntime(temp_repo, "run-001")
        decisions = runtime2.get_durable_decisions_for_feature("feature-001")
        assert len(decisions) == 1
        assert decisions[0].decision_id == decision_id

    def test_loads_approved_durable_decisions_across_runs_for_same_product(self, temp_repo):
        run_a = ProductRuntime(temp_repo, "run-a")
        run_a.initialize_run("plan-001", "hash-a")

        criterion_decision_id = run_a.record_durable_decision(
            feature_id="feature-001",
            decision_type="CRITERION_REALLOCATION",
            content={
                "criterion_id": "AC-R29-3",
                "old_owner": "task-001",
                "new_owner": "task-002",
            },
            task_id="task-001",
        )
        scope_decision_id = run_a.record_durable_decision(
            feature_id="feature-001",
            decision_type="SCOPE_EXTENSION",
            content={"extended_paths": ["src/product_extra.py"]},
        )
        run_a.approve_durable_decision(criterion_decision_id)
        run_a.approve_durable_decision(scope_decision_id)

        run_b = ProductRuntime(temp_repo, "run-b")
        state_b = run_b.initialize_run("plan-001", "hash-b")

        assert set(state_b.durable_decisions) == {criterion_decision_id, scope_decision_id}
        assert state_b.durable_decisions[criterion_decision_id]["source_run_id"] == "run-a"
        assert state_b.durable_decisions[criterion_decision_id]["product_key"] == "plan-001"
        assert state_b.durable_decisions[criterion_decision_id]["status"] == "approved"

        backlog = {
            "features": ["feature-001"],
            "reallocations": {},
            "extended_paths": [],
        }
        updated, conflicts = run_b.apply_durable_decisions_to_backlog(
            run_b.get_approved_durable_decisions(),
            backlog,
        )

        assert conflicts == []
        assert updated["reallocations"]["AC-R29-3"] == "task-002"
        assert "src/product_extra.py" in updated["extended_paths"]

    def test_does_not_load_durable_decisions_for_other_product(self, temp_repo):
        run_a = ProductRuntime(temp_repo, "run-a")
        run_a.initialize_run("plan-001", "hash-a")
        decision_id = run_a.record_durable_decision(
            feature_id="feature-001",
            decision_type="SCOPE_EXTENSION",
            content={"extended_paths": ["src/product_extra.py"]},
        )
        run_a.approve_durable_decision(decision_id)

        run_c = ProductRuntime(temp_repo, "run-c")
        state_c = run_c.initialize_run("plan-002", "hash-c")

        assert state_c.durable_decisions == {}
        assert run_c.get_approved_durable_decisions() == []

    def test_ignores_non_approved_durable_decisions_when_loading_new_run(self, temp_repo):
        run_a = ProductRuntime(temp_repo, "run-a")
        run_a.initialize_run("plan-001", "hash-a")
        pending_decision_id = run_a.record_durable_decision(
            feature_id="feature-001",
            decision_type="SCOPE_EXTENSION",
            content={"extended_paths": ["src/pending.py"]},
        )

        run_b = ProductRuntime(temp_repo, "run-b")
        state_b = run_b.initialize_run("plan-001", "hash-b")

        assert pending_decision_id not in state_b.durable_decisions
        assert run_b.get_approved_durable_decisions() == []

    def test_loading_durable_decisions_is_idempotent_across_reinitialization(self, temp_repo):
        run_a = ProductRuntime(temp_repo, "run-a")
        run_a.initialize_run("plan-001", "hash-a")
        decision_id = run_a.record_durable_decision(
            feature_id="feature-001",
            decision_type="SCOPE_EXTENSION",
            content={"extended_paths": ["src/product_extra.py"]},
        )
        run_a.approve_durable_decision(decision_id)

        run_b = ProductRuntime(temp_repo, "run-b")
        first_state = run_b.initialize_run("plan-001", "hash-b")
        second_state = run_b.initialize_run("plan-001", "hash-b")

        assert list(first_state.durable_decisions) == [decision_id]
        assert list(second_state.durable_decisions) == [decision_id]
        assert len(second_state.durable_decisions) == 1

    def test_reconstruct_state_reloads_approved_durable_decisions(self, temp_repo):
        run_a = ProductRuntime(temp_repo, "run-a")
        run_a.initialize_run("plan-001", "hash-a")
        decision_id = run_a.record_durable_decision(
            feature_id="feature-001",
            decision_type="SCOPE_EXTENSION",
            content={"extended_paths": ["src/product_extra.py"]},
        )
        run_a.approve_durable_decision(decision_id)

        run_b = ProductRuntime(temp_repo, "run-b")
        run_b.initialize_run("plan-001", "hash-b")
        state_b = run_b.state_manager.read_state("plan-001", "hash-b")
        state_b.durable_decisions = {}
        persist_runtime_state(run_b, state_b)

        result = run_b.reconstruct_state("plan-001", "hash-b")

        assert decision_id in result.state.durable_decisions

    def test_reconstruction_detects_plan_feature_set_divergence(self, runtime):
        initial_plan = make_plan_dict(
            features=[
                {
                    "feature_id": "feature-001",
                    "title": "Feature 001",
                    "specification_path": "specs/feature-001.md",
                    "required": True,
                    "priority": 1,
                    "depends_on": [],
                    "validations": ["unit"],
                }
            ]
        )
        runtime.initialize_run("plan-001", "abc123", plan=initial_plan)

        changed_plan = make_plan_dict(
            features=[
                {
                    "feature_id": "feature-001",
                    "title": "Feature 001",
                    "specification_path": "specs/feature-001.md",
                    "required": True,
                    "priority": 1,
                    "depends_on": [],
                    "validations": ["unit"],
                },
                {
                    "feature_id": "feature-002",
                    "title": "Feature 002",
                    "specification_path": "specs/feature-002.md",
                    "required": True,
                    "priority": 2,
                    "depends_on": ["feature-001"],
                    "validations": ["integration"],
                },
            ]
        )

        result = runtime.reconstruct_state("plan-001", "abc123", plan=changed_plan)

        assert not result.is_clean
        assert any(i.code == "PLAN_FEATURE_SET_DIVERGENCE" for i in result.incidents)

    def test_reconstruction_detects_plan_integration_branch_divergence(self, runtime):
        initial_plan = make_plan_dict(integration_branch="main")
        runtime.initialize_run("plan-001", "abc123", plan=initial_plan)

        changed_plan = make_plan_dict(integration_branch="release/2026-08")

        result = runtime.reconstruct_state("plan-001", "abc123", plan=changed_plan)

        assert not result.is_clean
        assert any(i.code == "PLAN_INTEGRATION_BRANCH_DIVERGENCE" for i in result.incidents)

    def test_reconstruction_detects_feature_plan_configuration_divergence(self, runtime):
        initial_plan = make_plan_dict()
        runtime.initialize_run("plan-001", "abc123", plan=initial_plan)

        changed_plan = make_plan_dict(
            features=[
                {
                    "feature_id": "feature-001",
                    "title": "Feature 001 changed",
                    "specification_path": "specs/feature-001-v2.md",
                    "required": False,
                    "priority": 9,
                    "depends_on": ["feature-099"],
                    "validations": ["integration"],
                }
            ]
        )

        result = runtime.reconstruct_state("plan-001", "abc123", plan=changed_plan)

        assert not result.is_clean
        assert any(i.code == "PLAN_FEATURE_CONFIG_DIVERGENCE" for i in result.incidents)

    def test_reconstruction_detects_global_validation_divergence_from_plan(self, runtime):
        initial_plan = make_plan_dict(global_validations=["pytest", "mypy"])
        runtime.initialize_run("plan-001", "abc123", plan=initial_plan)

        changed_plan = make_plan_dict(global_validations=["pytest", "ruff"])

        result = runtime.reconstruct_state("plan-001", "abc123", plan=changed_plan)

        assert not result.is_clean
        assert any(i.code == "PLAN_GLOBAL_VALIDATIONS_DIVERGENCE" for i in result.incidents)

    def test_reconstruct_state_still_detects_divergence_after_resume_refusal(self, runtime):
        initial_plan = make_plan_dict()
        runtime.initialize_run("plan-001", "abc123", plan=initial_plan)

        changed_plan = make_plan_dict(
            features=[
                {
                    "feature_id": "feature-001",
                    "title": "Feature 001 changed",
                    "specification_path": "specs/feature-001-v2.md",
                    "required": False,
                    "priority": 9,
                    "depends_on": ["feature-099"],
                    "validations": ["integration"],
                }
            ]
        )

        with pytest.raises(ProductRuntimeError, match="PLAN_FEATURE_CONFIG_DIVERGENCE"):
            runtime.initialize_run("plan-001", "abc123", plan=changed_plan)

        result = runtime.reconstruct_state("plan-001", "abc123", plan=changed_plan)

        assert not result.is_clean
        assert any(i.code == "PLAN_FEATURE_CONFIG_DIVERGENCE" for i in result.incidents)

    def test_apply_durable_decisions_to_backlog_detects_incompatible_feature(self, temp_repo):
        run_a = ProductRuntime(temp_repo, "run-a")
        run_a.initialize_run("plan-001", "hash-a")
        decision_id = run_a.record_durable_decision(
            feature_id="feature-001",
            decision_type="CRITERION_REALLOCATION",
            content={
                "criterion_id": "AC-R29-3",
                "old_owner": "task-001",
                "new_owner": "task-002",
            },
        )
        run_a.approve_durable_decision(decision_id)

        run_b = ProductRuntime(temp_repo, "run-b")
        run_b.initialize_run("plan-001", "hash-b")

        backlog = {"features": ["feature-999"], "reallocations": {}, "extended_paths": []}
        updated, conflicts = run_b.apply_durable_decisions_to_backlog(
            run_b.get_approved_durable_decisions(),
            backlog,
        )

        assert updated["reallocations"] == {}
        assert any("feature-001" in conflict for conflict in conflicts)

    def test_durable_decisions_remain_available_without_run_a_namespace(self, temp_repo):
        run_a = ProductRuntime(temp_repo, "run-a")
        run_a.initialize_run("plan-001", "hash-a")
        decision_id = run_a.record_durable_decision(
            feature_id="feature-001",
            decision_type="SCOPE_EXTENSION",
            content={"extended_paths": ["src/product_extra.py"]},
        )
        run_a.approve_durable_decision(decision_id)

        run_a_namespace = temp_repo / ".autodev" / "runs" / "products" / "run-a"
        assert run_a_namespace.exists()
        for path in sorted(run_a_namespace.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            else:
                path.rmdir()
        run_a_namespace.rmdir()

        run_b = ProductRuntime(temp_repo, "run-b")
        state_b = run_b.initialize_run("plan-001", "hash-b")

        assert decision_id in state_b.durable_decisions

    def test_prevents_concurrent_product_lock(self, runtime, temp_repo):
        """Test that concurrent lock acquisition is prevented, not just detected."""
        from autodev.product_state import ProductLockError

        lock_id = runtime.acquire_product_lock()
        assert lock_id is not None

        other_runtime = ProductRuntime(temp_repo, "run-002")
        with pytest.raises(ProductLockError, match="Cannot acquire.*already locked"):
            other_runtime.acquire_product_lock()

        runtime.release_lock(lock_id)

    def test_prevents_concurrent_feature_lock(self, runtime, temp_repo):
        """Test that concurrent feature lock acquisition is prevented."""
        from autodev.product_state import ProductLockError

        lock_id = runtime.acquire_feature_lock("feature-001")
        assert lock_id is not None

        other_runtime = ProductRuntime(temp_repo, "run-002")
        with pytest.raises(ProductLockError, match="Cannot acquire.*already locked"):
            other_runtime.acquire_feature_lock("feature-001")

        runtime.release_lock(lock_id)

    def test_idempotence_prevents_double_completion(self, runtime):
        """Test that idempotence truly prevents double-counting of completed actions."""
        key = IdempotenceKey(
            run_id="run-001",
            feature_id="feature-001",
            task_id="task-001",
            action="IMPLEMENT",
            attempt=1,
        )

        assert not runtime.is_action_already_completed(key)

        runtime.complete_idempotent_action(key, success=True, result={"value": 1})
        assert runtime.is_action_already_completed(key)

        journal_before = runtime.state_manager.read_journal()
        completed_before = len([e for e in journal_before if e.entry_type.value == "action_completed"])

        runtime.complete_idempotent_action(key, success=True, result={"value": 2})

        journal_after = runtime.state_manager.read_journal()
        completed_after = len([e for e in journal_after if e.entry_type.value == "action_completed"])

        assert completed_before == completed_after, "Idempotent action should not be recorded twice"

    def test_product_graph_id_is_distinct(self, runtime):
        """Test that ProductGraph receives a distinct, non-reusable ID."""
        state1 = runtime.initialize_run("plan-001", "hash1")
        graph_id1 = state1.product_graph_id

        assert graph_id1 is not None
        assert graph_id1.startswith("product-run-001-")

        runtime2 = ProductRuntime(runtime.repo_root, "run-002")
        state2 = runtime2.initialize_run("plan-001", "hash1")
        graph_id2 = state2.product_graph_id

        assert graph_id2 is not None
        assert graph_id1 != graph_id2, "Each run should have a distinct ProductGraph ID"

    def test_feature_graph_ids_are_distinct_and_tracked(self, runtime):
        """Test that feature graph IDs are distinct and can be registered per feature."""
        runtime.initialize_run("plan-001", "hash1")

        runtime.register_feature_graph_id("feature-001", "feature-run-001-abc123")
        runtime.register_feature_graph_id("feature-002", "feature-run-002-def456")

        assert runtime.get_feature_graph_id("feature-001") == "feature-run-001-abc123"
        assert runtime.get_feature_graph_id("feature-002") == "feature-run-002-def456"
        assert runtime.get_feature_graph_id("feature-003") is None

    def test_reconstruction_detects_missing_product_graph_id(self, runtime):
        """Test that reconstruction detects when a run is missing its ProductGraph ID."""
        state = runtime.initialize_run("plan-001", "hash1")
        state.product_graph_id = None
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "hash1")
        assert not result.is_clean
        assert any(i.code == "MISSING_PRODUCT_GRAPH_ID" for i in result.incidents)

    def test_reconstruction_is_clean_updated_after_git_checks(self, runtime):
        """Test that is_clean is recalculated after Git checks (AC-R2-2)."""
        state = runtime.initialize_run("plan-001", "abc123")
        state.status = "COMPLETED"
        state.integrated_commit = None
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert not result.is_clean
        assert any(i.code == "MISSING_INTEGRATION_COMMIT" for i in result.incidents)

    def test_reconstruction_detects_validation_results_missing(self, runtime):
        """Test that reconstruction detects missing validation results (AC-R16)."""
        state = runtime.initialize_run("plan-001", "abc123")
        state.status = "COMPLETED"
        state.integrated_commit = "abc123def456"
        state.validation_results = {}
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert not result.is_clean
        assert any(i.code == "MISSING_VALIDATION_RESULTS" for i in result.incidents)

    def test_reconstruction_detects_feature_graph_ids_missing_on_complete(self, runtime):
        """Test that reconstruction detects missing feature graph IDs for completed run (AC-R13-6)."""
        state = runtime.initialize_run("plan-001", "abc123")
        state.status = "COMPLETED"
        state.feature_graph_ids = {}
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert not result.is_clean
        assert any(i.code == "MISSING_FEATURE_GRAPH_IDS" for i in result.incidents)

    def test_reconstruction_detects_status_divergence(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123")
        state.status = "COMPLETED"
        state.feature_states["feature-001"] = {"status": "IN_PROGRESS"}
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert not result.is_clean
        assert any(i.code == "FEATURE_STATUS_DIVERGENCE" for i in result.incidents)

    def test_reconstruction_detects_feature_branch_divergence(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123")
        state.feature_states["feature-001"] = {
            "status": "RUNNING",
            "branch": "autodev/feature-001",
            "current_branch": "autodev/feature-001-hotfix",
        }
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert not result.is_clean
        assert any(i.code == "FEATURE_BRANCH_DIVERGENCE" for i in result.incidents)

    def test_reconstruction_detects_feature_worktree_divergence(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123")
        state.feature_states["feature-001"] = {
            "status": "RUNNING",
            "worktree": "/tmp/feature-001",
            "current_worktree": "/tmp/feature-001-alt",
        }
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert not result.is_clean
        assert any(i.code == "FEATURE_WORKTREE_DIVERGENCE" for i in result.incidents)

    def test_reconstruction_detects_base_commit_divergence(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123")
        state.base_commit = "base-commit"
        state.current_commit = "current-commit"
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert not result.is_clean
        assert any(i.code == "BASE_COMMIT_DIVERGENCE" for i in result.incidents)

    def test_reconstruction_detects_integrated_commit_divergence(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123")
        state.integrated_commit = "integrated-commit"
        state.current_commit = "current-commit"
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert not result.is_clean
        assert any(i.code == "INTEGRATED_COMMIT_DIVERGENCE" for i in result.incidents)

    def test_reconstruction_detects_dependency_divergence(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123")
        state.feature_states["feature-001"] = {
            "status": "RUNNING",
            "dependencies": ["feature-010"],
            "resolved_dependencies": ["feature-011"],
        }
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert not result.is_clean
        assert any(i.code == "FEATURE_DEPENDENCY_DIVERGENCE" for i in result.incidents)

    def test_reconstruction_detects_checkpoint_incompatible(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123")
        persist_runtime_state(runtime, state)
        persist_runtime_checkpoint(runtime, {"run_id": "run-001", "plan_hash": "wrong-hash"})

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert not result.is_clean
        assert any(i.code == "CHECKPOINT_PLAN_HASH_DIVERGENCE" for i in result.incidents)

    def test_reconstruction_detects_validation_results_incoherent(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123")
        state.status = "COMPLETED"
        state.integrated_commit = "abc123"
        state.validation_results = {
            "global": {"status": "PASS", "expected_status": "FAIL"}
        }
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert not result.is_clean
        assert any(i.code == "VALIDATION_RESULT_DIVERGENCE" for i in result.incidents)

    def test_reconstruction_detects_missing_required_child_artifact(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123")
        state.feature_states["feature-001"] = {
            "required_child_artifacts": [
                {"path": "reports/dev/missing.md", "exists": False}
            ]
        }
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert not result.is_clean
        assert any(i.code == "MISSING_REQUIRED_CHILD_ARTIFACT" for i in result.incidents)

    def test_reconstruction_detects_divergent_required_child_artifact(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123")
        artifact_path = "reports/dev/existing.md"
        artifact_file = runtime.repo_root / artifact_path
        artifact_file.parent.mkdir(parents=True, exist_ok=True)
        artifact_file.write_text("current-artifact", encoding="utf-8")
        state.feature_states["feature-001"] = {
            "required_child_artifacts": [
                {
                    "path": artifact_path,
                    "absolute_path": str(artifact_file),
                    "exists": True,
                    "recorded_digest": "abc",
                }
            ]
        }
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert not result.is_clean
        assert any(i.code == "CHILD_ARTIFACT_DIVERGENCE" for i in result.incidents)

    def test_reconstruction_does_not_trust_plan_status_or_narrative_report(self, runtime):
        state = runtime.initialize_run("plan-001", "abc123")
        state.feature_states["feature-001"] = {
            "plan_status": "COMPLETED",
            "narrative_report": "Everything is done.",
            "status": "RUNNING",
        }
        persist_runtime_state(runtime, state)

        result = runtime.reconstruct_state("plan-001", "abc123")
        assert result.state.feature_states["feature-001"]["status"] == "RUNNING"
        assert result.is_clean

    def test_attach_child_artifacts_persists_legacy_and_required_metadata(self, runtime):
        runtime.initialize_run("plan-001", "abc123")
        artifact_path = "reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T05.md"
        artifact_file = runtime.repo_root / artifact_path
        artifact_file.parent.mkdir(parents=True, exist_ok=True)
        artifact_file.write_text("artifact", encoding="utf-8")

        runtime.attach_child_artifacts("feature-001", [artifact_path])

        state = runtime.state_manager.read_state("plan-001", "abc123")
        attachment = state.feature_states["feature-001"]["child_artifacts"][0]

        assert attachment["path"] == artifact_path
        assert attachment["legacy_path"] == artifact_path
        assert attachment["required"] is True
        assert state.feature_states["feature-001"]["attached_artifacts"] == [artifact_path]

    def test_attach_child_artifacts_is_idempotent_and_journaled(self, runtime):
        runtime.initialize_run("plan-001", "abc123")
        artifact_path = "reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T05.md"
        artifact_file = runtime.repo_root / artifact_path
        artifact_file.parent.mkdir(parents=True, exist_ok=True)
        artifact_file.write_text("artifact", encoding="utf-8")

        runtime.attach_child_artifacts("feature-001", [artifact_path])
        runtime.attach_child_artifacts("feature-001", [artifact_path])

        state = runtime.state_manager.read_state("plan-001", "abc123")
        assert len(state.feature_states["feature-001"]["child_artifacts"]) == 1

        journal_entries = runtime.state_manager.read_journal()
        attachment_entries = [
            entry
            for entry in journal_entries
            if entry.data.get("action") == "attach_child_artifacts"
            and entry.entry_type.value == "action_completed"
        ]
        assert len(attachment_entries) == 1

    def test_attach_child_artifacts_rejects_missing_required_artifact(self, runtime):
        runtime.initialize_run("plan-001", "abc123")

        with pytest.raises(ProductRuntimeError, match="Missing required child artifact"):
            runtime.attach_child_artifacts("feature-001", ["reports/dev/missing.md"])

    def test_record_git_evidence_persists_product_and_feature_evidence_to_disk_and_reloads(self, temp_repo):
        runtime = ProductRuntime(temp_repo, "run-001")
        runtime.initialize_run("plan-001", "abc123", plan=make_plan_dict())

        product_lock = runtime.acquire_product_lock()
        try:
            runtime.record_git_evidence(
                branch="main",
                current_branch="main",
                base_commit="prod-base-001",
                current_commit="prod-head-001",
                integrated_commit="prod-head-001",
                worktree="/tmp/product-run-001",
                current_worktree="/tmp/product-run-001",
            )
        finally:
            runtime.release_lock(product_lock, reason="product evidence recorded")

        feature_lock = runtime.acquire_feature_lock("feature-001")
        try:
            runtime.record_git_evidence(
                feature_id="feature-001",
                branch="autodev/feature-001",
                current_branch="autodev/feature-001",
                base_commit="feature-base-001",
                current_commit="feature-head-001",
                integrated_commit="feature-integrated-001",
                worktree="/tmp/feature-001",
                current_worktree="/tmp/feature-001",
            )
        finally:
            runtime.release_lock(feature_lock, reason="feature evidence recorded")

        state_path = runtime.state_manager.get_state_path()
        persisted = json.loads(state_path.read_text(encoding="utf-8"))
        assert persisted["product_branch"] == "main"
        assert persisted["current_commit"] == "prod-head-001"
        assert persisted["product_worktree"] == "/tmp/product-run-001"
        assert persisted["feature_states"]["feature-001"]["branch"] == "autodev/feature-001"
        assert persisted["feature_states"]["feature-001"]["base_commit"] == "feature-base-001"
        assert persisted["feature_states"]["feature-001"]["integrated_commit"] == "feature-integrated-001"
        assert persisted["feature_states"]["feature-001"]["worktree"] == "/tmp/feature-001"

        reloaded_runtime = ProductRuntime(temp_repo, "run-001")
        result = reloaded_runtime.reconstruct_state("plan-001", "abc123", plan=make_plan_dict())

        assert result.state.product_branch == "main"
        assert result.state.current_commit == "prod-head-001"
        assert result.state.product_worktree == "/tmp/product-run-001"
        assert result.state.feature_states["feature-001"]["branch"] == "autodev/feature-001"
        assert result.state.feature_states["feature-001"]["base_commit"] == "feature-base-001"
        assert result.state.feature_states["feature-001"]["integrated_commit"] == "feature-integrated-001"
        assert result.state.feature_states["feature-001"]["worktree"] == "/tmp/feature-001"

    def test_record_git_evidence_partial_update_preserves_existing_fields(self, runtime):
        runtime.initialize_run("plan-001", "abc123")

        lock_id = runtime.acquire_product_lock()
        try:
            runtime.record_git_evidence(
                branch="main",
                current_branch="main",
                base_commit="prod-base-001",
                current_commit="prod-head-001",
                integrated_commit="prod-head-001",
                worktree="/tmp/product-run-001",
                current_worktree="/tmp/product-run-001",
            )
            runtime.record_git_evidence(
                integrated_commit="prod-release-002",
            )
        finally:
            runtime.release_lock(lock_id, reason="product evidence updated")

        persisted = json.loads(runtime.state_manager.get_state_path().read_text(encoding="utf-8"))
        assert persisted["product_branch"] == "main"
        assert persisted["current_product_branch"] == "main"
        assert persisted["base_commit"] == "prod-base-001"
        assert persisted["current_commit"] == "prod-head-001"
        assert persisted["integrated_commit"] == "prod-release-002"
        assert persisted["product_worktree"] == "/tmp/product-run-001"
        assert persisted["current_product_worktree"] == "/tmp/product-run-001"

    def test_record_git_evidence_is_idempotent_and_journaled(self, runtime):
        runtime.initialize_run("plan-001", "abc123")

        lock_id = runtime.acquire_feature_lock("feature-001")
        try:
            runtime.record_git_evidence(
                feature_id="feature-001",
                branch="autodev/feature-001",
                current_branch="autodev/feature-001",
                base_commit="feature-base-001",
                integrated_commit="feature-integrated-001",
                worktree="/tmp/feature-001",
                current_worktree="/tmp/feature-001",
            )
            runtime.record_git_evidence(
                feature_id="feature-001",
                branch="autodev/feature-001",
                current_branch="autodev/feature-001",
                base_commit="feature-base-001",
                integrated_commit="feature-integrated-001",
                worktree="/tmp/feature-001",
                current_worktree="/tmp/feature-001",
            )
        finally:
            runtime.release_lock(lock_id, reason="feature evidence idempotence")

        journal_entries = runtime.state_manager.read_journal()
        evidence_entries = [
            entry
            for entry in journal_entries
            if entry.action == "record_git_evidence"
            and entry.entry_type.value == "action_completed"
        ]
        assert len(evidence_entries) == 1
        assert evidence_entries[0].feature_id == "feature-001"
        assert evidence_entries[0].data["scope"] == "feature"

    def test_record_git_evidence_requires_appropriate_lock(self, runtime):
        runtime.initialize_run("plan-001", "abc123")

        with pytest.raises(ProductRuntimeError, match="active product lock"):
            runtime.record_git_evidence(branch="main")

        product_lock = runtime.acquire_product_lock()
        try:
            with pytest.raises(ProductRuntimeError, match="active feature lock"):
                runtime.record_git_evidence(feature_id="feature-001", branch="autodev/feature-001")
        finally:
            runtime.release_lock(product_lock, reason="wrong-lock-test")

    def test_apply_durable_decisions_to_backlog_scope_extension(self, runtime):
        """Test applying durable decisions preserves scope extensions (AC-R29-3)."""
        decision_id = runtime.record_durable_decision(
            feature_id="feature-001",
            decision_type="SCOPE_EXTENSION",
            content={"extended_paths": ["src/new_file.py", "tests/new_test.py"]},
        )
        runtime.approve_durable_decision(decision_id)

        backlog = {"features": ["feature-001"], "extended_paths": []}
        updated, conflicts = runtime.apply_durable_decisions_to_backlog(
            runtime.get_approved_durable_decisions(),
            backlog,
        )

        assert len(conflicts) == 0
        assert "src/new_file.py" in updated["extended_paths"]
        assert "tests/new_test.py" in updated["extended_paths"]

    def test_apply_durable_decisions_to_backlog_detects_conflicts(self, runtime):
        """Test that conflicting decisions are detected (AC-R29-3)."""
        decision_id = runtime.record_durable_decision(
            feature_id="feature-001",
            decision_type="CRITERION_REALLOCATION",
            content={
                "criterion_id": "cr-001",
                "old_owner": "task-001",
                "new_owner": "task-002",
            },
        )
        runtime.approve_durable_decision(decision_id)

        backlog = {
            "features": ["feature-001"],
            "reallocations": {"cr-001": "task-003"},
        }
        updated, conflicts = runtime.apply_durable_decisions_to_backlog(
            runtime.get_approved_durable_decisions(),
            backlog,
        )

        assert len(conflicts) > 0
        assert "cr-001" in conflicts[0]

    def test_acquire_task_lock_prevents_concurrent_writes(self, runtime, temp_repo):
        """Test that task locks prevent concurrent writes to task artifacts (AC-R13-10)."""
        from autodev.product_state import ProductLockError

        task_lock_id = runtime.acquire_task_lock("task-001")
        assert task_lock_id is not None

        other_runtime = ProductRuntime(temp_repo, "run-002")
        with pytest.raises(ProductLockError, match="Cannot acquire.*already locked"):
            other_runtime.acquire_task_lock("task-001")

        runtime.release_lock(task_lock_id)
