# ⚔️ The War — Card Game

A browser-based card game of attack, shields, and strategy for 2–5 players — playable hot-seat (one device) or over a local network.

[![Download](https://img.shields.io/github/v/release/JoepKapma/CardGame_TheWar?label=Download%20.exe)](https://github.com/JoepKapma/CardGame_TheWar/releases/latest)

---

## Screenshot

<img width="1916" height="901" alt="image" src="https://github.com/user-attachments/assets/096985bd-3576-4f81-a08d-431279f9a42a" />

---

## What is it?

- **Hot-seat multiplayer** — 2–5 players share one browser window, passing the keyboard between turns
- **LAN multiplayer** — each player connects from their own device; the host is auto-discovered via UDP broadcast
- **Browser-based UI** — players only need a browser; no installation required on their end
- **Shareable Windows .exe** — one double-click to play, no Python needed

---

## Quick Start

### Windows — no Python needed
Download **[CardGame_TheWar.exe](https://github.com/JoepKapma/CardGame_TheWar/releases/latest)** and double-click it. That's it.

### Hot-seat from source (Python 3.10+)
```bash
pip install flask
python app.py
# Open http://localhost:5000
```

### LAN multiplayer from source
```bash
pip install flask pillow
python launcher_app.py   # click "Host Game (LAN)"
```
1. The launcher shows your LAN URL (e.g. `http://192.168.1.10:5000`) — share it with other players
2. Other players open that URL, enter a name, and wait in the lobby
3. Host clicks **Start Game**; each player picks their shield, then play begins

### Build the .exe yourself
```bash
pip install pyinstaller pillow
python build_exe.py
# Produces dist/CardGame_TheWar.exe
```

---

## File Guide

| File | Role |
|---|---|
| `game.py` | Pure game engine — Deck, Player, Game classes; all rule logic lives here |
| `app.py` | Flask server; thin HTTP layer over `game.py`; manages LAN lobby phases |
| `launcher_app.py` | Tkinter launcher window; also the PyInstaller entry point and tutorial viewer |
| `discovery.py` | UDP broadcast (host) and scan (joiner) for automatic LAN game discovery |
| `Start_Game.py` | Minimal launcher: spawns `app.py`, polls until ready, opens browser |
| `build_exe.py` | PyInstaller build script that bundles everything into a single `.exe` |
| `test_game.py` | Self-contained unit tests; imports `game.py` directly |
| `templates/index.html` | The entire UI in one HTML file — 7 screens toggled by JS |
| `static/game.js` | Mode detection, game rendering, all 4 action animations, LAN polling |
| `static/style.css` | Green felt theme, card styling, and all CSS keyframe animations |

---

## Running Tests

```bash
python test_game.py
```

9 headless unit tests — no browser or server needed.

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
| **⚔️ Attack** | Draw a card. Deal `max(0, card_value − shield_value)` damage to a chosen opponent. |
| **🛡️ Change My Shield** | Discard your shield and draw a new one. |
| **🔀 Change Opponent's Shield** | Discard an opponent's shield and draw them a new one. |
| **⚡ Charge** | Draw a card face-down. If you take **no damage** before your next turn, it is added to your next attack as bonus. Take damage? The charge is lost. |

### Damage & Health
- Damage = `max(0, attack_value − shield_value)`
- The shield does **not** break after blocking — it stays until someone changes it
- Health is represented by 1–3 cards whose values sum to current HP

### Winning
- A player is eliminated when HP ≤ 0
- The **last player still alive** wins
- When the draw pile runs out, the discard pile is reshuffled

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3 + Flask (game logic, REST API, in-memory state) |
| Frontend | Vanilla JS + CSS (single-page app, no framework) |
| Desktop launcher | Tkinter (start/host/join buttons, tutorial window) |
| Distribution | PyInstaller (Windows `.exe` for easy sharing) |

---

## License

MIT © 2024 — see [LICENSE](LICENSE) for details.
