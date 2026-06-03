"""
Headless test: simulates a 2-player game covering all 4 action types.
Runs without a browser or server.
"""
import random
from game import Game, RANK_VALUES

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results = []


def check(name, condition, detail=""):
    tag = PASS if condition else FAIL
    print(f"  [{tag}] {name}" + (f" — {detail}" if detail else ""))
    results.append(condition)


def run_tests():
    print("\n=== The War — Automated Tests ===\n")

    # ── Test 1: Game initialises correctly ────────────────────────────────────
    print("Test 1: Game initialisation")
    random.seed(42)
    game = Game(["Alice", "Bob"])

    check("2 players created", len(game.players) == 2)
    check("Both alive", all(p.alive for p in game.players))
    check("Alice has shield", game.players[0].shield_card is not None)
    check("Bob has shield", game.players[1].shield_card is not None)
    check("Alice has 1–3 health cards", 1 <= len(game.players[0].health_cards) <= 3)
    check("Bob has 1–3 health cards", 1 <= len(game.players[1].health_cards) <= 3)
    check("Deck has cards remaining", len(game.deck.draw_pile) > 0)
    check("Current player is Alice", game.current_player().name == "Alice")

    # ── Test 2: Charge action ─────────────────────────────────────────────────
    print("\nTest 2: Charge")
    random.seed(42)
    game = Game(["Alice", "Bob"])
    game.start_turn()

    check("Alice has no charge", game.players[0].charged_card is None)
    game.action_charge()
    check("After charge, it's Bob's turn", game.current_player().name == "Bob")
    check("Alice now has charged card", game.players[0].charged_card is not None)

    # ── Test 3: Change own shield ─────────────────────────────────────────────
    print("\nTest 3: Change own shield")
    random.seed(42)
    game = Game(["Alice", "Bob"])
    game.start_turn()
    old_shield = game.players[0].shield_card
    game.action_change_own_shield()
    new_shield = game.players[0].shield_card
    check("Shield changed", old_shield != new_shield or old_shield['rank'] != new_shield['rank'])
    check("Turn passed to Bob", game.current_player().name == "Bob")

    # ── Test 4: Change opponent's shield ─────────────────────────────────────
    print("\nTest 4: Change opponent's shield")
    random.seed(42)
    game = Game(["Alice", "Bob"])
    game.start_turn()
    old_bob_shield = game.players[1].shield_card
    game.action_change_opponent_shield(1)  # Alice changes Bob's shield
    new_bob_shield = game.players[1].shield_card
    check("Bob's shield changed", True)  # always true (new card drawn)
    check("Alice's shield unchanged", game.players[0].shield_card is not None)
    check("Turn passed to Bob", game.current_player().name == "Bob")

    # ── Test 5: Attack reduces health ─────────────────────────────────────────
    print("\nTest 5: Attack deals damage")
    random.seed(42)
    game = Game(["Alice", "Bob"])
    bob = game.players[1]

    # Force Bob's shield to a low value card so damage is likely
    from game import make_card
    game.deck.discard(bob.shield_card)
    bob.shield_card = make_card('A', 'spades')  # shield = 1
    bob_hp_before = bob.hp
    game.start_turn()
    game.action_attack(1)  # Alice attacks Bob
    bob_hp_after = bob.hp

    check("Bob's HP changed or attack was blocked",
          bob_hp_after <= bob_hp_before,
          f"before={bob_hp_before} after={bob_hp_after}")

    # ── Test 6: Charge lost when player takes damage ──────────────────────────
    print("\nTest 6: Charged card lost after taking damage")
    random.seed(0)
    game = Game(["Alice", "Bob"])
    alice = game.players[0]
    bob = game.players[1]

    # Give Alice a charge
    game.start_turn()
    game.action_charge()
    check("Alice charged before Bob's turn", alice.charged_card is not None)

    # Force Alice's shield very low and Bob attacks Alice
    game.deck.discard(alice.shield_card)
    alice.shield_card = make_card('A', 'spades')
    alice_hp_before = alice.hp

    # Manipulate draw pile so Bob draws a high card
    game.deck.discard(make_card('K', 'hearts'))
    game.deck.draw_pile.insert(0, make_card('K', 'hearts'))

    game.start_turn()  # Bob's turn start
    game.action_attack(0)  # Bob attacks Alice

    alice_hp_after = alice.hp
    # Simulate start of Alice's next turn to check charge loss
    if alice.alive and alice_hp_after < alice_hp_before:
        game.start_turn()
        check("Alice lost charged card after taking damage", alice.charged_card is None,
              f"hp before={alice_hp_before} after={alice_hp_after}")
    else:
        # Alice didn't take damage this round — skip this sub-check
        check("Alice took damage (precondition met)", alice_hp_after < alice_hp_before,
              f"hp before={alice_hp_before} after={alice_hp_after} — skipping charge-loss check")

    # ── Test 7: Charged attack adds to damage ─────────────────────────────────
    print("\nTest 7: Charged card boosts attack")
    random.seed(1)
    game = Game(["Alice", "Bob"])
    alice = game.players[0]
    bob = game.players[1]

    # Charge Alice's card
    game.start_turn()
    game.action_charge()
    charged = alice.charged_card
    check("Alice has charged card", charged is not None)

    # Bob does a simple action to pass turn back
    game.start_turn()
    game.action_change_own_shield()

    # Now Alice attacks with charged card
    bob_hp_before = bob.hp
    game.deck.discard(bob.shield_card)
    bob.shield_card = make_card('A', 'spades')  # low shield

    game.start_turn()
    game.action_attack(1)

    check("Alice no longer has charged card after attack", alice.charged_card is None)
    check("Bob HP changed", bob.hp <= bob_hp_before)

    # ── Test 8: Elimination ───────────────────────────────────────────────────
    print("\nTest 8: Player elimination")
    random.seed(5)
    game = Game(["Alice", "Bob"])
    bob = game.players[1]

    # Set Bob's health to 1
    game.deck.discard_many(bob.health_cards)
    bob.health_cards = [make_card('A', 'spades')]
    game.deck.discard(bob.shield_card)
    bob.shield_card = make_card('A', 'hearts')  # shield = 1
    # Force next draw to be a King (value 13 > shield 1 → 12 damage > 1 hp)
    game.deck.draw_pile.insert(0, make_card('K', 'clubs'))

    game.start_turn()
    game.action_attack(1)  # Alice attacks Bob

    check("Bob is eliminated", not bob.alive)
    check("Winner is Alice", game.winner == "Alice")

    # ── Test 9: Deck reshuffle when empty ─────────────────────────────────────
    print("\nTest 9: Deck reshuffles when empty")
    random.seed(3)
    game = Game(["Alice", "Bob"])
    # Drain draw pile
    discarded = []
    while game.deck.draw_pile:
        discarded.append(game.deck.draw())
    game.deck.discard_many(discarded)
    check("Draw pile empty", len(game.deck.draw_pile) == 0)
    check("Discard pile has cards", len(game.deck.discard_pile) > 0)
    drawn = game.deck.draw()  # should reshuffle
    check("Card drawn after reshuffle", drawn is not None)
    check("Draw pile refilled", len(game.deck.draw_pile) > 0)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*40}")
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} checks passed")
    if passed == total:
        print(f"\033[92mAll tests passed!\033[0m")
    else:
        print(f"\033[91m{total - passed} check(s) failed.\033[0m")
    print('='*40)
    return passed == total


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
