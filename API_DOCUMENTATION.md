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

Direct host and trusted LAN connections can select ADMIN or an existing player without
passwords. Cloudflare connections can only join through a player or registration link;
ADMIN login and operations are blocked even if an admin cookie is supplied.
The trusted LAN is the security boundary: anyone on it can choose ADMIN and fully
control the game. All game mutations require a session cookie and CSRF token.
Read-only game endpoints are available before login only on the trusted LAN; tunnel
clients must first redeem a valid player or registration link.

**GET `/api/csrf`** returns `{"csrf_token":"..."}` and sets the session cookie.
Send this token as `X-CSRF-Token` on every POST/DELETE request. Login/logout rotate the
session token; mutation responses return the current token in `X-CSRF-Token`.
Missing or invalid tokens and cross-origin requests return **403**.
Requests larger than 16 KiB return **413**. Verified tunnel traffic is rate-limited;
exhausted limits return **429** with a `Retry-After` header.

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

Retain cookies and the latest CSRF token for subsequent requests:

```python
import requests

http = requests.Session()
base = "http://localhost:8080"
http.headers["X-CSRF-Token"] = http.get(base + "/api/csrf").json()["csrf_token"]
response = http.post(base + "/api/login", json={"role": "admin"})
response.raise_for_status()
http.headers["X-CSRF-Token"] = response.headers["X-CSRF-Token"]
http.post(base + "/api/scores", json={"left": 7, "right": 3}).raise_for_status()
```

Missing login returns **401**; a forbidden player action or stale player identity
returns **403**. A square with a mismatched `expected_value` returns **409**.

## Endpoints

### Get Current Game State
**GET** `/api/state`

Returns all game data including squares, players, scores, and settings.
Tunnel requests without a valid PLAYER session return **401**.

Additional fields:
- `connection`: `{"public":false,"sync":"sse"}` locally or `{"public":true,"sync":"poll"}` through Cloudflare. Public clients poll every five seconds; `/api/events` returns 409 for them.
- `square_costs`: stored token costs for occupied cells, keyed by `"row,col"`, for example `{"1,0":4}`. A missing legacy purchase multiplier defaults to one. Deleting that square refunds its stored cost, regardless of the current multiplier.
- Optional `expected_cost` on POST `/api/squares` rejects a changed purchase cost with 409, alongside the existing `expected_value` owner check.

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

## Tunnel and player QR endpoints

These controls require a direct host/LAN ADMIN session:

| Endpoint | Behavior |
| --- | --- |
| GET/POST/DELETE `/api/tunnel` | Read/start/stop the temporary tunnel; returns `active` and `url`. |
| GET `/api/player-registration-qr` | Registration QR, available after teams are selected. |
| POST `/api/player-invites/<initial>` | Stable player QR; returns `url`, `svg`, `player`, and `player_name`. |
| DELETE `/api/player-invites/<initial>` | Revoke future use of that player's old link; active sessions remain valid. |

`/join/<initial>/<token>` redeems a player link and redirects to the board.
`/join/register/<token>` serves the public registration form; POST
`/api/public/register/<token>` creates and signs in a player using CSRF protection.
Deleting a player revokes their link; game reset revokes player and registration links.
Server restarts invalidate sessions and require newly displayed QR links.

Cloudflared sends the fixed origin Host `player-tunnel.invalid`; it is always treated
as public, regardless of tunnel process state. Forwarded headers never grant LAN privileges.
Bearer-link pages and API responses disable caching; link tokens are redacted from application request logs.
