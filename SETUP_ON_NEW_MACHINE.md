# Setup on a new Windows machine (demo)

## What’s in the zip

Source code, HR policies, docs, and scripts.  
**Not included:** Python virtualenv (`.venv`) — recreate it on the new PC with `pip install`.

## Prerequisites on the new machine

1. **Python 3.11+** installed  
   - Check: open PowerShell → `python --version`  
   - If missing: https://www.python.org/downloads/ (tick “Add Python to PATH”)
2. Internet for the first `pip install` only (downloads packages).
3. **No paid OpenAI key required.** App runs in free **local** tool mode by default.

## Steps

### 1) Unzip

Unzip to a simple path, for example:

`C:\hr-chat-agent`

Avoid very long paths if possible.

### 2) Open PowerShell in that folder

```powershell
cd C:\hr-chat-agent
```

### 3) Create virtual environment and install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If `Activate.ps1` is blocked:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 4) Configure env (optional)

```powershell
copy .env.example .env
```

Default works with **no API key** (`llm_provider=local`).

Optional nicer answers (still free): get a key from https://console.groq.com/keys and set in `.env`:

```env
GROQ_API_KEY=gsk_your_key
```

### 5) Seed the demo database

```powershell
python scripts\seed_db.py --force
```

### 6) Start the API (Terminal 1)

```powershell
.\.venv\Scripts\Activate.ps1
python scripts\run_api.py
```

Wait until you see: `Uvicorn running on http://127.0.0.1:8000`

### 7) Start the UI (Terminal 2)

```powershell
cd C:\hr-chat-agent
.\.venv\Scripts\Activate.ps1
python scripts\run_ui.py
```

Open browser: **http://localhost:8501**

### 8) Login and demo

Sign in with a seeded employee account, then try asking:

- What is my leave balance?
- Am I eligible for privilege leave?
- How many leave days for 2026-10-20 to 2026-10-24?
- What is the maternity leave policy?

Expand **Agent tool trace** in the UI to show tool usage.

## Or use the helper script

After steps 3–4:

```powershell
.\start.ps1
```

## Demo talking points

- Auth: JWT login  
- Agentic: LangGraph (or local tool routing) + HR tools + policy search  
- Free: no OpenAI payment; optional free Groq key  
- Docs: `docs\ARCHITECTURE.md`, `docs\DEMO_SCRIPT.md`

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `python` not found | Reinstall Python with “Add to PATH”, reopen PowerShell |
| Port 8000 in use | Close other apps or change `API_PORT` in `.env` |
| UI can’t reach API | Ensure Terminal 1 API is still running |
| pip slow / fails | Retry; check corporate proxy/firewall |
| bcrypt warning on login | Safe to ignore if login still works |
