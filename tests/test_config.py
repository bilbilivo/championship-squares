"""Stable local signing-secret lifecycle."""

import stat

import pytest

from config import load_flask_secret


def test_generated_secret_is_private_and_stable(tmp_path, monkeypatch):
    secret_file = tmp_path / 'signing-secret'
    monkeypatch.delenv('FLASK_SECRET_KEY', raising=False)
    monkeypatch.setenv('FLASK_SECRET_KEY_FILE', str(secret_file))

    first = load_flask_secret(tmp_path)
    second = load_flask_secret(tmp_path)

    assert first == second
    assert len(first) >= 32
    assert stat.S_IMODE(secret_file.stat().st_mode) == 0o600


def test_environment_secret_takes_precedence_without_writing_file(tmp_path, monkeypatch):
    secret_file = tmp_path / 'signing-secret'
    monkeypatch.setenv('FLASK_SECRET_KEY', 'configured-secret-that-is-long-enough')
    monkeypatch.setenv('FLASK_SECRET_KEY_FILE', str(secret_file))

    assert load_flask_secret(tmp_path) == 'configured-secret-that-is-long-enough'
    assert not secret_file.exists()


def test_empty_or_short_secret_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv('FLASK_SECRET_KEY', '')
    with pytest.raises(RuntimeError, match='must not be empty'):
        load_flask_secret(tmp_path)

    monkeypatch.delenv('FLASK_SECRET_KEY')
    secret_file = tmp_path / 'signing-secret'
    secret_file.write_text('too-short', encoding='ascii')
    monkeypatch.setenv('FLASK_SECRET_KEY_FILE', str(secret_file))
    with pytest.raises(RuntimeError, match='at least 32'):
        load_flask_secret(tmp_path)
