"""
web_app.py — FastAPI web UI for the 718 duty scheduler.

Run:
    python -m uvicorn web_app:app --reload

Then open http://127.0.0.1:8000

SECURITY / DEPLOYMENT NOTE
--------------------------
This app has NO authentication. It is intended to be run on the LOCALHOST
of one administrator's machine only. Do NOT expose it on a network interface
(don't pass `--host 0.0.0.0`); if you need multi-user access, put a reverse
proxy with auth in front. uvicorn's default bind is 127.0.0.1, which is
the safe configuration.

WHAT THIS FILE PROVIDES
-----------------------
A small browser-based UI for the whole workflow:

  Dashboard           → today's group + today's schedule + combined auto-plan
  /users              → CRUD for the platoon roster (add, edit, deactivate, delete)
  /vacations          → manage vacation date ranges per person
  /outings            → view and (re)plan outings for upcoming weeks
  /strikeforce        → manage 타격대 (quick-reaction force) rotation + settings
  /calendar           → grid view of vacation/outing/strike-force by person × day
  /schedules          → list saved schedules, bulk-generate by date range
  /schedule/{date}    → view or generate a single day's schedule
  /ledger             → cumulative work-count statistics

DESIGN NOTES
------------
- All data goes through store.py (JSON files).
- Solver / outing_scheduler modules are pure and side-effect-free; the routes
  here orchestrate them and persist the results.
- For HTMX-aware responses, we usually return a fragment (just the updated
  table row) for hx-* requests, full pages otherwise.
"""

import datetime
from typing import Optional

from fastapi import FastAPI, Form, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import ledger
import store
import outing_scheduler
import strikeforce_scheduler
from constants import work_group, Timetable, placetable
from solver import (
    solve_day,
    feasibility_report,
    SLOT_24H,
    SITE_NAMES,
    STATUS_ABSENT,
    STATUS_OUTING,
    STATUS_LONGNIGHT,
    STATUS_STRIKE,
)


app = FastAPI(title="718 Duty Scheduler")
app.mount('/static', StaticFiles(directory='static'), name='static')
# Jinja2Templates uses jinja2.select_autoescape() by default — autoescape is
# ON for .html / .xml files. Confirmed by inspecting `templates.env.autoescape`.
# No template uses `|safe`, `|raw`, or `{% autoescape false %}`, so all
# user-supplied strings (names, notes) are HTML-escaped.
templates = Jinja2Templates(directory='templates')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_today_group(d: datetime.date) -> int:
    return ((d - datetime.date(2020, 1, 1)).days + 1) % 3


def parse_date(s: str) -> datetime.date:
    """Parse YYYY-MM-DD with a clean 400 on malformed input."""
    try:
        return datetime.date.fromisoformat(s)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"날짜 형식 오류: {s!r}")


def build_statuses(d: datetime.date, active: list, longnight_names: set) -> dict:
    """Construct the status dict the solver expects, from store data."""
    vac_ids = store.vacation_user_ids_on(d)
    out_ids = store.outing_user_ids_on(d)
    strike_ids = store.strikeforce_user_ids_on(d)
    by_id = {u.id: u for u in active}

    statuses: dict = {}
    for uid in vac_ids:
        u = by_id.get(uid)
        if u:
            statuses[u.name] = STATUS_ABSENT
    for uid in out_ids:
        u = by_id.get(uid)
        if u:
            statuses[u.name] = STATUS_OUTING
    for uid in strike_ids:
        u = by_id.get(uid)
        if u:
            statuses[u.name] = STATUS_STRIKE
    for name in longnight_names:
        statuses[name] = STATUS_LONGNIGHT
    return statuses


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get('/', response_class=HTMLResponse)
def dashboard(
    request: Request,
    auto_sf: Optional[int] = None,
    auto_out: Optional[int] = None,
    auto_sched: Optional[int] = None,
    auto_skip: Optional[int] = None,
    auto_fail: Optional[int] = None,
):
    today = datetime.date.today()
    group = compute_today_group(today)
    is_weekend = today.weekday() >= 5
    active = store.active_users()
    book = store.load_ledger()
    today_sched = store.schedule_on(today)

    # If today's schedule exists, prepare slot-grid + per-person data so the
    # dashboard can render the full assignment inline (saves one click).
    by_slot_site = None
    per_person = None
    times = None
    place_cap = None
    statuses = None
    if today_sched:
        times = Timetable[group][0]
        weekend_idx = 1 if is_weekend else 0
        place_cap = placetable[group][weekend_idx]
        statuses = build_statuses(today, active, longnight_names=set())
        assignments = today_sched['assignments']
        by_slot_site = {(s, l): [] for s in range(4) for l in range(4)}
        for name, slots in assignments.items():
            for s, l in slots:
                by_slot_site[(s, l)].append(name)
        per_person = sorted(assignments.items(), key=lambda kv: -len(kv[1]))

    # Default start for the combined auto-plan form: this week's Monday.
    this_monday = today - datetime.timedelta(days=today.weekday())

    auto_summary = None
    if any(v is not None for v in (auto_sf, auto_out, auto_sched, auto_skip, auto_fail)):
        auto_summary = {
            'sf': auto_sf or 0,
            'outings': auto_out or 0,
            'sched_added': auto_sched or 0,
            'sched_skipped': auto_skip or 0,
            'sched_failed': auto_fail or 0,
        }

    return templates.TemplateResponse(request, 'dashboard.html', {
        'today': today,
        'this_monday': this_monday,
        'group_letter': work_group[group],
        'is_weekend': is_weekend,
        'active_count': len(active),
        'all_count': len(store.load_users()),
        'days_recorded': book.get('days_recorded', 0),
        'last_date': book.get('last_date'),
        'has_today_schedule': today_sched is not None,
        'times': times,
        'slot_24h': SLOT_24H[group] if today_sched else None,
        'place_cap': place_cap,
        'site_names': SITE_NAMES,
        'by_slot_site': by_slot_site,
        'per_person': per_person,
        'statuses': statuses,
        'auto_summary': auto_summary,
    })


