# Assessment Submission Checklist

Fill the official submission form with:

| Field | Value |
|-------|-------|
| Project name | I2I Corp HR Chat Agent |
| GitHub public repo | *(add after you push)* |
| Demo video | *(record using docs/DEMO_SCRIPT.md; upload to Drive/YouTube unlisted)* |
| Architecture docs | `docs/ARCHITECTURE.md` |
| Setup / runbook | `README.md` |
| Framework | LangGraph + LangChain + Groq/Ollama + FastAPI + Streamlit |

## What this submission demonstrates

- Authenticated employee interaction (JWT login)
- Answers grounded in provided HR policy documents
- Tools + database for leave balance, eligibility, and leave-day calculation
- Agent reasoning / tool-calling workflow with visible traces in the UI
- Conversation history for follow-up context

## Push to GitHub (public)

```powershell
cd Y:\agentic-ai\hr-chat-agent
git init
git add .
git commit -m "Initial HR Chat Agent assessment submission"
gh repo create hr-chat-agent --public --source=. --remote=origin --push
```

Do **not** commit a real `.env` with your API key. Only `.env.example` should be in git.
