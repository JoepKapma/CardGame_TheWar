import subprocess
import sys


def find_pids_on_port(port):
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        pids = set()
        for line in out.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    try:
                        pids.add(int(parts[-1]))
                    except ValueError:
                        pass
        return pids
    except Exception as e:
        print(f"Could not query netstat: {e}")
        return set()


pids = find_pids_on_port(5000)
if not pids:
    print("No game server running on port 5000 — nothing to stop.")
    sys.exit(0)

stopped = False
for pid in pids:
    result = subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    if result.returncode == 0:
        print(f"Game server stopped (PID {pid}).")
        stopped = True

if not stopped:
    print("No game server running on port 5000 — nothing to stop.")
