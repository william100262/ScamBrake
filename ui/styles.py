"""Static presentation only. Never interpolate submitted or provider text here."""
import streamlit as st


def apply_styles():
    st.markdown("""<style>
    .stApp {
      background: linear-gradient(180deg, #001427 0%, #0b1d2b 100%);
      color: #F4F7FA;
    }
    [data-testid="stElementContainer"],
    [data-testid="stMarkdownContainer"],
    [data-testid="stWidgetLabel"],
    .stText { color: #F4F7FA; }
    label, [data-testid="stWidgetLabel"] { color: #F4F7FA; }
    header[data-testid="stHeader"] { display: none; }
    div[data-testid="stDecoration"] { display: none; }
    .block-container { max-width: 1100px; padding-top: 1rem; padding-bottom: 2rem; }
    h1,h2,h3 { letter-spacing: -.035em; color: #F4D58D; }
    h2 { font-size: 1.65rem !important; }
    h3 { font-size: 1.15rem !important; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 18px; }
    .st-key-input_card, .st-key-how_card, .st-key-verification_card,
    .st-key-summary_card, .st-key-signals_card {
      background: rgba(112, 141, 129, 0.12);
      border: 1px solid rgba(244, 213, 141, 0.18);
      border-radius: 18px;
      box-shadow: 0 8px 24px rgba(0, 20, 39, 0.28);
      color: #F4F7FA;
    }
    .st-key-hero {
      background: linear-gradient(135deg, #708D81 0%, #001427 100%);
      color: #F8FAFC;
      border-radius: 22px;
      padding: 2.3rem 2.5rem;
      margin: .5rem 0 1.2rem;
      border: 1px solid rgba(244, 213, 141, 0.4);
    }
    .st-key-hero h1 { color: #F4D58D; font-size: clamp(2rem, 4vw, 3.25rem); padding-top: .2rem; }
    .st-key-hero p { color: #E9F5F0; max-width: 650px; font-size: 1.05rem; }
    .st-key-hero [data-testid="stCaptionContainer"] p { color: #F4D58D; letter-spacing: .14em; font-size: .72rem; }
    .brand { display: flex; align-items: center; gap: 10px; font-size: 1.3rem; font-weight: 750; color: #F4D58D; }
    .brand svg { background: #708D81; padding: 7px; width: 38px; height: 38px; border-radius: 11px; }
    .stButton > button {
      border-radius: 10px; min-height: 44px; font-weight: 700;
      background: linear-gradient(135deg, #F4D58D 0%, #F0C66A 100%);
      border: none; color: #001427 !important; box-shadow: 0 8px 18px rgba(244, 213, 141, 0.2);
    }
    .stButton > button * { color: #001427 !important; }
    .stButton > button:hover {
      background: linear-gradient(135deg, #F9E0A6 0%, #F4D58D 100%);
      border: none; color: #001427 !important;
    }
    .stTextArea textarea {
      border-radius: 12px; font-size: 1rem; line-height: 1.65;
      background: #F4D58D !important; color: #001427 !important;
      border: 1px solid #F4D58D !important;
      box-shadow: inset 0 0 0 1px rgba(0, 20, 39, 0.08);
    }
    .stTextArea textarea::placeholder { color: rgba(0, 20, 39, 0.72); }
    [data-testid="stFileUploader"] {
      border-radius: 12px;
      background: #F4D58D !important;
      border: 1px solid #F4D58D !important;
    }
    [data-testid="stFileUploader"] > div { background: #F4D58D !important; }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] p, [data-testid="stFileUploader"] span {
      color: #001427 !important;
    }
    [data-testid="stTooltipContent"],
    [data-testid="stTooltipContent"] * { color: #000 !important; }
    [data-testid="stCaptionContainer"] p { color: #E0EAE4; }
    [data-testid="stCaptionContainer"] p { color: #64748B; }
    [data-testid="stText"], [data-testid="stText"] * { color: #c1c1c1 !important; }
    .st-key-summary_card { border-left: 4px solid #F4D58D; }
    .st-key-verification_card { border-top: 4px solid #708D81; }
    button:focus-visible, textarea:focus-visible { outline: 3px solid #F4D58D !important; outline-offset: 3px; }
    .stAlert { border-radius: 12px; }
    .st-bw { color: #F4F7FA; }
    @media(max-width: 700px) {
      .block-container { padding: 1rem; }
      .st-key-hero { padding: 1.5rem; }
      [data-testid="stHorizontalBlock"] { flex-direction: column; gap: .75rem; }
      [data-testid="stColumn"] { width: 100% !important; min-width: 0 !important; flex: 1 1 100% !important; }
    }
    </style>""", unsafe_allow_html=True)


def brand():
    st.markdown('''<div class="brand"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M12 3 20 6v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z" stroke="#fff" stroke-width="1.7"/>
    <path d="m8 12 3 3 5-6" stroke="#99F6E4" stroke-width="1.7" stroke-linecap="round"/>
    </svg>ScamBrake</div>''', unsafe_allow_html=True)
