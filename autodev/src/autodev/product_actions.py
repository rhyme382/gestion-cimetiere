from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Literal, Mapping

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore


class ProductActionError(RuntimeError):
    """Error during product action operations."""


class ActionCategory(str, Enum):
    """Category of action for organization and routing."""

    WORKFLOW_CONTROL = "workflow_control"
    GIT_RECONCILIATION = "git_reconciliation"
    DATA_PRESERVATION = "data_preservation"
    REPORTING = "reporting"
    SCOPE_MANAGEMENT = "scope_management"
    OWNERSHIP_MANAGEMENT = "ownership_management"
    AGENT_RECOVERY = "agent_recovery"
    VALIDATION = "validation"
    RESUMPTION = "resumption"
    INTEGRATION = "integration"
    HUMAN_ESCALATION = "human_escalation"


class AuthorizationRequirement(str, Enum):
    """What policy authorization is required for an action."""

    NONE = "none"
    EXPLICIT = "explicit"
    SUPERVISOR_ONLY = "supervisor_only"


@dataclass(frozen=True)
class Preconditions:
    """Required and forbidden states for an action."""

    required_state: list[str]
    forbidden_state: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Preconditions:
        return Preconditions(
            required_state=data.get("required_state", []),
            forbidden_state=data.get("forbidden_state", []),
        )


@dataclass(frozen=True)
class Authorization:
    """Authorization requirements for an action."""

    policy_requirement: AuthorizationRequirement
    default_allowed: bool
    policy_field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_requirement": self.policy_requirement.value,
            "default_allowed": self.default_allowed,
            "policy_field": self.policy_field,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Authorization:
        return Authorization(
            policy_requirement=AuthorizationRequirement(data["policy_requirement"]),
            default_allowed=data["default_allowed"],
            policy_field=data.get("policy_field"),
        )


@dataclass(frozen=True)
class InputParameter:
    """Specification for an input parameter."""

    name: str
    type: Literal["string", "integer", "boolean", "list", "object", "path"]
    description: str = ""
    default: str | int | bool | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "name": self.name,
            "type": self.type,
        }
        if self.description:
            result["description"] = self.description
        if self.default is not None:
            result["default"] = self.default
        return result

    @staticmethod
    def from_dict(data: dict[str, Any]) -> InputParameter:
        return InputParameter(
            name=data["name"],
            type=data["type"],
            description=data.get("description", ""),
            default=data.get("default"),
        )


@dataclass(frozen=True)
class Inputs:
    """Input specification for an action."""

    required: list[InputParameter]
    optional: list[InputParameter] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "required": [p.to_dict() for p in self.required],
            "optional": [p.to_dict() for p in self.optional],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Inputs:
        return Inputs(
            required=[InputParameter.from_dict(p) for p in data.get("required", [])],
            optional=[InputParameter.from_dict(p) for p in data.get("optional", [])],
        )


@dataclass(frozen=True)
class Scope:
    """Scope constraints for action execution."""

    max_entities: int
    entity_types: list[str]
    modifications_bounded: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Scope:
        return Scope(
            max_entities=data["max_entities"],
            entity_types=data.get("entity_types", []),
            modifications_bounded=data["modifications_bounded"],
        )


@dataclass(frozen=True)
class AuditTrail:
    """Audit requirements for an action."""

    mandatory_evidence: list[str]
    decision_recorded: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AuditTrail:
        return AuditTrail(
            mandatory_evidence=data.get("mandatory_evidence", []),
            decision_recorded=data["decision_recorded"],
        )


@dataclass(frozen=True)
class IdempotenceRule:
    """Idempotence guarantees for an action."""

    is_idempotent: bool
    rule: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> IdempotenceRule:
        return IdempotenceRule(
            is_idempotent=data["is_idempotent"],
            rule=data["rule"],
        )


@dataclass(frozen=True)
class RollbackStrategy:
    """Rollback capabilities for an action."""

    can_rollback: bool
    strategy: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> RollbackStrategy:
        return RollbackStrategy(
            can_rollback=data["can_rollback"],
            strategy=data["strategy"],
        )


@dataclass(frozen=True)
class StopReason:
    """Reason that forces REQUEST_HUMAN."""

    reason: str
    severity: Literal["critical", "high", "medium"]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> StopReason:
        return StopReason(
            reason=data["reason"],
            severity=data["severity"],
        )


