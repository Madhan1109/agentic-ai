# Demo Script — HR Chat Agent

Use this script for the assessment demo video (~5–8 minutes).

## Before recording

1. Optional: add a free `GROQ_API_KEY` in `.env` (or skip — local tool mode still works)
2. Start API: `python scripts/run_api.py`
3. Start UI: `python scripts/run_ui.py`
4. Open `http://localhost:8501`

## Scene 1 — Problem & architecture (45–60s)

- State the use case: authenticated employees need policy answers + personal leave data.
- Show `docs/ARCHITECTURE.md` briefly (agent + tools + DB + policies).
- Mention framework: **LangGraph** with FastAPI + Streamlit.

## Scene 2 — Authentication (30s)

1. Sign in as a full-time employee from the seeded HR database
2. Show sidebar employee identity (name, department)

## Scene 3 — Policy question (RAG tool) (60s)

Ask:

> What is the maternity leave policy and who is eligible?

Expected:

- Agent calls `search_hr_policies`
- Answer cites leave policy (26 weeks, 6 months service)
- Expand **Agent tool trace** in the UI

## Scene 4 — Dynamic leave balance (DB tool) (60s)

Ask:

> What is my current leave balance?

Expected:

- Calls `get_leave_balance`
- Shows PL/SL/CL entitled, used, pending, available for that employee

## Scene 5 — Eligibility + calculation (multi-tool) (90s)

Ask:

> Am I eligible for privilege leave, and how many days would be deducted if I take leave from 2026-10-20 to 2026-10-24?

Expected:

- Calls `check_leave_eligibility` and/or `calculate_leave_days` (and maybe balance)
- Explains eligibility (full-time employee past probation)
- Calculates working days (exclude weekend) and compares to available balance

## Scene 6 — Context / different persona (60s)

1. Sign out
2. Sign in as a probationary employee from the seed data
3. Ask: `Can I take privilege leave?`

Expected:

- Eligibility tool returns **not eligible** (< 90 days)

Optional: sign in as a contractor from the seed data and show no leave entitlements.

## Scene 7 — Wrap-up (30s)

- Recap: auth, policy RAG, DB tools, LangGraph reasoning, visible tool traces
- Point to GitHub repo + `docs/ARCHITECTURE.md` + README setup

## Suggested video outline title cards

1. HR Chat Agent — Assessment Demo
2. Architecture
3. Authenticated Chat
4. Policy RAG
5. Leave Tools
6. Eligibility by Persona
7. Thank you / repo link
