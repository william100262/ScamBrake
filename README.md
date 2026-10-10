# ScamBrake
AI-powered scam detection and payment verification assistant

## Frontend

A Python 3.13 / Streamlit prototype with three stages: submit a request, review
possible warning signs, then pause and verify through an independent channel.
The frontend works without API keys in **Demo mode — simulated analysis**.
It does not transfer money, establish legitimacy, or persist submitted content.

### Run on this computer (Windows PowerShell)

The local virtual environment and dependencies have already been installed.
Open PowerShell and run:

```powershell
Set-Location "C:\Visual Studio Folder\ScamBrake"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open **http://localhost:8501** in your browser, or use the Local URL printed in
the terminal if Streamlit chooses a different port. Keep that terminal open
while using the app. Press **Ctrl+C** in the terminal to stop it.

The application starts in demo mode without AI provider API keys.
Select **Family emergency scam**, then **Analyze message**, then **Pause & Verify**
to try the complete workflow. Use **Check another message** to reset it.

### First-time setup on another computer

Install **Python 3.13** and Git, then open PowerShell. Clone the repository if
you do not already have it:

```powershell
git clone https://github.com/william100262/ScamBrake.git
cd ScamBrake
```

If the repository is already downloaded, change into the folder containing
`app.py` and `requirements.txt` instead. Create a virtual environment, install
runtime dependencies, and launch:

```powershell
py -3.13 -m venv .venv
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

- **`py` is not recognized:** Install Python 3.13 with the Python launcher, or
  use `python -m venv .venv` if `python --version` reports Python 3.13.
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
4. Upload a PNG, JPEG, or WebP, review the locally extracted text, correct any
   mistakes, and click **Analyze confirmed text**. The native × removes the upload.

The moderate-concern fictional fixture is also available by pasting exactly:

```text
Hi, this is the event organizer. Please send the $40 registration fee by bank transfer today. We have changed our payment details.
```

Other custom text produces an **Unable to assess** generic simulation. Demo mode
reads screenshot text locally but does not run AI analysis. No arbitrary message is represented
as genuinely analyzed. The default is `SCAMBRAKE_DEMO_MODE=true`.

### Analysis contract

`analyzer.analyze_input(text: str) -> dict` is the shared text backend for pasted
messages and user-confirmed OCR text. Its seven fields remain `scenario`,
`risk_level`, `signals`, `requested_amount`, `payment_method`, `claimed_sender`,
and `explanation`. The integration boundary maps backend `medium`/`uncertain`
to UI `moderate`/`unknown`. Exact evidence and payment details must occur in the
submitted text; OCR mistakes are never silently corrected into fabricated quotes.

Set `SCAMBRAKE_DEMO_MODE=false` for real analysis. Select
`SCAMBRAKE_AI_PROVIDER=mistral` or `lmstudio`; absent an explicit selection,
the analyzer uses Mistral when `MISTRAL_API_KEY` is set, otherwise LM Studio.
Mistral uses `MISTRAL_MODEL` when configured. LM Studio uses the existing local
endpoint `http://localhost:1235/api/v1/chat` and model `qwen/qwen3.5-9b`.
Both providers receive text only. No vision model or second API key is needed.
Screenshots are not sent to either provider. Provider failures produce an
uncertain assessment with a safe explanation; use **Check another message** to retry.

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
screenshot evidence is checked against the user-confirmed text.

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

## Local screenshot analysis

Install the free Tesseract engine with English language data, then the Python
dependencies. These commands work from Windows PowerShell (Python 3.13 required):

```powershell
Set-Location "C:\Visual Studio Folder\ScamBrake"
# Only create the environment if it does not already exist:
if (!(Test-Path .venv\Scripts\python.exe)) { py -3.13 -m venv .venv }
winget install --id UB-Mannheim.TesseractOCR --exact --source winget --silent --accept-package-agreements --accept-source-agreements
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
# Preserve an existing .env, including credentials:
if (!(Test-Path .env)) { Copy-Item .env.example .env }
$env:SCAMBRAKE_DEMO_MODE = "false"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

For Mistral, set `MISTRAL_API_KEY` in your local `.env`. Never commit that file.
For a fully local workflow, run the configured LM Studio server and set
`$env:SCAMBRAKE_AI_PROVIDER = "lmstudio"` before launching. The app defaults to
demo mode when `SCAMBRAKE_DEMO_MODE` is absent from both the environment and
`.env`; existing process environment variables take priority over `.env`.

OCR detects `tesseract` on PATH or the standard Windows installation at
`C:\Program Files\Tesseract-OCR\tesseract.exe`. For a custom installation, set
`SCAMBRAKE_TESSERACT_CMD` to the full executable path in PowerShell or `.env`.
If using `.env`, restart the app after changing configuration. Missing engines,
language data, timeouts, and unreadable images give safe messages and permit
manual text entry or a retry. Pasted-text analysis works without Tesseract.

### Why Tesseract

[pytesseract](https://github.com/madmaze/pytesseract) is a small Python wrapper
around a mature local OCR engine and supports process timeouts. It avoids
paid services and neural model downloads. The legacy `rapidocr-onnxruntime`
distribution excludes Python 3.13; newer RapidOCR adds an inference runtime and
model management. EasyOCR adds PyTorch and larger model dependencies. For this
English screenshot MVP, Tesseract is a practical lightweight choice, at the cost
of one external installer. See the [official installation guide](https://tesseract-ocr.github.io/tessdoc/Installation.html).

### Workflow, limits, and privacy

1. Choose **Upload a screenshot**, then a still PNG, JPG/JPEG, or WebP.
2. Local OCR runs once for the selected upload. Review and edit the extracted
   text, especially names, amounts, URLs, and payment methods.
3. Click **Analyze confirmed text** to send that text to the configured text
   provider. Uploading, editing, and ordinary reruns do not trigger AI calls.
4. Review the usual risk assessment and evidence, then use **Pause & Verify**.

Limits: 5 MB encoded data, sides between 32 and 10,000 pixels, at most 20 million
decoded pixels, still images only, and 5,000 confirmed characters. Both file
contents and extension must match. Decoding and decompression checks precede OCR.
EXIF orientation is honored; alpha is composited on white; dark backgrounds are
inverted; contrast and bounded resizing improve recognition. OCR processes at
most 6 million pixels with a 3,200-pixel longest side and a 20-second timeout.
Only one OCR job runs at a time per process; busy requests can retry.

English printed text is supported. Blurred, tiny, handwritten, rotated images
without EXIF, complex columns, and mixed-language screenshots may be inaccurate.
Crop to the conversation and rotate upright first. Unreliable extraction leaves
the review box empty with a retry/paste message. No spell correction is applied. Reading
order follows Tesseract's single-block layout and may differ for complex screens.

The application does not permanently save screenshots or log extracted content.
Streamlit holds the upload in session memory; custom session state keeps only
its fingerprint, review text, and workflow status, not a second copy of the bytes.
`pytesseract` uses temporary files and removes them on success, error, and timeout;
an abrupt process or machine crash can leave OS temporary files behind. Remove
the upload or select **Check another message** to clear the review state. Live
provider retention policies apply to confirmed text sent for analysis.

### Tests and manual acceptance

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest tests/test_screenshots.py -q
```