@dataclass(frozen=True)
class ProductAction:
    """Complete definition of a closed action in the product supervisor."""

    schema_version: str
    action_id: str
    title: str
    category: ActionCategory
    preconditions: Preconditions
    authorization: Authorization
    inputs: Inputs
    expected_effect: str
    scope: Scope
    audit_trail: AuditTrail
    idempotence_rule: IdempotenceRule
    rollback_strategy: RollbackStrategy
    stop_reasons: list[StopReason]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "action_id": self.action_id,
            "title": self.title,
            "category": self.category.value,
            "preconditions": self.preconditions.to_dict(),
            "authorization": self.authorization.to_dict(),
            "inputs": self.inputs.to_dict(),
            "expected_effect": self.expected_effect,
            "scope": self.scope.to_dict(),
            "audit_trail": self.audit_trail.to_dict(),
            "idempotence_rule": self.idempotence_rule.to_dict(),
            "rollback_strategy": self.rollback_strategy.to_dict(),
            "stop_reasons": [sr.to_dict() for sr in self.stop_reasons],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ProductAction:
        return ProductAction(
            schema_version=data["schema_version"],
            action_id=data["action_id"],
            title=data["title"],
            category=ActionCategory(data["category"]),
            preconditions=Preconditions.from_dict(data["preconditions"]),
            authorization=Authorization.from_dict(data["authorization"]),
            inputs=Inputs.from_dict(data["inputs"]),
            expected_effect=data["expected_effect"],
            scope=Scope.from_dict(data["scope"]),
            audit_trail=AuditTrail.from_dict(data["audit_trail"]),
            idempotence_rule=IdempotenceRule.from_dict(data["idempotence_rule"]),
            rollback_strategy=RollbackStrategy.from_dict(data["rollback_strategy"]),
            stop_reasons=[StopReason.from_dict(sr) for sr in data.get("stop_reasons", [])],
        )


