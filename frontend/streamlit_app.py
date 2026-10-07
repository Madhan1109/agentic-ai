"""Streamlit chat UI for the Ideas2IT HR Chat Agent."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
ASSETS = Path(__file__).resolve().parent / "assets"
LOGIN_LOGO_PATH = ASSETS / "ideas2it-logo-square.png"
SIDE_LOGO_PATH = ASSETS / "ideas2it-logo-wide.png"
# Fallbacks if new assets are missing
if not LOGIN_LOGO_PATH.exists():
    LOGIN_LOGO_PATH = ASSETS / "ideas2it-logo.png"
if not SIDE_LOGO_PATH.exists():
    SIDE_LOGO_PATH = ASSETS / "ideas2it-logo.png"


def _logo_data_uri(path: Path) -> str:
    if path.exists():
        raw = path.read_bytes()
        return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
    return ""


LOGIN_LOGO_URI = _logo_data_uri(LOGIN_LOGO_PATH)
SIDE_LOGO_URI = _logo_data_uri(SIDE_LOGO_PATH)

st.set_page_config(
    page_title="Ideas2IT | HR Assistant",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  html, body, [class*="css"], .stApp, .stMarkdown, p, span, label, input, button, textarea {
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
  }

  /* Hide Streamlit top header strip + deploy chrome */
  header[data-testid="stHeader"] {
    background: transparent !important;
    height: 0 !important;
    min-height: 0 !important;
  }
  header[data-testid="stHeader"] * { display: none !important; }
  [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
  .stDeployButton, #MainMenu, footer { display: none !important; visibility: hidden !important; }
  .stApp > header { display: none !important; }

  .stApp { background: #e8eef8 !important; color: #1e3a5f; }

  [data-testid="stChatMessage"] {
    background: #ffffff !important;
    color: #1e3a5f !important;
    border: 1px solid #d7e3f4;
    border-radius: 14px;
    padding: 0.75rem 0.9rem;
    box-shadow: 0 8px 20px rgba(30, 77, 123, 0.06);
    margin-bottom: 0.55rem;
  }
  [data-testid="stChatMessage"] p,
  [data-testid="stChatMessage"] span,
  [data-testid="stChatMessage"] li { color: #1e3a5f !important; }

  .stButton>button {
    background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%) !important;
    color: #ffffff !important;
    border: 0 !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    box-shadow: 0 8px 18px rgba(37, 99, 235, 0.28);
    min-height: 2.5rem;
  }

  .stTextInput input, .stTextInput input:focus {
    background: #ffffff !important;
    color: #111827 !important;
    border: 1px solid #c5d4ea !important;
    border-radius: 12px !important;
  }

  [data-testid="stChatInput"] textarea {
    border-radius: 14px !important;
    border: 1px solid #c5d4ea !important;
    box-shadow: 0 8px 18px rgba(30, 77, 123, 0.06);
    background: #ffffff !important;
  }
</style>
"""