The screenshot suite includes real synthetic PNG/JPEG/WebP extraction and blank,
dark, and EXIF cases, validation limits, safe failures, literal OCR preservation,
mocked Mistral/LM Studio calls, corrected-text submission, reruns, retry, replacement,
removal, and Pause & Verify. Real-engine tests explicitly skip if Tesseract is
absent. External AI calls are mocked. AppTest injects uploads because its public
API does not support selecting files. These tests do not prove live API acceptance
or native browser file selection.

Manual acceptance checklist:
- Start in live mode with the desired provider available.
- Upload a real message screenshot in each supported format. Confirm OCR appears
  before any AI analysis and the names, amount, payment method, and URL are readable.
- Correct a word or amount; click **Analyze confirmed text** and check that all
  evidence quotes match the corrected text exactly.
- Open **Pause & Verify**, choose an answer, and complete a checklist step.
- Start over, try a different upload, remove it, and verify old text is cleared.
- Try a blank/corrupt/oversized image, then verify pasted-text analysis still works.
- Repeat with LM Studio if testing both providers. Treat all findings as possible
  warning signs, never a guarantee of fraud or legitimacy.


### OCR confidence filtering

Tesseract's native TSV word confidences and line boxes are now used instead of
accepting every string containing three alphanumeric characters. No new packages
or model downloads are required. Existing dependency setup still applies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Optional environment / `.env` settings (restart the app after changes):

| Setting | Default | Meaning |
| --- | --- | --- |
| `SCAMBRAKE_OCR_WORD_CONFIDENCE` | 60 | Minimum individual word score, 0-100 |
| `SCAMBRAKE_OCR_LINE_CONFIDENCE` | 80 | Minimum average score of retained words in each line |
| `SCAMBRAKE_OCR_SINGLE_WORD_CONFIDENCE` | 90 | Extra minimum for a line containing only one retained word |
| `SCAMBRAKE_OCR_RELIABLE_FRACTION` | 0.5 | Minimum retained fraction of detections in each line and the image |

All settings must be positive and finite; confidence settings may not exceed 100,
and the fraction may not exceed 1. Invalid values produce a safe configuration
error with manual entry available. Defaults are conservative heuristics, not a
measured probability of correctness. Lowering them admits more noise; raising
them can omit legitimate words. No English dictionary or minimum message length
is required: high-confidence short messages such as "OK" can pass.

The filter excludes low-confidence or invalid word records and control/replacement
characters. At least 40% of a retained token must be letters or digits (so common
amounts, URLs, and names pass without rewriting). Line membership comes from
Tesseract. Within each line, word heights must be 0.4-2.5 times the median and
bottom edges within 0.6 median heights of the median baseline. Retained lines
must pass both mean-confidence and detection-fraction gates. A few confident
accidents surrounded by rejected photo noise therefore do not make a message.
Words are preserved literally and joined by spaces in line order; low-confidence
words can be omitted. Always compare the full message before confirming.

If quality is insufficient, the app displays:
"We couldn't reliably read a message from this image. Try a clearer screenshot or paste the message instead."
The preview, manual text entry, retry, and explicit confirmation remain available.
No rejected text is placed in the editor or sent to a provider. This means the
extraction was unreliable, not that the image is definitely text-free. High-score
mistakes remain possible; photos with clear subtitles may legitimately yield text.
Mixed font sizes, heavy noise, or text over photography can cause false rejections.

Retest the bank screenshot: confirm bank name, Zelle, $3,500, and the reply
instructions survive, correct any omissions, then analyze and check exact evidence.
Retest the movie screenshot: expect the quoted warning, an empty review box, and
the preview. Verify no analysis occurs until you type a message and confirm it.
The original two images are not included in the repository; real-engine tests use
synthetic bank alerts, short messages, generated noise, and attributed photographs
in `tests/fixtures/ocr`. External AI requests remain mocked.
