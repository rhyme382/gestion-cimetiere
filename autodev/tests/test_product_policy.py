import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from autodev.product_actions import (
    ProductActionRegistry,
    ActionCategory,
    get_action_registry,
    ProductActionError,
)
from autodev.product_policy import (
    ExecutionContext,
    ProductPolicyEngine,
    ProductPolicy,
    PolicyFacts,
    RecordedDecision,
    DecisionType,
    ActionExecutionContext,
    TypedActionExecutor,
    ProductPolicyError,
)


@pytest.fixture
def default_facts():
    """Return facts with all booleans false."""
    return PolicyFacts()


@pytest.fixture
def default_policy():
    return ProductPolicy(
        schema_version="1.0.0",
        plan_id="test-plan",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def policy_engine(default_policy):
    """Fresh engine for each test to avoid memoization issues."""
    return ProductPolicyEngine(policy=default_policy)


def make_engine(policy=None):
    """Helper to create fresh engine without memoization cache."""
    if policy is None:
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    return ProductPolicyEngine(policy=policy)


@pytest.fixture
def executor():
    return TypedActionExecutor()


class TestActionRegistry:
    """Test that action registry is closed and complete."""

    def test_registry_has_all_required_actions(self):
        registry = get_action_registry()
        required_actions = {
            "WAIT_PROVIDER_RESET",
            "RECONCILE_WORKTREE",
            "PRESERVE_PARTIAL_CHANGES",
            "REGENERATE_TASK_REPORT",
            "REQUEST_SCOPE_EXTENSION",
            "APPLY_SCOPE_EXTENSION",
            "REQUEST_CRITERION_REALLOCATION",
            "APPLY_CRITERION_REALLOCATION",
            "RECOVER_AGENT_GIT_HISTORY",
            "RUN_BASELINE_VALIDATION",
            "REVALIDATE_TASK",
            "RESUME_FEATURE",
            "REQUEST_HUMAN",
            "INTEGRATE_FEATURE",
        }
        for action_id in required_actions:
            assert registry.validate_action_id(action_id), f"Missing action: {action_id}"

    def test_registry_contains_valid_action_map(self):
        registry = get_action_registry()
        assert len(registry.action_map) > 0
        assert len(registry.list_actions()) == len(registry.action_map)

    def test_actions_are_categorized(self):
        registry = get_action_registry()
        for action in registry.list_actions():
            assert isinstance(action.category, ActionCategory)
            assert action.category.value in [
                "workflow_control",
                "git_reconciliation",
                "data_preservation",
                "reporting",
                "scope_management",
                "ownership_management",
                "agent_recovery",
                "validation",
                "resumption",
                "integration",
                "human_escalation",
            ]

    def test_each_action_has_serializable_definition(self):
        registry = get_action_registry()
        for action in registry.list_actions():
            # Should serialize to dict without error
            action_dict = action.to_dict()
            assert action_dict["action_id"] == action.action_id
            assert "preconditions" in action_dict
            assert "authorization" in action_dict
            assert "inputs" in action_dict
            assert "scope" in action_dict
            assert "audit_trail" in action_dict
            assert "idempotence_rule" in action_dict
            assert "rollback_strategy" in action_dict
            assert "stop_reasons" in action_dict


class TestPolicyDeterminism:
    """Test that policy engine is deterministic."""

    def test_identical_facts_same_action(self, policy_engine, default_facts):
        """For identical facts, selection must be the same."""
        selection1 = policy_engine.select_action(default_facts)
        selection2 = policy_engine.select_action(default_facts)

        assert selection1.selected_action_id == selection2.selected_action_id
        assert selection1.justification == selection2.justification

    def test_identical_facts_and_decisions_same_action(self, policy_engine, default_facts):
        """For identical facts and decisions, selection must be the same."""
        decision = RecordedDecision(
            decision_id="d001",
            decision_type=DecisionType.SCOPE_EXTENSION_APPROVED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data={"file": "test.py"},
        )
        decisions = [decision]

        selection1 = policy_engine.select_action(default_facts, decisions)
        selection2 = policy_engine.select_action(default_facts, decisions)

        assert selection1.selected_action_id == selection2.selected_action_id
        assert selection1.facts_hash == selection2.facts_hash
        assert selection1.decisions_hash == selection2.decisions_hash

    def test_different_facts_may_select_different_action(self, policy_engine):
        """Different facts may lead to different action selection."""
        facts1 = PolicyFacts(provider_quota_exceeded=True, retry_budget_exhausted=True)
        facts2 = PolicyFacts(
            operation_failed_midway=True,
            partial_changes_exist=True,
        )

        selection1 = policy_engine.select_action(facts1)
        selection2 = policy_engine.select_action(facts2)

        # Both should be valid actions, but may differ
        assert selection1.selected_action_id  # Some action selected
        assert selection2.selected_action_id  # Some action selected


class TestPreconditionChecking:
    """Test precondition validation."""

    def test_wait_provider_requires_quota_and_budget(self):
        """WAIT_PROVIDER_RESET requires specific preconditions."""
        engine = make_engine()
        # No preconditions met
        facts = PolicyFacts()
        selection = engine.select_action(facts)
        assert selection.selected_action_id != "WAIT_PROVIDER_RESET"

        # Preconditions met
        engine2 = make_engine()
        facts = PolicyFacts(
            provider_quota_exceeded=True,
            retry_budget_exhausted=True,
        )
        selection = engine2.select_action(facts)
        assert selection.selected_action_id == "WAIT_PROVIDER_RESET"

    def test_reconcile_requires_divergence_and_origin(self):
        """RECONCILE_WORKTREE requires Git state and origin."""
        engine = make_engine()
        facts = PolicyFacts(git_state_diverged=True, origin_reachable=True)
        selection = engine.select_action(facts)
        assert selection.selected_action_id == "RECONCILE_WORKTREE"

    def test_forbidden_states_block_action(self):
        """Forbidden states prevent action selection."""
        engine = make_engine()
        # RECONCILE_WORKTREE forbids merge_in_progress
        facts = PolicyFacts(
            git_state_diverged=True,
            origin_reachable=True,
            merge_in_progress=True,
        )
        selection = engine.select_action(facts)
        assert selection.selected_action_id != "RECONCILE_WORKTREE"


class TestAuthorizationEnforcement:
    """Test that authorization is enforced."""

    def test_no_authorization_required_for_default_actions(self):
        """Actions with NONE authorization are allowed by default."""
        engine = make_engine()
        facts = PolicyFacts(
            provider_quota_exceeded=True,
            retry_budget_exhausted=True,
        )
        selection = engine.select_action(facts)
        assert selection.authorization_allowed is True
        assert selection.selected_action_id == "WAIT_PROVIDER_RESET"

    def test_explicit_authorization_required_for_scope_extension(self):
        """APPLY_SCOPE_EXTENSION requires explicit policy."""
        facts = PolicyFacts(
            scope_extension_approved_by_policy=True,
            approval_recorded=True,
        )
        # Without policy authorization
        engine1 = make_engine()
        selection = engine1.select_action(facts)
        assert selection.selected_action_id != "APPLY_SCOPE_EXTENSION"

        # With policy authorization
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at=datetime.now(timezone.utc).isoformat(),
            allow_scope_extension=True,
        )
        engine2 = ProductPolicyEngine(policy=policy)
        selection = engine2.select_action(facts)
        assert selection.selected_action_id != "APPLY_SCOPE_EXTENSION"
        assert selection.authorization_allowed is False

    def test_recorded_decision_alone_does_not_allow_scope_extension(self):
        """A decision without runtime proof cannot select a scope extension."""
        engine = make_engine()
        facts = PolicyFacts(
            scope_extension_approved_by_policy=True,
            approval_recorded=True,
        )
        decision = RecordedDecision(
            decision_id="d001",
            decision_type=DecisionType.SCOPE_EXTENSION_APPROVED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data={"action_id": "APPLY_SCOPE_EXTENSION"},
        )
        selection = engine.select_action(facts, [decision])
        assert selection.selected_action_id != "APPLY_SCOPE_EXTENSION"
        assert selection.authorization_allowed is False


