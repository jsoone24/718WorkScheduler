"""
Main_program.py — CLI entry point for the 718 daily duty scheduler.

This is the command-line driver. The same logic is also exposed via the web
app (web_app.py); both share solver.py / ledger.py / store.py underneath via
the small helper module domain.py.

USAGE
-----
    python Main_program.py

It pulls today's roster (active users, vacations, outings, strike-force) from
data/*.json and prints the schedule. The web app is the recommended way to
manage data; this CLI exists for quick smoke checks and for users who prefer
the terminal.
"""

import datetime

import domain
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

# Optional: explicitly mark some active users as 긴밤자 (long-night) for the
# day. Useful for the CLI flow only — the web app does not surface this yet.
# Names must match `User.name` exactly. Only meaningful in Group B.
LONG_NIGHT_NAMES: set[str] = set()


def main() -> None:
    today_group = domain.today_group(TODAY)
    is_weekend = TODAY.weekday() >= 5

    active = store.active_users()
    statuses = domain.build_statuses(TODAY, active, longnight_names=LONG_NIGHT_NAMES)

    weekend_label = '주말' if is_weekend else '평일'
    print(f"Date  : {TODAY} ({work_group[today_group]}조, {weekend_label})")
    print(f"Active users: {len(active)}")
    absents = [n for n, s in statuses.items() if s == STATUS_ABSENT]
    outings = [n for n, s in statuses.items() if s == STATUS_OUTING]
    strike = [n for n, s in statuses.items() if s == STATUS_STRIKE]
    longnight = [n for n, s in statuses.items() if s == STATUS_LONGNIGHT]
    print(f"  사고/휴가 ({len(absents):>2}): {', '.join(absents) if absents else '(none)'}")
    print(f"  외출      ({len(outings):>2}): {', '.join(outings) if outings else '(none)'}")
    print(f"  타격대    ({len(strike):>2}): {', '.join(strike) if strike else '(none)'}")
    print(f"  긴밤      ({len(longnight):>2}): {', '.join(longnight) if longnight else '(none)'}")

    issues = feasibility_report(today_group, is_weekend, active, statuses)
    if issues:
        print("\nFeasibility warnings:")
        for issue in issues:
            print(f"  - {issue}")

    book = store.load_ledger()
    today_str = TODAY.isoformat()
    if today_str in book.get('recorded_dates', []):
        print(f"\n알림: 통계에 이미 {today_str} 기록이 있습니다. "
              f"재실행 시 중복 집계되지 않으며, 같은 결과가 표시됩니다.")

    schedule = solve_day(
        today_group, is_weekend, active, statuses,
        work_count_before=ledger.work_count_for_solver(book, active),
    )
    if schedule is None:
        print("\n실현 가능한 근무표가 없습니다. 휴가/외출/타격대 인원을 조정해 주세요.")
        return

    print_schedule(schedule, today_group, is_weekend)

    # Persist the schedule and bump the ledger (idempotent on the same date
    # via `recorded_dates` inside ledger.update).
    store.save_schedule(TODAY, work_group[today_group], is_weekend, schedule)
    candidates, sf_users = domain.split_for_ledger(active, statuses)
    ledger.update(
        book, schedule, candidates, today_group, today_str, sf_users=sf_users,
    )
    store.save_ledger(book)
    ledger.print_summary(book)


if __name__ == '__main__':
    main()
