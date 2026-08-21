from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autodev.git_tools import GitError, current_head
from autodev.specification_policy import (
    SpecificationValidationError,
    enforce_specification_gate,
    validate_json_schema_for_metadata,
    validate_specification_content,
    validate_specification_for_policy,
)

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
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
COMMIT_HASH_PATTERN = re.compile(r"^[a-f0-9]{7,40}$")


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


def _resolve_specification_path(specification_path: str, plan_path: Path) -> Path:
    raw_path = Path(specification_path)
    if raw_path.is_absolute():
        return raw_path

    plan_relative_path = (plan_path.parent / raw_path).resolve()
    if plan_relative_path.exists():
        return plan_relative_path

    workspace_relative_path = (WORKSPACE_ROOT / raw_path).resolve()
    if workspace_relative_path.exists():
        return workspace_relative_path

    return plan_relative_path


def _is_git_worktree(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _resolve_current_commit(plan_path: Path) -> str:
    git_context = plan_path.parent if _is_git_worktree(plan_path.parent) else WORKSPACE_ROOT

    if not _is_git_worktree(git_context):
        raise ProductPlanError(
            f"Unable to determine a Git repository for plan validation from '{plan_path}'"
        )

    try:
        commit = current_head(git_context)
    except GitError as exc:
        raise ProductPlanError(f"Git rev-parse HEAD failed for plan validation: {exc}") from exc

    if not COMMIT_HASH_PATTERN.fullmatch(commit):
        invalid_value = commit or "<empty>"
        raise ProductPlanError(
            f"Unable to determine a valid Git commit for plan validation: {invalid_value}"
        )

    return commit


def _ensure_valid_current_commit(commit: str) -> str:
    if not COMMIT_HASH_PATTERN.fullmatch(commit):
        raise ProductPlanError(
            f"Unable to determine a valid Git commit for plan validation: {commit or '<empty>'}"
        )
    return commit


def _load_specification_metadata(spec_path: Path) -> Any | None:
    from autodev.specification_policy import (
        SpecificationMetadata,
        SpecificationValidationError,
        ValidationStatus,
        validate_json_schema_for_metadata,
    )

    metadata_candidates = [
        spec_path.with_suffix(f"{spec_path.suffix}.validation.json"),
        spec_path.with_suffix(".validation.json"),
    ]
    schema_path = WORKSPACE_ROOT / "autodev" / "schemas" / "specification-validation.schema.json"

    for metadata_path in metadata_candidates:
        if not metadata_path.exists():
            continue
        try:
            with open(metadata_path, encoding="utf-8") as f:
                metadata_dict = json.load(f)
            validate_json_schema_for_metadata(metadata_dict, schema_path)
            return SpecificationMetadata(
                source=metadata_dict["source"],
                prompt=metadata_dict.get("prompt"),
                commit=metadata_dict["commit"],
                validation_status=ValidationStatus(metadata_dict["validation_status"]),
                validated_at=metadata_dict.get("validated_at"),
                validated_by=metadata_dict.get("validated_by"),
                ambiguities=metadata_dict.get("ambiguities", []),
            )
        except (KeyError, ValueError, TypeError, json.JSONDecodeError, SpecificationValidationError) as exc:
            raise ProductPlanError(
                f"Invalid specification metadata for '{spec_path}': {exc}"
            ) from exc

    return None


def _metadata_path_for_specification(spec_path: Path) -> Path:
    return spec_path.with_suffix(f"{spec_path.suffix}.validation.json")


def _persist_specification_metadata(
    spec_path: Path,
    validation_result: Any,
) -> None:
    metadata_path = _metadata_path_for_specification(spec_path)
    metadata_dict = validation_result.metadata.to_dict()
    schema_path = WORKSPACE_ROOT / "autodev" / "schemas" / "specification-validation.schema.json"
    validate_json_schema_for_metadata(metadata_dict, schema_path)
    metadata_path.write_text(
        json.dumps(metadata_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    reloaded_metadata = _load_specification_metadata(spec_path)
    if reloaded_metadata is None:
        raise ProductPlanError(
            f"Generated metadata could not be reloaded for '{validation_result.feature_id}'"
        )
    if reloaded_metadata.immutable_hash() != validation_result.metadata.immutable_hash():
        raise ProductPlanError(
            f"Generated metadata is not stable for '{validation_result.feature_id}'"
        )


def _persist_generated_specification(
    spec_path: Path,
    validation_result: Any,
) -> None:
    if validation_result.specification_content is None:
        raise ProductPlanError(
            f"Specification generation failed for '{validation_result.feature_id}': no content produced"
        )

    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(validation_result.specification_content, encoding="utf-8")

    is_valid, issues = validate_specification_content(spec_path)
    if validation_result.is_valid and not is_valid:
        raise ProductPlanError(
            f"Generated specification validation mismatch for "
            f"'{validation_result.feature_id}': expected structurally valid content, "
            f"got issues: {'; '.join(issues)}"
        )
    missing_issues = [issue for issue in issues if issue not in validation_result.metadata.ambiguities]
    if missing_issues:
        raise ProductPlanError(
            f"Generated specification metadata is missing structural issues for "
            f"'{validation_result.feature_id}': {'; '.join(missing_issues)}"
        )

    _persist_specification_metadata(spec_path, validation_result)


def _persist_generated_draft_specification(
    spec_path: Path,
    validation_result: Any,
) -> None:
    _persist_generated_specification(spec_path, validation_result)


def _is_autonomous_generation_authorized(plan: ProductPlan, feature: Feature) -> bool:
    return plan.specification_policy == "autonomous"


def _build_autonomous_generation_prompt(feature: Feature, resolved_spec_path: Path) -> str:
    return (
        f"Generate a complete autonomous specification for feature {feature.feature_id} "
        f"titled '{feature.title}' at {feature.specification_path} "
        f"(resolved path: {resolved_spec_path}). "
        "Describe concrete business rules, deterministic requirements, explicit data impacts, "
        "and verifiable acceptance criteria without ambiguity."
    )


def _build_missing_autonomous_specification_content(
    *,
    feature: Feature,
    generation_prompt: str,
) -> str:
    cleaned_prompt = " ".join(generation_prompt.split())
    return (
        "## Objectif\n"
        f"Formaliser une spécification autonome exploitable pour {feature.feature_id} "
        f"({feature.title}) à partir de la demande suivante: {cleaned_prompt}\n\n"
        "## Exigences\n"
        f"- R1: Décrire précisément le comportement attendu pour {feature.feature_id} en couvrant "
        f"les règles métier associées à {feature.title}.\n"
        f"- R2: Détailler les données, contrôles et contraintes nécessaires à la réalisation de "
        f"{feature.feature_id} sans laisser d'ambiguïté opérationnelle.\n"
        f"- R3: Rendre vérifiable chaque décision fonctionnelle documentée dans "
        f"`{feature.specification_path}` afin de permettre une planification automatique sûre.\n\n"
        "## Critères d'acceptation\n"
        f"- AC1: La spécification définit un objectif concret et des exigences traçables pour "
        f"{feature.feature_id}.\n"
        "- AC2: Chaque exigence métier possède un critère d'acceptation vérifiable sans revue "
        "interprétative supplémentaire.\n"
        "- AC3: La planification automatique est refusée dès qu'une ambiguïté, une contradiction "
        "ou une validation structurelle échouée est détectée.\n"
    )


def _generate_missing_autonomous_specification(
    *,
    plan: ProductPlan,
    feature: Feature,
    spec_path: Path,
    current_commit: str,
) -> Any:
    if not _is_autonomous_generation_authorized(plan, feature):
        raise ProductPlanError(
            f"Specification validation failed for feature '{feature.feature_id}': "
            "autonomous specification generation is not explicitly authorized — "
            "REQUEST_HUMAN intervention required"
        )

    generation_prompt = _build_autonomous_generation_prompt(feature, spec_path)
    generated_content = _build_missing_autonomous_specification_content(
        feature=feature,
        generation_prompt=generation_prompt,
    )
    result = validate_specification_for_policy(
        feature_id=feature.feature_id,
        specification_path=feature.specification_path,
        policy=plan.specification_policy,
        prompt=generation_prompt,
        current_commit=current_commit,
        spec_content=generated_content,
    )
    _persist_generated_specification(spec_path, result)
    return result


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

    enforce_specifications_for_plan(plan, plan_path)

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


def enforce_specifications_for_plan(plan: ProductPlan, plan_path: Path) -> None:
    """
    Enforce specification policy for all features in a product plan.

    Validates each feature specification against the plan's specification_policy.
    Raises ProductPlanError if any specification is not usable for planning.

    Args:
        plan: Loaded ProductPlan instance
        plan_path: Path to the plan file (used to resolve relative spec paths)

    Raises:
        ProductPlanError: If any specification fails validation gate
    """
    policy = plan.specification_policy
    current_commit = _ensure_valid_current_commit(_resolve_current_commit(plan_path))

    for feature in plan.features:
        spec_path = _resolve_specification_path(feature.specification_path, plan_path)
        spec_exists = spec_path.exists()
        existing_metadata = None
        metadata_error: ProductPlanError | None = None
        if spec_exists:
            try:
                existing_metadata = _load_specification_metadata(spec_path)
            except ProductPlanError as exc:
                metadata_error = exc

        try:
            if policy == "autonomous" and not spec_exists:
                result = _generate_missing_autonomous_specification(
                    plan=plan,
                    feature=feature,
                    spec_path=spec_path,
                    current_commit=current_commit,
                )
            else:
                result = validate_specification_for_policy(
                    feature_id=feature.feature_id,
                    specification_path=feature.specification_path,
                    policy=policy,
                    spec_file=spec_path if spec_exists else None,
                    existing_metadata=existing_metadata,
                    current_commit=current_commit,
                )
            if metadata_error is not None and policy == "approved-only":
                raise metadata_error
            if policy == "draft" and not spec_exists:
                _persist_generated_draft_specification(spec_path, result)
            elif policy in {"draft", "autonomous"} and spec_exists:
                _persist_specification_metadata(spec_path, result)
            enforce_specification_gate(result)
        except SpecificationValidationError as e:
            raise ProductPlanError(
                f"Specification validation failed for feature '{feature.feature_id}': {str(e)}"
            ) from e
