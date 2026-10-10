"""Validate the exact agreed JSON shape without external schema packages."""
import json
from .context import SCENARIOS, RISK_LEVELS, MAX_SIGNALS, MAX_SIGNAL_TYPE
from .sources import SOURCES

_FIELDS = {
    "questioning": {"title", "message", "options"},
    "authority": {"title", "message", "source"},
    "social_influence": {"title", "message", "matched_signals"},
    "diversion": {"title", "message", "actions"},
}


def _require(condition):
    if not condition:
        raise ValueError("Invalid intervention output contract.")


def _text(value, limit=3000):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def validate_strategy(name, card):
    _require(isinstance(card, dict) and set(card) == _FIELDS[name])
    _require(_text(card["title"], 100) and _text(card["message"]))
    if name in {"questioning", "diversion"}:
        items = card["options" if name == "questioning" else "actions"]
        _require(isinstance(items, list) and 1 <= len(items) <= 8)
        for item in items:
            _require(isinstance(item, dict) and set(item) == {"id", "label"})
            _require(_text(item["id"], 64) and _text(item["label"], 500))
        ids = [item["id"] for item in items]
        _require(len(set(ids)) == len(ids))
        if name == "questioning":
            _require(ids == ["yes", "no", "unsure"])
    elif name == "authority":
        source = card["source"]
        _require(isinstance(source, dict) and set(source) == {"name", "label", "url"})
        _require(all(v is None for v in source.values()) or any(
            source == {"name": s.name, "label": s.label, "url": s.url} for s in SOURCES.values()))
    else:
        matched = card["matched_signals"]
        _require(isinstance(matched, list) and len(matched) <= MAX_SIGNALS)
        _require(all(_text(item, MAX_SIGNAL_TYPE) for item in matched))


def validate_bundle(result):
    _require(isinstance(result, dict) and set(result) == {"scenario", "risk_level", "interventions"})
    _require(isinstance(result["scenario"], str) and result["scenario"] in SCENARIOS)
    _require(isinstance(result["risk_level"], str) and result["risk_level"] in RISK_LEVELS)
    cards = result["interventions"]
    _require(isinstance(cards, dict) and set(cards) == set(_FIELDS))
    for name, card in cards.items():
        validate_strategy(name, card)
    json.dumps(result, allow_nan=False)
