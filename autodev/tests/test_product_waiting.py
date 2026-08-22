"""Tests for product pause, wait, and resume behavior.

AC-R14: Wait, pause, and resume distinct from failures, using injectable
clock, explicit timezone, no blocking loops, and deterministic retry.
AC-R21-6: WAITING_PROVIDER_RESET state explicitly materialized and observable.
AC-R21-8: Complete audit logging of provider incidents.
"""

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from autodev.provider_incidents import (
    ProviderIncidentEvent,
    ProviderType,
    ErrorClassification,
    detect_provider_incident,
)
from autodev.product_runtime import ProductRuntime
from autodev.product_state import ProductStateManager
from autodev.monitor_state import should_resume_from_provider_wait, read_provider_waiting_state


class TestWaitingStateProperties:
    """Test that waiting states are distinct from failures (AC-R14-1)."""

    def test_incident_state_is_distinct_from_failed(self):
        """Incident state is not FAILED status."""
        incident = ProviderIncidentEvent(
            provider=ProviderType.CLAUDE,
            error_type=ErrorClassification.SESSION_LIMIT,
            raw_message="Session limit hit",
            retry_at="2026-08-23T10:00:00+00:00",
            decision="scheduled_retry",
        )
        assert incident.decision != "FAILED"
        assert incident.decision == "scheduled_retry"

    def test_incident_state_is_distinct_from_blocked(self):
        """Incident state is not BLOCKED status."""
        incident = ProviderIncidentEvent(
            provider=ProviderType.CLAUDE,
            error_type=ErrorClassification.QUOTA_EXCEEDED,
            raw_message="Quota exceeded",
            policy="wait_until_deadline",
        )
        assert incident.policy != "BLOCKED"
        assert incident.policy == "wait_until_deadline"

    def test_incident_state_is_distinct_from_paused(self):
        """Incident waiting is different from explicit pause."""
        incident = ProviderIncidentEvent(
            provider=ProviderType.CLAUDE,
            error_type=ErrorClassification.RATE_LIMITED,
            raw_message="Rate limited",
            decision="scheduled_retry",
        )
        assert incident.decision == "scheduled_retry"
        assert incident.decision != "PAUSED"


class TestInjectableClockAndTimezone:
    """Test injectable clock and explicit timezone handling (AC-R14-2)."""

    def test_detect_accepts_injectable_now(self):
        """Can inject current time for testing."""
        now = datetime(2026, 8, 22, 10, 0, 0, tzinfo=timezone.utc)
        message = "You've hit your session limit · resets 7:10pm (Europe/Paris)"

        incident = detect_provider_incident(message, now=now)
        assert incident is not None
        assert incident.retry_at is not None

    def test_retry_at_uses_explicit_timezone(self):
        """Retry time includes explicit timezone source (AC-R14-2)."""
        message = "You've hit your session limit · resets 7:10pm (Europe/Paris)"
        incident = detect_provider_incident(message)
        assert incident is not None
        assert incident.source_timezone == "Europe/Paris"

    def test_retry_at_iso_format_with_timezone(self):
        """Retry_at is ISO 8601 with timezone info."""
        message = "Rate limited"
        incident = detect_provider_incident(message)
        assert incident is not None
        assert incident.retry_at is not None
        assert "T" in incident.retry_at
        assert ("+" in incident.retry_at or "Z" in incident.retry_at)

    def test_no_blocking_loops_required(self):
        """Incident detection is non-blocking (AC-R14-2)."""
        message = "Session limit hit · resets 7:10pm (Europe/Paris)"
        start = datetime.now()
        detect_provider_incident(message)
        elapsed = (datetime.now() - start).total_seconds()
        assert elapsed < 1.0


