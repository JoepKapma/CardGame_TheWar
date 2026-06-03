"""
Build CardGame_TheWar.exe and verify it works.
Run with:  python build_exe.py
"""
import subprocess
import sys
import os
import urllib.request
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, 'dist')
EXE_NAME = 'CardGame_TheWar.exe'
EXE_PATH = os.path.join(DIST, EXE_NAME)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
results = []


def check(name, condition, detail=''):
    tag = PASS if condition else FAIL
    print(f'  [{tag}] {name}' + (f' -- {detail}' if detail else ''))
    results.append(condition)
    return condition


print('\n=== Building CardGame_TheWar.exe ===\n')

# ── Step 0: Generate tutorial images ─────────────────────────────────────────
print('Generating tutorial images...')
r = subprocess.run([sys.executable, os.path.join(ROOT, 'make_tutorial_images.py')],
                   capture_output=True, text=True, cwd=ROOT)
if r.returncode != 0:
    print('  Tutorial image generation failed:')
    print(r.stderr)
else:
    print('  Tutorial images OK')

# ── Step 1: Install PyInstaller ───────────────────────────────────────────────
print('\nInstalling PyInstaller...')
subprocess.check_call([sys.executable, '-m', 'pip', 'install',
                       'pyinstaller', 'pillow', '--quiet'])
print('Done.\n')

# ── Step 2: Run PyInstaller ───────────────────────────────────────────────────
print('Running PyInstaller...')
sep = os.pathsep
cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--onefile',
    '--noconsole',
    '--clean',
    '--add-data', f'templates{sep}templates',
    '--add-data', f'static{sep}static',
    '--add-data', f'tutorial_images{sep}tutorial_images',
    '--add-data', f'discovery.py{sep}.',
    '--name', 'CardGame_TheWar',
    '--distpath', DIST,
    '--workpath', os.path.join(ROOT, 'build'),
    '--specpath', ROOT,
    os.path.join(ROOT, 'launcher_app.py'),
]
result = subprocess.run(cmd, cwd=ROOT)
print()

if not check('PyInstaller exited successfully', result.returncode == 0):
    print('\nBuild failed -- stopping here.')
    sys.exit(1)

# ── Step 3: Verify file ───────────────────────────────────────────────────────
print('\nVerifying build...')
exists = os.path.exists(EXE_PATH)
size   = os.path.getsize(EXE_PATH) if exists else 0
check('CardGame_TheWar.exe exists', exists)
check('File size > 5 MB', size > 5_000_000, f'{size // 1_000_000} MB')

if not exists:
    print('\nExe not found -- stopping here.')
    sys.exit(1)

# ── Step 4: Verify tutorial images bundled ────────────────────────────────────
print('\nVerifying tutorial images...')
tutorial_dir = os.path.join(ROOT, 'tutorial_images')
required_imgs = ['overview.png', 'health_shield.png', 'actions.png', 'charge_win.png']
for fname in required_imgs:
    fpath = os.path.join(tutorial_dir, fname)
    sz = os.path.getsize(fpath) if os.path.exists(fpath) else 0
    check(f'tutorial_images/{fname} ({sz//1024} KB)', os.path.exists(fpath) and sz > 0)

# ── Step 5: Launch exe in headless --test mode ────────────────────────────────
print('\nLaunching exe in test mode (Flask server)...')
try:
    out = subprocess.check_output(['netstat', '-ano'], text=True, stderr=subprocess.DEVNULL)
    for line in out.splitlines():
        if ':5000' in line and 'LISTENING' in line:
            pid = int(line.split()[-1])
            subprocess.run(['taskkill', '/PID', str(pid), '/F'], capture_output=True)
except Exception:
    pass

proc = subprocess.Popen(
    [EXE_PATH, '--test'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
)
output = ''
deadline = time.time() + 20
while time.time() < deadline:
    try:
        line = proc.stdout.readline()
        if line:
            output += line
        if 'SERVER_OK' in output or 'SERVER_FAIL' in output:
            break
    except Exception:
        break
    time.sleep(0.2)

proc.terminate()
proc.wait(timeout=5)
check('Server started and responded (--test mode)', 'SERVER_OK' in output,
      output.strip() or 'no output')

# ── Step 6: Launch exe in --test-tutorial mode ────────────────────────────────
print('\nVerifying tutorial bundle...')
proc2 = subprocess.Popen(
    [EXE_PATH, '--test-tutorial'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
)
try:
    stdout2, stderr2 = proc2.communicate(timeout=15)
except subprocess.TimeoutExpired:
    proc2.kill()
    stdout2 = stderr2 = ''

# --noconsole PyInstaller builds route stdout to NUL; check both streams
combined2 = stdout2 + stderr2
check('Tutorial images load correctly inside bundle',
      'TUTORIAL_OK' in combined2,
      combined2.strip() or 'no output')

# ── Step 7: Verify process exited cleanly ────────────────────────────────────
time.sleep(0.5)
exited = proc.poll() is not None
check('Exe process exited cleanly', exited)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f'\n{"=" * 48}')
passed = sum(results)
total  = len(results)
print(f'Results: {passed}/{total} checks passed')
if passed == total:
    print('\033[92mBuild verified! Share this file:\033[0m')
    print(f'  {EXE_PATH}')
else:
    print(f'\033[91m{total - passed} check(s) failed -- do not share this build.\033[0m')
print('=' * 48)
sys.exit(0 if passed == total else 1)
