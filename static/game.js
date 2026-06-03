let state = null;
let pendingAction = null;
let shieldSetupQueue = [];
let shieldSetupIndex = 0;
let isAnimating = false;

// LAN mode
let isLan = false;
let myPlayerIndex = null;
let pollInterval = null;

const SUIT_SYMBOLS = { spades: '♠', hearts: '♥', diamonds: '♦', clubs: '♣' };
const RED_SUITS = new Set(['hearts', 'diamonds']);

// ── Mode detection (runs on page load) ──────────────────────────────────────

async function initMode() {
  // Three branches:
  // 1. No lobby active (phase === null)  → hot-seat mode, show normal setup screen
  // 2. LAN lobby/shield_setup phase      → show join/lobby/waiting screens as appropriate
  // 3. LAN playing phase                 → jump straight into the game (page reload case)
  let status;
  try {
    const r = await fetch('/lan_status');
    status = await r.json();
  } catch (e) {
    show('setup-screen');
    buildNameInputs();
    return;
  }

  if (!status.phase) {
    // Hot-seat mode — normal setup screen
    show('setup-screen');
    buildNameInputs();
    return;
  }

  // LAN mode
  isLan = true;
  myPlayerIndex = status.my_player_index;

  if (status.phase === 'lobby') {
    if (myPlayerIndex === null || myPlayerIndex === undefined) {
      showJoinScreen(status);
    } else {
      showLobbyScreen(status);
      startLanPolling();
    }
  } else if (status.phase === 'shield_setup') {
    if (!status.my_shield_done && myPlayerIndex !== null) {
      // Fetch game state so we can show the shield cards
      state = await (await fetch('/state')).json();
      showLanShieldSetup(myPlayerIndex);
    } else {
      showWaiting('Waiting…', 'Waiting for other players to pick their shields…');
      startLanPolling();
    }
  } else if (status.phase === 'playing') {
    state = await (await fetch('/state')).json();
    show('game-screen');
    renderState();
    startGamePolling();
  }
}

window.addEventListener('DOMContentLoaded', initMode);

// ── Join Screen ──────────────────────────────────────────────────────────────

function showJoinScreen(status) {
  const subtitle = document.getElementById('join-subtitle');
  if (status.is_host || status.host_pending) {
    subtitle.textContent = 'You are the host — enter your name to continue';
  } else {
    subtitle.textContent = 'Join the game';
  }
  show('join-screen');
}

async function joinLobby() {
  const nameEl = document.getElementById('join-name');
  const errEl  = document.getElementById('join-error');
  const name   = nameEl.value.trim();
  errEl.style.display = 'none';

  if (!name) { errEl.textContent = 'Please enter your name.'; errEl.style.display = ''; return; }

  const r = await fetch('/join_lobby', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name })
  });
  const data = await r.json();
  if (!r.ok) { errEl.textContent = data.error || 'Could not join.'; errEl.style.display = ''; return; }

  myPlayerIndex = data.player_index;
  const lobbyData = await (await fetch('/lan_status')).json();
  showLobbyScreen(lobbyData);
  startLanPolling();
}

// ── Lobby Screen ─────────────────────────────────────────────────────────────

function showLobbyScreen(status) {
  show('lobby-screen');

  // Build player list
  const ul = document.getElementById('lobby-player-list');
  ul.innerHTML = (status.lobby_players || [])
    .map((n, i) => `<li>${i === 0 ? '👑 ' : ''}${n}</li>`).join('');

  // Show URL box only to host (player 0)
  const urlBox = document.getElementById('lobby-url-box');
  if (status.my_player_index === 0) {
    urlBox.style.display = '';
    // Fetch the real LAN IP (not localhost) so the host can share the correct link
    fetch('/host_ip').then(r => r.json()).then(data => {
      document.getElementById('lobby-url').textContent = data.url;
    }).catch(() => {
      document.getElementById('lobby-url').textContent = window.location.origin;
    });
  } else {
    urlBox.style.display = 'none';
  }

  // Show start button only to host, and only when ≥ 2 players
  const startBtn = document.getElementById('start-lan-btn');
  const waitMsg  = document.getElementById('lobby-wait-msg');
  if (status.my_player_index === 0 && (status.lobby_players || []).length >= 2) {
    startBtn.classList.remove('hidden');
    waitMsg.classList.add('hidden');
  } else if (status.my_player_index === 0) {
    startBtn.classList.add('hidden');
    waitMsg.textContent = 'Waiting for at least one more player to join…';
    waitMsg.classList.remove('hidden');
  } else {
    startBtn.classList.add('hidden');
    waitMsg.classList.remove('hidden');
  }
}