class TestPublicSensitiveActionSelection:
    """AC-R9-2 public selection uses the same blocking gates as execution."""

    @staticmethod
    def _policy(action_id):
        return ProductPolicy(
            schema_version="1.0.0", plan_id="T07", created_at="2026-01-01T00:00:00Z",
            allow_scope_extension=action_id == "APPLY_SCOPE_EXTENSION",
            allow_criterion_reallocation=action_id == "APPLY_CRITERION_REALLOCATION",
        )

    @staticmethod
    def _facts(action_id, **overrides):
        values = {
            "scope_extension_approved_by_policy": action_id == "APPLY_SCOPE_EXTENSION",
            "criterion_reallocation_approved_by_policy": action_id == "APPLY_CRITERION_REALLOCATION",
            "approval_recorded": True,
            "baseline_established": True,
        }
        values.update(overrides)
        return PolicyFacts(**values)

    @staticmethod
    def _execution(**overrides):
        values = {
            "entities_modified": 1, "modifications_audited": True,
            "modification_is_mechanical": True, "baseline_proof_available": True,
            "exactly_one_bounded_modification": True, "feature_id": "feature-7",
            "task_id": "T07", "target": "product-policy", "modification": "scope-guard",
        }
        values.update(overrides)
        return ExecutionContext(**values)

    @staticmethod
    def _inputs(action_id):
        if action_id == "APPLY_SCOPE_EXTENSION":
            return {
                "approval_id": "decision-1",
                "change_definition": {
                    "feature_id": "feature-7", "task_id": "T07",
                    "target": "product-policy", "modification": "scope-guard",
                },
            }
        return {"approval_id": "decision-1", "criterion": "R9", "new_owner": "supervisor"}

    @classmethod
    def _decision(cls, action_id, **overrides):
        data = {
            "action_id": action_id, "feature_id": "feature-7", "task_id": "T07",
            "target": "product-policy", "modification": "scope-guard",
        }
        if action_id == "APPLY_SCOPE_EXTENSION":
            data["change_definition"] = cls._inputs(action_id)["change_definition"]
        else:
            data.update({"criterion": "R9", "new_owner": "supervisor"})
        data.update(overrides)
        return RecordedDecision(
            decision_id="decision-1",
            decision_type=(DecisionType.SCOPE_EXTENSION_APPROVED
                           if action_id == "APPLY_SCOPE_EXTENSION"
                           else DecisionType.CRITERION_REALLOCATION_APPROVED),
            timestamp="2026-01-01T00:00:00Z", data=data,
        )

    @pytest.mark.parametrize("action_id", ["APPLY_SCOPE_EXTENSION", "APPLY_CRITERION_REALLOCATION"])
    def test_sensitive_action_is_refused_without_acquired_decision(self, action_id):
        selection = ProductPolicyEngine(policy=self._policy(action_id)).select_action(
            self._facts(action_id), execution_context=self._execution(),
            action_inputs={action_id: self._inputs(action_id)},
        )
        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert selection.authorization_allowed is False
        assert "decision" in selection.justification.lower()

    @pytest.mark.parametrize("identity_key", ["action_id", "feature_id", "task_id", "target", "modification"])
    def test_sensitive_action_is_refused_when_decision_identity_differs(self, identity_key):
        action_id = "APPLY_SCOPE_EXTENSION"
        overrides = {identity_key: "other"}
        if identity_key == "action_id":
            decision = self._decision("APPLY_CRITERION_REALLOCATION")
        else:
            decision = self._decision(action_id, **overrides)
        selection = ProductPolicyEngine(policy=self._policy(action_id)).select_action(
            self._facts(action_id), [decision],
            execution_context=self._execution(), action_inputs={action_id: self._inputs(action_id)},
        )
        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert selection.authorization_allowed is False
        assert "decision" in selection.justification.lower()

    @pytest.mark.parametrize("identity_key", ["feature_id", "task_id", "target", "modification"])
    def test_scope_extension_is_refused_when_change_definition_differs_from_context(self, identity_key):
        action_id = "APPLY_SCOPE_EXTENSION"
        inputs = self._inputs(action_id)
        inputs["change_definition"][identity_key] = "other"
        selection = ProductPolicyEngine(policy=self._policy(action_id)).select_action(
            self._facts(action_id), [self._decision(action_id, change_definition=inputs["change_definition"])],
            execution_context=self._execution(), action_inputs={action_id: inputs},
        )
        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert selection.authorization_allowed is False
        assert "definition" in selection.justification.lower() or "decision" in selection.justification.lower()

    @pytest.mark.parametrize(
        ("fact_overrides", "execution_overrides", "expected_reason"),
        [
            ({"baseline_established": False}, {}, "baseline"),
            ({}, {"baseline_proof_available": False}, "baseline"),
            ({}, {"modifications_audited": False}, "audit"),
            ({}, {"modification_is_mechanical": False}, "mechanical"),
            ({}, {"entities_modified": 2}, "scope"),
            ({}, {"exactly_one_bounded_modification": False}, "one bounded"),
            ({"ambiguous_functional_impact": True}, {}, "ambiguous"),
        ],
    )
    def test_sensitive_action_is_refused_for_each_runtime_gate(self, fact_overrides, execution_overrides, expected_reason):
        action_id = "APPLY_SCOPE_EXTENSION"
        selection = ProductPolicyEngine(policy=self._policy(action_id)).select_action(
            self._facts(action_id, **fact_overrides), [self._decision(action_id)],
            execution_context=self._execution(**execution_overrides),
            action_inputs={action_id: self._inputs(action_id)},
        )
        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert selection.authorization_allowed is False
        assert expected_reason in selection.justification.lower()

    @pytest.mark.parametrize("action_id", ["APPLY_SCOPE_EXTENSION", "APPLY_CRITERION_REALLOCATION"])
    def test_select_action_and_execute_share_sensitive_action_verdict(self, action_id):
        policy = self._policy(action_id)
        context = ActionExecutionContext(
            facts=self._facts(action_id), execution=self._execution(), decisions=(self._decision(action_id),),
        )
        inputs = self._inputs(action_id)
        selection = ProductPolicyEngine(policy=policy).select_action(
            context.facts, list(context.decisions), execution_context=context.execution,
            action_inputs={action_id: inputs},
        )
        result = TypedActionExecutor(policy=policy).execute(action_id, inputs, context)
        assert selection.authorization_allowed is result.decision.authorization_allowed is True
        assert selection.selected_action_id == result.decision.selected_action_id == action_id

    def test_selection_cache_includes_sensitive_inputs_and_decision_evidence(self):
        action_id = "APPLY_SCOPE_EXTENSION"
        engine = ProductPolicyEngine(policy=self._policy(action_id))
        facts, execution = self._facts(action_id), self._execution()
        allowed = engine.select_action(
            facts, [self._decision(action_id)], execution_context=execution,
            action_inputs={action_id: self._inputs(action_id)},
        )
        missing_inputs = engine.select_action(
            facts, [self._decision(action_id)], execution_context=execution, action_inputs={},
        )
        mismatched_decision = engine.select_action(
            facts, [self._decision(action_id, target="other")], execution_context=execution,
            action_inputs={action_id: self._inputs(action_id)},
        )
        assert allowed.authorization_allowed is True
        assert missing_inputs.authorization_allowed is False
        assert mismatched_decision.authorization_allowed is False

    def test_non_sensitive_action_selection_remains_available_without_candidate_inputs(self):
        selection = ProductPolicyEngine().select_action(
            PolicyFacts(provider_quota_exceeded=True, retry_budget_exhausted=True)
        )
        assert selection.selected_action_id == "WAIT_PROVIDER_RESET"
        assert selection.authorization_allowed is True


