"""
solver.py — CP-SAT scheduler for 718 auxiliary police daily duty allocation.

WHAT THIS FILE DOES
-------------------
Given a roster of who is working today (and who is absent / out / on long-night),
this module produces a duty schedule that:

  1. Respects every hard rule (capacity per site, status overrides, no double-booking)
  2. Maximises the number of people who get one of their preferred shift hours

It does this with Google's OR-Tools CP-SAT solver, which solves this kind of
small constraint problem in milliseconds. This replaces the old random-greedy
approach in Time_Scheduler.py + Work_Scheduler.py, which could hang forever on
hard inputs because random shuffling has no notion of "give up cleanly".

DOMAIN RECAP (see constants.py for the data)
--------------------------------------------
- 21 officers in p2 (the second platoon), each with `fav` preferences
- 3 rotation groups A / B / C, cycling once per day
- Each group has 4 time slots (each a 2-hour block)
- 4 duty sites: 정출, 별정, 별후, 서남문
- Per-slot, per-site capacity tables in `placetable` (different on weekends)

STATUS TYPES
------------
Each person on a given day is in exactly one of these states:
  - normal     : works 1 to 4 slots. Crucially, ALL normals on the same day
                 are kept within 1 slot of each other (max - min ≤ 1) — so
                 you never see one person at 4 while another is at 1. Min is
                 1, not 0: nobody just "rests" while still being on duty.
                 If a person should rest, mark them as outing/strike/absent.
  - absent     : 사고자 — works 0 slots (vacation, sick, training, etc.)
  - outing     : 외출자 — works 0 slots (away from the unit for the day).
                 Functionally identical to `absent` for the solver; the label
                 exists so the outing scheduler can track Sat/Sun rotation
                 fairness separately from medical/training absences.
  - longnight  : 긴밤자 — exempt from the 02:00 and 04:00 slots so they can
                 sleep through the night. Only meaningful in Group B (the only
                 group that has those night slots). Bounded at 1–2 slots.
                 NOT subject to the "within 1 slot" balance rule — they're
                 fundamentally capped lower than normals.
  - strike     : 타격대 — quick-reaction standby for the week, no regular duty
                 assignments. Treated like absent by the solver; tracked in
                 the strike-force ledger for rotation fairness.

Anyone not mentioned in the status dict is treated as normal.
"""

from typing import Dict, List, Optional, Tuple
from ortools.sat.python import cp_model

from constants import Timetable, placetable, work_group
from store import User


# Site index -> Korean name. The order MUST match how placetable rows are written
# in constants.py: the comment there says "정출, 별정, 별후, 서남문 순서".
SITE_NAMES = ['정출', '별정', '별후', '서남문']
NUM_SITES = 4
NUM_SLOTS = 4

# Hard wall-clock cap on a single solve. Typical real-world inputs converge
# in tens of milliseconds; this only guards against pathological corner cases
# (e.g., a malformed input that happens to be near-infeasible).
SOLVER_TIMEOUT_SECONDS = 30.0

# Status codes. Use these strings (or the constants below) when building the
# `statuses` dict you pass to solve_day().
STATUS_NORMAL = 'normal'
STATUS_ABSENT = 'absent'
STATUS_OUTING = 'outing'
STATUS_LONGNIGHT = 'longnight'
STATUS_STRIKE = 'strike'    # 타격대 — quick-reaction standby for the week

# 24-hour-clock equivalent of each group's in-code hour labels.
# The labels in constants.py (TimeA / TimeB / TimeC) use a 12-hour-clock
# convention WITHOUT AM/PM, which is hard to read. This table converts them
# back to 24-hour for display. The one quirk: Group C's last slot is written
# as `22` rather than `10` to disambiguate from C's morning slot, also `10`.
SLOT_24H = {
    0: {6: 6, 4: 16, 8: 20, 12: 24},   # Group A: 06, 16, 20, 24
    1: {8: 8, 12: 12, 2: 2, 4: 4},     # Group B: 08, 12, 02, 04
    2: {10: 10, 2: 14, 6: 18, 22: 22}, # Group C: 10, 14, 18, 22
}


