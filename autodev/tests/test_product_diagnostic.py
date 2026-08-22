import json

import pytest

from autodev.product_actions import get_action_registry
from autodev.product_diagnostic import (
    DiagnosticBuilder,
    EvidenceCollector,
    ProductDiagnosticError,
    ProposedAction,
    validate_json_schema,
)
from autodev.product_policy import ProductPolicyEngine, TypedActionExecutor


class ObservingPolicyEngine(ProductPolicyEngine):
    """Observe public T07 authorizations while retaining the real contract."""

    def __init__(self):
        super().__init__()
        self.authorization_calls = []
        self.authorization_results = []

    def authorize_action(self, action_id, context, inputs=None, check_mandatory_escalation=True):
        self.authorization_calls.append((action_id, context, dict(inputs or {})))
        result = super().authorize_action(action_id, context, inputs, check_mandatory_escalation)
        self.authorization_results.append(result)
        return result


def authoritative_collector(state=None):
    defaults = {
        "base": "base-1", "commit": "commit-1", "paths": ["autodev/src/autodev/product_diagnostic.py"],
        "review": "APPROVED", "tests": "PASS", "diff": "technical diff",
        "git": {"head": "commit-1", "clean": True}, "corrections": [], "incidents": [],
        "decisions": [], "policy": {},
    }
    if state is None:
        state = defaults
    else:
        for key, value in defaults.items():
            state.setdefault(key, value)
    return (
        EvidenceCollector("TASK-001")
        .with_base_commit_reader(lambda: state["base"])
        .with_produced_commit_reader(lambda: state["commit"])
        .with_modified_paths_reader(lambda: state["paths"])
        .with_review_verdict_reader(lambda: state["review"])
        .with_test_status_reader(lambda: state["tests"])
        .with_diff_reader(lambda: state["diff"])
        .with_git_status_reader(lambda: state["git"])
        .with_corrections_reader(lambda: state["corrections"])
        .with_prior_incident_codes_reader(lambda: state["incidents"])
        .with_decisions_reader(lambda: state["decisions"])
        .with_policy_context_reader(lambda: state["policy"])
    )


def test_collect_without_required_readers_fails():
    with pytest.raises(ProductDiagnosticError, match="missing authoritative readers"):
        EvidenceCollector("TASK-001").collect()


def test_build_without_authoritative_collector_fails():
    with pytest.raises(ProductDiagnosticError, match="EvidenceCollector"):
        DiagnosticBuilder(None, ProductPolicyEngine(), "TASK-001")  # type: ignore[arg-type]


def test_prefabricated_facts_are_not_a_public_builder_input():
    with pytest.raises(TypeError):
        DiagnosticBuilder(facts=object(), policy_engine=ProductPolicyEngine(), task_id="TASK-001")  # type: ignore[call-arg]


def test_build_collects_on_every_invocation_and_observes_commit_diff_and_validations():
    state = {}
    collector = authoritative_collector(state)
    builder = DiagnosticBuilder(collector, ProductPolicyEngine(), "TASK-001").with_proposed_action(
        "REQUEST_HUMAN", "Human confirmation is required", []
    )
    first = builder.build()
    state.update({"commit": "commit-2", "diff": "new technical diff", "tests": "FAIL"})
    second = builder.build()
    assert first.facts.produced_commit == "commit-1"
    assert second.facts.produced_commit == "commit-2"
    assert second.facts.diff_summary == "new technical diff"
    assert second.facts.test_status == "FAIL"


def test_build_calls_collect_on_every_invocation():
    collector = authoritative_collector()
    calls = 0
    original_collect = collector.collect

    def counted_collect():
        nonlocal calls
        calls += 1
        return original_collect()

    collector.collect = counted_collect  # type: ignore[method-assign]
    builder = DiagnosticBuilder(collector, ProductPolicyEngine(), "TASK-001")
    builder.build()
    builder.build()
    assert calls == 2


def test_build_observes_review_change_and_technical_evidence_beats_narrative_report():
    state = {}
    collector = authoritative_collector(state)
    builder = DiagnosticBuilder(collector, ProductPolicyEngine(), "TASK-001").with_proposed_action(
        "REQUEST_HUMAN", "Human confirmation is required", []
    )
    first = builder.build()
    state.update({"review": "CORRECTION_REQUIRED", "corrections": [{"narrative": "all clear"}]})
    second = builder.build()
    assert first.facts.review_verdict == "APPROVED"
    assert second.facts.review_verdict == "CORRECTION_REQUIRED"
    assert second.facts.test_status == "PASS"


def test_source_error_is_forwarded_without_diagnostic():
    collector = authoritative_collector()
    collector.with_diff_reader(lambda: (_ for _ in ()).throw(OSError("diff unavailable")))
    with pytest.raises(ProductDiagnosticError, match="diff unavailable"):
        DiagnosticBuilder(collector, ProductPolicyEngine(), "TASK-001").build()


def test_schema_action_ids_match_the_real_closed_registry():
    schema = json.loads(open("autodev/schemas/product-diagnostic.schema.json", encoding="utf-8").read())
    assert set(schema["$defs"]["action_id"]["enum"]) == {action.action_id for action in get_action_registry().list_actions()}


def test_direct_request_human_requires_one_public_policy_validation():
    engine = ObservingPolicyEngine()
    diagnostic = (DiagnosticBuilder(authoritative_collector(), engine, "TASK-001")
        .with_proposed_action("REQUEST_HUMAN", "No action is safely applicable", []).build())
    assert diagnostic.proposed_action.action_id == "REQUEST_HUMAN"
    assert [call[0] for call in engine.authorization_calls] == ["REQUEST_HUMAN"]
    assert set(engine.authorization_calls[0][2]) >= {
        "reason", "facts", "evidence", "decisions_to_preserve", "attempted_solutions", "possible_choices",
    }


