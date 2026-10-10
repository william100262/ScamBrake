"""Evaluation integrity tests. All analyzers are canned or injected, never live."""
import csv
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import evaluate as ev
from ui.mock_data import FAMILY_MESSAGE


def case(label="scam", text=FAMILY_MESSAGE, **extra):
    return {"id": "001", "text": text, "ground_truth": label, "split": "dev", **extra}


def provider(risk, **extra):
    return lambda **kwargs: {"risk_level": risk, **extra}


def write_dataset(path, rows, fields=None):
    with path.open("w", newline="", encoding="utf-8-sig") as target:
        writer = csv.DictWriter(target, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def summary(results, selected=None):
    return ev.build_summary(results, ev.parse_arguments([]), len(results) if selected is None else selected)


def test_dataset_loading(tmp_path):
    path = write_dataset(tmp_path / "cases.csv", [case(text="Line one\nLine two, with comma")])
    assert ev.load_dataset(path)[0]["text"] == "Line one\nLine two, with comma"


@pytest.mark.parametrize("rows", [[], [case(id="")], [case(text=" \n")], [case(label="safe")],
    [case(split="train")], [case(), case()], [case(), case(id="002", split="bad")]],
    ids=["empty", "missing-id", "blank-text", "bad-label", "bad-split", "duplicate", "invalid-unselected-row"])
def test_dataset_validation(rows):
    with pytest.raises(ev.EvaluationError):
        ev.validate_dataset(rows)


@pytest.mark.parametrize("content", ["", "id,text\n1,message\n", "id,text,ground_truth,split\n1,test,scam\n",
    "id,text,ground_truth,split\n1,test,scam,dev,extra\n", "id,id,text,ground_truth,split\n",
    'id,text,ground_truth,split\n1,"unfinished,scam,dev'])
def test_invalid_csv(tmp_path, content):
    path = tmp_path / "bad.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ev.EvaluationError):
        ev.load_dataset(path)


def test_missing_csv(tmp_path):
    with pytest.raises(ev.EvaluationError, match="Dataset not found"):
        ev.load_dataset(tmp_path / "missing.csv")


@pytest.mark.parametrize("risk,threshold,decision", [("high", "moderate", "flagged"),
    ("moderate", "moderate", "flagged"), ("moderate", "high", "not_flagged"),
    ("low", "moderate", "not_flagged"), ("unknown", "high", "unassessed")])
def test_warning_mapping(risk, threshold, decision):
    assert ev.classify_prediction(risk, threshold) == decision


def test_confusion_matrix_and_metrics():
    results = [ev.evaluate_case(case(), provider("high")), ev.evaluate_case(case("legitimate"), provider("low")),
               ev.evaluate_case(case("legitimate"), provider("moderate")), ev.evaluate_case(case(), provider("low")),
               ev.evaluate_case(case(), provider("unknown")), ev.evaluate_case(case(), lambda **kwargs: None)]
    report = summary(results)
    assert report["confusion_matrix"] == {"TP": 1, "TN": 1, "FP": 1, "FN": 1}
    assert report["attempted"] == 6 and report["assessed"] == 4
    assert report["unknown"] == 1 and report["errors"] == 1 and report["unassessed"] == 2
    assert report["malformed_responses"] == 1
    metrics = report["metrics"]
    for key in ("accuracy", "precision", "recall", "f1", "false_positive_rate"):
        assert metrics[key] == .5
    assert metrics["coverage"] == pytest.approx(4 / 6)


def test_metrics_asymmetric_and_zero_denominators():
    result = ev.calculate_metrics(4, 4, 0, 1, 10)
    assert result["accuracy"] == pytest.approx(8 / 9)
    assert result["precision"] == 1
    assert result["recall"] == .8
    assert result["f1"] == pytest.approx(8 / 9)
    assert result["false_positive_rate"] == 0
    assert result["coverage"] == .9
    assert all(value is None for value in ev.calculate_metrics(0, 0, 0, 0, 0).values())
    result = ev.calculate_metrics(0, 2, 0, 0, 3)
    assert result["accuracy"] == 1 and result["coverage"] == pytest.approx(2 / 3)
    assert result["precision"] is None and result["recall"] is None and result["f1"] is None
    assert ev.calculate_metrics(0, 0, 1, 1, 2)["f1"] is None


def test_missing_optional_fields_and_nulls():
    assert ev.normalize_analysis({"risk_level": " LOW "})["signals"] == []
    result = ev.normalize_analysis({"risk_level": "unknown", "summary": None,
        "signals": [{"type": "urgency", "evidence": None, "explanation": None}], "requested_amount": None})
    assert result["signals"][0]["evidence"] is None
    assert ev.evaluate_case(case(), provider("unknown"))["outcome"] == "UNKNOWN"


@pytest.mark.parametrize("raw", [None, [], {}, {"risk_level": "safe"}, {"risk_level": ["high"]},
    {"risk_level": "low", "signals": None}, {"risk_level": "high", "signals": ["urgency"]},
    {"risk_level": "high", "signals": [{}]}, {"risk_level": "low", "requested_amount": 500}])
def test_malformed_output(raw):
    result = ev.evaluate_case(case(), lambda **kwargs: raw)
    assert result["outcome"] == "ERROR"
    assert result["decision"] == "unassessed"
    assert result["error_category"].startswith("malformed_response:")


def test_evidence_and_detail_checks():
    data = case(text="Please SEND   $500 now via Zelle.", expected_amount="USD 500.00",
                expected_payment_method=" zelle ", expected_signals="urgency|secrecy")
    signals = [{"type": "urgency", "evidence": "send $500 NOW"}, {"type": "impersonation", "evidence": "I'm Dad"}]
    result = ev.evaluate_case(data, provider("high", signals=signals, requested_amount="$500", payment_method="ZELLE"))
    assert result["evidence_checked"] == 2 and result["unsupported_evidence"] == 1
    assert result["amount_match"] and result["payment_method_match"]
    assert result["signals_found"] == ["urgency"]
    assert result["signals_missing"] == ["secrecy"]
    assert result["signals_unexpected"] == ["impersonation"]
    missing = ev.evaluate_case(data, provider("low"))
    assert missing["amount_match"] is False and missing["payment_method_match"] is False
    absent = ev.evaluate_case(case(), provider("low"))
    assert absent["amount_match"] is None and not absent["signals_evaluated"]
    assert ev.normalized_amount("$1,000.00") == ev.normalized_amount("USD 1000")
    assert ev.normalized_amount("€500") != ev.normalized_amount("$500")


def test_failures_do_not_leak_provider_errors():
    def fails(**kwargs):
        raise RuntimeError("secret API key and raw submitted message")
    result = ev.evaluate_case(case(), fails)
    assert result["error_category"] == "analysis_failure"
    assert "secret" not in json.dumps(result)
    assert summary([result])["processing_failures"] == 1


def test_no_answer_leakage():
    seen = []
    def analyzer(**kwargs):
        seen.append(kwargs)
        return ev.get_mock_analysis(**kwargs)
    scam = ev.evaluate_case(case(expected_signals="different"), analyzer)
    legitimate = ev.evaluate_case(case("legitimate", expected_amount="$10000"), analyzer)
    assert seen == [{"text": FAMILY_MESSAGE, "image_bytes": None, "mime_type": None}] * 2
    assert scam["risk_level"] == legitimate["risk_level"] == "high"
    assert scam["outcome"] == "TP" and legitimate["outcome"] == "FP"


def test_reports_and_formula_injection(tmp_path):
    result = ev.evaluate_case(case(id=" \t=HYPERLINK(\"bad\")"), provider("high"))
    report = summary([result])
    paths = ev.save_reports(report, [result], tmp_path)
    assert json.loads(paths[0].read_text(encoding="utf-8")) == report
    with paths[1].open(encoding="utf-8-sig", newline="") as source:
        row = next(csv.DictReader(source))
    assert row["id"].startswith("'")
    assert row["outcome"] == "TP" and row["evaluation_notice"] == ev.SIMULATED_NOTICE
    assert "text" not in row and FAMILY_MESSAGE not in paths[0].read_text(encoding="utf-8")
    second = ev.save_reports(report, [result], tmp_path)
    assert second != paths and all(path.exists() for path in (*paths, *second))


def test_report_write_failure_cleanup(tmp_path, monkeypatch):
    original = Path.open
    def fail_csv(self, *args, **kwargs):
        if self.suffix == ".csv":
            raise PermissionError
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "open", fail_csv)
    result = ev.evaluate_case(case(), provider("low"))
    with pytest.raises(ev.EvaluationError, match="Unable to save"):
        ev.save_reports(summary([result]), [result], tmp_path)
    assert not list(tmp_path.iterdir())


