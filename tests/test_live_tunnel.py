"""Opt-in real Cloudflare smoke test using only a disposable game and local port."""
import os
from collections import deque
import threading
import time
from urllib.parse import urlsplit

import pytest
import requests


@pytest.mark.skipif(os.environ.get('SQUARES_REAL_TUNNEL_TESTS') != '1',
                    reason='Opt-in real Cloudflare test')
def test_real_quick_tunnel_is_player_only(app, client, monkeypatch):
    import app as module
    from werkzeug.serving import make_server
    manager = module.TunnelManager()
    output = deque(maxlen=12)
    popen = module.subprocess.Popen
    class CaptureOutput:
        def __init__(self, source):
            self.source = source
        def __iter__(self):
            for line in self.source:
                output.append(line.strip())
                yield line
        def close(self):
            self.source.close()
    def capture(*args, **kwargs):
        process = popen(*args, **kwargs)
        process.stdout = CaptureOutput(process.stdout)
        return process
    monkeypatch.setattr(module.subprocess, 'Popen', capture)
    monkeypatch.setattr(module, 'tunnel', manager)
    observed_hosts = []
    original = app.wsgi_app
    def record_host(environ, start_response):
        observed_hosts.append(environ.get('HTTP_HOST'))
        return original(environ, start_response)
    monkeypatch.setattr(app, 'wsgi_app', record_host)
    server = make_server('127.0.0.1', 0, app, threaded=True)
    monkeypatch.setitem(module.config.config, 'port', server.server_port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    client.post('/api/teams', json={'left': 'ARI', 'right': 'ATL'})
    try:
        base = manager.start()
        phone = requests.Session()
        phone.trust_env = False
        deadline = time.monotonic() + 40
        last_error = None
        while True:
            try:
                bootstrap = phone.get(base + '/api/csrf', timeout=5)
                last_error = f'HTTP {bootstrap.status_code}: {bootstrap.text[:160]}'
                if bootstrap.status_code == 200:
                    break
            except requests.RequestException as error:
                last_error = str(error)
            if time.monotonic() >= deadline:
                pytest.fail(f'Quick Tunnel unreachable: {last_error}; logs: {list(output)}')
            time.sleep(1)
        assert module.TUNNEL_HOST in observed_hosts
        phone.headers['Origin'] = base
        phone.headers['X-CSRF-Token'] = bootstrap.json()['csrf_token']
        denied = phone.post(base + '/api/login', json={'role': 'admin'}, timeout=10)
        assert denied.status_code == 403
        phone.headers['X-CSRF-Token'] = denied.headers['X-CSRF-Token']
        registration = client.get('/api/player-registration-qr').json['url']
        token = registration.rsplit('/', 1)[1]
        joined = phone.post(base + '/api/public/register/' + token,
                            json={'initial': 'A', 'name': 'ALICE'}, timeout=10)
        assert joined.status_code == 200
        phone.headers['X-CSRF-Token'] = joined.headers['X-CSRF-Token']
        state = phone.get(base + '/api/state', timeout=10).json()
        assert state['connection'] == {'public': True, 'sync': 'poll'}
        assert state['session'] == {'role': 'player', 'player': 'A'}
        assert phone.post(base + '/api/squares', json={'row': 1, 'col': 0, 'value': 'A'}, timeout=10).status_code == 200
        assert phone.post(base + '/api/reset', json={}, timeout=10).status_code == 403
        assert phone.get(joined.json()['rejoin_url'], timeout=10).status_code == 200
        assert all(cookie.secure for cookie in phone.cookies)
        admin_cookie = client.get_cookie('session').value
        phone.cookies.set('session', admin_cookie, domain=urlsplit(base).hostname, path='/')
        assert phone.get(base + '/api/tunnel', timeout=10).status_code == 403
    finally:
        manager.stop()
        server.shutdown()
        server.server_close()
