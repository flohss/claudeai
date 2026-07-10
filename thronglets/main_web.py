"""Serve Thronglets in a browser - no pygame, no curses, just stdlib + a browser.

Runs the simulation in a background thread and exposes it over plain HTTP:
  GET  /        the page (canvas + controls)
  GET  /state   a JSON snapshot of the world, polled by the page a few times a second
  POST /control start/pause/resume/reset/speed/placing/predator_count/click,
                driven by the page's buttons and clicks

The world doesn't exist until the page's start screen picks automatic or
manual mode - that choice is made once, up front, not toggled mid-run.

No third-party dependencies beyond numpy (for simulation.py) - the server
itself is only the standard library's http.server, so this needs nothing
extra to install anywhere main_tui.py already runs.
"""

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from simulation import DANGER, FOOD, HEIGHT, IDLE, MATE, World, WIDTH

DEFAULT_PORT = 8765
STEP_INTERVAL = 0.05
STATE_NAMES = {IDLE: "idle", FOOD: "food-call", MATE: "mate-call", DANGER: "alarm-call"}


def _new_world(mode, predator_count):
    if mode == "manual":
        return World(init_pop=70, manual_food=True, manual_predators=True)
    return World(init_pop=70, predator_count=predator_count)


class SimState:
    def __init__(self):
        self.started = False
        self.mode = None
        self.placing = "food"
        self.world = None
        self.paused = False
        self.speed = 1
        self.lock = threading.Lock()


def snapshot(state):
    if not state.started:
        return {"started": False}

    w = state.world
    breakdown = w.vocabulary_breakdown()
    return {
        "started": True,
        "tick": w.tick,
        "pop": w.population(),
        "births": w.births,
        "deaths": w.deaths,
        "paused": state.paused,
        "speed": state.speed,
        "mode": state.mode,
        "placing": state.placing,
        "predator_count": len(w.predators),
        "width": WIDTH,
        "height": HEIGHT,
        "food": [[float(x), float(y)] for x, y in w.food],
        "predators": [[float(p.pos[0]), float(p.pos[1])] for p in w.predators],
        "creatures": [
            {"x": float(c.pos[0]), "y": float(c.pos[1]), "token": c.token}
            for c in w.creatures if c.alive
        ],
        "vocabulary": {
            STATE_NAMES[s]: [[int(t), float(f)] for t, f in breakdown[s]]
            for s in (DANGER, FOOD, MATE, IDLE)
        },
    }


def simulation_loop(state):
    while True:
        with state.lock:
            if state.started and not state.paused:
                for _ in range(state.speed):
                    state.world.step()
        time.sleep(STEP_INTERVAL)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", INDEX_HTML.encode())
        elif self.path == "/state":
            with self.server.state.lock:
                data = snapshot(self.server.state)
            self._send(200, "application/json", json.dumps(data).encode(), no_store=True)
        elif self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self._send(404, "text/plain", b"not found")

    def do_POST(self):
        if self.path != "/control":
            self._send(404, "text/plain", b"not found")
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            body = {}

        state = self.server.state
        action = body.get("action")
        with state.lock:
            if action == "start" and not state.started:
                state.mode = "manual" if body.get("mode") == "manual" else "auto"
                state.world = _new_world(state.mode, 6)
                state.started = True
            elif not state.started:
                pass  # ignore every other action until a mode has been chosen
            elif action == "pause":
                state.paused = True
            elif action == "resume":
                state.paused = False
            elif action == "reset":
                state.world = _new_world(state.mode, len(state.world.predators))
                state.paused = False
            elif action == "speed":
                state.speed = max(1, min(200, int(body.get("value", state.speed))))
            elif action == "placing":
                state.placing = "predator" if body.get("value") == "predator" else "food"
            elif action == "predator_count":
                if int(body.get("delta", 0)) > 0:
                    state.world.add_random_predator()
                else:
                    state.world.remove_predator()
            elif action == "click":
                x, y = float(body.get("x", 0)), float(body.get("y", 0))
                if state.mode == "manual" and state.placing == "predator":
                    state.world.add_predator(x, y)
                else:
                    state.world.add_food(x, y)
        self._send(200, "application/json", b'{"ok":true}')

    def _send(self, code, content_type, body, no_store=False):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if no_store:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


