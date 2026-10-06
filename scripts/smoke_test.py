#!/usr/bin/env python
"""Offline smoke test (no OpenAI): auth, policy retrieval, leave tools."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.agent.graph import run_hr_agent
from backend.app.agent.rag import get_retriever
from backend.app.agent.tools import (
    calculate_leave_days,
    check_leave_eligibility,
    get_leave_balance,
    search_hr_policies,
    set_current_employee,
)
from backend.app.auth.security import authenticate_employee, create_access_token, decode_access_token
from backend.app.db.models import get_session_factory
from backend.app.db.seed import seed


def main() -> None:
    seed(force=True)

    Session = get_session_factory()
    with Session() as session:
        emp = authenticate_employee(session, "alice.nguyen@12icorp.example", "Password@123")
        assert emp is not None, "login failed"
        token = create_access_token({"sub": emp.email, "employee_id": emp.employee_id})
        payload = decode_access_token(token)
        assert payload and payload["employee_id"] == "E1001"
        print("OK auth:", emp.full_name)

    hits = get_retriever().search("maternity leave entitlement", k=3)
    assert hits, "policy retrieval returned nothing"
    print("OK rag:", hits[0]["source"], "|", hits[0]["title"][:60])

    set_current_employee("E1001")
    bal = get_leave_balance.invoke({"leave_type": "ALL"})
    elig = check_leave_eligibility.invoke({"leave_type": "PL"})
    calc = calculate_leave_days.invoke(
        {"start_date": "2026-10-20", "end_date": "2026-10-24", "leave_type": "PL", "half_day": False}
    )
    policy = search_hr_policies.invoke({"query": "hybrid work office days"})
    result = run_hr_agent(
        "I took 2 days leave this month & shall I take one more sick leave on this month"
    )
    set_current_employee(None)

    print("OK leave balance tool chars:", len(bal))
    print("OK eligibility tool chars:", len(elig))
    print("OK calculate tool chars:", len(calc))
    print("OK policy tool chars:", len(policy))
    print("OK scenario:", result["answer"])
    assert "Yes" in result["answer"] or "No" in result["answer"]
    assert "```" not in result["answer"]
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
