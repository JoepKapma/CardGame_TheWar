import subprocess
import sys
import time
import webbrowser
import urllib.request
import os

PYTHON = sys.executable
APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
URL = "http://localhost:5000"


def server_ready():
    try:
        urllib.request.urlopen(URL, timeout=1)
        return True
    except Exception:
        return False


if server_ready():
    print("Server already running — opening browser.")
    webbrowser.open(URL)
    sys.exit(0)

print("Starting The War game server...")
subprocess.Popen(
    [PYTHON, APP],
    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
    cwd=os.path.dirname(APP),
)

for _ in range(20):
    time.sleep(0.5)
    if server_ready():
        print("Server started — opening browser.")
        webbrowser.open(URL)
        sys.exit(0)

print("Server did not start in time. Try running app.py manually.")
sys.exit(1)
