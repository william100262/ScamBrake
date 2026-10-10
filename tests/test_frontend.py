from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ui import integration, mock_data
from ui.validation import InputError, validate_image, validate_text, MAX_IMAGE_BYTES


@pytest.fixture(autouse=True)
def demo_environment(monkeypatch):
    monkeypatch.setenv("SCAMBRAKE_DEMO_MODE", "true")
    monkeypatch.delenv("SCAMBRAKE_VOICE_MODULE", raising=False)


def app():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    assert not at.exception
    return at


def button(at, label):
    return next(x for x in at.button if x.label == label)


def analyzed(at, text=mock_data.FAMILY_MESSAGE):
    at.text_area(key="message").set_value(text).run()
    at.button(key="analyze").click().run()
    assert not at.exception
    return at


@pytest.mark.parametrize("text", ["", "   \n", "x" * 5001])
def test_invalid_text(text):
    with pytest.raises(InputError):
        validate_text(text)


def test_text_limit_and_multiline():
    assert validate_text("x" * 5000) == "x" * 5000
    assert validate_text(" first\nsecond ") == "first\nsecond"


def image_bytes(fmt="PNG", size=(120, 80)):
    output = BytesIO()
    Image.new("RGB", size, "white").save(output, format=fmt)
    return output.getvalue()


@pytest.mark.parametrize("fmt,ext,mime", [("PNG", "png", "image/png"), ("JPEG", "jpg", "image/jpeg"), ("JPEG", "jpeg", "image/jpeg")])
def test_valid_images(fmt, ext, mime):
    result = validate_image(f"screenshot.{ext}", image_bytes(fmt))
    assert result["mime_type"] == mime
    assert result["width"] == 120


@pytest.mark.parametrize("name,data", [("test.gif", b"bad"), ("test.png", b"bad"), ("test.png", b""),
    ("test.png", b"x" * (MAX_IMAGE_BYTES + 1)), ("test.png", image_bytes("JPEG")),
    ("test.png", image_bytes(size=(20, 20))), ("test.png", image_bytes(size=(10001, 32)))],
    ids=["unsupported", "corrupt", "empty", "oversize", "mismatched-format", "too-small", "too-wide"])
def test_invalid_images(name, data):
    with pytest.raises(InputError):
        validate_image(name, data)


@pytest.mark.parametrize("text,risk", [(mock_data.FAMILY_MESSAGE, "high"), (mock_data.REMINDER_MESSAGE, "low"),
    (mock_data.MODERATE_MESSAGE, "moderate"), ("custom request", "unknown")])
def test_mock_contract(text, risk):
    result = integration.analyze_input(text=text)
    assert result["risk_level"] == risk
    assert integration.build_intervention(result)["recommended_actions"]
    assert all(signal["evidence"] is None or signal["evidence"] in text for signal in result["signals"])


def test_normalization():
    result = integration.normalize_analysis({"risk_level": ["high"], "summary": "Something", "signals": [None, {},
        {"title": "Warning", "explanation": "Explanation", "evidence": "invented quote"}], "requested_amount": 500}, "original message")
    assert result["risk_level"] == "unknown"
    assert result["requested_amount"] is None
    assert result["signals"][0]["evidence"] is None
    assert integration.normalize_analysis({})["risk_level"] == "unknown"
    assert integration.normalize_intervention({})["recommended_actions"]
    with pytest.raises(integration.ServiceError):
        integration.normalize_analysis(None)
    with pytest.raises(integration.ServiceError):
        integration.normalize_intervention("bad")


def test_live_missing_and_provider_failure(monkeypatch):
    monkeypatch.setenv("SCAMBRAKE_ANALYZER_MODULE", "missing_scamb_module")
    with pytest.raises(integration.ServiceError, match="unavailable"):
        integration.analyze_input(text="message", demo=False)
    def failed(**kwargs):
        raise RuntimeError("PRIVATE_API_KEY")
    monkeypatch.setitem(sys.modules, "test_analyzer", SimpleNamespace(analyze_input=failed))
    monkeypatch.setenv("SCAMBRAKE_ANALYZER_MODULE", "test_analyzer")
    with pytest.raises(integration.ServiceError) as error:
        integration.analyze_input(text="message", demo=False)
    assert "PRIVATE_API_KEY" not in str(error.value)


def test_direct_image_analysis_requires_confirmation(monkeypatch):
    calls = []
    monkeypatch.setattr(integration, "load_function", lambda *args: calls.append(args))
    for demo in (True, False):
        with pytest.raises(integration.ServiceError, match="review"):
            integration.analyze_input(image_bytes=b"image", mime_type="image/png", demo=demo)
    assert not calls


def test_home_validation_and_examples():
    at = app()
    assert any("Demo mode — simulated analysis" in x.value for x in at.caption)
    button(at, "How it works").click().run()
    assert at.session_state["show_how"]
    at.button(key="analyze").click().run()
    assert at.error
    at.button(key="family_example").click().run()
    assert at.text_area(key="message").value == mock_data.FAMILY_MESSAGE
    assert at.session_state["analysis"] is None
    at.button(key="analyze").click().run()
    assert at.session_state["stage"] == "results"
    assert len(at.session_state["analysis"]["signals"]) == 3
    assert not at.exception


