"""
The War — Game Launcher
Tkinter UI that starts/stops the Flask server and opens the browser.
Also used as the PyInstaller entry point for the .exe build.
"""
import sys
import os
import threading
import webbrowser
import time
import urllib.request
import subprocess
import tkinter as tk
import tkinter.messagebox
import tkinter.ttk as ttk


def resource_path(rel):
    """Works for normal runs and PyInstaller --onefile bundles."""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


# Make bundled modules importable
sys.path.insert(0, resource_path('.'))

# Import the Flask app (PyInstaller traces this import to bundle everything)
from app import app as flask_app  # noqa: E402

URL = 'http://localhost:5000'
_server_started = False


def _run_flask():
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


# ── Headless test mode (used by build_exe.py to verify the bundle) ────────────
if '--test' in sys.argv:
    t = threading.Thread(target=_run_flask, daemon=True)
    t.start()
    for _ in range(20):
        time.sleep(0.5)
        try:
            urllib.request.urlopen(URL, timeout=1)
            print('SERVER_OK', flush=True)
            sys.exit(0)
        except Exception:
            pass
    print('SERVER_FAIL', flush=True)
    sys.exit(1)


# ── Tutorial headless test mode ───────────────────────────────────────────────
if '--test-tutorial' in sys.argv:
    try:
        img_dir = resource_path('tutorial_images')
        required = ['overview.png', 'health_shield.png', 'actions.png', 'charge_win.png']
        missing = [f for f in required if not os.path.exists(os.path.join(img_dir, f))]
        if missing:
            sys.stderr.write(f'TUTORIAL_FAIL missing: {missing}\n')
            sys.stderr.flush()
            sys.exit(1)
        from PIL import Image
        for f in required:
            img = Image.open(os.path.join(img_dir, f))
            img.verify()
        sys.stderr.write('TUTORIAL_OK\n')
        sys.stderr.flush()
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f'TUTORIAL_FAIL {e}\n')
        sys.stderr.flush()
        sys.exit(1)


# ── Tutorial window ───────────────────────────────────────────────────────────

TUTORIAL_PAGES = [
    {
        'title': '1 / 4  —  Overview',
        'image': 'overview.png',
        'text': (
            "The War is a hot-seat card game for 2-5 players.\n\n"
            "Each player gets 4 cards:\n"
            "  • 1 Shield card (horizontal, face-up) — blocks incoming damage\n"
            "  • 3 Health cards (face-up) — their sum is your HP\n\n"
            "The draw pile sits in the centre. Discarded cards pile up next to it.\n"
            "The gold-bordered zone shows whose turn it is."
        ),
    },
    {
        'title': '2 / 4  —  Health & Shield',
        'image': 'health_shield.png',
        'text': (
            "Your HP equals the sum of your health cards (1 to 3 cards).\n"
            "When you take damage, cards are swapped to show your new HP total.\n\n"
            "Your shield absorbs damage equal to its card value.\n"
            "  Damage dealt = max(0,  Attack value  -  Shield value)\n\n"
            "The shield does NOT break or get removed after blocking — it stays all game\n"
            "until someone changes it (see Actions)."
        ),
    },
    {
        'title': '3 / 4  —  Turn Actions',
        'image': 'actions.png',
        'text': (
            "On your turn, choose exactly ONE of the four actions:\n\n"
            "  Attack          Draw a card, deal its value minus the target's shield as damage.\n"
            "                  Cards fly to target, are revealed for 2 seconds, then collide!\n\n"
            "  Change My Shield      Discard your shield and draw a new random one.\n\n"
            "  Change Opp. Shield    Discard an opponent's shield and draw them a new one.\n\n"
            "  Charge          Draw a secret face-down card next to your health.\n"
            "                  If you take NO damage before your next turn, add it to your\n"
            "                  next attack. Taking damage? The charge is lost automatically.\n"
            "                  Charged attacks trigger the horse battalion animation! "
        ),
    },
    {
        'title': '4 / 4  —  Charged Attacks & Winning',
        'image': 'charge_win.png',
        'text': (
            "Charged Attack:\n"
            "  First charge on one turn, then attack on the next (if you haven't taken damage).\n"
            "  The drawn card + the charged card are BOTH added together as the attack value.\n"
            "  A cavalry charge animation fires across the screen before the cards fly!\n\n"
            "Winning:\n"
            "  A player is eliminated when their HP drops to 0 or below.\n"
            "  All their cards go to the discard pile.\n"
            "  The LAST player still alive wins the game!"
        ),
    },
]


