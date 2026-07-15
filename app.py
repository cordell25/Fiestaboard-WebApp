# Project: Fiestaboard WebApp Hub
# Maintainer: cordell25

from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import random
import threading
import time
import uuid

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

# --- GLOBAL CONFIG LOGIC ---
def get_config():
    if not os.path.exists(CONFIG_FILE):
        return {"vestaboard_ip": "", "local_api_key": "", "fiestaboard_uuid": "", "timer_end_delay": 1}
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def send_to_vestaboard(board_matrix):
    cfg = get_config()
    if not cfg.get("vestaboard_ip") or not cfg.get("local_api_key"):
        raise Exception("Vestaboard IP or API Key missing.")

    url = f"http://{cfg['vestaboard_ip']}:7000/local-api/message"
    headers = {'X-Vestaboard-Local-Api-Key': cfg['local_api_key']}
    payload = {'characters': board_matrix}
    
    response = requests.post(url, json=payload, headers=headers, timeout=5)
    response.raise_for_status()

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

# --- API ROUTES (GLOBAL) ---
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

# --- TIMER LOGIC ---
timer_state = {"active_id": None}

def build_timer_board(name, total_seconds, ticks_passed, is_done):
    board = [[0]*15 for _ in range(3)]
    
    # Row 1: Centered Name
    name_str = str(name)[:15].upper().center(15)
    for i, c in enumerate(name_str): 
        board[0][i] = VB_CHARS.get(c, 0)
    
    # Row 2: The Color Blocks
    board[1][0] = 63  # Red Left Cap
    board[1][14] = 66 # Green Right Cap
    
    for i in range(1, 14): # Indices 1 through 13
        if i >= (14 - ticks_passed):
            board[1][i] = 68 # Violet (Replaced from right to left)
        else:
            board[1][i] = 69 # White (Remaining)
            
    # Row 3: Duration / Times Up
    if is_done:
        text = "TIMES UP".center(15)
    else:
        m = total_seconds // 60
        s = total_seconds % 60
        text = f"{m}'{s}\" TIMER".center(15)
        
    for i, c in enumerate(text): 
        board[2][i] = VB_CHARS.get(c, 0)
        
    return board

def run_timer_thread(timer_id, name, total_seconds, delay_minutes):
    cfg = get_config()
    board_uuid = cfg.get("fiestaboard_uuid")
    
    # 1. Pause Fiestaboard
    if board_uuid:
        try:
            requests.post(f"http://fiestapi.local:4420/api/settings/board/{board_uuid}/pause", json={"paused": True}, timeout=5)
        except Exception as e:
            print(f"Timer thread failed to pause Fiestaboard: {e}")

    # 2. Execute Timer Ticks
    ticks = 0
    tick_interval = total_seconds / 13.0
    
    while ticks <= 13:
        if timer_state["active_id"] != timer_id:
            return # A new timer was started, cancel this thread
            
        board = build_timer_board(name, total_seconds, ticks, is_done=(ticks==13))
        try:
            send_to_vestaboard(board)
        except Exception as e:
            print(f"Timer tick error: {e}") 
            
        if ticks < 13:
            time.sleep(tick_interval)
        ticks += 1
        
    # 3. Wait X minutes before unpausing
    wait_seconds = int(float(delay_minutes) * 60)
    for _ in range(wait_seconds):
        if timer_state["active_id"] != timer_id:
            return # Cancelled during wait
        time.sleep(1)
        
    # 4. Resume Fiestaboard
    if board_uuid and timer_state["active_id"] == timer_id:
        try:
            requests.post(f"http://fiestapi.local:4420/api/settings/board/{board_uuid}/pause", json={"paused": False}, timeout=5)
        except Exception as e:
            print(f"Timer thread failed to resume Fiestaboard: {e}")

@app.route('/api/timer/start', methods=['POST'])
def timer_start():
    data = request.json
    name = str(data.get('name', 'TIMER')).strip()
    if not name: name = 'TIMER'
    
    minutes = int(data.get('minutes', 5))
    seconds = int(data.get('seconds', 0))
    total_seconds = (minutes * 60) + seconds
    
    if total_seconds <= 0:
        return jsonify({"status": "error", "message": "Duration must be greater than 0"}), 400
        
    cfg = get_config()
    delay_minutes = cfg.get("timer_end_delay", 1)
    
    # Assign a unique ID so old timer threads terminate if a new one is launched
    timer_id = str(uuid.uuid4())
    timer_state["active_id"] = timer_id
    
    t = threading.Thread(target=run_timer_thread, args=(timer_id, name, total_seconds, delay_minutes))
    t.daemon = True
    t.start()
    
    return jsonify({"status": "success", "message": f"'{name}' Timer running on board!"})


