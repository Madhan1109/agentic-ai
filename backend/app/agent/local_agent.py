"""Zero-cost conversational HR agent: same tools, short natural answers."""

from __future__ import annotations

import json
import re
from typing import Any

from backend.app.agent.tools import (
    CURRENT_EMPLOYEE_ID,
    calculate_leave_days,
    check_leave_eligibility,
    draft_manager_leave_note,
    evaluate_leave_scenario,
    get_employee_profile,
    get_hr_insights,
    get_leave_balance,
    get_recent_leave_requests,
    search_hr_policies,
)

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_NUM_WORDS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "half": 0.5,
}


def _detect_leave_type(text: str, default: str | None = None) -> str:
    q = text.lower()
    if "maternity" in q:
        return "MATERNITY"
    if "paternity" in q:
        return "PATERNITY"
    if "sick" in q or re.search(r"\bsl\b", q):
        return "SL"
    if "casual" in q or re.search(r"\bcl\b", q):
        return "CL"
    if "privilege" in q or "annual" in q or re.search(r"\bpl\b", q) or "pto" in q:
        return "PL"
    if "comp" in q and "off" in q:
        return "COMP_OFF"
    return default or "PL"


def _label(lt: str) -> str:
    return {
        "PL": "privilege leave",
        "SL": "sick leave",
        "CL": "casual leave",
        "MATERNITY": "maternity leave",
        "PATERNITY": "paternity leave",
        "COMP_OFF": "comp-off",
    }.get(lt, lt)


def _parse_json(raw: str) -> dict:
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _call(tool, args: dict, trace: list[dict]) -> str:
    name = getattr(tool, "name", None) or tool.__name__
    trace.append({"tool": name, "args": args, "type": "call"})
    output = tool.invoke(args)
    shown = output if isinstance(output, str) else json.dumps(output)
    if len(shown) > 800:
        shown = shown[:800] + "…"
    trace.append({"tool": name, "output": shown, "type": "result"})
    return output if isinstance(output, str) else json.dumps(output)


def _first_number_before(text: str, keywords: tuple[str, ...]) -> float | None:
    q = text.lower()
    for kw in keywords:
        m = re.search(rf"(\d+(?:\.\d+)?)\s*(?:days?|day)?\s*[^\n.]{{0,20}}{kw}", q)
        if m:
            return float(m.group(1))
        m = re.search(rf"\b({'|'.join(_NUM_WORDS)})\s+(?:more\s+)?(?:days?|day)?\s*[^\n.]{{0,20}}{kw}", q)
        if m:
            return float(_NUM_WORDS[m.group(1)])
    return None


def _extra_days(text: str) -> float:
    q = text.lower()
    if re.search(r"\bone more\b|\banother (?:one|day)\b|\bone extra\b", q):
        return 1.0
    if re.search(r"\bhalf[- ]?day\b", q):
        return 0.5
    m = re.search(r"(?:take|need|want|avail|apply).{0,24}(\d+(?:\.\d+)?)\s*days?", q)
    if m:
        return float(m.group(1))
    m = re.search(rf"(?:take|need|want).{{0,16}}\b({'|'.join(_NUM_WORDS)})\b", q)
    if m:
        return float(_NUM_WORDS[m.group(1)])
    m = re.search(r"(\d+(?:\.\d+)?)\s*more\s*days?", q)
    if m:
        return float(m.group(1))
    return 1.0


def _already_taken(text: str) -> float | None:
    q = text.lower()
    m = re.search(
        r"(?:took|taken|availed|used|already)\s+(\d+(?:\.\d+)?)\s*days?",
        q,
    )
    if m:
        return float(m.group(1))
    m = re.search(
        rf"(?:took|taken|availed|used|already)\s+\b({'|'.join(_NUM_WORDS)})\b",
        q,
    )
    if m:
        return float(_NUM_WORDS[m.group(1)])
    return _first_number_before(q, ("leave this month", "this month", "already"))


def _wellbeing_note(q: str) -> str:
    if any(
        w in q
        for w in (
            "burnout",
            "overwhelmed",
            "can't cope",
            "cannot cope",
            "depressed",
            "anxious",
            "mental health",
            "not okay",
            "struggling",
        )
    ):
        return (
            "\n\nIf you are struggling, I2I Employee Assistance (EAP) is confidential and 24/7. "
            "See benefits policy or contact benefits@i2icorp.example — this chat does not replace EAP."
        )
    return ""


_OTHER_PEOPLE = {
    "alice": "E1001",
    "nguyen": "E1001",
    "cara": "E1003",
    "devon": "E2001",
    "brooks": "E2001",
    "bob": "E1002",
    "martinez": "E1002",
}


def _privacy_block(q: str) -> str | None:
    me = (CURRENT_EMPLOYEE_ID or "").upper()
    for name, emp_id in _OTHER_PEOPLE.items():
        if re.search(rf"\b{name}\b", q) and emp_id != me:
            return (
                "I can only discuss the signed-in employee's own HR record. "
                "I cannot share another person's leave or profile. Sign in as that employee, or ask HRBP through official channels."
            )
    return None


