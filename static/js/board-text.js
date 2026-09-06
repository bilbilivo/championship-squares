// SPDX-License-Identifier: MIT
// Center visible glyphs, accounting for the font's side bearings and baseline.
const BoardText = (() => {
    const fontSize = 100;
    const font = `${fontSize}px "Press Start 2P", monospace`;

    function offsets(metrics) {
        return {
            dx: (metrics.width + metrics.actualBoundingBoxLeft - metrics.actualBoundingBoxRight) / (2 * fontSize),
            dy: (metrics.actualBoundingBoxAscent - metrics.actualBoundingBoxDescent) / (2 * fontSize)
        };
    }

    function create(context) {
        const cache = new Map();
        function center(selection) {
            selection.each(function () {
                const text = this.textContent;
                let offset = cache.get(text);
                if (!offset) {
                    context.font = font;
                    context.textAlign = 'left';
                    context.textBaseline = 'alphabetic';
                    offset = text ? offsets(context.measureText(text)) : {dx: 0, dy: 0};
                    cache.set(text, offset);
                }
                // em offsets scale equally in the zoomed grid and pinned headers.
                this.setAttribute('dx', `${offset.dx}em`);
                this.setAttribute('dy', `${offset.dy}em`);
            });
        }
        return {center, clear: () => cache.clear()};
    }

    return {create, offsets};
})();

if (typeof module !== 'undefined') module.exports = BoardText;
