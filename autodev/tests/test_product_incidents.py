import json
import tempfile
from pathlib import Path

import pytest

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore

from autodev.product_incidents import (
    CLOSED_INCIDENTS,
    IncidentRepeatability,
    IncidentScope,
    IncidentSeverity,
    ProductIncident,
    ProductIncidentError,
    ProductIncidentTaxonomy,
    build_default_taxonomy,
    load_product_incidents,
    load_product_incidents_from_file,
    validate_duplicate_codes,
    validate_json_schema,
    validate_schema_version,
)


class TestIncidentSeverity:
    def test_severity_values(self):
        assert IncidentSeverity.CRITICAL.value == "critical"
        assert IncidentSeverity.HIGH.value == "high"
        assert IncidentSeverity.MEDIUM.value == "medium"
        assert IncidentSeverity.LOW.value == "low"

    def test_severity_from_string(self):
        assert IncidentSeverity("critical") == IncidentSeverity.CRITICAL
        assert IncidentSeverity("high") == IncidentSeverity.HIGH


class TestIncidentScope:
    def test_all_scopes_defined(self):
        expected = {
            "provider",
            "permissions",
            "git_state",
            "initialization",
            "worktree",
            "validation",
            "correction_limit",
            "dependency",
            "git_conflict",
            "human_decision",
        }
        actual = {s.value for s in IncidentScope}
        assert actual == expected

    def test_scope_from_string(self):
        assert IncidentScope("provider") == IncidentScope.PROVIDER
        assert IncidentScope("git_conflict") == IncidentScope.GIT_CONFLICT


class TestIncidentRepeatability:
    def test_repeatability_values(self):
        assert IncidentRepeatability.ALWAYS.value == "always"
        assert IncidentRepeatability.SOMETIMES.value == "sometimes"
        assert IncidentRepeatability.RARELY.value == "rarely"
        assert IncidentRepeatability.UNKNOWN.value == "unknown"


class TestProductIncident:
    @pytest.fixture
    def sample_incident(self):
        return ProductIncident(
            code="TEST_INCIDENT",
            title="Test Incident",
            description="A test incident",
            severity=IncidentSeverity.HIGH,
            scope=IncidentScope.PROVIDER,
            proofs=["proof1", "proof2"],
            repeatability=IncidentRepeatability.ALWAYS,
            recommended_action="Take action",
            retryable=True,
            deferrable=False,
            correctable_under_supervision=True,
            terminal=False,
        )

    def test_incident_creation(self, sample_incident):
        assert sample_incident.code == "TEST_INCIDENT"
        assert sample_incident.severity == IncidentSeverity.HIGH
        assert sample_incident.proofs == ["proof1", "proof2"]

    def test_incident_frozen(self, sample_incident):
        with pytest.raises(AttributeError):
            sample_incident.code = "CHANGED"

    def test_incident_to_dict(self, sample_incident):
        data = sample_incident.to_dict()
        assert data["code"] == "TEST_INCIDENT"
        assert data["severity"] == "high"
        assert data["scope"] == "provider"
        assert data["repeatability"] == "always"
        assert data["proofs"] == ["proof1", "proof2"]

    def test_is_recoverable_retryable(self):
        incident = ProductIncident(
            code="TEST",
            severity=IncidentSeverity.LOW,
            scope=IncidentScope.PROVIDER,
            proofs=["proof"],
            repeatability=IncidentRepeatability.ALWAYS,
            recommended_action="Retry",
            retryable=True,
            deferrable=False,
            correctable_under_supervision=False,
            terminal=False,
        )
        assert incident.is_recoverable()

    def test_is_recoverable_deferrable(self):
        incident = ProductIncident(
            code="TEST",
            severity=IncidentSeverity.LOW,
            scope=IncidentScope.PROVIDER,
            proofs=["proof"],
            repeatability=IncidentRepeatability.ALWAYS,
            recommended_action="Defer",
            retryable=False,
            deferrable=True,
            correctable_under_supervision=False,
            terminal=False,
        )
        assert incident.is_recoverable()

    def test_is_recoverable_supervised(self):
        incident = ProductIncident(
            code="TEST",
            severity=IncidentSeverity.LOW,
            scope=IncidentScope.PROVIDER,
            proofs=["proof"],
            repeatability=IncidentRepeatability.ALWAYS,
            recommended_action="Supervise",
            retryable=False,
            deferrable=False,
            correctable_under_supervision=True,
            terminal=False,
        )
        assert incident.is_recoverable()

    def test_is_not_recoverable(self):
        incident = ProductIncident(
            code="TEST",
            severity=IncidentSeverity.CRITICAL,
            scope=IncidentScope.GIT_CONFLICT,
            proofs=["proof"],
            repeatability=IncidentRepeatability.ALWAYS,
            recommended_action="Abort",
            retryable=False,
            deferrable=False,
            correctable_under_supervision=False,
            terminal=True,
        )
        assert not incident.is_recoverable()


