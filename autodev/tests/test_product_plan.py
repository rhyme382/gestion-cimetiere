import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from autodev.product_plan import (
    ProductPlan,
    ProductPlanError,
    Feature,
    freeze_plan_revision,
    load_product_plan,
    validate_duplicate_ids,
    validate_json_schema,
    validate_no_cycles,
    validate_schema_version,
    validate_specification_policy,
    validate_unknown_dependencies,
    validate_mutable_statuses,
    validate_required_fields,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def valid_schema(temp_dir):
    schema_src = Path(__file__).parent.parent / "schemas" / "product-plan.schema.json"
    if schema_src.exists():
        with open(schema_src) as f:
            schema = json.load(f)
    else:
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Autodev Product Plan",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "schema_version",
                "plan_id",
                "generated_at",
                "integration_branch",
                "specification_policy",
                "features",
                "global_validations",
            ],
            "properties": {
                "schema_version": {"type": "string"},
                "plan_id": {"type": "string", "minLength": 3},
                "generated_at": {"type": "string"},
                "integration_branch": {"type": "string", "minLength": 1},
                "specification_policy": {
                    "type": "string",
                    "enum": ["approved-only", "draft", "autonomous"],
                },
                "global_validations": {"type": "array", "items": {"type": "string"}},
                "features": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": [
                            "feature_id",
                            "title",
                            "specification_path",
                            "required",
                            "priority",
                            "depends_on",
                            "validations",
                        ],
                        "properties": {
                            "feature_id": {"type": "string"},
                            "title": {"type": "string", "minLength": 3},
                            "specification_path": {"type": "string", "minLength": 1},
                            "required": {"type": "boolean"},
                            "priority": {"type": "integer", "minimum": 0},
                            "depends_on": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "validations": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
        }
    schema_path = temp_dir / "product-plan.schema.json"
    with open(schema_path, "w") as f:
        json.dump(schema, f)
    return schema_path


@pytest.fixture
def valid_plan_dict():
    return {
        "schema_version": "1.0.0",
        "plan_id": "PLAN-TEST-001",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "integration_branch": "main",
        "specification_policy": "approved-only",
        "global_validations": ["npm test", "cargo test"],
        "features": [
            {
                "feature_id": "FEATURE-A",
                "title": "Feature A",
                "specification_path": "spec/feature-a.md",
                "required": True,
                "priority": 1,
                "depends_on": [],
                "validations": ["test feature-a"],
            },
            {
                "feature_id": "FEATURE-B",
                "title": "Feature B",
                "specification_path": "spec/feature-b.md",
                "required": True,
                "priority": 2,
                "depends_on": ["FEATURE-A"],
                "validations": [],
            },
        ],
    }


def _materialize_approved_specifications(temp_dir: Path, plan_dict: dict) -> None:
    for feature in plan_dict["features"]:
        spec_path = temp_dir / feature["specification_path"]
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            f"""## Objectif
Formaliser la feature {feature["feature_id"]}.

## Exigences
- R1: Implémenter {feature["title"]} conformément au plan produit.

## Critères d'acceptation
- AC1: La feature {feature["feature_id"]} dispose d'une spécification approuvée exploitable.
""",
            encoding="utf-8",
        )
        spec_path.with_suffix(f"{spec_path.suffix}.validation.json").write_text(
            json.dumps(
                {
                    "source": f"spec:manual/{feature['specification_path']}",
                    "prompt": None,
                    "commit": "abc123def456",
                    "validation_status": "approved",
                    "validated_at": datetime.now(timezone.utc).isoformat(),
                    "validated_by": "human-supervisor",
                    "ambiguities": [],
                }
            ),
            encoding="utf-8",
        )


class TestSchemaVersion:
    def test_valid_semantic_version(self):
        validate_schema_version("1.0.0")
        validate_schema_version("1.1.5")
        validate_schema_version("1.2.0")

    def test_invalid_version_missing_parts(self):
        with pytest.raises(ProductPlanError):
            validate_schema_version("1.0")

    def test_invalid_version_non_integer(self):
        with pytest.raises(ProductPlanError):
            validate_schema_version("a.b.c")

    def test_unsupported_schema_version_rejected(self):
        with pytest.raises(ProductPlanError, match="Unsupported schema_version"):
            validate_schema_version("2.0.0")

    def test_unsupported_major_version_rejected(self):
        with pytest.raises(ProductPlanError, match="Unsupported schema_version"):
            validate_schema_version("3.5.1")


