# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Stephane Belliveau
from flask import Flask, Response, jsonify, redirect, render_template, request, session, stream_with_context, url_for
from copy import deepcopy
from functools import wraps
import json
import logging
import re
import hmac
import os
import atexit
import queue
import threading
import socket
import secrets
import shutil
import subprocess
import time
import math
from ipaddress import ip_address, ip_network
from urllib.parse import quote, urlsplit, urlunsplit
import qrcode
from qrcode.image.svg import SvgPathImage
from flask.sessions import SecureCookieSessionInterface
from config import config
from database import (delete_all_player_invites, delete_player_invite, init_db, invite_key_for_player, load_game_state as db_load_state,
                      save_game_state as db_save_state,
                      save_player_invite)

# Check for lite mode from environment variable
LITE_MODE = os.environ.get('LITE_MODE', '0') == '1'

app = Flask(__name__, 
           template_folder=str(config.template_dir),
           static_folder=str(config.static_dir))
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
MAX_REQUEST_BYTES = 16 * 1024
app.config['MAX_CONTENT_LENGTH'] = MAX_REQUEST_BYTES
WAITRESS_OPTIONS = {
    'threads': 32,
    'connection_limit': 100,
    'channel_timeout': 45,
    'cleanup_interval': 15,
    'max_request_body_size': MAX_REQUEST_BYTES,
    'max_request_header_size': MAX_REQUEST_BYTES,
    'expose_tracebacks': False,
    'clear_untrusted_proxy_headers': True,
}


TUNNEL_HOST = 'player-tunnel.invalid'
LOCAL_NETWORKS = tuple(ip_network(net) for net in (
    '127.0.0.0/8', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16',
    '169.254.0.0/16', '::1/128', 'fc00::/7', 'fe80::/10',
))


class TunnelManager:
    """Own one Quick Tunnel; keep its ingress distinguishable from LAN requests."""
    def __init__(self):
        self.process = None
        self.url = None
        self.registration_token = None
        self.lock = threading.RLock()

    def active(self):
        with self.lock:
            return self.process is not None and self.process.poll() is None and bool(self.url)

    def start(self):
        with self.lock:
            if self.active():
                return self.url
            executable = shutil.which('cloudflared')
            if not executable:
                raise RuntimeError('INSTALL CLOUDFLARED FIRST')
            self.stop()
            lines = queue.Queue(maxsize=128)
            finished = threading.Event()
            try:
                process = subprocess.Popen(
                    [executable, 'tunnel', '--url', f"http://127.0.0.1:{config.config['port']}",
                     '--http-host-header', TUNNEL_HOST],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                )
                self.process = process

                def read_output():
                    try:
                        for line in process.stdout:
                            if not finished.is_set():
                                try:
                                    lines.put_nowait(line)
                                except queue.Full:
                                    pass
                    finally:
                        process.stdout.close()

                threading.Thread(target=read_output, daemon=True).start()
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline and process.poll() is None:
                    try:
                        line = lines.get(timeout=0.25)
                    except queue.Empty:
                        continue
                    for word in line.split():
                        candidate = word.rstrip('.,')
                        if re.fullmatch(r'https://[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com', candidate):
                            self.url = candidate
                            self.registration_token = secrets.token_urlsafe(24)
                            return self.url
                raise RuntimeError('TUNNEL FAILED — TRY AGAIN')
            except (OSError, RuntimeError) as error:
                self.stop()
                raise RuntimeError('TUNNEL FAILED — TRY AGAIN') from error
            finally:
                finished.set()

    def stop(self):
        with self.lock:
            process = self.process
            self.process = None
            self.url = None
            self.registration_token = None
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)


tunnel = TunnelManager()
atexit.register(tunnel.stop)


def request_hostname():
    return (urlsplit(request.host_url).hostname or '').lower().rstrip('.')


def loopback_address(value):
    try:
        address = ip_address(value)
        if getattr(address, 'ipv4_mapped', None):
            address = address.ipv4_mapped
        return address.is_loopback
    except ValueError:
        return False


def is_tunnel_request():
    # cloudflared connects over loopback and rewrites Host to this sentinel.
    # Requiring both prevents directly reachable clients from spoofing public ingress.
    return request_hostname() == TUNNEL_HOST and loopback_address(request.remote_addr or '')


def local_address(value):
    try:
        address = ip_address(value)
        if getattr(address, 'ipv4_mapped', None):
            address = address.ipv4_mapped
        return any(address in network for network in LOCAL_NETWORKS)
    except ValueError:
        return False


def is_local_request():
    host = request_hostname()
    local_names = {'localhost', socket.gethostname().lower(), socket.getfqdn().lower()}
    return (not is_tunnel_request() and local_address(request.remote_addr or '') and
            (local_address(host) or host in local_names or host == '0.0.0.0'))


def csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


class ConnectionSessionInterface(SecureCookieSessionInterface):
    def get_cookie_secure(self, app):
        return is_tunnel_request() or request.is_secure


app.session_interface = ConnectionSessionInterface()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')


