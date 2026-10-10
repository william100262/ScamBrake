# Inline intervention update

Implemented locally in `C:\Users\willi\Desktop\ScamBrake Merge` on
`merged-ahmed-denise`. No branch switch, merge, commit, push, or `.env` edit was
performed. Earlier uncommitted visual changes were retained.

## Why the workflows were duplicated

Both the Questioning button and Authority's “Pause & Verify” button called
`state.change_stage("verify")`. The resulting separate page contained one generic
question and the legacy action list. The frontend adapter also discarded the
analyzer's `scenario`, preventing contextual selection.

## The four interactions

- **Questioning:** “Review verification questions” reveals 3–5 questions directly
  inside the card. Each has a descriptive radio label, Yes / No / Not sure options,
  a stable ID and supporting explanation. The same button collapses the panel.
- **Authority:** “What trusted sources recommend” gives relevant institutional
  guidance. “View official guidance” expands the source details; the source link
  opens only when clicked. It does not open Questioning. A null source displays
  an explicit general-guidance notice instead of a fabricated link.
- **Social Influence:** “Recognize the pattern” explains possible tactics matched
  to the returned signals. The expander shows their message evidence. Without
  matches, the card says so. It makes no claims about other users or scam rates.
- **Diversion:** “Take a safer next step” contains a separate expandable checklist
  of independent verification actions. Checkbox progress is self-reported and
  never presented as proof of verification.

The risk assessment and warning signs remain visible on the results page. The
existing navy/sage/gold theme, font, logo, payment halos and red High concern card
were preserved. No CSS or theme change was needed for this interaction update.

## Context and state

`intervention_questions.build_verification(analysis)` is a deterministic,
standard-library-only companion. It selects questions and actions using scenario,
claimed sender, signal types/evidence and payment method. It supports family,
bank, invoice, suspicious-link, government and neutral/general contexts. Urgency
and unusual payment methods add relevant questions, capped at five. It does not
assign a new fraud verdict or interpret all Yes answers as successful verification.

The integration retains `scenario` in the normalized frontend result and stores a
deep copy of the original seven-field live analyzer output as `analyzer_result`.
That original result reaches the presentation companion without altering the
analyzer's public schema. Demo fixtures without scenarios use limited context
fallbacks; arbitrary demo messages remain explicitly generic simulations.

The model is generated on submission and stored in session state. Independent
answer/checklist dictionaries preserve responses across widget reruns and hidden
questionnaire widgets. Existing input-change/restart callbacks clear the model,
responses and progress. Interactive reruns do not call the analyzer, legacy
intervention provider or OCR again. Progress lasts within the current tab/session.

The specified `intervention.py`, `interventions/*` modules and
`docs/intervention_contract.md` do not exist in this checkout. No replacement
four-card JSON contract was invented. The existing `ui.integration.build_intervention`
and `normalize_intervention` legacy interfaces remain available and continue to
run on submission. Compatibility with the absent Denise backend cannot be tested
here; its module can be integrated separately when supplied.

## IRS and government handling

The analyzer's fixed scenario vocabulary does not contain a government scenario.
The companion recognizes IRS/agency context from the claimed sender and returned
signal evidence, without changing that vocabulary. Its actions use independently
located official sites, securely accessed records and published procedures. There
is no “Call the IRS” default, and no submitted links or phone numbers become trusted
contacts. Non-IRS agencies receive general FTC guidance rather than an invented
agency-specific source.

Curated source pages were opened and checked during implementation:

- [IRS: Recognize tax scams and fraud](https://www.irs.gov/help/tax-scams/recognize-tax-scams-and-fraud)
- [FTC: How to avoid a scam](https://consumer.ftc.gov/articles/how-avoid-scam)
- [FTC: How to recognize and avoid phishing scams](https://consumer.ftc.gov/articles/how-recognize-avoid-phishing-scams)

These sources describe general warning patterns and independent checking. None
has inspected a submitted ScamBrake message. Links are curated constants, not
derived from submitted content; their future availability is not guaranteed.

## Files changed for this update

- `app.py`: route any legacy verification stage back to results.
- `ui/components.py`: inline questionnaire and distinct card interactions.
- `ui/state.py`: contextual answer, visibility and checklist persistence/reset.
- `ui/integration.py`: preserve scenario and the original live analyzer result.
- `intervention_questions.py`: new deterministic presentation companion.
- `tests/test_frontend.py`, `tests/test_screenshots.py`, `tests/test_ui_design.py`:
  replace old navigation assumptions and cover contextual interactions.
- `docs/UI_DESIGN.md`, `docs/INLINE_INTERVENTIONS.md`: updated behavior and guide.

`ui/styles.py`, logo assets and the earlier layout modifications were already
uncommitted from the previous design request; this update retains them.

## Actual verification

Executed with the merge folder's `.venv` interpreter:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pip check
git --work-tree="C:\Users\willi\Desktop\ScamBrake Merge" diff --check
```

Final results: **131 passed, 20 skipped** in 27.23 seconds; no broken dependencies;
no whitespace errors. Skips require a native Tesseract executable. Provider tests
use mocked responses and make no real Mistral requests. Coverage includes scenario
selection, IRS guidance, original analyzer fields, neutral/link handling, native
card separation, inline answers, collapse persistence, message reset, text and
mocked screenshot workflows, and no extra analyzer/OCR calls during interaction.

Streamlit AppTest exercised the actual application and callbacks. Browser clicks,
responsive layout and external-link opening were **not** visually verified.

## Manual testing

Use a fresh preview process from the merge folder to avoid imported modules cached
in an older Streamlit process. Choose an unused port, for example 8503:

```powershell
cd "C:\Users\willi\Desktop\ScamBrake Merge"
$env:SCAMBRAKE_DEMO_MODE = "true"
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
```

1. **Family:** select “Family emergency scam”, then Analyze message. Open “Review
   verification questions”. Expect trusted relative contact, independent family
   confirmation, secrecy and deadline questions. Answer one and check a Diversion
   item. Hide/reopen Questioning; both values should remain and analysis stays visible.
2. **Bank:** arbitrary demo messages do not receive contextual AI analysis. Stop
   the preview, set `$env:SCAMBRAKE_DEMO_MODE = "false"`, and restart with the same
   command using your existing configured provider. Submit: “This is your bank.
   Your account will be locked today. Open https://example.invalid/security and
   send the security code to confirm your account.” If the returned scenario is
   `bank_impersonation`, expect official app, account records and security-code
   questions. The example URL must never become a trusted link or checklist contact.
3. **IRS:** in live mode submit: “IRS notice: pay $500 in gift cards today or face
   arrest. Use https://example.invalid/tax and do not contact anyone else.” If the
   returned sender/evidence identifies IRS, expect official notice/records,
   unexpected instructions and published procedure questions; no default call.
   Authority should name the IRS and link only to the curated IRS guidance page.
4. Expand Authority and Social Influence independently. Neither should reveal the
   questionnaire or navigate away. Diversion should have its own checkbox list.
5. Select “Check another message” and analyze a different message. Answers,
   checklist completion and questionnaire visibility should reset.
6. Repeat with a screenshot: review/correct locally extracted text before analyzing.
   Answering questions and marking checklist items should not repeat extraction.

Live contextual output depends on the actual analyzer result, not merely keywords
typed into the UI. Tests exercise these scenarios with controlled provider results.
