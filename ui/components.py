"""Native accessible controls; untrusted strings are displayed as plain text."""
import re
import streamlit as st
from . import integration, state
from .mock_data import FAMILY_MESSAGE, REMINDER_MESSAGE
from .validation import validate_text, validate_image, InputError

PRIVACY = "Remove sensitive personal information before submitting. Your content will be sent to an AI service for analysis. ScamBrake cannot guarantee that a payment request is legitimate."
DISCLAIMER = "ScamBrake identifies possible warning signs and suggests verification steps. Its analysis is not a guarantee of fraud or legitimacy."
ANSWERS = ["No, I haven't verified", "Yes, I verified independently", "I'm not sure"]
RISK_LABELS = {"high": "High concern", "moderate": "Some concerns", "low": "No strong warning signs identified", "unknown": "Unable to assess"}


def how_it_works():
    st.subheader("How ScamBrake works")
    for title, detail in [("1 · Submit", "Paste a message or upload a screenshot."), ("2 · Understand", "Review possible warning signs and supporting evidence."), ("3 · Verify", "Confirm the request using an independent contact channel.")]:
        st.markdown(f"**{title}**")
        st.caption(detail)


def submit_analysis():
    if st.session_state.busy:
        return
    state.clear_results()
    st.session_state.busy = True
    try:
        if st.session_state.input_method == "Paste a message":
            kwargs = {"text": validate_text(st.session_state.message)}
        else:
            image = st.session_state.uploaded_image
            if image is None:
                raise InputError("Upload a valid screenshot before analyzing it.")
            kwargs = {"image_bytes": image["bytes"], "mime_type": image["mime_type"]}
        with st.spinner("Reviewing your payment request..."):
            analysis = integration.analyze_input(**kwargs, demo=st.session_state.demo_mode)
            intervention = integration.build_intervention(analysis, demo=st.session_state.demo_mode)
        st.session_state.update(analysis=analysis, intervention=intervention, stage="results")
    except (InputError, integration.ServiceError) as exc:
        st.session_state.error = str(exc)
    except Exception:
        st.session_state.error = "We couldn't review this request right now. Please try again."
    finally:
        st.session_state.busy = False
    st.rerun()


def submission():
    main, aside = st.columns([2.2, 1], gap="large")
    with main, st.container(border=True, key="input_card"):
        st.subheader("Check a payment request")
        st.caption("A moment to check. A better-informed decision.")
        st.radio("Input method", ["Paste a message", "Upload a screenshot"], horizontal=True,
                 key="input_method", on_change=state.input_changed)
        if st.session_state.input_method == "Paste a message":
            st.text_area("Payment request", key="message", height=185,
                         placeholder="Paste the text message, email, or payment request you received...",
                         on_change=state.input_changed)
            length = len(st.session_state.message)
            st.caption(f"{length:,} / 5,000 characters")
            if length > 5000:
                st.error("Please shorten your message to 5,000 characters or fewer.")
            label = "Analyze message"
        else:
            upload = st.file_uploader("Upload a screenshot of the payment request", type=["png", "jpg", "jpeg"],
                                      accept_multiple_files=False, key=f"upload_{st.session_state.upload_generation}",
                                      on_change=state.input_changed, help="PNG or JPEG · up to 5 MB. Use the × beside the filename to remove it.")
            if upload is not None:
                try:
                    image = validate_image(upload.name, upload.getvalue())
                    st.session_state.uploaded_image = image
                    st.image(image["bytes"], caption="Screenshot preview", width="stretch")
                    st.text(image["name"])
                except InputError as exc:
                    st.session_state.uploaded_image = None
                    st.error(str(exc))
            label = "Analyze screenshot"
        if st.session_state.error:
            st.error(st.session_state.error)
        if st.button("Retry analysis" if st.session_state.error else label, type="primary", width="stretch",
                     disabled=st.session_state.busy, key="analyze", icon=":material/search:"):
            submit_analysis()
        st.caption(PRIVACY)
        if st.session_state.demo_mode:
            st.caption("In demo mode, analysis stays local and uses fictional fixtures. Custom text and screenshots receive a generic simulation.")
        st.divider()
        st.caption("TRY AN EXAMPLE · FICTIONAL MESSAGES")
        a, b = st.columns(2)
        a.button("Family emergency scam", key="family_example", width="stretch", on_click=state.load_example, args=(FAMILY_MESSAGE,))
        b.button("Legitimate payment reminder", key="reminder_example", width="stretch", on_click=state.load_example, args=(REMINDER_MESSAGE,))
    with aside:
        with st.container(border=True, key="how_card"):
            how_it_works()
            st.divider()
            st.markdown("**Trust the pause.**")
            st.caption("You stay in control. ScamBrake offers information and a practical next step before you decide.")


