"""Tests for analyzer.py's Gemini integration, parsing, and error handling.

No real API calls are made: the Gemini client factory is replaced with a fake,
so these run without the google-genai package installed and without a network.
Written to run under either `pytest` or `python -m unittest`.
"""

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import analyzer  # noqa: E402

MESSAGE = (
    "Hi grandma, it's your grandson Jake. I need $2,500 for bail right away. "
    "Send it through Apple gift cards ASAP."
)


def _gemini_response(content):
    """Build a fake object shaped like a Gemini models.generate_content() response."""
    return SimpleNamespace(text=content)


def _fake_client(content=None, exc=None):
    """A stand-in Gemini client whose models.generate_content returns content or raises."""

    def complete(**kwargs):
        if exc is not None:
            raise exc
        return _gemini_response(content)

    return SimpleNamespace(models=SimpleNamespace(generate_content=complete), close=mock.Mock())


class GeminiProviderTests(unittest.TestCase):
    def setUp(self):
        # Force the Gemini provider with a dummy key for every test here.
        env = mock.patch.dict(
            analyzer.os.environ,
            {"SCAMBRAKE_AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"},
        )
        env.start()
        self.addCleanup(env.stop)

    def _patch_client(self, **kwargs):
        patcher = mock.patch.object(
            analyzer, "_gemini_client", return_value=_fake_client(**kwargs)
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_valid_response_is_parsed_and_coerced(self):
        payload = {
            "scenario": "family_emergency",
            "risk_level": "high",
            "signals": [
                {"type": "urgency", "evidence": "right away"},
                {"type": "gift_card", "evidence": "Apple gift cards"},
            ],
            "requested_amount": "$2,500",
            "payment_method": "Apple gift cards",
            "claimed_sender": "grandson Jake",
            "explanation": "Possible scam indicators are present.",
        }
        self._patch_client(content=json.dumps(payload))

        result = analyzer.analyze_input(MESSAGE)

        self.assertEqual(result["scenario"], "family_emergency")
        self.assertEqual(result["risk_level"], "high")
        self.assertEqual(result["requested_amount"], "$2,500")
        self.assertEqual(result["payment_method"], "Apple gift cards")
        self.assertEqual(len(result["signals"]), 2)
        self.assertEqual(
            {s["evidence"] for s in result["signals"]},
            {"right away", "Apple gift cards"},
        )

    def test_fabricated_evidence_and_bad_enums_are_rejected(self):
        payload = {
            "scenario": "not_a_real_scenario",  # invalid -> unknown
            "risk_level": "extreme",            # invalid -> uncertain
            "signals": [
                {"type": "real", "evidence": "right away"},     # kept
                {"type": "fake", "evidence": "wire transfer"},  # not in message
                {"evidence": "Apple gift cards"},               # missing type
            ],
            "requested_amount": "$9,999",   # not in message -> dropped
            "payment_method": "Apple gift cards",  # present -> kept
            "claimed_sender": None,
            "explanation": "x",
        }
        self._patch_client(content=json.dumps(payload))

        result = analyzer.analyze_input(MESSAGE)

        self.assertEqual(result["scenario"], "unknown")
        self.assertEqual(result["risk_level"], "uncertain")
        self.assertEqual(result["signals"], [{"type": "real", "evidence": "right away"}])
        self.assertIsNone(result["requested_amount"])
        self.assertEqual(result["payment_method"], "Apple gift cards")

    def test_invalid_json_returns_safe_fallback(self):
        self._patch_client(content="Sure! Here is the analysis: not-json {")

        result = analyzer.analyze_input(MESSAGE)

        self.assertEqual(result, analyzer._empty_result(result["explanation"]))
        self.assertIn("not valid JSON", result["explanation"])

    def test_non_object_json_returns_safe_fallback(self):
        self._patch_client(content="[1, 2, 3]")

        result = analyzer.analyze_input(MESSAGE)

        self.assertEqual(result["scenario"], "unknown")
        self.assertIn("not a JSON object", result["explanation"])

    def test_empty_content_returns_safe_fallback(self):
        self._patch_client(content="")

        result = analyzer.analyze_input(MESSAGE)

        self.assertIn("empty response", result["explanation"])

    def test_api_failure_does_not_crash(self):
        self._patch_client(exc=RuntimeError("503 service unavailable"))

        result = analyzer.analyze_input(MESSAGE)

        self.assertEqual(result["scenario"], "unknown")
        self.assertEqual(result["risk_level"], "uncertain")
        self.assertIn("Gemini API request failed", result["explanation"])
        # The raw exception text must not leak through verbatim.
        self.assertNotIn("503 service unavailable", result["explanation"])

    def test_missing_api_key_reports_clearly(self):
        with mock.patch.dict(
            analyzer.os.environ, {"GEMINI_API_KEY": ""}, clear=False
        ):
            # Real factory (not patched) so the key check runs.
            result = analyzer.analyze_input(MESSAGE)
        self.assertIn("GEMINI_API_KEY", result["explanation"])


class EmptyInputTests(unittest.TestCase):
    def test_blank_text_short_circuits(self):
        for value in ("", "   ", None):
            result = analyzer.analyze_input(value)
            self.assertEqual(result["explanation"], "No message was submitted.")
            self.assertEqual(result["signals"], [])


class ProviderSelectionTests(unittest.TestCase):
    def _select(self, env):
        with mock.patch.dict(analyzer.os.environ, env, clear=True):
            return analyzer._select_provider()

    def test_defaults_to_gemini_when_key_present(self):
        self.assertEqual(self._select({"GEMINI_API_KEY": "k"}), "gemini")

    def test_defaults_to_lmstudio_without_key(self):
        self.assertEqual(self._select({}), "lmstudio")

    def test_explicit_lmstudio_overrides_key(self):
        env = {"GEMINI_API_KEY": "k", "SCAMBRAKE_AI_PROVIDER": "lmstudio"}
        self.assertEqual(self._select(env), "lmstudio")

    def test_explicit_gemini(self):
        self.assertEqual(self._select({"SCAMBRAKE_AI_PROVIDER": "gemini"}), "gemini")


if __name__ == "__main__":
    unittest.main()
