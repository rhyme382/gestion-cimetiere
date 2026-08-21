import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from autodev.decision_registry import (
    DecisionRegistry,
    DecisionRegistryError,
    Decision,
    DecisionStatus,
    DecisionScope,
    InvalidationEvent,
    InvalidationEventType,
    DecisionHistory,
    CorrectionContext,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def empty_registry():
    return DecisionRegistry()


@pytest.fixture
def populated_registry():
    registry = DecisionRegistry()
    registry.add_decision(
        scope=DecisionScope.FEATURE,
        statement="Use async/await pattern throughout",
        proofs=["code-review-321", "performance-benchmark-15%"],
        entity_id="FEATURE-001",
        created_by="supervisor@example.com",
    )
    registry.add_decision(
        scope=DecisionScope.TASK,
        statement="Database must use PostgreSQL 14+",
        proofs=["requirements-doc-v2", "compatibility-matrix"],
        entity_id="TASK-042",
        created_by="db-architect@example.com",
    )
    return registry


class TestDecisionStatus:
    def test_status_values(self):
        assert DecisionStatus.ACTIVE.value == "active"
        assert DecisionStatus.INVALIDATED.value == "invalidated"
        assert DecisionStatus.PENDING.value == "pending"
        assert DecisionStatus.OBSOLETE.value == "obsolete"

    def test_status_from_string(self):
        assert DecisionStatus("active") == DecisionStatus.ACTIVE
        assert DecisionStatus("invalidated") == DecisionStatus.INVALIDATED


class TestDecisionScope:
    def test_scope_values(self):
        assert DecisionScope.PRODUCT.value == "product"
        assert DecisionScope.FEATURE.value == "feature"
        assert DecisionScope.TASK.value == "task"
        assert DecisionScope.REQUIREMENT.value == "requirement"
        assert DecisionScope.INCIDENT.value == "incident"

    def test_scope_from_string(self):
        assert DecisionScope("product") == DecisionScope.PRODUCT
        assert DecisionScope("incident") == DecisionScope.INCIDENT


class TestInvalidationEventType:
    def test_event_types_defined(self):
        expected = {
            "structured_verdict",
            "git_commit",
            "policy_change",
            "human_override",
            "incident_discovery",
        }
        actual = {et.value for et in InvalidationEventType}
        assert actual == expected


class TestInvalidationEvent:
    @pytest.fixture
    def sample_event(self):
        return InvalidationEvent(
            event_type=InvalidationEventType.STRUCTURED_VERDICT,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason="Architectural constraint no longer applicable",
            evidence=["design-review-report", "migration-plan"],
            git_commit="abc123def456",
            actor="lead-dev@example.com",
        )

    def test_event_creation(self, sample_event):
        assert sample_event.event_type == InvalidationEventType.STRUCTURED_VERDICT
        assert sample_event.reason == "Architectural constraint no longer applicable"
        assert len(sample_event.evidence) == 2

    def test_event_to_dict(self, sample_event):
        data = sample_event.to_dict()
        assert data["event_type"] == "structured_verdict"
        assert data["reason"] == "Architectural constraint no longer applicable"
        assert data["git_commit"] == "abc123def456"

    def test_event_from_dict(self, sample_event):
        data = sample_event.to_dict()
        restored = InvalidationEvent.from_dict(data)
        assert restored.event_type == sample_event.event_type
        assert restored.reason == sample_event.reason
        assert restored.evidence == sample_event.evidence

    def test_event_rejects_empty_reason(self):
        with pytest.raises(DecisionRegistryError) as exc_info:
            InvalidationEvent(
                event_type=InvalidationEventType.STRUCTURED_VERDICT,
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason="",
                evidence=["proof"],
            )
        assert "non-empty reason" in str(exc_info.value)

    def test_event_rejects_whitespace_only_reason(self):
        with pytest.raises(DecisionRegistryError) as exc_info:
            InvalidationEvent(
                event_type=InvalidationEventType.STRUCTURED_VERDICT,
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason="   ",
                evidence=["proof"],
            )
        assert "non-empty reason" in str(exc_info.value)

    def test_event_rejects_structured_verdict_without_evidence(self):
        with pytest.raises(DecisionRegistryError) as exc_info:
            InvalidationEvent(
                event_type=InvalidationEventType.STRUCTURED_VERDICT,
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason="Some reason",
                evidence=[],
            )
        assert "STRUCTURED_VERDICT" in str(exc_info.value) and "evidence" in str(exc_info.value)

    def test_event_rejects_git_commit_without_hash(self):
        with pytest.raises(DecisionRegistryError) as exc_info:
            InvalidationEvent(
                event_type=InvalidationEventType.GIT_COMMIT,
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason="Committed change",
                git_commit=None,
            )
        assert "GIT_COMMIT" in str(exc_info.value) and "git_commit" in str(exc_info.value)

    def test_event_from_dict_rejects_empty_reason(self):
        with pytest.raises(DecisionRegistryError) as exc_info:
            InvalidationEvent.from_dict({
                "event_type": "structured_verdict",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "",
                "evidence": ["proof"],
            })
        assert "non-empty reason" in str(exc_info.value)

    def test_event_from_dict_rejects_structured_verdict_without_evidence(self):
        with pytest.raises(DecisionRegistryError) as exc_info:
            InvalidationEvent.from_dict({
                "event_type": "structured_verdict",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "Some reason",
                "evidence": [],
            })
        assert "STRUCTURED_VERDICT" in str(exc_info.value) and "evidence" in str(exc_info.value)

    def test_event_from_dict_rejects_git_commit_without_hash(self):
        with pytest.raises(DecisionRegistryError) as exc_info:
            InvalidationEvent.from_dict({
                "event_type": "git_commit",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "Committed change",
            })
        assert "GIT_COMMIT" in str(exc_info.value) and "git_commit" in str(exc_info.value)


class TestDecisionHistory:
    @pytest.fixture
    def sample_event(self):
        return InvalidationEvent(
            event_type=InvalidationEventType.STRUCTURED_VERDICT,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason="No longer valid",
            evidence=[],
        )

    @pytest.fixture
    def sample_history(self):
        event = InvalidationEvent(
            event_type=InvalidationEventType.STRUCTURED_VERDICT,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason="No longer valid",
            evidence=["review-doc"],
        )
        return DecisionHistory(
            timestamp=datetime.now(timezone.utc).isoformat(),
            status_before=DecisionStatus.ACTIVE,
            status_after=DecisionStatus.INVALIDATED,
            event=event,
            note="Invalidated due to architectural review",
        )

    def test_history_creation(self, sample_history):
        assert sample_history.status_before == DecisionStatus.ACTIVE
        assert sample_history.status_after == DecisionStatus.INVALIDATED
        assert sample_history.note == "Invalidated due to architectural review"

    def test_history_to_dict(self, sample_history):
        data = sample_history.to_dict()
        assert data["status_before"] == "active"
        assert data["status_after"] == "invalidated"
        assert data["event"]["event_type"] == "structured_verdict"

    def test_history_from_dict(self, sample_history):
        data = sample_history.to_dict()
        restored = DecisionHistory.from_dict(data)
        assert restored.status_before == sample_history.status_before
        assert restored.status_after == sample_history.status_after
        assert restored.event is not None


class TestDecision:
    @pytest.fixture
    def sample_decision(self):
        return Decision(
            identifier="DEC-ABC12345",
            scope=DecisionScope.FEATURE,
            statement="Use Redis for caching",
            proofs=["perf-test-results", "cost-analysis"],
            status=DecisionStatus.ACTIVE,
            entity_id="FEATURE-123",
            created_at=datetime.now(timezone.utc).isoformat(),
            created_by="architect@example.com",
        )

    def test_decision_creation(self, sample_decision):
        assert sample_decision.identifier == "DEC-ABC12345"
        assert sample_decision.scope == DecisionScope.FEATURE
        assert sample_decision.is_active()

    def test_decision_frozen(self, sample_decision):
        with pytest.raises(AttributeError):
            sample_decision.statement = "Changed statement"

    def test_decision_to_dict(self, sample_decision):
        data = sample_decision.to_dict()
        assert data["identifier"] == "DEC-ABC12345"
        assert data["scope"] == "feature"
        assert data["status"] == "active"
        assert data["proofs"] == ["perf-test-results", "cost-analysis"]

    def test_decision_from_dict(self, sample_decision):
        data = sample_decision.to_dict()
        restored = Decision.from_dict(data)
        assert restored.identifier == sample_decision.identifier
        assert restored.scope == sample_decision.scope
        assert restored.statement == sample_decision.statement

    def test_decision_immutable_hash(self, sample_decision):
        hash1 = sample_decision.immutable_hash()
        hash2 = sample_decision.immutable_hash()
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_decision_status_checks(self):
        active = Decision(
            identifier="DEC-1",
            scope=DecisionScope.PRODUCT,
            statement="Test",
            proofs=["proof"],
            status=DecisionStatus.ACTIVE,
            entity_id="PROD-1",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        assert active.is_active()

        invalidated = Decision(
            identifier="DEC-2",
            scope=DecisionScope.PRODUCT,
            statement="Test",
            proofs=["proof"],
            status=DecisionStatus.INVALIDATED,
            entity_id="PROD-2",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        assert not invalidated.is_active()


class TestDecisionRegistry:
    def test_empty_registry_creation(self, empty_registry):
        assert len(empty_registry.decisions) == 0
        assert empty_registry.get_all_active_decisions() == []

    def test_add_decision(self, empty_registry):
        decision = empty_registry.add_decision(
            scope=DecisionScope.FEATURE,
            statement="Use async patterns",
            proofs=["review-doc"],
            entity_id="FEATURE-001",
            created_by="dev@example.com",
        )

        assert decision.identifier.startswith("DEC-")
        assert decision.scope == DecisionScope.FEATURE
        assert decision.status == DecisionStatus.ACTIVE
        assert decision in empty_registry.get_all_active_decisions()

    def test_add_decision_with_custom_identifier(self, empty_registry):
        decision = empty_registry.add_decision(
            scope=DecisionScope.REQUIREMENT,
            statement="Must support GDPR",
            proofs=["legal-review"],
            entity_id="REQ-042",
            identifier="DEC-GDPR-001",
        )

        assert decision.identifier == "DEC-GDPR-001"
        assert empty_registry.get_decision("DEC-GDPR-001") is not None

    def test_add_decision_validation_empty_statement(self, empty_registry):
        with pytest.raises(DecisionRegistryError) as exc_info:
            empty_registry.add_decision(
                scope=DecisionScope.FEATURE,
                statement="",
                proofs=["proof"],
                entity_id="FEATURE-001",
            )
        assert "statement cannot be empty" in str(exc_info.value)

    def test_add_decision_validation_no_proofs(self, empty_registry):
        with pytest.raises(DecisionRegistryError) as exc_info:
            empty_registry.add_decision(
                scope=DecisionScope.FEATURE,
                statement="Test decision",
                proofs=[],
                entity_id="FEATURE-001",
            )
        assert "at least one proof" in str(exc_info.value)

    def test_add_decision_validation_no_entity_id(self, empty_registry):
        with pytest.raises(DecisionRegistryError) as exc_info:
            empty_registry.add_decision(
                scope=DecisionScope.FEATURE,
                statement="Test decision",
                proofs=["proof"],
                entity_id="",
            )
        assert "must be linked to an entity" in str(exc_info.value)

    def test_add_duplicate_decision_fails(self, empty_registry):
        empty_registry.add_decision(
            scope=DecisionScope.FEATURE,
            statement="Test",
            proofs=["proof"],
            entity_id="FEATURE-001",
            identifier="DEC-UNIQUE",
        )

        with pytest.raises(DecisionRegistryError) as exc_info:
            empty_registry.add_decision(
                scope=DecisionScope.FEATURE,
                statement="Another",
                proofs=["proof"],
                entity_id="FEATURE-002",
                identifier="DEC-UNIQUE",
            )
        assert "already exists" in str(exc_info.value)

    def test_get_decision(self, populated_registry):
        decisions = populated_registry.get_all_active_decisions()
        assert len(decisions) == 2

        decision = populated_registry.get_decision(decisions[0].identifier)
        assert decision is not None
        assert decision.scope in [DecisionScope.FEATURE, DecisionScope.TASK]

    def test_get_decision_not_found(self, empty_registry):
        assert empty_registry.get_decision("DEC-NONEXISTENT") is None

    def test_get_decisions_by_scope(self, populated_registry):
        feature_decisions = populated_registry.get_decisions_by_scope(DecisionScope.FEATURE)
        assert len(feature_decisions) == 1
        assert feature_decisions[0].scope == DecisionScope.FEATURE

        task_decisions = populated_registry.get_decisions_by_scope(DecisionScope.TASK)
        assert len(task_decisions) == 1
        assert task_decisions[0].scope == DecisionScope.TASK

    def test_get_constraints_for_entity(self, populated_registry):
        constraints = populated_registry.get_constraints_for_entity("FEATURE-001")
        assert len(constraints) == 1
        assert constraints[0].entity_id == "FEATURE-001"

    def test_get_constraints_for_correction(self, populated_registry):
        constraints = populated_registry.get_constraints_for_correction(
            entity_id="FEATURE-001"
        )
        assert len(constraints) == 1

        constraints_with_scope = populated_registry.get_constraints_for_correction(
            entity_id="FEATURE-001",
            scope=DecisionScope.FEATURE,
        )
        assert len(constraints_with_scope) == 1

    def test_get_constraints_excludes_inactive(self, populated_registry):
        decisions = populated_registry.get_all_active_decisions()
        decision_id = decisions[0].identifier

        event = InvalidationEvent(
            event_type=InvalidationEventType.STRUCTURED_VERDICT,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason="No longer applicable",
            evidence=["architectural-review"],
        )
        populated_registry.invalidate_decision(decision_id, event)

        constraints = populated_registry.get_constraints_for_entity(decisions[0].entity_id)
        assert len(constraints) == 0

    def test_invalidate_decision(self, populated_registry):
        decisions = populated_registry.get_all_active_decisions()
        decision_id = decisions[0].identifier
        original_entity_id = decisions[0].entity_id

        event = InvalidationEvent(
            event_type=InvalidationEventType.HUMAN_OVERRIDE,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason="Architecture changed in design review",
            evidence=["design-review-minutes", "stakeholder-approval"],
            actor="lead-architect@example.com",
        )

        invalidated = populated_registry.invalidate_decision(decision_id, event)

        assert invalidated.status == DecisionStatus.INVALIDATED
        assert len(invalidated.history) == 1
        assert invalidated.history[0].status_before == DecisionStatus.ACTIVE
        assert invalidated.history[0].status_after == DecisionStatus.INVALIDATED
        assert invalidated.history[0].event is not None

        constraints = populated_registry.get_constraints_for_entity(original_entity_id)
        assert len(constraints) == 0

    def test_invalidate_nonexistent_decision(self, populated_registry):
        event = InvalidationEvent(
            event_type=InvalidationEventType.STRUCTURED_VERDICT,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason="Test",
            evidence=["test-evidence"],
        )

        with pytest.raises(DecisionRegistryError) as exc_info:
            populated_registry.invalidate_decision("DEC-NONEXISTENT", event)
        assert "not found" in str(exc_info.value)

    def test_invalidate_already_invalidated_decision(self, populated_registry):
        decisions = populated_registry.get_all_active_decisions()
        decision_id = decisions[0].identifier

        event1 = InvalidationEvent(
            event_type=InvalidationEventType.STRUCTURED_VERDICT,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason="First invalidation",
            evidence=["review-doc"],
        )
        populated_registry.invalidate_decision(decision_id, event1)

        event2 = InvalidationEvent(
            event_type=InvalidationEventType.STRUCTURED_VERDICT,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason="Second invalidation",
            evidence=["second-review"],
        )

        with pytest.raises(DecisionRegistryError) as exc_info:
            populated_registry.invalidate_decision(decision_id, event2)
        assert "already invalidated" in str(exc_info.value)

    def test_get_invalidation_history(self, populated_registry):
        decisions = populated_registry.get_all_active_decisions()
        decision_id = decisions[0].identifier

        history_before = populated_registry.get_invalidation_history(decision_id)
        assert len(history_before) == 0

        event = InvalidationEvent(
            event_type=InvalidationEventType.GIT_COMMIT,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason="Committed change invalidates decision",
            evidence=["commit-sha"],
            git_commit="abc123def456",
        )
        populated_registry.invalidate_decision(decision_id, event)

        history_after = populated_registry.get_invalidation_history(decision_id)
        assert len(history_after) == 1
        assert history_after[0].event is not None

    def test_registry_to_dict(self, populated_registry):
        data = populated_registry.to_dict()
        assert "decisions" in data
        assert len(data["decisions"]) == 2

    def test_registry_from_dict(self, populated_registry):
        original_data = populated_registry.to_dict()
        restored = DecisionRegistry.from_dict(original_data)

        assert len(restored.decisions) == len(populated_registry.decisions)
        assert restored.get_all_active_decisions() == populated_registry.get_all_active_decisions()

    def test_registry_persistence(self, temp_dir):
        registry = DecisionRegistry()
        registry.add_decision(
            scope=DecisionScope.PRODUCT,
            statement="Use PostgreSQL database",
            proofs=["requirements-doc"],
            entity_id="PROD-001",
            created_by="db-team@example.com",
        )

        file_path = temp_dir / "decisions.json"
        registry.save_to_file(file_path)
        assert file_path.exists()

        loaded = DecisionRegistry.load_from_file(file_path)
        assert len(loaded.decisions) == 1
        assert len(loaded.get_all_active_decisions()) == 1

    def test_registry_load_nonexistent_file(self, temp_dir):
        with pytest.raises(DecisionRegistryError) as exc_info:
            DecisionRegistry.load_from_file(temp_dir / "nonexistent.json")
        assert "not found" in str(exc_info.value)

    def test_registry_with_multiple_scopes(self, empty_registry):
        empty_registry.add_decision(
            scope=DecisionScope.PRODUCT,
            statement="Statement 1",
            proofs=["proof1"],
            entity_id="PROD-001",
        )
        empty_registry.add_decision(
            scope=DecisionScope.FEATURE,
            statement="Statement 2",
            proofs=["proof2"],
            entity_id="FEATURE-001",
        )
        empty_registry.add_decision(
            scope=DecisionScope.INCIDENT,
            statement="Statement 3",
            proofs=["proof3"],
            entity_id="INC-001",
        )

        product_decisions = empty_registry.get_decisions_by_scope(DecisionScope.PRODUCT)
        feature_decisions = empty_registry.get_decisions_by_scope(DecisionScope.FEATURE)
        incident_decisions = empty_registry.get_decisions_by_scope(DecisionScope.INCIDENT)

        assert len(product_decisions) == 1
        assert len(feature_decisions) == 1
        assert len(incident_decisions) == 1

    def test_registry_index_consistency(self, empty_registry):
        dec1 = empty_registry.add_decision(
            scope=DecisionScope.TASK,
            statement="Test",
            proofs=["proof"],
            entity_id="TASK-001",
        )

        entity_constraints = empty_registry.get_constraints_for_entity("TASK-001")
        assert len(entity_constraints) == 1
        assert entity_constraints[0].identifier == dec1.identifier

    def test_multiple_invalidations_tracked(self, empty_registry):
        decision = empty_registry.add_decision(
            scope=DecisionScope.REQUIREMENT,
            statement="Must use TLS 1.2+",
            proofs=["security-policy"],
            entity_id="REQ-SEC-001",
        )

        assert decision.status == DecisionStatus.ACTIVE

        event = InvalidationEvent(
            event_type=InvalidationEventType.POLICY_CHANGE,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason="Security policy updated to require TLS 1.3+",
            evidence=["security-policy-v2"],
            actor="ciso@example.com",
        )
        invalidated = empty_registry.invalidate_decision(decision.identifier, event)

        assert invalidated.status == DecisionStatus.INVALIDATED
        assert len(invalidated.history) == 1

        retrieved = empty_registry.get_decision(decision.identifier)
        assert retrieved.status == DecisionStatus.INVALIDATED
        assert len(retrieved.history) == 1

    def test_constraints_sorted_by_creation(self, empty_registry):
        entity_id = "ENTITY-001"

        for i in range(3):
            empty_registry.add_decision(
                scope=DecisionScope.FEATURE,
                statement=f"Decision {i}",
                proofs=[f"proof-{i}"],
                entity_id=entity_id,
            )

        constraints = empty_registry.get_constraints_for_correction(entity_id)
        assert len(constraints) == 3

        for i in range(len(constraints) - 1):
            assert constraints[i].created_at <= constraints[i + 1].created_at


class TestCorrectionContext:
    def test_context_creation(self):
        context = CorrectionContext(
            entity_id="TASK-001",
            scope=DecisionScope.TASK,
            related_entities={
                DecisionScope.FEATURE: "FEATURE-001",
                DecisionScope.PRODUCT: "PRODUCT-001",
            },
        )
        assert context.entity_id == "TASK-001"
        assert context.scope == DecisionScope.TASK

    def test_context_get_all_entity_ids(self):
        context = CorrectionContext(
            entity_id="TASK-001",
            scope=DecisionScope.TASK,
            related_entities={
                DecisionScope.FEATURE: "FEATURE-001",
                DecisionScope.PRODUCT: "PRODUCT-001",
            },
        )
        entity_ids = context.get_all_entity_ids()
        assert len(entity_ids) == 3
        scopes = {scope for scope, _ in entity_ids}
        assert scopes == {DecisionScope.TASK, DecisionScope.FEATURE, DecisionScope.PRODUCT}

    def test_context_without_related_entities(self):
        context = CorrectionContext(
            entity_id="TASK-001",
            scope=DecisionScope.TASK,
        )
        entity_ids = context.get_all_entity_ids()
        assert len(entity_ids) == 1
        assert entity_ids[0] == (DecisionScope.TASK, "TASK-001")


class TestMultiLevelConstraints:
    def test_get_constraints_for_correction_with_context_single_level(self):
        registry = DecisionRegistry()
        registry.add_decision(
            scope=DecisionScope.TASK,
            statement="Use Python 3.11+",
            proofs=["requirements-doc"],
            entity_id="TASK-001",
        )

        context = CorrectionContext(
            entity_id="TASK-001",
            scope=DecisionScope.TASK,
        )
        constraints = registry.get_constraints_for_correction_with_context(context)

        assert len(constraints) == 1
        assert constraints[0].entity_id == "TASK-001"

    def test_get_constraints_for_correction_with_context_multi_level(self):
        registry = DecisionRegistry()

        product_dec = registry.add_decision(
            scope=DecisionScope.PRODUCT,
            statement="Use PostgreSQL",
            proofs=["architecture-doc"],
            entity_id="PRODUCT-001",
        )

        feature_dec = registry.add_decision(
            scope=DecisionScope.FEATURE,
            statement="Implement caching layer",
            proofs=["design-review"],
            entity_id="FEATURE-001",
        )

        task_dec = registry.add_decision(
            scope=DecisionScope.TASK,
            statement="Use async/await",
            proofs=["code-review"],
            entity_id="TASK-001",
        )

        context = CorrectionContext(
            entity_id="TASK-001",
            scope=DecisionScope.TASK,
            related_entities={
                DecisionScope.FEATURE: "FEATURE-001",
                DecisionScope.PRODUCT: "PRODUCT-001",
            },
        )

        constraints = registry.get_constraints_for_correction_with_context(context)

        assert len(constraints) == 3
        decision_ids = {c.identifier for c in constraints}
        assert decision_ids == {product_dec.identifier, feature_dec.identifier, task_dec.identifier}

    def test_get_constraints_for_correction_with_context_deduplication(self):
        registry = DecisionRegistry()

        decision1 = registry.add_decision(
            scope=DecisionScope.TASK,
            statement="Statement 1",
            proofs=["proof1"],
            entity_id="TASK-001",
        )

        decision2 = registry.add_decision(
            scope=DecisionScope.FEATURE,
            statement="Statement 2",
            proofs=["proof2"],
            entity_id="FEATURE-001",
        )

        context = CorrectionContext(
            entity_id="TASK-001",
            scope=DecisionScope.TASK,
            related_entities={
                DecisionScope.FEATURE: "FEATURE-001",
            },
        )

        constraints = registry.get_constraints_for_correction_with_context(context)

        assert len(constraints) == 2
        identifiers = [c.identifier for c in constraints]
        assert len(identifiers) == len(set(identifiers))

    def test_get_constraints_for_correction_with_context_excludes_inactive(self):
        registry = DecisionRegistry()

        active_dec = registry.add_decision(
            scope=DecisionScope.TASK,
            statement="Active decision",
            proofs=["proof"],
            entity_id="TASK-001",
        )

        invalidated_dec = registry.add_decision(
            scope=DecisionScope.FEATURE,
            statement="Invalidated decision",
            proofs=["proof"],
            entity_id="FEATURE-001",
        )

        event = InvalidationEvent(
            event_type=InvalidationEventType.STRUCTURED_VERDICT,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason="No longer applicable",
            evidence=["review"],
        )
        registry.invalidate_decision(invalidated_dec.identifier, event)

        context = CorrectionContext(
            entity_id="TASK-001",
            scope=DecisionScope.TASK,
            related_entities={
                DecisionScope.FEATURE: "FEATURE-001",
            },
        )

        constraints = registry.get_constraints_for_correction_with_context(context)

        assert len(constraints) == 1
        assert constraints[0].identifier == active_dec.identifier

    def test_get_constraints_for_correction_with_context_sorted_by_creation(self):
        registry = DecisionRegistry()

        decs = []
        for i in range(3):
            dec = registry.add_decision(
                scope=DecisionScope.TASK if i == 0 else DecisionScope.FEATURE,
                statement=f"Decision {i}",
                proofs=[f"proof-{i}"],
                entity_id="TASK-001" if i == 0 else "FEATURE-001",
            )
            decs.append(dec)

        context = CorrectionContext(
            entity_id="TASK-001",
            scope=DecisionScope.TASK,
            related_entities={
                DecisionScope.FEATURE: "FEATURE-001",
            },
        )

        constraints = registry.get_constraints_for_correction_with_context(context)

        assert len(constraints) == 3
        for i in range(len(constraints) - 1):
            assert constraints[i].created_at <= constraints[i + 1].created_at
