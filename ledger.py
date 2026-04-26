"""
ledger.py — fairness business logic on top of store.load_ledger / save_ledger.

WHY THIS EXISTS
---------------
The solver runs ONE day at a time. "Fairness" only shows up across many days
("Alice and Bob worked the same total hours this month"). This module:

  - folds a day's schedule into the cumulative counters
  - exposes a fairness-aware work-count signal that the solver can use to
    bias today's choice toward people who are behind
  - prints a human-readable summary

PERSISTENCE LIVES IN store.py
-----------------------------
This file is pure logic. `store.load_ledger()` and `store.save_ledger()` do
the file I/O.

VACATION-NORMALISED FAIRNESS
----------------------------
The earlier ledger.py used raw cumulative counts. That was unfair to people
who took vacation: their `work_count` would lag, then they'd get hammered with
3-duty days the moment they came back to "catch up". We now also track
`available_days` per person — days where they were eligible to work — and the
solver uses a virtual count that scales work by the platoon mean rate. See
`work_count_for_solver()` below for the exact formula.

STRIKE-FORCE CREDIT
-------------------
Strike-force (타격대) members are on standby for the whole week, so they don't
appear on regular schedules. Without intervention their `work_count` would
stagnate, the fairness term would mark them as "behind" when they come off
duty, and they'd get hammered with extra slots — punishment for serving as SF.

Fix: every day we update the ledger, we ALSO credit each SF member with the
day's average slots-per-worker. To the fairness term, an SF day looks the same
as a normal duty day. People who serve SF stay roughly in line with peers.

The credit is stored in a SEPARATE field (`sf_credit_slots`) — NOT in
`work_count`. This way:
  - `work_count` stays a clean record of real, actual slots worked.
  - The preference-match RATE (matches / work_count) is computed on real work
    only, so SF time doesn't drag the rate down (you can't match preferences
    on a day you didn't actually work).
  - The fairness signal still uses BOTH (combined for the virtual count), so
    SF members aren't punished as "behind".
"""

from typing import Dict, List, Tuple

from constants import Timetable, work_group
from store import User, load_ledger, save_ledger


def work_count_for_solver(ledger: dict, users: List[User]) -> Dict[str, int]:
    """
    Convert raw counters into a vacation-normalised "virtual work count" the
    solver can balance.

    The fairness signal uses COMBINED counts: real work + SF credit slots.
    This is the key to keeping SF members from being punished — their combined
    count (which includes the credit) is comparable to peers, so the spread
    term doesn't single them out as "behind".

    Formula (multiplied through by total_avail to keep everything integer):
        virtual[name] = combined[name] * total_avail
                        - total_combined * available_days[name]
    where:
        combined[name]   = work_count[name] + sf_credit_slots[name]
        total_combined   = sum of combined across all users
        total_avail      = sum of available_days across all users

    Interpretation:
      - virtual > 0 → person is ABOVE their fair share (combined)
      - virtual < 0 → person is BELOW their fair share
      - virtual ≈ 0 → dead even
    """
    sf_credit = ledger.get('sf_credit_slots', {})

    def combined_for(name: str) -> int:
        return (
            ledger['work_count'].get(name, 0)
            + sf_credit.get(name, 0)
        )

    total_combined = sum(combined_for(u.name) for u in users)
    total_avail = sum(ledger['available_days'].get(u.name, 0) for u in users)

    if total_avail == 0:
        # First day ever — no history. Return zeros so the solver has something
        # to balance, but the spread term will be trivial.
        return {u.name: 0 for u in users}

    return {
        u.name: (
            combined_for(u.name) * total_avail
            - total_combined * ledger['available_days'].get(u.name, 0)
        )
        for u in users
    }


