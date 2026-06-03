# The War — Card Game

Hot-seat multiplayer card game for 2–5 players, playable in a local browser.

## Stack
- **Backend:** Python + Flask (game logic, API)
- **Frontend:** Vanilla JS + CSS (no framework)
- **State:** In-memory (no database)

## Project Structure
```
fun_project/
├── app.py           # Flask app + API routes
├── game.py          # Game engine (deck, players, rules)
├── test_game.py     # Headless automated tests
├── requirements.txt
├── templates/
│   └── index.html   # Single-page UI
└── static/
    ├── style.css
    └── game.js
```

## How to Run
```bash
conda activate HW-Sim2
pip install flask
python app.py
# Open http://localhost:5000
```

## How to Test
```bash
conda activate HW-Sim2
python test_game.py
```

## Game Rules Summary
- Each player gets 4 cards: 3 face-up as health (sum = HP), 1 face-up as shield
- Turn actions (pick one):
  1. **Attack** — draw a card, deal damage = max(0, card_value - target_shield) to a target's health
  2. **Change own shield** — discard shield, draw new one
  3. **Change opponent's shield** — discard their shield, draw new one for them
  4. **Charge** — place a face-down card; if HP unchanged by next turn, add it to your next attack
- Health is always represented by 1–3 cards whose values sum to current HP
- Player eliminated when HP ≤ 0; last player alive wins
- Card values: A=1, 2–10=face, J=11, Q=12, K=13
- Empty draw pile → shuffle discard pile → new draw pile
