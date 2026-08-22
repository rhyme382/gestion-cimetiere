import json
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from autodev.product_state import (
    IdempotenceKey,
    JournalEntry,
    JournalEntryType,
    ProductLock,
    ProductLockError,
    ProductRunState,
    ProductStateError,
    ProductStateManager,
)


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        (repo_root / ".autodev").mkdir(parents=True)
        yield repo_root


@pytest.fixture
def state_manager(temp_repo):
    return ProductStateManager(temp_repo, "run-001")


class TestIdempotenceKey:
    def test_creates_key_from_components(self):
        key = IdempotenceKey(
            run_id="run-001",
            feature_id="feature-001",
            task_id="task-001",
            action="IMPLEMENT",
            attempt=1,
        )
        assert key.run_id == "run-001"
        assert key.feature_id == "feature-001"
        assert key.action == "IMPLEMENT"
        assert key.attempt == 1

    def test_converts_to_dict(self):
        key = IdempotenceKey(
            run_id="run-001",
            feature_id="feature-001",
            task_id="task-001",
            action="IMPLEMENT",
            attempt=1,
        )
        data = key.to_dict()
        assert data["run_id"] == "run-001"
        assert data["feature_id"] == "feature-001"
        assert data["task_id"] == "task-001"
        assert data["action"] == "IMPLEMENT"
        assert data["attempt"] == 1

    def test_creates_from_dict(self):
        data = {
            "run_id": "run-001",
            "feature_id": "feature-001",
            "task_id": "task-001",
            "action": "IMPLEMENT",
            "attempt": 1,
        }
        key = IdempotenceKey.from_dict(data)
        assert key.run_id == "run-001"
        assert key.attempt == 1


class TestJournalEntry:
    def test_creates_entry_with_required_fields(self):
        entry = JournalEntry(
            entry_id="entry-001",
            entry_type=JournalEntryType.RUN_START,
            timestamp=datetime.now(timezone.utc).isoformat(),
            timezone="UTC",
            run_id="run-001",
        )
        assert entry.entry_type == JournalEntryType.RUN_START
        assert entry.run_id == "run-001"

    def test_rejects_empty_timestamp(self):
        with pytest.raises(ProductStateError, match="timestamp cannot be empty"):
            JournalEntry(
                entry_id="entry-001",
                entry_type=JournalEntryType.RUN_START,
                timestamp="",
                timezone="UTC",
                run_id="run-001",
            )

    def test_rejects_empty_timezone(self):
        with pytest.raises(ProductStateError, match="timezone cannot be empty"):
            JournalEntry(
                entry_id="entry-001",
                entry_type=JournalEntryType.RUN_START,
                timestamp=datetime.now(timezone.utc).isoformat(),
                timezone="",
                run_id="run-001",
            )

    def test_rejects_empty_run_id(self):
        with pytest.raises(ProductStateError, match="run_id cannot be empty"):
            JournalEntry(
                entry_id="entry-001",
                entry_type=JournalEntryType.RUN_START,
                timestamp=datetime.now(timezone.utc).isoformat(),
                timezone="UTC",
                run_id="",
            )

    def test_converts_to_dict(self):
        key = IdempotenceKey(
            run_id="run-001",
            feature_id="feature-001",
            task_id="task-001",
            action="IMPLEMENT",
            attempt=1,
        )
        entry = JournalEntry(
            entry_id="entry-001",
            entry_type=JournalEntryType.INTENTION_START,
            timestamp=datetime.now(timezone.utc).isoformat(),
            timezone="UTC",
            run_id="run-001",
            feature_id="feature-001",
            task_id="task-001",
            action="IMPLEMENT",
            idempotence_key=key,
            data={"test": "value"},
        )
        data = entry.to_dict()
        assert data["entry_type"] == "intention_start"
        assert data["run_id"] == "run-001"
        assert data["idempotence_key"]["attempt"] == 1

    def test_creates_from_dict(self):
        data = {
            "entry_id": "entry-001",
            "entry_type": "intention_start",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "timezone": "UTC",
            "run_id": "run-001",
            "feature_id": "feature-001",
            "task_id": "task-001",
            "action": "IMPLEMENT",
            "idempotence_key": {
                "run_id": "run-001",
                "feature_id": "feature-001",
                "task_id": "task-001",
                "action": "IMPLEMENT",
                "attempt": 1,
            },
            "data": {"test": "value"},
        }
        entry = JournalEntry.from_dict(data)
        assert entry.entry_type == JournalEntryType.INTENTION_START
        assert entry.idempotence_key is not None


