"""
domain.py — shared helpers used by web_app.py, Main_program.py, and the two
weekly auto-planners. Lives between `store` (raw persistence) and the
route/CLI layer.

The helpers fall into three groups:
  - Calendar helpers (today_group, is_weekend, monday_of, require_monday)
  - Capacity/preference helpers (place_for)
  - Schedule helpers (build_statuses, split_for_ledger, invert_schedule,
    generate_and_persist)

generate_and_persist() is the big one — it bundles the "solve + save +
update ledger (idempotent)" sequence that used to be duplicated four times
across the route and CLI layer.
"""

from datetime import date, timedelta
from typing import List, Optional, Tuple

import ledger as _ledger
import store
from constants import placetable, work_group
from solver import (
    solve_day,
    STATUS_ABSENT,
    STATUS_OUTING,
    STATUS_STRIKE,
    STATUS_LONGNIGHT,
)


# Anchor: 2020-01-01 was Group B in the platoon's 3-day rotation.
_ROTATION_ANCHOR = date(2020, 1, 1)


# ---------------------------------------------------------------------------
# Calendar helpers
# ---------------------------------------------------------------------------

def today_group(d: date) -> int:
    """
    Return 0/1/2 for Groups A/B/C on the given date.

    Anchored on 2020-01-01 = Group B (per the platoon's known rotation).
    """
    return ((d - _ROTATION_ANCHOR).days + 1) % 3


def is_weekend(d: date) -> bool:
    """True on Saturday or Sunday. Mon=0 .. Sun=6."""
    return d.weekday() >= 5


def monday_of(d: date) -> date:
    """The Monday on or before `d` (so `monday_of(any_day_in_week) == that_week's_Mon`)."""
    return d - timedelta(days=d.weekday())


def require_monday(d: date) -> None:
    """Raise ValueError if `d` is not a Monday. Routes wrap this in HTTP 400."""
    if d.weekday() != 0:
        raise ValueError(f"월요일이어야 합니다 — 받은 값: {d.isoformat()}")


# ---------------------------------------------------------------------------
# Capacity helpers
# ---------------------------------------------------------------------------

def place_for(group: int, weekend: bool) -> list[list[int]]:
    """Today's 4×4 capacity matrix `place[slot][site]` for the given group."""
    return placetable[group][1 if weekend else 0]


def build_statuses(
    d: date,
    active: List[store.User],
    longnight_names: set[str] | None = None,
) -> dict[str, str]:
    """
    Assemble today's status dict (name -> status code) for `solver.solve_day`.

    Sources:
      - vacations on `d`     -> STATUS_ABSENT
      - outings on `d`       -> STATUS_OUTING
      - strike-force on `d`  -> STATUS_STRIKE
      - explicit names list  -> STATUS_LONGNIGHT  (only meaningful in Group B)

    Names not present in `active` (e.g. inactive or unknown users) are skipped
    silently; the solver layer will raise `ValueError` if `longnight_names`
    contains an unknown name.
    """
    longnight_names = longnight_names or set()
    by_id = {u.id: u for u in active}
    statuses: dict[str, str] = {}

    for uid in store.vacation_user_ids_on(d):
        u = by_id.get(uid)
        if u:
            statuses[u.name] = STATUS_ABSENT
    for uid in store.outing_user_ids_on(d):
        u = by_id.get(uid)
        if u:
            statuses[u.name] = STATUS_OUTING
    for uid in store.strikeforce_user_ids_on(d):
        u = by_id.get(uid)
        if u:
            statuses[u.name] = STATUS_STRIKE
    for name in longnight_names:
        statuses[name] = STATUS_LONGNIGHT
    return statuses


# ---------------------------------------------------------------------------
# Schedule helpers
# ---------------------------------------------------------------------------

def invert_schedule(
    assignments: dict[str, list],
) -> Tuple[dict[Tuple[int, int], list[str]], list[Tuple[str, list]]]:
    """
    Re-shape a `solve_day` result for display.

    Returns:
      by_slot_site: {(slot_idx, site_idx): [name, ...]} — for the slot grid
      per_person:   [(name, slots), ...] sorted by busiest first — for the
                    per-person summary table.
    """
    by_slot_site: dict[Tuple[int, int], list[str]] = {
        (s, l): [] for s in range(4) for l in range(4)
    }
    for name, slots in assignments.items():
        for s, l in slots:
            by_slot_site[(s, l)].append(name)
    per_person = sorted(assignments.items(), key=lambda kv: -len(kv[1]))
    return by_slot_site, per_person


def generate_and_persist(
    d: date,
    active: List[store.User],
    longnight_names: set[str] | None = None,
    book: dict | None = None,
) -> Optional[dict]:
    """
    Run `solve_day` for `d`, persist the schedule, fold the result into the
    ledger (idempotently), and return the resulting schedule dict.

    Idempotency contract: if `d.isoformat()` is already in
    `book['recorded_dates']`, the schedule is still saved (overwriting any
    prior version) but the ledger is NOT bumped a second time. So calling
    this twice for the same date counts as one ledger update.

    `book` is the loaded ledger (if the caller already has it for batch
    operations); we'll load + save it ourselves if not given. Returns the
    schedule on success, or `None` on infeasibility.
    """
    group = today_group(d)
    statuses = build_statuses(d, active, longnight_names=longnight_names)

    own_book = book is None
    if own_book:
        book = store.load_ledger()

    sched = solve_day(
        group, is_weekend(d), active, statuses,
        work_count_before=_ledger.work_count_for_solver(book, active),
    )
    if sched is None:
        return None

    store.save_schedule(d, work_group[group], is_weekend(d), sched)

    if d.isoformat() not in book.get('recorded_dates', []):
        candidates, sf_users = split_for_ledger(active, statuses)
        _ledger.update(book, sched, candidates, group, d.isoformat(), sf_users=sf_users)
        if own_book:
            store.save_ledger(book)
    return sched


def split_for_ledger(
    active: List[store.User],
    statuses: dict[str, str],
) -> Tuple[List[store.User], List[store.User]]:
    """
    Partition today's `active` roster for `ledger.update()`.

    Returns `(candidates, sf_users)` where:
      - `candidates`  = users on regular duty today (eligible for slot
        assignment + their actual slot count is folded into the ledger).
        Excludes ABSENT, OUTING, and STRIKE statuses.
      - `sf_users`    = users on strike-force standby today; the ledger
        credits them with the day's average slots so their fairness signal
        does not lag.
    """
    away = {
        n for n, s in statuses.items()
        if s in (STATUS_ABSENT, STATUS_OUTING, STATUS_STRIKE)
    }
    sf_names = {n for n, s in statuses.items() if s == STATUS_STRIKE}

    candidates = [u for u in active if u.name not in away]
    sf_users = [u for u in active if u.name in sf_names]
    return candidates, sf_users
