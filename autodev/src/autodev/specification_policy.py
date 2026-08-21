from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore


COMMIT_HASH_PATTERN = re.compile(r"^[a-f0-9]{7,40}$")


class SpecificationValidationError(RuntimeError):
    """Error during specification validation or policy enforcement."""


class SpecificationPolicy(str, Enum):
    APPROVED_ONLY = "approved-only"
    DRAFT = "draft"
    AUTONOMOUS = "autonomous"


class ValidationStatus(str, Enum):
    APPROVED = "approved"
    DRAFT = "draft"
    REJECTED = "rejected"
    PENDING_HUMAN = "pending-human"


@dataclass(frozen=True)
class SpecificationMetadata:
    source: str
    prompt: str | None
    commit: str
    validation_status: ValidationStatus
    validated_at: str | None = None
    validated_by: str | None = None
    ambiguities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "prompt": self.prompt,
            "commit": self.commit,
            "validation_status": self.validation_status.value,
            "validated_at": self.validated_at,
            "validated_by": self.validated_by,
            "ambiguities": self.ambiguities,
        }

    def immutable_hash(self) -> str:
        content = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass(frozen=True)
class SpecificationValidationResult:
    feature_id: str
    specification_path: str
    metadata: SpecificationMetadata
    is_valid: bool
    is_usable: bool
    reason: str
    request_human: bool = False
    metadata_hash: str = ""
    specification_content: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "specification_path": self.specification_path,
            "metadata": self.metadata.to_dict(),
            "is_valid": self.is_valid,
            "is_usable": self.is_usable,
            "reason": self.reason,
            "request_human": self.request_human,
            "metadata_hash": self.metadata_hash,
            "specification_content": self.specification_content,
        }


def _read_specification_content(
    spec_file: Path | None, spec_content: str | None = None
) -> str | None:
    if spec_content is not None:
        return spec_content
    if spec_file and spec_file.exists():
        with open(spec_file, encoding="utf-8") as f:
            return f.read()
    return None


def _normalize_spec_line(line: str) -> str:
    normalized = re.sub(r"^\s*[-*]\s*", "", line.strip())
    normalized = re.sub(r"^[A-Z]{1,4}\d+\s*:\s*", "", normalized)
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized.lower())
    stopwords = {
        "the",
        "a",
        "an",
        "le",
        "la",
        "les",
        "de",
        "des",
        "du",
        "and",
        "or",
        "et",
        "ou",
        "must",
        "not",
        "required",
        "optional",
        "enabled",
        "disabled",
        "accept",
        "reject",
        "write",
        "read",
        "only",
    }
    tokens = [token for token in normalized.split() if token not in stopwords]
    return " ".join(tokens)


def _detect_structured_contradictions(content: str) -> list[str]:
    contradiction_patterns = [
        (r"\bmust\b.*\bmust not\b|\bmust not\b.*\bmust\b", "Contradictory requirements"),
        (
            r"\b(required|mandatory)\b.*\boptional\b|\boptional\b.*\b(required|mandatory)\b",
            "Contradictory requirements",
        ),
        (r"\benabled\b.*\bdisabled\b|\bdisabled\b.*\benabled\b", "Contradictory requirements"),
        (r"\baccept\b.*\breject\b|\breject\b.*\baccept\b", "Contradictory requirements"),
        (r"\bread-only\b.*\bwrite\b|\bwrite\b.*\bread-only\b", "Contradictory requirements"),
        (r"\ballow\b.*\bdeny\b|\bdeny\b.*\ballow\b", "Contradictory requirements"),
    ]

    issues: list[str] = []
    lowered_lines = [line.strip().lower() for line in content.splitlines() if line.strip()]

    for line in lowered_lines:
        for pattern, message in contradiction_patterns:
            if re.search(pattern, line):
                issues.append(message)
                break

    polarity_pairs = [
        (("must", "required", "mandatory", "enabled", "accept", "allow"), ("must not", "optional", "disabled", "reject", "deny")),
    ]
    normalized_lines = []
    for line in lowered_lines:
        if not line.startswith(("-", "*")):
            continue
        normalized_lines.append((line, _normalize_spec_line(line)))

    for index, (left_line, left_key) in enumerate(normalized_lines):
        if not left_key:
            continue
        for right_line, right_key in normalized_lines[index + 1 :]:
            if left_key != right_key:
                continue
            for positive_terms, negative_terms in polarity_pairs:
                left_positive = any(term in left_line for term in positive_terms)
                left_negative = any(term in left_line for term in negative_terms)
                right_positive = any(term in right_line for term in positive_terms)
                right_negative = any(term in right_line for term in negative_terms)
                if (left_positive and right_negative) or (left_negative and right_positive):
                    issues.append("Contradictory requirements")
                    break

    return list(dict.fromkeys(issues))


