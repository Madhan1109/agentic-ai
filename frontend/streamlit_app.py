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
LOGO_PATH = ASSETS / "ideas2it-logo.png"


def _logo_data_uri() -> str:
    if LOGO_PATH.exists():
        raw = LOGO_PATH.read_bytes()
        return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
    return ""


LOGO_URI = _logo_data_uri()

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

  header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; }
  header[data-testid="stHeader"] * { display: none !important; }
  [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
  .stDeployButton, #MainMenu, footer { display: none !important; visibility: hidden !important; }

  .stApp {
    background: #e8eef8 !important;
    color: #1e3a5f;
  }
  .stApp p, .stApp span, .stApp label, .stApp li { color: #334155 !important; }

  [data-testid="stChatMessage"] {
    background: #ffffff !important;
    color: #1e3a5f !important;
    border: 1px solid #d7e3f4;
    border-radius: 16px;
    padding: 0.85rem 1rem;
    box-shadow: 0 10px 28px rgba(30, 77, 123, 0.08);
    margin-bottom: 0.65rem;
  }
  [data-testid="stChatMessage"] p,
  [data-testid="stChatMessage"] span,
  [data-testid="stChatMessage"] li {
    color: #1e3a5f !important;
  }

  .stButton>button {
    background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%) !important;
    color: #ffffff !important;
    border: 0 !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    box-shadow: 0 8px 18px rgba(37, 99, 235, 0.28);
    min-height: 2.6rem;
  }
  .stButton>button:hover { filter: brightness(1.05); }

  .stTextInput input, .stTextInput input:focus {
    background: #ffffff !important;
    color: #1e3a5f !important;
    border: 1px solid #c5d4ea !important;
    border-radius: 12px !important;
  }

  [data-testid="stChatInput"] {
    background: transparent !important;
  }
  [data-testid="stChatInput"] textarea {
    border-radius: 16px !important;
    border: 1px solid #c5d4ea !important;
    box-shadow: 0 10px 24px rgba(30, 77, 123, 0.08);
    background: #ffffff !important;
  }
</style>
"""

LOGIN_CSS = """
<style>
  [data-testid="stSidebar"] { display: none !important; }

  html, body, .stApp {
    height: 100vh !important;
    min-height: 100vh !important;
    overflow: hidden !important;
  }
  .stApp {
    background: linear-gradient(145deg, #0b4f9c 0%, #1565c0 42%, #1e88e5 100%) !important;
  }
  [data-testid="stAppViewContainer"],
  [data-testid="stAppViewContainer"] > .main,
  section.main {
    height: 100vh !important;
    min-height: 100vh !important;
    background: transparent !important;
  }
  section.main > div {
    height: 100vh !important;
    padding-top: 0 !important;
  }
  .block-container {
    max-width: 520px !important;
    min-height: 100vh !important;
    height: 100vh !important;
    padding: 0 1.25rem !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
  }
  [data-testid="stForm"] {
    background: rgba(255, 255, 255, 0.14) !important;
    border: 1px solid rgba(255, 255, 255, 0.30) !important;
    border-radius: 28px !important;
    padding: 1.6rem 1.45rem 1.25rem !important;
    box-shadow: 0 28px 60px rgba(11, 79, 156, 0.35) !important;
    backdrop-filter: blur(10px);
  }
  .login-brand {
    text-align: center;
    margin-bottom: 0.35rem;
  }
  .login-brand img {
    width: min(100%, 280px);
    border-radius: 18px;
    margin: 0 auto 1rem;
    display: block;
    box-shadow: 0 12px 28px rgba(11, 79, 156, 0.25);
  }
  .login-brand h1 {
    margin: 0;
    font-size: 1.75rem;
    color: #ffffff !important;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .login-brand p {
    margin: 0.55rem auto 0;
    max-width: 360px;
    color: #e3f2fd !important;
    font-size: 0.95rem;
    line-height: 1.5;
  }
  .login-chip {
    display: inline-block;
    margin-top: 0.9rem;
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.18);
    border: 1px solid rgba(255, 255, 255, 0.35);
    color: #ffffff !important;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .login-title h2 {
    margin: 0.9rem 0 0.25rem;
    color: #ffffff !important;
    font-size: 1.2rem;
    font-weight: 700;
    text-align: center;
  }
  .login-title p {
    margin: 0 0 0.85rem;
    color: #e3f2fd !important;
    font-size: 0.9rem;
    text-align: center;
  }
  [data-testid="stForm"] label,
  [data-testid="stForm"] p,
  [data-testid="stForm"] span {
    color: #e8f3ff !important;
  }
  [data-testid="stForm"] .stTextInput input {
    background: #ffffff !important;
    color: #1e3a5f !important;
    border: 1px solid #b7d0ef !important;
  }
  .stCaption, [data-testid="stCaptionContainer"] {
    color: #dbeafe !important;
    text-align: center;
  }
</style>
"""

APP_CSS = """
<style>
  html, body, .stApp {
    min-height: 100vh !important;
  }
  .stApp {
    background: #e8eef8 !important;
  }
  [data-testid="stAppViewContainer"],
  [data-testid="stAppViewContainer"] > .main,
  section.main {
    min-height: 100vh !important;
    background: #e8eef8 !important;
  }
  section.main > div {
    min-height: 100vh !important;
    padding-top: 0 !important;
  }
  .block-container {
    max-width: 1100px !important;
    min-height: calc(100vh - 1rem) !important;
    padding-top: 1.25rem !important;
    padding-bottom: 6.5rem !important;
  }

  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b4f9c 0%, #1565c0 55%, #1a73c7 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.14);
    box-shadow: 8px 0 28px rgba(11, 79, 156, 0.22);
  }
  [data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem;
    min-height: 100vh;
  }
  [data-testid="stSidebar"] * { color: #eef6ff !important; }
  [data-testid="stSidebar"] .stCaption,
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] small {
    color: #d0e4ff !important;
  }
  [data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, 0.18) !important;
  }
  [data-testid="stSidebar"] .stButton>button {
    background: rgba(255, 255, 255, 0.10) !important;
    border: 1px solid rgba(255, 255, 255, 0.22) !important;
    color: #ffffff !important;
    border-radius: 12px !important;
    box-shadow: none !important;
    font-weight: 500 !important;
  }
  [data-testid="stSidebar"] .stButton>button:hover {
    background: rgba(255, 255, 255, 0.18) !important;
  }
  [data-testid="stSidebar"] .stButton>button[kind="primary"],
  [data-testid="stSidebar"] .stButton>button[data-testid="baseButton-primary"] {
    background: linear-gradient(180deg, #60a5fa 0%, #3b82f6 100%) !important;
    border: 0 !important;
    color: #ffffff !important;
    box-shadow: 0 10px 22px rgba(37, 99, 235, 0.35) !important;
  }

  .side-brand {
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 18px;
    padding: 0.9rem 0.85rem 1rem;
    margin-bottom: 0.95rem;
    box-shadow: 0 10px 24px rgba(11, 79, 156, 0.18);
  }
  .side-brand img {
    width: 100%;
    max-width: 220px;
    border-radius: 12px;
    display: block;
    margin: 0 auto 0.7rem;
  }
  .side-brand h2 {
    margin: 0;
    font-size: 1.05rem;
    color: #ffffff !important;
    font-weight: 700;
    text-align: center;
  }
  .side-brand .tag {
    margin: 0.2rem 0 0.75rem;
    font-size: 0.78rem;
    color: #d7ebff !important;
    text-align: center;
  }
  .side-brand .user-name {
    margin: 0;
    color: #ffffff !important;
    font-weight: 600;
    font-size: 0.95rem;
    text-align: center;
  }
  .side-brand .user-meta {
    margin: 0.2rem 0 0;
    color: #d0e4ff !important;
    font-size: 0.76rem;
    text-align: center;
  }

  .side-section-title {
    margin: 0.85rem 0 0.5rem;
    color: #d7ebff !important;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .side-tips {
    background: rgba(255, 255, 255, 0.10);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 14px;
    padding: 0.75rem 0.85rem;
    margin-bottom: 0.8rem;
    color: #eef6ff !important;
    font-size: 0.84rem;
    line-height: 1.45;
  }

  .chat-shell {
    background: #ffffff;
    border: 1px solid #d7e3f4;
    border-radius: 22px;
    padding: 1.25rem 1.35rem 1.1rem;
    min-height: calc(100vh - 7.5rem);
    box-shadow: 0 16px 40px rgba(30, 77, 123, 0.08);
  }
  .chat-shell h1 {
    margin: 0;
    font-size: 1.55rem;
    color: #0b4f9c !important;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .chat-shell .subtitle {
    margin: 0.4rem 0 0;
    color: #5b7290 !important;
    font-size: 0.95rem;
  }
  .chat-shell .hero-accent {
    display: inline-block;
    margin-top: 0.8rem;
    margin-bottom: 0.85rem;
    padding: 0.3rem 0.7rem;
    border-radius: 999px;
    background: #e8f1ff;
    color: #1565c0 !important;
    font-size: 0.75rem;
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


def new_chat() -> None:
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
              <img src="{LOGO_URI}" alt="Ideas2IT logo" />
              <h1>HR Chat Agent</h1>
              <p>Sign in with your employee ID or work email to ask about leave, eligibility, holidays, and policy.</p>
              <div class="login-chip">Secure employee access</div>
            </div>
            <div class="login-title">
              <h2>Welcome back</h2>
              <p>Enter your credentials to continue.</p>
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
          <img src="{LOGO_URI}" alt="Ideas2IT" />
          <h2>Ideas2IT</h2>
          <p class="tag">HR Chat Agent</p>
          <p class="user-name">{u.get('full_name', '')}</p>
          <p class="user-meta">{u.get('employee_id', '')} · {u.get('department', '')}</p>
          <p class="user-meta">{u.get('email', '')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("New chat", key="new_chat_btn", type="primary", use_container_width=True):
        new_chat()
        st.rerun()
    if st.button("Sign out", key="sign_out_btn", use_container_width=True):
        sign_out()
        st.rerun()

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

st.markdown('<div class="chat-shell">', unsafe_allow_html=True)
st.markdown(
    """
    <h1>HR Chat Agent</h1>
    <p class="subtitle">Ask about leave, eligibility, holidays, and policy. Answers use your record and Ideas2IT documents.</p>
    <span class="hero-accent">Policy-aware · Private by role</span>
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

st.markdown("</div>", unsafe_allow_html=True)

prompt = st.chat_input("Ask about leave, policy, or eligibility…")
if prompt:
    st.session_state.chat_log.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.chat_log[:-1]
        if m["role"] in {"user", "assistant"}
    ]

    with st.chat_message("assistant"):
        with st.spinner("Looking up your record and policies…"):
            try:
                result = api_chat(st.session_state.token, prompt, history)
                answer = result["answer"]
                trace = result.get("tool_trace", [])
            except Exception as exc:  # noqa: BLE001
                answer = f"Sorry — the agent could not complete this request.\n\n`{exc}`"
                trace = []
        st.markdown(answer)
        render_trace(trace)

    called = [step.get("tool") for step in (trace or []) if step.get("type") == "call" and step.get("tool")]
    if called:
        st.session_state.session_tools = (st.session_state.session_tools or []) + called

    st.session_state.chat_log.append({"role": "assistant", "content": answer, "trace": trace})
    st.rerun()
