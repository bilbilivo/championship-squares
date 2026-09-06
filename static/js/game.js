// SPDX-License-Identifier: MIT
// Copyright (c) 2025 Stephane Belliveau

// Initialize variables
const baseSize = 40;
let currentSize = baseSize;
// Update maxScore variable to be dynamic
let maxScore = 60; // Default NFL score, will be updated based on sport
// Lite mode - detected from html class set by server
const isLiteMode = document.documentElement.classList.contains('lite-mode') || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let players = {};  // Format: {'A': {'name': 'Alice', 'playerIndex': 0, 'bets': 0, 'tokens': 40}
let currentSport = 'nfl';  // Default sport
let currentMultiplier = 1;  // Current betting multiplier
let availableMultipliers = [1, 2, 4, 8];  // Available multipliers for current sport
let multiplierLabels = ['<Q1', '<Q2', '<Q3', '<Q4'];  // Labels for when to use each multiplier
let tokensPerPlayer = 40;  // Tokens each player gets for current sport

// The board container determines the available drawing area.
const gridContainer = document.querySelector('.grid-container');
const boardText = BoardText.create(document.createElement('canvas').getContext('2d'));

// Get color from index using d3's color scale
const playerColorScale = d3.scaleOrdinal(d3.schemeCategory10);

// Modify the setSportTheme function to have an option to skip the API call
function setSportTheme(sport, skipAPICall = false) {
    const root = document.documentElement;
    currentSport = sport.toLowerCase();
    
    // Update game title
    updateGameTitle(currentSport);
    
    root.style.setProperty('--retro-primary', `var(--${sport}-primary)`);
    root.style.setProperty('--retro-dark', `var(--${sport}-dark)`);
    root.style.setProperty('--retro-light', `var(--${sport}-light)`);
    root.style.setProperty('--retro-bg', `var(--${sport}-bg)`);
    root.style.setProperty('--retro-logo-primary', `var(--${sport}-logo-primary)`);
    root.style.setProperty('--retro-logo-secondary', `var(--${sport}-logo-secondary)`);

    // Only make the API call if not skipped
    if (!skipAPICall) {
        gameSync.mutate(() => fetch('/api/sport', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sport: currentSport })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                maxScore = data.max_score;
                availableMultipliers = data.available_multipliers || [1];
                multiplierLabels = data.multiplier_labels || [];
                tokensPerPlayer = data.tokens_per_player || 40;
                currentMultiplier = 1;
                updateMultiplierButtons();
                createGrid(); // Recreate grid with new max score
            }
        })
        .catch(error => console.error('Error updating sport:', error)));
    }
    
    // Update team selections
    populateTeamSelects();
}


// Generate 8-bit helmet SVG with both team colors
function generateHelmetSVG(primaryColor, secondaryColor) {
	return `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
            <!-- Main helmet shell -->
            <path d="M4 16 L8 8 L24 8 L28 16 L24 24 L8 24 Z" fill="${primaryColor}"/>
            <!-- Secondary color stripe -->
            <path d="M10 12 L22 12 L24 16 L22 20 L10 20 L8 16 Z" fill="${secondaryColor}"/>
            <!-- Facemask -->
            <path d="M12 14 L20 14 L21 16 L20 18 L12 18 L11 16 Z" fill="${primaryColor}"/>
        </svg>`;
}

// Function to update title based on selected sport
function updateGameTitle(sport) {
    const titles = {
        'fifa': 'WORLD CUP SQUARES',
        'nfl': 'SUPER BOWL SQUARES',
        'nhl': 'SLAP SHOT SQUARES',
        'nba': 'SLAM DUNK SQUARES',
        'mlb': 'GRAND SLAM SQUARES',
        'olym': 'GOLD MEDAL SQUARES'
    };

    const title = titles[sport] || 'CHAMPIONSHIP SQUARES';
    document.getElementById('gameTitle').textContent = title;
    document.getElementById('gameTitleLanding').textContent = title;
    document.title = title;
}

// Function to update multiplier buttons based on available multipliers
function updateMultiplierButtons() {
    const container = document.getElementById('multiplierButtons');
    container.innerHTML = '';

    availableMultipliers.forEach((multiplier, index) => {
        const button = document.createElement('button');
        button.className = 'multiplier-btn';

        // Create button content with multiplier and label
        const multiplierText = document.createElement('div');
        multiplierText.className = 'multiplier-value';
        multiplierText.textContent = `${multiplier}x`;

        const labelText = document.createElement('div');
        labelText.className = 'multiplier-hint';
        labelText.textContent = multiplierLabels[index] || '';

        button.appendChild(multiplierText);
        button.appendChild(labelText);
        button.onclick = () => selectMultiplier(multiplier);

        if (multiplier === currentMultiplier) {
            button.classList.add('active');
        }

        container.appendChild(button);
    });
}

// Function to select a multiplier
function selectMultiplier(multiplier) {
    currentMultiplier = multiplier;

    // Update button states - remove active from all, then add to the selected one
    const buttons = document.querySelectorAll('.multiplier-btn');
    buttons.forEach((btn, index) => {
        btn.classList.remove('active');
        // Add active class to the button with the matching multiplier
        if (availableMultipliers[index] === multiplier) {
            btn.classList.add('active');
        }
    });

    // Save multiplier to backend
    gameSync.mutate(() => fetch('/api/multiplier', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ multiplier: multiplier })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            console.error('Failed to update multiplier:', data.error);
        }
    })
    .catch(error => console.error('Error updating multiplier:', error)));
}


// A fixed header gutter surrounds a clipped, zoomable score plane.
const svg = d3.select("#grid").append("svg")
    .attr("class", "board-svg").attr("tabindex", 0)
    .attr("role", "group")
    .attr("aria-label", "Score grid. Arrow keys pan; plus and minus zoom. Use Go to score to locate the current score.");
const defs = svg.append("defs");
const boardClip = defs.append("clipPath").attr("id", "board-clip").append("rect");
const topClip = defs.append("clipPath").attr("id", "top-clip").append("rect");
const leftClip = defs.append("clipPath").attr("id", "left-clip").append("rect");
const mainGroup = svg.append("g").attr("clip-path", "url(#board-clip)").append("g");
const scoreMarker = svg.append('g').attr('clip-path', 'url(#board-clip)')
    .attr('pointer-events', 'none').attr('aria-hidden', 'true');
scoreMarker.append('rect').attr('class', 'current-score-halo');
scoreMarker.append('rect').attr('class', 'current-score-border');
const axesGroups = {
    top: svg.append("g").attr("clip-path", "url(#top-clip)"),
    left: svg.append("g").attr("clip-path", "url(#left-clip)")
};
const tooltip = d3.select("body").append("div").attr("class", "tooltip");
const teamLeftInput = document.getElementById('teamLeft');
const teamRightInput = document.getElementById('teamRight');
let viewport = BoardGeometry.metrics(1, 1, maxScore + 1);
let boardMeasured = false;
const touchPointer = window.matchMedia('(pointer: coarse)');

function d3Transform(value) {
    return d3.zoomIdentity.translate(value.x, value.y).scale(value.k);
}

function updateAxesPositions(transform) {
    const { header: h, plotWidth, plotHeight } = BoardGeometry.layout(viewport, transform.k);
    const size = currentSize * transform.k;
    // Header cells and text use exactly the same scale as the score plane.
    const baseFontSize = parseFloat(getComputedStyle(gridContainer).getPropertyValue('--board-score-font-size'));
    const scaledFontSize = baseFontSize * transform.k;
    for (const [side, group] of Object.entries(axesGroups)) {
        const horizontal = side === 'top';
        const offset = horizontal ? transform.x : transform.y;
        const available = horizontal ? plotWidth : plotHeight;
        const first = Math.max(0, Math.floor((h - offset) / size));
        const last = Math.min(maxScore, Math.ceil((h + available - offset) / size));
        const values = d3.range(first, last + 1);
        group.selectAll('rect').data(values).join('rect')
            .attr('x', i => horizontal ? offset + i * size : 0)
            .attr('y', i => horizontal ? 0 : offset + i * size)
            .attr('width', horizontal ? size : h).attr('height', horizontal ? h : size)
            .attr('class', 'score-header').style('stroke-width', 2 * transform.k);
        group.selectAll('text').data(values).join('text')
            .attr('x', i => horizontal ? offset + (i + 0.5) * size : h / 2)
            .attr('y', i => horizontal ? h / 2 : offset + (i + 0.5) * size)
            .attr('class', 'score-header-text')
            .style('font-size', scaledFontSize + 'px')
            .text(i => i).call(boardText.center).raise();
    }
}

const zoom = d3.zoom()
    .clickDistance(6)
    .constrain(transform => d3Transform(BoardGeometry.constrain(transform, viewport)))
    .on('zoom', event => {
        updateBoardClips(event.transform.k);
        mainGroup.attr('transform', event.transform);
        updateAxesPositions(event.transform);
        updateScoreMarker(event.transform);
        tooltip.style('opacity', 0);
    });
svg.call(zoom).on('dblclick.zoom', null);

function updateZoomLimits() {
    zoom.extent([[0, 0], [viewport.width, viewport.height]])
        .scaleExtent([viewport.fit, viewport.max]);

}

function applyBoardTransform(value) {
    svg.interrupt().call(zoom.transform, d3Transform(BoardGeometry.constrain(value, viewport)));
}

function updateBoardClips(k) {
    const { header: h, plotWidth, plotHeight } = BoardGeometry.layout(viewport, k);
    boardClip.attr('x', h).attr('y', h).attr('width', plotWidth).attr('height', plotHeight);
    topClip.attr('x', h).attr('y', 0).attr('width', plotWidth).attr('height', h);
    leftClip.attr('x', 0).attr('y', h).attr('width', h).attr('height', plotHeight);
}

function measureBoard() {
    fitTeamLabels();
    const bounds = svg.node().getBoundingClientRect();
    if (bounds.width <= 0 || bounds.height <= 0) return;
    const previous = d3.zoomTransform(svg.node());
    const center = BoardGeometry.center(previous, viewport);
    viewport = BoardGeometry.metrics(bounds.width, bounds.height, maxScore + 1, currentSize, touchPointer.matches);
    svg.attr('viewBox', [0, 0, bounds.width, bounds.height]);
    updateZoomLimits();
    if (boardMeasured) {
        applyBoardTransform(BoardGeometry.centered(center, BoardGeometry.zoomScale(previous.k, 1, viewport), viewport));
    } else {
        goToScore();
    }
    boardMeasured = true;
}

function zoomBoard(factor) {
    const transform = d3.zoomTransform(svg.node());
    const center = BoardGeometry.center(transform, viewport);
    updateZoomLimits();
    const k = BoardGeometry.zoomScale(transform.k, factor, viewport);
    applyBoardTransform(BoardGeometry.centered(center, k, viewport));
}