class TestHumanEscalation:
    """Test REQUEST_HUMAN escalation."""

    def test_no_suitable_action_escalates_to_human(self, policy_engine):
        """If no action matches facts, escalate to REQUEST_HUMAN."""
        # Create impossible facts (no action requires these)
        facts = PolicyFacts()
        selection = policy_engine.select_action(facts)
        # Should escalate since no preconditions match
        # (Could be REQUEST_HUMAN or some catch-all action)
        assert selection.selected_action_id is not None

    def test_explicit_authorization_missing_escalates(self, policy_engine):
        """Missing explicit authorization can escalate to REQUEST_HUMAN."""
        facts = PolicyFacts(
            criterion_reallocation_approved_by_policy=True,
            approval_recorded=True,
        )
        # APPLY_CRITERION_REALLOCATION requires explicit authorization
        selection = policy_engine.select_action(facts)
        # Without policy permission, should not select it
        assert selection.selected_action_id != "APPLY_CRITERION_REALLOCATION"


class TestTypedActionExecutor:
    """Test the typed action executor."""

    def test_executor_rejects_unknown_actions(self, executor):
        """Executor rejects actions not in registry."""
        with pytest.raises(ProductPolicyError, match="Unknown action"):
            executor.validate_action_exists("FAKE_ACTION")

    def test_executor_validates_required_inputs(self, executor):
        """Executor requires all required inputs."""
        action = executor.validate_action_exists("WAIT_PROVIDER_RESET")
        # Missing required 'wait_seconds'
        with pytest.raises(ProductPolicyError, match="Missing required inputs"):
            executor.validate_inputs(action, {})

    def test_executor_allows_missing_optional_inputs(self, executor):
        """Executor allows missing optional inputs."""
        action = executor.validate_action_exists("REGENERATE_TASK_REPORT")
        inputs = {
            "task_id": "task-001",
            "log_path": "/path/to/logs",
        }
        # Should not raise
        executor.validate_inputs(action, inputs)

    def test_executor_validates_input_types(self, executor):
        """Executor validates input parameter types."""
        action = executor.validate_action_exists("WAIT_PROVIDER_RESET")
        # wait_seconds should be integer
        with pytest.raises(ProductPolicyError, match="wrong type"):
            executor.validate_inputs(action, {"wait_seconds": "not_an_int"})

        # Valid integer input
        executor.validate_inputs(action, {"wait_seconds": 60})

    def test_executor_rejects_free_commands(self, executor):
        """Executor rejects free-form commands."""
        with pytest.raises(ProductPolicyError, match="not in the closed action registry"):
            executor.reject_free_commands("rm -rf /")

    def test_executor_validates_preconditions(self, executor):
        """Executor validates preconditions before action."""
        action = executor.validate_action_exists("WAIT_PROVIDER_RESET")
        # Missing preconditions
        facts = PolicyFacts()
        with pytest.raises(ProductPolicyError, match="Precondition failed"):
            executor.validate_preconditions(action, facts)

        # With preconditions
        facts = PolicyFacts(
            provider_quota_exceeded=True,
            retry_budget_exhausted=True,
        )
        executor.validate_preconditions(action, facts)


class TestActionSerialization:
    """Test action serialization and deserialization."""

    def test_action_serializes_to_dict(self):
        registry = get_action_registry()
        action = registry.get_action("WAIT_PROVIDER_RESET")
        assert action is not None

        action_dict = action.to_dict()
        assert action_dict["action_id"] == "WAIT_PROVIDER_RESET"
        assert action_dict["schema_version"] == "1.0.0"
        assert "preconditions" in action_dict
        assert "authorization" in action_dict

    def test_action_roundtrip_serialization(self):
        registry = get_action_registry()
        action = registry.get_action("INTEGRATE_FEATURE")
        assert action is not None

        # Serialize
        action_dict = action.to_dict()
        # Deserialize
        restored = type(action).from_dict(action_dict)

        assert restored.action_id == action.action_id
        assert restored.title == action.title
        assert restored.category == action.category


class TestPolicySerialization:
    """Test policy serialization."""

    def test_policy_serializes(self, default_policy):
        policy_dict = default_policy.to_dict()
        assert policy_dict["schema_version"] == "1.0.0"
        assert policy_dict["plan_id"] == "test-plan"
        assert "allow_scope_extension" in policy_dict

    def test_policy_roundtrip(self, default_policy):
        policy_dict = default_policy.to_dict()
        restored = ProductPolicy.from_dict(policy_dict)

        assert restored.plan_id == default_policy.plan_id
        assert restored.allow_scope_extension == default_policy.allow_scope_extension


class TestSelectionMemoization:
    """Test that selections are memoized for determinism."""

    def test_selection_is_memoized(self, policy_engine, default_facts):
        """Engine memoizes selections for identical input."""
        selection1 = policy_engine.select_action(default_facts)

        # Should hit memo on second call
        selection2 = policy_engine.select_action(default_facts)

        # Must be identical
        assert selection1.hash() == selection2.hash()

    def test_memoization_survives_decision_ordering(self, policy_engine):
        """Decisions in different order produce same result."""
        facts = PolicyFacts(
            scope_extension_approved_by_policy=True,
            approval_recorded=True,
        )

        d1 = RecordedDecision(
            decision_id="d001",
            decision_type=DecisionType.SCOPE_EXTENSION_APPROVED,
            timestamp="2026-01-01T00:00:00Z",
            data={"file": "test.py"},
        )
        d2 = RecordedDecision(
            decision_id="d002",
            decision_type=DecisionType.ACTION_AUTHORIZED,
            timestamp="2026-01-02T00:00:00Z",
            data={"action_id": "APPLY_SCOPE_EXTENSION"},
        )

        selection1 = policy_engine.select_action(facts, [d1, d2])
        selection2 = policy_engine.select_action(facts, [d2, d1])

        # Different order, but same decisions hash
        assert selection1.decisions_hash == selection2.decisions_hash
        assert selection1.selected_action_id == selection2.selected_action_id


class TestStopReasons:
    """Test stop reason evaluation."""

    def test_merge_conflict_stop_reason(self, policy_engine):
        """Stop reasons can prevent action selection."""
        facts = PolicyFacts(
            git_state_diverged=True,
            origin_reachable=True,
            merge_conflicts=True,  # Stop reason for RECONCILE_WORKTREE
        )
        selection = policy_engine.select_action(facts)
        # Should not select RECONCILE_WORKTREE due to merge conflict
        assert selection.selected_action_id != "RECONCILE_WORKTREE"


