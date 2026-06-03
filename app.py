import sys
import os
import secrets
import time
from flask import Flask, jsonify, request, render_template, session, redirect

from game import Game


def resource_path(rel):
    """Return absolute path — works both for normal runs and PyInstaller bundles."""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


app = Flask(__name__,
            template_folder=resource_path('templates'),
            static_folder=resource_path('static'))
app.secret_key = secrets.token_hex(16)

game_state: Game | None = None

# LAN lobby — shared server-side state for the pre-game waiting room.
# Phase state machine:  None → 'lobby' → 'shield_setup' → 'playing'
lobby = {
    'phase': None,          # current phase (None = no active lobby)
    'players': [],          # player names in join order (index 0 = host)
    'shields_done': [],     # player indices who have confirmed their shield pick
    'host_pending': False,  # True until the host joins via /join_lobby
}


# ── Pages ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/host_ip')
def host_ip():
    """Return the LAN-reachable IP so the lobby can show the correct join URL."""
    try:
        from discovery import get_local_ip
        ip = get_local_ip()
    except Exception:
        import socket
        ip = socket.gethostbyname(socket.gethostname())
    return jsonify({'ip': ip, 'url': f'http://{ip}:5000'})


@app.route('/host')
def host():
    """Launcher opens this URL to initialise the lobby and mark the browser as host.

    The session cookie written here is what distinguishes the host browser from
    regular joiner browsers — it is checked in start_lan_game and action routes.
    """
    lobby['phase'] = 'lobby'
    lobby['players'] = []
    lobby['shields_done'] = []
    lobby['host_pending'] = True
    session['is_host'] = True
    session.pop('player_index', None)
    return redirect('/')


# ── LAN lobby API ─────────────────────────────────────────────────────────────

@app.route('/lan_status')
def lan_status():
    # Polled every 2 seconds by every connected browser.  Acts as the phase gate:
    # the frontend switches screens (lobby → shield_setup → playing) based on the
    # 'phase' field returned here.
    pi = session.get('player_index', None)
    return jsonify({
        'phase':          lobby['phase'],
        'my_player_index': pi,
        'is_host':        session.get('is_host', False),
        'host_pending':   lobby.get('host_pending', False),
        'lobby_players':  lobby['players'],
        'shields_done':   lobby['shields_done'],
        'my_shield_done': (pi in lobby['shields_done']) if pi is not None else False,
    })


@app.route('/join_lobby', methods=['POST'])
def join_lobby():
    if lobby['phase'] != 'lobby':
        return jsonify({'error': 'No lobby open right now'}), 400
    if len(lobby['players']) >= 5:
        return jsonify({'error': 'Game is full (max 5 players)'}), 400
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400

    pi = len(lobby['players'])
    lobby['players'].append(name)
    session['player_index'] = pi
    if lobby.get('host_pending') and pi == 0:
        lobby['host_pending'] = False
    return jsonify({'player_index': pi, 'players': lobby['players']})


@app.route('/lobby_state')
def lobby_state_route():
    return jsonify({
        'phase':        lobby['phase'],
        'players':      lobby['players'],
        'shields_done': lobby['shields_done'],
    })


@app.route('/start_lan_game', methods=['POST'])
def start_lan_game():
    global game_state
    if session.get('player_index') != 0:
        return jsonify({'error': 'Only the host can start the game'}), 403
    if len(lobby['players']) < 2:
        return jsonify({'error': 'Need at least 2 players to start'}), 400

    # Create the game with lan_mode=True so the 40-second turn timer is active.
    # Transition to shield_setup: each player must pick their shield before play begins.
    # shields_done is reset here in case a previous game was abandoned mid-setup.
    game_state = Game(lobby['players'])
    game_state.lan_mode = True
    lobby['phase'] = 'shield_setup'
    lobby['shields_done'] = []
    return jsonify({'ok': True, 'phase': 'shield_setup'})


# ── Hot-seat game API ─────────────────────────────────────────────────────────

@app.route('/new_game', methods=['POST'])
def new_game():
    global game_state
    data = request.get_json()
    players = data.get('players', [])
    if len(players) < 2 or len(players) > 5:
        return jsonify({'error': 'Need 2–5 players'}), 400
    game_state = Game(players)
    return jsonify(game_state.to_dict())


# ── Shared game API ──────────────────────────────────────────────────────────

@app.route('/state', methods=['GET'])
def state():
    if game_state is None:
        return jsonify({'error': 'No game in progress'}), 400

    # Auto-skip timed-out player (LAN mode only).
    # /state is polled every 2 seconds by all clients, so the skip fires within
    # ~2 seconds of the 40-second deadline — no separate background thread needed.
    if game_state.lan_mode and game_state.turn_start_time and not game_state.winner:
        if time.time() - game_state.turn_start_time > 40:
            game_state.auto_skip_turn()
            game_state.start_turn()

    d = game_state.to_dict()
    d['my_player_index'] = session.get('player_index', None)
    return jsonify(d)


@app.route('/start_turn', methods=['POST'])
def start_turn():
    if game_state is None:
        return jsonify({'error': 'No game in progress'}), 400
    # LAN mode: only the current player may call this
    if game_state.lan_mode:
        pi = session.get('player_index')
        if pi != game_state.current_index:
            return jsonify({'error': 'Not your turn'}), 403
    game_state.start_turn()
    d = game_state.to_dict()
    d['my_player_index'] = session.get('player_index', None)
    return jsonify(d)


@app.route('/set_shield', methods=['POST'])
def set_shield():
    if game_state is None:
        return jsonify({'error': 'No game in progress'}), 400
    data = request.get_json()
    player_index = data.get('player_index')
    card_index = data.get('card_index')

    if game_state.lan_mode:
        # In LAN mode players can only set their own shield (session-bound index check)
        pi = session.get('player_index')
        if pi is None or pi != player_index:
            return jsonify({'error': 'Can only set your own shield'}), 403
        game_state.set_shield(player_index, card_index)
        if player_index not in lobby['shields_done']:
            lobby['shields_done'].append(player_index)
        # Once every player has confirmed their shield, advance to 'playing'
        if len(lobby['shields_done']) == len(lobby['players']):
            lobby['phase'] = 'playing'
    else:
        game_state.set_shield(player_index, card_index)

    return jsonify(game_state.to_dict())


@app.route('/action', methods=['POST'])
def action():
    # The client must call /start_turn before /action on each turn.
    # start_turn() checks whether the charged card should be discarded (took damage);
    # skipping it would let a player keep a charge they should have lost.
    global game_state
    if game_state is None:
        return jsonify({'error': 'No game in progress'}), 400
    if game_state.winner:
        return jsonify({'error': 'Game already over'}), 400

    # LAN mode: only the current player may act
    if game_state.lan_mode:
        pi = session.get('player_index')
        if pi != game_state.current_index:
            return jsonify({'error': 'Not your turn'}), 403

    data = request.get_json()
    action_type = data.get('type')
    target_index = data.get('target_index')

    if action_type == 'attack':
        if target_index is None:
            return jsonify({'error': 'target_index required'}), 400
        result = game_state.action_attack(int(target_index))
    elif action_type == 'change_own_shield':
        result = game_state.action_change_own_shield()
    elif action_type == 'change_opponent_shield':
        if target_index is None:
            return jsonify({'error': 'target_index required'}), 400
        result = game_state.action_change_opponent_shield(int(target_index))
    elif action_type == 'charge':
        result = game_state.action_charge()
    else:
        return jsonify({'error': f'Unknown action: {action_type}'}), 400

    if 'error' in result:
        return jsonify(result), 400

    result['my_player_index'] = session.get('player_index', None)
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
