"""
Generate tutorial PNG images for the War card game launcher.
Run once before building the exe:  python make_tutorial_images.py
"""
from PIL import Image, ImageDraw, ImageFont
import os, sys

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tutorial_images')
os.makedirs(OUT_DIR, exist_ok=True)

W, H = 680, 400

# ── Colour palette (matches the game CSS) ────────────────────────────────────
C_FELT   = '#2d7a3a'
C_DARK   = '#1e5429'
C_GOLD   = '#f4c542'
C_RED    = '#e63946'
C_CARD   = '#fffef5'
C_BACK   = '#1a3a8a'
C_ZONE   = '#1a3319'
C_BORDER = '#4a7a5a'
C_ACTIVE = '#f4c542'
C_TEXT   = '#ffffff'
C_GRAY   = '#aaaaaa'
C_BTN_R  = '#c0392b'
C_BTN_B  = '#2980b9'
C_BTN_P  = '#8e44ad'
C_BTN_O  = '#e67e22'


def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def make_base(title_text):
    img = Image.new('RGB', (W, H), hex2rgb(C_DARK))
    d = ImageDraw.Draw(img)
    # Felt gradient approximation — darker band at top
    for y in range(60):
        frac = y / 60
        r = int(hex2rgb(C_DARK)[0] * (1-frac) + hex2rgb(C_FELT)[0] * frac)
        g = int(hex2rgb(C_DARK)[1] * (1-frac) + hex2rgb(C_FELT)[1] * frac)
        b = int(hex2rgb(C_DARK)[2] * (1-frac) + hex2rgb(C_FELT)[2] * frac)
        d.rectangle([(0, y), (W, y+1)], fill=(r, g, b))
    for y in range(60, H):
        d.rectangle([(0, y), (W, y+1)], fill=hex2rgb(C_FELT))
    # Header bar
    d.rectangle([(0, 0), (W, 38)], fill=hex2rgb(C_DARK))
    d.line([(0, 38), (W, 38)], fill=hex2rgb(C_GOLD), width=2)
    try:
        fnt_title = ImageFont.truetype('arialbd.ttf', 16)
        fnt_sub   = ImageFont.truetype('arial.ttf',   12)
        fnt_card  = ImageFont.truetype('arialbd.ttf', 14)
        fnt_label = ImageFont.truetype('arial.ttf',   11)
        fnt_big   = ImageFont.truetype('arialbd.ttf', 18)
    except Exception:
        fnt_title = fnt_sub = fnt_card = fnt_label = fnt_big = ImageFont.load_default()
    d.text((12, 10), '⚔  The War', fill=hex2rgb(C_GOLD), font=fnt_title)
    d.text((W//2, 10), title_text, fill=hex2rgb(C_GOLD), font=fnt_title, anchor='mt')
    return img, d, {'title': fnt_title, 'sub': fnt_sub, 'card': fnt_card,
                    'label': fnt_label, 'big': fnt_big}


def draw_card(d, x, y, rank, suit, fonts, face_up=True, w=52, h=76):
    """Draw a playing card at (x,y)."""
    red_suits = {'♥', '♦'}
    bg = hex2rgb(C_CARD) if face_up else hex2rgb(C_BACK)
    d.rounded_rectangle([(x, y), (x+w, y+h)], radius=5,
                         fill=bg, outline=hex2rgb(C_BORDER), width=1)
    if face_up:
        color = hex2rgb(C_RED) if suit in red_suits else (20, 20, 46)
        d.text((x+4, y+3),   f'{rank}{suit}', fill=color, font=fonts['card'])
        d.text((x+w//2, y+h//2), suit, fill=color, font=fonts['big'], anchor='mm')


def draw_player_zone(d, x, y, w, h, name, hp, shield, health_cards, fonts,
                     active=False, charged=False):
    border_col = hex2rgb(C_ACTIVE) if active else hex2rgb(C_BORDER)
    d.rounded_rectangle([(x, y), (x+w, y+h)], radius=10,
                         fill=hex2rgb(C_ZONE), outline=border_col, width=2 if active else 1)
    # Name + HP
    d.text((x+w//2, y+10), f'{name}  ❤ {hp}', fill=hex2rgb(C_GOLD),
           font=fonts['title'], anchor='mt')
    # Shield label & card
    d.text((x+8, y+34), 'SHIELD', fill=hex2rgb(C_GRAY), font=fonts['label'])
    if shield:
        draw_card(d, x+8, y+48, shield[0], shield[1], fonts)
    # Health label & cards
    d.text((x+8, y+134), f'HEALTH ({hp})', fill=hex2rgb(C_GRAY), font=fonts['label'])
    cx = x + 8
    for rank, suit in health_cards:
        draw_card(d, cx, y+148, rank, suit, fonts)
        cx += 58
    # Charged
    if charged:
        d.text((x+8, y+234), 'CHARGED ⚡', fill=hex2rgb(C_GRAY), font=fonts['label'])
        draw_card(d, x+8, y+248, '?', '?', fonts, face_up=False)


def draw_btn(d, x, y, w, h, text, color, fonts):
    d.rounded_rectangle([(x, y), (x+w, y+h)], radius=8,
                         fill=hex2rgb(color), outline=(0,0,0,0))
    d.text((x+w//2, y+h//2), text, fill=(255,255,255), font=fonts['label'], anchor='mm')


def annotate(d, x, y, text, fonts, color=C_GOLD, arrow_to=None):
    d.text((x, y), text, fill=hex2rgb(color), font=fonts['sub'])
    if arrow_to:
        d.line([(x, y+8), arrow_to], fill=hex2rgb(color), width=2)
        # Arrowhead
        ax, ay = arrow_to
        d.polygon([(ax-4, ay-6), (ax+4, ay-6), (ax, ay)], fill=hex2rgb(color))


# ── Page 1: Overview ──────────────────────────────────────────────────────────
def page_overview():
    img, d, fonts = make_base('Overview — The Game Board')

    # Draw pile area
    d.rounded_rectangle([(W-120, 8), (W-4, 32)], radius=4,
                         fill=hex2rgb(C_DARK), outline=hex2rgb(C_GOLD), width=1)
    d.text((W-62, 20), '🂠 42 left   |   Discard: 0', fill=hex2rgb(C_GRAY),
           font=fonts['label'], anchor='mm')

    # Two player zones side by side
    draw_player_zone(d, 20, 50, 290, 305, 'Alice', 26,
                     ('9', '♥'), [('6','♠'),('9','♠'),('J','♣')],
                     fonts, active=True)
    draw_player_zone(d, 330, 50, 290, 305, 'Bob', 19,
                     ('A', '♠'), [('5','♦'),('J','♥'),('3','♠')],
                     fonts)

    # Action panel
    d.rectangle([(0, 358), (W, H)], fill=hex2rgb(C_DARK))
    d.line([(0, 358), (W, 358)], fill=hex2rgb(C_GOLD), width=1)
    d.text((W//2, 363), "Alice's turn", fill=hex2rgb(C_GOLD), font=fonts['title'], anchor='mt')

    # Annotation
    annotate(d, 22, 360, '← Active player (gold border)', fonts)

    img.save(os.path.join(OUT_DIR, 'overview.png'))
    print('  overview.png OK')


# ── Page 2: Health & Shield ───────────────────────────────────────────────────
def page_health_shield():
    img, d, fonts = make_base('Health & Shield Explained')

    # Single large player zone
    draw_player_zone(d, 40, 50, 320, 320, 'Alice', 26,
                     ('9', '♥'), [('6','♠'),('9','♠'),('J','♣')], fonts, active=True)

    # Annotations
    annotate(d, 380, 80,  '← Shield card', fonts,
             arrow_to=(96, 86))
    annotate(d, 380, 110, 'Blocks damage equal\nto its value (9 here)', fonts, color=C_GRAY)

    annotate(d, 380, 175, '← Health cards', fonts,
             arrow_to=(100, 200))
    annotate(d, 380, 200, 'Their sum = your HP\n(6+9+11 = 26 here)', fonts, color=C_GRAY)

    annotate(d, 380, 270, 'Shield does NOT break\nafter blocking an attack', fonts, color=C_GRAY)

    # HP formula box
    d.rounded_rectangle([(380, 290), (640, 340)], radius=8,
                         fill=hex2rgb(C_ZONE), outline=hex2rgb(C_GOLD), width=1)
    d.text((510, 315), 'HP = sum of health cards (1–3 cards)',
           fill=hex2rgb(C_TEXT), font=fonts['label'], anchor='mm')

    img.save(os.path.join(OUT_DIR, 'health_shield.png'))
    print('  health_shield.png OK')


# ── Page 3: Actions ───────────────────────────────────────────────────────────
def page_actions():
    img, d, fonts = make_base('Turn Actions')

    # Action buttons row
    btns = [
        ('⚔ Attack',               C_BTN_R, 20),
        ('🛡 Change My Shield',     C_BTN_B, 155),
        ('🔀 Change Opp. Shield',   C_BTN_P, 310),
        ('⚡ Charge',               C_BTN_O, 470),
    ]
    for txt, col, bx in btns:
        draw_btn(d, bx, 50, 155, 34, txt, col, fonts)

    # Attack explanation
    d.rounded_rectangle([(20, 100), (W-20, 195)], radius=8,
                         fill=hex2rgb(C_ZONE), outline=hex2rgb(C_BTN_R), width=1)
    d.text((30, 110), '⚔ Attack', fill=hex2rgb(C_BTN_R), font=fonts['title'])
    d.text((30, 135), 'Draw a card from the pile. Damage = card value − target shield.',
           fill=hex2rgb(C_TEXT), font=fonts['sub'])
    d.text((30, 155), 'Cards fly to the target, are revealed for 2 seconds, then collide.',
           fill=hex2rgb(C_GRAY), font=fonts['label'])
    d.text((30, 172), 'If attack > shield → explosion 💥   |   If attack ≤ shield → shield glows 🛡',
           fill=hex2rgb(C_GRAY), font=fonts['label'])

    # Shield change
    d.rounded_rectangle([(20, 205), (W//2-10, 280)], radius=8,
                         fill=hex2rgb(C_ZONE), outline=hex2rgb(C_BTN_B), width=1)
    d.text((30, 215), '🛡 Change My Shield', fill=hex2rgb(C_BTN_B), font=fonts['title'])
    d.text((30, 238), 'Discard your shield and draw\na new random one from the pile.',
           fill=hex2rgb(C_TEXT), font=fonts['sub'])

    # Change opponent shield
    d.rounded_rectangle([(W//2+10, 205), (W-20, 280)], radius=8,
                         fill=hex2rgb(C_ZONE), outline=hex2rgb(C_BTN_P), width=1)
    d.text((W//2+20, 215), '🔀 Change Opponent Shield', fill=hex2rgb(C_BTN_P), font=fonts['title'])
    d.text((W//2+20, 238), 'Discard an opponent\'s shield\nand replace it with a random card.',
           fill=hex2rgb(C_TEXT), font=fonts['sub'])

    # Charge
    d.rounded_rectangle([(20, 295), (W-20, 375)], radius=8,
                         fill=hex2rgb(C_ZONE), outline=hex2rgb(C_BTN_O), width=1)
    d.text((30, 305), '⚡ Charge', fill=hex2rgb(C_BTN_O), font=fonts['title'])
    d.text((30, 328), 'Draw a secret card face-down next to your health. If you take no damage before your\n'
                       'next turn, add this card\'s value to your next attack. Taking damage loses the charge.',
           fill=hex2rgb(C_TEXT), font=fonts['sub'])
    d.text((30, 364), '🏇 A charged attack triggers the horse battalion charge animation!',
           fill=hex2rgb(C_GOLD), font=fonts['label'])

    img.save(os.path.join(OUT_DIR, 'actions.png'))
    print('  actions.png OK')


# ── Page 4: Charged attack & winning ─────────────────────────────────────────
def page_charge_win():
    img, d, fonts = make_base('Charged Attack & Winning')

    # Alice with charged card
    draw_player_zone(d, 20, 50, 270, 320, 'Alice', 26,
                     ('9', '♥'), [('6','♠'),('9','♠'),('J','♣')],
                     fonts, active=True, charged=True)

    # Bob (low health)
    draw_player_zone(d, 320, 50, 270, 185, 'Bob', 3,
                     ('A', '♠'), [('3','♦')],
                     fonts)

    # Arrow
    d.line([(292, 190), (318, 190)], fill=hex2rgb(C_GOLD), width=3)
    d.polygon([(318, 185), (326, 190), (318, 195)], fill=hex2rgb(C_GOLD))
    d.text((300, 175), 'ATTACK', fill=hex2rgb(C_GOLD), font=fonts['label'], anchor='mm')

    # Charge annotation
    annotate(d, 22, 310, '← Face-down charged card', fonts, arrow_to=(60, 294))
    annotate(d, 22, 330, 'Added to next attack if\nno damage was taken', fonts, color=C_GRAY)

    # Winning box
    d.rounded_rectangle([(320, 250), (W-20, 375)], radius=10,
                         fill=hex2rgb(C_ZONE), outline=hex2rgb(C_GOLD), width=2)
    d.text((W//2 + 80, 262), '🏆 Winning', fill=hex2rgb(C_GOLD),
           font=fonts['big'], anchor='mt')
    d.text((W//2 + 20, 292),
           'Last player with HP > 0 wins.\n\n'
           'HP drops to 0 when:\n  Attack value - Shield value >= HP\n\n'
           "Eliminated players' cards go\nto the discard pile.",
           fill=hex2rgb(C_TEXT), font=fonts['sub'])

    img.save(os.path.join(OUT_DIR, 'charge_win.png'))
    print('  charge_win.png OK')


if __name__ == '__main__':
    print('Generating tutorial images...')
    page_overview()
    page_health_shield()
    page_actions()
    page_charge_win()
    print(f'\nAll 4 images saved to: {OUT_DIR}')
