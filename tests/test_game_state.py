"""
Unit tests for GameState class and calculate_winner logic.
"""

import pytest
from config import config


# ---------------------------------------------------------------------------
# GameState.reset_state
# ---------------------------------------------------------------------------
class TestResetState:
    def test_default_sport_is_nfl(self, game_state):
        assert game_state.sport == "nfl"

    def test_scores_zeroed(self, game_state):
        game_state.scores = {"left": 10, "right": 5}
        game_state.reset_state()
        assert game_state.scores == {"left": 0, "right": 0}

    def test_players_cleared(self, game_state):
        game_state.players = {"A": {"name": "TEST", "playerIndex": 0, "bets": 0, "tokens": 40}}
        game_state.reset_state()
        assert game_state.players == {}

    def test_teams_cleared(self, game_state):
        game_state.teams = {"left": "KC", "right": "SF"}
        game_state.reset_state()
        assert game_state.teams == {"left": "", "right": ""}

    def test_grid_size_matches_nfl(self, game_state):
        max_score = config.max_scores["nfl"]  # 70
        assert len(game_state.squares) == max_score + 1
        assert len(game_state.squares[0]) == max_score + 1

    def test_multiplier_reset_to_one(self, game_state):
        game_state.current_multiplier = 4
        game_state.reset_state()
        assert game_state.current_multiplier == 1

    def test_available_indices_full(self, game_state):
        max_players = config.config["max_players"]
        assert game_state.available_indices == list(range(max_players))

    def test_square_multipliers_cleared(self, game_state):
        game_state.square_multipliers = {(0, 1): 2}
        game_state.reset_state()
        assert game_state.square_multipliers == {}


# ---------------------------------------------------------------------------
# GameState.get_next_player_index / release_player_index
# ---------------------------------------------------------------------------
class TestPlayerIndexManagement:
    def test_get_next_returns_zero_first(self, game_state):
        idx = game_state.get_next_player_index()
        assert idx == 0

    def test_get_next_sequential(self, game_state):
        first = game_state.get_next_player_index()
        second = game_state.get_next_player_index()
        assert first == 0
        assert second == 1

    def test_get_next_raises_when_exhausted(self, game_state):
        max_players = config.config["max_players"]
        for _ in range(max_players):
            game_state.get_next_player_index()
        with pytest.raises(Exception, match="No more player slots"):
            game_state.get_next_player_index()

    def test_release_index_makes_it_available(self, game_state):
        idx = game_state.get_next_player_index()  # pops 0
        game_state.release_player_index(idx)
        assert idx in game_state.available_indices

    def test_release_keeps_sorted(self, game_state):
        game_state.get_next_player_index()  # pops 0
        game_state.get_next_player_index()  # pops 1
        game_state.release_player_index(0)
        assert game_state.available_indices == sorted(game_state.available_indices)

    def test_release_ignores_duplicate(self, game_state):
        idx = game_state.get_next_player_index()
        game_state.release_player_index(idx)
        count_before = len(game_state.available_indices)
        game_state.release_player_index(idx)  # release again
        assert len(game_state.available_indices) == count_before

    def test_release_ignores_out_of_range(self, game_state):
        count_before = len(game_state.available_indices)
        game_state.release_player_index(999)
        assert len(game_state.available_indices) == count_before


# ---------------------------------------------------------------------------
# GameState.save_state / load_state  (round-trip)
# ---------------------------------------------------------------------------
class TestStatePersistence:
    def test_round_trip_empty_state(self, game_state):
        game_state.save_state()
        game_state.players = {"X": {"name": "GHOST"}}
        loaded = game_state.load_state()
        assert loaded is True
        assert game_state.players == {}

    def test_round_trip_with_players(self, game_state):
        game_state.players["A"] = {
            "name": "ALICE",
            "playerIndex": 0,
            "bets": 5,
            "tokens": 35,
        }
        game_state.available_indices.remove(0)
        game_state.save_state()

        # Corrupt in-memory state
        game_state.players = {}
        game_state.load_state()

        assert "A" in game_state.players
        assert game_state.players["A"]["name"] == "ALICE"
        assert game_state.players["A"]["tokens"] == 35

    def test_round_trip_with_squares(self, game_state):
        game_state.squares[3][7] = "B"
        game_state.square_multipliers[(3, 7)] = 4
        game_state.save_state()

        game_state.squares[3][7] = ""
        game_state.square_multipliers = {}
        game_state.load_state()

        assert game_state.squares[3][7] == "B"
        assert game_state.square_multipliers.get((3, 7)) == 4

    def test_round_trip_scores_and_teams(self, game_state):
        game_state.scores = {"left": 21, "right": 14}
        game_state.teams = {"left": "KC", "right": "SF"}
        game_state.save_state()

        game_state.scores = {"left": 0, "right": 0}
        game_state.load_state()

        assert game_state.scores == {"left": 21, "right": 14}
        assert game_state.teams == {"left": "KC", "right": "SF"}

    def test_round_trip_sport_change(self, game_state):
        game_state.sport = "nhl"
        config.update_sport("nhl")
        max_score = config.config["max_score"]
        game_state.squares = [['' for _ in range(max_score + 1)] for _ in range(max_score + 1)]
        game_state.save_state()

        game_state.sport = "nfl"
        game_state.load_state()

        assert game_state.sport == "nhl"

    def test_load_on_empty_db_returns_false(self, game_state):
        # No save has been made -> tables are empty
        loaded = game_state.load_state()
        assert loaded is False

    def test_load_corrupted_db_resets(self, game_state, tmp_path):
        """If the DB is corrupt, load_state should reset to defaults."""
        import database
        # Write garbage to the DB file
        database.DB_PATH.write_text("not a database")
        loaded = game_state.load_state()
        assert loaded is False
        # State should be reset to defaults
        assert game_state.sport == "nfl"

    def test_scores_clamped_on_load(self, game_state):
        """Scores exceeding max_score should be clamped on load."""
        game_state.scores = {"left": 999, "right": 500}
        game_state.save_state()

        game_state.load_state()
        max_score = config.config["max_score"]
        assert game_state.scores["left"] <= max_score
        assert game_state.scores["right"] <= max_score


