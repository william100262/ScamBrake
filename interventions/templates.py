"""Scenario-specific questions and actions. Wording never embeds untrusted data."""
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class Plan:
    question: str
    message: str
    actions: tuple[tuple[str, str], ...]


PLANS = MappingProxyType({
    "family_emergency": Plan(
        "Have you contacted your family member using a phone number you trusted before receiving this message?",
        "Check the claimed emergency through family contacts you already trust before deciding whether to pay.",
        (("call_relative", "Call the family member using a previously saved phone number."),
         ("confirm_family", "Ask another trusted family member to help check the story."),
         ("pause_payment", "Wait to send money until you have independently checked the request."))),
    "bank_impersonation": Plan(
        "Have you checked this request through your bank's official app or the number printed on your bank card?",
        "Check the request directly with your bank using an established channel.",
        (("open_bank_app", "Open your bank's official app independently and check for the request."),
         ("call_bank", "Call the number printed on your bank card."),
         ("use_known_contact", "Use established bank contact details instead of any details supplied with the request."))),
    "invoice_fraud": Plan(
        "Have you confirmed the invoice and payment details with your usual contact at the supplier?",
        "Confirm the invoice and intended recipient with the supplier through an established contact.",
        (("contact_supplier", "Call your usual supplier contact using a previously established number."),
         ("confirm_payment_details", "Confirm the account details and invoice with that contact before paying."),
         ("pause_payment", "Wait to make the payment until those details have been independently checked."))),
    "suspicious_payment": Plan(
        "Have you independently confirmed the recipient, purpose, and payment method for this request?",
        "Check the recipient and payment instructions through contact details you already trust.",
        (("verify_recipient", "Contact the intended recipient through previously trusted details."),
         ("confirm_payment", "Confirm the reason, amount, and payment method before deciding whether to pay."),
         ("pause_payment", "Wait to send money until the request has been independently checked."))),
    "link": Plan(
        "Have you checked the request through the organization's official website or app instead of following the message's link?",
        "Check the request through an official channel you open independently.",
        (("avoid_link", "Leave the message's link unopened while you verify the request."),
         ("open_official_channel", "Open the organization's official app or use a previously trusted website bookmark."),
         ("confirm_request", "Check the claimed request through that channel or an established contact."))),
    "general": Plan(
        "Have you independently verified the identity of the sender and the request?",
        "An independent check can clarify the request. ScamBrake has not verified it for you.",
        (("verify_sender", "Contact the sender using previously trusted contact information."),
         ("confirm_request", "Confirm what is being requested and why through that independent channel."),
         ("protect_information", "Before sending money or sensitive information, independently verify the request. Never share passwords or verification codes."))),
})
