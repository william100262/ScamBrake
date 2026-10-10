"""Native accessible controls; untrusted strings are displayed as plain text."""
import re
from hashlib import sha256
import streamlit as st
from . import integration, state
from .mock_data import FAMILY_MESSAGE, REMINDER_MESSAGE
from .validation import validate_text, InputError
from ocr import OCRError, UNREADABLE_MESSAGE

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
            if not st.session_state.ocr_valid:
                raise InputError("Upload a valid screenshot before analyzing it.")
            kwargs = {"text": validate_text(st.session_state.ocr_text)}
        with st.spinner("Reviewing your payment request..."):
            # analyze_with_interventions runs a single analysis and also returns the
            # four-card bundle built from the ORIGINAL analyzer output (temporary demo).
            analysis, cards = integration.analyze_with_interventions(**kwargs, demo=st.session_state.demo_mode)
            intervention = integration.build_intervention(analysis, demo=st.session_state.demo_mode)
        st.session_state.update(analysis=analysis, intervention=intervention, interventions=cards, stage="results")
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
    intervention_cards()
    a, b = st.columns([2, 1])
    a.button("Pause & Verify", type="primary", icon=":material/shield:", width="stretch", on_click=state.change_stage, args=("verify",))
    b.button("Check another message", width="stretch", on_click=state.start_over)


# --- TEMPORARY four-card intervention demo -------------------------------------
# A minimal preview of the intervention backend, wired to real build_interventions
# output. Not Denise's final design; kept self-contained for easy later removal.
INTERVENTION_CARDS = [("questioning", "Questioning"), ("authority", "Authority"),
                      ("social_influence", "Social Influence"), ("diversion", "Diversion")]


def _escape_markdown(text):
    # Native checkbox/markdown labels interpret Markdown; escape untrusted punctuation.
    return re.sub(r"([\\`*_{}\[\]()<>#+.!|~-])", r"\\\1", text)


def intervention_cards():
    cards = st.session_state.interventions
    strategies = cards.get("interventions") if isinstance(cards, dict) else None
    if not strategies:
        return
    st.divider()
    st.caption("TEMPORARY DEMO · FOUR INTERVENTION CARDS · NOT FINAL DESIGN")
    st.subheader("Intervention strategies")
    st.caption("A temporary preview of the intervention backend. Denise's final frontend will replace this layout and styling.")
    columns = st.columns(2)
    for position, (key, title) in enumerate(INTERVENTION_CARDS):
        card = strategies.get(key)
        if not isinstance(card, dict):
            continue
        with columns[position % 2], st.container(border=True):
            _intervention_card(key, title, card)


def _intervention_card(key, fallback_title, card):
    st.caption(fallback_title.upper())
    st.text(card.get("title") or fallback_title)
    st.text(card.get("message") or "")
    if key == "questioning":
        options = [opt.get("label", "") for opt in card.get("options", []) if isinstance(opt, dict)]
        if options:
            # Mirror the Pause & Verify pattern: persist the choice across reruns.
            st.session_state.intervention_answer_widget = st.session_state.intervention_answer
            st.radio("Your response", options, index=None, key="intervention_answer_widget",
                     on_change=state.intervention_answer_changed)
    elif key == "authority":
        source = card.get("source") if isinstance(card.get("source"), dict) else {}
        name, label, url = source.get("name"), source.get("label"), source.get("url")
        if url:
            st.link_button(label or name or "View official guidance", url, width="stretch")
            if name:
                st.caption(f"Source: {name}")
        else:
            st.caption("No verified official source is available for this scenario.")
    elif key == "social_influence":
        matched = [sig for sig in card.get("matched_signals", []) if isinstance(sig, str)]
        if matched:
            st.caption("Matched signals")
            st.text(", ".join(matched))
        else:
            st.caption("No specific scam-pattern signals were matched.")
    elif key == "diversion":
        actions = [act for act in card.get("actions", []) if isinstance(act, dict)]
        if actions:
            st.caption("Verification checklist")
            for action in actions:
                action_id = str(action.get("id", ""))
                widget_key = f"icheck_{action_id}"
                st.session_state[widget_key] = st.session_state.intervention_checks.get(action_id, False)
                st.checkbox(_escape_markdown(action.get("label", "")), key=widget_key,
                            on_change=state.intervention_check_changed, args=(action_id,))


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