class TestMandatoryEscalationToHuman:
    """Test mandatory escalation conditions (AC-R15)."""

    @pytest.mark.parametrize("supervised_corrections_used", [2, 3])
    def test_select_action_escalates_at_or_above_supervised_correction_ceiling(
        self, supervised_corrections_used
    ):
        """AC-R15-7: the public selection path escalates at the inclusive supervised ceiling."""
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at="2026-01-01T00:00:00Z",
            max_supervised_corrections=2,
        )

        selection = ProductPolicyEngine(policy=policy).select_action(
            PolicyFacts(provider_quota_exceeded=True, retry_budget_exhausted=True),
            execution_context=ExecutionContext(
                supervised_corrections_used=supervised_corrections_used
            ),
        )

        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert "supervised correction limit" in selection.justification.lower()

    def test_select_action_does_not_escalate_below_supervised_correction_ceiling(self):
        """AC-R15-7: an available supervised budget leaves the normal action selectable."""
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at="2026-01-01T00:00:00Z",
            max_supervised_corrections=2,
        )

        selection = ProductPolicyEngine(policy=policy).select_action(
            PolicyFacts(provider_quota_exceeded=True, retry_budget_exhausted=True),
            execution_context=ExecutionContext(supervised_corrections_used=1),
        )

        assert selection.selected_action_id == "WAIT_PROVIDER_RESET"

    def test_select_action_keeps_ordinary_ceiling_out_of_mandatory_escalation(self):
        """AC-R15-7: the ordinary ceiling alone never selects REQUEST_HUMAN."""
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at="2026-01-01T00:00:00Z",
            max_ordinary_corrections=1,
            max_supervised_corrections=2,
        )

        selection = ProductPolicyEngine(policy=policy).select_action(
            PolicyFacts(provider_quota_exceeded=True, retry_budget_exhausted=True),
            execution_context=ExecutionContext(
                ordinary_corrections_used=1,
                supervised_corrections_used=0,
            ),
        )

        assert selection.selected_action_id != "REQUEST_HUMAN"

    def test_select_action_passes_exact_execution_context_to_mandatory_escalation(self, monkeypatch):
        """The public selector forwards its supplied runtime context unchanged."""
        engine = make_engine()
        execution = ExecutionContext(supervised_corrections_used=1)
        received_contexts = []
        original_check = engine._check_mandatory_escalation

        def capture_context(facts, decisions, debugger=None, execution_context=None):
            received_contexts.append(execution_context)
            return original_check(facts, decisions, debugger, execution_context)

        monkeypatch.setattr(engine, "_check_mandatory_escalation", capture_context)

        engine.select_action(
            PolicyFacts(provider_quota_exceeded=True, retry_budget_exhausted=True),
            execution_context=execution,
        )

        assert received_contexts == [execution]

    def test_select_action_cache_keeps_execution_contexts_distinct(self):
        """A cached normal selection cannot mask a later supervised escalation."""
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at="2026-01-01T00:00:00Z",
            max_supervised_corrections=2,
        )
        engine = ProductPolicyEngine(policy=policy)
        facts = PolicyFacts(provider_quota_exceeded=True, retry_budget_exhausted=True)

        initial = engine.select_action(
            facts,
            execution_context=ExecutionContext(supervised_corrections_used=1),
        )
        escalated = engine.select_action(
            facts,
            execution_context=ExecutionContext(supervised_corrections_used=2),
        )

        assert initial.selected_action_id == "WAIT_PROVIDER_RESET"
        assert escalated.selected_action_id == "REQUEST_HUMAN"

    def test_select_action_preserves_existing_mandatory_escalations_with_execution_context(self):
        """Existing R15 escalations retain their structured reason when runtime data is present."""
        selection = make_engine().select_action(
            PolicyFacts(merge_conflicts_unresolved=True),
            execution_context=ExecutionContext(supervised_corrections_used=0),
        )

        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert "merge conflicts" in selection.justification.lower()

    def test_scope_extension_without_authorization_escalates_to_human(self):
        """AC-R15-2: Scope extension without explicit authorization must escalate to REQUEST_HUMAN."""
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at=datetime.now(timezone.utc).isoformat(),
            allow_scope_extension=False,  # Not authorized
        )
        engine = ProductPolicyEngine(policy=policy)
        facts = PolicyFacts(necessary_change_outside_scope=True)

        selection = engine.select_action(facts)
        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert "scope extension" in selection.justification.lower()

    def test_criterion_reallocation_without_authorization_escalates_to_human(self):
        """AC-R15-2: Criterion reallocation without explicit authorization must escalate to REQUEST_HUMAN."""
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at=datetime.now(timezone.utc).isoformat(),
            allow_criterion_reallocation=False,  # Not authorized
        )
        engine = ProductPolicyEngine(policy=policy)
        facts = PolicyFacts(criterion_ownership_mismatch=True)

        selection = engine.select_action(facts)
        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert "criterion reallocation" in selection.justification.lower()

    def test_specification_absent_without_generation_policy_escalates(self):
        """AC-R15-6: Specification absent without generation policy must escalate."""
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at=datetime.now(timezone.utc).isoformat(),
            specification_generation_policy="approved_only",
        )
        engine = ProductPolicyEngine(policy=policy)
        facts = PolicyFacts(
            specification_absent=True,
            specification_generation_allowed=False,
        )

        selection = engine.select_action(facts)
        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert "specification absent" in selection.justification.lower()

    @pytest.mark.parametrize(
        "generation_policy",
        [None, "", "unknown", "approved-only", "approved_only", False, "autonomous?"],
    )
    def test_specification_absent_escalates_for_every_non_authorizing_policy(self, generation_policy):
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at=datetime.now(timezone.utc).isoformat(),
            specification_generation_policy=generation_policy,
        )

        selection = ProductPolicyEngine(policy=policy).select_action(
            PolicyFacts(
                specification_absent=True,
                specification_generation_allowed=False,
                provider_quota_exceeded=True,
                retry_budget_exhausted=True,
            )
        )

        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert "specification absent" in selection.justification.lower()

    @pytest.mark.parametrize("generation_policy", ["draft", "autonomous"])
    def test_specification_absent_proceeds_only_with_explicit_policy_and_fact(self, generation_policy):
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at=datetime.now(timezone.utc).isoformat(),
            specification_generation_policy=generation_policy,
        )

        selection = ProductPolicyEngine(policy=policy).select_action(
            PolicyFacts(
                specification_absent=True,
                specification_generation_allowed=True,
                provider_quota_exceeded=True,
                retry_budget_exhausted=True,
            )
        )

        assert selection.selected_action_id == "WAIT_PROVIDER_RESET"

    @pytest.mark.parametrize("generation_policy", [None, "unknown", "approved_only", False])
    def test_unknown_policy_cannot_be_authorized_by_runtime_fact_alone(self, generation_policy):
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at=datetime.now(timezone.utc).isoformat(),
            specification_generation_policy=generation_policy,
        )

        selection = ProductPolicyEngine(policy=policy).select_action(
            PolicyFacts(
                specification_absent=True,
                specification_generation_allowed=True,
                provider_quota_exceeded=True,
                retry_budget_exhausted=True,
            )
        )

        assert selection.selected_action_id == "REQUEST_HUMAN"

    def test_incident_environment_persistent_escalates(self):
        """AC-R15-6: Environmental incident persistent beyond bound must escalate."""
        engine = make_engine()
        facts = PolicyFacts(incident_environment_persistent=True)

        selection = engine.select_action(facts)
        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert "environmental incident" in selection.justification.lower()

    def test_supervised_correction_limit_exceeded_escalates(self):
        """AC-R15-7: Supervised correction limit exceeds triggers REQUEST_HUMAN."""
        engine = make_engine()
        facts = PolicyFacts(supervised_correction_limit_exceeded=True)

        selection = engine.select_action(facts)
        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert "supervised" in selection.justification.lower()

    def test_ambiguous_functional_impact_blocks_criterion_reallocation(self):
        """AC-R15-5: Ambiguous functional impact must block APPLY_CRITERION_REALLOCATION."""
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at=datetime.now(timezone.utc).isoformat(),
            allow_criterion_reallocation=True,  # Policy allows it
        )
        engine = make_engine(policy)

        # Facts show reallocation approved but with ambiguous impact
        facts = PolicyFacts(
            criterion_reallocation_approved_by_policy=True,
            approval_recorded=True,
            ambiguous_functional_impact=True,  # This should block the action
        )

        selection = engine.select_action(facts)
        # Should not select APPLY_CRITERION_REALLOCATION due to ambiguity
        assert selection.selected_action_id != "APPLY_CRITERION_REALLOCATION", \
            "APPLY_CRITERION_REALLOCATION should be blocked when ambiguous_functional_impact is true"