class TestProductIncidentTaxonomy:
    @pytest.fixture
    def sample_taxonomy(self):
        incidents = [
            ProductIncident(
                code="INC1",
                severity=IncidentSeverity.HIGH,
                scope=IncidentScope.PROVIDER,
                proofs=["p1"],
                repeatability=IncidentRepeatability.ALWAYS,
                recommended_action="Action 1",
                retryable=True,
                deferrable=False,
                correctable_under_supervision=False,
                terminal=False,
            ),
            ProductIncident(
                code="INC2",
                severity=IncidentSeverity.LOW,
                scope=IncidentScope.PERMISSIONS,
                proofs=["p2"],
                repeatability=IncidentRepeatability.SOMETIMES,
                recommended_action="Action 2",
                retryable=False,
                deferrable=True,
                correctable_under_supervision=True,
                terminal=False,
            ),
        ]
        incident_map = {i.code: i for i in incidents}
        return ProductIncidentTaxonomy(
            schema_version="1.0.0", incidents=incidents, incident_map=incident_map
        )

    def test_taxonomy_creation(self, sample_taxonomy):
        assert sample_taxonomy.schema_version == "1.0.0"
        assert len(sample_taxonomy.incidents) == 2

    def test_taxonomy_empty_fails(self):
        with pytest.raises(ProductIncidentError):
            ProductIncidentTaxonomy(
                schema_version="1.0.0",
                incidents=[],
                incident_map={},
            )

    def test_get_incident(self, sample_taxonomy):
        incident = sample_taxonomy.get_incident("INC1")
        assert incident is not None
        assert incident.code == "INC1"

    def test_get_incident_not_found(self, sample_taxonomy):
        incident = sample_taxonomy.get_incident("NONEXISTENT")
        assert incident is None

    def test_taxonomy_to_dict(self, sample_taxonomy):
        data = sample_taxonomy.to_dict()
        assert data["schema_version"] == "1.0.0"
        assert len(data["incidents"]) == 2
        assert data["incidents"][0]["code"] == "INC1"
        assert data["incidents"][1]["code"] == "INC2"


class TestValidationFunctions:
    def test_validate_schema_version_valid(self):
        validate_schema_version("1.0.0")
        validate_schema_version("1.2.3")
        validate_schema_version("0.0.1")
        validate_schema_version("2.1.0")

    def test_validate_schema_version_invalid_format(self):
        with pytest.raises(ProductIncidentError):
            validate_schema_version("1")

        with pytest.raises(ProductIncidentError):
            validate_schema_version("1.0")

        with pytest.raises(ProductIncidentError):
            validate_schema_version("invalid")

    def test_validate_schema_version_non_numeric(self):
        with pytest.raises(ProductIncidentError):
            validate_schema_version("a.b.c")

    def test_validate_duplicate_codes_no_duplicates(self):
        incidents = [
            ProductIncident(
                code="INC1",
                severity=IncidentSeverity.HIGH,
                scope=IncidentScope.PROVIDER,
                proofs=["p"],
                repeatability=IncidentRepeatability.ALWAYS,
                recommended_action="Act",
                retryable=False,
                deferrable=False,
                correctable_under_supervision=False,
                terminal=False,
            ),
            ProductIncident(
                code="INC2",
                severity=IncidentSeverity.HIGH,
                scope=IncidentScope.PROVIDER,
                proofs=["p"],
                repeatability=IncidentRepeatability.ALWAYS,
                recommended_action="Act",
                retryable=False,
                deferrable=False,
                correctable_under_supervision=False,
                terminal=False,
            ),
        ]
        validate_duplicate_codes(incidents)

    def test_validate_duplicate_codes_with_duplicates(self):
        incidents = [
            ProductIncident(
                code="SAME",
                severity=IncidentSeverity.HIGH,
                scope=IncidentScope.PROVIDER,
                proofs=["p"],
                repeatability=IncidentRepeatability.ALWAYS,
                recommended_action="Act",
                retryable=False,
                deferrable=False,
                correctable_under_supervision=False,
                terminal=False,
            ),
            ProductIncident(
                code="SAME",
                severity=IncidentSeverity.HIGH,
                scope=IncidentScope.PROVIDER,
                proofs=["p"],
                repeatability=IncidentRepeatability.ALWAYS,
                recommended_action="Act",
                retryable=False,
                deferrable=False,
                correctable_under_supervision=False,
                terminal=False,
            ),
        ]
        with pytest.raises(ProductIncidentError):
            validate_duplicate_codes(incidents)


