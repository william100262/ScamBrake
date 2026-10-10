"""Evaluate warning behavior on fictional text cases, without a frontend or SDK.

Run ``python evaluate.py --help``. Mock results exercise this evaluation tool;
they say nothing about Gemini performance. Live mode calls the teammate's module.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import importlib
import inspect
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from typing import Callable
from uuid import uuid4

SIMULATED_NOTICE = "SIMULATED RESULTS — NOT REAL GEMINI MODEL PERFORMANCE"
REQUIRED_COLUMNS = {"id", "text", "ground_truth", "split"}
RISKS = {"high", "moderate", "low", "unknown"}
OUTCOMES = ("TP", "TN", "FP", "FN", "UNKNOWN", "ERROR")
Provider = Callable[..., dict]


class EvaluationError(ValueError):
    """A safe setup/report error suitable for display in the terminal."""


class ResponseError(ValueError):
    """An invalid analyzer response, distinct from a valid unknown assessment."""


def positive_integer(value: str) -> int:
    try:
        number = int(value)
        if number > 0:
            return number
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("must be a positive integer")


def nonnegative_seconds(value: str) -> float:
    try:
        number = float(value)
        if math.isfinite(number) and number >= 0:
            return number
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("must be a finite, nonnegative number of seconds")


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate ScamBrake warning decisions against fictional labels.")
    parser.add_argument("--mode", choices=("mock", "live"), default="mock")
    parser.add_argument("--data", type=Path, default=Path("data/cases.csv"))
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    parser.add_argument("--limit", type=positive_integer)
    parser.add_argument("--threshold", choices=("moderate", "high"), default="moderate")
    parser.add_argument("--delay", type=nonnegative_seconds, default=0, help="Seconds between calls, not after the last call.")
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    parser.add_argument("--create-template", type=Path, metavar="CSV_PATH",
                        help="Create a small fictional starter CSV and exit; never overwrite an existing file.")
    return parser.parse_args(argv)


def terminal_text(value: str, limit: int | None = 120) -> str:
    """Keep untrusted IDs on one line and remove terminal control sequences."""
    return "".join(char if char.isprintable() else "?" for char in value)[:limit]


def validate_dataset(rows: list[dict]) -> list[dict]:
    """Validate every row before split filtering, so bad data cannot be hidden."""
    if not rows:
        raise EvaluationError("The dataset has no examples.")
    seen = set()
    for row_number, row in enumerate(rows, start=2):
        prefix = f"CSV record {row_number}"
        for field in REQUIRED_COLUMNS:
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise EvaluationError(f"{prefix}: required field '{field}' is empty or missing.")
        row["id"] = row["id"].strip()
        if row["id"] in seen:
            raise EvaluationError(f"{prefix}: duplicate ID '{terminal_text(row['id'])}'.")
        seen.add(row["id"])
        if row["ground_truth"] not in {"scam", "legitimate"}:
            raise EvaluationError(f"{prefix}: ground_truth must be scam or legitimate.")
        if row["split"] not in {"dev", "test"}:
            raise EvaluationError(f"{prefix}: split must be dev or test.")
    return rows


def load_dataset(path: Path) -> list[dict]:
    """Read UTF-8 CSV (including Excel's UTF-8 BOM) using only the standard library."""
    try:
        with Path(path).open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source, strict=True)
            headers = reader.fieldnames
            if not headers or len(headers) != len(set(headers)):
                raise EvaluationError("The CSV needs a header with unique column names.")
            missing = REQUIRED_COLUMNS - set(headers)
            if missing:
                raise EvaluationError("Missing CSV columns: " + ", ".join(sorted(missing)))
            rows = []
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise EvaluationError(f"CSV near line {reader.line_num}: field count does not match the header.")
                rows.append(row)
    except FileNotFoundError:
        raise EvaluationError("Dataset not found. Supply --data with a CSV containing id,text,ground_truth,split, or explicitly use --create-template data/cases.csv.") from None
    except (OSError, UnicodeError, csv.Error):
        raise EvaluationError("Cannot read the dataset. Check access, UTF-8 encoding, and CSV quoting.") from None
    return validate_dataset(rows)


