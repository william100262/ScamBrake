"""Temporary UI contract fixtures. No personalization or answer interpretation.

Used only when the proposed backend API is absent, with a visible preview label.
Remove this fallback after the backend integration is merged and verified.
"""
from copy import deepcopy

QUESTIONNAIRE = {"questions": [
    {"id": "independent_contact", "text": "Have you independently contacted the claimed sender?"},
    {"id": "expected_request", "text": "Were you expecting this request?"},
    {"id": "confirmed_details", "text": "Have you independently checked the requested details?"},
]}
FEEDBACK = {
    "headline": "Temporary feedback preview",
    "summary": "This fixed mock response demonstrates the feedback layout. Your answers have not been interpreted.",
    "concerns": [], "recommended_actions": [],
}

def build_questionnaire(original_analysis):
    return deepcopy(QUESTIONNAIRE)

def review_questionnaire(questionnaire, answers):
    return deepcopy(FEEDBACK)
