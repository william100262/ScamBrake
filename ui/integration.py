"""The only boundary between the frontend and teammates' service modules."""
from importlib import import_module
from os import environ
from . import mock_data


class ServiceError(RuntimeError):
    """Contains only safe public messages, never provider exception text."""


def demo_enabled():
    value = environ.get("SCAMBRAKE_DEMO_MODE", "true").strip().lower()
    if value not in {"true", "false", "1", "0", "yes", "no"}:
        raise ServiceError("SCAMBRAKE_DEMO_MODE must be true or false. Ask the app owner to correct the configuration.")
    return value in {"true", "1", "yes"}


def clean_text(value, fallback="", limit=6000):
    return value.strip()[:limit] if isinstance(value, str) and value.strip() else fallback


def normalize_analysis(raw, source_text=None):
    if not isinstance(raw, dict):
        raise ServiceError("The analysis service returned an unreadable response. Please try again.")
    risk = raw.get("risk_level")
    risk = risk if risk in ("high", "moderate", "low", "unknown") else "unknown"
    summary = clean_text(raw.get("summary"))
    if not summary:
        risk, summary = "unknown", "The analysis did not include an explanation. Please verify the request independently."
    signals = []
    entries = raw.get("signals")
    for item in entries if isinstance(entries, list) else []:
        if not isinstance(item, dict):
            continue
        title = clean_text(item.get("title"), limit=200)
        explanation = clean_text(item.get("explanation"))
        if not title or not explanation:
            continue
        evidence = clean_text(item.get("evidence")) or None
        # Text-mode quotes must appear in the actual submitted text. For images,
        # omit quotes until the service contract includes independently usable OCR.
        if source_text is None or (evidence and evidence not in source_text):
            evidence = None
        signals.append({"type": clean_text(item.get("type"), "other", 100), "title": title, "explanation": explanation, "evidence": evidence})
    return {"risk_level": risk, "summary": summary, "signals": signals,
            **{key: clean_text(raw.get(key), limit=300) or None for key in ("requested_amount", "payment_method", "claimed_sender")}}


def normalize_intervention(raw):
    if not isinstance(raw, dict):
        raise ServiceError("The verification service returned an unreadable response. Please try again.")
    entries = raw.get("recommended_actions")
    actions = [clean_text(item, limit=1000) for item in entries if isinstance(item, str) and item.strip()] if isinstance(entries, list) else []
    return {"question": clean_text(raw.get("question"), "Have you confirmed the request using contact information you already trust?"),
            "context": clean_text(raw.get("context"), "Use an independent contact channel to confirm the amount and recipient before paying."),
            "recommended_actions": actions or ["Contact the sender using saved details or contact information you find independently.", "Confirm the amount and recipient before sending money."]}


def load_function(module_env, default_module, function_name):
    try:
        module = import_module(environ.get(module_env, default_module))
        function = getattr(module, function_name)
        if not callable(function):
            raise TypeError
        return function
    except Exception:
        raise ServiceError(f"Live {default_module} integration is unavailable. Ask the app owner to connect it, then retry.") from None


def analyze_input(text="", image_bytes=None, mime_type=None, *, demo=True):
    provider = mock_data.analyze_input if demo else load_function("SCAMBRAKE_ANALYZER_MODULE", "analyzer", "analyze_input")
    try:
        raw = provider(text=text, image_bytes=image_bytes, mime_type=mime_type)
    except Exception:
        raise ServiceError("We couldn't analyze your request right now. Please retry in a moment.") from None
    return normalize_analysis(raw, source_text=text if image_bytes is None else None)


def build_intervention(analysis, *, demo=True):
    provider = mock_data.build_intervention if demo else load_function("SCAMBRAKE_INTERVENTION_MODULE", "intervention", "build_intervention")
    try:
        raw = provider(analysis)
    except Exception:
        raise ServiceError("We couldn't prepare the verification steps. Please retry in a moment.") from None
    return normalize_intervention(raw)


def audio_available():
    return bool(environ.get("SCAMBRAKE_VOICE_MODULE"))


def get_audio(text):
    provider = load_function("SCAMBRAKE_VOICE_MODULE", "voice", "generate_audio")
    try:
        audio = provider(text)
        if not isinstance(audio, bytes) or not audio or len(audio) > 20 * 1024 * 1024:
            raise ValueError
        return audio
    except Exception:
        raise ServiceError("Audio is unavailable right now. You can still read the explanation below.") from None
