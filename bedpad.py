import argparse
import ctypes
import html
import json
import secrets
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


USER32 = ctypes.windll.user32
KERNEL32 = ctypes.windll.kernel32

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_CODES = {
    "enter": 0x0D,
    "backspace": 0x08,
    "tab": 0x09,
    "escape": 0x1B,
    "space": 0x20,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "delete": 0x2E,
}


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("union", INPUTUNION)]


def send_inputs(items):
    array = (INPUT * len(items))(*items)
    sent = USER32.SendInput(len(items), array, ctypes.sizeof(INPUT))
    if sent != len(items):
        raise ctypes.WinError()


def mouse_move(dx, dy):
    send_inputs([
        INPUT(type=INPUT_MOUSE, union=INPUTUNION(mi=MOUSEINPUT(dx, dy, 0, MOUSEEVENTF_MOVE, 0, None)))
    ])


def mouse_click(button):
    if button == "right":
        down, up = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    else:
        down, up = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
    send_inputs([
        INPUT(type=INPUT_MOUSE, union=INPUTUNION(mi=MOUSEINPUT(0, 0, 0, down, 0, None))),
        INPUT(type=INPUT_MOUSE, union=INPUTUNION(mi=MOUSEINPUT(0, 0, 0, up, 0, None))),
    ])


def mouse_wheel(delta):
    send_inputs([
        INPUT(type=INPUT_MOUSE, union=INPUTUNION(mi=MOUSEINPUT(0, 0, delta, MOUSEEVENTF_WHEEL, 0, None)))
    ])


def key_press(name):
    key = VK_CODES.get(name.lower())
    if key is None:
        raise ValueError(f"Unsupported key: {name}")
    send_inputs([
        INPUT(type=INPUT_KEYBOARD, union=INPUTUNION(ki=KEYBDINPUT(key, 0, 0, 0, None))),
        INPUT(type=INPUT_KEYBOARD, union=INPUTUNION(ki=KEYBDINPUT(key, 0, KEYEVENTF_KEYUP, 0, None))),
    ])


def type_text(text):
    events = []
    for ch in text:
        code = ord(ch)
        events.append(INPUT(type=INPUT_KEYBOARD, union=INPUTUNION(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, None))))
        events.append(INPUT(type=INPUT_KEYBOARD, union=INPUTUNION(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None))))
    if events:
        send_inputs(events)


def set_clipboard(text):
    GMEM_MOVEABLE = 0x0002
    CF_UNICODETEXT = 13
    data = text.encode("utf-16-le") + b"\x00\x00"
    if not USER32.OpenClipboard(None):
        raise ctypes.WinError()
    try:
        USER32.EmptyClipboard()
        handle = KERNEL32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not handle:
            raise ctypes.WinError()
        locked = KERNEL32.GlobalLock(handle)
        ctypes.memmove(locked, data, len(data))
        KERNEL32.GlobalUnlock(handle)
        if not USER32.SetClipboardData(CF_UNICODETEXT, handle):
            raise ctypes.WinError()
    finally:
        USER32.CloseClipboard()


def local_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


