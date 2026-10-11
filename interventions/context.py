"""Bounded input normalization and explicit interpretation of analyzer signals."""
from dataclasses import dataclass
import re
from types import MappingProxyType

SCENARIOS = frozenset({"family_emergency", "bank_impersonation", "invoice_fraud", "suspicious_payment", "general", "unknown"})
RISK_LEVELS = frozenset({"low", "medium", "high", "uncertain"})
MAX_SIGNALS = 32
MAX_SIGNAL_TYPE = 64
MAX_EVIDENCE = 1000
MAX_DETAIL = 300
MAX_EXPLANATION = 6000

ALIASES = MappingProxyType({
    "urgency": "urgency", "urgent_request": "urgency", "urgency_pressure": "urgency",
    "immediate_action_required": "urgency",
    "secrecy": "secrecy", "secrecy_demand": "secrecy", "keep_secret": "secrecy",
    "impersonation": "impersonation", "identity_spoofing": "impersonation", "sender_impersonation": "impersonation",
    "threat": "threats", "threats": "threats", "account_threat": "threats",
    "suspicious_link": "link", "phishing_link": "link", "malicious_link": "link",
    "phishing": "phishing", "credential_request": "credentials", "credential_harvesting": "credentials",
    "gift_card": "gift_cards", "gift_cards": "gift_cards", "gift_card_payment": "gift_cards",
    "payment_method": "payment", "suspicious_payment": "payment", "unusual_payment_method": "payment",
    "changed_payment_details": "changed_details", "payment_redirection": "changed_details",
    "changed_bank_details": "changed_details", "invoice_redirection": "changed_details",
    "discouraging_verification": "avoid_verification", "avoid_verification": "avoid_verification",
})
_TYPE = re.compile(r"[A-Za-z][A-Za-z0-9_ -]{0,63}\Z")
_GIFT = re.compile(r"\bgift[ -]+cards?\b", re.I)
_LINK = re.compile(r"https?://\S+|\bwww\.\S+|\b(?:click|open|follow)\b.{0,40}\blink\b", re.I)
_CHANGED = re.compile(r"\b(?:changed?|new|different)\b.{0,40}\b(?:bank|account|payment)\b", re.I)


def bounded(value, limit):
    """Keep accepted strings verbatim; drop oversize strings, never cut quotes."""
    if not isinstance(value, str) or len(value) > limit or not value.strip():
        return None
    if any(not c.isprintable() and c not in "\n\r\t" for c in value):
        return None
    return value


@dataclass(frozen=True)
class Signal:
    type: str
    evidence: str
    concepts: frozenset[str]


@dataclass(frozen=True)
class Context:
    scenario: str
    risk_level: str
    signals: tuple[Signal, ...]
    requested_amount: str | None
    payment_method: str | None
    claimed_sender: str | None
    explanation: str | None
    concepts: frozenset[str]
    path: str

    @property
    def concerned(self):
        return self.risk_level in {"medium", "high"}


def normalize(analysis) -> Context:
    """Normalize ordinary malformed Python/JSON data without mutating it.

    Do not import analyzer: that module loads environment configuration. The
    enum parity test guards these copies without coupling this backend to AI.
    """
    raw = analysis if isinstance(analysis, dict) else {}
    scenario = bounded(raw.get("scenario"), 64)
    scenario = scenario if scenario in SCENARIOS else "unknown"
    risk = bounded(raw.get("risk_level"), 32)
    risk = risk if risk in RISK_LEVELS else "uncertain"
    signals = []
    entries = raw.get("signals")
    for item in entries[:MAX_SIGNALS] if isinstance(entries, list) else []:
        if not isinstance(item, dict):
            continue
        kind = bounded(item.get("type"), MAX_SIGNAL_TYPE)
        evidence = bounded(item.get("evidence"), MAX_EVIDENCE)
        if not kind or not evidence or not _TYPE.fullmatch(kind):
            continue
        canonical = ALIASES.get(kind.lower().replace("-", "_").replace(" ", "_"))
        concepts = {canonical} if canonical else set()
        # Inspect evidence only; never infer behavior from the free-form explanation.
        if _LINK.search(evidence):
            concepts.add("link")
        if canonical in {"payment", "gift_cards"} and _GIFT.search(evidence):
            concepts.add("gift_cards")
        if canonical == "payment" and _CHANGED.search(evidence):
            concepts.add("changed_details")
        signals.append(Signal(kind, evidence, frozenset(concepts)))
    details = {key: bounded(raw.get(key), MAX_DETAIL) for key in ("requested_amount", "payment_method", "claimed_sender")}
    concepts = set().union(*(s.concepts for s in signals))
    if details["payment_method"] and _GIFT.search(details["payment_method"]):
        concepts.add("gift_cards")
    path = "general"
    if risk in {"medium", "high"}:
        if scenario in {"family_emergency", "bank_impersonation", "invoice_fraud"}:
            path = scenario
        elif "link" in concepts:
            path = "link"  # Internal route, never an added analyzer scenario enum.
        elif scenario == "suspicious_payment":
            path = "suspicious_payment"
    return Context(scenario, risk, tuple(signals), **details,
                   explanation=bounded(raw.get("explanation"), MAX_EXPLANATION),
                   concepts=frozenset(concepts), path=path)
