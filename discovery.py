"""
LAN game discovery — UDP broadcast/scan so joiners find the host automatically.
Used by launcher_app.py.
"""
import socket
import json
import threading

DISCOVERY_PORT = 5001
MAGIC = b'WARGAME_DISCOVER'
_broadcaster_started = False


def get_local_ip():
    """Return the LAN-reachable IP of this machine.

    Connecting a UDP socket to an external address (8.8.8.8) without actually
    sending data causes the OS to select the correct outbound interface.
    getsockname() then reveals which local IP would be used — this is the address
    other machines on the same network can reach us at.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return '127.0.0.1'


def start_broadcaster(game_port=5000):
    """Start a daemon thread that responds to UDP discovery pings.

    Protocol: joiner sends MAGIC bytes → host replies with JSON {port, game}.
    The thread is a daemon so it exits automatically when the launcher process ends,
    releasing the UDP port without needing explicit cleanup.
    """
    global _broadcaster_started
    if _broadcaster_started:
        return
    _broadcaster_started = True

    def _run():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', DISCOVERY_PORT))
            while True:
                try:
                    data, addr = sock.recvfrom(64)
                    if data.strip() == MAGIC:
                        reply = json.dumps({'port': game_port, 'game': 'The War'}).encode()
                        sock.sendto(reply, addr)
                except Exception:
                    pass
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


def scan_for_games(timeout=2.5):
    """Broadcast a discovery ping; return list of (ip, port) tuples found.

    Sends MAGIC to the subnet broadcast address (255.255.255.255) so every host
    on the LAN receives it.  Replies are collected until the socket times out,
    so multiple hosts can be found in a single scan.
    """
    found = []
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        sock.sendto(MAGIC, ('255.255.255.255', DISCOVERY_PORT))
        while True:
            try:
                data, addr = sock.recvfrom(256)
                info = json.loads(data.decode())
                entry = (addr[0], info.get('port', 5000))
                if entry not in found:
                    found.append(entry)
            except socket.timeout:
                break
            except Exception:
                pass
    except Exception:
        pass
    return found