def open_tutorial(parent):
    try:
        from PIL import Image, ImageTk
    except ImportError:
        tk.messagebox.showinfo('Tutorial', 'Install Pillow to view the tutorial:\n  pip install pillow')
        return

    win = tk.Toplevel(parent)
    win.title('How to Play — The War')
    win.geometry('700x530')
    win.resizable(False, False)
    win.configure(bg='#1e5429')
    win.grab_set()  # modal

    page_idx = [0]
    photo_ref = [None]

    title_lbl = tk.Label(win, text='', font=('Arial', 13, 'bold'),
                         bg='#1e5429', fg='#f4c542')
    title_lbl.pack(pady=(10, 4))

    img_lbl = tk.Label(win, bg='#1e5429')
    img_lbl.pack()

    text_lbl = tk.Label(win, text='', font=('Arial', 9), bg='#1e5429',
                         fg='#cccccc', justify='left', wraplength=660)
    text_lbl.pack(padx=20, pady=(6, 0), anchor='w')

    nav_frame = tk.Frame(win, bg='#1e5429')
    nav_frame.pack(side='bottom', pady=10)

    btn_cfg = dict(font=('Arial', 10, 'bold'), width=12, relief='flat',
                   cursor='hand2', pady=4)
    back_btn = tk.Button(nav_frame, text='◀  Back', bg='#555', fg='white',
                          command=lambda: go(-1), **btn_cfg)
    back_btn.pack(side='left', padx=8)

    page_lbl = tk.Label(nav_frame, text='', font=('Arial', 10),
                         bg='#1e5429', fg='#aaa', width=10)
    page_lbl.pack(side='left')

    next_btn = tk.Button(nav_frame, text='Next  ▶', bg='#27ae60', fg='white',
                          command=lambda: go(+1), **btn_cfg)
    next_btn.pack(side='left', padx=8)

    tk.Button(nav_frame, text='Close', bg='#c0392b', fg='white',
              command=win.destroy, **btn_cfg).pack(side='left', padx=16)

    def show_page(idx):
        page = TUTORIAL_PAGES[idx]
        title_lbl.config(text=page['title'])
        text_lbl.config(text=page['text'])
        page_lbl.config(text=f'{idx+1} / {len(TUTORIAL_PAGES)}')
        back_btn.config(state=tk.NORMAL if idx > 0 else tk.DISABLED)
        next_btn.config(state=tk.NORMAL if idx < len(TUTORIAL_PAGES)-1 else tk.DISABLED)

        img_path = os.path.join(resource_path('tutorial_images'), page['image'])
        if os.path.exists(img_path):
            pil_img = Image.open(img_path)
            pil_img.thumbnail((660, 220), Image.LANCZOS)
            photo = ImageTk.PhotoImage(pil_img)
            photo_ref[0] = photo
            img_lbl.config(image=photo)
        else:
            img_lbl.config(image='', text=f'[image not found: {page["image"]}]',
                           fg='#e74c3c')

    def go(delta):
        page_idx[0] = max(0, min(len(TUTORIAL_PAGES)-1, page_idx[0] + delta))
        show_page(page_idx[0])

    show_page(0)


# ── Join dialog (shown when user clicks Join Game) ───────────────────────────