@pytest.mark.parametrize("answer", ["yes", "no", "not_sure"])
def test_verification_and_restart(answer):
    at = analyzed(app())
    at.button(key="question_verify").click().run()
    assert at.session_state["stage"] == "results"
    at.radio(key="question_answer_independent_contact").set_value(answer).run()
    at.checkbox(key="action_check_saved_contact").check().run()
    at.button(key="question_verify").click().run()
    assert not any(r.key.startswith("question_answer_") for r in at.radio)
    at.button(key="question_verify").click().run()
    assert at.radio(key="question_answer_independent_contact").value == answer
    assert at.checkbox(key="action_check_saved_contact").value
    button(at, "Check another message").click().run()
    assert at.session_state["analysis"] is None
    assert at.session_state["question_answers"] == {}
    assert at.session_state["checklist_completion"] == {}
    assert at.text_area(key="message").value == ""
    at.button(key="reminder_example").click().run()
    at.button(key="analyze").click().run()
    assert at.session_state["analysis"]["risk_level"] == "low"
    assert not at.exception


def test_input_changes_clear_stale_state():
    at = app()
    at.session_state["analysis"] = mock_data.FAMILY
    at.session_state["intervention"] = {}
    at.text_area(key="message").set_value("a new request").run()
    assert at.session_state["analysis"] is None
    assert at.session_state["intervention"] is None
    at.radio(key="input_method").set_value("Upload a screenshot").run()
    assert at.session_state["stage"] == "submit"
    at.button(key="analyze").click().run()
    assert at.error
    assert not at.exception


@pytest.mark.parametrize("data,expected", [(image_bytes(), "results"), (b"corrupt", "submit")])
def test_screenshot_preview_and_submission(monkeypatch, data, expected):
    # AppTest has no file-uploader input API; inject an in-memory upload to test
    # the actual validation, preview, and submit path without persistent files.
    import streamlit as st
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: SimpleNamespace(name="screen.png", getvalue=lambda: data))
    import ocr
    from test_screenshots import detections
    monkeypatch.setattr(ocr, "_recognize", lambda image: detections(mock_data.FAMILY_MESSAGE))
    at = app()
    at.radio(key="input_method").set_value("Upload a screenshot").run()
    at.button(key="analyze").click().run()
    assert at.session_state["stage"] == expected
    if expected == "results":
        assert at.session_state["analysis"]["risk_level"] == "high"
        assert at.session_state["analysis"]["requested_amount"] == "$500"
    else:
        assert at.error
    assert not at.exception


def test_live_ui_error_and_retry(monkeypatch):
    monkeypatch.setenv("SCAMBRAKE_DEMO_MODE", "false")
    monkeypatch.setenv("SCAMBRAKE_ANALYZER_MODULE", "missing_scamb_module")
    at = analyzed(app())
    assert at.session_state["stage"] == "submit"
    assert at.error
    assert at.button(key="analyze").label == "Retry analysis"
    assert not at.session_state["busy"]


def test_untrusted_display(monkeypatch):
    untrusted = '<script>alert("x")</script> [click](https://untrusted.invalid)'
    monkeypatch.setattr(mock_data, "analyze_input", lambda **kwargs: {"risk_level": "high", "summary": untrusted,
        "signals": [{"title": untrusted, "explanation": untrusted, "evidence": None}], "claimed_sender": untrusted})
    at = analyzed(app())
    assert any(x.value == untrusted for x in at.text)
    assert not any(untrusted in x.value for x in at.markdown)
    assert not at.exception


@pytest.mark.parametrize("text,label", [(mock_data.MODERATE_MESSAGE, "Some concerns"), ("unrecognized input", "Unable to assess")])
def test_other_concern_screens(text, label):
    at = analyzed(app(), text)
    assert any(x.value == label for kind in (at.warning, at.info) for x in kind)
    if text == "unrecognized input":
        assert sum(x.value == "Not specified" for x in at.text) == 3
    assert not at.exception


def test_audio_is_explicit_and_persists(monkeypatch):
    calls = []
    def generate_audio(text):
        calls.append(text)
        return b"fake-mp3-for-ui-test"
    monkeypatch.setenv("SCAMBRAKE_VOICE_MODULE", "test_voice")
    monkeypatch.setitem(sys.modules, "test_voice", SimpleNamespace(generate_audio=generate_audio))
    at = analyzed(app())
    assert not calls
    button(at, "Listen to explanation").click().run()
    assert len(calls) == 1
    at.run()
    assert len(calls) == 1
    assert at.session_state["audio"] == b"fake-mp3-for-ui-test"
    assert not at.exception


def test_missing_intervention_and_audio_failure(monkeypatch):
    monkeypatch.setenv("SCAMBRAKE_INTERVENTION_MODULE", "missing_scamb_intervention")
    assert integration.build_intervention(mock_data.FAMILY, demo=False)["recommended_actions"]
    monkeypatch.setenv("SCAMBRAKE_VOICE_MODULE", "test_bad_voice")
    monkeypatch.setitem(sys.modules, "test_bad_voice", SimpleNamespace(generate_audio=lambda text: "bad audio"))
    with pytest.raises(integration.ServiceError, match="Audio is unavailable"):
        integration.get_audio("summary")
