const test = require('node:test');
const assert = require('node:assert/strict');
const BoardText = require('../static/js/board-text.js');

const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-8);

test('visible glyph bounds are centered on both axes at every zoom', () => {
    // Asymmetric side bearings, multi-digit scores, overhangs and descenders.
    const samples = [
        {width: 100, actualBoundingBoxLeft: 0, actualBoundingBoxRight: 87.5,
            actualBoundingBoxAscent: 87.5, actualBoundingBoxDescent: 0},
        {width: 300, actualBoundingBoxLeft: -12.5, actualBoundingBoxRight: 287.5,
            actualBoundingBoxAscent: 87.5, actualBoundingBoxDescent: 0},
        {width: 100, actualBoundingBoxLeft: 5, actualBoundingBoxRight: 105,
            actualBoundingBoxAscent: 70, actualBoundingBoxDescent: 20}
    ];
    for (const metrics of samples) {
        const {dx, dy} = BoardText.offsets(metrics);
        for (const size of [9, 18, 36, 72]) {
            const centerX = 120, centerY = 80;
            const scale = size / 100;
            const originX = centerX + dx * size - metrics.width * scale / 2;
            const baselineY = centerY + dy * size;
            const left = originX - metrics.actualBoundingBoxLeft * scale;
            const right = originX + metrics.actualBoundingBoxRight * scale;
            const top = baselineY - metrics.actualBoundingBoxAscent * scale;
            const bottom = baselineY + metrics.actualBoundingBoxDescent * scale;
            near((left + right) / 2, centerX);
            near((top + bottom) / 2, centerY);
        }
    }
});

test('measurements are reused, refreshed after font loading, and reapplied when text changes', () => {
    let calls = 0;
    const context = {
        measureText(text) {
            calls++;
            return {width: 100 * text.length, actualBoundingBoxLeft: 0,
                actualBoundingBoxRight: 100 * text.length - 12.5,
                actualBoundingBoxAscent: 87.5, actualBoundingBoxDescent: 0};
        }
    };
    const renderer = BoardText.create(context);
    const node = {textContent: 'A', setAttribute(name, value) { this[name] = value; }};
    const selection = {each(callback) { callback.call(node); }};
    renderer.center(selection);
    assert.equal(node.dx, '0.0625em');
    assert.equal(node.dy, '0.4375em');
    renderer.center(selection);
    assert.equal(calls, 1);
    node.textContent = '100';
    renderer.center(selection);
    assert.equal(calls, 2);
    renderer.clear(); renderer.center(selection);
    assert.equal(calls, 3);
    node.textContent = '';
    renderer.center(selection);
    assert.equal(node.dx, '0em');
    assert.equal(node.dy, '0em');
    assert.equal(calls, 3);
});
