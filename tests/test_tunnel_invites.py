"""Tunnel access stays player-only and QR links survive repeated display."""
from urllib.parse import urlsplit

import pytest


@pytest.fixture(autouse=True)
def _app_module(_isolated_db):
    global app_module
    import app as app_module


class ActiveProcess:
    def poll(self):
        return None


def enable_tunnel(monkeypatch):
    monkeypatch.setattr(app_module.tunnel, 'process', ActiveProcess())
    monkeypatch.setattr(app_module.tunnel, 'url', 'https://blue-squares.trycloudflare.com')
    monkeypatch.setattr(app_module.tunnel, 'registration_token', 'registration-token')


def test_tunnel_replaces_join_qr_for_local_admin(client, monkeypatch):
    enable_tunnel(monkeypatch)
    response = client.get('/api/join')
    assert response.status_code == 200
    assert response.json['url'] == 'https://blue-squares.trycloudflare.com'
    assert response.json['tunnel'] is True


def test_public_tunnel_rejects_admin_login(client, monkeypatch):
    enable_tunnel(monkeypatch)
    response = client.post('/api/login', json={'role': 'admin'}, base_url='https://blue-squares.trycloudflare.com')
    assert response.status_code == 403
    assert 'player QR' in response.json['error']


def test_player_qr_is_stable_until_player_is_deleted(client, monkeypatch):
    enable_tunnel(monkeypatch)
    assert client.post('/api/players', json={'initial': 'A', 'name': 'Alice'}).status_code == 200
    first = client.post('/api/player-invites/A').json['url']
    second = client.post('/api/player-invites/A').json['url']
    assert first == second
    path = urlsplit(first).path
    response = client.get(path, base_url='https://blue-squares.trycloudflare.com', follow_redirects=False)
    assert response.status_code == 302
    assert response.headers['Location'] == '/'
    assert client.get('/api/session', base_url='https://blue-squares.trycloudflare.com').json == {'role': 'player', 'player': 'A'}


def test_reset_revokes_existing_player_links(client, monkeypatch):
    enable_tunnel(monkeypatch)
    assert client.post('/api/players', json={'initial': 'A', 'name': 'Alice'}).status_code == 200
    invite = client.post('/api/player-invites/A').json['url']
    assert client.post('/api/reset').status_code == 200
    assert client.get(urlsplit(invite).path, base_url='https://blue-squares.trycloudflare.com').status_code == 403


def test_admin_can_rotate_a_player_link(client, monkeypatch):
    enable_tunnel(monkeypatch)
    assert client.post('/api/players', json={'initial': 'A', 'name': 'Alice'}).status_code == 200
    first = client.post('/api/player-invites/A').json['url']
    assert client.delete('/api/player-invites/A').status_code == 200
    second = client.post('/api/player-invites/A').json['url']
    assert first != second


def test_public_registration_creates_and_logs_in_player(client, monkeypatch):
    enable_tunnel(monkeypatch)
    assert client.post('/api/teams', json={'left': 'NFL_ARI', 'right': 'NFL_ATL'}).status_code == 200
    response = client.post('/api/public/register/registration-token',
                           json={'initial': 'B', 'name': 'Bob'},
                           base_url='https://blue-squares.trycloudflare.com')
    assert response.status_code == 200
    assert response.json['player'] == 'B'
    assert '/join/B/' in response.json['rejoin_url']
    assert client.get('/api/session', base_url='https://blue-squares.trycloudflare.com').json == {'role': 'player', 'player': 'B'}
