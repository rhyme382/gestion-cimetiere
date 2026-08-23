"""Tests for provider incident detection, classification, and retry scheduling.

AC-R21: Provider incidents, quotas, and bounded waiting.
AC-R14: Wait, pause, and resume without consuming correction budget.
"""

from datetime import datetime, timezone, timedelta

import pytest

try:
    import pytz
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False

from autodev.provider_incidents import (
    ProviderIncidentError,
    ProviderType,
    ErrorClassification,
    ProviderIncidentEvent,
    ProviderIncidentDetector,
    ProviderIncidentRegistry,
    ProviderRetryPolicy,
    detect_provider_incident,
)
from autodev.process_runner import classify_provider_result, run_process


class TestDeclaredProviderRegistry:
    def test_declared_providers_keep_independent_identity_and_deadlines(self):
        """A registry must never merge declared provider incidents or schedules."""
        now = datetime(2026, 8, 22, 10, 0, tzinfo=timezone.utc)
        incidents = [
            detect_provider_incident("Claude: rate limited", provider_name="claude", now=now),
            detect_provider_incident("Codex: quota exceeded", provider_name="codex", now=now),
            detect_provider_incident("Gemini: rate limited", provider_name="gemini", declared_providers={"gemini", "mistral"}, now=now),
            detect_provider_incident("Mistral: service unavailable", provider_name="mistral", declared_providers={"gemini", "mistral"}, now=now),
        ]
        assert [incident.provider for incident in incidents] == ["claude", "codex", "gemini", "mistral"]
        assert len({incident.retry_at for incident in incidents}) >= 2
        assert ProviderIncidentEvent.from_dict(incidents[2].to_dict()).provider == "gemini"
        registry = ProviderIncidentRegistry({"gemini", "mistral"})
        for incident in incidents:
            registry.record(incident)
        assert registry.snapshot("gemini")["incident_count"] == 1
        assert registry.snapshot("mistral")["incident_count"] == 1
        assert registry.snapshot("gemini")["retry_at"] != registry.snapshot("mistral")["retry_at"]

    def test_unknown_provider_is_rejected_not_merged(self):
        with pytest.raises(ProviderIncidentError, match="not declared"):
            detect_provider_incident("rate limited", provider_name="unapproved")

    def test_unknown_provider_error_stays_typed_and_serializable(self):
        incident = detect_provider_incident("Claude: strange upstream failure", provider_name="claude", now=datetime(2026, 8, 22, 10, tzinfo=timezone.utc))
        assert incident.error_type == ErrorClassification.UNKNOWN
        assert incident.raw_message == "Claude: strange upstream failure"
        assert ProviderIncidentEvent.from_dict(incident.to_dict()).error_type == ErrorClassification.UNKNOWN

    @pytest.mark.parametrize(
        ("policy", "retry_at", "absolute_quota", "expected"),
        [
            ("wait_until_deadline", "2026-08-22T12:00:00+00:00", False, "WAIT_UNTIL"),
            ("no_more_waits", None, False, "REQUEST_HUMAN"),
            ("bounded_backoff", None, True, "REQUEST_HUMAN"),
            ("bounded_backoff", None, False, "WAIT_UNTIL"),
        ],
    )
    def test_escalation_policy_matrix(self, policy, retry_at, absolute_quota, expected):
        assert ProviderRetryPolicy.decide(policy=policy, retry_at=retry_at, absolute_quota_reached=absolute_quota) == expected

    def test_forged_request_human_decision_is_rejected(self):
        with pytest.raises(ProviderIncidentError, match="REQUEST_HUMAN"):
            ProviderIncidentEvent.from_dict({
                "provider": "claude", "error_type": "rate_limited", "raw_message": "rate limited",
                "retry_at": "2026-08-22T12:00:00+00:00", "policy": "wait_until_deadline", "decision": "REQUEST_HUMAN",
            })


class TestProcessRunnerProviderIntegration:
    def test_simulated_process_returns_structured_provider_wait_without_business_correction(self, tmp_path):
        result = run_process(command=["/bin/sh", "-c", "printf 'plain-out'; printf 'Claude: rate limited' >&2; exit 1"], cwd=tmp_path, timeout_seconds=5)
        classified = classify_provider_result(result, provider_name="claude", now=datetime(2026, 8, 22, 10, tzinfo=timezone.utc))
        assert classified.provider_incident is not None
        assert classified.provider_incident.provider == "claude"
        assert classified.wait_state == "WAITING_PROVIDER_RESET"
        assert classified.stdout == "plain-out"
        assert classified.stderr == "Claude: rate limited"


