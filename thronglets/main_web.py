"""Serve Thronglets in a browser - no pygame, no curses, just stdlib + a browser.

Runs the simulation in a background thread and exposes it over plain HTTP:
  GET  /        the page (canvas + controls)
  GET  /state   a JSON snapshot of the world, polled by the page a few times a second
  POST /control start/pause/resume/reset/speed/predator_count/click/quick_place,
                driven by the page's buttons, clicks, and n/p keys

The world doesn't exist until the page's start screen picks a language,
automatic or manual mode, and whether to seed the AI language - those
choices are made once, up front, not toggled mid-run. A "Notice"/"Help"
button opens an in-page explainer of the mechanics at any time. All UI
text (including the state names like food-call/mate-call) is translated
client-side between English and French; the server only ever deals in
fixed internal ids (idle/food/mate/danger).

No third-party dependencies beyond numpy (for simulation.py) - the server
itself is only the standard library's http.server, so this needs nothing
extra to install: if Python and numpy run, so does this.
"""

import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from simulation import (DANGER, DISTRESS, FOOD, HEIGHT, IDLE, MATE, MAX_POPULATION, N_TOKENS, N_TRAITS, TRAIT_HEARING,
                         TRAIT_METABOLISM, TRAIT_SPEED, TRAIT_VISION, World, WIDTH,
                         compare_seeds, load_bundled_genome, load_seed_genome, load_world, save_world)

DEFAULT_PORT = 8765
STEP_INTERVAL = 0.05
DEFAULT_INIT_POP = 100
DEFAULT_LANGUAGE_FILE = "language_model.json"
DEFAULT_SAVE_FILE = "thronglets_save.json"
TRAIT_IDS = {TRAIT_SPEED: "speed", TRAIT_VISION: "vision", TRAIT_HEARING: "hearing",
             TRAIT_METABOLISM: "metabolism"}
STATE_IDS = {IDLE: "idle", FOOD: "food", MATE: "mate", DANGER: "danger", DISTRESS: "distress"}
COMPARE_DEPTHS = {"quick": (4, 8000), "thorough": (8, 40000), "expert": (16, 60000)}


def _new_world(mode, predator_count, init_pop=DEFAULT_INIT_POP, seed_genome=None, adaptive_traits=False):
    if mode == "manual":
        return World(init_pop=init_pop, manual_food=True, manual_predators=True, seed_genome=seed_genome,
                     adaptive_traits=adaptive_traits)
    return World(init_pop=init_pop, predator_count=predator_count, seed_genome=seed_genome,
                 adaptive_traits=adaptive_traits)


class SimState:
    def __init__(self, seed_genome=None):
        self.started = False
        self.mode = None
        self.init_pop = DEFAULT_INIT_POP
        self.world = None
        self.paused = False
        self.speed = 1
        self.cli_seed_genome = seed_genome
        self.active_seed_genome = None
        self.adaptive_traits = False
        self.family_focus_id = None
        self.lock = threading.Lock()

        # Seed comparison runs in its own thread with its own lock - it never
        # touches state.world (it builds independent World instances), so it
        # can run alongside the live simulation without blocking it.
        self.compare_lock = threading.Lock()
        self.compare_running = False
        self.compare_mode = None
        self.compare_progress = {"seed": 0, "n_seeds": 0, "tick": 0, "ticks": 0}
        self.compare_result = None
        self.compare_cancel_event = threading.Event()


def _serialize_compare_result(r):
    return {
        "seed": r["seed"],
        "population": r["population"],
        "vocab": {STATE_IDS[s]: [int(tok), float(frac)] for s, (tok, frac) in r["vocab"].items()},
        "collision": r["collision"],
        "traits": ({TRAIT_IDS[t]: float(v) for t, v in r["traits"].items()}
                    if r["traits"] is not None else None),
    }


def _compare_payload(state):
    with state.compare_lock:
        return {
            "running": state.compare_running,
            "mode": state.compare_mode,
            "progress": dict(state.compare_progress),
            "result": state.compare_result,
        }


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
        "adaptive_traits": w.adaptive_traits,
        "compare": _compare_payload(state),
        "mode": state.mode,
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
        "vocab_history": {
            STATE_IDS[s]: [float(v) for v in w.vocab_history[s]]
            for s in (DANGER, FOOD, DISTRESS, MATE, IDLE)
        },
        "trait_history": {
            TRAIT_IDS[i]: [float(v) for v in w.trait_history[i]]
            for i in range(N_TRAITS)
        },
        "translator": {
            str(token): [[STATE_IDS[s], float(frac)] for s, frac in claims]
            for token, claims in w.translator().items()
        },
    }


def _family_payload(state):
    """The current focus creature's family_info(), auto-picking a fresh focus
    if there isn't one yet (or the old one no longer resolves, e.g. after a
    reset). Returns None only if the world has no creatures at all."""
    w = state.world
    if state.family_focus_id is None or w.family_info(state.family_focus_id) is None:
        state.family_focus_id = w.default_family_focus()
    if state.family_focus_id is None:
        return None
    return w.family_info(state.family_focus_id)


def _start_compare_worker(state, mode, n_seeds, ticks):
    """Runs compare_seeds() in its own daemon thread, independent of the live
    simulation_loop thread - it builds its own World instances and never
    touches state.world, so it can't interfere with (or be blocked by) the
    running game."""
    init_pop = state.init_pop
    predator_count = len(state.world.predators)
    seed_genome = state.active_seed_genome
    cancel_event = state.compare_cancel_event

    def on_progress(seed_i, n, tick, total_ticks):
        with state.compare_lock:
            state.compare_progress.update(seed=seed_i + 1, tick=tick)

    def worker():
        results = compare_seeds(n_seeds, ticks, init_pop, predator_count, mode == "traits",
                                 seed_genome=seed_genome, progress_callback=on_progress,
                                 cancel_event=cancel_event)
        with state.compare_lock:
            state.compare_result = {
                "mode": mode,
                "n_seeds": len(results),
                "ticks": ticks,
                "cancelled": cancel_event.is_set() and len(results) < n_seeds,
                "results": [_serialize_compare_result(r) for r in results],
            }
            state.compare_running = False

    threading.Thread(target=worker, daemon=True).start()


