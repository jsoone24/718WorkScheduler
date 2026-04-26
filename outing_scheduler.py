"""
outing_scheduler.py — assigns who goes out on Sat / Sun (and weekday fallback).

THE PROBLEM
-----------
Officers get to "go out" (외출) periodically — typically a Saturday or Sunday,
sometimes a weekday if both weekend days fill up. The unit can spare some
people each day depending on how tight duty is.

USER'S RULES
------------
  1. Try to send EVERYONE out on weekends — outings are a perk, not a scarce
     resource. The cap is purely the day's feasibility floor.
  2. DISTRIBUTE outings across Sat AND Sun — don't dump everyone on Sat.
  3. If both weekend days have zero spare, push at least 1 outing to a weekday
     (so the week never goes by without someone getting out).
  4. Sat/Sun rotation: someone who went out last Sat is preferred for next Sun
     (and vice versa).
  5. Each person gets at most 1 outing per week.

ALGORITHM
---------
1. For each weekend day, compute the MAXIMUM number of outings — this is the
   feasibility floor: `available - ceil(demand / 4)` people can leave before
   the remaining duty crew can't cover (since each person works at most 4
   slots/day under the loosened solver). On a Group A weekend (demand 27),
   that's `21 - 7 = 14`; on Group B (demand 30), `21 - 8 = 13`.

2. Build a priority-sorted candidate pool: longest-since-last-outing first.

3. Iterate the pool, assigning each person to the best-available day:
     - If their last outing was Sat: prefer Sun this week (rotation).
     - If their last outing was Sun: prefer Sat.
     - Otherwise: pick the day with MORE remaining spare (balances Sat/Sun).
   Decrement that day's spare; once both hit zero, stop.

4. If after Sat+Sun nobody got an outing but pending requests exist, push 1
   onto the next-week weekday with available spare (the at-least-1 guarantee).

This is a simple greedy. The problem space is tiny (≤21 people, 2 weekend
days), so we don't need ILP/CP-SAT here — clarity beats cleverness.

TRADE-OFF
---------
With aggressive spare, weekend duty crews end up averaging 3–4 slots each
(since many people are out). This is intentional and matches the user's spec:
"if there are more or enough people, there can be people who can work 1 time
a day or just rest. or, if people are very tightened, may be they have to
work 4 times a day." Outings tighten things; the solver still keeps it valid.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Tuple

from constants import placetable
from domain import today_group, require_monday, is_weekend
from store import (
    User, Outing, active_users, load_outings, load_vacations, load_strikeforce,
    load_ledger, next_outing_id,
)


def _capacity_for(d: date) -> int:
    """Total person-slots demanded on date d (sum of all site capacities)."""
    cap = placetable[today_group(d)][1 if is_weekend(d) else 0]
    return sum(cap[s][l] for s in range(4) for l in range(4))


def _index_by_day(rows, dates: list[date], get_id, *, range_starts=None, range_ends=None,
                   single_date_attr=None) -> dict[date, set[int]]:
    """
    Helper: project a list of rows into {date: {user_id, ...}} for the given
    dates only. Caller picks the projection by passing either:
      - `single_date_attr`  — name of an ISO-string attribute compared by ==
                              (used for outings where each row has a fixed date)
      - `range_starts`/`range_ends` — names of two ISO-string attributes used
                              as inclusive [start, end] ranges (vacations + SF)

    Avoids re-loading the source file once per date.
    """
    out = {d: set() for d in dates}
    for row in rows:
        if single_date_attr is not None:
            iso = getattr(row, single_date_attr)
            for d in dates:
                if d.isoformat() == iso:
                    out[d].add(get_id(row))
        else:
            start = getattr(row, range_starts)
            end = getattr(row, range_ends)
            for d in dates:
                if start <= d.isoformat() <= end:
                    out[d].add(get_id(row))
    return out


def _max_outings_for(
    d: date,
    users: List[User],
    extra_busy: set,
    vac_by_day: dict,
    strike_by_day: dict,
    outings_by_day: dict,
) -> int:
    """
    How many people we can send out on day d, maximally.

    Using the FEASIBILITY bound, not the "comfortable" bound. Under the
    loosened solver rule (0–4 slots/person), the day is feasible as long as
    `remaining * 4 >= demand`, i.e. `remaining >= ceil(demand / 4)`. So:

        spare = available - ceil(demand / 4)

    INTENTIONALLY aggressive — the user's spec is "everyone should go out on
    weekends", so we send as many as possible, accepting that the remaining
    duty crew will average 3–4 slots/person on busy weekend days.

    The three `*_by_day` dicts are pre-built once per `plan_week` call (see
    that function's top), so this helper does no file I/O.
    """
    on_vac = vac_by_day.get(d, set())
    on_strike = strike_by_day.get(d, set())
    available = sum(
        1 for u in users
        if u.id not in on_vac and u.id not in on_strike and u.id not in extra_busy
    )
    min_remaining = (_capacity_for(d) + 3) // 4
    spare = available - min_remaining - len(outings_by_day.get(d, set()))
    return max(0, spare)


@dataclass
class OutingPlan:
    """One outing the planner wants to grant. Caller persists via store.save_outings()."""
    user_id: int
    user_name: str
    outing_date: date
    kind: str   # 'weekend_sat' | 'weekend_sun' | 'weekday'
    reason: str  # human-readable explanation


def _last_outing(ledger: dict, name: str) -> Optional[dict]:
    return ledger.get('last_outing', {}).get(name)


def _user_priority_key(user: User, ledger: dict) -> tuple:
    """
    Sort key for the candidate pool. Lower = higher priority.

    Two factors:
      1. How long ago was this person's last outing? (Older → higher priority.)
      2. Stable tiebreak by user.id so the order is deterministic when multiple
         people have identical history.
    """
    last = _last_outing(ledger, user.name)
    last_date = last.get('date', '0000-00-00') if last else '0000-00-00'
    return (last_date, user.id)


def _preferred_day_for(
    user: User, ledger: dict,
    sat_remaining: int, sun_remaining: int,
) -> Tuple[str, str]:
    """
    Choose Sat vs Sun for this user.

    Returns: (first_choice, second_choice) where each is 'sat' or 'sun'.
    The caller assigns to first_choice if it has spare, else second_choice.

    Rotation rule: someone who went Sat last week → prefer Sun this week,
    and vice versa. Otherwise: pick the day with MORE spare (balances totals).
    """
    last = _last_outing(ledger, user.name)
    last_kind = last.get('kind') if last else None

    if last_kind == 'weekend_sat':
        return ('sun', 'sat')
    if last_kind == 'weekend_sun':
        return ('sat', 'sun')

    # No prior weekend outing (or last was a weekday) — load-balance.
    if sat_remaining > sun_remaining:
        return ('sat', 'sun')
    if sun_remaining > sat_remaining:
        return ('sun', 'sat')
    # Equal — alphabetical-ish tiebreak by user id parity, just to vary
    return ('sat', 'sun') if user.id % 2 == 0 else ('sun', 'sat')


def plan_week(
    week_start: date,
    requesters: Optional[List[int]] = None,
) -> List[OutingPlan]:
    """
    Plan outings for the 7 days starting at `week_start` (a Monday).

    `requesters` — if given, only consider these user IDs. If None, every
    active user is fair game (the typical "rotate everyone" mode).

    Returns a list of OutingPlan items. Caller persists via plans_to_outings()
    + store.save_outings().
    """
    require_monday(week_start)

    users = active_users()
    ledger = load_ledger()
    candidate_ids = (
        set(requesters) if requesters is not None
        else {u.id for u in users}
    )

    saturday = week_start + timedelta(days=5)
    sunday = week_start + timedelta(days=6)
    weekday_dates = [week_start + timedelta(days=offset) for offset in range(7, 12)]
    all_dates = [saturday, sunday] + weekday_dates

    # Hoist ALL store reads out of the per-day inner loops. Each load_*() is
    # a JSON file read; without this, _max_outings_for did 3 reads per call,
    # called up to 7 times — 21 file reads per plan_week. Now: 3.
    all_vacations = load_vacations()
    all_outings = load_outings()
    all_strikes = load_strikeforce()

    vac_by_day = _index_by_day(
        all_vacations, all_dates, lambda v: v.user_id,
        range_starts='start', range_ends='end',
    )
    strike_by_day = _index_by_day(
        all_strikes, all_dates, lambda s: s.user_id,
        range_starts='start', range_ends='end',
    )
    outings_by_day = _index_by_day(
        all_outings, all_dates, lambda o: o.user_id,
        single_date_attr='outing_date',
    )

    sat_spare = _max_outings_for(saturday, users, set(), vac_by_day, strike_by_day, outings_by_day)
    sun_spare = _max_outings_for(sunday, users, set(), vac_by_day, strike_by_day, outings_by_day)

    # Build candidate pool. We do NOT pre-filter by vacation here — someone
    # on Sat vacation can still go out on Sun or a weekday, so the per-day
    # check happens in `can_take` below.
    pool = [u for u in users if u.id in candidate_ids]
    pool.sort(key=lambda u: _user_priority_key(u, ledger))

    chosen: List[OutingPlan] = []
    assigned_ids: set = set()
    # `remaining` is mutated in-place as outings are handed out. Keeping it
    # as a single dict (instead of free locals + closure) makes the mutation
    # site obvious from reading the loop body.
    remaining = {'sat': sat_spare, 'sun': sun_spare}

    vac_for = {
        'sat': vac_by_day.get(saturday, set()) | strike_by_day.get(saturday, set()),
        'sun': vac_by_day.get(sunday, set()) | strike_by_day.get(sunday, set()),
    }

    def can_take(user_id: int, day_label: str) -> bool:
        """User is free for `day_label` if not on vacation/SF AND day has spare."""
        return user_id not in vac_for[day_label] and remaining[day_label] > 0

    for user in pool:
        if user.id in assigned_ids:
            continue  # defensive — already placed

        first, second = _preferred_day_for(
            user, ledger, remaining['sat'], remaining['sun'],
        )
        if can_take(user.id, first):
            target = first
        elif can_take(user.id, second):
            target = second
        else:
            continue   # no weekend day works; weekday fallback below

        day_date = saturday if target == 'sat' else sunday
        kind = 'weekend_sat' if target == 'sat' else 'weekend_sun'
        chosen.append(OutingPlan(
            user_id=user.id,
            user_name=user.name,
            outing_date=day_date,
            kind=kind,
            reason=f"{kind} (last outing: {_last_outing(ledger, user.name)})",
        ))
        assigned_ids.add(user.id)
        remaining[target] -= 1

    # Weekday fallback: anyone still unassigned gets a next-week weekday
    # outing if any has spare. Implements "everyone gets out eventually" —
    # not just an at-least-1 guarantee but a comprehensive catch-all.
    weekday_spare = {
        wd: _max_outings_for(wd, users, set(), vac_by_day, strike_by_day, outings_by_day)
        for wd in weekday_dates
    }

    for user in pool:
        if user.id in assigned_ids:
            continue   # already got a weekend outing
        for wd in weekday_dates:
            if user.id in vac_by_day.get(wd, set()):
                continue
            if user.id in strike_by_day.get(wd, set()):
                continue
            if weekday_spare[wd] <= 0:
                continue
            chosen.append(OutingPlan(
                user_id=user.id,
                user_name=user.name,
                outing_date=wd,
                kind='weekday',
                reason='weekday fallback (weekend was full or rotation)',
            ))
            assigned_ids.add(user.id)
            weekday_spare[wd] -= 1
            break

    return chosen


def plans_to_outings(plans: List[OutingPlan]) -> List[Outing]:
    """Convert OutingPlan items into Outing rows ready to be saved by the store."""
    next_id = next_outing_id()
    return [
        Outing(
            id=next_id + i,
            user_id=p.user_id,
            outing_date=p.outing_date.isoformat(),
            kind=p.kind,
        )
        for i, p in enumerate(plans)
    ]
