"""Confidence regressions: native Tesseract images and deterministic TSV cases."""
from io import BytesIO
from pathlib import Path
import random
from unittest.mock import Mock

import pytest
from PIL import Image, ImageDraw, ImageFont
import ocr
from test_screenshots import detections, engine, screenshot, setup_upload, MESSAGE

FIXTURES = Path(__file__).parent / "fixtures" / "ocr"


@pytest.fixture(autouse=True)
def default_thresholds(monkeypatch):
    for name in ("WORD_CONFIDENCE", "LINE_CONFIDENCE", "SINGLE_WORD_CONFIDENCE", "RELIABLE_FRACTION"):
        monkeypatch.delenv("SCAMBRAKE_OCR_" + name, raising=False)


@pytest.mark.parametrize("text", ["OK", "No", "$5", "Pay now", "Zelle", "J8ke", "https://examp1e.com/pay", "李明"])
def test_short_confident_tokens_need_no_dictionary(text):
    assert ocr._filter_detections(detections(text)) == text


@pytest.mark.parametrize("text", ["OK", "Pay now", "Send $5"])
def test_real_short_messages(engine, text):
    assert ocr.extract_text(screenshot(text=text)) == text


def bank_image(fmt):
    # Phone-style screenshot: header, chat bubble, multiple message lines.
    image = Image.new("RGB", (820, 720), "#f2f3f5")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", 30)
    draw.text((35, 35), "Example Bank", font=font, fill="black")
    draw.rounded_rectangle((20, 130, 800, 620), radius=25, fill="white")
    draw.multiline_text((40, 165), "Example Bank fraud alert:\nA Zelle transaction of $3,500\nwas requested from your account.\nReply YES to approve or NO to decline.\nDo not share your security code.",
                        font=font, spacing=22, fill="black")
    output = BytesIO()
    image.save(output, format=fmt)
    return output.getvalue()


@pytest.mark.parametrize("fmt,ext", [("PNG", "png"), ("JPEG", "jpg"), ("WEBP", "webp")])
def test_real_bank_alert_preserves_details(engine, fmt, ext):
    result = ocr.extract_text(bank_image(fmt), "bank." + ext)
    for exact in ("Example Bank", "Zelle", "$3,500", "Reply YES to approve or NO to decline.", "Do not share your security code."):
        assert exact in result


@pytest.mark.parametrize("name", ["coffee.png", "astronaut.png"])
def test_real_photographs_rejected(engine, name):
    assert ocr.extract_text((FIXTURES / name).read_bytes(), name) == ""


def test_photo_reproduces_old_false_positive(engine):
    # Keep a realistic negative that actually exercises filtering, not just an
    # image on which the engine produces nothing. No text contents are logged.
    with ocr._prepare((FIXTURES / "coffee.png").read_bytes()) as image:
        raw = ocr._recognize(image)
    old_text = " ".join(raw["text"])
    assert sum(c.isalnum() for c in old_text) >= 3
    assert ocr._filter_detections(raw) == ""


def test_real_noise_rejected(engine):
    rng = random.Random(123)
    image = Image.frombytes("L", (500, 300), rng.randbytes(500 * 300))
    output = BytesIO()
    image.save(output, format="PNG")
    assert ocr.extract_text(output.getvalue()) == ""


@pytest.mark.parametrize("confidence", [0, 25, 59.9, -1, "nan", "inf", 101, "invalid"])
def test_low_or_invalid_confidences_rejected(confidence):
    assert ocr._filter_detections(detections("Lots of supposed message words", confidence)) == ""


def test_mixed_confidence_filters_before_reconstruction():
    data = detections("Jake requests $3,500 xyzz Zelle now\nReply NO")
    data["conf"][3] = 12
    assert ocr._filter_detections(data) == "Jake requests $3,500 Zelle now\nReply NO"


def test_confident_accident_amid_noise_rejected():
    data = detections("noise noise noise noise noise\nOK", 20)
    data["conf"][-1] = 96
    assert ocr._filter_detections(data) == ""


def test_low_line_average_rejected():
    assert ocr._filter_detections(detections("Send funds now", 65)) == ""