# ---------------------------------------------------------------------------
# Users CRUD
# ---------------------------------------------------------------------------

@app.get('/users', response_class=HTMLResponse)
def users_page(request: Request):
    users = store.load_users()
    return templates.TemplateResponse(request, 'users.html', {'users': users})


@app.post('/users')
def users_create(name: str = Form(...)):
    name = name.strip()
    if not name:
        raise HTTPException(400, "이름을 입력하세요")
    if store.user_by_name(name):
        raise HTTPException(400, f"이미 존재하는 이름입니다: {name!r}")
    users = store.load_users()
    users.append(store.User(
        id=store.next_user_id(),
        name=name,
        active=True,
        display_order=len(users),
        preferences={},  # user can fill in via edit page
    ))
    store.save_users(users)
    return RedirectResponse('/users', status_code=303)


@app.post('/users/{user_id}/toggle')
def users_toggle(user_id: int):
    users = store.load_users()
    for u in users:
        if u.id == user_id:
            u.active = not u.active
            break
    else:
        raise HTTPException(404, "대원을 찾을 수 없습니다")
    store.save_users(users)
    return RedirectResponse('/users', status_code=303)


@app.post('/users/{user_id}/delete')
def users_delete(user_id: int):
    users = [u for u in store.load_users() if u.id != user_id]
    store.save_users(users)
    return RedirectResponse('/users', status_code=303)


@app.get('/users/{user_id}/edit', response_class=HTMLResponse)
def users_edit(request: Request, user_id: int):
    user = store.user_by_id(user_id)
    if not user:
        raise HTTPException(404, "대원을 찾을 수 없습니다")
    return templates.TemplateResponse(request, 'user_edit.html', {'user': user})


@app.post('/users/{user_id}/edit')
def users_edit_post(
    user_id: int,
    name: str = Form(...),
    active: Optional[str] = Form(None),
    times3_a: str = Form(''),
    times2_a: str = Form(''),
    times3_b: str = Form(''),
    times2_b: str = Form(''),
    times3_c: str = Form(''),
    times2_c: str = Form(''),
):
    users = store.load_users()
    for u in users:
        if u.id == user_id:
            u.name = name.strip() or u.name
            u.active = active == 'on'
            u.preferences = {
                'A': store.Preferences(times3=_csv_ints(times3_a), times2=_csv_ints(times2_a)),
                'B': store.Preferences(times3=_csv_ints(times3_b), times2=_csv_ints(times2_b)),
                'C': store.Preferences(times3=_csv_ints(times3_c), times2=_csv_ints(times2_c)),
            }
            break
    else:
        raise HTTPException(404, "대원을 찾을 수 없습니다")
    store.save_users(users)
    return RedirectResponse('/users', status_code=303)


def _csv_ints(s: str) -> list[int]:
    return [int(x) for x in s.replace(' ', '').split(',') if x]


# ---------------------------------------------------------------------------
# Calendar grid (rows = people, columns = days)
# ---------------------------------------------------------------------------

CALENDAR_DAYS_DEFAULT = 14


def _calendar_status_for(uid: int, d: datetime.date,
                          vac_by_day: dict, out_by_day: dict,
                          strike_by_day: dict) -> str:
    """Return one of '' | 'vacation' | 'weekend_sat'/'weekend_sun'/'weekday' | 'strike'."""
    if uid in strike_by_day.get(d, set()):
        return 'strike'
    if uid in vac_by_day.get(d, set()):
        return 'vacation'
    o_kind = out_by_day.get(d, {}).get(uid)
    if o_kind:
        return o_kind
    return ''


