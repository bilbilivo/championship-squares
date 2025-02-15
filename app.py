from flask import Flask, render_template, jsonify, request, send_from_directory
import json
import colorsys
from pathlib import Path
from config import config

app = Flask(__name__, 
           template_folder=str(config.template_dir),
           static_folder=str(config.static_dir))

# Data structure to store squares and player info
class GameState:
    def __init__(self):
        grid_size = config.config['grid_size']
        self.squares = [['' for _ in range(grid_size)] for _ in range(grid_size)]
        self.players = {}  # Format: {'A': {'name': 'Alice', 'color': '#FF5733'}}
        self.next_color_index = 0
        self.teams = {}  # Store team code (e.g., 'KC', 'SF')

    def save_state(self):
        """Save game state to file"""
        try:
            state = {
                'squares': self.squares,
                'players': self.players,
                'next_color_index': self.next_color_index,
                'teams': self.teams  # Add teams to saved state
            }
            with open(config.base_dir / 'game_state.json', 'w') as f:
                json.dump(state, f)
        except Exception as e:
            print(f"Error saving game state: {e}")

    def load_state(self):
        """Load game state from file"""
        try:
            state_file = config.base_dir / 'game_state.json'
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.squares = state.get('squares', self.squares)
                    self.players = state.get('players', self.players)
                    self.next_color_index = state.get('next_color_index', 0)
                    self.teams = state.get('teams', {'left': '', 'right': ''})  # Load teams with default
        except Exception as e:
            print(f"Error loading game state: {e}")

game_state = GameState()
game_state.load_state()  # Load previous state if exists

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Error loading template: {e}", 500

@app.route('/api/state', methods=['GET'])
def get_state():
    try:
        return jsonify({
            'squares': game_state.squares,
            'players': game_state.players,
            'teams': game_state.teams  # Include teams in state response
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/squares', methods=['POST'])
def update_square():
    try:
        data = request.json
        row = data.get('row')
        col = data.get('col')
        value = data.get('value')
        
        if not (0 <= row < config.config['grid_size'] and 0 <= col < config.config['grid_size']):
            return jsonify({'error': 'Invalid input'}), 400
        
        # Clear the square if value is empty or update with uppercase initial
        game_state.squares[row][col] = value.upper() if value else ''
        game_state.save_state()  # Save state after update
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/players', methods=['POST'])
def add_player():
    try:
        data = request.json
        initial = data.get('initial', '').strip().upper()
        name = data.get('name', '').strip()

        if not initial or not name:
            return jsonify({'error': 'Initial and name are required'}), 400

        if initial in game_state.players:
            return jsonify({'error': 'Initial already taken'}), 400

        if len(game_state.players) >= config.config['max_players']:
            return jsonify({'error': 'Maximum number of players reached'}), 400

        color = data.get('color', '#FFFFFF')  # Use provided color or default to white
        game_state.players[initial] = {'name': name, 'color': color}
        game_state.save_state()  # Save state after adding player
        return jsonify({'success': True, 'color': color})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset_game():
    try:
        game_state.squares = [['' for _ in range(config.config['grid_size'])] for _ in range(config.config['grid_size'])]
        game_state.players = {}
        game_state.next_color_index = 0
        game_state.teams = {'left': '', 'right': ''}  # Reset teams
        game_state.save_state()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/players/<initial>', methods=['DELETE'])
def delete_player(initial):
    try:
        initial = initial.upper()
        if initial in game_state.players:
            # Clear all squares with this player's initial
            for i in range(len(game_state.squares)):
                for j in range(len(game_state.squares[i])):
                    if game_state.squares[i][j] == initial:
                        game_state.squares[i][j] = ''
            # Remove player from players dict
            del game_state.players[initial]
            game_state.save_state()  # Save state after deletion
            return jsonify({'success': True})
        return jsonify({'error': 'Player not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add new route to handle team updates
@app.route('/api/teams', methods=['POST'])
def update_teams():
    try:
        data = request.json
        left_team = data.get('left', '')
        right_team = data.get('right', '')
        
        # Update team state
        game_state.teams['left'] = left_team
        game_state.teams['right'] = right_team
        game_state.save_state()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def open_browser():
    """Open the browser to the application URL"""
    import webbrowser
    import threading
    import time
    
    def _open_browser():
        time.sleep(1.5)  # Wait for the server to start
        url = f'http://{config.config["host"]}:{config.config["port"]}'
        # If host is 0.0.0.0, replace with localhost for browser
        if config.config["host"] == "0.0.0.0":
            url = f'http://localhost:{config.config["port"]}'
        webbrowser.open(url)

    threading.Thread(target=_open_browser).start()

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

    # Start the server with platform-specific configuration
    # Open browser when app starts
    open_browser()
    
    app.run(
        host=config.config['host'],
        port=config.config['port'],
        debug=config.config['debug']
    )