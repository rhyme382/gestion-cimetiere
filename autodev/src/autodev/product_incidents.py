from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore


class ProductIncidentError(RuntimeError):
    """Error loading or validating product incidents."""


class IncidentSeverity(str, Enum):
    """Incident severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentScope(str, Enum):
    """Scope/subsystem affected by the incident."""

    PROVIDER = "provider"
    PERMISSIONS = "permissions"
    GIT_STATE = "git_state"
    INITIALIZATION = "initialization"
    WORKTREE = "worktree"
    VALIDATION = "validation"
    CORRECTION_LIMIT = "correction_limit"
    DEPENDENCY = "dependency"
    GIT_CONFLICT = "git_conflict"
    HUMAN_DECISION = "human_decision"


class IncidentRepeatability(str, Enum):
    """How reliably an incident can be reproduced."""

    ALWAYS = "always"
    SOMETIMES = "sometimes"
    RARELY = "rarely"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProductIncident:
    """Represents a single incident type in the closed taxonomy."""

    code: str
    severity: IncidentSeverity
    scope: IncidentScope
    proofs: list[str]
    repeatability: IncidentRepeatability
    recommended_action: str
    retryable: bool
    deferrable: bool
    correctable_under_supervision: bool
    terminal: bool
    title: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, with enums as their values."""
        data = asdict(self)
        data["severity"] = self.severity.value
        data["scope"] = self.scope.value
        data["repeatability"] = self.repeatability.value
        return data

    def is_recoverable(self) -> bool:
        """Check if incident is recoverable (retryable or deferrable or correctable)."""
        return self.retryable or self.deferrable or self.correctable_under_supervision


@dataclass(frozen=True)
class ProductIncidentTaxonomy:
    """Closed taxonomy of product incidents."""

    schema_version: str
    incidents: list[ProductIncident]
    incident_map: dict[str, ProductIncident]

    def __post_init__(self) -> None:
        """Validate after initialization."""
        if not self.incidents:
            raise ProductIncidentError("Taxonomy must contain at least one incident")

    def get_incident(self, code: str) -> ProductIncident | None:
        """Lookup incident by code."""
        return self.incident_map.get(code)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "schema_version": self.schema_version,
            "incidents": [i.to_dict() for i in self.incidents],
        }


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


