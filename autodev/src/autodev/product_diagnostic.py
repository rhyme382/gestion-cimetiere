from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from autodev.product_actions import ProductAction, ProductActionRegistry, get_action_registry
from autodev.product_policy import (
    ActionExecutionContext,
    DecisionType,
    ExecutionContext,
    PolicyFacts,
    ProductPolicyEngine,
    RecordedDecision,
)

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore


class ProductDiagnosticError(RuntimeError):
    """A diagnostic cannot be produced from authoritative evidence."""


@dataclass(frozen=True)
class DiagnosticFacts:
    """Fresh, authoritative observations; narrative reports never override them."""

    base_commit: str
    produced_commit: str
    modified_paths: list[str]
    review_verdict: str
    test_status: str
    diff_summary: str
    git_status: dict[str, Any]
    prior_corrections: list[dict[str, Any]]
    prior_incident_codes: list[str]
    acquired_decisions: list[dict[str, Any]]
    policy_context: dict[str, Any]
    scope_violations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DiagnosticInferences:
    scope_compliant: bool
    test_confidence: str
    implementation_completeness: str
    risk_factors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DiagnosticConstraints:
    must_preserve: list[str] = field(default_factory=list)
    must_not_modify: list[str] = field(default_factory=list)
    required_validations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SHELL_METACHARACTERS = ("|", "&", ";", ">", "<", "`", "$()")


@dataclass(frozen=True)
class ProposedAction:
    """A non-executed proposal naming exactly one canonical T07 action."""

    action_id: str
    rationale: str
    next_steps: list[str]
    action_inputs: dict[str, Any] = field(default_factory=dict)
    blocking_issue: str = ""

    def __post_init__(self) -> None:
        if not self.action_id or not self.rationale:
            raise ProductDiagnosticError("A canonical action_id and rationale are required")
        if not isinstance(self.action_inputs, dict):
            raise ProductDiagnosticError("Action inputs must be a structured object")
        if any(any(token in step for token in _SHELL_METACHARACTERS) for step in self.next_steps):
            raise ProductDiagnosticError("Diagnostic next_steps must not contain shell commands")

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "rationale": self.rationale,
            "next_steps": self.next_steps,
            "action_inputs": self.action_inputs,
            "blocking_issue": self.blocking_issue,
        }


@dataclass(frozen=True)
class ProductDiagnostic:
    schema_version: str
    task_id: str
    timestamp: str
    facts: DiagnosticFacts
    inferences: DiagnosticInferences
    constraints: DiagnosticConstraints
    proposed_action: ProposedAction
    confidence_level: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version, "task_id": self.task_id,
            "timestamp": self.timestamp, "facts": self.facts.to_dict(),
            "inferences": self.inferences.to_dict(), "constraints": self.constraints.to_dict(),
            "proposed_action": self.proposed_action.to_dict(), "confidence_level": self.confidence_level,
        }


