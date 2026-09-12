"""
Shared test fixtures for Championship Squares.

Provides a fresh Flask test client and isolated GameState for each test,
using a temporary database so tests never touch production data.
"""

import sys
import pytest
from pathlib import Path
from flask.testing import FlaskClient

# Ensure the project root is on sys.path so imports work
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Redirect the SQLite database to a temp directory for every test."""
    temp_db = tmp_path / "test_game_state.db"
    import database
    monkeypatch.setattr(database, "DB_PATH", temp_db)


class CsrfClient(FlaskClient):
    """Exercise real CSRF validation while keeping older domain tests concise."""
    def open(self, *args, **kwargs):
        if kwargs.get('method', 'GET').upper() not in {'GET', 'HEAD', 'OPTIONS'}:
            headers = dict(kwargs.get('headers') or {})
            if 'X-CSRF-Token' not in headers:
                connection = {key: kwargs[key] for key in ('base_url', 'environ_overrides') if key in kwargs}
                bootstrap = super().open('/api/csrf', method='GET', **connection)
                if bootstrap.is_json and 'csrf_token' in bootstrap.json:
                    headers['X-CSRF-Token'] = bootstrap.json['csrf_token']
            kwargs['headers'] = headers
        return super().open(*args, **kwargs)


@pytest.fixture()
def app(monkeypatch):
    """Create a fresh Flask application with an isolated GameState."""
    # Import after DB_PATH has been patched (autouse fixture runs first)
    import app as app_module
    from database import init_db

    # Re-initialise the database in the temp location
    init_db()

    # Build a fresh GameState so every test starts clean
    app_module.game_state = app_module.GameState()
    app_module.rate_limiter.clear()

    app_module.app.config["TESTING"] = True
    monkeypatch.setattr(app_module.app, "test_client_class", CsrfClient)
    yield app_module.app
    app_module.rate_limiter.clear()


@pytest.fixture()
def client(app):
    """Flask test client — no running server needed."""
    client = app.test_client()
    client.post('/api/login', json={'role': 'admin'})
    return client


@pytest.fixture()
def game_state():
    """Direct access to a fresh GameState instance (no Flask context)."""
    import app as app_module
    from database import init_db

    init_db()
    gs = app_module.GameState()
    app_module.game_state = gs
    return gs
