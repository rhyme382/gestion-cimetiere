from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore


class ProductPlanError(RuntimeError):
    """Error loading or validating a product plan."""


@dataclass(frozen=True)
class Feature:
    feature_id: str
    title: str
    specification_path: str
    required: bool
    priority: int
    depends_on: list[str]
    validations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProductPlan:
    schema_version: str
    plan_id: str
    generated_at: str
    integration_branch: str
    specification_policy: str
    features: list[Feature]
    global_validations: list[str]
    plan_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "generated_at": self.generated_at,
            "integration_branch": self.integration_branch,
            "specification_policy": self.specification_policy,
            "global_validations": self.global_validations,
            "features": [f.to_dict() for f in self.features],
            "plan_hash": self.plan_hash,
        }

    def immutable_hash(self) -> str:
        feature_str = json.dumps(
            [f.to_dict() for f in self.features],
            sort_keys=True,
            separators=(",", ":"),
        )
        global_validations_str = json.dumps(
            self.global_validations,
            sort_keys=True,
            separators=(",", ":"),
        )
        content = (
            f"{self.schema_version}|{self.plan_id}|{self.generated_at}|"
            f"{self.integration_branch}|{self.specification_policy}|"
            f"{global_validations_str}|{feature_str}"
        )
        return hashlib.sha256(content.encode()).hexdigest()


SUPPORTED_SCHEMA_VERSIONS = {"1.0", "1.1", "1.2"}


def validate_schema_version(version: str) -> None:
    parts = version.split(".")
    if len(parts) < 3:
        raise ProductPlanError(
            f"Invalid schema_version '{version}': must be semantic versioning (X.Y.Z)"
        )
    try:
        major = int(parts[0])
        minor = int(parts[1])
        int(parts[2])
    except ValueError:
        raise ProductPlanError(
            f"Invalid schema_version '{version}': major, minor, and patch must be integers"
        )

    version_key = f"{major}.{minor}"
    if version_key not in SUPPORTED_SCHEMA_VERSIONS:
        raise ProductPlanError(
            f"Unsupported schema_version '{version}': supported versions are {SUPPORTED_SCHEMA_VERSIONS}"
        )


def validate_duplicate_ids(features: list[dict[str, Any]]) -> None:
    ids = [f["feature_id"] for f in features]
    duplicates = {id for id in ids if ids.count(id) > 1}
    if duplicates:
        raise ProductPlanError(f"Duplicate feature IDs: {duplicates}")


def validate_unknown_dependencies(features: list[dict[str, Any]]) -> None:
    all_ids = {f["feature_id"] for f in features}
    for feature in features:
        depends_on = feature.get("depends_on", [])
        unknown = set(depends_on) - all_ids
        if unknown:
            raise ProductPlanError(
                f"Feature '{feature['feature_id']}' has unknown dependencies: {unknown}"
            )


def find_cycle(
    feature_id: str,
    features_dict: dict[str, dict[str, Any]],
    visited: set[str],
    rec_stack: set[str],
) -> list[str] | None:
    visited.add(feature_id)
    rec_stack.add(feature_id)

    dependencies = features_dict[feature_id].get("depends_on", [])
    for dep in dependencies:
        if dep not in visited:
            cycle = find_cycle(dep, features_dict, visited, rec_stack)
            if cycle is not None:
                return cycle
        elif dep in rec_stack:
            return [feature_id, dep]

    rec_stack.remove(feature_id)
    return None


def validate_no_cycles(features: list[dict[str, Any]]) -> None:
    features_dict = {f["feature_id"]: f for f in features}
    visited: set[str] = set()
    rec_stack: set[str] = set()

    for feature_id in features_dict.keys():
        if feature_id not in visited:
            cycle = find_cycle(feature_id, features_dict, visited, rec_stack)
            if cycle is not None:
                raise ProductPlanError(
                    f"Dependency cycle detected: {' -> '.join(cycle)}"
                )


def validate_specification_policy(policy: str) -> None:
    valid_policies = {"approved-only", "draft", "autonomous"}
    if policy not in valid_policies:
        raise ProductPlanError(
            f"Invalid specification_policy '{policy}': must be one of {valid_policies}"
        )


