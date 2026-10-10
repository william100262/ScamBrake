"""Predictable, ephemeral workflow state; callbacks run before widgets render."""
import streamlit as st


def initialize(demo):
    defaults = {"stage": "submit", "input_method": "Paste a message", "message": "", "upload_generation": 0,
                "uploaded_image": None, "ocr_digest": None, "ocr_text": "", "ocr_error": None, "ocr_valid": False, "analysis": None, "intervention": None, "verification_answer": None,
                "continued_answer": None, "demo_mode": demo, "error": None, "busy": False,
                "show_how": False, "audio": None, "audio_error": None, "checklist_completion": {},
                # Temporary four-card intervention demo (see ui.components).
                "interventions": None, "intervention_answer": None, "intervention_checks": {}}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if st.session_state.demo_mode != demo:
        clear_results()
        st.session_state.demo_mode = demo


def clear_results():
    for key in list(st.session_state):
        if key.startswith("check_") or key.startswith("icheck_") or key in ("answer_widget", "intervention_answer_widget"):
            del st.session_state[key]
    st.session_state.update(stage="submit", analysis=None, intervention=None, verification_answer=None,
                            continued_answer=None, error=None, busy=False, audio=None, audio_error=None, checklist_completion={},
                            interventions=None, intervention_answer=None, intervention_checks={})


def reset_screenshot():
    st.session_state.update(uploaded_image=None, ocr_digest=None, ocr_text="", ocr_error=None, ocr_valid=False)


def input_changed():
    clear_results()
    reset_screenshot()


def method_changed():
    input_changed()
    st.session_state.upload_generation += 1


def load_example(message):
    clear_results()
    st.session_state.message = message
    st.session_state.input_method = "Paste a message"
    reset_screenshot()
    st.session_state.upload_generation += 1


def start_over():
    load_example("")


def change_stage(stage):
    st.session_state.stage = stage


def toggle_how():
    st.session_state.show_how = not st.session_state.show_how


def answer_changed():
    st.session_state.verification_answer = st.session_state.answer_widget
    st.session_state.continued_answer = None


def checklist_changed(index):
    st.session_state.checklist_completion[index] = st.session_state[f"check_{index}"]


# --- Temporary four-card intervention demo callbacks ---
def intervention_answer_changed():
    st.session_state.intervention_answer = st.session_state.intervention_answer_widget


def intervention_check_changed(action_id):
    st.session_state.intervention_checks[action_id] = st.session_state[f"icheck_{action_id}"]
