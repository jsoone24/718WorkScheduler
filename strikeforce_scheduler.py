"""
strikeforce_scheduler.py — pick this week's 타격대 (quick-reaction force).

WHAT 타격대 IS
-------------
A small group (default 2 people) on standby for the whole week. They are
NOT scheduled for regular duty — think of it as a 5분대기조: stay nearby,
respond to emergencies, otherwise rest. Rotates so the same person doesn't
keep getting pulled.

ROTATION RULE
-------------
Pick the people who have been on strike-force LEAST RECENTLY. Tie-break by
user.id for stable ordering. Skip anyone on vacation that week (they're
already away from the unit).

CONFIGURABLE
------------
Size and duration come from data/settings.json (load via store.load_settings):
  - strike_force_size : how many people per shift (default 2)
  - strike_force_days : length of one shift in days (default 7 = Mon-Sun)
"""

from datetime import date, timedelta
from typing import List, Optional

from store import (
    User, StrikeForce, active_users, vacation_user_ids_on,
    load_strikeforce, load_settings, next_strikeforce_id,
)


def _last_strike_end_for(user_id: int, all_strikes: list) -> Optional[str]:
    """
    Most recent strike-force `end` date (ISO string) for this user, or None
    if they've never been on strike force.
    """
    user_strikes = [s for s in all_strikes if s.user_id == user_id]
    if not user_strikes:
        return None
    return max(s.end for s in user_strikes)


def plan_week(week_start: date) -> List[StrikeForce]:
    """
    Build the strike-force assignment for the week starting at `week_start`
    (must be a Monday). Returns a list of NEW StrikeForce records ready to be
    saved by store.save_strikeforce(...). Caller appends + persists.

    Skips users who already have a strike-force assignment overlapping this
    week, and users on vacation for any day of the week.
    """
    if week_start.weekday() != 0:
        raise ValueError(f"week_start는 월요일이어야 합니다 — 받은 값: {week_start}")

    settings = load_settings()
    size = int(settings['strike_force_size'])
    days = int(settings['strike_force_days'])
    week_end = week_start + timedelta(days=days - 1)

    users = active_users()
    all_strikes = load_strikeforce()

    # Anyone whose existing assignment overlaps this week is already serving.
    serving_ids = {
        s.user_id for s in all_strikes
        if s.start <= week_end.isoformat() and s.end >= week_start.isoformat()
    }

    # Anyone on vacation any day this week is excluded (they're already away).
    vacation_ids: set = set()
    for offset in range(days):
        vacation_ids |= vacation_user_ids_on(week_start + timedelta(days=offset))

    # Candidate pool: active, not currently serving, not on vacation.
    pool = [
        u for u in users
        if u.id not in serving_ids and u.id not in vacation_ids
    ]

    # Sort by rotation: least-recent strike force first; if never been, comes
    # before anyone who has. Stable tiebreak by user.id.
    def sort_key(u: User):
        last_end = _last_strike_end_for(u.id, all_strikes)
        # Users who've never served sort earliest (date '0000-00-00' < any real ISO date).
        return (last_end or '0000-00-00', u.id)
    pool.sort(key=sort_key)

    chosen = pool[:size]

    next_id = next_strikeforce_id()
    return [
        StrikeForce(
            id=next_id + i,
            user_id=u.id,
            start=week_start.isoformat(),
            end=week_end.isoformat(),
        )
        for i, u in enumerate(chosen)
    ]