# --- WHEEL OF FORTUNE LOGIC ---
CATEGORY_MAP = {
    "doing.json": "WHAT R U DOING?",
    "food_drink.json": "FOOD & DRINK",
    "person.json": "PERSON / PEOPLE",
    "phrase.json": "PHRASE",
    "place.json": "ON THE MAP",
    "things.json": "THING / THINGS"
}
wheel_state = { "answer": "", "category_name": "", "revealed_letters": set(), "board_type": "note" }

def load_random_puzzle(category_file=None):
    if not category_file or category_file == "random":
        category_file = random.choice(list(CATEGORY_MAP.keys()))
    filepath = os.path.join("data", category_file)
    cat_name = CATEGORY_MAP.get(category_file, "MYSTERY")
    try:
        with open(filepath, 'r') as f:
            answers = json.load(f)
            answer = random.choice(answers).upper()
    except:
        answer = "TEST PUZZLE" 
        cat_name = "ERROR LOADING DATA"
    wheel_state["answer"] = answer
    wheel_state["category_name"] = cat_name
    wheel_state["revealed_letters"] = set()
    return cat_name, answer

def build_puzzle_board():
    cols, rows = 15, 3 
    answer = wheel_state["answer"]
    words = answer.split(' ')
    lines = []
    current_line = []
    current_len = 0
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
    for row_idx, line in enumerate(lines):
        if row_idx >= rows - (1 if show_category else 0):
            break 
        padding = (cols - len(line)) // 2 
        for col_idx, char in enumerate(line):
            if char == ' ':
                board[row_idx][padding + col_idx] = 0 
            elif char in wheel_state["revealed_letters"] or not char.isalpha():
                board[row_idx][padding + col_idx] = VB_CHARS.get(char, 0) 
            else:
                board[row_idx][padding + col_idx] = 69 

    if show_category:
        cat_str = wheel_state["category_name"][:cols].center(cols)
        for j, char in enumerate(cat_str):
             board[rows-1][j] = VB_CHARS.get(char, 0)
    return board

@app.route('/api/wheel/start', methods=['POST'])
def wheel_start():
    cat_file = request.json.get('category', 'random')
    cat_name, _ = load_random_puzzle(cat_file)
    try:
        board = build_puzzle_board()
        send_to_vestaboard(board)
        return jsonify({"status": "success", "category": cat_name})
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

@app.route('/api/wheel/reveal_random', methods=['POST'])
def wheel_reveal_random():
    answer = wheel_state["answer"]
    unrevealed = set(char for char in answer if char.isalpha() and char not in wheel_state["revealed_letters"])
    if not unrevealed:
        return jsonify({"status": "complete"})
    chosen_letter = random.choice(list(unrevealed))
    wheel_state["revealed_letters"].add(chosen_letter)
    try:
        board = build_puzzle_board()
        send_to_vestaboard(board)
        return jsonify({"status": "success", "letter": chosen_letter})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/wheel/solve', methods=['POST'])
def wheel_solve():
    wheel_state["revealed_letters"].update([chr(i) for i in range(65, 91)])
    try:
        board = build_puzzle_board()
        send_to_vestaboard(board)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- SCOREBOARD LOGIC ---
@app.route('/update_board', methods=['POST'])
def update_board():
    cfg = get_config()
    if not cfg.get("vestaboard_ip") or not cfg.get("local_api_key"):
        return jsonify({"status": "error", "message": "Vestaboard IP or API Key missing."}), 400
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
        for j, char in enumerate(title_str): board[current_row][j] = VB_CHARS.get(char, 0)
        current_row += 1
    
    for i, player in enumerate(players):
        if current_row >= rows: break 
        board[current_row][0] = int(player.get('color', 63))
        name = str(player['name']).upper()[:name_max_len]
        for j, char in enumerate(name): board[current_row][j + 2] = VB_CHARS.get(char, 0) 
        score_str = str(player['score']).rjust(4)
        score_start_col = cols - 4
        for j, char in enumerate(score_str): board[current_row][score_start_col + j] = VB_CHARS.get(char, 0)
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
    if not uuid: return jsonify({"status": "error", "message": "Fiestaboard UUID missing in settings."}), 400
    try:
        response = requests.post(f"http://fiestapi.local:4420/api/settings/board/{uuid}/pause", json={"paused": request.json.get('paused', True)}, timeout=5)
        response.raise_for_status()
        return jsonify({"status": "success", "message": "Success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