class EvidenceCollector:
    """Production collector: every observation is supplied by a typed reader."""

    _REQUIRED_READERS = (
        "base_commit", "produced_commit", "modified_paths", "review_verdict", "test_status",
        "diff", "git_status", "corrections", "incidents", "decisions", "policy_context",
    )

    def __init__(self, task_id: str):
        if not task_id:
            raise ProductDiagnosticError("task_id is required")
        self.task_id = task_id
        self._readers: dict[str, Callable[[], Any]] = {}
        self._authorized_paths_reader: Callable[[], list[str]] | None = None

    def _reader(self, name: str, reader: Callable[[], Any]) -> EvidenceCollector:
        if not callable(reader):
            raise ProductDiagnosticError(f"Authoritative reader for {name} must be callable")
        self._readers[name] = reader
        return self

    def with_base_commit_reader(self, reader: Callable[[], str]) -> EvidenceCollector: return self._reader("base_commit", reader)
    def with_produced_commit_reader(self, reader: Callable[[], str]) -> EvidenceCollector: return self._reader("produced_commit", reader)
    def with_modified_paths_reader(self, reader: Callable[[], list[str]]) -> EvidenceCollector: return self._reader("modified_paths", reader)
    def with_review_verdict_reader(self, reader: Callable[[], str]) -> EvidenceCollector: return self._reader("review_verdict", reader)
    def with_test_status_reader(self, reader: Callable[[], str]) -> EvidenceCollector: return self._reader("test_status", reader)
    def with_diff_reader(self, reader: Callable[[], str]) -> EvidenceCollector: return self._reader("diff", reader)
    def with_git_status_reader(self, reader: Callable[[], dict[str, Any]]) -> EvidenceCollector: return self._reader("git_status", reader)
    def with_corrections_reader(self, reader: Callable[[], list[dict[str, Any]]]) -> EvidenceCollector: return self._reader("corrections", reader)
    def with_prior_incident_codes_reader(self, reader: Callable[[], list[str]]) -> EvidenceCollector: return self._reader("incidents", reader)
    def with_decisions_reader(self, reader: Callable[[], list[dict[str, Any]]]) -> EvidenceCollector: return self._reader("decisions", reader)
    def with_policy_context_reader(self, reader: Callable[[], dict[str, Any]]) -> EvidenceCollector: return self._reader("policy_context", reader)

    def with_authorized_paths_reader(self, reader: Callable[[], list[str]]) -> EvidenceCollector:
        if not callable(reader):
            raise ProductDiagnosticError("Authoritative reader for authorized paths must be callable")
        self._authorized_paths_reader = reader
        return self

    def collect(self) -> DiagnosticFacts:
        """Read every source afresh. No constructor values or cached facts exist."""
        missing = [name for name in self._REQUIRED_READERS if name not in self._readers]
        if missing:
            raise ProductDiagnosticError("missing authoritative readers: " + ", ".join(missing))
        try:
            values = {name: self._readers[name]() for name in self._REQUIRED_READERS}
            authorized = self._authorized_paths_reader() if self._authorized_paths_reader else None
        except Exception as exc:
            raise ProductDiagnosticError(f"authoritative evidence source failed: {exc}") from exc
        self._validate(values)
        scope_violations = [] if authorized is None else [p for p in values["modified_paths"] if p not in authorized]
        return DiagnosticFacts(
            base_commit=values["base_commit"], produced_commit=values["produced_commit"],
            modified_paths=list(values["modified_paths"]), review_verdict=values["review_verdict"],
            test_status=values["test_status"], diff_summary=values["diff"], git_status=dict(values["git_status"]),
            prior_corrections=list(values["corrections"]), prior_incident_codes=list(values["incidents"]),
            acquired_decisions=list(values["decisions"]), policy_context=dict(values["policy_context"]),
            scope_violations=scope_violations,
        )

    @staticmethod
    def _validate(values: Mapping[str, Any]) -> None:
        if not all(isinstance(values[key], str) and values[key] for key in ("base_commit", "produced_commit", "diff")):
            raise ProductDiagnosticError("commits and diff must be fresh non-empty technical evidence")
        if not isinstance(values["modified_paths"], list) or not all(isinstance(p, str) for p in values["modified_paths"]):
            raise ProductDiagnosticError("modified paths source is invalid")
        if values["review_verdict"] not in {"APPROVED", "CORRECTION_REQUIRED", "HUMAN_REVIEW_REQUIRED"}:
            raise ProductDiagnosticError("review source is invalid")
        if values["test_status"] not in {"PASS", "FAIL", "SKIPPED"}:
            raise ProductDiagnosticError("validation source is invalid")
        for name in ("git_status", "policy_context"):
            if not isinstance(values[name], dict): raise ProductDiagnosticError(f"{name} source is invalid")
        for name in ("corrections", "incidents", "decisions"):
            if not isinstance(values[name], list): raise ProductDiagnosticError(f"{name} source is invalid")


