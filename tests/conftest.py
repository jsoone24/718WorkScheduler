"""
conftest.py — pytest fixtures shared by every test module.

Each test gets a fresh `data/` directory under tmp_path so:
  * Tests are completely isolated from each other and from any real run.
  * Failed tests don't leave junk behind in the repo's `data/`.
  * Concurrent test runs (pytest-xdist) won't trample each other.

The trick is monkeypatching `store`'s module-level path constants AND
its `DATA_DIR`. Every other module reaches storage only through `store`,
so this single redirection covers the whole codebase.
"""

from pathlib import Path

import pytest


@pytest.fixture
def isolated_store(monkeypatch, tmp_path):
    """
    Redirect every store path to a fresh tmp directory and seed the roster
    so each test starts from "fresh install" state. Yields the tmp data
    dir for any test that needs to inspect the on-disk JSON directly.
    """
    import store

    data_dir = tmp_path / 'data'
    data_dir.mkdir()

    monkeypatch.setattr(store, 'DATA_DIR', str(data_dir))
    for name, filename in [
        ('USERS_PATH', 'users.json'),
        ('VACATIONS_PATH', 'vacations.json'),
        ('OUTINGS_PATH', 'outings.json'),
        ('STRIKEFORCE_PATH', 'strikeforce.json'),
        ('SETTINGS_PATH', 'settings.json'),
        ('SCHEDULES_PATH', 'schedules.json'),
        ('LEDGER_PATH', 'ledger.json'),
    ]:
        monkeypatch.setattr(store, name, str(data_dir / filename))

    # Seed the roster from constants.py so tests have realistic users.
    import seed_data
    seed_data.main()

    yield data_dir


@pytest.fixture
def client(isolated_store):
    """A FastAPI TestClient bound to the isolated store."""
    from fastapi.testclient import TestClient
    import web_app
    return TestClient(web_app.app)
