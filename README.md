# I2I Corp HR Chat Agent

Agentic AI assessment project: an authenticated **HR Chat Agent** that answers policy questions from HR documents and uses tools/database lookups for leave balance, eligibility, and leave-day calculations.

**Stack:** LangGraph · LangChain · Groq (free) / Ollama · FastAPI · Streamlit · SQLite · BM25 policy retrieval

## Features

- JWT employee authentication
- Policy Q&A over markdown HR documents (`data/policies/`)
- Dynamic tools: leave balance, eligibility, working-day calculation, recent requests
- Visible agent tool traces in the UI (reasoning / tool usage)
- Multi-turn conversation context

## Unique features

These go beyond a basic FAQ chatbot:

1. **Privacy wall** — Asking about another employee (e.g. Alice's balance while signed in as Bob) is refused. Tools only see the JWT employee.
2. **HR insights briefing** — “What should I know?” returns probation countdown, pending requests, and a next action.
3. **Manager leave draft** — “Draft an email to my manager…” builds a note with the real manager address and balance. It is **not sent**.
4. **Wellbeing / EAP nudge** — Distressed language (burnout, overwhelmed) adds a confidential EAP pointer.
5. **Session tool log** — Sidebar lists tools used this chat (compliance / audit for HR).
6. **Twisted leave scenarios** — “I already took 2 days, one more sick leave?” uses `evaluate_leave_scenario`, not a canned FAQ.

Ask in the demo:

- What should I know?
- Draft an email to my manager for 1 day of sick leave
- Show me Alice's leave balance (while logged in as Bob)
- I'm overwhelmed with work, can I take sick leave?

## Quick start

### 1) Prerequisites

- Python 3.11+ (tested with 3.13)
- No paid API required. Default mode uses local HR tools. Optional free Groq key for natural-language replies.

### 2) Setup

```powershell
cd Y:\agentic-ai\hr-chat-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Optional (free): set GROQ_API_KEY from https://console.groq.com/keys
python scripts\seed_db.py --force
```

### 3) Run

Terminal A — API:

```powershell
python scripts\run_api.py
```

Terminal B — UI:

```powershell
python scripts\run_ui.py
```

Open:

- Chat UI: http://localhost:8501
- API docs: http://127.0.0.1:8000/docs

Sign in from the UI with a seeded employee. Each person has **one** employment type — switch account to see a different policy outcome.

| Login | Type | What the agent is allowed to do |
|-------|------|----------------------------------|
| Alice | Full-time | Leave balance, eligibility, extra sick days, policy |
| Cara | Probation (&lt; 90 days) | Limited — PL/CL generally blocked; some SL |
| Devon | Contractor | No company leave entitlements |
| Bob | Full-time HRBP | Same leave tools as an employee; title is HRBP, not a superuser |

Seed records live in `backend/app/db/seed.py` (not listed here).

## Example questions

- What is my leave balance?
- Am I eligible for privilege leave?
- How many days will be deducted if I take leave from 2026-10-20 to 2026-10-24?
- What is the maternity leave policy?
- Explain our hybrid work model.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Demo video script](docs/DEMO_SCRIPT.md)
- [Submission checklist](docs/SUBMISSION.md)

## API sketch

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | No | Exchange email/password for JWT |
| GET | `/me` | Bearer | Current employee profile |
| POST | `/chat` | Bearer | Ask the HR agent (`message`, optional `history`) |
| GET | `/health` | No | Liveness |

## Project structure

```
hr-chat-agent/
├── backend/app/       # FastAPI + LangGraph agent + tools
├── data/policies/     # HR knowledge base
├── frontend/          # Streamlit chat UI
├── docs/              # Architecture, demo, submission notes
└── scripts/           # Seed & run helpers
```

## License

Assessment / demo use.
