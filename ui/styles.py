"""Static presentation only. Never interpolate submitted or provider text here."""
from base64 import b64encode
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote
import streamlit as st

LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "scambrake-logo.png"


@lru_cache(maxsize=1)
def logo_data():
    return b64encode(LOGO_PATH.read_bytes()).decode("ascii")


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
    .block-container { max-width: 1280px; padding-top: 1rem; padding-bottom: 2rem; }
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
    /* Keep the official-source link gold in every state, without a hover change. */
    .st-key-official_source_button [data-testid="stLinkButton"] > a,
    .st-key-official_source_button [data-testid="stLinkButton"] > a:is(:hover, :focus, :active) {
      background: linear-gradient(135deg, #F9E0A6 0%, #F4D58D 100%) !important;
      color: #001427 !important; border: none !important;
      border-radius: 10px; min-height: 44px; font-weight: 700;
      box-shadow: 0 0 20px rgba(244, 213, 141, .25) !important;
      transition: none !important; text-decoration: none !important;
    }
    .st-key-official_source_button [data-testid="stLinkButton"] > a * {
      color: #001427 !important;
    }
    .st-key-official_source_button [data-testid="stLinkButton"] > a:focus-visible {
      outline: 3px solid #F4D58D !important; outline-offset: 3px;
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
    [data-testid="stText"], [data-testid="stText"] * { color: #c1c1c1 !important; }
    .st-key-summary_card { border-left: 4px solid #F4D58D; }
    .st-key-verification_card { border-top: 4px solid #708D81; }
    button:focus-visible, textarea:focus-visible { outline: 3px solid #F4D58D !important; outline-offset: 3px; }
    .stAlert { border-radius: 12px; }
    .st-bw { color: #F4F7FA; }
    /* Keep the inherited palette and font. Red is reserved for high concern. */
    .brand { min-height: 52px; gap: 12px; }
    .brand-logo { width: 48px; height: 48px; flex: 0 0 48px; }
    .brand .brand-logo { background: transparent; padding: 0; border-radius: 0; }
    .st-key-question_panel, .st-key-auth_panel, .st-key-social_panel, .st-key-pause_panel {
      background: rgba(112, 141, 129, 0.12);
      border: 1px solid rgba(244, 213, 141, 0.25); border-radius: 18px;
      box-shadow: 0 8px 24px rgba(0, 20, 39, 0.28);
    }
    .st-key-question_prompt, .st-key-ask_prompt {
      background: rgba(112, 141, 129, 0.08); border-radius: 12px;
      padding: .8rem 1rem; border: 1px solid rgba(112, 141, 129, .35);
    }
    /* Only the three strategy accordions; retain native summary keyboard behavior. */
    .st-key-questionnaire_feedback .st-key-feedback_headline [data-testid="stText"] {
      color: #F4D58D !important; font-weight: 750;
    }
    :is(.st-key-auth_panel, .st-key-social_panel, .st-key-pause_panel)
      [data-testid="stExpander"] details {
      background: #001427 !important; color: #F4F7FA !important;
      border: 1px solid rgba(244, 213, 141, .25); border-radius: 12px;
    }
    :is(.st-key-auth_panel, .st-key-social_panel, .st-key-pause_panel)
      [data-testid="stExpander"] summary,
    :is(.st-key-auth_panel, .st-key-social_panel, .st-key-pause_panel)
      [data-testid="stExpander"] summary:is(:hover, :focus, :focus-visible),
    :is(.st-key-auth_panel, .st-key-social_panel, .st-key-pause_panel)
      [data-testid="stExpander"] details[open] > summary {
      background: #001427 !important; color: #F4F7FA !important;
      border-radius: 12px;
    }
    :is(.st-key-auth_panel, .st-key-social_panel, .st-key-pause_panel)
      [data-testid="stExpander"] summary * { color: #F4F7FA !important; }
    :is(.st-key-auth_panel, .st-key-social_panel, .st-key-pause_panel)
      [data-testid="stExpander"] summary svg { fill: currentColor !important; }
    :is(.st-key-auth_panel, .st-key-social_panel, .st-key-pause_panel)
      [data-testid="stExpander"] summary:focus-visible {
      outline: 3px solid #F4D58D !important; outline-offset: 3px;
    }
    .st-key-payment_amount, .st-key-payment_method, .st-key-payment_sender {
      min-height: 120px; background: rgba(112, 141, 129, 0.12);
      border: 1px solid rgba(244, 213, 141, .5); border-radius: 16px;
      box-shadow: 0 0 0 1px rgba(244, 213, 141, .12),
        0 0 24px rgba(244, 213, 141, .16), 0 8px 24px rgba(0, 20, 39, .28);
    }
    .st-key-payment_amount strong, .st-key-payment_method strong, .st-key-payment_sender strong {
      font-weight: 750; color: #F4D58D;
    }
    .st-key-payment_amount [data-testid="stText"], .st-key-payment_method [data-testid="stText"],
    .st-key-payment_sender [data-testid="stText"] { overflow-wrap: anywhere; }
    .st-key-risk_high [data-testid="stAlert"] {
      background: #DC2626 !important; border: 1px solid #DC2626 !important;
      border-radius: 12px; box-shadow: 0 0 22px rgba(220, 38, 38, .25);
    }
    .st-key-risk_high [data-testid="stAlert"] * { color: #FFFFFF !important; }
    .st-key-risk_high strong { font-weight: 800; }
    .st-key-signals_card { border-color: rgba(244, 213, 141, .4); }
    .st-key-results_layout h3 { margin-top: .2rem; }
    .stButton > button { transition: box-shadow 140ms ease, filter 140ms ease; }
    .stButton > button:hover { box-shadow: 0 0 20px rgba(244, 213, 141, .25); }
    @media(prefers-reduced-motion: reduce) { .stButton > button { transition: none; } }
    @media(max-width: 700px) {
      .block-container { padding: 1rem; }
      .st-key-hero { padding: 1.5rem; }
      [data-testid="stHorizontalBlock"] { flex-direction: column; gap: .75rem; }
      [data-testid="stColumn"] { width: 100% !important; min-width: 0 !important; flex: 1 1 100% !important; }
    }
    </style>""", unsafe_allow_html=True)


def brand(*, on_click):
    # One native button makes both the logo and name keyboard/click accessible.
    # The decorative SVG viewport crops transparent padding, preserving the PNG.
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="881 484 663 640">
    <image width="2360" height="1640" href="data:image/png;base64,{logo_data()}"/></svg>'''
    logo_url = "data:image/svg+xml," + quote(svg, safe="")
    st.markdown(f'''<style>
    .st-key-brand_home button,
    .st-key-brand_home button:is(:hover, :focus, :active) {{
      background: transparent !important; color: #F4D58D !important;
      border: none !important; box-shadow: none !important; transition: none;
      padding: 0; min-height: 52px; gap: 12px; border-radius: 6px;
    }}
    .st-key-brand_home button * {{ color: #F4D58D !important; }}
    .st-key-brand_home button p {{ font-size: 1.3rem; font-weight: 750; }}
    .st-key-brand_home button::before {{
      content: ""; display: block; width: 48px; height: 48px;
      flex: 0 0 48px; background: url("{logo_url}") center / contain no-repeat;
      pointer-events: none;
    }}
    </style>''', unsafe_allow_html=True)
    st.button("ScamBrake", key="brand_home", on_click=on_click)