@app.get('/calendar', response_class=HTMLResponse)
def calendar_view(request: Request,
                   start: Optional[str] = None,
                   days: int = CALENDAR_DAYS_DEFAULT):
    """
    Render a grid: rows = active users, columns = N days starting at `start`
    (default: today). Each cell shows the person's status for that day and is
    clickable to cycle through {none → vacation → outing → none}.
    """
    if start:
        start_date = parse_date(start)
    else:
        start_date = datetime.date.today()

    days = max(1, min(60, days))  # clamp 1–60

    # Snap to the Monday of the week ONLY for week-aligned views (≥ 7 days).
    # For short ranges (1, 3 days) we keep the raw start so "next 1 day"
    # actually shows tomorrow rather than this week's Monday.
    if days >= 7:
        start_date = start_date - datetime.timedelta(days=start_date.weekday())

    date_list = [start_date + datetime.timedelta(days=i) for i in range(days)]
    users = store.active_users()

    # Pre-index vacations, outings, strike-force by date for O(1) cell lookups
    vac_by_day: dict = {}
    for v in store.load_vacations():
        for d in date_list:
            iso = d.isoformat()
            if v.start <= iso <= v.end:
                vac_by_day.setdefault(d, set()).add(v.user_id)
    out_by_day: dict = {}
    for o in store.load_outings():
        d = datetime.date.fromisoformat(o.outing_date)
        if d in date_list:
            out_by_day.setdefault(d, {})[o.user_id] = o.kind
    strike_by_day: dict = {}
    for s in store.load_strikeforce():
        for d in date_list:
            iso = d.isoformat()
            if s.start <= iso <= s.end:
                strike_by_day.setdefault(d, set()).add(s.user_id)

    # Pre-build cells matrix for the template (avoids a function call per cell)
    rows = []
    for u in users:
        cells = []
        for d in date_list:
            status = _calendar_status_for(
                u.id, d, vac_by_day, out_by_day, strike_by_day,
            )
            cells.append({'date': d, 'status': status})
        rows.append({'user': u, 'cells': cells})

    return templates.TemplateResponse(request, 'calendar.html', {
        'start_date': start_date,
        'date_list': date_list,
        'rows': rows,
        'prev_start': start_date - datetime.timedelta(days=days),
        'next_start': start_date + datetime.timedelta(days=days),
    })


@app.post('/calendar/cell', response_class=HTMLResponse)
def calendar_cell_toggle(
    request: Request,
    user_id: int = Form(...),
    date_str: str = Form(...),
):
    """
    Cycle this cell's status: none → vacation → outing(weekend/weekday auto)
                                  → none.
    Returns just the updated cell HTML (HTMX swaps it in).
    """
    d = parse_date(date_str)
    user = store.user_by_id(user_id)
    if not user:
        raise HTTPException(404, "대원을 찾을 수 없습니다")

    # If the user is on strike-force standby that day, the cell is read-only:
    # strike force is managed on its own page (so the toggle here doesn't
    # accidentally clobber a planned rotation).
    if user.id in store.strikeforce_user_ids_on(d):
        return templates.TemplateResponse(request, '_calendar_cell.html', {
            'user_id': user.id, 'date': d, 'status': 'strike',
        })

    # Determine current state
    on_vac = user.id in store.vacation_user_ids_on(d)
    out_kind = None
    for o in store.load_outings():
        if o.user_id == user.id and o.outing_date == d.isoformat():
            out_kind = o.kind
            break

    # Cycle: none → vacation → outing → none
    if not on_vac and not out_kind:
        # add vacation
        vacs = store.load_vacations()
        vacs.append(store.Vacation(
            id=store.next_vacation_id(),
            user_id=user.id,
            start=d.isoformat(), end=d.isoformat(),
            kind='vacation', notes='(달력에서 추가)',
        ))
        store.save_vacations(vacs)
        new_status = 'vacation'
    elif on_vac and not out_kind:
        # remove vacation, add outing (kind by day-of-week)
        vacs = [v for v in store.load_vacations()
                if not (v.user_id == user.id and v.start == d.isoformat() and v.end == d.isoformat())]
        store.save_vacations(vacs)

        if d.weekday() == 5:
            kind = 'weekend_sat'
        elif d.weekday() == 6:
            kind = 'weekend_sun'
        else:
            kind = 'weekday'
        outs = store.load_outings()
        outs.append(store.Outing(
            id=store.next_outing_id(),
            user_id=user.id,
            outing_date=d.isoformat(),
            kind=kind,
        ))
        store.save_outings(outs)
        new_status = kind
    else:
        # remove outing, leave clear
        outs = [o for o in store.load_outings()
                if not (o.user_id == user.id and o.outing_date == d.isoformat())]
        store.save_outings(outs)
        new_status = ''

    return templates.TemplateResponse(request, '_calendar_cell.html', {
        'user_id': user.id,
        'date': d,
        'status': new_status,
    })


# ---------------------------------------------------------------------------
# Vacations
# ---------------------------------------------------------------------------

@app.get('/vacations', response_class=HTMLResponse)
def vacations_page(request: Request):
    vacations = store.load_vacations()
    users_by_id = {u.id: u for u in store.load_users()}
    return templates.TemplateResponse(request, 'vacations.html', {
        'vacations': sorted(vacations, key=lambda v: v.start, reverse=True),
        'users': store.active_users(),
        'users_by_id': users_by_id,
    })


