"""Deterministic, personalized verification questionnaire and answer review.

This module is additive and offline: it reuses ``context.normalize`` and the
shared ``templates`` wording, never calls the analyzer or network, and never
embeds untrusted analysis text (claimed sender, evidence, explanation) in its
output. Personalization is expressed purely as *which* fixed questions are
selected, mirroring how the existing strategies choose fixed templates.

Answer interpretation is driven by an internal registry keyed on stable question
IDs, so a malformed or untrusted questionnaire cannot dictate safety
conclusions: only IDs this module defines are ever interpreted.
"""
from dataclasses import dataclass
import re

from .context import normalize

__all__ = ["build_questionnaire", "review_questionnaire"]

# Answers never prove safety. Every review ends with this standing action.
_UNIVERSAL = "Do not send money or share sensitive details until the request is independently verified."

# Grounded government/agency-impersonation cues. Scanned only in the structured
# claimed-sender field and in signal evidence (never the free-form explanation),
# consistent with the engine's existing evidence-based concept detection. This
# selects neutral verification questions; it never produces an accusation and
# never recommends calling a specific agency.
_GOVERNMENT = re.compile(
    r"\b(?:irs|internal revenue|social security(?: administration)?|ssa|medicare|medicaid|"
    r"uscis|immigration|deportation|customs|border protection|"
    r"federal (?:agent|agency|bureau|marshal)|law enforcement|"
    r"arrest(?:ed)?|warrant|subpoena|"
    r"back taxes|unpaid taxes|taxes you owe|owe(?:d)? taxes|tax fraud|tax authority|"
    r"government (?:agency|grant|benefit)|stimulus (?:payment|check))\b",
    re.I,
)


@dataclass(frozen=True)
class _Question:
    """A fixed question plus the internal metadata used to interpret answers.

    ``kind`` is "verification" (a protective step the user may have taken; the
    concerning answer is "no") or "warning" (a possible scam indicator; the
    concerning answer is "yes"). ``gap``/``ok``/``unresolved`` are summary
    fragments; ``concern`` is a standalone concern sentence; ``remedy`` is a safe
    next step aligned with the Diversion wording.
    """
    id: str
    text: str
    explanation: str
    kind: str
    concern: str
    remedy: str
    gap: str
    ok: str
    unresolved: str


def _q(id, text, explanation, kind, concern, remedy, gap, ok, unresolved):
    return _Question(id, text, explanation, kind, concern, remedy, gap, ok, unresolved)


