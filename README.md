# ScamBrake
AI-powered scam detection and payment verification assistant

## Frontend

A Python 3.12 / Streamlit prototype with three stages: submit a request, review
possible warning signs, then pause and verify through an independent channel.
The frontend works without API keys in **Demo mode — simulated analysis**.
It does not transfer money, establish legitimacy, or persist submitted content.

### Setup and run (PowerShell)

Run these commands from this repository's root (the inner `ScamBrake` folder):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
```

If activation is restricted, use `.\.venv\Scripts\python.exe` instead of
`python`; no execution-policy change is needed. `requirements.txt` contains
runtime dependencies; `requirements-dev.txt` additionally installs pytest.

### Demonstrating the workflow

1. Select **Family emergency scam**, then **Analyze message** to see a high-concern
   fictional example with three supporting quotes and extracted payment details.
2. Select **Pause & Verify**, choose any of the three answers, then **Continue**.
   Checklist marks track the user's progress only. Return to results and back to
   see that progress persists.
3. Select **Check another message**, then **Legitimate payment reminder** and
   **Analyze message** to see a low-concern example with a light verification step.
4. Upload a PNG or JPEG and explicitly select **Analyze screenshot** to exercise
   the in-memory preview and simulated screenshot flow. The native × removes the
   upload. Screenshots are never saved by the frontend.

The moderate-concern fictional fixture is also available by pasting exactly:

```text
Hi, this is the event organizer. Please send the $40 registration fee by bank transfer today. We have changed our payment details.
```

Other custom text produces an **Unable to assess** generic simulation. Demo mode
does not read screenshot text or run AI analysis. No arbitrary message is represented
as genuinely analyzed. The default is `SCAMBRAKE_DEMO_MODE=true`.

### Person 2: connect analysis

Add your own `analyzer.py` in the root, exposing this synchronous function:

```python
def analyze_input(text="", image_bytes=None, mime_type=None):
    return {
        "risk_level": "high",  # high / moderate / low / unknown
        "summary": "Plain-English explanation",
        "signals": [{
            "type": "urgency",
            "title": "Pressure to act",
            "evidence": "An exact quote from the submitted text, or None",
            "explanation": "Why this deserves an independent check",
        }],
        "requested_amount": None,  # optional strings
        "payment_method": None,
        "claimed_sender": None,
    }
```

Text and image inputs are mutually exclusive. The frontend passes validated image
bytes and `image/png` or `image/jpeg`, without a filesystem path. Keep API credentials
and Gemini calls inside your module, using environment variables; never return or
log raw requests, screenshots, keys, or provider exception details.

### Person 3: connect verification

Add your own `intervention.py` in the root, exposing:

```python
def build_intervention(analysis):
    return {
        "question": "Have you contacted the sender using a saved number?",
        "context": "An independent contact channel helps confirm who sent this.",
        "recommended_actions": ["Use your saved contact details.",
                                "Confirm the amount and recipient before paying."],
    }
```

This function receives the normalized analysis dictionary. It is called once per
analysis, before results are stored together in Session State.

Enable both real integrations before starting Streamlit:

```powershell
$env:SCAMBRAKE_DEMO_MODE = "false"
python -m streamlit run app.py
```

Modules in other locations can be selected with `SCAMBRAKE_ANALYZER_MODULE` and
`SCAMBRAKE_INTERVENTION_MODULE` (Python dotted module names). If your functions have
different signatures, add thin wrappers in those modules or adapt `ui/integration.py`.
No teammate modules are created or overwritten by the frontend. Live failures never
fall back to fictional data. Missing optional fields render as **Not specified**;
missing verification actions get conservative, generic steps. An invalid top-level
response fails with a friendly retry message. Invalid risk values become unknown.
Text evidence is displayed only when it appears exactly in the submitted message;
image quotes are omitted until an OCR evidence contract is established.

### Optional audio

Audio is hidden by default. A future server-side voice integration can expose
`generate_audio(text) -> bytes` (MP3) in a module named by `SCAMBRAKE_VOICE_MODULE`.
The UI calls it only when the user selects **Listen to explanation**, stores the
result in Session State, and displays a native player without autoplay. ElevenLabs
API logic and credentials belong in that module. No voice service is implemented.

### Tests

```powershell
python -m pytest -q
```

Tests cover input limits, image formats/size/dimensions, all four concern levels,
normalization, live adapters/failures, demo controls, all three verification answers,
checklist persistence, resets, retry behavior, and plain-text rendering of untrusted
responses. Streamlit AppTest does not provide a file-uploader input API, so upload
tests inject an in-memory file through the actual validation/preview/submit path.
Native file selection and responsive layout should also be checked in a browser.

### Frontend files

- `app.py`: single application entry point and stage routing.
- `ui/components.py`, `ui/styles.py`: native controls, presentation, static CSS.
- `ui/state.py`: session initialization and workflow callbacks.
- `ui/validation.py`: text and in-memory image validation.
- `ui/mock_data.py`: fictional responses using the integration contract.
- `ui/integration.py`: real/mock providers, normalization, optional audio boundary.
- `.streamlit/config.toml`: light theme and 5 MB uploader limit.
- `tests/test_frontend.py`: helper and AppTest coverage.

The frontend keeps data only in the current session. Browser refresh can clear it.
In live mode, content is sent to the configured AI service; provider retention
policies are outside this frontend's control. Remove sensitive information first.
