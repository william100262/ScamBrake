"""Documented patterns gated by scenario/signals; never fake social proof."""
from .context import normalize

# Source keys correspond to the verified pages in sources.py; these are design
# mappings, not experimentally established scenario/strategy pairings.
PATTERNS = {
    "urgency": ("Pressure to act quickly is a documented scam tactic.", "general"),
    "secrecy": ("Requests for secrecy can discourage independent checks in documented emergency scams.", "family"),
    "impersonation": ("Impersonation scams use a claimed identity to gain trust.", "general"),
    "threats": ("Threats of adverse consequences can be used to pressure recipients in scams.", "general"),
    "link": ("Links identified in the analysis can resemble phishing attempts that steer recipients to an unverified channel.", "phishing"),
    "phishing": ("The phishing indicator in the analysis resembles documented attempts to obtain personal or financial information.", "phishing"),
    "credentials": ("Requests for sensitive account information resemble documented phishing tactics.", "phishing"),
    "gift_cards": ("Requests to pay with gift cards resemble a documented scam payment pattern.", "gift_cards"),
    "payment": ("The payment-related concern in the analysis is a reason to independently check the recipient and payment method.", "general"),
    "changed_details": ("Unexpected changes in payment instructions resemble a documented invoice-redirection tactic.", "invoice"),
    "avoid_verification": ("Discouraging independent contact can make a request harder to check, as in documented emergency scams.", "family"),
}
SCENARIO_PATTERNS = {
    "family_emergency": "Documented family-emergency scams involve someone posing as a relative who needs help. The scenario identified by the analysis warrants checking that possibility.",
    "bank_impersonation": "Documented bank-impersonation messages pose as a bank to gain trust. The scenario identified by the analysis warrants checking the sender independently.",
    "invoice_fraud": "Documented invoice scams can imitate a supplier's request. The invoice-fraud classification warrants checking that possibility.",
}
NEUTRAL = "The available analysis does not establish a matching scam pattern. You can clarify the request through an independent contact."


def build(analysis: dict) -> dict:
    context = normalize(analysis)
    if not context.concerned:
        return {"title": "Recognize the Scam Pattern", "message": NEUTRAL, "matched_signals": []}
    used = context.concepts.intersection(PATTERNS)
    parts = [SCENARIO_PATTERNS[context.path]] if context.path in SCENARIO_PATTERNS else []
    parts.extend(sentence for concept, (sentence, _) in PATTERNS.items() if concept in used)
    matched = list(dict.fromkeys(signal.type for signal in context.signals if signal.concepts.intersection(used)))
    return {"title": "Recognize the Scam Pattern",
            "message": " ".join(parts) + " These similarities do not establish that fraud occurred." if parts else NEUTRAL,
            "matched_signals": matched}