@app.post('/vacations')
def vacations_create(
    user_id: int = Form(...),
    start: str = Form(...),
    end: str = Form(...),
    kind: str = Form('vacation'),
    notes: str = Form(''),
):
    parse_date(start); parse_date(end)
    if start > end:
        raise HTTPException(400, "시작일은 종료일과 같거나 이전이어야 합니다")
    if not store.user_by_id(user_id):
        raise HTTPException(404, "대원을 찾을 수 없습니다")
    vacations = store.load_vacations()
    vacations.append(store.Vacation(
        id=store.next_vacation_id(),
        user_id=user_id,
        start=start, end=end,
        kind=kind, notes=notes,
    ))
    store.save_vacations(vacations)
    return RedirectResponse('/vacations', status_code=303)


@app.post('/vacations/{vac_id}/delete')
def vacations_delete(vac_id: int):
    vacs = [v for v in store.load_vacations() if v.id != vac_id]
    store.save_vacations(vacs)
    return RedirectResponse('/vacations', status_code=303)


@app.post('/vacations/bulk-delete')
def vacations_bulk_delete(ids: list[int] = Form(default=[])):
    """Delete every vacation whose id is in `ids` (from checkboxes)."""
    if not ids:
        return RedirectResponse('/vacations', status_code=303)
    drop = set(ids)
    rows = [v for v in store.load_vacations() if v.id not in drop]
    store.save_vacations(rows)
    return RedirectResponse('/vacations', status_code=303)


# ---------------------------------------------------------------------------
# Outings
# ---------------------------------------------------------------------------

@app.get('/outings', response_class=HTMLResponse)
def outings_page(request: Request, week: Optional[str] = None):
    """Show outings for the week containing `week` (defaults to current week)."""
    if week:
        anchor = parse_date(week)
    else:
        anchor = datetime.date.today()
    monday = anchor - datetime.timedelta(days=anchor.weekday())

    outings = sorted(store.load_outings(), key=lambda o: o.outing_date, reverse=True)
    users_by_id = {u.id: u for u in store.load_users()}
    return templates.TemplateResponse(request, 'outings.html', {
        'outings': outings,
        'users': store.active_users(),
        'users_by_id': users_by_id,
        'week_monday': monday,
        'sat': monday + datetime.timedelta(days=5),
        'sun': monday + datetime.timedelta(days=6),
    })


@app.post('/outings')
def outings_create(
    user_id: int = Form(...),
    outing_date: str = Form(...),
    kind: str = Form('weekend_sat'),
):
    parse_date(outing_date)
    if not store.user_by_id(user_id):
        raise HTTPException(404, "대원을 찾을 수 없습니다")
    outings = store.load_outings()
    outings.append(store.Outing(
        id=store.next_outing_id(),
        user_id=user_id,
        outing_date=outing_date,
        kind=kind,
    ))
    store.save_outings(outings)
    return RedirectResponse('/outings', status_code=303)


@app.post('/outings/plan')
def outings_plan(
    week_start: str = Form(...),
    num_weeks: int = Form(1),
):
    """
    Run the outing scheduler for `num_weeks` *new* weeks starting at or after
    `week_start` (a Monday).

    Skip-and-shift: any week that already has outings on either Sat or Sun is
    treated as "already done" and we shift to the next free week. Re-running
    the same form won't create duplicates.
    """
    monday = parse_date(week_start)
    if monday.weekday() != 0:
        raise HTTPException(400, "week_start는 월요일이어야 합니다")
    if num_weeks < 1 or num_weeks > 12:
        raise HTTPException(400, "주 수는 1~12 사이여야 합니다")

    planned = 0
    wk = monday
    safety_iterations = num_weeks + 24
    while planned < num_weeks and safety_iterations > 0:
        safety_iterations -= 1
        sat = wk + datetime.timedelta(days=5)
        sun = wk + datetime.timedelta(days=6)
        # If either Sat or Sun already has outings, treat the week as done
        # and skip to the next one.
        already = (
            len(store.outing_user_ids_on(sat)) > 0
            or len(store.outing_user_ids_on(sun)) > 0
        )
        if already:
            wk += datetime.timedelta(weeks=1)
            continue

        plans = outing_scheduler.plan_week(wk)
        new_outings = outing_scheduler.plans_to_outings(plans)
        if new_outings:
            all_outings = store.load_outings()
            all_outings.extend(new_outings)
            store.save_outings(all_outings)
            book = store.load_ledger()
            for plan in plans:
                book['last_outing'][plan.user_name] = {
                    'date': plan.outing_date.isoformat(),
                    'kind': plan.kind,
                }
            store.save_ledger(book)
            planned += 1
        wk += datetime.timedelta(weeks=1)

    return RedirectResponse(f'/outings?week={monday.isoformat()}', status_code=303)


@app.post('/outings/{outing_id}/delete')
def outings_delete(outing_id: int):
    rows = [o for o in store.load_outings() if o.id != outing_id]
    store.save_outings(rows)
    return RedirectResponse('/outings', status_code=303)


