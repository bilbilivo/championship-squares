const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function setup() {
    const elements = {};
    const controls = [{}, {}];
    const adminPanels = [{}, {}];
    const calls = [];
    const context = vm.createContext({
        players: {A: {name: 'Alice'}},
        document: {
            getElementById: id => elements[id] ||= {style: {}},
            querySelectorAll: selector => selector.includes('.player-form') ? adminPanels : controls,
            addEventListener() {},
        },
        fetch: async (url, options) => {
            calls.push([url, options]);
            return {ok: true, json: async () => ({players: {A: {name: 'Alice'}}})};
        },
        applyGameState: state => calls.push(['apply', state]),
        gameSync: { start: () => calls.push(['sync']) },
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/js/login.js'), 'utf8'), context);
    return {elements, controls, adminPanels, calls, context};
}

test('ADMIN enters New/Load menu with full controls', async () => {
    const env = setup();
    await vm.runInContext("enterSession({role: 'admin', player: null})", env.context);
    assert.equal(env.elements.mainButtons.style.display, 'flex');
    assert.equal(env.elements.loginPanel.hidden, true);
    assert.ok(env.controls.every(control => !control.disabled));
    assert.ok(env.adminPanels.every(panel => !panel.hidden));
    assert.deepEqual(env.calls, []);
});

test('PLAYER loads current game directly with admin controls disabled', async () => {
    const env = setup();
    await vm.runInContext("enterSession({role: 'player', player: 'A'})", env.context);
    assert.equal(env.elements.mainButtons.style.display, 'none');
    assert.equal(env.elements['landing-overlay'].style.display, 'none');
    assert.equal(env.elements.sessionLabel.textContent, 'Alice');
    assert.ok(env.controls.every(control => control.disabled));
    assert.ok(env.adminPanels.every(panel => panel.hidden));
    assert.deepEqual(env.calls.map(call => call[0]), ['/api/state', 'apply', 'sync']);
});

test('Signed out sessions see mode selection and no game controls', async () => {
    const env = setup();
    await vm.runInContext('enterSession({role: null, player: null})', env.context);
    assert.equal(env.elements.loginPanel.hidden, false);
    assert.equal(env.elements.mainButtons.style.display, 'none');
    assert.ok(env.controls.every(control => control.disabled));
    assert.deepEqual(env.calls, []);
});
