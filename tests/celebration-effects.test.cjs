const test = require('node:test');
const assert = require('node:assert/strict');
const effects = require('../static/js/celebration-effects.js');

function scene() {
    let now = 0, nextId = 0;
    const timers = new Map();
    function element() {
        return {
            isConnected: true,
            children: [],
            style: {setProperty() {}},
            appendChild(child) { this.children.push(child); child.parent = this; },
            remove() {
                if (this.parent) {
                    this.parent.children = this.parent.children.filter(child => child !== this);
                    this.parent = null;
                }
            }
        };
    }
    const container = element();
    const env = {
        document: {hidden: false, createElement: element},
        setTimeout(callback, delay) {
            timers.set(++nextId, {callback, at: now + delay});
            return nextId;
        },
        clearTimeout(id) { timers.delete(id); }
    };
    function advance(ms) {
        const end = now + ms;
        while (true) {
            const next = [...timers].sort((a, b) => a[1].at - b[1].at)[0];
            if (!next || next[1].at > end) break;
            timers.delete(next[0]);
            now = next[1].at;
            next[1].callback();
        }
        now = end;
    }
    return {container, env, timers, advance};
}

test('fireworks keep launching after ten seconds with bounded particles and clean up on close', () => {
    const h = scene();
    const stop = effects.fireworks(h.container, ['gold', 'blue'], 0, h.env);
    const first = h.container.children[0];
    assert.equal(first.children.length, 12);
    for (let i = 0; i < 60; i++) {
        h.advance(1000);
        assert.ok(h.container.children.length > 0 && h.container.children.length <= 3);
        assert.ok(h.timers.size <= 4);
    }
    assert.ok(!h.container.children.includes(first));
    stop(); stop(); h.advance(10000);
    assert.equal(h.container.children.length, 0);
    assert.equal(h.timers.size, 0);
});

test('closing before a staggered burst prevents it from launching', () => {
    const h = scene();
    const stop = effects.fireworks(h.container, ['gold'], 200, h.env);
    stop(); h.advance(1000);
    assert.equal(h.container.children.length, 0);
    assert.equal(h.timers.size, 0);
});

test('hidden tabs skip bursts and resume when visible; detached overlays stop work', () => {
    const h = scene();
    effects.fireworks(h.container, ['gold'], 0, h.env);
    h.env.document.hidden = true; h.advance(5000);
    assert.equal(h.container.children.length, 0);
    assert.equal(h.timers.size, 1);
    h.env.document.hidden = false; h.advance(700);
    assert.equal(h.container.children.length, 1);
    h.container.isConnected = false; h.advance(700);
    assert.equal(h.container.children.length, 0);
    assert.equal(h.timers.size, 0);
});

test('opening End Game starts both fireworks without a button in every motion mode', () => {
    for (const reducedMotion of [false, true]) {
        for (const liteMode of [false, true]) {
            const h = scene();
            const classes = new Set(liteMode ? ['lite-mode'] : []);
            const right = h.env.document.createElement('div');
            const overlay = {
                classList: {
                    add(name) { classes.add(name); },
                    remove(name) { classes.delete(name); }
                },
                querySelector(selector) {
                    const containers = {'#fireworksLeft': h.container, '#fireworksRight': right};
                    assert.ok(selector in containers, 'Playback must not require a button');
                    return containers[selector];
                }
            };
            h.env.matchMedia = () => ({matches: reducedMotion});
            const stop = effects.mount(overlay, ['gold'], h.env);
            assert.ok(classes.has('fireworks-playing'));
            assert.equal(h.container.children.length, 1);
            h.advance(200);
            assert.equal(right.children.length, 1);
            h.advance(12000);
            assert.ok(h.container.children.length > 0);
            assert.ok(right.children.length > 0);
            stop(); stop(); h.advance(1000);
            assert.ok(!classes.has('fireworks-playing'));
            assert.equal(h.container.children.length, 0);
            assert.equal(right.children.length, 0);
            assert.equal(h.timers.size, 0);
        }
    }
});
