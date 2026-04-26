# 718 Duty Scheduler

A daily duty-roster planner for the **718 auxiliary police 2분대** (~21 officers).
Replaces the old random-greedy scheduler that hung on tight inputs with a
constraint-programming solver, a small JSON-backed store, and a local web UI
for managing vacations / outings / strike-force rotations.

The whole thing runs on a single laptop — no database, no auth, no cloud.

---

## What it does

- **Generates a daily duty schedule** that respects every hard rule (per-site
  capacity, no double-booking, status overrides, per-day balance) and softly
  prefers each person's favourite shift hours.
- **Tracks fairness across days** so people who lagged behind one week get
  prioritised the next, even after vacations or strike-force standby.
- **Auto-plans 외출 (outings)** week by week — Saturday + Sunday balanced,
  rotation-aware (someone who went Sat last week prefers Sun this week),
  weekday fallback when the weekend is already full.
- **Auto-plans 타격대 (strike-force standby)** with the same rotation rule;
  configurable size and shift length.
- **One-click "전부 자동 배정"** — chain SF → 외출 → 근무표 generation across
  any range of upcoming weeks.

---

## Quickstart

Requires **Python 3.10+**.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. One-time: bootstrap data/users.json from the static roster in constants.py
python seed_data.py

# 3. Start the web UI on http://127.0.0.1:8000
python -m uvicorn web_app:app --reload
```

Open <http://127.0.0.1:8000> and you're done. The dashboard shows today's
group + today's schedule (or a generate button), plus a one-click "전부 자동
배정" form for the upcoming weeks.

For a CLI sanity check without the web UI:

```bash
python Main_program.py
```

---

## Daily / weekly workflow

Typical sequence for one administrator running this:

1. **`/users`** — once, then again whenever someone joins/leaves the platoon.
   Set per-person preference hours via the edit page.
2. **`/vacations`** — register 휴가 / 사고 / 교육 date ranges as they come up.
   Bulk-delete via checkboxes when records become stale.
3. **`/strikeforce`** — auto-plan or manually edit the weekly 타격대 rotation.
   Set size / shift length under "설정".
4. **`/outings`** — auto-plan weekend 외출 for one or many upcoming weeks.
5. **Dashboard "전부 자동 배정"** — runs steps 3 + 4 + the daily schedule
   generator across every day in your chosen range. Idempotent: existing
   weeks/schedules are preserved, only new ones are created.
6. **`/schedules`** — review past schedules, regenerate one day, or
   wipe-and-rebuild the whole thing if rules change.
7. **`/ledger`** — verify fairness over time. Activity rate (`활용률`) should
   stay tightly clustered (~0.05 spread is normal, 0.20+ suggests something
   skewing the input).

The **달력 page** is the calendar grid (rows = officers, columns = days);
click any cell to cycle `none → 휴가 → 외출 → none`.

---

## Status types

Every officer is in exactly one state on a given day:

| Status | Korean | What it means | Solver effect |
|---|---|---|---|
| `normal` | (default) | On duty | Works 1–4 slots; balanced within 1 of every other normal worker |
| `absent` | 사고/휴가 | Vacation, sick, training | 0 slots; doesn't count as available |
| `outing` | 외출 | Off-base for the day | 0 slots; doesn't count as available |
| `strike` | 타격대 | Quick-reaction standby | 0 slots; counted as available + credited in fairness |
| `longnight` | 긴밤자 | Sleep-through-the-night exemption (Group B only) | 1–2 slots, never the 02:00 / 04:00 slots |

See [docs/DOMAIN.md](docs/DOMAIN.md) for the rotation calendar, time-slot
encoding, and the strike-force credit system.

---

## Configuration

| What | Where |
|---|---|
| Time slots per group, capacity per site | `constants.py` (static unit regulations) |
| Initial roster + preferences | `constants.py` → seeded into `data/users.json` once |
| Strike-force size / shift length | `data/settings.json` (or via the UI: `/strikeforce` → 설정) |
| Solver wall-clock cap (default 30s) | `solver.py:SOLVER_TIMEOUT_SECONDS` |
| Fairness vs preference weight (default 10) | `solver.py:solve_day(..., fairness_weight=10)` |

---

## File layout

```
.
├── Main_program.py          ← CLI entry point
├── web_app.py               ← FastAPI app
├── solver.py                ← CP-SAT model (the core algorithm)
├── store.py                 ← JSON-backed persistence
├── ledger.py                ← cross-day fairness counters
├── domain.py                ← shared helpers used by CLI + web
├── outing_scheduler.py      ← weekly 외출 auto-planner
├── strikeforce_scheduler.py ← weekly 타격대 auto-planner
├── seed_data.py             ← bootstrap data/users.json
├── constants.py             ← static unit regulations + initial roster
├── requirements.txt
├── README.md  (this file)
├── docs/
│   ├── ARCHITECTURE.md      ← module map + request lifecycle
│   ├── DOMAIN.md            ← time-slot encoding, status types, fairness
│   └── SOLVER.md            ← CP-SAT model decisions
├── tests/
│   ├── conftest.py          ← isolated tmp-dir fixtures
│   └── test_smoke.py        ← 17-test smoke suite
├── templates/               ← Jinja2 + HTMX
├── static/style.css
└── data/
    ├── users.json           ← roster + preferences (tracked)
    └── (vacations|outings|strikeforce|schedules|ledger|settings).json
                             ← runtime state (gitignored)
```

---

## Tests

```bash
pytest                       # 17 tests, < 1 second
pytest -v                    # verbose
```

Each test runs against a fresh `tmp_path` data directory — they never touch
the real `data/`.

---

## Security / deployment note

This app has **no authentication**. Run it on `127.0.0.1` only. uvicorn's
default bind is safe; do **not** pass `--host 0.0.0.0`. If you need
multi-user access, put a reverse proxy with auth in front.

The store writes JSON files under `data/`. They are atomic (`tmp` + rename
+ fsync) so a crash mid-write can't leave a half-written file. If a file
ever becomes corrupted by hand-editing, the routes will fail with a clear
Korean error message pointing at the offending file rather than crashing
silently.

---

## Limits

- **Single user.** No locking around file writes — concurrent operators
  could trample each other.
- **JSON files, not a database.** Fine up to thousands of records; well
  beyond that you'd want SQLite.
- **One platoon's worth of regulations baked in** (constants.py). Adapting
  to another unit means editing the time tables and capacity matrices.
- **No Korean-holiday calendar.** Vacations and rotations follow the
  platoon's known anchor (2020-01-01 = Group B); no holiday handling.