def open_join_dialog(parent):
    """Scan LAN for a hosted game and open the browser to join."""
    from discovery import scan_for_games

    win = tk.Toplevel(parent)
    win.title('Join Game (LAN)')
    win.geometry('360x260')
    win.resizable(False, False)
    win.configure(bg='#1e5429')
    win.grab_set()

    tk.Label(win, text='Join a LAN Game', font=('Arial', 14, 'bold'),
             bg='#1e5429', fg='#f4c542').pack(pady=(14, 6))

    status_lbl = tk.Label(win, text='🔍 Scanning your network…',
                          font=('Arial', 10), bg='#1e5429', fg='#ccc')
    status_lbl.pack(pady=4)

    # List of found games
    list_frame = tk.Frame(win, bg='#1e5429')
    list_frame.pack(fill='x', padx=20)

    found_var   = tk.StringVar(value=[])
    found_games = []   # list of (ip, port)
    listbox = tk.Listbox(list_frame, listvariable=found_var, height=3,
                         bg='#0d2010', fg='#f4c542', font=('Arial', 10),
                         selectbackground='#27ae60', relief='flat')
    listbox.pack(fill='x')
    listbox.pack_forget()  # hide until results arrive

    # Manual IP fallback
    manual_frame = tk.Frame(win, bg='#1e5429')
    tk.Label(manual_frame, text='Or enter IP manually:', font=('Arial', 9),
             bg='#1e5429', fg='#aaa').pack(side='left')
    ip_var = tk.StringVar()
    ip_entry = tk.Entry(manual_frame, textvariable=ip_var, font=('Arial', 10),
                        bg='#1a2a1a', fg='#fff', insertbackground='#fff',
                        relief='flat', width=14)
    ip_entry.pack(side='left', padx=6)
    manual_frame.pack(pady=(8, 4), padx=20, fill='x')
    manual_frame.pack_forget()

    def join_selected():
        ip = None
        if listbox.curselection():
            idx = listbox.curselection()[0]
            ip, port = found_games[idx]
        elif ip_var.get().strip():
            ip   = ip_var.get().strip()
            port = 5000
        if not ip:
            status_lbl.config(text='⚠️ Select a game or enter an IP.', fg='#e63946')
            return
        win.destroy()
        webbrowser.open(f'http://{ip}:{port}')

    join_btn = tk.Button(win, text='Join ▶', font=('Arial', 11, 'bold'),
                         bg='#27ae60', fg='white', relief='flat', cursor='hand2',
                         pady=6, width=16, command=join_selected)
    join_btn.pack(pady=8)

    def do_scan():
        games = scan_for_games(timeout=2.5)
        win.after(0, lambda: _show_scan_results(games))

    def _show_scan_results(games):
        if not games:
            status_lbl.config(
                text='No game found automatically.\n'
                     'Ask the host for their IP and enter it below\n'
                     '(e.g.  192.168.1.5  — NOT localhost)',
                fg='#f4c542')
            manual_frame.pack(pady=(8, 4), padx=20, fill='x')
        else:
            status_lbl.config(text=f'Found {len(games)} game(s). Select one:', fg='#7fff7f')
            found_games.clear()
            found_games.extend(games)
            found_var.set([f'  {ip}:{port}' for ip, port in games])
            listbox.pack(fill='x')
            listbox.selection_set(0)
            manual_frame.pack(pady=(4, 0), padx=20, fill='x')

    threading.Thread(target=do_scan, daemon=True).start()


# ── GUI ───────────────────────────────────────────────────────────────────────

