"""Zero-cost fallback: route questions to the same HR tools without a cloud LLM."""

from __future__ import annotations

import json
import re
from typing import Any

from backend.app.agent.tools import (
    calculate_leave_days,
    check_leave_eligibility,
    get_employee_profile,
    get_leave_balance,
    get_recent_leave_requests,
    search_hr_policies,
)

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _detect_leave_type(text: str) -> str:
    q = text.lower()
    if "maternity" in q:
        return "MATERNITY"
    if "paternity" in q:
        return "PATERNITY"
    if "sick" in q or re.search(r"\bsl\b", q):
        return "SL"
    if "casual" in q or re.search(r"\bcl\b", q):
        return "CL"
    if "comp" in q and "off" in q:
        return "COMP_OFF"
    return "PL"


def _call(tool, args: dict, trace: list[dict]) -> str:
    name = getattr(tool, "name", None) or tool.__name__
    trace.append({"tool": name, "args": args, "type": "call"})
    output = tool.invoke(args)
    shown = output if isinstance(output, str) else json.dumps(output)
    if len(shown) > 1200:
        shown = shown[:1200] + "…"
    trace.append({"tool": name, "output": shown, "type": "result"})
    return output if isinstance(output, str) else json.dumps(output)


def run_local_hr_agent(user_message: str) -> dict[str, Any]:
    q = user_message.lower()
    trace: list[dict] = []
    sections: list[str] = []

    wants_balance = any(w in q for w in ("balance", "how many days", "pto", "remaining leave", "leave left"))
    wants_elig = any(w in q for w in ("eligib", "can i take", "am i allowed", "qualify"))
    wants_calc = bool(_DATE.search(user_message)) or any(
        w in q for w in ("calculat", "how many leave days", "deduct", "working day")
    )
    wants_requests = any(w in q for w in ("request", "pending leave", "applied"))
    wants_profile = any(w in q for w in ("my profile", "who am i", "my department", "join date"))
    wants_policy = any(
        w in q
        for w in (
            "policy",
            "maternity",
            "paternity",
            "hybrid",
            "remote",
            "benefit",
            "conduct",
            "holiday",
            "what is",
            "explain",
        )
    )

    if wants_profile:
        raw = _call(get_employee_profile, {}, trace)
        sections.append("**Profile**\n```json\n" + raw + "\n```")

    if wants_balance or wants_elig or wants_calc:
        raw = _call(get_leave_balance, {"leave_type": "ALL"}, trace)
        sections.append("**Leave balance (HR database)**\n```json\n" + raw + "\n```")

    if wants_elig or "maternity" in q or "paternity" in q:
        lt = _detect_leave_type(user_message)
        raw = _call(check_leave_eligibility, {"leave_type": lt}, trace)
        sections.append(f"**Eligibility ({lt})**\n```json\n" + raw + "\n```")

    dates = _DATE.findall(user_message)
    if wants_calc and dates:
        start = dates[0]
        end = dates[1] if len(dates) > 1 else dates[0]
        lt = _detect_leave_type(user_message)
        if lt not in {"PL", "SL", "CL"}:
            lt = "PL"
        raw = _call(
            calculate_leave_days,
            {"start_date": start, "end_date": end, "leave_type": lt, "half_day": "half" in q},
            trace,
        )
        sections.append("**Leave-day calculation**\n```json\n" + raw + "\n```")

    if wants_requests:
        raw = _call(get_recent_leave_requests, {"limit": 5}, trace)
        sections.append("**Recent leave requests**\n```json\n" + raw + "\n```")

    if wants_policy or not sections:
        raw = _call(search_hr_policies, {"query": user_message}, trace)
        sections.append("**Policy excerpts**\n" + raw)

    answer = (
        "Answer from HR tools (local free mode).\n\n"
        + "\n\n".join(sections)
        + "\n\n_Optional: add a free Groq key (`GROQ_API_KEY`) for natural-language LangGraph replies._"
    )
    return {"answer": answer, "tool_trace": trace, "llm_provider": "local"}