# Controlled registry: the only question IDs this backend will ever emit or
# interpret. IDs are stable; wording never contains submitted content.
QUESTIONS = {q.id: q for q in (
    # --- shared / neutral ---
    _q("independent_contact",
       "Have you contacted the person or organization using a phone number, app, or address you already trusted before this message?",
       "A previously trusted contact method helps confirm identity independently.",
       "verification",
       "The sender's identity has not been independently confirmed.",
       "Contact the person or organization through a phone number, app, or address you already trusted before this message.",
       "you have not contacted the sender through a previously trusted channel",
       "you have contacted the sender through a previously trusted channel",
       "you are not sure whether you have contacted the sender through a trusted channel"),
    _q("expected_request",
       "Were you expecting this request before it arrived?",
       "Unexpected requests are worth checking before you act.",
       "verification",
       "This request was unexpected, which is a reason to check it before acting.",
       "If the request was unexpected, confirm it through a contact you already trust before acting.",
       "this request was not expected",
       "you were expecting this request",
       "you are not sure whether you were expecting this request"),
    _q("sender_identity_known",
       "Do you already know and trust the sender of this message?",
       "Knowing the sender is a starting point, though it does not by itself confirm the request.",
       "verification",
       "The sender is not someone you already know and trust.",
       "If you are unsure who sent this, confirm their identity through a channel you already trust.",
       "you do not already know and trust the sender",
       "you already know and trust the sender",
       "you are not sure whether you know and trust the sender"),
    _q("pressure_urgency",
       "Are you being pressured to act immediately, before you can check the request?",
       "Urgency can make it harder to pause and verify.",
       "warning",
       "Pressure to act immediately is a reason to slow down and verify.",
       "Give yourself time to check the request; a genuine request can wait for verification.",
       "the message pressures you to act immediately",
       "the message does not pressure you to act immediately",
       "you are not sure whether the message pressures you to act immediately"),
    _q("requests_sensitive_info",
       "Does the message ask you to share passwords, verification codes, or payment details?",
       "Legitimate organizations do not ask you to share passwords or one-time codes.",
       "warning",
       "A request for passwords, codes, or payment details is a common scam indicator.",
       "Do not share passwords, verification codes, or payment details in response to this message.",
       "the message asks for passwords, codes, or payment details",
       "the message does not ask for passwords, codes, or payment details",
       "you are not sure whether the message asks for passwords, codes, or payment details"),
    _q("unusual_payment_method",
       "Are you being asked to pay in an unusual way, such as gift cards, a wire transfer, or cryptocurrency?",
       "Hard-to-reverse payment methods are common in scams.",
       "warning",
       "An unusual, hard-to-reverse payment method is a common scam indicator.",
       "Be cautious with gift cards, wire transfers, or cryptocurrency; these payments are hard to reverse. Verify the request first.",
       "you are being asked to pay in an unusual, hard-to-reverse way",
       "you are not being asked to pay in an unusual way",
       "you are not sure whether the payment method is unusual"),
    # --- family emergency ---
    _q("contact_relative_known_number",
       "Have you reached the family member directly using a phone number you already had saved for them?",
       "Reaching the relative on a known number helps confirm who is really asking.",
       "verification",
       "You have not yet reached the relative using a number you already had saved.",
       "Call the family member using a phone number you already had saved, not a number in this message.",
       "you have not reached the relative on a previously saved number",
       "you have reached the relative on a previously saved number",
       "you are not sure whether you reached the relative on a saved number"),
    _q("confirm_other_family",
       "Have you checked the story with another family member you trust?",
       "Another relative can help confirm whether the emergency is real.",
       "verification",
       "The story has not been checked with another trusted family member.",
       "Ask another family member you trust to help check the story.",
       "you have not checked the story with another trusted family member",
       "you have checked the story with another trusted family member",
       "you are not sure whether you checked the story with another family member"),
    _q("secrecy_pressure",
       "Are you being asked to keep this request secret?",
       "Requests for secrecy can prevent independent checks.",
       "warning",
       "Secrecy pressure is a reason to pause before acting.",
       "Do not keep the request secret; talk it over with someone you trust before acting.",
       "the message pressures you to keep the request secret",
       "the message does not pressure you to keep the request secret",
       "you are not sure whether the message pressures you to keep it secret"),
    # --- bank impersonation ---
    _q("bank_official_app",
       "Have you checked this by opening your bank's official app or website yourself, rather than a link in the message?",
       "Reaching the bank through a channel you open yourself avoids links placed by a sender.",
       "verification",
       "The request has not been checked through your bank's official app or website.",
       "Open your bank's official app or website yourself and check for the request there.",
       "you have not checked your bank's official app or website yourself",
       "you have checked your bank's official app or website yourself",
       "you are not sure whether you checked your bank's official app or website"),
    _q("transaction_in_account",
       "Have you checked whether the claimed transaction actually appears in your account?",
       "A claimed transaction that does not appear in your account is a warning sign.",
       "verification",
       "You have not confirmed whether the claimed transaction appears in your account.",
       "Check your account through the official app for the transaction described.",
       "you have not confirmed the claimed transaction in your account",
       "you have confirmed the claimed transaction in your account",
       "you are not sure whether the claimed transaction appears in your account"),
    _q("credentials_or_code_request",
       "Does the message ask for your login details, PIN, or a one-time security code?",
       "Banks do not ask you to share login credentials or one-time codes.",
       "warning",
       "A bank message asking for your login details, PIN, or a one-time code is a strong warning sign.",
       "Never share your password, PIN, or one-time security codes; banks do not ask for them.",
       "the message asks for your login details, PIN, or a security code",
       "the message does not ask for your login details, PIN, or a security code",
       "you are not sure whether the message asks for login details or a code"),
    _q("pressure_to_follow_link",
       "Are you being urged to follow an unfamiliar link to resolve this?",
       "Links in a message can lead to a look-alike site rather than your bank.",
       "warning",
       "Being pushed to follow an unfamiliar link is a common phishing tactic.",
       "Do not follow the message's link; reach the organization through a channel you open yourself.",
       "the message urges you to follow an unfamiliar link",
       "the message does not urge you to follow an unfamiliar link",
       "you are not sure whether the message urges you to follow a link"),
    # --- government / agency impersonation (grounded subtype) ---
    _q("official_notice_checked",
       "Have you checked any claimed notice against official records or notices you accessed independently?",
       "Checking against records you reach yourself avoids relying on the message.",
       "verification",
       "A claimed official notice has not been checked against records you reached independently.",
       "Check any claimed notice against official records or notices you access independently.",
       "you have not checked the claimed notice against independently accessed records",
       "you have checked the claimed notice against independently accessed records",
       "you are not sure whether you checked the claimed notice independently"),
    _q("agency_site_independent",
       "Have you confirmed the instructions through the agency's official website that you looked up yourself?",
       "Looking up the agency yourself avoids links or numbers supplied in the message.",
       "verification",
       "The instructions have not been confirmed through an official website you looked up yourself.",
       "Look up the agency's official website yourself and confirm the instructions there, rather than using links or numbers in the message.",
       "you have not confirmed the instructions through an independently found official website",
       "you have confirmed the instructions through an independently found official website",
       "you are not sure whether you confirmed the instructions through an official website"),
    _q("threat_penalty_arrest",
       "Does the message threaten immediate penalties, arrest, or legal action unless you act now?",
       "Government agencies generally do not threaten immediate arrest through a message demanding payment.",
       "warning",
       "Threats of immediate penalties or arrest are a common government-impersonation tactic.",
       "Treat threats of immediate penalties or arrest with caution; verify any claim through the agency's official channel you find yourself.",
       "the message threatens immediate penalties, arrest, or legal action",
       "the message does not threaten immediate penalties or arrest",
       "you are not sure whether the message threatens penalties or arrest"),
    # --- invoice fraud ---
    _q("verify_changed_details",
       "Have you confirmed the changed banking or payment details with your established supplier contact?",
       "Confirming a change with a known contact guards against redirected payments.",
       "verification",
       "The changed payment details have not been confirmed with your established supplier contact.",
       "Confirm any changed banking details with your established supplier contact before paying.",
       "you have not confirmed the changed payment details with your established supplier contact",
       "you have confirmed the changed payment details with your established supplier contact",
       "you are not sure whether you confirmed the changed details with your supplier"),
    _q("confirm_payment_details",
       "Have you confirmed the invoice and payment details with your usual contact at the supplier?",
       "Confirming with a known contact helps catch a redirected or fake invoice.",
       "verification",
       "The invoice and payment details have not been confirmed with your usual supplier contact.",
       "Confirm the invoice and payment details with your usual supplier contact before paying.",
       "you have not confirmed the invoice with your usual supplier contact",
       "you have confirmed the invoice with your usual supplier contact",
       "you are not sure whether you confirmed the invoice with your supplier"),
    _q("compare_records",
       "Have you compared the payment details against your existing records for this supplier?",
       "Existing records can reveal account details that do not match.",
       "verification",
       "The payment details have not been compared against your existing records.",
       "Compare the payment details with your existing records for this supplier.",
       "you have not compared the details against your existing records",
       "you have compared the details against your existing records",
       "you are not sure whether you compared the details against your records"),
    # --- suspicious payment ---
    _q("recipient_identified",
       "Have you independently confirmed who will receive this payment?",
       "Confirming the recipient independently helps catch a redirected payment.",
       "verification",
       "The recipient of the payment has not been independently confirmed.",
       "Independently confirm who will receive the payment before sending anything.",
       "you have not independently confirmed who will receive the payment",
       "you have independently confirmed who will receive the payment",
       "you are not sure whether you confirmed who will receive the payment"),
    _q("payment_method_checked",
       "Have you checked whether the requested payment method is normal for this kind of request?",
       "An unusual payment method for the situation is worth questioning.",
       "verification",
       "It is unclear whether the requested payment method is normal for this request.",
       "Check whether the requested payment method is normal for this kind of request.",
       "you have not checked whether the payment method is normal for this request",
       "you have checked that the payment method is normal for this request",
       "you are not sure whether the payment method is normal for this request"),
    _q("unusual_instructions",
       "Are the payment instructions unusual or different from what you would normally expect?",
       "Unusual instructions are a reason to confirm through a trusted channel.",
       "warning",
       "Unusual payment instructions are a reason to confirm before paying.",
       "Be cautious of unusual payment instructions; confirm them through a trusted channel.",
       "the payment instructions are unusual or unexpected",
       "the payment instructions are not unusual",
       "you are not sure whether the payment instructions are unusual"),
    _q("confirmed_before_sending",
       "Have you confirmed the request through a trusted channel before sending any money?",
       "A quick confirmation before paying is the most reliable check.",
       "verification",
       "The request has not been confirmed through a trusted channel before paying.",
       "Confirm the request through a trusted channel before sending any money.",
       "you have not confirmed the request through a trusted channel before paying",
       "you have confirmed the request through a trusted channel before paying",
       "you are not sure whether you confirmed the request before paying"),
    # --- general phishing / suspicious links ---
    _q("official_channel_checked",
       "Have you checked the request through the organization's official app or website that you opened yourself?",
       "Opening the official channel yourself avoids links placed in the message.",
       "verification",
       "The request has not been checked through an official channel you opened yourself.",
       "Open the organization's official app or website yourself to check the request.",
       "you have not checked the request through an official channel you opened yourself",
       "you have checked the request through an official channel you opened yourself",
       "you are not sure whether you checked an official channel you opened yourself"),
    _q("suspicious_link_present",
       "Is the message pushing you to click a link to resolve this?",
       "A link in the message can lead somewhere other than the real organization.",
       "warning",
       "Being pushed to click a link is a common phishing tactic.",
       "Leave the message's link unopened; reach the organization through a channel you open yourself.",
       "the message pushes you to click a link",
       "the message does not push you to click a link",
       "you are not sure whether the message pushes you to click a link"),
)}