def _parse_required_sections(content: str) -> dict[str, list[str] | None]:
    section_patterns = {
        "objectif": re.compile(
            r"^(?:#+\s*)?(objectif|objective)(?:\s*:\s*(.*))?$",
            re.IGNORECASE,
        ),
        "exigences": re.compile(
            r"^(?:#+\s*)?(exigence|exigences|requirement|requirements)(?:\s*:\s*(.*))?$",
            re.IGNORECASE,
        ),
        "critères d'acceptation": re.compile(
            r"^(?:#+\s*)?(crit[eè]res?\s+d['’]acceptation|acceptance criteria)(?:\s*:\s*(.*))?$",
            re.IGNORECASE,
        ),
    }
    sections: dict[str, list[str] | None] = {name: None for name in section_patterns}
    current_section: str | None = None

    for raw_line in content.splitlines():
        stripped_line = raw_line.strip()
        matched_section = None
        inline_content = ""

        for section_name, pattern in section_patterns.items():
            match = pattern.match(stripped_line)
            if match:
                matched_section = section_name
                inline_content = (match.group(2) or "").strip()
                break

        if matched_section is not None:
            current_section = matched_section
            if sections[current_section] is None:
                sections[current_section] = []
            if inline_content:
                sections[current_section].append(inline_content)
            continue

        if current_section is not None and stripped_line:
            if sections[current_section] is None:
                sections[current_section] = []
            sections[current_section].append(stripped_line)

    return sections


