#!/usr/bin/env python3
"""
Test setup script for Championship Squares.
Creates a fully loaded game with multiple players and random bets.

Usage:
  python generate_fake_game.py              # defaults to NFL
  python generate_fake_game.py nfl          # NFL game (8 players)
  python generate_fake_game.py nhl          # NHL game (8 players)
  python generate_fake_game.py mlb          # MLB game (8 players)
  python generate_fake_game.py olym         # Olympics game (8 players)

Logs in as ADMIN and replaces the game at CHAMPIONSHIP_SQUARES_URL (default: http://localhost:8080).
Each player gets a sport-specific token allocation distributed across multiplier tiers.
Square placement is uniformly random from 0 up to the sport's typical high score (SCORE_RANGES max).
"""

import os
import requests
import random
import string
import sys

BASE_URL = os.environ.get("CHAMPIONSHIP_SQUARES_URL", "http://localhost:8080").rstrip('/')
# Preserve the ADMIN login cookie for every read and write in this run.
http = requests.Session()

# Sport-specific configuration
# bet_distribution: number of squares at each multiplier level
# Token math: sum(bet_distribution[i] * multipliers[i]) must equal tokens_per_player
SPORT_CONFIG = {
    'nfl': {
        'players': 8,
        'max_score': 70,
        'multipliers': [1, 2, 4, 8],
        'tokens_per_player': 40,
        'bet_distribution': [12, 6, 2, 1],  # 12*1 + 6*2 + 2*4 + 1*8 = 40 tokens
    },
    'nhl': {
        'players': 8,
        'max_score': 12,
        'multipliers': [1, 2, 4],
        'tokens_per_player': 12,
        'bet_distribution': [4, 2, 1],       # 4*1 + 2*2 + 1*4 = 12 tokens
    },
    'mlb': {
        'players': 8,
        'max_score': 30,
        'multipliers': [1, 2, 4, 8],
        'tokens_per_player': 20,
        'bet_distribution': [6, 1, 1, 1],    # 6*1 + 1*2 + 1*4 + 1*8 = 20 tokens
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

# Random player names (8 chars max) — one per letter A-Z
PLAYER_NAMES = [
    "ALEX",  # A
    "BILL",  # B (requested)
    "CHRIS", # C
    "DAVE",  # D (requested)
    "ERIC",  # E (requested)
    "FRED",  # F (requested)
    "GARY",  # G
    "HANK",  # H
    "IAN",   # I
    "JAMES", # J 
    "KATE",  # K
    "LUCY",  # L
    "MARK",  # M
    "NICK",  # N
    "OLI",   # O (requested)
    "PETE",  # P (requested)
    "QUINN", # Q
    "ROSE",  # R
    "STEPH", # S (requested)
    "TOM",   # T
    "UMA",   # U
    "VERO",# V
    "WILL",  # W
    "XANDER",# X
    "YVONNE",# Y
    "ZACK"   # Z
]


def check_server():
    """Check if the server is running."""
    try:
        response = http.get(f"{BASE_URL}/api/state", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def login_admin():
    """Select ADMIN mode before any destructive setup steps."""
    print("Logging in as ADMIN...")
    try:
        bootstrap = http.get(f"{BASE_URL}/api/csrf", timeout=5)
        bootstrap.raise_for_status()
        http.headers['X-CSRF-Token'] = bootstrap.json()['csrf_token']
        response = http.post(f"{BASE_URL}/api/login", json={"role": "admin"}, timeout=5)
        if response.status_code == 200 and response.json().get('role') == 'admin':
            http.headers['X-CSRF-Token'] = response.headers['X-CSRF-Token']
            return True
        print(f"  ERROR: ADMIN login failed: {response.text}")
    except (requests.exceptions.RequestException, ValueError) as error:
        print(f"  ERROR: ADMIN login failed: {error}")
    return False


def reset_game():
    """Reset the game state."""
    print("Resetting game...")
    try:
        response = http.post(f"{BASE_URL}/api/reset")
        if response.status_code == 200:
            print("  Game reset successfully")
        else:
            print(f"  Failed to reset game: {response.text}")
            return False
        return True
    except requests.exceptions.RequestException:
        print(f"  ERROR: Cannot connect to server at {BASE_URL}")
        print(f"  Make sure the server is running: python app.py")
        return False


def set_sport(sport="nfl"):
    """Set the sport."""
    print(f"Setting sport to {sport.upper()}...")
    response = http.post(f"{BASE_URL}/api/sport", json={"sport": sport})
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
    response = http.post(f"{BASE_URL}/api/teams", json={
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
    # Use module-level SCORE_RANGES for consistency
    min_score, max_typical = SCORE_RANGES.get(sport, (3, SPORT_CONFIG.get(sport, SPORT_CONFIG['nfl'])['max_score'] // 3))

    sport_cfg = SPORT_CONFIG.get(sport, SPORT_CONFIG['nfl'])
    max_score = sport_cfg['max_score']


    # Generate two different scores within typical range
    left_score = random.randint(min_score, max_typical)
    right_score = random.randint(min_score, max_typical)

    # Ensure scores are different
    while right_score == left_score:
        right_score = random.randint(min_score, max_typical)

    print(f"Setting final scores: {left_score} - {right_score}...")
    response = http.post(f"{BASE_URL}/api/scores", json={
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
    """Add players with random IDs and names where the initial matches the name first letter."""
    print(f"Adding {count} players...")

    # Prepare shuffled unique IDs (A-Z)
    available_ids = list(string.ascii_uppercase)
    random.shuffle(available_ids)

    # Index names by their starting initial (uppercase)
    names_by_initial = {}
    for n in PLAYER_NAMES:
        initial = n[0].upper()
        names_by_initial.setdefault(initial, []).append(n)

    used_names = set()
    players = []

    for i in range(count):
        if i >= len(available_ids):
            print("  ERROR: Not enough unique initials available for requested player count")
            break
        player_id = available_ids[i]

        # Prefer an unused existing name that starts with the player's initial
        candidate_list = names_by_initial.get(player_id, [])
        player_name = None
        for cand in candidate_list:
            if cand not in used_names:
                player_name = cand
                break

        # If no existing name available for this initial, synthesize one (max 8 chars)
        if not player_name:
            suffix_len = random.randint(2, 7)
            suffix = ''.join(random.choices(string.ascii_lowercase, k=suffix_len)).upper()
            player_name = (player_id + suffix)[:8]

        response = http.post(f"{BASE_URL}/api/players", json={
            "initial": player_id,
            "name": player_name
        })

        if response.status_code == 200:
            print(f"  Added player {player_id}: {player_name}")
            players.append(player_id)
            used_names.add(player_name)
        else:
            print(f"  Failed to add player {player_id}: {response.text}")

    return players


def set_multiplier(multiplier, verbose=False):
    """Set the current betting multiplier."""
    response = http.post(f"{BASE_URL}/api/multiplier", json={
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
    response = http.post(f"{BASE_URL}/api/squares", json={
        "row": row,
        "col": col,
        "value": player_id
    })
    return response.status_code == 200






# Typical score ranges for all sports (module-level, shareable)
SCORE_RANGES = {
    'nfl': (17, 35),      # Typical NFL final scores
    'nhl': (2, 6),        # Typical hockey final scores
    'mlb': (3, 8),        # Typical baseball final scores
    'olym': (2, 6),       # Olympic hockey final scores
}

def place_bets_for_players(players, sport="nfl"):
    """Place bets using a draft-style round-robin: cycle through players
    at each multiplier tier, starting from the lowest."""
    print("Placing bets for all players...")

    sport_cfg = SPORT_CONFIG.get(sport, SPORT_CONFIG['nfl'])
    max_score = sport_cfg['max_score']
    multipliers = sport_cfg['multipliers']
    bet_distribution = sport_cfg['bet_distribution']

    # Use upper bound from SCORE_RANGES (if defined), else fall back to max_score
    _, score_max = SCORE_RANGES.get(sport, (0, max_score))
    squares_needed = sum(bet_distribution) * len(players)
    # Generate Phase 1 (realistic range) unique squares
    phase1_squares = [(r, c) for r in range(0, score_max + 1) for c in range(0, score_max + 1)]
    random.shuffle(phase1_squares)
    phase1_bucket = list(phase1_squares)
    
    # Generate Phase 2 (full grid) unique squares
    phase2_squares = [(r, c) for r in range(0, max_score + 1) for c in range(0, max_score + 1)]
    random.shuffle(phase2_squares)
    phase2_bucket = list(phase2_squares)
    
    phase1_available = len(phase1_bucket)
    phase2_available = len(phase2_bucket)
    
    # Track which squares have been claimed to avoid re-requesting them
    claimed_squares = set()
    
    # Track per-player bet counts at each multiplier level
    bet_counts = {pid: [0] * len(multipliers) for pid in players}
    phase1_bets = 0
    phase2_bets = 0

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
                # Keep retrying until this player gets their bet placed
                placed = False
                retries = 0
                max_retries = 50
                
                while not placed and retries < max_retries:
                    # Get a square: phase1 first, then phase2, then allow repeats
                    if phase1_bucket:
                        row, col = phase1_bucket.pop()
                        this_phase = 1
                    elif phase2_bucket:
                        row, col = phase2_bucket.pop()
                        this_phase = 2
                    else:
                        # All unique squares exhausted; allow repeats from full grid
                        row = random.randint(0, max_score)
                        col = random.randint(0, max_score)
                        this_phase = 3  # Phase 3 = repeats
                    
                    # Skip if already claimed (to avoid re-requesting)
                    square_key = (row, col)
                    if square_key in claimed_squares:
                        retries += 1
                        continue
                    
                    # Try to place it
                    if place_bet(player_id, row, col):
                        claimed_squares.add(square_key)
                        bet_counts[player_id][mult_idx] += 1
                        if this_phase == 1:
                            phase1_bets += 1
                        else:
                            phase2_bets += 1
                        placed = True
                    else:
                        retries += 1
                
                if not placed:
                    print(f"    ERROR: Could not place {multiplier}x bet for {player_id} after {max_retries} retries")

    # Print per-player summaries
    for player_id in players:
        bet_parts = []
        for i in range(len(multipliers)):
            if bet_distribution[i] > 0:
                bet_parts.append(f"{bet_counts[player_id][i]}@{multipliers[i]}x({bet_counts[player_id][i] * multipliers[i]})")
        total_tokens = sum(bet_counts[player_id][i] * multipliers[i] for i in range(len(multipliers)))
        total_squares = sum(bet_counts[player_id])
        print(f"    {player_id}: {' + '.join(bet_parts)} = {total_squares} squares ({total_tokens} tokens)")

    print(f"  Total squares filled: {phase1_bets + phase2_bets} (Phase1: {phase1_bets}, Phase2: {phase2_bets})")
    total_bets_expected = sum(bet_distribution) * len(players)
    if (phase1_bets + phase2_bets) < total_bets_expected:
        print(f"  WARNING: Only {phase1_bets + phase2_bets} of {total_bets_expected} bets placed!")


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

    if not login_admin():
        sys.exit(1)

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

    # Step 5: Place bets (uniform random from 0 to SCORE_RANGES max)
    place_bets_for_players(players, sport)

    # Step 6: Set final scores (non-equal, within typical range)
    print()
    left_score, right_score = set_final_scores(sport)

    # Print summary
    total_squares = sum(d for d in sport_cfg['bet_distribution'] if d > 0)
    total_tokens_per_player = sum(sport_cfg['bet_distribution'][i] * sport_cfg['multipliers'][i]
                                  for i in range(len(sport_cfg['multipliers'])))

    # Fetch teams from server for summary
    try:
        resp = http.get(f"{BASE_URL}/api/state", timeout=3)
        teams = resp.json().get('teams', {}) if resp.status_code == 200 else {}
        left_team = teams.get('left', 'AWAY') or 'AWAY'
        right_team = teams.get('right', 'HOME') or 'HOME'
    except Exception:
        left_team = 'AWAY'
        right_team = 'HOME'

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
        print(f"  - Final score: {left_team} {left_score} - {right_score} {right_team}")
    print("=" * 50)


if __name__ == "__main__":
    sport = sys.argv[1].lower() if len(sys.argv) > 1 else "nfl"
    main(sport)