# Closed registry of all authorized actions - no additions without formal change.
_CLOSED_ACTION_DEFINITIONS = [
    ProductAction(
        schema_version="1.0.0",
        action_id="WAIT_PROVIDER_RESET",
        title="Wait for provider quota reset",
        category=ActionCategory.WORKFLOW_CONTROL,
        preconditions=Preconditions(
            required_state=[
                "provider_quota_exceeded",
                "retry_budget_exhausted",
            ],
            forbidden_state=["human_intervention_in_progress"],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.NONE,
            default_allowed=True,
        ),
        inputs=Inputs(
            required=[
                InputParameter(
                    name="wait_seconds",
                    type="integer",
                    description="Seconds to wait before retry",
                ),
            ],
            optional=[],
        ),
        expected_effect="Pause workflow and allow provider to reset quota",
        scope=Scope(
            max_entities=1,
            entity_types=["provider_session"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=["wait_duration", "provider_status_checked"],
            decision_recorded=True,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=True,
            rule="Waiting the same duration multiple times has same effect",
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=False,
            strategy="No rollback needed; waiting is side-effect-free",
        ),
        stop_reasons=[],
    ),
    ProductAction(
        schema_version="1.0.0",
        action_id="RECONCILE_WORKTREE",
        title="Reconcile worktree with origin",
        category=ActionCategory.GIT_RECONCILIATION,
        preconditions=Preconditions(
            required_state=[
                "git_state_diverged",
                "origin_reachable",
            ],
            forbidden_state=["uncommitted_changes", "merge_in_progress"],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.NONE,
            default_allowed=True,
        ),
        inputs=Inputs(
            required=[
                InputParameter(
                    name="worktree_path",
                    type="path",
                    description="Path to worktree to reconcile",
                ),
            ],
            optional=[
                InputParameter(
                    name="strategy",
                    type="string",
                    description="Reconciliation strategy (rebase, merge, reset)",
                    default="rebase",
                ),
            ],
        ),
        expected_effect="Reconcile worktree with upstream without losing local work",
        scope=Scope(
            max_entities=1,
            entity_types=["worktree"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=["reconciliation_method", "commits_replayed", "conflicts_resolved"],
            decision_recorded=True,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=True,
            rule="Reconciling against same state is idempotent",
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=True,
            strategy="Restore from pre-reconciliation reflog",
        ),
        stop_reasons=[
            StopReason(
                reason="Unresolvable merge conflicts detected",
                severity="critical",
            ),
            StopReason(
                reason="Origin branch force-pushed incompatibly",
                severity="high",
            ),
        ],
    ),
    ProductAction(
        schema_version="1.0.0",
        action_id="PRESERVE_PARTIAL_CHANGES",
        title="Preserve partial changes from failed operation",
        category=ActionCategory.DATA_PRESERVATION,
        preconditions=Preconditions(
            required_state=[
                "operation_failed_midway",
                "partial_changes_exist",
                "backup_target_is_new_or_matching_autodev_backup",
            ],
            forbidden_state=["committed_to_baseline"],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.NONE,
            default_allowed=True,
        ),
        inputs=Inputs(
            required=[
                InputParameter(
                    name="source_path",
                    type="path",
                    description="Path containing partial changes",
                ),
                InputParameter(
                    name="backup_path",
                    type="path",
                    description="Path where to save preserved changes",
                ),
            ],
            optional=[],
        ),
        expected_effect=(
            "Create one new controlled backup, or return the existing identical "
            "Autodev backup without changing it; never overwrite a pre-existing target"
        ),
        scope=Scope(
            max_entities=1,
            entity_types=["working_directory"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=[
                "backup_created", "backup_identity", "source_content_hash",
                "backup_content_hash", "file_count", "total_size",
            ],
            decision_recorded=True,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=True,
            rule=(
                "A matching Autodev-owned backup with coherent structured evidence is "
                "returned unchanged; every other pre-existing target is refused and a "
                "new unique backup path is required"
            ),
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=True,
            strategy="Restore from backup if needed",
        ),
        stop_reasons=[
            StopReason(
                reason="Insufficient disk space for backup",
                severity="critical",
            ),
        ],
    ),
    ProductAction(
        schema_version="1.0.0",
        action_id="REGENERATE_TASK_REPORT",
        title="Regenerate task report from logs",
        category=ActionCategory.REPORTING,
        preconditions=Preconditions(
            required_state=[
                "task_execution_logged",
            ],
            forbidden_state=[],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.NONE,
            default_allowed=True,
        ),
        inputs=Inputs(
            required=[
                InputParameter(
                    name="task_id",
                    type="string",
                    description="Task ID to regenerate report for",
                ),
                InputParameter(
                    name="log_path",
                    type="path",
                    description="Path to task execution logs",
                ),
            ],
            optional=[],
        ),
        expected_effect="Produce complete task report from execution logs",
        scope=Scope(
            max_entities=1,
            entity_types=["task_report"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=["report_generated", "log_digest"],
            decision_recorded=False,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=True,
            rule="Regenerating from same logs produces same report",
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=False,
            strategy="Report is read-only artifact",
        ),
        stop_reasons=[],
    ),
    ProductAction(
        schema_version="1.0.0",
        action_id="REQUEST_SCOPE_EXTENSION",
        title="Request human approval for scope extension",
        category=ActionCategory.SCOPE_MANAGEMENT,
        preconditions=Preconditions(
            required_state=[
                "necessary_change_outside_scope",
            ],
            forbidden_state=[],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.NONE,
            default_allowed=True,
        ),
        inputs=Inputs(
            required=[
                InputParameter(
                    name="file_path",
                    type="path",
                    description="Exact file or criterion requiring scope extension",
                ),
                InputParameter(
                    name="justification",
                    type="string",
                    description="Precise reason why the change is necessary",
                ),
                InputParameter(
                    name="baseline_proof",
                    type="object",
                    description="Evidence of issue from baseline or previous state",
                ),
                InputParameter(
                    name="impact_estimate",
                    type="string",
                    description="Estimated impact of the change on other modules",
                ),
                InputParameter(
                    name="alternatives_discarded",
                    type="string",
                    description="Why alternatives were not feasible",
                ),
                InputParameter(
                    name="constraints_to_preserve",
                    type="list",
                    description="Critical constraints that must not be violated",
                ),
            ],
            optional=[],
        ),
        expected_effect="Create structured dossier for human review containing exact need, baseline proof, impact, alternatives, and constraints",
        scope=Scope(
            max_entities=1,
            entity_types=["scope_extension_request"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=[
                "file_path",
                "justification",
                "baseline_proof",
                "impact_analysis",
                "alternatives_analyzed",
                "constraints_documented",
            ],
            decision_recorded=True,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=True,
            rule="Multiple requests for same change produce same dossier",
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=False,
            strategy="Request is idempotent; can be redone if decision pending",
        ),
        stop_reasons=[],
    ),
    ProductAction(
        schema_version="1.0.0",
        action_id="APPLY_SCOPE_EXTENSION",
        title="Apply approved scope extension",
        category=ActionCategory.SCOPE_MANAGEMENT,
        preconditions=Preconditions(
            required_state=[
                "scope_extension_approved_by_policy",
                "approval_recorded",
            ],
            forbidden_state=["ambiguous_functional_impact"],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.EXPLICIT,
            default_allowed=False,
            policy_field="allow_scope_extension",
        ),
        inputs=Inputs(
            required=[
                InputParameter(
                    name="approval_id",
                    type="string",
                    description="ID of approval decision",
                ),
                InputParameter(
                    name="change_definition",
                    type="object",
                    description="Precise definition of the change to apply",
                ),
            ],
            optional=[],
        ),
        expected_effect="Apply single, bounded, audited change to extend scope",
        scope=Scope(
            max_entities=1,
            entity_types=["file", "criterion"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=[
                "approval_id",
                "change_applied",
                "verification_result",
            ],
            decision_recorded=True,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=True,
            rule="Applying same approved change twice is safe",
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=True,
            strategy="Revert change using Git if needed",
        ),
        stop_reasons=[
            StopReason(
                reason="Policy does not authorize scope extension",
                severity="critical",
            ),
            StopReason(
                reason="Change definition is ambiguous or multi-part",
                severity="critical",
            ),
        ],
    ),
    ProductAction(
        schema_version="1.0.0",
        action_id="REQUEST_CRITERION_REALLOCATION",
        title="Request human review for criterion ownership change",
        category=ActionCategory.OWNERSHIP_MANAGEMENT,
        preconditions=Preconditions(
            required_state=[
                "criterion_ownership_mismatch",
            ],
            forbidden_state=[],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.NONE,
            default_allowed=True,
        ),
        inputs=Inputs(
            required=[
                InputParameter(
                    name="criterion",
                    type="string",
                    description="Exact criterion requiring reallocation",
                ),
                InputParameter(
                    name="current_owner",
                    type="string",
                    description="Current owner scope and constraints",
                ),
                InputParameter(
                    name="proposed_owner",
                    type="string",
                    description="Proposed new owner scope and capabilities",
                ),
                InputParameter(
                    name="infeasibility_proof",
                    type="object",
                    description="Evidence that current owner cannot implement this criterion",
                ),
                InputParameter(
                    name="proposed_owner_justification",
                    type="string",
                    description="Why proposed owner is capable of implementing it",
                ),
                InputParameter(
                    name="alternatives_considered",
                    type="string",
                    description="Why other potential owners were not suitable",
                ),
                InputParameter(
                    name="dependency_impact",
                    type="list",
                    description="Affected dependencies and validation state",
                ),
                InputParameter(
                    name="baseline_proof",
                    type="object",
                    description="Proof of baseline state before any attempted implementation",
                ),
                InputParameter(
                    name="impact_expected",
                    type="string",
                    description="Expected impact of the reallocation on other tasks and validations",
                ),
                InputParameter(
                    name="constraints_to_preserve",
                    type="list",
                    description="Critical constraints that must not be violated by reallocation",
                ),
            ],
            optional=[],
        ),
        expected_effect="Create structured dossier for human review of ownership change with feasibility evidence, baseline proof, impact analysis, alternatives, constraints, and dependency impact",
        scope=Scope(
            max_entities=2,
            entity_types=["criterion_reallocation_request", "plan"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=[
                "criterion",
                "current_owner",
                "proposed_owner",
                "infeasibility_proof",
                "alternatives_analyzed",
                "dependency_impact_assessed",
                "baseline_proof",
                "impact_expected",
                "constraints_to_preserve",
            ],
            decision_recorded=True,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=True,
            rule="Multiple requests for same reallocation produce same dossier",
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=False,
            strategy="Request is idempotent",
        ),
        stop_reasons=[],
    ),
    ProductAction(
        schema_version="1.0.0",
        action_id="APPLY_CRITERION_REALLOCATION",
        title="Apply approved criterion ownership change",
        category=ActionCategory.OWNERSHIP_MANAGEMENT,
        preconditions=Preconditions(
            required_state=[
                "criterion_reallocation_approved_by_policy",
                "approval_recorded",
            ],
            forbidden_state=["ambiguous_functional_impact"],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.EXPLICIT,
            default_allowed=False,
            policy_field="allow_criterion_reallocation",
        ),
        inputs=Inputs(
            required=[
                InputParameter(
                    name="approval_id",
                    type="string",
                    description="ID of approval decision",
                ),
                InputParameter(
                    name="criterion",
                    type="string",
                    description="Criterion to reallocate",
                ),
                InputParameter(
                    name="new_owner",
                    type="string",
                    description="New owner for criterion",
                ),
            ],
            optional=[],
        ),
        expected_effect="Change criterion ownership in plan and validation state",
        scope=Scope(
            max_entities=2,
            entity_types=["criterion", "plan"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=[
                "approval_id",
                "criterion",
                "old_owner",
                "new_owner",
                "reallocation_recorded",
            ],
            decision_recorded=True,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=True,
            rule="Applying same approved reallocation twice is safe",
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=True,
            strategy="Restore previous ownership from decision history",
        ),
        stop_reasons=[
            StopReason(
                reason="Policy does not authorize criterion reallocation",
                severity="critical",
            ),
            StopReason(
                reason="Reallocation would have ambiguous functional impact or affect multiple entities",
                severity="critical",
            ),
            StopReason(
                reason="Multiple reasonable owners could implement this criterion",
                severity="critical",
            ),
        ],
    ),
    ProductAction(
        schema_version="1.0.0",
        action_id="RECOVER_AGENT_GIT_HISTORY",
        title="Recover agent Git history from backup",
        category=ActionCategory.AGENT_RECOVERY,
        preconditions=Preconditions(
            required_state=[
                "agent_worktree_corrupted",
                "backup_available",
            ],
            forbidden_state=["manual_recovery_in_progress"],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.NONE,
            default_allowed=True,
        ),
        inputs=Inputs(
            required=[
                InputParameter(
                    name="backup_path",
                    type="path",
                    description="Path to Git history backup",
                ),
                InputParameter(
                    name="restore_path",
                    type="path",
                    description="Where to restore history",
                ),
            ],
            optional=[],
        ),
        expected_effect="Restore agent's Git history to working state",
        scope=Scope(
            max_entities=1,
            entity_types=["git_repository"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=["backup_verified", "restore_successful", "consistency_check"],
            decision_recorded=True,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=True,
            rule="Restoring from same backup is idempotent",
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=True,
            strategy="Keep pre-restore state for manual intervention if needed",
        ),
        stop_reasons=[
            StopReason(
                reason="Backup integrity check failed",
                severity="critical",
            ),
        ],
    ),
    ProductAction(
        schema_version="1.0.0",
        action_id="RUN_BASELINE_VALIDATION",
        title="Run baseline validation suite",
        category=ActionCategory.VALIDATION,
        preconditions=Preconditions(
            required_state=[
                "baseline_established",
            ],
            forbidden_state=[],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.NONE,
            default_allowed=True,
        ),
        inputs=Inputs(
            required=[],
            optional=[
                InputParameter(
                    name="validation_commands",
                    type="list",
                    description="Specific commands to run",
                ),
            ],
        ),
        expected_effect="Validate baseline state against all requirements",
        scope=Scope(
            max_entities=1,
            entity_types=["baseline"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=["validation_results", "duration", "exit_code"],
            decision_recorded=False,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=True,
            rule="Validating same baseline produces same results",
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=False,
            strategy="Validation is read-only",
        ),
        stop_reasons=[],
    ),
    ProductAction(
        schema_version="1.0.0",
        action_id="REVALIDATE_TASK",
        title="Revalidate completed task",
        category=ActionCategory.VALIDATION,
        preconditions=Preconditions(
            required_state=[
                "task_completed",
                "validation_available",
            ],
            forbidden_state=[],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.NONE,
            default_allowed=True,
        ),
        inputs=Inputs(
            required=[
                InputParameter(
                    name="task_id",
                    type="string",
                    description="Task to revalidate",
                ),
            ],
            optional=[],
        ),
        expected_effect="Run validation suite for completed task to confirm it still passes",
        scope=Scope(
            max_entities=1,
            entity_types=["task"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=["task_id", "validation_results", "pass_fail"],
            decision_recorded=False,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=True,
            rule="Validating same task produces consistent results",
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=False,
            strategy="Validation is read-only",
        ),
        stop_reasons=[],
    ),
    ProductAction(
        schema_version="1.0.0",
        action_id="RESUME_FEATURE",
        title="Resume feature execution from checkpoint",
        category=ActionCategory.RESUMPTION,
        preconditions=Preconditions(
            required_state=[
                "feature_paused",
                "checkpoint_exists",
            ],
            forbidden_state=["feature_already_running"],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.NONE,
            default_allowed=True,
        ),
        inputs=Inputs(
            required=[
                InputParameter(
                    name="feature_id",
                    type="string",
                    description="Feature to resume",
                ),
                InputParameter(
                    name="checkpoint_id",
                    type="string",
                    description="Checkpoint to resume from",
                ),
            ],
            optional=[],
        ),
        expected_effect="Resume feature execution from saved checkpoint",
        scope=Scope(
            max_entities=1,
            entity_types=["feature"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=["checkpoint_id", "resume_started", "initial_state"],
            decision_recorded=True,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=False,
            rule="Resuming twice may execute same task twice",
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=False,
            strategy="Feature execution cannot be rolled back once started",
        ),
        stop_reasons=[
            StopReason(
                reason="Checkpoint is corrupted or outdated",
                severity="critical",
            ),
        ],
    ),
    ProductAction(
        schema_version="1.0.0",
        action_id="INTEGRATE_FEATURE",
        title="Integrate completed feature to main branch",
        category=ActionCategory.INTEGRATION,
        preconditions=Preconditions(
            required_state=[
                "baseline_established",
                "feature_approved",
                "tests_passed",
                "scope_validated",
            ],
            forbidden_state=["uncommitted_changes", "merge_conflicts"],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.NONE,
            default_allowed=True,
        ),
        inputs=Inputs(
            required=[
                InputParameter(
                    name="feature_id",
                    type="string",
                    description="Feature to integrate",
                ),
                InputParameter(
                    name="commit_message",
                    type="string",
                    description="Commit message for integration",
                ),
            ],
            optional=[],
        ),
        expected_effect="Merge feature branch to integration branch with full audit trail",
        scope=Scope(
            max_entities=1,
            entity_types=["feature", "branch"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=[
                "feature_id",
                "merge_commit",
                "tests_final_run",
                "scope_final_check",
            ],
            decision_recorded=True,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=False,
            rule="Integration creates new commits; not idempotent",
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=True,
            strategy="Revert merge commit if critical issues found post-integration",
        ),
        stop_reasons=[
            StopReason(
                reason="Baseline validation fails",
                severity="critical",
            ),
            StopReason(
                reason="Feature tests do not pass",
                severity="critical",
            ),
            StopReason(
                reason="Scope validation detects unauthorized changes",
                severity="critical",
            ),
        ],
    ),
    ProductAction(
        schema_version="1.0.0",
        action_id="REQUEST_HUMAN",
        title="Escalate to human for decision",
        category=ActionCategory.HUMAN_ESCALATION,
        preconditions=Preconditions(
            required_state=[],
            forbidden_state=[],
        ),
        authorization=Authorization(
            policy_requirement=AuthorizationRequirement.NONE,
            default_allowed=True,
        ),
        inputs=Inputs(
            required=[
                InputParameter(
                    name="reason",
                    type="string",
                    description="Specific reason forcing human escalation",
                ),
                InputParameter(
                    name="facts",
                    type="object",
                    description="Current system state facts that triggered escalation",
                ),
                InputParameter(
                    name="evidence",
                    type="list",
                    description="Audit trail and proof supporting the facts",
                ),
                InputParameter(
                    name="decisions_to_preserve",
                    type="list",
                    description="Prior decisions that must not be violated",
                ),
                InputParameter(
                    name="attempted_solutions",
                    type="list",
                    description="Automated solutions already tried and why they failed",
                ),
                InputParameter(
                    name="possible_choices",
                    type="list",
                    description="Valid options available for human decision",
                ),
            ],
            optional=[
                InputParameter(
                    name="severity",
                    type="string",
                    description="Escalation severity level",
                ),
            ],
        ),
        expected_effect="Suspend automation and present structured dossier containing facts, evidence, preserved decisions, attempted solutions, and possible choices",
        scope=Scope(
            max_entities=1,
            entity_types=["escalation_request"],
            modifications_bounded=True,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=["reason", "facts", "evidence", "decisions_to_preserve", "attempted_solutions", "possible_choices", "timestamp"],
            decision_recorded=True,
        ),
        idempotence_rule=IdempotenceRule(
            is_idempotent=True,
            rule="Requesting human decision multiple times is equivalent",
        ),
        rollback_strategy=RollbackStrategy(
            can_rollback=False,
            strategy="Human decision is the final word",
        ),
        stop_reasons=[],
    ),
]


def _freeze_action(action: ProductAction) -> ProductAction:
    """Return a canonical action with no mutable collection reachable from it."""
    return ProductAction(
        schema_version=action.schema_version,
        action_id=action.action_id,
        title=action.title,
        category=action.category,
        preconditions=Preconditions(
            required_state=tuple(action.preconditions.required_state),
            forbidden_state=tuple(action.preconditions.forbidden_state),
        ),
        authorization=action.authorization,
        inputs=Inputs(
            required=tuple(action.inputs.required),
            optional=tuple(action.inputs.optional),
        ),
        expected_effect=action.expected_effect,
        scope=Scope(
            max_entities=action.scope.max_entities,
            entity_types=tuple(action.scope.entity_types),
            modifications_bounded=action.scope.modifications_bounded,
        ),
        audit_trail=AuditTrail(
            mandatory_evidence=tuple(action.audit_trail.mandatory_evidence),
            decision_recorded=action.audit_trail.decision_recorded,
        ),
        idempotence_rule=action.idempotence_rule,
        rollback_strategy=action.rollback_strategy,
        stop_reasons=tuple(action.stop_reasons),
    )


# This tuple is the sole canonical representation.  No mutable source list is
# retained after import, and ProductActionRegistry never accepts substitutions.
CLOSED_ACTION_REGISTRY = tuple(_freeze_action(action) for action in _CLOSED_ACTION_DEFINITIONS)
del _CLOSED_ACTION_DEFINITIONS


class ProductActionRegistry:
    """Closed, immutable registry of all authorized actions."""

    def __init__(self, actions: Iterable[ProductAction] | None = None):
        if actions is not None:
            provided_actions = tuple(actions)
            canonical_ids = {a.action_id for a in CLOSED_ACTION_REGISTRY}
            provided_ids = {a.action_id for a in provided_actions}
            extra_ids = provided_ids - canonical_ids
            if extra_ids:
                raise ProductActionError(
                    f"Custom registry contains unknown actions not in closed registry: {extra_ids}"
                )
            duplicates = [aid for aid in provided_ids if sum(a.action_id == aid for a in provided_actions) > 1]
            if duplicates:
                raise ProductActionError(f"Custom registry contains duplicate action IDs: {duplicates}")
            if len(provided_actions) != len(CLOSED_ACTION_REGISTRY) or any(
                provided is not canonical
                for provided, canonical in zip(provided_actions, CLOSED_ACTION_REGISTRY)
            ):
                raise ProductActionError("Registry definitions must be the identical canonical definitions")

        self._actions = CLOSED_ACTION_REGISTRY

        if not self._actions:
            raise ProductActionError("Action registry must contain at least one action")

        self._action_map: Mapping[str, ProductAction] = MappingProxyType(
            {action.action_id: action for action in self._actions}
        )

    @property
    def action_map(self) -> Mapping[str, ProductAction]:
        """Read-only lookup view retained for inspection compatibility."""
        return self._action_map

    @property
    def actions(self) -> tuple[ProductAction, ...]:
        """Immutable actions list (read-only property)."""
        return self._actions

    def get_action(self, action_id: str) -> ProductAction | None:
        """Lookup action by ID."""
        return self._action_map.get(action_id)

    def list_actions(self) -> tuple[ProductAction, ...]:
        """Return the immutable canonical action sequence."""
        return self._actions

    def list_by_category(self, category: ActionCategory) -> tuple[ProductAction, ...]:
        """Return matching canonical actions without exposing a mutable list."""
        return tuple(a for a in self.actions if a.category == category)

    def validate_action_id(self, action_id: str) -> bool:
        """Check if action is in registry."""
        return action_id in self._action_map

    def to_dict(self) -> dict[str, Any]:
        """Convert registry to dictionary."""
        return {
            "schema_version": "1.0.0",
            "actions": [action.to_dict() for action in self.actions],
        }


# Global singleton registry
_GLOBAL_REGISTRY: ProductActionRegistry | None = None


def get_action_registry() -> ProductActionRegistry:
    """Get or create global action registry."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ProductActionRegistry()
    return _GLOBAL_REGISTRY
