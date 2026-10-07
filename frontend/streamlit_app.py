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
    background: #eef2f7 !important;
    color: #1f2937;
  }
  .stApp p, .stApp span, .stApp label, .stApp li { color: #334155 !important; }

  [data-testid="stChatMessage"] {
    background: #ffffff !important;
    color: #1f2937 !important;
    border: 1px solid #e5eaf1;
    border-radius: 16px;
    padding: 0.75rem 0.9rem;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    margin-bottom: 0.55rem;
  }
  [data-testid="stChatMessage"] p,
  [data-testid="stChatMessage"] span,
  [data-testid="stChatMessage"] li {
    color: #1f2937 !important;
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
  .stButton>button:hover {
    filter: brightness(1.05);
  }

  .stTextInput input, .stTextInput input:focus {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #d7dee8 !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  }

  [data-testid="stChatInput"] textarea {
    border-radius: 14px !important;
    border: 1px solid #d7dee8 !important;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
  }
</style>
"""

LOGIN_CSS = """
<style>
  [data-testid="stSidebar"] { display: none !important; }
  section.main > div { padding-top: 0 !important; }
  .block-container {
    max-width: 1040px;
    padding-top: 2.4rem;
    padding-bottom: 2rem;
  }
  .stApp {
    background:
      radial-gradient(circle at top left, rgba(59,130,246,0.12), transparent 34%),
      linear-gradient(160deg, #eef2f7 0%, #f8fafc 55%, #e8eef7 100%) !important;
  }

  .login-brand {
    border-radius: 22px;
    box-shadow: 0 22px 50px rgba(15, 23, 42, 0.14);
    min-height: 460px;
    background: radial-gradient(circle at top left, #1e3a5f 0%, #0b1220 55%, #05080f 100%);
    color: #fff;
    padding: 2.4rem 2rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
    border: 1px solid rgba(255,255,255,0.08);
  }
  .login-brand img {
    width: min(100%, 320px);
    margin-bottom: 1.4rem;
  }
  .login-brand h1 {
    margin: 0;
    font-size: 1.85rem;
    color: #ffffff !important;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .login-brand p {
    margin: 0.7rem 0 0;
    color: #cbd5e1 !important;
    font-size: 1rem;
    line-height: 1.55;
  }
  .login-chip {
    display: inline-block;
    margin-top: 1.25rem;
    padding: 0.35rem 0.8rem;
    border-radius: 999px;
    background: rgba(59, 130, 246, 0.18);
    border: 1px solid rgba(96, 165, 250, 0.35);
    color: #bfdbfe !important;
    font-size: 0.78rem;
    font-weight: 600;
  }
  .login-title h2 {
    margin: 0 0 0.35rem;
    color: #0f172a !important;
    font-size: 1.35rem;
    font-weight: 700;
  }
  .login-title p {
    margin: 0 0 0.85rem;
    color: #64748b !important;
    font-size: 0.92rem;
  }
  [data-testid="stForm"] {
    background: #ffffff;
    border: 1px solid #e5eaf1;
    border-radius: 22px;
    padding: 1.4rem 1.25rem 1.1rem;
    box-shadow: 0 22px 50px rgba(15, 23, 42, 0.14);
  }
</style>
"""

APP_CSS = """
<style>
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b1b33 0%, #0f2748 45%, #122c52 100%) !important;
    border-right: 1px solid rgba(148, 163, 184, 0.18);
    box-shadow: 8px 0 28px rgba(15, 23, 42, 0.18);
  }
  [data-testid="stSidebar"] > div:first-child {
    padding-top: 1.1rem;
  }
  [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
  [data-testid="stSidebar"] .stCaption,
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] small {
    color: #94a3b8 !important;
  }
  [data-testid="stSidebar"] hr {
    border-color: rgba(148, 163, 184, 0.22) !important;
  }
  [data-testid="stSidebar"] .stButton>button {
    background: transparent !important;
    border: 1px solid rgba(148, 163, 184, 0.22) !important;
    color: #e2e8f0 !important;
    border-radius: 12px !important;
    box-shadow: none !important;
    justify-content: flex-start;
    font-weight: 500 !important;
  }
  [data-testid="stSidebar"] .stButton>button:hover {
    background: rgba(59, 130, 246, 0.18) !important;
    border-color: rgba(59, 130, 246, 0.45) !important;
  }
  [data-testid="stSidebar"] .stButton>button[kind="primary"],
  [data-testid="stSidebar"] .stButton>button[data-testid="baseButton-primary"] {
    background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%) !important;
    border: 0 !important;
    color: #ffffff !important;
    box-shadow: 0 10px 22px rgba(37, 99, 235, 0.35) !important;
  }

  .block-container {
    padding-top: 1.35rem;
    max-width: 980px;
  }

  .side-brand {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
    margin-bottom: 1.1rem;
    padding: 0.2rem 0.15rem 0.85rem;
    border-bottom: 1px solid rgba(148, 163, 184, 0.18);
  }
  .side-brand img {
    width: 100%;
    max-width: 210px;
    border-radius: 10px;
  }
  .side-brand h2 {
    margin: 0;
    font-size: 1.05rem;
    color: #ffffff !important;
    font-weight: 700;
  }
  .side-brand p {
    margin: 0;
    font-size: 0.78rem;
    color: #93c5fd !important;
    letter-spacing: 0.02em;
  }

  .user-card {
    background: rgba(15, 23, 42, 0.35);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 14px;
    padding: 0.85rem 0.9rem;
    margin: 0.75rem 0 1rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
  }
  .user-card .name {
    margin: 0;
    color: #ffffff !important;
    font-weight: 600;
    font-size: 0.95rem;
  }
  .user-card .meta {
    margin: 0.25rem 0 0;
    color: #94a3b8 !important;
    font-size: 0.78rem;
  }

  .side-section-title {
    margin: 0.35rem 0 0.55rem;
    color: #94a3b8 !important;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .side-tips {
    background: rgba(15, 23, 42, 0.28);
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 14px;
    padding: 0.75rem 0.85rem;
    margin-bottom: 0.8rem;
  }
  .side-tips li { color: #cbd5e1 !important; font-size: 0.84rem; margin-bottom: 0.25rem; }

  .hero-card {
    background: #ffffff;
    border: 1px solid #e5eaf1;
    border-radius: 18px;
    padding: 1.2rem 1.35rem;
    margin-bottom: 1rem;
    box-shadow: 0 14px 34px rgba(15, 23, 42, 0.07);
  }
  .hero-card h1 {
    margin: 0;
    font-size: 1.55rem;
    color: #0f172a !important;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .hero-card p {
    margin: 0.4rem 0 0;
    color: #64748b !important;
    font-size: 0.95rem;
  }
  .hero-accent {
    display: inline-block;
    margin-top: 0.85rem;
    padding: 0.3rem 0.7rem;
    border-radius: 999px;
    background: #eff6ff;
    color: #1d4ed8 !important;
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
    left, right = st.columns([1.05, 0.95], gap="large")
    with left:
        st.markdown(
            f"""
            <div class="login-brand">
              <img src="{LOGO_URI}" alt="Ideas2IT logo" />
              <h1>HR Chat Agent</h1>
              <p>Sign in with your employee ID or work email to ask about leave, eligibility, holidays, and policy.</p>
              <div class="login-chip">Secure employee access</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        with st.form("login_form"):
            st.markdown(
                """
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
          <div>
            <h2>Ideas2IT</h2>
            <p>HR Chat Agent</p>
          </div>
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

    st.markdown(
        f"""
        <div class="user-card">
          <p class="name">{u.get('full_name', '')}</p>
          <p class="meta">{u.get('employee_id', '')} · {u.get('department', '')}</p>
          <p class="meta">{u.get('email', '')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<p class="side-section-title">Try asking</p>', unsafe_allow_html=True)
    eid = u.get("employee_id")
    et = u.get("employment_type") or ""
    if et == "contractor":
        tips = "- What should I know?\n- Is Diwali a holiday?\n- Raise an HR ticket"
    elif eid == "E1003":
        tips = "- Onboarding checklist\n- Can I take privilege leave?\n- What should I know?"
    else:
        tips = (
            "- What is my leave balance?\n"
            "- Submit leave for 2026-11-10 to 2026-11-11 PL\n"
            "- Is Diwali a holiday?\n"
            "- If I take 5 PL what's left?"
        )
    st.markdown(f'<div class="side-tips">{tips.replace(chr(10), "<br/>")}</div>', unsafe_allow_html=True)

    tools = st.session_state.get("session_tools") or []
    if tools:
        st.markdown('<p class="side-section-title">Tools this session</p>', unsafe_allow_html=True)
        st.caption(", ".join(tools[-10:]))

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
