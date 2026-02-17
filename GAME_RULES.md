# Game Rules

## How Championship Squares Works

Championship Squares is a sports betting pool game where players pick squares on a grid to predict game outcomes based on final scores.

---

## Basic Game Mechanics

### The Grid
- A rectangular grid representing possible score combinations
- Rows = score for the left/away team
- Columns = score for the right/home team
- Players claim individual squares

### Playing
1. **Add Players** - Players join the game with a name
2. **Claim Squares** - Players select unclaimed squares on the grid
3. **Place Bets** - Each square has a multiplier (1x, 2x, 4x, etc.)
4. **Track Score** - Update team scores during the game
5. **Win** - Winner is determined by closest square to final score

### Winning Condition
- The closest square to the final score wins
- "Closest" is measured using Manhattan distance: `|row - left_score| + |col - right_score|`
- Multiple players can tie if they have equally close squares

---

## Sport-Specific Configurations

Each sport has different maximum scores and multiplier systems based on typical game scoring patterns.

### NFL (National Football League)

**Maximum Score:** 70

**Typical Multipliers:** 1x, 2x, 4x, 8x

**Multiplier Periods:**
- **1x** - During Quarter 1
- **2x** - During Quarter 2  
- **4x** - During Quarter 3
- **8x** - During Quarter 4

**Notes:** 
- Football games typically reach high scores
- Multiplier increases each quarter as stakes rise
- Higher multipliers available in later game periods

---

### NHL (National Hockey League)

**Maximum Score:** 12

**Typical Multipliers:** 1x, 2x, 4x

**Multiplier Periods:**
- **1x** - During Period 1
- **2x** - During Period 2
- **4x** - During Period 3

**Notes:**
- Hockey scores are typically low (2-6 per team)
- Three periods with 1x, 2x, 4x progression
- Smaller grid due to lower scoring

---

### NBA (National Basketball Association)

**Maximum Score:** 160

**Typical Multipliers:** 1x, 2x, 4x, 8x

**Multiplier Periods:**
- **1x** - During Quarter 1
- **2x** - During Quarter 2
- **4x** - During Quarter 3
- **8x** - During Quarter 4

**Notes:**
- Basketball games reach high scores (100+ points)
- Uses standard quarter-based multiplier system
- Largest grid due to high scoring

---

### MLB (Major League Baseball)

**Maximum Score:** 30

**Typical Multipliers:** 1x, 2x, 4x, 8x

**Multiplier Periods:**
- **1x** - Through 3rd Inning
- **2x** - Through 6th Inning
- **4x** - Through 8th Inning
- **8x** - 9th Inning

**Notes:**
- Baseball games have moderate scores (3-10 per team typical)
- Multipliers tied to inning progression
- Single game can last 3+ hours

---

### Olympics (Olympic Games)

**Maximum Score:** 12

**Typical Multipliers:** 1x, 2x, 4x

**Multiplier Periods:**
- **1x** - First half of event
- **2x** - Second half of event
- **4x** - Final period/rounds

**Notes:**
- Lower scoring typical for medal events
- Variable event types (gymnastics, track, swimming, etc.)
- Simplified 3-tier multiplier system

---

### FIFA (World Cup Soccer)

**Maximum Score:** 10

**Typical Multipliers:** 1x, 2x

**Multiplier Periods:**
- **1x** - First Half
- **2x** - Second Half

**Notes:**
- Soccer is very low-scoring (1-3 per team typical)
- Only two multiplier tiers (halves)
- Smallest grid and token allocation

---

## Token/Betting System

### Tokens
- Each player starts with a fixed number of tokens based on sport
- Tokens represent bet allocation across all squares
- When you claim a square with a multiplier, tokens are deducted

**Tokens by Sport:**
| Sport | Tokens |
|-------|--------|
| NFL | 40 |
| NHL | 12 |
| NBA | 48 |
| MLB | 16 |
| Olympics | 12 |
| FIFA | 8 |

### Cost Formula
- **Cost = Multiplier × 1**
- Example: Claiming a 4x square costs 4 tokens
- A player with 40 tokens can claim up to 10 squares at 4x each

### Remaining Tokens
- Unused tokens do not convert to prize money
- Strategy: Decide upfront which squares/multipliers to target
- Difficult to perfectly use all tokens

---

## Score Tracking

### Updating Scores
Scores must be entered as integers matching the sport's grid (0-70 for NFL, 0-12 for NHL, etc.).

### Out-of-Range Protection
If scores exceed the maximum for the sport, they are automatically capped at max score to protect game logic.

### Real-Time Updates
- Scores can be updated at any time during or after the game
- Winner calculation updates automatically
- No need to end the game; winner displays when applicable

---

## Player Management

### Adding a Player
- Enter player name
- System auto-generates initials from first/last name
- Player receives full token allocation
- Assigned a player slot (max 12 players by default)

### Removing a Player
- All squares claimed by that player are cleared
- Tokens are not returned (they were "spent" on those bets)
- Player slot becomes available for new player

### Player Status
- **Active** - Actively claimed squares
- **Inactive** - No squares claimed but still in game
- **Eliminated** - Removed from game

---

## Multiple Winners

If multiple players have squares at equal distance from final score, all tied players win (pot is split by application rules, which may vary).

Example: If final score is 21-17:
- Player A has square [21, 17] - distance 0 - **WINS**
- Player B has square [20, 17] - distance 1 - loses
- Player C has square [21, 16] - distance 1 - loses

---

## Game Reset

Resetting the game:
- Clears all players
- Clears all squares
- Resets scores to 0-0
- Preserves sport/multiplier settings
- Allows new game to start with same configuration

To start a completely fresh game, use the Reset button.

---

## Sport Selection

Switching sports during a game will:
- Clear all existing squares
- Reset scores to 0-0
- Update maximum score and grid size
- Change available multipliers
- Does NOT reset player list (players persist)

Use sport selection to run multiple games with different sports in one session.
