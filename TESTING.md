# Testing Guide

## Responsive board regression checks

Run the board, text alignment, live sync, celebration, and login tests with Node.js 18 or later (no npm dependencies):

```bash
node --test tests/*.test.cjs
```

Run application regressions with `venv/bin/python -m pytest -q`. The pytest fixtures
use temporary databases; do not seed or reset a live game for visual testing.

For browser verification, use a separate test instance with disposable game data.
Check 1366×768, 1920×1080, 2560×1440, 3440×1440, 768×1024, 390×844,
and 844×390 viewports. Exercise NFL, MLB, NHL, and Olympics with no players and
with 12 players, loaded claims, long team names, prompts, and a final celebration.

- New and loaded games use the Go to score view: roughly 15 cells along the shorter viewport dimension, including the score and winning squares. Panning stops at all four edges.
- Score headers remain visible and aligned; the final row and column are reachable.
- Zooming out fully shows the entire board, flush with the top and left score axes. Zooming out, panning, and resizing must never introduce a gap between either axis and the grid. Selecting a cell smaller than 24px navigates without claiming it.
- Resize while zoomed and verify the same region remains visible unless an edge requires clamping.
- Go to score locates both low and maximum scores. Navigation sends no game-state writes.
- Desktop player lists scroll independently; narrow-screen controls and dialog actions remain reachable.
- Check keyboard pan/zoom, touch drag/pinch, and normal, lite, and reduced-motion rendering. End-game fireworks always start automatically; other effects retain their motion settings.

## Login regression checks

- ADMIN sees New Game / Load Game and retains all controls.
- PLAYER selects or creates a player and enters the current game directly.
- Players can place/remove only their own tokens; other players and admin settings stay protected.
- Change mode signs out; refresh restores the selected session.
- Deleting a player or resetting the game invalidates that player's session.
- `tests/test_generate_fake_game.py` runs the generator against isolated Flask clients for every sport.

## Overview

Championship Squares includes a test setup script (`tests/generate_fake_game.py`) that populates a complete game with sample data. This guide covers testing procedures and data generation.

---

## Test Setup Script

### What It Does

`tests/generate_fake_game.py` logs in as ADMIN and replaces the target game with
8 players, two teams, scores, and random bets. NFL is the default; pass `nhl`, `mlb`,
or `olym` to select another sport. Set `CHAMPIONSHIP_SQUARES_URL` to target a disposable
instance instead of the default `http://localhost:8080`.

NFL gives each player 40 tokens: 12 squares at 1x, 6 at 2x, 2 at 4x, and 1 at 8x
(21 squares per player, 168 total). Login failure stops setup before resetting data.

### Prerequisites

1. **Virtual environment activated** (REQUIRED):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   ```

2. Server running: `python app.py` (or via launcher script)
3. Python 3.10+ installed
4. Test script will use the `requests` module from the `dev` extras in `pyproject.toml`

### Running the Script

From the project directory:

```bash
python tests/generate_fake_game.py
```


## Testing Scenarios

### Scenario 1: Basic Game Flow

1. Run `python tests/generate_fake_game.py` to populate game
2. Open browser to `http://localhost:8080`
3. Select ADMIN → Load Game and verify board shows 8 players with initials
4. Update team scores: "MIN 14, GB 17"
5. Verify winner displays (if closest square exists)
6. Click Reset to clear game

**Checks:**
- Board renders correctly
- Player initials visible in squares
- Score updates propagate
- Winner calculation works
- Reset clears all data

---

### Scenario 2: Winner Calculation

1. Load test game with `python tests/generate_fake_game.py`
2. Open developer console (F12)
3. Manually call winner endpoint:
   ```javascript
   fetch('/api/winner').then(r => r.json()).then(console.log)
   ```
4. Update scores to approach different final scores
5. Verify winner changes correctly

**Checks:**
- Manhattan distance calculation correct
- Multiple winners handled properly
- Path visualization accurate
- Winner persists across score updates

---

### Scenario 3: Token Budget

1. Load test game
2. Attempt to add new player (should succeed)
3. Attempt to claim many squares at high multipliers
4. Verify token deduction correct:
   - 1x square = 1 token
   - 2x square = 2 tokens
   - 4x square = 4 tokens
   - 8x square = 8 tokens

**Checks:**
- Token count decreases with claims
- Cannot claim when insufficient tokens
- Reset restores full token allocation
- Token display matches backend state

---

### Scenario 4: Player Management

1. Load test game
2. Remove a player from the UI
3. Verify their squares cleared
4. Verify player can be re-added
5. Check available player slots updated

**Checks:**
- Player removal clears squares
- Player index released for reuse
- Player list updates correctly
- No orphaned data

---

### Scenario 5: Sport Switching

1. Load test game (NFL)
2. Switch to NHL via UI dropdown
3. Verify grid shrinks from 71×71 to 13×13
4. Verify multipliers update (1x, 2x, 4x instead of 1x-8x)
5. Switch back to NFL
6. Verify grid expands again

**Checks:**
- Grid resizes correctly
- Max score updates
- Multiplier options change
- Previous scores capped appropriately
- UI updates instantly

---

### Scenario 6: Concurrent Operations

1. Load test game
2. Open same game in 2 browser tabs
3. Update score in Tab 1
4. Verify Tab 2 updates without refreshing, then disconnect and reconnect it
5. Verify both see same state

