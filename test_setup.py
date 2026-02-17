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
Square placement biases toward lower scores using an expanding-range loop.
"""

import requests
import random
import string
import sys
import time

BASE_URL = "http://localhost:8080"

# Sport-specific configuration
# bet_distribution: number of squares at each multiplier level
# Token math: sum(bet_distribution[i] * multipliers[i]) must equal tokens_per_player
SPORT_CONFIG = {
    'nfl': {
        'players': 12,
        'max_score': 70,
        'multipliers': [1, 2, 4, 8],
        'tokens_per_player': 40,
        'bet_distribution': [26, 1, 1, 1],  # 26*1 + 1*2 + 1*4 + 1*8 = 40 tokens
    },
    'nhl': {
        'players': 8,
        'max_score': 12,
        'multipliers': [1, 2, 4],
        'tokens_per_player': 12,
        'bet_distribution': [4, 2, 1],       # 4*1 + 2*2 + 1*4 = 12 tokens
    },
    'mlb': {
        'players': 10,
        'max_score': 30,
        'multipliers': [1, 2, 4, 8],
        'tokens_per_player': 16,
        'bet_distribution': [8, 2, 1, 0],    # 8*1 + 2*2 + 1*4 + 0*8 = 16 tokens
    },
    'olym': {
        'players': 8,
        'max_score': 12,
        'multipliers': [1, 2, 4],
        'tokens_per_player': 12,
        'bet_distribution': [4, 2, 1],       # 4*1 + 2*2 + 1*4 = 12 tokens
    }
}

# Team codes by sport - MUST match the keys in static/js/game.js team objects exactly
TEAMS = {
    'nfl': [
        "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
        "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
        "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO", "NYG",
        "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"
    ],
    'nhl': [
        "ANA", "ARI", "BOS", "BUF", "CAR", "CBJ", "CGY", "CHI",
        "COL", "DAL", "DET", "EDM", "FLA", "HAR", "LAK", "MIN",
        "MNS", "MTL", "NJD", "NSH", "NYI", "NYR", "OTT", "PHI",
        "PIT", "QUE", "SEA", "SJS", "STL", "TBL", "TOR", "VAN",
        "VGK", "WPG", "WSH"
    ],
    'mlb': [
        "ARI", "ATL", "BAL", "BOS", "CHC", "CWS", "CIN", "CLE",
        "COL", "DET", "MIA", "HOU", "KC", "LAA", "LAD", "MIL",
        "MIN", "MTL", "NYM", "NYY", "OAK", "PHI", "PIT", "SD",
        "SF", "SEA", "STL", "TB", "TEX", "TOR", "WSH"
    ],
    'olym': [
        "AUT", "CAN", "CHN", "CZE", "DEN", "FIN", "FRA", "GER",
        "GBR", "HUN", "ITA", "JPN", "KAZ", "LAT", "NOR", "POL",
        "SVK", "SLO", "KOR", "SWE", "SUI", "USA"
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
    """Set non-equal final scores within typical ranges for the sport."""
    # Define typical score ranges by sport
    score_ranges = {
        'nfl': (17, 35),      # Typical NFL final scores
        'nhl': (2, 6),        # Typical hockey final scores
        'mlb': (3, 8),        # Typical baseball final scores
        'olym': (2, 6),       # Olympic hockey final scores
    }

    sport_cfg = SPORT_CONFIG.get(sport, SPORT_CONFIG['nfl'])
    max_score = sport_cfg['max_score']
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


def generate_biased_squares(max_score):
    """Generate a list of squares biased toward lower scores.
    
    Uses an expanding-range loop: iterates x from 0 to max_score.
    At each value of x, picks multiple random squares within the
    (0..x, 0..x) range. Since x starts low and grows, early squares
    cluster around low scores. As x increases the eligible area grows
    and higher scores gradually appear.
    """
    squares = []
    used = set()
    total_available = (max_score + 1) * (max_score + 1)

    # At each step x, try to place several squares within [0..x, 0..x].
    # picks scales with x so we generate enough biased squares even on small grids.
    for x in range(max_score + 1):
        picks = max(3, x + 1)
        for _ in range(picks):
            attempts = 0
            while attempts < 20:
                r = random.randint(0, x)
                c = random.randint(0, x)
                if (r, c) not in used:
                    squares.append((r, c))
                    used.add((r, c))
                    break
                attempts += 1

            if len(used) >= total_available:
                return squares

    # Fill any remaining squares in random order
    remaining = [(r, c) for r in range(max_score + 1)
                 for c in range(max_score + 1) if (r, c) not in used]
    random.shuffle(remaining)
    squares.extend(remaining)

    return squares


def place_bets_for_players(players, sport="nfl"):
    """Place bets using a draft-style round-robin: cycle through players
    at each multiplier tier, starting from the lowest."""
    print("Placing bets for all players...")

    sport_cfg = SPORT_CONFIG.get(sport, SPORT_CONFIG['nfl'])
    max_score = sport_cfg['max_score']
    multipliers = sport_cfg['multipliers']
    bet_distribution = sport_cfg['bet_distribution']

    # Generate squares biased toward lower scores
    all_squares = generate_biased_squares(max_score)

    square_index = 0
    # Track per-player bet counts at each multiplier level
    bet_counts = {pid: [0] * len(multipliers) for pid in players}

    # Outer loop: multipliers from lowest to highest
    for mult_idx, (multiplier, num_squares) in enumerate(zip(multipliers, bet_distribution)):
        if num_squares == 0:
            continue
        if not set_multiplier(multiplier):
            print(f"  ERROR: Failed to set {multiplier}x multiplier")
            continue

        print(f"  Round-robin at {multiplier}x ({num_squares} squares each)...")

        # Each player places one square per round, cycling through all players
        for round_num in range(num_squares):
            for player_id in players:
                if square_index < len(all_squares):
                    row, col = all_squares[square_index]
                    if place_bet(player_id, row, col):
                        square_index += 1
                        bet_counts[player_id][mult_idx] += 1
                    else:
                        print(f"    Failed to place {multiplier}x bet for {player_id} at ({row}, {col})")

    # Print per-player summaries
    for player_id in players:
        bet_parts = []
        for i in range(len(multipliers)):
            if bet_distribution[i] > 0:
                bet_parts.append(f"{bet_counts[player_id][i]}@{multipliers[i]}x({bet_counts[player_id][i] * multipliers[i]})")
        total_tokens = sum(bet_counts[player_id][i] * multipliers[i] for i in range(len(multipliers)))
        total_squares = sum(bet_counts[player_id])
        print(f"    {player_id}: {' + '.join(bet_parts)} = {total_squares} squares ({total_tokens} tokens)")

    print(f"  Total squares filled: {square_index}")


def main(sport="nfl"):
    """Run the full test setup for the specified sport."""
    # Validate sport
    if sport not in SPORT_CONFIG:
        print(f"ERROR: Unknown sport '{sport}'")
        print(f"Available sports: {', '.join(SPORT_CONFIG.keys())}")
        sys.exit(1)

    sport_cfg = SPORT_CONFIG[sport]

    # Verify token math before running
    token_cost = sum(sport_cfg['bet_distribution'][i] * sport_cfg['multipliers'][i]
                     for i in range(len(sport_cfg['multipliers'])))
    if token_cost > sport_cfg['tokens_per_player']:
        print(f"ERROR: bet_distribution costs {token_cost} tokens but only {sport_cfg['tokens_per_player']} available")
        sys.exit(1)

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

    # Step 1: Reset game first (clears everything, resets to NFL defaults)
    if not reset_game():
        return

    # Step 2: Set sport AFTER reset (reset hardcodes sport to nfl)
    if not set_sport(sport):
        return

    # Step 3: Set random teams (using correct sport-specific team codes)
    if not set_teams(sport):
        return

    # Step 4: Add players (sport-specific count)
    players = add_players(sport_cfg['players'])
    if len(players) < sport_cfg['players']:
        print(f"Warning: Only added {len(players)} players")

    # Step 5: Place bets (biased toward lower scores)
    place_bets_for_players(players, sport)

    # Step 6: Set final scores (non-equal, within typical range)
    print()
    left_score, right_score = set_final_scores(sport)

    # Print summary
    total_squares = sum(d for d in sport_cfg['bet_distribution'] if d > 0)
    total_tokens_per_player = sum(sport_cfg['bet_distribution'][i] * sport_cfg['multipliers'][i]
                                  for i in range(len(sport_cfg['multipliers'])))

    print()
    print("=" * 50)
    print("Test setup complete!")
    print(f"  - Sport: {sport.upper()}")
    print(f"  - Grid: {sport_cfg['max_score'] + 1}x{sport_cfg['max_score'] + 1} ({(sport_cfg['max_score'] + 1)**2} squares)")
    print(f"  - Players: {len(players)}")
    print(f"  - Squares per player: {total_squares}")
    print(f"  - Tokens per player: {total_tokens_per_player} / {sport_cfg['tokens_per_player']}")
    print(f"  - Total bets: {len(players) * total_squares} squares")
    if left_score and right_score:
        print(f"  - Final score: {left_score} - {right_score}")
    print("=" * 50)


if __name__ == "__main__":
    sport = sys.argv[1].lower() if len(sys.argv) > 1 else "nfl"
    main(sport)