@app.post('/outings/bulk-delete')
def outings_bulk_delete(ids: list[int] = Form(default=[])):
    """Delete every outing whose id is in `ids` (from checkboxes)."""
    if not ids:
        return RedirectResponse('/outings', status_code=303)
    drop = set(ids)
    rows = [o for o in store.load_outings() if o.id not in drop]
    store.save_outings(rows)
    return RedirectResponse('/outings', status_code=303)


# ---------------------------------------------------------------------------
# Strike force (타격대)
# ---------------------------------------------------------------------------

@app.get('/strikeforce', response_class=HTMLResponse)
def strikeforce_page(request: Request, week: Optional[str] = None):
    """
    Manage strike-force assignments. Shows:
      - this week's roster (auto-plan button)
      - upcoming + past assignments
      - settings for size & duration
    """
    if week:
        anchor = parse_date(week)
    else:
        anchor = datetime.date.today()
    monday = anchor - datetime.timedelta(days=anchor.weekday())

    settings = store.load_settings()
    duration = int(settings['strike_force_days'])
    week_end = monday + datetime.timedelta(days=duration - 1)

    items = sorted(store.load_strikeforce(), key=lambda s: s.start, reverse=True)
    users_by_id = {u.id: u for u in store.load_users()}

    # Highlight the rows that overlap THIS week
    this_week_iso_range = (monday.isoformat(), week_end.isoformat())
    return templates.TemplateResponse(request, 'strikeforce.html', {
        'items': items,
        'users': store.active_users(),
        'users_by_id': users_by_id,
        'week_monday': monday,
        'week_end': week_end,
        'this_week_range': this_week_iso_range,
        'settings': settings,
    })


@app.post('/strikeforce/plan')
def strikeforce_plan(
    week_start: str = Form(...),
    num_weeks: int = Form(1),
):
    """
    Auto-plan strike force for `num_weeks` *new* weeks starting at or after
    `week_start` (a Monday).

    Skip-and-shift behaviour: any week that is already fully filled (size
    already met) is skipped, and we shift forward to find the next free week.
    Re-running the same form won't create duplicates — each click only adds
    `num_weeks` genuinely new assignments.
    """
    monday = parse_date(week_start)
    if monday.weekday() != 0:
        raise HTTPException(400, "week_start는 월요일이어야 합니다")
    if num_weeks < 1 or num_weeks > 12:
        raise HTTPException(400, "주 수는 1~12 사이여야 합니다")

    settings = store.load_settings()
    size = int(settings['strike_force_size'])

    planned = 0
    wk = monday
    safety_iterations = num_weeks + 24  # don't loop forever on weird data
    while planned < num_weeks and safety_iterations > 0:
        safety_iterations -= 1
        existing_count = sum(
            1 for s in store.load_strikeforce() if s.start == wk.isoformat()
        )
        if existing_count >= size:
            wk += datetime.timedelta(weeks=1)
            continue   # this week is full; try next
        new_items = strikeforce_scheduler.plan_week(wk)
        if new_items:
            existing = store.load_strikeforce()
            existing.extend(new_items)
            store.save_strikeforce(existing)
            planned += 1
        wk += datetime.timedelta(weeks=1)
    return RedirectResponse(f'/strikeforce?week={monday.isoformat()}', status_code=303)


@app.post('/strikeforce')
def strikeforce_create(
    user_id: int = Form(...),
    start: str = Form(...),
    end: str = Form(...),
):
    """Manually add a strike-force assignment."""
    parse_date(start); parse_date(end)
    if start > end:
        raise HTTPException(400, "시작일은 종료일과 같거나 이전이어야 합니다")
    if not store.user_by_id(user_id):
        raise HTTPException(404, "대원을 찾을 수 없습니다")
    items = store.load_strikeforce()
    items.append(store.StrikeForce(
        id=store.next_strikeforce_id(),
        user_id=user_id, start=start, end=end,
    ))
    store.save_strikeforce(items)
    return RedirectResponse('/strikeforce', status_code=303)


@app.post('/strikeforce/{sf_id}/delete')
def strikeforce_delete(sf_id: int):
    rows = [s for s in store.load_strikeforce() if s.id != sf_id]
    store.save_strikeforce(rows)
    return RedirectResponse('/strikeforce', status_code=303)


@app.post('/strikeforce/bulk-delete')
def strikeforce_bulk_delete(ids: list[int] = Form(default=[])):
    """Delete every strike-force assignment whose id is in `ids`."""
    if not ids:
        return RedirectResponse('/strikeforce', status_code=303)
    drop = set(ids)
    rows = [s for s in store.load_strikeforce() if s.id not in drop]
    store.save_strikeforce(rows)
    return RedirectResponse('/strikeforce', status_code=303)