def solve_day(
    today_group: int,            # 0=A, 1=B, 2=C
    is_weekend: bool,            # True on Saturday / Sunday
    users: List[User],           # the candidate pool (active users + their preferences)
    statuses: Dict[str, str],    # name -> status code; missing names default to normal
    work_count_before: Optional[Dict[str, int]] = None,  # cumulative slots per person from prior days
    fairness_weight: int = 10,   # how much to weigh fairness against preferences
    seed: Optional[int] = None,  # optional, for reproducible random tie-breaking
) -> Optional[Dict[str, List[Tuple[int, int]]]]:
    """
    Build and solve the day's scheduling problem.

    Returns:
        On success: a dict mapping each person's name to a list of
        (slot_index, site_index) tuples — the slots they were assigned to,
        and where they go for each.

        On failure (no schedule satisfies the constraints): None.

    The solver runs in two phases internally:
      Phase 1 (hard constraints): refuses any assignment that breaks a rule.
      Phase 2 (objective): among all feasible assignments, pick one that
                           maximises preference matches AND minimises the
                           cumulative work-count spread across the platoon.

    FAIRNESS ARGUMENT
    -----------------
    `work_count_before` is an optional dict mapping each person's name to how
    many slots they have worked across all PRIOR days (loaded from ledger.py).
    When provided, the objective adds a penalty of (max_after - min_after) for
    the cumulative counts after today's schedule is applied. This means people
    who are currently behind get prioritised, keeping totals balanced over time.

    `fairness_weight` controls the trade-off: each unit of cumulative spread
    costs this many preference-match points. Higher = fairness wins; lower =
    preferences win. Default 10 keeps fairness firmly in the lead.

    Pass `work_count_before=None` to disable the fairness term entirely (useful
    for one-off tests, or for the very first day when the ledger is empty).
    """
    # ----- Step 1: pull today's domain data out of the tables in constants.py -----

    # Timetable[group] = [TimeX, WorkX_weekday, WorkX_weekend]. We only need TimeX
    # here (per-slot people totals are implicit in placetable's row sums).
    times = Timetable[today_group][0]  # e.g. [6, 4, 8, 12] for Group A

    # placetable[group] is [weekday_matrix, weekend_matrix].
    # Each matrix is 4 slots x 4 sites of integer capacities.
    weekend_idx = 1 if is_weekend else 0
    place_cap = placetable[today_group][weekend_idx]

    # The group letter is the key into each person's `fav.times3` / `fav.times2`
    # preference dicts.
    group_letter = work_group[today_group]  # 'A', 'B', or 'C'

    # The "return shift" — outings (외출자) come back to barracks just in time
    # to work this slot. In all 3 groups this is conventionally the LAST slot
    # of the day (index 3).
    return_slot = NUM_SLOTS - 1

    # The "night slots" — only relevant in Group B, where 긴밤자 (long-night)
    # workers are exempt so they can get an unbroken night of sleep. We find
    # which slot indices in B have the clock hours 02:00 and 04:00.
    night_slot_indices: List[int] = []
    if today_group == 1:  # Group B
        night_slot_indices = [s for s, t in enumerate(times) if t in (2, 4)]

    # ----- Step 2: classify every person by today's status -----

    num_people = len(users)
    name_of = {i: users[i].name for i in range(num_people)}
    idx_of = {u.name: i for i, u in enumerate(users)}

    # Catch typos in the roster early. Better to fail with a clear message here
    # than to silently ignore a misspelled name and produce a "wrong" schedule.
    for name in statuses:
        if name not in idx_of:
            raise ValueError(
                f"알 수 없는 대원 이름: {name!r}. "
                f"등록된 이름 중 하나여야 합니다: {sorted(idx_of)}"
            )

    status_of = {
        i: statuses.get(name_of[i], STATUS_NORMAL) for i in range(num_people)
    }

    # ----- Step 3: build the CP-SAT model -----

    model = cp_model.CpModel()

    # The decision variable: x[p, s, l] = 1 if person p is at site l in slot s,
    # else 0. Think of it as a 4-D table of yes/no flags. Every constraint and
    # the objective are written as linear arithmetic over these flags.
    x = {}
    for p in range(num_people):
        for s in range(NUM_SLOTS):
            for l in range(NUM_SITES):
                x[p, s, l] = model.NewBoolVar(f'x_p{p}_s{s}_l{l}')

    # ----- Hard constraint A: no double-booking -----
    # In any one slot, a person is at AT MOST one site. They might be at NONE
    # (they're off that slot, which is what makes 2-duty vs 3-duty meaningful).
    for p in range(num_people):
        for s in range(NUM_SLOTS):
            model.Add(sum(x[p, s, l] for l in range(NUM_SITES)) <= 1)

    # ----- Hard constraint B: site capacity -----
    # For each (slot, site), the number of people assigned must EXACTLY equal
    # the capacity from placetable. Equality (not "<=") because every duty post
    # must be filled — under-staffing is just as broken as over-staffing.
    for s in range(NUM_SLOTS):
        for l in range(NUM_SITES):
            model.Add(
                sum(x[p, s, l] for p in range(num_people)) == place_cap[s][l]
            )

    # ----- Hard constraint C: status overrides -----
    # Each status type imposes its own work-count and slot restrictions.
    for p in range(num_people):
        # `total_slots` = how many slots person p ends up working today.
        total_slots = sum(
            x[p, s, l] for s in range(NUM_SLOTS) for l in range(NUM_SITES)
        )
        status = status_of[p]

        if status in (STATUS_ABSENT, STATUS_OUTING, STATUS_STRIKE):
            # 사고자 / 외출자 / 타격대 — works zero slots today.
            # All three mean "away from regular duty". The labels are kept
            # distinct so each can be tracked for its own rotation fairness
            # (vacation history vs Sat/Sun outing rotation vs strike force
            # rotation), but the solver treats them identically.
            model.Add(total_slots == 0)

        elif status == STATUS_LONGNIGHT:
            # 긴밤자 — exempt from the 02:00 and 04:00 night slots. In
            # groups A and C, `night_slot_indices` is empty so this is a
            # no-op. In Group B, this caps them at the 2 daytime slots.
            # They still must work at least 1 slot (no full rest).
            for s in night_slot_indices:
                for l in range(NUM_SITES):
                    model.Add(x[p, s, l] == 0)
            model.Add(total_slots >= 1)
            model.Add(total_slots <= NUM_SLOTS)

        else:  # STATUS_NORMAL
            # Everyone on regular duty works at least 1 slot — nobody just
            # "rests" while officially on duty. The actual count (1–4) and
            # the per-day balance (max−min ≤ 1) are enforced separately
            # below, so all normals end up within 1 slot of each other.
            model.Add(total_slots >= 1)
            model.Add(total_slots <= NUM_SLOTS)

    # ----- Hard constraint D: per-day balance among normals -----
    # All NORMAL workers on the same day must end up within 1 slot of each
    # other (max − min ≤ 1). This is the user's "everyone works roughly the
    # same" rule: no one does 4 slots while another does 1 on the same day.
    # Long-night is excluded — they're already capped at 2 by the night-slot
    # exclusion, so applying this rule to them would conflict with normals
    # working 3 or 4 on tight days.
    normal_totals = []
    for p in range(num_people):
        if status_of[p] != STATUS_NORMAL:
            continue
        normal_totals.append(
            sum(x[p, s, l] for s in range(NUM_SLOTS) for l in range(NUM_SITES))
        )
    if normal_totals:
        max_normal = model.NewIntVar(1, NUM_SLOTS, 'max_normal_slots')
        min_normal = model.NewIntVar(1, NUM_SLOTS, 'min_normal_slots')
        model.AddMaxEquality(max_normal, normal_totals)
        model.AddMinEquality(min_normal, normal_totals)
        model.Add(max_normal - min_normal <= 1)

    # ----- Soft objective: maximise preference matches -----
    # Each person has a list of preferred shift HOURS (not sites — preferences
    # are about WHEN you work, not WHERE). We sum up `x[p, s, l]` for every
    # combination where the slot's hour matches one of the person's preferred
    # hours, and tell the solver to maximise that sum.
    #
    # We use the union of `times3` and `times2` because times2 is essentially
    # always a subset of times3 in the data, and gating preferences on duty
    # count would complicate the model without changing answers.
    pref_terms = []
    for p in range(num_people):
        if status_of[p] in (STATUS_ABSENT, STATUS_OUTING, STATUS_STRIKE):
            # All three statuses work zero slots today; no preferences to optimise.
            continue
        person = users[p]
        prefs = person.preferences.get(group_letter)
        if prefs is None:
            # No preferences saved for this group — treat as no preferred hours.
            preferred_hours = set()
        else:
            preferred_hours = set(prefs.times3) | set(prefs.times2)
        for s in range(NUM_SLOTS):
            if times[s] in preferred_hours:
                for l in range(NUM_SITES):
                    pref_terms.append(x[p, s, l])

    # ----- Soft objective part 2: fairness across days -----
    # If a cumulative work-count ledger is supplied, add a penalty proportional
    # to the (max - min) spread of "work_count after today" across all people.
    # This is what ties single-day decisions to long-term fairness: people who
    # are currently behind have low before-counts, so giving them more slots
    # raises min_after (closes the gap), while giving slots to someone already
    # ahead raises max_after (opens the gap further) and is therefore avoided.
    pref_score = sum(pref_terms) if pref_terms else 0
    if work_count_before is not None:
        # IntVar bounds need to accommodate the FULL range of possible
        # `after` values, including NEGATIVE before-counts. The fairness
        # ledger's `work_count_for_solver()` returns vacation-normalised
        # *virtual* counts that can be negative (someone below their fair
        # share has a negative virtual count). If we used IntVar(0, ...) the
        # solver would silently reject negative before-counts as INFEASIBLE.
        before_values = list(work_count_before.values()) or [0]
        lo = min(before_values)              # may be negative
        hi = max(before_values) + NUM_SLOTS  # before + max-possible today
        spread_max = hi - lo                 # max possible (max - min) spread

        after_counts = []
        for p in range(num_people):
            before = work_count_before.get(name_of[p], 0)
            total_today = sum(
                x[p, s, l] for s in range(NUM_SLOTS) for l in range(NUM_SITES)
            )
            after = model.NewIntVar(lo, hi, f'after_{p}')
            model.Add(after == before + total_today)
            after_counts.append(after)

        max_after = model.NewIntVar(lo, hi, 'max_after')
        min_after = model.NewIntVar(lo, hi, 'min_after')
        model.AddMaxEquality(max_after, after_counts)
        model.AddMinEquality(min_after, after_counts)

        spread = model.NewIntVar(0, spread_max, 'spread')
        model.Add(spread == max_after - min_after)

        # Combined: maximise preference-matches MINUS a weighted fairness penalty.
        # The pref_score might be 0 if no preferences applied; that's fine —
        # the objective then becomes pure fairness, which is what we want.
        model.Maximize(pref_score - fairness_weight * spread)
    elif pref_terms:
        model.Maximize(pref_score)

    # ----- Solve -----
    solver = cp_model.CpSolver()
    if seed is not None:
        # Setting the seed makes the solver deterministic for a given input,
        # which is helpful when you want to reproduce a particular schedule.
        solver.parameters.random_seed = seed
    # Single-threaded: required for the seed to fully determine the result.
    solver.parameters.num_search_workers = 1
    # Hard wall-clock cap so a malformed input or a pathological corner case
    # cannot pin a worker thread indefinitely. Real days converge in well
    # under a second; 30s is generous and still bounded.
    solver.parameters.max_time_in_seconds = SOLVER_TIMEOUT_SECONDS

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    # ----- Extract the solution into a friendly name -> [(slot, site), ...] dict -----
    schedule: Dict[str, List[Tuple[int, int]]] = {}
    for p in range(num_people):
        assignments = []
        for s in range(NUM_SLOTS):
            for l in range(NUM_SITES):
                if solver.Value(x[p, s, l]) == 1:
                    assignments.append((s, l))
        assignments.sort()  # stable order for display
        schedule[name_of[p]] = assignments
    return schedule