# Closed incident registry - all possible incident types.
CLOSED_INCIDENTS = [
    ProductIncident(
        code="PROVIDER_QUOTA_EXCEEDED",
        title="Provider quota exceeded",
        description="The external provider (e.g., LLM API) quota has been exhausted",
        severity=IncidentSeverity.HIGH,
        scope=IncidentScope.PROVIDER,
        proofs=["429 error from provider", "quota limit reached message"],
        repeatability=IncidentRepeatability.ALWAYS,
        recommended_action="Wait for quota reset or upgrade plan",
        retryable=True,
        deferrable=True,
        correctable_under_supervision=False,
        terminal=False,
    ),
    ProductIncident(
        code="PROVIDER_RATE_LIMITED",
        title="Provider rate limit hit",
        description="The provider is rate limiting requests",
        severity=IncidentSeverity.MEDIUM,
        scope=IncidentScope.PROVIDER,
        proofs=["rate limit error from provider", "retry-after header"],
        repeatability=IncidentRepeatability.SOMETIMES,
        recommended_action="Implement exponential backoff or increase wait time",
        retryable=True,
        deferrable=True,
        correctable_under_supervision=False,
        terminal=False,
    ),
    ProductIncident(
        code="PROVIDER_UNAVAILABLE",
        title="Provider service unavailable",
        description="The external provider service is temporarily unavailable",
        severity=IncidentSeverity.HIGH,
        scope=IncidentScope.PROVIDER,
        proofs=["503 error", "connection timeout", "service down"],
        repeatability=IncidentRepeatability.SOMETIMES,
        recommended_action="Retry with backoff until service recovers",
        retryable=True,
        deferrable=True,
        correctable_under_supervision=False,
        terminal=False,
    ),
    ProductIncident(
        code="PERMISSION_DENIED",
        title="Permission denied",
        description="User lacks required permissions to perform operation",
        severity=IncidentSeverity.HIGH,
        scope=IncidentScope.PERMISSIONS,
        proofs=["403 error", "access denied message", "insufficient permissions"],
        repeatability=IncidentRepeatability.ALWAYS,
        recommended_action="Grant necessary permissions or escalate to administrator",
        retryable=False,
        deferrable=False,
        correctable_under_supervision=True,
        terminal=True,
    ),
    ProductIncident(
        code="GIT_DIVERGENT_STATE",
        title="Git repository in divergent state",
        description="Local and remote branches have diverged in an unexpected way",
        severity=IncidentSeverity.HIGH,
        scope=IncidentScope.GIT_STATE,
        proofs=["branch divergence detected", "rebase/merge required"],
        repeatability=IncidentRepeatability.ALWAYS,
        recommended_action="Reconcile branches using supervised merge or rebase",
        retryable=False,
        deferrable=False,
        correctable_under_supervision=True,
        terminal=False,
    ),
    ProductIncident(
        code="GIT_CONFLICT_DETECTED",
        title="Git merge conflict",
        description="Unresolved merge conflicts in Git repository",
        severity=IncidentSeverity.CRITICAL,
        scope=IncidentScope.GIT_CONFLICT,
        proofs=["conflict markers in files", "git status shows conflicts"],
        repeatability=IncidentRepeatability.ALWAYS,
        recommended_action="Resolve conflicts manually under supervision",
        retryable=False,
        deferrable=False,
        correctable_under_supervision=True,
        terminal=True,
    ),
    ProductIncident(
        code="INITIALIZATION_MUTATION_FAILED",
        title="Initialization mutation failed",
        description="Product initialization mutation did not complete successfully",
        severity=IncidentSeverity.CRITICAL,
        scope=IncidentScope.INITIALIZATION,
        proofs=["mutation incomplete", "initialization rollback occurred"],
        repeatability=IncidentRepeatability.ALWAYS,
        recommended_action="Review mutation logs and retry or recover from backup",
        retryable=True,
        deferrable=False,
        correctable_under_supervision=True,
        terminal=False,
    ),
    ProductIncident(
        code="WORKTREE_DIRTY",
        title="Worktree has uncommitted changes",
        description="Working tree has uncommitted or untracked changes",
        severity=IncidentSeverity.HIGH,
        scope=IncidentScope.WORKTREE,
        proofs=["git status shows modified files", "untracked files detected"],
        repeatability=IncidentRepeatability.ALWAYS,
        recommended_action="Commit, stash, or clean working tree before proceeding",
        retryable=False,
        deferrable=True,
        correctable_under_supervision=True,
        terminal=False,
    ),
    ProductIncident(
        code="WORKTREE_INTERRUPTED",
        title="Worktree operation interrupted",
        description="Previous operation was interrupted, leaving worktree in inconsistent state",
        severity=IncidentSeverity.CRITICAL,
        scope=IncidentScope.WORKTREE,
        proofs=["lock files present", "incomplete state markers", "stale process markers"],
        repeatability=IncidentRepeatability.ALWAYS,
        recommended_action="Clean up lock files and verify worktree consistency",
        retryable=False,
        deferrable=False,
        correctable_under_supervision=True,
        terminal=True,
    ),
    ProductIncident(
        code="VALIDATION_TRANSITIVE_FAILED",
        title="Transitive validation failed",
        description="A dependency validation that should have passed failed unexpectedly",
        severity=IncidentSeverity.MEDIUM,
        scope=IncidentScope.VALIDATION,
        proofs=["test failure in dependency", "unexpected validation result"],
        repeatability=IncidentRepeatability.SOMETIMES,
        recommended_action="Investigate dependency state and retry validation",
        retryable=True,
        deferrable=False,
        correctable_under_supervision=True,
        terminal=False,
    ),
    ProductIncident(
        code="CORRECTION_LIMIT_ORDINARY_EXCEEDED",
        title="Ordinary correction limit exceeded",
        description="Correction attempts for this incident have exceeded ordinary limits",
        severity=IncidentSeverity.CRITICAL,
        scope=IncidentScope.CORRECTION_LIMIT,
        proofs=["correction retry count exceeded", "ordinary limit cap reached"],
        repeatability=IncidentRepeatability.ALWAYS,
        recommended_action="Escalate to supervised correction or abort operation",
        retryable=False,
        deferrable=False,
        correctable_under_supervision=True,
        terminal=True,
    ),
    ProductIncident(
        code="CORRECTION_LIMIT_SUPERVISED_EXCEEDED",
        title="Supervised correction limit exceeded",
        description="Correction attempts under supervision have exceeded limits",
        severity=IncidentSeverity.CRITICAL,
        scope=IncidentScope.CORRECTION_LIMIT,
        proofs=["supervised correction retry count exceeded"],
        repeatability=IncidentRepeatability.ALWAYS,
        recommended_action="Abort operation or request higher-level override",
        retryable=False,
        deferrable=False,
        correctable_under_supervision=False,
        terminal=True,
    ),
    ProductIncident(
        code="DEPENDENCY_MISSING",
        title="Required dependency missing",
        description="A required dependency is not available or cannot be satisfied",
        severity=IncidentSeverity.HIGH,
        scope=IncidentScope.DEPENDENCY,
        proofs=["import error", "package not found", "version mismatch"],
        repeatability=IncidentRepeatability.ALWAYS,
        recommended_action="Install missing dependency or resolve version conflict",
        retryable=False,
        deferrable=False,
        correctable_under_supervision=True,
        terminal=True,
    ),
    ProductIncident(
        code="SPECIFICATION_MISSING",
        title="Required specification missing",
        description="A required specification file or data is missing",
        severity=IncidentSeverity.HIGH,
        scope=IncidentScope.DEPENDENCY,
        proofs=["specification file not found", "required spec data absent"],
        repeatability=IncidentRepeatability.ALWAYS,
        recommended_action="Create missing specification or check file paths",
        retryable=False,
        deferrable=False,
        correctable_under_supervision=True,
        terminal=True,
    ),
    ProductIncident(
        code="HUMAN_DECISION_REQUIRED",
        title="Human decision required",
        description="An automated decision cannot be made; human intervention needed",
        severity=IncidentSeverity.MEDIUM,
        scope=IncidentScope.HUMAN_DECISION,
        proofs=["ambiguous state", "multiple valid options", "policy requires human approval"],
        repeatability=IncidentRepeatability.SOMETIMES,
        recommended_action="Pause and wait for human input or decision",
        retryable=False,
        deferrable=True,
        correctable_under_supervision=True,
        terminal=False,
    ),
]


