const test = require('node:test');
const assert = require('node:assert/strict');
const CelebrationSync = require('../static/js/celebration-sync.js');

function setup() {
    const opened = [], closed = [];
    const sync = new CelebrationSync((event, dismiss) => {
        opened.push({event, dismiss});
        return () => closed.push(event.id);
    });
    return {sync, opened, closed};
}

const event = id => ({id, standings: []});

test('initial state establishes a baseline without replaying', () => {
    for (const initial of [null, event('existing')]) {
        const h = setup();
        assert.equal(h.sync.observe(initial), false);
        assert.equal(h.opened.length, 0);
    }
});

test('an unseen event opens once', () => {
    const h = setup(); h.sync.observe(null);
    assert.equal(h.sync.observe(event('one')), true);
    assert.equal(h.sync.observe(event('one')), false);
    assert.deepEqual(h.opened.map(item => item.event.id), ['one']);
});

test('immediate presentation prevents a duplicate synced event', () => {
    const h = setup(); h.sync.observe(null);
    assert.equal(h.sync.present(event('one')), true);
    assert.equal(h.sync.observe(event('one')), false);
    assert.equal(h.opened.length, 1);
});

test('local dismissal does not reopen the same event', () => {
    const h = setup(); h.sync.observe(null); h.sync.observe(event('one'));
    h.opened[0].dismiss();
    assert.deepEqual(h.closed, ['one']);
    h.sync.observe(event('one'));
    assert.equal(h.opened.length, 1);
});

test('a new event replaces the current event', () => {
    const h = setup(); h.sync.observe(null); h.sync.observe(event('one'));
    h.sync.observe(event('two'));
    assert.deepEqual(h.closed, ['one']);
    assert.deepEqual(h.opened.map(item => item.event.id), ['one', 'two']);
});

test('reset state closes the current event', () => {
    const h = setup(); h.sync.observe(null); h.sync.observe(event('one'));
    h.sync.observe(null);
    h.sync.observe(null);
    h.sync.dismiss();
    assert.deepEqual(h.closed, ['one']);
});