class TestDuplicateIds:
    def test_no_duplicates(self):
        features = [
            {"feature_id": "FEATURE-A"},
            {"feature_id": "FEATURE-B"},
        ]
        validate_duplicate_ids(features)

    def test_duplicate_ids_rejected(self):
        features = [
            {"feature_id": "FEATURE-A"},
            {"feature_id": "FEATURE-A"},
            {"feature_id": "FEATURE-B"},
        ]
        with pytest.raises(ProductPlanError, match="Duplicate feature IDs"):
            validate_duplicate_ids(features)


class TestUnknownDependencies:
    def test_no_dependencies(self):
        features = [
            {"feature_id": "FEATURE-A"},
            {"feature_id": "FEATURE-B"},
        ]
        validate_unknown_dependencies(features)

    def test_valid_dependencies(self):
        features = [
            {"feature_id": "FEATURE-A", "depends_on": []},
            {"feature_id": "FEATURE-B", "depends_on": ["FEATURE-A"]},
        ]
        validate_unknown_dependencies(features)

    def test_unknown_dependency_rejected(self):
        features = [
            {"feature_id": "FEATURE-A"},
            {"feature_id": "FEATURE-B", "depends_on": ["FEATURE-UNKNOWN"]},
        ]
        with pytest.raises(ProductPlanError, match="unknown dependencies"):
            validate_unknown_dependencies(features)

    def test_multiple_unknown_dependencies(self):
        features = [
            {"feature_id": "FEATURE-A"},
            {
                "feature_id": "FEATURE-B",
                "depends_on": ["FEATURE-UNKNOWN-1", "FEATURE-UNKNOWN-2"],
            },
        ]
        with pytest.raises(ProductPlanError, match="unknown dependencies"):
            validate_unknown_dependencies(features)


class TestCycleDependencies:
    def test_no_cycle(self):
        features = [
            {"feature_id": "FEATURE-A", "depends_on": []},
            {"feature_id": "FEATURE-B", "depends_on": ["FEATURE-A"]},
            {"feature_id": "FEATURE-C", "depends_on": ["FEATURE-B"]},
        ]
        validate_no_cycles(features)

    def test_self_cycle_rejected(self):
        features = [
            {"feature_id": "FEATURE-A", "depends_on": ["FEATURE-A"]},
        ]
        with pytest.raises(ProductPlanError, match="Dependency cycle"):
            validate_no_cycles(features)

    def test_two_feature_cycle_rejected(self):
        features = [
            {"feature_id": "FEATURE-A", "depends_on": ["FEATURE-B"]},
            {"feature_id": "FEATURE-B", "depends_on": ["FEATURE-A"]},
        ]
        with pytest.raises(ProductPlanError, match="Dependency cycle"):
            validate_no_cycles(features)

    def test_three_feature_cycle_rejected(self):
        features = [
            {"feature_id": "FEATURE-A", "depends_on": ["FEATURE-B"]},
            {"feature_id": "FEATURE-B", "depends_on": ["FEATURE-C"]},
            {"feature_id": "FEATURE-C", "depends_on": ["FEATURE-A"]},
        ]
        with pytest.raises(ProductPlanError, match="Dependency cycle"):
            validate_no_cycles(features)


class TestSpecificationPolicy:
    def test_approved_only_valid(self):
        validate_specification_policy("approved-only")

    def test_draft_valid(self):
        validate_specification_policy("draft")

    def test_autonomous_valid(self):
        validate_specification_policy("autonomous")

    def test_invalid_policy_rejected(self):
        with pytest.raises(ProductPlanError, match="Invalid specification_policy"):
            validate_specification_policy("unknown")


class TestRequiredFields:
    def test_valid_plan_has_all_required_fields(self, valid_plan_dict):
        validate_required_fields(valid_plan_dict)

    def test_missing_global_validations(self, valid_plan_dict):
        del valid_plan_dict["global_validations"]
        with pytest.raises(ProductPlanError, match="required"):
            validate_required_fields(valid_plan_dict)

    def test_missing_feature_depends_on(self, valid_plan_dict):
        del valid_plan_dict["features"][0]["depends_on"]
        with pytest.raises(ProductPlanError, match="required"):
            validate_required_fields(valid_plan_dict)

    def test_missing_feature_validations(self, valid_plan_dict):
        del valid_plan_dict["features"][0]["validations"]
        with pytest.raises(ProductPlanError, match="required"):
            validate_required_fields(valid_plan_dict)