def _combined_text(user_message: str, history: list[dict[str, str]] | None) -> str:
    prior = " ".join(
        m.get("content", "") for m in (history or [])[-6:] if m.get("role") == "user"
    )
    return f"{prior} {user_message}".strip()


def _is_scenario(q: str) -> bool:
    extra = any(
        w in q
        for w in (
            "one more",
            "another",
            "extra",
            "shall i take",
            "can i take",
            "should i take",
            "may i take",
            "allowed to take",
            "take leave",
            "take sick",
            "take one",
        )
    )
    stated = any(w in q for w in ("took", "taken", "already", "this month", "availed"))
    return extra or (stated and any(w in q for w in ("more", "another", "can i", "shall i")))


def _format_balance_line(row: dict) -> str:
    return (
        f"- {_label(row['leave_type']).title()} ({row['leave_type']}): "
        f"{row['available']} available "
        f"(entitled {row['entitled']}, used {row['used']}, pending {row['pending']})"
    )


def _plain_text(text: str) -> str:
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`+", "", text)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    return " ".join(text.split())


def _policy_snippet(raw: str) -> str:
    block = raw.split("\n\n---\n\n")[0]
    lines = [ln for ln in block.splitlines() if ln.strip() and not ln.startswith("[")]
    text = _plain_text(" ".join(lines))
    if len(text) > 320:
        text = text[:320].rsplit(" ", 1)[0] + "..."
    if "Source:" in raw:
        source = raw.split("Source:", 1)[1].split("|", 1)[0].strip()
        return f"{text} Source: {source}."
    return text


def _known_policy_answer(q: str) -> str | None:
    if "maternity" in q:
        return (
            "Maternity leave at I2I Corp: eligible after 6 months of continuous service, "
            "with 26 weeks entitlement. Notify HR at least 8 weeks before the expected start. "
            "Source: leave policy (HR-POL-LEAVE-2025)."
        )
    if "paternity" in q:
        return (
            "Paternity leave: eligible after 6 months of continuous service, 10 working days, "
            "to be taken within 3 months of childbirth. Source: leave policy (HR-POL-LEAVE-2025)."
        )
    if "hybrid" in q or "remote work" in q:
        return (
            "Default hybrid model is 3 days in office and 2 days remote. "
            "Tuesday and Thursday are core in-office days. Eligible after 90 days probation. "
            "Source: remote work policy (HR-POL-REMOTE-2025)."
        )
    return None


def run_local_hr_agent(
    user_message: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    q = user_message.lower()
    ctx = _combined_text(user_message, history).lower()
    trace: list[dict] = []
    lt = _detect_leave_type(user_message, default=_detect_leave_type(ctx, default="PL"))
    note = _wellbeing_note(q)

    blocked = _privacy_block(q)
    if blocked:
        return {"answer": blocked + note, "tool_trace": trace, "llm_provider": "local"}

    if any(w in q for w in ("insight", "should i know", "what should i know", "briefing", "anything pending", "proactive")):
        data = _parse_json(_call(get_hr_insights, {}, trace))
        alerts = " ".join(data.get("alerts") or [])
        answer = f"{alerts} Next: {data.get('next_action', '')}".strip() + note
        return {"answer": answer, "tool_trace": trace, "llm_provider": "local"}

    if any(w in q for w in ("draft", "email my manager", "write to my manager", "message for my manager", "manager note")):
        days = _extra_days(user_message)
        data = _parse_json(
            _call(
                draft_manager_leave_note,
                {
                    "leave_type": lt if lt in {"PL", "SL", "CL"} else "PL",
                    "days": days,
                    "reason": "as discussed",
                },
                trace,
            )
        )
        answer = (
            f"Draft only (not sent). To: {data.get('to')}\n"
            f"Subject: {data.get('subject')}\n\n{data.get('body')}"
        ) + note
        return {"answer": answer, "tool_trace": trace, "llm_provider": "local"}

    wants_scenario = _is_scenario(q)
    wants_balance = any(
        w in q for w in ("balance", "how many days left", "remaining", "leave left", "what's my leave", "what is my leave")
    )
    wants_elig = any(w in q for w in ("eligib", "am i allowed", "qualify", "can i take", "shall i take")) and not wants_scenario
    wants_calc = bool(_DATE.search(user_message))
    wants_requests = any(w in q for w in ("my request", "pending leave", "applied"))
    wants_profile = any(w in q for w in ("my profile", "who am i", "my department", "join date"))
    wants_policy = any(
        w in q
        for w in (
            "policy",
            "maternity",
            "paternity",
            "hybrid",
            "remote work",
            "benefit",
            "code of conduct",
            "holiday",
            "what is our",
            "explain",
        )
    ) and not wants_scenario

    if wants_scenario:
        extra = _extra_days(user_message)
        taken = _already_taken(user_message)
        if lt not in {"PL", "SL", "CL"}:
            lt = "SL" if "sick" in ctx else "PL"
        args: dict[str, Any] = {"leave_type": lt, "extra_days": extra}
        if taken is not None:
            args["already_taken_this_month"] = taken
        data = _parse_json(_call(evaluate_leave_scenario, args, trace))
        name = _label(lt)
        if data.get("can_take_extra"):
            leftover = data.get("remaining_after_extra")
            bits = [
                f"Yes - you can take {extra:g} more day(s) of {name}.",
                f"Official {data.get('leave_type')} available: {data.get('official_available')} day(s).",
            ]
            if taken is not None:
                bits.append(
                    f"After the {taken:g} day(s) you mentioned plus this extra {extra:g}, you would still have {leftover} day(s) left."
                )
            else:
                bits.append(f"After this extra {extra:g} day(s) you would have {leftover} day(s) left.")
            bits.extend(data.get("notes") or [])
            bits.append("Apply in the HR portal (or with your manager) when you are ready.")
            return {"answer": " ".join(str(b) for b in bits if b), "tool_trace": trace, "llm_provider": "local"}

        blockers = data.get("blockers") or ["This extra leave is not allowed on current records."]
        return {
            "answer": "No - not based on current HR data. " + " ".join(blockers),
            "tool_trace": trace,
            "llm_provider": "local",
        }

    if wants_calc:
        dates = _DATE.findall(user_message)
        start = dates[0]
        end = dates[1] if len(dates) > 1 else dates[0]
        calc_lt = lt if lt in {"PL", "SL", "CL"} else "PL"
        data = _parse_json(
            _call(
                calculate_leave_days,
                {
                    "start_date": start,
                    "end_date": end,
                    "leave_type": calc_lt,
                    "half_day": "half" in q,
                },
                trace,
            )
        )
        days = data.get("working_days_to_deduct")
        ok = data.get("sufficient_balance")
        avail = data.get("available_balance")
        verdict = "That fits your balance." if ok else "That would exceed your available balance."
        answer = (
            f"{days:g} working day(s) of {_label(calc_lt)} would be deducted "
            f"({start} to {end}, weekends excluded). You have {avail} available. {verdict}"
        )
        return {"answer": answer, "tool_trace": trace, "llm_provider": "local"}

    if wants_elig:
        data = _parse_json(_call(check_leave_eligibility, {"leave_type": lt}, trace))
        reasons = " ".join(data.get("reasons") or [])
        if data.get("eligible"):
            avail = data.get("available_balance")
            extra = f" Available balance: {avail} day(s)." if avail is not None else ""
            answer = f"Yes - you are eligible for {_label(lt)}.{extra} {reasons}".strip()
        else:
            answer = f"No - you are not eligible for {_label(lt)} right now. {reasons}".strip()
        return {"answer": answer, "tool_trace": trace, "llm_provider": "local"}

    if wants_balance:
        data = _parse_json(_call(get_leave_balance, {"leave_type": "ALL"}, trace))
        rows = data.get("balances") or []
        if not rows:
            msg = data.get("message") or "No leave balances on file."
            return {"answer": msg, "tool_trace": trace, "llm_provider": "local"}
        lines = ["Your current leave:"] + [_format_balance_line(r) for r in rows]
        return {"answer": "\n".join(lines), "tool_trace": trace, "llm_provider": "local"}

    if wants_requests:
        data = _parse_json(_call(get_recent_leave_requests, {"limit": 5}, trace))
        reqs = data.get("requests") or []
        if not reqs:
            return {"answer": "You have no leave requests on file.", "tool_trace": trace, "llm_provider": "local"}
        lines = [
            f"- {r['leave_type']} {r['start_date']} → {r['end_date']} ({r['days']:g} day(s), {r['status']})"
            for r in reqs
        ]
        return {"answer": "Recent requests:\n" + "\n".join(lines), "tool_trace": trace, "llm_provider": "local"}

    if wants_profile:
        data = _parse_json(_call(get_employee_profile, {}, trace))
        answer = (
            f"You are {data.get('full_name')} ({data.get('employee_id')}), "
            f"{data.get('role_title')} in {data.get('department')}, "
            f"{data.get('employment_type')}, joined {data.get('join_date')}."
        )
        return {"answer": answer, "tool_trace": trace, "llm_provider": "local"}

    if wants_policy or True:
        known = _known_policy_answer(q)
        if known:
            _call(search_hr_policies, {"query": user_message}, trace)
            return {"answer": known + note, "tool_trace": trace, "llm_provider": "local"}
        raw = _call(search_hr_policies, {"query": user_message}, trace)
        snippet = _policy_snippet(raw)
        return {
            "answer": f"{snippet} If you need this applied to your balance, ask something like: can I take one more sick leave?" + note,
            "tool_trace": trace,
            "llm_provider": "local",
        }