def validate_schema_version(version: str) -> None:
    """Validate semantic version format (X.Y.Z)."""
    parts = version.split(".")
    if len(parts) != 3:
        raise ProductIncidentError(
            f"Invalid schema_version '{version}': must be semantic versioning (X.Y.Z)"
        )
    try:
        int(parts[0])
        int(parts[1])
        int(parts[2])
    except ValueError:
        raise ProductIncidentError(
            f"Invalid schema_version '{version}': version parts must be integers"
        )


def validate_duplicate_codes(incidents: list[ProductIncident]) -> None:
    """Ensure all incident codes are unique."""
    codes = [i.code for i in incidents]
    if len(codes) != len(set(codes)):
        duplicates = [c for c in codes if codes.count(c) > 1]
        raise ProductIncidentError(f"Duplicate incident codes: {duplicates}")


def validate_json_schema(data: dict[str, Any]) -> None:
    """Validate data against JSON schema."""
    if jsonschema is None:
        return
    schema_path = WORKSPACE_ROOT / "autodev" / "schemas" / "product-incident.schema.json"
    if not schema_path.exists():
        raise ProductIncidentError(f"Schema file not found: {schema_path}")
    with open(schema_path) as f:
        schema = json.load(f)
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        raise ProductIncidentError(f"JSON schema validation failed: {e.message}")


def load_product_incidents(data: dict[str, Any]) -> ProductIncidentTaxonomy:
    """Load and validate product incidents from dictionary."""
    validate_json_schema(data)
    validate_schema_version(data["schema_version"])

    incidents = []
    for incident_data in data["incidents"]:
        try:
            severity = IncidentSeverity(incident_data["severity"])
            scope = IncidentScope(incident_data["scope"])
            repeatability = IncidentRepeatability(incident_data["repeatability"])

            incident = ProductIncident(
                code=incident_data["code"],
                severity=severity,
                scope=scope,
                proofs=incident_data["proofs"],
                repeatability=repeatability,
                recommended_action=incident_data["recommended_action"],
                retryable=incident_data["retryable"],
                deferrable=incident_data["deferrable"],
                correctable_under_supervision=incident_data[
                    "correctable_under_supervision"
                ],
                terminal=incident_data["terminal"],
                title=incident_data.get("title", ""),
                description=incident_data.get("description", ""),
            )
            incidents.append(incident)
        except (KeyError, ValueError) as e:
            raise ProductIncidentError(f"Invalid incident data: {e}")

    validate_duplicate_codes(incidents)

    incident_map = {i.code: i for i in incidents}
    return ProductIncidentTaxonomy(
        schema_version=data["schema_version"],
        incidents=incidents,
        incident_map=incident_map,
    )


def load_product_incidents_from_file(path: Path | str) -> ProductIncidentTaxonomy:
    """Load product incidents from a JSON file."""
    path = Path(path)
    if not path.exists():
        raise ProductIncidentError(f"Incident file not found: {path}")
    with open(path) as f:
        data = json.load(f)
    return load_product_incidents(data)


def build_default_taxonomy() -> ProductIncidentTaxonomy:
    """Build the default closed incident taxonomy."""
    return ProductIncidentTaxonomy(
        schema_version="1.0.0",
        incidents=CLOSED_INCIDENTS,
        incident_map={i.code: i for i in CLOSED_INCIDENTS},
    )