async function startLanGame() {
  const r = await fetch('/start_lan_game', { method: 'POST' });
  const data = await r.json();
  if (!r.ok) { alert(data.error || 'Could not start game.'); return; }
  // Polling will detect shield_setup phase and transition everyone
}

// ── Waiting Screen ────────────────────────────────────────────────────────────

function showWaiting(title, msg) {
  document.getElementById('waiting-title').textContent = title;
  document.getElementById('waiting-msg').textContent   = msg;
  show('waiting-screen');
}

// ── LAN polling ───────────────────────────────────────────────────────────────

// startLanPolling: used during lobby and shield_setup phases.
// startGamePolling: used once the game is running.
// Two separate functions exist so that shield_setup can clear the lobby poll
// and start a fresh game poll without ambiguity — both use the same pollInterval var.
function startLanPolling() {
  if (pollInterval) return;
  pollInterval = setInterval(async () => {
    const r = await fetch('/lan_status');
    const status = await r.json();
    myPlayerIndex = status.my_player_index;

    if (status.phase === 'playing') {
      clearInterval(pollInterval); pollInterval = null;
      state = await (await fetch('/state')).json();
      show('game-screen');
      renderState();
      startGamePolling();
    } else if (status.phase === 'shield_setup') {
      if (!status.my_shield_done && myPlayerIndex !== null) {
        clearInterval(pollInterval); pollInterval = null;
        state = await (await fetch('/state')).json();
        showLanShieldSetup(myPlayerIndex);
      } else {
        const done  = (status.shields_done || []).length;
        const total = (status.lobby_players || []).length;
        showWaiting('✓ Shield chosen!',
          `Waiting for ${total - done} more player(s) to pick their shield…`);
      }
    } else if (status.phase === 'lobby') {
      showLobbyScreen(status);
    }
  }, 2000);
}

function startGamePolling() {
  if (pollInterval) return;
  pollInterval = setInterval(async () => {
    try {
      const r = await fetch('/state');
      const newState = await r.json();
      if (newState.error) return;
      state = newState;
      renderState();
    } catch (e) { /* server unreachable */ }
  }, 2000);
}

// ── LAN shield setup ──────────────────────────────────────────────────────────

function showLanShieldSetup(playerIdx) {
  // Build a single-item queue so the existing hot-seat logic works for just this player
  shieldSetupQueue = [playerIdx];
  shieldSetupIndex = 0;
  // Hide the hot-seat "pass the computer" hint
  document.getElementById('shield-hint').style.display = 'none';
  showShieldSetup();
}

// ── Setup ────────────────────────────────────────────────────────────────────

document.getElementById('player-count').addEventListener('change', buildNameInputs);

function buildNameInputs() {
  const n = parseInt(document.getElementById('player-count').value);
  const container = document.getElementById('name-inputs');
  container.innerHTML = '';
  for (let i = 0; i < n; i++) {
    const label = document.createElement('label');
    label.textContent = `Player ${i + 1} name:`;
    const input = document.createElement('input');
    input.type = 'text';
    input.value = `Player ${i + 1}`;
    input.id = `pname-${i}`;
    label.appendChild(input);
    container.appendChild(label);
  }
}

async function startGame() {
  const n = parseInt(document.getElementById('player-count').value);
  const players = [];
  for (let i = 0; i < n; i++) {
    const v = document.getElementById(`pname-${i}`).value.trim();
    players.push(v || `Player ${i + 1}`);
  }
  const resp = await fetch('/new_game', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ players })
  });
  state = await resp.json();
  shieldSetupQueue = players.map((_, i) => i);
  shieldSetupIndex = 0;
  document.getElementById('shield-hint').style.display = '';
  showShieldSetup();
}

function showShieldSetup() {
  if (shieldSetupIndex >= shieldSetupQueue.length) {
    if (isLan) {
      // Done with my shield — wait for others
      showWaiting('✓ Shield chosen!', 'Waiting for other players to pick their shields…');
      startLanPolling();
    } else {
      show('game-screen');
      renderState();
    }
    return;
  }
  const pi = shieldSetupQueue[shieldSetupIndex];
  const player = state.players[pi];
  document.getElementById('shield-player-name').textContent =
    isLan ? `${player.name} — choose your shield` : `${player.name} — Choose your shield`;

  const allCards = [...player.health_cards, player.shield_card];
  const container = document.getElementById('shield-card-choices');
  container.innerHTML = '';
  allCards.forEach((card, idx) => {
    const el = makeCardEl(card);
    el.classList.add('clickable');
    el.title = 'Click to make this your shield';
    el.addEventListener('click', () => pickShield(pi, idx));
    container.appendChild(el);
  });

  show('shield-screen');
}

