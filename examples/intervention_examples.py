"""Print four fictional, schema-validated bundles without calling an AI service."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from intervention import build_interventions
from interventions.contract import validate_bundle

EXAMPLES = {
    "family_emergency": {
        "scenario": "family_emergency", "risk_level": "high",
        "signals": [{"type": "urgency", "evidence": "right away"},
                    {"type": "secrecy_demand", "evidence": "don't tell anyone"},
                    {"type": "suspicious_payment", "evidence": "Apple gift cards"}],
        "requested_amount": "$2,500", "payment_method": "Apple gift cards", "claimed_sender": "grandson Jake",
        "explanation": "A fictional claim of a grandson in jail asks for an urgent payment and secrecy.",
    },
    "bank_impersonation": {
        "scenario": "bank_impersonation", "risk_level": "high",
        "signals": [{"type": "account_threat", "evidence": "your account will be frozen"},
                    {"type": "suspicious_link", "evidence": "click https://bank-alert.example.invalid"}],
        "requested_amount": None, "payment_method": None, "claimed_sender": "Example Bank",
        "explanation": "A fictional bank warning threatens an account freeze and asks the recipient to follow a link.",
    },
    "invoice_fraud": {
        "scenario": "invoice_fraud", "risk_level": "medium",
        "signals": [{"type": "changed_payment_details", "evidence": "pay into our new bank account"}],
        "requested_amount": "$850", "payment_method": "bank transfer", "claimed_sender": "Example Supplies",
        "explanation": "A fictional supplier request changes the payment destination.",
    },
    "ambiguous_request": {
        "scenario": "general", "risk_level": "low", "signals": [],
        "requested_amount": "$20", "payment_method": None, "claimed_sender": "Alex",
        "explanation": "A fictional reminder with little suspicious evidence.",
    },
}


def generated_examples():
    results = {}
    for name, analysis in EXAMPLES.items():
        bundle = build_interventions(analysis)
        validate_bundle(bundle)
        results[name] = {"analysis": analysis, "result": bundle}
    return results


if __name__ == "__main__":
    print(json.dumps(generated_examples(), indent=2, ensure_ascii=True))
