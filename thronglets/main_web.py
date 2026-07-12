"""Serve Thronglets in a browser - no pygame, no curses, just stdlib + a browser.

Runs the simulation in a background thread and exposes it over plain HTTP:
  GET  /        the page (canvas + controls)
  GET  /state   a JSON snapshot of the world, polled by the page a few times a second
  POST /control start/pause/resume/reset/speed/placing/predator_count/click,
                driven by the page's buttons and clicks

The world doesn't exist until the page's start screen picks automatic or
manual mode - that choice is made once, up front, not toggled mid-run. A
"Notice" button opens an in-page explainer of the mechanics at any time.

No third-party dependencies beyond numpy (for simulation.py) - the server
itself is only the standard library's http.server, so this needs nothing
extra to install anywhere main_tui.py already runs.
"""

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from simulation import DANGER, FOOD, HEIGHT, IDLE, MATE, MAX_POPULATION, World, WIDTH, load_seed_genome

DEFAULT_PORT = 8765
STEP_INTERVAL = 0.05
DEFAULT_INIT_POP = 70
DEFAULT_LANGUAGE_FILE = "language_model.json"
STATE_NAMES = {IDLE: "idle", FOOD: "food-call", MATE: "mate-call", DANGER: "alarm-call"}


def _new_world(mode, predator_count, init_pop=DEFAULT_INIT_POP, seed_genome=None):
    if mode == "manual":
        return World(init_pop=init_pop, manual_food=True, manual_predators=True, seed_genome=seed_genome)
    return World(init_pop=init_pop, predator_count=predator_count, seed_genome=seed_genome)


class SimState:
    def __init__(self, seed_genome=None):
        self.started = False
        self.mode = None
        self.placing = "food"
        self.init_pop = DEFAULT_INIT_POP
        self.world = None
        self.paused = False
        self.speed = 1
        self.cli_seed_genome = seed_genome
        self.active_seed_genome = None
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
        "trained": state.active_seed_genome is not None,
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
        ai_error = None
        with state.lock:
            if action == "start" and not state.started:
                state.mode = "manual" if body.get("mode") == "manual" else "auto"
                try:
                    init_pop = int(body.get("init_pop", DEFAULT_INIT_POP))
                except (TypeError, ValueError):
                    init_pop = DEFAULT_INIT_POP
                state.init_pop = max(1, min(MAX_POPULATION, init_pop))

                if state.cli_seed_genome is not None:
                    state.active_seed_genome = state.cli_seed_genome
                elif body.get("use_ai"):
                    try:
                        state.active_seed_genome = load_seed_genome(DEFAULT_LANGUAGE_FILE)
                    except OSError:
                        state.active_seed_genome = None
                        ai_error = f"'{DEFAULT_LANGUAGE_FILE}' introuvable - lancement sans IA."
                else:
                    state.active_seed_genome = None

                state.world = _new_world(state.mode, 6, state.init_pop, state.active_seed_genome)
                state.started = True
            elif not state.started:
                pass  # ignore every other action until a mode has been chosen
            elif action == "pause":
                state.paused = True
            elif action == "resume":
                state.paused = False
            elif action == "reset":
                state.world = _new_world(state.mode, len(state.world.predators), state.init_pop,
                                          state.active_seed_genome)
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
        self._send(200, "application/json", json.dumps({"ok": True, "error": ai_error}).encode())

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
  #start-overlay label { font-size: 13px; display: flex; align-items: center; justify-content: center; gap: 8px; }
  #initPop { width: 70px; font-family: inherit; font-size: 14px; padding: 4px 6px; }
  #app { display: none; flex-direction: column; align-items: center; gap: 10px; width: 100%; }

  #help-overlay {
    display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    align-items: center; justify-content: center; padding: 16px; z-index: 10;
  }
  #help-panel {
    background: #171d13; border: 1px solid #3a4530; border-radius: 10px;
    max-width: 640px; width: 100%; max-height: 85vh; overflow-y: auto;
    padding: 22px 24px; line-height: 1.6; font-size: 13.5px;
  }
  #help-panel h2 { font-size: 17px; margin: 18px 0 6px; }
  #help-panel h2:first-child { margin-top: 0; }
  #help-panel p, #help-panel li { color: #c3c8b6; margin: 4px 0; }
  #help-panel ul { margin: 4px 0; padding-left: 1.3em; }
  #help-panel .close-row { text-align: right; margin-top: 16px; }