def feasibility_report(
    today_group: int,
    is_weekend: bool,
    users: List[User],
    statuses: Dict[str, str],
) -> List[str]:
    """
    Quick sanity check before invoking the solver. Returns a list of warning
    strings; an empty list means the input is at least roughly feasible.

    The point of this is to catch the silent-hang cases that crashed the old
    code (e.g., too many people for the day's capacity, so no valid mix of
    2-duty and 3-duty exists). The CP-SAT solver itself would return
    INFEASIBLE in milliseconds, but this gives the human a clearer message.
    """
    weekend_idx = 1 if is_weekend else 0
    place_cap = placetable[today_group][weekend_idx]

    # Total person-slots demanded today (sum of all site capacities across all slots).
    total_capacity = sum(
        place_cap[s][l] for s in range(NUM_SLOTS) for l in range(NUM_SITES)
    )

    num_people = len(users)
    absent_count = sum(1 for s in statuses.values() if s == STATUS_ABSENT)
    outing_count = sum(1 for s in statuses.values() if s == STATUS_OUTING)
    strike_count = sum(1 for s in statuses.values() if s == STATUS_STRIKE)
    longnight_count = sum(1 for s in statuses.values() if s == STATUS_LONGNIGHT)
    normal_count = (
        num_people - absent_count - outing_count - strike_count - longnight_count
    )

    # Person-slot accounting under the hardened solver rules:
    #   - normal     : 1–4 slots, all within 1 of each other (balance rule)
    #   - longnight  : 1–2 slots
    #   - outing/absent/strike : 0 slots
    # Min supply: every working person does at least 1.
    # Max supply: normals up to 4, longnights up to 2.
    min_supply = normal_count + longnight_count
    max_supply = 4 * normal_count + 2 * longnight_count

    issues: List[str] = []
    if total_capacity > max_supply:
        issues.append(
            f"인원 부족: 오늘 필요한 근무 슬롯은 {total_capacity}개인데 "
            f"최대 공급 가능 슬롯은 {max_supply}개입니다. "
            f"휴가/외출/타격대 인원을 줄이거나 더 많은 대원을 활성화하세요."
        )
    if total_capacity < min_supply:
        issues.append(
            f"인원 과다: 오늘 필요한 근무 슬롯은 {total_capacity}개인데 "
            f"최소 공급 가능 슬롯은 {min_supply}개입니다 (모든 근무자가 최소 1슬롯). "
            f"외출/타격대를 더 보내거나 demand가 큰 날을 고르세요."
        )
    if longnight_count > 0 and today_group != 1:
        issues.append(
            f"긴밤자 설정은 B조에서만 의미가 있습니다 "
            f"(오늘은 {work_group[today_group]}조). 일반 근무자로 처리됩니다."
        )
    return issues


