"""Native accessible controls; untrusted strings are displayed as plain text."""
import re
from hashlib import sha256
import streamlit as st
from . import integration, state
from .mock_data import FAMILY_MESSAGE, REMINDER_MESSAGE
from .validation import validate_text, InputError
from ocr import OCRError, UNREADABLE_MESSAGE
from intervention_questions import build_verification

PRIVACY = "Remove sensitive personal information before submitting. Your content will be sent to an AI service for analysis. ScamBrake cannot guarantee that a payment request is legitimate."
DISCLAIMER = "ScamBrake identifies possible warning signs and suggests verification steps. Its analysis is not a guarantee of fraud or legitimacy."
ANSWERS = ["No, I haven't verified", "Yes, I verified independently", "I'm not sure"]
RISK_LABELS = {"high": "High concern", "moderate": "Some concerns", "low": "No strong warning signs identified", "unknown": "Unable to assess"}


def hero():
    with st.container(key="hero"):
        st.caption("A MOMENT OF CAUTION. A LITTLE MORE CLARITY.")
        st.title("Pause before you pay.")
        st.write("Not sure if a payment request is legitimate? ScamBrake helps you spot warning signs and verify the request before sending money.")


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
            if not st.session_state.ocr_valid:
                raise InputError("Upload a valid screenshot before analyzing it.")
            kwargs = {"text": validate_text(st.session_state.ocr_text)}
        with st.spinner("Reviewing your payment request..."):
            analysis = integration.analyze_input(**kwargs, demo=st.session_state.demo_mode)
            intervention = integration.build_intervention(analysis, demo=st.session_state.demo_mode)
        model = build_verification(analysis.get("analyzer_result", analysis))
        st.session_state.update(analysis=analysis, intervention=intervention, verification_model=model, stage="results")
        prepare_questions()
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
                 key="input_method", on_change=state.method_changed)
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
            upload = st.file_uploader("Upload a screenshot of the payment request", type=["png", "jpg", "jpeg", "webp"],
                                      accept_multiple_files=False, key=f"upload_{st.session_state.upload_generation}",
                                      on_change=state.input_changed, help="PNG, JPEG, or WebP · up to 5 MB. Use the × beside the filename to remove it.")
            if upload is None:
                state.reset_screenshot()
            else:
                data = upload.getvalue()
                digest = sha256(data).hexdigest() + upload.name
                retry = st.button("Retry text extraction", key="retry_ocr") if st.session_state.ocr_error else False
                if digest != st.session_state.ocr_digest or retry:
                    state.clear_results()
                    state.reset_screenshot()
                    st.session_state.ocr_digest = digest
                    try:
                        with st.spinner("Reading screenshot text locally..."):
                            st.session_state.ocr_text = integration.extract_screenshot(data, upload.name)
                        st.session_state.ocr_valid = True
                        if not st.session_state.ocr_text:
                            st.session_state.ocr_error = UNREADABLE_MESSAGE
                    except OCRError as exc:
                        st.session_state.ocr_valid = True
                        st.session_state.ocr_error = str(exc)
                    except InputError as exc:
                        st.session_state.ocr_error = str(exc)
                    except Exception:
                        st.session_state.ocr_error = "We couldn't read this screenshot. Try again or paste its text instead."
                if st.session_state.ocr_valid:
                    st.image(data, caption="Screenshot preview", width="stretch")
                    st.caption("Text extraction stays on this computer. Low-confidence words may be omitted. Compare the full message, including names, amounts, payment methods, and URLs, before confirming.")
                    st.text_area("Review and correct extracted text", key="ocr_text", height=220,
                                 on_change=state.clear_results)
                    st.caption(f"{len(st.session_state.ocr_text):,} / 5,000 characters · Shorten longer text before analysis.")
                if st.session_state.ocr_error:
                    st.warning(st.session_state.ocr_error)
            label = "Analyze confirmed text"
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
            st.markdown("**Trust the pause**")
            st.caption("You stay in control. ScamBrake offers information and a practical next step before you decide.")


