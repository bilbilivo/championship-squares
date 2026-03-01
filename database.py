# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Stephane Belliveau
import sqlite3
from config import config

DB_PATH = config.base_dir / 'game_state.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS game_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS players (
                    initial TEXT PRIMARY KEY,
                    name TEXT,
                    player_index INTEGER,
                    bets INTEGER,
                    tokens INTEGER
                )''')
                
    c.execute('''CREATE TABLE IF NOT EXISTS squares (
                    row INTEGER,
                    col INTEGER,
                    player_initial TEXT,
                    multiplier INTEGER,
                    PRIMARY KEY (row, col)
                )''')
                
    c.execute('''CREATE TABLE IF NOT EXISTS available_indices (
                    player_index INTEGER PRIMARY KEY
                )''')

    conn.commit()
    conn.close()

def save_game_state(state):
    conn = get_db()
    c = conn.cursor()
    
    try:
        # Save config
        c.execute('INSERT OR REPLACE INTO game_config (key, value) VALUES (?, ?)', ('sport', state['sport']))
        c.execute('INSERT OR REPLACE INTO game_config (key, value) VALUES (?, ?)', ('current_multiplier', str(state['current_multiplier'])))
        c.execute('INSERT OR REPLACE INTO game_config (key, value) VALUES (?, ?)', ('score_left', str(state['scores']['left'])))
        c.execute('INSERT OR REPLACE INTO game_config (key, value) VALUES (?, ?)', ('score_right', str(state['scores']['right'])))
        c.execute('INSERT OR REPLACE INTO game_config (key, value) VALUES (?, ?)', ('team_left', state['teams']['left']))
        c.execute('INSERT OR REPLACE INTO game_config (key, value) VALUES (?, ?)', ('team_right', state['teams']['right']))
        
        # Save players
        c.execute('DELETE FROM players')
        for initial, p in state['players'].items():
            c.execute('INSERT INTO players (initial, name, player_index, bets, tokens) VALUES (?, ?, ?, ?, ?)',
                      (initial, p['name'], p['playerIndex'], p.get('bets', 0), p.get('tokens', 0)))
                      
        # Save squares
        c.execute('DELETE FROM squares')
        # Flatten squares
        squares_data = []
        for r in range(len(state['squares'])):
            for col in range(len(state['squares'][r])):
                val = state['squares'][r][col]
                # Assume keys are tuples (row, col) as in GameState
                mult = state['square_multipliers'].get((r, col), 1) 
                
                if val:
                   squares_data.append((r, col, val, mult))
        
        c.executemany('INSERT INTO squares (row, col, player_initial, multiplier) VALUES (?, ?, ?, ?)', squares_data)
        
        # Save available indices
        c.execute('DELETE FROM available_indices')
        indices_data = [(i,) for i in state['available_indices']]
        c.executemany('INSERT INTO available_indices (player_index) VALUES (?)', indices_data)
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving to DB: {e}")
        return False
    finally:
        conn.close()

def load_game_state():
    if not DB_PATH.exists():
        return None
        
    conn = get_db()
    c = conn.cursor()
    
    state = {}
    
    try:
        # Load config
        c.execute('SELECT key, value FROM game_config')
        config_dict = {row['key']: row['value'] for row in c.fetchall()}
        
        if not config_dict:
            return None
            
        state['sport'] = config_dict.get('sport', 'nfl')
        state['current_multiplier'] = int(config_dict.get('current_multiplier', 1))
        state['scores'] = {
            'left': int(config_dict.get('score_left', 0)),
            'right': int(config_dict.get('score_right', 0))
        }
        state['teams'] = {
            'left': config_dict.get('team_left', ''),
            'right': config_dict.get('team_right', '')
        }
        
        # Load players
        c.execute('SELECT * FROM players')
        players = {}
        for row in c.fetchall():
            players[row['initial']] = {
                'name': row['name'],
                'playerIndex': row['player_index'],
                'bets': row['bets'],
                'tokens': row['tokens']
            }
        state['players'] = players
        
        # Load squares
        # We need to reconstruct the 2D array. Size depends on sport/max_score.
        # But max_score is in config.config['max_score']. We need to know the size.
        # The caller (GameState) will handle sizing based on sport.
        # Here we just return the list of squares and let GameState populate.
        
        c.execute('SELECT * FROM squares')
        squares_list = c.fetchall()
        
        # Convert to dictionary for easier loading: {(r,c): {'val': val, 'mult': mult}}
        squares_dict = {}
        square_multipliers = {}
        
        for row in squares_list:
            squares_dict[(row['row'], row['col'])] = row['player_initial']
            if row['multiplier'] > 1:
                square_multipliers[(row['row'], row['col'])] = row['multiplier']
                
        state['squares_dict'] = squares_dict
        state['square_multipliers'] = square_multipliers
        
        # Load available indices
        c.execute('SELECT player_index FROM available_indices ORDER BY player_index')
        state['available_indices'] = [row['player_index'] for row in c.fetchall()]
        
        return state
        
    except Exception as e:
        print(f"Error loading from DB: {e}")
        return None
    finally:
        conn.close()