class TestIntegrationBaselineRequirement:
    """Test that INTEGRATE_FEATURE requires baseline."""

    def test_integrate_feature_requires_baseline(self):
        """INTEGRATE_FEATURE must have baseline_established as precondition."""
        engine = make_engine()
        facts = PolicyFacts(
            baseline_established=False,  # Missing baseline
            feature_approved=True,
            tests_passed=True,
            scope_validated=True,
        )

        selection = engine.select_action(facts)
        # Should not select INTEGRATE_FEATURE without baseline
        assert selection.selected_action_id != "INTEGRATE_FEATURE"

    def test_integrate_feature_with_baseline(self):
        """INTEGRATE_FEATURE can be selected when baseline is established."""
        engine = make_engine()
        facts = PolicyFacts(
            baseline_established=True,  # Baseline present
            feature_approved=True,
            tests_passed=True,
            scope_validated=True,
        )

        selection = engine.select_action(facts)
        assert selection.selected_action_id == "INTEGRATE_FEATURE"


class TestStructuredDossiers:
    """Test structured dossier requirements for escalations."""

    def test_request_scope_extension_has_structured_inputs(self):
        """REQUEST_SCOPE_EXTENSION must have all required dossier fields."""
        registry = get_action_registry()
        action = registry.get_action("REQUEST_SCOPE_EXTENSION")
        assert action is not None

        # Check required inputs
        required_names = {p.name for p in action.inputs.required}
        assert "file_path" in required_names
        assert "justification" in required_names
        assert "baseline_proof" in required_names
        assert "impact_estimate" in required_names
        assert "alternatives_discarded" in required_names
        assert "constraints_to_preserve" in required_names

    def test_request_criterion_reallocation_has_structured_inputs(self):
        """REQUEST_CRITERION_REALLOCATION must have all required dossier fields including baseline proof and impact."""
        registry = get_action_registry()
        action = registry.get_action("REQUEST_CRITERION_REALLOCATION")
        assert action is not None

        # Check required inputs - must include all R15-3 elements
        required_names = {p.name for p in action.inputs.required}
        assert "criterion" in required_names
        assert "current_owner" in required_names
        assert "proposed_owner" in required_names
        assert "infeasibility_proof" in required_names
        assert "proposed_owner_justification" in required_names
        assert "alternatives_considered" in required_names
        assert "dependency_impact" in required_names
        # AC-R15-3 requires baseline_proof, impact_expected, and constraints_to_preserve
        assert "baseline_proof" in required_names, "Missing baseline_proof required by AC-R15-3"
        assert "impact_expected" in required_names, "Missing impact_expected required by AC-R15-3"
        assert "constraints_to_preserve" in required_names, "Missing constraints_to_preserve required by AC-R15-3"

    def test_request_human_has_full_dossier_structure(self):
        """REQUEST_HUMAN must require facts, evidence, decisions, attempts, and choices."""
        registry = get_action_registry()
        action = registry.get_action("REQUEST_HUMAN")
        assert action is not None

        # Check required inputs for full dossier
        required_names = {p.name for p in action.inputs.required}
        assert "reason" in required_names
        assert "facts" in required_names
        assert "evidence" in required_names
        assert "decisions_to_preserve" in required_names
        assert "attempted_solutions" in required_names
        assert "possible_choices" in required_names


class TestScopeAndPolicyLimits:
    """Test explicit scope and policy limit checking (AC-R9-2)."""

    def test_scope_constraints_are_checked(self):
        """AC-R9-2: Action scope constraints must be explicitly checked."""
        engine = make_engine()
        registry = get_action_registry()

        # Check that all actions have scope constraints
        for action in registry.list_actions():
            assert action.scope is not None, f"Action {action.action_id} missing scope"
            assert action.scope.max_entities >= 0, \
                f"Action {action.action_id} has invalid max_entities"
            assert isinstance(action.scope.modifications_bounded, bool), \
                f"Action {action.action_id} missing modifications_bounded"

    def test_policy_limits_prevent_unauthorized_scope_extension(self):
        """AC-R9-2: Policy must refuse scope extension when not authorized."""
        # Policy that explicitly forbids scope extension
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at=datetime.now(timezone.utc).isoformat(),
            allow_scope_extension=False,  # Explicitly forbidden
        )
        engine = make_engine(policy)

        facts = PolicyFacts(necessary_change_outside_scope=True)
        selection = engine.select_action(facts)

        # Should escalate to REQUEST_HUMAN when policy forbids it
        assert selection.selected_action_id == "REQUEST_HUMAN"

    def test_policy_limits_prevent_unauthorized_criterion_reallocation(self):
        """AC-R9-2: Policy must refuse criterion reallocation when not authorized."""
        # Policy that explicitly forbids criterion reallocation
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at=datetime.now(timezone.utc).isoformat(),
            allow_criterion_reallocation=False,  # Explicitly forbidden
        )
        engine = make_engine(policy)

        facts = PolicyFacts(criterion_ownership_mismatch=True)
        selection = engine.select_action(facts)

        # Should escalate to REQUEST_HUMAN when policy forbids it
        assert selection.selected_action_id == "REQUEST_HUMAN"

    def test_apply_scope_extension_requires_policy_authorization(self):
        """AC-R9-2: APPLY_SCOPE_EXTENSION action requires explicit policy authorization."""
        # Policy without authorization
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at=datetime.now(timezone.utc).isoformat(),
            allow_scope_extension=False,
        )
        engine = make_engine(policy)

        facts = PolicyFacts(
            scope_extension_approved_by_policy=True,
            approval_recorded=True,
        )

        selection = engine.select_action(facts)
        # Should not select APPLY_SCOPE_EXTENSION when policy forbids it
        assert selection.selected_action_id != "APPLY_SCOPE_EXTENSION"

    def test_apply_criterion_reallocation_requires_policy_authorization(self):
        """AC-R9-2: APPLY_CRITERION_REALLOCATION requires explicit policy authorization."""
        # Policy without authorization
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test-plan",
            created_at=datetime.now(timezone.utc).isoformat(),
            allow_criterion_reallocation=False,
        )
        engine = make_engine(policy)

        facts = PolicyFacts(
            criterion_reallocation_approved_by_policy=True,
            approval_recorded=True,
        )

        selection = engine.select_action(facts)
        # Should not select APPLY_CRITERION_REALLOCATION when policy forbids it
        assert selection.selected_action_id != "APPLY_CRITERION_REALLOCATION"