def results():
    analysis = st.session_state.analysis
    with st.container(key="results_layout"):
        overview, prompts = st.columns([1.15, 1], gap="large")
        with overview:
            hero()
            st.header("Your analysis")
            st.caption("Review the warning signs before making a payment decision.")
            analysis_details(analysis)
        with prompts:
            decision_prompts()
    st.button("Check another message", key="results_restart", on_click=state.start_over)


def analysis_details(analysis):
    """The left column follows the team's risk, payment, and evidence hierarchy."""
    risk = analysis["risk_level"]
    with st.container(border=True, key="summary_card"):
        label = RISK_LABELS[risk]
        with st.container(key=f"risk_{risk}"):
            if risk == "high":
                st.error("**High concern**", icon=":material/report:")
            else:
                {"moderate": st.warning, "low": st.success, "unknown": st.info}[risk](label)
        st.text(analysis["summary"])
    st.subheader("Payment details")
    for column, key, label, card_key in zip(st.columns(3, gap="small"),
            ["requested_amount", "payment_method", "claimed_sender"],
            ["Requested amount", "Payment method", "Claimed sender"],
            ["payment_amount", "payment_method", "payment_sender"]):
        with column, st.container(border=True, key=card_key):
            st.markdown(f"**{label}**")
            st.text(analysis[key] or "Not specified")
    with st.container(border=True, key="signals_card"):
        st.subheader(":material/search: Warning signs")
        if not analysis["signals"]:
            st.info("No warning signs were returned. This does not establish that the request is legitimate.")
        icons = {"urgency": "schedule", "impersonation": "person_search", "secrecy": "visibility_off",
                 "threats": "report", "payment_method": "payments", "discouraging_verification": "phone_disabled",
                 "suspicious_link": "link", "spelling": "spellcheck"}
        for index, signal in enumerate(analysis["signals"]):
            with st.container(border=True, key=f"signal_{index}"):
                st.markdown(f":material/{icons.get(signal['type'], 'info')}:")
                st.text(signal["title"])
                st.text(signal["explanation"])
                if signal["evidence"]:
                    st.caption("Supporting quote")
                    st.text(f'“{signal["evidence"]}”')
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


def prepare_questions():
    """Questionnaire errors must not discard successful text/image analysis."""
    st.session_state.question_answers = {}
    st.session_state.questionnaire_feedback = None
    st.session_state.review_error = None
    try:
        analysis = st.session_state.analysis
        st.session_state.questionnaire_bundle = integration.prepare_questionnaire(analysis.get("analyzer_result", analysis))
        st.session_state.questionnaire_error = None
    except integration.ServiceError as exc:
        st.session_state.questionnaire_bundle = None
        st.session_state.questionnaire_error = str(exc)


def questionnaire_panel():
    """Render backend questions and feedback without interpreting responses."""
    if st.session_state.questionnaire_bundle is None and not st.session_state.questionnaire_error:
        prepare_questions()
    with st.container(key="inline_questions"):
        if st.session_state.questionnaire_error:
            st.warning(st.session_state.questionnaire_error)
            st.button("Retry verification questions", key="retry_questions", on_click=prepare_questions)
            return
        bundle = st.session_state.questionnaire_bundle
        if bundle["mock"]:
            st.info("Temporary questionnaire preview — backend functions are not connected. Questions and feedback use fixed mock data; answers are not interpreted.")
        st.caption("Your answers stay in this tab and are reviewed only when you select Review my answers.")
        questions = bundle["questionnaire"]["questions"]
        labels = {"yes": "Yes", "no": "No", "not_sure": "Not sure"}
        for question in questions:
            identifier = question["id"]
            key = f"question_answer_{identifier}"
            st.session_state[key] = st.session_state.question_answers.get(identifier)
            # Widget labels support Markdown; never turn backend content into links.
            label = re.sub(r"([\\`*_{}\[\]()<>#+.!|~-])", r"\\\1", question["text"])
            st.radio(label, list(labels), format_func=labels.get, index=None, horizontal=True,
                     key=key, on_change=state.contextual_answer_changed, args=(identifier,))
            if isinstance(question.get("explanation"), str):
                st.text(question["explanation"])
        answers = {q["id"]: st.session_state.question_answers.get(q["id"]) for q in questions}
        count = sum(value in labels for value in answers.values())
        st.caption(f"{count} of {len(questions)} answered")
        st.progress(count / len(questions))
        if st.button("Review my answers", key="review_answers", type="primary", width="stretch",
                     disabled=count != len(questions)):
            st.session_state.questionnaire_feedback = None
            try:
                with st.spinner("Reviewing your answers..."):
                    st.session_state.questionnaire_feedback = integration.review_answers(bundle, answers)
                st.session_state.review_error = None
            except integration.ServiceError as exc:
                st.session_state.review_error = str(exc)
        if st.session_state.review_error:
            st.error(st.session_state.review_error)
        feedback = st.session_state.questionnaire_feedback
        if feedback:
            with st.container(border=True, key="questionnaire_feedback"):
                with st.container(key="feedback_headline"):
                    st.text(feedback["headline"])
                st.text(feedback["summary"])
                for heading, field in (("Concerns", "concerns"), ("Recommended actions", "recommended_actions")):
                    if feedback[field]:
                        st.markdown(f"**{heading}**")
                        for item in feedback[field]:
                            st.text(item)