function focusSquare(row, col) {
    updateZoomLimits();
    applyBoardTransform(BoardGeometry.centered([(col + 0.5) * currentSize, (row + 0.5) * currentSize], viewport.play, viewport));
}

function goToScore() {
    const squares = [{ row: currentLeftScore, col: currentRightScore }];
    mainGroup.selectAll('rect.winner-square').each(function () {
        squares.push({
            row: Number(this.getAttribute('data-row')),
            col: Number(this.getAttribute('data-col'))
        });
    });
    updateZoomLimits();
    applyBoardTransform(BoardGeometry.scoreView(squares, viewport));
}

function togglePlayers(button) {
    const expanded = button.getAttribute('aria-expanded') !== 'true';
    button.setAttribute('aria-expanded', expanded);
    button.textContent = expanded ? 'Players ▾' : 'Players ▸';
    document.getElementById('playersPanel').classList.toggle('collapsed', !expanded);
}

svg.on('keydown', event => {
    const directions = { ArrowLeft: [80, 0], ArrowRight: [-80, 0], ArrowUp: [0, 80], ArrowDown: [0, -80] };
    if (directions[event.key]) {
        event.preventDefault();
        const transform = d3.zoomTransform(svg.node());
        const [x, y] = directions[event.key];
        applyBoardTransform({ x: transform.x + x, y: transform.y + y, k: transform.k });
    } else if (['+', '=', '-'].includes(event.key)) {
        event.preventDefault();
        zoomBoard(event.key === '-' ? 0.8 : 1.25);
    }
});

let currentLeftScore = 0;
let currentRightScore = 0;

// Update score validation to use dynamic maxScore
function updateScore(team) {
    const teamSelect = document.getElementById(team === 'left' ? 'teamLeft' : 'teamRight');
    const teamCode = teamSelect.value;
    const teamName = teamCode ? getCurrentTeams()[teamCode].name : (team === 'left' ? 'Left' : 'Right') + ' Team';

    showGenericPrompt({
        title: 'Update Score',
        message: `Enter new score for ${teamCode}`,
        inputType: 'number',
        maxLength: String(maxScore).length,
        minValue: 0,
        maxValue: maxScore,
        validateInput: (value) => {
            if (!value) {
                return { isValid: false, message: 'Enter score or cancel' };
            }
            if (!/^\d+$/.test(value)) {
                return { isValid: false, message: 'Enter numbers' };
            }
            const score = parseInt(value);
            if (isNaN(score)) {
                return { isValid: false, message: 'Enter valid number' };
            }
            if (score < 0 || score > maxScore) {
                return { isValid: false, message: `Score between 0 and ${maxScore}` };
            }
            return { isValid: true };
        },
        onConfirm: (value) => {
            const score = parseInt(value);
            if (team === 'left') {
                currentLeftScore = score;
                document.getElementById('leftScore').textContent = currentLeftScore;
            } else {
                currentRightScore = score;
                document.getElementById('rightScore').textContent = currentRightScore;
            }

            gameSync.mutate(() => fetch('/api/scores', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    left: currentLeftScore,
                    right: currentRightScore
                })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    showAlert('Failed to save scores');
                }
                highlightCurrentScore();
                updateWinnerDisplay();
            })
            .catch(error => {
                console.error('Error saving scores:', error);
                showAlert('Failed to save scores');
            }));
        }
    });
}

function getCurrentTeams() {
    switch(currentSport) {
        case 'nfl':
            return NFL_TEAMS;
        case 'nhl':
            return NHL_TEAMS;
        case 'nba':
            return NBA_TEAMS;
        case 'mlb':
            return MLB_TEAMS;
        case 'olym':
            return OLYM_TEAMS;
        case 'fifa':
            return FIFA_TEAMS;
        default:
            return NFL_TEAMS;
    }
}

// Function to populate team select options
function populateTeamSelects() {
    const leftSelect = document.getElementById('teamLeft');
    const rightSelect = document.getElementById('teamRight');
    
    // Clear existing options
    leftSelect.innerHTML = '<option value="">SELECT AWAY TEAM</option>';
    rightSelect.innerHTML = '<option value="">SELECT HOME TEAM</option>';
    
	const allTeams = Object.entries(getCurrentTeams())
        .sort((a, b) => a[0] - b[0]); // Sort by numeric team ID

	
    // Add all teams to both selects
    allTeams.forEach(([code, team]) => {
        // Add to away team select
        const awayOption = document.createElement('option');
        awayOption.value = code;
        awayOption.textContent = team.name;
        awayOption.setAttribute('data-colors', `${team.colors[0]},${team.colors[1]}`);
        leftSelect.appendChild(awayOption);
        
        // Add to home team select
        const homeOption = document.createElement('option');
        homeOption.value = code;
        homeOption.textContent = team.name;
        homeOption.setAttribute('data-colors', `${team.colors[0]},${team.colors[1]}`);
        rightSelect.appendChild(homeOption);
    });
}

// Draw above the score plane so neighboring cells and winner paths cannot cover it.
function updateScoreMarker(transform = d3.zoomTransform(svg.node())) {
    const size = currentSize * transform.k;
    const inset = Math.min(3, size / 4);
    scoreMarker.selectAll('rect')
        .attr('x', transform.x + currentRightScore * size + inset)
        .attr('y', transform.y + currentLeftScore * size + inset)
        .attr('width', Math.max(1, size - 2 * inset))
        .attr('height', Math.max(1, size - 2 * inset));
}

function highlightCurrentScore() {
    updateScoreMarker();
}

function fitTeamLabels() {
    for (const selector of ['.team-name-top', '.team-name-left']) {
        const label = document.querySelector(selector);
        const available = selector.endsWith('top') ? label.clientWidth : label.clientHeight;
        if (available > 0 && label.textContent) {
            label.style.fontSize = Math.min(18, (available - 18) / label.textContent.length) + 'px';
        }
    }
}

// Function to highlight winner and path
// winnerData can be a single winner object or an array of winners
function highlightWinner(winnerData) {
    // Remove all winner highlights
    d3.selectAll('.square').classed('winner-path', false);
    d3.selectAll('.square').classed('winner-square', false);

    if (!winnerData) {
        return; // No winner to highlight
    }

    // Convert to array if single winner
    const winners = Array.isArray(winnerData) ? winnerData : [winnerData];

    // Process each winner
    winners.forEach((winner, index) => {
        // Highlight the path squares
        if (winner.path && winner.path.length > 0) {
            winner.path.forEach(square => {
                const element = d3.select(`rect[data-row="${square.row}"][data-col="${square.col}"]`);
                element.classed('winner-path', true);
            });
        }

        // Highlight the winning square with gold border
        if (winner.square) {
            const element = d3.select(`rect[data-row="${winner.square.row}"][data-col="${winner.square.col}"]`);
            element.classed('winner-square', true);
        }
    });
}

// Function to update winner display
function updateWinnerDisplay() {
    gameSync.refresh();
}

// Update the createGrid function to add data attributes to the squares
function createGrid() {
  // Clear existing elements
  mainGroup.selectAll("*").remove();
  Object.values(axesGroups).forEach(group => group.selectAll("*").remove());

  const squaresGroup = mainGroup.append("g");

  // Create main grid squares
  for (let row = 0; row <= maxScore; row++) {
    for (let col = 0; col <= maxScore; col++) {
      const isTieSquare = row === col;

      // Create square
      squaresGroup.append("rect")
        .attr("class", `square ${isTieSquare ? 'tie-square' : ''}`)
        .attr("x", col * currentSize)
        .attr("y", row * currentSize)
        .attr("width", currentSize)
        .attr("height", currentSize)
        .attr("data-row", row)
        .attr("data-col", col)
        .on("click", () => {
          if (currentSize * d3.zoomTransform(svg.node()).k < 24) focusSquare(row, col);
          else if (!isTieSquare) handleSquareClick(row, col);
        })
        .on("contextmenu", (event) => {
          event.preventDefault();
          if (currentSize * d3.zoomTransform(svg.node()).k >= 24 && !isTieSquare) handleSquareDelete(row, col);
        });

      // Add text for squares
      squaresGroup.append("text")
        .attr("class", `square-text ${isTieSquare ? 'tie-text' : ''}`)
        .attr("x", col * currentSize + currentSize / 2)
        .attr("y", row * currentSize + currentSize / 2)
        .attr("data-row", row)
        .attr("data-col", col)
        .text(isTieSquare ? row : '').call(boardText.center);
    }
  }

  // Event delegation for hover - one handler instead of 100+ individual handlers
  squaresGroup
    .on("mouseover", (event) => {
      const target = event.target;
      if (target.classList.contains("square")) {
        const row = target.getAttribute("data-row");
        const col = target.getAttribute("data-col");
        // Skip header squares (no data attributes)
        if (row === null || col === null) return;
        // Tie squares (diagonal) - show TIE
        const isTie = row === col;
        const text = isTie
          ? `TIE: ${row} - ${col}`
          : `${teamLeftInput.value}: ${row} - ${teamRightInput.value}: ${col}`;
        tooltip.style("opacity", 1).text(text);
        const box = tooltip.node().getBoundingClientRect();
        tooltip.style('left', Math.max(8, Math.min(event.clientX + 12, window.innerWidth - box.width - 8)) + 'px')
          .style('top', Math.max(8, Math.min(event.clientY + 12, window.innerHeight - box.height - 8)) + 'px');
      }
    })
    .on("mouseout", (event) => {
      if (event.target.classList.contains("square")) {
        tooltip.style("opacity", 0);
      }
    });

  // Update team names with adjusted positioning
  resetZoom();
  updateTeamColors(false);
  // Add this line at the end of the function
  setTimeout(highlightCurrentScore, 100); // Small delay to ensure DOM is updated
}

