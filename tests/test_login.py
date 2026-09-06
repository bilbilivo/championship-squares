"""Mode selection and server-enforced player ownership."""
import pytest


def register(client, initial):
    return client.post('/api/players', json={'initial': initial, 'name': initial})


def player_device(app, initial='A', create=False):
    device = app.test_client()
    response = device.post('/api/login', json={
        'role': 'player', 'initial': initial, 'name': initial, 'create': create,
    })
    assert response.status_code == 200
    return device


def test_login_create_select_restore_logout(app, client):
    client.post('/api/teams', json={'left': 'BUF', 'right': 'KC'})
    device = player_device(app, create=True)
    assert device.get('/api/session').json == {'role': 'player', 'player': 'A'}
    assert 'A' in client.get('/api/state').json['players']
    other = player_device(app)
    assert other.get('/api/session').json['player'] == 'A'
    assert device.post('/api/logout').status_code == 200
    assert device.get('/api/session').json['role'] is None
    assert device.post('/api/squares', json={'row': 1, 'col': 2, 'value': 'A'}).status_code == 401


@pytest.mark.parametrize(('path', 'payload'), [
    ('/api/reset', {}), ('/api/sport', {'sport': 'nhl'}),
    ('/api/teams', {'left': 'BUF'}), ('/api/scores', {'left': 3}),
    ('/api/multiplier', {'multiplier': 2}),
    ('/api/players', {'initial': 'B', 'name': 'Bob'}),
])
def test_restricted_mutations(app, client, path, payload):
    client.post('/api/teams', json={'left': 'BUF', 'right': 'KC'})
    device = player_device(app, create=True)
    before = client.get('/api/state').json
    assert device.post(path, json=payload).status_code == 403
    assert app.test_client().post(path, json=payload).status_code == 401
    assert client.get('/api/state').json == before


def test_player_owns_only_their_tokens(app, client):
    register(client, 'A')
    register(client, 'B')
    device = player_device(app)
    square = {'row': 1, 'col': 2}
    before = client.get('/api/state').json['players']['A']['tokens']
    assert device.post('/api/squares', json={**square, 'value': 'A'}).status_code == 200
    assert client.get('/api/state').json['players']['A']['tokens'] == before - 1
    assert device.post('/api/squares', json={**square, 'value': 'B'}).status_code == 403
    assert device.post('/api/squares', json={**square, 'value': ''}).status_code == 200
    assert client.get('/api/state').json['players']['A']['tokens'] == before
    assert client.post('/api/squares', json={**square, 'value': 'B'}).status_code == 200
    for value in ['', 'A', 'B']:
        assert device.post('/api/squares', json={**square, 'value': value}).status_code == 403
    for initial in ['A', 'B']:
        assert device.delete(f'/api/players/{initial}').status_code == 403


@pytest.mark.parametrize('reset', [True, False])
def test_deleted_or_reset_identity_cannot_control_reused_initial(app, client, reset):
    register(client, 'A')
    device = player_device(app)
    if reset:
        assert client.post('/api/reset').status_code == 200
    else:
        assert client.delete('/api/players/A').status_code == 200
    register(client, 'A')
    assert device.post('/api/squares', json={'row': 1, 'col': 2, 'value': 'A'}).status_code == 403
    assert device.get('/api/session').json['role'] is None


def test_login_validation_and_failed_registration(app, client, monkeypatch):
    client.post('/api/teams', json={'left': 'BUF', 'right': 'KC'})
    device = app.test_client()
    for payload in [{}, {'role': 'invalid'}, {'role': 'player', 'initial': 'Z'},
                    {'role': 'player', 'initial': [], 'create': True},
                    {'role': 'player', 'initial': 'AB', 'name': 'Bad', 'create': True}]:
        assert device.post('/api/login', json=payload).status_code == 400
    register(client, 'A')
    assert device.post('/api/login', json={'role': 'player', 'initial': 'A', 'name': 'Dup', 'create': True}).status_code == 400
    import app as module
    monkeypatch.setattr(module.game_state, 'save_state', lambda: False)
    assert device.post('/api/login', json={'role': 'player', 'initial': 'B', 'name': 'Bob', 'create': True}).status_code == 500
    assert 'B' not in module.game_state.players
    assert device.get('/api/session').json['role'] is None


@pytest.mark.parametrize('teams', [{}, {'left': 'BUF'}, {'right': 'KC'}, {'left': '', 'right': ''}])
def test_player_creation_requires_both_teams(app, client, teams):
    client.post('/api/teams', json=teams)
    device = app.test_client()
    response = device.post('/api/login', json={
        'role': 'player', 'initial': 'A', 'name': 'ALICE', 'create': True,
    })
    assert response.status_code == 403
    assert 'ADMIN' in response.json['error']
    assert client.get('/api/state').json['players'] == {}
    assert device.get('/api/session').json['role'] is None
    # Admin setup remains available before teams are chosen.
    assert register(client, 'A').status_code == 200