LOGIN_CSS = """
<style>
  [data-testid="stSidebar"] { display: none !important; visibility: hidden !important; }
  [data-testid="collapsedControl"] { display: none !important; }

  .stApp {
    background: linear-gradient(145deg, #0b4f9c 0%, #1565c0 42%, #1e88e5 100%) !important;
    min-height: 100vh !important;
  }
  [data-testid="stAppViewContainer"],
  [data-testid="stAppViewContainer"] > .main,
  section.main {
    background: transparent !important;
    min-height: 100vh !important;
  }
  section.main > div { min-height: 100vh !important; }
  .block-container {
    max-width: 440px !important;
    min-height: 100vh !important;
    padding: 1.5rem 1rem !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
  }

  [data-testid="stForm"] {
    background: #ffffff !important;
    border: 1px solid #d7e3f4 !important;
    border-radius: 22px !important;
    padding: 1rem 1.1rem 0.9rem !important;
    box-shadow: 0 22px 48px rgba(11, 79, 156, 0.28) !important;
  }

  .login-brand { text-align: center; }
  .login-brand img {
    width: 120px;
    height: auto;
    border-radius: 12px;
    margin: 0 auto 0.55rem;
    display: block;
  }
  .login-brand h1 {
    margin: 0;
    font-size: 1.35rem;
    color: #111827 !important;
    font-weight: 700;
  }
  .login-brand p {
    margin: 0.35rem auto 0;
    max-width: 340px;
    color: #111827 !important;
    font-size: 0.86rem;
    line-height: 1.4;
  }
  .login-chip {
    display: inline-block;
    margin-top: 0.55rem;
    margin-bottom: 0.75rem;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    background: #e8f1ff;
    border: 1px solid #c7dbf7;
    color: #111827 !important;
    font-size: 0.72rem;
    font-weight: 600;
  }

  [data-testid="stForm"] label,
  [data-testid="stForm"] label p,
  [data-testid="stForm"] label span,
  [data-testid="stForm"] [data-testid="stWidgetLabel"] * {
    color: #111827 !important;
  }

  /* Match email + password field widths: reserve a right gutter for the eye icon */
  [data-testid="stForm"] .stTextInput { width: 100% !important; }
  [data-testid="stForm"] [data-testid="stTextInputRootElement"] {
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    gap: 0.2rem !important;
    box-sizing: border-box !important;
  }
  [data-testid="stForm"] [data-testid="stTextInputRootElement"] > div {
    flex: 1 1 auto !important;
    width: auto !important;
    min-width: 0 !important;
    max-width: calc(100% - 2.35rem) !important;
  }
  [data-testid="stForm"] [data-baseweb="base-input"],
  [data-testid="stForm"] [data-baseweb="input"] {
    width: 100% !important;
    max-width: 100% !important;
  }
  [data-testid="stForm"] [data-baseweb="input"] input {
    width: 100% !important;
    color: #111827 !important;
    box-sizing: border-box !important;
    padding-right: 0.75rem !important;
  }
  /* Email has no eye button — keep the same right gutter so boxes match */
  [data-testid="stForm"] [data-testid="stTextInputRootElement"]:not(:has(button)) {
    padding-right: 2.35rem !important;
  }
  [data-testid="stForm"] [data-testid="stTextInputRootElement"]:not(:has(button)) > div {
    max-width: 100% !important;
  }
  [data-testid="stForm"] [data-testid="stTextInputRootElement"] button {
    position: static !important;
    transform: none !important;
    flex: 0 0 2.1rem !important;
    width: 2.1rem !important;
    min-width: 2.1rem !important;
    height: 2.1rem !important;
    min-height: 2.1rem !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    border-radius: 8px !important;
    background: #eef2f7 !important;
    box-shadow: none !important;
    color: #4b5563 !important;
  }

  .stCaption, [data-testid="stCaptionContainer"] p {
    color: #e8f1ff !important;
    text-align: center;
  }
</style>
"""

