# Domain Model

This document explains the unit-specific concepts the code encodes. Read
once and you'll understand why `solver.py` is laid out the way it is.

## The platoon and the day

The 718 auxiliary police 2분대 has roughly 21 active officers. Every day,
some subset of them mans four duty posts across four time slots. Officers
not on duty are either on personal leave (휴가), short off-base time
(외출), or quick-reaction standby (타격대).

## The 3-day group rotation

The platoon cycles through three groups every 3 days:

- **Group A** — typically morning + late-night slots
- **Group B** — typically afternoon + middle-of-the-night slots
- **Group C** — typically afternoon + evening slots

Anchor: **2020-01-01 was a Group B day** (the platoon's known reference).
Every other date is computed from there:

```python
# domain.py
def today_group(d: date) -> int:
    """0 = A, 1 = B, 2 = C."""
    return ((d - date(2020, 1, 1)).days + 1) % 3
```

So `2020-01-02` = C, `2020-01-03` = A, `2020-01-04` = B, etc.

## Time slots and their hour encoding

Each group has **4 time slots** per day, each covering a 2-hour block. The
in-code labels are written in 12-hour-clock notation (no AM/PM). The actual
24-hour wall-clock equivalents are translated for display via
`solver.SLOT_24H`.

| Group | Code label (`Time*`)       | 24-hour clock           |
|-------|----------------------------|-------------------------|
| A     | `[6, 4, 8, 12]`            | 06:00, 16:00, 20:00, 24:00 |
| B     | `[8, 12, 2, 4]`            | 08:00, 12:00, 02:00, 04:00 |
| C     | `[10, 2, 6, 22]`           | 10:00, 14:00, 18:00, 22:00 |

The one quirk: Group C's last slot is written as `22` rather than `10`
because `10` is already taken by C's morning slot. Disambiguation, not
a different convention.

Each `fav.times3` / `fav.times2` preference list in `constants.py` uses
the same label encoding — when a user lists `[6, 4, 8]` for Group A as
their `times3` preference, that means "I prefer to be on the 06:00,
16:00, and 20:00 slots when I'm 3-duty in Group A."

## Duty posts (사이트)

Four physical posts, in this fixed order everywhere in the code:

```
[정출, 별정, 별후, 서남문]
```

Per-slot, per-site capacities live in `constants.py:placetable`. Weekday
and weekend matrices are different — weekends have lower demand for most
slots. Example for Group A weekday:

```python
placeA = [
    [2, 2, 2, 1],   # 06시: 정출=2, 별정=2, 별후=2, 서남문=1  (sum 7)
    [5, 3, 2, 1],   # 16시: 11 person-slots
    [3, 2, 2, 1],   # 20시: 8
    [2, 2, 1, 1],   # 24시: 6
]
# total demand = 32 person-slots/day
```

## Status types

Every active officer is in exactly one state on a given day:

| Status | Korean | Solver effect | Counts as available_day? |
|---|---|---|---|
| `normal` | (default) | Works 1–4 slots; per-day max−min ≤ 1 | ✓ |
| `absent` | 사고/휴가 | 0 slots | ✗ |
| `outing` | 외출 | 0 slots | ✗ |
| `strike` | 타격대 | 0 slots | ✓ (with credit — see below) |
| `longnight` | 긴밤자 | 1–2 slots, never the 02:00/04:00 slots | ✓ |

`absent` and `outing` are functionally identical to the solver — both mean
"works 0 slots today". The labels are kept distinct only so the outing
scheduler can track Sat/Sun rotation fairness independently from
medical/training absences.

`strike` is also 0 slots but its bookkeeping is different — see the
fairness section below.

`longnight` is only meaningful in Group B (the only group with 02:00 and
04:00 slots). In other groups it's silently treated as `normal`.

## The per-day balance rule

A hard solver constraint: among officers in `normal` status on the same
day, **max − min ≤ 1 slot**. Nobody is ever 4-duty while a peer is
1-duty on the same day. Long-night and SF members are not in this
balance set (long-night because they're capped lower by construction;
SF because they don't show up on the schedule).

## Fairness across days

`ledger.py` keeps three numbers per officer:

- `work_count` — actual duty slots ever worked
- `sf_credit_slots` — virtual credit accumulated for strike-force days
- `available_days` — days the officer was eligible to work
                     (i.e. not 휴가 / not 외출, but SF days DO count)

The solver's fairness signal is the **utilisation rate**:

```
utilisation = (work_count + sf_credit_slots) / available_days
```

The CP-SAT model minimises the spread (max − min) of this rate across
the platoon when assigning today's duty. Result: people who are behind
get prioritised; people who are ahead get less. Vacation-normalised, so
returning vacationers don't get hammered with extra duty to "catch up".

### Why strike-force credit?

Without it, a 타격대 member's `work_count` would stagnate during their
standby week. The fairness signal would mark them as "behind" the moment
they came back, and the solver would dump extra slots on them — punishing
them for serving on standby.

Fix: every day the ledger is updated, each SF member gets credited the
**day's average slots-per-worker** in `sf_credit_slots`. Their utilisation
rate stays comparable to peers throughout. The credit lives in a separate
field (not `work_count`) so the **preference-match rate** (`matches /
work_count`) still reflects their actual on-duty performance only.

See `ledger.py:work_count_for_solver` for the exact integer arithmetic.

## Outings — the weekly plan

`outing_scheduler.plan_week(monday)` produces a list of 외출 assignments
for the week starting on `monday`:

1. Compute the maximum feasible outings for each weekend day (under the
   loosened solver rule that allows 0–4 slots/person, this is
   `available - ceil(demand/4)`).
2. Sort the candidate pool by least-recent-outing first.
3. Iterate the pool, assigning each person to whichever weekend day they
   prefer per the rotation rule:
   - Last outing was Sat → prefer Sun this week
   - Last outing was Sun → prefer Sat
   - No prior outing → pick the day with more remaining spare
4. Anyone still unassigned (weekend full, or vacation/SF that weekend)
   gets pushed to the **next-week weekday** with spare. This is the "at
   least everyone gets out eventually" guarantee.

Re-running on the same week is a no-op — the route auto-shifts past
already-filled weeks before planning, so accidental double-clicks add
zero new outings.

## Strike-force — the weekly plan

`strikeforce_scheduler.plan_week(monday)` is simpler: pick the
**`strike_force_size` officers who have been on SF least recently**,
covering Mon–Sun (or however long `strike_force_days` is configured).
Skip anyone on vacation any day of the week, and skip anyone already
serving SF that week.

Configuration via `data/settings.json`:

```json
{
    "strike_force_size": 2,
    "strike_force_days": 7
}
```

Both also editable from `/strikeforce → 설정` in the web UI.
