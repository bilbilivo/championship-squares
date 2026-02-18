"""
Shared test fixtures for Championship Squares.

Provides a fresh Flask test client and isolated GameState for each test,
using a temporary database so tests never touch production data.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# Ensure the project root is on sys.path so imports work
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Redirect the SQLite database to a temp directory for every test."""
    temp_db = tmp_path / "test_game_state.db"
    import database
    monkeypatch.setattr(database, "DB_PATH", temp_db)


@pytest.fixture()
def app():
    """Create a fresh Flask application with an isolated GameState."""
    # Import after DB_PATH has been patched (autouse fixture runs first)
    import app as app_module
    from database import init_db

    # Re-initialise the database in the temp location
    init_db()

    # Build a fresh GameState so every test starts clean
    app_module.game_state = app_module.GameState()

    app_module.app.config["TESTING"] = True
    yield app_module.app


@pytest.fixture()
def client(app):
    """Flask test client — no running server needed."""
    return app.test_client()


@pytest.fixture()
def game_state():
    """Direct access to a fresh GameState instance (no Flask context)."""
    import app as app_module
    from database import init_db

    init_db()
    gs = app_module.GameState()
    app_module.game_state = gs
    return gs
