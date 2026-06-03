import random
import time
from itertools import combinations

RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
SUITS = ['spades', 'hearts', 'diamonds', 'clubs']
RANK_VALUES = {'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
               '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13}


def make_card(rank, suit):
    return {'rank': rank, 'suit': suit, 'value': RANK_VALUES[rank]}


def card_str(card):
    return f"{card['rank']}{card['suit'][0].upper()}"


class Deck:
    def __init__(self):
        # draw_pile is used as a stack: cards are appended and popped from the end
        self.draw_pile = [make_card(r, s) for s in SUITS for r in RANKS]
        random.shuffle(self.draw_pile)
        self.discard_pile = []

    def draw(self):
        # When the draw pile runs out, reverse the discard pile and reshuffle it
        if not self.draw_pile:
            if not self.discard_pile:
                raise RuntimeError("Both piles are empty")
            self.draw_pile = self.discard_pile[::-1]
            random.shuffle(self.draw_pile)
            self.discard_pile = []
        return self.draw_pile.pop()

    def discard(self, card):
        self.discard_pile.append(card)

    def discard_many(self, cards):
        for c in cards:
            self.discard_pile.append(c)

    def find_cards_for_health(self, target_hp):
        """Find 1–3 cards from available piles that sum to target_hp.
        Tries draw pile first, then discard pile. Returns list of cards drawn.

        Health is always represented by physical cards (not a bare integer), so
        after any HP change we must find real cards whose values sum exactly to
        the new HP total. We search in three passes — 1-card, 2-card, 3-card
        combinations — before falling back to a greedy draw (rarely needed).
        """
        if target_hp <= 0:
            return []

        all_available = self.draw_pile + list(reversed(self.discard_pile))
        values = [c['value'] for c in all_available]

        # Try 1 card
        for i, v in enumerate(values):
            if v == target_hp:
                return [self._take_specific(i, all_available)]

        # Try 2 cards
        for i, j in combinations(range(len(values)), 2):
            if values[i] + values[j] == target_hp:
                # Take higher index first to not shift lower
                c2 = self._take_specific(j, all_available)
                c1 = self._take_specific(i, all_available)
                return [c1, c2]

        # Try 3 cards
        for i, j, k in combinations(range(len(values)), 3):
            if values[i] + values[j] + values[k] == target_hp:
                c3 = self._take_specific(k, all_available)
                c2 = self._take_specific(j, all_available)
                c1 = self._take_specific(i, all_available)
                return [c1, c2, c3]

        # Fallback: just draw cards and return closest (should rarely happen)
        result = []
        remaining = target_hp
        for _ in range(3):
            if remaining <= 0:
                break
            c = self.draw()
            result.append(c)
            remaining -= c['value']
        return result

    def _take_specific(self, idx, all_available):
        # Remove the card from whichever pile it currently lives in
        card = all_available[idx]
        if card in self.draw_pile:
            self.draw_pile.remove(card)
        elif card in self.discard_pile:
            self.discard_pile.remove(card)
        return card

    def to_dict(self):
        return {
            'draw_count': len(self.draw_pile),
            'discard_top': self.discard_pile[-1] if self.discard_pile else None,
            'discard_count': len(self.discard_pile),
        }


class Player:
    def __init__(self, name, health_cards, shield_card):
        self.name = name
        self.health_cards = health_cards
        self.shield_card = shield_card
        self.charged_card = None
        self.health_at_turn_start = sum(c['value'] for c in health_cards)
        self.alive = True

    @property
    def hp(self):
        return sum(c['value'] for c in self.health_cards)

    def to_dict(self, show_charged=True):
        # When show_charged=False (used for all players in the public game state),
        # opponents only see a face-down placeholder for the charged card so they
        # can't read its value — only the current player's own view shows it face-up.
        return {
            'name': self.name,
            'health_cards': self.health_cards,
            'hp': self.hp,
            'shield_card': self.shield_card,
            'charged_card': self.charged_card if show_charged else (
                {'rank': '?', 'suit': 'back', 'value': 0} if self.charged_card else None
            ),
            'health_at_turn_start': self.health_at_turn_start,
            'alive': self.alive,
        }


class Game:
    def __init__(self, player_names):
        self.deck = Deck()
        self.players = []
        self.current_index = 0
        self.winner = None
        self.log = []
        self.last_drawn = []      # cards drawn in the last attack (for reveal animation)
        self.turn_start_time = time.time()  # reset each turn; used for the 40-s LAN timer
        self.lan_mode = False     # set True by app.py when a LAN game is started

        for name in player_names:
            cards = [self.deck.draw() for _ in range(4)]
            # Default shield = highest-value card; the UI immediately calls set_shield()
            # so players can override this choice before the first turn begins.
            shield_idx = max(range(4), key=lambda i: cards[i]['value'])
            shield = cards.pop(shield_idx)
            self.players.append(Player(name, cards, shield))

    def current_player(self):
        return self.players[self.current_index]

    def alive_players(self):
        return [p for p in self.players if p.alive]

    def _next_turn(self):
        count = 0
        while count < len(self.players):
            self.current_index = (self.current_index + 1) % len(self.players)
            if self.players[self.current_index].alive:
                break
            count += 1
        self.turn_start_time = time.time()  # reset timer for the new player's turn

    def _check_win(self):
        alive = self.alive_players()
        if len(alive) == 1:
            self.winner = alive[0].name
            self._log(f"🏆 {self.winner} wins the game!")
            return True
        return False

    def _eliminate(self, player):
        player.alive = False
        player.hp_display = 0
        # Send all their cards to discard
        self.deck.discard_many(player.health_cards)
        player.health_cards = []
        if player.shield_card:
            self.deck.discard(player.shield_card)
            player.shield_card = None
        if player.charged_card:
            self.deck.discard(player.charged_card)
            player.charged_card = None
        self._log(f"💀 {player.name} has been eliminated!")

    def _apply_damage(self, target, damage):
        # Health is stored as physical cards, not a bare integer.  After damage
        # we discard all current health cards and find new ones that sum to the
        # updated HP — this keeps the "cards on the table" representation intact.
        if damage <= 0:
            return
        new_hp = max(0, target.hp - damage)
        self.deck.discard_many(target.health_cards)
        target.health_cards = []
        if new_hp > 0:
            target.health_cards = self.deck.find_cards_for_health(new_hp)

    def _log(self, msg):
        self.log.append(msg)

    # ── Actions ──────────────────────────────────────────────────────────────

    def action_attack(self, target_index):
        cp = self.current_player()
        target = self.players[target_index]
        if not target.alive or target is cp:
            return {'error': 'Invalid target'}

        drawn = self.deck.draw()
        self.deck.discard(drawn)
        attack_value = drawn['value']
        charged_used = None

        # Use charged card if available
        if cp.charged_card:
            charged_used = cp.charged_card
            attack_value += charged_used['value']
            self.deck.discard(charged_used)
            cp.charged_card = None

        # last_drawn is read by the frontend to know which card faces to reveal
        # during the 2-second pause in the attack animation.
        self.last_drawn = [drawn] + ([charged_used] if charged_used else [])

        shield_val = target.shield_card['value'] if target.shield_card else 0
        damage = max(0, attack_value - shield_val)

        msg = f"{cp.name} attacks {target.name} with {card_str(drawn)}"
        if charged_used:
            msg += f" + charged {card_str(charged_used)}"
        msg += f" (total {attack_value} vs shield {shield_val}) → {damage} damage"
        self._log(msg)

        if damage > 0:
            self._apply_damage(target, damage)
            if target.hp <= 0:
                self._eliminate(target)

        if not self._check_win():
            self._next_turn()

        return self.to_dict()

    def action_change_own_shield(self):
        cp = self.current_player()
        if cp.shield_card:
            self.deck.discard(cp.shield_card)
        new_shield = self.deck.draw()
        cp.shield_card = new_shield
        self._log(f"{cp.name} changed their shield to {card_str(new_shield)}")
        self._next_turn()
        return self.to_dict()

    def action_change_opponent_shield(self, target_index):
        cp = self.current_player()
        target = self.players[target_index]
        if not target.alive:
            return {'error': 'Invalid target'}
        if target.shield_card:
            self.deck.discard(target.shield_card)
        new_shield = self.deck.draw()
        target.shield_card = new_shield
        self._log(f"{cp.name} changed {target.name}'s shield to {card_str(new_shield)}")
        self._next_turn()
        return self.to_dict()

    def action_charge(self):
        cp = self.current_player()
        if cp.charged_card:
            return {'error': 'Already have a charged card'}
        card = self.deck.draw()
        cp.charged_card = card
        self._log(f"{cp.name} charged an attack (card hidden)")
        self._next_turn()
        return self.to_dict()

    def auto_skip_turn(self):
        """Skip the current player's turn (called when they time out in LAN mode)."""
        name = self.current_player().name
        self._log(f"⏰ {name}'s turn was skipped (timed out after 40 s)")
        self._next_turn()

    def start_turn(self):
        """Called at the beginning of a player's turn to check charge validity.

        Rule: a charged card is lost if the player took any damage since they
        charged it. We detect this by comparing current HP to hp_at_turn_start,
        which was recorded at the end of the previous turn.
        """
        cp = self.current_player()
        if cp.charged_card and cp.hp < cp.health_at_turn_start:
            self.deck.discard(cp.charged_card)
            cp.charged_card = None
            self._log(f"{cp.name} lost their charged card (took damage last round)")
        cp.health_at_turn_start = cp.hp

    def to_dict(self):
        elapsed = time.time() - self.turn_start_time if self.turn_start_time else 0
        return {
            'players': [p.to_dict(show_charged=False) for p in self.players],
            'current_index': self.current_index,
            'current_player': self.current_player().name,
            'deck': self.deck.to_dict(),
            'winner': self.winner,
            'log': self.log[-20:],  # cap at 20 entries to keep the payload small
            'last_drawn': self.last_drawn,
            # time_remaining is None in hot-seat mode so the frontend hides the timer
            'time_remaining': max(0.0, 40.0 - elapsed) if self.lan_mode else None,
        }

    def set_shield(self, player_index, card_index):
        """During setup: player picks which of their 4 cards is the shield."""
        p = self.players[player_index]
        # card_index refers to index in health_cards; shield_card is also in play
        all_cards = p.health_cards + [p.shield_card]
        chosen = all_cards.pop(card_index)
        old_shield = p.shield_card
        p.shield_card = chosen
        p.health_cards = [c for c in all_cards if c is not old_shield]
        if old_shield is not chosen:
            p.health_cards.append(old_shield)
        p.health_at_turn_start = p.hp
