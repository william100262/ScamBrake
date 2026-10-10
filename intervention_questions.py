"""Optional deterministic presentation companion; no provider calls or UI imports.

Does not replace the legacy intervention adapter or a teammate's four-card API.
Only curated official URLs are used; submitted contact details are never links.
"""
import re

FTC = {"name": "Federal Trade Commission", "title": "How to avoid a scam",
       "url": "https://consumer.ftc.gov/articles/how-avoid-scam"}
PHISHING = {"name": "Federal Trade Commission", "title": "How to recognize and avoid phishing scams",
            "url": "https://consumer.ftc.gov/articles/how-recognize-avoid-phishing-scams"}
IRS = {"name": "Internal Revenue Service", "title": "Recognize tax scams and fraud",
       "url": "https://www.irs.gov/help/tax-scams/recognize-tax-scams-and-fraud"}

def _question(identifier, text, explanation):
    return {"id": identifier, "text": text, "explanation": explanation}

def build_verification(analysis):
    """Derive 3–5 questions and independent actions from analyzer context.

    Government recognition supplements the analyzer's fixed scenario vocabulary;
    it does not alter that schema or classify a message as fraudulent.
    """
    scenario = analysis.get("scenario", "unknown")
    sender = analysis.get("claimed_sender") or ""
    signals = analysis.get("signals") or []
    types = {str(s.get("type", "")).lower() for s in signals if isinstance(s, dict)}
    evidence = " ".join(str(s.get("evidence") or "") for s in signals if isinstance(s, dict))
    context = f"{sender} {evidence}".lower()
    is_irs = bool(re.search(r"\birs\b|internal revenue service", context))
    government = is_irs or "government" in scenario or bool(re.search(r"\b(?:tax agency|government agency|hmrc|social security administration)\b", context))
    # Demo family fixture predates the scenario field; named relatives are context.
    if scenario in ("unknown", "general") and re.fullmatch(r"dad|mom|mum|father|mother|son|daughter|grandson|granddaughter", sender.lower()):
        scenario = "family_emergency"
    if government:
        kind = "government"
        questions = [
            _question("official_notice", "Does the claim appear in securely accessed official government records or correspondence you can independently verify?", "Use an independently located official account or notice; a message alone is not proof."),
            _question("unexpected_instructions", "Is the message pressuring you to use an unexpected payment method or unfamiliar link?", "Pressure and unusual instructions deserve a separate check before acting."),
            _question("published_instructions", "Have you checked the request against instructions published on the agency's official website?", "You can verify online instructions without assuming a phone call is convenient.")]
        actions = [("official_site", "Independently locate the agency's official website; avoid the message's links and numbers."),
                   ("official_records", "Check the claim through a securely accessed official account or independently verifiable correspondence."),
                   ("published_process", "Compare the requested action with the agency's published procedures before paying or sharing information.")]
        source = IRS if is_irs else FTC
        guidance = "IRS guidance describes impersonators using threats, demands and misleading links. Compare any claimed IRS request with official records and published procedures." if is_irs else "FTC guidance recommends resisting pressure and checking claims using contact information found independently. Apply that check to the claimed agency."
    elif scenario == "family_emergency":
        kind = scenario
        questions = [
            _question("saved_contact", "Have you contacted the relative using contact details you already trusted?", "A familiar name or new number does not establish identity."),
            _question("family_confirmation", "Has another trusted family member independently confirmed the emergency?", "A separate check can clarify the story without relying on the requester."),
            _question("secrecy_pressure", "Are you being pressured to keep the request secret?", "Secrecy can prevent you from seeking help; a Yes here is a reason to pause.")]
        actions = [("saved_contact", "Contact the relative through a saved phone number or another channel you already trust."), ("family_confirmation", "Ask another trusted family member to independently confirm the situation."), ("recipient", "Confirm the amount and recipient independently before deciding whether to pay.")]
        source, guidance = FTC, "FTC guidance describes impersonation and pressure as common scam tactics. Use your established family contacts to check the request."
    elif scenario == "bank_impersonation":
        kind = scenario
        questions = [
            _question("official_app", "Did you independently open your bank's official app or website to check for the alert?", "Open the service directly rather than following a message link."),
            _question("account_records", "Does the claimed transaction or issue appear in your actual account?", "Compare the claim with records accessed independently."),
            _question("security_code", "Are you being asked to follow a link or share a security code?", "Do not share codes with the message sender; confirm instructions in the official app.")]
        actions = [("official_app", "Open your bank's official app or independently navigate to its website."), ("account_records", "Check the claimed alert or transaction in your account."), ("trusted_support", "If needed, use support inside the official app or contact details on your bank card.")]
        source, guidance = PHISHING, "FTC phishing guidance recommends checking a claim through a website or number you know is real. Check the bank alert in the official app rather than the message."
    elif scenario == "invoice_fraud":
        kind = scenario
        questions = [
            _question("supplier_contact", "Have you confirmed changed payment details through an established supplier contact?", "Use your existing business records, not contact details accompanying the change."),
            _question("expected_change", "Were the new payment instructions expected?", "An unexpected change deserves independent confirmation."),
            _question("invoice_records", "Have you checked the invoice against your existing records?", "Compare the amount, supplier and work ordered before paying.")]
        actions = [("supplier_contact", "Verify the payment instructions through a previously established supplier contact."), ("invoice_records", "Compare the invoice with existing orders, invoices and payment records."), ("recipient", "Confirm the recipient and amount before authorizing payment.")]
        source, guidance = FTC, "FTC guidance recommends independently checking requests before paying. Use your established supplier records to verify changed instructions."
    elif any("link" in t or "phish" in t for t in types):
        kind = "suspicious_link"
        questions = [
            _question("expected_message", "Were you expecting this message?", "An unexpected message warrants checking its context."),
            _question("independent_service", "Have you independently visited the legitimate service instead of following the provided link?", "Access the service using its known app or an independently obtained address."),
            _question("account_issue", "Does the claimed issue appear in your official account?", "Compare the message with records accessed independently.")]
        actions = [("independent_service", "Open the service's known app or independently obtained official website."), ("account_issue", "Check whether the claimed issue appears in your account."), ("trusted_support", "Use support through that official service if the claim is unclear.")]
        source, guidance = PHISHING, "FTC phishing guidance recommends checking the story using a channel you know is real. Verify the claimed issue without following the submitted link."
    else:
        kind = "general"
        questions = [
            _question("expected_request", "Were you expecting this request?", "Compare it with your plans and existing records without assuming fraud."),
            _question("independent_confirmation", "Have you confirmed the request through a channel you already trust?", "Use saved contact details or independently obtained official information."),
            _question("requested_action", "Does the requested action match what you independently confirmed?", "Check the amount and recipient for payments, or the information requested for account checks.")]
        actions = [("existing_records", "Compare the request with your existing records or expected arrangements."), ("independent_confirmation", "Confirm it using saved contact details or an independently located official channel."), ("requested_action", "Check the requested action, amount and recipient before deciding to proceed.")]
        source, guidance = FTC, "FTC guidance recommends pausing and checking requests through trusted channels. This is general guidance, not evidence that this request is fraudulent."
    if any("urgency" in t or "threat" in t for t in types):
        questions.append(_question("deadline_pressure", "Are you being pressured to act before you can independently check the request?", "A Yes is a reason to pause; it is not independent proof of fraud."))
    method = str(analysis.get("payment_method") or "").lower()
    if len(questions) < 5 and any(x in method for x in ("gift card", "crypto", "wire")):
        questions.append(_question("payment_confirmed", "Have you independently confirmed that this payment method is expected?", "Some payment methods can be hard to recover; confirm instructions before sending funds."))
    patterns = []
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        t = str(signal.get("type", "")).lower()
        description = next((description for token, description in [
            ("urgency", "Pressure to act quickly can reduce time for independent checks."),
            ("threat", "Threats can pressure recipients into acting before verifying."),
            ("impersonation", "A familiar identity can be used to make an unverified request seem credible."),
            ("link", "Message links can direct recipients to lookalike services."),
            ("payment", "Unexpected payment instructions deserve independent confirmation."),
            ("secrecy", "Secrecy can discourage advice from trusted people."),
            ("discouraging_verification", "Discouraging contact can prevent an independent identity check.")]
            if token in t), None)
        if description:
            patterns.append({"text": description, "evidence": signal.get("evidence")})
    return {"context": kind, "questions": questions, "actions": [{"id": i, "text": t} for i, t in actions],
            "authority": {"guidance": guidance, "source": dict(source)}, "patterns": patterns}
