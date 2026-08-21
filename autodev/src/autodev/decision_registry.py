from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal, NamedTuple
from uuid import uuid4

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore


class DecisionRegistryError(RuntimeError):
    """Error during decision registry operations."""


class CorrectionContext(NamedTuple):
    """Context of a correction operation, capturing hierarchical relationships."""

    entity_id: str
    scope: DecisionScope
    related_entities: dict[DecisionScope, str] | None = None

    def get_all_entity_ids(self) -> list[tuple[DecisionScope, str]]:
        """Get all entity IDs including related scopes."""
        entity_ids = [(self.scope, self.entity_id)]
        if self.related_entities:
            for scope, entity_id in self.related_entities.items():
                entity_ids.append((scope, entity_id))
        return entity_ids


class DecisionStatus(str, Enum):
    """Status of a decision."""

    ACTIVE = "active"
    INVALIDATED = "invalidated"
    PENDING = "pending"
    OBSOLETE = "obsolete"


class DecisionScope(str, Enum):
    """Scope/level at which a decision applies."""

    PRODUCT = "product"
    FEATURE = "feature"
    TASK = "task"
    REQUIREMENT = "requirement"
    INCIDENT = "incident"


class InvalidationEventType(str, Enum):
    """Type of event that can invalidate a decision."""

    STRUCTURED_VERDICT = "structured_verdict"
    GIT_COMMIT = "git_commit"
    POLICY_CHANGE = "policy_change"
    HUMAN_OVERRIDE = "human_override"
    INCIDENT_DISCOVERY = "incident_discovery"


@dataclass(frozen=True)
class InvalidationEvent:
    """Represents an event that invalidates a decision."""

    event_type: InvalidationEventType
    timestamp: str
    reason: str
    evidence: list[str] = field(default_factory=list)
    git_commit: str | None = None
    actor: str | None = None

    def __post_init__(self) -> None:
        """Validate that event is properly structured and justified."""
        if not self.reason or not self.reason.strip():
            raise DecisionRegistryError(
                "Invalidation event must have a non-empty reason"
            )

        if self.event_type == InvalidationEventType.GIT_COMMIT:
            if not self.git_commit:
                raise DecisionRegistryError(
                    "GIT_COMMIT invalidation event must include git_commit"
                )

        if self.event_type == InvalidationEventType.STRUCTURED_VERDICT:
            if not self.evidence:
                raise DecisionRegistryError(
                    "STRUCTURED_VERDICT invalidation event must include evidence"
                )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with enums as their values."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> InvalidationEvent:
        """Create from dictionary, validating justification."""
        reason = data.get("reason", "").strip()
        if not reason:
            raise DecisionRegistryError(
                "Invalidation event must have a non-empty reason"
            )

        event_type = InvalidationEventType(data["event_type"])

        if event_type == InvalidationEventType.GIT_COMMIT:
            if not data.get("git_commit"):
                raise DecisionRegistryError(
                    "GIT_COMMIT invalidation event must include git_commit"
                )

        if event_type == InvalidationEventType.STRUCTURED_VERDICT:
            if not data.get("evidence"):
                raise DecisionRegistryError(
                    "STRUCTURED_VERDICT invalidation event must include evidence"
                )

        return InvalidationEvent(
            event_type=event_type,
            timestamp=data["timestamp"],
            reason=reason,
            evidence=data.get("evidence", []),
            git_commit=data.get("git_commit"),
            actor=data.get("actor"),
        )


@dataclass(frozen=True)
class DecisionHistory:
    """History entry for a decision."""

    timestamp: str
    status_before: DecisionStatus
    status_after: DecisionStatus
    event: InvalidationEvent | None = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "status_before": self.status_before.value,
            "status_after": self.status_after.value,
            "event": self.event.to_dict() if self.event else None,
            "note": self.note,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DecisionHistory:
        """Create from dictionary."""
        event = None
        if data.get("event"):
            event = InvalidationEvent.from_dict(data["event"])
        return DecisionHistory(
            timestamp=data["timestamp"],
            status_before=DecisionStatus(data["status_before"]),
            status_after=DecisionStatus(data["status_after"]),
            event=event,
            note=data.get("note", ""),
        )


