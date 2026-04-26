"""
constants.py — static domain rules for the 718 platoon scheduler.

These tables encode unit regulations (rotation cycle, time slots per group,
duty-post capacity per slot) and are NOT user-editable through the app.
The platoon roster + per-person preferences live in `data/users.json` and
are seeded from the `p2` list at the bottom of this file via `seed_data.py`.

NAMING CONVENTIONS
------------------
* `TimeA / TimeB / TimeC`  — clock-hour LABELS (12-hour clock without AM/PM)
                             for each group's four 2-hour duty slots. See
                             the 24-hour translation table in solver.SLOT_24H.
* `WorkA / WorkB / WorkC` (and `_weekend`)
                           — per-slot total person count. Equal to the row
                             sums of the corresponding `place*` matrix; kept
                             only for backward compatibility with code that
                             reads them directly. The CP-SAT solver uses
                             `placetable` exclusively.
* `placeA / placeB / placeC` (and `_weekend`)
                           — 4×4 capacity matrices: `place[slot][site]`.
                             Site order is fixed: [정출, 별정, 별후, 서남문].
* `Timetable`              — 3-tuple-of-tuples indexed by group: each entry
                             is `[TimeX, WorkX_weekday, WorkX_weekend]`.
* `placetable`             — 3-tuple indexed by group: each entry is
                             `[placeX_weekday, placeX_weekend]`.
* `work_group`             — group-index → letter mapping ('A' / 'B' / 'C').
"""

# Group-index → letter. Index ordering matches `Timetable` and `placetable`
# below: 0 = A, 1 = B, 2 = C. The platoon's 3-day rotation is anchored on
# 2020-01-01 = Group B (see `domain.today_group`).
work_group = {0: 'A', 1: 'B', 2: 'C'}

# ---------------------------------------------------------------------------
# Time slots and per-slot totals (per group, weekday vs weekend)
# ---------------------------------------------------------------------------

TimeA = [6, 4, 8, 12]
WorkA = [7, 11, 8, 6]
WorkA_weekend = [6, 8, 8, 6]

TimeB = [8, 12, 2, 4]
WorkB = [11, 11, 6, 6]
WorkB_weekend = [8, 8, 6, 6]

TimeC = [10, 2, 6, 22]
WorkC = [11, 11, 11, 6]
WorkC_weekend = [8, 8, 8, 6]

Timetable = [[TimeA, WorkA, WorkA_weekend],
             [TimeB, WorkB, WorkB_weekend],
             [TimeC, WorkC, WorkC_weekend]]

# ---------------------------------------------------------------------------
# Per-slot, per-site capacities (site order: 정출, 별정, 별후, 서남문)
# ---------------------------------------------------------------------------

placeA = [[2, 2, 2, 1], [5, 3, 2, 1], [3, 2, 2, 1], [2, 2, 1, 1]]
placeB = [[5, 3, 2, 1], [5, 3, 2, 1], [2, 2, 1, 1], [2, 2, 1, 1]]
placeC = [[5, 3, 2, 1], [5, 3, 2, 1], [5, 3, 2, 1], [2, 2, 1, 1]]

placeA_weekend = [[2, 2, 1, 1], [3, 2, 2, 1], [2, 2, 2, 1], [2, 2, 1, 1]]
placeB_weekend = [[3, 2, 2, 1], [3, 3, 2, 1], [2, 2, 2, 1], [2, 2, 1, 1]]
placeC_weekend = [[3, 2, 2, 1], [3, 2, 2, 1], [2, 2, 2, 1], [2, 2, 1, 1]]

placetable = [[placeA, placeA_weekend],
              [placeB, placeB_weekend],
              [placeC, placeC_weekend]]


# ---------------------------------------------------------------------------
# Initial roster + per-person preferences (read once by `seed_data.py`)
# ---------------------------------------------------------------------------