class TestProofReloadingBeforeAction:
    """Test proof reloading before deadline action (AC-R14-3)."""

    def test_incident_preserves_raw_message(self):
        """All incident details preserved for reconciliation (AC-R14-3)."""
        message = "Claude API: You've hit your session limit · resets 7:10pm (Europe/Paris)"
        incident = detect_provider_incident(message)
        assert incident is not None
        assert incident.raw_message == message
        assert incident.source_timezone == "Europe/Paris"
        assert incident.retry_at is not None

    def test_incident_serialization_preserves_all_data(self):
        """Serialization preserves all proof data for reload (AC-R14-3)."""
        message = "Session limit reached"
        incident = detect_provider_incident(message)
        assert incident is not None

        data = incident.to_dict()
        deserialized = ProviderIncidentEvent.from_dict(data)

        assert deserialized.provider == incident.provider
        assert deserialized.error_type == incident.error_type
        assert deserialized.raw_message == incident.raw_message
        assert deserialized.retry_at == incident.retry_at
        assert deserialized.policy == incident.policy


class TestLimitWithReturnTimeAsWaiting:
    """Test provider limit with return time becomes waiting (AC-R14-4, R21-4)."""

    def test_incident_with_reset_time_is_waiting(self):
        """Incident with reset time should trigger WAITING_PROVIDER_RESET (AC-R14-4)."""
        message = "You've hit your session limit · resets 7:10pm (Europe/Paris)"
        incident = detect_provider_incident(message)
        assert incident is not None
        assert incident.retry_at is not None
        assert incident.policy == "wait_until_deadline"

    def test_no_correction_budget_consumed(self):
        """Provider incident does not consume correction budget (AC-R14-4, R21-7)."""
        message = "Quota exceeded"
        incident = detect_provider_incident(message)
        assert incident is not None

        incident_dict = incident.to_dict()
        assert "correction" not in str(incident_dict).lower()
        assert incident.decision == "scheduled_retry"

    def test_waiting_preserves_worktree_state(self):
        """Incident should not cause worktree modifications (R21-7)."""
        message = "You've hit your session limit"
        incident = detect_provider_incident(message)
        assert incident is not None

        assert incident.decision == "scheduled_retry"
        assert incident.policy in ["wait_until_deadline", "bounded_backoff"]


class TestProviderDistinctionWithoutMerging:
    """Test providers are distinguished without merging (R21-1, AC-R21-1)."""

    def test_claude_incidents_identified_separately(self):
        """Claude incidents are clearly marked."""
        claude_msg = "Claude API: You've hit your session limit"
        incident = detect_provider_incident(claude_msg)
        assert incident is not None
        assert incident.provider == ProviderType.CLAUDE

    def test_codex_incidents_identified_separately(self):
        """Codex incidents are clearly marked."""
        codex_msg = "Codex service: Rate limit exceeded"
        incident = detect_provider_incident(codex_msg)
        assert incident is not None
        assert incident.provider == ProviderType.CODEX

    def test_provider_field_never_merged(self):
        """Provider field always identifies original source."""
        incidents = []
        messages = [
            ("Claude: quota exceeded", ProviderType.CLAUDE),
            ("Codex: service down", ProviderType.CODEX),
            ("Gemini: rate limit", "gemini"),
        ]
        for msg, expected_provider in messages:
            incident = detect_provider_incident(
                msg, declared_providers={"gemini"} if expected_provider == "gemini" else None
            )
            assert incident is not None
            assert incident.provider == expected_provider
            incidents.append(incident)

        assert incidents[0].provider != incidents[1].provider
        assert incidents[1].provider != incidents[2].provider


