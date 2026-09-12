"""
API endpoint tests using Flask test client.

Covers all routes: reset, scores, state, winner, standings, squares,
players, teams, sport, multiplier.
"""

import json
import pytest


def post_json(client, url, data):
    """Helper to POST JSON and return parsed response + status."""
    resp = client.post(url, data=json.dumps(data), content_type="application/json")
    return resp.get_json(), resp.status_code


def add_player(client, initial="A", name="ALICE"):
    """Helper to add a player."""
    return post_json(client, "/api/players", {"initial": initial, "name": name})


# ---------------------------------------------------------------------------
# /api/reset
# ---------------------------------------------------------------------------
class TestResetEndpoint:
    def test_reset_returns_success(self, client):
        data, status = post_json(client, "/api/reset", {})
        assert status == 200
        assert data["success"] is True

    def test_reset_clears_players(self, client):
        add_player(client)
        post_json(client, "/api/reset", {})
        state = client.get("/api/state").get_json()
        assert state["players"] == {}

    def test_reset_clears_scores(self, client):
        post_json(client, "/api/scores", {"left": 14, "right": 7})
        post_json(client, "/api/reset", {})
        state = client.get("/api/state").get_json()
        assert state["scores"] == {"left": 0, "right": 0}


# ---------------------------------------------------------------------------
# /api/scores
# ---------------------------------------------------------------------------
class TestScoresEndpoint:
    def test_update_scores(self, client):
        data, status = post_json(client, "/api/scores", {"left": 21, "right": 17})
        assert status == 200
        assert data["success"] is True

    def test_scores_persist_in_state(self, client):
        post_json(client, "/api/scores", {"left": 21, "right": 17})
        state = client.get("/api/state").get_json()
        assert state["scores"]["left"] == 21
        assert state["scores"]["right"] == 17

    def test_reject_non_integer_scores(self, client):
        data, status = post_json(client, "/api/scores", {"left": "abc", "right": 3})
        assert status == 400

    def test_reject_negative_scores(self, client):
        data, status = post_json(client, "/api/scores", {"left": -1, "right": 3})
        assert status == 400

    def test_reject_scores_above_max(self, client):
        data, status = post_json(client, "/api/scores", {"left": 999, "right": 3})
        assert status == 400

    def test_accept_zero_scores(self, client):
        data, status = post_json(client, "/api/scores", {"left": 0, "right": 0})
        assert status == 200

    def test_accept_max_score(self, client):
        from config import config
        max_s = config.config["max_score"]
        data, status = post_json(client, "/api/scores", {"left": max_s, "right": max_s})
        assert status == 200


# ---------------------------------------------------------------------------
# /api/state
# ---------------------------------------------------------------------------
class TestStateEndpoint:
    def test_state_returns_all_fields(self, client):
        state = client.get("/api/state").get_json()
        for key in ("squares", "players", "teams", "scores", "sport",
                     "max_score", "current_multiplier", "available_multipliers",
                     "multiplier_labels", "tokens_per_player", "celebration", "winner"):
            assert key in state, f"Missing key: {key}"

    def test_state_default_sport_is_nfl(self, client):
        state = client.get("/api/state").get_json()
        assert state["sport"] == "nfl"
        assert state["max_score"] == 70