class TokenBucketLimiter:
    """Small in-process limiter for the app's single-process deployment model."""
    def __init__(self):
        self._buckets = {}
        self._lock = threading.Lock()
        self._last_cleanup = 0.0

    def check(self, key, rate_per_minute, capacity):
        now = time.monotonic()
        refill_rate = rate_per_minute / 60.0
        with self._lock:
            tokens, updated = self._buckets.get(key, (float(capacity), now))
            tokens = min(float(capacity), tokens + max(0.0, now - updated) * refill_rate)
            allowed = tokens >= 1.0
            if allowed:
                tokens -= 1.0
            self._buckets[key] = (tokens, now)
            if now - self._last_cleanup >= 300:
                cutoff = now - 600
                self._buckets = {bucket_key: value for bucket_key, value in self._buckets.items()
                                 if value[1] >= cutoff}
                self._last_cleanup = now
        retry_after = 0 if allowed else max(1, math.ceil((1.0 - tokens) / refill_rate))
        return allowed, retry_after

    def clear(self):
        with self._lock:
            self._buckets.clear()
            self._last_cleanup = 0.0


rate_limiter = TokenBucketLimiter()
PUBLIC_PLAYER_READS = {'/api/state', '/api/winner', '/api/standings'}


def public_client_address():
    """Use Cloudflare's client address only on verified tunnel-origin traffic."""
    forwarded = request.headers.get('CF-Connecting-IP', '')
    try:
        return str(ip_address(forwarded))
    except ValueError:
        return request.remote_addr or 'unknown'


def valid_player_session():
    initial = session.get('player')
    return (session.get('role') == 'player' and initial in game_state.players and
            session.get('identity') == game_state.player_identities.get(initial))


def enforce_rate_limit(key, rate, capacity):
    allowed, retry_after = rate_limiter.check(key, rate, capacity)
    if allowed:
        return None
    response = jsonify(error='TOO MANY REQUESTS — TRY AGAIN')
    response.status_code = 429
    response.headers['Retry-After'] = str(retry_after)
    return response


@app.before_request
def protect_request():
    if not is_tunnel_request() and not is_local_request():
        return jsonify(error='UNTRUSTED CONNECTION'), 403
    if request.content_length is not None and request.content_length > app.config['MAX_CONTENT_LENGTH']:
        return jsonify(error='REQUEST TOO LARGE'), 413
    if is_tunnel_request():
        client = public_client_address()
        principal = session.get('identity') if valid_player_session() else client
        limited = enforce_rate_limit(('public', principal), 120, 30)
        if limited:
            return limited
        if request.path.startswith('/api/public/register/'):
            limited = enforce_rate_limit(('registration', client), 12, 4)
            if limited:
                return limited
        if request.path in PUBLIC_PLAYER_READS or request.path == '/api/squares':
            if not valid_player_session():
                return jsonify(error='PLAYER LINK REQUIRED'), 401
            limited = enforce_rate_limit(('player', session['identity']), 60, 20)
            if limited:
                return limited
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        supplied = request.headers.get('X-CSRF-Token', '')
        expected = session.get('csrf_token', '')
        if not expected or not hmac.compare_digest(supplied.encode(), expected.encode()):
            return jsonify(error='SESSION CHANGED — RETRY'), 403
        origin = request.headers.get('Origin')
        expected_origin = tunnel.url if is_tunnel_request() else request.host_url.rstrip('/')
        if origin and origin != expected_origin:
            return jsonify(error='INVALID REQUEST ORIGIN'), 403


@app.route('/api/csrf')
def csrf_bootstrap():
    return jsonify(csrf_token=csrf_token())