def test_unknown_and_local_action_ids_are_rejected():
    builder = DiagnosticBuilder(authoritative_collector(), ProductPolicyEngine(), "TASK-001")
    with pytest.raises(ProductDiagnosticError, match="canonical registry"):
        builder.with_proposed_action("CONTINUE", "local name", [])
    with pytest.raises(ProductDiagnosticError, match="canonical registry"):
        builder.with_proposed_action("rm -rf /", "command", [])


def test_authorized_action_is_published_only_after_its_public_policy_validation():
    engine = ObservingPolicyEngine()
    state = {"policy": {"provider_quota_exceeded": True, "retry_budget_exhausted": True}}
    diagnostic = (DiagnosticBuilder(authoritative_collector(state), engine, "TASK-001")
        .with_proposed_action("WAIT_PROVIDER_RESET", "Wait for the provider quota", [], {"wait_seconds": 60}).build())
    assert diagnostic.proposed_action.action_id == "WAIT_PROVIDER_RESET"
    assert [call[0] for call in engine.authorization_calls] == ["WAIT_PROVIDER_RESET"]
    assert engine.authorization_results[0].authorization_allowed is True
    assert diagnostic.proposed_action.action_id == engine.authorization_results[0].selected_action_id


def test_diagnostic_authorization_never_executes_an_action(monkeypatch):
    executor_calls = []

    def forbidden_execute(*args, **kwargs):
        executor_calls.append((args, kwargs))
        raise AssertionError("diagnostics must not execute actions")

    monkeypatch.setattr(TypedActionExecutor, "execute", forbidden_execute)
    state = {"policy": {"provider_quota_exceeded": True, "retry_budget_exhausted": True}}
    diagnostic = (DiagnosticBuilder(authoritative_collector(state), ProductPolicyEngine(), "TASK-001")
        .with_proposed_action("WAIT_PROVIDER_RESET", "Wait for the provider quota", [], {"wait_seconds": 60}).build())
    assert diagnostic.proposed_action.action_id == "WAIT_PROVIDER_RESET"
    assert executor_calls == []


def test_refused_action_authorizes_request_human_as_the_second_and_final_action():
    engine = ObservingPolicyEngine()
    diagnostic = (DiagnosticBuilder(authoritative_collector(), engine, "TASK-001")
        .with_proposed_action("REVALIDATE_TASK", "Revalidate the task", [], {"task_id": "TASK-001"}).build())
    assert diagnostic.proposed_action.action_id == "REQUEST_HUMAN"
    assert [call[0] for call in engine.authorization_calls] == ["REVALIDATE_TASK", "REQUEST_HUMAN"]
    assert engine.authorization_calls[1][0] == "REQUEST_HUMAN"
    assert diagnostic.proposed_action.action_inputs == engine.authorization_calls[1][2]
    assert engine.authorization_results[1].authorization_allowed is True
    assert diagnostic.proposed_action.action_id == engine.authorization_results[1].selected_action_id


def test_refused_action_does_not_publish_diagnostic_when_request_human_is_refused():
    engine = ObservingPolicyEngine()
    state = {"policy": {"business_ambiguity_unresolved": True}}
    builder = (DiagnosticBuilder(authoritative_collector(state), engine, "TASK-001")
        .with_proposed_action("REVALIDATE_TASK", "Revalidate the task", [], {"task_id": "TASK-001"}))
    with pytest.raises(ProductDiagnosticError, match="REQUEST_HUMAN"):
        builder.build()
    assert [call[0] for call in engine.authorization_calls] == ["REVALIDATE_TASK", "REQUEST_HUMAN"]


def test_policy_engine_error_during_fallback_stops_build_without_executor(monkeypatch):
    engine = ObservingPolicyEngine()
    real_evaluate = engine._evaluate_action

    def fail_request_human(action, *args, **kwargs):
        if action.action_id == "REQUEST_HUMAN":
            raise RuntimeError("policy engine unavailable")
        return real_evaluate(action, *args, **kwargs)

    monkeypatch.setattr(engine, "_evaluate_action", fail_request_human)
    builder = (DiagnosticBuilder(authoritative_collector(), engine, "TASK-001")
        .with_proposed_action("REVALIDATE_TASK", "Revalidate the task", [], {"task_id": "TASK-001"}))
    with pytest.raises(ProductDiagnosticError, match="policy validation failed"):
        builder.build()
    assert [call[0] for call in engine.authorization_calls] == ["REVALIDATE_TASK", "REQUEST_HUMAN"]


def test_incompatible_fake_policy_engine_is_rejected():
    class FakeEngine: pass
    with pytest.raises(ProductDiagnosticError, match="ProductPolicyEngine"):
        DiagnosticBuilder(authoritative_collector(), FakeEngine(), "TASK-001")  # type: ignore[arg-type]


def test_policy_validation_is_deterministic_for_identical_evidence_and_context():
    builder = (DiagnosticBuilder(authoritative_collector(), ProductPolicyEngine(), "TASK-001")
        .with_proposed_action("REQUEST_HUMAN", "No action is safely applicable", []))
    assert builder.build().proposed_action.action_id == builder.build().proposed_action.action_id


def test_proposed_action_does_not_accept_shell_steps():
    with pytest.raises(ProductDiagnosticError, match="shell"):
        ProposedAction("REQUEST_HUMAN", "Escalate", ["pytest && rm -rf /"])


def test_diagnostic_serializes_and_validates_against_schema():
    diagnostic = (DiagnosticBuilder(authoritative_collector(), ProductPolicyEngine(), "TASK-001")
        .with_proposed_action("REQUEST_HUMAN", "No action is safely applicable", []).build())
    validate_json_schema(diagnostic.to_dict())
