# Running ScamBrake evaluations

`evaluate.py` is a command-line tool for comparing the analyzer's warning decisions
with labels on fictional messages. It does not implement detection, call Gemini
directly, or use Streamlit. Its own runtime dependencies are Python's standard
library and the existing fictional fixtures in `ui/mock_data.py` for mock mode.
Live mode additionally needs your teammate's analyzer and its dependencies.

Start PowerShell in the folder containing `evaluate.py`. On this computer:

```powershell
cd C:\Users\willi\Desktop\ScamBrake\ScamBrake
```

The examples below use `python` from an activated virtual environment. You can
replace `python` with `.\.venv\Scripts\python.exe` without activating it.

## Dataset

No dataset is created automatically. If the team has not made one yet, explicitly
create a small fictional starter file:

```powershell
python evaluate.py --create-template data/cases.csv
```

This command refuses to overwrite an existing file. It creates six cases (four dev,
two test), intended to exercise the tool. Expand your team's dataset separately;
the intended 20 dev / 10 test balance is a design target, not a validation rule.
Fictional labels are authored expectations, not proof that real messages are scams.

The required UTF-8 CSV header is:

```csv
id,text,ground_truth,split
```

| Column | Meaning |
| --- | --- |
| `id` | Unique, nonempty case identifier |
| `text` | Fictional message; quote CSV fields containing commas or newlines |
| `ground_truth` | Exactly `scam` or `legitimate` |
| `split` | Exactly `dev` or `test` |
| `expected_signals` (optional) | Pipe-separated types, such as `urgency\|impersonation` |
| `expected_amount` (optional) | Expected amount, such as `$500` |
| `expected_payment_method` (optional) | Expected method, such as `Zelle` |
| `scenario` (optional) | Human-readable scenario description |

Leave optional expectations blank to skip their checks. Every row is validated
before split selection; errors in unselected rows are still reported. Duplicate
IDs, missing text, invalid labels/splits, or malformed CSV stop the run before
analysis. The evaluator never sends labels or expected annotations to the provider.

## Mock evaluation

```powershell
python evaluate.py --help
python evaluate.py --mode mock --data data/cases.csv --split dev
```

Mock and dev are the defaults. The mock provider reuses the three exact fictional
frontend fixtures. Other messages receive unknown simulations. It never imports
the live analyzer or calls Gemini. Every console report, JSON summary, and CSV row
is labeled **SIMULATED RESULTS — NOT REAL GEMINI MODEL PERFORMANCE**.

Mock mode tests the evaluator's plumbing, not the quality of an AI model. Even
perfect mock metrics would not establish real model accuracy. Coverage makes the
unrecognized cases visible.

## Live evaluation and teammate integration

Person 2 should expose this synchronous function in `analyzer.py`:

```python
def analyze_input(text="", image_bytes=None, mime_type=None):
    # Delegate to the existing Gemini implementation and return its dictionary.
    ...
```

The same analysis dictionary used by the frontend is accepted: `risk_level`,
`summary`, a `signals` list with `type`, `title`, `evidence`, and `explanation`, and
optional `requested_amount`, `payment_method`, and `claimed_sender`. Optional text
can be omitted or null. Missing signals default to an empty list; a supplied signals
value must be a list, and each signal must have a nonempty string type. Invalid risk
values or wrong field types are recorded as malformed responses, never low concern.

A text-only `analyze_input(text=...)` function is also supported. Other signatures
need a wrapper in the teammate's module. Set `SCAMBRAKE_ANALYZER_MODULE` to a Python
dotted module name if it lives elsewhere. Configure API access in that module;
the evaluator does not own prompts, keys, model selection, or API setup.

```powershell
python evaluate.py --mode live --data data/cases.csv --split dev --limit 5
python evaluate.py --mode live --data data/cases.csv --split dev --delay 1
python evaluate.py --mode live --data data/cases.csv --split test
python evaluate.py --mode live --data data/cases.csv --split all --threshold high
```

Live mode is explicit because calls may incur charges. It is independent of the
frontend's `SCAMBRAKE_DEMO_MODE` setting. The evaluator imports only the real analyzer
in live mode and never falls back to mocks when that analyzer fails. Per-case errors
are recorded and subsequent cases still run. Import/interface errors stop setup.
Ctrl+C during analysis or a delay saves a partial report when possible.

Use dev cases while tuning. Keep test cases held out until the configuration and
threshold are fixed; repeatedly tuning against test results defeats their purpose.
The evaluator does not change splits or thresholds automatically.

## Reading results

At the default moderate threshold, high and moderate concern mean `flagged`; low
means `not_flagged`. At the high threshold, moderate also means `not_flagged`.
Unknown is always unassessed.

| Outcome | Interpretation |
| --- | --- |
| TP | Fictional scam case flagged |
| TN | Fictional legitimate case not flagged |
| FP | Fictional legitimate case flagged |
| FN | Fictional scam case not flagged |
| UNKNOWN | Valid unknown assessment; excluded from confusion matrix |
| ERROR | Malformed response, provider failure, or interrupted call; excluded |

Accuracy is `(TP + TN) / assessed`; precision is `TP / (TP + FP)`; recall is
`TP / (TP + FN)`; F1 is `2 * precision * recall / (precision + recall)`; false
positive rate is `FP / (FP + TN)`. These are assessed-only rates. Coverage is
`assessed / attempted`, so unknowns and errors reduce coverage. Undefined metrics
are `N/A` in the console and `null` in JSON, rather than fabricated zeroes.

Always read classification metrics alongside coverage, unknowns, and errors.
Performance on a small fictional dataset is not real-world fraud detection accuracy.

Evidence checks normalize case and whitespace and look for the quote in the source
message; they do not check semantics. Amount matching handles US dollar formatting
such as `$1,000` versus `USD 1000.00`, preserves explicit other currencies, and does
not convert currencies. Payment methods compare case and whitespace. Signal checks
list found, missing, and unexpected types. Missing expected annotations are not
evaluated; missing actual details are mismatches when expectations are provided.
Failed/malformed responses have no detail checks performed. These checks remain
separate from the confusion matrix and classification metrics.

## Reports, exit codes, and tests

JSON summaries and CSV case results go into `reports/` by default. Timestamped,
unique filenames preserve previous runs. Choose another directory with
`--output-dir`. JSON rates are fractions, while console rates are percentages.
CSV rows contain duration, risk, decision, outcome, detected types, checks, and a
safe error category. CSV strings are guarded against spreadsheet formula injection.
Neither output stores submitted message content, evidence quote text, or screenshots.
No model/prompt version metadata is invented.

Exit codes: `0` = completed without case errors (unknowns can still occur), `1` =
completed with case errors, `2` = invalid arguments or fatal setup/report failure,
`130` = interrupted. Classification mistakes do not cause a nonzero exit code.

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests/test_evaluate.py -q
python -m pytest -q
```

Tests inject responses and do not contact APIs. They cover validation, thresholds,
metrics, malformed/unknown/failure cases, evidence/details, report safety, label
leakage, mock isolation, live signature compatibility, and partial runs.

Major functions: `load_dataset`/`validate_dataset` check input; `get_mock_analysis`
and `get_live_analyzer` select providers; `normalize_analysis` validates output;
`evaluate_case` calls the provider and compares its decision; `calculate_metrics`
computes rates; `check_evidence_quotes`/`check_extracted_details` check explanations;
`build_summary`, `print_evaluation_report`, and `save_reports` produce reports.
`main` coordinates selection, calls, and CLI exit status.

This version evaluates text only. Screenshot evaluation and grading intervention
questions are future extensions, with no claims that either was performed.
