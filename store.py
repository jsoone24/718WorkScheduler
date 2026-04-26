"""
store.py — JSON-backed data layer.

EVERYTHING IS A FILE
--------------------
We persist all mutable data as JSON files in the `data/` directory:

    data/users.json       — the platoon roster + per-person preferences
    data/vacations.json   — date ranges where users are unavailable
    data/outings.json     — assigned outing dates (one row per outing)
    data/strikeforce.json — weekly strike-force (타격대) assignments
    data/settings.json    — app config (strike-force size & duration, etc.)
    data/schedules.json   — generated daily duty schedules (kept for history)
    data/ledger.json      — cumulative work-count counters (fairness state)

Why JSON instead of SQLite? With ~21 people and at most a few hundred records
per year of history, total data is well under 1 MB and loads in microseconds.
JSON is human-readable, greppable, and trivial to back up (just copy the
folder). SQL would buy us nothing here and cost a lot of boilerplate.

ATOMIC WRITES
-------------
Every save writes to a temp file then renames — so a crash mid-write can
never leave a half-written file. Same trick the original ledger.py used.

DATACLASSES
-----------
Each "table" has a dataclass for ergonomics. We convert dataclass <-> dict
manually rather than pulling in pydantic, since the schemas are tiny and
stable.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional


DATA_DIR = 'data'

USERS_PATH       = os.path.join(DATA_DIR, 'users.json')
VACATIONS_PATH   = os.path.join(DATA_DIR, 'vacations.json')
OUTINGS_PATH     = os.path.join(DATA_DIR, 'outings.json')
STRIKEFORCE_PATH = os.path.join(DATA_DIR, 'strikeforce.json')
SETTINGS_PATH    = os.path.join(DATA_DIR, 'settings.json')
SCHEDULES_PATH   = os.path.join(DATA_DIR, 'schedules.json')
LEDGER_PATH      = os.path.join(DATA_DIR, 'ledger.json')

# Default settings — overridable via data/settings.json
DEFAULT_SETTINGS = {
    'strike_force_size': 2,            # how many people per strike-force assignment
    'strike_force_days': 7,            # length of one strike-force shift in days
}


# ---------------------------------------------------------------------------
# Dataclasses (one per "table")
# ---------------------------------------------------------------------------

@dataclass
class Preferences:
    """Per-group preferred shift hours for a single user."""
    times3: list[int] = field(default_factory=list)  # preferred slots when 3-duty
    times2: list[int] = field(default_factory=list)  # preferred slots when 2-duty


@dataclass
class User:
    """
    A platoon member.

    `active=False` keeps the user on the roster (history preserved) but excludes
    them from all future scheduling. Use this for transferred / on-extended-
    leave / awaiting-discharge cases instead of deleting the row.
    """
    id: int
    name: str
    active: bool = True
    display_order: int = 0
    # Preferences keyed by group letter ('A', 'B', 'C')
    preferences: dict[str, Preferences] = field(default_factory=dict)


@dataclass
class Vacation:
    """
    A date range (inclusive on both ends) where a user is unavailable.
    Single-day vacations have start == end.
    """
    id: int
    user_id: int
    start: str   # ISO date 'YYYY-MM-DD'
    end: str
    kind: str = 'vacation'   # free-text: 'vacation' | 'training' | 'medical' | 'personal'
    notes: str = ''


@dataclass
class Outing:
    """
    An assigned outing. The outing scheduler decides who goes when; this row
    is the result.
    """
    id: int
    user_id: int
    outing_date: str         # ISO date
    kind: str                # 'weekend_sat' | 'weekend_sun' | 'weekday'


@dataclass
class StrikeForce:
    """
    A 타격대 (quick-reaction standby) assignment. The user is OFF regular duty
    for the entire date range — Mon–Sun by convention, but flexible. Multiple
    StrikeForce rows can overlap (the strike-force size is configurable).
    """
    id: int
    user_id: int
    start: str   # ISO date — typically a Monday
    end: str     # ISO date — typically a Sunday


# ---------------------------------------------------------------------------
# Generic load / save (atomic)
# ---------------------------------------------------------------------------

def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(path: str, default):
    """Read a JSON file, or return `default` if it doesn't exist."""
    if not os.path.exists(path):
        return default
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_json(path: str, payload) -> None:
    """Write JSON atomically (tmp + rename) so a crash can't corrupt the file."""
    _ensure_data_dir()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=False)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def load_users() -> list[User]:
    raw = _load_json(USERS_PATH, [])
    out = []
    for r in raw:
        prefs = {
            g: Preferences(**p) for g, p in r.get('preferences', {}).items()
        }
        out.append(User(
            id=r['id'],
            name=r['name'],
            active=r.get('active', True),
            display_order=r.get('display_order', 0),
            preferences=prefs,
        ))
    out.sort(key=lambda u: (u.display_order, u.id))
    return out


def save_users(users: list[User]) -> None:
    payload = [
        {
            'id': u.id,
            'name': u.name,
            'active': u.active,
            'display_order': u.display_order,
            'preferences': {g: asdict(p) for g, p in u.preferences.items()},
        }
        for u in users
    ]
    _save_json(USERS_PATH, payload)


def active_users() -> list[User]:
    return [u for u in load_users() if u.active]


