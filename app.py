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

@app.route('/vestaword')
def vestaword():
    return render_template('vestaword.html')

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
    
    name_str = str(name)[:15].upper().center(15)
    for i, c in enumerate(name_str): 
        board[0][i] = VB_CHARS.get(c, 0)
    
    board[1][0] = 63  
    board[1][14] = 66 
    
    for i in range(1, 14): 
        if i >= (14 - ticks_passed):
            board[1][i] = 68 
        else:
            board[1][i] = 69 
            
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
    
    if board_uuid:
        try:
            requests.post(f"http://fiestapi.local:4420/api/settings/board/{board_uuid}/pause", json={"paused": True}, timeout=5)
        except Exception as e:
            print(f"Timer thread failed to pause Fiestaboard: {e}")

    ticks = 0
    tick_interval = total_seconds / 13.0
    
    while ticks <= 13:
        if timer_state["active_id"] != timer_id:
            return 
            
        board = build_timer_board(name, total_seconds, ticks, is_done=(ticks==13))
        try:
            send_to_vestaboard(board)
        except Exception as e:
            print(f"Timer tick error: {e}") 
            
        if ticks < 13:
            time.sleep(tick_interval)
        ticks += 1
        
    wait_seconds = int(float(delay_minutes) * 60)
    for _ in range(wait_seconds):
        if timer_state["active_id"] != timer_id:
            return 
        time.sleep(1)
        
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


# --- VESTA-WORD (MULTIPLAYER WORDLE) LOGIC ---
vestaword_state = {
    "status": "lobby", 
    "players": [],     
    "current_turn": 0, 
    "target_word": "",
    "guesses": [],     
    "max_guesses": 6,
    "winner": None,
    "timer_enabled": False,
    "timer_seconds": 30,
    "turn_id": 0,
    "game_id": None
}

def schedule_vestaword_unpause(game_id):
    """Background thread to wait 30s, then unpause if no new game started."""
    time.sleep(30)
    if vestaword_state["game_id"] == game_id and vestaword_state["status"] != "playing":
        cfg = get_config()
        board_uuid = cfg.get("fiestaboard_uuid")
        if board_uuid:
            try:
                requests.post(f"http://fiestapi.local:4420/api/settings/board/{board_uuid}/pause", json={"paused": False}, timeout=5)
            except Exception as e:
                print(f"Vesta-word auto-unpause failed: {e}")

@app.route('/api/vestaword/state', methods=['GET'])
def vestaword_get_state():
    return jsonify(vestaword_state)

@app.route('/api/vestaword/join', methods=['POST'])
def vestaword_join():
    if vestaword_state["status"] != "lobby":
        return jsonify({"status": "error", "message": "Game already in progress!"}), 400
        
    if len(vestaword_state["players"]) == 0:
        vestaword_state["max_guesses"] = int(request.json.get("max_guesses", 6))
        vestaword_state["timer_enabled"] = bool(request.json.get("timer_enabled", False))
        vestaword_state["timer_seconds"] = int(request.json.get("timer_seconds", 30))
        
    player_name = request.json.get("name", "Player").upper()[:10]
    player_id = str(uuid.uuid4())
    
    vestaword_state["players"].append({
        "id": player_id,
        "name": player_name
    })
    
    board = [[0]*15 for _ in range(3)]
    title = "VESTA-WORD".center(15)
    for j, char in enumerate(title): board[0][j] = VB_CHARS.get(char, 0)
    
    msg = f"{len(vestaword_state['players'])} JOINED".center(15)
    for j, char in enumerate(msg): board[2][j] = VB_CHARS.get(char, 0)
    
    try:
        send_to_vestaboard(board)
    except:
        pass 
        
    return jsonify({"status": "success", "player_id": player_id})

@app.route('/api/vestaword/start', methods=['POST'])
def vestaword_start():
    if len(vestaword_state["players"]) == 0:
        return jsonify({"status": "error", "message": "Need at least 1 player"}), 400
        
    try:
        with open('data/5_letter_words.json', 'r') as f:
            words = json.load(f)
            vestaword_state["target_word"] = random.choice(words).upper()
    except Exception as e:
        print(f"Word load error: {e}")
        vestaword_state["target_word"] = "BOARD" 
        
    vestaword_state["status"] = "playing"
    vestaword_state["current_turn"] = 0
    vestaword_state["guesses"] = []
    vestaword_state["winner"] = None
    vestaword_state["turn_id"] += 1
    vestaword_state["game_id"] = str(uuid.uuid4())
    
    # Auto-Pause Fiestaboard when game starts
    cfg = get_config()
    board_uuid = cfg.get("fiestaboard_uuid")
    if board_uuid:
        try:
            requests.post(f"http://fiestapi.local:4420/api/settings/board/{board_uuid}/pause", json={"paused": True}, timeout=5)
        except Exception as e:
            print(f"Vesta-word auto-pause failed: {e}")
    
    update_vestaword_board()
    return jsonify({"status": "success"})

@app.route('/api/vestaword/end', methods=['POST'])
def vestaword_end():
    current_game_id = vestaword_state["game_id"]
    vestaword_state["status"] = "lobby"
    vestaword_state["players"] = []
    vestaword_state["current_turn"] = 0
    vestaword_state["target_word"] = ""
    vestaword_state["guesses"] = []
    vestaword_state["winner"] = None
    vestaword_state["turn_id"] += 1
    
    board = [[0]*15 for _ in range(3)]
    msg = "GAME ENDED".center(15)
    for j, char in enumerate(msg): board[1][j] = VB_CHARS.get(char, 0)
    
    try:
        send_to_vestaboard(board)
    except:
        pass
        
    # Start 30-second unpause thread
    t = threading.Thread(target=schedule_vestaword_unpause, args=(current_game_id,))
    t.daemon = True
    t.start()
        
    return jsonify({"status": "success"})

