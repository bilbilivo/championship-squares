const { test } = require('node:test');
const assert = require('node:assert/strict');
const geometry = require('../static/js/board-geometry.js');

const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-8,
    `${actual} != ${expected}`);

test('zoom out moves below Play view and stops at the full-board scale', () => {
    const v = geometry.metrics(1200, 600, 71);
    const next = geometry.zoomScale(v.play, 0.8, v);
    assert.ok(next < v.play);
    near(next, v.play * 0.8);
    near(geometry.zoomScale(next, 0.001, v), v.fit);
    near(geometry.zoomScale(v.max, 2, v), v.max);
    near(geometry.zoomScale(next, 1, v), next);
});

test('Play view covers wide and tall viewports for every sport, with readable cells', () => {
    for (const count of [11, 13, 31, 71, 161]) {
        for (const [width, height] of [[2800, 1200], [1050, 540], [320, 600], [700, 250]]) {
            for (const touch of [true, false]) {
                const v = geometry.metrics(width, height, count, 40, touch);
                assert.ok(v.size * v.play >= geometry.layout(v, v.play).plotWidth - 1e-8);
                assert.ok(v.size * v.play >= geometry.layout(v, v.play).plotHeight - 1e-8);
                assert.ok(40 * v.play >= (touch ? 44 : 40));
                assert.ok(v.max >= v.play);
            }
        }
    }
});

test('panning to any extreme exposes neither blank edges nor unreachable final cells', () => {
    const v = geometry.metrics(1200, 650, 71);
    for (const k of [v.play, v.max]) {
        const { header, plotWidth, plotHeight } = geometry.layout(v, k);
        const start = geometry.constrain({ x: 1e6, y: 1e6, k }, v);
        near(start.x, header);
        near(start.y, header);
        const end = geometry.constrain({ x: -1e6, y: -1e6, k }, v);
        near(end.x + v.size * k, header + plotWidth);
        near(end.y + v.size * k, header + plotHeight);
    }
});

test('overview contains the complete board flush with both score axes', () => {
    for (const [width, height] of [[1200, 500], [350, 650]]) {
        const v = geometry.metrics(width, height, 71);
        const t = geometry.centered([v.size / 2, v.size / 2], v.fit, v);
        const { header, plotWidth, plotHeight } = geometry.layout(v, t.k);
        near(t.x, header);
        near(t.y, header);
        assert.ok(v.size * t.k <= plotWidth + 1e-8);
        assert.ok(v.size * t.k <= plotHeight + 1e-8);
    }
});

test('zoomed-out panning and resizing cannot open a gap beside either axis', () => {
    for (const [width, height] of [[1200, 500], [350, 650], [650, 650]]) {
        const v = geometry.metrics(width, height, 71);
        for (const k of [v.fit, (v.fit + v.play) / 2, v.play]) {
            const area = geometry.layout(v, k);
            for (const offset of [-1e6, 0, 1e6]) {
                const t = geometry.constrain({ x: offset, y: offset, k }, v);
                assert.ok(t.x <= area.header + 1e-8);
                assert.ok(t.y <= area.header + 1e-8);
                if (v.size * k <= area.plotWidth) near(t.x, area.header);
                if (v.size * k <= area.plotHeight) near(t.y, area.header);
            }
        }
    }
});

test('resize preserves a viewed score coordinate when it is away from the edges', () => {
    const initial = geometry.metrics(1000, 700, 71);
    const point = [1400, 1400];
    let t = geometry.centered(point, 1.5, initial);
    for (const [width, height] of [[350, 600], [2400, 1100], [1000, 700]]) {
        const v = geometry.metrics(width, height, 71);
        t = geometry.centered(point, t.k, v);
        const actual = geometry.center(t, v);
        near(actual[0], point[0]);
        near(actual[1], point[1]);
    }
});