async function pickShield(playerIndex, cardIndex) {
  const resp = await fetch('/set_shield', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ player_index: playerIndex, card_index: cardIndex })
  });
  state = await resp.json();
  shieldSetupIndex++;
  showShieldSetup();
}

// ── Game rendering ────────────────────────────────────────────────────────────

// Hides every screen div, then un-hides the one with the given id.
// All screen transitions go through this so no stale screen is ever left visible.
function show(id) {
  ['setup-screen', 'join-screen', 'lobby-screen', 'waiting-screen',
   'shield-screen', 'game-screen', 'winner-screen'].forEach(s => {
    document.getElementById(s).classList.toggle('hidden', s !== id);
  });
}

function renderState() {
  if (!state) return;

  if (state.winner) {
    document.getElementById('winner-name').textContent = `🏆 ${state.winner} wins!`;
    show('winner-screen');
    if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
    return;
  }

  document.getElementById('draw-count').textContent = state.deck.draw_count;
  document.getElementById('discard-count').textContent = state.deck.discard_count;
  const discardTopEl = document.getElementById('discard-top');
  if (state.deck.discard_top) {
    renderCardInto(discardTopEl, state.deck.discard_top);
  } else {
    discardTopEl.className = 'card small';
    discardTopEl.innerHTML = '<span style="color:#888;font-size:0.7rem;text-align:center;margin:auto">Empty</span>';
  }

  const area = document.getElementById('players-area');
  area.innerHTML = '';
  state.players.forEach((p, i) => {
    area.appendChild(makePlayerZone(p, i));
  });

  document.getElementById('turn-label').textContent = `${state.current_player}'s turn`;

  // LAN mode: show/hide action panel based on whose turn it is
  if (isLan) {
    const isMyTurn = state.current_index === myPlayerIndex;
    document.getElementById('action-buttons').style.display = isMyTurn ? 'flex' : 'none';
    document.getElementById('target-row').classList.add('hidden');
    const waitBanner = document.getElementById('lan-wait-banner');
    if (isMyTurn) {
      waitBanner.classList.add('hidden');
    } else {
      waitBanner.classList.remove('hidden');
      document.getElementById('lan-wait-player').textContent = state.current_player;
    }
  }

  // Turn timer (LAN mode)
  updateTurnTimer(state.time_remaining);

  const logEl = document.getElementById('log-entries');
  logEl.innerHTML = state.log.slice().reverse().map(l => `<div>${l}</div>`).join('');

  cancelAction();
  setButtonsEnabled(!isAnimating);
  // Charge button: must come AFTER setButtonsEnabled (or it gets re-enabled)
  const cp = state.players[state.current_index];
  document.querySelector('.btn-charge').disabled = !!cp.charged_card || isAnimating;
}

function updateTurnTimer(timeRemaining) {
  const el = document.getElementById('turn-timer');
  if (timeRemaining !== null && timeRemaining !== undefined && timeRemaining <= 10) {
    el.classList.remove('hidden');
    document.getElementById('timer-seconds').textContent = Math.ceil(timeRemaining);
  } else {
    el.classList.add('hidden');
  }
}