@dataclass(frozen=True)
class Decision:
    """Represents a single decision in the registry."""

    identifier: str
    scope: DecisionScope
    statement: str
    proofs: list[str]
    status: DecisionStatus
    entity_id: str
    created_at: str
    created_by: str | None = None
    history: list[DecisionHistory] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with enums as their values."""
        data = asdict(self)
        data["scope"] = self.scope.value
        data["status"] = self.status.value
        data["history"] = [h.to_dict() for h in self.history]
        return data

    def immutable_hash(self) -> str:
        """Generate an immutable hash of the decision core (excluding history)."""
        core_data = {
            "identifier": self.identifier,
            "scope": self.scope.value,
            "statement": self.statement,
            "proofs": self.proofs,
            "entity_id": self.entity_id,
            "created_at": self.created_at,
        }
        content = json.dumps(core_data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode()).hexdigest()

    def is_active(self) -> bool:
        """Check if this decision is currently active."""
        return self.status == DecisionStatus.ACTIVE

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Decision:
        """Create from dictionary."""
        history = []
        if "history" in data:
            history = [DecisionHistory.from_dict(h) for h in data["history"]]

        return Decision(
            identifier=data["identifier"],
            scope=DecisionScope(data["scope"]),
            statement=data["statement"],
            proofs=data["proofs"],
            status=DecisionStatus(data["status"]),
            entity_id=data["entity_id"],
            created_at=data["created_at"],
            created_by=data.get("created_by"),
            history=history,
        )


@dataclass
class DecisionRegistry:
    """Registry for managing decisions and constraints."""

    decisions: dict[str, Decision] = field(default_factory=dict)
    scope_index: dict[str, list[str]] = field(default_factory=dict)
    entity_index: dict[str, list[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate after initialization."""
        for decision_id, decision in self.decisions.items():
            if decision_id != decision.identifier:
                raise DecisionRegistryError(
                    f"Decision ID mismatch: {decision_id} != {decision.identifier}"
                )

    def add_decision(
        self,
        scope: DecisionScope,
        statement: str,
        proofs: list[str],
        entity_id: str,
        created_by: str | None = None,
        identifier: str | None = None,
    ) -> Decision:
        """Add a new decision to the registry."""
        if not statement:
            raise DecisionRegistryError("Decision statement cannot be empty")
        if not proofs:
            raise DecisionRegistryError("Decision must have at least one proof")
        if not entity_id:
            raise DecisionRegistryError("Decision must be linked to an entity")

        decision_id = identifier or f"DEC-{uuid4().hex[:8].upper()}"

        if decision_id in self.decisions:
            raise DecisionRegistryError(
                f"Decision with ID {decision_id} already exists"
            )

        now = datetime.now(timezone.utc).isoformat()
        decision = Decision(
            identifier=decision_id,
            scope=scope,
            statement=statement,
            proofs=proofs,
            status=DecisionStatus.ACTIVE,
            entity_id=entity_id,
            created_at=now,
            created_by=created_by,
            history=[],
        )

        self.decisions[decision_id] = decision
        self._update_indices(decision_id, decision)

        return decision

    def invalidate_decision(
        self,
        decision_id: str,
        event: InvalidationEvent,
    ) -> Decision:
        """Invalidate a decision with a structured event."""
        if decision_id not in self.decisions:
            raise DecisionRegistryError(f"Decision {decision_id} not found")

        old_decision = self.decisions[decision_id]

        if old_decision.status == DecisionStatus.INVALIDATED:
            raise DecisionRegistryError(f"Decision {decision_id} is already invalidated")

        now = datetime.now(timezone.utc).isoformat()
        history_entry = DecisionHistory(
            timestamp=now,
            status_before=old_decision.status,
            status_after=DecisionStatus.INVALIDATED,
            event=event,
        )

        new_history = list(old_decision.history) + [history_entry]

        new_decision = Decision(
            identifier=old_decision.identifier,
            scope=old_decision.scope,
            statement=old_decision.statement,
            proofs=old_decision.proofs,
            status=DecisionStatus.INVALIDATED,
            entity_id=old_decision.entity_id,
            created_at=old_decision.created_at,
            created_by=old_decision.created_by,
            history=new_history,
        )

        self.decisions[decision_id] = new_decision
        return new_decision

    def get_decision(self, decision_id: str) -> Decision | None:
        """Retrieve a decision by ID."""
        return self.decisions.get(decision_id)

    def get_decisions_by_scope(self, scope: DecisionScope) -> list[Decision]:
        """Get all decisions for a given scope."""
        decision_ids = self.scope_index.get(scope.value, [])
        return [
            self.decisions[did]
            for did in decision_ids
            if did in self.decisions and self.decisions[did].is_active()
        ]

    def get_constraints_for_entity(self, entity_id: str) -> list[Decision]:
        """Get all active constraints (decisions) for an entity."""
        decision_ids = self.entity_index.get(entity_id, [])
        return [
            self.decisions[did]
            for did in decision_ids
            if did in self.decisions and self.decisions[did].is_active()
        ]

    def get_constraints_for_correction(
        self,
        entity_id: str,
        scope: DecisionScope | None = None,
    ) -> list[Decision]:
        """Get relevant constraints for a correction operation."""
        constraints = self.get_constraints_for_entity(entity_id)

        if scope:
            constraints = [c for c in constraints if c.scope == scope]

        return sorted(constraints, key=lambda c: c.created_at)

    def get_constraints_for_correction_with_context(
        self,
        context: CorrectionContext,
    ) -> list[Decision]:
        """Get all relevant constraints for a correction with hierarchical context.

        This method aggregates constraints from the correction's own entity
        and from related entities at other scope levels (e.g., parent product,
        parent feature, task requirements, incident context).

        Args:
            context: CorrectionContext with entity_id, scope, and related_entities

        Returns:
            List of active Decision constraints, deduplicated and sorted by creation time
        """
        constraints: dict[str, Decision] = {}

        for scope, entity_id in context.get_all_entity_ids():
            entity_constraints = self.get_constraints_for_entity(entity_id)
            for constraint in entity_constraints:
                constraints[constraint.identifier] = constraint

        return sorted(constraints.values(), key=lambda c: c.created_at)

    def _update_indices(self, decision_id: str, decision: Decision) -> None:
        """Update scope and entity indices."""
        scope_key = decision.scope.value
        if scope_key not in self.scope_index:
            self.scope_index[scope_key] = []
        if decision_id not in self.scope_index[scope_key]:
            self.scope_index[scope_key].append(decision_id)

        entity_key = decision.entity_id
        if entity_key not in self.entity_index:
            self.entity_index[entity_key] = []
        if decision_id not in self.entity_index[entity_key]:
            self.entity_index[entity_key].append(decision_id)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "decisions": {
                did: d.to_dict() for did, d in self.decisions.items()
            },
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DecisionRegistry:
        """Create from dictionary."""
        registry = DecisionRegistry()

        for decision_data in data.get("decisions", {}).values():
            decision = Decision.from_dict(decision_data)
            registry.decisions[decision.identifier] = decision
            registry._update_indices(decision.identifier, decision)

        return registry

    def save_to_file(self, path: Path | str) -> None:
        """Save registry to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def load_from_file(path: Path | str) -> DecisionRegistry:
        """Load registry from a JSON file."""
        path = Path(path)
        if not path.exists():
            raise DecisionRegistryError(f"Registry file not found: {path}")

        with open(path) as f:
            data = json.load(f)

        return DecisionRegistry.from_dict(data)

    def get_all_active_decisions(self) -> list[Decision]:
        """Get all active decisions in the registry."""
        return [d for d in self.decisions.values() if d.is_active()]

    def get_invalidation_history(self, decision_id: str) -> list[DecisionHistory]:
        """Get the invalidation history for a decision."""
        decision = self.get_decision(decision_id)
        if not decision:
            raise DecisionRegistryError(f"Decision {decision_id} not found")

        return decision.history