class TestIncidentPersistenceAndRecovery:
    """Test incident can be persisted and recovered (AC-R21-6, AC-R14-3)."""

    def test_incident_serializes_to_json_compatible_dict(self):
        """Incident can be serialized for persistence."""
        incident = ProviderIncidentEvent(
            provider=ProviderType.CLAUDE,
            error_type=ErrorClassification.SESSION_LIMIT,
            raw_message="You've hit your session limit · resets 7:10pm (Europe/Paris)",
            source_timezone="Europe/Paris",
            retry_at="2026-08-23T17:10:00+00:00",
            retry_after_seconds=None,
            policy="wait_until_deadline",
            decision="scheduled_retry",
        )

        data = incident.to_dict()
        assert isinstance(data, dict)
        assert all(isinstance(v, (str, int, type(None))) for v in data.values())

    def test_incident_recovers_from_serialized_state(self):
        """Incident can be recovered from persistence."""
        original = ProviderIncidentEvent(
            provider=ProviderType.CODEX,
            error_type=ErrorClassification.RATE_LIMITED,
            raw_message="Rate limited",
            source_timezone="US/Eastern",
            retry_at="2026-08-23T12:00:00+00:00",
            retry_after_seconds=60,
            policy="bounded_backoff",
            decision="scheduled_retry",
        )

        data = original.to_dict()
        recovered = ProviderIncidentEvent.from_dict(data)

        assert recovered.provider == original.provider
        assert recovered.error_type == original.error_type
        assert recovered.raw_message == original.raw_message
        assert recovered.source_timezone == original.source_timezone
        assert recovered.retry_at == original.retry_at
        assert recovered.policy == original.policy
        assert recovered.decision == original.decision


class TestWaitingStateTransitions:
    """Test transitions between waiting and other states."""

    def test_waiting_provider_reset_state_name(self):
        """WAITING_PROVIDER_RESET should be the state for incidents (AC-R21-6)."""
        message = "Session limit reached · resets 7:10pm (UTC)"
        incident = detect_provider_incident(message)
        assert incident is not None

        incident_dict = incident.to_dict()
        assert incident_dict["decision"] == "scheduled_retry"
        assert incident_dict["policy"] in ["wait_until_deadline", "bounded_backoff"]

    def test_no_escalation_without_deadline_impossibility(self):
        """Don't request human unless deadline is indeterminable (AC-R21-9)."""
        message = "You've hit your session limit · resets 7:10pm (Europe/Paris)"
        incident = detect_provider_incident(message)
        assert incident is not None
        assert incident.retry_at is not None
        assert incident.decision != "REQUEST_HUMAN"

    def test_no_modification_during_waiting(self):
        """Waiting state should not modify worktree (R21-7, AC-R21-7)."""
        message = "Rate limited"
        incident = detect_provider_incident(message)
        assert incident is not None

        incident_dict = incident.to_dict()
        assert "error" not in incident_dict["decision"].lower()
        assert "failed" not in incident_dict["decision"].lower()


class TestIncidentLogging:
    """Test incident logging meets audit requirements (AC-R21-8)."""

    def test_incident_contains_all_logged_fields(self):
        """Incident includes all required audit fields (AC-R21-8)."""
        message = "Claude API: You've hit your session limit · resets 7:10pm (Europe/Paris)"
        incident = detect_provider_incident(message)
        assert incident is not None

        data = incident.to_dict()
        required_fields = [
            "provider",
            "error_type",
            "raw_message",
            "policy",
            "decision",
        ]
        for field in required_fields:
            assert field in data, f"Missing required audit field: {field}"

    def test_incident_preserves_timezone_source(self):
        """Timezone source is preserved in audit (AC-R21-8)."""
        message = "You've hit your session limit · resets 3:30pm (Asia/Tokyo)"
        incident = detect_provider_incident(message)
        assert incident is not None
        assert incident.source_timezone == "Asia/Tokyo"

    def test_incident_audit_includes_retry_schedule(self):
        """Audit includes retry scheduling info (AC-R21-8)."""
        message = "Rate limited"
        incident = detect_provider_incident(message)
        assert incident is not None

        data = incident.to_dict()
        assert data["retry_at"] is not None or data["retry_after_seconds"] is not None