class TestLoadProductIncidents:
    @pytest.fixture
    def valid_incident_data(self):
        return {
            "schema_version": "1.0.0",
            "incidents": [
                {
                    "code": "TEST_INC",
                    "title": "Test Incident",
                    "description": "A test incident",
                    "severity": "high",
                    "scope": "provider",
                    "proofs": ["test proof"],
                    "repeatability": "always",
                    "recommended_action": "Test action",
                    "retryable": True,
                    "deferrable": False,
                    "correctable_under_supervision": False,
                    "terminal": False,
                }
            ],
        }

    def test_load_product_incidents_valid(self, valid_incident_data):
        taxonomy = load_product_incidents(valid_incident_data)
        assert taxonomy.schema_version == "1.0.0"
        assert len(taxonomy.incidents) == 1
        assert taxonomy.incidents[0].code == "TEST_INC"

    def test_load_product_incidents_invalid_severity(self, valid_incident_data):
        valid_incident_data["incidents"][0]["severity"] = "invalid"
        with pytest.raises(ProductIncidentError):
            load_product_incidents(valid_incident_data)

    def test_load_product_incidents_missing_required_field(self, valid_incident_data):
        del valid_incident_data["incidents"][0]["retryable"]
        with pytest.raises(ProductIncidentError):
            load_product_incidents(valid_incident_data)

    def test_load_product_incidents_from_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "incidents.json"
            data = {
                "schema_version": "1.0.0",
                "incidents": [
                    {
                        "code": "FILE_INC",
                        "title": "File Incident",
                        "description": "From file",
                        "severity": "medium",
                        "scope": "git_state",
                        "proofs": ["file proof"],
                        "repeatability": "sometimes",
                        "recommended_action": "Fix",
                        "retryable": False,
                        "deferrable": True,
                        "correctable_under_supervision": True,
                        "terminal": False,
                    }
                ],
            }
            with open(path, "w") as f:
                json.dump(data, f)
            taxonomy = load_product_incidents_from_file(path)
            assert taxonomy.incidents[0].code == "FILE_INC"

    def test_load_product_incidents_file_not_found(self):
        with pytest.raises(ProductIncidentError):
            load_product_incidents_from_file("/nonexistent/path.json")


