"""Opt-in real browser checks against an isolated game, never the running server.

Run with SQUARES_BROWSER_TESTS=1 and an installed Playwright Chromium.
"""
import os
from pathlib import Path
import subprocess
import threading

import pytest

pytestmark = pytest.mark.skipif(os.environ.get('SQUARES_BROWSER_TESTS') != '1',
                                reason='Opt-in Playwright browser checks')


@pytest.fixture
def browser_game(app, client, monkeypatch, tmp_path):
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server
    import app as module
    cert, key = tmp_path / 'cert.pem', tmp_path / 'key.pem'
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                    '-keyout', str(key), '-out', str(cert), '-days', '1', '-subj', '/CN=player-tunnel.invalid'],
                   check=True, capture_output=True)
    local = make_server('127.0.0.1', 0, app, threaded=True)
    public = make_server('127.0.0.1', 0, app, threaded=True, ssl_context=(str(cert), str(key)))
    local_url = f'http://127.0.0.1:{local.server_port}'
    public_url = f'https://player-tunnel.invalid:{public.server_port}'
    class Active:
        def poll(self):
            return None
    def start():
        module.tunnel.process = Active()
        module.tunnel.url = public_url
        module.tunnel.registration_token = 'browser-registration'
        return public_url
    def stop():
        module.tunnel.process = module.tunnel.url = module.tunnel.registration_token = None
    monkeypatch.setattr(module.tunnel, 'process', None)
    monkeypatch.setattr(module.tunnel, 'url', None)
    monkeypatch.setattr(module.tunnel, 'registration_token', None)
    monkeypatch.setattr(module.tunnel, 'start', start)
    monkeypatch.setattr(module.tunnel, 'stop', stop)
    client.post('/api/teams', json={'left': 'ARI', 'right': 'ATL'})
    client.post('/api/players', json={'initial': 'B', 'name': 'BILL'})
    client.post('/api/multiplier', json={'multiplier': 4})
    client.post('/api/squares', json={'row': 1, 'col': 0, 'value': 'B'})
    client.post('/api/multiplier', json={'multiplier': 8})
    for server in (local, public):
        threading.Thread(target=server.serve_forever, daemon=True).start()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=[
            # Disposable self-signed HTTPS only; avoid Chromium parallel TLS retry failures.
            '--ignore-certificate-errors',
            '--host-resolver-rules=MAP player-tunnel.invalid 127.0.0.1', '--no-proxy-server'])
        yield browser, local_url, public_url, start
        browser.close()
    for server in (local, public):
        server.shutdown()
        server.server_close()


def screenshot(page, name):
    destination = os.environ.get('SQUARES_SCREENSHOTS')
    if destination:
        Path(destination).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(destination) / f'{name}.png'), full_page=True)