def decision_prompts():
    """Four distinct strategies; only Questioning reveals response controls."""
    model = st.session_state.verification_model
    if model is None:
        model = build_verification(st.session_state.analysis.get("analyzer_result", st.session_state.analysis))
        st.session_state.verification_model = model
    with st.container(border=True, key="question_panel"):
        st.subheader(":material/help: Question the request")
        st.caption("Check the claims using information you trust independently.")
        st.button("Hide verification questions" if st.session_state.questions_open else "Review verification questions",
                  key="question_verify", type="primary", width="stretch", on_click=state.toggle_questions)
        if st.session_state.questions_open:
            questionnaire_panel()
    with st.container(border=True, key="auth_panel"):
        st.subheader(":material/verified_user: What trusted sources recommend")
        authority = model["authority"]
        st.text(authority["guidance"])
        with st.expander("View official guidance"):
            source = authority.get("source")
            if source:
                st.text(source["name"])
                st.text(source["title"])
                # This model uses only curated, verified URLs, never submitted links.
                if source.get("url"):
                    with st.container(key="official_source_button"):
                        st.link_button("Open official source", source["url"])
            else:
                st.caption("General guidance only; no specific official source was supplied.")
            st.caption("The institution has not inspected your submitted message. Guidance is not proof of fraud or legitimacy.")
    with st.container(border=True, key="social_panel"):
        st.subheader(":material/group: Recognize the pattern")
        patterns = model["patterns"]
        st.text(patterns[0]["text"] if patterns else "No documented warning pattern was matched to the returned signals. You can still review the request with someone you trust.")
        with st.expander("Matched warning patterns"):
            if not patterns:
                st.caption("No matched patterns were returned.")
            for pattern in patterns:
                st.text(pattern["text"])
                if pattern.get("evidence"):
                    st.caption("Matched message evidence")
                    st.text(pattern["evidence"])
            st.caption("These possible tactics do not establish fraud. No claims are made about other ScamBrake users.")
    with st.container(border=True, key="pause_panel"):
        st.subheader(":material/pause_circle: Take a safer next step")
        st.caption("Pause the conversation while you check through independent channels.")
        with st.expander("Your independent verification checklist"):
            st.caption("Local progress only. Checking a box does not mean ScamBrake verified the action.")
            for action in model["actions"]:
                identifier = action["id"]
                key = f"action_check_{identifier}"
                st.session_state[key] = st.session_state.checklist_completion.get(identifier, False)
                label = re.sub(r"([\\`*_{}\[\]()<>#+.!|~-])", r"\\\1", action["text"])
                st.checkbox(label, key=key, on_change=state.action_changed, args=(identifier,))
            count = sum(bool(st.session_state.checklist_completion.get(a["id"])) for a in model["actions"])
            st.caption(f"{count} of {len(model['actions'])} steps marked by you.")
