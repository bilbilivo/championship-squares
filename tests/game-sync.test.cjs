const test = require('node:test');
const assert = require('node:assert/strict');
const GameSync = require('../static/js/game-sync.js');

function setup() {
    let id = 0;
    const timers = new Map(), intervals = new Map(), requests = [], applied = [], sources = [], listeners = {};
    const env = {
        document: {
            hidden: false,
            addEventListener: (name, fn) => { listeners[name] = fn; },
            removeEventListener: name => { delete listeners[name]; }
        },
        addEventListener: (name, fn) => { listeners[name] = fn; },
        removeEventListener: name => { delete listeners[name]; },
        setTimeout: (fn, ms) => { timers.set(++id, {fn, ms}); return id; },
        clearTimeout: key => timers.delete(key),
        setInterval: (fn, ms) => { intervals.set(++id, {fn, ms}); return id; },
        clearInterval: key => intervals.delete(key),
        AbortController, console: {error() {}},
        fetch: (url, options) => new Promise((resolve, reject) => requests.push({url, options, resolve, reject})),
        EventSource: class {
            constructor(url) { this.url = url; this.handlers = {}; sources.push(this); }
            addEventListener(name, fn) { this.handlers[name] = fn; }
            close() { this.closed = true; }
        }
    };
    const sync = new GameSync(data => applied.push(data), env);
    function tick(ms = 40) {
        for (const [key, timer] of [...timers]) {
            if (timer.ms === ms) { timers.delete(key); timer.fn(); }
        }
    }
    async function respond(index, data) {
        requests[index].resolve({ok: true, json: async () => data});
        await new Promise(resolve => setImmediate(resolve));
    }
    return {sync, env, timers, intervals, requests, applied, sources, listeners, tick, respond};
}

test('one connection and no idle polling while push works', async () => {
    const h = setup(); h.sync.start(); h.sync.start();
    assert.equal(h.sources.length, 1);
    h.sources[0].onopen(); assert.equal(h.intervals.size, 0);
    h.tick(); await h.respond(0, {players: {}});
    assert.equal(h.timers.size, 0);
    assert.equal(h.requests[0].options.cache, 'no-store');
});

test('bursts coalesce and events during a read trigger one follow-up read', async () => {
    const h = setup(); h.sync.start();
    const notify = h.sources[0].handlers['game-updated'];
    for (let i = 0; i < 20; i++) notify();
    h.tick(); assert.equal(h.requests.length, 1);
    for (let i = 0; i < 20; i++) notify();
    h.tick(); assert.equal(h.requests.length, 1);
    await h.respond(0, {version: 1}); h.tick(); await h.respond(1, {version: 2});
    assert.deepEqual(h.applied, [{version: 1}, {version: 2}]);
});

test('a mutation invalidates an older read even after the mutation finishes', async () => {
    const h = setup(); h.sync.start(); h.tick();
    await h.sync.mutate(async () => {});
    await h.respond(0, {version: 'stale'}); assert.deepEqual(h.applied, []);
    h.tick(); await h.respond(1, {version: 'saved'});
    assert.deepEqual(h.applied, [{version: 'saved'}]);
});

test('refresh waits until local writes and their UI callbacks finish', async () => {
    const h = setup(); h.sync.start(); let finish;
    const mutation = h.sync.mutate(() => new Promise(resolve => { finish = resolve; }));
    h.tick(); assert.equal(h.requests.length, 0);
    finish(); await mutation; h.tick(); await h.respond(0, {saved: true});
    assert.deepEqual(h.applied, [{saved: true}]);
});

test('failed writes still resync authoritative state', async () => {
    const h = setup(); h.sync.start();
    await assert.rejects(h.sync.mutate(async () => { throw new Error('write failed'); }));
    assert.equal(h.sync.pendingMutations, 0);
    h.tick(); assert.equal(h.requests.length, 1);
});

test('disconnect enables fallback polling and reconnect catches up', async () => {
    const h = setup(); h.sync.start(); h.sources[0].onopen(); h.tick(); await h.respond(0, {version: 1});
    h.sources[0].onerror(); h.sources[0].onerror(); assert.equal(h.intervals.size, 1);
    [...h.intervals.values()][0].fn(); h.tick(); await h.respond(1, {version: 2});
    h.sources[0].onopen(); h.tick(); assert.equal(h.intervals.size, 0);
    await h.respond(2, {version: 3}); assert.equal(h.applied.at(-1).version, 3);
});

test('hidden tabs release connections and refresh on return', async () => {
    const h = setup(); h.sync.start(); h.tick();
    h.env.document.hidden = true; h.listeners.visibilitychange();
    assert.equal(h.sources[0].closed, true); assert.equal(h.intervals.size, 0);
    await h.respond(0, {version: 'hidden'}); assert.deepEqual(h.applied, []);
    h.env.document.hidden = false; h.listeners.visibilitychange(); h.tick();
    assert.equal(h.sources.length, 2);
    await h.respond(1, {version: 'current'}); assert.deepEqual(h.applied, [{version: 'current'}]);
    h.sync.stop(); assert.equal(h.sources[1].closed, true); assert.equal(h.timers.size, 0);
});

test('failed state fetch retries even when push remains connected', async () => {
    const h = setup(); h.sync.start(); h.sources[0].onopen(); h.tick();
    h.requests[0].reject(new Error('offline')); await new Promise(resolve => setImmediate(resolve));
    h.tick(5000); h.tick(); await h.respond(1, {version: 'recovered'});
    assert.deepEqual(h.applied, [{version: 'recovered'}]);
});

test('browsers without EventSource use fallback polling', () => {
    const h = setup(); delete h.env.EventSource;
    h.sync.start(); h.tick(); assert.equal(h.sources.length, 0);
    assert.equal(h.intervals.size, 1); assert.equal(h.requests.length, 1);
});

test('public connections poll without ever opening SSE', async () => {
    const h = setup(); h.sync.setConnection({sync: 'poll'}); h.sync.start();
    assert.equal(h.sources.length, 0); assert.equal(h.intervals.size, 1);
    h.tick(); await h.respond(0, {version: 1});
    [...h.intervals.values()][0].fn(); h.tick(); await h.respond(1, {version: 2});
    assert.deepEqual(h.applied, [{version: 1}, {version: 2}]);
    h.env.document.hidden = true; h.listeners.visibilitychange();
    assert.equal(h.intervals.size, 0);
    h.env.document.hidden = false; h.listeners.visibilitychange();
    assert.equal(h.intervals.size, 1); assert.equal(h.sources.length, 0);
    h.listeners.online(); assert.equal(h.intervals.size, 1);
    h.sync.stop(); assert.equal(h.intervals.size, 0);
});

test('server capability switches an existing SSE connection to polling', () => {
    const h = setup(); h.sync.start(); h.sources[0].onopen();
    h.sync.setConnection({sync: 'poll'});
    assert.equal(h.sources[0].closed, true); assert.equal(h.intervals.size, 1);
    assert.equal(h.sources.length, 1);
});