const NFL_TEAMS = {
    "ARI": { name: "ARIZONA CARDINALS", colors: ["#97233F", "#FFFFFF"] },
    "ATL": { name: "ATLANTA FALCONS", colors: ["#A71930", "#000000"] },
    "BAL": { name: "BALTIMORE RAVENS", colors: ["#241773", "#9E7C0C"] },
    "BUF": { name: "BUFFALO BILLS", colors: ["#00338D", "#C60C30"] },
    "CAR": { name: "CAROLINA PANTHERS", colors: ["#0085CA", "#B2B4BB"] },
    "CHI": { name: "CHICAGO BEARS", colors: ["#C83803", "#0B162A"] },
    "CIN": { name: "CINCINNATI BENGALS", colors: ["#FB4F14", "#000000"] },
    "CLE": { name: "CLEVELAND BROWNS", colors: ["#311D00", "#FF3C00"] },
    "DAL": { name: "DALLAS COWBOYS", colors: ["#003594", "#869397"] },
    "DEN": { name: "DENVER BRONCOS", colors: ["#FB4F14", "#002244"] },
    "DET": { name: "DETROIT LIONS", colors: ["#0076B6", "#B0B7BC"] },
    "GB": { name: "GREEN BAY PACKERS", colors: ["#203731", "#FFB612"] },
    "HOU": { name: "HOUSTON TEXANS", colors: ["#03202F", "#A71930"] },
    "IND": { name: "INDIANAPOLIS COLTS", colors: ["#002C5F", "#A2AAAD"] },
    "JAX": { name: "JACKSONVILLE JAGUARS", colors: ["#006778", "#9F792C"] },
    "KC": { name: "KANSAS CITY CHIEFS", colors: ["#E31837", "#FFB81C"] },
    "LAC": { name: "LOS ANGELES CHARGERS", colors: ["#0080C6", "#FFC20E"] },
    "LAR": { name: "LOS ANGELES RAMS", colors: ["#003594", "#FFA300"] },
    "LV": { name: "LAS VEGAS RAIDERS", colors: ["#000000", "#A5ACAF"] },
    "MIA": { name: "MIAMI DOLPHINS", colors: ["#008E97", "#FC4C02"] },
    "MIN": { name: "MINNESOTA VIKINGS", colors: ["#4F2683", "#FFC62F"] },
    "NE": { name: "NEW ENGLAND PATRIOTS", colors: ["#002244", "#C60C30"] },
    "NO": { name: "NEW ORLEANS SAINTS", colors: ["#D3BC8D", "#101820"] },
    "NYG": { name: "NEW YORK GIANTS", colors: ["#0B2265", "#A71930"] },
    "NYJ": { name: "NEW YORK JETS", colors: ["#125740", "#FFFFFF"] },
    "PHI": { name: "PHILADELPHIA EAGLES", colors: ["#004C54", "#A5ACAF"] },
    "PIT": { name: "PITTSBURGH STEELERS", colors: ["#FFB612", "#101820"] },
    "SEA": { name: "SEATTLE SEAHAWKS", colors: ["#002244", "#69BE28"] },
    "SF": { name: "SAN FRANCISCO 49ERS", colors: ["#AA0000", "#B3995D"] },
    "TB": { name: "TAMPA BAY BUCCANEERS", colors: ["#D50A0A", "#34302B"] },
    "TEN": { name: "TENNESSEE TITANS", colors: ["#0C2340", "#4B92DB"] },
    "WAS": { name: "WASHINGTON COMMANDERS", colors: ["#773141", "#FFB612"] }
};

// NHL Teams with primary and secondary colors
const NHL_TEAMS = {
    "ANA": { name: "ANAHEIM DUCKS", colors: ["#00675A", "#4F324C"] },
    "ARI": { name: "ARIZONA COYOTES", colors: ["#8C2633", "#E2D6B5"] },
    "BOS": { name: "BOSTON BRUINS", colors: ["#FFC600", "#000000"] }, // Same
    "BUF": { name: "BUFFALO SABRES", colors: ["#000084", "#FDB827"] }, // Same
    "CAR": { name: "CAROLINA HURRICANES", colors: ["#CC0000", "#FFFFFF"] },
    "CBJ": { name: "COLUMBUS BLUE JACKETS", colors: ["#002654", "#CE1126"] },
    "CGY": { name: "CALGARY FLAMES", colors: ["#C62100", "#FFC600"] }, // Slightly different red
    "CHI": { name: "CHICAGO BLACKHAWKS", colors: ["#BD2108", "#F0AE00"] }, // Different red
    "COL": { name: "COLORADO AVALANCHE", colors: ["#822433", "#165788"] },
    "DAL": { name: "DALLAS STARS", colors: ["#005837", "#B6A953"] },
    "DET": { name: "DETROIT RED WINGS", colors: ["#CE1126", "#FFFFFF"] }, // Same
    "EDM": { name: "EDMONTON OILERS", colors: ["#002B7F", "#FF4C00"] }, // Different blue
    "FLA": { name: "FLORIDA PANTHERS", colors: ["#011E41", "#BC955C"] },
    "HAR": { name: "HARTFORD WHALERS", colors: ["#009A44", "#FFFFFF"] },
    "LAK": { name: "LOS ANGELES KINGS", colors: ["#FDB515", "#582C83"] }, // Purple and gold era
    "MIN": { name: "MINNESOTA WILD", colors: ["#A6192E", "#154734"] },
	"MNS": { name: "MINNESOTA NORTH STARS", colors: ["#FFC600", "#007934"] }, // North Stars' classic gold and green
    "MTL": { name: "CANADIENS DE MONTRÉAL ", colors: ["#C60000", "#000084"] }, // Same
    "NJD": { name: "NEW JERSEY DEVILS", colors: ["#CE1126", "#006A36"] }, // Same
    "NSH": { name: "NASHVILLE PREDATORS", colors: ["#FFB81C", "#041E42"] },
    "NYI": { name: "NEW YORK ISLANDERS", colors: ["#000084", "#F84822"] }, // Same
    "NYR": { name: "NEW YORK RANGERS", colors: ["#0031AD", "#C62100"] }, // Same
    "OTT": { name: "OTTAWA SENATORS", colors: ["#C60C30", "#D59F0D"] },
    "PHI": { name: "PHILADELPHIA FLYERS", colors: ["#F9461C", "#FFFFFF"] }, // Same
    "PIT": { name: "PITTSBURGH PENGUINS", colors: ["#FFBD00", "#000000"] }, // Gold was primary
    "QUE": { name: "NORDIQUES DE QUÉBEC", colors: ["#007BBB", "#FFFFFF"] },	
    "SEA": { name: "SEATTLE KRAKEN", colors: ["#99D9D9", "#001628"] },
    "SJS": { name: "SAN JOSE SHARKS", colors: ["#007C92", "#A5ACAF"] },
    "STL": { name: "ST. LOUIS BLUES", colors: ["#002F87", "#FCB514"] }, // Same
    "TBL": { name: "TAMPA BAY LIGHTNING", colors: ["#0046AD", "#A2A9AE"] },
    "TOR": { name: "TORONTO MAPLE LEAFS", colors: ["#000084", "#FFFFFF"] }, // Slightly different blue
    "VAN": { name: "VANCOUVER CANUCKS", colors: ["#FF2100", "#FFC600"] }, // Yellow and orange era
    "VGK": { name: "VEGAS GOLDEN KNIGHTS", colors: ["#B4975A", "#333F42"] },
    "WPG": { name: "WINNIPEG JETS", colors: ["#002776", "#C60C30"] }, // Original Jets' blue and red
    "WSH": { name: "WASHINGTON CAPITALS", colors: ["#BD0000", "#FFFFFF"] }, // Same basic scheme
};

// NBA Teams with primary and secondary colors
const NBA_TEAMS = {
    "ATL": { name: "ATLANTA HAWKS", colors: ["#E03A3E", "#C1D32F"] },
    "BOS": { name: "BOSTON CELTICS", colors: ["#008348", "#FFFFFF"] },
    "BKN": { name: "BROOKLYN NETS", colors: ["#000000", "#FFFFFF"] },
    "CHA": { name: "CHARLOTTE HORNETS", colors: ["#1D1160", "#00788C"] },
    "CHI": { name: "CHICAGO BULLS", colors: ["#CE1141", "#000000"] },
    "CLE": { name: "CLEVELAND CAVALIERS", colors: ["#860038", "#041E42"] },
    "DAL": { name: "DALLAS MAVERICKS", colors: ["#00538C", "#002B5E"] },
    "DEN": { name: "DENVER NUGGETS", colors: ["#0E2240", "#FEC524"] },
    "DET": { name: "DETROIT PISTONS", colors: ["#C8102E", "#1D42BA"] },
    "GSW": { name: "GOLDEN STATE WARRIORS", colors: ["#1D428A", "#FFC72C"] },
    "HOU": { name: "HOUSTON ROCKETS", colors: ["#CE1141", "#000000"] },
    "IND": { name: "INDIANA PACERS", colors: ["#002D62", "#FDBB30"] },
    "LAC": { name: "LA CLIPPERS", colors: ["#C8102E", "#1D428A"] },
    "LAL": { name: "LOS ANGELES LAKERS", colors: ["#552583", "#FDB927"] },
    "MEM": { name: "MEMPHIS GRIZZLIES", colors: ["#5D76A9", "#12173F"] },
    "MIA": { name: "MIAMI HEAT", colors: ["#98002E", "#F9A01B"] },
    "MIL": { name: "MILWAUKEE BUCKS", colors: ["#00471B", "#EEE1C6"] },
    "MIN": { name: "MINNESOTA TIMBERWOLVES", colors: ["#0C2340", "#236192"] },
    "NOP": { name: "NEW ORLEANS PELICANS", colors: ["#0C2340", "#C8102E"] },
    "NYK": { name: "NEW YORK KNICKS", colors: ["#006BB6", "#F58426"] },
    "OKC": { name: "OKLAHOMA CITY THUNDER", colors: ["#007AC1", "#EF3B24"] },
    "ORL": { name: "ORLANDO MAGIC", colors: ["#0077C0", "#C4CED4"] },
    "PHI": { name: "PHILADELPHIA 76ERS", colors: ["#006BB6", "#ED174C"] },
    "PHX": { name: "PHOENIX SUNS", colors: ["#1D1160", "#E56020"] },
    "POR": { name: "PORTLAND TRAIL BLAZERS", colors: ["#E03A3E", "#000000"] },
    "SAC": { name: "SACRAMENTO KINGS", colors: ["#5A2D81", "#63727A"] },
    "SAS": { name: "SAN ANTONIO SPURS", colors: ["#C4CED4", "#000000"] },
    "TOR": { name: "TORONTO RAPTORS", colors: ["#B90B2F", "#753BBD"] },
    "UTA": { name: "UTAH JAZZ", colors: ["#3D2971", "#FAD424"] },
    "WAS": { name: "WASHINGTON WIZARDS", colors: ["#002B5C", "#E31837"] }
};

