# Architecture

## Layers

The codebase is intentionally thin. Five layers, no framework magic:

```
┌────────────────────────────────────────────────────────────┐
│  Presentation                                               │
│    web_app.py  (FastAPI routes + Jinja2 templates)         │
│    Main_program.py  (CLI driver)                            │
└─────────────────────┬───────────────────────────────────────┘
                      │ uses
┌─────────────────────▼───────────────────────────────────────┐
│  Orchestration                                              │
│    domain.py     — today_group, build_statuses, split_for_ledger │
│    outing_scheduler.py  — weekly 외출 plan                    │
│    strikeforce_scheduler.py  — weekly 타격대 plan             │
│    seed_data.py  — one-shot bootstrap                        │
└─────────────────────┬───────────────────────────────────────┘
                      │ uses
┌─────────────────────▼───────────────────────────────────────┐
│  Pure logic (no I/O)                                        │
│    solver.py  — CP-SAT model                                 │
│    ledger.py  — fairness counters                            │
└─────────────────────┬───────────────────────────────────────┘
                      │ uses
┌─────────────────────▼───────────────────────────────────────┐
│  Persistence                                                │
│    store.py  — JSON file I/O (atomic writes)                 │
└─────────────────────┬───────────────────────────────────────┘
                      │ reads
┌─────────────────────▼───────────────────────────────────────┐
│  Static rules                                               │
│    constants.py  — time tables, capacity matrices, roster    │
└─────────────────────────────────────────────────────────────┘
```

The dependency graph is strict: **lower layers never import upper layers**.
`solver.py` knows nothing about HTTP. `store.py` knows nothing about the
solver. This is what lets `tests/conftest.py` swap the store's path
constants at fixture time and have every layer above just work.

## Request lifecycle

The `POST /auto-plan-all` route is the most representative end-to-end path.
For one click on the dashboard's "전부 자동 배정" button:

```
Browser
   │  POST /auto-plan-all  (start_week, num_weeks)
   ▼
web_app.auto_plan_all
   │  for each week in range:
   │    ├─ strikeforce_scheduler.plan_week(monday)
   │    │     uses store.load_strikeforce + store.active_users
   │    │     returns list[StrikeForce]
   │    │  ↓
   │    │  store.save_strikeforce(...)
   │    │
   │    ├─ outing_scheduler.plan_week(monday)
   │    │     uses store.load_outings + store.load_ledger
   │    │     returns list[OutingPlan]
   │    │  ↓
   │    │  store.save_outings(...) + store.save_ledger(last_outing bumped)
   │    │
   │    └─ for each day in week:
   │         ├─ domain.build_statuses(date, active)
   │         │     queries store for vacation/outing/strike on this date
   │         ├─ ledger.work_count_for_solver(book, active)
   │         ├─ solver.solve_day(group, weekend, active, statuses, ...)
   │         │     pure CP-SAT call, returns dict[name, list[(slot, site)]]
   │         ├─ store.save_schedule(date, ...)
   │         └─ ledger.update(book, sched, candidates, ..., sf_users=...)
   │              splits roster via domain.split_for_ledger
   │
   ▼
303 → /  (dashboard with summary banner)
```

Every step is idempotent on its own — re-running `/auto-plan-all` with the
same range advances `planned/added` counts but preserves existing data.

## Where state lives

| File | Purpose | Tracked in git? |
|---|---|---|
| `data/users.json` | Roster + preferences | Yes (initial seed) |
| `data/vacations.json` | Date-range vacations | No (runtime state) |
| `data/outings.json` | Single-day outing assignments | No |
| `data/strikeforce.json` | Weekly 타격대 assignments | No |
| `data/schedules.json` | Generated daily duty schedules | No |
| `data/ledger.json` | Cumulative fairness counters | No |
| `data/settings.json` | Strike-force size + duration | No |

The `tracked / untracked` split is encoded in `.gitignore`. The roster
(`users.json`) is the only piece of mutable state that's worth versioning;
everything else is either ephemeral runtime state or can be regenerated.

## Why no database

For ~21 people and ~years-of-history-worth of records (low thousands of
rows total) JSON files are simpler than SQLite:

- No schema migrations.
- Diffable in git, greppable on the filesystem.
- Backup = copy `data/`.
- Editable in any text editor for one-off corrections.

If you ever need concurrent writers or millions of rows, swap `store.py`
for SQLAlchemy + SQLite without touching anything else — the rest of the
codebase only knows the function signatures `load_X()`, `save_X()`, etc.

## Why no auth

Single administrator, single laptop, `127.0.0.1` only. Adding auth would
add a dependency tree (passlib, python-jose, etc.) for zero gain. If you
ever do need multi-user access, put a reverse proxy with auth in front
rather than baking it in.

## Templates

Server-rendered Jinja2. HTMX (loaded from CDN in `templates/base.html`)
handles in-page updates so individual cell-toggles don't reload the
whole page. There is no JavaScript build step, no React, no bundler.

`templates/_calendar_cell.html` is the only HTMX-returned partial; every
other template is a full page extending `templates/base.html`.

## Threading and async

The solver and the store are both **synchronous**. FastAPI routes are
defined as `def`, not `async def`, so each request runs in a worker
thread (the default `anyio.to_thread`). The CP-SAT call has its own
wall-clock cap (`solver.SOLVER_TIMEOUT_SECONDS`, default 30s) so a
pathological input cannot pin a worker forever.

For a single-user local app this is the right trade-off — async would
add complexity without any throughput benefit, and json read/write +
solver CPU dominate any perceivable latency.