def results():
    analysis = st.session_state.analysis
    st.header("Your analysis")
    st.caption("Review the warning signs before making a payment decision.")
    risk = analysis["risk_level"]
    with st.container(border=True, key="summary_card"):
        label = RISK_LABELS[risk]
        {"high": st.error, "moderate": st.warning, "low": st.success, "unknown": st.info}[risk](label)
        st.text(analysis["summary"])
    st.subheader("Payment details")
    for column, key, label in zip(st.columns(3), ["requested_amount", "payment_method", "claimed_sender"], ["Requested amount", "Payment method", "Claimed sender"]):
        with column, st.container(border=True):
            st.caption(label)
            st.text(analysis[key] or "Not specified")
    with st.container(border=True, key="signals_card"):
        st.subheader("Warning signs")
        if not analysis["signals"]:
            st.info("No warning signs were returned. This does not establish that the request is legitimate.")
        icons = {"urgency": "◷", "impersonation": "♙", "secrecy": "◈", "threats": "!", "payment_method": "$", "discouraging_verification": "↗"}
        for signal in analysis["signals"]:
            with st.container(border=True):
                st.text(f"{icons.get(signal['type'], '•')}  {signal['title']}")
                st.text(signal["explanation"])
                if signal["evidence"]:
                    st.caption("Supporting quote")
                    st.text(f'“{signal["evidence"]}”')
    st.subheader("What this means")
    st.text(analysis["summary"])
    st.caption("An independent check of the sender, amount, and recipient can help you decide what to do next.")
    if integration.audio_available():
        if st.button("Listen to explanation", key="listen"):
            try:
                with st.spinner("Preparing audio..."):
                    st.session_state.audio = integration.get_audio(analysis["summary"])
                st.session_state.audio_error = None
            except integration.ServiceError as exc:
                st.session_state.audio_error = str(exc)
        if st.session_state.audio_error:
            st.warning(st.session_state.audio_error)
        if st.session_state.audio:
            st.audio(st.session_state.audio, format="audio/mpeg", autoplay=False)
    a, b = st.columns([2, 1])
    a.button("Pause & Verify", type="primary", icon=":material/shield:", width="stretch", on_click=state.change_stage, args=("verify",))
    b.button("Check another message", width="stretch", on_click=state.start_over)


def verification():
    intervention = st.session_state.intervention
    with st.container(border=True, key="verification_card"):
        st.caption("STEP 3 · AN INDEPENDENT CHECK")
        st.header("Pause & Verify")
        st.caption("One small check could prevent a costly mistake.")
        st.text(intervention["question"])
        st.text(intervention["context"])
        st.session_state.answer_widget = st.session_state.verification_answer
        st.radio("Have you verified the request?", ANSWERS, index=None, key="answer_widget", on_change=state.answer_changed)
        if st.button("Continue", key="continue", type="primary", disabled=st.session_state.verification_answer is None):
            st.session_state.continued_answer = st.session_state.verification_answer
        answer = st.session_state.continued_answer
        if answer:
            st.divider()
            if answer == ANSWERS[1]:
                st.info("Independent verification is an important step. ScamBrake cannot independently confirm who you contacted, so make sure the payment amount and recipient match what you verified.")
            else:
                st.info("Take a moment to confirm the request independently before sending money.")
                if answer == ANSWERS[2]:
                    st.text("Independently locate contact information or use saved contacts. Do not rely on phone numbers or links supplied in the message.")
            st.subheader("Your verification checklist")
            st.caption("Local progress tracking only. Checking an item does not mean ScamBrake verified it.")
            actions = intervention["recommended_actions"]
            for index, action in enumerate(actions):
                # Native checkbox labels are Markdown: escape punctuation to prevent links.
                label = re.sub(r"([\\`*_{}\[\]()<>#+.!|~-])", r"\\\1", action)
                st.session_state[f"check_{index}"] = st.session_state.checklist_completion.get(index, False)
                st.checkbox(label, key=f"check_{index}", on_change=state.checklist_changed, args=(index,))
            count = sum(bool(st.session_state.checklist_completion.get(i)) for i in range(len(actions)))
            st.caption(f"{count} of {len(actions)} steps marked by you.")
        a, b = st.columns(2)
        a.button("Back to results", width="stretch", on_click=state.change_stage, args=("results",))
        b.button("Check another message", width="stretch", on_click=state.start_over)
