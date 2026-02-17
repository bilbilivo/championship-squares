# Configuration Guide

## Overview

Championship Squares configuration is managed through `config.py`. Modify settings in this file to customize game parameters, sports, and server behavior.

---

## Server Configuration

In `config.py`, the `Config` class contains server settings:

### Host & Port
```python
self.config = {
    'host': platform_hosts.get(self.system, '0.0.0.0'),
    'port': 8080,
    'debug': False,
    'max_players': 12,
    'max_score': self.max_scores['nfl']
}
```

**Modifiable Settings:**
- `port` - Server port (default 8080). Change to run multiple instances.
- `debug` - Enable Flask debug mode (default False). Set to True for development.
- `max_players` - Maximum player slots (default 12). Increase for larger groups.

**Auto-Set (Platform-Aware):**
- `host` - Windows/macOS use 'localhost', Linux uses '0.0.0.0' for network access.

---

## Sport Configuration

All sports are defined in `config.py`. Each sport has three key settings:

### Max Score
The highest possible row/column value in the game grid.

```python
self.max_scores = {
    'nfl': 70,
    'nhl': 12,
    'nba': 160,
    'mlb': 30,
    'olym': 12,
    'fifa': 10
}
```

**How it Works:**
- Determines grid size (max_score + 1 rows/columns)
- NFL with max_score 70 = 71×71 grid
- Higher scores = larger grids = more squares available

**Adjusting:**
- Increase if games regularly exceed current maximum
- Decrease if games never reach high scores
- Must account for realistic game scores

---

### Multipliers
Available multiplier values for betting on squares.

```python
self.multipliers = {
    'nfl': [1, 2, 4, 8],
    'nhl': [1, 2, 4],
    'nba': [1, 2, 4, 8],
    'mlb': [1, 2, 4, 8],
    'olym': [1, 2, 4],
    'fifa': [1, 2]
}
```

**How it Works:**
- Multiplier value multiplied by 1 token = cost to claim square
- 4x multiplier costs 4 tokens
- Higher multipliers = higher risk/reward

**Adjusting:**
- Add more tiers: `'nfl': [1, 2, 4, 8, 16]`
- Remove tiers: `'nfl': [1, 2, 4]`
- Ensure labels list has same length (see below)

---

### Multiplier Labels
Descriptions for when each multiplier applies during game.

```python
self.multiplier_labels = {
    'nfl': ['<Q1', '<Q2', '<Q3', '<Q4'],
    'nhl': ['<P1', '<P2', '<P3'],
    'nba': ['<Q1', '<Q2', '<Q3', '<Q4'],
    'mlb': ['<I3', '<I6', '<I8', '<I9'],
    'olym': ['<P1', '<P2', '<P3'],
    'fifa': ['<H1', '<H2']
}
```

**How it Works:**
- Labels appear in the UI multiplier buttons
- Describe game period/quarter when multiplier is used
- Example: '<Q1' = "Before/During Quarter 1"

**Label Conventions:**
- `Q#` - Quarter (NFL, NBA)
- `P#` - Period (NHL, Olympics)
- `I#` - Inning (MLB)
- `H#` - Half (Soccer/FIFA)

**Adjusting:**
- Keep same count as multipliers list
- Update when changing multiplier tiers
- Display only in UI; doesn't affect gameplay

---

### Total Tokens
Starting token allocation per player for each sport.

```python
self.total_tokens = {
    'nfl': 40,
    'nhl': 12,
    'nba': 48,
    'mlb': 16,
    'olym': 12,
    'fifa': 8
}
```

**How it Works:**
- Each new player receives this many tokens
- Tokens represent total betting budget
- Token spent = multiplier × 1

**Token Math:**
- 40 tokens with 1x-8x multipliers = ~10 squares average
- 12 tokens with 1x-4x multipliers = ~6 squares average
- Higher tokens = more engagement, longer play

**Adjusting:**
- Increase for more strategic depth
- Decrease for faster, simpler games
- Should exceed max_score for good gameplay

---

## Adding a New Sport

Complete example of adding a new sport called "XYZ":