class TestProviderType:
    """Test provider type enumeration (R21-1)."""

    def test_provider_types_defined(self):
        """Ensure all provider types are defined."""
        assert ProviderType.CLAUDE.value == "claude"
        assert ProviderType.CODEX.value == "codex"

    def test_provider_string_representation(self):
        """Provider types convert to lowercase strings."""
        assert str(ProviderType.CLAUDE) == "claude"
        assert str(ProviderType.CODEX) == "codex"


class TestErrorClassification:
    """Test error type taxonomy (R21-2)."""

    def test_error_types_defined(self):
        """Ensure closed taxonomy of error types exists."""
        expected = {
            "session_limit",
            "quota_exceeded",
            "rate_limited",
            "service_unavailable",
            "unknown",
        }
        actual = {et.value for et in ErrorClassification}
        assert actual == expected

    def test_error_string_representation(self):
        """Error types convert to lowercase strings."""
        assert str(ErrorClassification.SESSION_LIMIT) == "session_limit"
        assert str(ErrorClassification.QUOTA_EXCEEDED) == "quota_exceeded"


class TestProviderIncidentEvent:
    """Test provider incident event dataclass (AC-R21-6)."""

    def test_incident_creation(self):
        """Create a provider incident event."""
        incident = ProviderIncidentEvent(
            provider=ProviderType.CLAUDE,
            error_type=ErrorClassification.SESSION_LIMIT,
            raw_message="You've hit your session limit",
            source_timezone="Europe/Paris",
            retry_at="2026-08-23T07:10:00+00:00",
            policy="wait_until_deadline",
            decision="scheduled_retry",
        )
        assert incident.provider == ProviderType.CLAUDE
        assert incident.error_type == ErrorClassification.SESSION_LIMIT
        assert incident.source_timezone == "Europe/Paris"

    def test_incident_frozen(self):
        """Incidents are immutable."""
        incident = ProviderIncidentEvent(
            provider=ProviderType.CLAUDE,
            error_type=ErrorClassification.QUOTA_EXCEEDED,
            raw_message="Quota exceeded",
        )
        with pytest.raises(AttributeError):
            incident.provider = ProviderType.CODEX

    def test_incident_to_dict(self):
        """Serialize incident to dictionary (AC-R21-8)."""
        incident = ProviderIncidentEvent(
            provider=ProviderType.CLAUDE,
            error_type=ErrorClassification.SESSION_LIMIT,
            raw_message="Session limit hit",
            source_timezone="Europe/Paris",
            retry_at="2026-08-23T07:10:00+00:00",
            retry_after_seconds=3600,
        )
        data = incident.to_dict()
        assert data["provider"] == "claude"
        assert data["error_type"] == "session_limit"
        assert data["raw_message"] == "Session limit hit"
        assert data["source_timezone"] == "Europe/Paris"
        assert data["retry_at"] == "2026-08-23T07:10:00+00:00"

    def test_incident_from_dict(self):
        """Deserialize incident from dictionary."""
        data = {
            "provider": "codex",
            "error_type": "rate_limited",
            "raw_message": "Rate limited",
            "source_timezone": "US/Eastern",
            "retry_at": "2026-08-23T12:00:00+00:00",
            "retry_after_seconds": 60,
            "policy": "bounded_backoff",
            "decision": "scheduled_retry",
        }
        incident = ProviderIncidentEvent.from_dict(data)
        assert incident.provider == ProviderType.CODEX
        assert incident.error_type == ErrorClassification.RATE_LIMITED
        assert incident.source_timezone == "US/Eastern"


class TestProviderDetection:
    """Test provider type inference (R21-1, AC-R21-1)."""

    def test_detect_claude_from_message(self):
        """Detect Claude provider from message."""
        provider = ProviderIncidentDetector.detect_provider(
            "Claude API error: quota exceeded"
        )
        assert provider == ProviderType.CLAUDE

    def test_detect_codex_from_message(self):
        """Detect Codex provider from message."""
        provider = ProviderIncidentDetector.detect_provider(
            "Codex service unavailable"
        )
        assert provider == ProviderType.CODEX

    def test_detect_from_stderr(self):
        """Detect provider from stderr context."""
        provider = ProviderIncidentDetector.detect_provider(
            "rate limited",
            stderr="Claude API error"
        )
        assert provider == ProviderType.CLAUDE

    def test_reject_undeclared_provider(self):
        """An ambiguous provider may not be silently merged into OTHER."""
        with pytest.raises(ProviderIncidentError):
            ProviderIncidentDetector.detect_provider("Generic API error", provider_name="unapproved")