function makePlayerZone(player, index) {
  const zone = document.createElement('div');
  zone.className = 'player-zone' + (index === state.current_index ? ' current' : '') + (!player.alive ? ' dead' : '');
  zone.dataset.player = index;

  const nameEl = document.createElement('div');
  nameEl.className = 'player-name';
  // Highlight "you" in LAN mode
  const youLabel = isLan && index === myPlayerIndex ? ' <span style="color:#7fff7f;font-size:0.75rem">(you)</span>' : '';
  nameEl.innerHTML = player.alive
    ? `${player.name}${youLabel} <span class="hp-label">❤️ ${player.hp}</span>`
    : `${player.name}${youLabel} <span class="dead-label">💀 Dead</span>`;
  zone.appendChild(nameEl);

  // Shield
  const shLabel = document.createElement('div');
  shLabel.className = 'section-label';
  shLabel.textContent = 'Shield';
  zone.appendChild(shLabel);
  const shRow = document.createElement('div');
  shRow.className = 'card-row';
  shRow.dataset.role = 'shield';
  if (player.shield_card) shRow.appendChild(makeCardEl(player.shield_card));
  zone.appendChild(shRow);

  // Health cards
  const hLabel = document.createElement('div');
  hLabel.className = 'section-label';
  hLabel.textContent = `Health (${player.hp})`;
  zone.appendChild(hLabel);
  const hRow = document.createElement('div');
  hRow.className = 'card-row';
  hRow.dataset.role = 'health';
  player.health_cards.forEach(c => hRow.appendChild(makeCardEl(c)));
  zone.appendChild(hRow);

  // Charged card
  if (player.charged_card) {
    const cLabel = document.createElement('div');
    cLabel.className = 'section-label';
    cLabel.textContent = 'Charged ⚡';
    zone.appendChild(cLabel);
    const cRow = document.createElement('div');
    cRow.className = 'card-row charged-zone';
    cRow.dataset.role = 'charged';
    const isCurrent = index === state.current_index;
    if (isCurrent && player.charged_card.suit !== 'back') {
      cRow.appendChild(makeCardEl(player.charged_card));
    } else {
      const back = document.createElement('div');
      back.className = 'card card-back';
      cRow.appendChild(back);
    }
    zone.appendChild(cRow);
  }

  return zone;
}

function makeCardEl(card) {
  const el = document.createElement('div');
  renderCardInto(el, card);
  return el;
}

function renderCardInto(el, card) {
  if (!card || card.suit === 'back') {
    el.className = 'card card-back';
    el.innerHTML = '';
    return;
  }
  const isRed = RED_SUITS.has(card.suit);
  el.className = 'card ' + (isRed ? 'red' : 'black');
  const sym = SUIT_SYMBOLS[card.suit] || '?';
  el.innerHTML = `
    <div class="rank-top">${card.rank}${sym}</div>
    <div class="suit-mid">${sym}</div>
    <div class="rank-bot">${card.rank}${sym}</div>
  `;
}

// ── Animation helpers ─────────────────────────────────────────────────────────

function setButtonsEnabled(enabled) {
  document.querySelectorAll('.action-buttons .btn').forEach(b => {
    b.disabled = !enabled;
  });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

/** Fly a card clone from sourceEl's rect to destEl's rect. Returns Promise. */
function flyCard(sourceEl, destEl, duration = 450, opts = {}) {
  return new Promise(resolve => {
    if (!sourceEl || !destEl) { resolve(); return; }
    const srcRect = sourceEl.getBoundingClientRect();
    const dstRect = destEl.getBoundingClientRect();
    const clone = sourceEl.cloneNode(true);
    clone.classList.add('card-flying');
    clone.classList.remove('clickable');
    clone.style.left   = srcRect.left + 'px';
    clone.style.top    = srcRect.top + 'px';
    clone.style.width  = srcRect.width + 'px';
    clone.style.height = srcRect.height + 'px';
    clone.style.transition = `left ${duration}ms ease, top ${duration}ms ease, opacity ${duration}ms ease, transform ${duration}ms ease`;
    document.body.appendChild(clone);
    // Double rAF: the first frame lets the browser paint the clone at the start
    // position; the second frame kicks off the CSS transition to the destination.
    // Without both frames the browser batches the style changes and skips the animation.
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        clone.style.left = dstRect.left + 'px';
        clone.style.top  = dstRect.top + 'px';
        if (opts.fade)  clone.style.opacity = '0';
        if (opts.scale) clone.style.transform = `scale(${opts.scale})`;
        setTimeout(() => { clone.remove(); resolve(); }, duration + 50);
      });
    });
  });
}

/** Temporarily add a CSS class to el, then remove after duration ms. */
function triggerClass(el, cls, duration) {
  return new Promise(resolve => {
    if (!el) { resolve(); return; }
    el.classList.add(cls);
    setTimeout(() => { el.classList.remove(cls); resolve(); }, duration);
  });
}

function getPlayerZone(idx) {
  return document.querySelector(`.player-zone[data-player="${idx}"]`);
}
function getShieldEl(playerIdx) {
  return getPlayerZone(playerIdx)?.querySelector('[data-role="shield"] .card') ?? null;
}
function getHealthZone(playerIdx) {
  return getPlayerZone(playerIdx)?.querySelector('[data-role="health"]') ?? null;
}
function getChargedEl(playerIdx) {
  return getPlayerZone(playerIdx)?.querySelector('[data-role="charged"] .card') ?? null;
}

// ── Horse battalion for charged attacks ───────────────────────────────────────

