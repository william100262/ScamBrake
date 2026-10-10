"""Focused tests for the TEMPORARY four-card intervention demo UI/integration."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ui import integration, mock_data
from interventions.contract import validate_bundle

ANALYZER_RAW = {
    "scenario": "family_emergency", "risk_level": "high",
    "signals": [{"type": "urgency", "evidence": "right away"}],
    "requested_amount": "$2,500", "payment_method": "Apple gift cards",
    "claimed_sender": "grandson Jake", "explanation": "A fictional urgent request.",
}


@pytest.fixture(autouse=True)
def demo_environment(monkeypatch):
    monkeypatch.setenv("SCAMBRAKE_DEMO_MODE", "true")
    monkeypatch.delenv("SCAMBRAKE_VOICE_MODULE", raising=False)


def app():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    assert not at.exception
    return at


def analyzed(at, text=mock_data.FAMILY_MESSAGE):
    at.text_area(key="message").set_value(text).run()
    at.button(key="analyze").click().run()
    assert not at.exception
    assert at.session_state["stage"] == "results"
    return at


# --- integration layer --------------------------------------------------------
def test_demo_cards_use_original_analyzer_output_with_scenario():
    """The bundle must come from the analyzer-shaped output (scenario preserved),
    not the normalized analysis which drops scenario."""
    analysis, cards = integration.analyze_with_interventions(text=mock_data.FAMILY_MESSAGE, demo=True)
    assert "scenario" not in analysis  # normalized frontend analysis never carries it
    validate_bundle(cards)
    assert cards["scenario"] == "family_emergency"
    assert set(cards["interventions"]) == {"questioning", "authority", "social_influence", "diversion"}
    assert cards["interventions"]["authority"]["source"]["url"]
    assert "urgency" in cards["interventions"]["social_influence"]["matched_signals"]


@pytest.mark.parametrize("message,scenario", [
    (mock_data.FAMILY_MESSAGE, "family_emergency"),
    (mock_data.MODERATE_MESSAGE, "invoice_fraud"),
    (mock_data.REMINDER_MESSAGE, "general"),
    ("totally unrecognized text", "unknown"),
])
def test_demo_bundles_valid_for_each_fixture(message, scenario):
    _, cards = integration.analyze_with_interventions(text=message, demo=True)
    validate_bundle(cards)
    assert cards["scenario"] == scenario


def test_live_mode_builds_cards_from_single_analysis(monkeypatch):
    analyze = Mock(return_value=ANALYZER_RAW)
    monkeypatch.setitem(sys.modules, "demo_analyzer", SimpleNamespace(analyze_input=analyze))
    monkeypatch.setenv("SCAMBRAKE_ANALYZER_MODULE", "demo_analyzer")
    analysis, cards = integration.analyze_with_interventions(text="Jake needs $2,500 right away", demo=False)
    analyze.assert_called_once()  # must not re-run the analyzer just to build cards
    validate_bundle(cards)
    assert cards["scenario"] == "family_emergency"
    assert analysis["risk_level"] == "high"


def test_card_build_failure_leaves_core_analysis(monkeypatch):
    import intervention
    monkeypatch.setattr(intervention, "build_interventions", Mock(side_effect=RuntimeError("boom")))
    analysis, cards = integration.analyze_with_interventions(text=mock_data.FAMILY_MESSAGE, demo=True)
    assert cards is None
    assert analysis["risk_level"] == "high"


# --- Streamlit UI -------------------------------------------------------------
def test_four_cards_render_after_analysis():
    at = analyzed(app())
    bundle = at.session_state["interventions"]
    validate_bundle(bundle)
    # Questioning radio with three options, in yes/no/unsure order.
    radio = at.radio(key="intervention_answer_widget")
    assert len(radio.options) == 3
    # Diversion checklist renders one checkbox per action.
    action_ids = [a["id"] for a in bundle["interventions"]["diversion"]["actions"]]
    for action_id in action_ids:
        assert any(cb.key == f"icheck_{action_id}" for cb in at.checkbox)
    # Social influence matched signals surface as text.
    assert any("urgency" in t.value for t in at.text)
    assert not at.exception


def test_demo_answer_and_checkboxes_persist_across_reruns():
    at = analyzed(app())
    bundle = at.session_state["interventions"]
    first_action = bundle["interventions"]["diversion"]["actions"][0]["id"]
    at.radio(key="intervention_answer_widget").set_value("I'm not sure").run()
    at.checkbox(key=f"icheck_{first_action}").check().run()
    assert at.session_state["intervention_answer"] == "I'm not sure"
    assert at.session_state["intervention_checks"][first_action] is True
    # A plain rerun must not lose the selections.
    at.run()
    assert at.radio(key="intervention_answer_widget").value == "I'm not sure"
    assert at.checkbox(key=f"icheck_{first_action}").value is True
    assert not at.exception


def test_start_over_clears_demo_state():
    at = analyzed(app())
    at.radio(key="intervention_answer_widget").set_value("I'm not sure").run()
    next(b for b in at.button if b.label == "Check another message").click().run()
    assert at.session_state["interventions"] is None
    assert at.session_state["intervention_answer"] is None
    assert at.session_state["intervention_checks"] == {}
    assert at.session_state["stage"] == "submit"
    assert not at.exception


def test_authority_without_source_shows_fallback(monkeypatch):
    """A scenario whose authority card has no curated source shows the fallback note."""
    reminder_cards = integration.analyze_with_interventions(text=mock_data.REMINDER_MESSAGE, demo=True)[1]
    # Sanity: general scenario still has a source, so force a sourceless card to
    # exercise the UI branch deterministically.
    import copy
    bundle = copy.deepcopy(reminder_cards)
    bundle["interventions"]["authority"]["source"] = {"name": None, "label": None, "url": None}
    at = app()
    at.text_area(key="message").set_value(mock_data.REMINDER_MESSAGE).run()
    at.button(key="analyze").click().run()
    at.session_state["interventions"] = bundle
    at.run()
    assert any("No verified official source" in c.value for c in at.caption)
    assert not at.exception