// MLB Teams with primary and secondary colors
const MLB_TEAMS = {
    "ARI": { name: "ARIZONA DIAMONDBACKS", colors: ["#A71930", "#E3D4AD"] },
    "ATL": { name: "ATLANTA BRAVES", colors: ["#CE1141", "#13274F"] },
    "BAL": { name: "BALTIMORE ORIOLES", colors: ["#DF4601", "#000000"] },
    "BOS": { name: "BOSTON RED SOX", colors: ["#BD3039", "#0C2340"] },
    "CHC": { name: "CHICAGO CUBS", colors: ["#0E3386", "#CC3433"] },
    "CWS": { name: "CHICAGO WHITE SOX", colors: ["#27251F", "#C4CED4"] },
    "CIN": { name: "CINCINNATI REDS", colors: ["#C6011F", "#000000"] },
    "CLE": { name: "CLEVELAND GUARDIANS", colors: ["#E31937", "#003366"] },
    "COL": { name: "COLORADO ROCKIES", colors: ["#333366", "#C4CED4"] },
    "DET": { name: "DETROIT TIGERS", colors: ["#0C2340", "#FA4616"] },
    "MIA": { name: "MIAMI MARLINS", colors: ["#009CA6", "#8A8D8F"] },
    "HOU": { name: "HOUSTON ASTROS", colors: ["#002D62", "#EB6E1F"] },
    "KC": { name: "KANSAS CITY ROYALS", colors: ["#004687", "#BD9B60"] },
    "LAA": { name: "LOS ANGELES ANGELS", colors: ["#BA0021", "#003263"] },
    "LAD": { name: "LOS ANGELES DODGERS", colors: ["#005A9C", "#FFFFFF"] },
    "MIL": { name: "MILWAUKEE BREWERS", colors: ["#0046AE", "#FFD451"] },
    "MIN": { name: "MINNESOTA TWINS", colors: ["#002B5C", "#D31145"] },
	"MTL": { name: "EXPOS DE MONTRÉAL",  colors: ["#003087", "#E4002B"] },
    "NYM": { name: "NEW YORK METS", colors: ["#002D72", "#FF5910"] },
    "NYY": { name: "NEW YORK YANKEES", colors: ["#003087", "#C4CED4"] },
    "OAK": { name: "OAKLAND ATHLETICS", colors: ["#003831", "#EFB21E"] },
    "PHI": { name: "PHILADELPHIA PHILLIES", colors: ["#6F263D", "#6BACE4"] },
    "PIT": { name: "PITTSBURGH PIRATES", colors: ["#FDB827", "#000000"] },
    "SD": { name: "SAN DIEGO PADRES", colors: ["#2F241D", "#FFC425"] },
    "SF": { name: "SAN FRANCISCO GIANTS", colors: ["#FD5A1E", "#27251F"] },
    "SEA": { name: "SEATTLE MARINERS", colors: ["#0C2C56", "#005C5C"] },
    "STL": { name: "ST. LOUIS CARDINALS", colors: ["#C41E3A", "#FEDB00"] },
    "TB": { name: "TAMPA BAY RAYS", colors: ["#092C5C", "#8FBCE6"] },
    "TEX": { name: "TEXAS RANGERS", colors: ["#003278", "#C0111F"] },
    "TOR": { name: "TORONTO BLUE JAYS", colors: ["#51ADE9", "#003CAB"] },
    "WSH": { name: "WASHINGTON NATIONALS", colors: ["#AB0003", "#14225A"] }
};

// Olympic Ice Hockey Teams (countries) with flag-based colors (sorted by team name)
const OLYM_TEAMS = {
    "AUT": { name: "AUSTRIA", colors: ["#ED2939", "#FFFFFF"] },
    "CAN": { name: "CANADA", colors: ["#FF0000", "#FFFFFF"] },
    "CHN": { name: "CHINA", colors: ["#DE2910", "#FFDE00"] },
    "CZE": { name: "CZECHIA", colors: ["#11457E", "#D7141A"] },
    "DEN": { name: "DENMARK", colors: ["#C60C30", "#FFFFFF"] },
    "FIN": { name: "FINLAND", colors: ["#003580", "#FFFFFF"] },
    "FRA": { name: "FRANCE", colors: ["#002395", "#ED2939"] },
    "GER": { name: "GERMANY", colors: ["#000000", "#DD0000"] },
    "GBR": { name: "GREAT BRITAIN", colors: ["#012169", "#C8102E"] },
    "HUN": { name: "HUNGARY", colors: ["#477050", "#CE2939"] },
    "ITA": { name: "ITALY", colors: ["#009246", "#CE2B37"] },
    "JPN": { name: "JAPAN", colors: ["#FFFFFF", "#BC002D"] },
    "KAZ": { name: "KAZAKHSTAN", colors: ["#00AEC7", "#FEC50C"] },
    "LAT": { name: "LATVIA", colors: ["#9E3039", "#FFFFFF"] },
    "NOR": { name: "NORWAY", colors: ["#EF2B2D", "#002868"] },
    "POL": { name: "POLAND", colors: ["#FFFFFF", "#DC143C"] },
    "SVK": { name: "SLOVAKIA", colors: ["#0B4EA2", "#EE1C25"] },
    "SLO": { name: "SLOVENIA", colors: ["#005DA4", "#ED1C24"] },
    "KOR": { name: "SOUTH KOREA", colors: ["#003478", "#C60C30"] },
    "SWE": { name: "SWEDEN", colors: ["#006AA7", "#FECC00"] },
    "SUI": { name: "SWITZERLAND", colors: ["#FF0000", "#FFFFFF"] },
    "USA": { name: "UNITED STATES", colors: ["#002868", "#BF0A30"] }
};

// FIFA World Cup 2026 Teams with flag-based colors (sorted by team name)
const FIFA_TEAMS = {
    "ALG": { name: "ALGERIA", colors: ["#006233", "#FFFFFF"] },
    "ARG": { name: "ARGENTINA", colors: ["#75AADB", "#FFFFFF"] },
    "AUS": { name: "AUSTRALIA", colors: ["#00843D", "#FFCD00"] },
    "AUT": { name: "AUSTRIA", colors: ["#ED2939", "#FFFFFF"] },
    "BHR": { name: "BAHRAIN", colors: ["#CE1126", "#FFFFFF"] },
    "BEL": { name: "BELGIUM", colors: ["#ED2939", "#FDDA24"] },
    "BOL": { name: "BOLIVIA", colors: ["#007934", "#D52B1E"] },
    "BRA": { name: "BRAZIL", colors: ["#009C3B", "#FFDF00"] },
    "CMR": { name: "CAMEROON", colors: ["#007A5E", "#CE1126"] },
    "CAN": { name: "CANADA", colors: ["#FF0000", "#FFFFFF"] },
    "CHI": { name: "CHILE", colors: ["#D52B1E", "#0039A6"] },
    "COL": { name: "COLOMBIA", colors: ["#FCD116", "#003893"] },
    "CRC": { name: "COSTA RICA", colors: ["#002B7F", "#CE1126"] },
    "CRO": { name: "CROATIA", colors: ["#FF0000", "#0000FF"] },
    "DEN": { name: "DENMARK", colors: ["#C60C30", "#FFFFFF"] },
    "ECU": { name: "ECUADOR", colors: ["#FFD100", "#0033A0"] },
    "EGY": { name: "EGYPT", colors: ["#C8102E", "#FFFFFF"] },
    "ENG": { name: "ENGLAND", colors: ["#FFFFFF", "#CF081F"] },
    "FIN": { name: "FINLAND", colors: ["#003580", "#FFFFFF"] },
    "FRA": { name: "FRANCE", colors: ["#002395", "#ED2939"] },
    "GER": { name: "GERMANY", colors: ["#000000", "#DD0000"] },
    "GRE": { name: "GREECE", colors: ["#0D5EAF", "#FFFFFF"] },
    "HON": { name: "HONDURAS", colors: ["#0073CF", "#FFFFFF"] },
    "HUN": { name: "HUNGARY", colors: ["#477050", "#CE2939"] },
    "IDN": { name: "INDONESIA", colors: ["#FF0000", "#FFFFFF"] },
    "IRN": { name: "IRAN", colors: ["#239F40", "#DA0000"] },
    "IRQ": { name: "IRAQ", colors: ["#007A3D", "#FFFFFF"] },
    "ITA": { name: "ITALY", colors: ["#009246", "#CE2B37"] },
    "CIV": { name: "IVORY COAST", colors: ["#FF8200", "#009A44"] },
    "JAM": { name: "JAMAICA", colors: ["#009B3A", "#FED100"] },
    "JPN": { name: "JAPAN", colors: ["#FFFFFF", "#BC002D"] },
    "JOR": { name: "JORDAN", colors: ["#007A3D", "#CE1126"] },
    "MEX": { name: "MEXICO", colors: ["#006847", "#CE1126"] },
    "MAR": { name: "MOROCCO", colors: ["#C1272D", "#006233"] },
    "NED": { name: "NETHERLANDS", colors: ["#FF6600", "#FFFFFF"] },
    "NZL": { name: "NEW ZEALAND", colors: ["#000000", "#FFFFFF"] },
    "NGR": { name: "NIGERIA", colors: ["#008751", "#FFFFFF"] },
    "PRK": { name: "NORTH KOREA", colors: ["#024FA2", "#ED1C27"] },
    "NOR": { name: "NORWAY", colors: ["#EF2B2D", "#002868"] },
    "PLE": { name: "PALESTINE", colors: ["#007A3D", "#CE1126"] },
    "PAN": { name: "PANAMA", colors: ["#005293", "#D21034"] },
    "PAR": { name: "PARAGUAY", colors: ["#D52B1E", "#0038A8"] },
    "PER": { name: "PERU", colors: ["#D91023", "#FFFFFF"] },
    "POL": { name: "POLAND", colors: ["#FFFFFF", "#DC143C"] },
    "POR": { name: "PORTUGAL", colors: ["#006600", "#FF0000"] },
    "QAT": { name: "QATAR", colors: ["#8D1B3D", "#FFFFFF"] },
    "KSA": { name: "SAUDI ARABIA", colors: ["#006C35", "#FFFFFF"] },
    "SCO": { name: "SCOTLAND", colors: ["#005EB8", "#FFFFFF"] },
    "SEN": { name: "SENEGAL", colors: ["#00853F", "#FDEF42"] },
    "SRB": { name: "SERBIA", colors: ["#C6363C", "#0C4076"] },
    "SLO": { name: "SLOVENIA", colors: ["#005DA4", "#ED1C24"] },
    "RSA": { name: "SOUTH AFRICA", colors: ["#007A4D", "#FFB612"] },
    "KOR": { name: "SOUTH KOREA", colors: ["#003478", "#C60C30"] },
    "ESP": { name: "SPAIN", colors: ["#AA151B", "#F1BF00"] },
    "SUI": { name: "SWITZERLAND", colors: ["#FF0000", "#FFFFFF"] },
    "TUR": { name: "TURKEY", colors: ["#E30A17", "#FFFFFF"] },
    "UKR": { name: "UKRAINE", colors: ["#005BBB", "#FFD500"] },
    "USA": { name: "UNITED STATES", colors: ["#002868", "#BF0A30"] },
    "URU": { name: "URUGUAY", colors: ["#5CBFEB", "#FFFFFF"] },
    "UZB": { name: "UZBEKISTAN", colors: ["#1EB53A", "#0099B5"] },
    "VEN": { name: "VENEZUELA", colors: ["#FFCC00", "#00247D"] },
    "WAL": { name: "WALES", colors: ["#C8102E", "#00AB39"] }
};