APP_CSS = """
<style>
  .stApp { background: #e8eef8 !important; }
  section.main { background: #e8eef8 !important; }
  .block-container {
    max-width: 920px !important;
    padding-top: 1.25rem !important;
    padding-bottom: 5.5rem !important;
  }

  section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b4f9c 0%, #1565c0 55%, #1a73c7 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.14);
  }
  section[data-testid="stSidebar"] > div {
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
  }
  section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
  section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
  section[data-testid="stSidebar"] .stCaption,
  section[data-testid="stSidebar"] label {
    color: #eef6ff !important;
  }
  section[data-testid="stSidebar"] .stButton>button {
    background: rgba(255, 255, 255, 0.12) !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    color: #ffffff !important;
    border-radius: 12px !important;
    box-shadow: none !important;
  }

  /* Account name: force blue so it is readable on the white popover chip */
  section[data-testid="stSidebar"] [data-testid="stPopover"] button,
  section[data-testid="stSidebar"] [data-testid="stPopover"] button p,
  section[data-testid="stSidebar"] [data-testid="stPopover"] button span,
  section[data-testid="stSidebar"] [data-testid="stPopover"] button div {
    color: #0b4f9c !important;
    font-weight: 700 !important;
  }
  section[data-testid="stSidebar"] [data-testid="stPopover"] > div > button,
  section[data-testid="stSidebar"] [data-testid="stPopoverButton"],
  section[data-testid="stSidebar"] button[kind="secondary"] {
    background: #ffffff !important;
    border: 1px solid #c7dbf7 !important;
    color: #0b4f9c !important;
    border-radius: 12px !important;
    box-shadow: none !important;
  }

  .side-brand {
    width: 100%;
    box-sizing: border-box;
    background: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.35);
    border-radius: 12px;
    padding: 0.45rem 0.55rem;
    margin: 0 0 0.85rem 0;
    display: flex;
    align-items: center;
    justify-content: flex-start;
  }
  .side-brand img {
    width: 100%;
    max-width: 100%;
    height: auto;
    max-height: 52px;
    object-fit: contain;
    object-position: left center;
    border-radius: 0;
    display: block;
    margin: 0;
  }
  .side-section-title {
    margin: 0.8rem 0 0.45rem;
    color: #d7ebff !important;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .side-tips {
    background: rgba(255, 255, 255, 0.10);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 12px;
    padding: 0.7rem 0.8rem;
    color: #eef6ff !important;
    font-size: 0.82rem;
    line-height: 1.45;
    margin-bottom: 1rem;
  }
  .side-user-hint {
    margin: 1.2rem 0 0.35rem;
    font-size: 0.72rem;
    color: #d0e4ff !important;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    font-weight: 600;
  }

  .hero-card {
    background: #ffffff;
    border: 1px solid #d7e3f4;
    border-radius: 16px;
    padding: 1rem 1.15rem;
    margin-bottom: 0.9rem;
    box-shadow: 0 10px 24px rgba(30, 77, 123, 0.07);
  }
  .hero-card h1 {
    margin: 0;
    font-size: 1.4rem;
    color: #0b4f9c !important;
    font-weight: 700;
  }
  .hero-card p {
    margin: 0.35rem 0 0;
    color: #5b7290 !important;
    font-size: 0.92rem;
  }
  .hero-accent {
    display: inline-block;
    margin-top: 0.7rem;
    padding: 0.28rem 0.65rem;
    border-radius: 999px;
    background: #e8f1ff;
    color: #1565c0 !important;
    font-size: 0.74rem;
    font-weight: 600;
  }
</style>
"""


def api_login(email: str, password: str) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        r = client.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
        if r.status_code != 200:
            try:
                payload = r.json()
                detail = payload.get("detail", payload)
                if isinstance(detail, list):
                    detail = "; ".join(
                        str(item.get("msg", item)) if isinstance(item, dict) else str(item) for item in detail
                    )
            except Exception:
                detail = r.text
            raise RuntimeError(detail)
        return r.json()


def api_chat(token: str, message: str, history: list[dict[str, str]]) -> dict[str, Any]:
    with httpx.Client(timeout=120.0) as client:
        r = client.post(
            f"{API_BASE}/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": message, "history": history},
        )
        if r.status_code != 200:
            detail = (
                r.json().get("detail", r.text)
                if r.headers.get("content-type", "").startswith("application/json")
                else r.text
            )
            raise RuntimeError(detail)
        return r.json()


def render_trace(trace: list[dict]) -> None:
    if not trace:
        return
    with st.expander("Agent tool trace"):
        for step in trace:
            if step.get("type") == "call":
                st.markdown(f"**Called** `{step.get('tool')}`")
                st.json(step.get("args") or {})
            else:
                st.markdown(f"**Result** `{step.get('tool')}`")
                st.code(step.get("output") or "", language="json")


def sign_out() -> None:
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.chat_log = []
    st.session_state.session_tools = []


if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []
if "session_tools" not in st.session_state:
    st.session_state.session_tools = []

st.markdown(BASE_CSS, unsafe_allow_html=True)

