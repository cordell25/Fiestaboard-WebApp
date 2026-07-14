# Project: Vestaboard Central Hub
# Maintainer: cordell25

from flask import Flask, render_template, request, jsonify
import requests
import json
import os

app = Flask(__name__)
CONFIG_FILE = 'config.json'

# Comprehensive Vestaboard Character Map
VB_CHARS = {
    ' ': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7,
    'H': 8, 'I': 9, 'J': 10, 'K': 11, 'L': 12, 'M': 13, 'N': 14,
    'O': 15, 'P': 16, 'Q': 17, 'R': 18, 'S': 19, 'T': 20, 'U': 21,
    'V': 22, 'W': 23, 'X': 24, 'Y': 25, 'Z': 26,
    '1': 27, '2': 28, '3': 29, '4': 30, '5': 31, '6': 32, '7': 33,
    '8': 34, '9': 35, '0': 36,
    '!': 37, '@': 38, '#': 39, '$': 40, '(': 41, ')': 42,
    '-': 44, '+': 46, '&': 47, '=': 48, ';': 49, ':': 50,
    "'": 52, '"': 53, '%': 54, ',': 55, '.': 56, '/': 59,
    '?': 60, '°': 62
}

def get_config():
    if not os.path.exists(CONFIG_FILE):
        return {"vestaboard_ip": "", "local_api_key": "", "fiestaboard_uuid": ""}
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- PAGE ROUTES ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/scoreboard')
def scoreboard():
    return render_template('scoreboard.html')

@app.route('/wheel')
def wheel():
    return render_template('wheel.html')

@app.route('/timer')
def timer():
    return render_template('timer.html')

# --- API ROUTES ---

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        save_config(request.json)
        return jsonify({"status": "success", "message": "Settings saved"})
    return jsonify(get_config())

@app.route('/update_board', methods=['POST'])
def update_board():
    cfg = get_config()
    if not cfg.get("vestaboard_ip") or not cfg.get("local_api_key"):
        return jsonify({"status": "error", "message": "Vestaboard IP or API Key missing in settings."}), 400

    local_api_url = f"http://{cfg['vestaboard_ip']}:7000/local-api/message"
    
    data = request.json
    players = data.get('players', [])
    board_type = data.get('board_type', 'note')
    game_name = data.get('game_name', 'SCORE').upper()
    
    show_title = False
    if board_type == 'note':
        rows, cols = 3, 15
        name_max_len = 9
        if len(players) <= 2: show_title = True
    else:
        rows, cols = 6, 22
        name_max_len = 14
        if len(players) <= 5: show_title = True
        
    board = [[0 for _ in range(cols)] for _ in range(rows)]
    current_row = 0
    
    if show_title:
        title_str = game_name[:cols].center(cols) 
        for j, char in enumerate(title_str):
            board[current_row][j] = VB_CHARS.get(char, 0)
        current_row += 1
    
    for i, player in enumerate(players):
        if current_row >= rows: break 
        
        board[current_row][0] = int(player.get('color', 63))
        
        name = str(player['name']).upper()[:name_max_len]
        for j, char in enumerate(name):
            board[current_row][j + 2] = VB_CHARS.get(char, 0) 
            
        score_str = str(player['score']).rjust(4)
        score_start_col = cols - 4
        for j, char in enumerate(score_str):
            board[current_row][score_start_col + j] = VB_CHARS.get(char, 0)
            
        current_row += 1

    headers = {'X-Vestaboard-Local-Api-Key': cfg['local_api_key']}
    payload = {'characters': board}
    
    try:
        response = requests.post(local_api_url, json=payload, headers=headers, timeout=5)
        response.raise_for_status()
        return jsonify({"status": "success", "message": f"{board_type.capitalize()} board updated"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/toggle_fiestaboard', methods=['POST'])
def toggle_fiestaboard():
    cfg = get_config()
    uuid = cfg.get("fiestaboard_uuid")
    if not uuid:
        return jsonify({"status": "error", "message": "Fiestaboard UUID missing in settings."}), 400
        
    fiestaboard_api_url = f"http://fiestapi.local:4420/api/settings/board/{uuid}/pause"
    pause_state = request.json.get('paused', True)
    
    try:
        response = requests.post(fiestaboard_api_url, json={"paused": pause_state}, timeout=5)
        response.raise_for_status()
        state_text = "Paused" if pause_state else "Resumed"
        return jsonify({"status": "success", "message": f"Fiestaboard Server {state_text}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