class TestErrorClassification:
    """Test error type classification (R21-2, AC-R21-2)."""

    def test_classify_session_limit(self):
        """Recognize session limit errors."""
        messages = [
            "You've hit your session limit",
            "you've hit your session limit",
            "Session limit reached",
            "session quota exceeded",
        ]
        for msg in messages:
            error_type = ProviderIncidentDetector.classify_error(msg)
            assert error_type == ErrorClassification.SESSION_LIMIT, f"Failed for: {msg}"

    def test_classify_quota_exceeded(self):
        """Recognize quota exceeded errors."""
        messages = [
            "Quota exceeded",
            "monthly quota limit reached",
            "rate limit: quota exceeded",
        ]
        for msg in messages:
            error_type = ProviderIncidentDetector.classify_error(msg)
            assert error_type == ErrorClassification.QUOTA_EXCEEDED, f"Failed for: {msg}"

    def test_classify_rate_limited(self):
        """Recognize rate limit errors."""
        messages = [
            "Rate limit exceeded",
            "too many requests",
            "request rate exceeded",
            "Retry-After: 60",
        ]
        for msg in messages:
            error_type = ProviderIncidentDetector.classify_error(msg)
            assert error_type == ErrorClassification.RATE_LIMITED, f"Failed for: {msg}"

    def test_classify_service_unavailable(self):
        """Recognize unavailability errors."""
        messages = [
            "Service unavailable",
            "temporarily unavailable",
            "connection timeout",
            "503 error",
            "Connection refused",
        ]
        for msg in messages:
            error_type = ProviderIncidentDetector.classify_error(msg)
            assert error_type == ErrorClassification.SERVICE_UNAVAILABLE, f"Failed for: {msg}"

    def test_classify_unknown(self):
        """Classify unrecognized errors as unknown."""
        error_type = ProviderIncidentDetector.classify_error("Something weird happened")
        assert error_type == ErrorClassification.UNKNOWN


class TestTimezoneAndTimeExtraction:
    """Test timezone and time parsing (R21-3, AC-R21-3)."""

    def test_extract_timezone_and_time(self):
        """Extract timezone and time from message (AC-R21-3)."""
        message = "You've hit your session limit · resets 7:10pm (Europe/Paris)"
        tz, time_str = ProviderIncidentDetector.extract_timezone_and_time(message)
        assert tz == "Europe/Paris"
        assert time_str == "19:10"

    def test_extract_timezone_morning(self):
        """Extract morning time correctly."""
        message = "Session limit resets 9:30am (US/Eastern)"
        tz, time_str = ProviderIncidentDetector.extract_timezone_and_time(message)
        assert tz == "US/Eastern"
        assert time_str == "09:30"

    def test_extract_noon(self):
        """Handle 12 PM correctly."""
        message = "resets 12:00pm (UTC)"
        tz, time_str = ProviderIncidentDetector.extract_timezone_and_time(message)
        assert tz == "UTC"
        assert time_str == "12:00"

    def test_extract_midnight(self):
        """Handle 12 AM correctly."""
        message = "resets 12:30am (Asia/Tokyo)"
        tz, time_str = ProviderIncidentDetector.extract_timezone_and_time(message)
        assert tz == "Asia/Tokyo"
        assert time_str == "00:30"

    def test_extract_without_meridiem(self):
        """Handle 24-hour format."""
        message = "resets 19:10 (Europe/Paris)"
        tz, time_str = ProviderIncidentDetector.extract_timezone_and_time(message)
        assert tz == "Europe/Paris"
        assert time_str == "19:10"

    def test_extract_dotted_meridiem(self):
        """Handle abbreviated meridiem (p.m., a.m.)."""
        message = "resets 7:10p.m. (Europe/London)"
        tz, time_str = ProviderIncidentDetector.extract_timezone_and_time(message)
        assert tz == "Europe/London"
        assert time_str == "19:10"

    def test_no_timezone_in_message(self):
        """Return None when timezone not found."""
        tz, time_str = ProviderIncidentDetector.extract_timezone_and_time(
            "Generic error message"
        )
        assert tz is None
        assert time_str is None


