"""Exercise authorization and CSRF without the convenience test client's headers."""
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
import logging
import subprocess
from urllib.parse import urlsplit

import pytest
from flask.testing import FlaskClient


@pytest.fixture(autouse=True)
def _app_module(_isolated_db):
    global module
    import app as module


def enable_tunnel(monkeypatch):
    monkeypatch.setattr(module.tunnel, 'process', FakeProcess(''))
    monkeypatch.setattr(module.tunnel, 'url', PUBLIC)
    monkeypatch.setattr(module.tunnel, 'registration_token', 'registration-token')


PUBLIC = 'https://blue-squares.trycloudflare.com'


def raw(app):
    return FlaskClient(app, app.response_class)


def post(device, path, data=None, base='http://localhost', **kwargs):
    token = device.get('/api/csrf', base_url=base).json['csrf_token']
    return device.post(path, json=data or {}, base_url=base,
                       headers={'X-CSRF-Token': token}, **kwargs)


@pytest.mark.parametrize('base,peer', [
    ('http://localhost', '127.0.0.1'),
    ('http://192.168.1.175:8080', '192.168.1.20'),
    ('http://10.0.0.4:8080', '10.0.0.5'),
    ('http://[fd00::1]:8080', 'fd00::2'),
])
def test_direct_host_and_lan_admin(app, base, peer):
    device = raw(app)
    device.environ_base['REMOTE_ADDR'] = peer
    assert post(device, '/api/login', {'role': 'admin'}, base).status_code == 200
    assert post(device, '/api/players', {'initial': 'A', 'name': 'ALICE'}, base).status_code == 200
    assert device.get('/api/tunnel', base_url=base).status_code == 200


@pytest.mark.parametrize('base,peer', [
    ('http://localhost', '8.8.8.8'),
    ('http://192.168.1.175', '8.8.8.8'),
    ('http://attacker.example', '127.0.0.1'),
    ('http://attacker.example', '192.168.1.20'),
])
def test_forged_forwarding_cannot_create_local_access(app, base, peer):
    device = raw(app)
    response = device.get('/api/csrf', base_url=base, environ_overrides={'REMOTE_ADDR': peer},
                          headers={'X-Forwarded-For': '127.0.0.1', 'X-Forwarded-Host': 'localhost',
                                   'CF-Connecting-IP': '192.168.1.20'})
    assert response.status_code == 403


@pytest.mark.parametrize('base', [PUBLIC, 'http://player-tunnel.invalid'])
def test_public_admin_cookie_is_rejected_even_when_tunnel_is_down(app, base):
    device = raw(app)
    assert post(device, '/api/login', {'role': 'admin'}).status_code == 200
    cookie = device.get_cookie('session').value
    device.set_cookie('session', cookie, domain=urlsplit(base).hostname)
    assert post(device, '/api/reset', base=base).status_code == 403
    assert device.get('/api/tunnel', base_url=base).status_code == 403
    assert post(device, '/api/login', {'role': 'admin'}, base).status_code == 403
    assert device.get('/api/session', base_url=base).json['role'] is None


def test_csrf_missing_wrong_cross_session_and_cross_origin(app):
    device = raw(app)
    assert device.post('/api/login', json={'role': 'admin'}).status_code == 403
    token = device.get('/api/csrf').json['csrf_token']
    for supplied in ['wrong', raw(app).get('/api/csrf').json['csrf_token']]:
        assert device.post('/api/login', json={'role': 'admin'},
                           headers={'X-CSRF-Token': supplied}).status_code == 403
    assert device.post('/api/login', json={'role': 'admin'},
                       headers={'X-CSRF-Token': token, 'Origin': 'https://attacker.example'}).status_code == 403
    response = device.post('/api/login', json={'role': 'admin'},
                           headers={'X-CSRF-Token': token, 'Origin': 'http://localhost'})
    assert response.status_code == 200
    assert response.headers['X-CSRF-Token'] != token
    assert device.post('/api/reset', headers={'X-CSRF-Token': token}).status_code == 403


@pytest.mark.parametrize('base,secure', [('http://localhost', False), (PUBLIC, True),
                                         ('http://player-tunnel.invalid', True)])
def test_session_cookie_and_sensitive_page_headers(app, base, secure):
    device = raw(app)
    response = device.get('/', base_url=base)
    cookie = response.headers['Set-Cookie']
    assert ('Secure;' in cookie) == secure
    assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.headers['Referrer-Policy'] == 'no-referrer'
    expired = device.get('/join/A/expired', base_url=base)
    assert expired.status_code == 403
    assert b'LINK EXPIRED' in expired.data and b'ASK HOST' in expired.data
    assert expired.headers['Cache-Control'] == 'no-store'


def test_public_uses_polling_and_local_uses_sse(client):
    assert client.get('/api/state').json['connection']['sync'] == 'sse'
    assert client.get('/api/state', base_url=PUBLIC).json['connection'] == {'public': True, 'sync': 'poll'}
    assert client.get('/api/events', base_url=PUBLIC).status_code == 409


