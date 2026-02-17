#!/usr/bin/env python3
"""
Test setup script for Championship Squares.
Creates a fully loaded game with multiple players and random bets.

Usage:
  python test_setup.py              # defaults to NFL
  python test_setup.py nfl          # NFL game (12 players)
  python test_setup.py nhl          # NHL game (8 players)
  python test_setup.py mlb          # MLB game (10 players)
  python test_setup.py olym         # Olympics game (8 players)

Each player gets a sport-specific token allocation distributed across multiplier tiers.
"""

import requests
import random
import string
import sys
import time
from config import config

BASE_URL = "http://localhost:8080"

# Sport-specific configuration
SPORT_CONFIG = {
    'nfl': {
        'players': 12,
        'max_score': 70,
        'multipliers': [1, 2, 4, 8],
        'tokens_per_player': 40,
        'bet_distribution': [26, 1, 1, 1],  # squares at each multiplier level
    },
    'nhl': {
        'players': 8,
        'max_score': 12,
        'multipliers': [1, 2, 4],
        'tokens_per_player': 12,
        'bet_distribution': [6, 3, 2],  # 6@1x(6) + 3@2x(6) + 2@4x(8) = 20 tokens
    },
    'mlb': {
        'players': 10,
        'max_score': 30,
        'multipliers': [1, 2, 4, 8],
        'tokens_per_player': 16,
        'bet_distribution': [8, 2, 1, 0],  # 8@1x(8) + 2@2x(4) + 1@4x(4) = 16 tokens
    },
    'olym': {
        'players': 8,
        'max_score': 12,
        'multipliers': [1, 2, 4],
        'tokens_per_player': 12,
        'bet_distribution': [6, 3, 2],  # 6@1x(6) + 3@2x(6) + 2@4x(8) = 20 tokens
    }
}

# Team codes by sport
TEAMS = {
    'nfl': [
        "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
        "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
        "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO", "NYG",
        "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"
    ],
    'nhl': [
        "ANA", "BOS", "BUF", "CAR", "CHI", "COL", "DAL", "DET",
        "EDM", "FLA", "LAK", "MIN", "MTL", "NJ", "NYI", "NYR",
        "OTT", "PHI", "PIT", "SJ", "STL", "TB", "TOR", "VAN",
        "VGK", "WAS", "WPG"
    ],
    'mlb': [
        "ARI", "ATL", "BAL", "BOS", "CHC", "CIN", "CLE", "COL",
        "DET", "HOU", "KC", "LAA", "LAD", "MIA", "MIL", "MIN",
        "NYM", "NYY", "OAK", "PHI", "PIT", "SD", "SF", "SEA",
        "STL", "TB", "TEX", "TOR", "WSH"
    ],
    'olym': [
        "CAN", "CHE", "CZE", "FIN", "FRA", "GER", "JPN", "LAT",
        "NOR", "RUS", "SWE", "USA", "AUT", "BEL", "CRO", "DEN",
        "EST", "GBR", "ITA", "KOR", "NED", "POL", "ROU", "SVK",
        "SVN", "THA", "UKR"
    ]
}

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
        # Small delay to ensure frontend theme updates
        time.sleep(0.5)
    else:
        print(f"  Failed to set sport: {response.text}")
        return False
    return True


def set_teams(sport="nfl"):
    """Set two random teams based on sport."""
    teams = random.sample(TEAMS[sport], 2)
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