class DiagnosticBuilder:
    """Production-only builder: collection is intentionally inside build()."""

    def __init__(self, collector: EvidenceCollector, policy_engine: ProductPolicyEngine, task_id: str):
        if not isinstance(collector, EvidenceCollector):
            raise ProductDiagnosticError("DiagnosticBuilder requires an EvidenceCollector")
        if not isinstance(policy_engine, ProductPolicyEngine):
            raise ProductDiagnosticError("DiagnosticBuilder requires the concrete ProductPolicyEngine")
        if collector.task_id != task_id:
            raise ProductDiagnosticError("collector task_id must match diagnostic task_id")
        self._collector, self._policy_engine, self.task_id = collector, policy_engine, task_id
        self._registry: ProductActionRegistry = policy_engine.registry
        self._proposed_action = ProposedAction("REQUEST_HUMAN", "No action has been authorized", [])
        self._constraints = DiagnosticConstraints()

    def with_constraints(self, constraints: DiagnosticConstraints) -> DiagnosticBuilder:
        self._constraints = constraints
        return self

    def with_proposed_action(self, action_id: str, rationale: str, next_steps: list[str], action_inputs: dict[str, Any] | None = None) -> DiagnosticBuilder:
        if not self._registry.validate_action_id(action_id):
            raise ProductDiagnosticError(f"Action '{action_id}' is not in the canonical registry")
        self._proposed_action = ProposedAction(action_id, rationale, next_steps, action_inputs or {})
        return self

    def _policy_context(self, facts: DiagnosticFacts) -> tuple[PolicyFacts, ExecutionContext, list[RecordedDecision]]:
        allowed = set(PolicyFacts.__dataclass_fields__)
        unknown = set(facts.policy_context) - allowed - {"execution"}
        if unknown:
            raise ProductDiagnosticError("policy context contains unknown fields: " + ", ".join(sorted(unknown)))
        policy_facts = PolicyFacts(**{name: value for name, value in facts.policy_context.items() if name in allowed})
        execution_data = facts.policy_context.get("execution", {})
        if not isinstance(execution_data, dict): raise ProductDiagnosticError("execution context is invalid")
        execution = ExecutionContext(**execution_data)
        decisions = []
        for raw in facts.acquired_decisions:
            try: decisions.append(RecordedDecision.from_dict(raw))
            except (KeyError, ValueError) as exc: raise ProductDiagnosticError(f"acquired decision is invalid: {exc}") from exc
        return policy_facts, execution, decisions

    def _resolve_action(self, action_id: str) -> ProductAction:
        action = self._registry.get_action(action_id)
        if action is None:
            raise ProductDiagnosticError(f"Action '{action_id}' is not in the canonical registry")
        return action

    @staticmethod
    def _input_matches(value: Any, expected_type: str) -> bool:
        if expected_type == "string":
            return isinstance(value, str) and not isinstance(value, bool)
        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type == "boolean":
            return isinstance(value, bool)
        if expected_type == "list":
            return isinstance(value, list)
        if expected_type == "object":
            return isinstance(value, dict)
        if expected_type == "path":
            return isinstance(value, (str, Path)) and not isinstance(value, bool)
        return False

    def _validate_inputs(self, action: ProductAction, inputs: Mapping[str, Any]) -> None:
        if not isinstance(inputs, Mapping):
            raise ProductDiagnosticError("Action inputs must be a structured mapping")
        parameters = tuple(action.inputs.required) + tuple(action.inputs.optional)
        required_names = {parameter.name for parameter in action.inputs.required}
        allowed_names = {parameter.name for parameter in parameters}
        missing = required_names - set(inputs)
        extra = set(inputs) - allowed_names
        if missing:
            raise ProductDiagnosticError(f"Missing required inputs for {action.action_id}: {sorted(missing)}")
        if extra:
            raise ProductDiagnosticError(f"Unknown inputs for {action.action_id}: {sorted(extra)}")
        for parameter in parameters:
            if parameter.name in inputs and not self._input_matches(inputs[parameter.name], parameter.type):
                raise ProductDiagnosticError(
                    f"Input {parameter.name} has wrong type for {action.action_id}: expected {parameter.type}"
                )

    def _authorize(self, proposal: ProposedAction, context: ActionExecutionContext) -> tuple[ProposedAction, Any]:
        action = self._resolve_action(proposal.action_id)
        self._validate_inputs(action, proposal.action_inputs)
        try:
            verdict = self._policy_engine.authorize_action(proposal.action_id, context, proposal.action_inputs)
        except Exception as exc:
            raise ProductDiagnosticError(f"T07 policy validation failed: {exc}") from exc
        return proposal, verdict

    def _request_human_proposal(
        self,
        facts: DiagnosticFacts,
        context: ActionExecutionContext,
        rationale: str,
        initial_proposal: ProposedAction | None = None,
        initial_verdict: Any | None = None,
    ) -> ProposedAction:
        evidence = [{
            "base_commit": facts.base_commit,
            "produced_commit": facts.produced_commit,
            "modified_paths": facts.modified_paths,
            "diff_summary": facts.diff_summary,
            "git_status": facts.git_status,
            "review_verdict": facts.review_verdict,
            "test_status": facts.test_status,
            "prior_incident_codes": facts.prior_incident_codes,
        }]
        attempts: list[dict[str, Any]] = []
        if initial_proposal is not None:
            attempts.append({
                "action_id": initial_proposal.action_id,
                "action_inputs": initial_proposal.action_inputs,
                "rationale": initial_proposal.rationale,
                "policy_verdict": initial_verdict.to_dict() if initial_verdict is not None else {},
            })
        else:
            attempts.append({"action_id": "REQUEST_HUMAN", "status": "requested_directly"})
        return ProposedAction(
            "REQUEST_HUMAN",
            rationale,
            [],
            {
                "reason": rationale,
                "facts": {
                    "policy_facts": context.facts.to_dict(),
                    "execution": context.execution.to_dict(),
                    "diagnostic": {
                        "task_id": self.task_id,
                        "scope_violations": facts.scope_violations,
                    },
                },
                "evidence": evidence,
                "decisions_to_preserve": [decision.to_dict() for decision in context.decisions],
                "attempted_solutions": attempts,
                "possible_choices": [
                    {"action_id": "REQUEST_HUMAN", "description": "Review the evidence and choose the next approved action"}
                ],
                "severity": "high",
            },
            blocking_issue=rationale if initial_proposal is not None else "",
        )

    def _authorized_action(self, facts: DiagnosticFacts) -> ProposedAction:
        policy_facts, execution, decisions = self._policy_context(facts)
        context = ActionExecutionContext(policy_facts, execution, tuple(decisions))
        if self._proposed_action.action_id == "REQUEST_HUMAN":
            proposal = self._request_human_proposal(facts, context, self._proposed_action.rationale)
            _, verdict = self._authorize(proposal, context)
            if verdict.authorization_allowed and verdict.selected_action_id == "REQUEST_HUMAN":
                return proposal
            raise ProductDiagnosticError(f"T07 refused REQUEST_HUMAN: {verdict.justification}")

        proposal, verdict = self._authorize(self._proposed_action, context)
        if verdict.authorization_allowed and verdict.selected_action_id == proposal.action_id:
            return proposal

        fallback = self._request_human_proposal(facts, context, verdict.justification, proposal, verdict)
        _, fallback_verdict = self._authorize(fallback, context)
        if fallback_verdict.authorization_allowed and fallback_verdict.selected_action_id == "REQUEST_HUMAN":
            return fallback
        raise ProductDiagnosticError(f"T07 refused REQUEST_HUMAN: {fallback_verdict.justification}")

    def build(self) -> ProductDiagnostic:
        facts = self._collector.collect()  # Mandatory fresh collection for each invocation.
        action = self._authorized_action(facts)
        inferences = DiagnosticInferences(
            scope_compliant=not facts.scope_violations,
            test_confidence="high" if facts.test_status == "PASS" else "low",
            implementation_completeness="complete" if facts.review_verdict == "APPROVED" else "partial",
            risk_factors=list(facts.prior_incident_codes),
        )
        return ProductDiagnostic("2.0.0", self.task_id, datetime.now(timezone.utc).isoformat(), facts, inferences, self._constraints, action)


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


def validate_json_schema(data: dict[str, Any]) -> None:
    if jsonschema is None: return
    schema = json.loads((WORKSPACE_ROOT / "autodev/schemas/product-diagnostic.schema.json").read_text(encoding="utf-8"))
    try: jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc: raise ProductDiagnosticError(f"JSON schema validation failed: {exc.message}") from exc
