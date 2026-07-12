"""Serve Thronglets in a browser - no pygame, no curses, just stdlib + a browser.

Runs the simulation in a background thread and exposes it over plain HTTP:
  GET  /        the page (canvas + controls)
  GET  /state   a JSON snapshot of the world, polled by the page a few times a second
  POST /control start/pause/resume/reset/speed/placing/predator_count/click,
                driven by the page's buttons and clicks

The world doesn't exist until the page's start screen picks a language,
automatic or manual mode, and whether to seed the AI language - those
choices are made once, up front, not toggled mid-run. A "Notice"/"Help"
button opens an in-page explainer of the mechanics at any time. All UI
text (including the state names like food-call/mate-call) is translated
client-side between English and French; the server only ever deals in
fixed internal ids (idle/food/mate/danger).

No third-party dependencies beyond numpy (for simulation.py) - the server
itself is only the standard library's http.server, so this needs nothing
extra to install anywhere main_tui.py already runs.
"""

import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from simulation import (DANGER, DISTRESS, FOOD, HEIGHT, IDLE, MATE, MAX_POPULATION, World, WIDTH,
                         load_seed_genome, load_world, save_world)

DEFAULT_PORT = 8765
STEP_INTERVAL = 0.05
DEFAULT_INIT_POP = 70
DEFAULT_LANGUAGE_FILE = "language_model.json"
DEFAULT_SAVE_FILE = "thronglets_save.json"
STATE_IDS = {IDLE: "idle", FOOD: "food", MATE: "mate", DANGER: "danger", DISTRESS: "distress"}


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
        return {"started": False, "save_exists": os.path.exists(DEFAULT_SAVE_FILE)}

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
            STATE_IDS[s]: [[int(t), float(f)] for t, f in breakdown[s]]
            for s in (DANGER, FOOD, DISTRESS, MATE, IDLE)
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
        error_code = None
        with state.lock:
            if action == "start" and not state.started and body.get("resume_save"):
                try:
                    state.world = load_world(DEFAULT_SAVE_FILE)
                    state.mode = "manual" if (state.world.manual_food or state.world.manual_predators) else "auto"
                    state.init_pop = state.world.population()
                    state.active_seed_genome = None
                    state.started = True
                except (OSError, ValueError, KeyError):
                    error_code = "resume_failed"
            elif action == "start" and not state.started:
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
                        error_code = "ai_missing"
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
            elif action == "save":
                save_world(state.world, DEFAULT_SAVE_FILE)
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
        error_file = DEFAULT_SAVE_FILE if error_code == "resume_failed" else DEFAULT_LANGUAGE_FILE
        self._send(200, "application/json",
                   json.dumps({"ok": True, "error": error_code, "file": error_file}).encode())

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

  #langToggle { display: flex; gap: 8px; justify-content: center; }
  .lang-btn { padding: 6px 14px; font-size: 13px; opacity: 0.6; }
  .lang-btn.active { opacity: 1; border-color: #6edc5a; }

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
  <div id="langToggle">
    <button id="langEn" class="lang-btn">English</button>
    <button id="langFr" class="lang-btn">Francais</button>
  </div>
  <div id="start-overlay">
    <h1 data-i18n="title"></h1>
    <p data-i18n="startPrompt"></p>
    <label>
      <span data-i18n="initPopLabel"></span>
      <input type="number" id="initPop" value="70" min="1" max="220">
    </label>
    <label><input type="checkbox" id="useAi"> <span data-i18n="useAiLabel"></span></label>
    <button id="startAuto" data-i18n="startAuto"></button>
    <button id="startManual" data-i18n="startManual"></button>
    <button id="startResume" data-i18n="resumeSaveText" style="display:none"></button>
  </div>

  <div id="app">
    <div id="hud">
      <div class="row" id="header"></div>
      <div class="row" id="settings"></div>
      <div class="row" id="vocab-danger"></div>
      <div class="row" id="vocab-food"></div>
      <div class="row" id="vocab-distress"></div>
      <div class="row" id="vocab-mate"></div>
      <div class="row" id="vocab-idle"></div>
    </div>
    <div id="controls">
      <button id="pause"></button>
      <button id="reset" data-i18n="resetText"></button>
      <button id="slower" data-i18n="slowerText"></button>
      <button id="faster" data-i18n="fasterText"></button>
      <button id="save" data-i18n="saveText"></button>
      <button id="openHelp" data-i18n="noticeText"></button>
    </div>
    <div id="controls2">
      <button id="placing"></button>
      <button id="predLess" data-i18n="predLessText"></button>
      <button id="predMore" data-i18n="predMoreText"></button>
    </div>
    <canvas id="world" width="900" height="630"></canvas>
    <div id="hint" data-i18n="hint"></div>
  </div>

  <div id="help-overlay">
    <div id="help-panel">
      <h2 data-i18n="helpH1"></h2>
      <p data-i18n="helpP1"></p>

      <h2 data-i18n="helpH2"></h2>
      <ul>
        <li><strong data-i18n="stateDanger"></strong> — <span data-i18n="stateDangerDesc"></span></li>
        <li><strong data-i18n="stateFood"></strong> — <span data-i18n="stateFoodDesc"></span></li>
        <li><strong data-i18n="stateDistress"></strong> — <span data-i18n="stateDistressDesc"></span></li>
        <li><strong data-i18n="stateMate"></strong> — <span data-i18n="stateMateDesc"></span></li>
        <li><strong data-i18n="stateIdle"></strong> — <span data-i18n="stateIdleDesc"></span></li>
      </ul>

      <h2 data-i18n="helpH3"></h2>
      <p data-i18n="helpP3"></p>

      <h2 data-i18n="helpH4"></h2>
      <p data-i18n="helpP4"></p>

      <h2 data-i18n="helpH5"></h2>
      <p data-i18n="helpP5"></p>

      <div class="close-row"><button id="closeHelp" data-i18n="closeText"></button></div>
    </div>
  </div>

<script>
const TOKEN_COLORS = ["#a0a0a0", "#eb4646", "#4682eb", "#f5c83c", "#c85ae6", "#46e1d2"];
const FOOD_COLOR = "#6edc5a";
const PREDATOR_COLOR = "#dc1e1e";

const STRINGS = {
  en: {
    title: "Thronglets",
    startPrompt: "Choose the starting mode - this choice does not change during the game.",
    initPopLabel: "Number of creatures to start with:",
    useAiLabel: "Activate the pre-trained AI language (language_model.json)",
    startAuto: "Automatic — food and predators spawn on their own",
    startManual: "Manual — I place everything myself",
    resumeSaveText: "Resume saved game",
    pauseText: "Pause", resumeText: "Resume",
    resetText: "Reset",
    slowerText: "- speed", fasterText: "+ speed",
    saveText: "Save", savedText: "Saved!",
    noticeText: "Notice",
    placingFoodBtn: "Placing: food", placingPredatorBtn: "Placing: predator",
    predLessText: "- predators", predMoreText: "+ predators",
    hint: "Click/tap the world to place food (or a predator in manual mode)",
    closeText: "Close",
    errorResumeFailed: (file) => `'${file}' could not be read - start a fresh game instead.`,

    labelIdle: "idle", labelFood: "food-call", labelMate: "mate-call", labelDanger: "alarm-call",
    labelDistress: "distress-call",
    wordBirths: "births", wordDeaths: "deaths", wordPaused: "PAUSE",
    trainedTag: "   [trained vocabulary]",
    placingWordFood: "food", placingWordPredator: "predator",
    settingsManual: (placing) => `mode: manual   placing: ${placing}`,
    settingsAuto: (count) => `mode: automatic   predators: ${count} (+/- act immediately)`,
    errorAiMissing: (file) => `'${file}' not found - starting without AI.`,

    helpH1: "The idea", helpP1: "Each creature is born with a genome deciding which color it shows for its current state, and how it reacts to colors it hears from others. Nobody programs what a color means - a shared language can emerge through natural selection, or it might not.",
    helpH2: "The 5 states, in priority order",
    stateDanger: "alarm-call", stateDangerDesc: "a predator was spotted, flee immediately",
    stateFood: "food-call", stateFoodDesc: "food is visible nearby",
    stateDistress: "distress-call", stateDistressDesc: "energy critically low, no food in sight",
    stateMate: "mate-call", stateMateDesc: "ready to mate, a ready partner is nearby",
    stateIdle: "idle", stateIdleDesc: "nothing special (by far the most common state)",
    helpH3: "Living, mating, dying", helpP3: "Energy drains constantly; eating restores it. Emitting a color (other than silence) costs a bit of extra energy. Enough energy and age, a matching partner nearby: a child is born. A predator that catches a creature kills it outright.",
    helpH4: "Reading the vocabulary rows at the top", helpP4: "For each state, the share of the population using each color. It starts near chance (~17%, there are 6 possible tokens) and climbs if a token wins out. The two dots '..' represent silence, not a missing color.",
    helpH5: "Worth knowing", helpP5: "Two states can end up sharing the same color purely by chance (e.g. idle and alarm-call) - nothing prevents it or guarantees it resolves. Signaling costs energy: silence is a real strategy, not a default.",
  },
  fr: {
    title: "Thronglets",
    startPrompt: "Choisis le mode de depart - ce choix ne se change pas en cours de partie.",
    initPopLabel: "Nombre de creatures au depart :",
    useAiLabel: "Activer le langage pre-entraine par IA (language_model.json)",
    startAuto: "Automatique — nourriture et predateurs apparaissent seuls",
    startManual: "Manuel — je place tout moi-meme",
    resumeSaveText: "Reprendre la partie sauvegardee",
    pauseText: "Pause", resumeText: "Reprendre",
    resetText: "Reset",
    slowerText: "- vitesse", fasterText: "+ vitesse",
    saveText: "Sauvegarder", savedText: "Sauvegarde !",
    noticeText: "Notice",
    placingFoodBtn: "Pose: nourriture", placingPredatorBtn: "Pose: predateur",
    predLessText: "- predateurs", predMoreText: "+ predateurs",
    hint: "Clique/touche le monde pour placer de la nourriture (ou un predateur en mode manuel)",
    closeText: "Fermer",
    errorResumeFailed: (file) => `'${file}' illisible - nouvelle partie a la place.`,

    labelIdle: "inactif", labelFood: "nourriture", labelMate: "partenaire", labelDanger: "alerte",
    labelDistress: "detresse",
    wordBirths: "naissances", wordDeaths: "morts", wordPaused: "PAUSE",
    trainedTag: "   [vocabulaire entraine]",
    placingWordFood: "nourriture", placingWordPredator: "predateur",
    settingsManual: (placing) => `mode: manuel   pose: ${placing}`,
    settingsAuto: (count) => `mode: auto   predateurs: ${count} (+/- agit tout de suite)`,
    errorAiMissing: (file) => `'${file}' introuvable - lancement sans IA.`,

    helpH1: "Le principe", helpP1: "Chaque creature nait avec un genome qui decide quelle couleur elle affiche selon son etat, et comment elle reagit aux couleurs des autres. Personne ne programme le sens des couleurs : un langage commun peut emerger par selection naturelle, ou pas.",
    helpH2: "Les 5 etats, par ordre de priorite",
    stateDanger: "alerte", stateDangerDesc: "un predateur est repere, fuite immediate",
    stateFood: "nourriture", stateFoodDesc: "de la nourriture est visible tout pres",
    stateDistress: "detresse", stateDistressDesc: "energie tres basse, aucune nourriture en vue",
    stateMate: "partenaire", stateMateDesc: "prete a se reproduire, partenaire prete proche",
    stateIdle: "inactif", stateIdleDesc: "rien de special (l'etat le plus frequent, de loin)",
    helpH3: "Vivre, se reproduire, mourir", helpP3: "L'energie baisse en permanence, manger la restaure. Emettre une couleur (hors silence) coute un peu d'energie en plus. Assez d'energie et d'age, un partenaire pareil a proximite : un enfant nait. Un predateur qui attrape une creature la tue net.",
    helpH4: "Lire le vocabulaire affiche en haut", helpP4: "Pour chaque etat, la part de la population qui utilise chaque couleur. Ca part du hasard (~17%, il y a 6 mots possibles) et grimpe si un mot fait consensus. Les deux points '..' representent le silence, pas une couleur en moins.",
    helpH5: "A savoir", helpP5: "Deux etats peuvent finir sur la meme couleur par hasard (par exemple idle et alarm-call) — rien ne l'empeche ni ne garantit que ca se resolve. Parler coute de l'energie : le silence est une vraie strategie, pas un defaut.",
  },
};

let uiLang = 'fr';

function applyLanguage(lang) {
  uiLang = lang;
  const t = STRINGS[lang];
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.dataset.i18n;
    if (t[key] !== undefined) el.textContent = t[key];
  });
  document.getElementById('langEn').classList.toggle('active', lang === 'en');
  document.getElementById('langFr').classList.toggle('active', lang === 'fr');
  document.getElementById('pause').textContent = paused ? t.resumeText : t.pauseText;
  document.getElementById('placing').textContent = placing === 'food' ? t.placingFoodBtn : t.placingPredatorBtn;
}