def test_reset_registration_and_player_delete_revoke_links(client, monkeypatch):
    enable_tunnel(monkeypatch)
    client.post('/api/players', json={'initial': 'A', 'name': 'ALICE'})
    invite = client.post('/api/player-invites/A').json['url']
    client.delete('/api/players/A')
    client.post('/api/players', json={'initial': 'A', 'name': 'AGAIN'})
    assert client.get(urlsplit(invite).path, base_url=PUBLIC).status_code == 403
    client.post('/api/reset')
    assert module.tunnel.registration_token != 'registration-token'
    assert client.get('/join/register/registration-token', base_url=PUBLIC).status_code == 403


def test_rotation_preserves_session_but_blocks_old_link(app, client, monkeypatch):
    enable_tunnel(monkeypatch)
    client.post('/api/players', json={'initial': 'A', 'name': 'ALICE'})
    old = client.post('/api/player-invites/A').json['url']
    player = raw(app)
    assert player.get(urlsplit(old).path, base_url=PUBLIC).status_code == 302
    client.delete('/api/player-invites/A')
    assert raw(app).get(urlsplit(old).path, base_url=PUBLIC).status_code == 403
    assert player.get('/api/session', base_url=PUBLIC).json['role'] == 'player'
    assert post(player, '/api/squares', {'row': 1, 'col': 0, 'value': 'A'}, PUBLIC).status_code == 200
    assert post(player, '/api/players', {'initial': 'B', 'name': 'BOB'}, PUBLIC).status_code == 403


def test_concurrent_invite_issuance_is_stable(app, client, monkeypatch):
    enable_tunnel(monkeypatch)
    client.post('/api/players', json={'initial': 'A', 'name': 'ALICE'})
    def issue(_):
        device = raw(app)
        post(device, '/api/login', {'role': 'admin'})
        return post(device, '/api/player-invites/A').json['url']
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert len(set(pool.map(issue, range(8)))) == 1


def test_square_refund_uses_purchase_cost_and_rejects_stale_cost(client):
    client.post('/api/players', json={'initial': 'A', 'name': 'ALICE'})
    client.post('/api/multiplier', json={'multiplier': 4})
    client.post('/api/squares', json={'row': 1, 'col': 0, 'value': 'A'})
    client.post('/api/multiplier', json={'multiplier': 8})
    state = client.get('/api/state').json
    assert state['square_costs']['1,0'] == 4
    payload = {'row': 1, 'col': 0, 'value': '', 'expected_value': 'A', 'expected_cost': 8}
    assert client.post('/api/squares', json=payload).status_code == 409
    payload['expected_cost'] = 4
    assert client.post('/api/squares', json=payload).status_code == 200
    after = client.get('/api/state').json
    assert after['players']['A']['tokens'] == state['players']['A']['tokens'] + 4
    assert '1,0' not in after['square_costs']


def test_request_logs_redact_bearer_paths():
    record = logging.LogRecord('werkzeug', 20, '', 0, '%s',
                               ('GET /join/A/secret-one /join/register/secret-two /api/public/register/secret-three HTTP/1.1',), None)
    module.RedactInviteTokens().filter(record)
    assert 'secret' not in record.getMessage()
    assert record.getMessage().count('[REDACTED]') == 3


class FakeProcess:
    def __init__(self, output):
        self.stdout = StringIO(output)
        self.dead = False
        self.terminated = self.killed = False
    def poll(self):
        return 0 if self.dead else None
    def terminate(self):
        self.terminated = True
        self.dead = True
    def wait(self, timeout):
        return 0
    def kill(self):
        self.killed = self.dead = True


def test_tunnel_serializes_start_and_sets_fixed_origin_host(monkeypatch):
    manager = module.TunnelManager()
    launched = []
    def launch(args, **kwargs):
        launched.append(args)
        return FakeProcess('https://evil.trycloudflare.com.attacker.example\nhttps://blue-squares.trycloudflare.com\n')
    monkeypatch.setattr(module.shutil, 'which', lambda _: '/bin/cloudflared')
    monkeypatch.setattr(module.subprocess, 'Popen', launch)
    monkeypatch.setitem(module.config.config, 'port', 8765)
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert set(pool.map(lambda _: manager.start(), range(4))) == {PUBLIC}
    assert len(launched) == 1
    assert launched[0][-2:] == ['--http-host-header', module.TUNNEL_HOST]
    assert 'http://127.0.0.1:8765' in launched[0]
    process = manager.process
    manager.stop()
    assert process.terminated and not manager.active() and manager.url is None


def test_tunnel_timeout_kills_and_clears_state(monkeypatch):
    manager = module.TunnelManager()
    process = FakeProcess('https://fake.trycloudflare.com.attacker.example\n')
    calls = iter([0, 21])
    monkeypatch.setattr(module.shutil, 'which', lambda _: '/bin/cloudflared')
    monkeypatch.setattr(module.subprocess, 'Popen', lambda *a, **k: process)
    monkeypatch.setattr(module.time, 'monotonic', lambda: next(calls))
    with pytest.raises(RuntimeError):
        manager.start()
    assert process.terminated and manager.process is None
    assert manager.registration_token is None
    def wait(timeout):
        if not process.killed:
            raise subprocess.TimeoutExpired('cloudflared', timeout)
    process.dead = False
    process.terminate = lambda: None
    process.wait = wait
    manager.process = process
    manager.stop()
    assert process.killed