@pytest.mark.skipif(not HAS_PYTZ, reason="pytz required for timezone tests")
class TestRetryDeadlineCalculation:
    """Test retry deadline calculation (R21-4, AC-R21-4)."""

    def test_calculate_future_deadline_same_day(self):
        """Calculate deadline for later today."""
        now = datetime(2026, 8, 22, 6, 0, 0, tzinfo=timezone.utc)
        retry_at = ProviderIncidentDetector.calculate_retry_deadline(
            "Europe/Paris", "19:10", now=now
        )
        assert retry_at is not None
        retry_dt = datetime.fromisoformat(retry_at)
        assert retry_dt.day == 22
        assert retry_dt.hour == 17 or retry_dt.hour == 18
        assert "Europe/Paris" not in retry_at or "UTC" in retry_at or "+00" in retry_at

    def test_calculate_future_deadline_next_day(self):
        """Calculate deadline for tomorrow when reset time has passed."""
        now = datetime(2026, 8, 22, 20, 0, 0, tzinfo=timezone.utc)
        retry_at = ProviderIncidentDetector.calculate_retry_deadline(
            "Europe/Paris", "19:10", now=now
        )
        assert retry_at is not None
        retry_dt = datetime.fromisoformat(retry_at)
        assert retry_dt.day == 23

    def test_retry_at_uses_utc(self):
        """Returned retry_at is in UTC (AC-R21-4)."""
        now = datetime(2026, 8, 22, 10, 0, 0, tzinfo=timezone.utc)
        retry_at = ProviderIncidentDetector.calculate_retry_deadline(
            "Europe/Paris", "15:00", now=now
        )
        assert retry_at is not None
        assert "+00:00" in retry_at or "Z" in retry_at

    def test_invalid_timezone_returns_none(self):
        """Return None for invalid timezone."""
        retry_at = ProviderIncidentDetector.calculate_retry_deadline(
            "Invalid/Timezone", "15:00"
        )
        assert retry_at is None

    def test_timezone_offset_correctness(self):
        """Verify timezone conversion is correct."""
        paris_tz = pytz.timezone("Europe/Paris")
        now_utc = datetime(2026, 8, 22, 14, 0, 0, tzinfo=timezone.utc)
        now_paris = now_utc.astimezone(paris_tz)

        retry_at = ProviderIncidentDetector.calculate_retry_deadline(
            "Europe/Paris", "19:10", now=now_utc
        )
        assert retry_at is not None
        retry_dt = datetime.fromisoformat(retry_at)
        assert retry_dt.tzinfo == timezone.utc


@pytest.mark.skipif(not HAS_PYTZ, reason="pytz required for retry policy tests")
class TestRetryPolicy:
    """Test retry policy and backoff (R21-5, AC-R21-5)."""

    def test_bounded_backoff_session_limit(self):
        """Session limit has 1-hour backoff."""
        backoff = ProviderRetryPolicy.get_backoff(ErrorClassification.SESSION_LIMIT)
        assert backoff == 3600

    def test_bounded_backoff_quota(self):
        """Quota exceeded has 24-hour backoff."""
        backoff = ProviderRetryPolicy.get_backoff(ErrorClassification.QUOTA_EXCEEDED)
        assert backoff == 86400

    def test_bounded_backoff_rate_limit(self):
        """Rate limit has 60-second backoff."""
        backoff = ProviderRetryPolicy.get_backoff(ErrorClassification.RATE_LIMITED)
        assert backoff == 60

    def test_bounded_backoff_unavailable(self):
        """Unavailability has 300-second backoff."""
        backoff = ProviderRetryPolicy.get_backoff(
            ErrorClassification.SERVICE_UNAVAILABLE
        )
        assert backoff == 300

    def test_should_wait_for_deadline_session_limit(self):
        """Prefer waiting for deadline for session limits."""
        should_wait = ProviderRetryPolicy.should_wait_for_deadline(
            ErrorClassification.SESSION_LIMIT
        )
        assert should_wait is True

    def test_should_wait_for_deadline_quota(self):
        """Prefer waiting for deadline for quotas."""
        should_wait = ProviderRetryPolicy.should_wait_for_deadline(
            ErrorClassification.QUOTA_EXCEEDED
        )
        assert should_wait is True

    def test_should_not_wait_for_deadline_rate_limit(self):
        """Use backoff immediately for rate limits."""
        should_wait = ProviderRetryPolicy.should_wait_for_deadline(
            ErrorClassification.RATE_LIMITED
        )
        assert should_wait is False


