import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
import autodev.product_plan as product_plan_module

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from autodev.specification_policy import (
    SpecificationValidationError,
    SpecificationPolicy,
    ValidationStatus,
    SpecificationMetadata,
    SpecificationValidationResult,
    validate_specification_content,
    validate_specification_for_policy,
    validate_json_schema_for_metadata,
    enforce_specification_gate,
    _detect_ambiguities,
)
from autodev.product_plan import ProductPlanError, load_product_plan


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def valid_metadata_schema(temp_dir):
    schema_src = Path(__file__).parent.parent / "schemas" / "specification-validation.schema.json"
    if schema_src.exists():
        with open(schema_src) as f:
            schema = json.load(f)
    else:
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Autodev Specification Validation Metadata",
            "type": "object",
            "additionalProperties": False,
            "required": ["source", "commit", "validation_status"],
            "properties": {
                "source": {"type": "string", "minLength": 1},
                "prompt": {"type": ["string", "null"]},
                "commit": {
                    "type": "string",
                    "minLength": 7,
                    "maxLength": 40,
                    "pattern": "^[a-f0-9]+$",
                },
                "validation_status": {
                    "type": "string",
                    "enum": ["approved", "draft", "rejected", "pending-human"],
                },
                "validated_at": {"type": ["string", "null"]},
                "validated_by": {"type": ["string", "null"]},
                "ambiguities": {"type": "array", "items": {"type": "string"}},
            },
        }
    schema_path = temp_dir / "specification-validation.schema.json"
    with open(schema_path, "w") as f:
        json.dump(schema, f)
    return schema_path


@pytest.fixture
def valid_approved_metadata():
    return SpecificationMetadata(
        source="approved-spec:path/to/spec.md",
        prompt=None,
        commit="abc123def456",
        validation_status=ValidationStatus.APPROVED,
        validated_at=datetime.now(timezone.utc).isoformat(),
        validated_by="supervisor@example.com",
        ambiguities=[],
    )


@pytest.fixture
def valid_draft_spec_metadata():
    return SpecificationMetadata(
        source="generated:draft",
        prompt="Create a feature to manage users",
        commit="abc123def456",
        validation_status=ValidationStatus.PENDING_HUMAN,
        ambiguities=["Draft specification requires explicit human validation before planning"],
    )


class TestSpecificationMetadata:
    def test_create_approved_metadata(self, valid_approved_metadata):
        assert valid_approved_metadata.source == "approved-spec:path/to/spec.md"
        assert valid_approved_metadata.validation_status == ValidationStatus.APPROVED
        assert valid_approved_metadata.ambiguities == []

    def test_metadata_to_dict(self, valid_approved_metadata):
        metadata_dict = valid_approved_metadata.to_dict()
        assert metadata_dict["source"] == "approved-spec:path/to/spec.md"
        assert metadata_dict["validation_status"] == "approved"
        assert metadata_dict["validated_by"] == "supervisor@example.com"

    def test_metadata_immutable_hash(self, valid_approved_metadata):
        hash1 = valid_approved_metadata.immutable_hash()
        hash2 = valid_approved_metadata.immutable_hash()
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex is 64 chars

    def test_metadata_hash_changes_with_content(self):
        meta1 = SpecificationMetadata(
            source="spec1",
            prompt=None,
            commit="abc123",
            validation_status=ValidationStatus.APPROVED,
        )
        meta2 = SpecificationMetadata(
            source="spec2",
            prompt=None,
            commit="abc123",
            validation_status=ValidationStatus.APPROVED,
        )
        assert meta1.immutable_hash() != meta2.immutable_hash()