</style>
</head>
<body>
  <div id="start-overlay">
    <h1>Thronglets</h1>
    <p>Choisis le mode de depart - ce choix ne se change pas en cours de partie.</p>
    <label>Nombre de creatures au depart :
      <input type="number" id="initPop" value="70" min="1" max="220">
    </label>
    <label><input type="checkbox" id="useAi"> Activer le langage pre-entraine par IA (language_model.json)</label>
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
      <button id="openHelp">Notice</button>
    </div>
    <div id="controls2">
      <button id="placing">Pose: nourriture</button>
      <button id="predLess">- predateurs</button>
      <button id="predMore">+ predateurs</button>
    </div>
    <canvas id="world" width="900" height="630"></canvas>
    <div id="hint">Clique/touche le monde pour placer de la nourriture (ou un predateur en mode manuel)</div>
  </div>

  <div id="help-overlay">
    <div id="help-panel">
      <h2>Le principe</h2>
      <p>Chaque creature nait avec un genome qui decide quelle couleur elle affiche selon son etat, et comment elle reagit aux couleurs des autres. Personne ne programme le sens des couleurs : un langage commun peut emerger par selection naturelle, ou pas.</p>

      <h2>Les 4 etats, par ordre de priorite</h2>
      <ul>
        <li><strong>danger</strong> — un predateur est repere, fuite immediate</li>
        <li><strong>food-call</strong> — de la nourriture est visible tout pres</li>
        <li><strong>mate-call</strong> — prete a se reproduire, partenaire prete proche</li>
        <li><strong>idle</strong> — rien de special (l'etat le plus frequent, de loin)</li>
      </ul>

      <h2>Vivre, se reproduire, mourir</h2>
      <p>L'energie baisse en permanence, manger la restaure. Emettre une couleur (hors silence) coute un peu d'energie en plus. Assez d'energie et d'age, un partenaire pareil a proximite : un enfant nait. Un predateur qui attrape une creature la tue net.</p>

      <h2>Lire le vocabulaire affiche en haut</h2>
      <p>Pour chaque etat, la part de la population qui utilise chaque couleur. Ca part du hasard (~17%, il y a 6 mots possibles) et grimpe si un mot fait consensus. Les deux points <code>..</code> representent le silence — pas une couleur en moins.</p>

      <h2>A savoir</h2>
      <p>Deux etats peuvent finir sur la meme couleur par hasard (par exemple idle et alarm-call) — rien ne l'empeche ni ne garantit que ca se resolve. Parler coute de l'energie : le silence est une vraie strategie, pas un defaut.</p>

      <div class="close-row"><button id="closeHelp">Fermer</button></div>
    </div>
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
    (state.paused ? "PAUSE" : "x" + state.speed) +
    (state.trained ? "   [vocabulaire entraine]" : "");

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
  const r = await fetch('/control', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(Object.assign({action}, extra || {})),
  });
  return r.json();
}

function stepSpeed(speed, dir) {
  if (dir > 0) return Math.min(200, speed + (speed < 10 ? 1 : 10));
  return Math.max(1, speed - (speed <= 10 ? 1 : 10));
}

function startingInitPop() {
  const raw = parseInt(document.getElementById('initPop').value, 10);
  return Number.isFinite(raw) ? raw : 70;
}
async function startGame(mode) {
  const useAi = document.getElementById('useAi').checked;
  const res = await post('start', {mode, init_pop: startingInitPop(), use_ai: useAi});
  if (res.error) alert(res.error);
}
document.getElementById('startAuto').onclick = () => startGame('auto');
document.getElementById('startManual').onclick = () => startGame('manual');
document.getElementById('pause').onclick = () => post(paused ? 'resume' : 'pause');
document.getElementById('reset').onclick = () => post('reset');
document.getElementById('faster').onclick = () => post('speed', {value: stepSpeed(currentSpeed, 1)});
document.getElementById('slower').onclick = () => post('speed', {value: stepSpeed(currentSpeed, -1)});
document.getElementById('placing').onclick = () => post('placing', {value: placing === 'food' ? 'predator' : 'food'});
document.getElementById('predLess').onclick = () => post('predator_count', {delta: -1});
document.getElementById('predMore').onclick = () => post('predator_count', {delta: 1});

const helpOverlay = document.getElementById('help-overlay');
document.getElementById('openHelp').onclick = () => { helpOverlay.style.display = 'flex'; };
document.getElementById('closeHelp').onclick = () => { helpOverlay.style.display = 'none'; };
helpOverlay.addEventListener('click', (ev) => {
  if (ev.target === helpOverlay) helpOverlay.style.display = 'none';
});

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
    parser = argparse.ArgumentParser(description="Thronglets - web renderer")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--language", type=str, default=None,
                         help="seed the population with a train_language.py --export vocabulary "
                              "instead of starting from scratch")
    args = parser.parse_args()

    seed_genome = load_seed_genome(args.language) if args.language else None
    state = SimState(seed_genome)
    threading.Thread(target=simulation_loop, args=(state,), daemon=True).start()

    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    server.state = state
    print(f"Thronglets running at http://localhost:{args.port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