function animateHorseCharge() {
  return new Promise(resolve => {
    const div = document.createElement('div');
    div.className = 'horse-charge';
    div.innerHTML = '🐴🤺&nbsp;&nbsp;🐴🤺&nbsp;&nbsp;🐴🤺&nbsp;&nbsp;<span style="font-family:sans-serif;font-weight:900;color:#f4c542;font-size:1.2em">⚔️ CHARGE! ⚔️</span>';
    document.body.appendChild(div);
    setTimeout(() => { div.remove(); resolve(); }, 1300);
  });
}

// ── Attack animation with reveal pause ───────────────────────────────────────

// 5-step attack animation:
//   0. Horse charge banner (charged attacks only)
//   1. Fly card-back clones from draw pile (+ charged zone) to reveal spot above target
//   2. Flip clones face-up to show the drawn card value
//   3. Pause 2 seconds so all players can read the attack value
//   4. Collide cards into shield (blocked) or health zone (damage dealt)
//   5. Impact effect — shield bump+glow or 💥 crack overlay on health zone
async function animateAttack(attackerIdx, targetIdx, oldState, newState) {
  const drawEl     = document.getElementById('draw-pile-card');
  const chargedEl  = getChargedEl(attackerIdx);
  const targetZone = getPlayerZone(targetIdx);
  const shieldEl   = getShieldEl(targetIdx);
  const healthZone = getHealthZone(targetIdx);

  const oldHp    = oldState.players[targetIdx]?.hp ?? 0;
  const newHp    = newState.players[targetIdx]?.hp ?? 0;
  const didDamage = newHp < oldHp;
  const isCharged = !!chargedEl || !!oldState.players[attackerIdx]?.charged_card;

  // ── Step 0: Horse charge (only for charged attacks) ───────────────────────
  if (isCharged) {
    await animateHorseCharge();
  }

  // ── Step 1: Fly card-backs to a reveal spot (centre of target zone) ───────
  const zoneRect = targetZone?.getBoundingClientRect() ?? { left: window.innerWidth/2, top: window.innerHeight/2, width: 0, height: 0 };
  const revealX = zoneRect.left + zoneRect.width / 2 - 35;
  const revealY = zoneRect.top + 10;

  const drawnCards  = newState.last_drawn || [];
  const cardSources = [drawEl, chargedEl].filter(Boolean);

  const cardFlyers = [];
  for (let i = 0; i < cardSources.length; i++) {
    const src = cardSources[i];
    if (!src) continue;
    const clone = src.cloneNode(true);
    clone.classList.add('card-flying');
    clone.classList.remove('clickable');
    const srcRect = src.getBoundingClientRect();
    clone.style.left   = srcRect.left + 'px';
    clone.style.top    = srcRect.top  + 'px';
    clone.style.width  = srcRect.width + 'px';
    clone.style.height = srcRect.height + 'px';
    clone.style.transition = 'left 0.45s ease, top 0.45s ease';
    document.body.appendChild(clone);
    cardFlyers.push({ clone, srcRect, offsetX: i * 14 });
  }

  // Fly all to reveal spot
  await new Promise(r => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        cardFlyers.forEach(({ clone, offsetX }) => {
          clone.style.left = (revealX + offsetX) + 'px';
          clone.style.top  = revealY + 'px';
        });
        setTimeout(r, 500);
      });
    });
  });

  // ── Step 2: Flip cards to face-up ─────────────────────────────────────────
  cardFlyers.forEach(({ clone }, i) => {
    const card = drawnCards[i];
    if (!card) return;
    // Save inline position before renderCardInto resets className
    const savedLeft   = clone.style.left;
    const savedTop    = clone.style.top;
    const savedWidth  = clone.style.width;
    const savedHeight = clone.style.height;
    // renderCardInto overwrites el.className entirely — must restore after
    renderCardInto(clone, card);
    clone.classList.add('card-flying', 'card-reveal', 'card-flip');
    Object.assign(clone.style, {
      position:   'fixed',
      left:       savedLeft,
      top:        savedTop,
      width:      savedWidth,
      height:     savedHeight,
      transition: '',
      zIndex:     '1100',
    });
  });

  await sleep(320);  // let flip animate

  // ── Step 3: Pause 2 seconds so players can read the attack value ──────────
  await sleep(2000);

  // ── Step 4: Collide into shield or health ─────────────────────────────────
  const collideDest = didDamage
    ? (healthZone?.firstElementChild ?? healthZone)
    : shieldEl;

  if (collideDest) {
    const destRect = collideDest.getBoundingClientRect();
    await new Promise(r => {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          cardFlyers.forEach(({ clone }) => {
            clone.style.transition = 'left 0.4s ease, top 0.4s ease, opacity 0.4s ease';
            clone.style.left    = destRect.left + 'px';
            clone.style.top     = destRect.top  + 'px';
            clone.style.opacity = '0';
          });
          setTimeout(r, 450);
        });
      });
    });
  }

  cardFlyers.forEach(({ clone }) => clone.remove());

  // ── Step 5: Impact effect ─────────────────────────────────────────────────
  if (didDamage) {
    if (healthZone) {
      const crack = document.createElement('div');
      crack.className = 'crack-overlay';
      crack.textContent = '💥';
      healthZone.appendChild(crack);
      await sleep(700);
      crack.remove();
    }
  } else {
    if (shieldEl) {
      await Promise.all([
        triggerClass(shieldEl, 'shield-bump', 500),
        triggerClass(shieldEl, 'shield-glow', 550),
      ]);
    }
  }
}