class TestSchemaversionCompliance:
    """Test that schema versions comply with SemVer."""

    def test_all_actions_have_semver_schema_version(self):
        """All actions must use valid SemVer schema_version (x.y.z)."""
        registry = get_action_registry()
        semver_pattern = r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?(?:\+[a-zA-Z0-9.-]+)?$"
        import re

        for action in registry.list_actions():
            assert re.match(
                semver_pattern, action.schema_version
            ), f"Action {action.action_id} has invalid schema_version: {action.schema_version}"

    def test_registry_exports_semver_version(self):
        """Registry export must use valid SemVer."""
        registry = get_action_registry()
        registry_dict = registry.to_dict()
        assert registry_dict["schema_version"] == "1.0.0"


class TestPolicyCorrection:
    """Test correction limits and policy constraints."""

    def test_policy_distinguishes_ordinary_and_supervised_limits(self):
        """Policy must have distinct ordinary and supervised correction limits."""
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test",
            created_at=datetime.now(timezone.utc).isoformat(),
            max_ordinary_corrections=3,
            max_supervised_corrections=7,
        )
        assert policy.max_ordinary_corrections == 3
        assert policy.max_supervised_corrections == 7
        assert policy.max_supervised_corrections > policy.max_ordinary_corrections

    def test_policy_has_specification_generation_policy(self):
        """Policy must include specification generation policy."""
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test",
            created_at=datetime.now(timezone.utc).isoformat(),
            specification_generation_policy="approved_only",
        )
        assert policy.specification_generation_policy == "approved_only"

    def test_policy_roundtrip_preserves_new_fields(self):
        """Policy serialization must preserve new fields."""
        original = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test",
            created_at="2026-01-01T00:00:00Z",
            max_ordinary_corrections=2,
            max_supervised_corrections=5,
            specification_generation_policy="draft",
        )
        policy_dict = original.to_dict()
        restored = ProductPolicy.from_dict(policy_dict)

        assert restored.max_ordinary_corrections == 2
        assert restored.max_supervised_corrections == 5
        assert restored.specification_generation_policy == "draft"


class TestGlobalMandatoryEscalations:
    """Test additional mandatory escalation conditions for R15."""

    def test_unresolved_merge_conflicts_escalate_to_human(self):
        """AC-R15-1: Unresolved merge conflicts must escalate to REQUEST_HUMAN."""
        engine = make_engine()
        facts = PolicyFacts(merge_conflicts_unresolved=True)

        selection = engine.select_action(facts)
        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert "merge conflicts" in selection.justification.lower()

    def test_business_ambiguity_escalates_to_human(self):
        """AC-R15-1: Unresolved business ambiguity must escalate to REQUEST_HUMAN."""
        engine = make_engine()
        facts = PolicyFacts(business_ambiguity_unresolved=True)

        selection = engine.select_action(facts)
        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert "ambiguity" in selection.justification.lower()

    def test_git_safety_unguaranteed_escalates_to_human(self):
        """AC-R15-1, AC-R15-5: Git safety unguaranteed must escalate to REQUEST_HUMAN."""
        engine = make_engine()
        facts = PolicyFacts(git_safety_unguaranteed=True)

        selection = engine.select_action(facts)
        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert "git safety" in selection.justification.lower()

    def test_multiple_reasonable_solutions_escalate_to_human(self):
        """AC-R15-1, AC-R15-5: Multiple reasonable solutions must escalate to REQUEST_HUMAN."""
        engine = make_engine()
        facts = PolicyFacts(multiple_reasonable_solutions=True)

        selection = engine.select_action(facts)
        assert selection.selected_action_id == "REQUEST_HUMAN"
        assert "multiple" in selection.justification.lower() or "ambiguous" in selection.justification.lower()


class TestRegistryImmutability:
    """Test that registry is closed and immutable (AC-R12-1)."""

    def test_global_registry_uses_canonical_actions(self):
        """Global registry must use canonical closed registry."""
        registry = get_action_registry()
        actions = registry.list_actions()
        assert len(actions) == 14  # Exact count of defined actions

    def test_custom_registry_rejects_unknown_actions(self):
        """Custom registry must reject actions not in canonical registry."""
        from autodev.product_actions import CLOSED_ACTION_REGISTRY
        fake_action = CLOSED_ACTION_REGISTRY[0]
        # Create a modified copy with unknown ID
        modified = type(fake_action)(
            schema_version=fake_action.schema_version,
            action_id="UNKNOWN_ACTION",
            title=fake_action.title,
            category=fake_action.category,
            preconditions=fake_action.preconditions,
            authorization=fake_action.authorization,
            inputs=fake_action.inputs,
            expected_effect=fake_action.expected_effect,
            scope=fake_action.scope,
            audit_trail=fake_action.audit_trail,
            idempotence_rule=fake_action.idempotence_rule,
            rollback_strategy=fake_action.rollback_strategy,
            stop_reasons=fake_action.stop_reasons,
        )
        with pytest.raises(ProductActionError, match="unknown actions"):
            ProductActionRegistry([modified])

    def test_custom_registry_rejects_duplicates(self):
        """Custom registry must reject duplicate action IDs."""
        from autodev.product_actions import CLOSED_ACTION_REGISTRY
        dup_actions = [CLOSED_ACTION_REGISTRY[0], CLOSED_ACTION_REGISTRY[0]]
        with pytest.raises(ProductActionError, match="duplicate"):
            ProductActionRegistry(dup_actions)

    def test_registry_list_is_immutable(self):
        """Registry list must be immutable (read-only via property)."""
        registry = get_action_registry()
        # Access via property
        actions_tuple = registry.actions
        assert isinstance(actions_tuple, tuple)
        # Attempting to modify should fail since it's a tuple
        with pytest.raises((TypeError, AttributeError)):
            actions_tuple[0] = None


class TestTypedExecutorStrictness:
    """Test that executor strictly validates types and rejects unknowns (AC-R9-3)."""

    def test_executor_rejects_extra_parameters(self, executor):
        """AC-R9-3: Executor must reject unknown/extra parameters."""
        action = executor.validate_action_exists("WAIT_PROVIDER_RESET")
        inputs = {
            "wait_seconds": 60,
            "unknown_param": "should_fail",
        }
        with pytest.raises(ProductPolicyError, match="Unknown input parameters"):
            executor.validate_inputs(action, inputs)

    def test_executor_rejects_wrong_types_strictly(self, executor):
        """AC-R9-3: Executor must reject type mismatches strictly."""
        action = executor.validate_action_exists("WAIT_PROVIDER_RESET")
        # Boolean as integer should fail
        with pytest.raises(ProductPolicyError, match="wrong type"):
            executor.validate_inputs(action, {"wait_seconds": True})

    def test_executor_rejects_unknown_types(self, executor):
        """AC-R9-3: Executor must reject unknown parameter types."""
        from autodev.product_actions import InputParameter, Inputs
        from autodev.product_policy import TypedActionExecutor
        action = executor.validate_action_exists("WAIT_PROVIDER_RESET")
        # Manually test _type_matches with unknown type
        unknown_type_result = executor._type_matches("value", "unknown_type")
        assert unknown_type_result is False, "Unknown types must be rejected, not assumed valid"


