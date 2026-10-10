"""Questions about an independent verification step, not accusations."""
from .context import normalize
from .templates import PLANS


def build(analysis: dict) -> dict:
    context = normalize(analysis)
    message = PLANS[context.path].question
    if context.path == "invoice_fraud" and "changed_details" in context.concepts:
        message = "Have you confirmed the changed payment details with your usual contact at the supplier?"
    return {"title": "Pause and Think", "message": message, "options": [
        {"id": "yes", "label": "Yes, I verified independently"},
        {"id": "no", "label": "No, I haven't verified"},
        {"id": "unsure", "label": "I'm not sure"},
    ]}