class TestDefaultTaxonomy:
    def test_build_default_taxonomy(self):
        taxonomy = build_default_taxonomy()
        assert taxonomy.schema_version == "1.0.0"
        assert len(taxonomy.incidents) > 0

    def test_closed_incidents_list(self):
        assert len(CLOSED_INCIDENTS) > 0
        codes = {i.code for i in CLOSED_INCIDENTS}
        assert "PROVIDER_QUOTA_EXCEEDED" in codes
        assert "PERMISSION_DENIED" in codes
        assert "GIT_CONFLICT_DETECTED" in codes
        assert "INITIALIZATION_MUTATION_FAILED" in codes
        assert "WORKTREE_DIRTY" in codes
        assert "WORKTREE_INTERRUPTED" in codes
        assert "VALIDATION_TRANSITIVE_FAILED" in codes
        assert "CORRECTION_LIMIT_ORDINARY_EXCEEDED" in codes
        assert "CORRECTION_LIMIT_SUPERVISED_EXCEEDED" in codes
        assert "DEPENDENCY_MISSING" in codes
        assert "SPECIFICATION_MISSING" in codes
        assert "HUMAN_DECISION_REQUIRED" in codes

    def test_all_incidents_have_valid_structure(self):
        for incident in CLOSED_INCIDENTS:
            assert incident.code
            assert isinstance(incident.severity, IncidentSeverity)
            assert isinstance(incident.scope, IncidentScope)
            assert isinstance(incident.repeatability, IncidentRepeatability)
            assert incident.proofs
            assert isinstance(incident.proofs, list)
            assert all(isinstance(p, str) for p in incident.proofs)
            assert incident.recommended_action
            assert isinstance(incident.retryable, bool)
            assert isinstance(incident.deferrable, bool)
            assert isinstance(incident.correctable_under_supervision, bool)
            assert isinstance(incident.terminal, bool)

    def test_default_taxonomy_unique_codes(self):
        taxonomy = build_default_taxonomy()
        codes = [i.code for i in taxonomy.incidents]
        assert len(codes) == len(set(codes))

    def test_default_taxonomy_lookup(self):
        taxonomy = build_default_taxonomy()
        incident = taxonomy.get_incident("PROVIDER_QUOTA_EXCEEDED")
        assert incident is not None
        assert incident.severity == IncidentSeverity.HIGH
        assert incident.scope == IncidentScope.PROVIDER

    def test_default_taxonomy_serializable(self):
        taxonomy = build_default_taxonomy()
        data = taxonomy.to_dict()
        assert data["schema_version"] == "1.0.0"
        assert len(data["incidents"]) > 0
        assert all("code" in i for i in data["incidents"])
        assert all("severity" in i for i in data["incidents"])

    def test_incident_coverage_of_requirements(self):
        """Verify all scope areas from AC-R6-2 are covered."""
        taxonomy = build_default_taxonomy()
        scopes = {i.scope for i in taxonomy.incidents}

        # All required scopes from AC-R6-2
        required_scopes = {
            IncidentScope.PROVIDER,  # provider quotas
            IncidentScope.PERMISSIONS,  # permissions
            IncidentScope.GIT_STATE,  # divergent Git state
            IncidentScope.INITIALIZATION,  # initialization mutation
            IncidentScope.WORKTREE,  # interrupted/dirty worktree
            IncidentScope.VALIDATION,  # transitive validations
            IncidentScope.CORRECTION_LIMIT,  # correction caps
            IncidentScope.DEPENDENCY,  # missing dependency/spec
            IncidentScope.GIT_CONFLICT,  # git conflict
            IncidentScope.HUMAN_DECISION,  # human decision
        }
        assert required_scopes <= scopes, f"Missing scopes: {required_scopes - scopes}"

    def test_recoverable_classification(self):
        """Verify incidents have consistent recovery classification."""
        taxonomy = build_default_taxonomy()
        for incident in taxonomy.incidents:
            recovery_options = [
                incident.retryable,
                incident.deferrable,
                incident.correctable_under_supervision,
            ]
            # Verify at least one recovery option or explicitly terminal
            if not any(recovery_options) and not incident.terminal:
                pytest.fail(
                    f"Incident {incident.code} has no recovery path and is not terminal"
                )