class TestProductLock:
    def test_creates_lock(self):
        lock = ProductLock(
            lock_id="lock-001",
            lock_type="product",
            owner_run_id="run-001",
            owner_pid=12345,
            owner_logical="autodev-run-001",
            acquired_at=datetime.now(timezone.utc).isoformat(),
            heartbeat_at=datetime.now(timezone.utc).isoformat(),
        )
        assert lock.lock_id == "lock-001"
        assert lock.lock_type == "product"

    def test_detects_expired_lock(self):
        past = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        lock = ProductLock(
            lock_id="lock-001",
            lock_type="product",
            owner_run_id="run-001",
            owner_pid=12345,
            owner_logical="autodev-run-001",
            acquired_at=past,
            heartbeat_at=past,
        )
        assert lock.is_expired(timeout_seconds=300)

    def test_detects_active_lock(self):
        now = datetime.now(timezone.utc).isoformat()
        lock = ProductLock(
            lock_id="lock-001",
            lock_type="product",
            owner_run_id="run-001",
            owner_pid=12345,
            owner_logical="autodev-run-001",
            acquired_at=now,
            heartbeat_at=now,
        )
        assert not lock.is_expired(timeout_seconds=300)

    def test_converts_to_dict(self):
        now = datetime.now(timezone.utc).isoformat()
        lock = ProductLock(
            lock_id="lock-001",
            lock_type="product",
            owner_run_id="run-001",
            owner_pid=12345,
            owner_logical="autodev-run-001",
            acquired_at=now,
            heartbeat_at=now,
            locked_entity_id="feature-001",
        )
        data = lock.to_dict()
        assert data["lock_id"] == "lock-001"
        assert data["locked_entity_id"] == "feature-001"

    def test_creates_from_dict(self):
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "lock_id": "lock-001",
            "lock_type": "product",
            "owner_run_id": "run-001",
            "owner_pid": 12345,
            "owner_logical": "autodev-run-001",
            "acquired_at": now,
            "heartbeat_at": now,
        }
        lock = ProductLock.from_dict(data)
        assert lock.lock_id == "lock-001"


class TestProductRunState:
    def test_creates_state(self, temp_repo):
        state = ProductRunState(
            run_id="run-001",
            plan_id="plan-001",
            product_key="plan-001",
            schema_version="1.0",
            plan_hash="abc123",
            started_at=datetime.now(timezone.utc).isoformat(),
            run_namespace=temp_repo / ".autodev" / "runs" / "products" / "run-001",
        )
        assert state.run_id == "run-001"
        assert state.status == "RUNNING"

    def test_converts_to_dict(self, temp_repo):
        state = ProductRunState(
            run_id="run-001",
            plan_id="plan-001",
            product_key="plan-001",
            schema_version="1.0",
            plan_hash="abc123",
            started_at=datetime.now(timezone.utc).isoformat(),
            run_namespace=temp_repo / ".autodev" / "runs" / "products" / "run-001",
        )
        data = state.to_dict()
        assert data["run_id"] == "run-001"
        assert data["status"] == "RUNNING"

    def test_creates_from_dict(self, temp_repo):
        run_namespace = temp_repo / ".autodev" / "runs" / "products" / "run-001"
        data = {
            "run_id": "run-001",
            "plan_id": "plan-001",
            "product_key": "plan-001",
            "schema_version": "1.0",
            "plan_hash": "abc123",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "RUNNING",
        }
        state = ProductRunState.from_dict(data, run_namespace)
        assert state.run_id == "run-001"


