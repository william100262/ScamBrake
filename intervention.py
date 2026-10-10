"""Frontend-independent intervention API and the existing Pause & Verify adapter."""
from interventions.context import normalize
from interventions.contract import validate_bundle, validate_strategy
from interventions.registry import STRATEGIES, build_strategy as _build_strategy

__all__ = ["build_interventions", "build_strategy", "build_intervention"]


def build_interventions(analysis: dict) -> dict:
    """Return all four cards in Denise's agreed schema; never mutate analysis."""
    context = normalize(analysis)
    result = {"scenario": context.scenario, "risk_level": context.risk_level,
              "interventions": {name: factory(analysis) for name, factory in STRATEGIES.items()}}
    validate_bundle(result)
    return result


def build_strategy(strategy: str, analysis: dict) -> dict:
    """Return one card. Unknown strategy names raise a fixed, safe ValueError."""
    result = _build_strategy(strategy, analysis)
    validate_strategy(strategy, result)
    return result


def build_intervention(analysis: dict) -> dict:
    """Legacy question/context/action-list shape, including UI risk aliases.

    The old UI drops scenario. Do not guess it from names or free-form prose.
    Signals still support general verification; Denise should pass raw analyzer
    output to build_interventions for full scenario-specific cards.
    """
    raw = analysis if isinstance(analysis, dict) else {}
    adapted = {key: raw.get(key) for key in ("scenario", "risk_level", "signals", "requested_amount", "payment_method", "claimed_sender", "explanation")}
    risk = adapted["risk_level"]
    if isinstance(risk, str):
        adapted["risk_level"] = {"moderate": "medium", "unknown": "uncertain"}.get(risk, risk)
    cards = build_interventions(adapted)["interventions"]
    return {"question": cards["questioning"]["message"],
            "context": cards["diversion"]["message"],
            "recommended_actions": [action["label"] for action in cards["diversion"]["actions"]]}
