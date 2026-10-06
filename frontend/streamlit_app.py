"""Streamlit chat UI for the 12I Corp HR Chat Agent."""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="12I Corp | HR Assistant",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');

      html, body, [class*="css"] {
        font-family: Outfit, system-ui, sans-serif;
      }
      .stApp {
        background:
          radial-gradient(1200px 600px at -10% -10%, #2b4cff33 0%, transparent 55%),
          radial-gradient(900px 500px at 110% 0%, #ff7a3d22 0%, transparent 50%),
          linear-gradient(180deg, #070b16 0%, #10182c 48%, #0b1020 100%);
        color: #eef2ff;
      }
      .block-container { padding-top: 1.1rem; max-width: 1180px; }
      [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1428 0%, #111c36 100%);
        border-right: 1px solid #2a3a68;
      }
      [data-testid="stSidebar"] * { color: #e8edff; }
      .hero {
        position: relative;
        overflow: hidden;
        background: linear-gradient(120deg, #121c3a 0%, #1b2b5c 42%, #c45c26 160%);
        border: 1px solid #3d4f88;
        color: #f7f3ee;
        padding: 1.55rem 1.7rem 1.45rem;
        border-radius: 22px;
        margin-bottom: 1.1rem;
        box-shadow: 0 18px 50px rgba(8, 12, 28, 0.45);
      }
      .hero::after {
        content: "";
        position: absolute;
        width: 240px; height: 240px;
        right: -40px; top: -70px;
        background: radial-gradient(circle, #ffd29a55, transparent 68%);
        pointer-events: none;
      }
      .eyebrow {
        letter-spacing: 0.18em;
        font-size: 0.72rem;
        text-transform: uppercase;
        color: #ffd7a8;
        margin: 0 0 0.35rem;
        font-weight: 600;
      }
      .hero h1 {
        margin: 0;
        font-family: Fraunces, Georgia, serif;
        font-size: 2.05rem;
        line-height: 1.15;
      }
      .hero p { margin: 0.45rem 0 0; opacity: 0.9; font-size: 1.02rem; }
      .chip-row { display: flex; gap: 0.45rem; flex-wrap: wrap; margin-top: 0.85rem; }
      .chip {
        font-size: 0.78rem;
        padding: 0.28rem 0.65rem;
        border-radius: 999px;
        background: #ffffff14;
        border: 1px solid #ffffff22;
      }
      .stChatMessage { background: transparent; }
      [data-testid="stChatMessage"] {
        background: #162242cc;
        border: 1px solid #334675;
        border-radius: 16px;
        padding: 0.35rem 0.4rem;
        margin-bottom: 0.55rem;
      }
      .stButton>button {
        background: linear-gradient(90deg, #3b6dff, #6a4dff);
        color: white;
        border: 0;
        border-radius: 12px;
        font-weight: 600;
      }
      .stTextInput input {
        background: #0c1428 !important;
        color: #f4f7ff !important;
        border-radius: 12px !important;
      }
      h1, h2, h3 { font-family: Fraunces, Georgia, serif; }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_login(email: str, password: str) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        r = client.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
        if r.status_code != 200:
            raise RuntimeError(r.json().get("detail", r.text))
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


if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

st.markdown(
    """
    <div class="hero">
      <p class="eyebrow">12I Corp People Experience</p>
      <h1>HR Chat Agent</h1>
      <p>Ask about leave, eligibility, and policy — grounded in your record and company documents.</p>
      <div class="chip-row">
        <span class="chip">Secure sign-in</span>
        <span class="chip">Policy-aware</span>
        <span class="chip">Live leave tools</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Sign in")
    st.caption("Use your 12I Corp work email.")
    if st.session_state.token:
        u = st.session_state.user
        st.markdown(f"**{u['full_name']}**")
        st.write(f"{u['employee_id']} · {u['department']}")
        st.write(u["email"])
        if st.button("Sign out", use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.chat_log = []
            st.rerun()
    else:
        email = st.text_input("Work email", placeholder="you@12icorp.example")
        password = st.text_input("Password", type="password")
        if st.button("Continue", type="primary", use_container_width=True):
            try:
                data = api_login(email.strip(), password)
                st.session_state.token = data["access_token"]
                st.session_state.user = data
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    st.divider()
    st.markdown("### You can ask")
    st.markdown(
        "- What is my leave balance?\n"
        "- I took 2 days this month — can I take one more sick leave?\n"
        "- Am I eligible for privilege leave?\n"
        "- How many days from 2026-10-20 to 2026-10-24?\n"
        "- What is the maternity leave policy?"
    )

if not st.session_state.token:
    st.markdown("#### Welcome")
    st.write("Sign in on the left to start a private HR conversation. Answers use your employee record and 12I Corp policies.")
    st.stop()

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

    st.session_state.chat_log.append({"role": "assistant", "content": answer, "trace": trace})
