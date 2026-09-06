"""Exercise the seeder with real Flask permissions and isolated game data."""
from urllib.parse import urlsplit

import pytest
import requests

import generate_fake_game as generator


@pytest.fixture
def seeder_transport(app, monkeypatch):
    # One Flask cookie jar per requests.Session: standalone requests would lose
    # login, just as they do over HTTP. No live server or database is contacted.
    clients = {}
    calls = []

    def request(session, method, url, **kwargs):
        client = clients.setdefault(session, app.test_client())
        path = urlsplit(url).path
        result = client.open(path, method=method, json=kwargs.get('json'))
        response = requests.Response()
        response.status_code = result.status_code
        response._content = result.data
        response.url = url
        calls.append((method.upper(), path, response.status_code))
        return response

    monkeypatch.setattr(requests.Session, 'request', request)
    monkeypatch.setattr(generator, 'http', requests.Session())
    return calls


@pytest.mark.parametrize('sport', generator.SPORT_CONFIG)
def test_generator_logs_in_and_populates_game(sport, client, seeder_transport, monkeypatch):
    import random
    monkeypatch.setattr(generator, 'random', random.Random(7))
    generator.main(sport)
    writes = [call for call in seeder_transport if call[0] == 'POST']
    assert writes[0] == ('POST', '/api/login', 200)
    assert writes[1] == ('POST', '/api/reset', 200)
    assert all(status == 200 for _, _, status in seeder_transport)
    state = client.get('/api/state').json
    config = generator.SPORT_CONFIG[sport]
    assert state['sport'] == sport
    assert len(state['players']) == config['players']
    assert all(player['tokens'] == 0 for player in state['players'].values())
    assert state['scores']['left'] != state['scores']['right']


def test_login_failure_does_not_reset_game(client, seeder_transport, monkeypatch):
    client.post('/api/players', json={'initial': 'A', 'name': 'KEEP'})
    before = client.get('/api/state').json
    original = generator.http.post

    def reject_login(url, **kwargs):
        if url.endswith('/api/login'):
            response = requests.Response()
            response.status_code = 403
            response._content = b'{"error":"Login rejected"}'
            return response
        return original(url, **kwargs)

    monkeypatch.setattr(generator.http, 'post', reject_login)
    with pytest.raises(SystemExit) as error:
        generator.main()
    assert error.value.code == 1
    assert not any(path == '/api/reset' for _, path, _ in seeder_transport)
    assert client.get('/api/state').json == before