**Checks:**
- State persists across browser sessions
- No data corruption from rapid updates
- Score updates sync between tabs

---

## Manual API Testing

### Using curl

Test endpoints directly without UI. First log in and save the session cookie:

```bash
curl -c /tmp/squares-cookies.txt http://localhost:8080/api/login \
  -H "Content-Type: application/json" -d '{"role":"admin"}'
```

**Get game state:**
```bash
curl http://localhost:8080/api/state
```

**Update scores:**
```bash
curl -b /tmp/squares-cookies.txt -X POST http://localhost:8080/api/scores \
  -H "Content-Type: application/json" \
  -d '{"left": 21, "right": 17}'
```

**Get winner:**
```bash
curl http://localhost:8080/api/winner
```

**Reset game:**
```bash
curl -b /tmp/squares-cookies.txt -X POST http://localhost:8080/api/reset
```

### Using Postman/Insomnia

Import Championship Squares API for comprehensive testing:
1. Import `API_DOCUMENTATION.md` endpoints
2. POST `/api/login` with `{"role":"admin"}` and retain its cookie. Create test collections for each scenario
3. Save responses for regression testing

### Using Browser Console

Select ADMIN in the page first, then test from its browser console (F12).
Fetch uses the browser session cookie automatically:

```javascript
// Get state
fetch('/api/state').then(r => r.json()).then(console.log)

// Update scores
fetch('/api/scores', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({left: 14, right: 10})
}).then(r => r.json()).then(console.log)

// Get winner
fetch('/api/winner').then(r => r.json()).then(console.log)

// Reset game
fetch('/api/reset', {method: 'POST'}).then(r => r.json()).then(console.log)
```

---

## Customizing Test Data

### Modifying tests/generate_fake_game.py

Edit the script to change test parameters:

**Change player count or token distribution:**
Edit the selected sport's `players` and `bet_distribution` entries in `SPORT_CONFIG`.
Keep the count within the app's player limit and the total token cost within
`tokens_per_player`.

**Change sport:**
```bash
python tests/generate_fake_game.py nhl
```

**Target a disposable test server:**
```bash
CHAMPIONSHIP_SQUARES_URL=http://localhost:5059 python tests/generate_fake_game.py nfl
```

---

## Edge Case Testing

### Test: Maximum Players

```bash
# Modify tests/generate_fake_game.py
add_players(12)  # Change to max_players value in config.py
```

Verify 13th player add fails with appropriate error.

### Test: Insufficient Tokens

1. Load test game
2. Manually update player tokens to low value in DB
3. Attempt to claim high-multiplier square
4. Verify rejection/error

### Test: Score Validation

1. Load test game (NFL, max_score 70)
2. Via API, try to set score to 100
3. Verify score capped at 70

### Test: Corrupted State

1. Start server normally
2. Corrupt `game_state.db` (e.g. `echo "junk" > game_state.db`)
3. Restart server
4. Verify graceful recovery (reset to fresh state)
5. Check logs for error messages

---

## Performance Testing

### Load Testing

Use Apache Bench or similar:

```bash
# 100 requests, 10 concurrent
ab -n 100 -c 10 http://localhost:8080/
```

### Memory Usage

Monitor during stress test:

```bash
# Linux/macOS
top -p $(pgrep -f "python app.py")

# Watch memory over time
watch -n 1 'ps aux | grep "python app.py"'
```

### Grid Rendering

Test large grids:

```python
# Modify config.py temporarily
'nba': 200  # Instead of 160 (creates 201×201 grid)
```

Monitor D3.js render time and browser responsiveness.

---

## Browser Compatibility Testing

Test in each supported browser:

**Chrome/Chromium:**
- Latest stable version
- Check console for errors (F12)

**Firefox:**
- Latest stable version
- Test CSS Grid support
- Monitor performance (performance tab)

**Safari:**
- macOS latest
- iOS Safari for mobile testing
- Check animation smoothness

**Internet Explorer:**
- Not supported (no ES6, CSS Grid support)

---

## Regression Testing Checklist

After any code changes, verify:

- [ ] Game loads without JS errors
- [ ] All players display correctly
- [ ] Scores update and persist
- [ ] Winner calculation accurate
- [ ] New players can be added
- [ ] Players can be removed
- [ ] Squares can be claimed
- [ ] Multipliers apply correctly
- [ ] Sport switching works
- [ ] Reset clears all data
- [ ] Game state persists across restarts
- [ ] No console errors or warnings
- [ ] Animations smooth (if not lite mode)
- [ ] Mobile/tablet responsive (if applicable)

---

## Continuous Integration

For automated testing setup:

1. **Unit Tests** - Test GameState class methods
2. **API Tests** - Hit endpoints and verify responses
3. **Snapshot Tests** - Compare JSON state outputs
4. **Visual Regression** - Screenshot grid layouts

See `DEVELOPER_GUIDE.md` for architecture details on testable components.

---

## Troubleshooting Tests

**Script fails to connect:**
- Verify server running: `python app.py`
- Check BASE_URL in tests/generate_fake_game.py matches server
- On Linux, may need to wait for server startup

**Bet placement fails:**
- Ensure sport set before reset (script does this)
- Check token count sufficient
- Verify square not already claimed

**Inconsistent scores:**
- Refresh browser before checking
- Check browser cache (Ctrl+Shift+Delete)
- Confirm all devices use the same server and that only one threaded server process is running