INDEX_HTML = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Thronglets</title>
<style>
  :root { color-scheme: dark; }
  body {
    margin: 0; background: #12160f; color: #dcdcd2;
    font-family: ui-monospace, Menlo, Consolas, monospace;
    display: flex; flex-direction: column; align-items: center;
    padding: 12px; gap: 10px;
  }
  #hud { width: 100%; max-width: 900px; font-size: 13px; line-height: 1.6; }
  .row { white-space: nowrap; overflow-x: auto; }
  .swatch {
    display: inline-block; width: 10px; height: 10px; border-radius: 50%;
    margin-right: 4px; vertical-align: middle;
  }
  #controls { display: flex; gap: 8px; flex-wrap: wrap; }
  button {
    background: #232a1c; color: #dcdcd2; border: 1px solid #3a4530;
    padding: 6px 14px; border-radius: 6px; font-family: inherit; font-size: 13px;
  }
  button:active { background: #3a4530; }
  canvas {
    width: 100%; max-width: 900px; background: #1e2618;
    border-radius: 6px; touch-action: manipulation;
  }
  #hint { font-size: 12px; opacity: 0.6; }
  #start-overlay { display: flex; flex-direction: column; gap: 14px; max-width: 480px; text-align: center; }
  #start-overlay h1 { font-size: 18px; margin: 0; }
  #start-overlay p { font-size: 13px; opacity: 0.8; margin: 0; }
  #start-overlay button { padding: 14px; font-size: 15px; }
  #app { display: none; flex-direction: column; align-items: center; gap: 10px; width: 100%; }
</style>
</head>
<body>
  <div id="start-overlay">
    <h1>Thronglets</h1>
    <p>Choisis le mode de depart - ce choix ne se change pas en cours de partie.</p>
    <button id="startAuto">Automatique — nourriture et predateurs apparaissent seuls</button>
    <button id="startManual">Manuel — je place tout moi-meme</button>
  </div>

  <div id="app">
    <div id="hud">
      <div class="row" id="header"></div>
      <div class="row" id="settings"></div>
      <div class="row" id="vocab-danger"></div>
      <div class="row" id="vocab-food"></div>
      <div class="row" id="vocab-mate"></div>
      <div class="row" id="vocab-idle"></div>
    </div>
    <div id="controls">
      <button id="pause">Pause</button>
      <button id="reset">Reset</button>
      <button id="slower">- vitesse</button>
      <button id="faster">+ vitesse</button>
    </div>
    <div id="controls2">
      <button id="placing">Pose: nourriture</button>
      <button id="predLess">- predateurs</button>
      <button id="predMore">+ predateurs</button>
    </div>
    <canvas id="world" width="900" height="630"></canvas>
    <div id="hint">Clique/touche le monde pour placer de la nourriture (ou un predateur en mode manuel)</div>
  </div>

<script>
const TOKEN_COLORS = ["#a0a0a0", "#eb4646", "#4682eb", "#f5c83c", "#c85ae6", "#46e1d2"];
const FOOD_COLOR = "#6edc5a";
const PREDATOR_COLOR = "#dc1e1e";
const STATE_LABELS = {"alarm-call": "alarm-call", "food-call": "food-call", "mate-call": "mate-call", "idle": "idle"};

const canvas = document.getElementById('world');
const ctx = canvas.getContext('2d');
let worldW = 200, worldH = 140, paused = false, currentSpeed = 1;

let mode = 'auto', placing = 'food', predatorCount = 6;

function render(state) {
  if (!state.started) {
    document.getElementById('start-overlay').style.display = 'flex';
    document.getElementById('app').style.display = 'none';
    return;
  }
  document.getElementById('start-overlay').style.display = 'none';
  document.getElementById('app').style.display = 'flex';

  worldW = state.width; worldH = state.height;
  paused = state.paused; currentSpeed = state.speed;
  mode = state.mode; placing = state.placing; predatorCount = state.predator_count;
  const scale = canvas.width / worldW;
  canvas.height = worldH * scale;

  ctx.fillStyle = "#1e2618";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = FOOD_COLOR;
  for (const [x, y] of state.food) {
    ctx.beginPath();
    ctx.arc(x * scale, y * scale, 2.5, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.fillStyle = PREDATOR_COLOR;
  for (const [x, y] of state.predators) {
    ctx.beginPath();
    ctx.arc(x * scale, y * scale, 6, 0, Math.PI * 2);
    ctx.fill();
  }

  for (const c of state.creatures) {
    ctx.fillStyle = TOKEN_COLORS[c.token] || TOKEN_COLORS[0];
    ctx.beginPath();
    ctx.arc(c.x * scale, c.y * scale, 4, 0, Math.PI * 2);
    ctx.fill();
  }

  document.getElementById('header').textContent =
    `tick ${state.tick}   pop ${state.pop}   births ${state.births}   deaths ${state.deaths}   ` +
    (state.paused ? "PAUSE" : "x" + state.speed);

  renderVocabRow('vocab-danger', 'alarm-call', state.vocabulary['alarm-call']);
  renderVocabRow('vocab-food', 'food-call', state.vocabulary['food-call']);
  renderVocabRow('vocab-mate', 'mate-call', state.vocabulary['mate-call']);
  renderVocabRow('vocab-idle', 'idle', state.vocabulary['idle']);

  document.getElementById('pause').textContent = state.paused ? 'Reprendre' : 'Pause';

  document.getElementById('settings').textContent = mode === 'manual'
    ? `mode: manuel   pose: ${placing === 'food' ? 'nourriture' : 'predateur'}`
    : `mode: auto   predateurs: ${predatorCount} (+/- agit tout de suite)`;
  document.getElementById('placing').textContent = placing === 'food' ? 'Pose: nourriture' : 'Pose: predateur';
  document.getElementById('placing').style.display = mode === 'manual' ? 'inline-block' : 'none';
}

function renderVocabRow(elId, label, pairs) {
  const el = document.getElementById(elId);
  el.innerHTML = '';
  const labelSpan = document.createElement('span');
  labelSpan.textContent = label + ': ';
  labelSpan.style.fontWeight = 'bold';
  el.appendChild(labelSpan);
  for (const [token, frac] of pairs) {
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = TOKEN_COLORS[token];
    if (token === 0) sw.style.border = '1px solid #666';
    el.appendChild(sw);
    const txt = document.createElement('span');
    txt.textContent = Math.round(frac * 100) + '%  ';
    el.appendChild(txt);
  }
}

async function poll() {
  try {
    const r = await fetch('/state');
    render(await r.json());
  } catch (e) { /* server warming up, try again next tick */ }
}

async function post(action, extra) {
  await fetch('/control', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(Object.assign({action}, extra || {})),
  });
}

function stepSpeed(speed, dir) {
  if (dir > 0) return Math.min(200, speed + (speed < 10 ? 1 : 10));
  return Math.max(1, speed - (speed <= 10 ? 1 : 10));
}

document.getElementById('startAuto').onclick = () => post('start', {mode: 'auto'});
document.getElementById('startManual').onclick = () => post('start', {mode: 'manual'});
document.getElementById('pause').onclick = () => post(paused ? 'resume' : 'pause');
document.getElementById('reset').onclick = () => post('reset');
document.getElementById('faster').onclick = () => post('speed', {value: stepSpeed(currentSpeed, 1)});
document.getElementById('slower').onclick = () => post('speed', {value: stepSpeed(currentSpeed, -1)});
document.getElementById('placing').onclick = () => post('placing', {value: placing === 'food' ? 'predator' : 'food'});
document.getElementById('predLess').onclick = () => post('predator_count', {delta: -1});
document.getElementById('predMore').onclick = () => post('predator_count', {delta: 1});

canvas.addEventListener('click', (ev) => {
  const rect = canvas.getBoundingClientRect();
  const px = (ev.clientX - rect.left) * (canvas.width / rect.width);
  const py = (ev.clientY - rect.top) * (canvas.height / rect.height);
  const scale = canvas.width / worldW;
  post('click', {x: px / scale, y: py / scale});
});

setInterval(poll, 100);
poll();
</script>
</body>
</html>
"""


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    state = SimState()
    threading.Thread(target=simulation_loop, args=(state,), daemon=True).start()

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    server.state = state
    print(f"Thronglets running at http://localhost:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