class TestMutableStatuses:
    def test_no_mutable_fields(self):
        plan = {
            "features": [
                {"feature_id": "FEATURE-A", "title": "Feature A"},
            ]
        }
        validate_mutable_statuses(plan)

    def test_mutable_status_rejected(self):
        plan = {
            "features": [
                {"feature_id": "FEATURE-A", "status": "COMPLETED"},
            ]
        }
        with pytest.raises(ProductPlanError, match="mutable fields"):
            validate_mutable_statuses(plan)

    def test_mutable_state_rejected(self):
        plan = {
            "features": [
                {"feature_id": "FEATURE-A", "state": "RUNNING"},
            ]
        }
        with pytest.raises(ProductPlanError, match="mutable fields"):
            validate_mutable_statuses(plan)

    def test_multiple_mutable_fields_rejected(self):
        plan = {
            "features": [
                {
                    "feature_id": "FEATURE-A",
                    "status": "COMPLETED",
                    "progress": 50,
                },
            ]
        }
        with pytest.raises(ProductPlanError, match="mutable fields"):
            validate_mutable_statuses(plan)


class TestLoadProductPlan:
    def test_load_valid_plan(self, temp_dir, valid_schema, valid_plan_dict):
        _materialize_approved_specifications(temp_dir, valid_plan_dict)
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict, f)

        plan = load_product_plan(plan_path)
        assert plan.plan_id == "PLAN-TEST-001"
        assert plan.schema_version == "1.0.0"
        assert len(plan.features) == 2
        assert plan.features[0].feature_id == "FEATURE-A"
        assert plan.specification_policy == "approved-only"
        assert plan.global_validations == ["npm test", "cargo test"]

    def test_load_plan_missing_global_validations(self, temp_dir, valid_schema, valid_plan_dict):
        valid_plan_dict_copy = valid_plan_dict.copy()
        del valid_plan_dict_copy["global_validations"]
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict_copy, f)

        with pytest.raises(ProductPlanError):
            load_product_plan(plan_path)

    def test_load_plan_missing_feature_depends_on(self, temp_dir, valid_schema, valid_plan_dict):
        valid_plan_dict_copy = valid_plan_dict.copy()
        valid_plan_dict_copy["features"] = [f.copy() if isinstance(f, dict) else f for f in valid_plan_dict_copy["features"]]
        del valid_plan_dict_copy["features"][0]["depends_on"]
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict_copy, f)

        with pytest.raises(ProductPlanError):
            load_product_plan(plan_path)

    def test_load_plan_missing_feature_validations(self, temp_dir, valid_schema, valid_plan_dict):
        valid_plan_dict_copy = valid_plan_dict.copy()
        valid_plan_dict_copy["features"] = [f.copy() if isinstance(f, dict) else f for f in valid_plan_dict_copy["features"]]
        del valid_plan_dict_copy["features"][0]["validations"]
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict_copy, f)

        with pytest.raises(ProductPlanError):
            load_product_plan(plan_path)

    def test_load_nonexistent_file(self, temp_dir):
        plan_path = temp_dir / "nonexistent.json"
        with pytest.raises(ProductPlanError, match="Plan file not found"):
            load_product_plan(plan_path)

    def test_load_invalid_json(self, temp_dir, valid_schema):
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            f.write("{invalid json")

        with pytest.raises(ProductPlanError, match="Invalid JSON"):
            load_product_plan(plan_path)

    def test_load_plan_with_invalid_schema_version(
        self, temp_dir, valid_schema, valid_plan_dict
    ):
        valid_plan_dict["schema_version"] = "invalid"
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict, f)

        with pytest.raises(ProductPlanError, match="Invalid schema_version"):
            load_product_plan(plan_path)

    def test_load_plan_with_duplicate_features(
        self, temp_dir, valid_schema, valid_plan_dict
    ):
        valid_plan_dict["features"].append(
            {
                "feature_id": "FEATURE-A",
                "title": "Duplicate",
                "specification_path": "spec/dup.md",
                "required": True,
                "priority": 3,
                "depends_on": [],
                "validations": [],
            }
        )
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict, f)

        with pytest.raises(ProductPlanError, match="Duplicate feature IDs"):
            load_product_plan(plan_path)

    def test_load_plan_with_unknown_dependency(
        self, temp_dir, valid_schema, valid_plan_dict
    ):
        valid_plan_dict["features"].append(
            {
                "feature_id": "FEATURE-C",
                "title": "Feature C",
                "specification_path": "spec/c.md",
                "required": True,
                "priority": 3,
                "depends_on": ["FEATURE-UNKNOWN"],
                "validations": [],
            }
        )
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict, f)

        with pytest.raises(ProductPlanError, match="unknown dependencies"):
            load_product_plan(plan_path)

    def test_load_plan_with_cycle(self, temp_dir, valid_schema, valid_plan_dict):
        valid_plan_dict["features"][0]["depends_on"] = ["FEATURE-B"]
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict, f)

        with pytest.raises(ProductPlanError, match="Dependency cycle"):
            load_product_plan(plan_path)

    def test_load_plan_with_invalid_policy(
        self, temp_dir, valid_schema, valid_plan_dict
    ):
        valid_plan_dict["specification_policy"] = "invalid-policy"
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict, f)

        with pytest.raises(ProductPlanError, match="Invalid specification_policy"):
            load_product_plan(plan_path)

    def test_load_plan_rejects_mutable_status(self, temp_dir, valid_schema, valid_plan_dict):
        valid_plan_dict["features"][0]["status"] = "COMPLETED"
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict, f)

        with pytest.raises(ProductPlanError, match="mutable fields"):
            load_product_plan(plan_path)


