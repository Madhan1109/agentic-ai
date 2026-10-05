"""Streamlit chat UI for the HR Chat Agent demo."""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Acme Corp HR Chat Agent",
    page_icon="💬",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.5rem; max-width: 1100px; }
      .hero {
        background: linear-gradient(135deg, #0f3d3e 0%, #1a5f62 45%, #c45c26 100%);
        color: #f7f3ee; padding: 1.4rem 1.6rem; border-radius: 18px; margin-bottom: 1rem;
      }
      .hero h1 { margin: 0; font-family: Georgia, serif; font-size: 1.8rem; }
      .hero p { margin: 0.35rem 0 0; opacity: 0.92; }
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
    with st.expander("Agent tool trace (reasoning / tool usage)"):
        for step in trace:
            if step.get("type") == "call":
                st.markdown(f"**→ Called** `{step.get('tool')}`")
                st.json(step.get("args") or {})
            else:
                st.markdown(f"**← Result** `{step.get('tool')}`")
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
      <h1>Acme Corp · HR Chat Agent</h1>
      <p>Authenticated employees · Policy-aware answers · Live leave tools</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Employee login")
    st.caption(f"API: `{API_BASE}`")
    if st.session_state.token:
        u = st.session_state.user
        st.success(f"Signed in as **{u['full_name']}**")
        st.write(f"{u['employee_id']} · {u['department']}")
        st.write(u["email"])
        if st.button("Sign out", use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.chat_log = []
            st.rerun()
    else:
        email = st.text_input("Work email", value="alice.nguyen@acmecorp.example")
        password = st.text_input("Password", type="password", value="Password@123")
        if st.button("Sign in", type="primary", use_container_width=True):
            try:
                data = api_login(email, password)
                st.session_state.token = data["access_token"]
                st.session_state.user = data
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    st.divider()
    st.markdown("**Demo accounts** (password `Password@123`)")
    st.code(
        "alice.nguyen@acmecorp.example  (full-time)\n"
        "cara.lee@acmecorp.example      (probation)\n"
        "devon.contractor@acmecorp.example (contractor)",
        language=None,
    )
    st.markdown("**Try asking**")
    st.markdown(
        "- What is my leave balance?\n"
        "- Am I eligible for privilege leave?\n"
        "- How many leave days for 2026-10-20 to 2026-10-24?\n"
        "- What is the maternity leave policy?\n"
        "- What is our hybrid work policy?"
    )

if not st.session_state.token:
    st.info("Sign in with a demo employee account to chat with the HR agent.")
    st.stop()

for msg in st.session_state.chat_log:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            render_trace(msg.get("trace") or [])

prompt = st.chat_input("Ask an HR question…")
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
        with st.spinner("Agent reasoning and using tools…"):
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