class TestClosedTaxonomy:
    """Tests that verify the taxonomy is closed at the schema level."""

    @pytest.mark.skipif(
        not jsonschema,
        reason="jsonschema not available - schema validation skipped in code",
    )
    def test_schema_rejects_code_outside_enum(self):
        """Verify schema validation rejects incident codes outside the defined enum."""
        invalid_data = {
            "schema_version": "1.0.0",
            "incidents": [
                {
                    "code": "INVALID_CUSTOM_CODE",
                    "title": "Invalid Incident",
                    "description": "This code is not in the enum",
                    "severity": "high",
                    "scope": "provider",
                    "proofs": ["proof"],
                    "repeatability": "always",
                    "recommended_action": "Reject",
                    "retryable": False,
                    "deferrable": False,
                    "correctable_under_supervision": False,
                    "terminal": False,
                }
            ],
        }
        with pytest.raises(ProductIncidentError, match="JSON schema validation failed"):
            load_product_incidents(invalid_data)

    def test_schema_accepts_all_enum_codes(self):
        """Verify schema validation accepts all codes in the closed enum."""
        valid_codes = [
            "PROVIDER_QUOTA_EXCEEDED",
            "PROVIDER_RATE_LIMITED",
            "PROVIDER_UNAVAILABLE",
            "PERMISSION_DENIED",
            "GIT_DIVERGENT_STATE",
            "GIT_CONFLICT_DETECTED",
            "INITIALIZATION_MUTATION_FAILED",
            "WORKTREE_DIRTY",
            "WORKTREE_INTERRUPTED",
            "VALIDATION_TRANSITIVE_FAILED",
            "CORRECTION_LIMIT_ORDINARY_EXCEEDED",
            "CORRECTION_LIMIT_SUPERVISED_EXCEEDED",
            "DEPENDENCY_MISSING",
            "SPECIFICATION_MISSING",
            "HUMAN_DECISION_REQUIRED",
        ]
        for code in valid_codes:
            data = {
                "schema_version": "1.0.0",
                "incidents": [
                    {
                        "code": code,
                        "title": f"Incident {code}",
                        "description": f"Testing {code}",
                        "severity": "medium",
                        "scope": "provider",
                        "proofs": ["proof"],
                        "repeatability": "always",
                        "recommended_action": "Test",
                        "retryable": True,
                        "deferrable": False,
                        "correctable_under_supervision": False,
                        "terminal": False,
                    }
                ],
            }
            taxonomy = load_product_incidents(data)
            assert taxonomy.incidents[0].code == code

    def test_schema_enforces_code_uniqueness(self):
        """Verify schema structure and Python validation enforce code uniqueness."""
        duplicate_data = {
            "schema_version": "1.0.0",
            "incidents": [
                {
                    "code": "PROVIDER_QUOTA_EXCEEDED",
                    "title": "First",
                    "description": "First incident",
                    "severity": "high",
                    "scope": "provider",
                    "proofs": ["p1"],
                    "repeatability": "always",
                    "recommended_action": "Act1",
                    "retryable": True,
                    "deferrable": False,
                    "correctable_under_supervision": False,
                    "terminal": False,
                },
                {
                    "code": "PROVIDER_QUOTA_EXCEEDED",
                    "title": "Duplicate",
                    "description": "Duplicate incident",
                    "severity": "high",
                    "scope": "provider",
                    "proofs": ["p2"],
                    "repeatability": "always",
                    "recommended_action": "Act2",
                    "retryable": True,
                    "deferrable": False,
                    "correctable_under_supervision": False,
                    "terminal": False,
                },
            ],
        }
        with pytest.raises(ProductIncidentError, match="Duplicate incident codes"):
            load_product_incidents(duplicate_data)

    def test_closed_incidents_list_matches_schema_enum(self):
        """Verify CLOSED_INCIDENTS list matches the schema enum definition."""
        closed_codes = {i.code for i in CLOSED_INCIDENTS}
        expected_codes = {
            "PROVIDER_QUOTA_EXCEEDED",
            "PROVIDER_RATE_LIMITED",
            "PROVIDER_UNAVAILABLE",
            "PERMISSION_DENIED",
            "GIT_DIVERGENT_STATE",
            "GIT_CONFLICT_DETECTED",
            "INITIALIZATION_MUTATION_FAILED",
            "WORKTREE_DIRTY",
            "WORKTREE_INTERRUPTED",
            "VALIDATION_TRANSITIVE_FAILED",
            "CORRECTION_LIMIT_ORDINARY_EXCEEDED",
            "CORRECTION_LIMIT_SUPERVISED_EXCEEDED",
            "DEPENDENCY_MISSING",
            "SPECIFICATION_MISSING",
            "HUMAN_DECISION_REQUIRED",
        }
        assert (
            closed_codes == expected_codes
        ), f"Mismatch: {closed_codes - expected_codes} or {expected_codes - closed_codes}"

    @pytest.mark.skipif(
        not jsonschema,
        reason="jsonschema not available - schema validation skipped in code",
    )
    def test_schema_version_is_enforced(self):
        """Verify schema_version field is required and enforced."""
        data_without_version = {
            "incidents": [
                {
                    "code": "PROVIDER_QUOTA_EXCEEDED",
                    "title": "Test",
                    "description": "Test",
                    "severity": "high",
                    "scope": "provider",
                    "proofs": ["p"],
                    "repeatability": "always",
                    "recommended_action": "Act",
                    "retryable": True,
                    "deferrable": False,
                    "correctable_under_supervision": False,
                    "terminal": False,
                }
            ]
        }
        with pytest.raises(ProductIncidentError, match="JSON schema validation failed"):
            load_product_incidents(data_without_version)

    @pytest.mark.skipif(
        not jsonschema,
        reason="jsonschema not available - schema validation skipped in code",
    )
    def test_schema_rejects_additional_incident_properties(self):
        """Verify schema rejects additional properties on incident objects."""
        data_with_extra_props = {
            "schema_version": "1.0.0",
            "incidents": [
                {
                    "code": "PROVIDER_QUOTA_EXCEEDED",
                    "title": "Test",
                    "description": "Test",
                    "severity": "high",
                    "scope": "provider",
                    "proofs": ["p"],
                    "repeatability": "always",
                    "recommended_action": "Act",
                    "retryable": True,
                    "deferrable": False,
                    "correctable_under_supervision": False,
                    "terminal": False,
                    "extra_property": "should_fail",
                }
            ],
        }
        with pytest.raises(ProductIncidentError, match="JSON schema validation failed"):
            load_product_incidents(data_with_extra_props)