class WarLauncher:
    def __init__(self, root):
        self.root = root
        self.server_thread = None

        root.title('The War')
        root.geometry('280x355')
        root.resizable(False, False)
        root.configure(bg='#1e5429')

        tk.Label(root, text='The War', font=('Arial', 22, 'bold'),
                 bg='#1e5429', fg='#f4c542').pack(pady=(18, 4))

        self.status_var = tk.StringVar(value='  Stopped')
        tk.Label(root, textvariable=self.status_var, font=('Arial', 10),
                 bg='#1e5429', fg='#cccccc').pack(pady=(0, 8))

        btn_cfg = dict(font=('Arial', 11, 'bold'), width=20,
                       relief='flat', cursor='hand2', pady=5)

        self.start_btn = tk.Button(root, text='Start Game (local)',
                                   command=self.start_game,
                                   bg='#27ae60', fg='white',
                                   activebackground='#2ecc71', **btn_cfg)
        self.start_btn.pack(pady=3)

        self.host_btn = tk.Button(root, text='Host Game (LAN)',
                                  command=self.host_game,
                                  bg='#16a085', fg='white',
                                  activebackground='#1abc9c', **btn_cfg)
        self.host_btn.pack(pady=3)

        tk.Button(root, text='Join Game (LAN)',
                  command=lambda: open_join_dialog(root),
                  bg='#d35400', fg='white',
                  activebackground='#e67e22', **btn_cfg).pack(pady=3)

        tk.Button(root, text='Close Game',
                  command=self.close_game,
                  bg='#c0392b', fg='white',
                  activebackground='#e74c3c', **btn_cfg).pack(pady=3)

        tk.Button(root, text='Tutorial',
                  command=lambda: open_tutorial(root),
                  bg='#8e44ad', fg='white',
                  activebackground='#9b59b6', **btn_cfg).pack(pady=3)

        tk.Button(root, text='Share',
                  command=self.share_game,
                  bg='#2980b9', fg='white',
                  activebackground='#3498db', **btn_cfg).pack(pady=3)

        root.protocol('WM_DELETE_WINDOW', self.close_game)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _server_ready(self, url=URL):
        try:
            urllib.request.urlopen(url, timeout=0.8)
            return True
        except Exception:
            return False

    def _ensure_server_started(self):
        global _server_started
        if not _server_started:
            self.status_var.set('  Starting…')
            self.start_btn.config(state=tk.DISABLED)
            self.host_btn.config(state=tk.DISABLED)
            self.server_thread = threading.Thread(target=_run_flask, daemon=True)
            self.server_thread.start()
            _server_started = True

    def _poll_then_open(self, open_url, attempt=0):
        if self._server_ready():
            self.status_var.set('  Running')
            self.start_btn.config(state=tk.NORMAL)
            self.host_btn.config(state=tk.NORMAL)
            webbrowser.open(open_url)
        elif attempt < 24:
            self.root.after(350, lambda: self._poll_then_open(open_url, attempt + 1))
        else:
            self.status_var.set('  Failed to start')
            self.start_btn.config(state=tk.NORMAL)
            self.host_btn.config(state=tk.NORMAL)

    # ── Actions ───────────────────────────────────────────────────────────────

    def start_game(self):
        """Hot-seat (local) mode — opens localhost."""
        global _server_started
        if _server_started and self._server_ready():
            webbrowser.open(URL)
            return
        self._ensure_server_started()
        self._poll_then_open(URL)

    def host_game(self):
        """LAN host mode — binds to 0.0.0.0, starts broadcaster, opens /host."""
        global _server_started
        self._ensure_server_started()

        def _after_start():
            # Get local IP and start UDP broadcaster
            try:
                from discovery import get_local_ip, start_broadcaster
                local_ip = get_local_ip()
                start_broadcaster(game_port=5000)
            except Exception:
                local_ip = 'localhost'

            open_url = f'http://localhost:5000/host'
            self.status_var.set(f'  Hosting at {local_ip}:5000')
            self._poll_then_open(open_url)

        if _server_started:
            _after_start()
        else:
            self.root.after(400, _after_start)

    def close_game(self):
        self.root.destroy()
        os._exit(0)  # forcefully kill process + all threads (releases port 5000 immediately)

    def share_game(self):
        # Open the GitHub releases page so anyone can download the latest .exe
        webbrowser.open('https://github.com/JoepKapma/CardGame_TheWar/releases/latest')


if __name__ == '__main__':
    root = tk.Tk()
    WarLauncher(root)
    root.mainloop()