### 1. Add Max Score
```python
self.max_scores = {
    ...
    'xyz': 50  # Your sport's typical max score
}
```

### 2. Add Multipliers
```python
self.multipliers = {
    ...
    'xyz': [1, 2, 4]  # Choose appropriate tiers
}
```

### 3. Add Multiplier Labels
```python
self.multiplier_labels = {
    ...
    'xyz': ['<Stage1', '<Stage2', '<Stage3']  # Match multiplier count
}
```

### 4. Add Total Tokens
```python
self.total_tokens = {
    ...
    'xyz': 20  # Budget for players
}
```

### 5. Add UI Theme (Optional)
In `templates/index.html`, add CSS color variables:
```css
.sport-xyz {
    --primary-color: #FF5733;
    --secondary-color: #22BBEE;
    --accent-color: #FFAA00;
}
```

### 6. Update API Default (Optional)
In `app.py`, GameState.reset_state():
```python
self.sport = 'xyz'  # Change from 'nfl' to new default
```

---

## Platform-Specific Settings

### Windows
- Host: 'localhost' (local machine only)
- Port: Default 8080
- Launcher: `start_server.ps1` (PowerShell)

### macOS
- Host: 'localhost' (local machine only)
- Port: Default 8080
- Launcher: `start_server.sh` (Bash)

### Linux
- Host: '0.0.0.0' (accessible over network)
- Port: Default 8080
- Launcher: `start_server.sh` (Bash)

**Note:** To change host on Windows/macOS for network access, edit `platform_hosts` dict in config.py.

---

## Player Slot Management

Default maximum players: 12

Increase in config:
```python
'max_players': 20
```

**Considerations:**
- More players = more UI complexity
- Squares array grows with player count internally
- Memory usage is negligible up to 100+ players
- Grid display may become crowded

---

## Debug Mode

Enable detailed error output and auto-reload:

```python
self.config = {
    ...
    'debug': True
}
```

Or via environment variable:
```bash
FLASK_DEBUG=1 python app.py
```

**Debug Mode Effects:**
- Server restarts on file changes
- Detailed error pages in browser
- API validation errors show stack traces
- Performance slightly degraded

---

## Environment Variables

Override config via environment variables:

### LITE_MODE
Disable visual effects (animations, confetti, scanlines):
```bash
LITE_MODE=1 python app.py
```

Affects:
- D3.js animations disabled
- CSS animations/effects disabled
- Cleaner, faster rendering
- Better for performance testing

### FLASK_ENV
Set development mode:
```bash
FLASK_ENV=development python app.py
```

### FLASK_DEBUG
Enable debug mode:
```bash
FLASK_DEBUG=1 python app.py
```

---

## Configuration Best Practices

### For Casual Play
- Standard sport settings (no changes needed)
- 12 players maximum
- Default tokens per sport

### For Competitive Play
- Increase max_score by 10-20% (adds challenge)
- Increase multipliers (higher risk/reward)
- Increase tokens (more strategic choice)
- Example: NFL at max_score 80, tokens 50

### For Quick Games
- Decrease max_score by 20% (games end faster)
- Decrease tokens (fewer squares, quicker fills)
- Keep multipliers standard
- Example: NFL at max_score 50, tokens 25

### For Large Groups
- Increase max_players to 16-20
- Increase max_score slightly (more squares available)
- Increase tokens (spread betting across more players)

### For Testing
- Set `debug: True`
- Use LITE_MODE for performance testing
- Use small max_score for fast grid rendering
- Example: 'test' sport with max_score 10

---

## File Locations

**Configuration file:** `/config.py`

**Sport colors in template:** `/templates/index.html` (CSS section)

**Game state file:** `/game_state.db` (auto-created)

---

## Restoring Defaults

If configuration becomes corrupted, delete `game_state.db` and reset `config.py` to factory defaults (from git).

```bash
git checkout config.py
rm game_state.db
python app.py
```

This resets all settings and clears the saved game.

---

## Validation

Configuration is validated on startup:
- Unknown sports are caught (returns error)
- Max score must match available multipliers
- Token counts must be positive
- Player limits enforced

Invalid configurations will cause API errors when attempting to use them.