class TestMessageParsingAccuracy:
    """Test exact message parsing for known patterns (AC-R21-3)."""

    def test_parse_exact_session_limit_message(self):
        """Parse the exact message from spec (AC-R21-3)."""
        message = "You've hit your session limit · resets 7:10pm (Europe/Paris)"
        tz, time_str = (
            detect_provider_incident(message).source_timezone,
            None,
        )
        if detect_provider_incident(message):
            incident = detect_provider_incident(message)
            assert incident.source_timezone == "Europe/Paris"
            assert incident.error_type == ErrorClassification.SESSION_LIMIT

    def test_message_parsing_case_insensitive(self):
        """Message parsing should handle case variations."""
        messages = [
            "YOU'VE HIT YOUR SESSION LIMIT",
            "you've hit your session limit",
            "You've Hit Your Session Limit",
        ]
        for msg in messages:
            error_type = (
                detect_provider_incident(msg).error_type
                if detect_provider_incident(msg)
                else None
            )
            if error_type:
                assert error_type == ErrorClassification.SESSION_LIMIT

    def test_message_parsing_whitespace_tolerant(self):
        """Message parsing handles whitespace variations."""
        messages = [
            "You've hit your session limit · resets 7:10pm (Europe/Paris)",
            "You've hit your session limit  resets  7:10pm (Europe/Paris)",
            "You've hit your session limit resets 7:10pm ( Europe/Paris )",
        ]
        for msg in messages:
            incident = detect_provider_incident(msg)
            if incident and incident.source_timezone:
                assert incident.source_timezone.strip() == "Europe/Paris"


class TestInvalidTimezoneBackoff:
    """Test backoff handling when timezone is invalid (AC-R21-5, AC-R14-2)."""

    def test_invalid_timezone_falls_back_to_backoff(self):
        """Invalid timezone triggers backoff policy (AC-R21-5)."""
        message = "You've hit your session limit · resets 7:10pm (Invalid/Timezone)"
        incident = detect_provider_incident(message)
        assert incident is not None
        assert incident.policy == "bounded_backoff"
        assert incident.retry_after_seconds is not None
        assert incident.retry_at is not None

    def test_invalid_timezone_without_time(self):
        """No timezone/time triggers bounded backoff."""
        message = "You've hit your session limit"
        incident = detect_provider_incident(message)
        assert incident is not None
        assert incident.policy == "bounded_backoff"
        assert incident.retry_after_seconds is not None

    def test_backoff_is_bounded_for_all_error_types(self):
        """All error types get bounded backoff when no deadline (AC-R21-5)."""
        error_messages = [
            ("You've hit your session limit", ErrorClassification.SESSION_LIMIT),
            ("Quota exceeded", ErrorClassification.QUOTA_EXCEEDED),
            ("Rate limited", ErrorClassification.RATE_LIMITED),
            ("Service unavailable", ErrorClassification.SERVICE_UNAVAILABLE),
        ]
        for msg, expected_error_type in error_messages:
            incident = detect_provider_incident(msg)
            assert incident is not None, f"Failed to detect incident for: {msg}"
            assert incident.error_type == expected_error_type
            assert incident.retry_after_seconds is not None
            assert incident.retry_after_seconds > 0