class TestApprovedOnlyPolicy:
    def test_approved_only_with_valid_metadata(self, valid_approved_metadata):
        result = validate_specification_for_policy(
            feature_id="FEATURE-001",
            specification_path="specs/feature-001.md",
            policy="approved-only",
            existing_metadata=valid_approved_metadata,
            current_commit="abc123def456",
        )
        assert result.is_valid is True
        assert result.is_usable is True
        assert result.request_human is False
        assert "ready for planning" in result.reason

    def test_approved_only_without_metadata(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-002",
            specification_path="specs/feature-002.md",
            policy="approved-only",
            existing_metadata=None,
            current_commit="abc123def456",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True
        assert "pre-existing validated specification" in result.reason

    def test_approved_only_with_draft_status_rejected(self):
        draft_metadata = SpecificationMetadata(
            source="generated:draft",
            prompt="test",
            commit="abc123",
            validation_status=ValidationStatus.DRAFT,
        )
        result = validate_specification_for_policy(
            feature_id="FEATURE-003",
            specification_path="specs/feature-003.md",
            policy="approved-only",
            existing_metadata=draft_metadata,
            current_commit="abc123def456",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True
        assert "APPROVED status" in result.reason

    def test_approved_only_with_pending_human_rejected(self):
        pending_metadata = SpecificationMetadata(
            source="generated:draft",
            prompt="test",
            commit="abc123",
            validation_status=ValidationStatus.PENDING_HUMAN,
            ambiguities=["Needs review"],
        )
        result = validate_specification_for_policy(
            feature_id="FEATURE-004",
            specification_path="specs/feature-004.md",
            policy="approved-only",
            existing_metadata=pending_metadata,
            current_commit="abc123def456",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True

    def test_approved_only_with_ambiguities_rejected(self):
        metadata_with_ambiguity = SpecificationMetadata(
            source="approved-spec:path/to/spec.md",
            prompt=None,
            commit="abc123def456",
            validation_status=ValidationStatus.APPROVED,
            validated_at=datetime.now(timezone.utc).isoformat(),
            validated_by="supervisor@example.com",
            ambiguities=["Unclear scope", "Missing acceptance criteria"],
        )
        result = validate_specification_for_policy(
            feature_id="FEATURE-005",
            specification_path="specs/feature-005.md",
            policy="approved-only",
            existing_metadata=metadata_with_ambiguity,
            current_commit="abc123def456",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True
        assert "unresolved ambiguities" in result.reason


class TestDraftPolicy:
    def test_draft_policy_creates_pending_human_status(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-DRAFT-001",
            specification_path="specs/feature-draft-001.md",
            policy="draft",
            prompt="Create a feature to handle user authentication",
            current_commit="abc123def456",
        )
        assert result.is_valid is True
        assert result.is_usable is False
        assert result.request_human is True
        assert result.metadata.validation_status == ValidationStatus.PENDING_HUMAN
        assert "waiting for human validation" in result.reason

    def test_draft_policy_rejects_empty_content(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-DRAFT-EMPTY",
            specification_path="specs/feature-draft-empty.md",
            policy="draft",
            prompt="Formaliser une spécification d'authentification",
            current_commit="abc123def456",
            spec_content="   \n\t",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True
        assert "No specification content" in result.reason

    def test_draft_policy_rejects_empty_sections(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-DRAFT-EMPTY-SECTIONS",
            specification_path="specs/feature-draft-empty-sections.md",
            policy="draft",
            prompt="Structurer un brouillon pour la feature",
            current_commit="abc123def456",
            spec_content="""## Objectif

## Exigences

## Critères d'acceptation
""",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True
        assert any("Section 'objectif'" in ambiguity for ambiguity in result.metadata.ambiguities)
        assert any("Section 'exigences'" in ambiguity for ambiguity in result.metadata.ambiguities)
        assert any(
            "Section 'critères d'acceptation'" in ambiguity
            for ambiguity in result.metadata.ambiguities
        )

    def test_draft_policy_rejects_objective_without_requirements(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-DRAFT-OBJECTIVE-ONLY",
            specification_path="specs/feature-draft-objective-only.md",
            policy="draft",
            prompt="Décrire la fonctionnalité de connexion",
            current_commit="abc123def456",
            spec_content="""## Objectif
Permettre une connexion sécurisée des agents municipaux.

## Exigences

## Critères d'acceptation
- AC1: Une validation humaine est requise avant planification.
""",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True
        assert any("Section 'exigences'" in ambiguity for ambiguity in result.metadata.ambiguities)

    def test_draft_policy_rejects_requirement_without_acceptance_criteria(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-DRAFT-NO-AC",
            specification_path="specs/feature-draft-no-ac.md",
            policy="draft",
            prompt="Décrire la synchronisation des concessions",
            current_commit="abc123def456",
            spec_content="""## Objectif
Synchroniser les concessions entre la mairie et le terrain.

## Exigences
- R1: Importer les modifications validées depuis le registre.

## Critères d'acceptation
""",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True
        assert any(
            "Section 'critères d'acceptation'" in ambiguity
            for ambiguity in result.metadata.ambiguities
        )

    def test_draft_policy_includes_ambiguity_flag(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-DRAFT-002",
            specification_path="specs/feature-draft-002.md",
            policy="draft",
            prompt="Add a new feature",
            current_commit="abc123def456",
        )
        assert result.metadata.ambiguities
        assert any(
            "requires explicit human validation" in amb
            for amb in result.metadata.ambiguities
        )

    def test_draft_policy_stores_prompt(self):
        prompt = "Implement user login with OAuth2 support"
        result = validate_specification_for_policy(
            feature_id="FEATURE-DRAFT-003",
            specification_path="specs/feature-draft-003.md",
            policy="draft",
            prompt=prompt,
            current_commit="abc123def456",
        )
        assert result.metadata.prompt == prompt

    def test_draft_policy_source_marked_generated(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-DRAFT-004",
            specification_path="specs/feature-draft-004.md",
            policy="draft",
            prompt="Some requirement",
            current_commit="abc123def456",
        )
        assert result.metadata.source == "generated:draft"

    def test_draft_policy_validates_content_with_valid_spec(self):
        valid_spec = """## Objectif
Create a user authentication system that municipal staff can use securely every day.

## Exigences
- R1: Support OAuth2 protocol for delegated authentication with the identity provider already used by the commune.
- R2: Implement multi-factor authentication so access to sensitive cemetery records is always protected.

## Critères d'acceptation
- AC1: OAuth2 flow works end-to-end for a valid municipal account without manual intervention.
- AC2: MFA validation passes before any protected dashboard is displayed to the authenticated user.
"""
        result = validate_specification_for_policy(
            feature_id="FEATURE-DRAFT-005",
            specification_path="specs/feature-draft-005.md",
            policy="draft",
            prompt="Implement user authentication",
            current_commit="abc123def456",
            spec_content=valid_spec,
        )
        assert result.is_valid is True
        assert result.is_usable is False
        assert result.request_human is True
        assert "waiting for human validation" in result.reason

    def test_draft_policy_generates_structured_content_when_missing(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-DRAFT-GENERATED",
            specification_path="specs/feature-draft-generated.md",
            policy="draft",
            prompt="Créer un brouillon initial pour l'export PDF des concessions avec règles de validation et revue humaine",
            current_commit="abc123def456",
        )
        assert result.is_valid is True
        assert result.is_usable is False
        assert result.request_human is True
        assert result.metadata.validation_status == ValidationStatus.PENDING_HUMAN

    def test_draft_policy_rejects_incomplete_spec(self):
        incomplete_spec = "Some incomplete content without required sections"
        result = validate_specification_for_policy(
            feature_id="FEATURE-DRAFT-006",
            specification_path="specs/feature-draft-006.md",
            policy="draft",
            prompt="Implement something",
            current_commit="abc123def456",
            spec_content=incomplete_spec,
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True
        assert any("Missing required section" in amb for amb in result.metadata.ambiguities)


class TestAutonomousPolicy:
    def test_autonomous_policy_validates_without_ambiguities(self):
        prompt = "Create a comprehensive user management system with role-based access control"
        valid_spec = """## Objectif
Implement a comprehensive user management system.

## Exigences
- R1: Support role-based access control
- R2: Manage user profiles

## Critères d'acceptation
- AC1: RBAC enforcement works correctly
- AC2: User profiles are persisted
"""
        result = validate_specification_for_policy(
            feature_id="FEATURE-AUTO-001",
            specification_path="specs/feature-auto-001.md",
            policy="autonomous",
            prompt=prompt,
            current_commit="abc123def456",
            spec_content=valid_spec,
        )
        assert result.is_valid is True
        assert result.is_usable is True
        assert result.request_human is False
        assert result.metadata.validation_status == ValidationStatus.APPROVED
        assert "validated by contract" in result.reason

    def test_autonomous_policy_sets_validated_by_contract(self):
        prompt = "Build a robust dashboard with real-time updates and notifications system"
        valid_spec = """## Objectif
Build a real-time dashboard.

## Exigences
- R1: Real-time data refresh
- R2: Notifications support

## Critères d'acceptation
- AC1: Dashboard updates in real time
- AC2: Notifications are delivered
"""
        result = validate_specification_for_policy(
            feature_id="FEATURE-AUTO-002",
            specification_path="specs/feature-auto-002.md",
            policy="autonomous",
            prompt=prompt,
            current_commit="abc123def456",
            spec_content=valid_spec,
        )
        assert result.metadata.validated_by == "autonomous-contract"
        assert result.metadata.validated_at is not None

    def test_autonomous_policy_requires_prompt(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-AUTO-003",
            specification_path="specs/feature-auto-003.md",
            policy="autonomous",
            prompt=None,
            current_commit="abc123def456",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True
        assert "requires prompt" in result.reason

    def test_autonomous_policy_detects_tbd(self):
        prompt = "Create feature TBD implementation details for better user experience"
        result = validate_specification_for_policy(
            feature_id="FEATURE-AUTO-004",
            specification_path="specs/feature-auto-004.md",
            policy="autonomous",
            prompt=prompt,
            current_commit="abc123def456",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True
        assert any("To-be-determined" in amb for amb in result.metadata.ambiguities)

    def test_autonomous_policy_detects_maybe(self):
        prompt = "Maybe implement caching if needed for performance"
        result = validate_specification_for_policy(
            feature_id="FEATURE-AUTO-005",
            specification_path="specs/feature-auto-005.md",
            policy="autonomous",
            prompt=prompt,
            current_commit="abc123def456",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert "Uncertain requirement" in result.metadata.ambiguities[0]

    def test_autonomous_policy_detects_unclear(self):
        prompt = "Unclear what the exact requirements are but implement something"
        result = validate_specification_for_policy(
            feature_id="FEATURE-AUTO-006",
            specification_path="specs/feature-auto-006.md",
            policy="autonomous",
            prompt=prompt,
            current_commit="abc123def456",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert any("Unclear" in amb for amb in result.metadata.ambiguities)

    def test_autonomous_policy_detects_short_prompt(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-AUTO-007",
            specification_path="specs/feature-auto-007.md",
            policy="autonomous",
            prompt="Do it",
            current_commit="abc123def456",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert any("too short" in amb for amb in result.metadata.ambiguities)

    def test_autonomous_policy_source_marked_generated(self):
        valid_spec = """## Objectif
Implement authentication.

## Exigences
- R1: Multi-factor support

## Critères d'acceptation
- AC1: MFA works
"""
        result = validate_specification_for_policy(
            feature_id="FEATURE-AUTO-008",
            specification_path="specs/feature-auto-008.md",
            policy="autonomous",
            prompt="Create a robust user authentication system with multi-factor support",
            current_commit="abc123def456",
            spec_content=valid_spec,
        )
        assert result.metadata.source == "generated:autonomous"

    def test_autonomous_policy_requires_specification_content(self):
        prompt = "Create a comprehensive system"
        result = validate_specification_for_policy(
            feature_id="FEATURE-AUTO-009",
            specification_path="specs/feature-auto-009.md",
            policy="autonomous",
            prompt=prompt,
            current_commit="abc123def456",
            spec_content=None,
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True
        assert any("No specification content" in amb for amb in result.metadata.ambiguities)

    def test_autonomous_policy_rejects_spec_without_requirements(self):
        prompt = "Create a system"
        incomplete_spec = """## Objectif
Create a system.

## Critères d'acceptation
- AC1: Something works
"""
        result = validate_specification_for_policy(
            feature_id="FEATURE-AUTO-010",
            specification_path="specs/feature-auto-010.md",
            policy="autonomous",
            prompt=prompt,
            current_commit="abc123def456",
            spec_content=incomplete_spec,
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True
        assert any("Missing required section: exigences" in amb for amb in result.metadata.ambiguities)

    def test_autonomous_policy_detects_contradictory_requirements(self):
        prompt = "Create system that must support optional features"
        result = validate_specification_for_policy(
            feature_id="FEATURE-AUTO-011",
            specification_path="specs/feature-auto-011.md",
            policy="autonomous",
            prompt=prompt,
            current_commit="abc123def456",
        )
        assert result.is_valid is False
        assert result.is_usable is False
        assert result.request_human is True
        assert any("Contradictory requirements" in amb for amb in result.metadata.ambiguities)


class TestAmbiguityDetection:
    def test_detect_tbd(self):
        ambiguities = _detect_ambiguities("Create feature with TBD implementation details")
        assert any("To-be-determined" in amb for amb in ambiguities)

    def test_detect_todo(self):
        ambiguities = _detect_ambiguities("Implement user login TODO: add OAuth2")
        assert any("Incomplete" in amb for amb in ambiguities)

    def test_detect_maybe(self):
        ambiguities = _detect_ambiguities("Maybe add caching if we need it")
        assert any("maybe" in amb.lower() for amb in ambiguities)

    def test_detect_possibly(self):
        ambiguities = _detect_ambiguities("Possibly implement export functionality")
        assert any("possibly" in amb.lower() for amb in ambiguities)

    def test_detect_unclear(self):
        ambiguities = _detect_ambiguities("The unclear part is how to handle errors")
        assert any("Unclear" in amb for amb in ambiguities)

    def test_detect_not_sure(self):
        ambiguities = _detect_ambiguities("We are not sure what the scope should be now")
        assert any("Uncertain specification" in amb for amb in ambiguities)

    def test_detect_question_mark(self):
        ambiguities = _detect_ambiguities("What should the API response format be?")
        assert any("?" in amb or "Question mark" in amb for amb in ambiguities)

    def test_detect_short_prompt(self):
        ambiguities = _detect_ambiguities("Short")
        assert any("too short" in amb for amb in ambiguities)

    def test_clean_prompt_no_ambiguities(self):
        ambiguities = _detect_ambiguities(
            "Implement a user management system with role-based access control and comprehensive audit logging"
        )
        assert len(ambiguities) == 0

    def test_detect_contradictory_must_not(self):
        ambiguities = _detect_ambiguities("The system must support caching but must not use external cache")
        assert any("Contradictory requirements" in amb for amb in ambiguities)

    def test_detect_contradictory_required_optional(self):
        ambiguities = _detect_ambiguities("The feature is required but optional for legacy systems")
        assert any("Contradictory requirements" in amb for amb in ambiguities)

    def test_detect_contradictory_mandatory_optional(self):
        ambiguities = _detect_ambiguities("Authentication is mandatory and optional depending on context")
        assert any("Contradictory requirements" in amb for amb in ambiguities)

    def test_detect_contradictory_cannot_must(self):
        ambiguities = _detect_ambiguities("The system cannot require authentication but must enforce it")
        assert any("Contradictory requirements" in amb for amb in ambiguities)

    def test_detect_contradictory_state(self):
        ambiguities = _detect_ambiguities("The service should be disabled and enabled simultaneously")
        assert any("Contradictory" in amb for amb in ambiguities)

    def test_detect_contradictory_access(self):
        ambiguities = _detect_ambiguities("The API endpoint is read-only and write-enabled")
        assert any("Contradictory" in amb for amb in ambiguities)


class TestSpecificationContentValidation:
    def test_rejects_placeholder_only_sections(self):
        is_valid, issues = validate_specification_content(
            None,
            """## Objectif
Objectif

## Exigences
- Exigence

## Critères d'acceptation
- Critère d'acceptation
""",
        )

        assert is_valid is False
        assert any("Section 'objectif'" in issue for issue in issues)
        assert any("Section 'exigences'" in issue for issue in issues)
        assert any("Section 'critères d'acceptation'" in issue for issue in issues)


class TestSpecificationValidationResult:
    def test_result_to_dict(self, valid_approved_metadata):
        result = SpecificationValidationResult(
            feature_id="FEATURE-001",
            specification_path="specs/feature-001.md",
            metadata=valid_approved_metadata,
            is_valid=True,
            is_usable=True,
            reason="Test result",
            request_human=False,
            metadata_hash="somehash",
        )
        result_dict = result.to_dict()
        assert result_dict["feature_id"] == "FEATURE-001"
        assert result_dict["is_valid"] is True
        assert result_dict["is_usable"] is True
        assert result_dict["request_human"] is False
        assert isinstance(result_dict["metadata"], dict)


class TestEnforceSpecificationGate:
    def test_enforce_gate_allows_usable_spec(self, valid_approved_metadata):
        result = SpecificationValidationResult(
            feature_id="FEATURE-001",
            specification_path="specs/feature-001.md",
            metadata=valid_approved_metadata,
            is_valid=True,
            is_usable=True,
            reason="Valid spec",
            request_human=False,
        )
        enforce_specification_gate(result)

    def test_enforce_gate_blocks_unusable_spec(self, valid_draft_spec_metadata):
        result = SpecificationValidationResult(
            feature_id="FEATURE-002",
            specification_path="specs/feature-002.md",
            metadata=valid_draft_spec_metadata,
            is_valid=True,
            is_usable=False,
            reason="Draft specification requires human approval",
            request_human=True,
        )
        with pytest.raises(SpecificationValidationError, match="Specification gate violation"):
            enforce_specification_gate(result)

    def test_enforce_gate_error_message_includes_human_request(self):
        metadata = SpecificationMetadata(
            source="generated:draft",
            prompt="test",
            commit="abc123",
            validation_status=ValidationStatus.PENDING_HUMAN,
        )
        result = SpecificationValidationResult(
            feature_id="FEATURE-003",
            specification_path="specs/feature-003.md",
            metadata=metadata,
            is_valid=True,
            is_usable=False,
            reason="Needs human validation",
            request_human=True,
        )
        with pytest.raises(SpecificationValidationError, match="REQUEST_HUMAN"):
            enforce_specification_gate(result)


class TestPolicyVariants:
    def test_policy_as_string(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-STR-001",
            specification_path="specs/feature-str-001.md",
            policy="approved-only",
            current_commit="abc123def456",
        )
        assert result.request_human is True

    def test_policy_as_enum(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-ENUM-001",
            specification_path="specs/feature-enum-001.md",
            policy=SpecificationPolicy.APPROVED_ONLY,
            current_commit="abc123def456",
        )
        assert result.request_human is True

    def test_invalid_policy_raises_error(self):
        with pytest.raises(SpecificationValidationError, match="Invalid specification_policy"):
            validate_specification_for_policy(
                feature_id="FEATURE-INVALID",
                specification_path="specs/feature-invalid.md",
                policy="invalid-policy",
                current_commit="abc123def456",
            )

    def test_missing_current_commit_raises_error(self):
        valid_spec = """## Objectif
Décrire une fonctionnalité exploitable.

## Exigences
- R1: Formaliser une exigence métier vérifiable.

## Critères d'acceptation
- AC1: Un humain doit encore approuver le brouillon.
"""
        with pytest.raises(SpecificationValidationError, match="valid Git commit"):
            validate_specification_for_policy(
                feature_id="FEATURE-MISSING-COMMIT",
                specification_path="specs/feature-missing-commit.md",
                policy="draft",
                prompt="Créer un brouillon structuré traçable pour la fonctionnalité",
                current_commit=None,
                spec_content=valid_spec,
            )


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestJsonSchemaValidation:
    def test_valid_metadata_passes_schema(self, valid_metadata_schema, valid_approved_metadata):
        metadata_dict = valid_approved_metadata.to_dict()
        validate_json_schema_for_metadata(metadata_dict, valid_metadata_schema)

    def test_invalid_commit_fails_schema(self, valid_metadata_schema):
        metadata_dict = {
            "source": "test-source",
            "prompt": None,
            "commit": "short",
            "validation_status": "approved",
            "ambiguities": [],
        }
        with pytest.raises(SpecificationValidationError, match="schema validation failed"):
            validate_json_schema_for_metadata(metadata_dict, valid_metadata_schema)

    def test_invalid_validation_status_fails_schema(self, valid_metadata_schema):
        metadata_dict = {
            "source": "test-source",
            "prompt": None,
            "commit": "abc123def456",
            "validation_status": "unknown",
            "ambiguities": [],
        }
        with pytest.raises(SpecificationValidationError, match="schema validation failed"):
            validate_json_schema_for_metadata(metadata_dict, valid_metadata_schema)


class TestIntegrationScenarios:
    @staticmethod
    def _write_plan(
        plan_path: Path,
        *,
        plan_id: str,
        specification_policy: str,
        feature_id: str,
        title: str,
        specification_path: str,
    ) -> None:
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "plan_id": plan_id,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "integration_branch": "main",
                    "specification_policy": specification_policy,
                    "global_validations": [],
                    "features": [
                        {
                            "feature_id": feature_id,
                            "title": title,
                            "specification_path": specification_path,
                            "required": True,
                            "priority": 1,
                            "depends_on": [],
                            "validations": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_load_product_plan_rejects_approved_only_when_spec_file_is_missing(self, temp_dir):
        missing_spec_path = temp_dir / "specs" / "missing-approved.md"
        plan_path = temp_dir / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "plan_id": "PLAN-APPROVED-MISSING-SPEC",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "integration_branch": "main",
                    "specification_policy": "approved-only",
                    "global_validations": [],
                    "features": [
                        {
                            "feature_id": "FEATURE-MISSING-SPEC",
                            "title": "Feature Missing Spec",
                            "specification_path": "specs/missing-approved.md",
                            "required": True,
                            "priority": 1,
                            "depends_on": [],
                            "validations": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        with pytest.raises(
            ProductPlanError,
            match="pre-existing validated specification",
        ):
            load_product_plan(plan_path)

        assert not missing_spec_path.exists()
        assert not missing_spec_path.with_suffix(".validation.json").exists()

    def test_load_product_plan_rejects_unresolved_specification_path(self, temp_dir):
        specs_dir = temp_dir / "specs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        (specs_dir / "different-file.md").write_text(
            """## Objectif
Ne pas résoudre un mauvais chemin.

## Exigences
- R1: Le chargeur doit échouer si le chemin déclaré n'existe pas.

## Critères d'acceptation
- AC1: Une erreur explicite est levée quand le chemin ciblé est introuvable.
""",
            encoding="utf-8",
        )

        plan_path = temp_dir / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "plan_id": "PLAN-UNRESOLVED-SPEC",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "integration_branch": "main",
                    "specification_policy": "approved-only",
                    "global_validations": [],
                    "features": [
                        {
                            "feature_id": "FEATURE-UNRESOLVED-SPEC",
                            "title": "Feature Unresolved Spec",
                            "specification_path": "specs/declared-but-missing.md",
                            "required": True,
                            "priority": 1,
                            "depends_on": [],
                            "validations": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        with pytest.raises(
            ProductPlanError,
            match="pre-existing validated specification",
        ):
            load_product_plan(plan_path)

    def test_feature_flow_approved_only(self):
        approved_metadata = SpecificationMetadata(
            source="spec:manual/feature-approved.md",
            prompt=None,
            commit="abc123def456",
            validation_status=ValidationStatus.APPROVED,
            validated_at=datetime.now(timezone.utc).isoformat(),
            validated_by="human-supervisor",
            ambiguities=[],
        )

        result = validate_specification_for_policy(
            feature_id="FEATURE-APPROVED",
            specification_path="specs/approved.md",
            policy="approved-only",
            existing_metadata=approved_metadata,
            current_commit="abc123def456",
        )

        assert result.is_usable is True
        enforce_specification_gate(result)

    def test_feature_flow_draft_requires_human(self):
        result = validate_specification_for_policy(
            feature_id="FEATURE-DRAFT",
            specification_path="specs/draft.md",
            policy="draft",
            prompt="Create new dashboard with analytics",
            current_commit="abc123def456",
        )

        assert result.is_usable is False
        assert result.request_human is True
        with pytest.raises(SpecificationValidationError):
            enforce_specification_gate(result)

    def test_feature_flow_draft_with_valid_content(self):
        valid_spec = """## Objectif
Create dashboard for analytics tracking with a first human-reviewed draft ready for product review.

## Exigences
- R1: Display key metrics needed by cemetery administrators in a consolidated dashboard.
- R2: Refresh data in near real time so agents can rely on the visible occupancy and renewal indicators.

## Critères d'acceptation
- AC1: Metrics display correctly for the published concession and deceased datasets used by the municipality.
- AC2: Data refreshes every 30 seconds without breaking navigation or requiring a page reload.
"""
        result = validate_specification_for_policy(
            feature_id="FEATURE-DRAFT-VALID",
            specification_path="specs/draft-valid.md",
            policy="draft",
            prompt="Create new dashboard with analytics",
            current_commit="abc123def456",
            spec_content=valid_spec,
        )

        assert result.is_valid is True

    def test_load_product_plan_generates_missing_draft_specification_and_blocks_execution(
        self, temp_dir, monkeypatch
    ):
        draft_spec_path = temp_dir / "specs" / "feature-draft-generated.md"
        metadata_path = draft_spec_path.with_suffix(f"{draft_spec_path.suffix}.validation.json")
        plan_path = temp_dir / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "plan_id": "PLAN-DRAFT-GENERATED-MISSING-SPEC",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "integration_branch": "main",
                    "specification_policy": "draft",
                    "global_validations": [],
                    "features": [
                        {
                            "feature_id": "FEATURE-DRAFT-GENERATED",
                            "title": "Feature Draft Generated",
                            "specification_path": "specs/feature-draft-generated.md",
                            "required": True,
                            "priority": 1,
                            "depends_on": [],
                            "validations": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(
            product_plan_module,
            "_resolve_current_commit",
            lambda _: "deadbeef1234567",
        )

        with pytest.raises(ProductPlanError, match="REQUEST_HUMAN"):
            load_product_plan(plan_path)

        assert draft_spec_path.exists()
        assert draft_spec_path.parent == temp_dir / "specs"
        content = draft_spec_path.read_text(encoding="utf-8")
        assert "## Objectif" in content
        assert "## Exigences" in content
        assert "## Critères d'acceptation" in content
        assert "- R1:" in content
        assert "- AC1:" in content
        assert "Formaliser un premier brouillon exploitable" in content

        assert metadata_path.exists()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["validation_status"] == "pending-human"
        assert metadata["commit"] == "deadbeef1234567"
        assert metadata["source"] == "generated:draft"
        assert any("human validation" in ambiguity for ambiguity in metadata["ambiguities"])

    def test_load_product_plan_generates_missing_autonomous_specification_and_allows_execution(
        self, temp_dir, monkeypatch
    ):
        spec_path = temp_dir / "specs" / "feature-autonomous-generated.md"
        metadata_path = spec_path.with_suffix(f"{spec_path.suffix}.validation.json")
        plan_path = temp_dir / "plan.json"
        self._write_plan(
            plan_path,
            plan_id="PLAN-AUTONOMOUS-GENERATED",
            specification_policy="autonomous",
            feature_id="FEATURE-AUTONOMOUS-GENERATED",
            title="Automatiser la synchronisation des concessions avec audit complet et règles métier explicites",
            specification_path="specs/feature-autonomous-generated.md",
        )

        monkeypatch.setattr(
            product_plan_module,
            "_resolve_current_commit",
            lambda _: "deadbeef1234567",
        )

        plan = load_product_plan(plan_path)

        assert plan.plan_id == "PLAN-AUTONOMOUS-GENERATED"
        assert spec_path.exists()
        assert spec_path.parent == temp_dir / "specs"
        assert not (product_plan_module.WORKSPACE_ROOT / "specs" / "feature-autonomous-generated.md").exists()
        content = spec_path.read_text(encoding="utf-8")
        assert "## Objectif" in content
        assert "## Exigences" in content
        assert "## Critères d'acceptation" in content
        assert "- R1:" in content
        assert "- AC1:" in content
        assert "FEATURE-AUTONOMOUS-GENERATED" in content

        is_valid, issues = validate_specification_content(spec_path)
        assert is_valid is True
        assert issues == []

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["validation_status"] == "approved"
        assert metadata["commit"] == "deadbeef1234567"
        assert metadata["source"] == "generated:autonomous"
        assert metadata["validated_by"] == "autonomous-contract"
        assert metadata["ambiguities"] == []
        assert metadata["prompt"]
        assert "feature-autonomous-generated.md" in metadata["prompt"]

    def test_load_product_plan_blocks_autonomous_generation_when_business_ambiguity_is_detected(
        self, temp_dir, monkeypatch
    ):
        spec_path = temp_dir / "specs" / "feature-autonomous-ambiguous.md"
        metadata_path = spec_path.with_suffix(f"{spec_path.suffix}.validation.json")
        plan_path = temp_dir / "plan.json"
        self._write_plan(
            plan_path,
            plan_id="PLAN-AUTONOMOUS-AMBIGUOUS",
            specification_policy="autonomous",
            feature_id="FEATURE-AUTONOMOUS-AMBIGUOUS",
            title="TBD workflow for cemetery dashboard with unclear business ownership",
            specification_path="specs/feature-autonomous-ambiguous.md",
        )

        monkeypatch.setattr(
            product_plan_module,
            "_resolve_current_commit",
            lambda _: "deadbeef1234567",
        )

        with pytest.raises(ProductPlanError, match="REQUEST_HUMAN"):
            load_product_plan(plan_path)

        assert spec_path.exists()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["validation_status"] == "draft"
        assert metadata["source"] == "generated:autonomous"
        assert any("To-be-determined" in ambiguity for ambiguity in metadata["ambiguities"])
        assert any("Unclear" in ambiguity for ambiguity in metadata["ambiguities"])

    def test_load_product_plan_blocks_autonomous_generation_when_generated_specification_is_invalid(
        self, temp_dir, monkeypatch
    ):
        spec_path = temp_dir / "specs" / "feature-autonomous-invalid.md"
        metadata_path = spec_path.with_suffix(f"{spec_path.suffix}.validation.json")
        plan_path = temp_dir / "plan.json"
        self._write_plan(
            plan_path,
            plan_id="PLAN-AUTONOMOUS-INVALID",
            specification_policy="autonomous",
            feature_id="FEATURE-AUTONOMOUS-INVALID",
            title="Automatiser les exports réglementaires des concessions avec contraintes métier déterministes",
            specification_path="specs/feature-autonomous-invalid.md",
        )

        monkeypatch.setattr(
            product_plan_module,
            "_resolve_current_commit",
            lambda _: "deadbeef1234567",
        )
        monkeypatch.setattr(
            product_plan_module,
            "_build_missing_autonomous_specification_content",
            lambda **_: "## Objectif\nContenu incomplet sans sections contractuelles.\n",
        )

        with pytest.raises(ProductPlanError, match="REQUEST_HUMAN"):
            load_product_plan(plan_path)

        assert spec_path.exists()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["validation_status"] == "draft"
        assert any("Missing required section: exigences" in ambiguity for ambiguity in metadata["ambiguities"])
        assert any(
            "Missing required section: critères d'acceptation" in ambiguity
            for ambiguity in metadata["ambiguities"]
        )

    def test_load_product_plan_blocks_autonomous_generation_without_explicit_authorization(
        self, temp_dir, monkeypatch
    ):
        spec_path = temp_dir / "specs" / "feature-autonomous-unauthorized.md"
        plan_path = temp_dir / "plan.json"
        self._write_plan(
            plan_path,
            plan_id="PLAN-AUTONOMOUS-UNAUTHORIZED",
            specification_policy="autonomous",
            feature_id="FEATURE-AUTONOMOUS-UNAUTHORIZED",
            title="Automatiser le suivi des reprises avec périmètre métier clairement défini",
            specification_path="specs/feature-autonomous-unauthorized.md",
        )

        monkeypatch.setattr(
            product_plan_module,
            "_resolve_current_commit",
            lambda _: "deadbeef1234567",
        )
        monkeypatch.setattr(
            product_plan_module,
            "_is_autonomous_generation_authorized",
            lambda *args, **kwargs: False,
        )

        with pytest.raises(ProductPlanError, match="REQUEST_HUMAN"):
            load_product_plan(plan_path)

        assert not spec_path.exists()
        assert not spec_path.with_suffix(f"{spec_path.suffix}.validation.json").exists()

    def test_feature_flow_autonomous_valid(self):
        prompt = "Implement comprehensive inventory tracking system with real-time notifications and multi-user support"
        valid_spec = """## Objectif
Implement inventory tracking with real-time notifications.

## Exigences
- R1: Track inventory changes
- R2: Send real-time notifications
- R3: Support multiple users

## Critères d'acceptation
- AC1: Inventory changes are tracked
- AC2: Notifications are sent within 1 second
- AC3: Multi-user concurrent access works
"""
        result = validate_specification_for_policy(
            feature_id="FEATURE-AUTO",
            specification_path="specs/autonomous.md",
            policy="autonomous",
            prompt=prompt,
            current_commit="abc123def456",
            spec_content=valid_spec,
        )

        assert result.is_usable is True
        assert result.request_human is False
        enforce_specification_gate(result)

    def test_feature_flow_autonomous_ambiguous(self):
        prompt = "Implement feature TBD based on unclear requirements"
        result = validate_specification_for_policy(
            feature_id="FEATURE-AUTO-AMBIGUOUS",
            specification_path="specs/autonomous-ambiguous.md",
            policy="autonomous",
            prompt=prompt,
            current_commit="abc123def456",
        )

        assert result.is_usable is False
        assert result.request_human is True
        with pytest.raises(SpecificationValidationError):
            enforce_specification_gate(result)

    def test_approved_only_blocks_draft_spec(self):
        draft_metadata = SpecificationMetadata(
            source="generated:draft",
            prompt="test",
            commit="abc123",
            validation_status=ValidationStatus.DRAFT,
        )
        result = validate_specification_for_policy(
            feature_id="FEATURE-BLOCKED",
            specification_path="specs/blocked.md",
            policy="approved-only",
            existing_metadata=draft_metadata,
            current_commit="abc123def456",
        )

        assert result.is_usable is False
        assert result.request_human is True
        with pytest.raises(SpecificationValidationError, match="Specification gate violation"):
            enforce_specification_gate(result)

    def test_autonomous_blocks_contradictory_spec(self):
        prompt = "System must reject and accept all requests simultaneously"
        result = validate_specification_for_policy(
            feature_id="FEATURE-CONTRADICTORY",
            specification_path="specs/contradictory.md",
            policy="autonomous",
            prompt=prompt,
            current_commit="abc123def456",
        )

        assert result.is_usable is False
        assert result.request_human is True
        assert any("Contradictory" in amb for amb in result.metadata.ambiguities)
        with pytest.raises(SpecificationValidationError):
            enforce_specification_gate(result)

    def test_load_product_plan_enforces_draft_specification_gate(self, temp_dir):
        spec_path = temp_dir / "specs" / "feature-draft.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            """## Objectif
Créer un brouillon traçable.

## Exigences
- R1: Préparer une version de travail.

## Critères d'acceptation
- AC1: Le brouillon est lisible et structuré.
""",
            encoding="utf-8",
        )

        plan_path = temp_dir / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "plan_id": "PLAN-DRAFT-GATE",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "integration_branch": "main",
                    "specification_policy": "draft",
                    "global_validations": [],
                    "features": [
                        {
                            "feature_id": "FEATURE-DRAFT-GATE",
                            "title": "Feature Draft Gate",
                            "specification_path": "specs/feature-draft.md",
                            "required": True,
                            "priority": 1,
                            "depends_on": [],
                            "validations": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        with pytest.raises(ProductPlanError, match="REQUEST_HUMAN"):
            load_product_plan(plan_path)

    def test_load_product_plan_blocks_approved_only_without_validated_metadata(self, temp_dir):
        spec_path = temp_dir / "specs" / "feature-approved.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            """## Objectif
Utiliser une spécification existante.

## Exigences
- R1: Le plan exige une validation préalable.

## Critères d'acceptation
- AC1: Aucune planification autonome ne démarre sans approbation.
""",
            encoding="utf-8",
        )

        plan_path = temp_dir / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "plan_id": "PLAN-APPROVED-GATE",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "integration_branch": "main",
                    "specification_policy": "approved-only",
                    "global_validations": [],
                    "features": [
                        {
                            "feature_id": "FEATURE-APPROVED-GATE",
                            "title": "Feature Approved Gate",
                            "specification_path": "specs/feature-approved.md",
                            "required": True,
                            "priority": 1,
                            "depends_on": [],
                            "validations": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        with pytest.raises(ProductPlanError, match="pre-existing validated specification"):
            load_product_plan(plan_path)

    def test_load_product_plan_does_not_bypass_gate_when_no_specifications_exist(self, temp_dir):
        plan_path = temp_dir / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "plan_id": "PLAN-NO-SPECS-PRESENT",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "integration_branch": "main",
                    "specification_policy": "approved-only",
                    "global_validations": [],
                    "features": [
                        {
                            "feature_id": "FEATURE-NO-SPECS-A",
                            "title": "Feature No Specs A",
                            "specification_path": "specs/a.md",
                            "required": True,
                            "priority": 1,
                            "depends_on": [],
                            "validations": [],
                        },
                        {
                            "feature_id": "FEATURE-NO-SPECS-B",
                            "title": "Feature No Specs B",
                            "specification_path": "specs/b.md",
                            "required": True,
                            "priority": 2,
                            "depends_on": ["FEATURE-NO-SPECS-A"],
                            "validations": [],
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        with pytest.raises(
            ProductPlanError,
            match="pre-existing validated specification",
        ):
            load_product_plan(plan_path)

    def test_load_product_plan_allows_approved_only_with_existing_approved_metadata(self, temp_dir):
        spec_path = temp_dir / "specs" / "feature-approved.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            """## Objectif
Réutiliser une spécification explicitement approuvée.

## Exigences
- R1: Charger la spécification existante.
- R2: Vérifier sa validation approuvée avant planification.

## Critères d'acceptation
- AC1: Le plan est chargé si les métadonnées sont approuvées.
- AC2: Aucune intervention humaine n'est requise dans ce cas.
""",
            encoding="utf-8",
        )
        metadata_path = spec_path.with_suffix(f"{spec_path.suffix}.validation.json")
        metadata_path.write_text(
            json.dumps(
                {
                    "source": "spec:manual/specs/feature-approved.md",
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

        plan_path = temp_dir / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "plan_id": "PLAN-APPROVED-METADATA",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "integration_branch": "main",
                    "specification_policy": "approved-only",
                    "global_validations": [],
                    "features": [
                        {
                            "feature_id": "FEATURE-APPROVED-METADATA",
                            "title": "Feature Approved Metadata",
                            "specification_path": "specs/feature-approved.md",
                            "required": True,
                            "priority": 1,
                            "depends_on": [],
                            "validations": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        plan = load_product_plan(plan_path)
        assert plan.plan_id == "PLAN-APPROVED-METADATA"

    def test_load_product_plan_allows_autonomous_with_valid_structured_spec(self, temp_dir):
        spec_path = temp_dir / "specs" / "feature-autonomous.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            """## Objectif
Automatiser une spécification complète et cohérente pour la feature.

## Exigences
- R1: Gérer les utilisateurs avec rôles persistés.
- R2: Journaliser les changements sensibles.
- R3: Refuser toute ambiguïté métier résiduelle.

## Critères d'acceptation
- AC1: Les rôles sont appliqués à chaque action sensible.
- AC2: Chaque changement d'autorisation est audité.
- AC3: Le flux échoue si une contradiction est détectée.
""",
            encoding="utf-8",
        )

        plan_path = temp_dir / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "plan_id": "PLAN-AUTONOMOUS-GATE",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "integration_branch": "main",
                    "specification_policy": "autonomous",
                    "global_validations": [],
                    "features": [
                        {
                            "feature_id": "FEATURE-AUTONOMOUS-GATE",
                            "title": "Feature Autonomous Gate",
                            "specification_path": "specs/feature-autonomous.md",
                            "required": True,
                            "priority": 1,
                            "depends_on": [],
                            "validations": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        plan = load_product_plan(plan_path)
        assert plan.plan_id == "PLAN-AUTONOMOUS-GATE"

    @pytest.mark.parametrize(
        ("policy", "expected_status", "expected_exception_pattern"),
        [
            ("draft", "pending-human", "REQUEST_HUMAN"),
            ("autonomous", "approved", None),
        ],
    )
    def test_load_product_plan_persists_metadata_for_existing_spec_without_metadata(
        self,
        temp_dir,
        monkeypatch,
        policy,
        expected_status,
        expected_exception_pattern,
    ):
        spec_path = temp_dir / "specs" / f"feature-{policy}.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            f"""## Objectif
Traiter une spécification existante pour la politique {policy}.

## Exigences
- R1: Réutiliser la spécification déjà présente au chemin déclaré.
- R2: Persister des métadonnées de validation traçables.

## Critères d'acceptation
- AC1: Le fichier de métadonnées est écrit à côté de la spécification.
- AC2: Le statut reflète la décision de la politique {policy}.
""",
            encoding="utf-8",
        )
        metadata_path = spec_path.with_suffix(f"{spec_path.suffix}.validation.json")
        plan_path = temp_dir / f"plan-{policy}.json"
        self._write_plan(
            plan_path,
            plan_id=f"PLAN-{policy.upper()}-EXISTING-NO-METADATA",
            specification_policy=policy,
            feature_id=f"FEATURE-{policy.upper()}-EXISTING-NO-METADATA",
            title=f"Feature {policy} Existing No Metadata",
            specification_path=f"specs/feature-{policy}.md",
        )

        monkeypatch.setattr(
            product_plan_module,
            "_resolve_current_commit",
            lambda _: "deadbeef1234567",
        )

        if expected_exception_pattern is None:
            plan = load_product_plan(plan_path)
            assert plan.plan_id == f"PLAN-{policy.upper()}-EXISTING-NO-METADATA"
        else:
            with pytest.raises(ProductPlanError, match=expected_exception_pattern):
                load_product_plan(plan_path)

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["commit"] == "deadbeef1234567"
        assert metadata["validation_status"] == expected_status
        assert metadata["prompt"]
        assert "document origin" in metadata["prompt"]
        assert f"feature-{policy}.md" in metadata["prompt"]
        if policy == "draft":
            assert metadata["source"] == "generated:draft"
            assert any("human validation" in ambiguity for ambiguity in metadata["ambiguities"])
        else:
            assert metadata["source"] == "generated:autonomous"
            assert metadata["validated_by"] == "autonomous-contract"
            assert metadata["ambiguities"] == []

    @pytest.mark.parametrize(
        ("policy", "expected_status", "expected_exception_pattern"),
        [
            ("draft", "pending-human", "REQUEST_HUMAN"),
            ("autonomous", "approved", None),
        ],
    )
    def test_load_product_plan_regenerates_invalid_metadata_for_existing_spec(
        self,
        temp_dir,
        monkeypatch,
        policy,
        expected_status,
        expected_exception_pattern,
    ):
        spec_path = temp_dir / "specs" / f"feature-{policy}-invalid-metadata.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            """## Objectif
Réutiliser une spécification existante malgré des métadonnées invalides.

## Exigences
- R1: Revalider le contenu contractuel.
- R2: Remplacer les métadonnées invalides par une version conforme.

## Critères d'acceptation
- AC1: Le flux ne conserve pas un fichier de métadonnées invalide.
- AC2: La nouvelle validation reflète la politique active.
""",
            encoding="utf-8",
        )
        metadata_path = spec_path.with_suffix(f"{spec_path.suffix}.validation.json")
        metadata_path.write_text(
            json.dumps(
                {
                    "source": "",
                    "prompt": 42,
                    "commit": "not-a-commit",
                    "validation_status": "broken",
                }
            ),
            encoding="utf-8",
        )
        plan_path = temp_dir / f"plan-{policy}-invalid-metadata.json"
        self._write_plan(
            plan_path,
            plan_id=f"PLAN-{policy.upper()}-EXISTING-INVALID-METADATA",
            specification_policy=policy,
            feature_id=f"FEATURE-{policy.upper()}-EXISTING-INVALID-METADATA",
            title=f"Feature {policy} Existing Invalid Metadata",
            specification_path=f"specs/feature-{policy}-invalid-metadata.md",
        )

        monkeypatch.setattr(
            product_plan_module,
            "_resolve_current_commit",
            lambda _: "deadbeef1234567",
        )

        if expected_exception_pattern is None:
            plan = load_product_plan(plan_path)
            assert plan.plan_id == f"PLAN-{policy.upper()}-EXISTING-INVALID-METADATA"
        else:
            with pytest.raises(ProductPlanError, match=expected_exception_pattern):
                load_product_plan(plan_path)

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["source"] == f"generated:{policy}"
        assert metadata["commit"] == "deadbeef1234567"
        assert metadata["validation_status"] == expected_status

    def test_load_product_plan_regenerates_stale_autonomous_metadata_for_existing_spec(
        self, temp_dir, monkeypatch
    ):
        spec_path = temp_dir / "specs" / "feature-autonomous-stale.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            """## Objectif
Réutiliser une spécification autonome existante en régénérant une traçabilité périmée.

## Exigences
- R1: Réévaluer le contenu de la spécification à chaque chargement du plan autonome.
- R2: Réattacher la validation au commit Git courant.

## Critères d'acceptation
- AC1: Le commit enregistré correspond au commit résolu pendant le chargement.
- AC2: Les métadonnées persistées décrivent la validation autonome effective.
""",
            encoding="utf-8",
        )
        metadata_path = spec_path.with_suffix(f"{spec_path.suffix}.validation.json")
        metadata_path.write_text(
            json.dumps(
                {
                    "source": "generated:autonomous",
                    "prompt": "document origin: specs/feature-autonomous-stale.md",
                    "commit": "abc123def456",
                    "validation_status": "draft",
                    "validated_at": "2026-01-01T00:00:00+00:00",
                    "validated_by": "autonomous-contract",
                    "ambiguities": ["Obsolete validation"],
                }
            ),
            encoding="utf-8",
        )
        plan_path = temp_dir / "plan-autonomous-stale.json"
        self._write_plan(
            plan_path,
            plan_id="PLAN-AUTONOMOUS-EXISTING-STALE-METADATA",
            specification_policy="autonomous",
            feature_id="FEATURE-AUTONOMOUS-EXISTING-STALE-METADATA",
            title="Feature Autonomous Existing Stale Metadata",
            specification_path="specs/feature-autonomous-stale.md",
        )

        monkeypatch.setattr(
            product_plan_module,
            "_resolve_current_commit",
            lambda _: "deadbeef1234567",
        )

        plan = load_product_plan(plan_path)

        assert plan.plan_id == "PLAN-AUTONOMOUS-EXISTING-STALE-METADATA"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["source"] == "generated:autonomous"
        assert metadata["commit"] == "deadbeef1234567"
        assert metadata["validation_status"] == "approved"
        assert metadata["validated_by"] == "autonomous-contract"
        assert metadata["ambiguities"] == []

    def test_load_product_plan_rejects_invalid_approved_only_metadata(self, temp_dir, monkeypatch):
        spec_path = temp_dir / "specs" / "feature-approved-invalid-metadata.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            """## Objectif
Refuser une spécification approuvée dont la traçabilité est invalide.

## Exigences
- R1: Ne pas réutiliser des métadonnées cassées en mode approved-only.

## Critères d'acceptation
- AC1: Le chargement échoue tant que la validation approuvée n'est pas restaurée.
""",
            encoding="utf-8",
        )
        metadata_path = spec_path.with_suffix(f"{spec_path.suffix}.validation.json")
        metadata_path.write_text(
            json.dumps(
                {
                    "source": "spec:manual/specs/feature-approved-invalid-metadata.md",
                    "prompt": None,
                    "commit": "abc123def456",
                    "validation_status": "invalid-status",
                }
            ),
            encoding="utf-8",
        )
        plan_path = temp_dir / "plan-approved-invalid-metadata.json"
        self._write_plan(
            plan_path,
            plan_id="PLAN-APPROVED-INVALID-METADATA",
            specification_policy="approved-only",
            feature_id="FEATURE-APPROVED-INVALID-METADATA",
            title="Feature Approved Invalid Metadata",
            specification_path="specs/feature-approved-invalid-metadata.md",
        )

        monkeypatch.setattr(
            product_plan_module,
            "_resolve_current_commit",
            lambda _: "deadbeef1234567",
        )

        with pytest.raises(ProductPlanError, match="Invalid specification metadata"):
            load_product_plan(plan_path)

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["validation_status"] == "invalid-status"

    def test_load_product_plan_preserves_existing_approved_metadata(self, temp_dir, monkeypatch):
        spec_path = temp_dir / "specs" / "feature-approved-preserved.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            """## Objectif
Préserver une validation humaine déjà acquise en mode approved-only.

## Exigences
- R1: Réutiliser une spécification approuvée sans réécrire sa traçabilité.

## Critères d'acceptation
- AC1: Le fichier de métadonnées reste inchangé après chargement du plan.
""",
            encoding="utf-8",
        )
        metadata_path = spec_path.with_suffix(f"{spec_path.suffix}.validation.json")
        original_metadata = {
            "source": "spec:manual/specs/feature-approved-preserved.md",
            "prompt": None,
            "commit": "abc123def456",
            "validation_status": "approved",
            "validated_at": "2026-02-01T12:00:00+00:00",
            "validated_by": "human-supervisor",
            "ambiguities": [],
        }
        metadata_path.write_text(
            json.dumps(original_metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        plan_path = temp_dir / "plan-approved-preserved.json"
        self._write_plan(
            plan_path,
            plan_id="PLAN-APPROVED-PRESERVED-METADATA",
            specification_policy="approved-only",
            feature_id="FEATURE-APPROVED-PRESERVED-METADATA",
            title="Feature Approved Preserved Metadata",
            specification_path="specs/feature-approved-preserved.md",
        )

        monkeypatch.setattr(
            product_plan_module,
            "_resolve_current_commit",
            lambda _: "deadbeef1234567",
        )

        plan = load_product_plan(plan_path)

        assert plan.plan_id == "PLAN-APPROVED-PRESERVED-METADATA"
        assert json.loads(metadata_path.read_text(encoding="utf-8")) == original_metadata

    def test_load_product_plan_propagates_resolved_git_commit(self, temp_dir, monkeypatch):
        spec_path = temp_dir / "specs" / "feature-approved.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            """## Objectif
Réutiliser une spécification approuvée avec un commit traçable.

## Exigences
- R1: Le commit Git courant doit être propagé à la validation.

## Critères d'acceptation
- AC1: La validation reçoit un hash de commit exploitable.
""",
            encoding="utf-8",
        )
        metadata_path = spec_path.with_suffix(f"{spec_path.suffix}.validation.json")
        metadata_path.write_text(
            json.dumps(
                {
                    "source": "spec:manual/specs/feature-approved.md",
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
        plan_path = temp_dir / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "plan_id": "PLAN-COMMIT-PROPAGATION",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "integration_branch": "main",
                    "specification_policy": "approved-only",
                    "global_validations": [],
                    "features": [
                        {
                            "feature_id": "FEATURE-COMMIT-PROPAGATION",
                            "title": "Feature Commit Propagation",
                            "specification_path": "specs/feature-approved.md",
                            "required": True,
                            "priority": 1,
                            "depends_on": [],
                            "validations": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        captured_commit: list[str] = []

        def fake_resolve_current_commit(plan_file: Path) -> str:
            assert plan_file == plan_path
            return "deadbeef1234567"

        original_validate = product_plan_module.validate_specification_for_policy

        def capturing_validate(*args, **kwargs):
            captured_commit.append(kwargs["current_commit"])
            return original_validate(*args, **kwargs)

        monkeypatch.setattr(product_plan_module, "_resolve_current_commit", fake_resolve_current_commit)
        monkeypatch.setattr(product_plan_module, "validate_specification_for_policy", capturing_validate)

        plan = load_product_plan(plan_path)

        assert plan.plan_id == "PLAN-COMMIT-PROPAGATION"
        assert captured_commit == ["deadbeef1234567"]

    def test_resolve_current_commit_uses_git_helper_for_identifiable_commit(self, temp_dir, monkeypatch):
        plan_path = temp_dir / "plan.json"
        plan_path.write_text("{}", encoding="utf-8")
        captured_repo_roots: list[Path] = []

        def fake_is_git_worktree(path: Path) -> bool:
            return path == plan_path.parent

        def fake_current_head(repo_root: Path) -> str:
            captured_repo_roots.append(repo_root)
            return "feedface1234567"

        monkeypatch.setattr(product_plan_module, "_is_git_worktree", fake_is_git_worktree)
        monkeypatch.setattr(product_plan_module, "current_head", fake_current_head, raising=False)

        assert product_plan_module._resolve_current_commit(plan_path) == "feedface1234567"
        assert captured_repo_roots == [plan_path.parent]

    def test_load_product_plan_rejects_unknown_commit_resolution(self, temp_dir, monkeypatch):
        spec_path = temp_dir / "specs" / "feature-approved.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            """## Objectif
Bloquer un commit non traçable.

## Exigences
- R1: Refuser toute validation si le commit courant n'est pas exploitable.

## Critères d'acceptation
- AC1: Le chargement du plan échoue explicitement.
""",
            encoding="utf-8",
        )
        metadata_path = spec_path.with_suffix(f"{spec_path.suffix}.validation.json")
        metadata_path.write_text(
            json.dumps(
                {
                    "source": "spec:manual/specs/feature-approved.md",
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
        plan_path = temp_dir / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "plan_id": "PLAN-UNKNOWN-COMMIT",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "integration_branch": "main",
                    "specification_policy": "approved-only",
                    "global_validations": [],
                    "features": [
                        {
                            "feature_id": "FEATURE-UNKNOWN-COMMIT",
                            "title": "Feature Unknown Commit",
                            "specification_path": "specs/feature-approved.md",
                            "required": True,
                            "priority": 1,
                            "depends_on": [],
                            "validations": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(
            product_plan_module,
            "_resolve_current_commit",
            lambda _: "unknown",
        )

        with pytest.raises(ProductPlanError, match="Unable to determine a valid Git commit"):
            load_product_plan(plan_path)

    def test_load_product_plan_blocks_when_git_commit_resolution_fails(self, temp_dir, monkeypatch):
        spec_path = temp_dir / "specs" / "feature-approved.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            """## Objectif
Refuser la planification sans commit Git.

## Exigences
- R1: La résolution Git doit être fiable et bloquante en cas d'échec.

## Critères d'acceptation
- AC1: Une erreur explicite remonte au chargement du plan.
""",
            encoding="utf-8",
        )
        metadata_path = spec_path.with_suffix(f"{spec_path.suffix}.validation.json")
        metadata_path.write_text(
            json.dumps(
                {
                    "source": "spec:manual/specs/feature-approved.md",
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
        plan_path = temp_dir / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "plan_id": "PLAN-COMMIT-ERROR",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "integration_branch": "main",
                    "specification_policy": "approved-only",
                    "global_validations": [],
                    "features": [
                        {
                            "feature_id": "FEATURE-COMMIT-ERROR",
                            "title": "Feature Commit Error",
                            "specification_path": "specs/feature-approved.md",
                            "required": True,
                            "priority": 1,
                            "depends_on": [],
                            "validations": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        def failing_resolve_current_commit(_: Path) -> str:
            raise ProductPlanError("Git rev-parse HEAD failed for plan validation")

        monkeypatch.setattr(
            product_plan_module,
            "_resolve_current_commit",
            failing_resolve_current_commit,
        )

        with pytest.raises(ProductPlanError, match="Git rev-parse HEAD failed for plan validation"):
            load_product_plan(plan_path)
