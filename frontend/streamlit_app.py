"""Streamlit chat UI for the I2I Corp HR Chat Agent."""

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
LOGO_PATH = ASSETS / "i2i-logo.svg"


def _logo_data_uri() -> str:
    if LOGO_PATH.exists():
        raw = LOGO_PATH.read_bytes()
        return "data:image/svg+xml;base64," + base64.b64encode(raw).decode("ascii")
    return ""


LOGO_URI = _logo_data_uri()

st.set_page_config(
    page_title="I2I Corp | HR Assistant",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_CSS = """
<style>
  header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; }
  header[data-testid="stHeader"] * { display: none !important; }
  [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
  .stDeployButton, #MainMenu, footer { display: none !important; visibility: hidden !important; }

  .stApp { background: #f4f6f8; color: #1a1a1a; }
  .stApp p, .stApp span, .stApp label, .stApp li { color: #1a1a1a !important; }

  [data-testid="stChatMessage"] {
    background: #ffffff !important;
    color: #1a1a1a !important;
    border: 1px solid #e5e8eb;
    border-radius: 10px;
    padding: 0.55rem 0.7rem;
  }
  .stButton>button {
    background: #1e4d7b;
    color: #ffffff !important;
    border: 0;
    border-radius: 10px;
    font-weight: 600;
  }
  .stTextInput input, .stTextInput input:focus {
    background: #ffffff !important;
    color: #1a1a1a !important;
    border-radius: 10px !important;
  }
</style>
"""

LOGIN_CSS = """
<style>
  [data-testid="stSidebar"] { display: none !important; }
  .block-container { max-width: 520px; padding-top: 3.5rem; }
  .login-shell {
    background: linear-gradient(160deg, #eef3f8 0%, #f7f9fb 45%, #ffffff 100%);
    border: 1px solid #d9e2ec;
    border-radius: 22px;
    padding: 2rem 1.75rem 1.5rem;
    box-shadow: 0 18px 40px rgba(30, 77, 123, 0.08);
    text-align: center;
  }
  .login-shell img { width: 84px; height: 84px; margin-bottom: 0.85rem; }
  .login-shell h1 {
    margin: 0;
    font-size: 1.7rem;
    color: #14395c !important;
  }
  .login-shell p {
    margin: 0.45rem 0 0;
    color: #4b5b6b !important;
    font-size: 0.98rem;
  }
  .login-badge {
    display: inline-block;
    margin-top: 0.9rem;
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    background: #e8f0f8;
    color: #1e4d7b !important;
    font-size: 0.78rem;
    font-weight: 600;
  }
</style>
"""

APP_CSS = """
<style>
  [data-testid="stSidebar"] {
    background: #0f2f4d;
    border-right: 1px solid #1a456b;
  }
  [data-testid="stSidebar"] * { color: #f4f8fc !important; }
  [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] p {
    color: #d5e4f2 !important;
  }
  [data-testid="stSidebar"] .stButton>button {
    background: #2f6fad;
    border: 1px solid #4a88c4;
  }
  .block-container { padding-top: 1.1rem; max-width: 920px; }
  .brand-row {
    display: flex; align-items: center; gap: 0.7rem; margin-bottom: 0.8rem;
  }
  .brand-row img { width: 42px; height: 42px; border-radius: 10px; }
  .brand-row h2 { margin: 0; font-size: 1.15rem; color: #ffffff !important; }
  .brand-row p { margin: 0; font-size: 0.8rem; color: #c9daf0 !important; }
  .hero {
    background: #1e4d7b;
    color: #ffffff;
    padding: 1.05rem 1.25rem;
    border-radius: 12px;
    margin-bottom: 1rem;
  }
  .hero h1 { margin: 0; font-size: 1.45rem; color: #ffffff !important; }
  .hero p { margin: 0.35rem 0 0; color: #e8f1fa !important; }
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
    st.markdown(
        f"""
        <div class="login-shell">
          <img src="{LOGO_URI}" alt="I2I Corp logo" />
          <h1>I2I Corp</h1>
          <p>HR Chat Agent — sign in with your employee ID or work email</p>
          <div class="login-badge">Secure employee access</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    with st.form("login_form"):
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
        <div class="brand-row">
          <img src="{LOGO_URI}" alt="I2I" />
          <div>
            <h2>I2I Corp</h2>
            <p>HR Chat Agent</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"**{u.get('full_name', '')}**")
    st.caption(f"{u.get('employee_id', '')} · {u.get('department', '')}")
    st.caption(u.get("email", ""))

    if st.button("New chat", key="new_chat_btn", use_container_width=True):
        new_chat()
        st.rerun()
    if st.button("Sign out", key="sign_out_btn", use_container_width=True):
        sign_out()
        st.rerun()

    st.divider()
    st.markdown("### Try asking")
    eid = u.get("employee_id")
    et = u.get("employment_type") or ""
    if et == "contractor":
        st.markdown("- What should I know?\n- Is Diwali a holiday?\n- Raise an HR ticket")
    elif eid == "E1003":
        st.markdown("- Onboarding checklist\n- Can I take privilege leave?\n- What should I know?")
    else:
        st.markdown(
            "- What is my leave balance?\n"
            "- Submit leave for 2026-11-10 to 2026-11-11 PL\n"
            "- Is Diwali a holiday?\n"
            "- If I take 5 PL what's left?"
        )

    tools = st.session_state.get("session_tools") or []
    if tools:
        st.divider()
        st.markdown("### Tools this session")
        st.write(", ".join(tools[-10:]))

st.markdown(
    """
    <div class="hero">
      <h1>HR Chat Agent</h1>
      <p>Ask about leave, eligibility, holidays, and policy. Answers use your record and I2I documents.</p>
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