def print_schedule(
    schedule: Dict[str, List[Tuple[int, int]]],
    today_group: int,
    is_weekend: bool,
) -> None:
    """Pretty-print the schedule grouped by slot, then by site."""
    times = Timetable[today_group][0]
    weekend_idx = 1 if is_weekend else 0
    place_cap = placetable[today_group][weekend_idx]
    group_letter = work_group[today_group]

    weekend_label = '주말' if is_weekend else '평일'
    print(f"\n=== {group_letter}조 {weekend_label} 근무표 ===")

    # Invert the schedule: (slot, site) -> [names assigned there]
    by_slot_site: Dict[Tuple[int, int], List[str]] = {
        (s, l): [] for s in range(NUM_SLOTS) for l in range(NUM_SITES)
    }
    for name, slots in schedule.items():
        for (s, l) in slots:
            by_slot_site[s, l].append(name)

    for s in range(NUM_SLOTS):
        clock_24h = SLOT_24H[today_group][times[s]]
        print(f"\n  [{clock_24h:02d}시 슬롯]")
        for l in range(NUM_SITES):
            names = by_slot_site[s, l]
            cap = place_cap[s][l]
            names_str = ', '.join(names) if names else '(none)'
            print(f"    {SITE_NAMES[l]:<6} ({len(names)}/{cap}): {names_str}")

    # Per-person summary at the bottom — easier to verify "did everyone get a fair count?"
    print(f"\n  [개인별 근무 횟수]")
    for name, slots in sorted(schedule.items(), key=lambda kv: -len(kv[1])):
        slot_hours = [SLOT_24H[today_group][times[s]] for (s, _) in slots]
        slot_str = ', '.join(f'{h:02d}시' for h in slot_hours) if slot_hours else '(off)'
        print(f"    {name}: {len(slots)}타 — {slot_str}")
