"""Streamlit chat UI for the I2I Corp HR Chat Agent."""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="I2I Corp | HR Assistant",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      /* Hide Streamlit chrome that shows as a blank white bar over the title */
      header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0 !important;
      }
      header[data-testid="stHeader"] * { display: none !important; }
      [data-testid="stToolbar"],
      [data-testid="stDecoration"],
      [data-testid="stStatusWidget"],
      .stDeployButton,
      #MainMenu,
      footer { display: none !important; visibility: hidden !important; }

      .stApp, .stApp p, .stApp span, .stApp label, .stApp li {
        color: #1a1a1a !important;
      }
      .stApp { background: #f4f6f8; }
      .block-container { padding-top: 1.25rem; max-width: 920px; }

      [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e2e6ea;
      }
      [data-testid="stSidebar"] * { color: #1a1a1a !important; }

      .hero {
        background: #1e4d7b;
        color: #ffffff;
        padding: 1.15rem 1.35rem;
        border-radius: 12px;
        margin-bottom: 1rem;
      }
      .hero .eyebrow {
        margin: 0 0 0.25rem;
        font-size: 0.75rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        opacity: 0.9;
      }
      .hero h1 {
        margin: 0;
        font-size: 1.55rem;
        font-weight: 650;
        color: #ffffff !important;
      }
      .hero p {
        margin: 0.35rem 0 0;
        color: #eef4fa !important;
        font-size: 0.95rem;
      }

      [data-testid="stChatMessage"] {
        background: #ffffff !important;
        color: #1a1a1a !important;
        border: 1px solid #e5e8eb;
        border-radius: 10px;
        padding: 0.55rem 0.7rem;
      }
      [data-testid="stChatMessage"] p,
      [data-testid="stChatMessage"] li,
      [data-testid="stChatMessage"] span {
        color: #1a1a1a !important;
      }
      [data-testid="stChatMessage"] code {
        background: #f0f2f4 !important;
        color: #111 !important;
      }

      .stButton>button {
        background: #1e4d7b;
        color: #ffffff !important;
        border: 0;
        border-radius: 8px;
      }
      .stTextInput input {
        background: #ffffff !important;
        color: #1a1a1a !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


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


if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

st.markdown(
    """
    <div class="hero">
      <p class="eyebrow">I2I Corp People Experience</p>
      <h1>HR Chat Agent</h1>
      <p>Ask about leave, eligibility, and policy. Answers use your record and company documents.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Sign in")
    st.caption("Work email or employee ID. Password is the seeded account password.")
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
        email = st.text_input("Email or employee ID", key="login_id", placeholder="E1001")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Continue", type="primary", use_container_width=True):
            try:
                data = api_login(email.replace("＠", "@").strip(), password)
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
    st.write("Sign in on the left to start a private HR conversation.")
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