const canvas = document.getElementById('world');
const ctx = canvas.getContext('2d');
let worldW = 200, worldH = 140, paused = false, currentSpeed = 1;

let mode = 'auto', placing = 'food', predatorCount = 6;

function render(state) {
  if (!state.started) {
    document.getElementById('start-overlay').style.display = 'flex';
    document.getElementById('app').style.display = 'none';
    document.getElementById('startResume').style.display = state.save_exists ? 'block' : 'none';
    return;
  }
  document.getElementById('start-overlay').style.display = 'none';
  document.getElementById('app').style.display = 'flex';

  const t = STRINGS[uiLang];
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
    `tick ${state.tick}   pop ${state.pop}   ${t.wordBirths} ${state.births}   ${t.wordDeaths} ${state.deaths}   ` +
    (state.paused ? t.wordPaused : "x" + state.speed) +
    (state.trained ? t.trainedTag : "");

  renderVocabRow('vocab-danger', t.labelDanger, state.vocabulary['danger']);
  renderVocabRow('vocab-food', t.labelFood, state.vocabulary['food']);
  renderVocabRow('vocab-distress', t.labelDistress, state.vocabulary['distress']);
  renderVocabRow('vocab-mate', t.labelMate, state.vocabulary['mate']);
  renderVocabRow('vocab-idle', t.labelIdle, state.vocabulary['idle']);

  document.getElementById('pause').textContent = state.paused ? t.resumeText : t.pauseText;

  document.getElementById('settings').textContent = mode === 'manual'
    ? t.settingsManual(placing === 'food' ? t.placingWordFood : t.placingWordPredator)
    : t.settingsAuto(predatorCount);
  document.getElementById('placing').textContent = placing === 'food' ? t.placingFoodBtn : t.placingPredatorBtn;
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
  if (res.error === 'ai_missing') alert(STRINGS[uiLang].errorAiMissing(res.file));
}
async function resumeGame() {
  const res = await post('start', {resume_save: true});
  if (res.error === 'resume_failed') alert(STRINGS[uiLang].errorResumeFailed(res.file));
}
async function saveGame() {
  await post('save');
  const btn = document.getElementById('save');
  const original = STRINGS[uiLang].saveText;
  btn.textContent = STRINGS[uiLang].savedText;
  setTimeout(() => { btn.textContent = STRINGS[uiLang].saveText; }, 1500);
}
document.getElementById('langEn').onclick = () => applyLanguage('en');
document.getElementById('langFr').onclick = () => applyLanguage('fr');
document.getElementById('startAuto').onclick = () => startGame('auto');
document.getElementById('startManual').onclick = () => startGame('manual');
document.getElementById('startResume').onclick = () => resumeGame();
document.getElementById('pause').onclick = () => post(paused ? 'resume' : 'pause');
document.getElementById('reset').onclick = () => post('reset');
document.getElementById('save').onclick = () => saveGame();
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

applyLanguage(uiLang);
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