@pytest.mark.parametrize('width,height', [(1280, 900), (390, 844)])
def test_admin_qr_layout_and_delete_refund(browser_game, width, height):
    from playwright.sync_api import expect
    browser, local, public, _ = browser_game
    context = browser.new_context(viewport={'width': width, 'height': height}, ignore_https_errors=True)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('requestfailed', lambda request: errors.append(request.url + ' ' + str(request.failure)) if '/static/' in request.url else None)
    page.goto(local)
    page.locator('#adminLoginBtn').click()
    expect(page.locator('#mainButtons')).to_be_visible()
    page.locator('#loadGameBtn').click()
    expect(page.locator('#landing-overlay')).to_be_hidden()
    expect(page.locator('#genericAlertTitle')).to_have_text('GAME LOADED SUCCESSFULLY')
    page.locator('#genericAlertOkBtn').click()
    page.locator('#joinGameBtn').click()
    expect(page.locator('#joinGameTitle')).to_have_text('LOCAL GAME QR')
    expect(page.locator('#joinGameHelp')).to_have_text('SAME WI-FI · SCAN TO PLAY')
    page.locator('#tunnelToggleBtn').click()
    expect(page.locator('#joinGameTitle')).to_have_text('NEW PLAYER QR')
    expect(page.locator('#joinGameHelp')).to_have_text('SCAN TO PLAY')
    page.locator('#playerQrBtn').click()
    expect(page.locator('#joinGameTitle')).to_have_text('PLAYER QR - BILL')
    label = page.locator('#playerQrLabel').bounding_box()
    button = page.locator('#registrationQrBtn').bounding_box()
    assert label['y'] >= button['y'] + button['height']
    assert page.locator('#joinGameDialog').evaluate('(e) => e.scrollWidth <= e.clientWidth')
    assert page.locator('#joinGameDialog').evaluate('(e) => e.scrollHeight <= e.clientHeight')
    screenshot(page, f'player-qr-{width}')
    page.locator('#resetPlayerQrBtn').click()
    expect(page.locator('#joinGameQr')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#joinGameBtn')).to_be_focused()
    page.evaluate('handleSquareDelete(1, 0)')
    expect(page.locator('#genericAlertTitle')).to_have_text('DELETE SQUARE?')
    expect(page.locator('#genericAlertMessage')).to_contain_text('REFUND: 4 TOKENS')
    expect(page.locator('#genericAlertMessage')).to_contain_text('B — BILL')
    expect(page.locator('#genericAlertMessage')).to_contain_text('ARI: 1 - ATL: 0')
    screenshot(page, f'delete-square-{width}')
    page.locator('#genericAlertCancelBtn').click()
    page.evaluate('handleSquareDelete(1, 0)')
    expect(page.locator('#genericAlertTitle')).to_have_text('DELETE SQUARE?')
    page.locator('#genericAlertOkBtn').click()
    page.wait_for_function("players.B.tokens === 40")
    assert not errors
    context.close()


def test_public_registration_player_menus_and_expired_links(browser_game, client):
    from playwright.sync_api import expect
    browser, _, public, start = browser_game
    start()
    context = browser.new_context(viewport={'width': 390, 'height': 844}, ignore_https_errors=True)
    page = context.new_page()
    requests, errors = [], []
    page.on('request', lambda request: requests.append(request.url))
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('requestfailed', lambda request: errors.append(request.url + ' ' + str(request.failure)) if '/static/' in request.url else None)
    page.goto(public)
    expect(page.locator('#publicJoinHelp')).to_be_visible()
    expect(page.locator('#loginPanel')).to_be_hidden()
    page.goto(public + '/join/register/browser-registration')
    page.locator('#initial').fill('C')
    page.locator('#name').fill('CHRIS')
    page.get_by_role('button', name='CREATE & PLAY').click()
    expect(page.locator('#landing-overlay')).to_be_hidden()
    expect(page.locator('#sessionLabel')).to_have_text('CHRIS')
    mode_box = page.locator('#logoutBtn').bounding_box()
    qr_box = page.locator('#joinGameBtn').bounding_box()
    assert abs(mode_box['y'] - qr_box['y']) <= 1
    page.reload()
    expect(page.locator('#sessionLabel')).to_have_text('CHRIS')
    invite = client.post('/api/player-invites/C').json['url']
    page.goto(invite)
    expect(page.locator('#sessionLabel')).to_have_text('CHRIS')
    for control in ['logoutBtn', 'joinGameBtn', 'logoutBtn', 'joinGameBtn']:
        page.locator('#' + control).click()
        expect(page.locator('#playerModeDialog')).to_be_visible()
        expect(page.locator('#playerModeDialog button')).to_have_count(2)
        expect(page.locator('#switchToAdminBtn')).to_be_hidden()
        expect(page.locator('#playerModeTitle')).to_have_text('PLAYER MODE')
        assert page.evaluate("getComputedStyle(document.body).fontFamily.includes('Press Start 2P')"), errors
        screenshot(page, 'player-mode-mobile')
        page.get_by_role('button', name='BACK TO GAME').click()
        expect(page.locator('#landing-overlay')).to_be_hidden()
        expect(page.locator('#sessionLabel')).to_have_text('CHRIS')
    page.locator('#logoutBtn').click()
    page.keyboard.press('Escape')
    expect(page.locator('#playerModeDialog')).to_be_hidden()
    assert not any('/api/logout' in url or '/api/events' in url for url in requests)
    assert page.evaluate('gameSync.pollOnly') is True
    client.delete('/api/players/C')
    page.evaluate('gameSync.refresh()')
    expect(page.locator('#publicJoinHelp')).to_be_visible()
    expect(page.locator('#loginPanel')).to_be_hidden()
    page.goto(public + '/join/C/expired')
    expect(page.get_by_role('heading', name='LINK EXPIRED')).to_be_visible()
    assert not errors
    context.close()


def test_qr_empty_players_errors_and_reopening(browser_game, client):
    from playwright.sync_api import expect
    browser, local, _, start = browser_game
    start()
    client.delete('/api/players/B')
    context = browser.new_context(viewport={'width': 390, 'height': 844})
    page = context.new_page()
    page.goto(local)
    page.locator('#adminLoginBtn').click()
    expect(page.locator('#mainButtons')).to_be_visible()
    page.locator('#joinGameBtn').click()
    expect(page.locator('#joinGameTitle')).to_have_text('NEW PLAYER QR')
    expect(page.locator('#playerQrBtn')).to_be_disabled()
    expect(page.locator('#resetPlayerQrBtn')).to_be_disabled()
    page.route('**/api/player-registration-qr', lambda route: route.fulfill(
        status=503, content_type='application/json', body='{"error":"TRY AGAIN"}'))
    page.locator('#registrationQrBtn').click()
    expect(page.locator('#joinGameStatus')).to_have_text('TRY AGAIN')
    expect(page.locator('#joinGameQr')).to_be_hidden()
    page.unroute('**/api/player-registration-qr')
    page.keyboard.press('Escape')
    held = []
    page.route('**/api/tunnel', lambda route: held.append(route))
    page.locator('#joinGameBtn').click()
    expect(page.locator('#joinGameStatus')).to_have_text('LOADING…')
    page.keyboard.press('Escape')
    page.locator('#joinGameBtn').click()
    page.unroute('**/api/tunnel')
    assert len(held) == 1
    expect(page.locator('#joinGameTitle')).to_have_text('NEW PLAYER QR')
    page.keyboard.press('Escape')
    client.post('/api/reset')
    page.locator('#joinGameBtn').click()
    expect(page.locator('#joinGameStatus')).to_have_text('SET TEAMS FIRST')
    expect(page.locator('#joinGameQr')).to_be_hidden()
    context.close()


def test_pending_delete_closes_when_square_changes(browser_game, client):
    from playwright.sync_api import expect
    browser, local, _, _ = browser_game
    context = browser.new_context()
    page = context.new_page()
    page.goto(local)
    page.locator('#adminLoginBtn').click()
    page.locator('#loadGameBtn').click()
    expect(page.locator('#genericAlertTitle')).to_have_text('GAME LOADED SUCCESSFULLY')
    page.locator('#genericAlertOkBtn').click()
    page.evaluate('handleSquareDelete(1, 0)')
    expect(page.locator('#genericAlertMessage')).to_contain_text('REFUND: 4 TOKENS')
    client.post('/api/squares', json={'row': 1, 'col': 0, 'value': ''})
    expect(page.locator('#genericAlert')).to_be_hidden()
    assert page.evaluate('pendingSquareDelete') is None
    context.close()