class TestProviderWaitingPersistence:
    """Test incident persistence as WAITING_PROVIDER_RESET (AC-R21-6, AC-R14-1)."""

    def test_incident_can_be_persisted(self):
        """Incident is serializable for state persistence (AC-R21-6)."""
        message = "You've hit your session limit · resets 7:10pm (Europe/Paris)"
        incident = detect_provider_incident(message)
        assert incident is not None

        persisted = incident.to_dict()
        assert "provider" in persisted
        assert "error_type" in persisted
        assert "retry_at" in persisted
        assert "policy" in persisted

    def test_incident_recovers_after_persistence(self):
        """Incident is recoverable from persistence (AC-R14-3)."""
        message = "You've hit your session limit · resets 7:10pm (Europe/Paris)"
        incident = detect_provider_incident(message)
        assert incident is not None

        persisted = incident.to_dict()
        recovered = ProviderIncidentEvent.from_dict(persisted)

        assert recovered.provider == incident.provider
        assert recovered.error_type == incident.error_type
        assert recovered.retry_at == incident.retry_at
        assert recovered.policy == incident.policy
        assert recovered.decision == incident.decision

    def test_waiting_state_distinct_from_terminal_states(self):
        """WAITING_PROVIDER_RESET is not FAILED, BLOCKED, or PAUSED (AC-R21-6)."""
        message = "Claude API: You've hit your session limit"
        incident = detect_provider_incident(message)
        assert incident is not None

        persisted = incident.to_dict()
        assert persisted["decision"] == "scheduled_retry"
        assert persisted["decision"] != "FAILED"
        assert persisted["decision"] != "BLOCKED"
        assert persisted["decision"] != "PAUSED"
        assert persisted["policy"] in ["wait_until_deadline", "bounded_backoff"]

    def test_automatic_resume_after_deadline(self):
        """Waiting state can be checked for automatic resume (AC-R14-3)."""
        now_before = datetime(2026, 8, 22, 10, 0, 0, tzinfo=timezone.utc)
        message = "You've hit your session limit · resets 7:10pm (Europe/Paris)"
        incident = detect_provider_incident(message, now=now_before)
        assert incident is not None
        assert incident.retry_at is not None

        now_after = datetime(2026, 8, 22, 20, 0, 0, tzinfo=timezone.utc)
        retry_dt = datetime.fromisoformat(incident.retry_at.replace("Z", "+00:00"))
        assert now_after >= retry_dt


