from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from autodev.product_incidents import IncidentRepeatability, IncidentScope, IncidentSeverity, ProductIncident
from autodev.product_plan import ProductPlan
from autodev.product_state import (
    IdempotenceKey,
    JournalEntry,
    JournalEntryType,
    ProductLockError,
    ProductRunState,
    ProductStateError,
    ProductStateManager,
)
from autodev.provider_incidents import ProviderIncidentEvent

class ProductRuntimeError(RuntimeError):
    """Error during product runtime execution."""

class StateReconstructionIncident(ProductIncident):
    """Incident detected during state reconstruction."""

    def __init__(self, code: str, reason: str, evidence: list[str] | None = None):
        super().__init__(
            code=code,
            severity=IncidentSeverity.HIGH,
            scope=IncidentScope.GIT_STATE,
            proofs=evidence or [reason],
            repeatability=IncidentRepeatability.ALWAYS,
            recommended_action=f"Investigate and manually resolve: {reason}",
            retryable=False,
            deferrable=False,
            correctable_under_supervision=True,
            terminal=False,
            title=f"State reconstruction incident: {code}",
            description=reason,
        )

@dataclass
class DurableDecision:
    """Durable decision necessary for reproductibility."""

    decision_id: str
    product_key: str
    run_id: str
    feature_id: str
    task_id: str | None
    decision_type: str
    content: dict[str, Any]
    created_at: str
    approved_at: str | None = None
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "decision_id": self.decision_id,
            "product_key": self.product_key,
            "run_id": self.run_id,
            "feature_id": self.feature_id,
            "task_id": self.task_id,
            "decision_type": self.decision_type,
            "content": self.content,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "status": self.status,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DurableDecision:
        """Create from dictionary."""
        return DurableDecision(
            decision_id=data["decision_id"],
            product_key=data.get("product_key") or data["run_id"],
            run_id=data["run_id"],
            feature_id=data["feature_id"],
            task_id=data.get("task_id"),
            decision_type=data["decision_type"],
            content=data["content"],
            created_at=data["created_at"],
            approved_at=data.get("approved_at"),
            status=data.get("status", "pending"),
        )