class RedactInviteTokens(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        record.msg = re.sub(r'(/(?:api/public/register|join/[^/\s]+|join/register)/)[^?\s"/]+',
                            r'\1[REDACTED]', message)
        record.args = ()
        return True


logging.getLogger('werkzeug').addFilter(RedactInviteTokens())


@app.context_processor
def versioned_assets():
    def asset_url(filename):
        version = os.stat(os.path.join(app.static_folder, filename)).st_mtime_ns
        return url_for('static', filename=filename, v=version)
    return {'asset_url': asset_url, 'csrf_token': csrf_token, 'public_connection': is_tunnel_request()}


class GameEventStream:
    """In-process revision broadcaster for browsers viewing the same game."""

    def __init__(self):
        self._condition = threading.Condition()
        self._revision = 0
        self._origin = None

    def snapshot(self):
        with self._condition:
            return self._revision

    def publish(self, origin=None):
        with self._condition:
            self._revision += 1
            self._origin = origin
            self._condition.notify_all()
            return self._revision

    def stream(self):
        revision = self.snapshot()
        yield self._message(revision, None)
        while True:
            with self._condition:
                changed = self._condition.wait_for(
                    lambda: self._revision != revision, timeout=20
                )
                if changed:
                    revision = self._revision
                    origin = self._origin
                    message = self._message(revision, origin)
                else:
                    message = ': keepalive\n\n'
            # A slow client must never hold the broadcaster lock while sending.
            yield message

    @staticmethod
    def _message(revision, origin):
        return f"event: game-updated\ndata: {json.dumps({'revision': revision, 'origin': origin})}\n\n"


game_events = GameEventStream()
game_state_lock = threading.RLock()


def synchronized_game(view):
    """Serialize state access and roll back rejected or failed mutations."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        with game_state_lock:
            if request.method != 'GET' and view.__name__ not in {'login', 'logout'}:
                role = session.get('role')
                if role not in {'admin', 'player'}:
                    return jsonify({'error': 'Please select ADMIN or PLAYER mode'}), 401
                if not is_local_request() and role == 'admin':
                    return jsonify({'error': 'ADMIN REQUIRES HOST OR LAN'}), 403
                if role == 'player':
                    if view.__name__ != 'update_square':
                        return jsonify({'error': 'This action requires ADMIN mode'}), 403
                    initial = session.get('player')
                    if (initial not in game_state.players or
                            session.get('identity') != game_state.player_identities.get(initial)):
                        return jsonify({'error': 'Please select your player again'}), 403
            previous = deepcopy(game_state.__dict__) if request.method != 'GET' else None
            try:
                response = app.make_response(view(*args, **kwargs))
                if response.status_code < 400:
                    previous = None
                return response
            finally:
                if previous is not None:
                    game_state.__dict__.update(previous)
                    config.update_sport(game_state.sport)
    return wrapped


def persist_game_state():
    if not game_state.save_state():
        raise RuntimeError('Failed to save game state')
    return True


def notify_game_change():
    """Tell other connected browsers to reload state after a successful save."""
    return game_events.publish(request.headers.get('X-Game-Client'))


@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'self'; form-action 'self'"
    )
    response.headers['Permissions-Policy'] = (
        'camera=(), microphone=(), geolocation=(), payment=(), usb=()'
    )
    if is_tunnel_request():
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        response.headers['X-CSRF-Token'] = csrf_token()
    if request.path.startswith(('/api/', '/join/')) or request.path == '/':
        response.headers['Cache-Control'] = 'no-store'
    return response

class GameState:
    def __init__(self):
        init_db()  # Initialize database
        self.reset_state()  # Initialize with a fresh state

    def reset_state(self):
        """Reset all game state to initial values"""
        self.sport = 'nfl'  # Default sport
        config.update_sport(self.sport)  # Sync config so grid size matches
        max_score = config.config['max_score']
        max_players = config.config['max_players']
        self.squares = [['' for _ in range(max_score + 1)] for _ in range(max_score + 1)]
        self.square_multipliers = {}  # Track multiplier used for each square {(row,col): multiplier}
        self.players = {}
        self.player_identities = {}
        self.teams = {'left': '', 'right': ''}
        self.scores = {'left': 0, 'right': 0}
        self.available_indices = list(range(max_players))
        self.current_multiplier = 1  # Default multiplier

    def save_state(self):
        """Save current game state to database"""
        state = {
            'squares': self.squares,
            'square_multipliers': self.square_multipliers,
            'players': self.players,
            'teams': self.teams,
            'scores': self.scores,
            'available_indices': self.available_indices,
            'sport': self.sport,
            'current_multiplier': self.current_multiplier
        }
        return db_save_state(state)

    def load_state(self):
        """Load game state from database"""
        try:
            state = db_load_state()
            if state:
                # Update sport first to ensure correct max_score
                self.sport = state.get('sport', 'nfl')
                config.update_sport(self.sport)  # This updates max_score in config

                # Load multiplier state
                self.current_multiplier = state.get('current_multiplier', 1)

                # Load square multipliers
                self.square_multipliers = state.get('square_multipliers', {})
                
                # Create fresh squares array with current max_score
                max_score = config.config['max_score']
                self.squares = [['' for _ in range(max_score + 1)] for _ in range(max_score + 1)]
                
                # Populate squares from loaded dictionary
                squares_dict = state.get('squares_dict', {})
                for (row, col), val in squares_dict.items():
                    if row <= max_score and col <= max_score:
                        self.squares[row][col] = val
                
                self.players = state.get('players', self.players)

                # Migrate old players to add tokens field if missing
                tokens_per_player = config.total_tokens.get(self.sport, 40)
                for player_initial in self.players:
                    if 'tokens' not in self.players[player_initial]:
                        # Calculate tokens based on current bets
                        bets = self.players[player_initial].get('bets', 0)
                        self.players[player_initial]['tokens'] = max(0, tokens_per_player - bets)

                self.teams = state.get('teams', {'left': '', 'right': ''})
                self.scores = state.get('scores', {'left': 0, 'right': 0})
                
                # Ensure scores don't exceed current max_score
                self.scores['left'] = min(self.scores['left'], max_score)
                self.scores['right'] = min(self.scores['right'], max_score)
                
                # Handle available indices safely
                max_players = config.config['max_players']
                loaded_indices = state.get('available_indices', list(range(max_players)))
                self.available_indices = [i for i in loaded_indices if i < max_players]
                
                # Add missing indices
                current_indices = set(self.available_indices)
                used_indices = {p['playerIndex'] for p in self.players.values()}
                for i in range(max_players):
                    if i not in current_indices and i not in used_indices:
                        self.available_indices.append(i)
                
                self.available_indices.sort()
                return True
            return False
        except Exception as e:
            print(f"Error loading game state: {e}")
            self.reset_state()  # Reset to fresh state on error
            return False

    def get_next_player_index(self):
        """Get next available player index"""
        if not self.available_indices:
            raise Exception('No more player slots available')
        return self.available_indices.pop(0)

    def release_player_index(self, index):
        """Release a player index back to the pool"""
        max_players = config.config['max_players']
        if index < max_players and index not in self.available_indices:
            self.available_indices.append(index)
            self.available_indices.sort()

game_state = GameState()
game_state.load_state()  # Load previous state if exists

def calculate_winner():
    """
    Calculate the current winner(s) based on the score.
    Returns list of winning players, their square locations, distances, and paths.
    Multiple players can be winners if they have the same minimum distance.
    """
    left_score = game_state.scores['left']
    right_score = game_state.scores['right']

    # Determine which team is winning/leading
    if left_score == right_score:
        # Tie - no winner yet
        return None

    winning_team = 'left' if left_score > right_score else 'right'

    # Find all occupied squares and track ALL squares at minimum distance
    min_distance = float('inf')
    winners = []  # Can have multiple winners

    for row in range(len(game_state.squares)):
        for col in range(len(game_state.squares[0])):
            square_value = game_state.squares[row][col]

            # Skip empty squares
            if not square_value:
                continue

            # Only consider squares that predict the correct winning team
            # A square predicts left wins if row > col, right wins if col > row
            square_predicts_left_wins = row > col
            square_predicts_right_wins = col > row

            if winning_team == 'left' and not square_predicts_left_wins:
                continue  # Square doesn't predict left team winning
            if winning_team == 'right' and not square_predicts_right_wins:
                continue  # Square doesn't predict right team winning

            # Calculate Manhattan distance from current score to this square
            distance = abs(row - left_score) + abs(col - right_score)

            # Update winners list
            if distance < min_distance:
                # Found a closer square - replace all previous winners
                min_distance = distance
                winners = [{
                    'player': square_value,
                    'player_name': game_state.players.get(square_value, {}).get('name', square_value),
                    'square': {'row': row, 'col': col},
                    'distance': distance,
                    'winning_team': winning_team
                }]
            elif distance == min_distance:
                # Found another square at same distance - add to winners
                winners.append({
                    'player': square_value,
                    'player_name': game_state.players.get(square_value, {}).get('name', square_value),
                    'square': {'row': row, 'col': col},
                    'distance': distance,
                    'winning_team': winning_team
                })

    # Calculate paths for each winner
    for winner_info in winners:
        path = []
        current_row = left_score
        current_col = right_score
        target_row = winner_info['square']['row']
        target_col = winner_info['square']['col']

        # Build path (excluding both the score square and the winning square)
        # Path order depends on which team is winning

        temp_row = current_row
        temp_col = current_col

        if winning_team == 'left':
            # Left team (Away) winning
            # Order: LEFT → UP → DOWN → RIGHT
            # Left = decrease col, Up = decrease row, Down = increase row, Right = increase col

            # 1. Move LEFT (decrease col - moving left on screen)
            while temp_col > target_col:
                temp_col -= 1
                if temp_row != target_row or temp_col != target_col:
                    path.append({'row': temp_row, 'col': temp_col})

            # 2. Move UP (decrease row - moving up on screen)
            while temp_row > target_row:
                temp_row -= 1
                if temp_row != target_row or temp_col != target_col:
                    path.append({'row': temp_row, 'col': temp_col})

            # 3. Move DOWN (increase row - moving down on screen)
            while temp_row < target_row:
                temp_row += 1
                if temp_row != target_row or temp_col != target_col:
                    path.append({'row': temp_row, 'col': temp_col})

            # 4. Move RIGHT (increase col - moving right on screen)
            while temp_col < target_col:
                temp_col += 1
                if temp_row != target_row or temp_col != target_col:
                    path.append({'row': temp_row, 'col': temp_col})
        else:
            # Right team (Home) winning
            # Order: UP → LEFT → RIGHT → DOWN
            # Up = decrease row, Left = decrease col, Right = increase col, Down = increase row

            # 1. Move UP (decrease row - moving up on screen)
            while temp_row > target_row:
                temp_row -= 1
                if temp_row != target_row or temp_col != target_col:
                    path.append({'row': temp_row, 'col': temp_col})

            # 2. Move LEFT (decrease col - moving left on screen)
            while temp_col > target_col:
                temp_col -= 1
                if temp_row != target_row or temp_col != target_col:
                    path.append({'row': temp_row, 'col': temp_col})

            # 3. Move RIGHT (increase col - moving right on screen)
            while temp_col < target_col:
                temp_col += 1
                if temp_row != target_row or temp_col != target_col:
                    path.append({'row': temp_row, 'col': temp_col})

            # 4. Move DOWN (increase row - moving down on screen)
            while temp_row < target_row:
                temp_row += 1
                if temp_row != target_row or temp_col != target_col:
                    path.append({'row': temp_row, 'col': temp_col})

        winner_info['path'] = path

    return winners if winners else None

@app.route('/')
def index():
    try:
        return render_template('index.html', lite_mode=LITE_MODE)
    except Exception as e:
        print(f"Error loading template: {e}")
        return "Error loading page", 500


def network_join_url():
    """Replace loopback URLs with the server's LAN address for nearby players."""
    parts = urlsplit(request.host_url)
    hostname = parts.hostname
    try:
        local_only = ip_address(hostname).is_loopback or ip_address(hostname).is_unspecified
    except ValueError:
        local_only = hostname == 'localhost' or hostname.endswith('.localhost')
    if not local_only:
        return request.host_url

    candidates = []
    try:
        # UDP connect selects an outbound interface without sending any packets.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(('8.8.8.8', 80))
            candidates.append(probe.getsockname()[0])
    except OSError:
        pass
    try:
        candidates.extend(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    for address in candidates:
        parsed = ip_address(address)
        if not parsed.is_loopback and not parsed.is_unspecified and not parsed.is_link_local:
            authority = f'{address}:{parts.port}' if parts.port else address
            return urlunsplit((parts.scheme, authority, '/', '', ''))
    raise RuntimeError('Open the game using this PC’s network IP address, then try again.')


def active_join_url():
    return tunnel.url if tunnel.active() else network_join_url()


def make_qr_response(join_url, **extra):
    code = qrcode.QRCode(box_size=8, border=4)
    code.add_data(join_url)
    code.make(fit=True)
    svg = code.make_image(image_factory=SvgPathImage).to_string().decode('utf-8')
    response = jsonify(url=join_url, svg=svg, **extra)
    response.headers['Cache-Control'] = 'no-store'
    return response


def require_local_admin():
    if session.get('role') != 'admin':
        return jsonify(error='This action requires ADMIN mode'), 403
    if not is_local_request():
        return jsonify(error='ADMIN REQUIRES HOST OR LAN'), 403
    return None


@app.route('/api/join')
def join_game():
    if is_tunnel_request():
        return jsonify(error='SCAN PLAYER QR'), 403
    if tunnel.active() and session.get('role') != 'admin':
        return jsonify(error='ADMIN REQUIRED'), 403
    try:
        join_url = active_join_url()
    except RuntimeError as error:
        return jsonify(error=str(error)), 503
    return make_qr_response(join_url, tunnel=tunnel.active())


@app.route('/api/tunnel', methods=['GET', 'POST', 'DELETE'])
def tunnel_control():
    denied = require_local_admin()
    if denied:
        return denied
    if request.method == 'POST':
        try:
            tunnel.start()
        except RuntimeError as error:
            return jsonify(error=str(error)), 503
    elif request.method == 'DELETE':
        tunnel.stop()
    return jsonify(active=tunnel.active(), url=tunnel.url)


def invite_token(initial, invite_key):
    secret = app.secret_key.encode() if isinstance(app.secret_key, str) else app.secret_key
    return hmac.new(secret, f'{initial}:{invite_key}'.encode(), 'sha256').hexdigest()


def invite_url(initial, token):
    return f'{tunnel.url.rstrip("/")}/join/{quote(initial)}/{token}'


def locked_invites(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        with tunnel.lock, game_state_lock:
            return view(*args, **kwargs)
    return wrapped


@app.route('/api/player-invites/<initial>', methods=['POST', 'DELETE'])
@locked_invites
def player_invite(initial):
    denied = require_local_admin()
    if denied:
        return denied
    if not tunnel.active():
        return jsonify(error='Turn the tunnel on before generating player QR codes'), 409
    initial = initial.upper()
    if initial not in game_state.players:
        return jsonify(error='Player not found'), 404
    if request.method == 'DELETE':
        delete_player_invite(initial)
        return jsonify(success=True)
    invite_key = invite_key_for_player(initial) or secrets.token_urlsafe(24)
    token = invite_token(initial, invite_key)
    save_player_invite(initial, invite_key, token)
    return make_qr_response(invite_url(initial, token), player=initial, player_name=game_state.players[initial]['name'])


@app.route('/api/player-registration-qr')
@locked_invites
def player_registration_qr():
    denied = require_local_admin()
    if denied:
        return denied
    if not tunnel.active():
        return jsonify(error='Turn the tunnel on before generating a registration QR code'), 409
    if not all(game_state.teams.get(side) for side in ('left', 'right')):
        return jsonify(error='Select both teams before enabling player registration'), 409
    return make_qr_response(f'{tunnel.url.rstrip("/")}/join/register/{tunnel.registration_token}')


@app.route('/join/<initial>/<token>')
@locked_invites
def redeem_player_invite(initial, token):
    initial = initial.upper()
    invite_key = invite_key_for_player(initial)
    valid = invite_key and hmac.compare_digest(token.encode(), invite_token(initial, invite_key).encode())
    if not is_tunnel_request() or not tunnel.active() or not valid or initial not in game_state.players:
        return render_template('link-expired.html'), 403
    session.clear()
    session['role'] = 'player'
    session['player'] = initial
    session['identity'] = game_state.player_identities.setdefault(initial, secrets.token_hex(16))
    return redirect('/')


@app.route('/join/register/<token>')
@locked_invites
def registration_page(token):
    if not is_tunnel_request() or (not tunnel.active() or not hmac.compare_digest(token.encode(), (tunnel.registration_token or '').encode())):
        return render_template('link-expired.html'), 403
    return render_template('register.html', token=token)


@app.route('/api/public/register/<token>', methods=['POST'])
@locked_invites
def public_register(token):
    if not is_tunnel_request() or (not tunnel.active() or not hmac.compare_digest(token.encode(), (tunnel.registration_token or '').encode())):
        return jsonify(error='This registration link is invalid or has expired.'), 403
    with game_state_lock:
        if not all(game_state.teams.get(side) for side in ('left', 'right')):
            return jsonify(error='The host has not selected both teams yet.'), 403
        data = request.get_json(silent=True) or {}
        result, status = create_player(data)
        if status != 200:
            return jsonify(error=result), status
        initial = data['initial'].strip().upper()
        invite_key = secrets.token_urlsafe(24)
        token = invite_token(initial, invite_key)
        save_player_invite(initial, invite_key, token)
        session.clear()
        session['role'] = 'player'
        session['player'] = initial
        session['identity'] = game_state.player_identities.setdefault(initial, secrets.token_hex(16))
        return jsonify(success=True, player=initial, rejoin_url=invite_url(initial, token))


@app.route('/api/events')
def game_events_stream():
    if is_tunnel_request():
        return jsonify(error='USE POLLING'), 409
    response = Response(
        stream_with_context(game_events.stream()),
        mimetype='text/event-stream',
    )
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

@app.route('/api/session', methods=['GET'])
@synchronized_game
def get_session():
    role = session.get('role')
    initial = session.get('player')
    if role == 'admin' and not is_local_request():
        session.clear()
        role = None
    if role == 'player' and (initial not in game_state.players or
                            session.get('identity') != game_state.player_identities.get(initial)):
        session.clear()
        role = None
        initial = None
    return jsonify({'role': role, 'player': initial})


@app.route('/api/login', methods=['POST'])
@synchronized_game
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get('role') not in ('admin', 'player'):
        return jsonify({'error': 'Choose ADMIN or PLAYER mode'}), 400
    role = data['role']
    if not is_local_request():
        return jsonify({'error': 'Use your player QR code to join this game'}), 403
    initial = None
    if role == 'player':
        if not isinstance(data.get('initial'), str) or not isinstance(data.get('name', ''), str):
            return jsonify({'error': 'Enter a player initial and name'}), 400
        initial = data['initial'].strip().upper()
        if data.get('create') is True:
            if not all(game_state.teams.get(side) for side in ('left', 'right')):
                return jsonify({'error': 'Select both teams in ADMIN mode before creating a player'}), 403
            # Reuse registration validation and persistence under the same lock.
            response = app.make_response(add_player.__wrapped__())
            if response.status_code >= 400:
                return response
        elif initial not in game_state.players:
            return jsonify({'error': 'Player no longer exists. Choose or create a player.'}), 400
    session.clear()
    session['role'] = role
    if initial:
        session['player'] = initial
        session['identity'] = game_state.player_identities.setdefault(initial, secrets.token_hex(16))
    return jsonify({'role': role, 'player': initial})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/api/reset', methods=['POST'])
@locked_invites
@synchronized_game
def reset_game():
    try:
        # Reset the game state to initial values
        game_state.reset_state()
        delete_all_player_invites()
        tunnel.registration_token = secrets.token_urlsafe(24) if tunnel.active() else None
        
        # Save the fresh state
        if persist_game_state():
            notify_game_change()
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to save game state'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add new route for updating scores
@app.route('/api/scores', methods=['POST'])
@synchronized_game
def update_scores():
    try:
        data = request.json
        left_score = data.get('left', 0)
        right_score = data.get('right', 0)
        
        # Validate scores are integers
        if not (isinstance(left_score, int) and isinstance(right_score, int)):
            return jsonify({'error': 'Invalid score values'}), 400

        # Validate scores are within allowed range
        max_score = config.config['max_score']
        if left_score < 0 or left_score > max_score:
            return jsonify({'error': f'Left score must be between 0 and {max_score}'}), 400
        if right_score < 0 or right_score > max_score:
            return jsonify({'error': f'Right score must be between 0 and {max_score}'}), 400

        # Update score state
        game_state.scores['left'] = left_score
        game_state.scores['right'] = right_score
        persist_game_state()
        notify_game_change()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update the state endpoint to include max_score
@app.route('/api/state', methods=['GET'])
@synchronized_game
def get_state():
    try:
        winner_info = calculate_winner()
        return jsonify({
            'session': get_session().get_json(),
            'connection': {'public': is_tunnel_request(), 'sync': 'poll' if is_tunnel_request() else 'sse'},
            'square_costs': {f'{row},{col}': game_state.square_multipliers.get((row, col), 1)
                             for row, values in enumerate(game_state.squares)
                             for col, value in enumerate(values) if value},
            'squares': game_state.squares,
            'players': game_state.players,
            'teams': game_state.teams,
            'scores': game_state.scores,
            'sport': game_state.sport,
            'max_score': config.config['max_score'],
            'current_multiplier': game_state.current_multiplier,
            'available_multipliers': config.multipliers.get(game_state.sport, [1]),
            'multiplier_labels': config.multiplier_labels.get(game_state.sport, []),
            'tokens_per_player': config.total_tokens.get(game_state.sport, 40),
            'winner': winner_info
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/winner', methods=['GET'])
@synchronized_game
def get_winner():
    """Get the current winner information"""
    try:
        winner_info = calculate_winner()
        return jsonify({
            'success': True,
            'winner': winner_info
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/standings', methods=['GET'])
@synchronized_game
def get_standings():
    """Get all players ranked by distance from current score"""
    try:
        left_score = game_state.scores['left']
        right_score = game_state.scores['right']

        # Determine which team is winning
        if left_score == right_score:
            return jsonify({
                'success': False,
                'error': 'Game is tied'
            })

        winning_team = 'left' if left_score > right_score else 'right'

        # Collect all players with bets on the correct side
        all_standings = []

        for row in range(len(game_state.squares)):
            for col in range(len(game_state.squares[0])):
                square_value = game_state.squares[row][col]

                if not square_value:
                    continue

                # Check if square predicts the correct winning team
                square_predicts_left_wins = row > col
                square_predicts_right_wins = col > row

                if winning_team == 'left' and not square_predicts_left_wins:
                    continue
                if winning_team == 'right' and not square_predicts_right_wins:
                    continue

                distance = abs(row - left_score) + abs(col - right_score)

                # Get multiplier used for this square
                square_key = (row, col)
                multiplier = game_state.square_multipliers.get(square_key, 1)

                all_standings.append({
                    'player': square_value,
                    'player_name': game_state.players.get(square_value, {}).get('name', square_value),
                    'square': {'row': row, 'col': col},
                    'distance': distance,
                    'winning_team': winning_team,
                    'multiplier': multiplier
                })

        # Sort by distance, then by player name when equal
        all_standings.sort(key=lambda x: (x['distance'], x['player_name']))

        return jsonify({
            'success': True,
            'standings': all_standings,
            'winning_team': winning_team
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/squares', methods=['POST'])
@synchronized_game
def update_square():
    try:
        data = request.json
        row = data.get('row')
        col = data.get('col')
        value = data.get('value')

        # Validate row and col are integers
        if not isinstance(row, int) or not isinstance(col, int):
            return jsonify({'error': 'Invalid input: row and col must be integers'}), 400

        if not (0 <= row <= config.config['max_score'] and 0 <= col <= config.config['max_score']):
            return jsonify({'error': 'Invalid input'}), 400

        # Get current value before update
        current_value = game_state.squares[row][col]
        if session.get('role') == 'player':
            initial = session['player']
            if (current_value and current_value != initial) or (value and (
                    not isinstance(value, str) or value.upper() != initial)):
                return jsonify({'error': 'You can only control your own tokens'}), 403
        square_key = (row, col)
        if 'expected_cost' in data and data['expected_cost'] != game_state.square_multipliers.get(square_key, 1):
            return jsonify(error='SQUARE CHANGED — TRY AGAIN'), 409
        if 'expected_value' in data and data['expected_value'] != current_value:
            return jsonify({'error': 'This square changed on another device. Please try again.'}), 409
        if value and (not isinstance(value, str) or value.upper() not in game_state.players):
            return jsonify({'error': 'Player not found'}), 400

        # Calculate token cost with current multiplier
        token_cost = game_state.current_multiplier

        # Track updated players
        updated_players = {}

        # Update bet counts and tokens
        if current_value and current_value in game_state.players:
            # Return tokens when removing a bet - use stored multiplier for this square
            old_multiplier = game_state.square_multipliers.get(square_key, 1)
            game_state.players[current_value]['bets'] = max(0, game_state.players[current_value].get('bets', 0) - old_multiplier)
            game_state.players[current_value]['tokens'] = game_state.players[current_value].get('tokens', 0) + old_multiplier
            updated_players[current_value] = game_state.players[current_value]['tokens']
            # Remove the multiplier entry for this square
            if square_key in game_state.square_multipliers:
                del game_state.square_multipliers[square_key]

        new_value = value.upper() if value else ''
        if new_value and new_value in game_state.players:
            # Check if player has enough tokens
            player_tokens = game_state.players[new_value].get('tokens', 0)
            if player_tokens < token_cost:
                return jsonify({'error': f'Player {new_value} does not have enough tokens remaining'}), 400

            # Deduct tokens and update bet count
            game_state.players[new_value]['bets'] = game_state.players[new_value].get('bets', 0) + token_cost
            game_state.players[new_value]['tokens'] = player_tokens - token_cost
            updated_players[new_value] = game_state.players[new_value]['tokens']
            # Store the multiplier used for this square
            game_state.square_multipliers[square_key] = token_cost

        # Update square
        game_state.squares[row][col] = new_value
        persist_game_state()  # Save state after update
        notify_game_change()
        return jsonify({
            'success': True,
            'updated_players': updated_players  # Return all players whose tokens changed
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_player(data):
    """Create a player while the caller holds the game-state lock."""
    try:
        if not isinstance(data, dict) or not isinstance(data.get('initial'), str) or not isinstance(data.get('name'), str):
            return 'ENTER ID AND NAME', 400
        initial = data.get('initial', '').strip().upper()
        name = data.get('name', '').strip()

        if not initial or not name:
            return 'Initial and name are required', 400

        # Validate initial is exactly 1 alphabetic character
        if not re.fullmatch('[A-Z]', initial):
            return 'Initial must be a single letter (A-Z)', 400

        # Validate name length
        if len(name) > 8:
            return 'Name must be 8 characters or less', 400

        if initial in game_state.players:
            return 'Initial already taken', 400

        if len(game_state.players) >= config.config['max_players']:
            return 'Maximum number of players reached', 400
            
        try:
            player_index = game_state.get_next_player_index()
        except Exception:
            return 'No more player slots available', 400

        # Get tokens per player for current sport
        tokens_per_player = config.total_tokens.get(game_state.sport, 40)

        game_state.players[initial] = {
            'name': name,
            'playerIndex': player_index,
            'bets': 0,
            'tokens': tokens_per_player  # Each player starts with full token allocation
        }
        
        persist_game_state()
        notify_game_change()
        
        return player_index, 200
    except Exception as e:
        return str(e), 500


@app.route('/api/players', methods=['POST'])
@synchronized_game
def add_player():
    player_index, status = create_player(request.get_json(silent=True) or {})
    if status != 200:
        return jsonify(error=player_index), status
    return jsonify(success=True, playerIndex=player_index)

@app.route('/api/players/<initial>', methods=['DELETE'])
@synchronized_game
def delete_player(initial):
    try:
        initial = initial.upper()
        if initial in game_state.players:
            # Release the player index back to the pool
            player_index = game_state.players[initial]['playerIndex']
            game_state.release_player_index(player_index)
            
            # Clear all squares with this player's initial
            for i in range(len(game_state.squares)):
                for j in range(len(game_state.squares[i])):
                    if game_state.squares[i][j] == initial:
                        game_state.squares[i][j] = ''
                        # Remove multiplier entry for this square
                        square_key = (i, j)
                        if square_key in game_state.square_multipliers:
                            del game_state.square_multipliers[square_key]
            
            # Remove player from players dict
            del game_state.players[initial]
            game_state.player_identities.pop(initial, None)
            delete_player_invite(initial)
            persist_game_state()
            notify_game_change()
            return jsonify({'success': True})
        return jsonify({'error': 'Player not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add new route to handle team updates
@app.route('/api/teams', methods=['POST'])
@synchronized_game
def update_teams():
    try:
        data = request.json
        left_team = data.get('left', '')
        right_team = data.get('right', '')
        
        # Update team state
        game_state.teams['left'] = left_team
        game_state.teams['right'] = right_team
        persist_game_state()
        notify_game_change()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update sport selection endpoint to include max score
@app.route('/api/sport', methods=['POST'])
@synchronized_game
def update_sport():
    try:
        data = request.json
        sport = data.get('sport', '').lower()

        # Validate sport
        valid_sports = ['nfl', 'nhl', 'nba', 'mlb', 'olym', 'fifa']
        if sport not in valid_sports:
            return jsonify({'error': 'Invalid sport selection'}), 400

        # Update sport and max score in config
        if config.update_sport(sport):
            # Update game state
            game_state.sport = sport
            # Reset multiplier to 1x
            game_state.current_multiplier = 1

            # Rebuild the grid to match the new sport's max_score
            new_max = config.config['max_score']
            game_state.squares = [['' for _ in range(new_max + 1)] for _ in range(new_max + 1)]
            game_state.square_multipliers = {}

            # Update all existing players to have the new sport's token total
            # Grid was cleared so all bets are gone — give full tokens
            tokens_per_player = config.total_tokens.get(sport, 40)
            for player_initial in game_state.players:
                game_state.players[player_initial]['bets'] = 0
                game_state.players[player_initial]['tokens'] = tokens_per_player

            persist_game_state()
            notify_game_change()

            # Return success with new max score and multiplier info
            return jsonify({
                'success': True,
                'max_score': config.config['max_score'],
                'available_multipliers': config.multipliers.get(sport, [1]),
                'multiplier_labels': config.multiplier_labels.get(sport, []),
                'tokens_per_player': tokens_per_player
            })
        else:
            return jsonify({'error': 'Failed to update sport configuration'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add new endpoint for updating multiplier
@app.route('/api/multiplier', methods=['POST'])
@synchronized_game
def update_multiplier():
    try:
        data = request.json
        multiplier = data.get('multiplier')

        # Validate multiplier
        available_multipliers = config.multipliers.get(game_state.sport, [1])
        if multiplier not in available_multipliers:
            return jsonify({'error': 'Invalid multiplier for current sport'}), 400

        # Update current multiplier
        game_state.current_multiplier = multiplier
        persist_game_state()
        notify_game_change()

        return jsonify({
            'success': True,
            'current_multiplier': multiplier
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_server():
    """Serve the single-process application with bounded production settings."""
    from waitress import serve
    serve(app, host=config.config['host'], port=config.config['port'], **WAITRESS_OPTIONS)


if __name__ == '__main__':
    # Ensure the template exists in the template directory
    index_template = config.template_dir / 'index.html'
    if not index_template.exists():
        try:
            with open('index.html', 'r') as source, open(index_template, 'w') as target:
                target.write(source.read())
        except Exception as e:
            print(f"Error copying template: {e}")
            exit(1)

    # Run one production-quality, threaded WSGI process. In-process game state
    # and event broadcasting intentionally preclude multiple worker processes.
    run_server()
