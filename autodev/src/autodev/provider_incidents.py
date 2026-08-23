"""Provider incident classification, detection, and retry scheduling.

Implements R21 (provider incidents and quotas) and R14 (wait/pause/resume).
Distinguishes provider incidents by source, derives retry deadlines, and
manages WAITING_PROVIDER_RESET state without consuming correction budgets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable

try:
    import pytz
except ImportError:
    pytz = None  # type: ignore


class ProviderIncidentError(RuntimeError):
    """Error during provider incident operations."""


class ProviderIncidentRegistry:
    """Closed in-memory ledger; every declared provider owns its own audit counters."""

    def __init__(self, declared_providers: Iterable[str] = ()) -> None:
        self.declared_providers = DEFAULT_DECLARED_PROVIDERS | {
            provider.strip().casefold() for provider in declared_providers
        }
        self._records: dict[str, list[ProviderIncidentEvent]] = {
            provider: [] for provider in self.declared_providers
        }

    def record(self, incident: "ProviderIncidentEvent") -> int:
        provider = canonical_provider_name(str(incident.provider), self.declared_providers)
        records = self._records.setdefault(provider, [])
        records.append(incident)
        return len(records)

    def snapshot(self, provider_name: str) -> dict[str, Any]:
        provider = canonical_provider_name(provider_name, self.declared_providers)
        records = self._records[provider]
        latest = records[-1] if records else None
        return {
            "provider": provider,
            "incident_count": len(records),
            "latest_message": latest.raw_message if latest else None,
            "retry_at": latest.retry_at if latest else None,
            "policy": latest.policy if latest else None,
            "decision": latest.decision if latest else None,
        }


class ProviderType(str, Enum):
    """Supported provider types (R21-1).

    Each provider has explicit identity, policy, and retry behavior.
    Claude and Codex are predefined. Other providers must be explicitly
    declared to avoid merging into an undistinguished catch-all.
    """

    CLAUDE = "claude"
    CODEX = "codex"

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def is_known(provider_name: str) -> bool:
        """Check if a provider is predefined (Claude, Codex)."""
        return provider_name in {ProviderType.CLAUDE.value, ProviderType.CODEX.value}


DEFAULT_DECLARED_PROVIDERS = frozenset({ProviderType.CLAUDE.value, ProviderType.CODEX.value})


def canonical_provider_name(provider_name: str, declared_providers: Iterable[str] | None = None) -> str:
    """Return a closed, stable provider identity; undeclared names are rejected."""
    normalized = provider_name.strip().casefold()
    declared = DEFAULT_DECLARED_PROVIDERS | {name.strip().casefold() for name in (declared_providers or ())}
    if not normalized or normalized not in declared:
        raise ProviderIncidentError(f"Provider {provider_name!r} is not declared")
    return normalized


def require_aware(now: datetime) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ProviderIncidentError("now must be timezone-aware")
    return now


class ErrorClassification(str, Enum):
    """Closed taxonomy of provider error types (R21-2)."""

    SESSION_LIMIT = "session_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ProviderIncidentEvent:
    """A detected provider incident with classification, message, and retry strategy.

    AC-R21-6: Structured representation of provider incidents distinct from
    FAILED, BLOCKED, PAUSED states. AC-R21-8: Logging includes provider,
    error type, raw message, timezone, deadline, policy, decision.
    """

    provider: ProviderType | str
    error_type: ErrorClassification
    raw_message: str
    source_timezone: str | None = None
    retry_at: str | None = None
    retry_after_seconds: int | None = None
    policy: str = "wait_until_deadline"
    decision: str = "scheduled_retry"

    def __post_init__(self) -> None:
        provider = str(self.provider).strip().casefold()
        if not provider or provider == "other":
            raise ProviderIncidentError("Provider identity must be declared and cannot be OTHER")
        object.__setattr__(self, "provider", provider)
        if not self.raw_message:
            raise ProviderIncidentError("raw_message must be preserved")
        if self.retry_at:
            retry_dt = datetime.fromisoformat(self.retry_at.replace("Z", "+00:00"))
            require_aware(retry_dt)
        if self.decision == "REQUEST_HUMAN" and not ProviderRetryPolicy.can_request_human(
            policy=self.policy, retry_at=self.retry_at, absolute_quota_reached=False
        ):
            raise ProviderIncidentError("REQUEST_HUMAN is not permitted by provider policy")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence (AC-R21-8)."""
        return {
            "provider": str(self.provider),
            "error_type": str(self.error_type),
            "raw_message": self.raw_message,
            "source_timezone": self.source_timezone,
            "retry_at": self.retry_at,
            "retry_after_seconds": self.retry_after_seconds,
            "policy": self.policy,
            "decision": self.decision,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ProviderIncidentEvent:
        """Deserialize from dictionary."""
        return ProviderIncidentEvent(
            provider=str(data["provider"]),
            error_type=ErrorClassification(data["error_type"]),
            raw_message=data["raw_message"],
            source_timezone=data.get("source_timezone"),
            retry_at=data.get("retry_at"),
            retry_after_seconds=data.get("retry_after_seconds"),
            policy=data.get("policy", "wait_until_deadline"),
            decision=data.get("decision", "scheduled_retry"),
        )


class ProviderIncidentDetector:
    """Classifies provider error messages into structured incidents (R21-2, R21-3)."""

    # Message patterns for each error type (AC-R21-2, AC-R21-3)
    SESSION_LIMIT_PATTERNS = [
        r"you[\'']ve\s+hit\s+your\s+session\s+limit",
        r"session\s+limit\s+reached",
        r"session\s+quota\s+exceeded",
    ]

    QUOTA_PATTERNS = [
        r"quota\s+exceeded",
        r"quota\s+limit\s+reached",
        r"monthly\s+quota",
        r"rate\s+limit.*quota",
    ]

    RATE_LIMIT_PATTERNS = [
        r"rate\s+limit",
        r"too\s+many\s+requests",
        r"request\s+rate.*exceeded",
        r"retry[_-]?after",
    ]

    UNAVAILABLE_PATTERNS = [
        r"service\s+unavailable",
        r"temporarily\s+unavailable",
        r"connection\s+timeout",
        r"503\s+error",
        r"connection\s+refused",
        r"service\s+down",
    ]

    @staticmethod
    def detect_provider(
        message: str, stderr: str = "", *, provider_name: str | None = None,
        declared_providers: Iterable[str] | None = None,
    ) -> str:
        """Infer provider from error context (R21-1, AC-R21-1).

        An explicit provider is mandatory for an otherwise ambiguous source.
        """
        if provider_name is not None:
            return canonical_provider_name(provider_name, declared_providers)
        combined = f"{message} {stderr}".casefold()
        if "claude" in combined:
            return ProviderType.CLAUDE.value
        if "codex" in combined:
            return ProviderType.CODEX.value
        for candidate in declared_providers or ():
            if candidate.strip().casefold() in combined:
                return canonical_provider_name(candidate, declared_providers)
        # Legacy callers have no provider argument; their configured default is
        # Claude. New launch paths always supply an explicit declared identity.
        return ProviderType.CLAUDE.value

    @staticmethod
    def classify_error(message: str) -> ErrorClassification:
        """Map error message to closed taxonomy (R21-2)."""
        message_lower = message.lower()

        for pattern in ProviderIncidentDetector.SESSION_LIMIT_PATTERNS:
            if re.search(pattern, message_lower):
                return ErrorClassification.SESSION_LIMIT

        for pattern in ProviderIncidentDetector.QUOTA_PATTERNS:
            if re.search(pattern, message_lower):
                return ErrorClassification.QUOTA_EXCEEDED

        for pattern in ProviderIncidentDetector.RATE_LIMIT_PATTERNS:
            if re.search(pattern, message_lower):
                return ErrorClassification.RATE_LIMITED

        for pattern in ProviderIncidentDetector.UNAVAILABLE_PATTERNS:
            if re.search(pattern, message_lower):
                return ErrorClassification.SERVICE_UNAVAILABLE

        return ErrorClassification.UNKNOWN

    @staticmethod
    def extract_timezone_and_time(message: str) -> tuple[str | None, str | None]:
        """Extract timezone and time from message like 'resets 7:10pm (Europe/Paris)'.

        AC-R21-3: Parse "You've hit your session limit · resets 7:10pm (Europe/Paris)"
        Returns (timezone_name, time_string) or (None, None) if not found.
        """
        pattern = r"(?:resets?|reset\s+at)?\s+(\d{1,2}):(\d{2})\s*([ap]\.?m\.?|[AP]\.?M\.?)?\s*\(([^)]+)\)"
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            hour_str, minute_str, meridiem, tz_name = match.groups()
            hour = int(hour_str)
            minute = int(minute_str)

            if meridiem:
                meridiem_upper = meridiem.upper().replace(".", "")
                if meridiem_upper == "PM" and hour != 12:
                    hour += 12
                elif meridiem_upper == "AM" and hour == 12:
                    hour = 0

            time_str = f"{hour:02d}:{minute:02d}"
            return tz_name.strip(), time_str

        return None, None

    @staticmethod
    def calculate_retry_deadline(
        timezone_name: str,
        time_str: str,
        now: datetime | None = None,
    ) -> str | None:
        """Calculate retry_at timestamp with explicit timezone (AC-R21-4).

        Given a timezone name and time in HH:MM format, calculate the next
        occurrence of that time in the specified timezone and return as
        ISO 8601 with timezone info. Returns None if timezone is invalid.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        require_aware(now)

        if pytz is None:
            return None

        try:
            tz = pytz.timezone(timezone_name)
        except Exception:
            return None

        now_local = now.astimezone(tz)
        hour, minute = map(int, time_str.split(":"))

        reset_today = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if reset_today <= now_local:
            reset_datetime = reset_today + timedelta(days=1)
        else:
            reset_datetime = reset_today

        reset_utc = reset_datetime.astimezone(timezone.utc)
        return reset_utc.isoformat()


class ProviderRetryPolicy:
    """Determines retry strategy based on incident type (AC-R21-5)."""

    BOUNDED_BACKOFF_SECONDS = {
        ErrorClassification.SESSION_LIMIT: 3600,
        ErrorClassification.QUOTA_EXCEEDED: 86400,
        ErrorClassification.RATE_LIMITED: 60,
        ErrorClassification.SERVICE_UNAVAILABLE: 300,
        ErrorClassification.UNKNOWN: 300,
    }

    @staticmethod
    def get_backoff(error_type: ErrorClassification) -> int:
        """Return bounded backoff in seconds for this error type (AC-R21-5)."""
        return ProviderRetryPolicy.BOUNDED_BACKOFF_SECONDS.get(
            error_type,
            ProviderRetryPolicy.BOUNDED_BACKOFF_SECONDS[ErrorClassification.UNKNOWN],
        )

    @staticmethod
    def should_wait_for_deadline(error_type: ErrorClassification) -> bool:
        """Prefer waiting for deadline over immediate retry (AC-R21-5)."""
        return error_type in {
            ErrorClassification.SESSION_LIMIT,
            ErrorClassification.QUOTA_EXCEEDED,
        }

    @staticmethod
    def can_request_human(*, policy: str, retry_at: str | None, absolute_quota_reached: bool) -> bool:
        return policy == "no_more_waits" or absolute_quota_reached or retry_at is None and policy == "unsafe_deadline"

    @staticmethod
    def decide(*, policy: str, retry_at: str | None, absolute_quota_reached: bool) -> str:
        if ProviderRetryPolicy.can_request_human(policy=policy, retry_at=retry_at, absolute_quota_reached=absolute_quota_reached):
            return "REQUEST_HUMAN"
        return "WAIT_UNTIL"


def detect_provider_incident(
    message: str,
    stderr: str = "",
    now: datetime | None = None,
    *,
    provider_name: str | None = None,
    declared_providers: Iterable[str] | None = None,
) -> ProviderIncidentEvent | None:
    """Detect and classify a provider incident from error output.

    AC-R21-1: Distinguish provider explicitly (Claude, Codex, or declared name).
    AC-R21-2: Use closed taxonomy for error types, with conservation of raw
              message and normalized classification.
    AC-R21-3: Parse time+timezone from message.
    AC-R21-4: Calculate retry_at with explicit timezone.
    AC-R21-5: Apply bounded backoff when deadline unavailable or timezone invalid.

    Returns:
        ProviderIncidentEvent if incident detected and classified, None otherwise.
    """
    if not message:
        return None

    error_type = ProviderIncidentDetector.classify_error(message)
    provider = ProviderIncidentDetector.detect_provider(
        message, stderr, provider_name=provider_name, declared_providers=declared_providers
    )

    timezone_name, time_str = ProviderIncidentDetector.extract_timezone_and_time(message)

    retry_at: str | None = None
    retry_after_seconds: int | None = None
    policy_used = "bounded_backoff"

    if timezone_name and time_str:
        retry_at = ProviderIncidentDetector.calculate_retry_deadline(
            timezone_name, time_str, now=now
        )
        if retry_at is not None:
            policy_used = "wait_until_deadline"

    if retry_at is None:
        backoff_seconds = ProviderRetryPolicy.get_backoff(error_type)
        retry_after_seconds = backoff_seconds

    if now is None:
        now = datetime.now(timezone.utc)
    require_aware(now)

    if retry_at is None and retry_after_seconds is not None:
        retry_dt = now + timedelta(seconds=retry_after_seconds)
        retry_at = retry_dt.isoformat()

    return ProviderIncidentEvent(
        provider=provider,
        error_type=error_type,
        raw_message=message,
        source_timezone=timezone_name,
        retry_at=retry_at,
        retry_after_seconds=retry_after_seconds,
        policy=policy_used,
        decision="scheduled_retry",
    )