function addPlayer() {
    const initialInput = document.getElementById('playerInitial');
    const nameInput = document.getElementById('playerName');
    const initial = initialInput.value.toUpperCase();
    const name = nameInput.value.trim().toUpperCase();

    // Validate initial
    if (initial.length !== 1) {
        showAlert("Enter Initial");
        return;
    }

    // Validate name length and content
    if (!name) {
        showAlert("Enter name");
        return;
    }
    
    if (name.length > 8) {
        showAlert("Name is max 8 char");
        nameInput.value = name.substring(0, 8);
        return;
    }

    // Check for duplicate initial
    if (players[initial]) {
        showAlert(`Initial ${initial} owned by ${players[initial].name}`);
        return;
    }

    // Add player via API
    gameSync.mutate(() => fetch('/api/players', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initial, name })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            players[initial] = {
                name: name,
                playerIndex: data.playerIndex,  // Changed from colorIndex
                bets: 0,
                tokens: tokensPerPlayer  // Initialize with tokens for current sport
            };
            updatePlayerList();
            initialInput.value = '';
            nameInput.value = '';
        } else {
            showAlert(data.error || "Failed to add player");
        }
    })
    .catch(error => {
        console.error("Error adding player:", error);
        showAlert("Failed to add player");
    }));
}

// Add these helper functions for contrast checking
function getLuminance(r, g, b) {
    let [rs, gs, bs] = [r, g, b].map(c => {
        c = c / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function getContrastRatio(color1, color2) {
    // Convert hex to RGB
    const getRGB = (hex) => {
        const shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
        hex = hex.replace(shorthandRegex, (m, r, g, b) => r + r + g + g + b + b);
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    };

    const rgb1 = getRGB(color1);
    const rgb2 = getRGB(color2);
    
    if (!rgb1 || !rgb2) return 1;

    const l1 = getLuminance(rgb1.r, rgb1.g, rgb1.b);
    const l2 = getLuminance(rgb2.r, rgb2.g, rgb2.b);
    
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    
    return (lighter + 0.05) / (darker + 0.05);
}

// Add function to save team selections
function saveTeams() {
    const leftTeam = document.getElementById('teamLeft').value;
    const rightTeam = document.getElementById('teamRight').value;
    
    gameSync.mutate(() => fetch('/api/teams', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            left: leftTeam,
            right: rightTeam
        })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            console.error('Failed to save teams');
        }
    })
    .catch(error => {
        console.error('Error saving teams:', error);
    }));
}



// Update team colors and visuals with new helmet colors
function updateTeamColors(persist = true) {
    const leftSelect = document.getElementById('teamLeft');
    const rightSelect = document.getElementById('teamRight');
    const leftTeam = leftSelect.value;
    const rightTeam = rightSelect.value;

    // Get computed theme logo colors for defaults
    const defaultPrimary = getComputedStyle(document.documentElement)
        .getPropertyValue('--retro-logo-primary').trim();
    const defaultSecondary = getComputedStyle(document.documentElement)
        .getPropertyValue('--retro-logo-secondary').trim();


    // Update team helmet icons in selection area
    if (leftTeam && getCurrentTeams()[leftTeam]) {
        const leftHelmetIcon = generateHelmetSVG(
            getCurrentTeams()[leftTeam].colors[0], 
            getCurrentTeams()[leftTeam].colors[1]
        );
        document.getElementById('leftHelmet').src = 'data:image/svg+xml,' + encodeURIComponent(leftHelmetIcon);
    } else {
        // Default NFL helmet for left side
        const defaultHelmet = generateHelmetSVG(defaultPrimary, defaultSecondary);
        document.getElementById('leftHelmet').src = 'data:image/svg+xml,' + encodeURIComponent(defaultHelmet);
    }

    if (rightTeam && getCurrentTeams()[rightTeam]) {
        const rightHelmetIcon = generateHelmetSVG(
            getCurrentTeams()[rightTeam].colors[0], 
            getCurrentTeams()[rightTeam].colors[1]
        );
        document.getElementById('rightHelmet').src = 'data:image/svg+xml,' + encodeURIComponent(rightHelmetIcon);
    } else {
        // Default NFL helmet for right side
        const defaultHelmet = generateHelmetSVG(defaultPrimary, defaultSecondary);
        document.getElementById('rightHelmet').src = 'data:image/svg+xml,' + encodeURIComponent(defaultHelmet);
    }

	// Update static team name displays
    const leftNameDisplay = document.querySelector('.team-name-left');
    const topNameDisplay = document.querySelector('.team-name-top');

    if (leftTeam && getCurrentTeams()[leftTeam]) {
        leftNameDisplay.textContent = getCurrentTeams()[leftTeam].name;
        leftNameDisplay.title = getCurrentTeams()[leftTeam].name;
        const leftColors = getCurrentTeams()[leftTeam].colors;
        // Determine which color is brighter for text
        const leftTextColor = getContrastRatio(leftColors[0], '#000000') > 
            getContrastRatio(leftColors[1], '#000000') ? leftColors[0] : leftColors[1];
        const leftBgColor = leftTextColor === leftColors[0] ? leftColors[1] : leftColors[0];
        
        leftNameDisplay.style.color = leftTextColor;
        leftNameDisplay.style.backgroundColor = leftBgColor;
        leftNameDisplay.style.display = 'block';
    } else {
        leftNameDisplay.textContent = 'AWAY';
        leftNameDisplay.removeAttribute('title');
        leftNameDisplay.style.removeProperty('color');
        leftNameDisplay.style.removeProperty('background-color');
    }

    if (rightTeam && getCurrentTeams()[rightTeam]) {
        topNameDisplay.textContent = getCurrentTeams()[rightTeam].name;
        topNameDisplay.title = getCurrentTeams()[rightTeam].name;
        const rightColors = getCurrentTeams()[rightTeam].colors;
        // Determine which color is brighter for text
        const rightTextColor = getContrastRatio(rightColors[0], '#000000') > 
            getContrastRatio(rightColors[1], '#000000') ? rightColors[0] : rightColors[1];
        const rightBgColor = rightTextColor === rightColors[0] ? rightColors[1] : rightColors[0];
        
        topNameDisplay.style.color = rightTextColor;
        topNameDisplay.style.backgroundColor = rightBgColor;
        topNameDisplay.style.display = 'block';
    } else {
        topNameDisplay.textContent = 'HOME';
        topNameDisplay.removeAttribute('title');
        topNameDisplay.style.removeProperty('color');
        topNameDisplay.style.removeProperty('background-color');
    }

    fitTeamLabels();

    // Update team backgrounds
    updateTeamBackgrounds(leftTeam, rightTeam);
	// Save team selections
    if (persist) saveTeams();
}

// Update team backgrounds
function updateTeamBackgrounds(leftTeam, rightTeam) {
    const leftBg = document.querySelector('.team-background.left');
    const rightBg = document.querySelector('.team-background.right');
    
    if (leftTeam && getCurrentTeams()[leftTeam]) {
        leftBg.style.setProperty('--team-color', getCurrentTeams()[leftTeam].colors[0]);
    } else {
        leftBg.style.setProperty('--team-color', 'transparent');
    }
    
    if (rightTeam && getCurrentTeams()[rightTeam]) {
        rightBg.style.setProperty('--team-color', getCurrentTeams()[rightTeam].colors[0]);
    } else {
        rightBg.style.setProperty('--team-color', 'transparent');
    }
}


// Player list update function with alphabetical sorting
function updatePlayerList() {
    const playerList = document.getElementById('playerList');
    playerList.innerHTML = '';
    
    // Convert players object to array and sort alphabetically by initial
    const sortedPlayers = Object.entries(players)
        .sort(([initialA], [initialB]) => initialA.localeCompare(initialB));
    
    sortedPlayers.forEach(([initial, info]) => {
        const playerItem = document.createElement('div');
        playerItem.className = 'player-item';
        
        const colorDot = document.createElement('div');
        colorDot.className = 'color-dot';
        colorDot.style.backgroundColor = playerColorScale(info.playerIndex);
        colorDot.textContent = initial;
        colorDot.title = `Player ${initial}`;
        
        const playerInfo = document.createElement('div');
        playerInfo.className = 'player-info';
        const identity = document.createElement('span');
        identity.className = 'player-identity';
        identity.textContent = info.name;
        identity.title = info.name;
        const tokens = document.createElement('span');
        tokens.className = 'player-tokens';
        tokens.textContent = `${info.tokens ?? 0}/${tokensPerPlayer}`;
        tokens.setAttribute('aria-label', `${info.tokens ?? 0} of ${tokensPerPlayer} tokens remaining`);
        playerInfo.append(identity, tokens);
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-btn';
        deleteBtn.textContent = 'X';
        deleteBtn.setAttribute('aria-label', `Remove ${info.name}`);
        deleteBtn.onclick = () => deletePlayer(initial);
        
        playerItem.appendChild(colorDot);
        playerItem.appendChild(playerInfo);
        playerItem.appendChild(deleteBtn);
        playerList.appendChild(playerItem);
    });
}


function deletePlayer(initial) {
    const playerName = players[initial]?.name || 'Unknown Player';
    
    showAlert(
        `Player: ${initial} - ${playerName}`,
        'Delete Player',
        true,
        (confirmed) => {
            if (confirmed) {
                // Delete player via API
                gameSync.mutate(() => fetch(`/api/players/${initial}`, {
                    method: 'DELETE',
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Remove from local players object
                        delete players[initial];
                        // Update the player list display
                        updatePlayerList();
                        // Clear any squares with this player's initial
                        d3.selectAll('.square-text')
                            .filter(function() {
                                return d3.select(this).text() === initial;
                            })
                            .each(function() {
                                const row = d3.select(this).attr('data-row');
                                const col = d3.select(this).attr('data-col');
                                updateSquare(row, col, '');
                            });
                        // Update winner display since removing a player might change the winner
                        updateWinnerDisplay();
                    } else {
                        showAlert(data.error || "Failed to delete player");
                    }
                })
                .catch(error => {
                    console.error("Error deleting player:", error);
                    showAlert("Failed to delete player");
                }));
            }
        }
    );
}