_PAD = ("independent_contact", "expected_request", "sender_identity_known", "requests_sensitive_info")


def _is_government(context) -> bool:
    texts = [context.claimed_sender or ""]
    texts.extend(signal.evidence for signal in context.signals)
    return any(_GOVERNMENT.search(text) for text in texts)


def _finalize(ids):
    """Deduplicate, keep order, pad to at least 3, and cap at 5 questions."""
    ordered = []
    for qid in ids:
        if qid in QUESTIONS and qid not in ordered:
            ordered.append(qid)
    for qid in _PAD:
        if len(ordered) >= 3:
            break
        if qid not in ordered:
            ordered.append(qid)
    return ordered[:5]


def _select_ids(context):
    payment = bool(context.concepts & {"payment", "gift_cards"})
    if context.concerned and _is_government(context) and context.path not in {"family_emergency", "invoice_fraud"}:
        ids = ["official_notice_checked", "agency_site_independent", "threat_penalty_arrest", "requests_sensitive_info"]
        if payment:
            ids.append("unusual_payment_method")
        return _finalize(ids)
    if not context.concerned:
        # Low-risk / uncertain / unknown: neutral verification only, no alarms.
        return _finalize(["sender_identity_known", "expected_request", "independent_contact"])
    path = context.path
    if path == "family_emergency":
        ids = ["contact_relative_known_number", "confirm_other_family", "secrecy_pressure", "pressure_urgency"]
        if payment:
            ids.append("unusual_payment_method")
    elif path == "bank_impersonation":
        ids = ["bank_official_app", "transaction_in_account", "credentials_or_code_request", "pressure_to_follow_link"]
    elif path == "invoice_fraud":
        first = "verify_changed_details" if "changed_details" in context.concepts else "confirm_payment_details"
        ids = [first, "expected_request", "compare_records", "pressure_urgency"]
    elif path == "suspicious_payment":
        ids = ["recipient_identified", "payment_method_checked", "unusual_instructions", "confirmed_before_sending"]
    elif path == "link":
        ids = ["official_channel_checked", "expected_request", "requests_sensitive_info", "pressure_urgency"]
        if "link" in context.concepts:
            ids.append("suspicious_link_present")
    else:  # concerned but no scenario-specific route
        ids = ["independent_contact", "expected_request", "requests_sensitive_info", "pressure_urgency"]
        if payment:
            ids.append("unusual_payment_method")
    return _finalize(ids)


