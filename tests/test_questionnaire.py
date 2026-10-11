"""Frontend transport/state tests against the proposed backend contract."""
import sys
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from test_frontend import app, analyzed, button
from ui import integration

QUESTIONS = {"questions": [
    {"id": "contact", "text": "Backend contact question?"},
    {"id": "records", "text": "Backend records question?"},
    {"id": "details", "text": "Backend details question?"}]}
FEEDBACK = {"headline": "Backend headline", "summary": "Backend summary",
            "concerns": ["Backend concern"], "recommended_actions": ["Backend action"]}
PAYLOAD = {"scenario": "bank_impersonation", "risk_level": "high",
           "signals": [{"type": "urgency", "evidence": "now"}], "claimed_sender": "Bank",
           "requested_amount": None, "payment_method": None, "explanation": "Backend analysis"}


@pytest.fixture
def backend(monkeypatch):
    import analyzer
    monkeypatch.setenv("SCAMBRAKE_DEMO_MODE", "false")
    monkeypatch.delenv("SCAMBRAKE_ANALYZER_MODULE", raising=False)
    monkeypatch.setenv("SCAMBRAKE_INTERVENTION_MODULE", "questionnaire_test_backend")
    analyze = Mock(return_value=deepcopy(PAYLOAD))
    monkeypatch.setattr(analyzer, "analyze_input", analyze)
    provider = SimpleNamespace(build_questionnaire=Mock(return_value=deepcopy(QUESTIONS)),
                               review_questionnaire=Mock(return_value=deepcopy(FEEDBACK)))
    monkeypatch.setitem(sys.modules, "questionnaire_test_backend", provider)
    return provider, analyze


def answer_all(at):
    for identifier, answer in (("contact", "no"), ("records", "yes"), ("details", "not_sure")):
        at.radio(key=f"question_answer_{identifier}").set_value(answer).run()


def test_backend_progress_review_invalidation_and_persistence(backend):
    provider, analyze = backend
    at = analyzed(app(), "Bank asks now")
    provider.build_questionnaire.assert_called_once_with(PAYLOAD)
    at.button(key="question_verify").click().run()
    assert at.button(key="review_answers").disabled
    assert any(c.value == "0 of 3 answered" for c in at.caption)
    at.radio(key="question_answer_contact").set_value("no").run()
    assert at.button(key="review_answers").disabled
    assert any(c.value == "1 of 3 answered" for c in at.caption)
    answer_all(at)
    assert not at.button(key="review_answers").disabled
    assert any(c.value == "3 of 3 answered" for c in at.caption)
    assert not provider.review_questionnaire.called
    at.button(key="review_answers").click().run()
    provider.review_questionnaire.assert_called_once_with(QUESTIONS, {"contact": "no", "records": "yes", "details": "not_sure"})
    for text in ("Backend headline", "Backend summary", "Backend concern", "Backend action"):
        assert any(t.value == text for t in at.text)
    at.button(key="question_verify").click().run()
    at.button(key="question_verify").click().run()
    assert at.session_state["questionnaire_feedback"] == FEEDBACK
    assert at.radio(key="question_answer_contact").value == "no"
    at.radio(key="question_answer_contact").set_value("yes").run()
    assert at.session_state["questionnaire_feedback"] is None
    assert not any(t.value == "Backend headline" for t in at.text)
    assert analyze.call_count == provider.build_questionnaire.call_count == provider.review_questionnaire.call_count == 1
    assert at.session_state["stage"] == "results"
    assert not at.exception
    button(at, "Check another message").click().run()
    assert at.session_state["question_answers"] == {}
    assert at.session_state["questionnaire_feedback"] is None
    analyzed(at, "Different Bank message now")
    at.button(key="question_verify").click().run()
    assert all(r.value is None for r in at.radio)
    assert at.button(key="review_answers").disabled
    assert provider.build_questionnaire.call_count == 2


def test_failed_review_safe_retry_without_analysis(backend):
    provider, analyze = backend
    provider.review_questionnaire.side_effect = RuntimeError("PRIVATE_BACKEND_DETAIL")
    at = analyzed(app(), "Bank now")
    at.button(key="question_verify").click().run()
    answer_all(at)
    at.button(key="review_answers").click().run()
    assert at.session_state["questionnaire_feedback"] is None
    assert any("retry" in e.value.lower() for e in at.error)
    assert not any("PRIVATE" in e.value for e in at.error)
    provider.review_questionnaire.side_effect = None
    at.button(key="review_answers").click().run()
    assert at.session_state["questionnaire_feedback"] == FEEDBACK
    assert analyze.call_count == 1
    assert not at.exception


def test_bad_questionnaire_does_not_discard_analysis(backend):
    provider, analyze = backend
    provider.build_questionnaire.return_value = {"questions": [{"id": "duplicate", "text": "One"}, {"id": "duplicate", "text": "Two"}]}
    at = analyzed(app(), "Bank now")
    assert at.session_state["stage"] == "results"
    assert at.session_state["analysis"] is not None
    at.button(key="question_verify").click().run()
    assert at.warning
    provider.build_questionnaire.return_value = deepcopy(QUESTIONS)
    at.button(key="retry_questions").click().run()
    assert len(at.radio) == 3
    assert analyze.call_count == 1
    assert not at.exception


def test_feedback_plain_text_and_no_local_conclusions(backend):
    provider, _ = backend
    literal = '<script>unsafe()</script> [link](https://untrusted.invalid)'
    provider.review_questionnaire.return_value = {"headline": literal, "summary": literal,
                                                "concerns": [literal], "recommended_actions": [literal]}
    at = analyzed(app(), "Bank now")
    at.button(key="question_verify").click().run()
    answer_all(at)
    at.button(key="review_answers").click().run()
    assert sum(t.value == literal for t in at.text) == 4
    assert not any(literal in m.value for m in at.markdown)
    assert not at.exception


def test_missing_api_uses_explicit_fixed_mock(monkeypatch):
    monkeypatch.setenv("SCAMBRAKE_DEMO_MODE", "true")
    monkeypatch.setenv("SCAMBRAKE_INTERVENTION_MODULE", "missing_questionnaire_backend")
    at = analyzed(app())
    at.button(key="question_verify").click().run()
    assert any("Temporary questionnaire preview" in i.value for i in at.info)
    for radio in at.radio:
        radio.set_value("yes").run()
    at.button(key="review_answers").click().run()
    assert any("have not been interpreted" in t.value for t in at.text)
    assert at.session_state["questionnaire_feedback"]["concerns"] == []
    assert not at.exception


@pytest.mark.parametrize("feedback", [None, {}, {**FEEDBACK, "concerns": "bad"}, {**FEEDBACK, "summary": 42}])
def test_malformed_review_is_not_displayed(backend, feedback):
    provider, _ = backend
    provider.review_questionnaire.return_value = feedback
    bundle = integration.prepare_questionnaire(PAYLOAD)
    with pytest.raises(integration.ServiceError, match="review"):
        integration.review_answers(bundle, {q["id"]: "no" for q in QUESTIONS["questions"]})