class fav:
    """
    Initial-seed record for one platoon member.

    Used ONLY by `seed_data.py` to bootstrap `data/users.json` on first run.
    After that, the canonical user records live in the JSON store and this
    class is not consulted again.

    `t3` / `t2` are list-of-3 lists, indexed in [A, B, C] group order; each
    inner list is the preferred clock-hour labels for that group when the
    person ends up as 3-duty (`t3`) or 2-duty (`t2`).

    Default `t3` / `t2` are `None` to avoid the classic mutable-default-arg
    Python footgun; the hard-coded p2 entries below always pass them.
    """
    def __init__(self, name, t3=None, t2=None):
        if t3 is None: t3 = [[], [], []]
        if t2 is None: t2 = [[], [], []]
        self.name = name
        self.times3 = {'A': t3[0], 'B': t3[1], 'C': t3[2]}
        self.times2 = {'A': t2[0], 'B': t2[1], 'C': t2[2]}


# Initial 2분대 (second platoon) roster. Order here becomes `display_order`
# in the seeded JSON so the UI shows them in the same sequence the unit
# physically lines up. Edit data/users.json (or use the web UI) to change
# membership after seeding — these constants are not re-read.

a1  = fav('Member01', [[6, 4, 8],  [8, 12, 4], [10, 6, 22]], [[6, 8], [8, 4],  [2, 22]])
a2  = fav('Member02', [[6, 4, 8],  [8, 12, 2], [10, 2, 6]],  [[4, 8], [8, 2],  [10, 2]])
a3  = fav('Member03', [[6, 4, 8],  [8, 12, 4], [2, 6, 22]],  [[6, 8], [8, 4],  [2, 22]])
a4  = fav('Member04', [[6, 4, 8],  [8, 12, 2], [10, 2, 6]],  [[6, 4], [8, 2],  [10, 2]])
a5  = fav('Member05', [[6, 8, 12], [8, 12, 2], [10, 6, 22]], [[6, 8], [12, 2], [6, 22]])

a6  = fav('Member06', [[6, 4, 8],  [8, 12, 2], [10, 2, 6]],  [[6, 8], [8, 2],  [10, 6]])
a7  = fav('Member07', [[6, 4, 8],  [8, 12, 4], [10, 2, 6]],  [[6, 4], [8, 4],  [10, 2]])
a8  = fav('Member08', [[6, 8, 12], [8, 12, 4], [2, 6, 22]],  [[6, 8], [12, 4], [2, 22]])
a9  = fav('Member09', [[6, 4, 8],  [8, 12, 2], [10, 2, 6]],  [[6, 4], [8, 2],  [6, 22]])
a10 = fav('Member10', [[6, 4, 8],  [8, 12, 2], [10, 2, 6]],  [[6, 4], [8, 2],  [10, 2]])

a11 = fav('Member11', [[6, 4, 8],  [8, 12, 2], [10, 2, 22]], [[6, 8], [8, 2],  [10, 22]])
a12 = fav('Member12', [[6, 4, 8],  [8, 12, 2], [10, 2, 6]],  [[6, 4], [8, 2],  [10, 2]])
a13 = fav('Member13', [[6, 8, 12], [8, 12, 4], [2, 6, 22]],  [[8, 12], [12, 2], [2, 22]])
a14 = fav('Member14', [[6, 4, 8],  [8, 12, 2], [10, 2, 6]],  [[6, 4], [8, 2],  [10, 2]])
a15 = fav('Member15', [[6, 4, 8],  [8, 12, 2], [10, 2, 6]],  [[6, 4], [8, 2],  [10, 2]])
a16 = fav('Member16', [[6, 4, 8],  [8, 12, 2], [10, 2, 6]],  [[6, 4], [8, 2],  [10, 2]])

a17 = fav('Member17', [[6, 4, 8],  [8, 12, 2], [10, 2, 6]],  [[6, 4], [12, 2], [10, 2]])
a18 = fav('Member18', [[6, 4, 8],  [8, 12, 2], [10, 2, 6]],  [[6, 4], [8, 2],  [10, 2]])
a19 = fav('Member19', [[6, 4, 8],  [8, 12, 2], [10, 2, 6]],  [[4, 8], [8, 2],  [10, 2]])
a20 = fav('Member20', [[6, 4, 8],  [8, 12, 2], [10, 2, 22]], [[6, 8], [12, 2], [10, 2]])
a21 = fav('Member21', [[6, 4, 8],  [8, 12, 2], [10, 2, 22]], [[6, 8], [8, 2],  [6, 22]])

p2 = [a1, a2, a3, a4, a5, a6, a7, a8,
      a9, a10, a11, a12, a13, a14, a15,
      a16, a17, a18, a19, a20, a21]
