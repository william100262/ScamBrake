SCENARIOS = {
    "family_emergency",
    "bank_impersonation",
    "invoice_fraud",
    "suspicious_payment",
    "general",
    "unknown"
}

RISK_LEVELS = {
    "low",
    "medium",
    "high",
    "uncertain"
}

def validate_analysis(analysis):

    if not isinstance(analysis, dict):  #check if analysis is true fromn all these catergories  
        return False

    if "scenario" not in analysis:
        return False

    if "risk_level" not in analysis:
        return False

    if analysis["scenario"] not in SCENARIOS:
        return False
    if analysis["risk_level"] not in RISK_LEVELS:
        return False

    return True 