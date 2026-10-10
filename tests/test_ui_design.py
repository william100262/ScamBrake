"""Behavioral separation, persistence and provider call regression coverage."""
from copy import deepcopy
from unittest.mock import Mock
import pytest
from test_frontend import app, analyzed, button
from ui import integration, mock_data
from intervention_questions import build_verification


@pytest.fixture(autouse=True)
def demo_environment(monkeypatch):
    # Force deterministic, offline demo mode for app-based UI tests. Without this,
    # app.py's load_dotenv() can select live mode (.env SCAMBRAKE_DEMO_MODE=false)
    # and call the real analyzer. Per-test overrides (e.g. live + mocked _generate)
    # still apply because they monkeypatch after this fixture runs.
    monkeypatch.setenv("SCAMBRAKE_DEMO_MODE", "true")
    monkeypatch.delenv("SCAMBRAKE_VOICE_MODULE", raising=False)
    monkeypatch.delenv("SCAMBRAKE_INTERVENTION_MODULE", raising=False)


@pytest.mark.parametrize("scenario", ["family_emergency", "bank_impersonation", "invoice_fraud", "suspicious_payment", "general", "unknown"])
def test_supported_contexts(scenario):
    model = build_verification({"scenario": scenario, "signals": [], "claimed_sender": None})
    assert 3 <= len(model["questions"]) <= 5
    assert len({q["id"] for q in model["questions"]}) == len(model["questions"])
    assert all(q["explanation"] for q in model["questions"])
    assert model["actions"]


@pytest.mark.parametrize("sender", ["IRS", "Internal Revenue Service", "Government agency", "HMRC"])
def test_government_without_phone_default(sender):
    model = build_verification({"scenario": "general", "claimed_sender": sender,
                                "payment_method": "gift cards", "signals": [{"type": "threat", "evidence": "pay now"}]})
    assert model["context"] == "government"
    assert len(model["questions"]) == 5
    assert "official_notice" in {q["id"] for q in model["questions"]}
    assert "call the irs" not in str(model).lower()
    assert "phone" not in " ".join(a["text"] for a in model["actions"]).lower()
    if sender in ("IRS", "Internal Revenue Service"):
        assert model["authority"]["source"]["name"] == "Internal Revenue Service"


def test_link_and_neutral_contexts_do_not_trust_submitted_contacts():
    model = build_verification({"scenario": "general", "claimed_sender": "https://evil.invalid",
                                "signals": [{"type": "suspicious_link", "evidence": "https://evil.invalid"}]})
    assert model["context"] == "suspicious_link"
    assert "evil.invalid" not in str(model["actions"])
    assert "evil.invalid" not in str(model["authority"])
    neutral = build_verification({"risk_level": "low", "signals": []})
    assert neutral["patterns"] == []
    assert "not evidence" in neutral["authority"]["guidance"]


def test_original_seven_fields_reach_companion(monkeypatch):
    payload = {"scenario": "bank_impersonation", "risk_level": "high", "signals": [{"type": "urgency", "evidence": "now"}],
               "requested_amount": None, "payment_method": None, "claimed_sender": "Bank", "explanation": "Check independently."}
    original = deepcopy(payload)
    monkeypatch.setattr(integration, "load_function", lambda *args: lambda text: payload)
    result = integration.analyze_input(text="Bank says now", demo=False)
    assert result["scenario"] == "bank_impersonation"
    assert result["analyzer_result"] == original
    assert payload == original
    assert build_verification(result["analyzer_result"])["context"] == "bank_impersonation"
    assert integration.normalize_intervention({})["recommended_actions"]


def test_inline_panels_preserve_progress_without_provider_reruns(monkeypatch):
    analyze = Mock(wraps=mock_data.analyze_input)
    monkeypatch.setattr(mock_data, "analyze_input", analyze)
    at = analyzed(app())
    assert not at.session_state["questions_open"]
    assert {e.label for e in at.expander} >= {"View official guidance", "Matched warning patterns", "Your independent verification checklist"}
    assert not any(b.label == "Pause & Verify" for b in at.button)
    at.checkbox(key="action_check_saved_contact").check().run()
    assert at.session_state["stage"] == "results"
    assert not at.session_state["questions_open"]
    at.button(key="question_verify").click().run()
    # Questions now come from the real backend (3-5 personalized items), not the
    # fixed 3-question mock; one radio is rendered per returned question.
    questions = at.session_state["questionnaire_bundle"]["questionnaire"]["questions"]
    assert 3 <= len(questions) <= 5
    assert len(at.radio) == len(questions)
    assert at.session_state["stage"] == "results"
    at.radio(key="question_answer_independent_contact").set_value("no").run()
    at.button(key="question_verify").click().run()
    at.button(key="question_verify").click().run()
    assert at.radio(key="question_answer_independent_contact").value == "no"
    assert at.checkbox(key="action_check_saved_contact").value
    assert analyze.call_count == 1
    assert any("High concern" in e.value for e in at.error)
    assert not at.exception
    button(at, "Check another message").click().run()
    assert at.session_state["question_answers"] == {}
    assert at.session_state["checklist_completion"] == {}
    analyzed(at, mock_data.REMINDER_MESSAGE)
    assert not at.session_state["questions_open"]
    assert not any(c.value for c in at.checkbox)
    assert not at.exception


def test_authority_null_source_is_honest_and_does_not_open_questions():
    at = analyzed(app())
    model = deepcopy(at.session_state["verification_model"])
    model["authority"] = {"guidance": "General independent verification guidance.", "source": None}
    at.session_state["verification_model"] = model
    at.run()
    assert any("no specific official source" in c.value for c in at.caption)
    assert not at.session_state["questions_open"]
    assert at.session_state["stage"] == "results"
    assert not at.exception


@pytest.mark.parametrize("scenario,sender,question_id", [
    ("bank_impersonation", "Bank", "official_app"),
    ("general", "IRS", "official_notice"),
    ("invoice_fraud", "Supplier", "supplier_contact")])
def test_live_provider_once_for_contextual_interactions(monkeypatch, scenario, sender, question_id):
    import json
    import analyzer
    monkeypatch.setenv("SCAMBRAKE_DEMO_MODE", "false")
    monkeypatch.delenv("SCAMBRAKE_ANALYZER_MODULE", raising=False)
    monkeypatch.setenv("SCAMBRAKE_INTERVENTION_MODULE", "missing_intervention")
    message = f"{sender}: pay now."
    payload = {"scenario": scenario, "risk_level": "high", "signals": [{"type": "urgency", "evidence": "now"}],
               "requested_amount": None, "payment_method": None, "claimed_sender": sender, "explanation": "Check independently."}
    generate = Mock(return_value=json.dumps(payload))
    monkeypatch.setattr(analyzer, "_generate", generate)
    at = analyzed(app(), message)
    assert at.session_state["analysis"]["scenario"] == scenario
    at.button(key="question_verify").click().run()
    at.radio(key="question_answer_independent_contact").set_value("not_sure").run()
    at.checkbox[0].check().run()
    at.button(key="question_verify").click().run()
    at.button(key="question_verify").click().run()
    assert at.radio(key="question_answer_independent_contact").value == "not_sure"
    assert at.session_state["stage"] == "results"
    assert generate.call_count == 1
    assert not at.exception
