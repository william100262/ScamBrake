"""General institutional advice, never an endorsement or investigation claim."""
from .context import normalize
from .sources import SOURCES, source_fields


def build(analysis: dict) -> dict:
    context = normalize(analysis)
    key = {"family_emergency": "family", "bank_impersonation": "phishing", "invoice_fraud": "invoice", "link": "phishing"}.get(context.path)
    if key is None:
        key = "gift_cards" if context.concerned and "gift_cards" in context.concepts else "general"
    source = SOURCES.get(key)
    guidance = source.guidance if source else "Check the request through a previously trusted contact before acting."
    return {"title": "What Experts Recommend",
            "message": guidance + " This is general advice, not an assessment of this particular message by the institution.",
            "source": source_fields(key)}
