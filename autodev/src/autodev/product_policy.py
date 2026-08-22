from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from autodev.product_actions import (
    ProductActionRegistry,
    ProductAction,
    AuthorizationRequirement,
    get_action_registry,
)

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore


class ProductPolicyError(RuntimeError):
    """Error during policy engine operations."""


class DecisionType(str, Enum):
    """Type of decision that can be recorded."""

    SCOPE_EXTENSION_APPROVED = "scope_extension_approved"
    CRITERION_REALLOCATION_APPROVED = "criterion_reallocation_approved"
    ACTION_AUTHORIZED = "action_authorized"


@dataclass(frozen=True)
class PolicyFacts:
    """Immutable facts about the current system state."""

    provider_quota_exceeded: bool = False
    retry_budget_exhausted: bool = False
    git_state_diverged: bool = False
    origin_reachable: bool = False
    operation_failed_midway: bool = False
    partial_changes_exist: bool = False
    backup_target_is_new_or_matching_autodev_backup: bool = False
    task_execution_logged: bool = False
    necessary_change_outside_scope: bool = False
    scope_extension_approved_by_policy: bool = False
    criterion_ownership_mismatch: bool = False
    criterion_reallocation_approved_by_policy: bool = False
    agent_worktree_corrupted: bool = False
    backup_available: bool = False
    baseline_established: bool = False
    task_completed: bool = False
    validation_available: bool = False
    feature_paused: bool = False
    checkpoint_exists: bool = False
    feature_approved: bool = False
    tests_passed: bool = False
    scope_validated: bool = False
    uncommitted_changes: bool = False
    merge_conflicts: bool = False
    merge_in_progress: bool = False
    human_intervention_in_progress: bool = False
    feature_already_running: bool = False
    approval_recorded: bool = False
    manual_recovery_in_progress: bool = False
    committed_to_baseline: bool = False
    ambiguous_functional_impact: bool = False
    specification_absent: bool = False
    specification_generation_allowed: bool = False
    incident_environment_persistent: bool = False
    supervised_correction_limit_exceeded: bool = False
    merge_conflicts_unresolved: bool = False
    multiple_reasonable_solutions: bool = False
    git_safety_unguaranteed: bool = False
    business_ambiguity_unresolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def hash(self) -> str:
        """Generate deterministic hash of facts."""
        content = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass(frozen=True)
class ExecutionContext:
    """Runtime context for action execution with real audit data."""

    ordinary_corrections_used: int = 0
    supervised_corrections_used: int = 0
    entities_modified: int = 0
    modifications_audited: bool = False
    modification_is_mechanical: bool = False
    baseline_proof_available: bool = False
    exactly_one_bounded_modification: bool = False
    feature_id: str | None = None
    task_id: str | None = None
    target: str | None = None
    modification: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ExecutionContext:
        return ExecutionContext(
            ordinary_corrections_used=data.get("ordinary_corrections_used", 0),
            supervised_corrections_used=data.get("supervised_corrections_used", 0),
            entities_modified=data.get("entities_modified", 0),
            modifications_audited=data.get("modifications_audited", False),
            modification_is_mechanical=data.get("modification_is_mechanical", False),
            baseline_proof_available=data.get("baseline_proof_available", False),
            exactly_one_bounded_modification=data.get("exactly_one_bounded_modification", False),
            feature_id=data.get("feature_id"),
            task_id=data.get("task_id"),
            target=data.get("target"),
            modification=data.get("modification"),
        )


@dataclass(frozen=True)
class ActionExecutionContext:
    """Structured, non-command context supplied to the closed executor."""

    facts: PolicyFacts
    execution: ExecutionContext = field(default_factory=ExecutionContext)
    decisions: tuple[RecordedDecision, ...] = ()


@dataclass(frozen=True)
class ActionExecutionResult:
    """Auditable result of attempting one canonical product action."""

    action_id: str
    executed: bool
    decision: "PolicySelection"
    output: Mapping[str, Any]
    audit: Mapping[str, Any]


@dataclass(frozen=True)
class RecordedDecision:
    """A decision that has been made and recorded."""

    decision_id: str
    decision_type: DecisionType
    timestamp: str
    data: dict[str, Any]
    approver: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type.value,
            "timestamp": self.timestamp,
            "data": self.data,
            "approver": self.approver,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> RecordedDecision:
        return RecordedDecision(
            decision_id=data["decision_id"],
            decision_type=DecisionType(data["decision_type"]),
            timestamp=data["timestamp"],
            data=data["data"],
            approver=data.get("approver", "unknown"),
        )