def update(
    ledger: dict,
    schedule: Dict[str, List[Tuple[int, int]]],
    candidate_users: List[User],
    today_group: int,
    date_str: str,
    sf_users: List[User] = None,
) -> None:
    """
    Fold today's schedule into the ledger's counters. Mutates `ledger` in place;
    call store.save_ledger() afterwards to persist.

    `schedule`         — what solver.solve_day() returned
    `candidate_users`  — every user who was on regular duty today (active,
                         not on vacation/outing/strike). Their available_days
                         is bumped by 1, work_count by their actual slot count.
    `today_group`      — 0/1/2 for A/B/C; needed for preference lookup
    `date_str`         — ISO date string, stored in 'last_date'
    `sf_users`         — users on strike-force standby today. Bumped same as
                         candidates BUT credited with the day's average slots
                         instead of zero, so they don't fall behind in
                         fairness while serving SF.

    The 'sf_credit_days' counter (per-user) is incremented separately so the
    UI can show how many SF days have been credited.
    """
    times = Timetable[today_group][0]
    group_letter = work_group[today_group]

    # First pass: real workers. Their actual slots set the day's "average"
    # which we'll use to credit SF members.
    for user in candidate_users:
        ledger['available_days'][user.name] = (
            ledger['available_days'].get(user.name, 0) + 1
        )
        slots = schedule.get(user.name, [])
        ledger['work_count'][user.name] = (
            ledger['work_count'].get(user.name, 0) + len(slots)
        )
        prefs = user.preferences.get(group_letter)
        if prefs is None or not slots:
            continue
        preferred = set(prefs.times3) | set(prefs.times2)
        matches = sum(1 for (slot_idx, _site_idx) in slots if times[slot_idx] in preferred)
        ledger['pref_match_count'][user.name] = (
            ledger['pref_match_count'].get(user.name, 0) + matches
        )

    # Second pass: strike-force credit.
    # Average slots per ACTUAL working candidate today. Stored as integer in
    # the ledger (CP-SAT solver requires integers downstream). Long-run average
    # comes out roughly fair; week-to-week variance ≤ 1 slot.
    if sf_users:
        actual_workers = [u for u in candidate_users if schedule.get(u.name)]
        if actual_workers:
            total_slots_today = sum(
                len(schedule.get(u.name, [])) for u in actual_workers
            )
            sf_credit = round(total_slots_today / len(actual_workers))
        else:
            sf_credit = 2
        sf_credit = max(1, sf_credit)  # never credit below 1

        sf_credit_slots = ledger.setdefault('sf_credit_slots', {})
        for user in sf_users:
            ledger['available_days'][user.name] = (
                ledger['available_days'].get(user.name, 0) + 1
            )
            # NOTE: SF credit goes into its OWN field, NOT into work_count.
            # This keeps `work_count` a clean record of REAL slots worked, so
            # the preference-match rate (matches / work_count) doesn't get
            # diluted by SF days where no actual matching could happen.
            sf_credit_slots[user.name] = (
                sf_credit_slots.get(user.name, 0) + sf_credit
            )

    ledger['last_date'] = date_str
    ledger['days_recorded'] = ledger.get('days_recorded', 0) + 1
    recorded = ledger.setdefault('recorded_dates', [])
    if date_str not in recorded:
        recorded.append(date_str)


def print_summary(ledger: dict) -> None:
    """Show cumulative counts with utilisation rate ((work + sf_credit) / avail)."""
    days = ledger.get('days_recorded', 0)
    print(f"\n=== 누적 근무 통계 (총 {days}일 기록, 마지막: {ledger.get('last_date', 'never')}) ===")

    sf_credit = ledger.get('sf_credit_slots', {})
    rows = []
    for name, work in ledger['work_count'].items():
        sf = sf_credit.get(name, 0)
        avail = ledger['available_days'].get(name, 0)
        matches = ledger['pref_match_count'].get(name, 0)
        # Utilization includes SF credit (matches the fairness signal).
        rate = (work + sf) / avail if avail > 0 else 0.0
        rows.append((name, work, sf, avail, matches, rate))
    rows.sort(key=lambda r: -r[5])  # by utilisation descending

    if rows:
        rates = [r[5] for r in rows if r[3] > 0]
        if rates:
            print(f"  활용률 분포: 최대 {max(rates):.2f}, 최소 {min(rates):.2f}, "
                  f"차이 {max(rates) - min(rates):.2f} (slots/day)\n")

    print(f"  {'name':<8} {'실근무':>5} {'타크레딧':>7} {'가용일':>6} "
          f"{'활용률':>7} {'선호일치':>8} {'일치율':>6}")
    for name, work, sf, avail, matches, rate in rows:
        rate_str = f"{rate:.2f}" if avail > 0 else '—'
        # Match rate uses REAL work only, not SF credit (since SF days have no
        # slots to match against).
        match_rate = f"{matches / work * 100:.0f}%" if work > 0 else '—'
        print(f"  {name:<8} {work:>5} {sf:>7} {avail:>6} "
              f"{rate_str:>7} {matches:>8} {match_rate:>6}")
