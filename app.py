from flask import Flask, render_template, jsonify, request
import json
import colorsys

app = Flask(__name__)

# Data structure to store squares and player info
class GameState:
    def __init__(self):
        self.squares = [['' for _ in range(61)] for _ in range(61)]
        self.players = {}  # Format: {'A': {'name': 'Alice', 'color': '#FF5733'}}
        self.next_color_index = 0
    
    def generate_color(self):
        # Generate colors with good contrast using HSV color space
        golden_ratio = 0.618033988749895
        hue = (self.next_color_index * golden_ratio) % 1
        self.next_color_index += 1
        
        # Convert HSV to RGB
        rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.95)
        # Convert RGB to hex
        return '#{:02x}{:02x}{:02x}'.format(
            int(rgb[0] * 255),
            int(rgb[1] * 255),
            int(rgb[2] * 255)
        )

game_state = GameState()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state', methods=['GET'])
def get_state():
    return jsonify({
        'squares': game_state.squares,
        'players': game_state.players
    })

@app.route('/api/squares', methods=['POST'])
def update_square():
    data = request.json
    row = data.get('row')
    col = data.get('col')
    value = data.get('value')
    
    if not (0 <= row < 51 and 0 <= col < 51):
        return jsonify({'error': 'Invalid input'}), 400
    
    # Clear the square if value is empty or update with uppercase initial
    game_state.squares[row][col] = value.upper() if value else ''
    return jsonify({'success': True})

@app.route('/api/players', methods=['POST'])
def add_player():
    data = request.json
    initial = data.get('initial', '').strip().upper()
    name = data.get('name', '').strip()

    if not initial or not name:
        return jsonify({'error': 'Initial and name are required'}), 400

    if initial in game_state.players:
        return jsonify({'error': 'Initial already taken'}), 400

    color = game_state.generate_color()
    game_state.players[initial] = {'name': name, 'color': color}
    return jsonify({'success': True, 'color': color})


@app.route('/api/players/<initial>', methods=['DELETE'])
def delete_player(initial):
    initial = initial.upper()
    if initial in game_state.players:
        # Clear all squares with this player's initial
        for i in range(len(game_state.squares)):
            for j in range(len(game_state.squares[i])):
                if game_state.squares[i][j] == initial:
                    game_state.squares[i][j] = ''
        # Remove player from players dict
        del game_state.players[initial]
        return jsonify({'success': True})
    return jsonify({'error': 'Player not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)