def simulation_loop(state):
    tick_accumulator = 0.0
    last = time.monotonic()
    while True:
        time.sleep(STEP_INTERVAL)
        now = time.monotonic()
        dt = min(now - last, 0.25)  # capped so a delayed loop iteration doesn't fast-forward
        last = now
        with state.lock:
            if state.started and not state.paused:
                tick_accumulator += dt
                tick_interval = 1.0 / state.speed
                while tick_accumulator >= tick_interval:
                    state.world.step()
                    tick_accumulator -= tick_interval
            else:
                tick_accumulator = 0.0


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
        family_payload = None
        with state.lock:
            if action == "start" and not state.started and body.get("resume_save"):
                try:
                    state.world = load_world(DEFAULT_SAVE_FILE)
                    state.mode = "manual" if (state.world.manual_food or state.world.manual_predators) else "auto"
                    state.init_pop = state.world.population()
                    state.active_seed_genome = None
                    state.adaptive_traits = state.world.adaptive_traits
                    state.family_focus_id = None
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
                state.adaptive_traits = bool(body.get("adaptive_traits"))

                if state.cli_seed_genome is not None:
                    state.active_seed_genome = state.cli_seed_genome
                elif body.get("use_ai"):
                    try:
                        # a language you trained yourself wins; otherwise fall
                        # back to the trained one shipped with the project
                        state.active_seed_genome = load_seed_genome(DEFAULT_LANGUAGE_FILE)
                    except OSError:
                        state.active_seed_genome = load_bundled_genome()
                        if state.active_seed_genome is None:
                            error_code = "ai_missing"
                else:
                    state.active_seed_genome = None

                state.world = _new_world(state.mode, 6, state.init_pop, state.active_seed_genome,
                                          state.adaptive_traits)
                state.family_focus_id = None
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
                                          state.active_seed_genome, state.adaptive_traits)
                state.family_focus_id = None
                state.paused = False
            elif action == "speed":
                state.speed = max(1, min(200, int(body.get("value", state.speed))))
            elif action == "predator_count":
                if int(body.get("delta", 0)) > 0:
                    state.world.add_random_predator()
                else:
                    state.world.remove_predator()
            elif action == "click":
                x, y = float(body.get("x", 0)), float(body.get("y", 0))
                if body.get("button") == "right":
                    state.world.add_predator(x, y)
                else:
                    state.world.add_food(x, y)
            elif action == "quick_place":
                if body.get("kind") == "predator":
                    state.world.add_random_predator()
                else:
                    state.world.add_food(*state.world.rng.uniform([10, 10], [WIDTH - 10, HEIGHT - 10]))
            elif action == "family_open":
                family_payload = _family_payload(state)
            elif action == "family_nav":
                info = _family_payload(state)
                if info is not None:
                    direction = body.get("dir")
                    if direction == "up" and info["parents"]:
                        state.family_focus_id = info["parents"][0]
                    elif direction == "down" and info["children"]:
                        state.family_focus_id = info["children"][0]
                    elif direction in ("left", "right") and info["parents"]:
                        siblings = state.world.family_info(info["parents"][0])["children"]
                        if state.family_focus_id in siblings and len(siblings) > 1:
                            i = siblings.index(state.family_focus_id)
                            i = (i + (1 if direction == "right" else -1)) % len(siblings)
                            state.family_focus_id = siblings[i]
                    family_payload = _family_payload(state)
            elif action == "compare_start" and not state.compare_running:
                mode = body.get("mode")
                if mode == "traits" and not state.world.adaptive_traits:
                    mode = None
                if mode in ("language", "traits"):
                    n_seeds, ticks = COMPARE_DEPTHS.get(body.get("depth"), COMPARE_DEPTHS["quick"])
                    state.compare_running = True
                    state.compare_mode = mode
                    state.compare_result = None
                    state.compare_cancel_event = threading.Event()
                    state.compare_progress = {"seed": 0, "n_seeds": n_seeds, "tick": 0, "ticks": ticks}
                    _start_compare_worker(state, mode, n_seeds, ticks)
            elif action == "compare_cancel":
                state.compare_cancel_event.set()
            elif action == "compare_dismiss":
                state.compare_result = None
        error_file = DEFAULT_SAVE_FILE if error_code == "resume_failed" else DEFAULT_LANGUAGE_FILE
        self._send(200, "application/json",
                   json.dumps({"ok": True, "error": error_code, "file": error_file, "family": family_payload}).encode())

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
  #header { cursor: pointer; }
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

  #faq-overlay {
    display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    align-items: center; justify-content: center; padding: 16px; z-index: 10;
  }
  #faq-panel {
    background: #171d13; border: 1px solid #3a4530; border-radius: 10px;
    max-width: 640px; width: 100%; max-height: 85vh; overflow-y: auto;
    padding: 22px 24px; line-height: 1.6; font-size: 13.5px;
  }
  #faq-panel h2 { font-size: 15px; margin: 18px 0 4px; }
  #faq-panel h2:first-child { margin-top: 0; }
  #faq-panel p { color: #c3c8b6; margin: 4px 0; }
  #faq-panel .close-row { text-align: right; margin-top: 16px; }

  #graph-overlay {
    display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    align-items: center; justify-content: center; padding: 16px; z-index: 10;
  }
  #graph-panel {
    background: #171d13; border: 1px solid #3a4530; border-radius: 10px;
    max-width: 640px; width: 100%; max-height: 85vh; overflow-y: auto;
    padding: 22px 24px; line-height: 1.6; font-size: 13.5px;
  }
  #graph-panel h2 { font-size: 17px; margin: 0 0 14px; }
  .graph-row { margin: 14px 0; }
  .graph-row .graph-label { display: flex; justify-content: space-between; margin-bottom: 4px; color: #c3c8b6; }
  .graph-row canvas { width: 100%; height: 44px; background: #1a2014; border-radius: 4px; display: block; }
  #graph-panel .close-row { text-align: right; margin-top: 16px; }

  #family-overlay {
    display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    align-items: center; justify-content: center; padding: 16px; z-index: 10;
  }
  #family-panel {
    background: #171d13; border: 1px solid #3a4530; border-radius: 10px;
    max-width: 480px; width: 100%; max-height: 85vh; overflow-y: auto;
    padding: 22px 24px; line-height: 1.6; font-size: 13.5px;
  }
  #family-panel h2 { font-size: 17px; margin: 0 0 10px; }
  #family-content p { margin: 3px 0; color: #c3c8b6; }
  #family-content .fam-id { font-size: 15px; font-weight: bold; color: #dcdcd2; }
  #family-content .fam-label { font-weight: bold; color: #dcdcd2; margin-top: 10px; }
  #family-content .fam-item { margin-left: 14px; }
  #family-nav { display: flex; justify-content: center; gap: 10px; margin: 14px 0 4px; }
  #family-nav button { padding: 8px 14px; }
  #family-panel .close-row { text-align: right; margin-top: 12px; }

  #compare-overlay {
    display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    align-items: center; justify-content: center; padding: 16px; z-index: 10;
  }
  #compare-panel {
    background: #171d13; border: 1px solid #3a4530; border-radius: 10px;
    max-width: 560px; width: 100%; max-height: 85vh; overflow-y: auto;
    padding: 22px 24px; line-height: 1.6; font-size: 13.5px;
  }
  #compare-panel h2 { font-size: 17px; margin: 0 0 10px; }
  #compare-panel p { color: #c3c8b6; margin: 10px 0 4px; }
  #compare-panel label {
    display: block; font-size: 13px; margin: 4px 0; color: #dcdcd2; cursor: pointer;
  }
  #compare-panel label.disabled { color: #6b7263; cursor: default; }
  #compareStart { margin-top: 14px; padding: 10px 16px; }
  #compare-progress-bar-track { background: #232a1c; border-radius: 4px; height: 12px; margin: 10px 0; overflow: hidden; }
  #compare-progress-bar-fill { background: #6edc5a; height: 100%; width: 0%; }
  #compareCancel { margin-top: 10px; }
  #compare-results-content table { border-collapse: collapse; width: 100%; font-size: 13px; }
  #compare-results-content th, #compare-results-content td {
    text-align: left; padding: 3px 10px 3px 0; color: #c3c8b6; white-space: nowrap;
  }
  #compare-results-content th { color: #dcdcd2; border-bottom: 1px solid #3a4530; }
  #compare-results-content .swatch {
    display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px;
  }
  #compare-panel .close-row { text-align: right; margin-top: 16px; }

  #translator-overlay {
    display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    align-items: center; justify-content: center; padding: 16px; z-index: 10;
  }
  #translator-panel {
    background: #171d13; border: 1px solid #3a4530; border-radius: 10px;
    max-width: 480px; width: 100%; max-height: 85vh; overflow-y: auto;
    padding: 22px 24px; line-height: 1.6; font-size: 13.5px;
  }
  #translator-panel h2 { font-size: 17px; margin: 0 0 10px; }
  .translator-row { display: flex; align-items: center; gap: 8px; margin: 6px 0; color: #c3c8b6; }
  .translator-row .swatch { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
  .translator-homonym { color: #eb5a5a; font-size: 12px; margin: -2px 0 6px 20px; }
  #translator-panel .close-row { text-align: right; margin-top: 16px; }
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
      <input type="number" id="initPop" value="100" min="1" max="220">
    </label>
    <label><input type="checkbox" id="useAi"> <span data-i18n="useAiLabel"></span></label>
    <label><input type="checkbox" id="adaptiveTraits" checked> <span data-i18n="adaptiveTraitsLabel"></span></label>
    <p data-i18n="adaptiveTraitsExplain" style="font-size:12px; opacity:0.65; margin-top:-8px;"></p>
    <button id="startAuto" data-i18n="startAuto"></button>
    <button id="startManual" data-i18n="startManual"></button>
    <button id="startResume" data-i18n="resumeSaveText" style="display:none"></button>
  </div>

  <div id="app">
    <div id="hud">
      <div class="row" id="header"></div>
      <div class="row" id="hud-summary" style="display:none"></div>
      <div id="hud-details">
        <div class="row" id="settings"></div>
        <div class="row" id="vocab-danger"></div>
        <div class="row" id="vocab-food"></div>
        <div class="row" id="vocab-distress"></div>
        <div class="row" id="vocab-mate"></div>
        <div class="row" id="vocab-idle"></div>
      </div>
    </div>
    <div id="controls">
      <button id="pause"></button>
      <button id="reset" data-i18n="resetText"></button>
      <button id="slower" data-i18n="slowerText"></button>
      <button id="faster" data-i18n="fasterText"></button>
      <button id="save" data-i18n="saveText"></button>
      <button id="openGraph" data-i18n="graphText"></button>
      <button id="openFamily" data-i18n="familyText"></button>
      <button id="openCompare" data-i18n="compareText"></button>
      <button id="openTranslator" data-i18n="translatorText"></button>
      <button id="openFaq" data-i18n="faqText"></button>
      <button id="openHelp" data-i18n="noticeText"></button>
      <button id="muteSound"></button>
    </div>
    <div id="controls2">
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

  <div id="faq-overlay">
    <div id="faq-panel">
      <h2 data-i18n="faqQ1"></h2>
      <p data-i18n="faqA1"></p>
      <h2 data-i18n="faqQ2"></h2>
      <p data-i18n="faqA2"></p>
      <h2 data-i18n="faqQ3"></h2>
      <p data-i18n="faqA3"></p>
      <h2 data-i18n="faqQ4"></h2>
      <p data-i18n="faqA4"></p>
      <h2 data-i18n="faqQ5"></h2>
      <p data-i18n="faqA5"></p>
      <h2 data-i18n="faqQ6"></h2>
      <p data-i18n="faqA6"></p>
      <h2 data-i18n="faqQ7"></h2>
      <p data-i18n="faqA7"></p>
      <h2 data-i18n="faqQ8"></h2>
      <p data-i18n="faqA8"></p>
      <h2 data-i18n="faqQ9"></h2>
      <p data-i18n="faqA9"></p>
      <div class="close-row"><button id="closeFaq" data-i18n="closeText"></button></div>
    </div>
  </div>

  <div id="graph-overlay">
    <div id="graph-panel">
      <h2 data-i18n="graphTitle"></h2>
      <div class="graph-row">
        <div class="graph-label"><span data-i18n="stateDanger"></span><span id="graph-cur-danger"></span></div>
        <canvas id="graph-danger" width="560" height="88"></canvas>
      </div>
      <div class="graph-row">
        <div class="graph-label"><span data-i18n="stateFood"></span><span id="graph-cur-food"></span></div>
        <canvas id="graph-food" width="560" height="88"></canvas>
      </div>
      <div class="graph-row">
        <div class="graph-label"><span data-i18n="stateDistress"></span><span id="graph-cur-distress"></span></div>
        <canvas id="graph-distress" width="560" height="88"></canvas>
      </div>
      <div class="graph-row">
        <div class="graph-label"><span data-i18n="stateMate"></span><span id="graph-cur-mate"></span></div>
        <canvas id="graph-mate" width="560" height="88"></canvas>
      </div>
      <div class="graph-row">
        <div class="graph-label"><span data-i18n="stateIdle"></span><span id="graph-cur-idle"></span></div>
        <canvas id="graph-idle" width="560" height="88"></canvas>
      </div>
      <div id="graph-traits-section" style="display:none">
        <h2 data-i18n="graphTraitsTitle"></h2>
        <div class="graph-row">
          <div class="graph-label"><span data-i18n="traitSpeed"></span><span id="graph-cur-speed"></span></div>
          <canvas id="graph-speed" width="560" height="88"></canvas>
        </div>
        <div class="graph-row">
          <div class="graph-label"><span data-i18n="traitVision"></span><span id="graph-cur-vision"></span></div>
          <canvas id="graph-vision" width="560" height="88"></canvas>
        </div>
        <div class="graph-row">
          <div class="graph-label"><span data-i18n="traitHearing"></span><span id="graph-cur-hearing"></span></div>
          <canvas id="graph-hearing" width="560" height="88"></canvas>
        </div>
        <div class="graph-row">
          <div class="graph-label"><span data-i18n="traitMetabolism"></span><span id="graph-cur-metabolism"></span></div>
          <canvas id="graph-metabolism" width="560" height="88"></canvas>
        </div>
      </div>
      <div class="close-row"><button id="closeGraph" data-i18n="closeText"></button></div>
    </div>
  </div>

  <div id="family-overlay">
    <div id="family-panel">
      <h2 data-i18n="familyTitle"></h2>
      <div id="family-content"></div>
      <div id="family-nav">
        <button id="famUp">&uarr;</button>
        <button id="famLeft">&larr;</button>
        <button id="famDown">&darr;</button>
        <button id="famRight">&rarr;</button>
      </div>
      <div class="close-row"><button id="closeFamily" data-i18n="closeText"></button></div>
    </div>
  </div>

  <div id="compare-overlay">
    <div id="compare-panel">
      <h2 data-i18n="compareTitle"></h2>

      <div id="compare-config">
        <p data-i18n="compareModePrompt"></p>
        <label><input type="radio" name="compareMode" value="language" checked> <span data-i18n="compareModeLanguage"></span></label>
        <label id="compare-mode-traits-label"><input type="radio" name="compareMode" value="traits"> <span data-i18n="compareModeTraits"></span></label>
        <p data-i18n="compareDepthPrompt"></p>
        <label><input type="radio" name="compareDepth" value="quick" checked> <span data-i18n="compareDepthQuick"></span></label>
        <label><input type="radio" name="compareDepth" value="thorough"> <span data-i18n="compareDepthThorough"></span></label>
        <label><input type="radio" name="compareDepth" value="expert"> <span data-i18n="compareDepthExpert"></span></label>
        <button id="compareStart" data-i18n="compareStartText"></button>
      </div>

      <div id="compare-progress-view" style="display:none">
        <p id="compare-progress-text"></p>
        <div id="compare-progress-bar-track"><div id="compare-progress-bar-fill"></div></div>
        <button id="compareCancel" data-i18n="compareCancelText"></button>
      </div>

      <div id="compare-results-view" style="display:none">
        <div id="compare-results-content"></div>
        <button id="compareAgain" data-i18n="compareAgainText"></button>
      </div>

      <div class="close-row"><button id="closeCompare" data-i18n="closeText"></button></div>
    </div>
  </div>

  <div id="translator-overlay">
    <div id="translator-panel">
      <h2 data-i18n="translatorTitle"></h2>
      <div id="translator-content"></div>
      <div class="close-row"><button id="closeTranslator" data-i18n="closeText"></button></div>
    </div>
  </div>

<script>
const TOKEN_COLORS = ["#a0a0a0", "#eb4646", "#4682eb", "#f5c83c", "#c85ae6", "#46e1d2"];
// A pentatonic scale (C4 D4 E4 G4 A4) so any combination of tokens sounds
// pleasant together - index 0 (silence) is never looked up, no tone assigned.
const TOKEN_FREQS = [0, 261.63, 293.66, 329.63, 392.00, 440.00];
const LISTEN_RADIUS = 10.0;  // world units - how close the mouse must be to hear a creature
const FOOD_COLOR = "#6edc5a";
const PREDATOR_COLOR = "#dc1e1e";

const STRINGS = {
  en: {
    title: "Thronglets",
    startPrompt: "Choose the starting mode - this choice does not change during the game.",
    initPopLabel: "Number of creatures to start with:",
    useAiLabel: "Activate the pre-trained AI language (language_model.json)",
    adaptiveTraitsLabel: "Adaptive evolution: speed, vision, hearing, metabolism",
    adaptiveTraitsExplain: "Each creature gets its own physical stats, inherited and mutated - but faster/keener senses cost more energy, a real trade-off. On by default.",
    startAuto: "Automatic — food and predators spawn on their own",
    startManual: "Manual — I place everything myself",
    resumeSaveText: "Resume saved game",
    pauseText: "Pause", resumeText: "Resume",
    resetText: "Reset",
    slowerText: "- speed", fasterText: "+ speed",
    saveText: "Save", savedText: "Saved!",
    noticeText: "Notice",
    graphText: "Graph", graphTitle: "Vocabulary over time - dominant share per state",
    graphTraitsTitle: "Physical traits over time - population average (share of range)",
    traitSpeed: "speed", traitVision: "vision", traitHearing: "hearing", traitMetabolism: "metabolism",
    familyText: "Family", familyTitle: "Family tree",
    familyGen: (gen) => `generation ${gen}`,
    familyAlive: (token, age) => `alive - token ${token}, age ${age}`,
    familyDead: (death) => `dead since tick ${death}`,
    familyBorn: (tick) => `born at tick ${tick}`,
    familyParents: "Parents:", familyFounder: "none - founding generation",
    familyChildren: (n) => `Children (${n}):`, familyNoChildren: "none yet",
    familyDescendants: (total, alive) => `Total descendants: ${total} (${alive} still alive)`,
    familyNone: "No creature to show yet.",
    compareText: "Compare", compareTitle: "Compare seeds",
    compareModePrompt: "What should be reproducible?",
    compareModeLanguage: "Language - does the same word win across independent runs?",
    compareModeTraits: "Physical traits - do speed/vision/hearing/metabolism converge the same way?",
    compareModeTraitsUnavailable: "Physical traits (unavailable - adaptive evolution is off for this world)",
    compareDepthPrompt: "How thorough?",
    compareDepthQuick: "Quick - 4 seeds x 8,000 ticks",
    compareDepthThorough: "Thorough - 8 seeds x 40,000 ticks",
    compareDepthExpert: "Expert - 16 seeds x 60,000 ticks, one at a time - can take a while",
    compareStartText: "Start comparison", compareCancelText: "Cancel",
    compareAgainText: "Compare again",
    compareProgress: (seed, nSeeds, tick, ticks) => `seed ${seed}/${nSeeds}   tick ${tick}/${ticks}`,
    compareResultTitle: (nSeeds, ticks) => `Comparison done (${nSeeds} seeds x ${ticks} ticks)`,
    compareCancelledNote: (n) => `Cancelled - ${n} seed(s) completed before stopping.`,
    compareCollisionSummary: (clean, nSeeds) => `Collisions: ${clean}/${nSeeds} seeds had none`,
    compareColState: "state", compareColSeed: (i) => `seed ${i}`,
    compareColTrait: "trait", compareColMean: "mean", compareColStd: "std dev",
    compareColMin: "min", compareColMax: "max",
    translatorText: "Translator", translatorTitle: "Translator - what each color currently means",
    translatorUnused: "unused / ambiguous",
    translatorHomonym: "! homonym - shared with another state",
    faqText: "FAQ",
    faqQ1: "Q: Why do creatures sometimes stay clustered even with food right next to them?",
    faqA1: "A: Following a neighbor's signal and heading for food are two forces that can partly cancel out - an accepted trade-off, not a bug.",
    faqQ2: "Q: Does distress make creatures help each other?",
    faqA2: "A: No - there's no cooperation mechanic. Distress is treated like any other signal, and creatures mostly learn to avoid it.",
    faqQ3: "Q: Why does the adaptive metabolism trait always drop to near its minimum?",
    faqA3: "A: Unlike speed/vision/hearing, a lower metabolism has zero downside here - it's not a real trade-off, so selection always pushes it down.",
    faqQ4: "Q: How can two creatures from very different generations be siblings?",
    faqA4: "A: Generation = max(both parents' generations)+1, and mate choice only cares about proximity, not generation - a long-lived parent can breed with a much ‘deeper’ partner late in life.",
    faqQ5: "Q: Can a creature really mate with its own descendant?",
    faqA5: "A: Yes - same reason: mate choice is purely proximity-based, with no notion of family.",
    faqQ6: "Q: Even a trained vocabulary can drift or ‘flip back’ - why?",
    faqA6: "A: No creature learns anything during its life; genomes are fixed at birth. Only mutation and selection across generations change anything, and mutation never stops - nothing is ever permanently locked in.",
    faqQ7: "Q: Two states share the same color (homonymy) - is that a bug?",
    faqA7: "A: No - nothing in the model prevents it. Genomes mutate per state independently, so two states can land on the same token by pure chance. Check the Translator panel to see it clearly.",
    faqQ8: "Q: A single playthrough shows a surprising result - can I trust it?",
    faqA8: "A: Not on its own. Use the Compare panel to run several independent seeds and see whether the result actually repeats, or was just one run's drift.",
    faqQ9: "Q: What's the real difference between the trained AI language and the evolved one?",
    faqA9: "A: The AI (train_language.py) uses gradient descent to directly minimize communication error, every step. The evolved language only rewards survival and reproduction - communicating well is never optimized directly, just indirectly useful.",
    predLessText: "- predators", predMoreText: "+ predators",
    hint: "n = food   p = predator   left-click = food   right-click = predator   move the mouse near a creature to hear it (m = mute)",
    hudExpandHint: "   (V or click here = show full HUD)",
    muteText: "Mute sound", unmuteText: "Unmute sound",
    closeText: "Close",
    errorResumeFailed: (file) => `'${file}' could not be read - start a fresh game instead.`,

    labelIdle: "idle", labelFood: "food-call", labelMate: "mate-call", labelDanger: "alarm-call",
    labelDistress: "distress-call",
    vocabOther: "other",
    wordBirths: "births", wordDeaths: "deaths", wordPaused: "PAUSE",
    trainedTag: "   [trained vocabulary]",
    traitsTag: "   [adaptive traits]",
    settingsManual: () => `mode: manual (no automatic spawning)`,
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
    adaptiveTraitsLabel: "Evolution adaptative : vitesse, vision, ouie, metabolisme",
    adaptiveTraitsExplain: "Chaque creature a ses propres stats physiques, heritees et mutees - mais etre rapide/perceptif coute plus d'energie, un vrai compromis. Active par defaut.",
    startAuto: "Automatique — nourriture et predateurs apparaissent seuls",
    startManual: "Manuel — je place tout moi-meme",
    resumeSaveText: "Reprendre la partie sauvegardee",
    pauseText: "Pause", resumeText: "Reprendre",
    resetText: "Reset",
    slowerText: "- vitesse", fasterText: "+ vitesse",
    saveText: "Sauvegarder", savedText: "Sauvegarde !",
    noticeText: "Notice",
    graphText: "Graphique", graphTitle: "Vocabulaire dans le temps - part dominante par etat",
    graphTraitsTitle: "Traits physiques dans le temps - moyenne population (part de la plage)",
    traitSpeed: "vitesse", traitVision: "vision", traitHearing: "ouie", traitMetabolism: "metabolisme",
    familyText: "Famille", familyTitle: "Arbre genealogique",
    familyGen: (gen) => `generation ${gen}`,
    familyAlive: (token, age) => `vivant - token ${token}, age ${age}`,
    familyDead: (death) => `mort depuis le tick ${death}`,
    familyBorn: (tick) => `ne au tick ${tick}`,
    familyParents: "Parents :", familyFounder: "aucun - generation fondatrice",
    familyChildren: (n) => `Enfants (${n}) :`, familyNoChildren: "aucun pour le moment",
    familyDescendants: (total, alive) => `Descendants au total : ${total} (${alive} encore en vie)`,
    familyNone: "Aucune creature a montrer pour le moment.",
    compareText: "Comparer", compareTitle: "Comparer des seeds",
    compareModePrompt: "Qu'est-ce qui doit etre reproductible ?",
    compareModeLanguage: "Langage - le meme mot gagne-t-il sur des parties independantes ?",
    compareModeTraits: "Traits physiques - vitesse/vision/ouie/metabolisme convergent-ils pareil ?",
    compareModeTraitsUnavailable: "Traits physiques (indisponibles - evolution adaptative desactivee)",
    compareDepthPrompt: "Quelle profondeur ?",
    compareDepthQuick: "Rapide - 4 seeds x 8 000 ticks",
    compareDepthThorough: "Approfondi - 8 seeds x 40 000 ticks",
    compareDepthExpert: "Expert - 16 seeds x 60 000 ticks, une par une - peut prendre du temps",
    compareStartText: "Lancer la comparaison", compareCancelText: "Annuler",
    compareAgainText: "Comparer a nouveau",
    compareProgress: (seed, nSeeds, tick, ticks) => `seed ${seed}/${nSeeds}   tick ${tick}/${ticks}`,
    compareResultTitle: (nSeeds, ticks) => `Comparaison terminee (${nSeeds} seeds x ${ticks} ticks)`,
    compareCancelledNote: (n) => `Annule - ${n} seed(s) terminee(s) avant l'arret.`,
    compareCollisionSummary: (clean, nSeeds) => `Collisions : ${clean}/${nSeeds} seeds sans collision`,
    compareColState: "etat", compareColSeed: (i) => `seed ${i}`,
    compareColTrait: "trait", compareColMean: "moyenne", compareColStd: "ecart-type",
    compareColMin: "min", compareColMax: "max",
    translatorText: "Traducteur", translatorTitle: "Traducteur - ce que signifie chaque couleur en ce moment",
    translatorUnused: "inutilisee / ambigue",
    translatorHomonym: "! homonymie - partagee avec un autre etat",
    faqText: "FAQ",
    faqQ1: "Q : Pourquoi les creatures restent parfois en groupe meme avec de la nourriture juste a cote ?",
    faqA1: "R : Suivre le signal d'un voisin et se diriger vers la nourriture sont deux forces qui peuvent s'annuler en partie - un compromis assume, pas un bug.",
    faqQ2: "Q : Est-ce que la detresse pousse les creatures a s'entraider ?",
    faqA2: "R : Non - il n'y a aucun mecanisme de cooperation. La detresse est traitee comme n'importe quel autre signal, et les creatures apprennent surtout a l'eviter.",
    faqQ3: "Q : Pourquoi le metabolisme adaptatif tombe toujours pres de son minimum ?",
    faqA3: "R : Contrairement a la vitesse/vision/ouie, un metabolisme bas n'a aucun inconvenient ici - ce n'est pas un vrai compromis, donc la selection le pousse toujours vers le bas.",
    faqQ4: "Q : Comment deux creatures de generations tres differentes peuvent-elles etre frere et soeur ?",
    faqA4: "R : Generation = max(generation des deux parents)+1, et le choix du partenaire ne tient compte que de la proximite, pas de la generation - un parent qui vit longtemps peut se reproduire avec un partenaire bien plus « profond » tard dans sa vie.",
    faqQ5: "Q : Une creature peut-elle vraiment s'accoupler avec son propre descendant ?",
    faqA5: "R : Oui - meme raison : le choix du partenaire est purement base sur la proximite, sans aucune notion de famille.",
    faqQ6: "Q : Meme un vocabulaire entraine peut deriver ou « revenir en arriere » - pourquoi ?",
    faqA6: "R : Aucune creature n'apprend quoi que ce soit pendant sa vie ; les genomes sont fixes a la naissance. Seules la mutation et la selection a travers les generations changent quelque chose, et la mutation ne s'arrete jamais - rien n'est jamais definitivement acquis.",
    faqQ7: "Q : Deux etats partagent la meme couleur (homonymie) - c'est un bug ?",
    faqA7: "R : Non - rien dans le modele ne l'empeche. Les genomes mutent independamment par etat, donc deux etats peuvent tomber sur le meme token par pur hasard. L'ecran Traducteur permet de le reperer clairement.",
    faqQ8: "Q : Une seule partie donne un resultat surprenant - puis-je lui faire confiance ?",
    faqA8: "R : Pas telle quelle. Utilise le panneau Comparer pour lancer plusieurs seeds independantes et voir si le resultat se reproduit vraiment, ou si c'etait juste la derive d'une seule partie.",
    faqQ9: "Q : Quelle est la vraie difference entre le langage entraine par IA et celui qui evolue ?",
    faqA9: "R : L'IA (train_language.py) utilise la descente de gradient pour minimiser directement l'erreur de communication, a chaque etape. Le langage evolue ne recompense que la survie et la reproduction - bien communiquer n'est jamais optimise directement, juste utile indirectement.",
    predLessText: "- predateurs", predMoreText: "+ predateurs",
    hint: "n = nourriture   p = predateur   clic gauche = nourriture   clic droit = predateur   approche la souris d'une creature pour l'entendre (m = muet)",
    hudExpandHint: "   (V ou clique ici = HUD complet)",
    muteText: "Couper le son", unmuteText: "Activer le son",
    closeText: "Fermer",
    errorResumeFailed: (file) => `'${file}' illisible - nouvelle partie a la place.`,

    labelIdle: "inactif", labelFood: "nourriture", labelMate: "partenaire", labelDanger: "alerte",
    labelDistress: "detresse",
    vocabOther: "autre",
    wordBirths: "naissances", wordDeaths: "morts", wordPaused: "PAUSE",
    trainedTag: "   [vocabulaire entraine]",
    traitsTag: "   [traits evolutifs]",
    settingsManual: () => `mode: manuel (pas d'apparition automatique)`,
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
  updateMuteButton();
}

const canvas = document.getElementById('world');
const ctx = canvas.getContext('2d');
let worldW = 200, worldH = 140, paused = false, currentSpeed = 1;

let mode = 'auto', predatorCount = 6;
let hudExpanded = false;
let lastCreatures = [];

let audioCtx = null, oscillator = null, gainNode = null, soundMuted = false;

function initSound() {
  // Best-effort - browsers require a user gesture to start audio, so this is
  // only ever called from a click handler, and it's fine if it silently
  // fails (older browser, autoplay blocked, whatever): sound is optional.
  if (audioCtx) return;
  try {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    oscillator = audioCtx.createOscillator();
    gainNode = audioCtx.createGain();
    gainNode.gain.value = 0;
    oscillator.type = 'sine';
    oscillator.frequency.value = TOKEN_FREQS[1];
    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    oscillator.start();
  } catch (e) {
    audioCtx = null;
  }
}

function updateMuteButton() {
  const t = STRINGS[uiLang];
  document.getElementById('muteSound').textContent = soundMuted ? t.unmuteText : t.muteText;
}

function updateListening(px, py) {
  // Plays a sustained tone for whichever living creature is closest to the
  // mouse, within LISTEN_RADIUS - a way to "listen in" on one creature's
  // signal instead of the whole population's noise.
  if (!gainNode) return;
  const now = audioCtx.currentTime;
  if (soundMuted) {
    gainNode.gain.linearRampToValueAtTime(0, now + 0.05);
    return;
  }
  const scale = canvas.width / worldW;
  const wx = px / scale, wy = py / scale;
  let bestDist = LISTEN_RADIUS, token = null;
  for (const c of lastCreatures) {
    if (c.token === 0) continue;
    const dist = Math.hypot(c.x - wx, c.y - wy);
    if (dist < bestDist) { bestDist = dist; token = c.token; }
  }
  if (token === null) {
    gainNode.gain.linearRampToValueAtTime(0, now + 0.05);
  } else {
    oscillator.frequency.setValueAtTime(TOKEN_FREQS[token], now);
    gainNode.gain.linearRampToValueAtTime(0.12, now + 0.05);
  }
}

function applyHudExpanded() {
  document.getElementById('hud-details').style.display = hudExpanded ? '' : 'none';
  document.getElementById('hud-summary').style.display = hudExpanded ? 'none' : '';
}

function renderVocabSummary(vocabulary) {
  // The collapsed HUD's one-line version - just each state's single
  // strongest token, no breakdown of the runners-up.
  const t = STRINGS[uiLang];
  const el = document.getElementById('hud-summary');
  el.innerHTML = '';
  const rows = [
    [t.labelDanger, vocabulary['danger']], [t.labelFood, vocabulary['food']],
    [t.labelDistress, vocabulary['distress']], [t.labelMate, vocabulary['mate']],
    [t.labelIdle, vocabulary['idle']],
  ];
  for (const [label, pairs] of rows) {
    const [token, frac] = pairs[0] || [0, 0];
    const labelSpan = document.createElement('span');
    labelSpan.textContent = label + ': ';
    labelSpan.style.fontWeight = 'bold';
    el.appendChild(labelSpan);
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
  mode = state.mode; predatorCount = state.predator_count;
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
    (state.trained ? t.trainedTag : "") +
    (state.adaptive_traits ? t.traitsTag : "") +
    (hudExpanded ? "" : t.hudExpandHint);
  applyHudExpanded();

  renderVocabRow('vocab-danger', t.labelDanger, state.vocabulary['danger']);
  renderVocabRow('vocab-food', t.labelFood, state.vocabulary['food']);
  renderVocabRow('vocab-distress', t.labelDistress, state.vocabulary['distress']);
  renderVocabRow('vocab-mate', t.labelMate, state.vocabulary['mate']);
  renderVocabRow('vocab-idle', t.labelIdle, state.vocabulary['idle']);
  renderVocabSummary(state.vocabulary);
  lastCreatures = state.creatures;

  document.getElementById('pause').textContent = state.paused ? t.resumeText : t.pauseText;

  document.getElementById('settings').textContent = mode === 'manual'
    ? t.settingsManual()
    : t.settingsAuto(predatorCount);

  if (graphOverlay.style.display === 'flex') renderGraphOverlay(state);
  if (compareOverlay.style.display === 'flex') renderCompare(state);
  if (translatorOverlay.style.display === 'flex') renderTranslator(state.translator);
}

function top3AndOther(pairs) {
  // Mirrors simulation.py's top3_and_other() so all three renderers agree
  // on the cutoff: the 3 largest entries, plus one combined "other" fraction
  // for anything beyond that.
  if (pairs.length <= 3) return [pairs, 0];
  const top = pairs.slice(0, 3);
  const other = pairs.slice(3).reduce((sum, [, frac]) => sum + frac, 0);
  return [top, other];
}

function renderVocabRow(elId, label, pairs) {
  const el = document.getElementById(elId);
  el.innerHTML = '';
  const labelSpan = document.createElement('span');
  labelSpan.textContent = label + ': ';
  labelSpan.style.fontWeight = 'bold';
  el.appendChild(labelSpan);
  const [top, other] = top3AndOther(pairs);
  for (const [token, frac] of top) {
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = TOKEN_COLORS[token];
    if (token === 0) sw.style.border = '1px solid #666';
    el.appendChild(sw);
    const txt = document.createElement('span');
    txt.textContent = Math.round(frac * 100) + '%  ';
    el.appendChild(txt);
  }
  if (other > 0) {
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = '#666';
    el.appendChild(sw);
    const txt = document.createElement('span');
    txt.textContent = Math.round(other * 100) + '% ' + STRINGS[uiLang].vocabOther + '  ';
    el.appendChild(txt);
  }
}

function downsample(values, maxPoints) {
  // Bucket-average down to at most maxPoints - once a run has thousands of
  // samples squeezed into a few hundred pixels, plotting every raw point
  // renders as a dense picket-fence of near-vertical spikes instead of a
  // readable trend.
  if (values.length <= maxPoints) return values;
  const bucket = values.length / maxPoints;
  const out = [];
  for (let i = 0; i < maxPoints; i++) {
    const lo = Math.floor(i * bucket);
    const hi = Math.max(lo + 1, Math.floor((i + 1) * bucket));
    let sum = 0;
    for (let j = lo; j < hi; j++) sum += values[j];
    out.push(sum / (hi - lo));
  }
  return out;
}

function renderSparkline(canvas, history) {
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  if (!history || history.length < 2) return;
  const values = downsample(history, Math.max(2, Math.floor(w)));
  ctx.strokeStyle = '#96c882';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  const step = w / (values.length - 1);
  values.forEach((v, i) => {
    const px = i * step;
    const py = h - 1 - v * (h - 2);
    if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
  });
  ctx.stroke();
}

function renderGraphOverlay(state) {
  for (const key of ['danger', 'food', 'distress', 'mate', 'idle']) {
    const history = state.vocab_history[key];
    renderSparkline(document.getElementById('graph-' + key), history);
    const cur = history && history.length ? Math.round(history[history.length - 1] * 100) + '%' : '-';
    document.getElementById('graph-cur-' + key).textContent = cur;
  }
  document.getElementById('graph-traits-section').style.display = state.adaptive_traits ? 'block' : 'none';
  if (state.adaptive_traits) {
    for (const key of ['speed', 'vision', 'hearing', 'metabolism']) {
      const history = state.trait_history[key];
      renderSparkline(document.getElementById('graph-' + key), history);
      const cur = history && history.length ? Math.round(history[history.length - 1] * 100) + '%' : '-';
      document.getElementById('graph-cur-' + key).textContent = cur;
    }
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
  return Number.isFinite(raw) ? raw : 100;
}
async function startGame(mode) {
  const useAi = document.getElementById('useAi').checked;
  const adaptiveTraits = document.getElementById('adaptiveTraits').checked;
  const res = await post('start', {mode, init_pop: startingInitPop(), use_ai: useAi, adaptive_traits: adaptiveTraits});
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
document.getElementById('startAuto').onclick = () => { initSound(); startGame('auto'); };
document.getElementById('startManual').onclick = () => { initSound(); startGame('manual'); };
document.getElementById('startResume').onclick = () => { initSound(); resumeGame(); };
document.getElementById('pause').onclick = () => post(paused ? 'resume' : 'pause');
document.getElementById('reset').onclick = () => post('reset');
document.getElementById('save').onclick = () => saveGame();
document.getElementById('faster').onclick = () => post('speed', {value: stepSpeed(currentSpeed, 1)});
document.getElementById('slower').onclick = () => post('speed', {value: stepSpeed(currentSpeed, -1)});
document.getElementById('predLess').onclick = () => post('predator_count', {delta: -1});
document.getElementById('header').onclick = () => { hudExpanded = !hudExpanded; applyHudExpanded(); };
document.getElementById('predMore').onclick = () => post('predator_count', {delta: 1});

const helpOverlay = document.getElementById('help-overlay');
document.getElementById('openHelp').onclick = () => { helpOverlay.style.display = 'flex'; };
document.getElementById('closeHelp').onclick = () => { helpOverlay.style.display = 'none'; };
helpOverlay.addEventListener('click', (ev) => {
  if (ev.target === helpOverlay) helpOverlay.style.display = 'none';
});

const faqOverlay = document.getElementById('faq-overlay');
document.getElementById('openFaq').onclick = () => { faqOverlay.style.display = 'flex'; };
document.getElementById('closeFaq').onclick = () => { faqOverlay.style.display = 'none'; };
faqOverlay.addEventListener('click', (ev) => {
  if (ev.target === faqOverlay) faqOverlay.style.display = 'none';
});

const graphOverlay = document.getElementById('graph-overlay');
document.getElementById('openGraph').onclick = () => { graphOverlay.style.display = 'flex'; };
document.getElementById('closeGraph').onclick = () => { graphOverlay.style.display = 'none'; };
graphOverlay.addEventListener('click', (ev) => {
  if (ev.target === graphOverlay) graphOverlay.style.display = 'none';
});

const familyOverlay = document.getElementById('family-overlay');
const familyContent = document.getElementById('family-content');

function renderFamily(info) {
  const t = STRINGS[uiLang];
  if (!info) {
    familyContent.innerHTML = `<p>${t.familyNone}</p>`;
    return;
  }
  const status = info.alive ? t.familyAlive(info.token, info.age) : t.familyDead(info.death);
  let html = `<p class="fam-id">#${info.id} — ${t.familyGen(info.gen)}</p>`;
  html += `<p>${status}</p>`;
  html += `<p>${t.familyBorn(info.birth)}</p>`;
  html += `<p class="fam-label">${t.familyParents}</p>`;
  if (info.parents.length) {
    for (const pid of info.parents) html += `<p class="fam-item">#${pid}</p>`;
  } else {
    html += `<p class="fam-item">${t.familyFounder}</p>`;
  }
  html += `<p class="fam-label">${t.familyChildren(info.children.length)}</p>`;
  if (info.children.length) {
    for (const cid of info.children.slice(0, 8)) html += `<p class="fam-item">#${cid}</p>`;
    if (info.children.length > 8) html += `<p class="fam-item">... +${info.children.length - 8}</p>`;
  } else {
    html += `<p class="fam-item">${t.familyNoChildren}</p>`;
  }
  html += `<p class="fam-label">${t.familyDescendants(info.total_descendants, info.alive_descendants)}</p>`;
  familyContent.innerHTML = html;
}

async function openFamily() {
  const res = await post('family_open');
  familyOverlay.style.display = 'flex';
  renderFamily(res.family);
}
async function navFamily(dir) {
  const res = await post('family_nav', {dir});
  renderFamily(res.family);
}
document.getElementById('openFamily').onclick = () => { openFamily(); };
document.getElementById('closeFamily').onclick = () => { familyOverlay.style.display = 'none'; };
document.getElementById('famUp').onclick = () => navFamily('up');
document.getElementById('famDown').onclick = () => navFamily('down');
document.getElementById('famLeft').onclick = () => navFamily('left');
document.getElementById('famRight').onclick = () => navFamily('right');
familyOverlay.addEventListener('click', (ev) => {
  if (ev.target === familyOverlay) familyOverlay.style.display = 'none';
});
document.addEventListener('keydown', (ev) => {
  if (familyOverlay.style.display !== 'flex') return;
  if (ev.key === 'ArrowUp') navFamily('up');
  else if (ev.key === 'ArrowDown') navFamily('down');
  else if (ev.key === 'ArrowLeft') navFamily('left');
  else if (ev.key === 'ArrowRight') navFamily('right');
  else if (ev.key === 'Escape') familyOverlay.style.display = 'none';
});

const compareOverlay = document.getElementById('compare-overlay');
const compareConfig = document.getElementById('compare-config');
const compareProgressView = document.getElementById('compare-progress-view');
const compareResultsView = document.getElementById('compare-results-view');
const compareResultsContent = document.getElementById('compare-results-content');
const compareTraitsLabel = document.getElementById('compare-mode-traits-label');
const compareTraitsRadio = document.querySelector('input[name="compareMode"][value="traits"]');

function renderCompare(state) {
  const t = STRINGS[uiLang];
  const compare = state.compare || {running: false, result: null, progress: {}};

  compareTraitsRadio.disabled = !state.adaptive_traits;
  compareTraitsLabel.classList.toggle('disabled', !state.adaptive_traits);
  compareTraitsLabel.querySelector('span').textContent =
    state.adaptive_traits ? t.compareModeTraits : t.compareModeTraitsUnavailable;
  if (!state.adaptive_traits && compareTraitsRadio.checked) {
    document.querySelector('input[name="compareMode"][value="language"]').checked = true;
  }

  if (compare.result) {
    compareConfig.style.display = 'none';
    compareProgressView.style.display = 'none';
    compareResultsView.style.display = 'block';
    renderCompareResults(compare.result);
  } else if (compare.running) {
    compareConfig.style.display = 'none';
    compareProgressView.style.display = 'block';
    compareResultsView.style.display = 'none';
    const p = compare.progress;
    document.getElementById('compare-progress-text').textContent =
      t.compareProgress(Math.max(1, p.seed || 0), p.n_seeds || 0, p.tick || 0, p.ticks || 0);
    const frac = p.ticks ? Math.min(1, (p.tick || 0) / p.ticks) : 0;
    document.getElementById('compare-progress-bar-fill').style.width = (frac * 100) + '%';
  } else {
    compareConfig.style.display = 'block';
    compareProgressView.style.display = 'none';
    compareResultsView.style.display = 'none';
  }
}

function renderCompareResults(result) {
  const t = STRINGS[uiLang];
  let html = `<p>${t.compareResultTitle(result.n_seeds, result.ticks)}</p>`;
  if (result.mode === 'traits') {
    html += `<table><tr><th>${t.compareColTrait}</th><th>${t.compareColMean}</th>` +
      `<th>${t.compareColStd}</th><th>${t.compareColMin}</th><th>${t.compareColMax}</th></tr>`;
    const traitKeys = ['speed', 'vision', 'hearing', 'metabolism'];
    const traitLabels = {speed: t.traitSpeed, vision: t.traitVision, hearing: t.traitHearing, metabolism: t.traitMetabolism};
    for (const key of traitKeys) {
      const vals = result.results.map((r) => r.traits[key] * 100);
      const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
      const std = Math.sqrt(vals.reduce((a, b) => a + (b - mean) ** 2, 0) / vals.length);
      html += `<tr><td>${traitLabels[key]}</td><td>${mean.toFixed(1)}%</td><td>${std.toFixed(1)}%</td>` +
        `<td>${Math.min(...vals).toFixed(1)}%</td><td>${Math.max(...vals).toFixed(1)}%</td></tr>`;
    }
    html += '</table>';
  } else {
    html += `<table><tr><th>${t.compareColState}</th>`;
    result.results.forEach((_, i) => { html += `<th>${t.compareColSeed(i + 1)}</th>`; });
    html += '</tr>';
    const stateKeys = ['danger', 'food', 'distress', 'mate', 'idle'];
    const stateLabels = {danger: t.labelDanger, food: t.labelFood, distress: t.labelDistress,
                          mate: t.labelMate, idle: t.labelIdle};
    for (const key of stateKeys) {
      html += `<tr><td>${stateLabels[key]}</td>`;
      for (const r of result.results) {
        const token = r.vocab[key][0];
        const style = token === 0
          ? 'border:1px solid #666; background:transparent'
          : `background:${TOKEN_COLORS[token] || TOKEN_COLORS[0]}`;
        html += `<td><span class="swatch" style="${style}"></span></td>`;
      }
      html += '</tr>';
    }
    html += '</table>';
    const clean = result.results.filter((r) => !r.collision).length;
    html += `<p>${t.compareCollisionSummary(clean, result.n_seeds)}</p>`;
  }
  if (result.cancelled) html += `<p>${t.compareCancelledNote(result.n_seeds)}</p>`;
  compareResultsContent.innerHTML = html;
}

document.getElementById('openCompare').onclick = () => { compareOverlay.style.display = 'flex'; };
document.getElementById('closeCompare').onclick = () => { compareOverlay.style.display = 'none'; };
document.getElementById('compareStart').onclick = () => {
  const mode = document.querySelector('input[name="compareMode"]:checked').value;
  const depth = document.querySelector('input[name="compareDepth"]:checked').value;
  post('compare_start', {mode, depth});
};
document.getElementById('compareCancel').onclick = () => post('compare_cancel');
document.getElementById('compareAgain').onclick = () => post('compare_dismiss');
compareOverlay.addEventListener('click', (ev) => {
  if (ev.target === compareOverlay) compareOverlay.style.display = 'none';
});

const translatorOverlay = document.getElementById('translator-overlay');
const translatorContent = document.getElementById('translator-content');

function renderTranslator(translator) {
  const t = STRINGS[uiLang];
  const stateLabels = {danger: t.labelDanger, food: t.labelFood, distress: t.labelDistress,
                        mate: t.labelMate, idle: t.labelIdle};
  let html = '';
  for (let token = 0; token < 6; token++) {
    const claims = (translator && translator[String(token)]) || [];
    const style = token === 0
      ? 'border:1px solid #666; background:transparent'
      : `background:${TOKEN_COLORS[token] || TOKEN_COLORS[0]}`;
    const text = claims.length
      ? claims.map(([s, frac]) => `${stateLabels[s]} (${Math.round(frac * 100)}%)`).join(' / ')
      : t.translatorUnused;
    html += `<div class="translator-row"><span class="swatch" style="${style}"></span><span>${text}</span></div>`;
    if (claims.length > 1) html += `<div class="translator-homonym">${t.translatorHomonym}</div>`;
  }
  translatorContent.innerHTML = html;
}

document.getElementById('openTranslator').onclick = () => { translatorOverlay.style.display = 'flex'; };
document.getElementById('closeTranslator').onclick = () => { translatorOverlay.style.display = 'none'; };
translatorOverlay.addEventListener('click', (ev) => {
  if (ev.target === translatorOverlay) translatorOverlay.style.display = 'none';
});

canvas.addEventListener('click', (ev) => {
  const rect = canvas.getBoundingClientRect();
  const px = (ev.clientX - rect.left) * (canvas.width / rect.width);
  const py = (ev.clientY - rect.top) * (canvas.height / rect.height);
  const scale = canvas.width / worldW;
  post('click', {x: px / scale, y: py / scale, button: 'left'});
});
canvas.addEventListener('contextmenu', (ev) => {
  ev.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const px = (ev.clientX - rect.left) * (canvas.width / rect.width);
  const py = (ev.clientY - rect.top) * (canvas.height / rect.height);
  const scale = canvas.width / worldW;
  post('click', {x: px / scale, y: py / scale, button: 'right'});
});
canvas.addEventListener('mousemove', (ev) => {
  const rect = canvas.getBoundingClientRect();
  const px = (ev.clientX - rect.left) * (canvas.width / rect.width);
  const py = (ev.clientY - rect.top) * (canvas.height / rect.height);
  updateListening(px, py);
});
canvas.addEventListener('mouseleave', () => {
  if (gainNode) gainNode.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.05);
});

document.getElementById('muteSound').onclick = () => {
  soundMuted = !soundMuted;
  updateMuteButton();
  if (soundMuted && gainNode) gainNode.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.05);
};

document.addEventListener('keydown', (ev) => {
  if (document.getElementById('app').style.display === 'none') return;
  const anyOverlayOpen = [helpOverlay, faqOverlay, graphOverlay, familyOverlay, compareOverlay, translatorOverlay]
    .some((el) => el.style.display === 'flex');
  if (anyOverlayOpen) return;
  if (ev.key === 'n' || ev.key === 'N') post('quick_place', {kind: 'food'});
  else if (ev.key === 'p' || ev.key === 'P') post('quick_place', {kind: 'predator'});
  else if (ev.key === 'v' || ev.key === 'V') { hudExpanded = !hudExpanded; applyHudExpanded(); }
  else if (ev.key === 'm' || ev.key === 'M') {
    soundMuted = !soundMuted;
    updateMuteButton();
    if (soundMuted && gainNode) gainNode.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.05);
  }
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