# ---------------------------------------------------------------------------
# calculate_winner
# ---------------------------------------------------------------------------
class TestCalculateWinner:
    def _setup_game(self, game_state):
        """Helper: set up a minimal game state for winner tests."""
        config.update_sport("nhl")  # smaller grid for speed
        game_state.sport = "nhl"
        max_score = config.config["max_score"]
        game_state.squares = [['' for _ in range(max_score + 1)] for _ in range(max_score + 1)]
        game_state.players = {
            "A": {"name": "ALICE", "playerIndex": 0, "bets": 1, "tokens": 11},
            "B": {"name": "BOB", "playerIndex": 1, "bets": 1, "tokens": 11},
        }

    def test_tie_score_returns_none(self, game_state):
        import app as app_module
        self._setup_game(game_state)
        game_state.scores = {"left": 3, "right": 3}
        game_state.squares[4][2] = "A"  # predicts left wins
        result = app_module.calculate_winner()
        assert result is None

    def test_no_qualifying_squares_returns_none(self, game_state):
        import app as app_module
        self._setup_game(game_state)
        game_state.scores = {"left": 5, "right": 3}  # left winning
        # Place square that predicts right wins (col > row)
        game_state.squares[1][4] = "A"
        result = app_module.calculate_winner()
        assert result is None

    def test_exact_match_distance_zero(self, game_state):
        import app as app_module
        self._setup_game(game_state)
        game_state.scores = {"left": 5, "right": 3}
        game_state.squares[5][3] = "A"  # exact score, row > col -> left wins
        result = app_module.calculate_winner()
        assert result is not None
        assert len(result) == 1
        assert result[0]["player"] == "A"
        assert result[0]["distance"] == 0
        assert result[0]["winning_team"] == "left"

    def test_manhattan_distance_correct(self, game_state):
        import app as app_module
        self._setup_game(game_state)
        game_state.scores = {"left": 5, "right": 3}
        # Place at (7, 1) -> distance = |7-5| + |1-3| = 4, row > col -> predicts left
        game_state.squares[7][1] = "A"
        result = app_module.calculate_winner()
        assert result is not None
        assert result[0]["distance"] == 4

    def test_multiple_winners_at_same_distance(self, game_state):
        import app as app_module
        self._setup_game(game_state)
        game_state.scores = {"left": 5, "right": 3}
        # Two squares at distance 2, both predicting left wins
        game_state.squares[6][2] = "A"  # |6-5|+|2-3| = 2, 6>2 -> left
        game_state.squares[7][3] = "B"  # |7-5|+|3-3| = 2, 7>3 -> left
        result = app_module.calculate_winner()
        assert result is not None
        assert len(result) == 2
        players = {w["player"] for w in result}
        assert players == {"A", "B"}

    def test_closer_square_wins(self, game_state):
        import app as app_module
        self._setup_game(game_state)
        game_state.scores = {"left": 5, "right": 3}
        game_state.squares[6][2] = "A"  # distance 2, predicts left
        game_state.squares[8][1] = "B"  # distance 5, predicts left
        result = app_module.calculate_winner()
        assert len(result) == 1
        assert result[0]["player"] == "A"

    def test_right_team_winning(self, game_state):
        import app as app_module
        self._setup_game(game_state)
        game_state.scores = {"left": 2, "right": 5}  # right winning
        # Square at (1, 4) -> col > row -> predicts right wins
        game_state.squares[1][4] = "B"
        result = app_module.calculate_winner()
        assert result is not None
        assert result[0]["winning_team"] == "right"
        assert result[0]["player"] == "B"

    def test_winner_has_path(self, game_state):
        import app as app_module
        self._setup_game(game_state)
        game_state.scores = {"left": 5, "right": 3}
        game_state.squares[7][1] = "A"  # distance 4, predicts left
        result = app_module.calculate_winner()
        assert "path" in result[0]
        assert isinstance(result[0]["path"], list)

    def test_empty_board_returns_none(self, game_state):
        import app as app_module
        self._setup_game(game_state)
        game_state.scores = {"left": 5, "right": 3}
        result = app_module.calculate_winner()
        assert result is None


# ---------------------------------------------------------------------------
# Config.update_sport
# ---------------------------------------------------------------------------
class TestConfigUpdateSport:
    def test_valid_sport_updates_max_score(self):
        config.update_sport("nhl")
        assert config.config["max_score"] == 12
        config.update_sport("nfl")
        assert config.config["max_score"] == 70

    def test_invalid_sport_returns_false(self):
        result = config.update_sport("curling")
        assert result is False

    def test_all_sports_have_consistent_configs(self):
        """Every sport key should exist in all config dicts."""
        for sport in config.max_scores:
            assert sport in config.multipliers, f"{sport} missing from multipliers"
            assert sport in config.multiplier_labels, f"{sport} missing from multiplier_labels"
            assert sport in config.total_tokens, f"{sport} missing from total_tokens"
            # multiplier count should match label count
            assert len(config.multipliers[sport]) == len(config.multiplier_labels[sport]), \
                f"{sport}: multiplier/label count mismatch"
