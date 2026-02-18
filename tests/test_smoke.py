"""
Lightweight smoke tests.

Verifies the Flask app serves pages and static assets correctly
without needing a real browser.
"""

import pytest


class TestHomepage:
    def test_homepage_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_homepage_is_html(self, client):
        resp = client.get("/")
        assert "text/html" in resp.content_type

    def test_homepage_contains_title(self, client):
        resp = client.get("/")
        html = resp.data.decode()
        assert "championship" in html.lower() or "squares" in html.lower()


class TestStaticAssets:
    def test_game_js_served(self, client):
        resp = client.get("/static/js/game.js")
        assert resp.status_code == 200
        assert "javascript" in resp.content_type or "text" in resp.content_type

    def test_style_css_served(self, client):
        resp = client.get("/static/css/style.css")
        assert resp.status_code == 200

    def test_d3_js_served(self, client):
        resp = client.get("/static/d3.v7.min.js")
        assert resp.status_code == 200


class TestApiSmoke:
    """Quick smoke test that every API endpoint responds without 500 errors."""

    def test_state_no_500(self, client):
        resp = client.get("/api/state")
        assert resp.status_code != 500

    def test_winner_no_500(self, client):
        resp = client.get("/api/winner")
        assert resp.status_code != 500

    def test_standings_no_500(self, client):
        resp = client.get("/api/standings")
        assert resp.status_code != 500
