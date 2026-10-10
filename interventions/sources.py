"""Curated official guidance, checked 2026-10-10; never fetched at runtime."""
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class Source:
    name: str
    label: str
    url: str
    guidance: str


SOURCES = MappingProxyType({
    "family": Source("Federal Trade Commission", "Scammers Use Fake Emergencies To Steal Your Money",
        "https://consumer.ftc.gov/articles/scammers-use-fake-emergencies-steal-your-money",
        "FTC guidance recommends checking a claimed family emergency by contacting the person through a known number and asking another trusted family member."),
    "phishing": Source("Federal Trade Commission", "How To Recognize and Avoid Phishing Scams",
        "https://consumer.ftc.gov/articles/how-recognize-avoid-phishing-scams",
        "FTC guidance recommends checking a message with the organization through a phone number or website you already trust, instead of contact details supplied in the message."),
    "invoice": Source("Federal Bureau of Investigation", "Business Email Compromise",
        "https://www.fbi.gov/how-we-can-help-you/common-frauds-and-scams/business-email-compromise",
        "FBI guidance recommends verifying payment requests and changes to account numbers or payment procedures directly with the known contact."),
    "gift_cards": Source("Federal Trade Commission", "Avoiding and Reporting Gift Card Scams",
        "https://consumer.ftc.gov/articles/avoiding-and-reporting-gift-card-scams",
        "FTC guidance warns against paying someone who demands gift cards and sharing the card numbers or PINs."),
    "general": Source("Federal Trade Commission", "How To Avoid a Scam",
        "https://consumer.ftc.gov/articles/how-avoid-scam",
        "FTC guidance recommends checking requests using contact information obtained independently and taking time to consider a request before acting."),
})


def source_fields(key):
    source = SOURCES.get(key)
    return ({"name": source.name, "label": source.label, "url": source.url} if source
            else {"name": None, "label": None, "url": None})
