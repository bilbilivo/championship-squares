# Developer Guide

## Architecture Overview

Championship Squares uses a modern client-server architecture:

**Backend:** Python Flask REST API  
**Frontend:** HTML5 + CSS3 + Vanilla JavaScript + D3.js visualization  
**State:** SQLite database persistence  

---

## Project Structure

```
app.py                 # Main Flask application with API endpoints
config.py              # Configuration and sport settings
database.py            # Database access layer
pyproject.toml         # Project metadata and dependencies
templates/index.html   # Single-page HTML template with embedded CSS/JS
static/               # Frontend assets (D3.js, fonts, images)
logs/                 # Runtime logs
game_state.db         # Persisted game state (SQLite)
```

---

## Backend Architecture

### GameState Class
Core state management class in `app.py`.

**Key Methods:**
- `reset_state()` - Initialize fresh game
- `save_state()` - Persist to JSON file
- `load_state()` - Restore from file with migration support
- `get_next_player_index()` - Allocate player slot
- `release_player_index()` - Free player slot

**Key Attributes:**
- `squares` - 2D array of player initials
- `square_multipliers` - Dict mapping square coordinates to multiplier values
- `players` - Dict with player data (name, tokens, bets)
- `teams` - Left/right team names
- `scores` - Current game scores
- `sport` - Current sport setting
- `current_multiplier` - Active multiplier for new claims

### Config Class
Configuration management in `config.py`.

**Key Methods:**
- `update_sport(sport)` - Switch sport and update max_score

**Key Attributes:**
- `max_scores` - Sport-specific maximum grid scores
- `multipliers` - Sport-specific available multipliers
- `multiplier_labels` - Sport-specific multiplier descriptions
- `total_tokens` - Sport-specific token allocations
- `config` - Runtime configuration (host, port, max_players, max_score)

### API Routes
All routes defined with `@app.route()` decorator in `app.py`.

**Route Categories:**
- **State Management:** `/api/state`, `/api/reset`
- **Gameplay:** `/api/scores`, `/api/winner`, `/api/squares`
- **Players:** `/api/players`, `/api/players/<initial>`
- **Configuration:** `/api/teams`, `/api/sport`, `/api/multiplier`
- **Analytics:** `/api/standings`

---

## Frontend Architecture

### Template Structure
Single `index.html` file contains:
- HTML structure
- Inline CSS styles
- Inline JavaScript

### Key JavaScript Components

**Game Manager**
- Handles API calls to backend
- Manages local game state cache
- Triggers UI updates

**D3.js Visualization**
- Renders interactive grid
- Handles square clicks
- Displays multipliers and player initials
- Animates winning paths and confetti

**UI Controls**
- Player management (add/remove)
- Team name entry
- Score input
- Sport selection
- Multiplier selection
- Reset button

### CSS Styling
- Retro 80s/90s arcade aesthetic
- Sport-specific color themes
- CSS animations (scanlines, glows, confetti)
- Responsive grid layout
- Dark mode with lite mode fallback

---

## Adding a New Sport

### Step 1: Update config.py
Add sport configuration to the `Config` class:

```python
# In max_scores dict
'newsport': 40

# In multipliers dict
'newsport': [1, 2, 4]

# In multiplier_labels dict
'newsport': ['<Stage1', '<Stage2', '<Stage3']

# In total_tokens dict
'newsport': 20
```

### Step 2: Update Color Theme (Optional)
In `templates/index.html`, add CSS variables for the new sport in the theme section.

### Step 3: Test
- Switch to new sport via API or UI
- Verify grid size matches max_score
- Confirm multiplier buttons display correctly
- Test player claiming and scoring

---

## Extending GameState

### Adding New State Properties
1. Update `reset_state()` to initialize new property
2. Update `save_game_state()` in `database.py` to include in DB
3. Update `load_game_state()` in `database.py` to restore from DB
4. Update any relevant API routes to read/return property

### Adding Game Logic
- Add methods to GameState class
- Create corresponding API route
- Update frontend to call new endpoint
- Test state persistence

---

## Release Procedure

Championship Squares follows a two-step release procedure:

1. **Update the CHANGELOG.md**:
   - Add a new entry summarizing the version, date, and major changes.
   - Document the comparison link.
2. **Create a Git tag** for the new version:
   - Use `git tag -a vYYYY.MM -m "release notes"` for annotated tags
   - Push the tag with `git push origin vYYYY.MM`