@dataclass(frozen=True)
class ProductPolicy:
    """Policy configuration for action authorization and constraints."""

    schema_version: str
    plan_id: str
    created_at: str
    allow_scope_extension: bool = False
    allow_criterion_reallocation: bool = False
    max_ordinary_corrections: int = 3
    max_supervised_corrections: int = 7
    max_concurrent_agents: int = 1
    specification_generation_policy: str | None = "approved_only"
    custom_constraints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "allow_scope_extension": self.allow_scope_extension,
            "allow_criterion_reallocation": self.allow_criterion_reallocation,
            "max_ordinary_corrections": self.max_ordinary_corrections,
            "max_supervised_corrections": self.max_supervised_corrections,
            "max_concurrent_agents": self.max_concurrent_agents,
            "specification_generation_policy": self.specification_generation_policy,
            "custom_constraints": self.custom_constraints,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ProductPolicy:
        return ProductPolicy(
            schema_version=data["schema_version"],
            plan_id=data["plan_id"],
            created_at=data["created_at"],
            allow_scope_extension=data.get("allow_scope_extension", False),
            allow_criterion_reallocation=data.get("allow_criterion_reallocation", False),
            max_ordinary_corrections=data.get("max_ordinary_corrections", 3),
            max_supervised_corrections=data.get("max_supervised_corrections", 7),
            max_concurrent_agents=data.get("max_concurrent_agents", 1),
            specification_generation_policy=data.get("specification_generation_policy", "approved_only"),
            custom_constraints=data.get("custom_constraints", {}),
        )


@dataclass(frozen=True)
class PolicySelection:
    """Result of policy engine selection."""

    selected_action_id: str
    justification: str
    facts_hash: str
    decisions_hash: str
    policy_hash: str
    preconditions_met: bool
    authorization_allowed: bool
    stop_reasons_triggered: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_action_id": self.selected_action_id,
            "justification": self.justification,
            "facts_hash": self.facts_hash,
            "decisions_hash": self.decisions_hash,
            "policy_hash": self.policy_hash,
            "preconditions_met": self.preconditions_met,
            "authorization_allowed": self.authorization_allowed,
            "stop_reasons_triggered": self.stop_reasons_triggered,
            "timestamp": self.timestamp,
        }

    def hash(self) -> str:
        """Generate deterministic hash of selection."""
        content = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(content.encode()).hexdigest()


