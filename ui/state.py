"""Predictable, ephemeral workflow state; callbacks run before widgets render."""
import streamlit as st


def initialize(demo):
    defaults = {"stage": "submit", "input_method": "Paste a message", "message": "", "upload_generation": 0,
                "uploaded_image": None, "analysis": None, "intervention": None, "verification_answer": None,
                "continued_answer": None, "demo_mode": demo, "error": None, "busy": False,
                "show_how": False, "audio": None, "audio_error": None, "checklist_completion": {}}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if st.session_state.demo_mode != demo:
        clear_results()
        st.session_state.demo_mode = demo


def clear_results():
    for key in list(st.session_state):
        if key.startswith("check_") or key == "answer_widget":
            del st.session_state[key]
    st.session_state.update(stage="submit", analysis=None, intervention=None, verification_answer=None,
                            continued_answer=None, error=None, busy=False, audio=None, audio_error=None, checklist_completion={})


def input_changed():
    clear_results()
    st.session_state.uploaded_image = None


def load_example(message):
    clear_results()
    st.session_state.message = message
    st.session_state.input_method = "Paste a message"
    st.session_state.uploaded_image = None
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
