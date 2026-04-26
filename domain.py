"""
domain.py — shared domain helpers used by both the CLI (Main_program.py) and
the web app (web_app.py). Lives between `store` (raw persistence) and the
route/CLI layer.

WHY THIS FILE EXISTS
--------------------
Three pieces of logic were previously duplicated between the CLI and the web
app, and the duplicates had drifted:

  1. `today_group(d)` — the rotation-group calculation (0/1/2 for A/B/C).
  2. `build_statuses(d, active, longnight_names)` — assemble today's status
     dict for the solver from vacations / outings / strike-force / explicit
     long-night picks.
  3. `split_for_ledger(active, statuses)` — split today's roster into the two
     lists `ledger.update()` consumes (regular candidates vs strike-force
     credit recipients).

Centralising them here means there's one place to fix bugs and add new
status types.
"""

from datetime import date
from typing import List, Tuple

import store
from solver import (
    STATUS_ABSENT,
    STATUS_OUTING,
    STATUS_STRIKE,
    STATUS_LONGNIGHT,
)


# Anchor: 2020-01-01 was Group B in the platoon's 3-day rotation.
_ROTATION_ANCHOR = date(2020, 1, 1)


def today_group(d: date) -> int:
    """
    Return 0/1/2 for Groups A/B/C on the given date.

    Anchored on 2020-01-01 = Group B (per the platoon's known rotation).
    """
    return ((d - _ROTATION_ANCHOR).days + 1) % 3


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