def validate_json_schema(plan_dict: dict[str, Any], schema_path: Path) -> None:
    if jsonschema is None:
        return

    if not schema_path.exists():
        raise ProductPlanError(f"Schema file not found: {schema_path}")

    with open(schema_path) as f:
        schema = json.load(f)

    try:
        jsonschema.validate(plan_dict, schema)
    except jsonschema.ValidationError as e:
        raise ProductPlanError(f"JSON schema validation failed: {e.message}") from e
    except jsonschema.SchemaError as e:
        raise ProductPlanError(f"Invalid JSON schema: {e.message}") from e


def validate_required_fields(plan_dict: dict[str, Any]) -> None:
    required_top_level = {
        "schema_version",
        "plan_id",
        "generated_at",
        "integration_branch",
        "specification_policy",
        "features",
        "global_validations",
    }
    missing = required_top_level - set(plan_dict.keys())
    if missing:
        raise ProductPlanError(f"Plan missing required fields: {missing}")

    required_feature_fields = {
        "feature_id",
        "title",
        "specification_path",
        "required",
        "priority",
        "depends_on",
        "validations",
    }
    for feature in plan_dict.get("features", []):
        missing_feature = required_feature_fields - set(feature.keys())
        if missing_feature:
            feature_id = feature.get("feature_id", "?")
            raise ProductPlanError(
                f"Feature '{feature_id}' missing required fields: {missing_feature}"
            )


def load_product_plan(plan_path: Path) -> ProductPlan:
    if not plan_path.exists():
        raise ProductPlanError(f"Plan file not found: {plan_path}")

    with open(plan_path) as f:
        try:
            plan_dict = json.load(f)
        except json.JSONDecodeError as e:
            raise ProductPlanError(f"Invalid JSON in plan file: {e}") from e

    schema_path = plan_path.parent / "product-plan.schema.json"
    if not schema_path.exists():
        schema_path = Path(__file__).parent.parent.parent / "schemas" / "product-plan.schema.json"

    validate_required_fields(plan_dict)
    validate_json_schema(plan_dict, schema_path)

    validate_schema_version(plan_dict["schema_version"])
    validate_specification_policy(plan_dict.get("specification_policy", "approved-only"))
    validate_mutable_statuses(plan_dict)
    validate_duplicate_ids(plan_dict["features"])
    validate_unknown_dependencies(plan_dict["features"])
    validate_no_cycles(plan_dict["features"])

    features = [
        Feature(
            feature_id=f["feature_id"],
            title=f["title"],
            specification_path=f["specification_path"],
            required=f.get("required", True),
            priority=f.get("priority", 0),
            depends_on=f.get("depends_on", []),
            validations=f.get("validations", []),
        )
        for f in plan_dict["features"]
    ]

    plan = ProductPlan(
        schema_version=plan_dict["schema_version"],
        plan_id=plan_dict["plan_id"],
        generated_at=plan_dict["generated_at"],
        integration_branch=plan_dict["integration_branch"],
        specification_policy=plan_dict["specification_policy"],
        features=features,
        global_validations=plan_dict.get("global_validations", []),
        plan_hash="",
    )

    plan_hash = plan.immutable_hash()
    plan = ProductPlan(
        schema_version=plan.schema_version,
        plan_id=plan.plan_id,
        generated_at=plan.generated_at,
        integration_branch=plan.integration_branch,
        specification_policy=plan.specification_policy,
        features=plan.features,
        global_validations=plan.global_validations,
        plan_hash=plan_hash,
    )

    return plan


def freeze_plan_revision(plan: ProductPlan, run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "plan_id": plan.plan_id,
        "schema_version": plan.schema_version,
        "plan_hash": plan.plan_hash,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "integration_branch": plan.integration_branch,
        "feature_count": len(plan.features),
    }


def validate_mutable_statuses(plan_dict: dict[str, Any]) -> None:
    MUTABLE_FIELDS = {"status", "state", "progress", "current_step", "last_run"}
    for feature in plan_dict.get("features", []):
        mutable_in_feature = set(feature.keys()) & MUTABLE_FIELDS
        if mutable_in_feature:
            raise ProductPlanError(
                f"Feature '{feature.get('feature_id', '?')}' contains mutable fields "
                f"({mutable_in_feature}) that should not be in the plan"
            )