def build_questionnaire(analysis: dict) -> dict:
    """Return 3-5 contextual verification questions for the given analysis.

    Output is UI-agnostic and JSON-serializable:
    ``{"questions": [{"id", "text", "explanation"}, ...]}``. Selection is
    deterministic and never embeds submitted content. Malformed input normalizes
    to a neutral set rather than raising.
    """
    context = normalize(analysis)
    questions = []
    for qid in _select_ids(context):
        question = QUESTIONS[qid]
        questions.append({"id": question.id, "text": question.text, "explanation": question.explanation})
    return {"questions": questions}


def _answer(answers, qid):
    """Normalize one answer to 'yes'/'no'/'unsure', or None when absent/invalid.

    The frontend transports the unsure option as 'not_sure' (and 'not sure'); both
    are accepted as aliases for 'unsure' so the UI and backend stay compatible.
    """
    value = answers.get(qid)
    if isinstance(value, str):
        value = value.strip().lower()
        if value in {"not_sure", "not sure"}:
            return "unsure"
        if value in {"yes", "no", "unsure"}:
            return value
    return None


def _state(question, answer):
    if answer == "unsure":
        return "unresolved"
    if question.kind == "verification":
        return "ok" if answer == "yes" else "gap"
    return "gap" if answer == "yes" else "ok"


