"""
Main_program.py — CLI entry point for the 718 daily duty scheduler.

This is the command-line driver. The same logic is also exposed via the web
app (web_app.py); both share solver.py / ledger.py / store.py underneath.

USAGE
-----
    python Main_program.py

It pulls today's roster (active users, vacations, outings) from data/*.json
and prints the schedule. The web app is the recommended way to manage data.
"""

import datetime

import ledger
import store
from constants import work_group
from solver import (
    solve_day,
    feasibility_report,
    print_schedule,
    STATUS_ABSENT,
    STATUS_OUTING,
    STATUS_LONGNIGHT,
    STATUS_STRIKE,
)


# Set this to schedule a different day. Defaults to today.
TODAY = datetime.date.today()

# Optional: override if you want to set 긴밤자 manually for the day. The web
# app will eventually let you pick this from the UI.
LONG_NIGHT_NAMES: list[str] = []


def compute_today_group(d: datetime.date) -> int:
    """0=A, 1=B, 2=C. Anchored on 2020-01-01 = Group B."""
    rotation_start = datetime.date(2020, 1, 1)
    return ((d - rotation_start).days + 1) % 3


def build_statuses(d: datetime.date, active_users: list) -> dict:
    """Combine vacation + outing data from the store into a status dict."""
    vacation_ids = store.vacation_user_ids_on(d)
    outing_ids = store.outing_user_ids_on(d)
    active_by_id = {u.id: u for u in active_users}

    statuses: dict[str, str] = {}
    for uid in vacation_ids:
        u = active_by_id.get(uid)
        if u:
            statuses[u.name] = STATUS_ABSENT
    for uid in outing_ids:
        u = active_by_id.get(uid)
        if u:
            statuses[u.name] = STATUS_OUTING
    for name in LONG_NIGHT_NAMES:
        statuses[name] = STATUS_LONGNIGHT
    return statuses


def main() -> None:
    today_group = compute_today_group(TODAY)
    is_weekend = TODAY.weekday() >= 5

    active = store.active_users()
    statuses = build_statuses(TODAY, active)

    weekend_label = '주말' if is_weekend else '평일'
    print(f"Date  : {TODAY} ({work_group[today_group]}조, {weekend_label})")
    print(f"Active users: {len(active)}")
    absents = [n for n, s in statuses.items() if s == STATUS_ABSENT]
    outings = [n for n, s in statuses.items() if s == STATUS_OUTING]
    longnight = [n for n, s in statuses.items() if s == STATUS_LONGNIGHT]
    print(f"  Absent ({len(absents):>2}): {', '.join(absents) if absents else '(none)'}")
    print(f"  Outing ({len(outings):>2}): {', '.join(outings) if outings else '(none)'}")
    print(f"  긴밤   ({len(longnight):>2}): {', '.join(longnight) if longnight else '(none)'}")

    issues = feasibility_report(today_group, is_weekend, active, statuses)
    if issues:
        print("\nFeasibility warnings:")
        for issue in issues:
            print(f"  - {issue}")

    book = store.load_ledger()
    today_str = TODAY.isoformat()
    if book.get('last_date') == today_str:
        print(f"\n알림: 통계에 이미 {today_str} 기록이 있습니다. "
              f"재실행 시 중복 집계됩니다.")

    schedule = solve_day(
        today_group, is_weekend, active, statuses,
        work_count_before=ledger.work_count_for_solver(book, active),
    )
    if schedule is None:
        print("\nNo feasible schedule found. Adjust the roster and try again.")
        return

    print_schedule(schedule, today_group, is_weekend)

    # Persist the schedule and bump the ledger
    store.save_schedule(TODAY, work_group[today_group], is_weekend, schedule)
    # `candidates` = people who actually showed up for regular duty today.
    # `sf_users`   = strike-force standby (credited as work for fairness).
    away_today = {
        n for n, s in statuses.items()
        if s in (STATUS_ABSENT, STATUS_OUTING, STATUS_STRIKE)
    }
    candidates = [u for u in active if u.name not in away_today]
    sf_names = {n for n, s in statuses.items() if s == STATUS_STRIKE}
    sf_users = [u for u in active if u.name in sf_names]
    ledger.update(book, schedule, candidates, today_group, today_str, sf_users=sf_users)
    store.save_ledger(book)
    ledger.print_summary(book)


if __name__ == '__main__':
    main()
