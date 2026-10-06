# Architecture — I2I Corp HR Chat Agent

## Overview

This project demonstrates an **Agentic AI** HR assistant that:

1. Authenticates employees (JWT)
2. Retrieves answers from **HR policy documents** (RAG / retrieval tool)
3. Calls **tools / database integrations** for dynamic personal data (leave balances, eligibility, calculations)
4. Uses a **LangGraph** ReAct-style loop for reasoning → tool calls → response generation

```
┌─────────────┐     JWT login      ┌──────────────────┐
│ Streamlit   │ ─────────────────► │ FastAPI Backend  │
│ Chat UI     │ ◄──── Bearer ───── │ /auth /chat /me  │
└─────────────┘                    └────────┬─────────┘
                                            │
                                   ┌────────▼─────────┐
                                   │ LangGraph Agent  │
                                   │ (ReAct + tools)  │
                                   └────────┬─────────┘
                      ┌─────────────────────┼─────────────────────┐
                      ▼                     ▼                     ▼
               Policy Retriever       SQLite HR DB          Groq / Ollama / local
               (BM25 over MD)         employees/leave       (free LLM options)
```

## Framework choices

| Layer | Choice | Why |
|-------|--------|-----|
| Agentic framework | **LangGraph** | Explicit agent ↔ tool loop, inspectable traces, production-friendly state machine |
| LLM | **Groq llama-3.3 (free)** or **Ollama** or local tools | No paid OpenAI required; Groq has a free API key
| API | **FastAPI** | Auth, clear contracts, easy to demo and extend |
| UI | **Streamlit** | Fast interactive demo with visible tool traces |
| Knowledge | Markdown policies + **BM25 retrieval** | Transparent, no embedding infra required for assessment |
| System of record | **SQLite** | Portable demo DB for leave balances and requests |
| Auth | **JWT + bcrypt** | Authenticated employee context bound into tools |

## Agent workflow

1. Employee signs in → JWT issued with `employee_id`
2. Chat request attaches Bearer token
3. API sets **request-scoped employee context** for tools (privacy boundary)
4. LangGraph agent:
   - Reads system prompt + conversation history
   - Decides whether to call tools (`search_hr_policies`, `get_leave_balance`, etc.)
   - Executes tools via `ToolNode`
   - Loops until a final natural-language answer is produced
5. API returns `answer` + `tool_trace` for demo transparency

## Tools

| Tool | Purpose |
|------|---------|
| `search_hr_policies` | Retrieve relevant HR policy excerpts |
| `get_employee_profile` | Profile / tenure / employment type |
| `get_leave_balance` | PL / SL / CL balances from DB |
| `check_leave_eligibility` | Policy + tenure + employment-type rules |
| `calculate_leave_days` | Working-day calculation vs available balance |
| `get_recent_leave_requests` | Pending/historical leave requests |

## Context handling

- **Auth context**: tools only see the authenticated `employee_id` (cannot query other employees).
- **Conversation context**: last 12 turns sent to the agent for follow-ups (“what about sick leave?”).
- **Policy context**: retrieved excerpts injected via tool results, not stuffed blindly every turn.

## Security notes (demo-grade)

- Demo passwords are intentionally simple for assessment.
- JWT secret must be rotated for any non-demo deployment.
- No cross-employee data access is exposed by tools.
- Production would add RBAC, audit logs, SSO/OIDC, and rate limiting.

## Repository layout

```
hr-chat-agent/
├── backend/app/
│   ├── agent/          # LangGraph agent, tools, RAG
│   ├── auth/           # JWT + password verify
│   ├── db/             # SQLAlchemy models + seed
│   ├── main.py         # FastAPI routes
│   └── config.py
├── data/policies/      # HR policy knowledge base
├── frontend/           # Streamlit UI
├── docs/               # Architecture & demo script
└── scripts/            # seed / run helpers
```