@app.route('/api/vestaword/timeout', methods=['POST'])
def vestaword_timeout():
    if vestaword_state["status"] != "playing":
        return jsonify({"status": "error", "message": "Game not active"}), 400
        
    player_id = request.json.get("player_id")
    current_player = vestaword_state["players"][vestaword_state["current_turn"]]
    
    if player_id == current_player["id"]:
        vestaword_state["current_turn"] = (vestaword_state["current_turn"] + 1) % len(vestaword_state["players"])
        vestaword_state["turn_id"] += 1
        update_vestaword_board()
        
    return jsonify({"status": "success"})
def update_vestaword_board():
    board = [[0]*15 for _ in range(3)]
    
    if vestaword_state["status"] == "playing":
        # Row 1: Player Name & Turn info
        current_player = vestaword_state["players"][vestaword_state["current_turn"]]["name"]
        header_str = f"{current_player} {len(vestaword_state['guesses']) + 1}/{vestaword_state['max_guesses']}"
        turn_text = header_str[:15].center(15)
        
        for j, char in enumerate(turn_text): 
            board[0][j] = VB_CHARS.get(char, 0)
        
        # Calculate cumulative correct letters across all past guesses
        revealed = [None, None, None, None, None]
        for guess_obj in vestaword_state["guesses"]:
            word = guess_obj["word"]
            colors = guess_obj["colors"]
            for i in range(5):
                if colors[i] == 66:
                    revealed[i] = word[i]
        
        # Row 2 & 3: Revealed Letters & Indicator Blocks
        # We space the 5 slots out across the board, starting at padding index 3
        padding = 3 
        for i in range(5):
            col = padding + (i * 2)
            if revealed[i]:
                board[1][col] = VB_CHARS.get(revealed[i], 0) # The letter
                board[2][col] = 66                           # Green Block
            else:
                board[1][col] = 0                            # Blank Space
                board[2][col] = 63                           # Red Block
    
    try:
        send_to_vestaboard(board)
    except Exception as e:
        print(f"Vesta-word board update failed: {e}")

@app.route('/api/vestaword/guess', methods=['POST'])
def vestaword_guess():
    if vestaword_state["status"] != "playing":
        return jsonify({"status": "error", "message": "Game not active"}), 400
        
    data = request.json
    player_id = data.get("player_id")
    guess = data.get("guess", "").upper()
    
    current_player = vestaword_state["players"][vestaword_state["current_turn"]]
    if player_id != current_player["id"]:
        return jsonify({"status": "error", "message": "Not your turn!"}), 403
        
    if len(guess) != 5:
        return jsonify({"status": "error", "message": "Guess must be 5 letters."}), 400

    target = vestaword_state["target_word"]
    colors = [0, 0, 0, 0, 0] 
    
    target_chars = list(target)
    
    for i in range(5):
        if guess[i] == target[i]:
            colors[i] = 66
            target_chars[i] = None 
            
    for i in range(5):
        if colors[i] != 66 and guess[i] in target_chars:
            colors[i] = 65
            target_chars[target_chars.index(guess[i])] = None

    vestaword_state["guesses"].append({"word": guess, "colors": colors})
    vestaword_state["turn_id"] += 1
    current_game_id = vestaword_state["game_id"]

    if guess == target:
        vestaword_state["status"] = "game_over"
        vestaword_state["winner"] = current_player["name"]
        
        board = [[0]*15 for _ in range(3)]
        w_text = f"{current_player['name']} WINS!"[:15].center(15)
        for j, char in enumerate(w_text): board[0][j] = VB_CHARS.get(char, 0)
        word_text = guess[:15].center(15)
        for j, char in enumerate(word_text): board[1][j] = VB_CHARS.get(char, 0)
        send_to_vestaboard(board)
        
        # Start 30-second unpause thread for Win
        t = threading.Thread(target=schedule_vestaword_unpause, args=(current_game_id,))
        t.daemon = True
        t.start()
        
        return jsonify({"status": "success"})
        
    elif len(vestaword_state["guesses"]) >= vestaword_state["max_guesses"]:
        vestaword_state["status"] = "game_over"
        vestaword_state["winner"] = "Nobody"
        
        board = [[0]*15 for _ in range(3)]
        l_text = "GAME OVER"[:15].center(15)
        for j, char in enumerate(l_text): board[0][j] = VB_CHARS.get(char, 0)
        word_text = f"WAS: {target}"[:15].center(15)
        for j, char in enumerate(word_text): board[2][j] = VB_CHARS.get(char, 0)
        send_to_vestaboard(board)
        
        # Start 30-second unpause thread for Loss
        t = threading.Thread(target=schedule_vestaword_unpause, args=(current_game_id,))
        t.daemon = True
        t.start()
        
        return jsonify({"status": "success"})
        
    else:
        vestaword_state["current_turn"] = (vestaword_state["current_turn"] + 1) % len(vestaword_state["players"])
        update_vestaword_board()
        return jsonify({"status": "success"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