class TestProductPlanImmutability:
    def test_plan_is_frozen(self, temp_dir, valid_schema, valid_plan_dict):
        _materialize_approved_specifications(temp_dir, valid_plan_dict)
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict, f)

        plan = load_product_plan(plan_path)
        assert plan.plan_hash is not None
        assert len(plan.plan_hash) == 64

    def test_plan_hash_consistent(self, temp_dir, valid_schema, valid_plan_dict):
        _materialize_approved_specifications(temp_dir, valid_plan_dict)
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict, f)

        plan1 = load_product_plan(plan_path)
        plan2 = load_product_plan(plan_path)
        assert plan1.plan_hash == plan2.plan_hash

    def test_plan_features_are_immutable(self, temp_dir, valid_schema, valid_plan_dict):
        _materialize_approved_specifications(temp_dir, valid_plan_dict)
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict, f)

        plan = load_product_plan(plan_path)
        with pytest.raises((AttributeError, TypeError)):
            plan.features[0].feature_id = "MODIFIED"

    def test_plan_hash_changes_with_generated_at(self, temp_dir, valid_schema, valid_plan_dict):
        # Load plan with original generated_at
        _materialize_approved_specifications(temp_dir, valid_plan_dict)
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict, f)
        plan1 = load_product_plan(plan_path)
        hash1 = plan1.plan_hash

        # Load plan with different generated_at
        valid_plan_dict["generated_at"] = "2025-01-01T00:00:00+00:00"
        plan_path2 = temp_dir / "plan2.json"
        with open(plan_path2, "w") as f:
            json.dump(valid_plan_dict, f)
        plan2 = load_product_plan(plan_path2)
        hash2 = plan2.plan_hash

        assert hash1 != hash2, "Plan hash should change when generated_at changes"

    def test_plan_hash_changes_with_global_validations(self, temp_dir, valid_schema, valid_plan_dict):
        # Load plan with original global_validations
        _materialize_approved_specifications(temp_dir, valid_plan_dict)
        plan_path = temp_dir / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(valid_plan_dict, f)
        plan1 = load_product_plan(plan_path)
        hash1 = plan1.plan_hash

        # Load plan with different global_validations
        valid_plan_dict["global_validations"] = ["npm test", "cargo test", "npm run lint"]
        plan_path2 = temp_dir / "plan2.json"
        with open(plan_path2, "w") as f:
            json.dump(valid_plan_dict, f)
        plan2 = load_product_plan(plan_path2)
        hash2 = plan2.plan_hash

        assert hash1 != hash2, "Plan hash should change when global_validations changes"


class TestFreezePlanRevision:
    def test_freeze_captures_essential_info(self, valid_plan_dict):
        plan = ProductPlan(
            schema_version=valid_plan_dict["schema_version"],
            plan_id=valid_plan_dict["plan_id"],
            generated_at=valid_plan_dict["generated_at"],
            integration_branch=valid_plan_dict["integration_branch"],
            specification_policy=valid_plan_dict["specification_policy"],
            features=[],
            global_validations=[],
            plan_hash="abc123",
        )

        frozen = freeze_plan_revision(plan, "RUN-001")
        assert frozen["run_id"] == "RUN-001"
        assert frozen["plan_id"] == "PLAN-TEST-001"
        assert frozen["plan_hash"] == "abc123"
        assert frozen["schema_version"] == "1.0.0"
        assert "frozen_at" in frozen
        assert frozen["integration_branch"] == "main"
        assert frozen["feature_count"] == 0
