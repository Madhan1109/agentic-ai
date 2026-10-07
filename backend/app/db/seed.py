"""Seed demo employees, leave, holidays, blackouts for the HR Chat Agent."""

from datetime import date
from pathlib import Path

from passlib.context import CryptContext

from backend.app.config import get_settings
from backend.app.db.models import (
    Base,
    BlackoutPeriod,
    Employee,
    EscalationTicket,
    Holiday,
    LeaveBalance,
    LeaveRequest,
    get_engine,
    get_session_factory,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEMO_PASSWORD = "Password@123"

EMPLOYEES = [
    {
        "employee_id": "E1001",
        "email": "alice.nguyen@i2icorp.example",
        "full_name": "Alice Nguyen",
        "department": "Engineering",
        "employment_type": "full-time",
        "role_title": "Senior Software Engineer",
        "manager_email": "priya.sharma@i2icorp.example",
        "join_date": date(2022, 3, 15),
        "location": "Austin, TX",
        "balances": [
            {"leave_type": "PL", "entitled": 18, "used": 6, "pending": 2, "carried_forward": 2},
            {"leave_type": "SL", "entitled": 12, "used": 1, "pending": 0, "carried_forward": 0},
            {"leave_type": "CL", "entitled": 6, "used": 2, "pending": 0, "carried_forward": 0},
        ],
        "requests": [
            {
                "leave_type": "PL",
                "start_date": date(2026, 10, 20),
                "end_date": date(2026, 10, 21),
                "days": 2,
                "status": "pending",
                "reason": "Family event",
            }
        ],
    },
    {
        "employee_id": "E1002",
        "email": "bob.martinez@i2icorp.example",
        "full_name": "Bob Martinez",
        "department": "People Operations",
        "employment_type": "full-time",
        "role_title": "HR Business Partner",
        "manager_email": "chen.wei@i2icorp.example",
        "join_date": date(2020, 7, 1),
        "location": "Chicago, IL",
        "balances": [
            {"leave_type": "PL", "entitled": 18, "used": 10, "pending": 0, "carried_forward": 5},
            {"leave_type": "SL", "entitled": 12, "used": 3, "pending": 0, "carried_forward": 0},
            {"leave_type": "CL", "entitled": 6, "used": 1, "pending": 1, "carried_forward": 0},
        ],
        "requests": [],
    },
    {
        "employee_id": "E1003",
        "email": "cara.lee@i2icorp.example",
        "full_name": "Cara Lee",
        "department": "Marketing",
        "employment_type": "full-time",
        "role_title": "Marketing Specialist",
        "manager_email": "dana.kim@i2icorp.example",
        "join_date": date(2026, 8, 1),
        "location": "New York, NY",
        "balances": [
            {"leave_type": "PL", "entitled": 7.5, "used": 0, "pending": 0, "carried_forward": 0},
            {"leave_type": "SL", "entitled": 5, "used": 0, "pending": 0, "carried_forward": 0},
            {"leave_type": "CL", "entitled": 2.5, "used": 0, "pending": 0, "carried_forward": 0},
        ],
        "requests": [],
    },
    {
        "employee_id": "E2001",
        "email": "devon.contractor@i2icorp.example",
        "full_name": "Devon Brooks",
        "department": "Engineering",
        "employment_type": "contractor",
        "role_title": "Contract Developer",
        "manager_email": "priya.sharma@i2icorp.example",
        "join_date": date(2025, 11, 1),
        "location": "Remote",
        "balances": [],
        "requests": [],
    },
]

HOLIDAYS_2026 = [
    ("New Year's Day", date(2026, 1, 1)),
    ("Martin Luther King Jr. Day", date(2026, 1, 19)),
    ("Presidents' Day", date(2026, 2, 16)),
    ("Memorial Day", date(2026, 5, 25)),
    ("Juneteenth", date(2026, 6, 19)),
    ("Independence Day", date(2026, 7, 3)),
    ("Labor Day", date(2026, 9, 7)),
    ("Thanksgiving", date(2026, 11, 26)),
    ("Day after Thanksgiving", date(2026, 11, 27)),
    ("Christmas Eve", date(2026, 12, 24)),
    ("Christmas Day", date(2026, 12, 25)),
    ("Diwali (observed)", date(2026, 11, 8)),
]

BLACKOUTS = [
    {
        "name": "Year-end close",
        "start_date": date(2026, 12, 15),
        "end_date": date(2026, 12, 31),
        "department": "ALL",
        "reason": "Finance and delivery blackout; PL restricted unless Director approves.",
    },
    {
        "name": "Major release freeze",
        "start_date": date(2026, 10, 27),
        "end_date": date(2026, 11, 7),
        "department": "Engineering",
        "reason": "Product release window; Engineering PL needs Director exception.",
    },
]


def seed(force: bool = False) -> None:
    settings = get_settings()
    db_path = settings.database_url.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    engine = get_engine()
    if force:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    Session = get_session_factory()
    with Session() as session:
        existing = session.query(Employee).count()
        if existing and not force:
            print(f"Database already seeded ({existing} employees). Use --force to reseed.")
            return

        if force:
            session.query(EscalationTicket).delete()
            session.query(BlackoutPeriod).delete()
            session.query(Holiday).delete()
            session.query(LeaveRequest).delete()
            session.query(LeaveBalance).delete()
            session.query(Employee).delete()
            session.commit()

        password_hash = pwd_context.hash(DEMO_PASSWORD)
        year = date.today().year

        for row in EMPLOYEES:
            emp = Employee(
                employee_id=row["employee_id"],
                email=row["email"],
                full_name=row["full_name"],
                password_hash=password_hash,
                department=row["department"],
                employment_type=row["employment_type"],
                role_title=row["role_title"],
                manager_email=row["manager_email"],
                join_date=row["join_date"],
                location=row["location"],
            )
            session.add(emp)
            session.flush()

            for bal in row["balances"]:
                session.add(
                    LeaveBalance(
                        employee_pk=emp.id,
                        year=year,
                        leave_type=bal["leave_type"],
                        entitled=bal["entitled"],
                        used=bal["used"],
                        pending=bal["pending"],
                        carried_forward=bal["carried_forward"],
                    )
                )

            for req in row["requests"]:
                session.add(
                    LeaveRequest(
                        employee_pk=emp.id,
                        leave_type=req["leave_type"],
                        start_date=req["start_date"],
                        end_date=req["end_date"],
                        days=req["days"],
                        status=req["status"],
                        reason=req["reason"],
                    )
                )

        for name, d in HOLIDAYS_2026:
            session.add(Holiday(name=name, holiday_date=d, year=d.year, region="US"))

        for bo in BLACKOUTS:
            session.add(BlackoutPeriod(**bo))

        session.commit()
        print("Seeded demo employees:")
        for row in EMPLOYEES:
            print(f"  - {row['email']} / {DEMO_PASSWORD} ({row['employee_id']})")
        print(f"Seeded {len(HOLIDAYS_2026)} holidays and {len(BLACKOUTS)} blackout periods.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    seed(force=args.force)
