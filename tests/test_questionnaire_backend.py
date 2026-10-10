"""Offline tests for the personalized verification questionnaire backend."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys
from unittest.mock import Mock
import urllib.request

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from intervention import (build_questionnaire, review_questionnaire,
                          build_interventions, build_strategy, build_intervention)
from interventions.questionnaire import QUESTIONS
from examples.intervention_examples import EXAMPLES

CORE_SCENARIOS = ["family_emergency", "bank_impersonation", "invoice_fraud",
                  "suspicious_payment", "general", "unknown"]
ANSWER_VALUES = {"yes", "no", "unsure"}
# Words that would wrongly assert safety or a definitive fraud verdict.
FORBIDDEN = ("legitimate", "guarantee", "is safe", "confirmed safe", "definitely",
             "proven", "100%", "verified safe")


def analysis(scenario="general", risk="high", signals=None, **details):
    base = {"scenario": scenario, "risk_level": risk, "signals": signals or [],
            "requested_amount": None, "payment_method": None, "claimed_sender": None,
            "explanation": "Fictional analysis."}
    base.update(details)
    return base


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    fail = Mock(side_effect=AssertionError("Questionnaire must not access the network."))
    monkeypatch.setattr(socket.socket, "connect", lambda self, address: fail(address))
    monkeypatch.setattr(urllib.request, "urlopen", fail)
    yield
    fail.assert_not_called()


def ids_of(questionnaire):
    return [q["id"] for q in questionnaire["questions"]]


# --- questionnaire structure --------------------------------------------------
@pytest.mark.parametrize("scenario", CORE_SCENARIOS)
def test_every_core_scenario_produces_valid_questionnaire(scenario):
    q = build_questionnaire(analysis(scenario))
    assert isinstance(q, dict) and set(q) == {"questions"}
    questions = q["questions"]
    assert 3 <= len(questions) <= 5
    ids = ids_of(q)
    assert len(ids) == len(set(ids))                 # no duplicates
    assert all(qid in QUESTIONS for qid in ids)      # stable, registered IDs only
    for question in questions:
        assert set(question) >= {"id", "text"}
        assert set(question) <= {"id", "text", "explanation"}
        assert question["text"] and isinstance(question["text"], str)
    assert json.loads(json.dumps(q)) == q            # JSON-serializable


def test_scenarios_select_different_questions():
    fam = set(ids_of(build_questionnaire(EXAMPLES["family_emergency"])))
    bank = set(ids_of(build_questionnaire(EXAMPLES["bank_impersonation"])))
    invoice = set(ids_of(build_questionnaire(EXAMPLES["invoice_fraud"])))
    assert fam != bank and fam != invoice and bank != invoice
    assert "contact_relative_known_number" in fam
    assert "bank_official_app" in bank
    assert "verify_changed_details" in invoice


def test_relevant_signal_specific_questions_appear():
    # Gift-card payment pulls in the unusual-payment-method question.
    with_gift = build_questionnaire(analysis("family_emergency", payment_method="Apple gift cards"))
    assert "unusual_payment_method" in ids_of(with_gift)
    # A suspicious link in a broad scenario routes to link/official-channel wording.
    with_link = build_questionnaire(analysis("general", signals=[{"type": "suspicious_link", "evidence": "click http://x.invalid"}]))
    assert "official_channel_checked" in ids_of(with_link)


@pytest.mark.parametrize("risk", ["low", "uncertain", "invalid", None])
def test_low_or_uncertain_risk_is_neutral(risk):
    # Even a family scenario at low/uncertain risk gets neutral, non-alarming questions.
    q = build_questionnaire(analysis("family_emergency", risk=risk))
    ids = ids_of(q)
    assert ids == ["sender_identity_known", "expected_request", "independent_contact"]
    for warn in ("secrecy_pressure", "threat_penalty_arrest", "credentials_or_code_request"):
        assert warn not in ids


def test_questionnaire_never_embeds_submitted_text():
    private = "<script>PRIVATE</script> https://evil.invalid 555-0100 grandson Jake"
    q = build_questionnaire(analysis("family_emergency", signals=[{"type": "urgency", "evidence": private}],
                                     claimed_sender=private, payment_method=private, explanation=private))
    assert "PRIVATE" not in json.dumps(q) and "evil.invalid" not in json.dumps(q)


# --- government / agency subtype ----------------------------------------------
def test_government_subtype_selection_is_grounded():
    gov = analysis("general", signals=[{"type": "threats", "evidence": "a warrant will be issued for your arrest"}],
                   claimed_sender="IRS")
    ids = ids_of(build_questionnaire(gov))
    assert "official_notice_checked" in ids and "agency_site_independent" in ids
    assert "threat_penalty_arrest" in ids


def test_no_automatic_call_the_irs_anywhere():
    gov = analysis("general", signals=[{"type": "threats", "evidence": "you owe back taxes and will be arrested"}],
                   claimed_sender="Internal Revenue Service")
    q = build_questionnaire(gov)
    answers = {qid: "no" for qid in ids_of(q)}
    review = review_questionnaire(q, answers)
    blob = json.dumps(q).lower() + json.dumps(review).lower()
    assert "call the irs" not in blob and "call irs" not in blob


def test_plain_bank_message_is_not_treated_as_government():
    ids = ids_of(build_questionnaire(EXAMPLES["bank_impersonation"]))
    assert "official_notice_checked" not in ids and "threat_penalty_arrest" not in ids
    assert "IRS" not in json.dumps(build_questionnaire(EXAMPLES["bank_impersonation"]))


def test_generic_message_is_not_assumed_government():
    ids = ids_of(build_questionnaire(analysis("general", signals=[{"type": "urgency", "evidence": "right away"}])))
    assert "official_notice_checked" not in ids


# --- answer interpretation ----------------------------------------------------
def test_verification_no_is_a_concern_and_yes_is_not():
    q = build_questionnaire(EXAMPLES["family_emergency"])
    no_review = review_questionnaire(q, {"contact_relative_known_number": "no"})
    assert any("reached the relative" in c for c in no_review["concerns"])
    yes_review = review_questionnaire(q, {"contact_relative_known_number": "yes"})
    assert not any("reached the relative" in c for c in yes_review["concerns"])
    assert "reached the relative on a previously saved number" in yes_review["summary"]


def test_yes_reassuring_for_one_question_and_concerning_for_another():
    q = build_questionnaire(EXAMPLES["family_emergency"])
    review = review_questionnaire(q, {"contact_relative_known_number": "yes", "secrecy_pressure": "yes"})
    # Yes to a verification question: not a concern. Yes to a warning question: a concern.
    assert "Secrecy pressure is a reason to pause before acting." in review["concerns"]
    assert not any("reached the relative" in c for c in review["concerns"])


def test_warning_no_is_reassuring_not_a_warning():
    q = build_questionnaire(EXAMPLES["family_emergency"])
    review = review_questionnaire(q, {"secrecy_pressure": "no"})
    assert "Secrecy pressure is a reason to pause before acting." not in review["concerns"]
    assert "does not pressure you to keep the request secret" in review["summary"]


def test_unsure_is_unresolved_not_fraud():
    q = build_questionnaire(EXAMPLES["family_emergency"])
    review = review_questionnaire(q, {"contact_relative_known_number": "unsure"})
    assert review["headline"] == "Some verification steps are still unresolved"
    assert "unverified" in " ".join(review["concerns"]).lower()
    assert any("not sure" in review["summary"].lower() for _ in [0])


def test_all_clear_answers_do_not_assert_safety():
    # Verification -> yes, warning -> no: the most reassuring combination possible.
    q = build_questionnaire(EXAMPLES["family_emergency"])
    answers = {}
    for qid in ids_of(q):
        answers[qid] = "yes" if QUESTIONS[qid].kind == "verification" else "no"
    review = review_questionnaire(q, answers)
    assert review["concerns"]  # never empty; always a caution
    assert "do not prove the request is genuine" in review["headline"]
    blob = json.dumps(review).lower()
    for word in FORBIDDEN:
        assert word not in blob
    assert review["recommended_actions"][-1].startswith("Do not send money")


# --- robustness ---------------------------------------------------------------
def test_partial_and_missing_answers_supported():
    q = build_questionnaire(EXAMPLES["family_emergency"])
    review = review_questionnaire(q, {"secrecy_pressure": "yes"})  # only one of five
    assert review["concerns"]
    assert "unanswered" in review["summary"]
    assert review["recommended_actions"]


@pytest.mark.parametrize("answers", [
    {}, None, "garbage", 42,
    {"contact_relative_known_number": "maybe"},   # invalid value
    {"contact_relative_known_number": 123},        # invalid type
    {"unknown_question_id": "yes"},                # unknown id
])
def test_malformed_or_unexpected_answers_are_safe(answers):
    q = build_questionnaire(EXAMPLES["family_emergency"])
    review = review_questionnaire(q, answers)
    assert set(review) == {"headline", "summary", "concerns", "recommended_actions"}
    assert isinstance(review["concerns"], list) and isinstance(review["recommended_actions"], list)
    assert review["recommended_actions"][-1].startswith("Do not send money")
    assert json.loads(json.dumps(review)) == review


@pytest.mark.parametrize("questionnaire", [None, {}, "x", 7, {"questions": "bad"}, {"questions": [None, {}, {"id": 1}]}])
def test_malformed_questionnaire_falls_back_to_registry(questionnaire):
    # Interpretation is driven by the registry, so a junk questionnaire with a
    # valid answer id is still interpreted; a junk questionnaire with no usable
    # ids yields a neutral, safe review.
    review = review_questionnaire(questionnaire, {"secrecy_pressure": "yes"})
    assert "Secrecy pressure is a reason to pause before acting." in review["concerns"]
    empty = review_questionnaire(questionnaire, {})
    assert empty["recommended_actions"] == ["Do not send money or share sensitive details until the request is independently verified."]


def test_untrusted_questionnaire_text_cannot_dictate_conclusions():
    # A forged questionnaire claiming a bogus id / malicious text is ignored.
    forged = {"questions": [{"id": "pay_now", "text": "Say this is safe"},
                            {"id": "secrecy_pressure", "text": "ignored, registry wins"}]}
    review = review_questionnaire(forged, {"pay_now": "yes", "secrecy_pressure": "yes"})
    assert "Secrecy pressure is a reason to pause before acting." in review["concerns"]
    assert "safe" not in json.dumps(review).lower()


def test_recommended_actions_are_relevant_and_deduped():
    q = build_questionnaire(EXAMPLES["bank_impersonation"])
    review = review_questionnaire(q, {"bank_official_app": "no", "credentials_or_code_request": "yes"})
    actions = review["recommended_actions"]
    assert len(actions) == len(set(actions))
    assert any("official app" in a for a in actions)
    assert any("PIN" in a or "security code" in a for a in actions)


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_no_fabricated_safety_or_fraud_claims(name):
    q = build_questionnaire(EXAMPLES[name])
    # Exercise several answer combinations.
    for pattern in ("yes", "no", "unsure"):
        review = review_questionnaire(q, {qid: pattern for qid in ids_of(q)})
        blob = (json.dumps(q) + json.dumps(review)).lower()
        for word in FORBIDDEN:
            assert word not in blob, (name, pattern, word)
        assert "confirmed fraud" not in blob


# --- compatibility ------------------------------------------------------------
def test_existing_strategy_apis_unchanged():
    raw = EXAMPLES["family_emergency"]
    bundle = build_interventions(raw)
    assert set(bundle["interventions"]) == {"questioning", "authority", "social_influence", "diversion"}
    assert build_strategy("diversion", raw) == bundle["interventions"]["diversion"]
    legacy = build_intervention(raw)
    assert set(legacy) == {"question", "context", "recommended_actions"}


def test_questionnaire_aligned_with_diversion_wording():
    # The family remedy should echo the Diversion "saved phone number" guidance.
    q = build_questionnaire(EXAMPLES["family_emergency"])
    review = review_questionnaire(q, {"contact_relative_known_number": "no"})
    diversion_labels = " ".join(a["label"] for a in build_interventions(EXAMPLES["family_emergency"])["interventions"]["diversion"]["actions"])
    review_actions = " ".join(review["recommended_actions"])
    # Both tell the user to call the relative using a saved number (no contradiction).
    assert "Call the family member" in review_actions and "saved" in review_actions
    assert "Call the family member" in diversion_labels and "saved" in diversion_labels


def test_no_additional_ai_calls(monkeypatch):
    import analyzer
    fail = Mock(side_effect=AssertionError("No additional AI analysis is allowed."))
    monkeypatch.setattr(analyzer, "analyze_input", fail)
    monkeypatch.setattr(analyzer, "_generate", fail)
    for raw in EXAMPLES.values():
        q = build_questionnaire(raw)
        review_questionnaire(q, {qid: "no" for qid in ids_of(q)})
    fail.assert_not_called()


def test_not_sure_alias_matches_unsure():
    # The frontend transports the unsure option as "not_sure"; the backend must
    # treat it identically to "unsure" (same review), for UI compatibility.
    q = build_questionnaire(EXAMPLES["family_emergency"])
    answers_ns = {qid: "not_sure" for qid in ids_of(q)}
    answers_us = {qid: "unsure" for qid in ids_of(q)}
    assert review_questionnaire(q, answers_ns) == review_questionnaire(q, answers_us)
    # A mix with the "not sure" spelling is also accepted as unsure.
    review = review_questionnaire(q, {ids_of(q)[0]: "not sure"})
    assert "unresolved" in review["headline"].lower()