class DurableDecisionStore:
    """Persistent store for durable decisions outside ephemeral artifacts."""

    def __init__(self, repo_root: Path, product_key: str):
        """Initialize durable decision store outside ephemeral run artifacts."""
        self.repo_root = repo_root
        self.product_key = product_key
        store_dir_name = self._store_dir_name(product_key)
        self.store_path = (
            repo_root
            / ".autodev"
            / "decisions"
            / "products"
            / store_dir_name
            / "decisions.jsonl"
        )
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _store_dir_name(product_key: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", product_key).strip("_") or "product"
        suffix = hashlib.sha256(product_key.encode("utf-8")).hexdigest()[:12]
        return f"{slug}-{suffix}"

    def record_decision(self, decision: DurableDecision) -> None:
        """Record a durable decision."""
        decision_line = json.dumps(decision.to_dict(), ensure_ascii=False) + "\n"
        with open(self.store_path, "a", encoding="utf-8") as f:
            f.write(decision_line)

    def read_all_decisions(self) -> list[DurableDecision]:
        """Read all recorded decisions."""
        decisions = []
        if not self.store_path.exists():
            return decisions

        try:
            with open(self.store_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            decisions.append(DurableDecision.from_dict(data))
                        except (json.JSONDecodeError, ValueError) as exc:
                            raise ProductRuntimeError(
                                f"Failed to parse decision entry: {line}: {exc}"
                            ) from exc
        except IOError as exc:
            raise ProductRuntimeError(f"Failed to read decisions from {self.store_path}: {exc}") from exc

        return decisions

    def get_decisions_for_feature(self, feature_id: str) -> list[DurableDecision]:
        """Get all decisions for a specific feature."""
        return [d for d in self.read_all_decisions() if d.feature_id == feature_id]

    def get_approved_decisions(self) -> list[DurableDecision]:
        """Get all approved decisions."""
        return [d for d in self.read_all_decisions() if d.status == "approved"]

    def approve_decision(self, decision_id: str) -> None:
        """Approve a pending decision."""
        decisions = self.read_all_decisions()
        updated_decisions = []
        found = False

        for decision in decisions:
            if decision.decision_id == decision_id:
                decision.status = "approved"
                decision.approved_at = datetime.now(timezone.utc).isoformat()
                found = True
            updated_decisions.append(decision)

        if not found:
            raise ProductRuntimeError(f"Decision not found: {decision_id}")

        self._rewrite_store(updated_decisions)

    def _rewrite_store(self, decisions: list[DurableDecision]) -> None:
        """Rewrite the entire decision store (used for updates)."""
        self.store_path.write_text("")
        for decision in decisions:
            self.record_decision(decision)

@dataclass
class ProviderWaitingState:
    """Persistent state for provider incident waiting (AC-R14-1, R21-6)."""

    incident: ProviderIncidentEvent
    recorded_at: str
    feature_id: str | None = None
    task_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "incident": self.incident.to_dict(),
            "recorded_at": self.recorded_at,
            "feature_id": self.feature_id,
            "task_id": self.task_id,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ProviderWaitingState":
        """Deserialize from dictionary."""
        return ProviderWaitingState(
            incident=ProviderIncidentEvent.from_dict(data["incident"]),
            recorded_at=data["recorded_at"],
            feature_id=data.get("feature_id"),
            task_id=data.get("task_id"),
        )


@dataclass
class StateReconstructionResult:
    """Result of state reconstruction."""

    run_id: str
    is_clean: bool
    incidents: list[StateReconstructionIncident]
    divergences: list[str]
    state: ProductRunState

    def has_critical_incidents(self) -> bool:
        """Check if reconstruction found critical issues."""
        return any(incident.severity.value == "critical" for incident in self.incidents)

ResumeCallback = Callable[[dict[str, Any]], bool]


class ProductRuntime:
    """Manages runtime execution and state of a product run."""

    def __init__(self, repo_root: Path, run_id: str, clock: Callable[[], datetime] | None = None):
        """Initialize product runtime."""
        self.repo_root = repo_root
        self.run_id = run_id
        self.state_manager = ProductStateManager(repo_root, run_id)
        self.decision_store: DurableDecisionStore | None = None
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ProductRuntimeError("Runtime clock must return a timezone-aware datetime")
        return now

    @classmethod
    def create(cls, repo_root: Path, clock: Callable[[], datetime] | None = None) -> "ProductRuntime":
        """Create a runtime with a globally unique product run identifier."""
        attempts = 0
        while attempts < 32:
            candidate = cls._generate_candidate_run_id()
            namespace = repo_root / ".autodev" / "runs" / "products" / candidate
            if not namespace.exists():
                return cls(repo_root, candidate, clock=clock)
            attempts += 1
        raise ProductRuntimeError("Unable to generate a unique product run identifier")

    @classmethod
    def _generate_candidate_run_id(cls) -> str:
        return f"product-run-{uuid4().hex[:12]}"

    def record_git_evidence(
        self,
        *,
        feature_id: str | None = None,
        branch: str | None = None,
        current_branch: str | None = None,
        base_commit: str | None = None,
        current_commit: str | None = None,
        integrated_commit: str | None = None,
        worktree: str | None = None,
        current_worktree: str | None = None,
    ) -> None:
        """Persist structured Git evidence supplied by the caller.

        This runtime records evidence only; it does not query Git itself.
        Product-scope evidence requires an active product lock. Feature-scope
        evidence requires an active lock for the targeted feature.
        """
        evidence_updates = self._normalize_git_evidence_updates(
            branch=branch,
            current_branch=current_branch,
            base_commit=base_commit,
            current_commit=current_commit,
            integrated_commit=integrated_commit,
            worktree=worktree,
            current_worktree=current_worktree,
        )
        if not evidence_updates:
            raise ProductRuntimeError("record_git_evidence requires at least one non-empty evidence field")

        lock_type = "product" if feature_id is None else "feature"
        locked_entity_id = feature_id
        scope = "product" if feature_id is None else "feature"
        self._require_active_transition_lock(lock_type=lock_type, locked_entity_id=locked_entity_id)

        current_state = self.state_manager.read_state("", "")
        if feature_id is None:
            current_values = {
                field_name: getattr(current_state, state_key)
                for field_name, state_key in self._product_git_evidence_field_map().items()
            }
        else:
            current_values = {
                field_name: current_state.feature_states.get(feature_id, {}).get(field_name)
                for field_name in self._feature_git_evidence_fields()
            }

        changed_fields = {
            field_name: value
            for field_name, value in evidence_updates.items()
            if current_values.get(field_name) != value
        }
        if not changed_fields:
            return

        def persist() -> dict[str, Any]:
            state = self.state_manager.read_state("", "")
            if feature_id is None:
                for field_name, value in changed_fields.items():
                    setattr(state, self._product_git_evidence_field_map()[field_name], value)
            else:
                feature_state = dict(state.feature_states.get(feature_id, {}))
                feature_state.update(changed_fields)
                state.feature_states[feature_id] = feature_state
            self.state_manager.write_state(state)
            return {
                "scope": scope,
                "feature_id": feature_id,
                "updated_fields": sorted(changed_fields),
                "evidence": dict(changed_fields),
            }

        self._run_logged_transition(
            action="record_git_evidence",
            lock_type=lock_type,
            locked_entity_id=locked_entity_id,
            feature_id=feature_id,
            attempt=1,
            mutation=persist,
        )

    def register_feature_graph_id(self, feature_id: str, graph_id: str) -> None:
        """Register a persisted feature graph ID with cross-run uniqueness guarantees."""
        state = self.state_manager.read_state("", "")

        if feature_id in state.feature_graph_ids:
            if state.feature_graph_ids[feature_id] == graph_id:
                return
            raise ProductRuntimeError(
                f"Feature {feature_id} already registered with different graph ID: "
                f"{state.feature_graph_ids[feature_id]} vs {graph_id}"
            )

        if state.product_graph_id == graph_id:
            raise ProductRuntimeError(
                f"Graph ID {graph_id} is reserved for the product graph in run {self.run_id}"
            )

        if graph_id in state.feature_graph_ids.values():
            raise ProductRuntimeError(
                f"Graph ID {graph_id} already used in this run for another feature"
            )

        graph_lock = self.state_manager.acquire_lock("feature-graph", locked_entity_id=graph_id)
        try:
            def register_graph() -> dict[str, Any]:
                conflicting_run = self._find_graph_id_owner(graph_id, exclude_run_id=self.run_id)
                if conflicting_run is not None:
                    raise ProductRuntimeError(
                        f"Graph ID {graph_id} already used by run {conflicting_run}"
                    )

                current_state = self.state_manager.read_state("", "")
                current_state.feature_graph_ids[feature_id] = graph_id
                self.state_manager.write_state(current_state)
                return {"feature_id": feature_id, "graph_id": graph_id}

            self._run_logged_transition(
                action="register_feature_graph_id",
                lock_type="feature",
                locked_entity_id=feature_id,
                feature_id=feature_id,
                attempt=1,
                mutation=register_graph,
            )
        finally:
            self.state_manager.release_lock(
                graph_lock.lock_id,
                reason=f"Feature graph registration completed for {graph_id}",
            )

    def attach_child_artifacts(self, parent_id: str, child_artifact_paths: list[str]) -> None:
        """Attach child artifacts to the product run without moving legacy artifacts."""
        with self._managed_lock("feature", locked_entity_id=parent_id):
            state = self.state_manager.read_state("", "")
            feature_state = state.feature_states.setdefault(parent_id, {})
            existing_artifacts = feature_state.get("child_artifacts", [])
            existing_by_path = {
                artifact.get("legacy_path", artifact.get("path")): artifact
                for artifact in existing_artifacts
            }

            normalized_artifacts = []
            for artifact_path in child_artifact_paths:
                artifact_file = self.repo_root / artifact_path
                if not artifact_file.exists():
                    raise ProductRuntimeError(f"Missing required child artifact: {artifact_path}")

                digest = hashlib.sha256(artifact_file.read_bytes()).hexdigest()
                normalized_artifacts.append(
                    {
                        "path": artifact_path,
                        "legacy_path": artifact_path,
                        "absolute_path": str(artifact_file),
                        "required": True,
                        "exists": True,
                        "recorded_digest": digest,
                        "current_digest": digest,
                    }
                )

            normalized_by_path = {
                artifact["legacy_path"]: artifact for artifact in normalized_artifacts
            }
            if existing_by_path == normalized_by_path:
                return

            def attach() -> dict[str, Any]:
                current_state = self.state_manager.read_state("", "")
                current_feature_state = current_state.feature_states.setdefault(parent_id, {})
                current_feature_state["attached_artifacts"] = child_artifact_paths
                current_feature_state["child_artifacts"] = normalized_artifacts
                current_feature_state["required_child_artifacts"] = [
                    dict(artifact) for artifact in normalized_artifacts
                ]
                current_state.feature_states[parent_id] = current_feature_state
                self.state_manager.write_state(current_state)
                return {
                    "action": "attach_child_artifacts",
                    "parent_id": parent_id,
                    "artifact_count": len(normalized_artifacts),
                    "artifacts": [artifact["legacy_path"] for artifact in normalized_artifacts],
                }

            self._run_logged_transition(
                action="attach_child_artifacts",
                lock_type="feature",
                locked_entity_id=parent_id,
                feature_id=parent_id,
                attempt=1,
                mutation=attach,
            )

    def initialize_run(
        self,
        plan_id: str,
        plan_hash: str,
        plan: ProductPlan | dict[str, Any] | None = None,
    ) -> ProductRunState:
        """Initialize a new product run with distinct LangGraph identifiers (AC-R13-1, AC-R13-6)."""
        normalized_plan = self._normalize_plan(plan, plan_id=plan_id, plan_hash=plan_hash)
        state_path = self.state_manager.get_state_path()
        if state_path.exists():
            state = self.state_manager.read_state(plan_id, plan_hash)
            if state.plan_id != plan_id or state.plan_hash != plan_hash:
                raise ProductRuntimeError(
                    f"Run {self.run_id} is already initialized for {state.plan_id}/{state.plan_hash}"
                )
            self._verify_resume_plan_snapshot(state=state, current_plan=normalized_plan)
            try:
                claim, _ = self.state_manager.reserve_run_namespace(
                    plan_id=plan_id,
                    plan_hash=plan_hash,
                )
            except ProductStateError as exc:
                raise ProductRuntimeError(str(exc)) from exc
            if claim.get("plan_id") not in (None, plan_id) or claim.get("plan_hash") not in (None, plan_hash):
                raise ProductRuntimeError(
                    f"Run {self.run_id} is already initialized for "
                    f"{claim.get('plan_id')}/{claim.get('plan_hash')}"
                )
            self._configure_decision_store(state.product_key or self._derive_product_key(plan_id))
            with self._managed_lock("product"):
                state = self._sync_durable_decisions_to_state(state)
            self.state_manager.ensure_run_artifacts(state, self._initial_checkpoint_data(state))
            return state

        try:
            claim, claim_created = self.state_manager.reserve_run_namespace(
                plan_id=plan_id,
                plan_hash=plan_hash,
            )
        except ProductStateError as exc:
            if state_path.exists():
                existing_state = self.state_manager.read_state("", "")
                if existing_state.plan_id != plan_id or existing_state.plan_hash != plan_hash:
                    raise ProductRuntimeError(
                        f"Run {self.run_id} is already initialized for "
                        f"{existing_state.plan_id}/{existing_state.plan_hash}"
                    ) from exc
            raise ProductRuntimeError(str(exc)) from exc
        if not claim_created:
            raise ProductRuntimeError(
                f"Product run namespace collision for {self.run_id}: "
                f"run_id already reserved without resumable state proof"
            )

        product_key = self._derive_product_key(plan_id)
        product_graph_id = f"product-{self.run_id}-{str(uuid4())[:12]}"
        state = ProductRunState(
            run_id=self.run_id,
            plan_id=plan_id,
            product_key=product_key,
            schema_version="1.0",
            plan_hash=plan_hash,
            started_at=datetime.now(timezone.utc).isoformat(),
            run_namespace=self.state_manager.run_namespace,
            plan_snapshot=normalized_plan or {},
            product_graph_id=product_graph_id,
        )
        self._configure_decision_store(product_key)
        with self.state_manager.bootstrap_writes():
            state = self._sync_durable_decisions_to_state(state)
        self.state_manager.ensure_run_artifacts(state, self._initial_checkpoint_data(state))
        return state

    def reconstruct_state(
        self,
        plan_id: str,
        plan_hash: str,
        plan: ProductPlan | dict[str, Any] | None = None,
    ) -> StateReconstructionResult:
        """Reconstruct product run state from persistent artifacts.

        Compares plan, persisted state, checkpoints, branches, commits, worktrees,
        validations and artifacts without trusting narrative reports.
        """
        incidents: list[StateReconstructionIncident] = []
        divergences: list[str] = []
        normalized_plan = self._normalize_plan(plan, plan_id=plan_id, plan_hash=plan_hash)

        try:
            state = self.state_manager.read_state(plan_id, plan_hash)
        except ProductStateError as exc:
            incidents.append(
                StateReconstructionIncident(
                    code="STATE_READ_ERROR",
                    reason=f"Failed to read persisted state: {exc}",
                    evidence=[str(exc)],
                )
            )
            state = ProductRunState(
                run_id=self.run_id,
                plan_id=plan_id,
                product_key=self._derive_product_key(plan_id),
                schema_version="1.0",
                plan_hash=plan_hash,
                started_at=datetime.now(timezone.utc).isoformat(),
                run_namespace=self.state_manager.run_namespace,
            )

        self._configure_decision_store(state.product_key or self._derive_product_key(plan_id))
        with self._managed_lock("product"):
            state = self._sync_durable_decisions_to_state(state)

        journal_entries = []
        try:
            journal_entries = self.state_manager.read_journal()
        except ProductStateError as exc:
            incidents.append(
                StateReconstructionIncident(
                    code="JOURNAL_READ_ERROR",
                    reason=f"Failed to read journal: {exc}",
                    evidence=[str(exc)],
                )
            )

        if state.plan_hash != plan_hash:
            divergences.append(
                f"Plan hash mismatch: persisted={state.plan_hash}, current={plan_hash}"
            )
            incidents.append(
                StateReconstructionIncident(
                    code="PLAN_HASH_DIVERGENCE",
                    reason="Plan hash divergence detected",
                    evidence=[divergences[-1]],
                )
            )

        if normalized_plan and state.plan_snapshot:
            self._compare_plan_snapshot(
                persisted_snapshot=state.plan_snapshot,
                current_snapshot=normalized_plan,
                divergences=divergences,
                incidents=incidents,
            )
        elif normalized_plan and not state.plan_snapshot:
            divergences.append("Missing immutable plan snapshot proof for this run")
            incidents.append(
                StateReconstructionIncident(
                    code="MISSING_PLAN_SNAPSHOT_PROOF",
                    reason="Persisted run state has no immutable plan snapshot proof",
                    evidence=[divergences[-1]],
                )
            )

        checkpoint = None
        try:
            checkpoint = self.state_manager.read_checkpoint()
        except ProductStateError:
            pass

        if not checkpoint and state.status == "COMPLETED":
            divergences.append("No checkpoint found for completed state")
            incidents.append(
                StateReconstructionIncident(
                    code="MISSING_COMPLETION_CHECKPOINT",
                    reason="No checkpoint found for a completed run state",
                    evidence=[divergences[-1]],
                )
            )
        elif checkpoint and checkpoint.get("plan_hash") not in (None, plan_hash):
            divergences.append(
                f"Checkpoint plan hash mismatch: checkpoint={checkpoint.get('plan_hash')}, current={plan_hash}"
            )
            incidents.append(
                StateReconstructionIncident(
                    code="CHECKPOINT_PLAN_HASH_DIVERGENCE",
                    reason="Product checkpoint does not match current plan hash",
                    evidence=[divergences[-1]],
                )
            )

        if not state.product_graph_id:
            divergences.append("No product graph ID assigned to this run")
            incidents.append(
                StateReconstructionIncident(
                    code="MISSING_PRODUCT_GRAPH_ID",
                    reason="ProductGraph identifier not registered",
                    evidence=[divergences[-1]],
                )
            )

        active_locks = []
        try:
            active_locks = self.state_manager.list_locks()
        except ProductStateError as exc:
            incidents.append(
                StateReconstructionIncident(
                    code="LOCK_READ_ERROR",
                    reason=f"Failed to read locks: {exc}",
                    evidence=[str(exc)],
                )
            )

        for lock in active_locks:
            if lock.is_expired():
                divergences.append(f"Expired lock detected: {lock.lock_id}")
                incidents.append(
                    StateReconstructionIncident(
                        code="EXPIRED_LOCK_DETECTED",
                        reason=f"Lock {lock.lock_id} has expired but still exists",
                        evidence=[divergences[-1]],
                    )
                )

        is_clean = len(incidents) == 0 and len(divergences) == 0

        # Compare Git state: commits, branches, worktrees
        if state.base_commit or state.current_commit or state.integrated_commit:
            if state.base_commit and state.current_commit:
                if state.base_commit != state.current_commit:
                    divergences.append(
                        f"Base commit divergence: expected={state.base_commit}, current={state.current_commit}"
                    )
                    incidents.append(
                        StateReconstructionIncident(
                            code="BASE_COMMIT_DIVERGENCE",
                            reason="Base commit does not match current commit",
                            evidence=[divergences[-1]],
                        )
                    )
            if state.integrated_commit and state.current_commit:
                if state.integrated_commit != state.current_commit:
                    divergences.append(
                        f"Integrated commit divergence: expected={state.integrated_commit}, current={state.current_commit}"
                    )
                    incidents.append(
                        StateReconstructionIncident(
                            code="INTEGRATED_COMMIT_DIVERGENCE",
                            reason="Integrated commit does not match current commit",
                            evidence=[divergences[-1]],
                        )
                    )

        if state.product_branch and state.current_product_branch and state.product_branch != state.current_product_branch:
            divergences.append(
                f"Product branch divergence: expected={state.product_branch}, current={state.current_product_branch}"
            )
            incidents.append(
                StateReconstructionIncident(
                    code="PRODUCT_BRANCH_DIVERGENCE",
                    reason="Product branch does not match persisted proof",
                    evidence=[divergences[-1]],
                )
            )

        if normalized_plan:
            expected_branch = normalized_plan.get("integration_branch")
            if expected_branch and state.product_branch and state.product_branch != expected_branch:
                divergences.append(
                    f"Plan integration branch divergence: expected={expected_branch}, persisted={state.product_branch}"
                )
                incidents.append(
                    StateReconstructionIncident(
                        code="PLAN_INTEGRATION_BRANCH_DIVERGENCE",
                        reason="Current plan integration branch does not match persisted product branch",
                        evidence=[divergences[-1]],
                    )
                )

        if state.product_worktree and state.current_product_worktree and state.product_worktree != state.current_product_worktree:
            divergences.append(
                f"Product worktree divergence: expected={state.product_worktree}, current={state.current_product_worktree}"
            )
            incidents.append(
                StateReconstructionIncident(
                    code="PRODUCT_WORKTREE_DIVERGENCE",
                    reason="Product worktree does not match persisted proof",
                    evidence=[divergences[-1]],
                )
            )

        for feature_id, feature_state in state.feature_states.items():
            feature_status = feature_state.get("status")
            if state.status == "COMPLETED" and feature_status and feature_status != "COMPLETED":
                divergences.append(
                    f"Feature status divergence for {feature_id}: run completed but feature status is {feature_status}"
                )
                incidents.append(
                    StateReconstructionIncident(
                        code="FEATURE_STATUS_DIVERGENCE",
                        reason=f"Feature {feature_id} is not completed in persisted state",
                        evidence=[divergences[-1]],
                    )
                )

            expected_branch = feature_state.get("branch")
            current_branch = feature_state.get("current_branch")
            if expected_branch and current_branch and expected_branch != current_branch:
                divergences.append(
                    f"Feature branch divergence for {feature_id}: expected={expected_branch}, current={current_branch}"
                )
                incidents.append(
                    StateReconstructionIncident(
                        code="FEATURE_BRANCH_DIVERGENCE",
                        reason=f"Feature {feature_id} branch proof diverged",
                        evidence=[divergences[-1]],
                    )
                )

            expected_worktree = feature_state.get("worktree")
            current_worktree = feature_state.get("current_worktree")
            if expected_worktree and current_worktree and expected_worktree != current_worktree:
                divergences.append(
                    f"Feature worktree divergence for {feature_id}: expected={expected_worktree}, current={current_worktree}"
                )
                incidents.append(
                    StateReconstructionIncident(
                        code="FEATURE_WORKTREE_DIVERGENCE",
                        reason=f"Feature {feature_id} worktree proof diverged",
                        evidence=[divergences[-1]],
                    )
                )

            expected_dependencies = feature_state.get("dependencies")
            resolved_dependencies = feature_state.get("resolved_dependencies")
            if (
                isinstance(expected_dependencies, list)
                and isinstance(resolved_dependencies, list)
                and expected_dependencies != resolved_dependencies
            ):
                divergences.append(
                    f"Feature dependency divergence for {feature_id}: expected={expected_dependencies}, current={resolved_dependencies}"
                )
                incidents.append(
                    StateReconstructionIncident(
                        code="FEATURE_DEPENDENCY_DIVERGENCE",
                        reason=f"Feature {feature_id} dependencies diverged",
                        evidence=[divergences[-1]],
                    )
                )

            for artifact in feature_state.get("required_child_artifacts", []):
                artifact_path = artifact.get("absolute_path") or artifact.get("path")
                artifact_file = None
                if artifact_path:
                    artifact_file = Path(artifact_path)
                    if not artifact_file.is_absolute():
                        artifact_file = self.repo_root / artifact_file

                current_exists = artifact.get("exists", True)
                current_digest = artifact.get("current_digest")
                if artifact_file is not None:
                    current_exists = artifact_file.exists()
                    if current_exists:
                        current_digest = hashlib.sha256(artifact_file.read_bytes()).hexdigest()

                if artifact.get("required", True) and not current_exists:
                    divergences.append(
                        f"Missing required child artifact for {feature_id}: {artifact.get('path')}"
                    )
                    incidents.append(
                        StateReconstructionIncident(
                            code="MISSING_REQUIRED_CHILD_ARTIFACT",
                            reason=f"Feature {feature_id} is missing a required child artifact",
                            evidence=[divergences[-1]],
                        )
                    )
                    continue

                recorded_digest = artifact.get("recorded_digest")
                if recorded_digest and current_digest and recorded_digest != current_digest:
                    divergences.append(
                        f"Child artifact divergence for {feature_id}: {artifact.get('path')}"
                    )
                    incidents.append(
                        StateReconstructionIncident(
                            code="CHILD_ARTIFACT_DIVERGENCE",
                            reason=f"Feature {feature_id} child artifact digest diverged",
                            evidence=[divergences[-1]],
                        )
                    )

        # Check for missing mandatory artefacts
        if state.status == "COMPLETED" and not state.integrated_commit:
            divergences.append("No integrated commit for completed state")
            incidents.append(
                StateReconstructionIncident(
                    code="MISSING_INTEGRATION_COMMIT",
                    reason="Completed state missing integrated commit proof",
                    evidence=[divergences[-1]],
                )
            )

        # Check for missing feature graph IDs (AC-R13-6)
        if state.status == "COMPLETED" and not state.feature_graph_ids:
            divergences.append("No feature graph IDs registered for completed run")
            incidents.append(
                StateReconstructionIncident(
                    code="MISSING_FEATURE_GRAPH_IDS",
                    reason="Completed run has no feature graph identifiers",
                    evidence=[divergences[-1]],
                )
            )

        # Check for missing validation results (AC-R16)
        if state.status == "COMPLETED" and not state.validation_results:
            divergences.append("No validation results recorded for completed state")
            incidents.append(
                StateReconstructionIncident(
                    code="MISSING_VALIDATION_RESULTS",
                    reason="Completed run missing validation results proof",
                    evidence=[divergences[-1]],
                )
            )
        for validation_id, validation_result in state.validation_results.items():
            expected_status = validation_result.get("expected_status")
            actual_status = validation_result.get("status")
            if expected_status and actual_status and expected_status != actual_status:
                divergences.append(
                    f"Validation divergence for {validation_id}: expected={expected_status}, current={actual_status}"
                )
                incidents.append(
                    StateReconstructionIncident(
                        code="VALIDATION_RESULT_DIVERGENCE",
                        reason=f"Validation proof diverged for {validation_id}",
                        evidence=[divergences[-1]],
                    )
                )
            if state.status == "COMPLETED" and actual_status is None:
                divergences.append(f"Missing validation status for {validation_id}")
                incidents.append(
                    StateReconstructionIncident(
                        code="MISSING_VALIDATION_RESULTS",
                        reason=f"Validation {validation_id} has no status proof",
                        evidence=[divergences[-1]],
                    )
                )

        # Recalculate is_clean after all checks (AC-R2-2)
        is_clean = len(incidents) == 0 and len(divergences) == 0

        return StateReconstructionResult(
            run_id=self.run_id,
            is_clean=is_clean,
            incidents=incidents,
            divergences=divergences,
            state=state,
        )

    def _normalize_plan(
        self,
        plan: ProductPlan | dict[str, Any] | None,
        *,
        plan_id: str,
        plan_hash: str,
    ) -> dict[str, Any] | None:
        if plan is None:
            return None

        if isinstance(plan, ProductPlan):
            source = plan.to_dict()
        else:
            source = dict(plan)

        features = source.get("features", [])
        normalized_features: dict[str, dict[str, Any]] = {}
        for feature in features:
            feature_id = str(feature["feature_id"])
            normalized_features[feature_id] = {
                "title": feature.get("title"),
                "specification_path": feature.get("specification_path"),
                "required": bool(feature.get("required")),
                "priority": feature.get("priority"),
                "depends_on": sorted(str(dep) for dep in feature.get("depends_on", [])),
                "validations": sorted(str(validation) for validation in feature.get("validations", [])),
            }

        return {
            "plan_id": source.get("plan_id", plan_id),
            "plan_hash": source.get("plan_hash", plan_hash),
            "integration_branch": source.get("integration_branch"),
            "global_validations": sorted(str(item) for item in source.get("global_validations", [])),
            "features": normalized_features,
        }

    def _compare_plan_snapshot(
        self,
        *,
        persisted_snapshot: dict[str, Any],
        current_snapshot: dict[str, Any],
        divergences: list[str],
        incidents: list[StateReconstructionIncident],
    ) -> None:
        if persisted_snapshot.get("plan_id") != current_snapshot.get("plan_id"):
            divergences.append(
                f"Plan identity divergence: persisted={persisted_snapshot.get('plan_id')}, "
                f"current={current_snapshot.get('plan_id')}"
            )
            incidents.append(
                StateReconstructionIncident(
                    code="PLAN_ID_DIVERGENCE",
                    reason="Current plan identity does not match persisted plan identity",
                    evidence=[divergences[-1]],
                )
            )

        if persisted_snapshot.get("integration_branch") != current_snapshot.get("integration_branch"):
            divergences.append(
                f"Plan integration branch divergence: persisted={persisted_snapshot.get('integration_branch')}, "
                f"current={current_snapshot.get('integration_branch')}"
            )
            incidents.append(
                StateReconstructionIncident(
                    code="PLAN_INTEGRATION_BRANCH_DIVERGENCE",
                    reason="Current plan integration branch does not match persisted plan snapshot",
                    evidence=[divergences[-1]],
                )
            )

        if persisted_snapshot.get("global_validations") != current_snapshot.get("global_validations"):
            divergences.append(
                f"Plan global validations divergence: persisted={persisted_snapshot.get('global_validations')}, "
                f"current={current_snapshot.get('global_validations')}"
            )
            incidents.append(
                StateReconstructionIncident(
                    code="PLAN_GLOBAL_VALIDATIONS_DIVERGENCE",
                    reason="Current plan global validations do not match persisted plan snapshot",
                    evidence=[divergences[-1]],
                )
            )

        persisted_features = persisted_snapshot.get("features", {})
        current_features = current_snapshot.get("features", {})
        if set(persisted_features) != set(current_features):
            divergences.append(
                f"Plan feature set divergence: persisted={sorted(persisted_features)}, "
                f"current={sorted(current_features)}"
            )
            incidents.append(
                StateReconstructionIncident(
                    code="PLAN_FEATURE_SET_DIVERGENCE",
                    reason="Current plan features do not match persisted plan snapshot",
                    evidence=[divergences[-1]],
                )
            )

        for feature_id in sorted(set(persisted_features) & set(current_features)):
            if persisted_features[feature_id] != current_features[feature_id]:
                divergences.append(
                    f"Plan feature config divergence for {feature_id}: "
                    f"persisted={persisted_features[feature_id]}, current={current_features[feature_id]}"
                )
                incidents.append(
                    StateReconstructionIncident(
                        code="PLAN_FEATURE_CONFIG_DIVERGENCE",
                        reason=f"Current plan configuration diverged for feature {feature_id}",
                        evidence=[divergences[-1]],
                    )
                )

    def _verify_resume_plan_snapshot(
        self,
        *,
        state: ProductRunState,
        current_plan: dict[str, Any] | None,
    ) -> None:
        if current_plan is None:
            return

        if not state.plan_snapshot:
            raise ProductRuntimeError(
                f"Cannot resume run {self.run_id}: MISSING_PLAN_SNAPSHOT_PROOF"
            )

        divergences: list[str] = []
        incidents: list[StateReconstructionIncident] = []
        self._compare_plan_snapshot(
            persisted_snapshot=state.plan_snapshot,
            current_snapshot=current_plan,
            divergences=divergences,
            incidents=incidents,
        )
        if incidents:
            codes = ", ".join(incident.code for incident in incidents)
            reasons = "; ".join(incident.description for incident in incidents)
            raise ProductRuntimeError(
                f"Cannot resume run {self.run_id}: {codes}: {reasons}"
            )

    def record_idempotent_action(
        self,
        feature_id: str,
        task_id: str,
        action: str,
        attempt: int,
        intention_data: dict[str, Any] | None = None,
    ) -> IdempotenceKey:
        """Record intention to perform an action (before execution)."""
        with self._managed_lock("task", locked_entity_id="task", task_id=task_id):
            return self.state_manager.record_action_intention(
                feature_id=feature_id,
                task_id=task_id,
                action=action,
                attempt=attempt,
                data=intention_data,
            )

    def complete_idempotent_action(
        self,
        idempotence_key: IdempotenceKey,
        success: bool,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Record action result (after execution).

        Ensures idempotence: action result is recorded only once per unique key.
        """
        with self._managed_lock("task", locked_entity_id="task", task_id=idempotence_key.task_id):
            if self.is_action_already_completed(idempotence_key):
                return

            self.state_manager.write_journal_entry(
                self._build_journal_entry(
                    JournalEntryType.ACTION_APPLIED,
                    feature_id=idempotence_key.feature_id,
                    task_id=idempotence_key.task_id,
                    action=idempotence_key.action,
                    idempotence_key=idempotence_key,
                    data=result or {},
                )
            )
            self.state_manager.record_action_result(
                idempotence_key=idempotence_key,
                success=success,
                result=result,
            )

            state = self.state_manager.read_state("", "")
            state.completed_actions.add(self._idempotence_key_to_string(idempotence_key))
            self.state_manager.write_state(state)

    def _idempotence_key_to_string(self, key: IdempotenceKey) -> str:
        """Convert idempotence key to unique string representation."""
        return f"{key.run_id}:{key.feature_id}:{key.task_id}:{key.action}:{key.attempt}"

    def is_action_already_completed(
        self,
        idempotence_key: IdempotenceKey,
    ) -> bool:
        """Check if an action has already been completed (idempotence check).

        Checks both persisted state and journal to prevent double execution.
        """
        state = self.state_manager.read_state("", "")
        key_str = self._idempotence_key_to_string(idempotence_key)

        if key_str in state.completed_actions:
            return True

        journal_entries = self.state_manager.read_journal()

        for entry in journal_entries:
            if entry.idempotence_key and entry.idempotence_key == idempotence_key:
                if entry.entry_type == JournalEntryType.ACTION_COMPLETED:
                    return True

        return False

    def record_durable_decision(
        self,
        feature_id: str,
        decision_type: str,
        content: dict[str, Any],
        task_id: str | None = None,
    ) -> str:
        """Record a durable decision necessary for reproductibility."""
        from uuid import uuid4

        decision = DurableDecision(
            decision_id=str(uuid4()),
            product_key=self._current_product_key(),
            run_id=self.run_id,
            feature_id=feature_id,
            task_id=task_id,
            decision_type=decision_type,
            content=content,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        def persist_decision() -> str:
            self._require_decision_store().record_decision(decision)
            return decision.decision_id

        return self._run_logged_transition(
            action="record_durable_decision",
            lock_type="product",
            feature_id=feature_id,
            task_id=task_id,
            attempt=1,
            mutation=persist_decision,
            result_factory=lambda decision_id: {
                "decision_id": decision_id,
                "decision_type": decision_type,
            },
        )

    def approve_durable_decision(self, decision_id: str) -> None:
        """Approve a durable decision."""
        def approve() -> dict[str, Any]:
            self._require_decision_store().approve_decision(decision_id)
            state = self.state_manager.read_state("", "")
            synchronized = False
            if state.product_key:
                previous_decisions = dict(state.durable_decisions)
                synced_state = self._sync_durable_decisions_to_state(state)
                synchronized = synced_state.durable_decisions != previous_decisions
            return {
                "decision_id": decision_id,
                "synchronized_state": synchronized,
            }

        self._run_logged_transition(
            action="approve_durable_decision",
            lock_type="product",
            attempt=1,
            mutation=approve,
        )

    def get_durable_decisions_for_feature(self, feature_id: str) -> list[DurableDecision]:
        """Get all durable decisions for a feature."""
        return self._require_decision_store().get_decisions_for_feature(feature_id)

    def get_approved_durable_decisions(self) -> list[DurableDecision]:
        """Get all approved durable decisions."""
        return self._require_decision_store().get_approved_decisions()

    def apply_durable_decisions_to_backlog(
        self,
        decisions: list[DurableDecision],
        backlog: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        """Apply durable decisions to a regenerated backlog.

        Preserves approved decisions through backlog regeneration (AC-R29-3).

        Returns:
            (updated_backlog, conflict_list)
        """
        conflicts = []
        updated_backlog = backlog.copy()
        decision_ids_seen: set[str] = set()
        runtime_product_key = self._current_product_key()
        available_features = set(backlog.get("features", []))

        for decision in decisions:
            if decision.decision_id in decision_ids_seen:
                continue
            decision_ids_seen.add(decision.decision_id)

            if decision.status != "approved":
                continue
            if decision.product_key != runtime_product_key:
                conflicts.append(
                    f"Decision {decision.decision_id} targets product {decision.product_key}, "
                    f"expected {runtime_product_key}"
                )
                continue
            if decision.feature_id not in available_features:
                conflicts.append(
                    f"Decision {decision.decision_id} targets missing feature {decision.feature_id}"
                )
                continue

            if decision.decision_type == "SCOPE_EXTENSION":
                if "extended_paths" not in updated_backlog:
                    updated_backlog["extended_paths"] = []
                extended = decision.content.get("extended_paths", [])
                for path in extended:
                    if path not in updated_backlog["extended_paths"]:
                        updated_backlog["extended_paths"].append(path)

            elif decision.decision_type == "CRITERION_REALLOCATION":
                if "reallocations" not in updated_backlog:
                    updated_backlog["reallocations"] = {}
                old_owner = decision.content.get("old_owner")
                new_owner = decision.content.get("new_owner")
                criterion_id = decision.content.get("criterion_id")
                if old_owner and new_owner and criterion_id:
                    if criterion_id in updated_backlog.get("reallocations", {}):
                        existing = updated_backlog["reallocations"][criterion_id]
                        if existing != new_owner:
                            conflicts.append(
                                f"Criterion {criterion_id} reallocation conflict: "
                                f"durable decision says {new_owner} but backlog says {existing}"
                            )
                    else:
                        updated_backlog["reallocations"][criterion_id] = new_owner

        return updated_backlog, conflicts

    def _derive_product_key(self, plan_id: str) -> str:
        if plan_id:
            return plan_id
        return f"run:{self.run_id}"

    def _configure_decision_store(self, product_key: str) -> DurableDecisionStore:
        if self.decision_store is None or self.decision_store.product_key != product_key:
            self.decision_store = DurableDecisionStore(self.repo_root, product_key)
        return self.decision_store

    def _require_decision_store(self) -> DurableDecisionStore:
        if self.decision_store is not None:
            return self.decision_store

        state_path = self.state_manager.get_state_path()
        if state_path.exists():
            state = self.state_manager.read_state("", "")
            return self._configure_decision_store(state.product_key or self._derive_product_key(state.plan_id))

        return self._configure_decision_store(self._derive_product_key(""))

    def _current_product_key(self) -> str:
        return self._require_decision_store().product_key

    def _sync_durable_decisions_to_state(self, state: ProductRunState) -> ProductRunState:
        approved_decisions = self._require_decision_store().get_approved_decisions()
        normalized_decisions = {}

        for decision in approved_decisions:
            normalized_decisions[decision.decision_id] = {
                **decision.to_dict(),
                "source_run_id": decision.run_id,
            }

        if state.durable_decisions == normalized_decisions:
            return state

        state.durable_decisions = normalized_decisions
        self.state_manager.write_state(state)
        return state

    def finish_run(self, success: bool, error_message: str | None = None) -> None:
        """Mark run as finished."""
        def finish() -> dict[str, Any]:
            state = self.state_manager.read_state("", "")
            state.status = "COMPLETED" if success else "FAILED"
            state.finished_at = datetime.now(timezone.utc).isoformat()
            if error_message:
                state.error_message = error_message
            self.state_manager.write_state(state)
            return {"status": state.status, "error_message": state.error_message}

        self._run_logged_transition(
            action="finish_run",
            lock_type="product",
            attempt=1,
            mutation=finish,
        )

    def update_feature_state(self, feature_id: str, feature_state: dict[str, Any]) -> None:
        """Update feature-level state in the run state."""
        def update() -> dict[str, Any]:
            state = self.state_manager.read_state("", "")
            state.feature_states[feature_id] = feature_state
            self.state_manager.write_state(state)
            return {"feature_id": feature_id, "status": feature_state.get("status")}

        self._run_logged_transition(
            action="update_feature_state",
            lock_type="feature",
            locked_entity_id=feature_id,
            feature_id=feature_id,
            attempt=1,
            mutation=update,
        )

    def update_task_state(self, task_id: str, task_state: dict[str, Any]) -> None:
        """Update task-level state in the run state."""
        def update() -> dict[str, Any]:
            state = self.state_manager.read_state("", "")
            state.task_states[task_id] = task_state
            self.state_manager.write_state(state)
            return {"task_id": task_id, "status": task_state.get("status")}

        self._run_logged_transition(
            action="update_task_state",
            lock_type="task",
            locked_entity_id="task",
            task_id=task_id,
            attempt=1,
            mutation=update,
        )

    def create_run_checkpoint(self, checkpoint_data: dict[str, Any]) -> None:
        """Create a checkpoint of the product run state."""
        def checkpoint() -> dict[str, Any]:
            payload = dict(checkpoint_data)
            payload["run_id"] = self.run_id
            self.state_manager.write_checkpoint(payload)
            return {"run_id": self.run_id, "keys": sorted(payload.keys())}

        self._run_logged_transition(
            action="create_run_checkpoint",
            lock_type="product",
            attempt=1,
            mutation=checkpoint,
        )

    def get_run_checkpoint(self) -> dict[str, Any] | None:
        """Retrieve the latest product run checkpoint."""
        return self.state_manager.read_checkpoint()

    def record_provider_waiting_state(
        self,
        incident: ProviderIncidentEvent,
        feature_id: str | None = None,
        task_id: str | None = None,
    ) -> None:
        """Persist a provider incident as WAITING_PROVIDER_RESET state (AC-R14-1, AC-R21-6).

        Materializes the explicit WAITING_PROVIDER_RESET status and logs complete audit details
        including provider, error type, raw message, timezone, deadline, policy and decision.
        """
        waiting_state = ProviderWaitingState(
            incident=incident,
            recorded_at=self._now().isoformat(),
            feature_id=feature_id,
            task_id=task_id,
        )

        def persist_waiting() -> dict[str, Any]:
            state = self.state_manager.read_state("", "")
            # Materialize explicit WAITING_PROVIDER_RESET status (AC-R14-1, AC-R21-6)
            if feature_id:
                feature_state = state.feature_states.setdefault(feature_id, {})
                feature_state["provider_waiting_state"] = waiting_state.to_dict()
                provider_states = feature_state.setdefault("provider_waiting_states", {})
                previous = provider_states.get(str(incident.provider), {})
                provider_states[str(incident.provider)] = {
                    **waiting_state.to_dict(),
                    "incident_count": int(previous.get("incident_count", 0)) + 1,
                }
                feature_state["status"] = "WAITING_PROVIDER_RESET"
                state.feature_states[feature_id] = feature_state
            else:
                # Store product-level provider waiting state as separate file in run namespace
                waiting_file = self.state_manager.run_namespace / "provider_waiting_state.json"
                waiting_file.write_text(
                    json.dumps(waiting_state.to_dict(), ensure_ascii=False),
                    encoding="utf-8",
                )
                ledger_file = self.state_manager.run_namespace / "provider_waiting_states.json"
                try:
                    provider_states = json.loads(ledger_file.read_text(encoding="utf-8")) if ledger_file.exists() else {}
                except (json.JSONDecodeError, IOError):
                    provider_states = {}
                previous = provider_states.get(str(incident.provider), {})
                provider_states[str(incident.provider)] = {
                    **waiting_state.to_dict(),
                    "incident_count": int(previous.get("incident_count", 0)) + 1,
                }
                ledger_file.write_text(json.dumps(provider_states, ensure_ascii=False), encoding="utf-8")
                state.status = "WAITING_PROVIDER_RESET"
            self.state_manager.write_state(state)

            # Log complete audit details (AC-R21-8)
            audit_entry = {
                "action": "provider_incident_detected",
                "provider": str(incident.provider),
                "error_type": str(incident.error_type),
                "raw_message": incident.raw_message,
                "source_timezone": incident.source_timezone,
                "retry_at": incident.retry_at,
                "retry_after_seconds": incident.retry_after_seconds,
                "policy": incident.policy,
                "decision": incident.decision,
                "scope": "feature" if feature_id else "product",
                "recorded_at": waiting_state.recorded_at,
            }
            self.state_manager.write_journal_entry(
                self._build_journal_entry(
                    JournalEntryType.ACTION_APPLIED,
                    feature_id=feature_id,
                    task_id=task_id,
                    action="record_provider_waiting_state",
                    data=audit_entry,
                )
            )

            return audit_entry

        self._run_logged_transition(
            action="record_provider_waiting_state",
            lock_type="feature" if feature_id else "product",
            locked_entity_id=feature_id,
            feature_id=feature_id,
            task_id=task_id,
            attempt=1,
            mutation=persist_waiting,
        )

    def get_provider_waiting_state(
        self,
        feature_id: str | None = None,
        provider_name: str | None = None,
    ) -> ProviderWaitingState | None:
        """Retrieve provider waiting state if present (AC-R21-6)."""
        waiting_data: dict[str, Any] | None = None

        if feature_id:
            state = self.state_manager.read_state("", "")
            feature_state = state.feature_states.get(feature_id, {})
            waiting_data = (
                feature_state.get("provider_waiting_states", {}).get(provider_name)
                if provider_name else feature_state.get("provider_waiting_state")
            )
        else:
            # Retrieve product-level waiting state from separate file
            waiting_file = self.state_manager.run_namespace / "provider_waiting_state.json"
            waiting_file = self.state_manager.run_namespace / (
                "provider_waiting_states.json" if provider_name else "provider_waiting_state.json"
            )
            if waiting_file.exists():
                try:
                    waiting_data = json.loads(waiting_file.read_text(encoding="utf-8"))
                    if provider_name:
                        waiting_data = waiting_data.get(provider_name)
                except (json.JSONDecodeError, IOError):
                    return None

        if waiting_data is None:
            return None

        try:
            return ProviderWaitingState.from_dict(waiting_data)
        except (KeyError, ValueError, TypeError):
            return None

    def clear_provider_waiting_state(self, feature_id: str | None = None) -> None:
        """Clear provider waiting state after successful resume (AC-R14-3)."""
        def clear_waiting() -> dict[str, Any]:
            state = self.state_manager.read_state("", "")
            if feature_id:
                feature_state = state.feature_states.get(feature_id, {})
                waiting_data = feature_state.get("provider_waiting_state", {})
                provider = waiting_data.get("incident", {}).get("provider")
                if "provider_waiting_state" in feature_state:
                    del feature_state["provider_waiting_state"]
                if provider:
                    feature_state.get("provider_waiting_states", {}).pop(provider, None)
                # Clear WAITING_PROVIDER_RESET status when resuming
                if feature_state.get("status") == "WAITING_PROVIDER_RESET":
                    feature_state.pop("status", None)
                state.feature_states[feature_id] = feature_state
            else:
                # Remove product-level waiting state file
                waiting_file = self.state_manager.run_namespace / "provider_waiting_state.json"
                try:
                    waiting_data = json.loads(waiting_file.read_text(encoding="utf-8")) if waiting_file.exists() else {}
                except (json.JSONDecodeError, IOError):
                    waiting_data = {}
                if waiting_file.exists():
                    waiting_file.unlink()
                ledger_file = self.state_manager.run_namespace / "provider_waiting_states.json"
                if ledger_file.exists():
                    try:
                        provider_states = json.loads(ledger_file.read_text(encoding="utf-8"))
                        provider_states.pop(waiting_data.get("incident", {}).get("provider"), None)
                        ledger_file.write_text(json.dumps(provider_states, ensure_ascii=False), encoding="utf-8")
                    except (json.JSONDecodeError, IOError):
                        pass
                # Clear WAITING_PROVIDER_RESET status when resuming
                if state.status == "WAITING_PROVIDER_RESET":
                    state.status = None
            self.state_manager.write_state(state)
            return {"cleared": True, "scope": "feature" if feature_id else "product"}

        self._run_logged_transition(
            action="clear_provider_waiting_state",
            lock_type="feature" if feature_id else "product",
            locked_entity_id=feature_id,
            feature_id=feature_id,
            attempt=1,
            mutation=clear_waiting,
        )

    def resume_from_provider_wait(
        self,
        feature_id: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        """Resume from WAITING_PROVIDER_RESET after deadline (AC-R14-3).

        Reloads and reconciles all proofs before action.
        Returns incident details if deadline is reached, None otherwise.
        """
        now = now or self._now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ProductRuntimeError("now must be timezone-aware")

        waiting_state = self.get_provider_waiting_state(feature_id=feature_id)
        if waiting_state is None:
            return None

        try:
            incident = waiting_state.incident
            if not incident.retry_at:
                return None

            # Parse deadline with explicit timezone
            retry_dt = datetime.fromisoformat(incident.retry_at.replace("Z", "+00:00"))
            if now < retry_dt:
                return None  # Deadline not reached yet

            # AC-R14-3: Reload and reconcile all proofs before resumption
            state = self.state_manager.read_state("", "")
            current_waiting = self.get_provider_waiting_state(feature_id=feature_id)
            if current_waiting is None or current_waiting.incident.retry_at != incident.retry_at:
                # State diverged - escalate
                return {
                    "ready_to_resume": False,
                    "reason": "state_diverged_during_reconciliation",
                    "provider": str(incident.provider),
                    "error_type": str(incident.error_type),
                }

            # All proofs reconciled - return resume details
            return {
                "ready_to_resume": True,
                "provider": str(incident.provider),
                "error_type": str(incident.error_type),
                "retry_at": incident.retry_at,
                "recorded_at": waiting_state.recorded_at,
                "policy": incident.policy,
                "source_timezone": incident.source_timezone,
            }
        except (KeyError, ValueError, TypeError) as exc:
            return {
                "ready_to_resume": False,
                "reason": f"reconciliation_error: {exc}",
            }

    def tick_provider_wait(
        self,
        *,
        feature_id: str | None = None,
        now: datetime | None = None,
        resume_callback: ResumeCallback,
    ) -> dict[str, Any] | None:
        """Non-blocking, atomic deadline tick that performs one bounded runtime resume.

        The callback is the typed integration seam for later orchestration work; it
        cannot issue shell commands through this runtime.  Failed callbacks retain
        the persisted wait state for a later tick.
        """
        effective_now = now or self._now()
        if effective_now.tzinfo is None or effective_now.utcoffset() is None:
            raise ProductRuntimeError("now must be timezone-aware")

        def resume() -> dict[str, Any]:
            state = self.state_manager.read_state("", "")  # fresh proof under lock
            waiting = self.get_provider_waiting_state(feature_id=feature_id)
            if waiting is None or not waiting.incident.retry_at:
                return {"resumed": False, "reason": "no_waiting_state"}
            retry_at = datetime.fromisoformat(waiting.incident.retry_at.replace("Z", "+00:00"))
            if effective_now < retry_at:
                return {"resumed": False, "reason": "deadline_not_reached"}
            evidence = {
                "run_id": self.run_id,
                "feature_id": feature_id,
                "state_status": state.status,
                "incident": waiting.incident.to_dict(),
                "recorded_at": waiting.recorded_at,
            }
            if not resume_callback(evidence):
                return {"resumed": False, "reason": "resume_callback_failed", **evidence}
            if feature_id:
                feature_state = state.feature_states.get(feature_id, {})
                feature_state.pop("provider_waiting_state", None)
                feature_state.get("provider_waiting_states", {}).pop(str(waiting.incident.provider), None)
                if feature_state.get("status") == "WAITING_PROVIDER_RESET":
                    feature_state["status"] = "READY"
                state.feature_states[feature_id] = feature_state
            else:
                waiting_file = self.state_manager.run_namespace / "provider_waiting_state.json"
                if waiting_file.exists():
                    waiting_file.unlink()
                ledger_file = self.state_manager.run_namespace / "provider_waiting_states.json"
                if ledger_file.exists():
                    try:
                        provider_states = json.loads(ledger_file.read_text(encoding="utf-8"))
                        provider_states.pop(str(waiting.incident.provider), None)
                        ledger_file.write_text(json.dumps(provider_states, ensure_ascii=False), encoding="utf-8")
                    except (json.JSONDecodeError, IOError):
                        pass
                if state.status == "WAITING_PROVIDER_RESET":
                    state.status = "READY"
            self.state_manager.write_state(state)
            return {"resumed": True, "decision": "RESUME", **evidence}

        result = self._run_logged_transition(
            action="tick_provider_wait",
            lock_type="feature" if feature_id else "product",
            locked_entity_id=feature_id,
            feature_id=feature_id,
            attempt=1,
            mutation=resume,
        )
        if result.get("reason") in {"no_waiting_state", "deadline_not_reached"}:
            return None
        return result

    def pause(self, *, feature_id: str | None = None, reason: str = "manual_pause") -> None:
        """Persist PAUSED independently from waiting, failed, and blocked states."""
        def persist_pause() -> dict[str, Any]:
            state = self.state_manager.read_state("", "")
            if feature_id:
                feature_state = state.feature_states.setdefault(feature_id, {})
                feature_state["status"] = "PAUSED"
            else:
                state.status = "PAUSED"
            self.state_manager.write_state(state)
            return {"state": "PAUSED", "reason": reason, "decision": "PAUSE"}
        self._run_logged_transition(
            action="pause", lock_type="feature" if feature_id else "product",
            locked_entity_id=feature_id, feature_id=feature_id, attempt=1, mutation=persist_pause,
        )

    def acquire_product_lock(self) -> str:
        """Acquire a product-level lock to prevent concurrent drivers."""
        lock = self.state_manager.acquire_lock("product")
        return lock.lock_id

    def acquire_feature_lock(self, feature_id: str) -> str:
        """Acquire a feature-level lock to prevent concurrent access."""
        lock = self.state_manager.acquire_lock("feature", locked_entity_id=feature_id)
        return lock.lock_id

    def acquire_task_lock(self, task_id: str) -> str:
        """Acquire a task-level lock to prevent concurrent writes to task artifacts (AC-R13-10)."""
        lock = self.state_manager.acquire_lock("task", locked_entity_id="task", task_id=task_id)
        return lock.lock_id

    def release_lock(self, lock_id: str, reason: str | None = None) -> None:
        """Release a held lock."""
        self.state_manager.release_lock(lock_id, reason=reason)

    def update_lock_heartbeat(self, lock_id: str) -> None:
        """Keep a lock alive by updating its heartbeat."""
        self.state_manager.update_lock_heartbeat(lock_id)

    def get_feature_graph_id(self, feature_id: str) -> str | None:
        """Get the registered LangGraph ID for a feature."""
        state = self.state_manager.read_state("", "")
        return state.feature_graph_ids.get(feature_id)

    def check_concurrent_access(self, lock_type: str, entity_id: str | None = None) -> str | None:
        """Check if there's concurrent access and return blocking lock ID if present."""
        locks = self.state_manager.list_locks()

        for lock in locks:
            if lock.lock_type != lock_type:
                continue
            if entity_id and lock.locked_entity_id != entity_id:
                continue
            if lock.owner_run_id == self.run_id:
                continue

            if lock.is_expired():
                try:
                    self.state_manager.release_lock(lock.lock_id, reason="Lock expired", force_expired=True)
                except ProductLockError:
                    return lock.lock_id
            else:
                return lock.lock_id

        return None

    def _build_journal_entry(
        self,
        entry_type: JournalEntryType,
        data: dict[str, Any],
        feature_id: str | None = None,
        task_id: str | None = None,
        action: str | None = None,
        idempotence_key: IdempotenceKey | None = None,
    ) -> JournalEntry:
        timestamp = datetime.now(timezone.utc).isoformat()
        return JournalEntry(
            entry_id=str(uuid4()),
            entry_type=entry_type,
            timestamp=timestamp,
            timezone=datetime.now(timezone.utc).astimezone().tzinfo.tzname(datetime.now()),
            run_id=self.run_id,
            feature_id=feature_id,
            task_id=task_id,
            action=action,
            idempotence_key=idempotence_key,
            data=data,
        )

    @contextmanager
    def _managed_lock(
        self,
        lock_type: str,
        locked_entity_id: str | None = None,
        task_id: str | None = None,
    ):
        if self.state_manager.has_active_owned_lock(
            lock_type=lock_type,
            locked_entity_id=locked_entity_id,
            task_id=task_id,
        ):
            yield None
            return

        lock = self.state_manager.acquire_lock(
            lock_type,
            locked_entity_id=locked_entity_id,
            task_id=task_id,
        )
        try:
            yield lock
        finally:
            self.state_manager.release_lock(lock.lock_id, reason=f"{lock_type} transition complete")

    def _run_logged_transition(
        self,
        *,
        action: str,
        lock_type: str,
        mutation,
        feature_id: str | None = None,
        task_id: str | None = None,
        attempt: int | None = None,
        locked_entity_id: str | None = None,
        result_factory=None,
    ):
        effective_entity_id = locked_entity_id
        if effective_entity_id is None and lock_type == "feature":
            effective_entity_id = feature_id
        with self._managed_lock(lock_type, locked_entity_id=effective_entity_id, task_id=task_id):
            idempotence_key = None
            if attempt is not None:
                idempotence_key = IdempotenceKey(
                    run_id=self.run_id,
                    feature_id=feature_id or "",
                    task_id=task_id or "",
                    action=action,
                    attempt=attempt,
                )
            self.state_manager.write_journal_entry(
                self._build_journal_entry(
                    JournalEntryType.INTENTION_START,
                    feature_id=feature_id,
                    task_id=task_id,
                    action=action,
                    idempotence_key=idempotence_key,
                    data={"attempt": attempt} if attempt is not None else {},
                )
            )
            try:
                result = mutation()
            except Exception as exc:
                self.state_manager.write_journal_entry(
                    self._build_journal_entry(
                        JournalEntryType.ACTION_FAILED,
                        feature_id=feature_id,
                        task_id=task_id,
                        action=action,
                        idempotence_key=idempotence_key,
                        data={
                            "attempt": attempt,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    )
                )
                raise
            action_data = result_factory(result) if result_factory is not None else result
            if not isinstance(action_data, dict):
                action_data = {"result": action_data}
            if "action" not in action_data:
                action_data["action"] = action
            if attempt is not None and "attempt" not in action_data:
                action_data["attempt"] = attempt
            self.state_manager.write_journal_entry(
                self._build_journal_entry(
                    JournalEntryType.ACTION_APPLIED,
                    feature_id=feature_id,
                    task_id=task_id,
                    action=action,
                    idempotence_key=idempotence_key,
                    data=action_data,
                )
            )
            self.state_manager.write_journal_entry(
                self._build_journal_entry(
                    JournalEntryType.ACTION_COMPLETED,
                    feature_id=feature_id,
                    task_id=task_id,
                    action=action,
                    idempotence_key=idempotence_key,
                    data=action_data,
                )
            )
            return result

    def _find_graph_id_owner(self, graph_id: str, exclude_run_id: str | None = None) -> str | None:
        runs_dir = self.repo_root / ".autodev" / "runs" / "products"
        if not runs_dir.exists():
            return None

        for run_dir in sorted(path for path in runs_dir.iterdir() if path.is_dir()):
            run_id = run_dir.name
            if exclude_run_id and run_id == exclude_run_id:
                continue
            state_path = run_dir / "state.json"
            if not state_path.exists():
                continue
            try:
                state_data = json.loads(state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue

            if state_data.get("product_graph_id") == graph_id:
                return run_id

            feature_graph_ids = state_data.get("feature_graph_ids", {})
            if isinstance(feature_graph_ids, dict) and graph_id in feature_graph_ids.values():
                return run_id

        return None

    @staticmethod
    def _product_git_evidence_field_map() -> dict[str, str]:
        return {
            "branch": "product_branch",
            "current_branch": "current_product_branch",
            "base_commit": "base_commit",
            "current_commit": "current_commit",
            "integrated_commit": "integrated_commit",
            "worktree": "product_worktree",
            "current_worktree": "current_product_worktree",
        }

    @classmethod
    def _feature_git_evidence_fields(cls) -> tuple[str, ...]:
        return tuple(cls._product_git_evidence_field_map().keys())

    @classmethod
    def _normalize_git_evidence_updates(
        cls,
        *,
        branch: str | None,
        current_branch: str | None,
        base_commit: str | None,
        current_commit: str | None,
        integrated_commit: str | None,
        worktree: str | None,
        current_worktree: str | None,
    ) -> dict[str, str]:
        raw_updates = {
            "branch": branch,
            "current_branch": current_branch,
            "base_commit": base_commit,
            "current_commit": current_commit,
            "integrated_commit": integrated_commit,
            "worktree": worktree,
            "current_worktree": current_worktree,
        }
        normalized: dict[str, str] = {}
        for field_name, value in raw_updates.items():
            if value is None:
                continue
            if not isinstance(value, str):
                raise ProductRuntimeError(f"record_git_evidence field {field_name} must be a string")
            stripped = value.strip()
            if not stripped:
                raise ProductRuntimeError(f"record_git_evidence field {field_name} cannot be blank")
            normalized[field_name] = stripped
        return normalized

    def _require_active_transition_lock(
        self,
        *,
        lock_type: str,
        locked_entity_id: str | None = None,
        task_id: str | None = None,
    ) -> None:
        if self.state_manager.has_active_owned_lock(
            lock_type=lock_type,
            locked_entity_id=locked_entity_id,
            task_id=task_id,
        ):
            return

        if lock_type == "product":
            message = "record_git_evidence requires an active product lock held by the caller"
        elif lock_type == "feature":
            message = (
                f"record_git_evidence requires an active feature lock held by the caller "
                f"for {locked_entity_id}"
            )
        else:
            message = "record_git_evidence requires an active owned lock held by the caller"
        raise ProductRuntimeError(message)

    def _initial_checkpoint_data(self, state: ProductRunState) -> dict[str, Any]:
        return {
            "run_id": state.run_id,
            "plan_id": state.plan_id,
            "plan_hash": state.plan_hash,
            "status": state.status,
            "product_graph_id": state.product_graph_id,
            "started_at": state.started_at,
        }

    def reconstruct_runtime_state(
        self,
        plan: ProductPlan | dict[str, Any],
        current_state: ProductRunState | None = None,
    ) -> StateReconstructionResult:
        """Reconstruct runtime state and detect divergences (AC-R2.2, AC-R2.3).

        Compares plan, persisted state, checkpoints, branches, commits, worktrees,
        validations and required artifacts to detect divergences.

        Returns StateReconstructionResult with incidents for any divergences found.
        """
        if current_state is None:
            try:
                current_state = self.state_manager.read_state("", "")
            except ProductStateError:
                # State not yet persisted
                return StateReconstructionResult(
                    run_id=self.run_id,
                    is_clean=True,
                    incidents=[],
                    divergences=[],
                    state=current_state or ProductRunState.initial(self.run_id),
                )

        normalized_plan = self._normalize_plan(plan)
        incidents: list[StateReconstructionIncident] = []
        divergences: list[str] = []

        # AC-R2.3: Detect divergence of status
        if current_state.status not in ("initializing", "running", "paused", "completed", "failed"):
            incidents.append(
                StateReconstructionIncident(
                    code="INVALID_RUNTIME_STATUS",
                    reason=f"Invalid runtime status: {current_state.status}",
                    evidence=[f"Status field: {current_state.status}"],
                )
            )
            divergences.append(f"status={current_state.status}")

        # AC-R2.3: Detect divergence of base commit
        if normalized_plan and "base_commit" in normalized_plan:
            declared_base = normalized_plan["base_commit"]
            if current_state.base_commit and current_state.base_commit != declared_base:
                incidents.append(
                    StateReconstructionIncident(
                        code="BASE_COMMIT_DIVERGENCE",
                        reason=f"Base commit divergence: declared {declared_base}, actual {current_state.base_commit}",
                        evidence=[
                            f"Plan base_commit: {declared_base}",
                            f"Runtime base_commit: {current_state.base_commit}",
                        ],
                    )
                )
                divergences.append(f"base_commit={current_state.base_commit}!={declared_base}")

        # AC-R2.3: Detect divergence of integrated commit
        if normalized_plan and "features" in normalized_plan:
            plan_features = {f.get("id"): f for f in normalized_plan["features"]}
            for feature_id, feature_state in current_state.feature_states.items():
                if feature_id in plan_features:
                    declared_integrated = plan_features[feature_id].get("integrated_commit")
                    actual_integrated = feature_state.get("integrated_commit")
                    if declared_integrated and actual_integrated and declared_integrated != actual_integrated:
                        incidents.append(
                            StateReconstructionIncident(
                                code="INTEGRATED_COMMIT_DIVERGENCE",
                                reason=f"Integrated commit divergence for {feature_id}",
                                evidence=[
                                    f"Feature {feature_id} declared: {declared_integrated}",
                                    f"Feature {feature_id} actual: {actual_integrated}",
                                ],
                            )
                        )
                        divergences.append(f"feature.{feature_id}.integrated_commit divergence")

        # AC-R2.3: Detect divergence of required artifacts
        if current_state.required_artifacts:
            for artifact in current_state.required_artifacts:
                artifact_path = self.repo_root / artifact.get("path", "")
                if not artifact_path.exists():
                    incidents.append(
                        StateReconstructionIncident(
                            code="MISSING_REQUIRED_ARTIFACT",
                            reason=f"Required artifact missing: {artifact.get('path')}",
                            evidence=[f"Path: {artifact_path}"],
                        )
                    )
                    divergences.append(f"artifact.missing={artifact.get('path')}")

        # AC-R2.2, AC-R2.3: Detect divergence of branches
        if current_state.feature_states:
            for feature_id, feature_state in current_state.feature_states.items():
                if feature_state.get("branch"):
                    declared_branch = feature_state.get("branch")
                    try:
                        from autodev.git_tools import branch_exists
                        if not branch_exists(self.repo_root, declared_branch):
                            incidents.append(
                                StateReconstructionIncident(
                                    code="FEATURE_BRANCH_DIVERGENCE",
                                    reason=f"Feature branch missing: {declared_branch}",
                                    evidence=[
                                        f"Feature {feature_id} branch: {declared_branch}",
                                        f"Branch status: not found in Git",
                                    ],
                                )
                            )
                            divergences.append(f"feature.{feature_id}.branch.missing")
                    except Exception:
                        pass

        # AC-R2.2, AC-R2.3: Detect divergence of worktrees
        if current_state.feature_states:
            for feature_id, feature_state in current_state.feature_states.items():
                if feature_state.get("worktree_path"):
                    declared_worktree = Path(feature_state.get("worktree_path", ""))
                    if not declared_worktree.exists():
                        incidents.append(
                            StateReconstructionIncident(
                                code="FEATURE_WORKTREE_DIVERGENCE",
                                reason=f"Feature worktree missing: {declared_worktree}",
                                evidence=[
                                    f"Feature {feature_id} worktree: {declared_worktree}",
                                    f"Worktree status: not found on disk",
                                ],
                            )
                        )
                        divergences.append(f"feature.{feature_id}.worktree.missing")

        # AC-R2.2, AC-R2.3: Detect divergence of checkpoints
        if current_state.checkpoints:
            for checkpoint_id, checkpoint_data in current_state.checkpoints.items():
                checkpoint_path = self.repo_root / checkpoint_data.get("path", "")
                if not checkpoint_path.exists():
                    incidents.append(
                        StateReconstructionIncident(
                            code="CHECKPOINT_MISSING",
                            reason=f"Checkpoint missing: {checkpoint_id}",
                            evidence=[
                                f"Checkpoint {checkpoint_id} path: {checkpoint_path}",
                                f"Checkpoint status: not found",
                            ],
                        )
                    )
                    divergences.append(f"checkpoint.{checkpoint_id}.missing")

        # AC-R2.2, AC-R2.3: Detect divergence of dependencies
        if normalized_plan and "features" in normalized_plan:
            plan_features = {f.get("id"): f for f in normalized_plan["features"]}
            for feature_id in current_state.feature_states:
                if feature_id in plan_features:
                    feature_def = plan_features[feature_id]
                    declared_deps = feature_def.get("dependencies", [])
                    for dep_id in declared_deps:
                        dep_state = current_state.feature_states.get(dep_id, {})
                        if dep_state.get("status") not in ("completed", "integrated"):
                            incidents.append(
                                StateReconstructionIncident(
                                    code="DEPENDENCY_NOT_SATISFIED",
                                    reason=f"Dependency {dep_id} not satisfied for feature {feature_id}",
                                    evidence=[
                                        f"Feature {feature_id} depends on: {dep_id}",
                                        f"Dependency status: {dep_state.get('status', 'unknown')}",
                                    ],
                                )
                            )
                            divergences.append(f"feature.{feature_id}.dependency.{dep_id}.unmet")

        # AC-R2.2, AC-R2.3: Detect divergence of validations
        if current_state.validation_results:
            for validation_id, validation_data in current_state.validation_results.items():
                if validation_data.get("status") == "failed":
                    incidents.append(
                        StateReconstructionIncident(
                            code="VALIDATION_FAILED",
                            reason=f"Validation failed: {validation_id}",
                            evidence=[
                                f"Validation {validation_id} status: failed",
                                f"Output: {validation_data.get('output', 'N/A')[:100]}",
                            ],
                        )
                    )
                    divergences.append(f"validation.{validation_id}.failed")

        return StateReconstructionResult(
            run_id=self.run_id,
            is_clean=len(incidents) == 0,
            incidents=incidents,
            divergences=divergences,
            state=current_state,
        )