@app.post('/strikeforce/settings')
def strikeforce_save_settings(
    strike_force_size: int = Form(...),
    strike_force_days: int = Form(...),
):
    """Update strike-force size and shift length."""
    if strike_force_size < 1 or strike_force_size > 21:
        raise HTTPException(400, "타격대 인원은 1~21명 사이여야 합니다")
    if strike_force_days < 1 or strike_force_days > 30:
        raise HTTPException(400, "기간은 1~30일 사이여야 합니다")
    s = store.load_settings()
    s['strike_force_size'] = strike_force_size
    s['strike_force_days'] = strike_force_days
    store.save_settings(s)
    return RedirectResponse('/strikeforce', status_code=303)


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

@app.get('/schedules', response_class=HTMLResponse)
def schedules_list(
    request: Request,
    ok: Optional[int] = None,
    skip: Optional[int] = None,
    fail: Optional[int] = None,
    wiped: Optional[int] = None,
):
    """
    List all generated schedules grouped by month, with quick-action forms
    at the top: pick a date to view, generate a single date, or generate a
    range of dates in one go.

    The optional `ok`/`skip`/`fail` query params are populated by the
    bulk-generate redirect and shown as a summary banner.
    """
    all_scheds = store.load_schedules()
    # Sort by date descending and group by 'YYYY-MM'
    by_month: dict = {}
    for date_str in sorted(all_scheds.keys(), reverse=True):
        s = all_scheds[date_str]
        d = datetime.date.fromisoformat(date_str)
        ym = d.strftime('%Y-%m')
        # How many slots filled vs total (a quick health check)
        total_slots = sum(len(v) for v in s['assignments'].values())
        active_in_sched = sum(1 for v in s['assignments'].values() if v)
        by_month.setdefault(ym, []).append({
            'date': d,
            'group': s['group'],
            'is_weekend': s['is_weekend'],
            'total_slots': total_slots,
            'active_count': active_in_sched,
        })

    today = datetime.date.today()
    next_week_end = today + datetime.timedelta(days=6)
    bulk_summary = None
    if ok is not None or skip is not None or fail is not None:
        bulk_summary = {'ok': ok or 0, 'skip': skip or 0, 'fail': fail or 0}
    return templates.TemplateResponse(request, 'schedules.html', {
        'by_month': by_month,
        'today': today,
        'default_range_start': today.isoformat(),
        'default_range_end': next_week_end.isoformat(),
        'bulk_summary': bulk_summary,
        'wiped': bool(wiped),
    })


@app.post('/auto-plan-all')
def auto_plan_all(
    start_week: str = Form(...),
    num_weeks: int = Form(2),
):
    """
    The full workflow in one click: 타격대 → 외출 → 근무표.

    For each of the next `num_weeks` weeks starting at `start_week` (Monday):
      1. Auto-plan strike force (skip if already filled this week)
      2. Auto-plan outings (skip if Sat/Sun already has outings this week)
      3. Generate daily schedules for each day in this week (skip existing)

    Each step's output feeds the next via the persistent store, and ledger
    fairness is updated chronologically so multi-week balance holds.

    Redirects to dashboard with a summary banner.
    """
    monday = parse_date(start_week)
    if monday.weekday() != 0:
        raise HTTPException(400, "월요일이어야 합니다")
    if num_weeks < 1 or num_weeks > 12:
        raise HTTPException(400, "주 수는 1~12 사이여야 합니다")

    settings = store.load_settings()
    sf_size = int(settings['strike_force_size'])

    sf_added = 0
    outing_added = 0
    sched_added = 0
    sched_skipped = 0
    sched_failed: list[str] = []

    for i in range(num_weeks):
        wk = monday + datetime.timedelta(weeks=i)

        # Step 1: SF for this week, only if not already filled
        existing_sf_for_wk = sum(
            1 for s in store.load_strikeforce() if s.start == wk.isoformat()
        )
        if existing_sf_for_wk < sf_size:
            new_sf = strikeforce_scheduler.plan_week(wk)
            if new_sf:
                rows = store.load_strikeforce()
                rows.extend(new_sf)
                store.save_strikeforce(rows)
                sf_added += len(new_sf)

        # Step 2: outings for this week, only if Sat/Sun has none yet
        sat = wk + datetime.timedelta(days=5)
        sun = wk + datetime.timedelta(days=6)
        already_outings = (
            len(store.outing_user_ids_on(sat)) > 0
            or len(store.outing_user_ids_on(sun)) > 0
        )
        if not already_outings:
            plans = outing_scheduler.plan_week(wk)
            new_outings = outing_scheduler.plans_to_outings(plans)
            if new_outings:
                rows = store.load_outings()
                rows.extend(new_outings)
                store.save_outings(rows)
                outing_added += len(new_outings)
                book = store.load_ledger()
                for plan in plans:
                    book['last_outing'][plan.user_name] = {
                        'date': plan.outing_date.isoformat(),
                        'kind': plan.kind,
                    }
                store.save_ledger(book)

        # Step 3: schedules for each day (Mon..Sun) of this week
        active = store.active_users()
        for d_offset in range(7):
            d = wk + datetime.timedelta(days=d_offset)
            iso = d.isoformat()
            if store.schedule_on(d) is not None:
                sched_skipped += 1
                continue
            group = compute_today_group(d)
            is_weekend = d.weekday() >= 5
            statuses = build_statuses(d, active, longnight_names=set())
            book = store.load_ledger()
            sched = solve_day(
                group, is_weekend, active, statuses,
                work_count_before=ledger.work_count_for_solver(book, active),
            )
            if sched is None:
                sched_failed.append(iso)
                continue
            store.save_schedule(d, work_group[group], is_weekend, sched)
            if iso not in book.get('recorded_dates', []):
                away = {n for n, s in statuses.items()
                        if s in (STATUS_ABSENT, STATUS_OUTING, STATUS_STRIKE)}
                candidates = [u for u in active if u.name not in away]
                sf_names = {n for n, s in statuses.items() if s == STATUS_STRIKE}
                sf_users = [u for u in active if u.name in sf_names]
                ledger.update(
                    book, sched, candidates, group, iso, sf_users=sf_users,
                )
                store.save_ledger(book)
            sched_added += 1

    return RedirectResponse(
        f'/?auto_sf={sf_added}&auto_out={outing_added}'
        f'&auto_sched={sched_added}&auto_skip={sched_skipped}'
        f'&auto_fail={len(sched_failed)}',
        status_code=303,
    )