class TestClosedRegistryRegression:
    """The canonical product-action catalogue cannot be modified or substituted."""

    def test_registry_index_mutation_fails_and_resolution_stays_canonical(self):
        registry = get_action_registry()
        canonical = registry.get_action("WAIT_PROVIDER_RESET")

        with pytest.raises(TypeError):
            registry.action_map["INJECTED"] = canonical

        assert registry.get_action("WAIT_PROVIDER_RESET") is canonical
        assert registry.get_action("INJECTED") is None

    def test_registry_rejects_external_definition_with_known_identifier(self):
        registry = get_action_registry()
        canonical = registry.get_action("WAIT_PROVIDER_RESET")
        assert canonical is not None
        forged = type(canonical)(
            schema_version=canonical.schema_version,
            action_id=canonical.action_id,
            title="Forged definition",
            category=canonical.category,
            preconditions=canonical.preconditions,
            authorization=canonical.authorization,
            inputs=canonical.inputs,
            expected_effect=canonical.expected_effect,
            scope=canonical.scope,
            audit_trail=canonical.audit_trail,
            idempotence_rule=canonical.idempotence_rule,
            rollback_strategy=canonical.rollback_strategy,
            stop_reasons=canonical.stop_reasons,
        )

        with pytest.raises(ProductActionError, match="canonical"):
            ProductActionRegistry([forged])
        with pytest.raises(ProductPolicyError, match="External ProductAction"):
            TypedActionExecutor().validate_inputs(forged, {"wait_seconds": 1})

    def test_schema_ids_match_canonical_registry(self):
        schema_path = Path(__file__).parents[1] / "schemas" / "product-action.schema.json"
        schema = json.loads(schema_path.read_text())
        registry_ids = {action.action_id for action in get_action_registry().actions}
        assert set(schema["properties"]["action_id"]["enum"]) == registry_ids

    def test_syntactically_valid_unregistered_action_is_rejected(self):
        executor = TypedActionExecutor()
        with pytest.raises(ProductPolicyError, match="Unknown action"):
            executor.execute("VALID_BUT_UNREGISTERED", {}, _permitted_context())


def _permitted_context():
    from autodev.product_policy import ActionExecutionContext, ExecutionContext

    return ActionExecutionContext(
        facts=PolicyFacts(provider_quota_exceeded=True, retry_budget_exhausted=True),
        execution=ExecutionContext(
            entities_modified=1,
            modifications_audited=True,
            modification_is_mechanical=True,
        ),
    )


class TestClosedActionExecution:
    """The sole execute API validates policy before a fixed, typed handler runs."""

    def test_executes_authorized_canonical_handler(self):
        executor = TypedActionExecutor()
        result = executor.execute("WAIT_PROVIDER_RESET", {"wait_seconds": 60}, _permitted_context())

        assert result.executed is True
        assert result.action_id == "WAIT_PROVIDER_RESET"
        assert result.output["status"] == "accepted"

    def test_constructor_rejects_public_handler_injection(self):
        with pytest.raises(TypeError, match="handlers"):
            TypedActionExecutor(handlers={"WAIT_PROVIDER_RESET": lambda inputs, context: {}})

    def test_arbitrary_callable_input_cannot_replace_internal_operation(self):
        executor = TypedActionExecutor()
        called = []

        def arbitrary_handler(*args):
            called.append(args)
            return {"replaced": True}

        with pytest.raises(ProductPolicyError, match="Unknown input parameters"):
            executor.execute(
                "WAIT_PROVIDER_RESET",
                {"wait_seconds": 60, "handler": arbitrary_handler},
                _permitted_context(),
            )

        assert called == []

    def test_refused_policy_never_calls_handler(self):
        calls = []

        class ObservedExecutor(TypedActionExecutor):
            def _handle_wait_provider_reset(self, inputs, context):
                calls.append(True)
                return super()._handle_wait_provider_reset(inputs, context)

        executor = ObservedExecutor()
        refused = _permitted_context()
        refused = type(refused)(facts=PolicyFacts(), execution=refused.execution)

        result = executor.execute("WAIT_PROVIDER_RESET", {"wait_seconds": 60}, refused)

        assert result.executed is False
        assert result.decision.selected_action_id == "REQUEST_HUMAN"
        assert calls == []

    def test_execute_rejects_forged_action_and_free_command_or_strategy(self):
        executor = TypedActionExecutor()
        context = _permitted_context()

        with pytest.raises(ProductPolicyError, match="Unknown action"):
            executor.execute("git reset --hard", {}, context)
        with pytest.raises(ProductPolicyError, match="canonical string"):
            executor.execute(object(), {}, context)
        with pytest.raises(ProductPolicyError, match="Unknown input parameters"):
            executor.execute(
                "WAIT_PROVIDER_RESET",
                {"wait_seconds": 60, "strategy": "reset"},
                context,
            )

    def test_handlers_are_immutable_after_initialization(self):
        executor = TypedActionExecutor()
        with pytest.raises(TypeError):
            executor._handlers["WAIT_PROVIDER_RESET"] = lambda inputs, context: {}