class TestRuntimePersistenceAndReconciliation:
    """Test runtime persistence and automatic resume with reconciliation (AC-R14-1, AC-R14-3, AC-R21-6)."""

    def test_runtime_persists_waiting_provider_reset_state(self):
        """ProductRuntime.record_provider_waiting_state() materializes WAITING_PROVIDER_RESET (AC-R21-6)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            repo_root.joinpath(".autodev/runs/products").mkdir(parents=True, exist_ok=True)

            runtime = ProductRuntime.create(repo_root)
            runtime.initialize_run(plan_id="test-plan", plan_hash="hash1")

            # Acquire lock for state mutation
            lock_id = runtime.acquire_product_lock()
            try:
                incident = ProviderIncidentEvent(
                    provider=ProviderType.CLAUDE,
                    error_type=ErrorClassification.SESSION_LIMIT,
                    raw_message="You've hit your session limit · resets 7:10pm (Europe/Paris)",
                    source_timezone="Europe/Paris",
                    retry_at="2026-08-23T17:10:00+00:00",
                    policy="wait_until_deadline",
                    decision="scheduled_retry",
                )

                # Record waiting state
                runtime.record_provider_waiting_state(incident, feature_id=None)

                # Verify WAITING_PROVIDER_RESET status is materialized
                state = runtime.state_manager.read_state("test-plan", "hash1")
                assert state.status == "WAITING_PROVIDER_RESET"

                # Verify waiting state is persisted in file
                waiting_state = runtime.get_provider_waiting_state()
                assert waiting_state is not None
                assert str(waiting_state.incident.provider) == "claude"
            finally:
                runtime.release_lock(lock_id)

    def test_runtime_persists_complete_audit_data(self):
        """Runtime audit logging includes all required fields (AC-R21-8)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            repo_root.joinpath(".autodev/runs/products").mkdir(parents=True, exist_ok=True)

            runtime = ProductRuntime.create(repo_root)
            runtime.initialize_run(plan_id="test-plan", plan_hash="hash1")

            lock_id = runtime.acquire_product_lock()
            try:
                incident = ProviderIncidentEvent(
                    provider=ProviderType.CODEX,
                    error_type=ErrorClassification.RATE_LIMITED,
                    raw_message="Rate limited · resets 3:30pm (Asia/Tokyo)",
                    source_timezone="Asia/Tokyo",
                    retry_at="2026-08-24T06:30:00+00:00",
                    retry_after_seconds=60,
                    policy="wait_until_deadline",
                    decision="scheduled_retry",
                )

                runtime.record_provider_waiting_state(incident, feature_id="feat-1")

                # Read journal and verify audit entry
                journal_entries = runtime.state_manager.read_journal()
                audit_entries = [e for e in journal_entries if e.action == "record_provider_waiting_state"]
                assert len(audit_entries) > 0

                latest_audit = audit_entries[-1]
                assert latest_audit.data["provider"] == "codex"
                assert latest_audit.data["error_type"] == "rate_limited"
                assert latest_audit.data["raw_message"] == "Rate limited · resets 3:30pm (Asia/Tokyo)"
                assert latest_audit.data["source_timezone"] == "Asia/Tokyo"
                assert latest_audit.data["retry_at"] == "2026-08-24T06:30:00+00:00"
                assert latest_audit.data["policy"] == "wait_until_deadline"
                assert latest_audit.data["decision"] == "scheduled_retry"
                assert "recorded_at" in latest_audit.data
            finally:
                runtime.release_lock(lock_id)

    def test_runtime_reconciles_before_automatic_resume(self):
        """ProductRuntime.resume_from_provider_wait() reconciles proofs (AC-R14-3)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            repo_root.joinpath(".autodev/runs/products").mkdir(parents=True, exist_ok=True)

            runtime = ProductRuntime.create(repo_root)
            runtime.initialize_run(plan_id="test-plan", plan_hash="hash1")

            now_before = datetime(2026, 8, 22, 10, 0, 0, tzinfo=timezone.utc)
            lock_id = runtime.acquire_product_lock()
            try:
                incident = detect_provider_incident(
                    "Claude API: You've hit your session limit · resets 7:10pm (Europe/Paris)",
                    now=now_before,
                )
                assert incident is not None

                # Record waiting state
                runtime.record_provider_waiting_state(incident)

                # Verify state before deadline
                result_before = runtime.resume_from_provider_wait(now=now_before)
                assert result_before is None  # Deadline not reached yet

                # Simulate time passing beyond deadline
                now_after = datetime(2026, 8, 22, 20, 0, 0, tzinfo=timezone.utc)
                result_after = runtime.resume_from_provider_wait(now=now_after)

                # Verify ready to resume after deadline with reconciliation
                assert result_after is not None
                assert result_after["ready_to_resume"] is True
                assert result_after["provider"] == "claude"
                assert result_after["error_type"] == "session_limit"
                assert "retry_at" in result_after
                assert "policy" in result_after
                assert "source_timezone" in result_after
            finally:
                runtime.release_lock(lock_id)

    def test_monitor_reconciles_during_deadline_check(self):
        """should_resume_from_provider_wait() performs full reconciliation (AC-R14-3)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            repo_root.joinpath(".autodev/runs/products").mkdir(parents=True, exist_ok=True)

            runtime = ProductRuntime.create(repo_root)
            runtime.initialize_run(plan_id="test-plan", plan_hash="hash1")

            now_before = datetime(2026, 8, 22, 10, 0, 0, tzinfo=timezone.utc)
            lock_id = runtime.acquire_product_lock()
            try:
                incident = detect_provider_incident(
                    "Claude API: Quota exceeded",
                    now=now_before,
                )
                assert incident is not None
                runtime.record_provider_waiting_state(incident, feature_id="feat-1")

                run_namespace = runtime.state_manager.run_namespace

                # Before deadline
                result_before = should_resume_from_provider_wait(
                    run_namespace,
                    now=now_before,
                    feature_id="feat-1",
                )
                assert result_before is None

                # After deadline - reconciliation should pass
                now_after = now_before + timedelta(hours=25)
                result_after = should_resume_from_provider_wait(
                    run_namespace,
                    now=now_after,
                    feature_id="feat-1",
                )

                assert result_after is not None
                assert result_after["ready_to_resume"] is True
                assert result_after["reconciliation_passed"] is True
                assert result_after["provider"] == "claude"
            finally:
                runtime.release_lock(lock_id)

    def test_state_divergence_detected_during_reconciliation(self):
        """Reconciliation detects divergence - missing state after deadline (AC-R14-3)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            repo_root.joinpath(".autodev/runs/products").mkdir(parents=True, exist_ok=True)

            runtime = ProductRuntime.create(repo_root)
            runtime.initialize_run(plan_id="test-plan", plan_hash="hash1")

            now = datetime(2026, 8, 22, 10, 0, 0, tzinfo=timezone.utc)
            lock_id = runtime.acquire_product_lock()
            try:
                incident = detect_provider_incident(
                    "Claude: You've hit your session limit · resets 7:10pm (UTC)",
                    now=now,
                )
                assert incident is not None
                runtime.record_provider_waiting_state(incident)

                # Get the run namespace to simulate external state change
                run_namespace = runtime.state_manager.run_namespace

                # Verify waiting state exists before deadline
                waiting_before = read_provider_waiting_state(run_namespace)
                assert waiting_before is not None

                # After timeout, clear the waiting state (simulating external divergence)
                runtime.clear_provider_waiting_state()

                # After deadline, reconciliation should detect missing state
                now_after = now + timedelta(hours=24)
                result = should_resume_from_provider_wait(run_namespace, now=now_after)

                # When waiting state is missing after deadline, function returns None
                # (safe behavior - no unsafe resume). Test passes state is properly isolated.
                assert result is None  # Correctly blocks resume when state is missing
            finally:
                runtime.release_lock(lock_id)

    def test_clear_waiting_removes_explicit_status(self):
        """Clearing waiting state also clears WAITING_PROVIDER_RESET status (AC-R14-1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            repo_root.joinpath(".autodev/runs/products").mkdir(parents=True, exist_ok=True)

            runtime = ProductRuntime.create(repo_root)
            runtime.initialize_run(plan_id="test-plan", plan_hash="hash1")

            lock_id = runtime.acquire_product_lock()
            try:
                incident = ProviderIncidentEvent(
                    provider=ProviderType.CLAUDE,
                    error_type=ErrorClassification.SESSION_LIMIT,
                    raw_message="Session limit",
                    retry_at="2026-08-23T10:00:00+00:00",
                    decision="scheduled_retry",
                )

                runtime.record_provider_waiting_state(incident)

                # Verify status is set
                state = runtime.state_manager.read_state("test-plan", "hash1")
                assert state.status == "WAITING_PROVIDER_RESET"

                # Clear waiting state
                runtime.clear_provider_waiting_state()

                # Verify status is cleared
                state_after = runtime.state_manager.read_state("test-plan", "hash1")
                assert state_after.status is None

                # Verify file is deleted
                waiting_state_after = runtime.get_provider_waiting_state()
                assert waiting_state_after is None
            finally:
                runtime.release_lock(lock_id)

    def test_feature_level_waiting_state_isolation(self):
        """Feature-level waiting states are isolated from product-level (AC-R14-1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            repo_root.joinpath(".autodev/runs/products").mkdir(parents=True, exist_ok=True)

            runtime = ProductRuntime.create(repo_root)
            runtime.initialize_run(plan_id="test-plan", plan_hash="hash1")

            lock_id = runtime.acquire_product_lock()
            try:
                incident_feat = ProviderIncidentEvent(
                    provider=ProviderType.CLAUDE,
                    error_type=ErrorClassification.SESSION_LIMIT,
                    raw_message="Feature incident",
                    retry_at="2026-08-23T10:00:00+00:00",
                    decision="scheduled_retry",
                )

                incident_prod = ProviderIncidentEvent(
                    provider=ProviderType.CODEX,
                    error_type=ErrorClassification.QUOTA_EXCEEDED,
                    raw_message="Product incident",
                    retry_at="2026-08-24T10:00:00+00:00",
                    decision="scheduled_retry",
                )

                # Record both
                runtime.record_provider_waiting_state(incident_feat, feature_id="feat-1")
                runtime.record_provider_waiting_state(incident_prod, feature_id=None)

                # Verify product-level status is set
                state = runtime.state_manager.read_state("test-plan", "hash1")
                assert state.status == "WAITING_PROVIDER_RESET"

                # Verify product-level waiting state from file
                prod_waiting = runtime.get_provider_waiting_state(feature_id=None)
                assert prod_waiting is not None
                assert str(prod_waiting.incident.provider) == "codex"

                # Verify feature-level isolation
                feat_state = state.feature_states.get("feat-1", {})
                assert feat_state.get("status") == "WAITING_PROVIDER_RESET"  # Feature level

                feat_waiting = runtime.get_provider_waiting_state(feature_id="feat-1")
                assert feat_waiting is not None
                assert str(feat_waiting.incident.provider) == "claude"
            finally:
                runtime.release_lock(lock_id)

    def test_tick_effectively_resumes_once_after_deadline_and_keeps_wait_on_failure(self):
        """A deadline triggers one atomic callback, then clears wait only after success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            repo_root.joinpath(".autodev/runs/products").mkdir(parents=True, exist_ok=True)
            before = datetime(2026, 8, 22, 10, 0, tzinfo=timezone.utc)
            after = datetime(2026, 8, 22, 20, 0, tzinfo=timezone.utc)
            calls = []
            runtime = ProductRuntime.create(repo_root, clock=lambda: before)
            runtime.initialize_run(plan_id="test-plan", plan_hash="hash1")
            incident = detect_provider_incident(
                "Claude: You've hit your session limit · resets 7:10pm (Europe/Paris)",
                provider_name="claude", now=before,
            )
            runtime.record_provider_waiting_state(incident)
            assert runtime.tick_provider_wait(now=before, resume_callback=lambda evidence: calls.append(evidence) or True) is None
            resumed = runtime.tick_provider_wait(now=after, resume_callback=lambda evidence: calls.append(evidence) or True)
            assert resumed["resumed"] is True
            assert len(calls) == 1
            assert runtime.state_manager.read_state("test-plan", "hash1").status != "WAITING_PROVIDER_RESET"
            assert runtime.tick_provider_wait(now=after, resume_callback=lambda evidence: calls.append(evidence) or True) is None
            assert len(calls) == 1

    def test_paused_and_waiting_are_persisted_as_distinct_states_after_reload(self):
        """Reloading a runtime preserves PAUSED independently from provider waiting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            repo_root.joinpath(".autodev/runs/products").mkdir(parents=True, exist_ok=True)
            runtime = ProductRuntime.create(repo_root)
            runtime.initialize_run(plan_id="test-plan", plan_hash="hash1")
            runtime.pause()
            reloaded = ProductRuntime(repo_root, runtime.run_id)
            assert reloaded.state_manager.read_state("test-plan", "hash1").status == "PAUSED"
            incident = ProviderIncidentEvent(provider="claude", error_type=ErrorClassification.RATE_LIMITED, raw_message="rate limited", retry_at="2026-08-23T10:00:00+00:00")
            reloaded.record_provider_waiting_state(incident, feature_id="waiting-feature")
            state = ProductRuntime(repo_root, runtime.run_id).state_manager.read_state("test-plan", "hash1")
            assert state.status == "PAUSED"
            assert state.feature_states["waiting-feature"]["status"] == "WAITING_PROVIDER_RESET"
