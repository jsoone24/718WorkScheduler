"""
seed_data.py — bootstrap data/users.json from the static p2 list in constants.py.

Run this once after a fresh checkout. Safe to re-run: it skips users who already
exist (matched by name) so it won't clobber edits you've made through the UI.

Usage:
    python seed_data.py
"""

import os

from constants import p2
from store import (
    load_users, save_users, next_user_id,
    User, Preferences, DATA_DIR,
)


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    existing = {u.name for u in load_users()}
    users = load_users()
    added = 0
    skipped = 0

    for order, person in enumerate(p2):
        if person.name in existing:
            skipped += 1
            continue

        prefs = {
            g: Preferences(
                times3=list(person.times3.get(g, [])),
                times2=list(person.times2.get(g, [])),
            )
            for g in ('A', 'B', 'C')
        }
        users.append(User(
            id=next_user_id() + added,  # increment for each new add in this run
            name=person.name,
            active=True,
            display_order=order,
            preferences=prefs,
        ))
        added += 1

    save_users(users)
    print(f"Seeded {added} users into data/users.json (skipped {skipped} existing).")


if __name__ == '__main__':
    main()