class TestProductStateManager:
    def _make_state(self, state_manager: ProductStateManager) -> ProductRunState:
        return ProductRunState(
            run_id="run-001",
            plan_id="plan-001",
            product_key="plan-001",
            schema_version="1.0",
            plan_hash="abc123",
            started_at=datetime.now(timezone.utc).isoformat(),
            run_namespace=state_manager.run_namespace,
        )

    def test_creates_namespace_on_init(self, temp_repo):
        manager = ProductStateManager(temp_repo, "run-001")
        assert manager.run_namespace.exists()

    def test_gets_state_path(self, state_manager):
        path = state_manager.get_state_path()
        assert path.name == "state.json"
        assert "run-001" in str(path)

    def test_gets_journal_path(self, state_manager):
        path = state_manager.get_journal_path()
        assert path.name == "journal.jsonl"
        assert "run-001" in str(path)

    def test_gets_locks_dir(self, state_manager):
        locks_dir = state_manager.get_locks_dir()
        assert locks_dir.exists()
        assert "locks" in str(locks_dir)

    def test_gets_checkpoints_path(self, state_manager):
        path = state_manager.get_checkpoints_path()
        assert path.name == "checkpoint.json"
        assert "run-001" in str(path)

    def test_writes_and_reads_state(self, state_manager, temp_repo):
        state = self._make_state(state_manager)
        state_manager.acquire_lock("product")
        state_manager.write_state(state)
        read_state = state_manager.read_state("plan-001", "abc123")
        assert read_state.run_id == "run-001"

    def test_creates_new_state_if_not_exists(self, state_manager):
        state = state_manager.read_state("plan-001", "abc123")
        assert state.run_id == "run-001"
        assert state.plan_id == "plan-001"

    def test_writes_journal_entry(self, state_manager):
        state_manager.acquire_lock("product")
        entry = JournalEntry(
            entry_id="entry-001",
            entry_type=JournalEntryType.RUN_START,
            timestamp=datetime.now(timezone.utc).isoformat(),
            timezone="UTC",
            run_id="run-001",
        )
        state_manager.write_journal_entry(entry)
        entries = state_manager.read_journal()
        assert len(entries) == 2
        assert entries[-1].entry_id == "entry-001"

    def test_reads_multiple_journal_entries(self, state_manager):
        state_manager.acquire_lock("product")
        for i in range(3):
            entry = JournalEntry(
                entry_id=f"entry-{i:03d}",
                entry_type=JournalEntryType.RUN_START,
                timestamp=datetime.now(timezone.utc).isoformat(),
                timezone="UTC",
                run_id="run-001",
            )
            state_manager.write_journal_entry(entry)

        entries = state_manager.read_journal()
        assert len(entries) == 4

    def test_records_action_intention(self, state_manager):
        state_manager.acquire_lock("task", locked_entity_id="task", task_id="task-001")
        key = state_manager.record_action_intention(
            feature_id="feature-001",
            task_id="task-001",
            action="IMPLEMENT",
            attempt=1,
            data={"test": "data"},
        )
        assert key.run_id == "run-001"
        assert key.action == "IMPLEMENT"

        entries = state_manager.read_journal()
        assert len(entries) == 2
        assert entries[-1].entry_type == JournalEntryType.INTENTION_START

    def test_records_action_result(self, state_manager):
        key = IdempotenceKey("run-001", "feature-001", "task-001", "IMPLEMENT", 1)
        state_manager.acquire_lock("task", locked_entity_id="task", task_id="task-001")
        state_manager.record_action_result(key, success=True, result={"done": True})

        entries = state_manager.read_journal()
        assert len(entries) == 2
        assert entries[-1].entry_type == JournalEntryType.ACTION_COMPLETED

    def test_acquires_product_lock(self, state_manager):
        lock = state_manager.acquire_lock("product")
        assert lock.lock_type == "product"
        assert lock.owner_run_id == "run-001"

        locks = state_manager.list_locks()
        assert len(locks) == 1

    def test_acquires_feature_lock(self, state_manager):
        lock = state_manager.acquire_lock("feature", locked_entity_id="feature-001")
        assert lock.lock_type == "feature"
        assert lock.locked_entity_id == "feature-001"

    def test_releases_lock(self, state_manager):
        lock = state_manager.acquire_lock("product")
        lock_id = lock.lock_id

        state_manager.release_lock(lock_id, reason="Test release")

        locks = state_manager.list_locks()
        assert len(locks) == 0

    def test_rejects_release_of_unowned_lock(self, state_manager, temp_repo):
        lock = state_manager.acquire_lock("product")
        lock_id = lock.lock_id

        other_manager = ProductStateManager(temp_repo, "run-002")

        with pytest.raises(ProductLockError, match="owned by|Cannot release"):
            other_manager.release_lock(lock_id)

    def test_refuses_recovery_of_expired_lock_when_owner_process_is_still_alive(
        self, state_manager, temp_repo
    ):
        lock = state_manager.acquire_lock("product")
        lock_path = state_manager.get_locks_dir() / f"{lock.lock_id}.json"
        lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
        lock_data["heartbeat_at"] = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        lock_path.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")

        other_manager = ProductStateManager(temp_repo, "run-002")
        with pytest.raises(ProductLockError, match="still active"):
            other_manager.release_lock(lock.lock_id, reason="stale recovery", force_expired=True)

        assert lock_path.exists()

    def test_recovers_expired_lock_when_local_owner_is_confirmed_inactive(
        self, state_manager, temp_repo
    ):
        lock = state_manager.acquire_lock("product")
        lock_path = state_manager.get_locks_dir() / f"{lock.lock_id}.json"
        lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
        lock_data["heartbeat_at"] = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        lock_data["owner_pid"] = 999999
        lock_data["owner_host"] = socket.gethostname()
        lock_path.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")

        other_manager = ProductStateManager(temp_repo, "run-002")
        other_manager.release_lock(lock.lock_id, reason="stale recovery", force_expired=True)

        assert not lock_path.exists()

        entries = other_manager.read_journal()
        release_entry = entries[-1]
        assert release_entry.entry_type == JournalEntryType.LOCK_RELEASED
        assert release_entry.data["owner_verification"]["owner_pid"] == 999999
        assert release_entry.data["owner_verification"]["owner_active"] is False
        assert release_entry.data["owner_verification"]["verification_status"] == "inactive"

    def test_refuses_recovery_of_unverifiable_expired_lock(self, state_manager, temp_repo):
        lock = state_manager.acquire_lock("product")
        lock_path = state_manager.get_locks_dir() / f"{lock.lock_id}.json"
        lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
        lock_data["heartbeat_at"] = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        lock_data["owner_host"] = "remote-host.example"
        lock_path.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")

        other_manager = ProductStateManager(temp_repo, "run-002")
        with pytest.raises(ProductLockError, match="cannot be verified reliably"):
            other_manager.release_lock(lock.lock_id, reason="stale recovery", force_expired=True)

        assert lock_path.exists()

    def test_refuses_recovery_of_non_expired_foreign_lock(self, state_manager, temp_repo):
        lock = state_manager.acquire_lock("product")
        other_manager = ProductStateManager(temp_repo, "run-002")

        with pytest.raises(ProductLockError, match="owned by run-001"):
            other_manager.release_lock(lock.lock_id, reason="stale recovery", force_expired=True)

    def test_refuses_recovery_when_lock_changes_during_reclamation(
        self, state_manager, temp_repo, monkeypatch
    ):
        lock = state_manager.acquire_lock("product")
        lock_path = state_manager.get_locks_dir() / f"{lock.lock_id}.json"
        lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
        lock_data["heartbeat_at"] = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        lock_data["owner_pid"] = 999999
        lock_data["owner_host"] = socket.gethostname()
        lock_path.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")

        other_manager = ProductStateManager(temp_repo, "run-002")
        original_delete = other_manager._delete_lock_file_if_unchanged

        def race_then_delete(path, expected_contents):
            changed = json.loads(path.read_text(encoding="utf-8"))
            changed["owner_logical"] = "replacement-owner"
            path.write_text(json.dumps(changed, indent=2), encoding="utf-8")
            original_delete(path, expected_contents)

        monkeypatch.setattr(other_manager, "_delete_lock_file_if_unchanged", race_then_delete)

        with pytest.raises(ProductLockError, match="changed during verification"):
            other_manager.release_lock(lock.lock_id, reason="stale recovery", force_expired=True)

        assert lock_path.exists()

    def test_repeated_recovery_of_same_lock_is_controlled(self, state_manager, temp_repo):
        lock = state_manager.acquire_lock("product")
        lock_path = state_manager.get_locks_dir() / f"{lock.lock_id}.json"
        lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
        lock_data["heartbeat_at"] = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        lock_data["owner_pid"] = 999999
        lock_data["owner_host"] = socket.gethostname()
        lock_path.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")

        other_manager = ProductStateManager(temp_repo, "run-002")
        other_manager.release_lock(lock.lock_id, reason="stale recovery", force_expired=True)

        with pytest.raises(ProductLockError, match="Lock not found"):
            other_manager.release_lock(lock.lock_id, reason="repeat recovery", force_expired=True)

    def test_updates_lock_heartbeat(self, state_manager):
        lock = state_manager.acquire_lock("product")
        lock_id = lock.lock_id
        original_heartbeat = lock.heartbeat_at

        state_manager.update_lock_heartbeat(lock_id)

        locks = state_manager.list_locks()
        assert locks[0].heartbeat_at >= original_heartbeat

    def test_lists_locks(self, state_manager):
        state_manager.acquire_lock("product")
        state_manager.acquire_lock("feature", locked_entity_id="feature-001")

        locks = state_manager.list_locks()
        assert len(locks) == 2

    def test_writes_and_reads_checkpoint(self, state_manager):
        checkpoint_data = {"feature_id": "feature-001", "status": "COMPLETED"}
        state_manager.acquire_lock("product")
        state_manager.write_checkpoint(checkpoint_data)

        checkpoint = state_manager.read_checkpoint()
        assert checkpoint is not None
        assert checkpoint["feature_id"] == "feature-001"
        assert "checkpoint_timestamp" in checkpoint

    def test_returns_none_for_missing_checkpoint(self, state_manager):
        checkpoint = state_manager.read_checkpoint()
        assert checkpoint is None

    def test_rejects_state_write_without_lock_after_initialization(self, state_manager):
        with pytest.raises(ProductLockError, match="state.json"):
            state_manager.write_state(self._make_state(state_manager))

    def test_rejects_checkpoint_write_without_lock_after_initialization(self, state_manager):
        with pytest.raises(ProductLockError, match="checkpoint.json"):
            state_manager.write_checkpoint({"feature_id": "feature-001"})

    def test_rejects_journal_write_without_lock_after_initialization(self, state_manager):
        entry = JournalEntry(
            entry_id="entry-001",
            entry_type=JournalEntryType.RUN_START,
            timestamp=datetime.now(timezone.utc).isoformat(),
            timezone="UTC",
            run_id="run-001",
        )
        with pytest.raises(ProductLockError, match="journal.jsonl"):
            state_manager.write_journal_entry(entry)

    def test_allows_state_checkpoint_and_journal_writes_with_owned_lock(self, state_manager):
        lock = state_manager.acquire_lock("product")
        state_manager.write_state(self._make_state(state_manager))
        state_manager.write_checkpoint({"feature_id": "feature-001"})
        state_manager.write_journal_entry(
            JournalEntry(
                entry_id="entry-001",
                entry_type=JournalEntryType.STATE_CHECKPOINT,
                timestamp=datetime.now(timezone.utc).isoformat(),
                timezone="UTC",
                run_id="run-001",
                data={"lock_id": lock.lock_id},
            )
        )

        assert state_manager.get_state_path().exists()
        assert state_manager.get_checkpoints_path().exists()
        assert state_manager.get_journal_path().exists()

    def test_rejects_write_when_only_foreign_lock_exists(self, state_manager, temp_repo):
        other_manager = ProductStateManager(temp_repo, "run-002")
        other_manager.acquire_lock("product")

        with pytest.raises(ProductLockError, match="owned lock"):
            state_manager.write_state(self._make_state(state_manager))

    def test_rejects_write_after_owned_lock_is_replaced(self, state_manager):
        lock = state_manager.acquire_lock("product")
        lock_path = state_manager.get_locks_dir() / f"{lock.lock_id}.json"
        replaced = json.loads(lock_path.read_text(encoding="utf-8"))
        replaced["owner_run_id"] = "run-999"
        replaced["owner_logical"] = "autodev-run-999"
        lock_path.write_text(json.dumps(replaced, indent=2), encoding="utf-8")

        with pytest.raises(ProductLockError, match="owned lock"):
            state_manager.write_state(self._make_state(state_manager))

    def test_rejects_write_after_owned_lock_is_deleted(self, state_manager):
        lock = state_manager.acquire_lock("product")
        lock_path = state_manager.get_locks_dir() / f"{lock.lock_id}.json"
        lock_path.unlink()

        with pytest.raises(ProductLockError, match="owned lock"):
            state_manager.write_checkpoint({"feature_id": "feature-001"})

    def test_rejects_concurrent_product_lock_acquisition(self, state_manager, temp_repo):
        """Test that concurrent product lock acquisition is actually prevented."""
        lock1 = state_manager.acquire_lock("product")
        assert lock1.lock_type == "product"

        other_manager = ProductStateManager(temp_repo, "run-002")

        with pytest.raises(ProductLockError, match="Cannot acquire.*already locked"):
            other_manager.acquire_lock("product")

        state_manager.release_lock(lock1.lock_id)

    def test_rejects_concurrent_feature_lock_acquisition(self, state_manager, temp_repo):
        """Test that concurrent feature lock acquisition is actually prevented."""
        lock1 = state_manager.acquire_lock("feature", locked_entity_id="feature-001")
        assert lock1.locked_entity_id == "feature-001"

        other_manager = ProductStateManager(temp_repo, "run-002")

        with pytest.raises(ProductLockError, match="Cannot acquire.*already locked"):
            other_manager.acquire_lock("feature", locked_entity_id="feature-001")

        state_manager.release_lock(lock1.lock_id)

    def test_allows_different_features_to_have_separate_locks(self, state_manager, temp_repo):
        """Test that different features can have separate locks concurrently."""
        lock1 = state_manager.acquire_lock("feature", locked_entity_id="feature-001")

        other_manager = ProductStateManager(temp_repo, "run-002")
        lock2 = other_manager.acquire_lock("feature", locked_entity_id="feature-002")

        assert lock1.locked_entity_id == "feature-001"
        assert lock2.locked_entity_id == "feature-002"

        state_manager.release_lock(lock1.lock_id)
        other_manager.release_lock(lock2.lock_id)
