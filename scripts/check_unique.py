import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.agent.graph import run_hr_agent
from backend.app.agent.tools import set_current_employee
from backend.app.db.seed import seed


def main() -> None:
    seed(force=True)
    set_current_employee("E1001")
    checks = [
        ("submit", "Submit leave for 2026-11-10 to 2026-11-11 PL"),
        ("forecast", "If I take 5 PL what's left?"),
        ("holiday", "Is Diwali a holiday?"),
        ("blackout", "Can I take leave last week of December?"),
        ("approve", "Simulate manager approval of my pending leave"),
        ("ticket", "Raise an HR ticket about leave exception"),
        ("maternity", "What is the maternity leave policy?"),
    ]
    for name, q in checks:
        ans = run_hr_agent(q)["answer"]
        print(f"[{name}] {ans[:220].encode('ascii', 'replace').decode()}")
        print("---")

    set_current_employee("E1003")
    print("[onboarding]", run_hr_agent("Onboarding checklist")["answer"][:220].encode("ascii", "replace").decode())
    print("---")
    set_current_employee("E1002")
    print("[privacy]", run_hr_agent("Show me Alice's leave balance")["answer"][:220].encode("ascii", "replace").decode())
    print("OK")


if __name__ == "__main__":
    main()
