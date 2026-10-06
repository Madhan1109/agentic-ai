"""Seed demo employees and leave balances for the HR Chat Agent."""

from datetime import date
from pathlib import Path

from passlib.context import CryptContext

from backend.app.config import get_settings
from backend.app.db.models import Base, Employee, LeaveBalance, LeaveRequest, get_engine, get_session_factory

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEMO_PASSWORD = "Password@123"

EMPLOYEES = [
    {
        "employee_id": "E1001",
        "email": "alice.nguyen@12icorp.example",
        "full_name": "Alice Nguyen",
        "department": "Engineering",
        "employment_type": "full-time",
        "role_title": "Senior Software Engineer",
        "manager_email": "priya.sharma@12icorp.example",
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
        "email": "bob.martinez@12icorp.example",
        "full_name": "Bob Martinez",
        "department": "People Operations",
        "employment_type": "full-time",
        "role_title": "HR Business Partner",
        "manager_email": "chen.wei@12icorp.example",
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
        "email": "cara.lee@12icorp.example",
        "full_name": "Cara Lee",
        "department": "Marketing",
        "employment_type": "full-time",
        "role_title": "Marketing Specialist",
        "manager_email": "dana.kim@12icorp.example",
        "join_date": date(2026, 8, 1),  # still in probation as of assessment date context
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
        "email": "devon.contractor@12icorp.example",
        "full_name": "Devon Brooks",
        "department": "Engineering",
        "employment_type": "contractor",
        "role_title": "Contract Developer",
        "manager_email": "priya.sharma@12icorp.example",
        "join_date": date(2025, 11, 1),
        "location": "Remote",
        "balances": [],
        "requests": [],
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

        session.commit()
        print("Seeded demo employees:")
        for row in EMPLOYEES:
            print(f"  - {row['email']} / {DEMO_PASSWORD} ({row['employee_id']})")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    seed(force=args.force)
