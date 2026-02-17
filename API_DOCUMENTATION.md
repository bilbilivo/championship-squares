# API Documentation

## Overview
Championship Squares is controlled via REST API endpoints. All API endpoints return JSON responses.

---

## Base URL
```
http://localhost:8080
```

---

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
- `available_indices`: Available player slots

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

Claims or updates a square with a player and multiplier.

**Request Body:**
```json
{
  "row": 7,
  "col": 3,
  "player": "JD",
  "multiplier": 2
}
```

**Response:**
```json
{
  "success": true,
  "square": {"row": 7, "col": 3, "player": "JD", "multiplier": 2},
  "player": {"tokens": 8, "bets": 32}
}
```

---

### Add Player
**POST** `/api/players`

Creates a new player and assigns them a slot.

**Request Body:**
```json
{
  "name": "John Doe"
}
```

**Response:**
```json
{
  "success": true,
  "player": {
    "initial": "JD",
    "name": "John Doe",
    "playerIndex": 0,
    "tokens": 40,
    "bets": 0
  }
}
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
