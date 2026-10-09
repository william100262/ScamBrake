# ScamBrake
AI-powered scam detection and payment verification assistant

## Frontend

A Python 3.12 / Streamlit prototype with three stages: submit a request, review
possible warning signs, then pause and verify through an independent channel.
The frontend works without API keys in **Demo mode — simulated analysis**.
It does not transfer money, establish legitimacy, or persist submitted content.

### Run on this computer (Windows PowerShell)

The local virtual environment and dependencies have already been installed.
Open PowerShell and run:

```powershell
cd C:\Users\willi\Desktop\ScamBrake\ScamBrake
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open **http://localhost:8501** in your browser, or use the Local URL printed in
the terminal if Streamlit chooses a different port. Keep that terminal open
while using the app. Press **Ctrl+C** in the terminal to stop it.

The application starts in demo mode without Gemini or ElevenLabs API keys.
Select **Family emergency scam**, then **Analyze message**, then **Pause & Verify**
to try the complete workflow. Use **Check another message** to reset it.

### First-time setup on another computer

Install **Python 3.12** and Git, then open PowerShell. Clone the repository if
you do not already have it:

```powershell
git clone https://github.com/william100262/ScamBrake.git
cd ScamBrake
```

If the repository is already downloaded, change into the folder containing
`app.py` and `requirements.txt` instead. Create a virtual environment, install
runtime dependencies, and launch:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The `.venv` folder is local and is not included on GitHub. Each developer must
create their own environment. These commands do not require activation or a
PowerShell execution-policy change.

If you prefer activating the environment, run:

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run app.py
```

### Common startup problems

- **`py` is not recognized:** Install Python 3.12 with the Python launcher, or
  use `python -m venv .venv` if `python --version` reports Python 3.12.
- **`No module named streamlit`:** Run
  `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` from the repository root.
- **`app.py` cannot be found:** Change into the folder containing `app.py`.
  On this computer, that is the inner `ScamBrake` folder shown above.
- **Activation scripts are blocked:** Use the direct `.venv\Scripts\python.exe`
  commands above; activation is optional.
- **Port 8501 is already in use:** Read the Local URL printed by Streamlit, or
  explicitly choose another port:

  ```powershell
  .\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
  ```

- **Live integration is unavailable:** To run the fictional demo again, set
  `$env:SCAMBRAKE_DEMO_MODE = "true"` in PowerShell before launching the app.

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

From the repository root, install the development dependencies and run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

With an activated environment, the equivalent test command is
`python -m pytest -q`.

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
