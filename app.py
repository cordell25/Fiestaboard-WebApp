# Project: Fiestaboard WebApp Hub
# Maintainer: cordell25

from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import random

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

# --- WHEEL OF FORTUNE LOGIC ---
CATEGORY_MAP = {
    "doing.json": "WHAT R U DOING?",
    "food_drink.json": "FOOD & DRINK",
    "person.json": "PERSON / PEOPLE",
    "phrase.json": "PHRASE",
    "place.json": "ON THE MAP",
    "things.json": "THING / THINGS"
}

wheel_state = {
    "answer": "",
    "category_name": "",
    "revealed_letters": set(),
    "board_type": "note" # Default to note, can be updated via config
}

def load_random_puzzle(category_file=None):
    if not category_file or category_file == "random":
        category_file = random.choice(list(CATEGORY_MAP.keys()))
    
    filepath = os.path.join("data", category_file)
    cat_name = CATEGORY_MAP.get(category_file, "MYSTERY")
    
    try:
        with open(filepath, 'r') as f:
            answers = json.load(f)
            answer = random.choice(answers).upper()
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        answer = "TEST PUZZLE" # Fallback if file is missing
        cat_name = "ERROR LOADING DATA"
        
    wheel_state["answer"] = answer
    wheel_state["category_name"] = cat_name
    wheel_state["revealed_letters"] = set()
    return cat_name, answer

def send_to_vestaboard(board_matrix):
    cfg = get_config()
    if not cfg.get("vestaboard_ip") or not cfg.get("local_api_key"):
        raise Exception("Vestaboard IP or API Key missing.")

    url = f"http://{cfg['vestaboard_ip']}:7000/local-api/message"
    headers = {'X-Vestaboard-Local-Api-Key': cfg['local_api_key']}
    payload = {'characters': board_matrix}
    
    response = requests.post(url, json=payload, headers=headers, timeout=5)
    response.raise_for_status()

def build_puzzle_board():
    # Note board sizing by default. If standard, adjust cols/rows.
    cols, rows = 15, 3 
    
    answer = wheel_state["answer"]
    words = answer.split(' ')
    lines = []
    current_line = []
    current_len = 0
    
    # Word Wrapping Logic
    for word in words:
        space_needed = 1 if current_line else 0
        if current_len + len(word) + space_needed <= cols:
            current_line.append(word)
            current_len += len(word) + space_needed
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_len = len(word)
    if current_line:
        lines.append(" ".join(current_line))

    show_category = len(lines) < rows
    board = [[0]*cols for _ in range(rows)]

    # Layout the puzzle
    for row_idx, line in enumerate(lines):
        if row_idx >= rows - (1 if show_category else 0):
            break # Avoid overflowing the board
            
        padding = (cols - len(line)) // 2 # Center horizontally
        for col_idx, char in enumerate(line):
            if char == ' ':
                board[row_idx][padding + col_idx] = 0 # Blank
            elif char in wheel_state["revealed_letters"] or not char.isalpha():
                board[row_idx][padding + col_idx] = VB_CHARS.get(char, 0) # Revealed
            else:
                board[row_idx][padding + col_idx] = 69 # White Block

    # Add category to the bottom row if space permits
    if show_category:
        cat_str = wheel_state["category_name"][:cols].center(cols)
        for j, char in enumerate(cat_str):
             board[rows-1][j] = VB_CHARS.get(char, 0)
             
    return board

# --- CONFIG LOGIC ---
def get_config():
    if not os.path.exists(CONFIG_FILE):
        return {"vestaboard_ip": "", "local_api_key": "", "fiestaboard_uuid": "", "timer_page_id": ""}
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
    categories = [{"file": k, "name": v} for k, v in CATEGORY_MAP.items()]
    return render_template('wheel.html', categories=categories)

@app.route('/timer')
def timer():
    return render_template('timer.html')

# --- API ROUTES (GLOBAL CONFIG & PROXIES) ---
@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        save_config(request.json)
        return jsonify({"status": "success", "message": "Settings saved"})
    return jsonify(get_config())

@app.route('/api/proxy/boards', methods=['GET'])
def proxy_boards():
    try:
        response = requests.get("http://fiestapi.local:4420/api/settings/board", timeout=5)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/proxy/pages', methods=['GET'])
def proxy_pages():
    try:
        response = requests.get("http://fiestapi.local:4420/api/pages", timeout=5)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- API ROUTES (WHEEL OF FORTUNE) ---
@app.route('/api/wheel/start', methods=['POST'])
def wheel_start():
    cat_file = request.json.get('category', 'random')
    cat_name, _ = load_random_puzzle(cat_file)
    
    # Generate the initial "CATEGORY" announcement board
    cols, rows = 15, 3
    board = [[0]*cols for _ in range(rows)]
    
    title = "CATEGORY".center(cols)
    for j, char in enumerate(title):
        board[0][j] = VB_CHARS.get(char, 0)
        
    cat_str = cat_name[:cols].center(cols)
    for j, char in enumerate(cat_str):
        board[2][j] = VB_CHARS.get(char, 0)
        
    try:
        send_to_vestaboard(board)
        return jsonify({"status": "success", "category": cat_name})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/wheel/puzzle', methods=['POST'])
def wheel_puzzle():
    try:
        board = build_puzzle_board()
        send_to_vestaboard(board)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/wheel/guess', methods=['POST'])
def wheel_guess():
    letter = request.json.get('letter', '').upper()
    wheel_state["revealed_letters"].add(letter)
    
    found = letter in wheel_state["answer"]
    
    try:
        board = build_puzzle_board()
        send_to_vestaboard(board)
        return jsonify({"status": "success", "found": found})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/wheel/solve', methods=['POST'])
def wheel_solve():
    # Add all uppercase letters to revealed set to show everything
    wheel_state["revealed_letters"].update([chr(i) for i in range(65, 91)])
    try:
        board = build_puzzle_board()
        send_to_vestaboard(board)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- REMAINING ROUTES (SCOREBOARD & TIMER) ---
# ... Keep your existing /update_board, /toggle_fiestaboard, and /api/timer/start logic here
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

@app.route('/api/timer/start', methods=['POST'])
def timer_start():
    data = request.json
    minutes = int(data.get('minutes', 5))
    cfg = get_config()
    page_id = cfg.get("timer_page_id")
    try:
        plugin_payload = {"duration": minutes}
        response1 = requests.post("http://fiestapi.local:4420/api/plugins/timer/receive", json=plugin_payload, timeout=5)
        response1.raise_for_status()
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to start timer logic: {str(e)}"}), 500

    if page_id:
        try:
            override_payload = {
                "duration_minutes": minutes + 2,
                "page_id": page_id
            }
            response2 = requests.post("http://fiestapi.local:4420/api/settings/temporary-override", json=override_payload, timeout=5)
            response2.raise_for_status()
        except Exception as e:
            return jsonify({"status": "warning", "message": "Timer started, but failed to set temporary override."}), 500
    return jsonify({"status": "success", "message": f"{minutes}-minute timer started!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
