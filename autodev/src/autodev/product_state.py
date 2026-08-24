from __future__ import annotations

import json
import os
import socket
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, NamedTuple
from uuid import uuid4

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore


class ProductStateError(RuntimeError):
    """Error during product state operations."""


class IdempotenceKey(NamedTuple):
    """Composite key ensuring idempotence of product run operations."""

    run_id: str
    feature_id: str
    task_id: str
    action: str
    attempt: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "feature_id": self.feature_id,
            "task_id": self.task_id,
            "action": self.action,
            "attempt": self.attempt,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> IdempotenceKey:
        """Create from dictionary."""
        return IdempotenceKey(
            run_id=data["run_id"],
            feature_id=data["feature_id"],
            task_id=data["task_id"],
            action=data["action"],
            attempt=data["attempt"],
        )


class JournalEntryType(str, Enum):
    """Type of journal entry."""

    RUN_START = "run_start"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    INTENTION_START = "intention_start"
    ACTION_APPLIED = "action_applied"
    ACTION_COMPLETED = "action_completed"
    ACTION_FAILED = "action_failed"
    STATE_CHECKPOINT = "state_checkpoint"
    LOCK_ACQUIRED = "lock_acquired"
    LOCK_RELEASED = "lock_released"
    DECISION_RECORDED = "decision_recorded"
    DECISION_INVALIDATED = "decision_invalidated"


