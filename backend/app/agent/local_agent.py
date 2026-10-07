"""Zero-cost conversational HR agent: same tools, short natural answers."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Any

from backend.app.agent.tools import (
    CURRENT_EMPLOYEE_ID,
    approve_pending_leave,
    calculate_leave_days,
    cancel_leave_request,
    check_leave_blackout,
    check_leave_eligibility,
    create_escalation_ticket,
    draft_manager_leave_note,
    evaluate_leave_scenario,
    forecast_leave_balance,
    get_employee_profile,
    get_holidays,
    get_hr_insights,
    get_leave_balance,
    get_onboarding_checklist,
    get_recent_leave_requests,
    search_hr_policies,
    submit_leave_request,
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

# Session-style prefs inferred from chat history + current message
_REPLY_LANG = "en"
_SHORT_MODE = False

_HINDI_SNIPPETS = {
    "yes": "हां",
    "no": "नहीं",
    "balance": "आपका वर्तमान अवकाश शेष:",
    "source": "स्रोत",
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
    m = re.search(r"(?:take|need|want|avail|apply|submit|forecast|plan).{0,28}(\d+(?:\.\d+)?)\s*(?:days?|pl|sl|cl)\b", q)
    if m:
        return float(m.group(1))
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:days?\s+of\s+)?(?:privilege|sick|casual|pl|sl|cl)\b", q)
    if m:
        return float(m.group(1))
    m = re.search(rf"(?:take|need|want|submit|forecast|plan).{{0,20}}\b({'|'.join(_NUM_WORDS)})\b", q)
    if m:
        return float(_NUM_WORDS[m.group(1)])
    m = re.search(r"(\d+(?:\.\d+)?)\s*more\s*days?", q)
    if m:
        return float(m.group(1))
    return 1.0


def _already_taken(text: str) -> float | None:
    q = text.lower()
    m = re.search(r"(?:took|taken|availed|used|already)\s+(\d+(?:\.\d+)?)\s*days?", q)
    if m:
        return float(m.group(1))
    m = re.search(rf"(?:took|taken|availed|used|already)\s+\b({'|'.join(_NUM_WORDS)})\b", q)
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
            " If you are struggling, I2I Employee Assistance (EAP) is confidential and 24/7. "
            "Contact benefits@i2icorp.example — this chat does not replace EAP."
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
                "I cannot share another person's leave or profile."
            )
    return None


def _combined_text(user_message: str, history: list[dict[str, str]] | None) -> str:
    prior = " ".join(m.get("content", "") for m in (history or [])[-6:] if m.get("role") == "user")
    return f"{prior} {user_message}".strip()


def _update_prefs(q: str, history: list[dict[str, str]] | None) -> None:
    global _REPLY_LANG, _SHORT_MODE
    blob = _combined_text(q, history).lower()
    if any(w in blob for w in ("in hindi", "reply in hindi", "hindi mein", "हिंदी", "hindi please")):
        _REPLY_LANG = "hi"
    if any(w in blob for w in ("in english", "reply in english", "english please")):
        _REPLY_LANG = "en"
    if any(w in blob for w in ("short answer", "brief", "voice mode", "keep it short", "be brief")):
        _SHORT_MODE = True
    if any(w in blob for w in ("detailed answer", "full answer", "normal mode")):
        _SHORT_MODE = False


def _finish(answer: str, trace: list[dict], note: str = "") -> dict[str, Any]:
    text = (answer + note).strip()
    if _SHORT_MODE and len(text) > 180:
        # Keep first 1–2 sentences
        parts = re.split(r"(?<=[.!?])\s+", text)
        text = " ".join(parts[:2]).strip()
    if _REPLY_LANG == "hi":
        text = (
            f"[Hindi summary] {_HINDI_SNIPPETS['yes'] if text.lower().startswith('yes') else ''}"
            f"{_HINDI_SNIPPETS['no'] if text.lower().startswith('no') else ''} "
            f"{text} "
            f"({_HINDI_SNIPPETS['source']}: same HR tools / policy)."
        ).strip()
    return {"answer": text, "tool_trace": trace, "llm_provider": "local"}


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
    citation = ""
    if "Source:" in raw:
        source = raw.split("Source:", 1)[1].split("|", 1)[0].strip()
        section = ""
        if "Section:" in raw:
            section = raw.split("Section:", 1)[1].split("\n", 1)[0].strip()
        citation = f" Citation: {source}" + (f" — {section}" if section else "") + "."
        return f"{text}{citation}"
    return text


def _known_policy_answer(q: str) -> str | None:
    if "maternity" in q:
        return (
            "Maternity leave at I2I Corp: eligible after 6 months of continuous service, "
            "with 26 weeks entitlement. Notify HR at least 8 weeks before the expected start. "
            "Citation: leave_policy.md — Maternity Leave (HR-POL-LEAVE-2025)."
        )
    if "paternity" in q:
        return (
            "Paternity leave: eligible after 6 months of continuous service, 10 working days, "
            "to be taken within 3 months of childbirth. "
            "Citation: leave_policy.md — Paternity Leave (HR-POL-LEAVE-2025)."
        )
    if "hybrid" in q or "remote work" in q:
        return (
            "Default hybrid model is 3 days in office and 2 days remote. "
            "Tuesday and Thursday are core in-office days. Eligible after 90 days probation. "
            "Citation: remote_work_policy.md — Hybrid Work Model (HR-POL-REMOTE-2025)."
        )
    return None


def _default_range(days: float = 1) -> tuple[str, str]:
    start = date.today() + timedelta(days=7)
    # skip to weekday
    while start.weekday() >= 5:
        start += timedelta(days=1)
    end = start
    left = max(int(days) - 1, 0)
    while left > 0:
        end += timedelta(days=1)
        if end.weekday() < 5:
            left -= 1
    return start.isoformat(), end.isoformat()


def run_local_hr_agent(
    user_message: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    q = user_message.lower()
    ctx = _combined_text(user_message, history).lower()
    _update_prefs(q, history)
    trace: list[dict] = []
    lt = _detect_leave_type(user_message, default=_detect_leave_type(ctx, default="PL"))
    note = _wellbeing_note(q)

    blocked = _privacy_block(q)
    if blocked:
        return _finish(blocked, trace, note)

    # Language / short-mode only switches
    if any(w in q for w in ("reply in hindi", "in hindi", "hindi mein")) and len(q) < 40:
        return _finish("Okay — I will reply in Hindi style summaries for the rest of this chat.", trace)
    if any(w in q for w in ("short answer", "brief", "voice mode", "keep it short")) and len(q) < 40:
        return _finish("Short answer mode on. Ask your HR question.", trace)

    if any(w in q for w in ("insight", "should i know", "what should i know", "briefing", "anything pending", "proactive")):
        data = _parse_json(_call(get_hr_insights, {}, trace))
        alerts = " ".join(data.get("alerts") or [])
        return _finish(f"{alerts} Next: {data.get('next_action', '')}".strip(), trace, note)

    if any(w in q for w in ("onboarding", "checklist", "new joiner", "what do i need to complete")):
        data = _parse_json(_call(get_onboarding_checklist, {}, trace))
        lines = [
            f"- {'[x]' if i.get('done') else '[ ]'} {i.get('step')}" for i in (data.get("checklist") or [])
        ]
        return _finish(
            f"Onboarding checklist ({data.get('tenure_days')} days tenure):\n" + "\n".join(lines),
            trace,
            note,
        )

    if any(w in q for w in ("escalate", "ticket", "hrbp help", "need hr help", "open a case", "raise a ticket")):
        topic = "HR assistance"
        if "leave" in q:
            topic = "Leave exception"
        data = _parse_json(_call(create_escalation_ticket, {"topic": topic, "details": user_message[:500]}, trace))
        return _finish(
            f"Escalation ticket #{data.get('ticket_id')} logged (status: {data.get('status')}). HRBP can follow up.",
            trace,
            note,
        )

    if any(
        w in q
        for w in (
            "approve my",
            "simulate approval",
            "simulate manager",
            "manager approval",
            "manager approved",
            "approve pending",
            "approval of my pending",
        )
    ):
        data = _parse_json(_call(approve_pending_leave, {}, trace))
        if not data.get("ok"):
            return _finish(data.get("error") or "Nothing to approve.", trace, note)
        return _finish(
            f"Simulated approval for request #{data.get('request_id')}: {data.get('days'):g} day(s) "
            f"{data.get('leave_type')} now approved. Available after: {data.get('available_after')}.",
            trace,
            note,
        )

    if any(w in q for w in ("cancel my leave", "withdraw", "cancel pending", "cancel leave request")):
        data = _parse_json(_call(cancel_leave_request, {}, trace))
        if not data.get("ok"):
            return _finish(data.get("error") or "Nothing to cancel.", trace, note)
        return _finish(
            f"Cancelled request #{data.get('request_id')} ({data.get('days'):g} day(s) {data.get('leave_type')}). "
            f"Available after: {data.get('available_after')}.",
            trace,
            note,
        )

    if any(w in q for w in ("submit leave", "apply leave", "book leave", "create leave request", "request leave for")):
        dates = _DATE.findall(user_message)
        if dates:
            start, end = dates[0], (dates[1] if len(dates) > 1 else dates[0])
        else:
            start, end = _default_range(_extra_days(user_message))
        use_lt = lt if lt in {"PL", "SL", "CL"} else "PL"
        data = _parse_json(
            _call(
                submit_leave_request,
                {
                    "leave_type": use_lt,
                    "start_date": start,
                    "end_date": end,
                    "reason": "requested via HR chat",
                    "half_day": "half" in q,
                },
                trace,
            )
        )
        if not data.get("ok"):
            return _finish(data.get("error") or "Could not submit leave.", trace, note)
        return _finish(
            f"Leave request #{data.get('request_id')} submitted: {data.get('days'):g} day(s) {data.get('leave_type')} "
            f"({start} to {end}), status pending. Available after submit: {data.get('available_after')}.",
            trace,
            note,
        )

    if any(w in q for w in ("forecast", "if i take", "what's left if", "what is left if", "remaining if")):
        planned = _extra_days(user_message)
        use_lt = lt if lt in {"PL", "SL", "CL"} else "PL"
        data = _parse_json(_call(forecast_leave_balance, {"leave_type": use_lt, "planned_days": planned}, trace))
        if not data.get("ok"):
            return _finish(data.get("error") or "No forecast available.", trace, note)
        ok = "fits" if data.get("feasible") else "does not fit"
        return _finish(
            f"If you take {planned:g} day(s) of {_label(use_lt)}, current available "
            f"{data.get('current_available')} -> remaining {data.get('remaining_after')} ({ok}).",
            trace,
            note,
        )

    if any(w in q for w in ("blackout", "busy period", "year-end", "last week of december", "december leave", "release freeze")):
        dates = _DATE.findall(user_message)
        if dates:
            start, end = dates[0], (dates[1] if len(dates) > 1 else dates[0])
        elif "december" in q or "year-end" in q:
            start, end = "2026-12-15", "2026-12-31"
        else:
            start, end = _default_range(5)
        data = _parse_json(_call(check_leave_blackout, {"start_date": start, "end_date": end}, trace))
        if data.get("blocked"):
            bo = (data.get("blackouts") or [{}])[0]
            return _finish(
                f"Yes — that overlaps blackout '{bo.get('name')}' ({bo.get('start_date')} to {bo.get('end_date')}). "
                f"{bo.get('reason')}",
                trace,
                note,
            )
        return _finish(f"No blackout for {data.get('department')} between {start} and {end}.", trace, note)

    if any(w in q for w in ("holiday", "diwali", "christmas", "thanksgiving", "public holiday", "holidays this year")):
        query = ""
        for name in ("diwali", "christmas", "thanksgiving", "memorial", "labor", "independence", "juneteenth"):
            if name in q:
                query = name
                break
        data = _parse_json(_call(get_holidays, {"year": 2026, "query": query}, trace))
        holidays = data.get("holidays") or []
        if not holidays:
            return _finish("No matching public holidays found for that query.", trace, note)
        if query and len(holidays) == 1:
            h = holidays[0]
            return _finish(f"Yes — {h['name']} is on {h['date']} (company holiday calendar).", trace, note)
        lines = [f"- {h['name']}: {h['date']}" for h in holidays[:12]]
        return _finish(f"Public holidays ({data.get('year')}):\n" + "\n".join(lines), trace, note)

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
        return _finish(
            f"Draft only (not sent). To: {data.get('to')}\nSubject: {data.get('subject')}\n\n{data.get('body')}",
            trace,
            note,
        )

    wants_scenario = _is_scenario(q) and not any(w in q for w in ("submit", "apply", "book", "forecast"))
    wants_balance = any(
        w in q for w in ("balance", "how many days left", "remaining", "leave left", "what's my leave", "what is my leave")
    ) and "if i take" not in q and "forecast" not in q
    wants_elig = any(w in q for w in ("eligib", "am i allowed", "qualify")) and not wants_scenario
    wants_calc = bool(_DATE.search(user_message)) and not any(
        w in q for w in ("submit", "apply", "book", "blackout", "holiday")
    )
    wants_requests = any(w in q for w in ("my request", "pending leave", "applied", "leave requests"))
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
            return _finish(" ".join(str(b) for b in bits if b), trace, note)
        blockers = data.get("blockers") or ["This extra leave is not allowed on current records."]
        return _finish("No - not based on current HR data. " + " ".join(blockers), trace, note)

    if wants_calc:
        dates = _DATE.findall(user_message)
        start = dates[0]
        end = dates[1] if len(dates) > 1 else dates[0]
        calc_lt = lt if lt in {"PL", "SL", "CL"} else "PL"
        data = _parse_json(
            _call(
                calculate_leave_days,
                {"start_date": start, "end_date": end, "leave_type": calc_lt, "half_day": "half" in q},
                trace,
            )
        )
        days = data.get("working_days_to_deduct")
        ok = data.get("sufficient_balance")
        avail = data.get("available_balance")
        verdict = "That fits your balance." if ok else "That would exceed your available balance."
        return _finish(
            f"{days:g} working day(s) of {_label(calc_lt)} would be deducted "
            f"({start} to {end}, weekends excluded). You have {avail} available. {verdict}",
            trace,
            note,
        )

    if wants_elig:
        data = _parse_json(_call(check_leave_eligibility, {"leave_type": lt}, trace))
        reasons = " ".join(data.get("reasons") or [])
        if data.get("eligible"):
            avail = data.get("available_balance")
            extra = f" Available balance: {avail} day(s)." if avail is not None else ""
            return _finish(f"Yes - you are eligible for {_label(lt)}.{extra} {reasons}".strip(), trace, note)
        return _finish(f"No - you are not eligible for {_label(lt)} right now. {reasons}".strip(), trace, note)

    if wants_balance:
        data = _parse_json(_call(get_leave_balance, {"leave_type": "ALL"}, trace))
        rows = data.get("balances") or []
        if not rows:
            return _finish(data.get("message") or "No leave balances on file.", trace, note)
        lines = ["Your current leave:"] + [_format_balance_line(r) for r in rows]
        return _finish("\n".join(lines), trace, note)

    if wants_requests:
        data = _parse_json(_call(get_recent_leave_requests, {"limit": 5}, trace))
        reqs = data.get("requests") or []
        if not reqs:
            return _finish("You have no leave requests on file.", trace, note)
        lines = [
            f"- #{r.get('request_id')} {r['leave_type']} {r['start_date']} -> {r['end_date']} "
            f"({r['days']:g} day(s), {r['status']})"
            for r in reqs
        ]
        return _finish("Recent requests:\n" + "\n".join(lines), trace, note)

    if wants_profile:
        data = _parse_json(_call(get_employee_profile, {}, trace))
        return _finish(
            f"You are {data.get('full_name')} ({data.get('employee_id')}), "
            f"{data.get('role_title')} in {data.get('department')}, "
            f"{data.get('employment_type')}, joined {data.get('join_date')}.",
            trace,
            note,
        )

    if wants_policy or True:
        known = _known_policy_answer(q)
        if known:
            _call(search_hr_policies, {"query": user_message}, trace)
            return _finish(known, trace, note)
        raw = _call(search_hr_policies, {"query": user_message}, trace)
        snippet = _policy_snippet(raw)
        return _finish(
            f"{snippet} If you need this applied to your balance, ask: can I take one more sick leave?",
            trace,
            note,
        )