test('Go to score keeps corner scores visible after clamping', () => {
    const v = geometry.metrics(1200, 600, 71);
    for (const row of [0, 70]) {
        for (const col of [0, 70]) {
            const point = [(col + 0.5) * 40, (row + 0.5) * 40];
            const t = geometry.scoreView([{ row, col }], v);
            const { header, plotWidth, plotHeight } = geometry.layout(v, t.k);
            const x = t.x + point[0] * t.k;
            const y = t.y + point[1] * t.k;
            assert.ok(x >= header && x <= header + plotWidth);
            assert.ok(y >= header && y <= header + plotHeight);
        }
    }
});

test('Go to score shows 15 cells on the shorter dimension and anchors the score top-left', () => {
    for (const [width, height] of [[640, 640], [1200, 600], [350, 650]]) {
        for (const touch of [true, false]) {
            const v = geometry.metrics(width, height, 71, 40, touch);
            const t = geometry.scoreView([{ row: 20, col: 15 }], v);
            const { header, plotWidth, plotHeight } = geometry.layout(v, t.k);
            near(Math.min(plotWidth, plotHeight) / (40 * t.k), 15);
            near(t.x + 15 * 40 * t.k, header);
            near(t.y + 20 * 40 * t.k, header);
        }
    }
});

test('Go to score anchors the bounds of the score and all winning squares', () => {
    const v = geometry.metrics(640, 640, 71);
    const squares = [{ row: 20, col: 15 }, { row: 17, col: 13 }, { row: 18, col: 11 }];
    const t = geometry.scoreView(squares, v);
    const { header } = geometry.layout(v, t.k);
    near(t.x + 11 * 40 * t.k, header);
    near(t.y + 17 * 40 * t.k, header);
    near(40 * t.k, 40);
});

test('Go to score widens enough to show distant winning squares in full', () => {
    for (const [width, height] of [[1200, 600], [350, 650]]) {
        const v = geometry.metrics(width, height, 71);
        const squares = [{ row: 20, col: 15 }, { row: 2, col: 3 }, { row: 40, col: 45 }];
        const t = geometry.scoreView(squares, v);
        const { header } = geometry.layout(v, t.k);
        for (const { row, col } of squares) {
            assert.ok(t.x + col * 40 * t.k >= header - 1e-8);
            assert.ok(t.y + row * 40 * t.k >= header - 1e-8);
            assert.ok(t.x + (col + 1) * 40 * t.k <= width + 1e-8);
            assert.ok(t.y + (row + 1) * 40 * t.k <= height + 1e-8);
        }
    }
});

test('Go to score fits smaller sports boards without exceeding zoom limits', () => {
    for (const count of [11, 13]) {
        const v = geometry.metrics(350, 650, count);
        const t = geometry.scoreView([{ row: count - 1, col: 0 }], v);
        near(t.k, v.fit);
        near(t.x, geometry.layout(v, t.k).header);
        near(t.y, geometry.layout(v, t.k).header);
    }
});

test('hidden or very small containers still produce finite geometry', () => {
    const v = geometry.metrics(0, 0, 13);
    const t = geometry.centered([0, 0], v.play, v);
    for (const value of [...Object.values(v), ...Object.values(t)]) assert.ok(Number.isFinite(value));
});


test('score headers are one full grid cell at every zoom level', () => {
    for (const count of [13, 31, 71, 161]) {
        const v = geometry.metrics(1200, 650, count);
        for (const k of [v.fit, 0.5, v.play, 2, v.max]) {
            const area = geometry.layout(v, k);
            near(area.header, 40 * k);
            near(area.header + area.plotWidth, v.width);
            near(area.header + area.plotHeight, v.height);
            const start = geometry.constrain({ x: 1e6, y: 1e6, k }, v);
            assert.ok(start.x >= area.header || v.size * k > area.plotWidth);
        }
        // The complete grid plus its score-header row fits Overview exactly on its short axis.
        near((count + 1) * 40 * v.fit, Math.min(v.width, v.height));
    }
});