# ---------------------------------------------------------------------------
# /api/players
# ---------------------------------------------------------------------------
class TestPlayersEndpoint:
    def test_add_player(self, client):
        data, status = add_player(client, "A", "ALICE")
        assert status == 200
        assert data["success"] is True
        assert "playerIndex" in data

    def test_add_player_appears_in_state(self, client):
        add_player(client, "A", "ALICE")
        state = client.get("/api/state").get_json()
        assert "A" in state["players"]
        assert state["players"]["A"]["name"] == "ALICE"

    def test_reject_duplicate_initial(self, client):
        add_player(client, "A", "ALICE")
        data, status = add_player(client, "A", "AARON")
        assert status == 400

    def test_reject_empty_initial(self, client):
        data, status = post_json(client, "/api/players", {"initial": "", "name": "TEST"})
        assert status == 400

    def test_reject_empty_name(self, client):
        data, status = post_json(client, "/api/players", {"initial": "A", "name": ""})
        assert status == 400

    def test_reject_multi_char_initial(self, client):
        data, status = post_json(client, "/api/players", {"initial": "AB", "name": "TEST"})
        assert status == 400

    def test_reject_numeric_initial(self, client):
        data, status = post_json(client, "/api/players", {"initial": "1", "name": "TEST"})
        assert status == 400

    def test_reject_name_too_long(self, client):
        data, status = post_json(client, "/api/players", {"initial": "A", "name": "LONGERNAME"})
        assert status == 400

    def test_accept_name_exactly_8_chars(self, client):
        data, status = post_json(client, "/api/players", {"initial": "A", "name": "ABCDEFGH"})
        assert status == 200

    def test_initial_lowercased_gets_uppercased(self, client):
        data, status = post_json(client, "/api/players", {"initial": "a", "name": "ALICE"})
        assert status == 200
        state = client.get("/api/state").get_json()
        assert "A" in state["players"]

    def test_player_gets_full_tokens(self, client):
        from config import config
        expected_tokens = config.total_tokens.get("nfl", 40)
        add_player(client, "A", "ALICE")
        state = client.get("/api/state").get_json()
        assert state["players"]["A"]["tokens"] == expected_tokens

    def test_max_players_enforced(self, client):
        from config import config
        max_p = config.config["max_players"]
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for i in range(max_p):
            add_player(client, letters[i], f"P{i}")
        data, status = add_player(client, letters[max_p], "EXTRA")
        assert status == 400

    def test_delete_player(self, client):
        add_player(client, "A", "ALICE")
        resp = client.delete("/api/players/A")
        assert resp.status_code == 200
        state = client.get("/api/state").get_json()
        assert "A" not in state["players"]

    def test_delete_nonexistent_player(self, client):
        resp = client.delete("/api/players/Z")
        assert resp.status_code == 404

    def test_delete_player_clears_squares(self, client):
        add_player(client, "A", "ALICE")
        # Place a square
        post_json(client, "/api/squares", {"row": 5, "col": 3, "value": "A"})
        # Delete player
        client.delete("/api/players/A")
        state = client.get("/api/state").get_json()
        assert state["squares"][5][3] == ""

    def test_delete_frees_index_for_reuse(self, client):
        add_player(client, "A", "ALICE")
        client.delete("/api/players/A")
        # Should be able to add another player
        data, status = add_player(client, "B", "BOB")
        assert status == 200


# ---------------------------------------------------------------------------
# /api/squares
# ---------------------------------------------------------------------------
class TestSquaresEndpoint:
    def test_claim_square(self, client):
        add_player(client, "A", "ALICE")
        data, status = post_json(client, "/api/squares", {"row": 5, "col": 3, "value": "A"})
        assert status == 200
        assert data["success"] is True

    def test_claim_deducts_tokens(self, client):
        add_player(client, "A", "ALICE")
        post_json(client, "/api/squares", {"row": 5, "col": 3, "value": "A"})
        state = client.get("/api/state").get_json()
        from config import config
        expected = config.total_tokens.get("nfl", 40) - 1  # 1x multiplier
        assert state["players"]["A"]["tokens"] == expected

    def test_claim_with_multiplier(self, client):
        add_player(client, "A", "ALICE")
        # Set multiplier to 4x
        post_json(client, "/api/multiplier", {"multiplier": 4})
        post_json(client, "/api/squares", {"row": 5, "col": 3, "value": "A"})
        state = client.get("/api/state").get_json()
        from config import config
        expected = config.total_tokens.get("nfl", 40) - 4
        assert state["players"]["A"]["tokens"] == expected

    def test_clear_square_refunds_tokens(self, client):
        from config import config
        full_tokens = config.total_tokens.get("nfl", 40)
        add_player(client, "A", "ALICE")
        post_json(client, "/api/squares", {"row": 5, "col": 3, "value": "A"})
        # Clear the square
        post_json(client, "/api/squares", {"row": 5, "col": 3, "value": ""})
        state = client.get("/api/state").get_json()
        assert state["players"]["A"]["tokens"] == full_tokens

    def test_reject_insufficient_tokens(self, client):
        add_player(client, "A", "ALICE")
        # Set 8x multiplier, fill squares until tokens run out
        post_json(client, "/api/multiplier", {"multiplier": 8})
        from config import config
        full_tokens = config.total_tokens.get("nfl", 40)
        placed = 0
        for r in range(10):
            for c in range(10):
                if placed * 8 >= full_tokens:
                    break
                post_json(client, "/api/squares", {"row": r, "col": c, "value": "A"})
                placed += 1
        # Next one should fail
        data, status = post_json(client, "/api/squares", {"row": 20, "col": 20, "value": "A"})
        assert status == 400
        assert "not have enough tokens" in data["error"]

    def test_reject_out_of_bounds(self, client):
        add_player(client, "A", "ALICE")
        data, status = post_json(client, "/api/squares", {"row": -1, "col": 0, "value": "A"})
        assert status == 400