def next_user_id() -> int:
    users = load_users()
    return (max((u.id for u in users), default=0)) + 1


def user_by_id(user_id: int) -> Optional[User]:
    return next((u for u in load_users() if u.id == user_id), None)


def user_by_name(name: str) -> Optional[User]:
    return next((u for u in load_users() if u.name == name), None)


# ---------------------------------------------------------------------------
# Vacations
# ---------------------------------------------------------------------------

def load_vacations() -> list[Vacation]:
    raw = _load_json(VACATIONS_PATH, [])
    return [Vacation(**r) for r in raw]


def save_vacations(vacations: list[Vacation]) -> None:
    _save_json(VACATIONS_PATH, [asdict(v) for v in vacations])


def next_vacation_id() -> int:
    return (max((v.id for v in load_vacations()), default=0)) + 1


def vacation_user_ids_on(d: date) -> set[int]:
    """User IDs whose vacation range covers the given date."""
    iso = d.isoformat()
    return {
        v.user_id for v in load_vacations()
        if v.start <= iso <= v.end
    }


# ---------------------------------------------------------------------------
# Outings
# ---------------------------------------------------------------------------

def load_outings() -> list[Outing]:
    raw = _load_json(OUTINGS_PATH, [])
    return [Outing(**r) for r in raw]


def save_outings(outings: list[Outing]) -> None:
    _save_json(OUTINGS_PATH, [asdict(o) for o in outings])


def next_outing_id() -> int:
    return (max((o.id for o in load_outings()), default=0)) + 1


def outing_user_ids_on(d: date) -> set[int]:
    iso = d.isoformat()
    return {o.user_id for o in load_outings() if o.outing_date == iso}


# ---------------------------------------------------------------------------
# Strike force (타격대)
# ---------------------------------------------------------------------------

def load_strikeforce() -> list[StrikeForce]:
    raw = _load_json(STRIKEFORCE_PATH, [])
    return [StrikeForce(**r) for r in raw]


def save_strikeforce(items: list[StrikeForce]) -> None:
    _save_json(STRIKEFORCE_PATH, [asdict(s) for s in items])


def next_strikeforce_id() -> int:
    return (max((s.id for s in load_strikeforce()), default=0)) + 1


def strikeforce_user_ids_on(d: date) -> set[int]:
    """User IDs on strike-force standby on the given date."""
    iso = d.isoformat()
    return {
        s.user_id for s in load_strikeforce()
        if s.start <= iso <= s.end
    }


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def load_settings() -> dict:
    """
    App-level settings (strike-force size, etc). Falls back to DEFAULT_SETTINGS
    for any keys not in the file. Always returns a complete dict.
    """
    saved = _load_json(SETTINGS_PATH, {})
    merged = dict(DEFAULT_SETTINGS)
    merged.update(saved)
    return merged


def save_settings(settings: dict) -> None:
    _save_json(SETTINGS_PATH, settings)


# ---------------------------------------------------------------------------
# Schedules (daily output, kept for history)
# ---------------------------------------------------------------------------

def load_schedules() -> dict:
    """All schedules keyed by ISO date string."""
    return _load_json(SCHEDULES_PATH, {})


def save_schedule(d: date, group_letter: str, is_weekend: bool,
                  assignments: dict[str, list[tuple[int, int]]]) -> None:
    """Add or replace today's schedule. `assignments` = name -> [(slot, site), ...]."""
    all_scheds = load_schedules()
    all_scheds[d.isoformat()] = {
        'group': group_letter,
        'is_weekend': is_weekend,
        'assignments': {name: [list(t) for t in slots]
                        for name, slots in assignments.items()},
    }
    _save_json(SCHEDULES_PATH, all_scheds)


def schedule_on(d: date) -> Optional[dict]:
    return load_schedules().get(d.isoformat())


# ---------------------------------------------------------------------------
# Ledger (cumulative fairness counters)
# ---------------------------------------------------------------------------

def load_ledger() -> dict:
    """
    Returns a dict shaped like:
        {
            'work_count': {name: int, ...},
            'pref_match_count': {name: int, ...},
            'available_days': {name: int, ...},
            'last_outing': {name: {'date': iso, 'kind': str}, ...},
            'last_date': iso or None,
            'days_recorded': int,
        }

    Auto-initialises empty counters for any user that exists in users.json
    but isn't yet in the ledger.
    """
    data = _load_json(LEDGER_PATH, None)
    if data is None:
        data = {
            'work_count': {},
            'pref_match_count': {},
            'available_days': {},
            'last_outing': {},
            'last_date': None,
            'days_recorded': 0,
        }
    # Backfill any users that exist in the roster but not the ledger
    for u in load_users():
        data.setdefault('work_count', {}).setdefault(u.name, 0)
        data.setdefault('sf_credit_slots', {}).setdefault(u.name, 0)
        data.setdefault('pref_match_count', {}).setdefault(u.name, 0)
        data.setdefault('available_days', {}).setdefault(u.name, 0)
        data.setdefault('last_outing', {})
    # `recorded_dates` is the set of ISO date strings already folded into the
    # cumulative counters. Used to skip double-counting when a day is
    # re-generated (or when bulk-generation overlaps an existing run).
    data.setdefault('recorded_dates', [])
    return data


def save_ledger(data: dict) -> None:
    _save_json(LEDGER_PATH, data)
