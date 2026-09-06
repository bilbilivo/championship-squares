# API Documentation

## Overview
Championship Squares is controlled via REST API endpoints. All API endpoints return JSON responses.

---

## Base URL
```
http://localhost:8080
```

---

## Sessions and permissions

Mode selection has no passwords: anyone can choose ADMIN or an existing player.
All game mutations require a session cookie. Read-only game endpoints remain public.

| Action | ADMIN | PLAYER |
| --- | --- | --- |
| Read current game | Yes | Yes |
| Place/remove selected player's tokens | Yes | Yes |
| Change other players' squares | Yes | No |
| Change scores, teams, sport, multiplier, or reset | Yes | No |
| Add/delete players via `/api/players` | Yes | No |

**POST `/api/login`** selects a mode and returns `{"role": "admin", "player": null}`
or `{"role": "player", "player": "A"}`. Send one of:

```json
{"role": "admin"}
```
```json
{"role": "player", "initial": "A"}
```
```json
{"role": "player", "initial": "A", "name": "ALICE", "create": true}
```

Creating a player joins the current game; it does not reset or change the sport.
**GET `/api/session`** returns the selected role/player, or null values when signed out.
**POST `/api/logout`** clears the session. Deleted/reset players and server restarts
require players to select their identity again.

Retain cookies for subsequent requests:

```bash
curl -c /tmp/squares-cookies.txt http://localhost:8080/api/login \
  -H 'Content-Type: application/json' -d '{"role":"admin"}'
curl -b /tmp/squares-cookies.txt -X POST http://localhost:8080/api/scores \
  -H 'Content-Type: application/json' -d '{"left":7,"right":3}'
```

Missing login returns **401**; a forbidden player action or stale player identity
returns **403**. A square with a mismatched `expected_value` returns **409**.

## Endpoints

### Get Current Game State
**GET** `/api/state`

Returns all game data including squares, players, scores, and settings.

**Response:**
- `squares`: 2D array of square assignments (player initials)
- `players`: Object with player data (name, tokens, bets)
- `teams`: Left and right team names
- `scores`: Current team scores
- `sport`: Current sport setting
- `current_multiplier`: Active betting multiplier
- `session`: Current session role and player (null when signed out)

---

### Reset Game
**POST** `/api/reset`

Clears all game data and returns to initial state. Players, scores, and squares are reset.

**Request Body:** None

**Response:**
```json
{"success": true}
```

---

### Update Team Scores
**POST** `/api/scores`

Updates the current game scores for both teams.

**Request Body:**
```json
{
  "left": 7,
  "right": 3
}
```

**Response:**
```json
{
  "success": true,
  "scores": {"left": 7, "right": 3}
}
```

---

### Get Game Winner
**GET** `/api/winner`

Calculates and returns the current winner(s) based on closest square to final score.

**Response (if winner exists):**
```json
{
  "winner": [
    {
      "player": "JD",
      "player_name": "John Doe",
      "square": {"row": 7, "col": 3},
      "distance": 0,
      "winning_team": "left",
      "path": []
    }
  ]
}
```

**Response (no winner):**
```json
{"winner": null}
```

---

### Get Player Standings
**GET** `/api/standings`

Returns all players ranked by winnings and bet status.

**Response:**
```json
{
  "standings": [
    {
      "player_initial": "JD",
      "player_name": "John Doe",
      "tokens": 10,
      "bets": 30,
      "squares": 5,
      "status": "active"
    }
  ]
}
```

---

### Update Square Assignment
**POST** `/api/squares`

Claims or removes a square using the current game multiplier. PLAYER mode can only
assign its own initial to an empty/owned square or remove its own assignment.
Use an empty `value` to remove a token. `expected_value` optionally checks for concurrent edits.

**Request Body:**
```json
{"row": 7, "col": 3, "value": "A", "expected_value": ""}
```

**Response:**
```json
{"success": true, "updated_players": {"A": 38}}
```

---

### Add Player
**POST** `/api/players`

Creates a new player and assigns a slot (ADMIN only). PLAYER registration uses `/api/login`.

**Request Body:**
```json
{"initial": "A", "name": "ALICE"}
```

**Response:**
```json
{"success": true, "playerIndex": 0}
```

---

### Delete Player
**DELETE** `/api/players/<initial>`

Removes a player and clears their squares from the board.

**URL Parameters:**
- `initial` - Player's initials (e.g., "JD")

**Response:**
```json
{
  "success": true,
  "message": "Player removed"
}
```

---

### Update Team Names
**POST** `/api/teams`

Sets or updates team names.

**Request Body:**
```json
{
  "left": "Away Team",
  "right": "Home Team"
}
```

**Response:**
```json
{
  "success": true,
  "teams": {"left": "Away Team", "right": "Home Team"}
}
```

---

### Change Sport
**POST** `/api/sport`

Switches the game to a different sport, which resets the board and updates scoring rules.

**Request Body:**
```json
{
  "sport": "nfl"
}
```

**Supported Sports:**
- `nfl` - National Football League
- `nhl` - National Hockey League
- `nba` - National Basketball Association
- `mlb` - Major League Baseball
- `olym` - Olympics
- `fifa` - FIFA World Cup

**Response:**
```json
{
  "success": true,
  "sport": "nfl",
  "max_score": 70,
  "multipliers": [1, 2, 4, 8]
}
```

---

### Update Multiplier
**POST** `/api/multiplier`

Changes the active multiplier used for new square claims.

**Request Body:**
```json
{
  "multiplier": 2
}
```

**Response:**
```json
{
  "success": true,
  "multiplier": 2
}
```

---

## Error Responses

All errors return standard format with HTTP status codes.

**400 Bad Request:**
```json
{"error": "Invalid request data"}
```

**404 Not Found:**
```json
{"error": "Player not found"}
```

**500 Server Error:**
```json
{"error": "Internal server error"}
```

---

## Data Model

### Player Object
```json
{
  "name": "John Doe",
  "playerIndex": 0,
  "tokens": 40,
  "bets": 5,
  "squares": 1
}
```

### Square
Identified by `[row][col]` coordinates. Row = left team score axis, Col = right team score axis.

### Multiplier
Increases bet value on a square. Available multipliers depend on sport (1x, 2x, 4x, 8x typically).

---

## State Persistence
All changes are automatically saved to `game_state.db`. Game state persists between server restarts.

Player self-registration requires both teams to be selected by ADMIN first.