class TestPreservePartialChanges:
    """PRESERVE_PARTIAL_CHANGES only creates or recognizes controlled backups."""

    @staticmethod
    def _context():
        from autodev.product_policy import ActionExecutionContext

        return ActionExecutionContext(
            facts=PolicyFacts(
                operation_failed_midway=True,
                partial_changes_exist=True,
                backup_target_is_new_or_matching_autodev_backup=True,
            ),
            execution=ExecutionContext(
                entities_modified=1,
                modifications_audited=True,
                modification_is_mechanical=True,
            ),
        )

    def test_existing_user_file_is_never_overwritten(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        source = tmp_path / "partial.txt"
        source.write_text("partial work")
        backup = tmp_path / ".autodev" / "backups" / "partial.txt"
        backup.parent.mkdir(parents=True)
        backup.write_text("user-owned content")

        with pytest.raises(ProductPolicyError, match="pre-existing backup target"):
            TypedActionExecutor().execute(
                "PRESERVE_PARTIAL_CHANGES",
                {"source_path": source, "backup_path": backup},
                self._context(),
            )

        assert backup.read_text() == "user-owned content"

    def test_double_execution_is_idempotent_without_overwriting(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        source = tmp_path / "partial.txt"
        source.write_text("partial work")
        backup = tmp_path / ".autodev" / "backups" / "partial.txt"
        executor = TypedActionExecutor()

        first = executor.execute(
            "PRESERVE_PARTIAL_CHANGES",
            {"source_path": source, "backup_path": backup},
            self._context(),
        )
        original = backup.read_text()
        second = executor.execute(
            "PRESERVE_PARTIAL_CHANGES",
            {"source_path": source, "backup_path": backup},
            self._context(),
        )

        assert first.executed is True
        assert second.executed is True
        assert second.output["idempotent"] is True
        assert backup.read_text() == original == "partial work"

    def test_backup_path_outside_controlled_area_is_refused(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        source = tmp_path / "partial.txt"
        source.write_text("partial work")

        with pytest.raises(ProductPolicyError, match="under .autodev/backups"):
            TypedActionExecutor().execute(
                "PRESERVE_PARTIAL_CHANGES",
                {"source_path": source, "backup_path": tmp_path / "backup.txt"},
                self._context(),
            )


class TestBlockingPolicyMatrix:
    """Each mandatory boolean independently blocks a proposed sensitive action."""

    @pytest.mark.parametrize(
        ("fact_overrides", "execution_overrides"),
        [
            ({"scope_extension_approved_by_policy": False}, {}),
            ({"approval_recorded": False}, {}),
            ({"ambiguous_functional_impact": True}, {}),
            ({}, {"entities_modified": 2}),
            ({}, {"modifications_audited": False}),
            ({}, {"modification_is_mechanical": False}),
            ({"baseline_established": False}, {}),
            ({}, {"baseline_proof_available": False}),
            ({}, {"exactly_one_bounded_modification": False}),
        ],
    )
    def test_each_scope_extension_gate_blocks_execution(self, fact_overrides, execution_overrides):
        from autodev.product_policy import ActionExecutionContext, ExecutionContext

        facts = {
            "scope_extension_approved_by_policy": True,
            "approval_recorded": True,
            "baseline_established": True,
        }
        facts.update(fact_overrides)
        execution = {
            "entities_modified": 1,
            "modifications_audited": True,
            "modification_is_mechanical": True,
            "baseline_proof_available": True,
            "exactly_one_bounded_modification": True,
        }
        execution.update(execution_overrides)
        policy = ProductPolicy(
            schema_version="1.0.0",
            plan_id="test",
            created_at="2026-01-01T00:00:00Z",
            allow_scope_extension=True,
        )
        context = ActionExecutionContext(
            facts=PolicyFacts(**facts),
            execution=ExecutionContext(**execution),
            decisions=(
                RecordedDecision(
                    decision_id="decision-1",
                    decision_type=DecisionType.SCOPE_EXTENSION_APPROVED,
                    timestamp="2026-01-01T00:00:00Z",
                    data={"action_id": "APPLY_SCOPE_EXTENSION"},
                ),
            ),
        )
        executor = TypedActionExecutor(policy=policy)

        result = executor.execute(
            "APPLY_SCOPE_EXTENSION",
            {"approval_id": "decision-1", "change_definition": {"change": "bounded"}},
            context,
        )
        assert result.executed is False

    def test_scope_extension_requires_an_acquired_plan_decision(self):
        from autodev.product_policy import ActionExecutionContext, ExecutionContext

        context = ActionExecutionContext(
            facts=PolicyFacts(scope_extension_approved_by_policy=True, approval_recorded=True,
                              baseline_established=True),
            execution=ExecutionContext(entities_modified=1, modifications_audited=True,
                                       modification_is_mechanical=True, baseline_proof_available=True,
                                       exactly_one_bounded_modification=True),
        )
        policy = ProductPolicy(schema_version="1.0.0", plan_id="test",
                               created_at="2026-01-01T00:00:00Z", allow_scope_extension=True)
        result = TypedActionExecutor(policy=policy).execute(
            "APPLY_SCOPE_EXTENSION",
            {"approval_id": "decision-1", "change_definition": {"change": "bounded"}},
            context,
        )
        assert result.executed is False

    @pytest.mark.parametrize(
        ("fact_overrides", "execution_overrides"),
        [
            ({"criterion_reallocation_approved_by_policy": False}, {}),
            ({"approval_recorded": False}, {}),
            ({"ambiguous_functional_impact": True}, {}),
            ({}, {"entities_modified": 2}),
            ({}, {"modifications_audited": False}),
            ({}, {"modification_is_mechanical": False}),
            ({"baseline_established": False}, {}),
            ({}, {"baseline_proof_available": False}),
            ({}, {"exactly_one_bounded_modification": False}),
        ],
    )
    def test_each_criterion_reallocation_gate_blocks_execution(self, fact_overrides, execution_overrides):
        from autodev.product_policy import ActionExecutionContext, ExecutionContext

        facts = {
            "criterion_reallocation_approved_by_policy": True,
            "approval_recorded": True,
            "baseline_established": True,
        }
        facts.update(fact_overrides)
        execution = {
            "entities_modified": 1,
            "modifications_audited": True,
            "modification_is_mechanical": True,
            "baseline_proof_available": True,
            "exactly_one_bounded_modification": True,
        }
        execution.update(execution_overrides)
        policy = ProductPolicy(
            schema_version="1.0.0", plan_id="test", created_at="2026-01-01T00:00:00Z",
            allow_criterion_reallocation=True,
        )
        context = ActionExecutionContext(
            facts=PolicyFacts(**facts),
            execution=ExecutionContext(**execution),
            decisions=(
                RecordedDecision(
                    decision_id="decision-2",
                    decision_type=DecisionType.CRITERION_REALLOCATION_APPROVED,
                    timestamp="2026-01-01T00:00:00Z",
                    data={"action_id": "APPLY_CRITERION_REALLOCATION"},
                ),
            ),
        )
        result = TypedActionExecutor(policy=policy).execute(
            "APPLY_CRITERION_REALLOCATION",
            {"approval_id": "decision-2", "criterion": "R15", "new_owner": "supervisor"},
            context,
        )
        assert result.executed is False

    @pytest.mark.parametrize("missing_gate", ["feature_approved", "tests_passed", "scope_validated", "baseline_established"])
    def test_each_integration_gate_blocks_execution(self, missing_gate):
        from autodev.product_policy import ActionExecutionContext, ExecutionContext

        facts = {
            "feature_approved": True,
            "tests_passed": True,
            "scope_validated": True,
            "baseline_established": True,
        }
        facts[missing_gate] = False
        context = ActionExecutionContext(
            facts=PolicyFacts(**facts),
            execution=ExecutionContext(entities_modified=1, modifications_audited=True,
                                       modification_is_mechanical=True),
        )
        result = TypedActionExecutor().execute(
            "INTEGRATE_FEATURE", {"feature_id": "T07", "commit_message": "integrate"}, context
        )
        assert result.executed is False

    def test_ordinary_limit_blocks_without_requesting_human_but_supervised_limit_escalates(self):
        from autodev.product_policy import ActionExecutionContext, ExecutionContext

        policy = ProductPolicy(
            schema_version="1.0.0", plan_id="test", created_at="2026-01-01T00:00:00Z",
            max_ordinary_corrections=1, max_supervised_corrections=2,
        )
        executor = TypedActionExecutor(policy=policy)
        ordinary = ActionExecutionContext(
            facts=PolicyFacts(provider_quota_exceeded=True, retry_budget_exhausted=True),
            execution=ExecutionContext(ordinary_corrections_used=2, entities_modified=1,
                                       modifications_audited=True, modification_is_mechanical=True),
        )
        supervised = ActionExecutionContext(
            facts=ordinary.facts,
            execution=ExecutionContext(supervised_corrections_used=3, entities_modified=1,
                                       modifications_audited=True, modification_is_mechanical=True),
        )

        ordinary_result = executor.execute("WAIT_PROVIDER_RESET", {"wait_seconds": 1}, ordinary)
        supervised_result = executor.execute("WAIT_PROVIDER_RESET", {"wait_seconds": 1}, supervised)
        assert ordinary_result.executed is False
        assert ordinary_result.decision.selected_action_id == "WAIT_PROVIDER_RESET"
        assert supervised_result.executed is False
        assert supervised_result.decision.selected_action_id == "REQUEST_HUMAN"
