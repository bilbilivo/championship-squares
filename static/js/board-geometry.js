// SPDX-License-Identifier: MIT
// Pure viewport geometry shared by the browser and Node regression tests.
const BoardGeometry = (() => {

    function metrics(width, height, count, cellSize = 40, touch = false) {
        width = Math.max(1, width);
        height = Math.max(1, height);
        const size = count * cellSize;
        // Include one full score-header cell when fitting the board.
        const fit = Math.min(width, height) / (size + cellSize);
        const play = Math.max((touch ? 44 : 40) / cellSize,
            width / (size + cellSize), height / (size + cellSize));
        const max = Math.max(play, Math.min(Math.max(4, play * 2),
            Math.min(width, height) / (2 * cellSize)));
        return { width, height, size, cellSize, fit, play, max };
    }

    function layout(viewport, k) {
        const header = viewport.cellSize * k;
        return { header, plotWidth: Math.max(1, viewport.width - header),
            plotHeight: Math.max(1, viewport.height - header) };
    }

    function constrain(transform, viewport) {
        const { header, plotWidth, plotHeight } = layout(viewport, transform.k);
        const size = viewport.size * transform.k;
        // A fully visible dimension stays flush with its pinned score axis.
        const position = (value, available) => size <= available
            ? header
            : Math.max(header + available - size, Math.min(header, value));
        return { x: position(transform.x, plotWidth),
            y: position(transform.y, plotHeight), k: transform.k };
    }

    function centered(point, k, viewport) {
        const { header, plotWidth, plotHeight } = layout(viewport, k);
        return constrain({ x: header + plotWidth / 2 - point[0] * k,
            y: header + plotHeight / 2 - point[1] * k, k }, viewport);
    }

    function center(transform, viewport) {
        const { header, plotWidth, plotHeight } = layout(viewport, transform.k);
        return [(header + plotWidth / 2 - transform.x) / transform.k,
            (header + plotHeight / 2 - transform.y) / transform.k];
    }

    function zoomScale(current, factor, viewport) {
        return Math.max(viewport.fit, Math.min(viewport.max, current * factor));
    }

    function scoreView(squares, viewport) {
        const firstRow = Math.min(...squares.map(square => square.row));
        const firstCol = Math.min(...squares.map(square => square.col));
        const lastRow = Math.max(...squares.map(square => square.row));
        const lastCol = Math.max(...squares.map(square => square.col));
        // Include the pinned score header plus at least 15 playable cells.
        // Expand further when the score and winning squares are farther apart.
        const rows = Math.max(15, lastRow - firstRow + 1);
        const cols = Math.max(15, lastCol - firstCol + 1);
        const k = zoomScale(Math.min(
            viewport.width / ((cols + 1) * viewport.cellSize),
            viewport.height / ((rows + 1) * viewport.cellSize)
        ), 1, viewport);
        const { header } = layout(viewport, k);
        return constrain({
            x: header - firstCol * viewport.cellSize * k,
            y: header - firstRow * viewport.cellSize * k,
            k
        }, viewport);
    }

    return { metrics, layout, constrain, centered, center, zoomScale, scoreView };
})();

if (typeof module !== 'undefined') module.exports = BoardGeometry;