# ---------- LOGIN PAGE ----------
if not st.session_state.token:
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    with st.form("login_form"):
        st.markdown(
            f"""
            <div class="login-brand">
              <img src="{LOGIN_LOGO_URI}" alt="Ideas2IT logo" />
              <h1>HR Chat Agent</h1>
              <p>Sign in with your employee ID or work email to ask about leave, eligibility, holidays, and policy.</p>
              <div class="login-chip">Secure employee access</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        login = st.text_input("Email or employee ID", placeholder="E1001")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
    if submitted:
        login = (login or "").replace("＠", "@").strip()
        if not login or not password:
            st.error("Enter employee ID (for example E1001) and password.")
        else:
            try:
                data = api_login(login, password)
                st.session_state.token = data["access_token"]
                st.session_state.user = data
                st.session_state.chat_log = []
                st.session_state.session_tools = []
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
    st.caption("Use a seeded employee account from the HR database.")
    st.stop()

# ---------- APP (logged in) ----------
st.markdown(APP_CSS, unsafe_allow_html=True)
u = st.session_state.user or {}

with st.sidebar:
    st.markdown(
        f"""
        <div class="side-brand">
          <img src="{SIDE_LOGO_URI}" alt="Ideas2IT" />
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<p class="side-section-title">Try asking</p>', unsafe_allow_html=True)
    eid = u.get("employee_id")
    et = u.get("employment_type") or ""
    if et == "contractor":
        tips = "What should I know?<br/>Is Diwali a holiday?<br/>Raise an HR ticket"
    elif eid == "E1003":
        tips = "Onboarding checklist<br/>Can I take privilege leave?<br/>What should I know?"
    else:
        tips = (
            "What is my leave balance?<br/>"
            "Submit leave for 2026-11-10 to 2026-11-11 PL<br/>"
            "Is Diwali a holiday?<br/>"
            "If I take 5 PL what's left?"
        )
    st.markdown(f'<div class="side-tips">{tips}</div>', unsafe_allow_html=True)

    tools = st.session_state.get("session_tools") or []
    if tools:
        st.markdown('<p class="side-section-title">Tools this session</p>', unsafe_allow_html=True)
        st.caption(", ".join(tools[-10:]))

    st.markdown('<p class="side-user-hint">Account</p>', unsafe_allow_html=True)
    full_name = (u.get("full_name") or "User").strip()
    short_name = full_name.split()[0] if full_name else "User"
    with st.popover(short_name, use_container_width=True):
        st.markdown(f"**{full_name}**")
        st.caption(f"{u.get('employee_id', '')} · {u.get('department', '')}")
        st.caption(u.get("email", ""))
        if st.button("Sign out", key="sign_out_btn", use_container_width=True):
            sign_out()
            st.rerun()

st.markdown(
    """
    <div class="hero-card">
      <h1>HR Chat Agent</h1>
      <p>Ask about leave, eligibility, holidays, and policy. Answers use your record and Ideas2IT documents.</p>
      <span class="hero-accent">Policy-aware · Private by role</span>
    </div>
    """,
    unsafe_allow_html=True,
)

for msg in st.session_state.chat_log:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            render_trace(msg.get("trace") or [])

if not st.session_state.chat_log:
    st.info("Start a conversation below — ask about leave balance, holidays, or policy.")

prompt = st.chat_input("Ask about leave, policy, or eligibility…")
if prompt:
    st.session_state.chat_log.append({"role": "user", "content": prompt})

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.chat_log[:-1]
        if m["role"] in {"user", "assistant"}
    ]

    try:
        result = api_chat(st.session_state.token, prompt, history)
        answer = result["answer"]
        trace = result.get("tool_trace", [])
    except Exception as exc:  # noqa: BLE001
        answer = f"Sorry — the agent could not complete this request.\n\n`{exc}`"
        trace = []

    called = [step.get("tool") for step in (trace or []) if step.get("type") == "call" and step.get("tool")]
    if called:
        st.session_state.session_tools = (st.session_state.session_tools or []) + called

    st.session_state.chat_log.append({"role": "assistant", "content": answer, "trace": trace})
    st.rerun()
