"""Cross-device notification, persistence and simultaneous-write regressions."""
from concurrent.futures import ThreadPoolExecutor
import json
import threading

import pytest


@pytest.fixture
def events(app, monkeypatch):
    import app as module
    stream = module.GameEventStream()
    monkeypatch.setattr(module, 'game_events', stream)
    return stream


def event_data(chunk):
    if isinstance(chunk, bytes):
        chunk = chunk.decode()
    return json.loads(chunk.split('data: ', 1)[1])


def test_two_devices_receive_saved_changes_and_reconnect(client, events):
    streams = [events.stream(), events.stream()]
    for stream in streams:
        assert event_data(next(stream))['revision'] == 0
    assert client.post('/api/players', json={'initial': 'A', 'name': 'Alice'}).status_code == 200
    for stream in streams:
        assert event_data(next(stream))['revision'] == 1
        stream.close()
    reconnect = events.stream()
    assert event_data(next(reconnect))['revision'] == 1
    reconnect.close()
    assert 'A' in client.get('/api/state').json['players']


def test_end_game_publishes_once_and_rejections_do_not_publish(client, events):
    revision = events.snapshot()
    assert client.post('/api/end-game').status_code == 400
    assert events.snapshot() == revision

    client.post('/api/teams', json={'left': 'BUF', 'right': 'KC'})
    client.post('/api/players', json={'initial': 'A', 'name': 'Alice'})
    client.post('/api/squares', json={'row': 3, 'col': 1, 'value': 'A'})
    client.post('/api/scores', json={'left': 3, 'right': 1})
    revision = events.snapshot()
    response = client.post('/api/end-game')
    assert response.status_code == 200
    assert events.snapshot() == revision + 1
    assert client.get('/api/state').json['celebration'] == response.json['celebration']

    revision = events.snapshot()
    client.post('/api/reset')
    assert events.snapshot() == revision + 1
    assert client.get('/api/state').json['celebration'] is None


def test_stream_headers_and_initial_event(client, events):
    response = client.get('/api/events', buffered=False)
    try:
        assert response.mimetype == 'text/event-stream'
        assert response.headers['X-Accel-Buffering'] == 'no'
        assert response.headers['Cache-Control'] == 'no-store'
        assert event_data(next(response.response))['revision'] == 0
    finally:
        response.close()


def test_slow_subscriber_does_not_block_publish(events):
    stream = events.stream()
    next(stream)
    events.publish()
    next(stream)  # Leave the generator suspended at its changed-event yield.
    completed = threading.Event()
    thread = threading.Thread(target=lambda: (events.publish(), completed.set()), daemon=True)
    thread.start()
    try:
        assert completed.wait(1), 'A subscriber held the broadcaster lock across yield'
    finally:
        stream.close()
        thread.join(timeout=1)


@pytest.mark.parametrize(('path', 'payload'), [
    ('/api/reset', {}), ('/api/scores', {'left': 3, 'right': 1}),
    ('/api/teams', {'left': 'BUF', 'right': 'KC'}),
    ('/api/sport', {'sport': 'nhl'}), ('/api/multiplier', {'multiplier': 2}),
    ('/api/players', {'initial': 'B', 'name': 'Bob'}),
    ('/api/squares', {'row': 2, 'col': 1, 'value': 'A'}),
])
def test_mutations_publish_only_after_success(client, events, monkeypatch, path, payload):
    import app as module
    client.post('/api/players', json={'initial': 'A', 'name': 'Alice'})
    before = client.get('/api/state').json
    revision = events.snapshot()
    with monkeypatch.context() as patch:
        patch.setattr(module, 'db_save_state', lambda state: False)
        assert client.post(path, json=payload).status_code == 500
    assert events.snapshot() == revision
    assert client.get('/api/state').json == before
    assert client.post(path, json=payload).status_code == 200
    assert events.snapshot() == revision + 1


def test_delete_player_publish_and_rollback(client, events, monkeypatch):
    import app as module
    client.post('/api/players', json={'initial': 'A', 'name': 'Alice'})
    revision = events.snapshot()
    with monkeypatch.context() as patch:
        patch.setattr(module, 'db_save_state', lambda state: False)
        assert client.delete('/api/players/A').status_code == 500
    assert 'A' in client.get('/api/state').json['players']
    assert events.snapshot() == revision
    assert client.delete('/api/players/A').status_code == 200
    assert events.snapshot() == revision + 1


def test_simultaneous_claims_cannot_overwrite_each_other(app, client, events):
    for initial in ['A', 'B']:
        client.post('/api/players', json={'initial': initial, 'name': initial})
    barrier = threading.Barrier(2)

    def claim(initial):
        with app.test_client() as device:
            device.post('/api/login', json={'role': 'admin'})
            barrier.wait(timeout=2)
            return device.post('/api/squares', json={
                'row': 2, 'col': 1, 'value': initial, 'expected_value': ''
            }).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(claim, ['A', 'B'])) == [200, 409]
    state = client.get('/api/state').json
    winner = state['squares'][2][1]
    assert state['players'][winner]['tokens'] == 39
    assert sum(player['tokens'] for player in state['players'].values()) == 79
    assert events.snapshot() == 3


def test_simultaneous_claims_do_not_overspend_tokens(app, client, events):
    import app as module
    client.post('/api/players', json={'initial': 'A', 'name': 'Alice'})
    module.game_state.players['A']['tokens'] = 1
    barrier = threading.Barrier(2)

    def claim(row):
        with app.test_client() as device:
            device.post('/api/login', json={'role': 'admin'})
            barrier.wait(timeout=2)
            return device.post('/api/squares', json={
                'row': row, 'col': 1, 'value': 'A', 'expected_value': ''
            }).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(claim, [2, 3])) == [200, 400]
    state = client.get('/api/state').json
    assert state['players']['A']['tokens'] == 0
    assert sum(value == 'A' for row in state['squares'] for value in row) == 1


def test_stale_delete_and_removed_player_are_rejected(client, events):
    client.post('/api/players', json={'initial': 'A', 'name': 'Alice'})
    client.post('/api/squares', json={'row': 2, 'col': 1, 'value': 'A'})
    before = client.get('/api/state').json
    assert client.post('/api/squares', json={
        'row': 2, 'col': 1, 'value': '', 'expected_value': 'B'
    }).status_code == 409
    assert client.post('/api/squares', json={
        'row': 2, 'col': 1, 'value': 'B'
    }).status_code == 400
    assert client.get('/api/state').json == before