def test_report_directory_failure(tmp_path):
    path = tmp_path / "file"
    path.write_text("not a directory")
    with pytest.raises(ev.EvaluationError):
        ev.save_reports(summary([]), [], path)


def test_mock_main_never_imports_live(tmp_path, monkeypatch, capsys):
    path = write_dataset(tmp_path / "cases.csv", [case(), case(id="002", split="test")])
    def forbidden(*args, **kwargs):
        pytest.fail("live import attempted")
    monkeypatch.setattr(ev, "get_live_analyzer", forbidden)
    monkeypatch.setattr(ev.importlib, "import_module", forbidden)
    reports = tmp_path / "reports"
    assert ev.main(["--data", str(path), "--output-dir", str(reports)]) == 0
    output = capsys.readouterr().out
    assert ev.SIMULATED_NOTICE in output
    data = json.loads(next(reports.glob("*.json")).read_text(encoding="utf-8"))
    assert data["attempted"] == 1 and data["split"] == "dev" and data["simulated"]


def test_live_interface_adapter(monkeypatch):
    seen = []
    monkeypatch.setenv("SCAMBRAKE_ANALYZER_MODULE", "test_evaluation_analyzer")
    monkeypatch.setitem(sys.modules, "test_evaluation_analyzer", SimpleNamespace(analyze_input=lambda text: seen.append(text) or {"risk_level": "low"}))
    assert ev.evaluate_case(case(), ev.get_live_analyzer())["outcome"] == "FN"
    assert seen == [FAMILY_MESSAGE]


