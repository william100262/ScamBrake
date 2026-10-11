"""The only boundary between the frontend and teammates' service modules."""
from importlib import import_module
from copy import deepcopy
from os import environ
from . import mock_data


def extract_screenshot(data, name):
    """Local OCR only: never call an AI provider or cache private image content."""
    from ocr import extract_text
    return extract_text(data, name)


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
        # Confirmed screenshot text and pasted text are equally authoritative.
        if source_text is None or (evidence and evidence not in source_text):
            evidence = None
        signals.append({"type": clean_text(item.get("type"), "other", 100), "title": title, "explanation": explanation, "evidence": evidence})
    return {"scenario": clean_text(raw.get("scenario"), "unknown", 100), "risk_level": risk, "summary": summary, "signals": signals,
            **{key: clean_text(raw.get(key), limit=300) or None for key in ("requested_amount", "payment_method", "claimed_sender")}}


def normalize_intervention(raw):
    if not isinstance(raw, dict):
        raise ServiceError("The verification service returned an unreadable response. Please try again.")
    entries = raw.get("recommended_actions")
    actions = [clean_text(item, limit=1000) for item in entries if isinstance(item, str) and item.strip()] if isinstance(entries, list) else []
    return {"question": clean_text(raw.get("question"), "Have you confirmed the request using contact information you already trust?"),
            "context": clean_text(raw.get("context"), "Use an independent contact channel to confirm the amount and recipient before paying."),
            "recommended_actions": actions or ["Contact the sender using saved details or contact information you find independently.", "Confirm the amount and recipient before sending money."]}


def _adapt_analyzer_output(raw):
    """Map analyzer.analyze_input() output onto the frontend's raw shape.

    The analyzer's seven-field contract is left intact for teammates' modules; a
    new dict is built here (never mutating `raw`). normalize_analysis() then does
    the exact-substring evidence check and final cleaning.
    """
    if not isinstance(raw, dict):
        raise ServiceError("The analysis service returned an unreadable response. Please try again.")
    risk_map = {"medium": "moderate", "uncertain": "unknown"}
    risk = raw.get("risk_level")
    risk = risk_map.get(risk, risk)
    signals = []
    for item in raw.get("signals") if isinstance(raw.get("signals"), list) else []:
        if not isinstance(item, dict):
            continue
        sig_type = item.get("type")
        if not isinstance(sig_type, str) or not sig_type.strip():
            continue
        title = sig_type.replace("_", " ").strip().capitalize()
        explanation = f'The message shows a possible "{title.lower()}" indicator worth verifying before paying.'
        signals.append({"type": sig_type, "title": title, "explanation": explanation, "evidence": item.get("evidence")})
    return {"scenario": raw.get("scenario"), "risk_level": risk, "summary": raw.get("explanation"), "signals": signals,
            **{key: raw.get(key) for key in ("requested_amount", "payment_method", "claimed_sender")}}


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
    if image_bytes is not None:
        raise ServiceError("Extract and review the screenshot text before analyzing it.")
    if demo:
        try:
            raw = mock_data.analyze_input(text=text, image_bytes=image_bytes, mime_type=mime_type)
        except Exception:
            raise ServiceError("We couldn't analyze your request right now. Please retry in a moment.") from None
        result = normalize_analysis(raw, source_text=text)
        result["analyzer_result"] = deepcopy(raw)
        return result

    # Live text mode -> call the real analyzer backend (analyzer.analyze_input(text))
    # and adapt its seven-field output to the frontend shape.
    analyze = load_function("SCAMBRAKE_ANALYZER_MODULE", "analyzer", "analyze_input")
    try:
        raw = analyze(text)
    except Exception:
        raise ServiceError("We couldn't analyze your request right now. Please retry in a moment.") from None
    result = normalize_analysis(_adapt_analyzer_output(raw), source_text=text)
    # Retain the original seven fields for deterministic intervention consumers.
    result["analyzer_result"] = deepcopy(raw)
    return result


def build_intervention(analysis, *, demo=True):
    if not demo:
        # Live mode: use a configured intervention module if one exists; otherwise
        # fall back to safe generic guidance so live analysis still completes.
        try:
            provider = load_function("SCAMBRAKE_INTERVENTION_MODULE", "intervention", "build_intervention")
        except ServiceError:
            return normalize_intervention({})
    else:
        provider = mock_data.build_intervention
    try:
        raw = provider(analysis)
    except Exception:
        raise ServiceError("We couldn't prepare the verification steps. Please retry in a moment.") from None
    return normalize_intervention(raw)


def audio_available():
    return bool(environ.get("SCAMBRAKE_VOICE_MODULE"))


def prepare_questionnaire(original_analysis):
    """Load the proposed backend API; visibly mocked only if it is absent."""
    module_name = environ.get("SCAMBRAKE_INTERVENTION_MODULE", "intervention")
    try:
        provider = import_module(module_name)
    except ModuleNotFoundError as exc:
        # A missing dependency inside an existing backend is an integration error.
        if exc.name != module_name:
            raise ServiceError("The verification backend could not load. Please retry later.") from None
        provider = None
    except Exception:
        raise ServiceError("The verification backend could not load. Please retry later.") from None
    mocked = provider is None or not all(callable(getattr(provider, name, None)) for name in ("build_questionnaire", "review_questionnaire"))
    if mocked:
        from . import questionnaire_mock as provider
    try:
        questionnaire = provider.build_questionnaire(deepcopy(original_analysis))
        questions = questionnaire["questions"]
        if not isinstance(questions, list) or not 1 <= len(questions) <= 5:
            raise ValueError
        identifiers = []
        for question in questions:
            if not isinstance(question, dict):
                raise ValueError
            identifier, text = question.get("id"), question.get("text")
            if not isinstance(identifier, str) or not identifier.strip() or len(identifier) > 200:
                raise ValueError
            if not isinstance(text, str) or not text.strip():
                raise ValueError
            identifiers.append(identifier)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError
        return {"questionnaire": deepcopy(questionnaire), "mock": mocked, "provider": module_name}
    except Exception:
        raise ServiceError("Verification questions are unavailable right now. Please retry.") from None


def review_answers(bundle, answers):
    """Validate transport, delegate all wording and conclusions to the backend."""
    questionnaire = bundle["questionnaire"]
    ids = {q["id"] for q in questionnaire["questions"]}
    if set(answers) != ids or any(value not in ("yes", "no", "not_sure") for value in answers.values()):
        raise ServiceError("Answer every verification question before reviewing.")
    try:
        if bundle["mock"]:
            from . import questionnaire_mock as provider
        else:
            provider = import_module(bundle["provider"])
        feedback = provider.review_questionnaire(deepcopy(questionnaire), deepcopy(answers))
        if not isinstance(feedback, dict):
            raise ValueError
        for key in ("headline", "summary"):
            if not isinstance(feedback.get(key), str) or not feedback[key].strip():
                raise ValueError
        for key in ("concerns", "recommended_actions"):
            if not isinstance(feedback.get(key), list) or not all(isinstance(item, str) for item in feedback[key]):
                raise ValueError
        return deepcopy(feedback)
    except Exception:
        raise ServiceError("We couldn't review your answers right now. Please retry.") from None


def get_audio(text):
    provider = load_function("SCAMBRAKE_VOICE_MODULE", "voice", "generate_audio")
    try:
        audio = provider(text)
        if not isinstance(audio, bytes) or not audio or len(audio) > 20 * 1024 * 1024:
            raise ValueError
        return audio
    except Exception:
        raise ServiceError("Audio is unavailable right now. You can still read the explanation below.") from None