@app.post('/schedules/wipe')
def schedules_wipe():
    """
    Delete ALL saved schedules and reset the cumulative ledger. Useful when
    the data has gone out of sync — e.g. after big rule changes (the per-day
    balance constraint, the SF crediting system) — and you want to regenerate
    everything from scratch with the current code.

    Outings, strike-force assignments, vacations, and users are NOT touched.
    Only schedules.json and ledger.json get wiped.
    """
    import os
    for path in (store.SCHEDULES_PATH, store.LEDGER_PATH):
        if os.path.exists(path):
            os.remove(path)
    return RedirectResponse('/schedules?wiped=1', status_code=303)


@app.post('/schedules/generate-range')
def schedules_generate_range(start: str = Form(...), end: str = Form(...)):
    """
    Generate schedules for every date in [start, end] inclusive.
    Skips dates that already have a saved schedule (does NOT overwrite).
    Updates the ledger chronologically so fairness across days remains correct.
    Returns a redirect to /schedules with a summary in the URL fragment.
    """
    start_d = parse_date(start)
    end_d = parse_date(end)
    if start_d > end_d:
        raise HTTPException(400, "시작일은 종료일과 같거나 이전이어야 합니다")

    # Hard cap so a typo can't trigger 1000 solver runs by accident.
    days_in_range = (end_d - start_d).days + 1
    if days_in_range > 60:
        raise HTTPException(400, f"한 번에 최대 60일까지만 생성 가능합니다 (요청: {days_in_range}일)")

    existing = store.load_schedules()
    book = store.load_ledger()
    active = store.active_users()

    succeeded: list[str] = []
    skipped_existing: list[str] = []
    failed: list[tuple[str, str]] = []  # (date, reason)

    # Iterate in chronological order so the fairness ledger advances day-by-day
    # exactly as it would on a real day-after-day rollout.
    cur = start_d
    while cur <= end_d:
        iso = cur.isoformat()
        if iso in existing:
            skipped_existing.append(iso)
            cur += datetime.timedelta(days=1)
            continue

        group = compute_today_group(cur)
        is_weekend = cur.weekday() >= 5
        statuses = build_statuses(cur, active, longnight_names=set())

        sched = solve_day(
            group, is_weekend, active, statuses,
            work_count_before=ledger.work_count_for_solver(book, active),
        )
        if sched is None:
            failed.append((iso, '실현 불가능 — 인원/제약 확인 필요'))
            cur += datetime.timedelta(days=1)
            continue

        store.save_schedule(cur, work_group[group], is_weekend, sched)
        # Fold into ledger only if this date hasn't been recorded before
        if iso not in book.get('recorded_dates', []):
            away = {n for n, s in statuses.items() if s in (STATUS_ABSENT, STATUS_OUTING, STATUS_STRIKE)}
            candidates = [u for u in active if u.name not in away]
            sf_names = {n for n, s in statuses.items() if s == STATUS_STRIKE}
            sf_users = [u for u in active if u.name in sf_names]
            ledger.update(book, sched, candidates, group, iso, sf_users=sf_users)
            store.save_ledger(book)

        succeeded.append(iso)
        cur += datetime.timedelta(days=1)

    # Pack a brief summary into the redirect URL so the list page can show it
    summary_parts = [f"ok={len(succeeded)}",
                     f"skip={len(skipped_existing)}",
                     f"fail={len(failed)}"]
    return RedirectResponse(f'/schedules?{"&".join(summary_parts)}', status_code=303)


@app.get('/schedule', response_class=HTMLResponse)
def schedule_today(request: Request):
    return RedirectResponse(f'/schedule/{datetime.date.today().isoformat()}', status_code=303)