function handleSquareClick(row, col) {
    if (row === col) return; // Prevent tie square interaction

    // Check if any players exist
    if (Object.keys(players).length === 0) {
        showAlert('Please add players before claiming squares', 'No players');
        return;
    }

    const currentValue = d3.select(`text[data-row='${row}'][data-col='${col}']`).text();
    if (currentValue) {
        showAlert(`Owned by ${currentValue}`, 'Square taken');
        return;
    }

    // Create player list content
    const playerList = Object.keys(players)
        .sort() // Sort the initials alphabetically
		.map(initial => `${initial}`)
        .join(',');

    // Build title with team/score info
    const leftTeam = document.getElementById('teamLeft').value || 'Away';
    const rightTeam = document.getElementById('teamRight').value || 'Home';
    const scoreTitle = `${leftTeam}: ${row} - ${rightTeam}: ${col}`;

    showGenericPrompt({
        title: scoreTitle,
        message: 'Player initial',
        maxLength: 1,
        showPlayerList: true,
        playerListContent: 'AVAILABLE PLAYERS:\n' + playerList,
        validateInput: (value) => {
            const initial = value.trim().toUpperCase();
            if (initial.length !== 1) {
                return { isValid: false, message: 'Initial must be 1 letter' };
            }
            if (!players[initial]) {
                return { isValid: false, message: 'Please register first' };
            }
            return { isValid: true };
        },
        onConfirm: (value) => {
            const initial = value.trim().toUpperCase();

            // Update square via API
            gameSync.mutate(() => fetch('/api/squares', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ row, col, value: initial, expected_value: '' })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateSquare(row, col, initial);
                    // Update player tokens for all affected players
                    if (data.updated_players) {
                        for (const [playerInitial, tokens] of Object.entries(data.updated_players)) {
                            if (players[playerInitial]) {
                                players[playerInitial].tokens = tokens;
                            }
                        }
                    }
                    // Update player list to show new token counts
                    updatePlayerList();
                    // Update winner display in case this bet affects the winner
                    updateWinnerDisplay();
                } else {
                    showAlert(data.error || 'Failed to update square');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('Failed to update square');
            }));
        }
    });
}

// Generic prompt method for input dialogs
function showGenericPrompt({
    title = 'Input Required',
    message = '',
    defaultValue = '',
    inputType = 'text',
    maxLength = null,
    minValue = null,
    maxValue = null,
    showPlayerList = false,
    playerListContent = '',
    validateInput = null,
    onConfirm = null,
    onCancel = null
}) {
    const genericPrompt = document.getElementById('genericPrompt');
    const promptTitle = document.getElementById('genericPromptTitle');
    const promptMessage = document.getElementById('genericPromptMessage');
    const promptInput = document.getElementById('genericPromptInput');
    const promptPlayerList = document.getElementById('genericPromptPlayerList');
    const okBtn = document.getElementById('genericPromptOkBtn');
    const cancelBtn = document.getElementById('genericPromptCancelBtn');

    // Set up prompt content
    promptTitle.textContent = title.toUpperCase();
    promptMessage.textContent = message.toUpperCase();
    promptInput.value = defaultValue;
    promptInput.type = inputType;
    
    if (maxLength !== null) promptInput.maxLength = maxLength;
    if (minValue !== null) promptInput.min = minValue;
    if (maxValue !== null) promptInput.max = maxValue;

    // Handle player list visibility
    promptPlayerList.style.display = showPlayerList ? 'block' : 'none';
    if (showPlayerList) {
        promptPlayerList.textContent = playerListContent;
    }

    // Show prompt
    genericPrompt.style.display = 'flex';
    promptInput.focus();

    // Input validation handler
    const handleValidation = (value) => {
        if (!validateInput) return { isValid: true };
        const result = validateInput(value);
        if (!result.isValid) {
            // Hide prompt temporarily
            genericPrompt.style.display = 'none';
            
            // Show error alert
            showAlert(result.message, 'Invalid Input', false, () => {
                // After alert is dismissed, show prompt again
                genericPrompt.style.display = 'flex';
                promptInput.value = '';
                promptInput.focus();
            });
        }
        return result;
    };

    // Input event handler
    promptInput.oninput = (e) => {
        const value = e.target.value;
        if (!value) return; // Allow empty for backspace
        handleValidation(value);
    };

    // Keyboard event handler
    promptInput.onkeydown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            okBtn.click();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelBtn.click();
        }
    };

    // Button handlers
    okBtn.onclick = () => {
        const value = promptInput.value.trim();
        const validationResult = handleValidation(value);
        
        if (validationResult.isValid) {
            genericPrompt.style.display = 'none';
            promptInput.type = 'text'; // Reset input type
            promptPlayerList.style.display = 'block'; // Reset player list display
            if (onConfirm) onConfirm(value);
        }
    };

    cancelBtn.onclick = () => {
        genericPrompt.style.display = 'none';
        promptInput.type = 'text'; // Reset input type
        promptPlayerList.style.display = 'block'; // Reset player list display
        if (onCancel) onCancel();
    };
}

// Generic alert method for messages and confirmations
function showAlert(message, title = null, showCancel = false, callback = null) {
    const genericAlert = document.getElementById('genericAlert');
    const alertTitle = document.getElementById('genericAlertTitle');
    const alertMessage = document.getElementById('genericAlertMessage');
    const okBtn = document.getElementById('genericAlertOkBtn');
    const cancelBtn = document.getElementById('genericAlertCancelBtn');
    
    if (title === null) {
        // If only message is provided, use it as title and hide message
        alertTitle.textContent = message.toUpperCase();
        alertMessage.style.display = 'none';
    } else {
        // If both title and message are provided, show both
        alertTitle.textContent = title.toUpperCase();
        alertMessage.textContent = message.toUpperCase();
        alertMessage.style.display = 'block';
    }
    
    cancelBtn.style.display = showCancel ? 'inline-block' : 'none';
    genericAlert.style.display = 'flex';
    
    okBtn.onclick = () => {
        genericAlert.style.display = 'none';
        if (callback) callback(true);
    };
    
    cancelBtn.onclick = () => {
        genericAlert.style.display = 'none';
        if (callback) callback(false);
    };
}

function handleSquareDelete(row, col) {
    if (row === col) return; // Can't delete tie squares
    
    const currentValue = d3.select(`text[data-row='${row}'][data-col='${col}']`).text();
    if (!currentValue) return; // No need to confirm if square is empty
    
    const playerName = players[currentValue]?.name || 'Unknown Player';
    showAlert(
        `Player: ${currentValue} - ${playerName}`, 'Delete Square',
        true,
        (confirmed) => {
            if (confirmed) {
                gameSync.mutate(() => fetch('/api/squares', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ row, col, value: '', expected_value: currentValue })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateSquare(row, col, '');
                        // Update player tokens for all affected players
                        if (data.updated_players) {
                            for (const [playerInitial, tokens] of Object.entries(data.updated_players)) {
                                if (players[playerInitial]) {
                                    players[playerInitial].tokens = tokens;
                                }
                            }
                        }
                        // Update player list to show new token counts
                        updatePlayerList();
                        // Update winner display since removing a bet might change the winner
                        updateWinnerDisplay();
                    } else {
                        showAlert(data.error || "Failed to delete square");
                    }
                })
                .catch(error => {
                    console.error("Error:", error);
                    showAlert("Failed to delete square");
                }));
            }
        }
    );
}

// Update square display function with proper color handling
function updateSquare(row, col, value) {
    const text = d3.select(`text[data-row='${row}'][data-col='${col}']`);
    if (text.empty()) return;

    const displayValue = value ? value.toUpperCase() : '';

    // Set text and color
    text.text(displayValue).call(boardText.center);
    
    // Only apply color if there's a value and it belongs to a player
    if (displayValue && players[displayValue]) {
        text.style("fill", playerColorScale(players[displayValue].playerIndex));
    } else {
        text.style("fill", "var(--retro-primary)");
    }
        
}


function resetZoom() {
    boardMeasured = false;
    measureBoard();
}

// End Game celebration function
function endGame() {
    showAlert(
        'Are you sure?',
        'End Game',
        true,
        (confirmed) => {
            if (confirmed) {
                // Fetch standings data
                fetch('/api/standings')
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && data.standings && data.standings.length > 0) {
                            showCelebration(data.standings, data.winning_team);
                        } else {
                            showAlert('No winner found. Make sure there are bets on the board and scores are set.', 'No Winner');
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching standings:', error);
                        showAlert('Failed to get standings data', 'Error');
                    });
            }
        }
    );
}

// Get team colors for celebration based on winning team
function getTeamColors(winningTeam) {
    const leftTeamCode = document.getElementById('teamLeft').value;
    const rightTeamCode = document.getElementById('teamRight').value;
    const teams = getCurrentTeams();

    const leftTeam = teams[leftTeamCode];
    const rightTeam = teams[rightTeamCode];

    // Get colors from each team
    const leftColors = [
        leftTeam?.colors?.[0] || '#FFD700',
        leftTeam?.colors?.[1] || '#FFA500'
    ];
    const rightColors = [
        rightTeam?.colors?.[0] || '#4ECDC4',
        rightTeam?.colors?.[1] || '#45B7D1'
    ];

    // Return winning team colors first, then losing team colors
    if (winningTeam === 'left') {
        return { winner: leftColors, loser: rightColors };
    } else {
        return { winner: rightColors, loser: leftColors };
    }
}

