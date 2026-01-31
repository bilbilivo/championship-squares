#!/usr/bin/env python3
"""
Test setup script for Championship Squares.
Creates a fully loaded NFL game with 12 players and random bets.

Each player gets:
- 26 squares at 1x multiplier (26 tokens)
- 1 square at 2x multiplier (2 tokens)
- 1 square at 4x multiplier (4 tokens)
- 1 square at 8x multiplier (8 tokens)
Total: 40 tokens per player
"""

import requests
import random
import string
import sys

BASE_URL = "http://localhost:8080"

# NFL team codes
NFL_TEAMS = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"
]

# Random player names (8 chars max)
PLAYER_NAMES = [
    "MIKE", "SARAH", "JOHN", "EMMA", "ALEX", "LISA",
    "CHRIS", "KATE", "DAVE", "AMY", "NICK", "JESS",
    "TOM", "ANNA", "STEVE", "MARY", "PAUL", "LUCY",
    "MARK", "JANE", "PETE", "ROSE", "BILL", "NINA"
]


def check_server():
    """Check if the server is running."""
    try:
        response = requests.get(f"{BASE_URL}/api/state", timeout=2)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def reset_game():
    """Reset the game state."""
    print("Resetting game...")
    try:
        response = requests.post(f"{BASE_URL}/api/reset")
        if response.status_code == 200:
            print("  Game reset successfully")
        else:
            print(f"  Failed to reset game: {response.text}")
            return False
        return True
    except requests.exceptions.ConnectionError:
        print(f"  ERROR: Cannot connect to server at {BASE_URL}")
        print(f"  Make sure the server is running: python app.py")
        return False


def set_sport(sport="nfl"):
    """Set the sport."""
    print(f"Setting sport to {sport.upper()}...")
    response = requests.post(f"{BASE_URL}/api/sport", json={"sport": sport})
    if response.status_code == 200:
        data = response.json()
        print(f"  Sport set to {sport.upper()}, max_score: {data.get('max_score')}")
    else:
        print(f"  Failed to set sport: {response.text}")
        return False
    return True


def set_teams():
    """Set two random NFL teams."""
    teams = random.sample(NFL_TEAMS, 2)
    print(f"Setting teams: {teams[0]} vs {teams[1]}...")
    response = requests.post(f"{BASE_URL}/api/teams", json={
        "left": teams[0],
        "right": teams[1]
    })
    if response.status_code == 200:
        print(f"  Teams set: {teams[0]} (away) vs {teams[1]} (home)")
    else:
        print(f"  Failed to set teams: {response.text}")
        return False
    return True


def add_players(count=12):
    """Add players with random IDs and names."""
    print(f"Adding {count} players...")

    # Get available letters for player IDs
    available_ids = list(string.ascii_uppercase)
    random.shuffle(available_ids)

    # Get random names
    names = random.sample(PLAYER_NAMES, min(count, len(PLAYER_NAMES)))
    if count > len(PLAYER_NAMES):
        names.extend(random.choices(PLAYER_NAMES, k=count - len(PLAYER_NAMES)))

    players = []
    for i in range(count):
        player_id = available_ids[i]
        player_name = names[i]

        response = requests.post(f"{BASE_URL}/api/players", json={
            "initial": player_id,
            "name": player_name
        })

        if response.status_code == 200:
            print(f"  Added player {player_id}: {player_name}")
            players.append(player_id)
        else:
            print(f"  Failed to add player {player_id}: {response.text}")

    return players


def set_multiplier(multiplier, verbose=False):
    """Set the current betting multiplier."""
    response = requests.post(f"{BASE_URL}/api/multiplier", json={
        "multiplier": multiplier
    })
    success = response.status_code == 200
    if verbose:
        if success:
            print(f"    Multiplier set to {multiplier}x")
        else:
            print(f"    Failed to set multiplier to {multiplier}x: {response.text}")
    return success


def place_bet(player_id, row, col):
    """Place a bet for a player at a specific square."""
    response = requests.post(f"{BASE_URL}/api/squares", json={
        "row": row,
        "col": col,
        "value": player_id
    })
    return response.status_code == 200


def place_bets_for_players(players, max_score=70):
    """Place bets for all players."""
    print("Placing bets for all players...")

    # Generate all possible squares
    all_squares = [(r, c) for r in range(max_score + 1) for c in range(max_score + 1)]
    random.shuffle(all_squares)

    square_index = 0

    for player_id in players:
        print(f"  Placing bets for player {player_id}...")
        bets_1x = 0
        bets_2x = 0
        bets_4x = 0
        bets_8x = 0

        # 26 squares at 1x
        if not set_multiplier(1):
            print(f"    ERROR: Failed to set 1x multiplier")
            continue
        for _ in range(26):
            if square_index < len(all_squares):
                row, col = all_squares[square_index]
                if place_bet(player_id, row, col):
                    square_index += 1
                    bets_1x += 1
                else:
                    print(f"    Failed to place 1x bet at ({row}, {col})")

        # 1 square at 2x
        if not set_multiplier(2):
            print(f"    ERROR: Failed to set 2x multiplier")
            continue
        if square_index < len(all_squares):
            row, col = all_squares[square_index]
            if place_bet(player_id, row, col):
                square_index += 1
                bets_2x += 1
            else:
                print(f"    Failed to place 2x bet at ({row}, {col})")

        # 1 square at 4x
        if not set_multiplier(4):
            print(f"    ERROR: Failed to set 4x multiplier")
            continue
        if square_index < len(all_squares):
            row, col = all_squares[square_index]
            if place_bet(player_id, row, col):
                square_index += 1
                bets_4x += 1
            else:
                print(f"    Failed to place 4x bet at ({row}, {col})")

        # 1 square at 8x
        if not set_multiplier(8):
            print(f"    ERROR: Failed to set 8x multiplier")
            continue
        if square_index < len(all_squares):
            row, col = all_squares[square_index]
            if place_bet(player_id, row, col):
                square_index += 1
                bets_8x += 1
            else:
                print(f"    Failed to place 8x bet at ({row}, {col})")

        total_tokens = bets_1x + (bets_2x * 2) + (bets_4x * 4) + (bets_8x * 8)
        total_squares = bets_1x + bets_2x + bets_4x + bets_8x
        print(f"    {player_id}: {bets_1x}@1x + {bets_2x}@2x + {bets_4x}@4x + {bets_8x}@8x = {total_squares} squares ({total_tokens} tokens)")

    print(f"  Total squares filled: {square_index}")


def main():
    """Run the full test setup."""
    print("=" * 50)
    print("Championship Squares - Test Setup")
    print("=" * 50)
    print()

    # Check server is running
    print(f"Checking server at {BASE_URL}...")
    if not check_server():
        print(f"  ERROR: Server is not running at {BASE_URL}")
        print(f"  Start it with: python app.py")
        sys.exit(1)
    print("  Server is running")
    print()

    # Step 1: Set sport to NFL first (ensures correct grid size)
    if not set_sport("nfl"):
        return

    # Step 2: Reset game (now with correct NFL config)
    if not reset_game():
        return

    # Step 3: Set random teams
    if not set_teams():
        return

    # Step 4: Add 12 players
    players = add_players(12)
    if len(players) < 12:
        print(f"Warning: Only added {len(players)} players")

    # Step 5: Place bets
    place_bets_for_players(players)

    print()
    print("=" * 50)
    print("Test setup complete!")
    print(f"  - Sport: NFL")
    print(f"  - Players: {len(players)}")
    print(f"  - Total bets: {len(players) * 29} squares ({len(players) * 40} tokens)")
    print("=" * 50)


if __name__ == "__main__":
    main()
