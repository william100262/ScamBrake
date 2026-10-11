VERIFICATION_QUESTIONS = {
    "family_emergency": [
        "Can you call your family member using a number you already know?",
        "Can another trusted family member confirm the emergency?"
    ],

    "bank_impersonation": [
        "Have you contacted your bank using the number on your card?",
        "Did you verify the request directly with your bank?"
    ],

    
    
    "invoice_fraud": [
        "Were you expecting this invoice?",
        "Can you confirm the invoice with the company using its official contact information?"
    ],

    "suspicious_payment": [
        "Do you recognize the person requesting this payment?",
        "Can you verify the payment request through another trusted method?"
    ],

    "general": [
        "Do you recognize the sender?",
        "Can you independently verify the information?"
    ],

    "unknown": [
        "Can you verify the sender's identity through a trusted channel?",
        "Does this message ask you to send money or share personal information?"
    ]
    
    
}

SAFE_ACTIONS = {
    "family_emergency": [
        "Do not send money until you verify the emergency.",
        "Call your family member using a trusted phone number."
    ],

    "bank_impersonation": [
        "Do not share your password or verification codes.",
        "Contact your bank using its official phone number."
    ],

    "invoice_fraud": [
        "Do not pay the invoice until you confirm it is legitimate.",
        "Contact the company using contact information you already trust."
    ],

    "suspicious_payment": [
        "Do not send money until you verify who is requesting it.",
        "Avoid clicking payment links in suspicious messages."
    ],

    "general": [
        "Do not click suspicious links or share personal information.",
        "Verify the sender through an independent trusted source."
    ],

    "unknown": [
        "Pause before sending money or sharing personal information.",
        "Contact the sender through a trusted channel to confirm the request."
    ]
}

def get_verification_questions(analysis):

    scenario = analysis.get("scenario", "unknown")

    if scenario in VERIFICATION_QUESTIONS:
        return VERIFICATION_QUESTIONS[scenario]

    return [
        "Can you verify this request through a trusted source?"
    ]

def get_safe_actions(analysis):

    scenario = analysis.get("scenario", "unknown")

    if scenario in SAFE_ACTIONS:
        return SAFE_ACTIONS[scenario]

    return [
        "Do not send money or share sensitive information until you verify the request."
    ]

def build_intervention(analysis):

    questions = get_verification_questions(analysis)
    actions = get_safe_actions(analysis)

    return {
        "verification_questions": questions,
        "safe_actions": actions
    }

# test code 1 function
if __name__ == "__main__":

    scenarios = [
        "family_emergency",
        "bank_impersonation",
        "invoice_fraud",
        "suspicious_payment",
        "general",
        "unknown"
    ]

    for scenario in scenarios:

        example = {
            "scenario": scenario,
            "risk_level": "medium"
        }

        result = build_intervention(example)

        print(f"\nScenario: {scenario}")

        print("Verification Questions:")
        for question in result["verification_questions"]:
            print("-", question)

        print("Safe Actions:")
        for action in result["safe_actions"]:
            print("-", action)