PAGE = """<!doctype html>
<html lang="zh-Hant">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<title>BedPad</title>
<style>
  :root { color-scheme: dark; --bg:#0f1216; --panel:#171d25; --line:#2f3b49; --text:#edf2f7; --muted:#94a3b8; --accent:#5eead4; --tap:#263241; }
  * { box-sizing:border-box; -webkit-tap-highlight-color: transparent; }
  html, body { height:100%; overscroll-behavior:none; }
  body { margin:0; font-family: system-ui, Segoe UI, sans-serif; background:var(--bg); color:var(--text); overflow:hidden; }
  main { height:100dvh; display:grid; grid-template-rows:auto 1fr auto; gap:10px; padding: max(12px, env(safe-area-inset-top)) 12px max(12px, env(safe-area-inset-bottom)); }
  header { display:flex; align-items:center; justify-content:space-between; gap:10px; }
  h1 { font-size:18px; margin:0; letter-spacing:0; }
  #status { color:var(--muted); font-size:13px; min-width:8em; text-align:right; }
  #pad { position:relative; touch-action:none; border:1px solid var(--line); background:radial-gradient(circle at 50% 35%, #1d2732, #151b22 70%); border-radius:8px; min-height:0; display:grid; place-items:center; color:var(--muted); user-select:none; overflow:hidden; }
  #pad.active { background:radial-gradient(circle at 50% 35%, #243345, #151b22 72%); }
  #pad::after { content:""; position:absolute; inset:18px; border:1px dashed rgba(148,163,184,.22); border-radius:8px; pointer-events:none; }
  .hint { text-align:center; line-height:1.8; font-size:14px; z-index:1; }
  .dock { display:grid; grid-template-columns:repeat(5, 1fr); gap:8px; }
  button, textarea { border-radius:8px; border:1px solid var(--line); background:var(--panel); color:var(--text); font:inherit; }
  button { min-height:48px; padding:10px 8px; font-weight:650; }
  button:active { background:var(--tap); transform:translateY(1px); }
  #sheet { position:fixed; left:0; right:0; bottom:0; padding:12px max(12px, env(safe-area-inset-right)) max(12px, env(safe-area-inset-bottom)) max(12px, env(safe-area-inset-left)); background:#111820; border-top:1px solid var(--line); transform:translateY(105%); transition:transform .16s ease-out; box-shadow:0 -18px 40px rgba(0,0,0,.38); }
  #sheet.open { transform:translateY(0); }
  textarea { width:100%; min-height:110px; padding:12px; resize:none; font-size:16px; line-height:1.4; }
  .sheetbar { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-top:8px; }
</style>
<main>
  <header>
    <h1>BedPad</h1>
    <div id="status">Ready</div>
  </header>
  <div id="pad">
    <div class="hint">
      單指移動游標<br>
      短按左鍵 · 長按右鍵 · 雙擊打字<br>
      雙指滑動滾頁
    </div>
  </div>
  <nav class="dock">
    <button onclick="post('/key?key=backspace'); pulse('Backspace')">⌫</button>
    <button onclick="post('/key?key=escape'); pulse('Esc')">Esc</button>
    <button onclick="post('/key?key=space'); pulse('Space')">Space</button>
    <button onclick="post('/key?key=enter'); pulse('Enter')">Enter</button>
    <button onclick="openSheet()">Text</button>
  </nav>
</main>
<section id="sheet">
  <textarea id="text" autocomplete="off" autocapitalize="sentences" placeholder="輸入要送到電腦目前焦點的文字"></textarea>
  <div class="sheetbar">
    <button onclick="sendText('/type')">送出</button>
    <button onclick="post('/key?key=enter'); pulse('Enter')">Enter</button>
    <button onclick="closeSheet()">收起</button>
  </div>
</section>
<script>
const token = new URLSearchParams(location.search).get('token');
const pad = document.getElementById('pad');
const sheet = document.getElementById('sheet');
const text = document.getElementById('text');
const statusEl = document.getElementById('status');
const pointers = new Map();
let primary = null;
let lastTap = 0;
let holdTimer = null;
let longPressed = false;
let moved = false;
let lastScrollCenterY = null;
let scrollRemainder = 0;
const tapMoveLimit = 10;
const longPressMs = 520;
const scrollPixelsPerStep = 42;
async function post(path, body) {
  const url = path + (path.includes('?') ? '&' : '?') + 'token=' + encodeURIComponent(token);
  try { await fetch(url, { method:'POST', body: body || '', keepalive:true }); }
  catch { pulse('Offline'); }
}
function sendText(path) {
  const value = text.value;
  if (!value) return;
  post(path, value);
  text.value = '';
  closeSheet();
  pulse('Typed');
}
function pulse(label) {
  statusEl.textContent = label;
  clearTimeout(window.statusTimer);
  window.statusTimer = setTimeout(() => statusEl.textContent = 'Ready', 900);
}
function openSheet() {
  sheet.classList.add('open');
  setTimeout(() => text.focus(), 80);
  pulse('Text');
}
function closeSheet() {
  sheet.classList.remove('open');
  text.blur();
}
function clearHold() {
  clearTimeout(holdTimer);
  holdTimer = null;
}
function scrollCenterY() {
  let sum = 0;
  for (const point of pointers.values()) sum += point.y;
  return sum / pointers.size;
}
function resetScroll() {
  lastScrollCenterY = pointers.size >= 2 ? scrollCenterY() : null;
  scrollRemainder = 0;
}
pad.addEventListener('contextmenu', e => e.preventDefault());
pad.addEventListener('pointerdown', e => {
  e.preventDefault();
  pad.classList.add('active');
  pad.setPointerCapture(e.pointerId);
  pointers.set(e.pointerId, { x:e.clientX, y:e.clientY, startX:e.clientX, startY:e.clientY });
  if (pointers.size === 1) {
    primary = e.pointerId;
    moved = false;
    longPressed = false;
    holdTimer = setTimeout(() => {
      if (!moved && pointers.has(primary)) {
        longPressed = true;
        post('/click?button=right');
        navigator.vibrate?.(18);
        pulse('Right click');
      }
    }, longPressMs);
  } else {
    clearHold();
    resetScroll();
  }
});
pad.addEventListener('pointerup', e => {
  e.preventDefault();
  clearHold();
  const info = pointers.get(e.pointerId);
  pointers.delete(e.pointerId);
  if (pointers.size === 0) {
    pad.classList.remove('active');
    primary = null;
    resetScroll();
    if (info && !moved && !longPressed) {
      const now = performance.now();
      if (now - lastTap < 310) {
        lastTap = 0;
        openSheet();
      } else {
        lastTap = now;
        post('/click?button=left');
        pulse('Click');
      }
    }
  }
});
pad.addEventListener('pointercancel', e => {
  clearHold();
  pointers.delete(e.pointerId);
  if (pointers.size === 0) pad.classList.remove('active');
  resetScroll();
});
pad.addEventListener('pointermove', e => {
  e.preventDefault();
  const info = pointers.get(e.pointerId);
  if (!info) return;
  const dxRaw = e.clientX - info.x;
  const dyRaw = e.clientY - info.y;
  info.x = e.clientX;
  info.y = e.clientY;
  const distance = Math.hypot(e.clientX - info.startX, e.clientY - info.startY);
  if (distance > tapMoveLimit) {
    moved = true;
    clearHold();
  }
  if (pointers.size >= 2) {
    const centerY = scrollCenterY();
    const dy = lastScrollCenterY === null ? 0 : centerY - lastScrollCenterY;
    lastScrollCenterY = centerY;
    scrollRemainder += dy;
    const steps = Math.trunc(scrollRemainder / scrollPixelsPerStep);
    if (steps !== 0) {
      scrollRemainder -= steps * scrollPixelsPerStep;
      post('/wheel?delta=' + (-steps * 120));
      pulse('Scroll');
    }
    return;
  }
  if (e.pointerId !== primary) return;
  const dx = Math.round(dxRaw * 1.45);
  const dy = Math.round(dyRaw * 1.45);
  if (dx || dy) post('/move?dx=' + dx + '&dy=' + dy);
});
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) sendText('/type');
  if (e.key === 'Escape') closeSheet();
});
</script>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "BedPad/0.1.0"

    def log_message(self, fmt, *args):
        return

    def auth_ok(self, query):
        return query.get("token", [""])[0] == self.server.token

    def send_json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path != "/" or not self.auth_ok(query):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return
        data = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if not self.auth_ok(query):
            self.send_json(403, {"ok": False, "error": "bad token"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            if parsed.path == "/move":
                mouse_move(int(query.get("dx", ["0"])[0]), int(query.get("dy", ["0"])[0]))
            elif parsed.path == "/click":
                mouse_click(query.get("button", ["left"])[0])
            elif parsed.path == "/wheel":
                mouse_wheel(int(query.get("delta", ["0"])[0]))
            elif parsed.path == "/key":
                key_press(query.get("key", [""])[0])
            elif parsed.path == "/type":
                type_text(body)
            elif parsed.path == "/clipboard":
                set_clipboard(body)
            else:
                self.send_json(404, {"ok": False, "error": "unknown endpoint"})
                return
            self.send_json(200, {"ok": True})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description="BedPad: use your phone browser as a Windows touchpad.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", default=secrets.token_urlsafe(9))
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.token = args.token
    url = f"http://{local_ip()}:{args.port}/?token={html.escape(args.token)}"
    print("BedPad is running.")
    print(url)
    print("Keep this window open. Press Ctrl+C to stop.")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        httpd.shutdown()
        print("\nStopped.")


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("This MVP uses Windows SendInput and must run on Windows.")
    main()
