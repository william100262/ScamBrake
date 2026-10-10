"""Fictional fixtures, not a scam detection implementation."""
from copy import deepcopy

FAMILY_MESSAGE = "Hey, it's Dad. My phone broke and I'm using a new number. I urgently need you to send $500 through Zelle. Please don't call me. Just send it now."
REMINDER_MESSAGE = "Hi Alex, just a reminder that your $75 invoice for tomorrow's tutoring session is due. You can use our usual payment method. Thanks!"
MODERATE_MESSAGE = "Hi, this is the event organizer. Please send the $40 registration fee by bank transfer today. We have changed our payment details."

FAMILY = {
    "risk_level": "high",
    "summary": "Multiple warning signs appear in this fictional request: a new number, pressure to send money, and a request not to call.",
    "signals": [
        {"type": "impersonation", "title": "An unfamiliar number claiming to be family", "evidence": "My phone broke and I'm using a new number.", "explanation": "A familiar name alone does not establish who is sending the message."},
        {"type": "urgency", "title": "Pressure to act immediately", "evidence": "Just send it now.", "explanation": "Urgency can make it harder to pause and check the request."},
        {"type": "discouraging_verification", "title": "Discouraging a phone call", "evidence": "Please don't call me.", "explanation": "Avoiding a call removes a useful opportunity to confirm the sender's identity."},
    ],
    "requested_amount": "$500", "payment_method": "Zelle", "claimed_sender": "Dad",
}
REMINDER = {
    "risk_level": "low",
    "summary": "This fictional reminder refers to a scheduled session and a usual payment method, without strong pressure or secrecy. That does not establish legitimacy.",
    "signals": [], "requested_amount": "$75", "payment_method": "Usual payment method (not named)", "claimed_sender": "Tutoring provider (not named)",
}
MODERATE = {
    "risk_level": "moderate",
    "summary": "The changed payment details in this fictional request deserve a quick independent check before paying.",
    "signals": [{"type": "payment_method", "title": "Payment details have changed", "evidence": "We have changed our payment details.", "explanation": "Confirm the new recipient using contact information you already trust."}],
    "requested_amount": "$40", "payment_method": "Bank transfer", "claimed_sender": "Event organizer",
}
UNKNOWN = {
    "risk_level": "unknown",
    "summary": "This is a generic demo simulation. Your submitted content has not been analyzed by AI. Live analysis requires Mistral or LM Studio.",
    "signals": [], "requested_amount": None, "payment_method": None, "claimed_sender": None,
}


def analyze_input(text="", image_bytes=None, mime_type=None):
    fixtures = {FAMILY_MESSAGE: FAMILY, REMINDER_MESSAGE: REMINDER, MODERATE_MESSAGE: MODERATE}
    return deepcopy(fixtures.get(text.strip(), UNKNOWN))


def build_intervention(analysis):
    if analysis["claimed_sender"] == "Dad":
        return {"question": "Have you called your dad using the phone number you already had saved?", "context": "A call to a known number helps confirm identity without relying on the new number in this request.", "recommended_actions": ["Call your dad using the phone number already stored in your contacts.", "Confirm the requested amount and recipient during that conversation.", "Wait to send money until you have independently confirmed the request."]}
    return {"question": "Have you confirmed the request using contact information you already trust?", "context": "A quick check with the sender can help confirm the amount, recipient, and reason for payment.", "recommended_actions": ["Use saved contact details or independently find the organization's official contact information.", "Confirm the payment amount and recipient with the sender before paying."]}