// Show celebration overlay with Excitebike-style podium
function showCelebration(standings, winningTeam) {
    const teamColors = getTeamColors(winningTeam);

    // Find the minimum distance (winner distance)
    const winnerDistance = standings[0]?.distance || 0;

    // Get winners (all entries with minimum distance) - unique player names only, sorted
    const winners = standings.filter(s => s.distance === winnerDistance);
    const uniqueWinnerNames = [...new Set(winners.map(w => players[w.player]?.name || w.player_name || w.player))].sort();
    const winnerNames = uniqueWinnerNames.length === 2
        ? uniqueWinnerNames.join(' & ')
        : uniqueWinnerNames.join(', ');

    // Build podium HTML - top 5, group by distance, show rank
    const top5 = standings.slice(0, 5);
    let currentRank = 1;
    let lastDistance = -1;

    // Get team info for score display
    const leftTeamCode = document.getElementById('teamLeft').value;
    const rightTeamCode = document.getElementById('teamRight').value;

    // Get final game score
    const finalLeftScore = currentLeftScore;
    const finalRightScore = currentRightScore;

    const podiumHtml = top5.map((entry, index) => {
        // Update rank when distance changes
        if (entry.distance !== lastDistance) {
            currentRank = index + 1;
            lastDistance = entry.distance;
        }

        const isWinner = entry.distance === winnerDistance;
        const playerName = players[entry.player]?.name || entry.player_name || entry.player;
        const distanceText = entry.distance === 0 ? 'PERFECT!' : `+${entry.distance}`;
        const scoreText = `${leftTeamCode} ${entry.square.row} - ${rightTeamCode} ${entry.square.col}`;
        const multiplierText = `${entry.multiplier || 1}x`;

        return `
            <div class="podium-entry ${isWinner ? 'winner' : 'other'}">
                <span class="podium-rank">${currentRank}.</span>
                <span class="podium-name" data-player-name="${playerName.replace(/"/g, '&quot;')}"></span>
                <span class="podium-multiplier">${multiplierText}</span>
                <span class="podium-score">${scoreText}</span>
                <span class="podium-distance">${distanceText}</span>
            </div>
        `;
    }).join('');

    // Create celebration overlay with winning team color gradient background
    const overlay = document.createElement('div');
    overlay.className = 'celebration-overlay';
    if (isLiteMode) overlay.classList.add('lite-mode');
    overlay.style.background = `linear-gradient(135deg, ${teamColors.winner[0]} 0%, ${teamColors.winner[1]} 100%)`;
    overlay.innerHTML = `
        <div class="celebration-confetti-layer" aria-hidden="true"></div>
        <div class="celebration-fireworks fireworks-left" id="fireworksLeft"></div>
        <div class="celebration-fireworks fireworks-right" id="fireworksRight"></div>
        <div class="celebration-content">
            <div class="celebration-trophy"><img src="/static/trophy3.png" alt="Trophy"></div>
            <div class="celebration-winner-banner">
                <div class="winner-label">WINNER</div>
                <div class="winner-name" id="celebrationWinnerName"></div>
            </div>
            <div class="celebration-final-score">
                <span class="final-score-team">${leftTeamCode}</span>
                <span class="final-score-value">${finalLeftScore}</span>
                <span class="final-score-separator">-</span>
                <span class="final-score-value">${finalRightScore}</span>
                <span class="final-score-team">${rightTeamCode}</span>
            </div>
            <div class="celebration-title">TOP 5 SQUARES</div>
            <div class="celebration-podium">
                ${podiumHtml}
            </div>
            <div class="celebration-actions">
                <button class="celebration-btn reset-btn" id="celebrationResetBtn">RESET</button>
                <button class="celebration-btn cancel-btn" id="celebrationCancelBtn">CANCEL</button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Set player names via textContent to prevent XSS
    overlay.querySelector('#celebrationWinnerName').textContent = winnerNames;
    overlay.querySelectorAll('.podium-name[data-player-name]').forEach(el => {
        el.textContent = el.dataset.playerName;
    });

    const stopFireworks = CelebrationEffects.mount(overlay, teamColors.winner);
    function closeCelebration() {
        stopFireworks();
        overlay.remove();
    }

    // Confetti is optional; fireworks always start when the celebration opens.
    if (!isLiteMode) {
        createConfetti(overlay.querySelector('.celebration-confetti-layer'), teamColors.winner);
    }

    // Add click handlers for buttons
    overlay.querySelector('#celebrationResetBtn').addEventListener('click', (e) => {
        e.stopPropagation();
        closeCelebration();
        resetGame(true);
    });

    overlay.querySelector('#celebrationCancelBtn').addEventListener('click', (e) => {
        e.stopPropagation();
        closeCelebration();
    });
}

// Create confetti particles
function createConfetti(container, teamColors = null) {
    // Skip confetti in lite mode
    if (isLiteMode) return;

    // Use team colors if provided, otherwise fall back to defaults
    const colors = teamColors || ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1'];

    for (let i = 0; i < 50; i++) {
        setTimeout(() => {
            if (!container.isConnected) return;
            const confetti = document.createElement('div');
            confetti.className = 'celebration-confetti';
            confetti.style.left = Math.random() * 100 + '%';
            confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            confetti.style.animationDuration = (Math.random() * 3 + 2) + 's';
            confetti.style.animationDelay = Math.random() * 2 + 's';
            container.appendChild(confetti);

            // Remove confetti after animation
            setTimeout(() => {
                if (confetti.parentNode) {
                    confetti.parentNode.removeChild(confetti);
                }
            }, 5000);
        }, i * 100);
    }
}

// Create static 8-bit style decorations for lite mode
function createStaticDecorations(container, teamColors) {
    const colors = teamColors || ['#FFD700', '#FF6B6B'];

    // Create decorations container
    const decorations = document.createElement('div');
    decorations.className = 'static-decorations';

    // Create static pixel confetti scattered around
    const confettiPositions = [
        // Left side confetti
        { x: 5, y: 10 }, { x: 8, y: 25 }, { x: 3, y: 40 }, { x: 10, y: 55 },
        { x: 6, y: 70 }, { x: 12, y: 85 }, { x: 4, y: 15 }, { x: 9, y: 45 },
        { x: 7, y: 60 }, { x: 2, y: 80 }, { x: 11, y: 30 }, { x: 5, y: 92 },
        // Right side confetti
        { x: 88, y: 12 }, { x: 92, y: 28 }, { x: 95, y: 42 }, { x: 89, y: 58 },
        { x: 94, y: 72 }, { x: 91, y: 88 }, { x: 87, y: 20 }, { x: 96, y: 48 },
        { x: 90, y: 65 }, { x: 93, y: 78 }, { x: 88, y: 35 }, { x: 97, y: 90 },
    ];

    confettiPositions.forEach((pos, i) => {
        const confetti = document.createElement('div');
        confetti.className = 'static-confetti';
        confetti.style.left = pos.x + '%';
        confetti.style.top = pos.y + '%';
        confetti.style.backgroundColor = colors[i % colors.length];
        // Vary sizes for 8-bit look
        const size = (i % 3 === 0) ? 6 : (i % 3 === 1) ? 8 : 10;
        confetti.style.width = size + 'px';
        confetti.style.height = size + 'px';
        decorations.appendChild(confetti);
    });

    // Create static 8-bit firework bursts - BIG and impressive
    const fireworkPositions = [
        { x: 6, y: 12, size: 'large' }, { x: 14, y: 45, size: 'large' }, { x: 8, y: 78, size: 'large' },
        { x: 94, y: 15, size: 'large' }, { x: 86, y: 50, size: 'large' }, { x: 92, y: 82, size: 'large' },
        { x: 10, y: 28, size: 'medium' }, { x: 5, y: 60, size: 'medium' },
        { x: 90, y: 32, size: 'medium' }, { x: 95, y: 65, size: 'medium' },
    ];

    fireworkPositions.forEach((pos, i) => {
        const firework = document.createElement('div');
        firework.className = 'static-firework';
        firework.style.left = pos.x + '%';
        firework.style.top = pos.y + '%';

        const isLarge = pos.size === 'large';
        const baseSize = isLarge ? 120 : 70;
        firework.style.width = baseSize + 'px';
        firework.style.height = baseSize + 'px';

        const color = colors[i % colors.length];
        const altColor = colors[(i + 1) % colors.length];

        // Large center pixel cluster (3x3 for big, 2x2 for medium)
        const centerSize = isLarge ? 12 : 8;
        const center = document.createElement('div');
        center.className = 'static-firework-center';
        center.style.backgroundColor = color;
        center.style.width = centerSize + 'px';
        center.style.height = centerSize + 'px';
        firework.appendChild(center);

        // Inner ring pixels around center
        const innerDist = isLarge ? 14 : 10;
        const innerPositions = [
            { dx: 0, dy: -innerDist }, { dx: 0, dy: innerDist },
            { dx: -innerDist, dy: 0 }, { dx: innerDist, dy: 0 },
        ];
        innerPositions.forEach(p => {
            const pixel = document.createElement('div');
            pixel.className = 'static-firework-ray';
            pixel.style.backgroundColor = color;
            pixel.style.width = '6px';
            pixel.style.height = '6px';
            pixel.style.left = `calc(50% + ${p.dx}px - 3px)`;
            pixel.style.top = `calc(50% + ${p.dy}px - 3px)`;
            firework.appendChild(pixel);
        });

        // Main rays - 8 directions with multiple pixels each
        const rayLength = isLarge ? 50 : 30;
        const rays = [
            { dx: 0, dy: -1 },   // up
            { dx: 0, dy: 1 },    // down
            { dx: -1, dy: 0 },   // left
            { dx: 1, dy: 0 },    // right
            { dx: -0.7, dy: -0.7 }, // up-left
            { dx: 0.7, dy: -0.7 },  // up-right
            { dx: -0.7, dy: 0.7 },  // down-left
            { dx: 0.7, dy: 0.7 },   // down-right
        ];

        rays.forEach((ray, j) => {
            const isCardinal = j < 4;
            const numPixels = isLarge ? (isCardinal ? 5 : 4) : (isCardinal ? 4 : 3);

            for (let k = 1; k <= numPixels; k++) {
                const dist = (rayLength / numPixels) * k;
                const pixel = document.createElement('div');
                pixel.className = 'static-firework-ray';
                // Alternate colors along the ray
                pixel.style.backgroundColor = k % 2 === 0 ? altColor : color;
                // Pixels get smaller toward the end
                const pixelSize = isLarge ? (7 - k) : (6 - k);
                pixel.style.width = Math.max(pixelSize, 3) + 'px';
                pixel.style.height = Math.max(pixelSize, 3) + 'px';
                pixel.style.left = `calc(50% + ${ray.dx * dist}px - ${pixelSize/2}px)`;
                pixel.style.top = `calc(50% + ${ray.dy * dist}px - ${pixelSize/2}px)`;
                // Fade out toward tips
                pixel.style.opacity = 1 - (k * 0.15);
                firework.appendChild(pixel);
            }
        });

        // Add extra sparkle pixels scattered around for large fireworks
        if (isLarge) {
            const sparkles = [
                { dx: 25, dy: -35 }, { dx: -30, dy: -30 }, { dx: 35, dy: 25 }, { dx: -25, dy: 35 },
                { dx: 40, dy: -15 }, { dx: -40, dy: 15 }, { dx: 15, dy: 40 }, { dx: -15, dy: -40 },
            ];
            sparkles.forEach((s, k) => {
                const sparkle = document.createElement('div');
                sparkle.className = 'static-firework-ray';
                sparkle.style.backgroundColor = k % 2 === 0 ? color : altColor;
                sparkle.style.width = '4px';
                sparkle.style.height = '4px';
                sparkle.style.left = `calc(50% + ${s.dx}px - 2px)`;
                sparkle.style.top = `calc(50% + ${s.dy}px - 2px)`;
                sparkle.style.opacity = '0.8';
                firework.appendChild(sparkle);
            });
        }

        decorations.appendChild(firework);
    });

    // Add bigger star/sparkle shapes
    const starPositions = [
        { x: 22, y: 8 }, { x: 78, y: 10 },
        { x: 20, y: 92 }, { x: 80, y: 90 },
        { x: 25, y: 40 }, { x: 75, y: 38 },
        { x: 23, y: 65 }, { x: 77, y: 62 },
    ];

    starPositions.forEach((pos, i) => {
        const star = document.createElement('div');
        star.className = 'static-firework';
        star.style.left = pos.x + '%';
        star.style.top = pos.y + '%';
        star.style.width = '50px';
        star.style.height = '50px';

        const color = colors[i % colors.length];
        const altColor = colors[(i + 1) % colors.length];

        // 4-point star with extended rays
        const starRays = [
            { dx: 0, dy: -20, size: 5 },
            { dx: 0, dy: 20, size: 5 },
            { dx: -20, dy: 0, size: 5 },
            { dx: 20, dy: 0, size: 5 },
            { dx: 0, dy: -12, size: 4 },
            { dx: 0, dy: 12, size: 4 },
            { dx: -12, dy: 0, size: 4 },
            { dx: 12, dy: 0, size: 4 },
            // Diagonal accents
            { dx: -10, dy: -10, size: 3 },
            { dx: 10, dy: -10, size: 3 },
            { dx: -10, dy: 10, size: 3 },
            { dx: 10, dy: 10, size: 3 },
        ];

        // Center cluster
        const starCenter = document.createElement('div');
        starCenter.style.position = 'absolute';
        starCenter.style.width = '8px';
        starCenter.style.height = '8px';
        starCenter.style.backgroundColor = color;
        starCenter.style.left = 'calc(50% - 4px)';
        starCenter.style.top = 'calc(50% - 4px)';
        star.appendChild(starCenter);

        starRays.forEach((ray, j) => {
            const pixel = document.createElement('div');
            pixel.className = 'static-firework-ray';
            pixel.style.backgroundColor = j < 4 ? color : (j < 8 ? altColor : color);
            pixel.style.width = ray.size + 'px';
            pixel.style.height = ray.size + 'px';
            pixel.style.left = `calc(50% + ${ray.dx}px - ${ray.size/2}px)`;
            pixel.style.top = `calc(50% + ${ray.dy}px - ${ray.size/2}px)`;
            if (j >= 8) pixel.style.opacity = '0.7';
            star.appendChild(pixel);
        });

        decorations.appendChild(star);
    });

    container.appendChild(decorations);
}

function resetGame(isNewGame = false) {
    showAlert(
        'All data will be erased. Continue?',
        isNewGame ? 'New Game' : 'Reset Game',
        true,
        (confirmed) => {
            if (confirmed) {
                // Show sport selection overlay
                const overlay = document.createElement('div');
                overlay.className = 'alert-overlay';
                overlay.style.display = 'flex';
                overlay.innerHTML = `
                    <div class="alert-content">
                        <h2 class="alert-title">SELECT SPORT</h2>
                        <div class="sport-grid">
                            <!-- <div class="sport-box" data-sport="fifa">FIFA</div> -->
                            <div class="sport-box" data-sport="mlb">MLB</div>
                            <!-- <div class="sport-box" data-sport="nba">NBA</div> -->
                            <div class="sport-box" data-sport="nfl">NFL</div>
                            <div class="sport-box" data-sport="nhl">NHL</div>
                            <div class="sport-box" data-sport="olym">OLYM</div>
                        </div>
                    </div>
                `;
                document.body.appendChild(overlay);

                // Add event listeners for sport selection
                overlay.querySelectorAll('.sport-box').forEach(box => {
                    box.addEventListener('click', async () => {  // Make this async
                        const sport = box.dataset.sport;
                        document.body.removeChild(overlay);
                        
                        // Show loading state
                        const loadingOverlay = document.createElement('div');
                        loadingOverlay.className = 'alert-overlay';
                        loadingOverlay.style.display = 'flex';
                        loadingOverlay.innerHTML = `
                            <div class="alert-content">
                                <h2 class="alert-title">${isNewGame ? 'STARTING NEW GAME' : 'RESETTING GAME'}</h2>
                                <div class="loading-dots">
                                    <span></span><span></span><span></span>
                                </div>
                            </div>
                        `;
                        document.body.appendChild(loadingOverlay);

                        const finishMutation = gameSync.beginMutation();
                        try {
                            // First reset the game (clears all state)
                            const resetResponse = await fetch('/api/reset', {
                                method: 'POST'
                            });
                            const resetData = await resetResponse.json();
                            if (!resetData.success) {
                                throw new Error('Failed to reset game');
                            }

                            // Then set the chosen sport (rebuilds grid, assigns tokens)
                            const sportResponse = await fetch('/api/sport', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ sport: sport })
                            });
                            const sportData = await sportResponse.json();
                            if (!sportData.success) {
                                throw new Error('Failed to update sport');
                            }

                            // Update UI — skip the API call since we already set the sport above
                            maxScore = sportData.max_score;
                            availableMultipliers = sportData.available_multipliers || [1];
                            multiplierLabels = sportData.multiplier_labels || [];
                            tokensPerPlayer = sportData.tokens_per_player || 40;
                            currentMultiplier = 1;
                            setSportTheme(sport, true);
                            updateMultiplierButtons();
                            players = {};
                            updatePlayerList();
                            document.getElementById('leftScore').textContent = '0';
                            document.getElementById('rightScore').textContent = '0';
							currentLeftScore = 0;  // Explicitly reset these variables
							currentRightScore = 0;
                            document.getElementById('teamLeft').value = '';
                            document.getElementById('teamRight').value = '';
                            createGrid();
                            highlightCurrentScore();

                            if (isNewGame) {
                                document.getElementById('landing-overlay').style.display = 'none';
                            }
                            
                            gameSync.start();
                            showAlert(isNewGame ? 'Game started' : 'Reset completed');
                        } catch (error) {
                            console.error(`Error ${isNewGame ? 'starting' : 'resetting'} game:`, error);
                            showAlert(`Failed to ${isNewGame ? 'start' : 'reset'} game`);
                        } finally {
                            finishMutation();
                            document.body.removeChild(loadingOverlay);
                        }
                    });
                });
            }
        }
    );
}

// Apply authoritative state without rebuilding the board on ordinary updates.
function applyGameState(data, { focusScore = false } = {}) {
    if (!data?.squares || !data.players || !data.teams || !data.scores ||
        !data.sport || !Number.isInteger(data.max_score)) {
        throw new Error('Invalid or incomplete game state');
    }
    const sportChanged = currentSport !== data.sport;
    const rebuild = maxScore !== data.max_score || mainGroup.select('.square').empty();
    const playersChanged = JSON.stringify(players) !== JSON.stringify(data.players);
    if (sportChanged || rebuild) setSportTheme(data.sport, true);
    maxScore = data.max_score;
    players = data.players;
    currentMultiplier = data.current_multiplier || 1;
    availableMultipliers = data.available_multipliers || [1];
    multiplierLabels = data.multiplier_labels || [];
    tokensPerPlayer = data.tokens_per_player || 40;
    updateMultiplierButtons();
    updatePlayerList();

    const left = document.getElementById('teamLeft');
    const right = document.getElementById('teamRight');
    left.value = data.teams.left || '';
    right.value = data.teams.right || '';
    updateTeamColors(false);
    currentLeftScore = data.scores.left;
    currentRightScore = data.scores.right;
    document.getElementById('leftScore').textContent = currentLeftScore;
    document.getElementById('rightScore').textContent = currentRightScore;
    if (rebuild) createGrid();

    mainGroup.selectAll('text.square-text').each(function () {
        const row = Number(this.getAttribute('data-row'));
        const col = Number(this.getAttribute('data-col'));
        if (row === col) return;
        const value = data.squares[row]?.[col] || '';
        if (this.textContent !== value || playersChanged || rebuild) {
            d3.select(this).text(value).style('fill', value && players[value]
                ? playerColorScale(players[value].playerIndex) : 'var(--retro-primary)')
                .call(boardText.center);
        }
    });
    highlightCurrentScore();
    highlightWinner(data.winner);
    // Focus only when entering/rebuilding a game; live updates preserve the user's view.
    if (focusScore || rebuild) goToScore();
}

const gameSync = new GameSync(applyGameState);
window.addEventListener('pagehide', () => gameSync.stop());
window.addEventListener('pageshow', () => {
    if (document.getElementById('landing-overlay').style.display === 'none') gameSync.start();
});

// Layout changes (including browser chrome and panel changes) update geometry.
document.fonts.ready.then(() => {
    // Discard fallback-font measurements once the bundled pixel font has loaded.
    boardText.clear();
    svg.selectAll('.square-text, .score-header-text').call(boardText.center);
});
const boardResizeObserver = new ResizeObserver(measureBoard);
boardResizeObserver.observe(gridContainer);
touchPointer.addEventListener('change', measureBoard);

document.addEventListener('DOMContentLoaded', () => {
    // Get references to elements
    const newGameBtn = document.getElementById('newGameBtn');
    const loadGameBtn = document.getElementById('loadGameBtn');
    const landingOverlay = document.getElementById('landing-overlay');
    const sportSelection = document.querySelector('.sport-selection');
    const mainButtons = document.getElementById('mainButtons');
    const backToMainBtn = document.getElementById('backToMainBtn');

    // New Game button click
	newGameBtn.addEventListener('click', () => resetGame(true));

    // Back button click
    backToMainBtn.addEventListener('click', () => {
        sportSelection.style.display = 'none';
        mainButtons.style.display = 'flex';
    });

    // Add click handlers for sport boxes in the landing page
    document.querySelectorAll('.sport-box').forEach(box => {
        box.addEventListener('click', () => {
            const sport = box.dataset.sport;
            setSportTheme(sport);
        });
    });

	// Update loadGameBtn click handler to handle max score
	loadGameBtn.addEventListener('click', () => {
		// Temporarily enable lite-mode to reduce animation load during loading
		const wasLiteMode = document.body.classList.contains('lite-mode');
		document.body.classList.add('lite-mode');

		// Use requestAnimationFrame to ensure lite-mode is applied before showing overlay
		requestAnimationFrame(() => {
		requestAnimationFrame(() => {

		// Show loading indicator
		const loadingOverlay = document.createElement('div');
		loadingOverlay.className = 'alert-overlay';
		loadingOverlay.style.display = 'flex';
		loadingOverlay.dataset.tempLiteMode = !wasLiteMode;
		loadingOverlay.innerHTML = `
			<div class="alert-content">
				<h2 class="alert-title">LOADING GAME</h2>
				<div class="loading-dots">
					<span></span><span></span><span></span>
				</div>
			</div>
		`;
		document.body.appendChild(loadingOverlay);

		fetch('/api/state', {
			method: 'GET', cache: 'no-store'
		})
		.then(response => {
			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}
			return response.json();
		})
		.then(data => {
			applyGameState(data, { focusScore: true });
			gameSync.start();

			// Hide overlays
			document.getElementById('landing-overlay').style.display = 'none';
			// Restore lite-mode state if it was temporarily added
			if (loadingOverlay.dataset.tempLiteMode === 'true') {
				document.body.classList.remove('lite-mode');
			}
			document.body.removeChild(loadingOverlay);

			// Show success message
			showAlert('Game loaded successfully');
		})
		.catch(error => {
			console.error('Error loading game state:', error);
			showAlert('Failed to load game state: ' + error.message);
			// Restore lite-mode state if it was temporarily added
			if (loadingOverlay.dataset.tempLiteMode === 'true') {
				document.body.classList.remove('lite-mode');
			}
			document.body.removeChild(loadingOverlay);
		});

		}); // close inner requestAnimationFrame
		}); // close outer requestAnimationFrame
	});

    // Then populate the team selects
    populateTeamSelects();

    // Initialize multiplier buttons
    updateMultiplierButtons();
});
