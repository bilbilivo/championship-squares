from flask import Flask, render_template, jsonify, request
import os
from config import config
from database import save_game_state as db_save_state, load_game_state as db_load_state, init_db

# Check for lite mode from environment variable
LITE_MODE = os.environ.get('LITE_MODE', '0') == '1'

app = Flask(__name__, 
           template_folder=str(config.template_dir),
           static_folder=str(config.static_dir))
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))


@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
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
        game_state.save_state()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update the state endpoint to include max_score
@app.route('/api/state', methods=['GET'])
def get_state():
    try:
        winner_info = calculate_winner()
        return jsonify({
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
        square_key = (row, col)

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
        game_state.save_state()  # Save state after update
        return jsonify({
            'success': True,
            'updated_players': updated_players  # Return all players whose tokens changed
        })
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

        # Validate initial is exactly 1 alphabetic character
        if len(initial) != 1 or not initial.isalpha():
            return jsonify({'error': 'Initial must be a single letter (A-Z)'}), 400

        # Validate name length
        if len(name) > 8:
            return jsonify({'error': 'Name must be 8 characters or less'}), 400

        if initial in game_state.players:
            return jsonify({'error': 'Initial already taken'}), 400

        if len(game_state.players) >= config.config['max_players']:
            return jsonify({'error': 'Maximum number of players reached'}), 400
            
        try:
            player_index = game_state.get_next_player_index()
        except Exception:
            return jsonify({'error': 'No more player slots available'}), 400

        # Get tokens per player for current sport
        tokens_per_player = config.total_tokens.get(game_state.sport, 40)

        game_state.players[initial] = {
            'name': name,
            'playerIndex': player_index,
            'bets': 0,
            'tokens': tokens_per_player  # Each player starts with full token allocation
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
                        # Remove multiplier entry for this square
                        square_key = (i, j)
                        if square_key in game_state.square_multipliers:
                            del game_state.square_multipliers[square_key]
            
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

# Update sport selection endpoint to include max score
@app.route('/api/sport', methods=['POST'])
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

            game_state.save_state()

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
        game_state.save_state()

        return jsonify({
            'success': True,
            'current_multiplier': multiplier
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    app.run(
        host=config.config['host'],
        port=config.config['port'],
        debug=config.config['debug']
    )