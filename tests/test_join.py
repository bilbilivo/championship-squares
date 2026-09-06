"""Network links must be reachable from another device, never loopback."""
from unittest.mock import MagicMock
from xml.etree import ElementTree

import pytest


def test_join_preserves_network_host_and_port(client):
    response = client.get('/api/join', base_url='http://192.168.1.175:8080')
    assert response.status_code == 200
    assert response.json['url'] == 'http://192.168.1.175:8080/'
    svg = ElementTree.fromstring(response.json['svg'])
    assert svg.tag == '{http://www.w3.org/2000/svg}svg'
    assert svg.find('{http://www.w3.org/2000/svg}path') is not None
    assert response.headers['Cache-Control'] == 'no-store'


@pytest.mark.parametrize('host', ['localhost', '127.0.0.1', '[::1]', '0.0.0.0'])
def test_loopback_is_replaced_with_lan_ip(client, monkeypatch, host):
    probe = MagicMock()
    probe.__enter__.return_value.getsockname.return_value = ('192.168.1.175', 12345)
    monkeypatch.setattr('app.socket.socket', lambda *args: probe)
    monkeypatch.setattr('app.socket.gethostbyname_ex', lambda *args: ('pc', [], []))
    response = client.get('/api/join', base_url=f'http://{host}:8080')
    assert response.json['url'] == 'http://192.168.1.175:8080/'


def test_no_route_falls_back_to_hostname(client, monkeypatch):
    def unavailable(*args):
        raise OSError('No route')
    monkeypatch.setattr('app.socket.socket', unavailable)
    monkeypatch.setattr('app.socket.gethostbyname_ex', lambda *args: ('pc', [], ['127.0.0.1', '192.168.1.175']))
    assert client.get('/api/join', base_url='http://localhost:8080').json['url'] == 'http://192.168.1.175:8080/'


def test_missing_network_shows_error_instead_of_loopback_qr(client, monkeypatch):
    def unavailable(*args):
        raise OSError('No network')
    monkeypatch.setattr('app.socket.socket', unavailable)
    monkeypatch.setattr('app.socket.gethostbyname_ex', unavailable)
    response = client.get('/api/join')
    assert response.status_code == 503
    assert 'network IP address' in response.json['error']
    assert 'svg' not in response.json