def test_isolated_word_needs_more_confidence():
    assert ocr._filter_detections(detections("OK", 89)) == ""
    assert ocr._filter_detections(detections("OK", 90)) == "OK"


@pytest.mark.parametrize("text", ["!!! ### ///", "\ufffd\ufffd\ufffd", "a|||||||| b~~~~~~~~", "te\x00xt"])
def test_character_noise_rejected_even_at_high_confidence(text):
    assert ocr._filter_detections(detections(text)) == ""


def test_inconsistent_line_layout_rejected():
    data = detections("some supposed words")
    data["top"] = [0, 200, 400]
    assert ocr._filter_detections(data) == ""


def test_structural_records_do_not_count_as_rejected_words():
    data = detections("header\nOK")
    data["level"][0] = 4
    data["conf"][0] = -1
    assert ocr._filter_detections(data) == "OK"


def test_line_order_preserved():
    data = detections("First line\nSecond line\nThird line")
    assert ocr._filter_detections(data) == "First line\nSecond line\nThird line"


@pytest.mark.parametrize("setting,value,text,score,expected", [
    ("WORD_CONFIDENCE", "95", "Send now", 94, ""),
    ("LINE_CONFIDENCE", "70", "Send now", 75, "Send now"),
    ("SINGLE_WORD_CONFIDENCE", "85", "OK", 86, "OK"),
    ("RELIABLE_FRACTION", "0.9", "Send now noise", 96, ""),
])
def test_configurable_thresholds(monkeypatch, setting, value, text, score, expected):
    monkeypatch.setenv("SCAMBRAKE_OCR_" + setting, value)
    data = detections(text, score)
    if setting == "RELIABLE_FRACTION":
        data["conf"][-1] = 10
    assert ocr._filter_detections(data) == expected


@pytest.mark.parametrize("value", ["garbage", "nan", "inf", "0", "-1", "101"])
def test_invalid_configuration_fails_safely(monkeypatch, value):
    monkeypatch.setenv("SCAMBRAKE_OCR_WORD_CONFIDENCE", value)
    with pytest.raises(ocr.OCRError, match="settings are invalid"):
        ocr._filter_detections(detections("OK"))


@pytest.mark.parametrize("data", [None, {}, {"text": []}])
def test_malformed_engine_results_fail_safely(data):
    with pytest.raises(ocr.OCRError, match="unreadable result"):
        ocr._filter_detections(data)


def test_unreliable_ui_preview_manual_entry_and_confirmation(monkeypatch):
    at, upload, extract, analyze = setup_upload(monkeypatch, extracted="")
    assert at.text_area(key="ocr_text").value == ""
    assert any(w.value == ocr.UNREADABLE_MESSAGE for w in at.warning)
    assert at.get("image") or at.get("imgs")
    analyze.assert_not_called()
    at.button(key="analyze").click().run()
    analyze.assert_not_called()
    at.text_area(key="ocr_text").set_value(MESSAGE).run()
    analyze.assert_not_called()
    at.button(key="analyze").click().run()
    analyze.assert_called_once_with(MESSAGE)
    assert at.session_state["stage"] == "results"
    assert not at.exception


def test_real_photo_ui_does_not_expose_garbage(engine, monkeypatch):
    import streamlit as st
    import analyzer
    from types import SimpleNamespace
    from streamlit.testing.v1 import AppTest
    from test_screenshots import ROOT
    monkeypatch.setenv("SCAMBRAKE_DEMO_MODE", "false")
    data = (FIXTURES / "coffee.png").read_bytes()
    monkeypatch.setattr(st, "file_uploader", lambda *a, **kw: SimpleNamespace(name="coffee.png", getvalue=lambda: data))
    analyze = Mock()
    monkeypatch.setattr(analyzer, "analyze_input", analyze)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    at.radio(key="input_method").set_value("Upload a screenshot").run()
    assert at.text_area(key="ocr_text").value == ""
    assert any(w.value == ocr.UNREADABLE_MESSAGE for w in at.warning)
    assert at.get("image") or at.get("imgs")
    at.button(key="analyze").click().run()
    analyze.assert_not_called()
    assert not at.exception