def normalize_analysis(raw) -> dict:
    """Validate risk/signals without replacing invalid output with a low prediction.

    Optional text may be absent or null. Wrong types are malformed, rather than
    silently removed. Unsupported evidence stays intact for the quality checks.
    """
    if not isinstance(raw, dict):
        raise ResponseError("response_not_dictionary")
    risk = raw.get("risk_level")
    if not isinstance(risk, str) or risk.strip().lower() not in RISKS:
        raise ResponseError("invalid_risk_level")

    def optional_text(value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ResponseError("invalid_metadata_type")
        return value.strip() or None

    signals = raw.get("signals", [])
    if not isinstance(signals, list):
        raise ResponseError("signals_not_list")
    normalized = []
    for signal in signals:
        if not isinstance(signal, dict) or not isinstance(signal.get("type"), str) or not signal["type"].strip():
            raise ResponseError("invalid_signal")
        normalized.append({"type": signal["type"].strip().lower(),
                           **{key: optional_text(signal.get(key)) for key in ("title", "evidence", "explanation")}})
    return {"risk_level": risk.strip().lower(), "signals": normalized,
            **{key: optional_text(raw.get(key)) for key in ("summary", "requested_amount", "payment_method", "claimed_sender")}}


def classify_prediction(risk_level: str, threshold: str = "moderate") -> str:
    if threshold not in {"moderate", "high"} or risk_level not in RISKS:
        raise ValueError("Unsupported risk level or threshold")
    if risk_level == "unknown":
        return "unassessed"
    return "flagged" if risk_level == "high" or (risk_level == "moderate" and threshold == "moderate") else "not_flagged"


def get_mock_analysis(text="", image_bytes=None, mime_type=None) -> dict:
    """Reuse fictional frontend fixtures, never labels or expected annotations.

    ui.mock_data uses only standard-library imports. This does not import
    Streamlit, the live analyzer, Gemini, or the frontend normalization adapter.
    Unrecognized messages yield a transparent unknown simulation.
    """
    from ui.mock_data import analyze_input
    return analyze_input(text=text, image_bytes=image_bytes, mime_type=mime_type)


def get_live_analyzer() -> Provider:
    """Load only in live mode; accept full contract or a simple text-only adapter."""
    module_name = os.environ.get("SCAMBRAKE_ANALYZER_MODULE", "analyzer")
    try:
        module = importlib.import_module(module_name)
    except Exception:
        raise EvaluationError("Cannot load the live analyzer. Add analyzer.py (or set SCAMBRAKE_ANALYZER_MODULE), install its dependencies, and configure its API access.") from None
    function = getattr(module, "analyze_input", None)
    if not callable(function) or inspect.iscoroutinefunction(function):
        raise EvaluationError("Live module must expose a synchronous callable analyze_input.")
    try:
        signature = inspect.signature(function)
        try:
            signature.bind(text="", image_bytes=None, mime_type=None)
            full_contract = True
        except TypeError:
            signature.bind(text="")
            full_contract = False
    except (TypeError, ValueError):
        raise EvaluationError("Incompatible analyze_input signature. Expected analyze_input(text='', image_bytes=None, mime_type=None), or a text-only function accepting text by keyword.") from None

    def analyze(text="", image_bytes=None, mime_type=None):
        if full_contract:
            return function(text=text, image_bytes=image_bytes, mime_type=mime_type)
        return function(text=text)
    return analyze


def normalized_words(text: str) -> str:
    return " ".join(text.casefold().split())


def check_evidence_quotes(text: str, signals: list[dict]) -> dict:
    source = normalized_words(text)
    quotes = [normalized_words(signal["evidence"]) for signal in signals if signal.get("evidence")]
    return {"evidence_checked": len(quotes), "unsupported_evidence": sum(quote not in source for quote in quotes)}


def normalized_amount(value: str):
    """Compare US dollar formatting while preserving explicit other currencies.

    $500, USD 500.00, and 500 compare equally. This is not currency conversion.
    Other formats fall back to literal case/whitespace normalization.
    """
    value = normalized_words(value)
    match = re.fullmatch(r"(?:(\$|usd|eur|gbp|€|£)\s*)?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?)(?:\s*(usd|eur|gbp))?", value)
    if not match:
        return ("literal", value)
    prefix, number, suffix = match.groups()
    symbols = {"$": "usd", "€": "eur", "£": "gbp"}
    currency = symbols.get(prefix, prefix) or suffix or "usd"
    if prefix and suffix and symbols.get(prefix, prefix) != suffix:
        return ("literal", value)
    try:
        return (currency, Decimal(number.replace(",", "")))
    except InvalidOperation:
        return ("literal", value)


def check_extracted_details(case: dict, analysis: dict) -> dict:
    result = {}
    for expected_key, actual_key, output_key, normalize in [
        ("expected_amount", "requested_amount", "amount_match", normalized_amount),
        ("expected_payment_method", "payment_method", "payment_method_match", normalized_words),
    ]:
        expected = case.get(expected_key, "").strip()
        actual = analysis.get(actual_key)
        result[output_key] = None if not expected else bool(actual and normalize(expected) == normalize(actual))
    expected_signals = case.get("expected_signals", "").strip()
    if expected_signals:
        expected = {part.strip().casefold() for part in expected_signals.split("|") if part.strip()}
        actual = {signal["type"].casefold() for signal in analysis["signals"]}
        result.update(signals_evaluated=True, signals_found=sorted(expected & actual),
                      signals_missing=sorted(expected - actual), signals_unexpected=sorted(actual - expected))
    else:
        result.update(signals_evaluated=False, signals_found=[], signals_missing=[], signals_unexpected=[])
    return result


def evaluate_case(case: dict, analyzer: Provider, threshold="moderate") -> dict:
    """Only text crosses the provider boundary. Labels are used after prediction."""
    started = time.perf_counter()
    result = {"id": case["id"], "split": case["split"], "ground_truth": case["ground_truth"],
              "risk_level": None, "decision": "unassessed", "outcome": "ERROR", "detected_signals": [],
              "evidence_checked": 0, "unsupported_evidence": 0, "detail_checks_performed": False,
              "amount_match": None, "payment_method_match": None, "signals_evaluated": False,
              "signals_found": [], "signals_missing": [], "signals_unexpected": [], "error_category": None}
    try:
        raw = analyzer(text=case["text"], image_bytes=None, mime_type=None)
        analysis = normalize_analysis(raw)
        decision = classify_prediction(analysis["risk_level"], threshold)
        if decision == "unassessed":
            outcome = "UNKNOWN"
        elif case["ground_truth"] == "scam":
            outcome = "TP" if decision == "flagged" else "FN"
        else:
            outcome = "FP" if decision == "flagged" else "TN"
        result.update(risk_level=analysis["risk_level"], decision=decision, outcome=outcome,
                      detected_signals=[signal["type"] for signal in analysis["signals"]], detail_checks_performed=True,
                      **check_evidence_quotes(case["text"], analysis["signals"]), **check_extracted_details(case, analysis))
    except ResponseError as exc:
        result["error_category"] = "malformed_response:" + str(exc)
    except KeyboardInterrupt:
        result["error_category"] = "interrupted"
    except Exception:
        # Never persist exception messages: a provider might embed a key or input.
        result["error_category"] = "analysis_failure"
    result["duration_seconds"] = round(time.perf_counter() - started, 6)
    return result


def safe_divide(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def calculate_metrics(tp: int, tn: int, fp: int, fn: int, attempted: int) -> dict:
    """Rates are fractions in JSON; zero denominators are None, displayed as N/A."""
    assessed = tp + tn + fp + fn
    precision, recall = safe_divide(tp, tp + fp), safe_divide(tp, tp + fn)
    f1 = safe_divide(2 * precision * recall, precision + recall) if precision is not None and recall is not None else None
    return {"accuracy": safe_divide(tp + tn, assessed), "precision": precision,
            "recall": recall, "f1": f1,
            "false_positive_rate": safe_divide(fp, fp + tn), "coverage": safe_divide(assessed, attempted)}


def build_summary(results: list[dict], args, selected_count: int, interrupted=False) -> dict:
    counts = Counter(result["outcome"] for result in results)
    matrix = {key: counts[key] for key in ("TP", "TN", "FP", "FN")}
    errors = [result for result in results if result["outcome"] == "ERROR"]
    details = {"cases_checked": sum(result["detail_checks_performed"] for result in results),
               "evidence_quotes_checked": sum(result["evidence_checked"] for result in results),
               "unsupported_evidence_quotes": sum(result["unsupported_evidence"] for result in results)}
    for key in ("amount_match", "payment_method_match"):
        checked = [result[key] for result in results if result[key] is not None]
        details[key] = {"evaluated": len(checked), "matches": sum(checked), "mismatches": len(checked) - sum(checked), "not_evaluated": len(results) - len(checked)}
    details["signal_types"] = {"cases_evaluated": sum(result["signals_evaluated"] for result in results),
                               **{key: sum(len(result[key]) for result in results) for key in ("signals_found", "signals_missing", "signals_unexpected")}}
    return {"run_timestamp": datetime.now(timezone.utc).isoformat(), "mode": args.mode,
            "simulated": args.mode == "mock", "notice": SIMULATED_NOTICE if args.mode == "mock" else "Live analyzer results on fictional examples; not proof of real-world fraud detection accuracy.",
            "dataset": str(args.data), "split": args.split, "threshold": args.threshold,
            "limit": args.limit, "delay_seconds": args.delay, "selected": selected_count, "attempted": len(results),
            "assessed": sum(matrix.values()), "unknown": counts["UNKNOWN"], "errors": counts["ERROR"],
            "unassessed": counts["UNKNOWN"] + counts["ERROR"],
            "malformed_responses": sum(result["error_category"].startswith("malformed_response:") for result in errors),
            "processing_failures": sum(result["error_category"] == "analysis_failure" for result in errors),
            "interrupted": interrupted, "not_attempted": selected_count - len(results),
            "confusion_matrix": matrix, "metrics": calculate_metrics(matrix["TP"], matrix["TN"], matrix["FP"], matrix["FN"], len(results)),
            "detail_checks": details}


def csv_safe(value):
    """Guard spreadsheet formulas, including prefixes hidden behind whitespace."""
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) and (value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n"))):
        return "'" + value
    return value


def save_reports(summary: dict, results: list[dict], output_dir: Path) -> tuple[Path, Path]:
    """Exclusive filenames prevent replacement; reports omit source messages."""
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:8]
    output_dir = Path(output_dir)
    json_path, csv_path = output_dir / f"summary_{run_id}.json", output_dir / f"cases_{run_id}.csv"
    created = []
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with json_path.open("x", encoding="utf-8") as target:
            created.append(json_path)
            json.dump(summary, target, indent=2, ensure_ascii=False, allow_nan=False)
            target.write("\n")
        with csv_path.open("x", encoding="utf-8-sig", newline="") as target:
            created.append(csv_path)
            if results:
                writer = csv.DictWriter(target, fieldnames=["run_timestamp", "warning_threshold", "evaluation_mode", "evaluation_notice", *results[0]])
                writer.writeheader()
                for result in results:
                    writer.writerow({key: csv_safe(value) for key, value in {
                        "run_timestamp": summary["run_timestamp"], "warning_threshold": summary["threshold"],
                        "evaluation_mode": summary["mode"], "evaluation_notice": summary["notice"], **result}.items()})
    except (OSError, TypeError, ValueError):
        for path in created:
            try:
                path.unlink()
            except OSError:
                pass
        raise EvaluationError("Unable to save both reports. Check the output directory and write permissions; no complete report pair was saved.") from None
    return json_path, csv_path


def print_evaluation_report(summary: dict):
    print("\nSCAMBRAKE — EVALUATION REPORT\n" + "=" * 66)
    print(summary["notice"])
    print(f"Mode: {summary['mode'].upper()} | Split: {summary['split'].upper()} | Threshold: {summary['threshold'].upper()}")
    print("\nMESSAGES")
    for key in ("selected", "attempted", "assessed", "unassessed", "unknown", "errors", "malformed_responses", "processing_failures", "not_attempted"):
        print(f"{key.replace('_', ' ').capitalize():<26} {summary[key]:>6}")
    print("\nCONFUSION MATRIX — ASSESSED ONLY")
    for key, title in [("TP", "True positives"), ("TN", "True negatives"), ("FP", "False positives"), ("FN", "False negatives")]:
        print(f"{title:<26} {summary['confusion_matrix'][key]:>6}")
    print("\nPERFORMANCE")
    meanings = {"accuracy": "correct warnings/non-warnings among assessed cases", "precision": "flagged cases labeled scam",
                "recall": "assessed scam cases flagged", "f1": "balance of precision and recall",
                "false_positive_rate": "assessed legitimate cases flagged", "coverage": "attempted cases with an assessed prediction"}
    for key, value in summary["metrics"].items():
        formatted = "N/A" if value is None else f"{value:.2%}"
        print(f"{key.replace('_', ' ').capitalize():<22} {formatted:>8}  {meanings[key]}")
    print("\nADDITIONAL CHECKS — NOT CLASSIFICATION METRICS")
    details = summary["detail_checks"]
    print(f"Evidence quotes checked: {details['evidence_quotes_checked']}; unsupported: {details['unsupported_evidence_quotes']}")
    for key in ("amount_match", "payment_method_match"):
        entry = details[key]
        print(f"{key.replace('_match', '').replace('_', ' ').capitalize()}: {entry['matches']} matches, {entry['mismatches']} mismatches, {entry['not_evaluated']} not evaluated")
    signals = details["signal_types"]
    print(f"Signal checks: {signals['cases_evaluated']} cases; found {signals['signals_found']}, missing {signals['signals_missing']}, unexpected {signals['signals_unexpected']}")
    print("Evidence matching checks literal text only; it is not semantic fact checking.")
    print("These warning decisions are not guarantees of fraud or legitimacy.")
    if summary["interrupted"]:
        print("Interrupted: this is a partial run; not-attempted cases are reported separately.")


def create_template(path: Path):
    """An explicitly requested small fictional fixture, not an evaluation result."""
    from ui.mock_data import FAMILY_MESSAGE, REMINDER_MESSAGE, MODERATE_MESSAGE
    rows = [
        ("dev01", FAMILY_MESSAGE, "scam", "dev", "impersonation|urgency|discouraging_verification", "$500", "Zelle", "family impersonation"),
        ("dev02", REMINDER_MESSAGE, "legitimate", "dev", "", "$75", "", "tutoring reminder"),
        ("dev03", MODERATE_MESSAGE, "scam", "dev", "payment_method", "$40", "Bank transfer", "fictional altered recipient details"),
        ("dev04", "Your $20 book club contribution is due next week. Please bring it to our usual meeting.", "legitimate", "dev", "", "$20", "", "book club reminder"),
        ("test01", "This is your bank. Transfer $900 to our recovery account now. Keep this secret.", "scam", "test", "impersonation|urgency|secrecy", "$900", "", "fictional bank impersonation"),
        ("test02", "The $30 pottery class fee is due Friday. Please use the payment method listed in your existing enrollment receipt.", "legitimate", "test", "", "$30", "", "class reminder"),
    ]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="") as target:
            writer = csv.writer(target)
            writer.writerow(["id", "text", "ground_truth", "split", "expected_signals", "expected_amount", "expected_payment_method", "scenario"])
            writer.writerows(rows)
    except FileExistsError:
        raise EvaluationError("Starter dataset not created: the target already exists. Choose a new path.") from None
    except OSError:
        raise EvaluationError("Unable to create the starter dataset. Check the path and write permissions.") from None


