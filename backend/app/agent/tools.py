"""Agent tools: policy search, leave balance, eligibility, leave day calculation."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Annotated

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from backend.app.agent.rag import format_policy_context, get_retriever
from backend.app.db.models import Employee, LeaveBalance, LeaveRequest, get_session_factory

# Set per-request by the API layer so tools only access the authenticated employee.
CURRENT_EMPLOYEE_ID: str | None = None


def set_current_employee(employee_id: str | None) -> None:
    global CURRENT_EMPLOYEE_ID
    CURRENT_EMPLOYEE_ID = employee_id


def _session() -> Session:
    return get_session_factory()()


def _require_employee(session: Session) -> Employee:
    if not CURRENT_EMPLOYEE_ID:
        raise ValueError("No authenticated employee context.")
    emp = session.query(Employee).filter(Employee.employee_id == CURRENT_EMPLOYEE_ID).first()
    if not emp:
        raise ValueError("Employee not found.")
    return emp


def _working_days(start: date, end: date) -> float:
    if end < start:
        raise ValueError("end_date must be on or after start_date")
    days = 0
    cur = start
    while cur <= end:
        if cur.weekday() < 5:  # Mon-Fri
            days += 1
        cur += timedelta(days=1)
    return float(days)


@tool
def search_hr_policies(query: Annotated[str, "Natural language HR policy question or keywords"]) -> str:
    """Search company HR policy documents (leave, remote work, benefits, code of conduct) and return relevant excerpts."""
    hits = get_retriever().search(query, k=4)
    return format_policy_context(hits)


@tool
def get_employee_profile() -> str:
    """Return the authenticated employee's profile details from the HR database."""
    with _session() as session:
        emp = _require_employee(session)
        tenure_days = (date.today() - emp.join_date).days
        payload = {
            "employee_id": emp.employee_id,
            "full_name": emp.full_name,
            "email": emp.email,
            "department": emp.department,
            "role_title": emp.role_title,
            "employment_type": emp.employment_type,
            "manager_email": emp.manager_email,
            "join_date": emp.join_date.isoformat(),
            "tenure_days": tenure_days,
            "location": emp.location,
        }
        return json.dumps(payload, indent=2)


@tool
def get_leave_balance(
    leave_type: Annotated[str, "Optional leave type filter: PL, SL, CL, or ALL"] = "ALL",
) -> str:
    """Fetch the authenticated employee's current leave balances from the HR database."""
    with _session() as session:
        emp = _require_employee(session)
        year = date.today().year
        q = session.query(LeaveBalance).filter(LeaveBalance.employee_pk == emp.id, LeaveBalance.year == year)
        lt = leave_type.upper().strip()
        if lt and lt != "ALL":
            q = q.filter(LeaveBalance.leave_type == lt)
        rows = q.all()
        if not rows:
            return json.dumps(
                {
                    "employee_id": emp.employee_id,
                    "message": "No leave balances found. Contractors typically have no leave entitlements.",
                    "employment_type": emp.employment_type,
                    "balances": [],
                },
                indent=2,
            )
        balances = [
            {
                "leave_type": r.leave_type,
                "year": r.year,
                "entitled": r.entitled,
                "carried_forward": r.carried_forward,
                "used": r.used,
                "pending": r.pending,
                "available": r.available,
            }
            for r in rows
        ]
        return json.dumps({"employee_id": emp.employee_id, "balances": balances}, indent=2)


