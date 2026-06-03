# ⚔️ The War — Card Game

A browser-based card game of attack, shields, and strategy for 2–5 players — playable hot-seat (one device) or over a local network.

---

## Demo / Screenshot

> Add a screenshot or GIF of the game here once you have one.
> (`![Gameplay](docs/screenshot.png)`)

---

## What is it?

- **Hot-seat multiplayer** — 2–5 players share one browser window, passing the keyboard between turns
- **LAN multiplayer** — each player connects from their own device; the host is auto-discovered via UDP broadcast
- **Browser-based UI** — players only need a browser; no installation required on their end
- **Shareable Windows .exe** — build a standalone executable and send it to friends

---

## Game Rules

### Setup
Each player receives 4 cards dealt face-up:
- **1 Shield card** — you choose which of the 4 cards becomes your shield
- **3 Health cards** — their values sum to your starting HP

Card values: A = 1, 2–10 = face value, J = 11, Q = 12, K = 13.

### On your turn, choose exactly one action

| Action | Effect |
|---|---|
| **⚔️ Attack** | Draw a card from the pile. Deal `max(0, card_value − target_shield)` damage to a chosen opponent. |
| **🛡️ Change My Shield** | Discard your shield and draw a new one from the pile. |
| **🔀 Change Opponent's Shield** | Discard an opponent's shield and draw them a new random one. |
| **⚡ Charge** | Draw a card face-down and hold it. If you take **no damage** before your next turn, it is added to your next attack as bonus damage. If you take damage, the charged card is lost automatically. |

### Damage & Health
- Damage dealt = `max(0, attack_value − shield_value)`
- The shield does **not** break after blocking — it stays until someone changes it
- Health is always represented by 1–3 cards whose values sum to current HP; cards are swapped to reflect the new total after damage

### Elimination & Winning
- A player is eliminated when their HP reaches 0 or below — all their cards go to the discard pile
- The **last player still alive** wins
- When the draw pile runs out, the discard pile is reshuffled into a new draw pile

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3 + Flask (game logic, REST API, in-memory state) |
| Frontend | Vanilla JS + CSS (single-page app, no framework) |
| Desktop launcher | Tkinter (start/host/join buttons, tutorial window) |
| Distribution | PyInstaller (Windows `.exe` for easy sharing) |

---

## Project Structure

```
fun_project_war_game/
├── app.py               # Flask server + all REST API routes
├── game.py              # Pure game engine (Deck, Player, Game classes)
├── launcher_app.py      # Tkinter desktop launcher + tutorial (PyInstaller entry point)
├── discovery.py         # UDP broadcast/scan for LAN auto-discovery
├── Start_Game.py        # Minimal subprocess launcher (starts server, opens browser)
├── Close_Game.py        # Stops the running server
├── build_exe.py         # PyInstaller build script → dist/war_game_share_me.exe
├── test_game.py         # Headless unit tests (9 tests, no server needed)
├── requirements.txt
├── templates/
│   └── index.html       # Single-page UI (7 screens)
├── static/
│   ├── game.js          # All frontend logic + card animations
│   └── style.css        # Casino green theme + keyframe animations
└── tutorial_images/     # PNG images shown in the in-app tutorial
```

---

## Quick Start

### Hot-Seat (one computer, multiple players)

```bash
# 1. Activate your Python environment (Python 3.10+ recommended)
conda activate HW-Sim2   # or: python -m venv .venv && .venv\Scripts\activate

# 2. Install dependencies
pip install flask

# 3. Start the server
python app.py
# Alternative: python Start_Game.py  (auto-opens the browser for you)

# 4. Open http://localhost:5000 in your browser
```

### LAN Multiplayer (each player on their own device)

1. **Host** — run the Tkinter launcher and click **Host Game (LAN)**:
   ```bash
   pip install flask pillow
   python launcher_app.py
   ```
2. The launcher displays your LAN URL (e.g. `http://192.168.1.10:5000`) — share it with other players
3. **Other players** — open that URL in their browser, enter a name, and wait in the lobby
4. Once everyone has joined, the host clicks **Start Game**
5. Each player picks their shield card privately, then the game begins

### Windows .exe (shareable, no Python needed)

```bash
pip install pyinstaller pillow
python build_exe.py
# Produces dist/war_game_share_me.exe
# Send this single file to anyone — double-click to play
```

---

## Running Tests

```bash
python test_game.py
```

Runs 9 headless unit tests covering: game initialisation, charge, shield changes, attack damage, charge-loss-on-damage, charged attack bonus, player elimination, and deck reshuffle. No browser or server needed.

---

## File Guide

| File | Role |
|---|---|
| `game.py` | Pure game engine — Deck, Player, Game classes; all rule logic lives here |
| `app.py` | Flask server; thin HTTP layer over `game.py`; manages LAN lobby phases |
| `launcher_app.py` | Tkinter launcher window; also the PyInstaller entry point and tutorial viewer |
| `discovery.py` | UDP broadcast (host) and scan (joiner) for automatic LAN game discovery |
| `Start_Game.py` | Minimal launcher: spawns `app.py` in a console, polls until ready, opens browser |
| `build_exe.py` | PyInstaller build script that bundles everything into a single `.exe` |
| `test_game.py` | Self-contained unit tests; imports `game.py` directly |
| `templates/index.html` | The entire UI in one HTML file — 7 `<div>` screens toggled by JS |
| `static/game.js` | Mode detection, game rendering, all 4 action animations, LAN polling |
| `static/style.css` | Green felt theme, card styling, and all CSS keyframe animations |

---

## License

MIT © 2024 — see [LICENSE](LICENSE) for details.