@pytest.mark.parametrize("module", [SimpleNamespace(), SimpleNamespace(analyze_input=lambda unrelated, required: {}), SimpleNamespace(analyze_input="bad")])
def test_incompatible_live_module(monkeypatch, module):
    monkeypatch.setenv("SCAMBRAKE_ANALYZER_MODULE", "test_evaluation_analyzer")
    monkeypatch.setitem(sys.modules, "test_evaluation_analyzer", module)
    with pytest.raises(ev.EvaluationError):
        ev.get_live_analyzer()


def test_live_missing_and_continues_after_failure(tmp_path, monkeypatch, capsys):
    path = write_dataset(tmp_path / "cases.csv", [case(), case(id="002"), case(id="003", split="test")])
    monkeypatch.setenv("SCAMBRAKE_ANALYZER_MODULE", "missing_scamb_evaluation_module")
    assert ev.main(["--mode", "live", "--data", str(path)]) == 2
    assert "Cannot load" in capsys.readouterr().err
    calls = []
    def analyzer(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RuntimeError("do not print me")
        return {"risk_level": "low"}
    monkeypatch.setattr(ev, "get_live_analyzer", lambda: analyzer)
    output = tmp_path / "reports"
    assert ev.main(["--mode", "live", "--data", str(path), "--split", "all", "--limit", "2", "--output-dir", str(output)]) == 1
    report = json.loads(next(output.glob("*.json")).read_text())
    assert report["attempted"] == 2 and report["errors"] == 1 and report["assessed"] == 1
    assert not report["simulated"] and "do not print me" not in capsys.readouterr().out


def test_interrupt_saves_partial_report(tmp_path, monkeypatch):
    path = write_dataset(tmp_path / "cases.csv", [case(), case(id="002")])
    def interrupted(**kwargs):
        raise KeyboardInterrupt
    monkeypatch.setattr(ev, "get_live_analyzer", lambda: interrupted)
    output = tmp_path / "reports"
    assert ev.main(["--mode", "live", "--data", str(path), "--output-dir", str(output)]) == 130
    report = json.loads(next(output.glob("*.json")).read_text())
    assert report["interrupted"] and report["attempted"] == 1 and report["not_attempted"] == 1


def test_template_is_explicit_and_no_overwrite(tmp_path):
    path = tmp_path / "cases.csv"
    assert ev.main(["--create-template", str(path)]) == 0
    original = path.read_bytes()
    assert len(ev.load_dataset(path)) == 6
    assert ev.main(["--create-template", str(path)]) == 2
    assert path.read_bytes() == original


@pytest.mark.parametrize("argv", [["--limit", "0"], ["--delay", "-1"], ["--delay", "nan"], ["--delay", "inf"], ["--threshold", "low"], ["--split", "train"]])
def test_argument_validation(argv):
    with pytest.raises(SystemExit) as error:
        ev.parse_arguments(argv)
    assert error.value.code == 2
