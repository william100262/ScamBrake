"""Run from the repository root: python -m streamlit run app.py."""
from dotenv import load_dotenv
import streamlit as st
from ui import components, integration, state, styles

st.set_page_config(page_title="ScamBrake · Pause before you pay", page_icon="🛡️", layout="wide")
styles.apply_styles()
# Load configuration before mode selection or the first local OCR request.
load_dotenv()
try:
    demo = integration.demo_enabled()
except integration.ServiceError as exc:
    st.error(str(exc))
    st.stop()
state.initialize(demo)

left, right = st.columns([4, 1])
with left:
    styles.brand(on_click=state.start_over)
with right:
    st.button("How it works", width="stretch", on_click=state.toggle_how)
if st.session_state.show_how:
    with st.container(border=True):
        components.how_it_works()

st.caption("Demo mode — simulated analysis" if demo else "Live mode · AI-assisted analysis")
stage = st.session_state.stage
if stage != "results":
    components.hero()
st.caption({"submit": "01  SUBMIT   /   02  UNDERSTAND   /   03  VERIFY", "results": "01  SUBMITTED   /   02  UNDERSTAND   /   03  VERIFY", "verify": "01  SUBMITTED   /   02  REVIEWED   /   03  VERIFY"}[stage])
if stage == "submit":
    components.submission()
elif stage == "results":
    components.results()
else:
    # Sessions from the old verification page return to the inline experience.
    st.session_state.stage = "results"
    components.results()
st.divider()
st.caption(components.DISCLAIMER)