# ---------------------------------------------------------------------------
# /api/teams
# ---------------------------------------------------------------------------
class TestTeamsEndpoint:
    def test_set_teams(self, client):
        data, status = post_json(client, "/api/teams", {"left": "KC", "right": "SF"})
        assert status == 200

    def test_teams_persist(self, client):
        post_json(client, "/api/teams", {"left": "KC", "right": "SF"})
        state = client.get("/api/state").get_json()
        assert state["teams"] == {"left": "KC", "right": "SF"}


# ---------------------------------------------------------------------------
# /api/sport
# ---------------------------------------------------------------------------
class TestSportEndpoint:
    def test_switch_to_nhl(self, client):
        data, status = post_json(client, "/api/sport", {"sport": "nhl"})
        assert status == 200
        assert data["max_score"] == 12

    def test_invalid_sport_rejected(self, client):
        data, status = post_json(client, "/api/sport", {"sport": "curling"})
        assert status == 400

    def test_sport_switch_clears_grid(self, client):
        add_player(client, "A", "ALICE")
        post_json(client, "/api/squares", {"row": 5, "col": 3, "value": "A"})
        post_json(client, "/api/sport", {"sport": "nhl"})
        state = client.get("/api/state").get_json()
        # Grid should be 13x13 (max_score 12) and empty
        assert len(state["squares"]) == 13
        assert all(cell == "" for row in state["squares"] for cell in row)

    def test_sport_switch_resets_tokens(self, client):
        from config import config
        add_player(client, "A", "ALICE")
        post_json(client, "/api/squares", {"row": 5, "col": 3, "value": "A"})
        post_json(client, "/api/sport", {"sport": "nhl"})
        state = client.get("/api/state").get_json()
        expected_tokens = config.total_tokens.get("nhl", 12)
        assert state["players"]["A"]["tokens"] == expected_tokens
        assert state["players"]["A"]["bets"] == 0

    def test_all_valid_sports_accepted(self, client):
        for sport in ("nfl", "nhl", "nba", "mlb", "olym", "fifa"):
            data, status = post_json(client, "/api/sport", {"sport": sport})
            assert status == 200, f"Sport {sport} rejected"


# ---------------------------------------------------------------------------
# /api/multiplier
# ---------------------------------------------------------------------------
class TestMultiplierEndpoint:
    def test_set_valid_multiplier(self, client):
        data, status = post_json(client, "/api/multiplier", {"multiplier": 4})
        assert status == 200
        assert data["current_multiplier"] == 4

    def test_reject_invalid_multiplier(self, client):
        data, status = post_json(client, "/api/multiplier", {"multiplier": 16})
        assert status == 400

    def test_multiplier_persists_in_state(self, client):
        post_json(client, "/api/multiplier", {"multiplier": 2})
        state = client.get("/api/state").get_json()
        assert state["current_multiplier"] == 2


# ---------------------------------------------------------------------------
# /api/winner
# ---------------------------------------------------------------------------
class TestWinnerEndpoint:
    def test_no_winner_on_tie(self, client):
        post_json(client, "/api/scores", {"left": 3, "right": 3})
        data = client.get("/api/winner").get_json()
        assert data["winner"] is None

    def test_no_winner_empty_board(self, client):
        post_json(client, "/api/scores", {"left": 7, "right": 3})
        data = client.get("/api/winner").get_json()
        assert data["winner"] is None

    def test_winner_returned(self, client):
        # Switch to NHL for a smaller grid
        post_json(client, "/api/sport", {"sport": "nhl"})
        add_player(client, "A", "ALICE")
        post_json(client, "/api/squares", {"row": 5, "col": 3, "value": "A"})
        post_json(client, "/api/scores", {"left": 5, "right": 3})
        data = client.get("/api/winner").get_json()
        assert data["winner"] is not None
        assert data["winner"][0]["player"] == "A"