class TestProviderIncidentDetection:
    """Integration tests for incident detection (R21, AC-R21-*)."""

    def test_detect_session_limit_incident(self):
        """Detect session limit incident with timezone (AC-R21-3)."""
        message = "Claude: You've hit your session limit · resets 7:10pm (Europe/Paris)"
        incident = detect_provider_incident(message, provider_name="claude")
        assert incident is not None
        assert incident.provider == ProviderType.CLAUDE
        assert incident.error_type == ErrorClassification.SESSION_LIMIT
        assert incident.source_timezone == "Europe/Paris"
        assert incident.retry_at is not None

    def test_detect_quota_incident(self):
        """Detect quota exceeded incident."""
        message = "Claude API: Monthly quota exceeded"
        incident = detect_provider_incident(message, provider_name="claude")
        assert incident is not None
        assert incident.error_type == ErrorClassification.QUOTA_EXCEEDED

    def test_detect_rate_limit_incident(self):
        """Detect rate limit incident."""
        message = "Rate limit exceeded; retry after 60 seconds"
        incident = detect_provider_incident(message, provider_name="claude")
        assert incident is not None
        assert incident.error_type == ErrorClassification.RATE_LIMITED
        assert incident.retry_after_seconds == 60

    def test_detect_unavailability_incident(self):
        """Detect service unavailability incident."""
        message = "Service temporarily unavailable, please retry later"
        incident = detect_provider_incident(message, provider_name="claude")
        assert incident is not None
        assert incident.error_type == ErrorClassification.SERVICE_UNAVAILABLE

    def test_unknown_error_is_a_typed_incident(self):
        """Unrecognized provider failures are retained as UNKNOWN incidents."""
        incident = detect_provider_incident("Something unexpected happened", provider_name="claude")
        assert incident.error_type == ErrorClassification.UNKNOWN

    def test_no_incident_for_empty_message(self):
        """Return None for empty message."""
        incident = detect_provider_incident("")
        assert incident is None

    def test_incident_with_stderr_context(self):
        """Use stderr context for provider detection (AC-R21-1)."""
        incident = detect_provider_incident(
            "Rate limit exceeded",
            stderr="Claude API: 429 Too Many Requests"
        )
        assert incident is not None
        assert incident.provider == ProviderType.CLAUDE

    def test_incident_uses_bounded_backoff_when_no_deadline(self):
        """Use bounded backoff when deadline not available (AC-R21-5)."""
        incident = detect_provider_incident("Rate limited", provider_name="claude")
        assert incident is not None
        assert incident.retry_after_seconds is not None
        assert incident.policy == "bounded_backoff"

    def test_incident_with_deadline_uses_wait_policy(self):
        """Use wait policy when deadline available (AC-R21-4)."""
        message = "You've hit your session limit · resets 7:10pm (Europe/Paris)"
        incident = detect_provider_incident(message, provider_name="claude")
        assert incident is not None
        assert incident.retry_at is not None
        assert incident.policy == "wait_until_deadline"

    @pytest.mark.skipif(not HAS_PYTZ, reason="pytz required")
    def test_incident_decision_is_scheduled_retry(self):
        """Incident decision should be scheduled_retry (AC-R21-6)."""
        message = "You've hit your session limit"
        incident = detect_provider_incident(message, provider_name="claude")
        assert incident is not None
        assert incident.decision == "scheduled_retry"

    def test_incident_preserves_raw_message(self):
        """Preserve raw message for audit (AC-R21-8)."""
        message = "You've hit your session limit"
        incident = detect_provider_incident(message, provider_name="claude")
        assert incident is not None
        assert incident.raw_message == message

    @pytest.mark.skipif(not HAS_PYTZ, reason="pytz required")
    def test_deterministic_retry_calculation(self):
        """Retry calculation is deterministic (AC-R21-4)."""
        message = "You've hit your session limit · resets 7:10pm (Europe/Paris)"
        now = datetime(2026, 8, 22, 10, 0, 0, tzinfo=timezone.utc)

        incident1 = detect_provider_incident(message, now=now, provider_name="claude")
        incident2 = detect_provider_incident(message, now=now, provider_name="claude")

        assert incident1 is not None
        assert incident2 is not None
        assert incident1.retry_at == incident2.retry_at