def _scope(questionnaire, answers):
    """Question IDs to review, taken from the questionnaire when valid, else from
    the answer keys. Only IDs in the controlled registry are ever considered."""
    ids = []
    if isinstance(questionnaire, dict) and isinstance(questionnaire.get("questions"), list):
        for item in questionnaire["questions"]:
            if isinstance(item, dict):
                qid = item.get("id")
                if isinstance(qid, str) and qid in QUESTIONS and qid not in ids:
                    ids.append(qid)
    if not ids:
        for qid in answers:
            if isinstance(qid, str) and qid in QUESTIONS and qid not in ids:
                ids.append(qid)
    return ids


def _join(parts):
    parts = [part for part in parts if part]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return ", ".join(parts[:-1]) + ", and " + parts[-1]


def _dedupe(items):
    seen = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def review_questionnaire(questionnaire: dict, answers: dict) -> dict:
    """Interpret the user's answers and return structured, cautious feedback.

    Shape: ``{"headline", "summary", "concerns", "recommended_actions"}`` with
    string / list-of-string values. Partial answers are supported: an unanswered
    or invalid answer is treated as unresolved, never as fraud. The review never
    concludes a request is safe, legitimate, or confirmed from answers alone.
    """
    answers = answers if isinstance(answers, dict) else {}
    asked = _scope(questionnaire, answers)

    if not asked:
        return {
            "headline": "Start by answering the verification questions",
            "summary": "No verification questions were available to review. Treat the request as unverified until you can check it.",
            "concerns": [],
            "recommended_actions": [_UNIVERSAL],
        }

    answered, gaps, unresolved, oks, unanswered = [], [], [], [], []
    for qid in asked:
        question = QUESTIONS[qid]
        answer = _answer(answers, qid)
        if answer is None:
            unanswered.append(question)
            continue
        state = _state(question, answer)
        answered.append((question, state))
        {"gap": gaps, "ok": oks, "unresolved": unresolved}[state].append(question)

    if gaps:
        headline = "Important verification steps remain"
    elif unresolved or unanswered:
        headline = "Some verification steps are still unresolved"
    elif oks:
        headline = "You reported some verification steps, but they do not prove the request is genuine"
    else:
        headline = "Start by answering the verification questions"

    fragments = [getattr(question, state) for question, state in answered]
    if fragments:
        summary = "You reported that " + _join(fragments) + "."
    else:
        summary = "You have not answered the verification questions yet."
    if unanswered:
        count = len(unanswered)
        noun, verb = ("question", "remains") if count == 1 else ("questions", "remain")
        summary += f" {count} {noun} {verb} unanswered; treat those as unresolved."

    concerns = [question.concern for question in gaps]
    if not concerns:
        if unresolved or unanswered:
            concerns = ["Some verification steps are still unresolved, so treat the request as unverified for now."]
        else:
            concerns = ["Your answers report verification steps, but they do not by themselves confirm the request is genuine."]

    actions = []
    for qid in asked:
        question = QUESTIONS[qid]
        answer = _answer(answers, qid)
        state = _state(question, answer) if answer is not None else "unresolved"
        if state in {"gap", "unresolved"}:
            actions.append(question.remedy)
    if not actions:
        actions = ["Continue to confirm the amount and recipient through a channel you already trust before sending money."]
    actions.append(_UNIVERSAL)

    return {
        "headline": headline,
        "summary": summary,
        "concerns": concerns,
        "recommended_actions": _dedupe(actions)[:6],
    }
