from flask import Flask, render_template, jsonify, request, send_from_directory
import json
from pathlib import Path
from config import config

app = Flask(__name__, 
           template_folder=str(config.template_dir),
           static_folder=str(config.static_dir))

class GameState:
    def __init__(self):
        self.reset_state()  # Initialize with a fresh state

    def reset_state(self):
        """Reset all game state to initial values"""
        grid_size = config.config['grid_size']
        max_players = config.config['max_players']
        self.squares = [['' for _ in range(grid_size)] for _ in range(grid_size)]
        self.players = {}
        self.teams = {'left': '', 'right': ''}
        self.scores = {'left': 0, 'right': 0}
        self.available_indices = list(range(max_players))

    def save_state(self):
        """Save current game state to file"""
        state = {
            'squares': self.squares,
            'players': self.players,
            'teams': self.teams,
            'scores': self.scores,
            'available_indices': self.available_indices
        }
        try:
            with open(config.base_dir / 'game_state.json', 'w') as f:
                json.dump(state, f)
            return True
        except Exception as e:
            print(f"Error saving game state: {e}")
            return False

    def load_state(self):
        """Load game state from file"""
        try:
            state_file = config.base_dir / 'game_state.json'
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.squares = state.get('squares', self.squares)
                    self.players = state.get('players', self.players)
                    self.teams = state.get('teams', {'left': '', 'right': ''})
                    self.scores = state.get('scores', {'left': 0, 'right': 0})
                    
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

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Error loading template: {e}", 500

@app.route('/api/reset', methods=['POST'])
def reset_game():
    try:
        # Reset the game state to initial values
        game_state.reset_state()
        
        # Save the fresh state
        if game_state.save_state():
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to save game state'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add new route for updating scores
@app.route('/api/scores', methods=['POST'])
def update_scores():
    try:
        data = request.json
        left_score = data.get('left', 0)
        right_score = data.get('right', 0)
        
        # Validate scores
        if not (isinstance(left_score, int) and isinstance(right_score, int)):
            return jsonify({'error': 'Invalid score values'}), 400
            
        # Update score state
        game_state.scores['left'] = left_score
        game_state.scores['right'] = right_score
        game_state.save_state()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update the state endpoint to include scores
@app.route('/api/state', methods=['GET'])
def get_state():
    try:
        return jsonify({
            'squares': game_state.squares,
            'players': game_state.players,
            'teams': game_state.teams,
            'scores': game_state.scores  # Include scores in state response
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
            
        # Get current value before update
        current_value = game_state.squares[row][col]
        
        # Update bet counts
        if current_value and current_value in game_state.players:
            game_state.players[current_value]['bets'] = max(0, game_state.players[current_value].get('bets', 0) - 1)
            
        new_value = value.upper() if value else ''
        if new_value and new_value in game_state.players:
            game_state.players[new_value]['bets'] = game_state.players[new_value].get('bets', 0) + 1
        
        # Update square
        game_state.squares[row][col] = new_value
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
            
        try:
            player_index = game_state.get_next_player_index()
        except Exception as e:
            return jsonify({'error': 'No more player slots available'}), 400

        game_state.players[initial] = {
            'name': name, 
            'playerIndex': player_index,
            'bets': 0
        }
        
        game_state.save_state()
        
        return jsonify({
            'success': True, 
            'playerIndex': player_index  # Frontend still uses this index for color selection
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/players/<initial>', methods=['DELETE'])
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
            
            # Remove player from players dict
            del game_state.players[initial]
            game_state.save_state()
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