# ---------------------------------------------------------------------------
# /api/standings
# ---------------------------------------------------------------------------
class TestStandingsEndpoint:
    def test_standings_on_tie_returns_error(self, client):
        post_json(client, "/api/scores", {"left": 3, "right": 3})
        data = client.get("/api/standings").get_json()
        assert data["success"] is False

    def test_standings_ranked_by_distance(self, client):
        post_json(client, "/api/sport", {"sport": "nhl"})
        add_player(client, "A", "ALICE")
        add_player(client, "B", "BOB")
        # A is closer
        post_json(client, "/api/squares", {"row": 6, "col": 3, "value": "A"})  # dist 1
        post_json(client, "/api/squares", {"row": 8, "col": 1, "value": "B"})  # dist 5
        post_json(client, "/api/scores", {"left": 5, "right": 3})
        data = client.get("/api/standings").get_json()
        assert data["success"] is True
        assert len(data["standings"]) >= 2
        assert data["standings"][0]["player"] == "A"
        assert data["standings"][0]["distance"] < data["standings"][1]["distance"]


# ---------------------------------------------------------------------------
# /api/end-game
# ---------------------------------------------------------------------------
class TestEndGameEndpoint:
    def setup_final_game(self, client):
        post_json(client, "/api/teams", {"left": "BUF", "right": "KC"})
        add_player(client, "A", "ALICE")
        post_json(client, "/api/squares", {"row": 3, "col": 1, "value": "A"})
        post_json(client, "/api/scores", {"left": 3, "right": 1})

    def test_tied_game_is_rejected_without_event(self, client):
        response = client.post("/api/end-game")
        assert response.status_code == 400
        assert response.get_json() == {"success": False, "error": "Game is tied"}
        assert client.get("/api/state").get_json()["celebration"] is None

    def test_game_without_eligible_standings_is_rejected(self, client):
        post_json(client, "/api/scores", {"left": 3, "right": 1})
        response = client.post("/api/end-game")
        assert response.status_code == 400
        assert response.get_json()["success"] is False
        assert client.get("/api/state").get_json()["celebration"] is None

    def test_success_returns_and_exposes_final_snapshot(self, client):
        self.setup_final_game(client)
        response = client.post("/api/end-game")
        assert response.status_code == 200
        celebration = response.get_json()["celebration"]
        assert celebration["id"]
        assert celebration["teams"] == {"left": "BUF", "right": "KC"}
        assert celebration["scores"] == {"left": 3, "right": 1}
        assert celebration["winning_team"] == "left"
        assert celebration["standings"][0]["player_name"] == "ALICE"
        assert client.get("/api/state").get_json()["celebration"] == celebration

    def test_snapshot_is_unchanged_by_later_game_edits(self, client):
        self.setup_final_game(client)
        celebration = client.post("/api/end-game").get_json()["celebration"]
        post_json(client, "/api/scores", {"left": 4, "right": 2})
        post_json(client, "/api/teams", {"left": "MIA", "right": "NYJ"})
        assert client.get("/api/state").get_json()["celebration"] == celebration

    def test_repeated_end_game_creates_a_new_event(self, client):
        self.setup_final_game(client)
        first = client.post("/api/end-game").get_json()["celebration"]["id"]
        second = client.post("/api/end-game").get_json()["celebration"]["id"]
        assert first != second

    def test_reset_clears_event(self, client):
        self.setup_final_game(client)
        client.post("/api/end-game")
        client.post("/api/reset")
        assert client.get("/api/state").get_json()["celebration"] is None

    def test_player_cannot_end_game(self, client):
        self.setup_final_game(client)
        client.post("/api/logout")
        client.post("/api/login", json={"role": "player", "initial": "A", "name": "ALICE"})
        assert client.post("/api/end-game").status_code == 403