def set_final_scores(sport="nfl"):
    """Set non-equal final scores with bias toward lower scores."""
    sport_cfg = SPORT_CONFIG.get(sport, SPORT_CONFIG['nfl'])
    max_score = sport_cfg['max_score']
    
    # Define typical score ranges by sport
    score_ranges = {
        'nfl': (17, 35),      # Typical NFL scores
        'nhl': (2, 6),        # Typical hockey scores
        'mlb': (3, 8),        # Typical baseball scores
        'olym': (2, 6),       # Olympic hockey scores
    }
    
    min_score, max_typical = score_ranges.get(sport, (3, max_score // 3))
    
    # Generate two different scores within typical range
    left_score = random.randint(min_score, max_typical)
    right_score = random.randint(min_score, max_typical)
    
    # Ensure scores are different
    while right_score == left_score:
        right_score = random.randint(min_score, max_typical)
    
    print(f"Setting final scores: {left_score} - {right_score}...")
    response = requests.post(f"{BASE_URL}/api/scores", json={
        "left": left_score,
        "right": right_score
    })
    
    if response.status_code == 200:
        print(f"  Final scores set: {left_score} (away) - {right_score} (home)")
        return left_score, right_score
    else:
        print(f"  Failed to set scores: {response.text}")
        return None, None


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


def place_bets_for_players(players, sport="nfl"):
    """Place bets for all players based on sport configuration.
    Uses incremental score ranges - starts with lower scores and gradually expands."""
    print("Placing bets for all players...")
    
    # Get sport config
    sport_cfg = SPORT_CONFIG.get(sport, SPORT_CONFIG['nfl'])
    max_score = sport_cfg['max_score']
    multipliers = sport_cfg['multipliers']
    bet_distribution = sport_cfg['bet_distribution']
    
    # Calculate total squares that will be filled
    total_squares_per_player = sum(bet_distribution)
    total_squares_to_fill = len(players) * total_squares_per_player
    
    # Generate squares with incremental score range preference
    # Start with a small range and gradually expand as we place more bets
    all_squares = []
    
    # Define initial range (lower scores are more common in real games)
    initial_range = min(max_score // 3, 10)  # Start with roughly 1/3 of max or 10
    
    # Generate squares in expanding circles from lower scores
    for expansion_factor in range(1, 20):  # Multiple passes with expanding ranges
        current_max = min(initial_range * expansion_factor, max_score)
        
        # Add squares within current range that haven't been added yet
        for r in range(current_max + 1):
            for c in range(current_max + 1):
                if (r, c) not in all_squares:
                    all_squares.append((r, c))
        
        # Stop when we have enough squares
        if len(all_squares) >= total_squares_to_fill + 50:  # Add buffer
            break
    
    # Shuffle to randomize within the biased distribution
    random.shuffle(all_squares)
    
    square_index = 0

    for player_id in players:
        print(f"  Placing bets for player {player_id}...")
        bet_counts = [0] * len(multipliers)  # Track bets at each multiplier level
        
        # Place bets according to distribution
        for multiplier_idx, (multiplier, num_squares) in enumerate(zip(multipliers, bet_distribution)):
            if not set_multiplier(multiplier):
                print(f"    ERROR: Failed to set {multiplier}x multiplier")
                continue
            
            for _ in range(num_squares):
                if square_index < len(all_squares):
                    row, col = all_squares[square_index]
                    if place_bet(player_id, row, col):
                        square_index += 1
                        bet_counts[multiplier_idx] += 1
                    else:
                        print(f"    Failed to place {multiplier}x bet at ({row}, {col})")

        # Print summary for this player
        bet_summary_parts = [f"{bet_counts[i]}@{multipliers[i]}x({bet_counts[i] * multipliers[i]})" 
                            for i in range(len(multipliers))]
        total_tokens = sum(bet_counts[i] * multipliers[i] for i in range(len(multipliers)))
        total_squares = sum(bet_counts)
        print(f"    {player_id}: {' + '.join(bet_summary_parts)} = {total_squares} squares ({total_tokens} tokens)")

    print(f"  Total squares filled: {square_index}")
    print(f"  Score range bias: Lower scores preferred (incremental expansion used)")


def main(sport="nfl"):
    """Run the full test setup for the specified sport."""
    # Validate sport
    if sport not in SPORT_CONFIG:
        print(f"ERROR: Unknown sport '{sport}'")
        print(f"Available sports: {', '.join(SPORT_CONFIG.keys())}")
        sys.exit(1)
    
    sport_cfg = SPORT_CONFIG[sport]
    
    print("=" * 50)
    print(f"Championship Squares - Test Setup ({sport.upper()})")
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

    # Step 1: Set sport first (ensures correct grid size)
    if not set_sport(sport):
        return

    # Step 2: Reset game (now with correct sport config)
    if not reset_game():
        return

    # Step 3: Set random teams
    if not set_teams(sport):
        return

    # Step 4: Add players (sport-specific count)
    players = add_players(sport_cfg['players'])
    if len(players) < sport_cfg['players']:
        print(f"Warning: Only added {len(players)} players")

    # Step 5: Place bets
    place_bets_for_players(players, sport)

    # Step 6: Set final scores (non-equal, biased toward lower scores)
    print()
    left_score, right_score = set_final_scores(sport)

    # Calculate totals
    total_squares = sum(sport_cfg['bet_distribution'])
    total_tokens_per_player = sum(sport_cfg['bet_distribution'][i] * sport_cfg['multipliers'][i] 
                                  for i in range(len(sport_cfg['multipliers'])))

    print()
    print("=" * 50)
    print("Test setup complete!")
    print(f"  - Sport: {sport.upper()}")
    print(f"  - Players: {len(players)}")
    print(f"  - Squares per player: {total_squares}")
    print(f"  - Tokens per player: {total_tokens_per_player}")
    print(f"  - Total bets: {len(players) * total_squares} squares ({len(players) * total_tokens_per_player} tokens)")
    if left_score and right_score:
        print(f"  - Final score: {left_score} - {right_score}")
    print("=" * 50)


if __name__ == "__main__":
    sport = sys.argv[1].lower() if len(sys.argv) > 1 else "nfl"
    main(sport)