class ProductPolicyEngine:
    """Deterministic policy engine for action selection."""

    def __init__(
        self,
        registry: ProductActionRegistry | None = None,
        policy: ProductPolicy | None = None,
    ):
        self.registry = registry or get_action_registry()
        self.policy = policy or ProductPolicy(
            schema_version="1.0",
            plan_id="default",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._selection_history: dict[str, PolicySelection] = {}
        self.execution_context = ExecutionContext()

    def select_action(
        self,
        facts: PolicyFacts,
        decisions: list[RecordedDecision] | None = None,
        debugger: Callable[[str], None] | None = None,
        execution_context: ExecutionContext | None = None,
        action_inputs: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> PolicySelection:
        """Select an action based on facts, decisions, and policy.

        For identical facts, decisions, and execution context, this always
        returns the same action.
        This ensures deterministic behavior across multiple invocations.
        """
        decisions = decisions or []
        effective_execution_context = execution_context or ExecutionContext()
        action_inputs = action_inputs or {}
        facts_hash = facts.hash()
        decisions_hash = self._hash_decisions(decisions)
        policy_hash = self._policy_hash()
        execution_hash = self._hash_execution_context(effective_execution_context)
        inputs_hash = self._hash_action_inputs(action_inputs)

        # Check memoization for determinism
        memo_key = f"{facts_hash}|{decisions_hash}|{policy_hash}|{execution_hash}|{inputs_hash}"
        if memo_key in self._selection_history:
            return self._selection_history[memo_key]

        if debugger:
            debugger(f"Selecting action for facts_hash={facts_hash}")

        # Check mandatory escalation conditions (R15)
        mandatory_escalation = self._check_mandatory_escalation(
            facts,
            decisions,
            debugger,
            effective_execution_context,
        )
        if mandatory_escalation:
            selection = PolicySelection(
                selected_action_id="REQUEST_HUMAN",
                justification=mandatory_escalation,
                facts_hash=facts_hash,
                decisions_hash=decisions_hash,
                policy_hash=policy_hash,
                preconditions_met=False,
                authorization_allowed=False,
            )
            self._selection_history[memo_key] = selection
            return selection

        # Evaluate each action to find the best fit
        candidates: list[tuple[ProductAction, int, str]] = []
        sensitive_blocking_reason: str | None = None

        for action in self.registry.list_actions():
            score, reason = self._evaluate_action(
                action, facts, decisions, effective_execution_context, debugger, enforce_runtime_limits=False,
            )
            candidate_inputs = action_inputs.get(action.action_id)
            if candidate_inputs is not None and not isinstance(candidate_inputs, Mapping):
                raise ProductPolicyError("Candidate action inputs must be structured mappings")
            if (
                score < 0
                and action.action_id in {"APPLY_SCOPE_EXTENSION", "APPLY_CRITERION_REALLOCATION"}
                and all(facts.to_dict().get(state) for state in action.preconditions.required_state)
            ):
                sensitive_blocking_reason = self.authorize_action(
                    action.action_id,
                    ActionExecutionContext(facts, effective_execution_context, tuple(decisions)),
                    candidate_inputs,
                    check_mandatory_escalation=False,
                ).justification
            if score >= 0:
                verdict = self.authorize_action(
                    action.action_id,
                    ActionExecutionContext(facts, effective_execution_context, tuple(decisions)),
                    candidate_inputs,
                    check_mandatory_escalation=False,
                )
                if not verdict.authorization_allowed:
                    if action.action_id in {"APPLY_SCOPE_EXTENSION", "APPLY_CRITERION_REALLOCATION"}:
                        sensitive_blocking_reason = verdict.justification
                    continue
                candidates.append((action, score, reason))
                if debugger:
                    debugger(f"  {action.action_id}: score={score}")

        # Sort candidates by score (higher is better)
        candidates.sort(key=lambda x: x[1], reverse=True)

        if sensitive_blocking_reason:
            selection = PolicySelection(
                selected_action_id="REQUEST_HUMAN",
                justification=sensitive_blocking_reason,
                facts_hash=facts_hash,
                decisions_hash=decisions_hash,
                policy_hash=policy_hash,
                preconditions_met=False,
                authorization_allowed=False,
            )
        elif not candidates:
            # No action matched; escalate to human
            selection = PolicySelection(
                selected_action_id="REQUEST_HUMAN",
                justification="No suitable action found in registry",
                facts_hash=facts_hash,
                decisions_hash=decisions_hash,
                policy_hash=policy_hash,
                preconditions_met=False,
                authorization_allowed=False,
            )
        else:
            best_action, score, reason = candidates[0]
            selection = PolicySelection(
                selected_action_id=best_action.action_id,
                justification=reason,
                facts_hash=facts_hash,
                decisions_hash=decisions_hash,
                policy_hash=policy_hash,
                preconditions_met=True,
                authorization_allowed=True,
            )

        # Memoize for determinism
        self._selection_history[memo_key] = selection

        return selection

    def _check_mandatory_escalation(
        self,
        facts: PolicyFacts,
        decisions: list[RecordedDecision],
        debugger: Callable[[str], None] | None = None,
        execution_context: ExecutionContext | None = None,
    ) -> str | None:
        """Check if mandatory escalation to REQUEST_HUMAN is required (R15).

        Returns justification string if escalation required, None otherwise.
        """
        # AC-R15-1: Unresolved merge conflicts impose human escalation
        if facts.merge_conflicts_unresolved:
            if debugger:
                debugger("Merge conflicts remain unresolved")
            return "Merge conflicts remain unresolved; human decision required (AC-R15-1)"

        # AC-R15-1: Business ambiguity imposes human escalation
        if facts.business_ambiguity_unresolved:
            if debugger:
                debugger("Business/functional ambiguity remains unresolved")
            return "Business/functional ambiguity unresolved; human decision required (AC-R15-1)"

        # AC-R15-1: Git safety cannot be guaranteed
        if facts.git_safety_unguaranteed:
            if debugger:
                debugger("Git safety cannot be guaranteed")
            return "Git safety cannot be guaranteed; human decision required (AC-R15-1, AC-R15-5)"

        # AC-R15-1, AC-R15-5: Multiple reasonable solutions exist
        if facts.multiple_reasonable_solutions:
            if debugger:
                debugger("Multiple reasonable solutions exist, ambiguous choice")
            return "Multiple reasonable solutions exist; human judgment required (AC-R15-5)"

        # AC-R15-2: Scope or criterion escalade without explicit authorization must escalate to REQUEST_HUMAN
        if facts.necessary_change_outside_scope:
            # Check if scope extension is explicitly authorized
            if not self.policy.allow_scope_extension:
                if debugger:
                    debugger("Scope extension needed but not authorized by policy")
                return "Scope extension required but not authorized by policy; REQUEST_HUMAN needed (AC-R15-2)"

        if facts.criterion_ownership_mismatch:
            # Check if criterion reallocation is explicitly authorized
            if not self.policy.allow_criterion_reallocation:
                if debugger:
                    debugger("Criterion reallocation needed but not authorized by policy")
                return "Criterion reallocation required but not authorized by policy; REQUEST_HUMAN needed (AC-R15-2)"

        # AC-R15-6: absence is only actionable automatically when both the
        # runtime authorization and one canonical policy mode explicitly allow it.
        if facts.specification_absent and not self._specification_generation_is_effectively_authorized(facts):
            if debugger:
                debugger("Specification absent without explicit effective generation authorization")
            return "Specification absent without policy authorization for generation (AC-R15-6)"

        # AC-R15-6: Environmental incident persistent beyond bound
        if facts.incident_environment_persistent:
            if debugger:
                debugger("Environmental incident persists beyond bound")
            return "Environmental incident persists beyond recovery bound (AC-R15-6)"

        # AC-R15-7: Only supervised correction limit triggers REQUEST_HUMAN, not ordinary
        if facts.supervised_correction_limit_exceeded or (
            execution_context is not None
            and execution_context.supervised_corrections_used >= self.policy.max_supervised_corrections
        ):
            if debugger:
                debugger("Supervised correction limit exceeded")
            return "Supervised correction limit exceeded; human decision required (AC-R15-7)"

        return None

    def _specification_generation_is_effectively_authorized(self, facts: PolicyFacts) -> bool:
        """Return true only for an explicit runtime authorization and known policy mode."""
        return (
            facts.specification_generation_allowed is True
            and self.policy.specification_generation_policy in {"draft", "autonomous"}
        )

    def authorize_action(
        self,
        action_id: str,
        context: ActionExecutionContext,
        inputs: Mapping[str, Any] | None = None,
        check_mandatory_escalation: bool = True,
    ) -> PolicySelection:
        """Make a blocking authorization decision for one requested canonical action."""
        action = self.registry.get_action(action_id)
        if action is None:
            raise ProductPolicyError(f"Unknown action: {action_id}")
        if not isinstance(context, ActionExecutionContext):
            raise ProductPolicyError("Execution context must be structured ActionExecutionContext")

        facts, execution, decisions = context.facts, context.execution, list(context.decisions)
        facts_hash, decisions_hash, policy_hash = facts.hash(), self._hash_decisions(decisions), self._policy_hash()
        if check_mandatory_escalation:
            escalation = self._check_mandatory_escalation(facts, decisions, execution_context=execution)
            if escalation:
                return PolicySelection("REQUEST_HUMAN", escalation, facts_hash, decisions_hash, policy_hash, False, False)

        if action_id in {"APPLY_SCOPE_EXTENSION", "APPLY_CRITERION_REALLOCATION"}:
            input_reason = self._sensitive_inputs_blocking_reason(action, inputs)
            if input_reason:
                return PolicySelection("REQUEST_HUMAN", input_reason, facts_hash, decisions_hash, policy_hash, False, False)

        score, reason = self._evaluate_action(action, facts, decisions, execution, enforce_runtime_limits=True)
        if score < 0:
            return PolicySelection("REQUEST_HUMAN", reason, facts_hash, decisions_hash, policy_hash, False, False)

        blocking_reason = self._execution_blocking_reason(action, inputs, facts, execution, decisions)
        if blocking_reason:
            # The ordinary ceiling transfers a refused proposal to supervision
            # without itself selecting REQUEST_HUMAN (AC-R15-7).
            selected_id = action_id if "ordinary correction limit" in blocking_reason.lower() else "REQUEST_HUMAN"
            return PolicySelection(selected_id, blocking_reason, facts_hash, decisions_hash, policy_hash, False, False)
        return PolicySelection(action_id, reason, facts_hash, decisions_hash, policy_hash, True, True)

    def _sensitive_inputs_blocking_reason(
        self,
        action: ProductAction,
        inputs: Mapping[str, Any] | None,
    ) -> str | None:
        """Validate effective candidate inputs without inventing missing evidence."""
        if not isinstance(inputs, Mapping):
            return "Effective action inputs are required"
        required = {parameter.name: parameter.type for parameter in action.inputs.required}
        if missing := sorted(set(required) - set(inputs)):
            return f"Required effective inputs are missing: {', '.join(missing)}"
        if extra := sorted(set(inputs) - set(required)):
            return f"Unknown effective inputs are not allowed: {', '.join(extra)}"
        for name, expected_type in required.items():
            value = inputs[name]
            if expected_type == "string" and (not isinstance(value, str) or isinstance(value, bool)):
                return f"Effective input {name} must be a string"
            if expected_type == "object" and not isinstance(value, dict):
                return f"Effective input {name} must be an object"
        return None

    def _execution_blocking_reason(
        self,
        action: ProductAction,
        inputs: Mapping[str, Any] | None,
        facts: PolicyFacts,
        execution: ExecutionContext,
        decisions: list[RecordedDecision],
    ) -> str | None:
        """Hard runtime gates that cannot be reduced to a justification."""
        if execution.ordinary_corrections_used > self.policy.max_ordinary_corrections:
            return "Ordinary correction limit exceeded; transfer to supervisor required"
        if execution.entities_modified > action.scope.max_entities:
            return "Declared action scope exceeded"
        if action.scope.modifications_bounded and execution.entities_modified > 0 and not execution.modifications_audited:
            return "Mandatory audit evidence is missing"
        if action.scope.modifications_bounded and execution.entities_modified > 0 and not execution.modification_is_mechanical:
            return "Modification is not mechanical"
        if action.action_id in {"APPLY_SCOPE_EXTENSION", "APPLY_CRITERION_REALLOCATION"}:
            if inputs is None:
                return "Effective action inputs are required"
            if execution.entities_modified != 1:
                return "Exactly one modification is required"
            if not execution.exactly_one_bounded_modification:
                return "Exactly one bounded modification is required"
            if not execution.baseline_proof_available:
                return "Baseline proof is required"
            if not facts.baseline_established:
                return "Baseline is not established"
            if facts.ambiguous_functional_impact or facts.business_ambiguity_unresolved:
                return "Ambiguous functional change requires human decision"
            if not any(self._decision_allows_action(decision, action, inputs, execution) for decision in decisions):
                return "Explicit plan decision matching action, feature, task, target, and modification is required"
        if facts.uncommitted_changes and action.action_id == "INTEGRATE_FEATURE":
            return "Pre-existing user changes cannot be overwritten"
        return None

    def _evaluate_action(
        self,
        action: ProductAction,
        facts: PolicyFacts,
        decisions: list[RecordedDecision],
        execution: ExecutionContext,
        debugger: Callable[[str], None] | None = None,
        enforce_runtime_limits: bool = False,
    ) -> tuple[int, str]:
        """Evaluate action for suitability given facts and policy.

        Returns (score, reason) where score >= 0 if action is viable.
        Higher scores = better fit.
        Negative score = not viable.
        """
        score = 0
        reasons: list[str] = []

        # Check preconditions
        precond_score, precond_reasons = self._check_preconditions(action, facts)
        if precond_score < 0:
            return -1, "; ".join(precond_reasons)
        score += precond_score
        reasons.extend(precond_reasons)

        # Check authorization
        auth_score, auth_reasons = self._check_authorization(action, facts, decisions)
        if auth_score < 0:
            return -1, "Authorization not allowed"
        score += auth_score
        reasons.extend(auth_reasons)

        # Check stop reasons
        stop_triggered = self._check_stop_reasons(action, facts)
        if stop_triggered:
            return -1, f"Stop reasons triggered: {', '.join(stop_triggered)}"

        # Check scope constraints (AC-R9-2)
        scope_score, scope_reasons = self._check_scope_constraints(action)
        if scope_score < 0:
            return -1, "Scope constraints violated"
        score += scope_score
        reasons.extend(scope_reasons)

        # Check policy correction limits (AC-R9-2)
        limit_score, limit_reasons = self._check_policy_limits(action, execution, enforce_runtime_limits)
        if limit_score < 0:
            return -1, f"Policy limits exceeded: {'; '.join(limit_reasons)}"
        score += limit_score
        reasons.extend(limit_reasons)

        return score, "; ".join(reasons) if reasons else "Action selected"

    def _check_scope_constraints(
        self,
        action: ProductAction,
    ) -> tuple[int, list[str]]:
        """Check scope constraints of action.

        Returns (score, reasons).
        score >= 0 if scope is acceptable, negative otherwise.
        """
        # All actions must respect their declared scope
        # max_entities and entity_types are constraints that must be honored
        reasons: list[str] = []

        if action.scope.max_entities > 0:
            reasons.append(f"Scope bounded to {action.scope.max_entities} entities")

        if action.scope.modifications_bounded:
            reasons.append("Modifications are bounded and auditable")

        return 1, reasons

    def _check_policy_limits(
        self,
        action: ProductAction,
        execution: ExecutionContext,
        enforce_runtime_limits: bool = False,
    ) -> tuple[int, list[str]]:
        """Check policy limits and quotas (AC-R9-2).

        Returns (score, reasons).
        score >= 0 if within limits, negative otherwise.
        """
        reasons: list[str] = []

        # Sensible actions requiring explicit policy authorization are subject to limits
        if action.authorization.policy_requirement == AuthorizationRequirement.EXPLICIT:
            if action.action_id == "APPLY_SCOPE_EXTENSION":
                if self.policy.allow_scope_extension:
                    reasons.append("Scope extension authorized by policy")
                else:
                    return -1, ["Scope extension not authorized by policy"]
            elif action.action_id == "APPLY_CRITERION_REALLOCATION":
                if self.policy.allow_criterion_reallocation:
                    reasons.append("Criterion reallocation authorized by policy")
                else:
                    return -1, ["Criterion reallocation not authorized by policy"]

        # Check scope constraints with real execution data (AC-R9-2)
        if enforce_runtime_limits and action.scope.max_entities > 0:
            if execution.entities_modified > action.scope.max_entities:
                return -1, [f"Declared action scope exceeded: entities modified ({execution.entities_modified}) exceeds max ({action.scope.max_entities})"]

        # Check modification bounds and audit requirements (AC-R9-2)
        if enforce_runtime_limits and action.scope.modifications_bounded and execution.entities_modified > 0:
            if not execution.modifications_audited:
                return -1, [f"Mandatory audit evidence is missing for {action.action_id}"]
            if not execution.modification_is_mechanical:
                return -1, [f"Modification must be mechanical for {action.action_id}"]

        return 1, reasons

    def _check_preconditions(
        self,
        action: ProductAction,
        facts: PolicyFacts,
    ) -> tuple[int, list[str]]:
        """Check action preconditions against facts.

        Returns (score, reasons).
        score >= 0 if preconditions met, negative otherwise.
        """
        facts_dict = facts.to_dict()
        score = 0
        reasons: list[str] = []

        # All required states must be present
        for required in action.preconditions.required_state:
            if required not in facts_dict or not facts_dict[required]:
                return -1, [f"Missing required state: {required}"]
            score += 1
            reasons.append(f"Required: {required}")

        # No forbidden states must be present
        for forbidden in action.preconditions.forbidden_state:
            if forbidden in facts_dict and facts_dict[forbidden]:
                return -1, [f"Forbidden state present: {forbidden}"]
            score += 1
            reasons.append(f"Allowed: no {forbidden}")

        return score, reasons

    def _check_authorization(
        self,
        action: ProductAction,
        facts: PolicyFacts,
        decisions: list[RecordedDecision],
    ) -> tuple[int, list[str]]:
        """Check if policy allows this action.

        Returns (score, reasons).
        """
        auth = action.authorization
        reasons: list[str] = []

        # NONE: always allowed
        if auth.policy_requirement == AuthorizationRequirement.NONE:
            return 1, ["No authorization required"]

        # EXPLICIT: must have policy field set or matching decision
        if auth.policy_requirement == AuthorizationRequirement.EXPLICIT:
            if auth.policy_field:
                policy_dict = self.policy.to_dict()
                if auth.policy_field in policy_dict and policy_dict[auth.policy_field]:
                    return 1, [f"Policy allows: {auth.policy_field}"]
                if auth.policy_field in self.policy.custom_constraints:
                    return 1, [f"Custom policy allows: {auth.policy_field}"]
            # Check if matching decision exists
            for decision in decisions:
                if self._decision_allows_action(decision, action):
                    return 1, ["Matching decision allows action"]
            return -1, ["Policy does not authorize action"]

        # SUPERVISOR_ONLY: only explicit human decision allows
        if auth.policy_requirement == AuthorizationRequirement.SUPERVISOR_ONLY:
            for decision in decisions:
                if (decision.decision_type == DecisionType.ACTION_AUTHORIZED and
                    decision.data.get("action_id") == action.action_id):
                    return 1, ["Supervisor authorized this action"]
            return -1, ["Supervisor authorization required"]

        return 0, ["Authorization checked"]

    def _check_stop_reasons(self, action: ProductAction, facts: PolicyFacts) -> list[str]:
        """Check if any stop reasons are triggered.

        If any stop reason is triggered, this forces REQUEST_HUMAN.
        """
        triggered: list[str] = []
        facts_dict = facts.to_dict()

        # Stop reasons are conditions that block the action
        # They are evaluated as a heuristic but not as hard blockers
        # unless the action explicitly requires them
        for stop_reason in action.stop_reasons:
            # Parse the stop reason text to infer what fact it checks
            # For now, we use simple keyword matching
            if self._stop_reason_applies(stop_reason.reason, facts_dict):
                triggered.append(stop_reason.reason)

        return triggered

    def _stop_reason_applies(self, reason: str, facts_dict: dict[str, Any]) -> bool:
        """Heuristically check if a stop reason applies."""
        # Simple keyword matching; could be more sophisticated
        keywords = {
            "unresolvable": facts_dict.get("merge_conflicts", False),
            "insufficient disk": False,  # Would need runtime check
            "corrupted": facts_dict.get("agent_worktree_corrupted", False),
            "ambiguous": facts_dict.get("ambiguous_functional_impact", False),
        }
        return any(kw in reason.lower() for kw, triggered in keywords.items() if triggered)

    def _decision_allows_action(
        self,
        decision: RecordedDecision,
        action: ProductAction,
        inputs: Mapping[str, Any] | None = None,
        execution: ExecutionContext | None = None,
    ) -> bool:
        """Require an acquired decision to identify this exact sensitive change."""
        expected_type = {
            "APPLY_SCOPE_EXTENSION": DecisionType.SCOPE_EXTENSION_APPROVED,
            "APPLY_CRITERION_REALLOCATION": DecisionType.CRITERION_REALLOCATION_APPROVED,
        }.get(action.action_id)
        if expected_type is None:
            return False
        if decision.decision_type != expected_type or decision.data.get("action_id") != action.action_id:
            return False
        if inputs is None or execution is None or decision.decision_id != inputs.get("approval_id"):
            return False
        context_identity = execution.to_dict()
        for identity in ("feature_id", "task_id", "target", "modification"):
            if not context_identity.get(identity) or decision.data.get(identity) != context_identity[identity]:
                return False
        if action.action_id == "APPLY_SCOPE_EXTENSION":
            change_definition = inputs.get("change_definition")
            if not isinstance(change_definition, Mapping):
                return False
            if any(change_definition.get(identity) != context_identity[identity]
                   for identity in ("feature_id", "task_id", "target", "modification")):
                return False
            return decision.data.get("change_definition") == change_definition
        return (
            decision.data.get("criterion") == inputs.get("criterion")
            and decision.data.get("new_owner") == inputs.get("new_owner")
        )

    def _hash_decisions(self, decisions: list[RecordedDecision]) -> str:
        """Generate deterministic hash of decisions list."""
        # Sort by decision_id to ensure consistent ordering
        sorted_decisions = sorted(decisions, key=lambda d: d.decision_id)
        content = json.dumps(
            [d.to_dict() for d in sorted_decisions],
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def _hash_execution_context(self, execution_context: ExecutionContext) -> str:
        """Generate a deterministic hash of runtime data affecting selection."""
        content = json.dumps(
            execution_context.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def _hash_action_inputs(self, action_inputs: Mapping[str, Mapping[str, Any]]) -> str:
        """Hash candidate inputs so cached authorizations cannot cross input contexts."""
        content = json.dumps(action_inputs, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    def _policy_hash(self) -> str:
        """Generate deterministic hash of current policy."""
        content = json.dumps(
            self.policy.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(content.encode()).hexdigest()


class TypedActionExecutor:
    """Executor that validates and runs actions with strict typing."""

    _INTERNAL_HANDLER_METHODS = MappingProxyType({
        "WAIT_PROVIDER_RESET": "_handle_wait_provider_reset",
        "RECONCILE_WORKTREE": "_handle_reconcile_worktree",
        "PRESERVE_PARTIAL_CHANGES": "_handle_preserve_partial_changes",
        "REGENERATE_TASK_REPORT": "_handle_regenerate_task_report",
        "REQUEST_SCOPE_EXTENSION": "_handle_request_scope_extension",
        "APPLY_SCOPE_EXTENSION": "_handle_apply_scope_extension",
        "REQUEST_CRITERION_REALLOCATION": "_handle_request_criterion_reallocation",
        "APPLY_CRITERION_REALLOCATION": "_handle_apply_criterion_reallocation",
        "RECOVER_AGENT_GIT_HISTORY": "_handle_recover_agent_git_history",
        "RUN_BASELINE_VALIDATION": "_handle_run_baseline_validation",
        "REVALIDATE_TASK": "_handle_revalidate_task",
        "RESUME_FEATURE": "_handle_resume_feature",
        "INTEGRATE_FEATURE": "_handle_integrate_feature",
        "REQUEST_HUMAN": "_handle_request_human",
    })

    def __init__(
        self,
        registry: ProductActionRegistry | None = None,
        policy: ProductPolicy | None = None,
    ):
        self.registry = registry or get_action_registry()
        self.policy_engine = ProductPolicyEngine(registry=self.registry, policy=policy)
        canonical_ids = {action.action_id for action in self.registry.actions}
        if canonical_ids != set(self._INTERNAL_HANDLER_METHODS):
            raise ProductPolicyError("Every canonical action requires one authorized internal handler")
        table = {
            action_id: getattr(self, method_name)
            for action_id, method_name in self._INTERNAL_HANDLER_METHODS.items()
        }
        if not all(callable(handler) for handler in table.values()):
            raise ProductPolicyError("An authorized internal handler is unavailable")
        self._handlers: Mapping[str, Callable[[Mapping[str, Any], ActionExecutionContext], Mapping[str, Any] | None]] = MappingProxyType(table)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_handlers" and hasattr(self, "_handlers"):
            raise AttributeError("Internal handler table is immutable")
        super().__setattr__(name, value)

    @property
    def handlers(self) -> Mapping[str, Callable[[Mapping[str, Any], ActionExecutionContext], Mapping[str, Any] | None]]:
        """Read-only diagnostic view of the closed internal execution table."""
        return self._handlers

    @staticmethod
    def _accepted(inputs: Mapping[str, Any], context: ActionExecutionContext) -> Mapping[str, Any]:
        return {"status": "accepted", "input_names": tuple(sorted(inputs))}

    def _handle_wait_provider_reset(self, inputs, context): return self._accepted(inputs, context)
    def _handle_reconcile_worktree(self, inputs, context): return self._accepted(inputs, context)
    def _handle_regenerate_task_report(self, inputs, context): return self._accepted(inputs, context)
    def _handle_request_scope_extension(self, inputs, context): return self._accepted(inputs, context)
    def _handle_apply_scope_extension(self, inputs, context): return self._accepted(inputs, context)
    def _handle_request_criterion_reallocation(self, inputs, context): return self._accepted(inputs, context)
    def _handle_apply_criterion_reallocation(self, inputs, context): return self._accepted(inputs, context)
    def _handle_recover_agent_git_history(self, inputs, context): return self._accepted(inputs, context)
    def _handle_run_baseline_validation(self, inputs, context): return self._accepted(inputs, context)
    def _handle_revalidate_task(self, inputs, context): return self._accepted(inputs, context)
    def _handle_resume_feature(self, inputs, context): return self._accepted(inputs, context)
    def _handle_integrate_feature(self, inputs, context): return self._accepted(inputs, context)
    def _handle_request_human(self, inputs, context): return self._accepted(inputs, context)

    def _handle_preserve_partial_changes(self, inputs, context):
        """Create an exclusive Autodev-owned backup or return its verified prior result."""
        worktree_root = Path.cwd().resolve()
        backup_root = (worktree_root / ".autodev" / "backups").resolve()
        source = Path(inputs["source_path"]).resolve(strict=True)
        target = Path(inputs["backup_path"]).resolve(strict=False)
        if not source.is_file() or source.is_symlink() or not source.is_relative_to(worktree_root):
            raise ProductPolicyError("Source path must be a regular file inside the current worktree")
        if not target.is_relative_to(backup_root) or target == backup_root:
            raise ProductPolicyError("Backup path must be a unique file under .autodev/backups")
        if source == target:
            raise ProductPolicyError("Source and backup paths must differ")

        source_bytes = source.read_bytes()
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        metadata_path = target.with_name(f"{target.name}.autodev-backup.json")
        if target.exists() or metadata_path.exists():
            if target.is_file() and metadata_path.is_file():
                try:
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    metadata = None
                if (
                    isinstance(metadata, dict)
                    and metadata.get("owner") == "autodev"
                    and metadata.get("action_id") == "PRESERVE_PARTIAL_CHANGES"
                    and metadata.get("source_path") == str(source)
                    and metadata.get("source_content_hash") == source_hash
                    and metadata.get("backup_content_hash") == hashlib.sha256(target.read_bytes()).hexdigest()
                ):
                    return {"status": "preserved", "backup_path": str(target), "idempotent": True}
            raise ProductPolicyError("Refusing pre-existing backup target without coherent Autodev ownership evidence")

        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.resolve(strict=False).is_relative_to(backup_root):
            raise ProductPolicyError("Backup path resolves outside the controlled Autodev backup directory")
        try:
            with target.open("xb") as backup_file:
                backup_file.write(source_bytes)
            metadata = {
                "owner": "autodev",
                "action_id": "PRESERVE_PARTIAL_CHANGES",
                "source_path": str(source),
                "source_content_hash": source_hash,
                "backup_content_hash": hashlib.sha256(source_bytes).hexdigest(),
            }
            with metadata_path.open("x", encoding="utf-8") as metadata_file:
                json.dump(metadata, metadata_file, sort_keys=True)
        except FileExistsError as error:
            raise ProductPolicyError("Refusing concurrent or pre-existing backup target") from error
        return {"status": "preserved", "backup_path": str(target), "idempotent": False}

    def validate_action_exists(self, action_id: str) -> ProductAction:
        """Validate that action exists in registry."""
        action = self.registry.get_action(action_id)
        if not action:
            raise ProductPolicyError(f"Unknown action: {action_id}")
        return action

    def _canonical_action(self, action: str | ProductAction) -> ProductAction:
        if isinstance(action, str):
            return self.validate_action_exists(action)
        canonical = self.registry.get_action(action.action_id)
        if canonical is not action:
            raise ProductPolicyError("External ProductAction definitions are not accepted")
        return canonical

    def validate_inputs(self, action: str | ProductAction, inputs: Mapping[str, Any]) -> None:
        """Validate that inputs match action specification."""
        action = self._canonical_action(action)
        # Check required inputs
        provided_names = set(inputs.keys())
        required_names = {p.name for p in action.inputs.required}
        optional_names = {p.name for p in action.inputs.optional}
        allowed_names = required_names | optional_names

        missing = required_names - provided_names
        if missing:
            raise ProductPolicyError(
                f"Missing required inputs for {action.action_id}: {missing}"
            )

        # Reject unknown/extra parameters (AC-R9-3)
        extra = provided_names - allowed_names
        if extra:
            raise ProductPolicyError(
                f"Unknown input parameters for {action.action_id}: {extra}. "
                f"Only these are allowed: {allowed_names}"
            )

        # Check types (simplified)
        for param in action.inputs.required + action.inputs.optional:
            if param.name not in inputs:
                continue
            value = inputs[param.name]
            if not self._type_matches(value, param.type):
                raise ProductPolicyError(
                    f"Input {param.name} has wrong type "
                    f"(expected {param.type}, got {type(value).__name__})"
                )

    def _type_matches(self, value: Any, param_type: str) -> bool:
        """Check if value matches parameter type."""
        if param_type == "string":
            return isinstance(value, str) and not isinstance(value, bool)
        if param_type == "integer":
            # Reject booleans; bool is a subclass of int in Python
            return isinstance(value, int) and not isinstance(value, bool)
        if param_type == "boolean":
            return isinstance(value, bool)
        if param_type == "list":
            return isinstance(value, list)
        if param_type == "object":
            return isinstance(value, dict)
        if param_type == "path":
            return isinstance(value, (str, Path)) and not isinstance(value, bool)
        return False  # Unknown type; reject (was: return True)

    def reject_free_commands(self, action_id: str) -> None:
        """Ensure action exists (no free-form commands allowed)."""
        if not self.registry.validate_action_id(action_id):
            raise ProductPolicyError(
                f"Action '{action_id}' is not in the closed action registry. "
                "Only pre-defined actions are allowed."
            )

    def validate_preconditions(
        self,
        action: str | ProductAction,
        facts: PolicyFacts,
    ) -> None:
        """Validate that preconditions are met before execution."""
        action = self._canonical_action(action)
        facts_dict = facts.to_dict()

        # Check required states
        for required in action.preconditions.required_state:
            if required not in facts_dict or not facts_dict[required]:
                raise ProductPolicyError(
                    f"Precondition failed: {required} must be true"
                )

        # Check forbidden states
        for forbidden in action.preconditions.forbidden_state:
            if forbidden in facts_dict and facts_dict[forbidden]:
                raise ProductPolicyError(
                    f"Precondition failed: {forbidden} must be false"
                )

    def execute(
        self,
        action_id: str,
        inputs: Mapping[str, Any],
        context: ActionExecutionContext,
    ) -> ActionExecutionResult:
        """The only public execution entry point for product actions."""
        if not isinstance(action_id, str):
            raise ProductPolicyError("Action identifier must be a canonical string")
        if not isinstance(inputs, Mapping):
            raise ProductPolicyError("Action inputs must be a structured mapping")
        action = self.validate_action_exists(action_id)
        self.validate_inputs(action, inputs)
        decision = self.policy_engine.authorize_action(action_id, context, inputs)
        audit = MappingProxyType({
            "action_id": action_id,
            "facts_hash": decision.facts_hash,
            "decisions_hash": decision.decisions_hash,
            "policy_hash": decision.policy_hash,
            "mandatory_evidence": tuple(action.audit_trail.mandatory_evidence),
        })
        if not decision.authorization_allowed:
            return ActionExecutionResult(action_id, False, decision, MappingProxyType({}), audit)
        handler = self._handlers.get(action_id)
        if handler is None:
            raise ProductPolicyError(f"No handler registered for {action_id}")
        output = handler(MappingProxyType(dict(inputs)), context) or {}
        if not isinstance(output, Mapping):
            raise ProductPolicyError("Action handler must return a structured mapping")
        return ActionExecutionResult(action_id, True, decision, MappingProxyType(dict(output)), audit)