def main(argv=None) -> int:
    args = parse_arguments(argv)
    try:
        if args.create_template:
            create_template(args.create_template)
            print("Created six fictional starter cases. This small fixture does not represent real-world fraud performance.")
            print(terminal_text(str(args.create_template), limit=None))
            return 0
        cases = load_dataset(args.data)
        selected = [case for case in cases if args.split == "all" or case["split"] == args.split]
        if args.limit:
            selected = selected[:args.limit]
        if not selected:
            raise EvaluationError("No cases match the requested split.")
        analyzer = get_mock_analysis if args.mode == "mock" else get_live_analyzer()
        print(SIMULATED_NOTICE if args.mode == "mock" else "LIVE evaluation on fictional cases; API usage may apply.")
        results, interrupted = [], False
        for index, case in enumerate(selected):
            result = evaluate_case(case, analyzer, args.threshold)
            results.append(result)
            error = " | " + result["error_category"] if result["error_category"] else ""
            print(f"[{terminal_text(result['id'])}] {result['ground_truth'].upper():<10} | {(result['risk_level'] or 'N/A').upper():<8} | {result['outcome']}{error}")
            if result["error_category"] == "interrupted":
                interrupted = True
                break
            if args.delay and index < len(selected) - 1:
                try:
                    time.sleep(args.delay)
                except KeyboardInterrupt:
                    interrupted = True
                    break
        summary = build_summary(results, args, len(selected), interrupted)
        print_evaluation_report(summary)
        paths = save_reports(summary, results, args.output_dir)
        print("\nREPORTS SAVED")
        for path in paths:
            print(terminal_text(str(path.resolve()), limit=None))
        return 130 if interrupted else (1 if summary["errors"] else 0)
    except EvaluationError as exc:
        print("Evaluation stopped: " + str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Evaluation interrupted before reports could be completed.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    # PowerShell/piped output can otherwise use a legacy Windows code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