3. **Publish a GitHub Release**:
   - Use GitHub UI or `gh release create` to turn the tag into a release
   - Attach detailed notes summarizing changes and provide comparison links (see CHANGELOG.md)

---

## API Development

### Adding a New Endpoint

1. Create Flask route with `@app.route()` decorator
2. Define request data structure
3. Access game_state and update as needed
4. Save state with `game_state.save_state()`
5. Return JSON response with status/data
6. Handle exceptions with try/except

**Example Pattern:**
```python
@app.route('/api/example', methods=['POST'])
def example_endpoint():
    try:
        data = request.json
        # Validate input
        # Update game_state
        game_state.save_state()
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## State Persistence

### Database Schema (SQLite)
Game state saved to `game_state.db`.

Tables:
- `game_config`: Key-value store for global settings (sport, scores, teams)
- `players`: Player records (name, tokens, bets)
- `squares`: Grid state (row, col, player, multiplier)
- `available_indices`: Available player slots

### Migration Support
`load_state()` handles data loading and validation:
- Auto-generates missing tokens field if needed
- Handles format changes gracefully
- Validates array sizes match current sport
- Caps scores at maximum

### Auto-Save
- Triggered after every state-changing operation
- Failures logged but don't break gameplay
- Allows server restarts without data loss

---

## Frontend Data Flow

### State Synchronization
1. **Startup** - Fetch initial state with `/api/state`
2. **Player Action** - User interacts with UI
3. **API Call** - Send POST/DELETE request to backend
4. **State Update** - Backend updates GameState and saves
5. **Response** - Backend returns updated data
6. **UI Render** - JavaScript updates display

### Event Handling
- Click handlers on grid squares
- Form submission handlers for player/team input
- Select dropdown change handlers for sport/multiplier
- Button click handlers for reset/other actions

---

## Testing Considerations

### Test Coverage Areas
- State initialization and reset
- Player add/remove (slot management)
- Square claiming (multiplier application, token deduction)
- Score updates and winner calculation
- Sport switching (max_score, multiplier updates)
- State persistence (save/load round-trip)

### Edge Cases
- Maximum players reached
- Insufficient tokens
- Invalid sport selection
- Out-of-range scores
- Corrupted state file
- Concurrent requests

---

## Performance Notes

### Optimization Opportunities
- D3.js visualization refreshes full grid on updates (could be incremental)
- State persisted on every change (database transactions are fast but frequent)
- No caching of winner calculations (recalculated on demand)

### Scalability Limitations
- SQLite database (better than JSON, but still file-based)
- Single Flask process (adequate for small to medium deployments)
- All players in memory (acceptable for <100 players)
- No distributed state (single machine only)

---

## Development Workflow

### Local Setup (Using Virtual Environment)
1. Clone repository
2. Create Python virtual environment: `python3 -m venv venv`
3. Activate virtual environment:
   - **Linux/macOS:** `source venv/bin/activate`
   - **Windows:** `venv\Scripts\activate`
4. Install dependencies: `pip install ".[dev]"` (for development) or `pip install .` (for production)
5. Run server: `python app.py` or use launcher script

**Important:** Always develop within the virtual environment. This isolates project dependencies from your system Python.

### Making Changes
1. Ensure virtual environment is activated (see Local Setup above)
2. Edit relevant file (app.py, config.py, database.py, or index.html)
3. Server auto-reloads on file changes (debug mode)
4. Test via browser UI or API calls
5. Verify state persistence

### Debugging
- Check browser console (F12) for JavaScript errors
- Check terminal output for Flask errors
- Review `logs/` directory if present
- Check `game_state.db` using sqlite3 CLI

---

## Browser Compatibility

**Tested/Supported:**
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

**Requirements:**
- ES6 JavaScript support
- CSS Grid support
- SVG support (for D3.js)
- Local Storage (for lite mode persistence)

---

## Deployment for Development

### Flask Debug Mode
```bash
FLASK_ENV=development FLASK_DEBUG=1 python app.py
```

Enables auto-reload on file changes and detailed error pages.

### Lite Mode
```bash
LITE_MODE=1 python app.py
```

Disables visual effects for testing on slower machines.

---

## Future Enhancement Ideas

- User authentication and multi-session support
- Database backend (SQLite/PostgreSQL)
- Undo/redo functionality
- Game history and statistics
- Customizable grid sizes
- Import/export game data
- Mobile app
- Real API score integration
