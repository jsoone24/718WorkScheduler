# The CP-SAT Solver

Why this file exists: the solver is the heart of the project, and it
encodes a non-trivial decision (constraint programming over a fairness
objective) that's easy to mess up if you don't know which knobs are
which. This document is the one-stop reference for "what does
`solve_day` actually do" and "what changes if I tweak X".

If you're just running the app, you don't need this. If you're tuning
fairness vs preferences or adding a new status type, start here.

## What problem we're solving

Every day, distribute officers across:

- **4 time slots** (per group's clock hours)
- **4 duty sites** (정출 / 별정 / 별후 / 서남문)
- **per-site capacity** that must be filled exactly

… while:

- respecting each officer's status (`absent` / `outing` / `strike` /
  `longnight`)
- balancing the slot count among officers (no one does 4 while a peer does 1)
- maximising preference matches (people land on their favourite hours)
- staying fair across days (utilisation rates converge)

This is a **constraint-satisfaction problem with a soft objective**.
CP-SAT is a perfect fit — small problem (~21 × 4 × 4 = 336 booleans),
hard constraints expressible as linear equalities, soft objective is a
linear sum.

## Decision variable

```python
x[p, s, l] = NewBoolVar(...)   # 1 ⇔ person p works site l in slot s
```

For 21 people × 4 slots × 4 sites this is 336 boolean variables. Solve
time on real inputs is tens of milliseconds.

## Hard constraints

### A. No double-booking
For each `(person p, slot s)`: at most one site assigned.

```python
sum(x[p, s, l] for l in range(4)) <= 1
```

### B. Per-site capacity
For each `(slot s, site l)`: exactly the required number of people.

```python
sum(x[p, s, l] for p) == place_cap[s][l]
```

Equality, not `<=` — every duty post must be staffed.

### C. Status overrides

| Status | Constraint |
|---|---|
| `absent` / `outing` / `strike` | `total_slots(p) == 0` |
| `longnight` | `1 ≤ total_slots(p) ≤ 4`, AND `x[p, night_slot, *] = 0` for the 02/04 slots |
| `normal` | `1 ≤ total_slots(p) ≤ 4` |

### D. Per-day balance (the "no 4-vs-1" rule)
Among `normal` workers only: max − min ≤ 1.

```python
max_normal = NewIntVar(...); AddMaxEquality(max_normal, normal_totals)
min_normal = NewIntVar(...); AddMinEquality(min_normal, normal_totals)
Add(max_normal - min_normal <= 1)
```

Long-night is excluded — it's already capped at 2, which would conflict
with normals doing 3 or 4 on tight days.

## Soft objective

Single scalar to maximise:

```
objective = pref_score - fairness_weight * spread
```

### `pref_score` — preferences
For every `(person p, slot s, site l)` where person p has the slot's
clock hour in their `times3` ∪ `times2` preference set, add `x[p, s, l]`
to the score. Each preferred-hour assignment contributes +1.

### `spread` — cross-day fairness
A virtual count per person (vacation-normalised, see
[DOMAIN.md](DOMAIN.md#fairness-across-days)) is fed in via
`work_count_before`. The spread term penalises growing the
(max − min) of `virtual_before + slots_today` across all people.

Concretely:

```python
combined[p]  = work_count[p] + sf_credit_slots[p]
total_avail  = sum(available_days[p] for p)
total_combined = sum(combined[p] for p)
virtual[p]  = combined[p] * total_avail - total_combined * available_days[p]
```

The `virtual` value is signed: positive means "above fair share", negative
means "below". Multiplying through by `total_avail` keeps everything
integer (CP-SAT requires integers).

The IntVar bounds for the after-counts are computed from the actual range
of incoming `virtual` values + 4 slots of headroom. That headroom matters:
without it, vacation-normalised virtuals (which can be very negative) get
silently rejected as infeasible.

### `fairness_weight`
Default `10`. Each unit of cumulative spread costs 10 preference matches.
This makes fairness dominate preferences in normal operation but lets
preferences break ties when fairness is already balanced. Raise to bias
harder toward equal utilisation; lower to honour preferences more.

## Solve parameters

```python
solver = cp_model.CpSolver()
solver.parameters.num_search_workers = 1            # deterministic with seed
solver.parameters.random_seed = seed                # if provided
solver.parameters.max_time_in_seconds = 30.0        # SOLVER_TIMEOUT_SECONDS
status = solver.Solve(model)
```

Single-threaded so a given seed produces a given schedule (useful for
reproducibility + tests). 30-second wall-clock cap is overkill for real
inputs (tens of milliseconds) and only kicks in on pathological corner
cases.

## Failure modes

`solve_day(...)` returns `None` whenever CP-SAT reports anything other
than `OPTIMAL` / `FEASIBLE`. The most common cause is the user's roster
being structurally infeasible — e.g. demand 30 with only 7 normal
workers (max supply 28 < demand 30). `feasibility_report(...)` is the
fast check that runs before `solve_day` and surfaces these cases as
human-readable warnings instead of silent infeasibility.

## When to touch this file

- **Add a new status type** — add a `STATUS_*` string, branch in the
  status-overrides loop (Constraint C), and decide whether it counts in
  the per-day balance set (Constraint D).
- **Change preference handling** — modify the `pref_terms` building loop.
- **Change fairness behaviour** — adjust the `virtual` formula in
  `ledger.work_count_for_solver`, or the `fairness_weight` default.
- **Add a new hard constraint** — add it to the "Hard constraint" section
  in `solve_day`. Keep the constraint independent of the objective —
  hard rules go above the `Maximize(...)` call.
- **Change capacity matrices** — those live in `constants.py:placetable`,
  not in solver code. The solver reads them at runtime.