@app.get('/schedule/{date_str}', response_class=HTMLResponse)
def schedule_view(request: Request, date_str: str):
    d = parse_date(date_str)
    group = compute_today_group(d)
    is_weekend = d.weekday() >= 5

    saved = store.schedule_on(d)
    active = store.active_users()
    statuses = build_statuses(d, active, longnight_names=set())
    issues = feasibility_report(group, is_weekend, active, statuses)

    times = Timetable[group][0]
    weekend_idx = 1 if is_weekend else 0
    place_cap = placetable[group][weekend_idx]

    by_slot_site = None
    per_person = None
    if saved:
        # Invert the saved assignments for display
        assignments = saved['assignments']
        by_slot_site = {(s, l): [] for s in range(4) for l in range(4)}
        for name, slots in assignments.items():
            for s, l in slots:
                by_slot_site[(s, l)].append(name)
        per_person = sorted(assignments.items(), key=lambda kv: -len(kv[1]))

    return templates.TemplateResponse(request, 'schedule.html', {
        'date': d,
        'group_letter': work_group[group],
        'is_weekend': is_weekend,
        'has_schedule': saved is not None,
        'active': active,
        'statuses': statuses,
        'issues': issues,
        'times': times,
        'slot_24h': SLOT_24H[group],
        'place_cap': place_cap,
        'site_names': SITE_NAMES,
        'by_slot_site': by_slot_site,
        'per_person': per_person,
    })


@app.post('/schedule/{date_str}/generate')
def schedule_generate(date_str: str):
    d = parse_date(date_str)
    group = compute_today_group(d)
    is_weekend = d.weekday() >= 5
    active = store.active_users()
    statuses = build_statuses(d, active, longnight_names=set())
    book = store.load_ledger()

    schedule = solve_day(
        group, is_weekend, active, statuses,
        work_count_before=ledger.work_count_for_solver(book, active),
    )
    if schedule is None:
        # Re-render the page with an error (use the existing route)
        raise HTTPException(409, "현재 명단으로 만들 수 있는 근무표가 없습니다. 휴가/외출 인원을 조정하세요.")

    store.save_schedule(d, work_group[group], is_weekend, schedule)

    # Update the ledger only if this date hasn't been recorded yet (avoid
    # double-counting if the user clicks Generate twice).
    if d.isoformat() not in book.get('recorded_dates', []):
        # Vacation/outing/strike are all away from regular duty.
        # candidates = people who actually showed up for duty today
        # sf_users   = people on strike-force standby today (credited as work)
        away = {n for n, s in statuses.items() if s in (STATUS_ABSENT, STATUS_OUTING, STATUS_STRIKE)}
        candidates = [u for u in active if u.name not in away]
        sf_names = {n for n, s in statuses.items() if s == STATUS_STRIKE}
        sf_users = [u for u in active if u.name in sf_names]
        ledger.update(book, schedule, candidates, group, d.isoformat(), sf_users=sf_users)
        store.save_ledger(book)

    return RedirectResponse(f'/schedule/{d.isoformat()}', status_code=303)


# ---------------------------------------------------------------------------
# Ledger view
# ---------------------------------------------------------------------------

@app.get('/ledger', response_class=HTMLResponse)
def ledger_view(request: Request):
    book = store.load_ledger()
    sf_credit_map = book.get('sf_credit_slots', {})

    # Count strike-force STINTS per user — each StrikeForce row = 1 stint
    # (typically a 1-week assignment), regardless of how many days it covers.
    sf_stints_by_user: dict = {}
    for sf in store.load_strikeforce():
        sf_stints_by_user[sf.user_id] = sf_stints_by_user.get(sf.user_id, 0) + 1

    users_by_name = {u.name: u for u in store.load_users()}

    rows = []
    for name, work in book['work_count'].items():
        sf_credit = sf_credit_map.get(name, 0)
        avail = book['available_days'].get(name, 0)
        matches = book['pref_match_count'].get(name, 0)
        # Combined for fairness, separate for match-rate display.
        combined = work + sf_credit
        utilization = combined / avail if avail > 0 else 0.0
        match_rate = (matches / work) if work > 0 else 0.0

        user = users_by_name.get(name)
        sf_stints = sf_stints_by_user.get(user.id, 0) if user else 0

        rows.append({
            'name': name,
            'work': work,                 # 실제 근무한 슬롯 (타격대 제외)
            'sf_credit': sf_credit,       # 타격대 크레딧 슬롯 (공정성 보정용)
            'sf_stints': sf_stints,       # 타격대를 한 횟수 (1회 = 한 주)
            'combined': combined,         # 총 인정 슬롯 (real + SF credit)
            'avail': avail,
            'utilization': utilization,   # combined / avail
            'matches': matches,
            'match_rate': match_rate,     # matches / 실근무 (타격대 제외)
        })
    rows.sort(key=lambda r: -r['utilization'])
    return templates.TemplateResponse(request, 'ledger.html', {
        'rows': rows,
        'days_recorded': book.get('days_recorded', 0),
        'last_date': book.get('last_date'),
    })