def _normalize_placeholder_text(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", ascii_value.lower())).strip()


def _is_placeholder_entry(section_name: str, candidate: str) -> bool:
    normalized = _normalize_placeholder_text(candidate)
    placeholders = {
        "objectif": {
            "objectif",
            "objective",
            "goal",
            "purpose",
            "description",
            "a definir",
            "a completer",
            "a renseigner",
            "todo",
            "tbd",
        },
        "exigences": {
            "exigence",
            "exigences",
            "requirement",
            "requirements",
            "regle metier",
            "regles metier",
            "a definir",
            "a completer",
            "a renseigner",
            "todo",
            "tbd",
        },
        "critères d'acceptation": {
            "critere d acceptation",
            "criteres d acceptation",
            "acceptance criterion",
            "acceptance criteria",
            "a definir",
            "a completer",
            "a renseigner",
            "todo",
            "tbd",
        },
    }
    return normalized in placeholders.get(section_name, set())


def _extract_substantive_entries(section_name: str, lines: list[str]) -> list[str]:
    entries: list[str] = []
    for line in lines:
        candidate = re.sub(r"^\s*[-*]\s*", "", line.strip())
        candidate = re.sub(r"^[A-Z]{1,4}\d+\s*:\s*", "", candidate)
        candidate = candidate.strip(" :.-")
        if re.search(r"[A-Za-zÀ-ÿ0-9]", candidate) and not _is_placeholder_entry(
            section_name, candidate
        ):
            entries.append(candidate)
    return entries


def _build_minimal_draft_content(
    feature_id: str,
    specification_path: str,
    prompt: str,
) -> str:
    cleaned_prompt = " ".join(prompt.split())
    return (
        "## Objectif\n"
        f"Formaliser un premier brouillon exploitable pour {feature_id} à partir de la demande "
        f"suivante: {cleaned_prompt}.\n\n"
        "## Exigences\n"
        f"- R1: Décrire précisément la fonctionnalité attendue pour {feature_id} dans "
        f"la spécification `{specification_path}`.\n"
        "- R2: Rendre explicites les règles métier, contraintes et données impactées afin "
        "qu'une revue humaine puisse compléter le périmètre sans ambiguïté.\n\n"
        "## Critères d'acceptation\n"
        "- AC1: Le brouillon contient un objectif lisible, des exigences identifiables et "
        "des critères vérifiables avant la revue humaine.\n"
        "- AC2: La planification reste bloquée tant qu'un humain n'a pas approuvé ce brouillon.\n"
    )


def validate_specification_content(spec_file: Path | None, spec_content: str | None = None) -> tuple[bool, list[str]]:
    """
    Validate specification content against proprietary format requirements.

    Checks for required sections (objectives, requirements, acceptance criteria).
    Returns (is_valid, list_of_missing_or_invalid_items).
    """
    issues = []

    if spec_file is None and spec_content is None:
        return False, ["No specification file or content provided"]

    content = _read_specification_content(spec_file, spec_content) or ""

    if not content.strip():
        return False, ["No specification content"]

    sections = _parse_required_sections(content)
    concrete_requirements = {
        "objectif": "concrete objective",
        "exigences": "concrete requirement",
        "critères d'acceptation": "concrete acceptance criterion",
    }

    for section_name, requirement_label in concrete_requirements.items():
        raw_lines = sections.get(section_name)
        if raw_lines is None:
            issues.append(f"Missing required section: {section_name}")
            continue
        if not _extract_substantive_entries(section_name, raw_lines):
            issues.append(
                f"Section '{section_name}' must contain at least one {requirement_label}"
            )

    issues.extend(_detect_structured_contradictions(content))

    issues = list(dict.fromkeys(issues))
    return len(issues) == 0, issues

def validate_specification_for_policy(
    feature_id: str,
    specification_path: str,
    policy: str | SpecificationPolicy,
    spec_file: Path | None = None,
    existing_metadata: SpecificationMetadata | None = None,
    prompt: str | None = None,
    current_commit: str | None = None,
    spec_content: str | None = None,
) -> SpecificationValidationResult:
    """
    Validate a specification against the requested policy.

    Args:
        feature_id: Feature identifier
        specification_path: Path to specification file
        policy: One of 'approved-only', 'draft', 'autonomous'
        spec_file: Optional Path to specification file to check if it exists
        existing_metadata: Optional existing metadata for reused specs
        prompt: Optional prompt that generated the spec (for draft/autonomous)
        current_commit: Optional current Git commit hash
        spec_content: Optional specification content to validate (for draft/autonomous)

    Returns:
        SpecificationValidationResult with validation outcome

    Raises:
        SpecificationValidationError: If policy is invalid
    """
    if isinstance(policy, str):
        try:
            policy_enum = SpecificationPolicy(policy)
        except ValueError:
            valid_policies = {p.value for p in SpecificationPolicy}
            raise SpecificationValidationError(
                f"Invalid specification_policy '{policy}': must be one of {valid_policies}"
            )
    else:
        policy_enum = policy

    current_time = datetime.now(timezone.utc).isoformat()
    commit = _require_valid_current_commit(current_commit)

    if policy_enum == SpecificationPolicy.APPROVED_ONLY:
        return _validate_approved_only(
            feature_id, specification_path, spec_file, existing_metadata, commit
        )
    elif policy_enum == SpecificationPolicy.DRAFT:
        return _validate_draft(
            feature_id, specification_path, spec_file, prompt, commit, current_time, spec_content
        )
    elif policy_enum == SpecificationPolicy.AUTONOMOUS:
        return _validate_autonomous(
            feature_id, specification_path, spec_file, prompt, commit, current_time, spec_content
        )
    else:
        raise SpecificationValidationError(f"Unknown policy: {policy_enum}")


def _require_valid_current_commit(current_commit: str | None) -> str:
    commit = (current_commit or "").strip()
    if not COMMIT_HASH_PATTERN.fullmatch(commit):
        raise SpecificationValidationError(
            f"Specification validation requires a valid Git commit hash, got {commit or '<empty>'}"
        )
    return commit


def _validate_approved_only(
    feature_id: str,
    specification_path: str,
    spec_file: Path | None,
    existing_metadata: SpecificationMetadata | None,
    commit: str,
) -> SpecificationValidationResult:
    """Validate spec for approved-only policy: must exist and be pre-validated."""
    spec_path = Path(specification_path)

    if not existing_metadata:
        return SpecificationValidationResult(
            feature_id=feature_id,
            specification_path=specification_path,
            metadata=SpecificationMetadata(
                source="none",
                prompt=None,
                commit=commit,
                validation_status=ValidationStatus.REJECTED,
                ambiguities=["No metadata: specification not found or not validated"],
            ),
            is_valid=False,
            is_usable=False,
            reason="approved-only policy requires pre-existing validated specification",
            request_human=True,
        )

    if existing_metadata.validation_status != ValidationStatus.APPROVED:
        return SpecificationValidationResult(
            feature_id=feature_id,
            specification_path=specification_path,
            metadata=existing_metadata,
            is_valid=False,
            is_usable=False,
            reason=f"approved-only policy requires APPROVED status, got {existing_metadata.validation_status.value}",
            request_human=True,
        )

    if existing_metadata.ambiguities:
        return SpecificationValidationResult(
            feature_id=feature_id,
            specification_path=specification_path,
            metadata=existing_metadata,
            is_valid=False,
            is_usable=False,
            reason="approved-only specification has unresolved ambiguities",
            request_human=True,
        )

    metadata_hash = existing_metadata.immutable_hash()

    return SpecificationValidationResult(
        feature_id=feature_id,
        specification_path=specification_path,
        metadata=existing_metadata,
        is_valid=True,
        is_usable=True,
        reason="approved-only specification is valid and ready for planning",
        request_human=False,
        metadata_hash=metadata_hash,
    )


def _validate_draft(
    feature_id: str,
    specification_path: str,
    spec_file: Path | None,
    prompt: str | None,
    commit: str,
    current_time: str,
    spec_content: str | None = None,
) -> SpecificationValidationResult:
    """Validate spec for draft policy: generate/receive draft, validate content, require human approval."""
    effective_prompt = prompt or (
        f"document origin: {specification_path}; draft review required for feature {feature_id}"
    )

    issues: list[str] = []
    is_content_structurally_valid = False
    resolved_content = _read_specification_content(spec_file, spec_content)

    if resolved_content is None and effective_prompt is not None:
        resolved_content = _build_minimal_draft_content(
            feature_id=feature_id,
            specification_path=specification_path,
            prompt=effective_prompt,
        )

    if resolved_content is None:
        issues = ["No specification content"]
    else:
        is_content_structurally_valid, content_issues = validate_specification_content(
            None, resolved_content
        )
        if not is_content_structurally_valid:
            issues = content_issues

    ambiguities = [
        "Draft specification requires explicit human validation before planning"
    ]
    if issues:
        ambiguities.extend(issues)

    metadata = SpecificationMetadata(
        source=f"generated:draft",
        prompt=effective_prompt or "unknown",
        commit=commit,
        validation_status=ValidationStatus.PENDING_HUMAN,
        validated_at=current_time,
        validated_by="draft-policy",
        ambiguities=ambiguities,
    )

    reason = "draft specification generated; waiting for human validation"
    if not is_content_structurally_valid:
        reason = f"draft specification has content issues: {'; '.join(issues)}"

    return SpecificationValidationResult(
        feature_id=feature_id,
        specification_path=specification_path,
        metadata=metadata,
        is_valid=is_content_structurally_valid,
        is_usable=False,
        reason=reason,
        request_human=True,
        metadata_hash=metadata.immutable_hash(),
        specification_content=resolved_content,
    )


def _validate_autonomous(
    feature_id: str,
    specification_path: str,
    spec_file: Path | None,
    prompt: str | None,
    commit: str,
    current_time: str,
    spec_content: str | None = None,
) -> SpecificationValidationResult:
    """Validate spec for autonomous policy: validate content by contract and detect structural issues."""
    resolved_content = _read_specification_content(spec_file, spec_content)
    if not prompt and resolved_content is None:
        ambiguities = ["No prompt provided for autonomous specification generation"]
        metadata = SpecificationMetadata(
            source="generated:autonomous",
            prompt="unknown",
            commit=commit,
            validation_status=ValidationStatus.DRAFT,
            ambiguities=ambiguities,
        )
        return SpecificationValidationResult(
            feature_id=feature_id,
            specification_path=specification_path,
            metadata=metadata,
            is_valid=False,
            is_usable=False,
            reason="autonomous specification requires prompt for contract validation",
            request_human=True,
            metadata_hash=metadata.immutable_hash(),
            specification_content=resolved_content,
        )

    effective_prompt = prompt
    if effective_prompt is None and spec_file is not None:
        effective_prompt = (
            f"document origin: {specification_path}; validate existing specification "
            f"content for feature {feature_id}"
        )

    all_ambiguities: list[str] = []

    if effective_prompt:
        all_ambiguities.extend(_detect_ambiguities(effective_prompt))

    if resolved_content is not None:
        is_content_valid, content_issues = validate_specification_content(None, resolved_content)
        all_ambiguities.extend(content_issues)
    else:
        is_content_valid = False
        all_ambiguities.append("No specification content")

    all_ambiguities = list(dict.fromkeys(all_ambiguities))

    if all_ambiguities:
        metadata = SpecificationMetadata(
            source="generated:autonomous",
            prompt=effective_prompt,
            commit=commit,
            validation_status=ValidationStatus.DRAFT,
            ambiguities=all_ambiguities,
        )
        return SpecificationValidationResult(
            feature_id=feature_id,
            specification_path=specification_path,
            metadata=metadata,
            is_valid=False,
            is_usable=False,
            reason=f"autonomous specification failed contract validation: {'; '.join(all_ambiguities)}",
            request_human=True,
            metadata_hash=metadata.immutable_hash(),
            specification_content=resolved_content,
        )

    metadata = SpecificationMetadata(
        source="generated:autonomous",
        prompt=effective_prompt,
        commit=commit,
        validation_status=ValidationStatus.APPROVED,
        validated_at=current_time,
        validated_by="autonomous-contract",
        ambiguities=[],
    )

    return SpecificationValidationResult(
        feature_id=feature_id,
        specification_path=specification_path,
        metadata=metadata,
        is_valid=True,
        is_usable=True,
        reason="autonomous specification validated by contract; no ambiguities detected",
        request_human=False,
        metadata_hash=metadata.immutable_hash(),
        specification_content=resolved_content,
    )


def _detect_ambiguities(prompt: str) -> list[str]:
    """
    Detect common ambiguities and contradictions in a specification prompt.

    Returns list of detected ambiguities, empty if none found.
    """
    ambiguities = []

    ambiguity_patterns = [
        (r"\btbd\b", "To-be-determined requirement found"),
        (r"\btodo\b", "Incomplete requirement found"),
        (r"\bmaybe\b", "Uncertain requirement (maybe) found"),
        (r"\bpossibly\b", "Uncertain requirement (possibly) found"),
        (r"\bunclear\b", "Unclear requirement noted"),
        (r"\bnot sure\b", "Uncertain specification found"),
        (r"\?", "Question mark in specification"),
    ]

    prompt_lower = prompt.lower()
    for pattern, message in ambiguity_patterns:
        if re.search(pattern, prompt_lower):
            ambiguities.append(message)

    if len(prompt) < 50:
        ambiguities.append("Specification prompt is too short to be meaningful")

    contradiction_patterns = [
        (r"must\s+.*\bnot\b", "Contradictory requirements (must ... not)"),
        (r"required\s+.*\soptional", "Contradictory requirements (required vs optional)"),
        (r"mandatory\s+.*\soptional", "Contradictory requirements (mandatory vs optional)"),
        (r"must\s+.*\soptional", "Contradictory requirements (must vs optional)"),
        (r"optional\s+.*\bmust\b", "Contradictory requirements (optional vs must)"),
        (r"cannot\s+.*\bmust\b", "Contradictory requirements (cannot ... must)"),
        (r"disabled\s+.*\senabled", "Contradictory state requirements"),
        (r"read-only\s+.*\swrite", "Contradictory access requirements"),
        (r"reject.*\saccept", "Contradictory requirements (reject vs accept)"),
        (r"accept.*\sreject", "Contradictory requirements (accept vs reject)"),
    ]

    for pattern, message in contradiction_patterns:
        if re.search(pattern, prompt_lower):
            ambiguities.append(message)

    duplicate_id_pattern = r"(requirement|criteria|spec|r\d+)[\s\-_]*(:\s*.*?)(?=requirement|criteria|spec|r\d+|$)"
    matches = list(re.finditer(duplicate_id_pattern, prompt_lower, re.MULTILINE))
    if len(matches) >= 2:
        ids_seen = {}
        for match in matches:
            identifier = match.group(1).strip()
            if identifier in ids_seen:
                ids_seen[identifier] += 1
            else:
                ids_seen[identifier] = 1
        for identifier, count in ids_seen.items():
            if count > 1:
                ambiguities.append(f"Duplicate requirement identifier '{identifier}' found {count} times")

    return ambiguities


def validate_json_schema_for_metadata(
    metadata_dict: dict[str, Any], schema_path: Path
) -> None:
    """Validate metadata against JSON schema."""
    if jsonschema is None:
        return

    if not schema_path.exists():
        raise SpecificationValidationError(f"Schema file not found: {schema_path}")

    with open(schema_path) as f:
        schema = json.load(f)

    try:
        jsonschema.validate(metadata_dict, schema)
    except jsonschema.ValidationError as e:
        raise SpecificationValidationError(
            f"JSON schema validation failed for specification metadata: {e.message}"
        ) from e
    except jsonschema.SchemaError as e:
        raise SpecificationValidationError(
            f"Invalid JSON schema for specification metadata: {e.message}"
        ) from e


def enforce_specification_gate(result: SpecificationValidationResult) -> None:
    """
    Enforce specification validation gate: block planning if not usable.

    Raises:
        SpecificationValidationError: If specification is not usable for planning
    """
    if not result.is_usable:
        msg = f"Specification gate violation for '{result.feature_id}': {result.reason}"
        if result.request_human:
            msg += " — REQUEST_HUMAN intervention required"
        raise SpecificationValidationError(msg)
