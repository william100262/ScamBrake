"""Static presentation only. Never interpolate submitted or provider text here."""
import streamlit as st


def apply_styles():
    st.markdown("""<style>
    .stApp { background: #F8FAFC; }
    .block-container { max-width: 1100px; padding-top: 2rem; padding-bottom: 2rem; }
    h1,h2,h3 { letter-spacing: -.035em; }
    h2 { font-size: 1.65rem !important; }
    h3 { font-size: 1.15rem !important; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 18px; }
    .st-key-input_card, .st-key-how_card, .st-key-verification_card,
    .st-key-summary_card, .st-key-signals_card { background: white; border-radius: 18px;
      box-shadow: 0 4px 20px rgba(15,23,42,.035); }
    .st-key-hero { background: #142339; color: #F8FAFC; border-radius: 22px;
      padding: 2.3rem 2.5rem; margin: .5rem 0 1.2rem; }
    .st-key-hero h1 { color: white; font-size: clamp(2rem, 4vw, 3.25rem); padding-top: .2rem; }
    .st-key-hero p { color: #CBD5E1; max-width: 650px; font-size: 1.05rem; }
    .st-key-hero [data-testid="stCaptionContainer"] p { color: #99F6E4; letter-spacing: .14em; font-size: .72rem; }
    .brand { display: flex; align-items: center; gap: 10px; font-size: 1.3rem; font-weight: 750; color: #142339; }
    .brand svg { background: #142339; padding: 7px; width: 38px; height: 38px; border-radius: 11px; }
    .stButton > button { border-radius: 10px; min-height: 44px; font-weight: 600; }
    .stTextArea textarea { border-radius: 12px; font-size: 1rem; line-height: 1.65; }
    [data-testid="stFileUploader"] { border-radius: 12px; }
    [data-testid="stCaptionContainer"] p { color: #64748B; }
    .st-key-summary_card { border-left: 4px solid #64748B; }
    .st-key-verification_card { border-top: 4px solid #0F766E; }
    button:focus-visible, textarea:focus-visible { outline: 3px solid #0F766E !important; outline-offset: 3px; }
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