// ── Shield-change animation ───────────────────────────────────────────────────

async function animateShieldChange(playerIdx) {
  const shieldEl  = getShieldEl(playerIdx);
  const discardEl = document.getElementById('discard-top');
  const drawEl    = document.getElementById('draw-pile-card');
  const shieldRow = getPlayerZone(playerIdx)?.querySelector('[data-role="shield"]');

  if (shieldEl && discardEl) {
    await flyCard(shieldEl, discardEl, 400, { fade: true });
  }
  if (drawEl && shieldRow) {
    const tempBack = document.createElement('div');
    tempBack.className = 'card card-back';
    shieldRow.appendChild(tempBack);
    await flyCard(drawEl, tempBack, 400);
    tempBack.remove();
  }
}

// ── Charge animation ──────────────────────────────────────────────────────────

async function animateCharge(playerIdx) {
  const drawEl = document.getElementById('draw-pile-card');
  const zone   = getPlayerZone(playerIdx);
  const destEl = zone?.querySelector('[data-role="health"]') ?? zone;
  if (drawEl && destEl) {
    await flyCard(drawEl, destEl, 400, { fade: true });
  }
}

// ── Dispatcher ────────────────────────────────────────────────────────────────

async function animateForAction(type, body, oldState, newState) {
  if (!type || !oldState) return;
  const currentIdx = oldState.current_index;

  if (type === 'change_own_shield') {
    await animateShieldChange(currentIdx);
  } else if (type === 'change_opponent_shield') {
    await animateShieldChange(body.target_index);
  } else if (type === 'attack') {
    await animateAttack(currentIdx, body.target_index, oldState, newState);
  } else if (type === 'charge') {
    await animateCharge(currentIdx);
  }
}

// ── Actions ───────────────────────────────────────────────────────────────────

function doAction(type) {
  if (isAnimating) return;
  // In LAN mode, only act on your turn
  if (isLan && state && state.current_index !== myPlayerIndex) return;

  pendingAction = type;
  const needsTarget = type === 'attack' || type === 'change_opponent_shield';

  if (needsTarget) {
    const select = document.getElementById('target-select');
    select.innerHTML = '';
    state.players.forEach((p, i) => {
      if (i !== state.current_index && p.alive) {
        const opt = document.createElement('option');
        opt.value = i;
        opt.textContent = p.name;
        select.appendChild(opt);
      }
    });
    document.getElementById('target-row').classList.remove('hidden');
  } else {
    confirmAction();
  }
}

async function confirmAction() {
  const type = pendingAction;
  if (!type || isAnimating) return;

  const body = { type };
  const needsTarget = type === 'attack' || type === 'change_opponent_shield';
  if (needsTarget) {
    body.target_index = parseInt(document.getElementById('target-select').value);
  }

  cancelAction();
  isAnimating = true;
  setButtonsEnabled(false);

  const oldState = state;

  // /start_turn must be called before /action: the server uses it to check
  // whether the charged card should be discarded (player took damage last turn).
  await fetch('/start_turn', { method: 'POST' });
  const resp = await fetch('/action', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const newState = await resp.json();

  await animateForAction(type, body, oldState, newState);

  state = newState;
  // In LAN mode, my_player_index comes back in action response
  if (newState.my_player_index !== undefined) myPlayerIndex = newState.my_player_index;
  isAnimating = false;
  renderState();
}

function cancelAction() {
  pendingAction = null;
  document.getElementById('target-row').classList.add('hidden');
}
