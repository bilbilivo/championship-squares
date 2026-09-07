/* SPDX-License-Identifier: MIT */
(() => {
    const byId = id => document.getElementById(id);
    const button = byId('joinGameBtn');
    const dialog = byId('joinGameDialog');
    const title = byId('joinGameTitle');
    const help = byId('joinGameHelp');
    const status = byId('joinGameStatus');
    const qr = byId('joinGameQr');
    const controls = byId('tunnelControls');
    const tunnelStatus = byId('tunnelStatus');
    const toggle = byId('tunnelToggleBtn');
    const registration = byId('registrationQrBtn');
    const playerControls = byId('playerQrControls');
    const select = byId('playerQrSelect');
    const playerQr = byId('playerQrBtn');
    const reset = byId('resetPlayerQrBtn');
    let active = false;
    let busy = false;
    let generation = 0;

    function clear(message = 'LOADING…') {
        qr.hidden = true;
        qr.removeAttribute('src');
        status.hidden = false;
        status.textContent = message;
        title.textContent = 'GAME QR';
        help.textContent = '';
    }
    function show(data, heading, isPublic) {
        const url = new URL(data.url);
        if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
            throw new Error('INVALID LINK');
        }
        title.textContent = heading;
        help.textContent = isPublic ? 'SCAN TO PLAY' : 'SAME WI-FI · SCAN TO PLAY';
        qr.alt = heading;
        qr.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(data.svg)}`;
        qr.hidden = false;
        status.hidden = true;
    }
    async function request(url, options) {
        const response = await fetch(url, {cache: 'no-store', ...options});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'QR FAILED — RETRY');
        return data;
    }
    function setDisabled() {
        toggle.disabled = registration.disabled = select.disabled = busy;
        playerQr.disabled = reset.disabled = busy || !select.options.length;
    }
    async function run(action) {
        if (busy) return;
        busy = true;
        const current = ++generation;
        clear();
        setDisabled();
        try { await action(() => current === generation && dialog.open); }
        catch (error) { if (current === generation) clear(error.message); }
        finally {
            busy = false;
            setDisabled();
            // A close/reopen during a slow tunnel request must not leave LOADING forever.
            if (current !== generation && dialog.open) run(refresh);
        }
    }
    async function refresh(valid) {
        controls.hidden = !isAdmin();
        if (!isAdmin()) {
            const data = await request('/api/join');
            if (valid()) show(data, 'LOCAL GAME QR', false);
            return;
        }
        const state = await request('/api/tunnel');
        if (!valid()) return;
        active = state.active;
        tunnelStatus.textContent = active ? 'TUNNEL ON' : 'TUNNEL OFF';
        toggle.textContent = active ? 'DISABLE TUNNEL' : 'ENABLE TUNNEL';
        registration.hidden = playerControls.hidden = !active;
        if (active) {
            const game = await request('/api/state');
            if (!valid()) return;
            const selected = select.value;
            select.replaceChildren();
            Object.entries(game.players).sort().forEach(([id, player]) =>
                select.add(new Option(`${id} — ${player.name}`, id)));
            if (game.players[selected]) select.value = selected;
            if (!game.teams.left || !game.teams.right) { clear('SET TEAMS FIRST'); return; }
            const data = await request('/api/player-registration-qr');
            if (valid()) show(data, 'NEW PLAYER QR', true);
        } else {
            const data = await request('/api/join');
            if (valid()) show(data, 'LOCAL GAME QR', false);
        }
    }
    button.addEventListener('click', () => {
        if (loginSession.role === 'player') { showPlayerMode(); return; }
        dialog.showModal();
        controls.hidden = true;
        if (publicConnection()) { clear('SCAN PLAYER QR'); return; }
        run(refresh);
    });
    toggle.addEventListener('click', () => run(async valid => {
        await request('/api/tunnel', {method: active ? 'DELETE' : 'POST'});
        await refresh(valid);
    }));
    registration.addEventListener('click', () => run(async valid => {
        const data = await request('/api/player-registration-qr');
        if (valid()) show(data, 'NEW PLAYER QR', true);
    }));
    async function showPlayer(valid, rotate = false) {
        const url = `/api/player-invites/${encodeURIComponent(select.value)}`;
        if (rotate) await request(url, {method: 'DELETE'});
        const data = await request(url, {method: 'POST'});
        if (valid()) show(data, `PLAYER QR - ${data.player_name}`, true);
    }
    playerQr.addEventListener('click', () => run(valid => showPlayer(valid)));
    reset.addEventListener('click', () => run(valid => showPlayer(valid, true)));
    dialog.addEventListener('close', () => { generation++; clear(); button.focus(); });
    dialog.addEventListener('click', event => {
        const bounds = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
    });
})();
