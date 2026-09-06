// SPDX-License-Identifier: MIT
let loginSession = { role: null, player: null };
const isAdmin = () => loginSession.role === 'admin';

function applyModeControls() {
    document.querySelectorAll('#teamLeft, #teamRight, #leftScore, #rightScore, #multiplierButtons button')
        .forEach(control => { control.disabled = !isAdmin(); });
    document.querySelectorAll('.player-form, .legend-controls').forEach(control => {
        control.hidden = !isAdmin();
    });
    const playerName = typeof players !== 'undefined' ? players[loginSession.player]?.name : '';
    document.getElementById('sessionLabel').textContent = isAdmin() ? 'ADMIN' : playerName || '';
    document.getElementById('logoutBtn').hidden = !loginSession.role;
}

async function loginRequest(path, payload) {
    const response = await fetch(path, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Unable to log in');
    return data;
}

async function enterSession(session) {
    loginSession = session;
    applyModeControls();
    document.getElementById('loginPanel').hidden = Boolean(session.role);
    document.getElementById('mainButtons').style.display = isAdmin() ? 'flex' : 'none';
    if (session.role === 'player') {
        const response = await fetch('/api/state', { cache: 'no-store' });
        if (!response.ok) throw new Error('Unable to load the current game');
        applyGameState(await response.json(), { focusScore: true });
        document.getElementById('landing-overlay').style.display = 'none';
        gameSync.start();
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const status = document.getElementById('loginStatus');
    const run = async action => {
        status.textContent = '';
        const buttons = document.querySelectorAll('#loginPanel button');
        buttons.forEach(button => { button.disabled = true; });
        try { await action(); }
        catch (error) {
            status.textContent = error.message;
            document.getElementById('loginPanel').hidden = false;
        } finally {
            buttons.forEach(button => { button.disabled = false; });
            document.getElementById('startPlayerBtn').disabled = document.getElementById('existingPlayer').disabled;
            document.getElementById('createPlayerBtn').disabled = document.getElementById('loginInitial').disabled;
        }
    };
    document.getElementById('adminLoginBtn').onclick = () => run(async () => {
        await enterSession(await loginRequest('/api/login', { role: 'admin' }));
    });
    document.getElementById('playerLoginBtn').onclick = () => run(async () => {
        const response = await fetch('/api/state', { cache: 'no-store' });
        if (!response.ok) throw new Error('Unable to get current players');
        const data = await response.json();
        const select = document.getElementById('existingPlayer');
        select.replaceChildren();
        Object.entries(data.players).sort().forEach(([initial, info]) => {
            select.add(new Option(`${initial} — ${info.name}`, initial));
        });
        select.disabled = select.options.length === 0;
        if (select.disabled) select.add(new Option('NO PLAYERS', ''));
        const teamsReady = Boolean(data.teams?.left && data.teams?.right);
        document.querySelectorAll('#createPlayerForm input, #createPlayerForm button').forEach(control => {
            control.disabled = !teamsReady;
        });
        document.getElementById('teamSetupHelp').hidden = teamsReady;
        document.getElementById('playerLoginPanel').hidden = false;
        if (select.disabled && teamsReady) document.getElementById('loginInitial').focus();
    });
    document.getElementById('existingPlayerForm').onsubmit = event => {
        event.preventDefault();
        if (document.getElementById('existingPlayer').disabled) return;
        run(async () => enterSession(await loginRequest('/api/login', {
            role: 'player', initial: document.getElementById('existingPlayer').value
        })));
    };
    document.getElementById('createPlayerForm').onsubmit = event => {
        event.preventDefault();
        if (document.getElementById('loginInitial').disabled) return;
        run(async () => enterSession(await loginRequest('/api/login', {
            role: 'player', create: true,
            initial: document.getElementById('loginInitial').value.trim().toUpperCase(),
            name: document.getElementById('loginName').value.trim().toUpperCase()
        })));
    };
    const logout = () => run(async () => {
        await loginRequest('/api/logout', {});
        gameSync.stop();
        window.location.reload();
    });
    document.getElementById('logoutBtn').onclick = logout;
    document.getElementById('landingLogoutBtn').onclick = logout;
    await run(async () => {
        const response = await fetch('/api/session', { cache: 'no-store' });
        if (!response.ok) throw new Error('Unable to restore session');
        await enterSession(await response.json());
    });
});