@dataclass(frozen=True)
class JournalEntry:
    """Single entry in the product run journal."""

    entry_id: str
    entry_type: JournalEntryType
    timestamp: str
    timezone: str
    run_id: str
    feature_id: str | None = None
    task_id: str | None = None
    action: str | None = None
    idempotence_key: IdempotenceKey | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate journal entry on creation."""
        if not self.timestamp:
            raise ProductStateError("Journal entry timestamp cannot be empty")
        if not self.timezone:
            raise ProductStateError("Journal entry timezone cannot be empty")
        if not self.run_id:
            raise ProductStateError("Journal entry run_id cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type.value,
            "timestamp": self.timestamp,
            "timezone": self.timezone,
            "run_id": self.run_id,
        }
        if self.feature_id:
            data["feature_id"] = self.feature_id
        if self.task_id:
            data["task_id"] = self.task_id
        if self.action:
            data["action"] = self.action
        if self.idempotence_key:
            data["idempotence_key"] = self.idempotence_key.to_dict()
        if self.data:
            data["data"] = self.data
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> JournalEntry:
        """Create from dictionary."""
        idempotence_key = None
        if "idempotence_key" in data and data["idempotence_key"]:
            idempotence_key = IdempotenceKey.from_dict(data["idempotence_key"])

        return JournalEntry(
            entry_id=data["entry_id"],
            entry_type=JournalEntryType(data["entry_type"]),
            timestamp=data["timestamp"],
            timezone=data["timezone"],
            run_id=data["run_id"],
            feature_id=data.get("feature_id"),
            task_id=data.get("task_id"),
            action=data.get("action"),
            idempotence_key=idempotence_key,
            data=data.get("data", {}),
        )


class ProductLockError(RuntimeError):
    """Error managing product locks."""


@dataclass
class ProductLock:
    """Lock protecting concurrent product or feature operations."""

    lock_id: str
    lock_type: str  # 'product' or 'feature' or 'task'
    owner_run_id: str
    owner_pid: int
    owner_logical: str
    acquired_at: str
    heartbeat_at: str
    owner_host: str | None = None
    locked_entity_id: str | None = None
    full_entity_key: str | None = None  # Composite key including task_id if present (AC-R13-10)

    def is_expired(self, timeout_seconds: int = 300) -> bool:
        """Check if lock is expired based on heartbeat."""
        try:
            last_beat = datetime.fromisoformat(self.heartbeat_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            elapsed = (now - last_beat).total_seconds()
            return elapsed > timeout_seconds
        except (ValueError, TypeError):
            return True

    def update_heartbeat(self) -> None:
        """Update the heartbeat timestamp."""
        self.heartbeat_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "lock_id": self.lock_id,
            "lock_type": self.lock_type,
            "owner_run_id": self.owner_run_id,
            "owner_pid": self.owner_pid,
            "owner_logical": self.owner_logical,
            "owner_host": self.owner_host,
            "acquired_at": self.acquired_at,
            "heartbeat_at": self.heartbeat_at,
            "locked_entity_id": self.locked_entity_id,
            "full_entity_key": self.full_entity_key,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ProductLock:
        """Create from dictionary."""
        return ProductLock(
            lock_id=data["lock_id"],
            lock_type=data["lock_type"],
            owner_run_id=data["owner_run_id"],
            owner_pid=data["owner_pid"],
            owner_logical=data["owner_logical"],
            owner_host=data.get("owner_host"),
            acquired_at=data["acquired_at"],
            heartbeat_at=data["heartbeat_at"],
            locked_entity_id=data.get("locked_entity_id"),
            full_entity_key=data.get("full_entity_key"),
        )


@dataclass(frozen=True)
class PatchInventoryEntry:
    """Entrée d'inventaire pour un patch sauvegardé avant restauration.

    AC-R22-6: Le superviseur conserve un inventaire des patchs, blobs ou diffs
    produits par tentative avant toute restauration ou reprise.
    """
    patch_id: str
    timestamp: str
    timezone: str
    run_id: str
    task_id: str | None
    paths_affected: list[str]
    patch_content: str  # Contenu du diff/patch
    reason: str  # Ex: "out_of_scope_restoration", "content_verification"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "patch_id": self.patch_id,
            "timestamp": self.timestamp,
            "timezone": self.timezone,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "paths_affected": self.paths_affected,
            "patch_content": self.patch_content,
            "reason": self.reason,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "PatchInventoryEntry":
        """Create from dictionary."""
        return PatchInventoryEntry(
            patch_id=data["patch_id"],
            timestamp=data["timestamp"],
            timezone=data["timezone"],
            run_id=data["run_id"],
            task_id=data.get("task_id"),
            paths_affected=data.get("paths_affected", []),
            patch_content=data["patch_content"],
            reason=data["reason"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class ProductRunState:
    """State of a product run, separate from plan."""

    run_id: str
    plan_id: str
    product_key: str | None
    schema_version: str
    plan_hash: str
    started_at: str
    run_namespace: Path
    plan_snapshot: dict[str, Any] = field(default_factory=dict)
    product_graph_id: str | None = None
    feature_graph_ids: dict[str, str] = field(default_factory=dict)

    status: str = "RUNNING"
    finished_at: str | None = None
    error_message: str | None = None

    # Track Git state for reconstruction comparison
    base_commit: str | None = None
    current_commit: str | None = None
    integrated_commit: str | None = None
    product_branch: str | None = None
    current_product_branch: str | None = None
    product_worktree: str | None = None
    current_product_worktree: str | None = None
    
    # Track feature/task artefacts for comparison
    feature_states: dict[str, dict[str, Any]] = field(default_factory=dict)
    task_states: dict[str, dict[str, Any]] = field(default_factory=dict)
    durable_decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    completed_actions: set[str] = field(default_factory=set)
    
    # Track validations state
    validation_results: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "plan_id": self.plan_id,
            "product_key": self.product_key,
            "schema_version": self.schema_version,
            "plan_hash": self.plan_hash,
            "started_at": self.started_at,
            "plan_snapshot": self.plan_snapshot,
            "status": self.status,
            "finished_at": self.finished_at,
            "error_message": self.error_message,
            "product_graph_id": self.product_graph_id,
            "feature_graph_ids": self.feature_graph_ids,
            "base_commit": self.base_commit,
            "current_commit": self.current_commit,
            "integrated_commit": self.integrated_commit,
            "product_branch": self.product_branch,
            "current_product_branch": self.current_product_branch,
            "product_worktree": self.product_worktree,
            "current_product_worktree": self.current_product_worktree,
            "feature_states": self.feature_states,
            "task_states": self.task_states,
            "durable_decisions": self.durable_decisions,
            "validation_results": self.validation_results,
            "completed_actions": list(self.completed_actions),
        }

    @staticmethod
    def from_dict(data: dict[str, Any], run_namespace: Path) -> ProductRunState:
        """Create from dictionary."""
        completed_actions = set()
        if "completed_actions" in data and isinstance(data["completed_actions"], list):
            completed_actions = set(data["completed_actions"])

        return ProductRunState(
            run_id=data["run_id"],
            plan_id=data["plan_id"],
            product_key=data.get("product_key") or data["plan_id"],
            schema_version=data["schema_version"],
            plan_hash=data["plan_hash"],
            started_at=data["started_at"],
            run_namespace=run_namespace,
            plan_snapshot=data.get("plan_snapshot", {}),
            product_graph_id=data.get("product_graph_id"),
            feature_graph_ids=data.get("feature_graph_ids", {}),
            status=data.get("status", "RUNNING"),
            finished_at=data.get("finished_at"),
            error_message=data.get("error_message"),
            base_commit=data.get("base_commit"),
            current_commit=data.get("current_commit"),
            integrated_commit=data.get("integrated_commit"),
            product_branch=data.get("product_branch"),
            current_product_branch=data.get("current_product_branch"),
            product_worktree=data.get("product_worktree"),
            current_product_worktree=data.get("current_product_worktree"),
            feature_states=data.get("feature_states", {}),
            task_states=data.get("task_states", {}),
            durable_decisions=data.get("durable_decisions", {}),
            validation_results=data.get("validation_results", {}),
            completed_actions=completed_actions,
        )


class ProductStateManager:
    """Manages product run state, journals, and locks."""

    def __init__(self, repo_root: Path, run_id: str):
        """Initialize product state manager."""
        self.repo_root = repo_root
        self.run_id = run_id
        self.run_namespace = repo_root / ".autodev" / "runs" / "products" / run_id
        self._bootstrap_write_depth = 0
        self._lock_audit_depth = 0
        self._held_locks: dict[str, ProductLock] = {}
        self._ensure_namespace()

    def _ensure_namespace(self) -> None:
        """Ensure run namespace exists."""
        self.run_namespace.mkdir(parents=True, exist_ok=True)

    def get_state_path(self) -> Path:
        """Path to product run state file."""
        return self.run_namespace / "state.json"

    def get_run_claim_path(self) -> Path:
        """Path to the atomic run namespace claim."""
        return self.run_namespace / "run_claim.json"

    def get_journal_path(self) -> Path:
        """Path to append-only JSONL journal."""
        return self.run_namespace / "journal.jsonl"

    def get_locks_dir(self) -> Path:
        """Directory for lock files in run namespace (AC-R13-9)."""
        locks_dir = self.run_namespace / "locks"
        locks_dir.mkdir(parents=True, exist_ok=True)
        return locks_dir
    
    def _get_all_locks_dirs(self) -> list[Path]:
        """Get lock directories from all runs for conflict detection (AC-R13-10)."""
        runs_dir = self.repo_root / ".autodev" / "runs" / "products"
        if not runs_dir.exists():
            return []
        return [run_dir / "locks" for run_dir in runs_dir.iterdir() if run_dir.is_dir()]
    def get_checkpoints_path(self) -> Path:
        """Path to product checkpoint (separate from feature checkpoints)."""
        return self.run_namespace / "checkpoint.json"

    def ensure_run_artifacts(self, state: ProductRunState, checkpoint_data: dict[str, Any]) -> None:
        """Materialize required run artifacts without overwriting existing ones."""
        with self.bootstrap_writes():
            state_path = self.get_state_path()
            if not state_path.exists():
                self.write_state(state)

            journal_path = self.get_journal_path()
            if not journal_path.exists():
                journal_path.touch()
            if journal_path.stat().st_size == 0:
                self.write_journal_entry(
                    JournalEntry(
                        entry_id=str(uuid4()),
                        entry_type=JournalEntryType.RUN_START,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        timezone=self._timezone_name(),
                        run_id=self.run_id,
                        data={
                            "plan_id": state.plan_id,
                            "plan_hash": state.plan_hash,
                            "product_graph_id": state.product_graph_id,
                            "schema_version": state.schema_version,
                        },
                    )
                )

            checkpoint_path = self.get_checkpoints_path()
            if not checkpoint_path.exists():
                self.write_checkpoint(dict(checkpoint_data))

            self.get_locks_dir()

    def reserve_run_namespace(
        self,
        plan_id: str | None = None,
        plan_hash: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        """Atomically reserve the namespace for this product run ID."""
        claim_path = self.get_run_claim_path()
        existing_artifacts = self._list_namespace_artifacts(exclude={claim_path.name})

        if not claim_path.exists() and existing_artifacts:
            raise ProductStateError(
                f"Product run namespace collision for {self.run_id}: "
                f"unexpected existing artifacts {existing_artifacts}"
            )

        claim_data = {
            "run_id": self.run_id,
            "owner_pid": os.getpid(),
            "owner_host": socket.gethostname(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "plan_id": plan_id,
            "plan_hash": plan_hash,
        }

        try:
            fd = os.open(claim_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            existing_claim = self.read_run_claim()
            if existing_claim.get("run_id") != self.run_id:
                raise ProductStateError(
                    f"Product run namespace collision for {self.run_id}: "
                    f"already claimed by {existing_claim.get('run_id')}"
                )
            existing_plan_id = existing_claim.get("plan_id")
            existing_plan_hash = existing_claim.get("plan_hash")
            if plan_id and existing_plan_id not in (None, plan_id):
                raise ProductStateError(
                    f"Product run namespace collision for {self.run_id}: "
                    f"already claimed for plan {existing_plan_id}"
                )
            if plan_hash and existing_plan_hash not in (None, plan_hash):
                raise ProductStateError(
                    f"Product run namespace collision for {self.run_id}: "
                    f"already claimed for plan hash {existing_plan_hash}"
                )
            if (existing_plan_id is None and plan_id) or (existing_plan_hash is None and plan_hash):
                updated_claim = dict(existing_claim)
                updated_claim["plan_id"] = plan_id or existing_plan_id
                updated_claim["plan_hash"] = plan_hash or existing_plan_hash
                claim_path.write_text(
                    json.dumps(updated_claim, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                existing_claim = updated_claim
            return existing_claim, False

        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(claim_data, handle, indent=2, ensure_ascii=False)
        return claim_data, True

    def read_run_claim(self) -> dict[str, Any]:
        """Read the namespace claim metadata."""
        claim_path = self.get_run_claim_path()
        if not claim_path.exists():
            raise ProductStateError(f"Run namespace claim not found for {self.run_id}")
        try:
            return json.loads(claim_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProductStateError(f"Failed to read run claim from {claim_path}: {exc}") from exc

    def write_state(self, state: ProductRunState) -> None:
        """Persist product run state to JSON."""
        self._assert_write_allowed("state.json")
        state_path = self.get_state_path()
        state_path.write_text(
            json.dumps(state.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def read_state(self, plan_id: str, plan_hash: str) -> ProductRunState:
        """Read and reconstruct product run state from disk."""
        state_path = self.get_state_path()

        if state_path.exists():
            try:
                data = json.loads(state_path.read_text(encoding="utf-8"))
                return ProductRunState.from_dict(data, self.run_namespace)
            except (json.JSONDecodeError, ValueError) as exc:
                raise ProductStateError(f"Failed to read state from {state_path}: {exc}") from exc
        else:
            return ProductRunState(
                run_id=self.run_id,
                plan_id=plan_id,
                product_key=plan_id or None,
                schema_version="1.0",
                plan_hash=plan_hash,
                started_at=datetime.now(timezone.utc).isoformat(),
                run_namespace=self.run_namespace,
            )

    def write_journal_entry(self, entry: JournalEntry) -> None:
        """Append journal entry to JSONL journal."""
        self._assert_write_allowed("journal.jsonl")
        journal_path = self.get_journal_path()
        journal_line = json.dumps(entry.to_dict(), ensure_ascii=False) + "\n"
        with open(journal_path, "a", encoding="utf-8") as f:
            f.write(journal_line)

    def read_journal(self) -> list[JournalEntry]:
        """Read all journal entries from JSONL journal."""
        journal_path = self.get_journal_path()
        entries = []

        if not journal_path.exists():
            return entries

        try:
            with open(journal_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            entries.append(JournalEntry.from_dict(data))
                        except (json.JSONDecodeError, ValueError) as exc:
                            raise ProductStateError(
                                f"Failed to parse journal entry: {line}: {exc}"
                            ) from exc
        except IOError as exc:
            raise ProductStateError(f"Failed to read journal from {journal_path}: {exc}") from exc

        return entries

    def record_action_intention(
        self,
        feature_id: str,
        task_id: str,
        action: str,
        attempt: int,
        data: dict[str, Any] | None = None,
    ) -> IdempotenceKey:
        """Record intention to start an action before execution."""
        idempotence_key = IdempotenceKey(
            run_id=self.run_id,
            feature_id=feature_id,
            task_id=task_id,
            action=action,
            attempt=attempt,
        )

        entry = JournalEntry(
            entry_id=str(uuid4()),
            entry_type=JournalEntryType.INTENTION_START,
            timestamp=datetime.now(timezone.utc).isoformat(),
            timezone=datetime.now(timezone.utc).astimezone().tzinfo.tzname(datetime.now()),
            run_id=self.run_id,
            feature_id=feature_id,
            task_id=task_id,
            action=action,
            idempotence_key=idempotence_key,
            data=data or {},
        )
        self.write_journal_entry(entry)
        return idempotence_key

    def record_action_result(
        self,
        idempotence_key: IdempotenceKey,
        success: bool,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Record action result after execution."""
        entry = JournalEntry(
            entry_id=str(uuid4()),
            entry_type=JournalEntryType.ACTION_COMPLETED if success else JournalEntryType.ACTION_FAILED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            timezone=datetime.now(timezone.utc).astimezone().tzinfo.tzname(datetime.now()),
            run_id=self.run_id,
            feature_id=idempotence_key.feature_id,
            task_id=idempotence_key.task_id,
            action=idempotence_key.action,
            idempotence_key=idempotence_key,
            data=result or {},
        )
        self.write_journal_entry(entry)

    def acquire_lock(
        self,
        lock_type: str,
        locked_entity_id: str | None = None,
        task_id: str | None = None,
    ) -> ProductLock:
        """Acquire a product, feature, or task lock.

        Raises ProductLockError if a conflicting lock already exists.
        With task_id, prevents concurrent writes to the same task artefacts (AC-R13-10).
        """
        locks = self.list_locks()

        # Construct full entity key including task if specified (AC-R13-10)
        full_entity_key = locked_entity_id
        if task_id:
            full_entity_key = f"{locked_entity_id or 'default'}:{task_id}"

        for existing_lock in locks:
            if existing_lock.lock_type != lock_type:
                continue
            # Check if this lock applies to the same entity using full_entity_key (AC-R13-10)
            existing_key = existing_lock.full_entity_key or existing_lock.locked_entity_id
            if full_entity_key != existing_key:
                continue
            if existing_lock.owner_run_id == self.run_id:
                continue

            if not existing_lock.is_expired():
                entity_desc = f"{locked_entity_id or 'product'}"
                if task_id:
                    entity_desc += f" (task {task_id})"
                raise ProductLockError(
                    f"Cannot acquire {lock_type} lock for {entity_desc}: "
                    f"already locked by {existing_lock.owner_run_id} (pid={existing_lock.owner_pid})"
                )
            else:
                try:
                    self.release_lock(existing_lock.lock_id, reason="Lock expired", force_expired=True)
                except ProductLockError as exc:
                    entity_desc = f"{locked_entity_id or 'product'}"
                    if task_id:
                        entity_desc += f" (task {task_id})"
                    raise ProductLockError(
                        f"Cannot acquire {lock_type} lock for {entity_desc}: "
                        f"expired lock {existing_lock.lock_id} cannot be reclaimed safely ({exc})"
                    ) from exc

        lock_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        lock = ProductLock(
            lock_id=lock_id,
            lock_type=lock_type,
            owner_run_id=self.run_id,
            owner_pid=os.getpid(),
            owner_logical=f"autodev-{self.run_id}",
            owner_host=socket.gethostname(),
            acquired_at=now,
            heartbeat_at=now,
            locked_entity_id=locked_entity_id,
            full_entity_key=full_entity_key,
        )

        lock_path = self.get_locks_dir() / f"{lock_id}.json"
        lock_path.write_text(
            json.dumps(lock.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._held_locks[lock_id] = lock

        entry = JournalEntry(
            entry_id=str(uuid4()),
            entry_type=JournalEntryType.LOCK_ACQUIRED,
            timestamp=now,
            timezone=lock.acquired_at.split("+")[1] if "+" in lock.acquired_at else "UTC",
            run_id=self.run_id,
            data={
                "lock_id": lock_id,
                "lock_type": lock_type,
                "locked_entity_id": locked_entity_id,
                "task_id": task_id,
                "full_entity_key": full_entity_key,
            },
        )
        with self.lock_audit_writes():
            self.write_journal_entry(entry)

        return lock

    def release_lock(self, lock_id: str, reason: str | None = None, force_expired: bool = False) -> None:
        """Release a lock after verifying ownership (AC-R13-11).

        Searches globally for locks to enable cross-run release of expired locks.

        Args:
            lock_id: ID of lock to release
            reason: Optional reason for release
            force_expired: If True, allow releasing locks that are expired, even if not owned
        """
        lock_path = self._resolve_lock_path(lock_id)
        if lock_path is None:
            raise ProductLockError(f"Lock not found: {lock_id}")

        try:
            expected_contents = lock_path.read_text(encoding="utf-8")
            lock_data = json.loads(expected_contents)
            lock = ProductLock.from_dict(lock_data)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ProductLockError(f"Failed to read lock {lock_id}: {exc}") from exc

        verification = {
            "verification_status": "owned_by_requester",
            "owner_run_id": lock.owner_run_id,
            "owner_logical": lock.owner_logical,
            "owner_pid": lock.owner_pid,
            "owner_host": lock.owner_host,
            "heartbeat_age_seconds": self._heartbeat_age_seconds(lock),
            "checks": ["ownership"],
            "owner_active": None,
        }

        if lock.owner_run_id != self.run_id:
            if not force_expired:
                raise ProductLockError(
                    f"Cannot release lock {lock_id}: owned by {lock.owner_run_id}, not {self.run_id}"
                )
            if not lock.is_expired():
                raise ProductLockError(
                    f"Cannot release lock {lock_id}: owned by {lock.owner_run_id}, not {self.run_id}"
                )
            verification = self._verify_expired_lock_owner(lock)
            if verification["verification_status"] == "active":
                raise ProductLockError(
                    f"Cannot release lock {lock_id}: expired heartbeat but owner is still active"
                )
            if verification["verification_status"] != "inactive":
                raise ProductLockError(
                    f"Cannot release lock {lock_id}: owner cannot be verified reliably"
                )

        self._delete_lock_file_if_unchanged(lock_path, expected_contents)
        self._held_locks.pop(lock_id, None)

        entry = JournalEntry(
            entry_id=str(uuid4()),
            entry_type=JournalEntryType.LOCK_RELEASED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            timezone=self._timezone_name(),
            run_id=self.run_id,
            data={
                "lock_id": lock_id,
                "lock_type": lock.lock_type,
                "reason": reason,
                "forced_expired": force_expired,
                "owner_verification": verification,
            },
        )
        with self.lock_audit_writes():
            self.write_journal_entry(entry)

    def list_locks(self, filter_entity_id: str | None = None) -> list[ProductLock]:
        """List all active locks for concurrent access detection (AC-R13-10).
        
        Checks locks from this run and all other runs to enable cross-run conflict detection.
        Locks are stored per-run but visible globally for conflict detection.
        """
        locks = []
        
        # Get locks from this run
        my_locks_dir = self.get_locks_dir()
        if my_locks_dir.exists():
            for lock_file in my_locks_dir.glob("*.json"):
                locks.extend(self._read_lock_file(lock_file, filter_entity_id))
        
        # Get locks from other runs for conflict detection (AC-R13-10)
        for locks_dir in self._get_all_locks_dirs():
            if locks_dir == my_locks_dir:
                continue
            if locks_dir.exists():
                for lock_file in locks_dir.glob("*.json"):
                    locks.extend(self._read_lock_file(lock_file, filter_entity_id))
        
        return locks
    
    def _read_lock_file(self, lock_file: Path, filter_entity_id: str | None = None) -> list[ProductLock]:
        """Helper to read a single lock file."""
        try:
            lock_data = json.loads(lock_file.read_text(encoding="utf-8"))
            lock = ProductLock.from_dict(lock_data)
            if filter_entity_id and lock.locked_entity_id != filter_entity_id:
                return []
            return [lock]
        except (json.JSONDecodeError, ValueError):
            return []

    def update_lock_heartbeat(self, lock_id: str) -> None:
        """Update lock heartbeat to keep it alive."""
        lock_path = self.get_locks_dir() / f"{lock_id}.json"

        if not lock_path.exists():
            raise ProductLockError(f"Lock not found: {lock_id}")

        try:
            lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
            lock = ProductLock.from_dict(lock_data)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ProductLockError(f"Failed to read lock {lock_id}: {exc}") from exc

        if lock.owner_run_id != self.run_id:
            raise ProductLockError(
                f"Cannot update lock {lock_id}: owned by {lock.owner_run_id}, not {self.run_id}"
            )

        lock.update_heartbeat()
        lock_path.write_text(
            json.dumps(lock.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._held_locks[lock_id] = lock

    def write_checkpoint(self, checkpoint_data: dict[str, Any]) -> None:
        """Write ProductGraph checkpoint (separate from feature checkpoints)."""
        self._assert_write_allowed("checkpoint.json")
        checkpoint_path = self.get_checkpoints_path()
        checkpoint_data["checkpoint_timestamp"] = datetime.now(timezone.utc).isoformat()
        checkpoint_path.write_text(
            json.dumps(checkpoint_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def read_checkpoint(self) -> dict[str, Any] | None:
        """Read ProductGraph checkpoint."""
        checkpoint_path = self.get_checkpoints_path()
        if not checkpoint_path.exists():
            return None
        try:
            return json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProductStateError(f"Failed to read checkpoint from {checkpoint_path}: {exc}") from exc

    def _resolve_lock_path(self, lock_id: str) -> Path | None:
        lock_path = self.get_locks_dir() / f"{lock_id}.json"
        if lock_path.exists():
            return lock_path
        for locks_dir in self._get_all_locks_dirs():
            candidate_path = locks_dir / f"{lock_id}.json"
            if candidate_path.exists():
                return candidate_path
        return None

    def _list_namespace_artifacts(self, exclude: set[str] | None = None) -> list[str]:
        excluded = exclude or set()
        artifacts: list[str] = []
        for child in sorted(self.run_namespace.iterdir(), key=lambda path: path.name):
            if child.name in excluded:
                continue
            if child.is_dir():
                if any(child.iterdir()):
                    artifacts.append(child.name)
            else:
                artifacts.append(child.name)
        return artifacts

    def _verify_expired_lock_owner(self, lock: ProductLock) -> dict[str, Any]:
        verification = {
            "verification_status": "unverifiable",
            "owner_run_id": lock.owner_run_id,
            "owner_logical": lock.owner_logical,
            "owner_pid": lock.owner_pid,
            "owner_host": lock.owner_host,
            "heartbeat_age_seconds": self._heartbeat_age_seconds(lock),
            "checks": ["heartbeat", "pid", "host"],
            "owner_active": None,
        }

        current_host = socket.gethostname()
        if not lock.owner_host:
            verification["reason"] = "owner_host_missing"
            return verification
        if lock.owner_host != current_host:
            verification["reason"] = "owner_host_mismatch"
            return verification
        if not isinstance(lock.owner_pid, int) or lock.owner_pid <= 0:
            verification["reason"] = "owner_pid_invalid"
            return verification

        try:
            os.kill(lock.owner_pid, 0)
        except ProcessLookupError:
            verification["verification_status"] = "inactive"
            verification["owner_active"] = False
            verification["reason"] = "pid_not_found"
            return verification
        except PermissionError:
            verification["verification_status"] = "active"
            verification["owner_active"] = True
            verification["reason"] = "pid_exists_permission_denied"
            return verification
        except OSError as exc:
            verification["reason"] = f"os_error:{exc.errno}"
            return verification

        verification["verification_status"] = "active"
        verification["owner_active"] = True
        verification["reason"] = "pid_alive"
        return verification

    def _delete_lock_file_if_unchanged(self, lock_path: Path, expected_contents: str) -> None:
        if not lock_path.exists():
            raise ProductLockError(f"Lock {lock_path.stem} changed during verification")
        current_contents = lock_path.read_text(encoding="utf-8")
        if current_contents != expected_contents:
            raise ProductLockError(f"Lock {lock_path.stem} changed during verification")
        lock_path.unlink()

    def _heartbeat_age_seconds(self, lock: ProductLock) -> float | None:
        try:
            last_beat = datetime.fromisoformat(lock.heartbeat_at.replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError):
            return None
        return (datetime.now(timezone.utc) - last_beat).total_seconds()

    def _timezone_name(self) -> str:
        tzinfo = datetime.now(timezone.utc).astimezone().tzinfo
        return tzinfo.tzname(datetime.now()) if tzinfo is not None else "UTC"

    @contextmanager
    def bootstrap_writes(self):
        """Allow one strictly bounded bootstrap phase for namespace materialization."""
        self._bootstrap_write_depth += 1
        try:
            yield
        finally:
            self._bootstrap_write_depth -= 1

    @contextmanager
    def lock_audit_writes(self):
        """Allow lock acquisition/release journaling without circular lock dependencies."""
        self._lock_audit_depth += 1
        try:
            yield
        finally:
            self._lock_audit_depth -= 1

    def has_active_owned_lock(
        self,
        lock_type: str | None = None,
        locked_entity_id: str | None = None,
        task_id: str | None = None,
    ) -> bool:
        """Return True when this process still holds a valid owned lock."""
        for lock in self._held_locks.values():
            if lock_type is not None and lock.lock_type != lock_type:
                continue
            if locked_entity_id is not None and lock.locked_entity_id != locked_entity_id:
                continue
            expected_full_key = None
            if task_id is not None:
                expected_full_key = f"{locked_entity_id or 'default'}:{task_id}"
            if expected_full_key is not None and lock.full_entity_key != expected_full_key:
                continue
            if self._validate_held_lock(lock) is not None:
                return True
        return False

    def _assert_write_allowed(self, target_name: str) -> None:
        if self._bootstrap_write_depth > 0:
            return
        if target_name == "journal.jsonl" and self._lock_audit_depth > 0:
            return
        if self.has_active_owned_lock():
            return
        raise ProductLockError(
            f"Cannot write {target_name}: no active owned lock is currently held by "
            f"run {self.run_id} pid={os.getpid()}"
        )

    def _validate_held_lock(self, lock: ProductLock) -> ProductLock | None:
        lock_path = self._resolve_lock_path(lock.lock_id)
        if lock_path is None or not lock_path.exists():
            return None
        try:
            current_lock = ProductLock.from_dict(json.loads(lock_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, ValueError):
            return None
        if current_lock.lock_id != lock.lock_id:
            return None
        if current_lock.owner_run_id != self.run_id:
            return None
        if current_lock.owner_pid != os.getpid():
            return None
        if current_lock.owner_logical != lock.owner_logical:
            return None
        if current_lock.owner_host != lock.owner_host:
            return None
        if current_lock.is_expired():
            return None
        return current_lock

    def get_patches_inventory_path(self) -> Path:
        """Path to patch inventory JSONL file.

        AC-R22-6: Sauvegarder les patchs produits par tentative.
        """
        patches_dir = self.run_namespace / "patches"
        patches_dir.mkdir(parents=True, exist_ok=True)
        return patches_dir / "inventory.jsonl"

    def save_patch(
        self,
        paths_affected: list[str],
        patch_content: str,
        reason: str,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Sauvegarder un patch dans l'inventaire avant restauration.

        AC-R22-6: Le superviseur conserve un inventaire des patchs, blobs ou diffs
        produits par tentative avant toute restauration ou reprise.
        """
        patch_id = f"patch-{uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)

        entry = PatchInventoryEntry(
            patch_id=patch_id,
            timestamp=now.isoformat(),
            timezone=now.astimezone().tzname() or "UTC",
            run_id=self.run_id,
            task_id=task_id,
            paths_affected=paths_affected,
            patch_content=patch_content,
            reason=reason,
            metadata=metadata or {},
        )

        inventory_path = self.get_patches_inventory_path()
        with open(inventory_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

        return patch_id

    def get_patches_inventory(self) -> list[PatchInventoryEntry]:
        """Récupérer l'inventaire des patchs sauvegardés.

        AC-R22-9: Produit des preuves vérifiables.
        """
        inventory_path = self.get_patches_inventory_path()
        if not inventory_path.exists():
            return []

        patches: list[PatchInventoryEntry] = []
        try:
            with open(inventory_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        patches.append(PatchInventoryEntry.from_dict(data))
                    except (json.JSONDecodeError, ValueError):
                        continue
        except (FileNotFoundError, IOError):
            return []

        return patches