@tool
def check_leave_eligibility(
    leave_type: Annotated[str, "Leave type: PL, SL, CL, MATERNITY, PATERNITY, COMP_OFF"],
) -> str:
    """Evaluate leave eligibility for the authenticated employee using policy rules + HR profile data."""
    lt = leave_type.upper().strip()
    with _session() as session:
        emp = _require_employee(session)
        tenure_days = (date.today() - emp.join_date).days
        reasons: list[str] = []
        eligible = True

        if emp.employment_type == "contractor":
            eligible = False
            reasons.append("Contractors are not eligible for company leave entitlements under HR-POL-LEAVE-2025.")
        elif lt in {"PL", "CL"} and tenure_days < 90:
            eligible = False
            reasons.append(
                f"Employee is in probation ({tenure_days} days served). "
                "PL/CL generally require 90 days continuous service before first use."
            )
        elif lt in {"MATERNITY", "PATERNITY"} and tenure_days < 180:
            eligible = False
            reasons.append(
                f"Maternity/Paternity leave requires 6 months continuous service. Current tenure: {tenure_days} days."
            )
        elif lt == "SL" and emp.employment_type == "full-time":
            reasons.append("Full-time employees are eligible for Sick Leave. Medical certificate needed for 3+ consecutive days.")
        elif lt in {"PL", "CL", "SL"} and emp.employment_type == "full-time" and tenure_days >= 90:
            reasons.append(f"Eligible for {lt} based on employment type and tenure.")
        elif lt == "COMP_OFF":
            reasons.append("Comp-Off requires prior manager approval of weekend/holiday work and must be used within 60 days.")
        else:
            if eligible:
                reasons.append("Eligibility evaluated from available policy rules; confirm with HRBP for edge cases.")

        # Attach available balance if present
        bal = (
            session.query(LeaveBalance)
            .filter(
                LeaveBalance.employee_pk == emp.id,
                LeaveBalance.year == date.today().year,
                LeaveBalance.leave_type == lt,
            )
            .first()
        )
        available = bal.available if bal else None

        return json.dumps(
            {
                "employee_id": emp.employee_id,
                "leave_type": lt,
                "eligible": eligible,
                "available_balance": available,
                "tenure_days": tenure_days,
                "employment_type": emp.employment_type,
                "reasons": reasons,
            },
            indent=2,
        )


@tool
def calculate_leave_days(
    start_date: Annotated[str, "Start date YYYY-MM-DD"],
    end_date: Annotated[str, "End date YYYY-MM-DD"],
    leave_type: Annotated[str, "Leave type: PL, SL, or CL"] = "PL",
    half_day: Annotated[bool, "Whether this is a half-day request"] = False,
) -> str:
    """Calculate working days to deduct for a leave request (excludes weekends) and compare with available balance."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as exc:
        return json.dumps({"error": f"Invalid date format: {exc}. Use YYYY-MM-DD."})

    days = 0.5 if half_day else _working_days(start, end)
    with _session() as session:
        emp = _require_employee(session)
        bal = (
            session.query(LeaveBalance)
            .filter(
                LeaveBalance.employee_pk == emp.id,
                LeaveBalance.year == date.today().year,
                LeaveBalance.leave_type == leave_type.upper(),
            )
            .first()
        )
        available = bal.available if bal else 0.0
        sufficient = available >= days if bal else False
        return json.dumps(
            {
                "employee_id": emp.employee_id,
                "leave_type": leave_type.upper(),
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "half_day": half_day,
                "working_days_to_deduct": days,
                "available_balance": available,
                "sufficient_balance": sufficient,
                "note": "Weekends excluded per leave policy. Public holidays are not deducted when they fall in the range (demo calculator uses weekends only).",
            },
            indent=2,
        )


@tool
def get_recent_leave_requests(
    limit: Annotated[int, "Max number of recent requests to return"] = 5,
) -> str:
    """List the authenticated employee's recent leave requests and their statuses."""
    with _session() as session:
        emp = _require_employee(session)
        rows = (
            session.query(LeaveRequest)
            .filter(LeaveRequest.employee_pk == emp.id)
            .order_by(LeaveRequest.created_at.desc())
            .limit(max(1, min(limit, 20)))
            .all()
        )
        payload = [
            {
                "leave_type": r.leave_type,
                "start_date": r.start_date.isoformat(),
                "end_date": r.end_date.isoformat(),
                "days": r.days,
                "status": r.status,
                "reason": r.reason,
            }
            for r in rows
        ]
        return json.dumps({"employee_id": emp.employee_id, "requests": payload}, indent=2)


HR_TOOLS = [
    search_hr_policies,
    get_employee_profile,
    get_leave_balance,
    check_leave_eligibility,
    calculate_leave_days,
    get_recent_leave_requests,
]
