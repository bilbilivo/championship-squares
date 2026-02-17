# Testing Guide

## Overview

Championship Squares includes a test setup script (`test_setup.py`) that populates a complete game with sample data. This guide covers testing procedures and data generation.

---

## Test Setup Script

### What It Does

`test_setup.py` creates a fully loaded NFL game:
- 12 random players
- 2 random NFL teams
- 29 bets per player (40 tokens distributed across 1x, 2x, 4x, 8x multipliers)
- Game board 95% filled

**Distribution per player:**
- 26 squares at 1x (26 tokens)
- 1 square at 2x (2 tokens)
- 1 square at 4x (4 tokens)
- 1 square at 8x (8 tokens)
- **Total: 40 tokens**

### Prerequisites

1. Server running: `python app.py` (or via launcher script)
2. Python 3.7+ installed
3. `requests` module installed (included in requirements.txt)

### Running the Script

From the project directory:

```bash
python test_setup.py
```

**Output example:**
```
==================================================
Championship Squares - Test Setup
==================================================

Checking server at http://localhost:8080...
  Server is running

Setting sport to NFL...
  Sport set to NFL, max_score: 70
Setting teams: MIN vs GB...
  Teams set: MIN (away) vs GB (home)
Adding 12 players...
  Added player A: MIKE
  Added player B: SARAH
  ...
Placing bets for all players...
  Placing bets for player A...
    A: 26@1x + 1@2x + 1@4x + 1@8x = 29 squares (40 tokens)
  ...
==================================================
Test setup complete!
  - Sport: NFL
  - Players: 12
  - Total bets: 348 squares (480 tokens)
==================================================
```

---

## Testing Scenarios

### Scenario 1: Basic Game Flow

1. Run `python test_setup.py` to populate game
2. Open browser to `http://localhost:8080`
3. Verify board shows 12 players with initials
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

1. Load test game with `python test_setup.py`
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
4. Refresh Tab 2
5. Verify both see same state

**Checks:**
- State persists across browser sessions
- No data corruption from rapid updates
- Score updates sync between tabs

---

## Manual API Testing

### Using curl

Test endpoints directly without UI:

**Get game state:**
```bash
curl http://localhost:8080/api/state
```

**Update scores:**
```bash
curl -X POST http://localhost:8080/api/scores \
  -H "Content-Type: application/json" \
  -d '{"left": 21, "right": 17}'
```

**Get winner:**
```bash
curl http://localhost:8080/api/winner
```

**Reset game:**
```bash
curl -X POST http://localhost:8080/api/reset
```

### Using Postman/Insomnia

Import Championship Squares API for comprehensive testing:
1. Import `API_DOCUMENTATION.md` endpoints
2. Create test collections for each scenario
3. Save responses for regression testing

### Using Browser Console

Quick testing from browser (F12 console):

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

### Modifying test_setup.py

Edit the script to change test parameters:

**Change player count:**
```python
players = add_players(20)  # Instead of 12
```

**Change sport:**
```python
if not set_sport("nba"):  # Instead of "nfl"
```

**Change bet distribution:**
Modify `place_bets_for_players()` to use different multiplier distributions.

---

## Edge Case Testing

### Test: Maximum Players

```bash
# Modify test_setup.py
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
- Check BASE_URL in test_setup.py matches server
- On Linux, may need to wait for server startup

**Bet placement fails:**
- Ensure sport set before reset (script does this)
- Check token count sufficient
- Verify square not already claimed

**Inconsistent scores:**
- Refresh browser before checking
- Check browser cache (Ctrl+Shift+Delete)
- Verify not using multiple browser tabs simultaneously
