"""Concrete recommendations; never visit or echo untrusted contact details."""
from .context import normalize
from .templates import PLANS


def build(analysis: dict) -> dict:
    context = normalize(analysis)
    plan = PLANS[context.path]
    actions = [{"id": key, "label": label} for key, label in plan.actions]
    if context.concerned and "changed_details" in context.concepts and context.path == "invoice_fraud":
        actions[1]["label"] = "Confirm the changed banking details with your usual supplier contact before paying."
    if context.concerned and "link" in context.concepts and context.path != "link":
        actions.append({"id": "avoid_link", "label": "Leave the message's link unopened; check the request through an official channel you open independently."})
    if context.concerned and "gift_cards" in context.concepts:
        actions.append({"id": "protect_gift_card_codes", "label": "Do not share gift card numbers or PINs in response to this request. Verify it independently first."})
    return {"title": "Take a Safer Step", "message": plan.message, "actions": actions}
