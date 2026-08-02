"""Watch a Thronglets world live in a window.

Runs fullscreen at the desktop's own resolution, stretching the world to
fill the screen exactly (each axis scaled independently, so no letterbox
bars regardless of aspect ratio). ESC quits back to the desktop.

You pick a language, automatic or manual mode, and whether to seed the AI
language once, at startup - not something you toggle mid-run.

Optionally, the creatures can also learn who you are - a start-screen
choice (default OFF, so a bare run stays pure natural selection, the
game's original spirit). Turn it on and the opt-in Mind system in
simulation.py runs here: the mouse cursor is your "hand",
and the two things you place are the lesson. Drop food near a creature and
it - and the ones close enough to witness it - learn the hand is worth
approaching; drop a predator and they learn to flee it. Over a session the
flock comes to trust or fear you (shown on its own line under the HUD
header and as a sparkline in the Graph screen), and passes what it learned
to its offspring. With it off, none of that HUD/graph appears.

Controls:
  SPACE        pause / resume
  UP / DOWN    simulation speed (ticks per real second - x1 is a genuine 1 tick/s)
  R            reset to a fresh world
  N / P        drop food / add a predator at a random spot (the flock learns from it)
  LEFT/RIGHT CLICK   place food / a predator at the clicked spot (kindness / harm)
  [ / ]        remove/add a predator right now
  F            fire tool: arm it, then left-click or drag to burn creatures
  I            (Master Mode) hold over a creature to isolate it until it obeys
  1/2/3/4      (Master Mode) order the broken: follow / gather / disperse / halt
               (Master Mode: no predators, no reproduction; left-click feeds,
                right-click births a new creature, F still kills)
  G            graph screen (vocab, traits, and the flock's feeling toward you)
  V            show/hide the full HUD (or click the top HUD strip)
  M            mute the proximity-listening sound
  H            in-game notice/help screen
  F11          fullscreen on/off (Alt+Enter too) - the window starts maximised,
               not fullscreen, and can be resized freely at any time
  ESC          quit

At the start menu, T opens the Measure screen: pick which of the report's seven
tests to run, how many seeds and how many ticks, and it writes the same file
report.py writes - running the same function, so the two cannot disagree. It
times this machine while you choose and shows what the run will cost before you
start it, which the command line cannot.
"""

import argparse
import math
import os
import random
import sys
import threading
import time

import numpy as np
import pygame

import report
import simulation
import tuning
from i18n import STATE_LABELS, TRAIT_LABELS, disposition_label
from simulation import (DANGER, DISTRESS, FOOD, Genome, HAND_PERCEPTION, HEIGHT, IDLE, MATE, MAX_POPULATION, N_TOKENS,
                         load_bundled_genome,
                         N_TRAITS, World, WIDTH, compare_seeds, load_seed_genome, load_world, save_world, top3_and_other,
                         MEM_ROWS, MEM_COLS, MEM_CLIP, UPRISING_UNREST,
                         ACT_APPROACH, ACT_FLEE, ACT_IGNORE, F_HAND, F_PREDATOR, F_FOOD, REPLAY_SIZE)

# When learning is on, a creature's fill colour shows its inner emotion (so a
# panic rippling through the flock is visible as a wave of red); the signal-token
# ring around it is unchanged. Off, creatures keep the plain BODY_COLOR.
MOOD_FILL = {"joy": (120, 210, 100), "neutral": (150, 150, 140),
             "sad": (90, 130, 215), "fear": (225, 85, 75)}

# The fire tool (F arms it): a click or drag burns every creature within this
# world-space radius of the cursor - so "one or several" is just a matter of how
# many are under the brush. Each burned creature learns fear (deliver_experience)
# and dies, leaving a brief flame.
FIRE_RADIUS = 12.0
FLAME_DUR = 0.6           # seconds a flame puff lingers where a creature burned
FLAME_COLORS = [(255, 240, 120), (255, 150, 40), (220, 60, 30)]

# Master Mode: hold I over a creature to isolate it in accelerated time. A few
# seconds of holding drives its obedience from 0 to 1 while, for the creature,
# many subjective months of solitude crawl by.
DOMINATE_RATE = 0.22     # obedience gained per real second of isolation
DOMINATE_DAYS_PER_SEC = 90.0   # subjective days that pass per real second held
OBEDIENT_COLOR = (150, 150, 158)   # the hollow grey of a broken creature


def _subjective_span(days, lang):
    """Turn accumulated subjective days into 'N days/weeks/months/years alone'."""
    if days < 14:
        n, unit = int(days), ("jours" if lang == "fr" else "days")
    elif days < 90:
        n, unit = int(days / 7), ("semaines" if lang == "fr" else "weeks")
    elif days < 730:
        n, unit = int(days / 30), ("mois" if lang == "fr" else "months")
    else:
        n, unit = int(days / 365), ("ans" if lang == "fr" else "years")
    return f"{n} {unit}"


def burn_at(world, wx, wy, flames):
    """Burn every living creature within FIRE_RADIUS of (wx, wy): each learns
    fear from it (a no-op when learning is off) and dies, leaving a flame."""
    for c in list(world.creatures):
        if not c.alive:
            continue
        if (c.pos[0] - wx) ** 2 + (c.pos[1] - wy) ** 2 <= FIRE_RADIUS ** 2:
            world.deliver_experience(c, LEARN_PREDATOR_REWARD)   # teach fear (+ witnesses)
            world.kill_creature(c)
            flames.append([float(c.pos[0]), float(c.pos[1]), 0.0])

TRAIN_EPISODES = 3000
TRAIN_BATCH_SIZE = 256
TRAIN_LR = 0.01

DEFAULT_INIT_POP = 100
DEFAULT_LANGUAGE_FILE = "language_model.json"
DEFAULT_SAVE_FILE = "thronglets_save.json"

EXPANDED_HUD_H = 304
MINIMAL_HUD_H = 76
HUD_H = MINIMAL_HUD_H  # the HUD starts collapsed; V or a click on it expands it
# Placeholder sizes - open_window() overwrites these with the real window size,
# and sync_screen() keeps them there as the player resizes. The world is
# stretched per-axis to exactly fill whatever it is given, so there is no fixed
# aspect ratio and no letterboxing on either axis at any window shape.
SCREEN_W, SCREEN_H = int(WIDTH * 5), int(HEIGHT * 5) + HUD_H
SCALE_X, SCALE_Y = 5.0, 5.0

BG = (18, 22, 16)
GROUND = (30, 38, 24)
HUD_BG = (10, 12, 9)
HUD_SEP = (44, 52, 38)       # thin rule between HUD sections
HUD_ACCENT = (150, 200, 130) # section titles
HUD_HINT = (140, 146, 132)   # secondary / hint text
TEXT_COLOR = (220, 220, 210)
FOOD_COLOR = (110, 220, 90)
BODY_COLOR = (222, 208, 150)
PREDATOR_COLOR = (220, 30, 30)
TOKEN_COLORS = [
    (120, 120, 120),  # 0: silence, not drawn as a ring
    (235, 70, 70),
    (70, 140, 235),
    (245, 200, 60),
    (200, 90, 230),
    (70, 225, 210),
]
# A pentatonic scale (C4 D4 E4 G4 A4) so any combination of tokens sounds
# pleasant together - index 0 (silence) is never looked up, no tone assigned.
TOKEN_FREQS = [0, 261.63, 293.66, 329.63, 392.00, 440.00]
LISTEN_RADIUS = 10.0  # world units - how close the mouse must be to hear a creature

# Emergent learning (the opt-in Mind system, reused from
# simulation.py). Here the player's "hand" is the mouse cursor, and the two
# things you place are the reward: dropping food nearby is kindness the
# creatures learn to approach, dropping a predator is harm they learn to
# flee - and every creature close enough to witness it learns a weaker
# version too (World.deliver_experience handles the observers). Over a
# session the flock comes to trust or fear you, and passes what it learned
# to its offspring.
LEARN_FOOD_REWARD = 1.0
LEARN_PREDATOR_REWARD = -1.0


def teach_nearby(world, x, y, reward):
    """The player just placed food (reward > 0) or a predator (reward < 0)
    at (x, y). Teach the nearest creature within reach - and, through
    World.deliver_experience, the witnesses around it. A no-op when learning
    is off or nobody is close enough to be affected."""
    if not getattr(world, "learning", False):
        return
    point = np.array([x, y], dtype=float)
    nearest, best = None, HAND_PERCEPTION
    for c in world.creatures:
        if not c.alive:
            continue
        d = float(np.linalg.norm(np.asarray(c.pos, dtype=float) - point))
        if d < best:
            nearest, best = c, d
    if nearest is not None:
        world.deliver_experience(nearest, reward)


TEXT = {
    "en": {
        "choose_mode_prompt": "Choose the starting mode:",
        "choose_mode_auto": "  A = automatic - food and predators spawn on their own (default)",
        "choose_mode_manual": "  M = manual - you place everything yourself, nothing spawns alone",
        "choose_mode_hint": "Press A or M, or ENTER for the default (automatic).",

        "choose_pop_prompt": "How many creatures to start with? (1-{max}, default {default})",
        "choose_pop_hint": "Press ENTER to confirm.",

        "choose_traits_prompt": "Adaptive evolution: speed, vision, hearing, metabolism?",
        "choose_traits_explain1": "  Each creature gets its own physical stats, inherited and mutated -",
        "choose_traits_explain2": "  but faster/keener senses cost more energy, so it's a real trade-off.",
        "choose_traits_yes": "  Y = yes - physical traits evolve too, not just signaling (default)",
        "choose_traits_no": "  N = no - everyone has the same fixed stats",
        "choose_traits_hint": "Press Y or N, or ENTER for the default (yes).",

        "choose_learning_prompt": "Let the flock learn to trust or fear you?",
        "choose_learning_explain1": "  Placing food is kindness, a predator is harm - creatures learn",
        "choose_learning_explain2": "  which, adapt to you, and pass it on. Not evolution: a learned mind.",
        "choose_learning_yes": "  Y = yes - the flock adapts to how you treat it",
        "choose_learning_no": "  N = no - pure natural selection, the original spirit (default)",
        "choose_learning_hint": "Press Y or N, or ENTER for the default (no).",

        "choose_ai_prompt": "Activate the pre-trained AI language?",
        "choose_ai_subtitle": "  (reads '{file}', generated by train_language.py)",
        "choose_ai_yes": "  Y = yes - creatures already speak an unambiguous language",
        "choose_ai_train": "  T = train a new one now, live, right here",
        "choose_ai_no": "  N = no - the language has to emerge on its own while you play (default)",
        "choose_ai_hint": "Press Y, T, or N, or ENTER for the default (no).",
        "ai_missing_file": "'{file}' not found - starting without AI.",
        "flash_hint": "-- press any key to continue --",

        "torch_missing": "PyTorch isn't installed - can't train here. Run 'pip install torch',\nor use a language_model.json trained elsewhere. Starting without AI.",
        "training_seed": "Training seed {seed} - this takes a little while, ESC cancels",
        "training_progress": "step {step}/{episodes}   loss {loss:.3f}   listener accuracy {acc:.0f}%",
        "training_elapsed": "{elapsed:.0f}s elapsed   {rate:.0f} steps/s",
        "training_explain": "Loss = how wrong the Listener's guesses still are (lower = better).",
        "training_explain2": "Accuracy = % of guesses it currently gets right, on this batch.",
        "training_live_title": "Current guess per state (still shifting - not final yet):",
        "training_result": "Seed {seed}: {outcome}   (overall accuracy {acc:.0f}%)",
        "training_clean": "no collisions - every state got its own color",
        "training_collision": "collision - two states share a color",
        "training_validate_hint": "V = use this seed   N = try another seed   ESC = cancel, no AI",
        "training_collision_hint": "This seed has a collision, can't be used as-is - N = try another seed   ESC = cancel, no AI",

        "choose_resume_prompt": "A saved game was found. Resume it?",
        "choose_resume_subtitle": "  (reads '{file}' - the population, food, and predators as you left them)",
        "choose_resume_yes": "  Y = yes - pick up exactly where you left off",
        "choose_resume_no": "  N = no - start a fresh game instead",
        "choose_resume_hint": "Press Y or N to continue.",
        "resume_load_failed": "'{file}' could not be read - starting a fresh game instead.",
        "choose_start_prompt": "Thronglets - choose how to begin:",
        "choose_start_resume": "  R = resume the saved game",
        "choose_start_new": "  N = new game",
        "choose_start_master": "  M = MASTER MODE - break their will until they obey (White Christmas)",
        "choose_start_tuning": "  P = parameters - see and change every number in the simulation",
        "choose_start_pinned": "      ({n} pinned as your defaults)",
        "tuning_title": "Parameters - everything that shapes the simulation",
        "tuning_hint": "UP/DOWN move   LEFT/RIGHT change (hold SHIFT for x10)   BACKSPACE reset this one",
        "tuning_hint2": "D = make these my defaults   R = reset everything   ESC = back",
        "tuning_was": "(was {v})",
        "tuning_footer": "{shown} parameters   {moved} changed from built-in   {pinned} pinned as defaults",
        "tuning_status_ready": "{n} of your saved defaults are in force",
        "tuning_status_saved": "{n} written to {file} - these are your defaults from now on",
        "tuning_status_cleared": "nothing differs from built-in any more - your defaults file was removed",
        "tuning_status_reset": "everything back to the built-in values",
        "tuning_status_one_reset": "{name} back to its built-in value",
        "tuning_status_locked": "{name} cannot be changed: {why}",
        "choose_start_measure": "  T = measure - run the report on this machine and get a file",
        "choose_start_hint": "Press R, N, M, P or T   (ENTER = new game).",
        "meas_title": "MEASURE - run the report on this machine",
        "meas_hint": "up/down = move   SPACE = include/exclude a test   left/right = change a number (shift = x10)",
        "meas_hint2": "A = all   Z = none   ENTER = run   ESC = back",
        "meas_scenarios": "WHICH TESTS TO RUN",
        "meas_size": "HOW BIG",
        "meas_seeds": "seeds per test",
        "meas_seeds_doc": "different worlds per test - more seeds narrows the spread, which is what decides a close call",
        "meas_ticks": "ticks per world",
        "meas_ticks_doc": "how long each world lives - long worlds are what reveal drift over generations",
        "meas_budget": "THE BILL",
        "meas_total": "{tests} tests x {seeds} seeds x {ticks} ticks = {total} ticks to live through",
        "meas_rate_measuring": "measuring this machine's speed... ({n} ticks timed so far)",
        "meas_rate": "this machine: {rate:.0f} ticks/second, measured here just now",
        "meas_eta": "estimated: {eta}",
        "meas_eta_warn": "estimated: {eta}   <- that is a long time. Fewer seeds or fewer ticks.",
        "meas_none": "no test selected - press SPACE on one, or A for all",
        "meas_running": "RUNNING - {done}/{total} worlds   {title}  seed {seed}",
        "meas_elapsed": "elapsed {el}   left about {left}",
        "meas_cancel": "ESC = stop (nothing is written)",
        "meas_stopping": "stopping...",
        "meas_written": "written to {file}",
        "meas_written2": "send me that file",
        "meas_cancelled": "stopped - nothing written",
        "meas_failed": "the run failed: {err}",
        "meas_pinned": "your {n} pinned parameter(s) are in force and are recorded in the file",
        "meas_builtin": "no pinned parameters - measuring the game as shipped",
        "master_banner": "MASTER MODE - hold I to break  |  left-click feeds  |  right-click births  |  F to kill",
        "master_obedience": "obedience of the flock: {pct:.0%}",
        "master_readout": "obedience {ob:.0%}    unrest {unrest:.0%}",
        "master_uprising": "UPRISING - the frightened are freeing the broken, your grip is slipping!",
        "master_isolating": "isolating #{cid}: {span} alone...  obedience {pct:.0%}",
        "order_follow": "follow", "order_gather": "gather", "order_disperse": "disperse", "order_halt": "halt",
        "master_order_line": "order to the broken: {name}   [1 follow  2 gather  3 disperse  4 halt]",
        "save_confirmed": "Game saved to '{file}'.",

        "hud_paused": "PAUSED",
        "hud_trained_tag": "[trained vocabulary]",
        "hud_traits_tag": "[adaptive traits]",
        "hud_muted_tag": "[sound muted]",
        "hud_header": "tick {tick:>6}   pop {pop:>4}   births {births:>5}   deaths {deaths:>5}   {status}",
        "hud_controls_hint1": "(space=pause  up/down=speed  r=reset  s=save  g=graph",
        "hud_controls_hint2": " t=family  c=compare  d=translator  ?=faq  h=help  m=mute  F11=fullscreen)",
        "hud_controls_hint3": "n/click = food   p/right-click = predator   f = fire tool",
        "hud_fire_armed": "FIRE - left-click or drag to burn   (F to stop)",
        "hud_expand_hint": "V or click here = show full HUD",
        "hud_manual": "mode: manual (no automatic spawning)",
        "hud_auto": "mode: automatic   predators: {count} ([ / ] act immediately)",
        "hud_vocab_title": "vocabulary — top 3 colors per state, population share:",
        "vocab_other": "other",
        "hud_disposition": "learning: the flock {label} ({pct:+.0%})",
        "graph_disposition": "the flock's feeling toward you: {pct:+.0%} ({label})",
        "graph_title": "Vocabulary over time - dominant share per state",
        "graph_traits_title": "Physical traits over time - population average (share of range)",
        "graph_dismiss": "-- press any key to go back --",
        "legend_creature": "creature (ring = its current signal)",
        "legend_food": "food",
        "legend_predator": "predator",
        "hud_mood_title": "mood (body colour):",
        "mood_calm": "calm",
        "mood_joy": "happy",
        "mood_sad": "sad",
        "mood_fear": "afraid",
        "hud_choice_approach": "coming",
        "hud_choice_flee": "fleeing",
        "hud_choice_ignore": "ignoring you",
        "hud_memory_hint": "hover a creature: green = places it trusts, red = places it fears",
        "extinct": "Extinct. Press R to start a new world.",

        "mind_title": "INSIDE THIS ONE",
        "mind_expects": "expects of this moment",
        "mind_decided": "has decided to",
        "mind_surprise": "surprise",
        "mind_dread": "what a hunter means to it",
        "mind_dread_none": "has not understood hunters yet",
        "mind_dread_runs": "runs {pct:+.0f}% harder for it",
        "mind_words": "what the flock's calls mean to it",
        "mind_dwells": "cannot stop going over",
        "mind_dwells_none": "nothing has shocked it yet",
        "act_approach": "come to you",
        "act_flee": "get away",
        "act_ignore": "ignore you",
        "mem_hand": "your hand",
        "mem_predator": "a predator",
        "mem_food": "food",
        "mem_other": "a moment",

        "translator_title": "Translator - what each color currently means",
        "translator_unused": "unused / ambiguous",
        "translator_homonym": "  ! homonym - shared with another state",
        "translator_col_word": "the word - inherited",
        "translator_col_meaning": "what it came to mean - learned",
        "translator_dreaded": "dreaded",
        "translator_welcomed": "welcomed",
        "translator_noise": "still just noise",
        "translator_learned_hint": "which colour means which state is inherited; what it predicts is learned in one lifetime",

        "family_title": "Family tree",
        "family_gen": "generation {gen}",
        "family_alive": "alive - token {token}, age {age}",
        "family_dead": "dead since tick {death}",
        "family_born": "born at tick {tick}",
        "family_parents": "Parents:",
        "family_founder": "none - founding generation",
        "family_children": "Children ({n}):",
        "family_no_children": "none yet",
        "family_descendants": "Total descendants: {total} ({alive} still alive)",
        "family_hint": "UP=parent   DOWN=child   LEFT/RIGHT=siblings   T or ESC=go back",
        "family_none": "No creature to show yet.",

        "compare_mode_prompt": "Compare seeds: what should be reproducible?",
        "compare_mode_language": "  L = language - does the same word win across independent runs?",
        "compare_mode_traits": "  T = physical traits - do speed/vision/hearing/metabolism converge the same way?",
        "compare_mode_traits_unavailable": "  (traits unavailable - adaptive evolution is off for this world)",
        "compare_mode_hint": "Press L or T, or ESC to cancel.",
        "compare_depth_prompt": "How thorough?",
        "compare_depth_quick": "  R = quick - 4 seeds x 8,000 ticks (default)",
        "compare_depth_thorough": "  A = thorough - 8 seeds x 40,000 ticks, same as the manual check earlier",
        "compare_depth_expert": "  E = expert - 16 seeds x 60,000 ticks, runs one at a time - can take a while",
        "compare_depth_hint": "Press R, A, or E, or ENTER for the default (quick). ESC cancels.",
        "compare_progress": "seed {seed}/{n_seeds}   tick {tick}/{ticks}   ESC cancels",
        "compare_result_title": "Comparison done ({n_seeds} seeds x {ticks} ticks)",
        "compare_traits_header": "trait          mean   std dev    min     max",
        "compare_lang_header": "state          seeds' dominant color",
        "compare_collision_summary": "Collisions: {clean}/{n_seeds} seeds had none",
        "compare_dismiss": "-- ESC to go back --",
        "compare_cancelled": "Cancelled - {n} seed(s) completed before stopping.",

        "help_more": "-- space for more --",
        "help_dismiss": "-- press any key to resume --",
        "help_lines": [
            ("Thronglets - notice", True),
            ("", False),
            ("Each creature is born with a genome deciding which color it shows for", False),
            ("its current state, and how it reacts to colors it hears from others.", False),
            ("Nobody programs what a color means - a shared language can emerge", False),
            ("through natural selection, or it might not.", False),
            ("", False),
            ("The 5 states, in priority order:", True),
            ("  1. alarm-call    a predator was spotted -> flee immediately", False),
            ("  2. food-call     food is visible nearby", False),
            ("  3. distress-call energy critically low, no food in sight", False),
            ("  4. mate-call     ready to mate, and a ready partner is nearby", False),
            ("  5. idle          nothing special (by far the most common state)", False),
            ("", False),
            ("Living, mating, dying:", True),
            ("  Energy drains constantly; eating restores it. Emitting a color", False),
            ("  (other than silence) costs a bit of extra energy. Enough energy", False),
            ("  and age, plus a matching partner nearby: a child is born. A", False),
            ("  predator that catches a creature kills it outright.", False),
            ("", False),
            ("Reading the vocabulary rows at the top:", True),
            ("  For each state, the share of the population using each color.", False),
            ("  It starts near chance (~17%) and climbs if a token wins out.", False),
            ("  A '..' swatch means silence, not a missing color.", False),
            ("", False),
            ("Worth knowing:", True),
            ("  Two states can end up sharing the same color purely by chance", False),
            ("  (e.g. idle and alarm-call) - nothing prevents it or guarantees", False),
            ("  it resolves. Signaling costs energy, so silence is a real", False),
            ("  strategy, not a default.", False),
        ],
        "faq_lines": [
            ("Thronglets - FAQ", True),
            ("", False),
            ("Q: Why do creatures sometimes stay clustered even with food right", True),
            ("   next to them?", True),
            ("A: Following a neighbor's signal and heading for food are two", False),
            ("   forces that can partly cancel out - an accepted trade-off,", False),
            ("   not a bug.", False),
            ("", False),
            ("Q: Does distress make creatures help each other?", True),
            ("A: No - there's no cooperation mechanic. Distress is treated like", False),
            ("   any other signal, and creatures mostly learn to avoid it.", False),
            ("", False),
            ("Q: Why does the adaptive metabolism trait always drop to near its", True),
            ("   minimum?", True),
            ("A: Unlike speed/vision/hearing, a lower metabolism has zero", False),
            ("   downside here - it's not a real trade-off, so selection", False),
            ("   always pushes it down.", False),
            ("", False),
            ("Q: How can two creatures from very different generations be", True),
            ("   siblings?", True),
            ("A: Generation = max(both parents' generations)+1, and mate choice", False),
            ("   only cares about proximity, not generation - a long-lived", False),
            ("   parent can breed with a much 'deeper' partner late in life.", False),
            ("", False),
            ("Q: Can a creature really mate with its own descendant?", True),
            ("A: Yes - same reason: mate choice is purely proximity-based,", False),
            ("   with no notion of family.", False),
            ("", False),
            ("Q: Even a trained vocabulary can drift or 'flip back' - why?", True),
            ("A: No creature learns anything during its life; genomes are", False),
            ("   fixed at birth. Only mutation and selection across", False),
            ("   generations change anything, and mutation never stops -", False),
            ("   nothing is ever permanently locked in.", False),
            ("", False),
            ("Q: Two states share the same color (homonymy) - is that a bug?", True),
            ("A: No - nothing in the model prevents it. Genomes mutate per", False),
            ("   state independently, so two states can land on the same", False),
            ("   token by pure chance. Check the Translator screen (D) to", False),
            ("   see it clearly.", False),
            ("", False),
            ("Q: A single playthrough shows a surprising result - can I trust", True),
            ("   it?", True),
            ("A: Not on its own. Use the Compare screen (C) to run several", False),
            ("   independent seeds and see whether the result actually", False),
            ("   repeats, or was just one run's drift.", False),
            ("", False),
            ("Q: What's the real difference between the trained AI language", True),
            ("   and the evolved one?", True),
            ("A: The AI (train_language.py) uses gradient descent to directly", False),
            ("   minimize communication error, every step. The evolved", False),
            ("   language only rewards survival and reproduction - comm-", False),
            ("   unicating well is never optimized directly, just indirectly", False),
            ("   useful.", False),
        ],
    },
    "fr": {
        "choose_mode_prompt": "Choisis le mode de depart :",
        "choose_mode_auto": "  A = automatique - nourriture et predateurs apparaissent seuls (defaut)",
        "choose_mode_manual": "  M = manuel - tu places tout toi-meme, rien ne spawn seul",
        "choose_mode_hint": "Appuie sur A ou M, ou ENTREE pour le defaut (auto).",

        "choose_pop_prompt": "Combien de creatures au depart ? (1-{max}, defaut {default})",
        "choose_pop_hint": "Appuie sur ENTREE pour confirmer.",

        "choose_traits_prompt": "Evolution adaptative : vitesse, vision, ouie, metabolisme ?",
        "choose_traits_explain1": "  Chaque creature a ses propres stats physiques, heritees et mutees -",
        "choose_traits_explain2": "  mais etre rapide/perceptif coute plus d'energie, un vrai compromis.",
        "choose_traits_yes": "  O = oui - les traits physiques evoluent aussi, pas juste le langage (defaut)",
        "choose_traits_no": "  N = non - tout le monde a les memes stats fixes",
        "choose_traits_hint": "Appuie sur O ou N, ou ENTREE pour le defaut (oui).",

        "choose_learning_prompt": "Laisser le groupe apprendre a te faire confiance ou a te craindre ?",
        "choose_learning_explain1": "  Nourriture = bienveillance, predateur = mal : les creatures",
        "choose_learning_explain2": "  apprennent, s'adaptent a toi et transmettent. Un esprit appris.",
        "choose_learning_yes": "  O = oui - le groupe s'adapte a la facon dont tu le traites",
        "choose_learning_no": "  N = non - pure selection naturelle, l'esprit d'origine (defaut)",
        "choose_learning_hint": "Appuie sur O ou N, ou ENTREE pour le defaut (non).",

        "choose_ai_prompt": "Activer le langage pre-entraine par IA ?",
        "choose_ai_subtitle": "  (relit '{file}', genere par train_language.py)",
        "choose_ai_yes": "  O = oui - les creatures parlent deja un langage sans confusion",
        "choose_ai_train": "  T = en entrainer un nouveau maintenant, en direct, ici",
        "choose_ai_no": "  N = non - le langage doit emerger tout seul en jouant (defaut)",
        "choose_ai_hint": "Appuie sur O, T ou N, ou ENTREE pour le defaut (non).",
        "ai_missing_file": "'{file}' introuvable - lancement sans IA.",
        "flash_hint": "-- une touche pour continuer --",

        "torch_missing": "PyTorch n'est pas installe - entrainement impossible ici. Lance\n'pip install torch', ou utilise un language_model.json deja entraine ailleurs. Lancement sans IA.",
        "training_seed": "Entrainement de la seed {seed} - ca prend un moment, ESC annule",
        "training_progress": "etape {step}/{episodes}   perte {loss:.3f}   precision {acc:.0f}%",
        "training_elapsed": "{elapsed:.0f}s ecoulees   {rate:.0f} etapes/s",
        "training_explain": "Perte = a quel point le Listener se trompe encore (plus bas = mieux).",
        "training_explain2": "Precision = % de bonnes reponses actuellement, sur ce lot d'essais.",
        "training_live_title": "Devinette actuelle par etat (encore mouvante - pas definitive) :",
        "training_result": "Seed {seed} : {outcome}   (precision globale {acc:.0f}%)",
        "training_clean": "aucune collision - chaque etat a sa propre couleur",
        "training_collision": "collision - deux etats partagent une couleur",
        "training_validate_hint": "V = utiliser cette seed   N = essayer une autre   ESC = annuler, sans IA",
        "training_collision_hint": "Cette seed a une collision, inutilisable telle quelle - N = essayer une autre   ESC = annuler, sans IA",

        "choose_resume_prompt": "Une partie sauvegardee existe. La reprendre ?",
        "choose_resume_subtitle": "  (relit '{file}' - la population, la nourriture et les predateurs tels que laisses)",
        "choose_resume_yes": "  O = oui - reprendre exactement ou tu t'es arrete",
        "choose_resume_no": "  N = non - commencer une nouvelle partie",
        "choose_resume_hint": "Appuie sur O ou N pour continuer.",
        "resume_load_failed": "'{file}' illisible - nouvelle partie a la place.",
        "choose_start_prompt": "Thronglets - choisis comment commencer :",
        "choose_start_resume": "  R = reprendre la partie sauvegardee",
        "choose_start_new": "  N = nouvelle partie",
        "choose_start_master": "  M = MODE MAITRE - briser leur volonte jusqu'a l'obeissance (White Christmas)",
        "choose_start_tuning": "  P = parametres - voir et modifier chaque nombre de la simulation",
        "choose_start_pinned": "      ({n} epingles comme tes valeurs par defaut)",
        "tuning_title": "Parametres - tout ce qui faconne la simulation",
        "tuning_hint": "HAUT/BAS deplacer   GAUCHE/DROITE modifier (SHIFT pour x10)   RETOUR ARRIERE remet celui-ci",
        "tuning_hint2": "D = en faire mes valeurs par defaut   R = tout remettre   ESC = revenir",
        "tuning_was": "(etait {v})",
        "tuning_footer": "{shown} parametres   {moved} modifies   {pinned} epingles par defaut",
        "tuning_status_ready": "{n} de tes valeurs par defaut sont actives",
        "tuning_status_saved": "{n} ecrits dans {file} - ce sont tes valeurs par defaut desormais",
        "tuning_status_cleared": "plus rien ne differe des valeurs d'origine - ton fichier a ete supprime",
        "tuning_status_reset": "tout est revenu aux valeurs d'origine",
        "tuning_status_one_reset": "{name} revenu a sa valeur d'origine",
        "tuning_status_locked": "{name} non modifiable : {why}",
        "choose_start_measure": "  T = tester - lancer le rapport sur cette machine et obtenir un fichier",
        "choose_start_hint": "Appuie sur R, N, M, P ou T   (ENTREE = nouvelle partie).",
        "meas_title": "TESTER - lancer le rapport sur cette machine",
        "meas_hint": "haut/bas = deplacer   ESPACE = inclure/exclure un test   gauche/droite = changer un nombre (maj = x10)",
        "meas_hint2": "A = tout   Z = rien   ENTREE = lancer   ECHAP = retour",
        "meas_scenarios": "QUELS TESTS LANCER",
        "meas_size": "QUELLE TAILLE",
        "meas_seeds": "graines par test",
        "meas_seeds_doc": "mondes differents par test - plus de graines resserre la dispersion, c'est elle qui tranche un cas serre",
        "meas_ticks": "ticks par monde",
        "meas_ticks_doc": "duree de vie de chaque monde - ce sont les mondes longs qui revelent une derive sur des generations",
        "meas_budget": "LA FACTURE",
        "meas_total": "{tests} tests x {seeds} graines x {ticks} ticks = {total} ticks a vivre",
        "meas_rate_measuring": "mesure de la vitesse de cette machine... ({n} ticks chronometres)",
        "meas_rate": "cette machine : {rate:.0f} ticks/seconde, mesure ici a l'instant",
        "meas_eta": "estimation : {eta}",
        "meas_eta_warn": "estimation : {eta}   <- c'est long. Moins de graines ou moins de ticks.",
        "meas_none": "aucun test selectionne - ESPACE sur l'un d'eux, ou A pour tout",
        "meas_running": "EN COURS - {done}/{total} mondes   {title}  graine {seed}",
        "meas_elapsed": "ecoule {el}   reste environ {left}",
        "meas_cancel": "ECHAP = arreter (rien ne sera ecrit)",
        "meas_stopping": "arret en cours...",
        "meas_written": "ecrit dans {file}",
        "meas_written2": "envoie-moi ce fichier",
        "meas_cancelled": "arrete - rien n'a ete ecrit",
        "meas_failed": "le run a echoue : {err}",
        "meas_pinned": "tes {n} parametre(s) epingles sont actifs et sont notes dans le fichier",
        "meas_builtin": "aucun parametre epingle - mesure du jeu tel qu'il est livre",
        "master_banner": "MODE MAITRE - maintiens I pour briser  |  clic gauche nourrit  |  clic droit cree  |  F pour tuer",
        "master_obedience": "obeissance du groupe : {pct:.0%}",
        "master_readout": "obeissance {ob:.0%}    agitation {unrest:.0%}",
        "master_uprising": "SOULEVEMENT - les effrayes liberent les brises, ton emprise lache !",
        "master_isolating": "isolement #{cid} : {span} de solitude...  obeissance {pct:.0%}",
        "order_follow": "au pied", "order_gather": "rassembler", "order_disperse": "disperser", "order_halt": "figer",
        "master_order_line": "ordre aux brises : {name}   [1 au pied  2 rassembler  3 disperser  4 figer]",
        "save_confirmed": "Partie sauvegardee dans '{file}'.",

        "hud_paused": "PAUSE",
        "hud_trained_tag": "[vocabulaire entraine]",
        "hud_traits_tag": "[traits evolutifs]",
        "hud_muted_tag": "[son coupe]",
        "hud_header": "tick {tick:>6}   pop {pop:>4}   naissances {births:>5}   morts {deaths:>5}   {status}",
        "hud_controls_hint1": "(espace=pause  haut/bas=vitesse  r=reset  s=sauver  g=graphique",
        "hud_controls_hint2": " t=famille  c=comparer  d=traducteur  ?=faq  h=aide  m=silence  F11=plein ecran)",
        "hud_controls_hint3": "n/clic = nourriture   p/clic droit = predateur   f = outil feu",
        "hud_fire_armed": "FEU - clic gauche ou glisser pour bruler   (F pour arreter)",
        "hud_expand_hint": "V ou clique ici = HUD complet",
        "hud_manual": "mode: manuel (pas d'apparition automatique)",
        "hud_auto": "mode: auto   predateurs : {count} ([ / ] agit tout de suite)",
        "hud_vocab_title": "vocabulaire — top 3 couleurs par etat, part de la population :",
        "vocab_other": "autre",
        "hud_disposition": "apprentissage : le groupe {label} ({pct:+.0%})",
        "graph_disposition": "sentiment du groupe envers toi : {pct:+.0%} ({label})",
        "graph_title": "Vocabulaire dans le temps - part dominante par etat",
        "graph_traits_title": "Traits physiques dans le temps - moyenne population (part de la plage)",
        "graph_dismiss": "-- une touche pour revenir --",
        "legend_creature": "creature (anneau = son signal actuel)",
        "legend_food": "nourriture",
        "legend_predator": "predateur",
        "hud_mood_title": "humeur (couleur du corps) :",
        "mood_calm": "calme",
        "mood_joy": "heureux",
        "mood_sad": "triste",
        "mood_fear": "apeure",
        "hud_choice_approach": "viennent",
        "hud_choice_flee": "fuient",
        "hud_choice_ignore": "t'ignorent",
        "hud_memory_hint": "survole une creature : vert = lieux de confiance, rouge = lieux de peur",
        "extinct": "Extinction. Appuie sur R pour un nouveau monde.",

        "mind_title": "DANS SA TETE",
        "mind_expects": "ce qu'elle attend de cet instant",
        "mind_decided": "elle a decide de",
        "mind_surprise": "surprise",
        "mind_dread": "un chasseur, pour elle",
        "mind_dread_none": "les chasseurs ne lui disent rien",
        "mind_dread_runs": "elle fuit {pct:+.0f}% plus fort",
        "mind_words": "ce que les cris du groupe veulent dire pour elle",
        "mind_dwells": "ce qu'elle ressasse",
        "mind_dwells_none": "rien ne l'a encore choquee",
        "act_approach": "venir vers toi",
        "act_flee": "s'eloigner",
        "act_ignore": "t'ignorer",
        "mem_hand": "ta main",
        "mem_predator": "un predateur",
        "mem_food": "la nourriture",
        "mem_other": "un instant",

        "translator_title": "Traducteur - ce que signifie chaque couleur en ce moment",
        "translator_unused": "inutilisee / ambigue",
        "translator_homonym": "  ! homonymie - partagee avec un autre etat",
        "translator_col_word": "le mot - herite",
        "translator_col_meaning": "ce qu'il annonce - appris",
        "translator_dreaded": "redoute",
        "translator_welcomed": "bienvenu",
        "translator_noise": "encore du bruit",
        "translator_learned_hint": "quelle couleur veut dire quel etat est herite ; ce qu'elle annonce s'apprend en une vie",

        "family_title": "Arbre genealogique",
        "family_gen": "generation {gen}",
        "family_alive": "vivant - token {token}, age {age}",
        "family_dead": "mort depuis le tick {death}",
        "family_born": "ne au tick {tick}",
        "family_parents": "Parents :",
        "family_founder": "aucun - generation fondatrice",
        "family_children": "Enfants ({n}) :",
        "family_no_children": "aucun pour le moment",
        "family_descendants": "Descendants au total : {total} ({alive} encore en vie)",
        "family_hint": "HAUT=parent   BAS=enfant   GAUCHE/DROITE=freres et soeurs   T ou ESC=revenir",
        "family_none": "Aucune creature a montrer pour le moment.",

        "compare_mode_prompt": "Comparer des seeds : qu'est-ce qui doit etre reproductible ?",
        "compare_mode_language": "  L = langage - le meme mot gagne-t-il sur des parties independantes ?",
        "compare_mode_traits": "  T = traits physiques - vitesse/vision/ouie/metabolisme convergent-ils pareil ?",
        "compare_mode_traits_unavailable": "  (traits indisponibles - evolution adaptative desactivee pour ce monde)",
        "compare_mode_hint": "Appuie sur L ou T, ou ESC pour annuler.",
        "compare_depth_prompt": "Quelle profondeur ?",
        "compare_depth_quick": "  R = rapide - 4 seeds x 8 000 ticks (defaut)",
        "compare_depth_thorough": "  A = approfondi - 8 seeds x 40 000 ticks, comme la verif faite plus tot",
        "compare_depth_expert": "  E = expert - 16 seeds x 60 000 ticks, une par une - peut prendre du temps",
        "compare_depth_hint": "Appuie sur R, A ou E, ou ENTREE pour le defaut (rapide). ESC annule.",
        "compare_progress": "seed {seed}/{n_seeds}   tick {tick}/{ticks}   ESC annule",
        "compare_result_title": "Comparaison terminee ({n_seeds} seeds x {ticks} ticks)",
        "compare_traits_header": "trait          moyenne  ecart-type  min     max",
        "compare_lang_header": "etat           couleur dominante par seed",
        "compare_collision_summary": "Collisions : {clean}/{n_seeds} seeds sans collision",
        "compare_dismiss": "-- ESC pour revenir --",
        "compare_cancelled": "Annule - {n} seed(s) terminee(s) avant l'arret.",

        "help_more": "-- espace pour la suite --",
        "help_dismiss": "-- une touche pour reprendre --",
        "help_lines": [
            ("Thronglets — notice", True),
            ("", False),
            ("Chaque creature nait avec un genome qui decide quelle couleur", False),
            ("elle affiche selon son etat, et comment elle reagit aux couleurs", False),
            ("des autres. Personne ne programme le sens des couleurs : un", False),
            ("langage commun peut emerger par selection naturelle, ou pas.", False),
            ("", False),
            ("Les 5 etats, par ordre de priorite :", True),
            ("  1. alerte     un predateur repere -> fuite immediate", False),
            ("  2. nourriture de la nourriture est visible tout pres", False),
            ("  3. detresse   energie tres basse, aucune nourriture en vue", False),
            ("  4. partenaire prete a se reproduire + partenaire prete proche", False),
            ("  5. inactif    rien de special (etat le plus frequent, de loin)", False),
            ("", False),
            ("Vivre, se reproduire, mourir :", True),
            ("  L'energie baisse en permanence, manger la restaure. Emettre", False),
            ("  une couleur (hors silence) coute un peu d'energie en plus.", False),
            ("  Assez d'energie et d'age, un partenaire pareil a proximite :", False),
            ("  un enfant nait. Un predateur qui attrape une creature la tue.", False),
            ("", False),
            ("Lire le vocabulaire affiche en haut :", True),
            ("  Pour chaque etat, la part de la population qui utilise chaque", False),
            ("  couleur. Ca part du hasard (~17%) et grimpe si un mot fait", False),
            ("  consensus. '..' = silence, pas une couleur en moins.", False),
            ("", False),
            ("A savoir :", True),
            ("  Deux etats peuvent finir sur la meme couleur par hasard (ex:", False),
            ("  inactif et alerte) - rien ne l'empeche ni ne garantit que ca", False),
            ("  se resolve. Parler coute de l'energie : le silence est une", False),
            ("  vraie strategie, pas un defaut.", False),
        ],
        "faq_lines": [
            ("Thronglets — FAQ", True),
            ("", False),
            ("Q : Pourquoi les creatures restent parfois en groupe meme avec", True),
            ("    de la nourriture juste a cote ?", True),
            ("R : Suivre le signal d'un voisin et se diriger vers la", False),
            ("    nourriture sont deux forces qui peuvent s'annuler en", False),
            ("    partie - un compromis assume, pas un bug.", False),
            ("", False),
            ("Q : Est-ce que la detresse pousse les creatures a s'entraider ?", True),
            ("R : Non - il n'y a aucun mecanisme de cooperation. La detresse", False),
            ("    est traitee comme n'importe quel autre signal, et les", False),
            ("    creatures apprennent surtout a l'eviter.", False),
            ("", False),
            ("Q : Pourquoi le metabolisme adaptatif tombe toujours pres de", True),
            ("    son minimum ?", True),
            ("R : Contrairement a la vitesse/vision/ouie, un metabolisme bas", False),
            ("    n'a aucun inconvenient ici - ce n'est pas un vrai", False),
            ("    compromis, donc la selection le pousse toujours vers le", False),
            ("    bas.", False),
            ("", False),
            ("Q : Comment deux creatures de generations tres differentes", True),
            ("    peuvent-elles etre frere et soeur ?", True),
            ("R : Generation = max(generation des deux parents)+1, et le", False),
            ("    choix du partenaire ne tient compte que de la proximite,", False),
            ("    pas de la generation - un parent qui vit longtemps peut se", False),
            ("    reproduire avec un partenaire bien plus 'profond' tard", False),
            ("    dans sa vie.", False),
            ("", False),
            ("Q : Une creature peut-elle vraiment s'accoupler avec son propre", True),
            ("    descendant ?", True),
            ("R : Oui - meme raison : le choix du partenaire est purement", False),
            ("    base sur la proximite, sans aucune notion de famille.", False),
            ("", False),
            ("Q : Meme un vocabulaire entraine peut deriver ou 'revenir en", True),
            ("    arriere' - pourquoi ?", True),
            ("R : Aucune creature n'apprend quoi que ce soit pendant sa vie ;", False),
            ("    les genomes sont fixes a la naissance. Seules la mutation", False),
            ("    et la selection a travers les generations changent quelque", False),
            ("    chose, et la mutation ne s'arrete jamais - rien n'est", False),
            ("    jamais definitivement acquis.", False),
            ("", False),
            ("Q : Deux etats partagent la meme couleur (homonymie) - c'est", True),
            ("    un bug ?", True),
            ("R : Non - rien dans le modele ne l'empeche. Les genomes mutent", False),
            ("    independamment par etat, donc deux etats peuvent tomber", False),
            ("    sur le meme token par pur hasard. L'ecran Traducteur (D)", False),
            ("    permet de le reperer clairement.", False),
            ("", False),
            ("Q : Une seule partie donne un resultat surprenant - puis-je lui", True),
            ("    faire confiance ?", True),
            ("R : Pas telle quelle. Utilise l'ecran Comparer (C) pour lancer", False),
            ("    plusieurs seeds independantes et voir si le resultat se", False),
            ("    reproduit vraiment, ou si c'etait juste la derive d'une", False),
            ("    seule partie.", False),
            ("", False),
            ("Q : Quelle est la vraie difference entre le langage entraine", True),
            ("    par IA et celui qui evolue ?", True),
            ("R : L'IA (train_language.py) utilise la descente de gradient", False),
            ("    pour minimiser directement l'erreur de communication, a", False),
            ("    chaque etape. Le langage evolue ne recompense que la", False),
            ("    survie et la reproduction - bien communiquer n'est jamais", False),
            ("    optimise directement, juste utile indirectement.", False),
        ],
    },
}


# =========================================================================
# the window
#
# The game used to seize the whole display: set_mode((0, 0), FULLSCREEN). That
# is a hostile default for something you leave running for hours next to other
# windows, so it now opens MAXIMISED and resizable, and fullscreen is a key you
# press rather than a state you are put in.
#
# Two facts about pygame 2 / SDL2 make this cheap, both verified rather than
# assumed. A resizable window's display Surface is resized IN PLACE - the same
# object, so the `screen` reference held by all 23 event loops in this file
# stays valid and nothing has to be threaded back through them. And the
# _sdl2 Window can maximise and go fullscreen without re-creating the window,
# which pygame.display.toggle_fullscreen() does do (it warns, and it loses the
# maximised state on the way back). So only the scaling globals need keeping in
# step, which is what sync_screen() and events() below are for.
# =========================================================================

_window = None          # the SDL2 window, or None where _sdl2 is unavailable
_fullscreen = False
_restore_geometry = None   # size/position to come back to when leaving fullscreen


def open_window():
    """Open the game window maximised, and return its surface.

    Falls back all the way down: no _sdl2 module -> size the window to the
    desktop by hand; no desktop size either -> a fixed sensible window. A
    player on an odd build gets a slightly wrong window, not a crash."""
    global _window
    try:
        sizes = pygame.display.get_desktop_sizes()
        dw, dh = sizes[0]
    except (pygame.error, IndexError, AttributeError):
        dw, dh = 1280, 800
    # a first size for the window in case maximising is not honoured (no window
    # manager, some remote sessions): most of the desktop, but not all of it
    screen = pygame.display.set_mode((int(dw * 0.9), int(dh * 0.88)), pygame.RESIZABLE)
    try:
        from pygame._sdl2.video import Window
        _window = Window.from_display_module()
        _window.maximize()
    except (ImportError, AttributeError, pygame.error):
        _window = None
    sync_screen()
    return screen


def toggle_fullscreen():
    """Fullscreen on and off, keeping the windowed geometry across the trip.

    set_windowed() restores the size the window was FIRST opened at, not the
    maximised one, so leaving fullscreen would silently un-maximise the game.
    Remembering the geometry ourselves is what makes the round trip land where
    it started."""
    global _fullscreen, _restore_geometry
    if _window is None:
        pygame.display.toggle_fullscreen()   # coarser, but better than nothing
        _fullscreen = not _fullscreen
        sync_screen()
        return
    if not _fullscreen:
        _restore_geometry = (_window.size, _window.position)
        _window.set_fullscreen(desktop=True)
    else:
        _window.set_windowed()
        if _restore_geometry is not None:
            size, position = _restore_geometry
            # A window that filled the desktop goes back to being MAXIMISED, not
            # to a loose window that merely happens to be that size: restoring
            # the geometry by hand left it a couple of pixels off and no longer
            # maximised in the window manager's eyes, so double-clicking the
            # title bar afterwards did the wrong thing.
            if _fills_desktop(size):
                _window.maximize()
            else:
                _window.size, _window.position = size, position
    _fullscreen = not _fullscreen
    sync_screen()


def _fills_desktop(size):
    """Was this window effectively maximised? A maximised window is a little
    smaller than the desktop - the title bar and any taskbar come out of it -
    so this asks whether it was close, not whether it matched."""
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
    except (pygame.error, IndexError, AttributeError):
        return False
    return size[0] >= dw * 0.95 and size[1] >= dh * 0.90


def sync_screen():
    """Keep the scaling globals matching the window the player actually has."""
    global SCREEN_W, SCREEN_H, SCALE_X, SCALE_Y
    surface = pygame.display.get_surface()
    if surface is None:
        return
    w, h = surface.get_size()
    if (w, h) == (SCREEN_W, SCREEN_H):
        return
    SCREEN_W, SCREEN_H = w, h
    SCALE_X = SCREEN_W / WIDTH
    SCALE_Y = max(1.0, SCREEN_H - HUD_H) / HEIGHT


def events():
    """Every event loop in this file pumps through here.

    Two things must hold on every screen and not just the main one: the scaling
    globals have to follow the window, and F11 has to toggle fullscreen. Doing
    it in one place rather than in each of the 23 loops means a screen added
    later cannot forget to, and a player cannot get stuck fullscreen inside a
    menu. Alt+Enter works too, because half the world reaches for that one."""
    out = []
    for event in pygame.event.get():          # the one raw pump in this file
        if event.type == pygame.KEYDOWN and (
                event.key == pygame.K_F11
                or (event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
                    and event.mod & pygame.KMOD_ALT)):
            toggle_fullscreen()
            continue          # swallowed: Enter must not also confirm a menu
        out.append(event)
    sync_screen()             # after pumping, so this frame draws at the new size
    return out


def show_help(screen, font, lang):
    t = TEXT[lang]
    lines = t["help_lines"]
    line_h = 24
    top = 20
    page_size = max(1, (SCREEN_H - top - 50) // line_h)
    for start in range(0, len(lines), page_size):
        page = lines[start:start + page_size]
        more = start + page_size < len(lines)
        footer = t["help_more"] if more else t["help_dismiss"]
        waiting = True
        while waiting:
            screen.fill(BG)
            for i, (line, bold) in enumerate(page):
                color = TEXT_COLOR if not bold else (255, 255, 255)
                screen.blit(font.render(line, True, color), (20, top + i * line_h))
            screen.blit(font.render(footer, True, (150, 155, 145)), (20, top + len(page) * line_h + 14))
            pygame.display.flip()
            for event in events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    waiting = False


def show_faq(screen, font, lang):
    """Paginated the same way as show_help() - curated questions that came
    up while building/playing this, with honest, specific answers."""
    t = TEXT[lang]
    lines = t["faq_lines"]
    line_h = 24
    top = 20
    page_size = max(1, (SCREEN_H - top - 50) // line_h)
    for start in range(0, len(lines), page_size):
        page = lines[start:start + page_size]
        more = start + page_size < len(lines)
        footer = t["help_more"] if more else t["help_dismiss"]
        waiting = True
        while waiting:
            screen.fill(BG)
            for i, (line, bold) in enumerate(page):
                color = TEXT_COLOR if not bold else (255, 255, 255)
                screen.blit(font.render(line, True, color), (20, top + i * line_h))
            screen.blit(font.render(footer, True, (150, 155, 145)), (20, top + len(page) * line_h + 14))
            pygame.display.flip()
            for event in events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    waiting = False


def show_graph(screen, font, world, lang):
    """A dedicated full-screen view of vocab_history (and trait_history, if
    adaptive traits are on), opened like show_help() - the HUD rows stay
    compact, this is where the curves get room to breathe."""
    t = TEXT[lang]
    labels = STATE_LABELS[lang]
    trait_labels = TRAIT_LABELS[lang]
    disp_hist = getattr(world, "disposition_history", None)
    show_disp = getattr(world, "learning", False) and disp_hist is not None
    n_rows = 5 + (N_TRAITS if world.adaptive_traits else 0) + (1 if show_disp else 0)
    title_h = 40 if world.adaptive_traits else 0
    row_h = (SCREEN_H - 80 - title_h) // n_rows
    graph_w = SCREEN_W - 260
    graph_h = min(60, row_h - 30)

    waiting = True
    while waiting:
        screen.fill(BG)
        screen.blit(font.render(t["graph_title"], True, (255, 255, 255)), (20, 20))

        y = 60
        if show_disp:
            # the world records the flock's feeling in its own -1..1 units, so
            # map it onto the 0..1 the shared sparkline plots (0.5 is neutral)
            raw = disp_hist[-1] if disp_hist else 0.0
            screen.blit(font.render(
                t["graph_disposition"].format(pct=raw, label=disposition_label(raw, lang)),
                True, (150, 220, 140) if raw > 0.05 else (225, 110, 110) if raw < -0.05 else TEXT_COLOR),
                (20, y))
            draw_sparkline(screen, 220, y - 6, graph_w, graph_h,
                           [(v + 1.0) / 2.0 for v in disp_hist])
            y += row_h

        for state in (DANGER, FOOD, DISTRESS, MATE, IDLE):
            history = world.vocab_history[state]
            current = f"{history[-1] * 100:3.0f}%" if history else "  -%"
            screen.blit(font.render(f"{labels[state]}: {current}", True, TEXT_COLOR), (20, y))
            draw_sparkline(screen, 220, y - 6, graph_w, graph_h, history)
            y += row_h

        if world.adaptive_traits:
            y += 10
            screen.blit(font.render(t["graph_traits_title"], True, (255, 255, 255)), (20, y))
            y += 30
            for trait in range(N_TRAITS):
                history = world.trait_history[trait]
                current = f"{history[-1] * 100:3.0f}%" if history else "  -%"
                screen.blit(font.render(f"{trait_labels[trait]}: {current}", True, TEXT_COLOR), (20, y))
                draw_sparkline(screen, 220, y - 6, graph_w, graph_h, history)
                y += row_h

        screen.blit(font.render(t["graph_dismiss"], True, (150, 155, 145)), (20, y))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                waiting = False


def show_translator(screen, font, world, lang):
    """A frozen snapshot - what each color means right now, inverted from
    the HUD's state->color view into a color->state dictionary. Opened like
    show_graph()/show_help(); no history, just this instant."""
    t = TEXT[lang]
    labels = STATE_LABELS[lang]
    by_token = world.translator()
    # the other half of a word: what living with that call taught them it
    # foretells. The colour->state mapping above is evolved and inherited; this
    # is learned, within a lifetime, and only exists when learning is on.
    meanings = world.signal_meanings()

    waiting = True
    while waiting:
        screen.fill(BG)
        screen.blit(font.render(t["translator_title"], True, (255, 255, 255)), (20, 20))

        y = 60
        if meanings is not None:
            screen.blit(font.render(t["translator_col_word"], True, HUD_ACCENT), (46, y))
            screen.blit(font.render(t["translator_col_meaning"], True, HUD_ACCENT), (470, y))
            y += 26
        for token in range(N_TOKENS):
            claims = by_token[token]
            if token == 0:
                pygame.draw.circle(screen, (110, 110, 110), (30, y + 8), 6, width=1)
            else:
                pygame.draw.circle(screen, TOKEN_COLORS[token], (30, y + 8), 6)
            text = (" / ".join(f"{labels[state]} ({frac * 100:.0f}%)" for state, frac in claims)
                    if claims else t["translator_unused"])
            screen.blit(font.render(text, True, TEXT_COLOR), (46, y))
            if meanings is not None and token in meanings:
                m = meanings[token]
                # a bar growing left from a centre line for dread, right for
                # welcome, so a glance down the column shows which of their own
                # words the flock has come to fear
                bx, bw, mid = 470, 120, 470 + 60
                pygame.draw.rect(screen, (28, 34, 24), (bx, y + 4, bw, 8))
                span = int(min(1.0, abs(m) / 0.08) * (bw // 2))
                if span:
                    col = (120, 200, 110) if m > 0 else (220, 95, 90)
                    rect = (mid, y + 4, span, 8) if m > 0 else (mid - span, y + 4, span, 8)
                    pygame.draw.rect(screen, col, rect)
                pygame.draw.line(screen, (150, 158, 140), (mid, y + 2), (mid, y + 13))
                word = (t["translator_dreaded"] if m < -0.02 else
                        t["translator_welcomed"] if m > 0.02 else t["translator_noise"])
                col = (225, 110, 110) if m < -0.02 else \
                      (150, 220, 140) if m > 0.02 else HUD_HINT
                screen.blit(font.render(f"{m:+.3f}  {word}", True, col), (bx + bw + 12, y))
            y += 24
            if len(claims) > 1:
                screen.blit(font.render(t["translator_homonym"], True, (235, 90, 90)), (46, y))
                y += 24

        if meanings is not None:
            y += 8
            screen.blit(font.render(t["translator_learned_hint"], True, HUD_HINT), (46, y))
            y += 24
        screen.blit(font.render(t["graph_dismiss"], True, (150, 155, 145)), (20, y + 16))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                waiting = False


def _family_short_label(world, cid):
    rec = world.lineage.get(cid)
    if rec is None:
        return f"#{cid}"
    if rec["death"] is None:
        return f"#{cid} (gen {rec['gen']}, alive)"
    return f"#{cid} (gen {rec['gen']}, dead t{rec['death']})"


def show_family(screen, font, world, lang):
    """An ego-centric genealogy browser, opened like show_graph()/show_help():
    one creature in focus at a time, arrow keys walk the tree (parent above,
    first child below, siblings sideways) instead of trying to cram a whole
    population's tree onto one screen."""
    t = TEXT[lang]
    focus = world.default_family_focus()
    if focus is None:
        waiting = True
        while waiting:
            screen.fill(BG)
            screen.blit(font.render(t["family_none"], True, (255, 255, 255)), (20, 20))
            screen.blit(font.render(t["graph_dismiss"], True, (150, 155, 145)), (20, 60))
            pygame.display.flip()
            for event in events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    waiting = False
        return

    line_h = 26
    while True:
        info = world.family_info(focus)
        screen.fill(BG)
        y = 20
        screen.blit(font.render(t["family_title"], True, (255, 255, 255)), (20, y))
        y += line_h * 2

        screen.blit(font.render(f"#{info['id']}  {t['family_gen'].format(gen=info['gen'])}",
                                 True, (255, 255, 255)), (20, y))
        y += line_h
        status = (t["family_alive"].format(token=info["token"], age=info["age"]) if info["alive"]
                  else t["family_dead"].format(death=info["death"]))
        color = TOKEN_COLORS[info["token"]] if info["alive"] and info["token"] else TEXT_COLOR
        screen.blit(font.render(status, True, color), (20, y))
        y += line_h
        screen.blit(font.render(t["family_born"].format(tick=info["birth"]), True, (150, 155, 145)), (20, y))
        y += line_h * 2

        screen.blit(font.render(t["family_parents"], True, (255, 255, 255)), (20, y))
        y += line_h
        if info["parents"]:
            for pid in info["parents"]:
                screen.blit(font.render(_family_short_label(world, pid), True, TEXT_COLOR), (40, y))
                y += line_h
        else:
            screen.blit(font.render(t["family_founder"], True, (150, 155, 145)), (40, y))
            y += line_h
        y += line_h // 2

        screen.blit(font.render(t["family_children"].format(n=len(info["children"])),
                                 True, (255, 255, 255)), (20, y))
        y += line_h
        if info["children"]:
            for cid in info["children"][:8]:
                screen.blit(font.render(_family_short_label(world, cid), True, TEXT_COLOR), (40, y))
                y += line_h
            if len(info["children"]) > 8:
                screen.blit(font.render(f"... +{len(info['children']) - 8}", True, (150, 155, 145)), (40, y))
                y += line_h
        else:
            screen.blit(font.render(t["family_no_children"], True, (150, 155, 145)), (40, y))
            y += line_h
        y += line_h // 2

        descendants = t["family_descendants"].format(total=info["total_descendants"], alive=info["alive_descendants"])
        screen.blit(font.render(descendants, True, TEXT_COLOR), (20, y))
        y += line_h * 2
        screen.blit(font.render(t["family_hint"], True, (150, 155, 145)), (20, y))
        pygame.display.flip()

        event_key = None
        waiting = True
        while waiting:
            for event in events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    event_key = event.key
                    waiting = False

        if event_key in (pygame.K_ESCAPE, pygame.K_t):
            break
        elif event_key == pygame.K_UP and info["parents"]:
            focus = info["parents"][0]
        elif event_key == pygame.K_DOWN and info["children"]:
            focus = info["children"][0]
        elif event_key in (pygame.K_LEFT, pygame.K_RIGHT) and info["parents"]:
            siblings = world.family_info(info["parents"][0])["children"]
            if focus in siblings and len(siblings) > 1:
                i = siblings.index(focus)
                i = (i + (1 if event_key == pygame.K_RIGHT else -1)) % len(siblings)
                focus = siblings[i]


def init_sound():
    """Best-effort mixer setup - returns {token: Sound} and a dedicated Channel
    to play them on, or (None, None) if there's no audio device at all (a
    headless box, a sandbox, a machine with sound disabled). Never crashes
    the game over something this optional."""
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=2)
        sample_rate = pygame.mixer.get_init()[0]
        tones = {token: _make_tone(freq, sample_rate, decay=True)
                 for token, freq in enumerate(TOKEN_FREQS) if token != 0}
        return tones, pygame.mixer.Channel(0)
    except pygame.error:
        return None, None


def _make_tone(freq, sample_rate, duration=0.6, volume=0.25, decay=False):
    """A short sine-wave tone. By default it has a symmetric fade in/out
    envelope meant to be looped (the fades soften the loop seam). With
    decay=True it gets a quick attack and a long ringing fall-off to
    silence - a struck, bell-like note played once, not held."""
    n = int(sample_rate * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    wave = np.sin(2 * np.pi * freq * t)
    if decay:
        attack = max(1, n // 40)
        envelope = np.concatenate([
            np.linspace(0, 1, attack),
            np.linspace(1, 0, n - attack) ** 1.6,   # a smooth, ringing fall-off
        ])
    else:
        fade = min(n // 20, 400)
        envelope = np.ones(n)
        envelope[:fade] = np.linspace(0, 1, fade)
        envelope[-fade:] = np.linspace(1, 0, fade)
    wave = (wave * envelope * volume * 32767).astype(np.int16)
    stereo = np.column_stack([wave, wave])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def update_listening(channel, tones, world, mouse_pos, hud_h, muted, hovered_id):
    """Strikes a creature's evolved signal once when the cursor moves ONTO
    it - a single struck note, not a tone sustained for as long as you
    hover (that constant drone was too much). Resting the cursor stays
    silent; sliding onto a different creature strikes that one's note. Finds
    the living creature nearest the mouse within LISTEN_RADIUS and returns
    its id, so the caller can tell next frame when the hovered creature has
    changed (an edge, not a hold)."""
    if channel is None:
        return None
    target_id, target_token = None, 0
    if not muted and mouse_pos[1] > hud_h:
        wx, wy = mouse_pos[0] / SCALE_X, (mouse_pos[1] - hud_h) / SCALE_Y
        best_dist = LISTEN_RADIUS
        for c in world.creatures:
            if not c.alive or c.token == 0:
                continue
            dist = ((c.pos[0] - wx) ** 2 + (c.pos[1] - wy) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                target_id, target_token = c.id, c.token
    if target_id is not None and target_id != hovered_id:
        channel.play(tones[target_token])
    return target_id


def draw_memory_overlay(screen, mind):
    """Paint a creature's spatial memory over the field - green tiles over
    ground it remembers as good, red over ground it fears - its mental map of
    the world made visible. Drawn on a translucent surface so the field shows
    through."""
    cell_w = WIDTH / MEM_COLS * SCALE_X
    cell_h = HEIGHT / MEM_ROWS * SCALE_Y
    overlay = pygame.Surface((SCREEN_W, SCREEN_H - HUD_H), pygame.SRCALPHA)
    for cy in range(MEM_ROWS):
        for cx in range(MEM_COLS):
            v = float(mind.memory[cy, cx])
            if abs(v) < 0.06:
                continue
            mag = min(1.0, abs(v) / MEM_CLIP)
            col = (60, 200, 90) if v > 0 else (210, 60, 50)
            rect = (int(cx * cell_w), int(cy * cell_h), int(cell_w) + 1, int(cell_h) + 1)
            overlay.fill((*col, int(45 + 120 * mag)), rect)
    screen.blit(overlay, (0, HUD_H))


def _signed_bar(screen, x, y, w, h, value, good=(120, 210, 100), bad=(225, 85, 75)):
    """A bar that grows right from a centre line when positive and left when
    negative - for quantities that are meaningfully signed, like what a creature
    expects of a moment."""
    mid = x + w // 2
    pygame.draw.rect(screen, (30, 36, 26), (x, y, w, h))
    span = int(abs(value) * (w // 2))
    if span > 0:
        col = good if value > 0 else bad
        rect = (mid, y, span, h) if value > 0 else (mid - span, y, span, h)
        pygame.draw.rect(screen, col, rect)
    pygame.draw.line(screen, HUD_SEP, (mid, y - 1), (mid, y + h))


def _memory_label(t, feat, target):
    """Name what a remembered moment was ABOUT: the rarest thing present, not
    the loudest.

    This used to take whichever perception was strongest, which quietly blamed
    food for almost everything. Food is noticed from 60 world units and a
    predator only from 26, so food is the strongest single perception nearly
    half the time - measured across 5 seeds, 47% of living moments have
    food_prox above 0.2. The result was that 1186 of 2773 kept memories were
    labelled "food", 489 of them with a predator in sight, and the panel showed
    a player line after line of "food -0.35". Inside those memories the target
    correlated -0.52 with how close the predator was and +0.04 with how close
    the food was: the food was scenery, not the cause.

    So a memory is named for the EVENT in it. A predator perceptible at all
    outranks the hand, the hand outranks food, and food only claims a moment
    when it is strongly there and nothing else is.

    The sign matters too. A hunter can never MAKE a moment good: the only
    lesson predators hand out is teach(-prox, ...), and they give no reward at
    all. But a meal is credited to the state the creature was in, and 14.4% of
    meals are taken with a hunter within perception, so the credit lands partly
    on the predator and the panel printed "a predator, +0.28" in green - which
    reads as though the creature enjoys them. It is 3.6% of predator-labelled
    memories, up from 1.1% before eating became worth something: the leak was
    always there, the bigger reward only made it visible.

    So a good surprise never gets the predator's name. It falls through to
    whatever else was in the frame - the meal that actually drove it, or
    nothing in particular. No new wording: a moment the flock cannot credit to
    anything it can name has always been just "a moment"."""
    if feat[F_PREDATOR] >= 0.1 and target <= 0.0:
        return t["mem_predator"]
    if feat[F_HAND] >= 0.2:
        return t["mem_hand"]
    if feat[F_FOOD] >= 0.4:
        return t["mem_food"]
    return t["mem_other"]


def _mind_panel_width(font, t):
    """How wide the creature panel has to be, measured rather than guessed.

    It was a flat 300px, which was set by eye against the English wording and
    then quietly outgrown: "ce que les cris du groupe veulent dire pour elle"
    renders about 390px and ran straight off the edge, and every label added
    since made it worse. Measuring every line the panel can draw - in whichever
    language is loaded - means new wording cannot silently overflow again.
    Capped against the window, so a narrow window gets a panel that fits it."""
    pad = 10
    lines = [
        t["mind_title"], t["mind_expects"], t["mind_words"],
        f"{t['mind_surprise']}  0.000",
        f"{t['mind_dwells']} ({REPLAY_SIZE}/{REPLAY_SIZE})",
        t["mind_dwells_none"], t["mind_dread_none"],
        t["mind_dread_runs"].format(pct=100),
    ]
    # the "decided to" line takes whichever choice reads longest
    lines += [f"{t['mind_decided']} {t[k]} (100%)"
              for k in ("act_approach", "act_flee", "act_ignore")]
    widest = max(font.size(s)[0] for s in lines)
    # the dread label shares its line with a right-aligned number
    widest = max(widest, font.size(t["mind_dread"])[0] + 8 + 40)
    # a memory row is bar, then label at +66, then a right-aligned value
    widest = max(widest, 66 + 8 + 34 + max(
        font.size(t[k])[0] for k in ("mem_hand", "mem_predator", "mem_food", "mem_other")))
    return min(max(300, widest + 2 * pad), max(320, SCREEN_W - 40))


def draw_mind_panel(screen, font, mind, t):
    """What the hovered creature predicts, what it has decided, and which
    moments it cannot let go of - the learned inner life, which until now ran
    entirely unseen. Drawn bottom-left over the field, out of the HUD's way."""
    pad = 10
    w = _mind_panel_width(font, t)
    rows = max(1, len(mind.replay))
    h = 216 + rows * 15
    x = 10
    # never let it climb over the HUD on a short window, even if that means
    # the bottom is clipped - the top of this panel is the part that names it
    y = max(HUD_H + 4, SCREEN_H - h - 10)
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    panel.fill((16, 20, 14, 232))
    screen.blit(panel, (x, y))
    pygame.draw.rect(screen, HUD_SEP, (x, y, w, h), width=1)

    now = mind.situation()
    cy = y + pad
    screen.blit(font.render(t["mind_title"], True, HUD_ACCENT), (x + pad, cy)); cy += 20

    # what it expects of right now (its own learned estimate)
    screen.blit(font.render(t["mind_expects"], True, HUD_HINT), (x + pad, cy)); cy += 16
    v = mind.value(now)
    _signed_bar(screen, x + pad, cy, w - 2 * pad, 8, v)
    screen.blit(font.render(f"{v:+.2f}", True, HUD_HINT), (x + w - pad - 34, cy - 1)); cy += 20

    # what it has decided to do about you, and how sure it is
    pi = mind.policy(now)
    choice = (t["act_approach"] if mind.act == ACT_APPROACH else
              t["act_flee"] if mind.act == ACT_FLEE else t["act_ignore"])
    line = f"{t['mind_decided']} {choice} ({pi[mind.act] * 100:.0f}%)"
    col = (120, 210, 100) if mind.act == ACT_APPROACH else \
          (225, 85, 75) if mind.act == ACT_FLEE else HUD_HINT
    screen.blit(font.render(line, True, col), (x + pad, cy)); cy += 18

    # how badly its last expectation was violated
    screen.blit(font.render(f"{t['mind_surprise']}  {mind.surprise:.3f}", True, HUD_HINT),
                (x + pad, cy)); cy += 18

    # The one piece of learning that reaches its body. Everything else on this
    # panel is what the creature feels; this is what it does about it. Read the
    # constants off the module rather than the import, so a value pinned in the
    # tuning screen shows up here instead of the built-in one.
    dread = mind.dread
    screen.blit(font.render(t["mind_dread"], True, HUD_HINT), (x + pad, cy))
    if dread <= 0.0:
        cy += 18
        screen.blit(font.render(t["mind_dread_none"], True, HUD_SEP), (x + pad, cy)); cy += 32
    else:
        full = max(1e-9, simulation.KNOWLEDGE_FLEE_FULL)
        grasp = min(1.0, dread / full)
        bonus = simulation.KNOWLEDGE_FLEE_GAIN * grasp
        screen.blit(font.render(f"{dread:.3f}", True, HUD_HINT), (x + w - pad - 40, cy))
        cy += 18
        pygame.draw.rect(screen, HUD_SEP, (x + pad, cy, w - 2 * pad, 8), width=1)
        pygame.draw.rect(screen, (225, 85, 75),
                         (x + pad + 1, cy + 1, int((w - 2 * pad - 2) * grasp), 6))
        cy += 14
        screen.blit(font.render(t["mind_dread_runs"].format(pct=bonus * 100), True,
                                (225, 85, 75)), (x + pad, cy)); cy += 18

    # what the flock's own calls have come to mean to it: the colour swatch is
    # the evolved, inherited word; the bar beside it is the meaning this one
    # creature learned for it, from whatever actually followed that call
    screen.blit(font.render(t["mind_words"], True, HUD_HINT), (x + pad, cy)); cy += 16
    sx = x + pad
    for tok in range(1, N_TOKENS):
        meaning = mind.signal_meaning(tok)
        pygame.draw.circle(screen, TOKEN_COLORS[tok], (sx + 5, cy + 5), 4)
        span = int(min(1.0, abs(meaning) / 0.08) * 14)
        if span:
            col = (120, 210, 100) if meaning > 0 else (225, 85, 75)
            pygame.draw.rect(screen, col, (sx + 12, cy + 8 - span // 2, 5, max(2, span)))
        sx += 26
    cy += 22

    pygame.draw.line(screen, HUD_SEP, (x + pad, cy - 5), (x + w - pad, cy - 5))
    screen.blit(font.render(f"{t['mind_dwells']} ({len(mind.replay)}/{REPLAY_SIZE})",
                            True, HUD_ACCENT), (x + pad, cy)); cy += 18

    if not mind.replay:
        screen.blit(font.render(t["mind_dwells_none"], True, HUD_HINT), (x + pad, cy))
        return
    # worst first - the order the creature itself prioritises them by
    for shock, feat, target in sorted(mind.replay, key=lambda m: -m[0]):
        bar = int(min(1.0, shock / 0.6) * 60)
        col = (120, 210, 100) if target > 0 else (225, 85, 75)
        pygame.draw.rect(screen, col, (x + pad, cy + 4, max(1, bar), 6))
        screen.blit(font.render(_memory_label(t, feat, target), True, HUD_HINT), (x + pad + 66, cy))
        screen.blit(font.render(f"{target:+.2f}", True, col), (x + w - pad - 34, cy))
        cy += 15


def draw(screen, font, world, paused, speed, mode, lang, expanded, trained=False, muted=False,
         hovered_id=None):
    screen.fill(BG)
    pygame.draw.rect(screen, GROUND, (0, HUD_H, SCREEN_W, SCREEN_H - HUD_H))

    # the hovered creature's mental map, laid on the field (learning only)
    hov = None
    if world.learning and hovered_id is not None:
        hov = next((c for c in world.creatures
                    if c.id == hovered_id and c.alive and c.mind is not None), None)
        if hov is not None:
            draw_memory_overlay(screen, hov.mind)

    for fx, fy in world.food:
        pygame.draw.circle(screen, FOOD_COLOR, (int(fx * SCALE_X), int(fy * SCALE_Y) + HUD_H), 3)

    for c in world.creatures:
        if not c.alive:
            continue
        x, y = int(c.pos[0] * SCALE_X), int(c.pos[1] * SCALE_Y) + HUD_H
        # when learning is on, the fill colour is the creature's inner emotion,
        # so a mood spreading through the flock is visible as a wave of colour
        body = MOOD_FILL[c.mind.emotion()] if (world.learning and c.mind is not None) else BODY_COLOR
        broken = world.learning and c.mind is not None and c.mind.obedience > 0.15
        if broken:
            # a broken creature is voided out: its heart drains to black, deeper
            # the more broken it is, under a black "collar" ring
            k = c.mind.obedience
            body = tuple(int(body[j] * (1 - k)) for j in range(3))
        pygame.draw.circle(screen, body, (x, y), 4)
        if broken:
            pygame.draw.circle(screen, (0, 0, 0), (x, y), 7, width=2)
        if c.id == hovered_id:
            pygame.draw.circle(screen, (245, 245, 210), (x, y), 9, width=1)
        if c.token != 0:
            pygame.draw.circle(screen, TOKEN_COLORS[c.token], (x, y), 7, width=2)

    for p in world.predators:
        x, y = int(p.pos[0] * SCALE_X), int(p.pos[1] * SCALE_Y) + HUD_H
        pygame.draw.circle(screen, PREDATOR_COLOR, (x, y), 6)

    # what that one creature predicts, decided and cannot stop going over
    if hov is not None:
        draw_mind_panel(screen, font, hov.mind, TEXT[lang])

    draw_hud(screen, font, world, paused, speed, mode, lang, expanded, trained, muted)


SPARK_COLOR = (150, 200, 130)
SPARK_BG = (26, 32, 20)


def _downsample(values, max_points):
    """Bucket-average down to at most max_points - plotting one line segment
    per raw sample looks like a smooth curve for a short history, but once a
    run has thousands of samples squeezed into a few hundred pixels, the
    unavoidably tiny gaps between adjacent (noisy) points render as a dense
    picket-fence of near-vertical spikes instead of a readable trend."""
    if len(values) <= max_points:
        return values
    bucket = len(values) / max_points
    return [
        sum(values[lo:hi]) / (hi - lo)
        for lo, hi in (
            (int(i * bucket), max(int(i * bucket) + 1, int((i + 1) * bucket)))
            for i in range(max_points)
        )
    ]


def draw_sparkline(screen, x, y, w, h, history):
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, SPARK_BG, rect)
    if len(history) < 2:
        return
    values = _downsample(list(history), max(2, int(w)))
    step = w / (len(values) - 1)
    points = [
        (x + i * step, y + h - 1 - v * (h - 2))
        for i, v in enumerate(values)
    ]
    pygame.draw.lines(screen, SPARK_COLOR, False, points, width=2)


def draw_vocab_row(screen, font, y, label, pairs, other_label):
    x = 10
    lbl = font.render(f"{label}:", True, TEXT_COLOR)
    screen.blit(lbl, (x, y))
    x += lbl.get_width() + 10
    top, other = top3_and_other(pairs)
    for token, frac in top:
        if token == 0:
            pygame.draw.circle(screen, (110, 110, 110), (x + 6, y + 8), 6, width=1)
        else:
            pygame.draw.circle(screen, TOKEN_COLORS[token], (x + 6, y + 8), 6)
        txt = font.render(f"{frac * 100:3.0f}%", True, TEXT_COLOR)
        screen.blit(txt, (x + 16, y))
        x += 16 + txt.get_width() + 14
    if other > 0:
        pygame.draw.circle(screen, (110, 110, 110), (x + 6, y + 8), 6)
        txt = font.render(f"{other * 100:3.0f}% {other_label}", True, TEXT_COLOR)
        screen.blit(txt, (x + 16, y))
        x += 16 + txt.get_width() + 14


def draw_vocab_summary_line(screen, font, y, world, labels):
    """The one-line version shown in the collapsed HUD - just each state's
    single strongest token, no breakdown of the runners-up."""
    x = 10
    vocab = world.vocabulary()
    for state in (DANGER, FOOD, DISTRESS, MATE, IDLE):
        token, frac = vocab[state]
        lbl = font.render(f"{labels[state]}:", True, TEXT_COLOR)
        screen.blit(lbl, (x, y))
        x += lbl.get_width() + 6
        if token == 0:
            pygame.draw.circle(screen, (110, 110, 110), (x + 6, y + 8), 6, width=1)
        else:
            pygame.draw.circle(screen, TOKEN_COLORS[token], (x + 6, y + 8), 6)
        txt = font.render(f"{frac * 100:3.0f}%", True, TEXT_COLOR)
        screen.blit(txt, (x + 16, y))
        x += 16 + txt.get_width() + 16


def _disposition_gauge(screen, font, x, y, disp, t, lang):
    """A small bar that reads at a glance: fills right/green as the flock comes
    to trust you, left/red as it comes to fear you, centred on neutral."""
    w, h = 150, 9
    cx = x + w // 2
    pygame.draw.rect(screen, (28, 34, 24), (x, y + 3, w, h))
    fill = int(min(1.0, abs(disp)) * (w // 2))
    if disp >= 0:
        pygame.draw.rect(screen, (120, 200, 110), (cx, y + 3, fill, h))
    else:
        pygame.draw.rect(screen, (220, 95, 90), (cx - fill, y + 3, fill, h))
    pygame.draw.rect(screen, (70, 78, 62), (x, y + 3, w, h), width=1)
    pygame.draw.line(screen, (150, 158, 140), (cx, y + 1), (cx, y + h + 5))
    line = t["hud_disposition"].format(label=disposition_label(disp, lang), pct=disp)
    color = (150, 220, 140) if disp > 0.05 else (225, 110, 110) if disp < -0.05 else (200, 200, 190)
    screen.blit(font.render(line, True, color), (x + w + 12, y))
    return y + 22


# what a creature has decided to do about you, in the order the bar stacks them
CHOICE_COLORS = {ACT_APPROACH: (120, 200, 110), ACT_FLEE: (220, 95, 90),
                 ACT_IGNORE: (120, 126, 112)}


def _choice_bar(screen, font, x, y, choices, t):
    """Who is coming, who is running and who could not care less, right now.

    The average above cannot show this: a flock split between coming to you and
    fleeing you averages to the same number as one that is uniformly
    indifferent. This is a single stacked bar, so a divided flock reads as two
    strong blocks and an indifferent one as a wall of grey."""
    w, h = 150, 9
    pygame.draw.rect(screen, (28, 34, 24), (x, y + 3, w, h))
    left = x
    for act in (ACT_APPROACH, ACT_FLEE, ACT_IGNORE):
        span = int(round(choices.get(act, 0.0) * w))
        if span > 0:
            pygame.draw.rect(screen, CHOICE_COLORS[act], (left, y + 3, span, h))
        left += span
    pygame.draw.rect(screen, (70, 78, 62), (x, y + 3, w, h), width=1)
    parts = [(t["hud_choice_approach"], ACT_APPROACH), (t["hud_choice_flee"], ACT_FLEE),
             (t["hud_choice_ignore"], ACT_IGNORE)]
    tx = x + w + 12
    for i, (word, act) in enumerate(parts):
        label = f"{choices.get(act, 0.0) * 100:.0f}% {word}"
        if i < len(parts) - 1:
            label += "   "
        surf = font.render(label, True, CHOICE_COLORS[act])
        screen.blit(surf, (tx, y))
        tx += surf.get_width()
    return y + 22


def _obedience_gauge(screen, font, x, y, ob, unrest, t):
    """The Master Mode readout, replacing the (now irrelevant) trust gauge: a
    grey bar for how broken the flock is, overlaid with a red sliver for how
    much of the free flock is in open unrest (which erodes your grip)."""
    w, h = 150, 9
    pygame.draw.rect(screen, (28, 30, 34), (x, y + 3, w, h))
    pygame.draw.rect(screen, OBEDIENT_COLOR, (x, y + 3, int(min(1.0, ob) * w), h))
    pygame.draw.rect(screen, (210, 70, 60), (x, y + 3, int(min(1.0, unrest) * w), 3))  # unrest overlay
    pygame.draw.rect(screen, (70, 72, 78), (x, y + 3, w, h), width=1)
    screen.blit(font.render(t["master_readout"].format(ob=ob, unrest=unrest), True, (235, 150, 90)),
                (x + w + 12, y))
    return y + 22


def _mood_legend(screen, font, x, y, t):
    """Explain the creature fill colours (and, on the next line, the memory
    overlay colours) - only shown when learning is on, since that's when they
    appear."""
    title = font.render(t["hud_mood_title"], True, HUD_ACCENT)
    screen.blit(title, (x, y))
    lx = x + title.get_width() + 14
    for label, emo in ((t["mood_calm"], "neutral"), (t["mood_joy"], "joy"),
                       (t["mood_sad"], "sad"), (t["mood_fear"], "fear")):
        pygame.draw.circle(screen, MOOD_FILL[emo], (lx + 6, y + 8), 5)
        lab = font.render(label, True, TEXT_COLOR)
        screen.blit(lab, (lx + 16, y))
        lx += 16 + lab.get_width() + 18
    y += 20
    screen.blit(font.render(t["hud_memory_hint"], True, HUD_HINT), (x, y))
    return y + 20


def draw_hud(screen, font, world, paused, speed, mode, lang, expanded, trained=False, muted=False):
    t = TEXT[lang]
    labels = STATE_LABELS[lang]
    pygame.draw.rect(screen, HUD_BG, (0, 0, SCREEN_W, HUD_H))
    pop = world.population()
    status = t["hud_paused"] if paused else f"x{speed}"
    header = t["hud_header"].format(tick=world.tick, pop=pop, births=world.births,
                                     deaths=world.deaths, status=status)
    screen.blit(font.render(header, True, TEXT_COLOR), (10, 8))

    # run-state tags right-aligned on the header row, out of the way
    tag_parts = [t["hud_trained_tag"]] if trained else []
    if world.adaptive_traits:
        tag_parts.append(t["hud_traits_tag"])
    if muted:
        tag_parts.append(t["hud_muted_tag"])
    if tag_parts:
        tag = font.render("   ".join(tag_parts), True, HUD_HINT)
        screen.blit(tag, (SCREEN_W - tag.get_width() - 12, 8))

    pygame.draw.line(screen, HUD_SEP, (10, 29), (SCREEN_W - 10, 29))
    y = 35

    # Master Mode is governed by obedience, not affection - so show obedience
    # there and drop the (now vestigial) trust gauge. Otherwise: how the flock
    # has come to feel about you.
    if getattr(world, "master_mode", False):
        ob = world.obedience_summary() or 0.0
        unrest = world.master_unrest() or 0.0
        y = _obedience_gauge(screen, font, 10, y, ob, unrest, t)
    else:
        disp = world.disposition_summary()
        if disp is not None:
            y = _disposition_gauge(screen, font, 10, y, disp, t, lang)
            if expanded:
                choices = world.choice_summary()
                if choices is not None:
                    y = _choice_bar(screen, font, 10, y, choices, t)

    if not expanded:
        if pop == 0:
            screen.blit(font.render(t["extinct"], True, (235, 90, 90)), (10, y))
        else:
            screen.blit(font.render(t["hud_expand_hint"], True, HUD_HINT), (10, y))
            draw_vocab_summary_line(screen, font, y + 20, world, labels)
        return

    for hint in ("hud_controls_hint1", "hud_controls_hint2", "hud_controls_hint3"):
        screen.blit(font.render(t[hint], True, HUD_HINT), (10, y)); y += 20

    settings = t["hud_manual"] if mode == "manual" else t["hud_auto"].format(count=len(world.predators))
    screen.blit(font.render(settings, True, TEXT_COLOR), (10, y)); y += 24

    pygame.draw.line(screen, HUD_SEP, (10, y - 4), (SCREEN_W - 10, y - 4))
    screen.blit(font.render(t["hud_vocab_title"], True, HUD_ACCENT), (10, y)); y += 22
    breakdown = world.vocabulary_breakdown()
    for state in (DANGER, FOOD, DISTRESS, MATE, IDLE):
        draw_vocab_row(screen, font, y, labels[state], breakdown[state], t["vocab_other"])
        y += 22

    # the mood/memory colour key, only meaningful while learning is on
    if getattr(world, "learning", False):
        pygame.draw.line(screen, HUD_SEP, (10, y - 2), (SCREEN_W - 10, y - 2))
        y += 4
        y = _mood_legend(screen, font, 10, y, t)

    pygame.draw.line(screen, HUD_SEP, (10, y - 2), (SCREEN_W - 10, y - 2))
    y += 4
    lx = 10
    for color, radius, ring, key in (
            (BODY_COLOR, 4, True, "legend_creature"),
            (FOOD_COLOR, 3, False, "legend_food"),
            (PREDATOR_COLOR, 6, False, "legend_predator")):
        pygame.draw.circle(screen, color, (lx + 6, y + 8), radius)
        if ring:
            pygame.draw.circle(screen, (150, 150, 150), (lx + 6, y + 8), 7, width=2)
        txt = font.render(t[key], True, TEXT_COLOR)
        screen.blit(txt, (lx + 18, y))
        lx += 18 + txt.get_width() + 20

    if pop == 0:
        screen.blit(font.render(t["extinct"], True, (235, 90, 90)), (10, y + 22))


def _new_world(mode, predator_count, init_pop=DEFAULT_INIT_POP, seed_genome=None,
               adaptive_traits=False, learning=False):
    # learning is a start-screen choice (default off = pure natural selection,
    # the original spirit); the headless compare_seeds runs are unaffected.
    if mode == "manual":
        return World(init_pop=init_pop, manual_food=True, manual_predators=True,
                      seed_genome=seed_genome, adaptive_traits=adaptive_traits, learning=learning)
    return World(init_pop=init_pop, predator_count=predator_count,
                 seed_genome=seed_genome, adaptive_traits=adaptive_traits, learning=learning)


def choose_language(screen, font):
    lines = [
        "Thronglets",
        "",
        "Choose your language / Choisis ta langue :",
        "  E = English",
        "  F = Francais (defaut)",
        "",
        "Press E or F to continue, or ENTER for the default (Francais).",
    ]
    while True:
        screen.fill(BG)
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e:
                    return "en"
                if event.key == pygame.K_f or event.key == pygame.K_RETURN:
                    return "fr"


def choose_mode(screen, font, lang):
    t = TEXT[lang]
    lines = [
        "Thronglets",
        "",
        t["choose_mode_prompt"],
        t["choose_mode_auto"],
        t["choose_mode_manual"],
        "",
        t["choose_mode_hint"],
    ]
    while True:
        screen.fill(BG)
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_a or event.key == pygame.K_RETURN:
                    return "auto"
                if event.key == pygame.K_m:
                    return "manual"


def choose_population(screen, font, lang):
    t = TEXT[lang]
    text = ""
    while True:
        screen.fill(BG)
        lines = [
            "Thronglets",
            "",
            t["choose_pop_prompt"].format(max=MAX_POPULATION, default=DEFAULT_INIT_POP),
            "",
            f"> {text}",
            "",
            t["choose_pop_hint"],
        ]
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if not text:
                        return DEFAULT_INIT_POP
                    return max(1, min(MAX_POPULATION, int(text)))
                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                elif event.unicode.isdigit() and len(text) < 3:
                    text += event.unicode


def choose_adaptive_traits(screen, font, lang):
    t = TEXT[lang]
    lines = [
        "Thronglets",
        "",
        t["choose_traits_prompt"],
        t["choose_traits_explain1"],
        t["choose_traits_explain2"],
        "",
        t["choose_traits_yes"],
        t["choose_traits_no"],
        "",
        t["choose_traits_hint"],
    ]
    yes_key = pygame.K_o if lang == "fr" else pygame.K_y
    while True:
        screen.fill(BG)
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == yes_key or event.key == pygame.K_RETURN:
                    return True
                if event.key == pygame.K_n:
                    return False


def choose_learning(screen, font, lang):
    """Whether the flock learns to trust/fear the player (the opt-in Mind
    system in simulation.py). Default (ENTER) is OFF, so a bare run stays pure natural
    selection - the game's original spirit - and the learned mind is an
    opt-in choice, not the imposed default."""
    t = TEXT[lang]
    lines = [
        "Thronglets",
        "",
        t["choose_learning_prompt"],
        t["choose_learning_explain1"],
        t["choose_learning_explain2"],
        "",
        t["choose_learning_yes"],
        t["choose_learning_no"],
        "",
        t["choose_learning_hint"],
    ]
    yes_key = pygame.K_o if lang == "fr" else pygame.K_y
    while True:
        screen.fill(BG)
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == yes_key:
                    return True
                if event.key == pygame.K_n or event.key == pygame.K_RETURN:
                    return False


def choose_ai(screen, font, lang):
    t = TEXT[lang]
    lines = [
        "Thronglets",
        "",
        t["choose_ai_prompt"],
        t["choose_ai_subtitle"].format(file=DEFAULT_LANGUAGE_FILE),
        "",
        t["choose_ai_yes"],
        t["choose_ai_train"],
        t["choose_ai_no"],
        "",
        t["choose_ai_hint"],
    ]
    yes_key = pygame.K_o if lang == "fr" else pygame.K_y
    while True:
        screen.fill(BG)
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == yes_key:
                    return "yes"
                if event.key == pygame.K_t:
                    return "train"
                if event.key == pygame.K_n or event.key == pygame.K_RETURN:
                    return "no"


def choose_resume(screen, font, lang):
    t = TEXT[lang]
    lines = [
        "Thronglets",
        "",
        t["choose_resume_prompt"],
        t["choose_resume_subtitle"].format(file=DEFAULT_SAVE_FILE),
        "",
        t["choose_resume_yes"],
        t["choose_resume_no"],
        "",
        t["choose_resume_hint"],
    ]
    yes_key = pygame.K_o if lang == "fr" else pygame.K_y
    while True:
        screen.fill(BG)
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == yes_key:
                    return True
                if event.key == pygame.K_n:
                    return False


def choose_start(screen, font, lang, has_save):
    """The opening screen: resume a save (if one exists), start a new game, or
    enter Master Mode. Returns 'resume', 'new', or 'master'."""
    t = TEXT[lang]
    lines = ["Thronglets", "", t["choose_start_prompt"], ""]
    if has_save:
        lines.append(t["choose_start_resume"])
    lines += [t["choose_start_new"], t["choose_start_master"], t["choose_start_tuning"],
              t["choose_start_measure"]]
    pinned = len(tuning.load())
    if pinned:
        lines.append(t["choose_start_pinned"].format(n=pinned))
    lines += ["", t["choose_start_hint"]]
    while True:
        screen.fill(BG)
        for i, line in enumerate(lines):
            col = (235, 150, 90) if line is t.get("choose_start_master") else TEXT_COLOR
            screen.blit(font.render(line, True, col), (20, 20 + i * 26))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    return "tuning"
                if event.key == pygame.K_t:
                    return "measure"
                if event.key == pygame.K_m:
                    return "master"
                if event.key == pygame.K_r and has_save:
                    return "resume"
                if event.key in (pygame.K_n, pygame.K_RETURN):
                    return "new"


# The report's scenario titles are English because the FILE is English - it is
# meant to be sent to someone. Only the on-screen name is translated, keyed by
# the English title so the two can never fall out of step: a title that gains
# no translation shows its English name rather than vanishing.
SCENARIO_FR = {
    "hunted, you never touch it": "avec predateurs, tu n'y touches jamais",
    "unhunted, you never touch it": "sans predateurs, tu n'y touches jamais",
    "hunted, hand wanders (no acts)": "avec predateurs, la main se promene (sans agir)",
    "hunted, hand feeds": "avec predateurs, la main nourrit",
    "hunted, hand burns": "avec predateurs, la main brule",
    "hunted, learning OFF (control)": "avec predateurs, apprentissage COUPE (temoin)",
    "MASTER MODE, breaking wills": "MODE MAITRE, briser les volontes",
}


def scenario_name(title, lang):
    return SCENARIO_FR.get(title, title) if lang == "fr" else title


def _hms(seconds):
    """A duration a person can act on. Hours matter more than seconds once a
    run is long enough to be a decision rather than a wait."""
    seconds = int(max(0, seconds))
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    if h:
        return f"{h}h{m:02d}"
    if m:
        return f"{m}m{s:02d}"
    return f"{s}s"


class _Speedometer:
    """How fast worlds actually run ON THIS MACHINE, measured while the player
    is still choosing what to run.

    The alternative was quoting a number from the machine this was written on,
    which is worthless: the estimate is the whole point of the screen, because
    the arithmetic is brutal and invisible. 7 tests x 16 seeds x 200000 ticks
    is 22.4 million ticks, which reads like nothing and is days.

    It times a real world built the way report.py builds them - same init_pop,
    learning on, predators in - rather than a synthetic loop, so the number is
    of the thing being estimated. Only a short warm-up is discarded, enough to
    get past cold caches; a report world starts at 60 and settles near 70, so
    it is at working size almost immediately and there is no cheap early
    stretch to flatter the estimate.

    It is an approximation across scenarios all the same: the learning-off
    control runs much faster than the rest, and an unhunted world has no
    predators to move. The screen says "estimated" and means it."""

    WARMUP = 40

    def __init__(self):
        self.rate = None
        self.timed = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        world = World(init_pop=60, seed=7, learning=True)
        n, t0 = 0, None
        while not self._stop.is_set():
            world.step()
            n += 1
            if n == self.WARMUP:
                t0 = time.time()
            elif n > self.WARMUP and n % 20 == 0:
                self.timed = n - self.WARMUP
                self.rate = self.timed / max(1e-6, time.time() - t0)

    def stop(self):
        self._stop.set()


def show_measure(screen, font, lang):
    """Run report.py's sweep from inside the game, choosing what to run.

    The same code as the command line - report.build_report - so the two cannot
    drift apart. What this screen adds is the part the command line cannot: it
    tells you what a run will COST before you start it, having just measured
    this machine, and it lets you cut the run down to the question you actually
    have instead of paying for all seven tests."""
    t = TEXT[lang]
    titles = [title for title, _kw in report.SCENARIOS]
    chosen = {title: True for title in titles}
    seeds, ticks = 3, 1500

    rows = ([("head", t["meas_scenarios"])]
            + [("test", title) for title in titles]
            + [("head", t["meas_size"]), ("seeds", None), ("ticks", None)])
    cursor = 1
    speedo = _Speedometer()
    # ONE clock. A Clock built inside the loop has no previous frame to measure
    # against, so tick() returns instantly and limits nothing - the draw loop
    # would spin flat out and starve the thread doing the actual work.
    clock = pygame.time.Clock()

    # run state, written by the worker thread and only read by the drawing loop
    state = {"done": 0, "total": 0, "title": "", "seed": 0,
             "text": None, "error": None, "started": None}
    stop = threading.Event()
    worker = None
    status = ""

    def move(delta):
        nonlocal cursor
        i = cursor
        while 0 <= i + delta < len(rows):
            i += delta
            if rows[i][0] != "head":
                cursor = i
                return

    def nudge(direction, coarse):
        nonlocal seeds, ticks
        kind = rows[cursor][0]
        if kind == "seeds":
            seeds = max(1, min(64, seeds + direction * (10 if coarse else 1)))
        elif kind == "ticks":
            ticks = max(100, min(500000, ticks + direction * (10000 if coarse else 500)))
        elif kind == "test":
            chosen[rows[cursor][1]] = direction > 0

    def launch():
        nonlocal worker, status
        picked = [x for x in titles if chosen[x]]
        if not picked:
            status = t["meas_none"]
            return
        speedo.stop()
        stop.clear()
        state.update(done=0, total=len(picked) * seeds, text=None, error=None,
                     started=time.time(), title="", seed=0)

        def progress(done, total, title, seed):
            state.update(done=done, total=total, title=title, seed=seed)

        def run():
            try:
                state["text"] = report.build_report(
                    seeds, ticks, titles=picked,
                    progress=progress, should_stop=stop.is_set)
            except Exception as exc:              # a failed run must not take
                state["error"] = f"{type(exc).__name__}: {exc}"   # the game down
        worker = threading.Thread(target=run, daemon=True)
        worker.start()

    while True:
        running = worker is not None and worker.is_alive()
        screen.fill(BG)
        screen.blit(font.render(t["meas_title"], True, (255, 255, 255)), (20, 16))

        if running or state["text"] is not None or state["error"] is not None:
            _draw_measure_run(screen, font, t, lang, state, running, stop.is_set())
        else:
            screen.blit(font.render(t["meas_hint"], True, HUD_HINT), (20, 38))
            screen.blit(font.render(t["meas_hint2"], True, HUD_HINT), (20, 56))
            y = 88
            for i, (kind, item) in enumerate(rows):
                here = (i == cursor)
                if kind == "head":
                    screen.blit(font.render(item, True, HUD_ACCENT), (20, y))
                    y += 22
                    continue
                if here:
                    pygame.draw.rect(screen, (32, 40, 28), (16, y - 2, SCREEN_W - 32, 18))
                if kind == "test":
                    on = chosen[item]
                    mark = "[x]" if on else "[ ]"
                    col = TEXT_COLOR if on else (96, 102, 92)
                    screen.blit(font.render(("> " if here else "  ") + mark + " "
                                            + scenario_name(item, lang),
                                            True, col), (20, y))
                else:
                    label = t["meas_seeds"] if kind == "seeds" else t["meas_ticks"]
                    value = seeds if kind == "seeds" else ticks
                    doc = t["meas_seeds_doc"] if kind == "seeds" else t["meas_ticks_doc"]
                    screen.blit(font.render(("> " if here else "  ") + label,
                                            True, TEXT_COLOR), (20, y))
                    screen.blit(font.render(f"{value}", True, (255, 210, 120)), (240, y))
                    screen.blit(font.render(doc, True, HUD_HINT), (320, y))
                y += 20

            n_tests = sum(1 for x in titles if chosen[x])
            total_ticks = n_tests * seeds * ticks
            y += 14
            screen.blit(font.render(t["meas_budget"], True, HUD_ACCENT), (20, y)); y += 22
            screen.blit(font.render(t["meas_total"].format(
                tests=n_tests, seeds=seeds, ticks=f"{ticks:,}".replace(",", " "),
                total=f"{total_ticks:,}".replace(",", " ")), True, TEXT_COLOR), (20, y))
            y += 20
            if speedo.rate is None:
                screen.blit(font.render(t["meas_rate_measuring"].format(n=speedo.timed),
                                        True, HUD_HINT), (20, y)); y += 20
            else:
                screen.blit(font.render(t["meas_rate"].format(rate=speedo.rate),
                                        True, HUD_HINT), (20, y)); y += 20
                eta = total_ticks / speedo.rate
                long_run = eta > 3600
                key = "meas_eta_warn" if long_run else "meas_eta"
                screen.blit(font.render(key and t[key].format(eta=_hms(eta)), True,
                                        (235, 150, 90) if long_run else (150, 220, 140)),
                            (20, y))
                y += 20
            pinned = len(tuning.load())
            y += 6
            screen.blit(font.render(t["meas_pinned"].format(n=pinned) if pinned
                                    else t["meas_builtin"], True, HUD_HINT), (20, y))
            if status:
                screen.blit(font.render(status, True, (235, 150, 90)), (20, SCREEN_H - 30))

        pygame.display.flip()

        for event in events():
            if event.type == pygame.QUIT:
                speedo.stop(); stop.set()
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                coarse = bool(event.mod & pygame.KMOD_SHIFT)
                if event.key == pygame.K_ESCAPE:
                    if running:
                        stop.set()          # let it notice between worlds
                        continue
                    speedo.stop()
                    return
                if running:
                    continue
                if state["text"] is not None or state["error"] is not None:
                    # a finished run: any key clears the result and comes back
                    state.update(text=None, error=None)
                    speedo = _Speedometer()
                    continue
                if event.key == pygame.K_UP:
                    move(-1)
                elif event.key == pygame.K_DOWN:
                    move(1)
                elif event.key == pygame.K_LEFT:
                    nudge(-1, coarse)
                elif event.key == pygame.K_RIGHT:
                    nudge(+1, coarse)
                elif event.key == pygame.K_SPACE and rows[cursor][0] == "test":
                    chosen[rows[cursor][1]] = not chosen[rows[cursor][1]]
                elif event.key == pygame.K_a:
                    for x in titles:
                        chosen[x] = True
                elif event.key == pygame.K_z:
                    for x in titles:
                        chosen[x] = False
                elif event.key == pygame.K_RETURN:
                    launch()

        # a run holds the GIL hard; drawing at 10fps leaves it room to work
        clock.tick(10 if running else 30)


def _draw_measure_run(screen, font, t, lang, state, running, cancelling):
    """The progress face of the Measure screen: what it is doing now, how long
    it has taken, and how long is left - estimated from THIS run's own pace
    rather than the speedometer, which stopped when the run started."""
    y = 48
    if running:
        screen.blit(font.render(t["meas_running"].format(
            done=state["done"], total=state["total"],
            title=scenario_name(state["title"], lang),
            seed=state["seed"]), True, TEXT_COLOR), (20, y))
        y += 26
        done, total = state["done"], max(1, state["total"])
        bar_w = min(SCREEN_W - 40, 700)
        pygame.draw.rect(screen, HUD_SEP, (20, y, bar_w, 14), width=1)
        pygame.draw.rect(screen, (120, 210, 100),
                         (21, y + 1, int((bar_w - 2) * done / total), 12))
        y += 26
        elapsed = time.time() - state["started"]
        # the first world has no pace to extrapolate from yet
        left = elapsed / done * (total - done) if done else None
        screen.blit(font.render(t["meas_elapsed"].format(
            el=_hms(elapsed), left=_hms(left) if left is not None else "?"),
            True, HUD_HINT), (20, y))
        y += 26
        screen.blit(font.render(t["meas_stopping"] if cancelling else t["meas_cancel"],
                                True, (235, 150, 90) if cancelling else HUD_HINT), (20, y))
        return

    if state["error"] is not None:
        screen.blit(font.render(t["meas_failed"].format(err=state["error"][:90]),
                                True, (225, 85, 75)), (20, y))
        return
    if state["text"] is None:
        screen.blit(font.render(t["meas_cancelled"], True, (235, 150, 90)), (20, y))
        return

    name = f"thronglets_report_{time.strftime('%Y%m%d_%H%M%S')}.txt"
    if not state.get("saved"):
        with open(name, "w", encoding="utf-8") as fh:
            fh.write(state["text"])
        state["saved"] = os.path.abspath(name)
    screen.blit(font.render(t["meas_written"].format(file=state["saved"]),
                            True, (150, 220, 140)), (20, y)); y += 22
    screen.blit(font.render(t["meas_written2"], True, HUD_HINT), (20, y)); y += 26
    # the tail of the report on screen, so a run tells you something without
    # having to go and open the file
    for line in state["text"].splitlines()[-((SCREEN_H - y) // 18):]:
        screen.blit(font.render(line[:110], True, TEXT_COLOR), (20, y))
        y += 18


def show_tuning(screen, font, lang):
    """Every number that shapes the simulation, in one scrollable list you can
    edit - and make the default for every future run.

    Deliberately shows ALL of them, including the ones that cannot move: the
    point is to see the whole machine in one place, so a parameter that is fixed
    by the shape of the data says so rather than quietly not being listed. The
    registry, the ranges and each parameter's description all come from
    tuning.py, which harvests the descriptions out of simulation.py itself - so
    this screen cannot drift from the code it is showing."""
    t = TEXT[lang]
    # a flat list of ("group", label) / ("param", name) rows, so one cursor and
    # one scroll offset cover headers and values alike
    rows = []
    for _key, en, fr, names in tuning.GROUPS:
        rows.append(("group", fr if lang == "fr" else en))
        for name in names:
            rows.append(("param", name))

    values = tuning.current()
    saved = tuning.load()          # what is currently pinned as the default
    cursor = 1                     # start on the first real parameter
    top = 0
    per_page = (SCREEN_H - 150) // 20
    status = t["tuning_status_ready"].format(n=len(saved)) if saved else ""

    def move(delta):
        """The cursor lands on any parameter, locked ones included - you must be
        able to scroll down and READ the fixed ones, which is half the point of
        the screen. It just refuses to change them."""
        nonlocal cursor
        i = cursor
        while 0 <= i + delta < len(rows):
            i += delta
            if rows[i][0] == "param":
                cursor = i
                return

    def nudge(name, direction, coarse):
        nonlocal status
        if name in tuning.LOCKED:
            status = t["tuning_status_locked"].format(name=name, why=tuning.LOCKED[name])
            return
        lo, hi = tuning.RANGES[name]
        step = tuning.STEPS[name] * (10 if coarse else 1)
        v = values[name] + direction * step
        values[name] = max(lo, min(hi, round(v, 6)))
        tuning.apply({name: values[name]})

    while True:
        if cursor < top + 1:
            top = max(0, cursor - 1)
        if cursor >= top + per_page:
            top = cursor - per_page + 1

        screen.fill(BG)
        screen.blit(font.render(t["tuning_title"], True, (255, 255, 255)), (20, 16))
        screen.blit(font.render(t["tuning_hint"], True, HUD_HINT), (20, 38))
        screen.blit(font.render(t["tuning_hint2"], True, HUD_HINT), (20, 56))

        y = 84
        for i in range(top, min(len(rows), top + per_page)):
            kind, item = rows[i]
            if kind == "group":
                screen.blit(font.render(item, True, HUD_ACCENT), (20, y))
                y += 20
                continue
            name = item
            locked = name in tuning.LOCKED
            here = (i == cursor)
            if here:
                pygame.draw.rect(screen, (32, 40, 28), (16, y - 2, SCREEN_W - 32, 18))
            builtin = tuning.BUILTIN[name]
            value = values.get(name, builtin)
            moved = not locked and abs(value - builtin) > 1e-12
            pinned = name in saved
            name_col = (90, 96, 86) if locked else \
                       (255, 210, 120) if moved else TEXT_COLOR
            screen.blit(font.render(("> " if here else "  ") + name, True, name_col), (20, y))
            if locked:
                shown = f"{builtin:g}"
            else:
                shown = f"{value:g}" if not tuning.is_int(name) else f"{int(value)}"
            screen.blit(font.render(shown, True, name_col), (330, y))
            # what it was born as, whenever that is not what it is now
            if moved:
                screen.blit(font.render(t["tuning_was"].format(v=f"{builtin:g}"),
                                        True, (150, 120, 80)), (410, y))
            if pinned:
                screen.blit(font.render("*", True, (150, 220, 140)), (318, y))
            note = tuning.LOCKED[name] if locked else tuning.DOCS.get(name, "")
            if note:
                screen.blit(font.render(note[:74], True,
                                        (86, 92, 82) if locked else HUD_HINT), (530, y))
            y += 20

        n_moved = sum(1 for n in tuning.tunables()
                      if abs(values[n] - tuning.BUILTIN[n]) > 1e-12)
        n_params = sum(1 for kind, _ in rows if kind == "param")
        foot = t["tuning_footer"].format(shown=n_params, moved=n_moved, pinned=len(saved))
        screen.blit(font.render(foot, True, TEXT_COLOR), (20, SCREEN_H - 44))
        if status:
            screen.blit(font.render(status, True, (150, 220, 140)), (20, SCREEN_H - 24))
        pygame.display.flip()

        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.KEYDOWN:
                continue
            key, mods = event.key, pygame.key.get_mods()
            coarse = bool(mods & pygame.KMOD_SHIFT)
            if key in (pygame.K_ESCAPE, pygame.K_p):
                return
            elif key == pygame.K_DOWN:
                move(1)
            elif key == pygame.K_UP:
                move(-1)
            elif key == pygame.K_PAGEDOWN:
                for _ in range(per_page):
                    move(1)
            elif key == pygame.K_PAGEUP:
                for _ in range(per_page):
                    move(-1)
            elif key in (pygame.K_RIGHT, pygame.K_EQUALS, pygame.K_PLUS):
                nudge(rows[cursor][1], +1, coarse)
            elif key in (pygame.K_LEFT, pygame.K_MINUS):
                nudge(rows[cursor][1], -1, coarse)
            elif key == pygame.K_BACKSPACE:      # this one back to built-in
                name = rows[cursor][1]
                if name in tuning.LOCKED:
                    status = t["tuning_status_locked"].format(
                        name=name, why=tuning.LOCKED[name])
                    continue
                values[name] = tuning.BUILTIN[name]
                tuning.apply({name: values[name]})
                status = t["tuning_status_one_reset"].format(name=name)
            elif key == pygame.K_d:              # make these the defaults
                n = tuning.save(values)
                saved = tuning.load()
                status = (t["tuning_status_saved"].format(n=n, file=tuning.PARAMS_FILE)
                          if n else t["tuning_status_cleared"])
            elif key == pygame.K_r:              # everything back to built-in
                tuning.reset_to_builtin()
                values = tuning.current()
                status = t["tuning_status_reset"]


def flash_message(screen, font, lang, text):
    lines = text.split("\n")
    waiting = True
    while waiting:
        screen.fill(BG)
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, (235, 90, 90)), (20, 20 + i * 24))
        screen.blit(font.render(TEXT[lang]["flash_hint"], True, TEXT_COLOR), (20, 20 + len(lines) * 24 + 20))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                waiting = False


def _import_train_language():
    """Lazy on purpose: only the "train a new one now" path needs PyTorch,
    so the rest of main.py stays usable without it installed."""
    try:
        import train_language
        return train_language
    except ImportError:
        return None


def run_training_ui(screen, font, lang):
    """In-app equivalent of `train_language.py --sweep`, but interactive:
    trains one seed at a time, shows live progress, and lets you accept a
    seed the moment you're happy with it instead of committing to a fixed
    seed count up front. Returns a ready-to-use Genome, or None if PyTorch
    isn't available or the user cancels."""
    t = TEXT[lang]
    train_language = _import_train_language()
    if train_language is None:
        flash_message(screen, font, lang, t["torch_missing"])
        return None

    labels = STATE_LABELS[lang]
    validate_key = pygame.K_v
    clock = pygame.time.Clock()
    tried_seeds = set()

    def next_seed():
        while True:
            s = random.randint(0, 999_999)
            if s not in tried_seeds:
                tried_seeds.add(s)
                return s

    seed = next_seed()

    while True:
        cancel_event = threading.Event()
        progress = {"step": 0, "episodes": TRAIN_EPISODES, "loss": 0.0, "acc": 0.0, "state_to_token": None}
        progress_lock = threading.Lock()
        result = {}

        def on_progress(step, episodes, loss, acc, temperature, state_to_token):
            with progress_lock:
                progress.update(step=step, episodes=episodes, loss=loss, acc=acc, state_to_token=state_to_token)

        def worker():
            speaker, listener = train_language.train(
                TRAIN_EPISODES, TRAIN_BATCH_SIZE, True, TRAIN_LR, seed,
                verbose=False, progress_callback=on_progress, cancel_event=cancel_event,
            )
            result["speaker"] = speaker
            result["listener"] = listener

        start_time = time.monotonic()
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        cancelled = False
        while thread.is_alive():
            for event in events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    cancel_event.set()
                    cancelled = True

            with progress_lock:
                step, episodes = progress["step"], progress["episodes"]
                loss, acc = progress["loss"], progress["acc"]
                state_to_token = progress["state_to_token"]
            elapsed = time.monotonic() - start_time
            rate = step / elapsed if elapsed > 0 else 0.0

            screen.fill(BG)
            lines = [
                "Thronglets",
                "",
                t["training_seed"].format(seed=seed),
                t["training_progress"].format(step=step, episodes=episodes, loss=loss, acc=acc * 100),
                t["training_elapsed"].format(elapsed=elapsed, rate=rate),
            ]
            for i, line in enumerate(lines):
                screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
            y = 20 + len(lines) * 26

            bar_x, bar_w, bar_h = 20, 400, 14
            frac = step / episodes if episodes else 0.0
            pygame.draw.rect(screen, (60, 66, 54), (bar_x, y, bar_w, bar_h))
            pygame.draw.rect(screen, (110, 220, 90), (bar_x, y, int(bar_w * frac), bar_h))
            y += bar_h + 20

            screen.blit(font.render(t["training_explain"], True, (150, 155, 145)), (20, y))
            y += 22
            screen.blit(font.render(t["training_explain2"], True, (150, 155, 145)), (20, y))
            y += 34

            screen.blit(font.render(t["training_live_title"], True, TEXT_COLOR), (20, y))
            y += 26
            if state_to_token is not None:
                for state in (DANGER, FOOD, DISTRESS, MATE, IDLE):
                    token = state_to_token[state]
                    lbl = font.render(f"  {labels[state]:<14}", True, TEXT_COLOR)
                    screen.blit(lbl, (20, y))
                    cx = 20 + lbl.get_width() + 16
                    if token == 0:
                        pygame.draw.circle(screen, (110, 110, 110), (cx, y + 8), 6, width=1)
                    else:
                        pygame.draw.circle(screen, TOKEN_COLORS[token], (cx, y + 8), 6)
                    y += 24

            pygame.display.flip()
            clock.tick(30)

        thread.join()
        if cancelled:
            return None

        speaker, listener = result["speaker"], result["listener"]
        _, collision, acc = train_language.evaluate(speaker, listener)
        state_to_token, token_to_state = train_language.compute_lookup(speaker, listener)

        outcome = t["training_collision"] if collision else t["training_clean"]
        header_lines = [
            "Thronglets",
            "",
            t["training_result"].format(seed=seed, outcome=outcome, acc=acc * 100),
        ]
        footer_line = t["training_collision_hint"] if collision else t["training_validate_hint"]

        choice = None
        while choice is None:
            screen.fill(BG)
            for i, line in enumerate(header_lines):
                screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
            y = 20 + len(header_lines) * 26 + 20
            for state in (DANGER, FOOD, DISTRESS, MATE, IDLE):
                token = state_to_token[state]
                lbl = font.render(f"  {labels[state]:<14}", True, TEXT_COLOR)
                screen.blit(lbl, (20, y))
                cx = 20 + lbl.get_width() + 16
                if token == 0:
                    pygame.draw.circle(screen, (110, 110, 110), (cx, y + 8), 6, width=1)
                else:
                    pygame.draw.circle(screen, TOKEN_COLORS[token], (cx, y + 8), 6)
                y += 24
            screen.blit(font.render(footer_line, True, TEXT_COLOR), (20, y + 20))
            pygame.display.flip()
            for event in events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == validate_key and not collision:
                        choice = "accept"
                    elif event.key == pygame.K_n:
                        choice = "next"
                    elif event.key == pygame.K_ESCAPE:
                        choice = "cancel"
            clock.tick(30)

        if choice == "accept":
            train_language.export_vocabulary(speaker, listener, DEFAULT_LANGUAGE_FILE)
            return Genome.from_lookup(state_to_token, token_to_state)
        if choice == "cancel":
            return None
        seed = next_seed()


COMPARE_QUICK = (4, 8000)
COMPARE_THOROUGH = (8, 40000)
COMPARE_EXPERT = (16, 60000)


def choose_compare_mode(screen, font, lang, traits_available):
    t = TEXT[lang]
    lines = [
        "Thronglets",
        "",
        t["compare_mode_prompt"],
        t["compare_mode_language"],
        t["compare_mode_traits"] if traits_available else t["compare_mode_traits_unavailable"],
        "",
        t["compare_mode_hint"],
    ]
    while True:
        screen.fill(BG)
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_l:
                    return "language"
                if event.key == pygame.K_t and traits_available:
                    return "traits"
                if event.key == pygame.K_ESCAPE:
                    return None


def choose_compare_depth(screen, font, lang):
    t = TEXT[lang]
    lines = [
        "Thronglets",
        "",
        t["compare_depth_prompt"],
        t["compare_depth_quick"],
        t["compare_depth_thorough"],
        t["compare_depth_expert"],
        "",
        t["compare_depth_hint"],
    ]
    while True:
        screen.fill(BG)
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r or event.key == pygame.K_RETURN:
                    return COMPARE_QUICK
                if event.key == pygame.K_a:
                    return COMPARE_THOROUGH
                if event.key == pygame.K_e:
                    return COMPARE_EXPERT
                if event.key == pygame.K_ESCAPE:
                    return None


def run_compare_ui(screen, font, world, lang, init_pop, seed_genome):
    """Runs simulation.compare_seeds() in a background thread with a live
    progress screen (same shape as run_training_ui's), then shows a results
    table. Purely a side experiment - never touches the live `world`."""
    t = TEXT[lang]
    labels = STATE_LABELS[lang]
    trait_labels = TRAIT_LABELS[lang]

    mode = choose_compare_mode(screen, font, lang, world.adaptive_traits)
    if mode is None:
        return
    depth = choose_compare_depth(screen, font, lang)
    if depth is None:
        return
    n_seeds, ticks = depth

    clock = pygame.time.Clock()
    cancel_event = threading.Event()
    progress = {"seed": 0, "tick": 0}
    progress_lock = threading.Lock()
    result = {}

    def on_progress(seed_i, n, tick, total_ticks):
        with progress_lock:
            progress.update(seed=seed_i + 1, tick=tick)

    def worker():
        result["results"] = compare_seeds(
            n_seeds, ticks, init_pop, len(world.predators), mode == "traits",
            seed_genome=seed_genome, progress_callback=on_progress, cancel_event=cancel_event,
        )

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    cancelled = False
    while thread.is_alive():
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                cancel_event.set()
                cancelled = True

        with progress_lock:
            seed_n, tick = progress["seed"], progress["tick"]
        screen.fill(BG)
        lines = [
            "Thronglets",
            "",
            t["compare_progress"].format(seed=max(1, seed_n), n_seeds=n_seeds, tick=tick, ticks=ticks),
        ]
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
        pygame.display.flip()
        clock.tick(30)

    thread.join()
    results = result.get("results", [])
    if cancelled and not results:
        flash_message(screen, font, lang, t["compare_cancelled"].format(n=len(results)))
        return

    waiting = True
    while waiting:
        screen.fill(BG)
        y = 20
        screen.blit(font.render(t["compare_result_title"].format(n_seeds=len(results), ticks=ticks),
                                 True, (255, 255, 255)), (20, y))
        y += 40

        if mode == "traits":
            screen.blit(font.render(t["compare_traits_header"], True, TEXT_COLOR), (20, y))
            y += 26
            for trait in range(N_TRAITS):
                vals = [r["traits"][trait] * 100 for r in results if r["traits"] is not None]
                mean = sum(vals) / len(vals)
                std = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
                row = f"{trait_labels[trait]:<14} {mean:5.1f}%   {std:5.1f}%   {min(vals):5.1f}%  {max(vals):5.1f}%"
                screen.blit(font.render(row, True, TEXT_COLOR), (20, y))
                y += 24
        else:
            screen.blit(font.render(t["compare_lang_header"], True, TEXT_COLOR), (20, y))
            y += 26
            for state in (DANGER, FOOD, DISTRESS, MATE, IDLE):
                lbl = font.render(f"  {labels[state]:<14}", True, TEXT_COLOR)
                screen.blit(lbl, (20, y))
                cx = 20 + lbl.get_width() + 10
                for r in results:
                    token = r["vocab"][state][0]
                    if token == 0:
                        pygame.draw.circle(screen, (110, 110, 110), (cx, y + 8), 6, width=1)
                    else:
                        pygame.draw.circle(screen, TOKEN_COLORS[token], (cx, y + 8), 6)
                    cx += 20
                y += 24
            y += 10
            clean = sum(1 for r in results if not r["collision"])
            screen.blit(font.render(t["compare_collision_summary"].format(clean=clean, n_seeds=len(results)),
                                     True, TEXT_COLOR), (20, y))
            y += 26

        if cancelled:
            y += 10
            screen.blit(font.render(t["compare_cancelled"].format(n=len(results)), True, (235, 90, 90)), (20, y))
            y += 26

        screen.blit(font.render(t["compare_dismiss"], True, (150, 155, 145)), (20, y + 14))
        pygame.display.flip()
        for event in events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                waiting = False


def main():
    parser = argparse.ArgumentParser(description="Thronglets - pygame renderer")
    parser.add_argument("--language", type=str, default=None,
                         help="seed the population with a train_language.py --export vocabulary "
                              "instead of starting from scratch")
    args = parser.parse_args()

    pygame.init()
    tones, sound_channel = init_sound()
    pygame.display.set_caption("Thronglets - a tiny language is being born")
    global SCREEN_W, SCREEN_H, SCALE_X, SCALE_Y, HUD_H, MINIMAL_HUD_H, EXPANDED_HUD_H
    # maximised and resizable, not fullscreen: this is a thing you leave running
    # beside other windows. F11 (or Alt+Enter) takes the whole screen when you
    # want it, from any screen in the game.
    screen = open_window()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)

    lang = choose_language(screen, font)

    world = None
    master_mode = False
    # a value pinned in the tuning screen is the default for this run, so it has
    # to land before the first world is built
    tuning.load_and_apply()
    while True:
        start = choose_start(screen, font, lang, os.path.exists(DEFAULT_SAVE_FILE))
        if start == "tuning":
            show_tuning(screen, font, lang)
        elif start == "measure":
            show_measure(screen, font, lang)
        else:
            break
    if start == "master":
        master_mode = True
    elif start == "resume":
        try:
            world = load_world(DEFAULT_SAVE_FILE)
            mode = "manual" if (world.manual_food or world.manual_predators) else "auto"
            init_pop = world.population()
        except (OSError, ValueError, KeyError):
            world = None
            flash_message(screen, font, lang, TEXT[lang]["resume_load_failed"].format(file=DEFAULT_SAVE_FILE))

    seed_genome = None
    learning = False
    if world is None:
        mode = choose_mode(screen, font, lang)
        init_pop = choose_population(screen, font, lang)
        adaptive_traits = choose_adaptive_traits(screen, font, lang)
        # Master Mode needs the learned mind (to break its will), so it forces
        # learning on and skips the usual opt-in prompt.
        learning = True if master_mode else choose_learning(screen, font, lang)

        if args.language:
            seed_genome = load_seed_genome(args.language)
        else:
            ai_choice = choose_ai(screen, font, lang)
            if ai_choice == "yes":
                try:
                    # a language you trained yourself wins; otherwise fall back
                    # to the trained one shipped with the project, so this
                    # option works out of the box with no PyTorch involved
                    seed_genome = load_seed_genome(DEFAULT_LANGUAGE_FILE)
                except OSError:
                    seed_genome = load_bundled_genome()
                    if seed_genome is None:
                        flash_message(screen, font, lang,
                                      TEXT[lang]["ai_missing_file"].format(file=DEFAULT_LANGUAGE_FILE))
            elif ai_choice == "train":
                seed_genome = run_training_ui(screen, font, lang)
        # Master Mode: no predators at all, and the flock never reproduces on
        # its own - it only grows when the master spawns a creature by hand.
        world = _new_world(mode, 0 if master_mode else 6, init_pop, seed_genome,
                           adaptive_traits, learning)
        if master_mode:
            world.allow_reproduction = False
    else:
        adaptive_traits = world.adaptive_traits
        learning = getattr(world, "learning", False)   # honour the saved world
        master_mode = getattr(world, "master_mode", False)   # a resumed Master game stays Master
    world.master_mode = master_mode

    # the disposition line takes one extra row, so grow both HUD sizes to fit
    # it (only when learning is on - a pure-selection run keeps the old, tidy
    # heights)
    if learning:
        MINIMAL_HUD_H += 22   # the disposition/obedience gauge row
        EXPANDED_HUD_H += 88   # gauge + choice breakdown + mood legend + memory hint
        HUD_H = MINIMAL_HUD_H
        SCALE_Y = (SCREEN_H - HUD_H) / HEIGHT

    paused = False
    speed = 1  # ticks per real second
    hud_expanded = False
    sound_muted = False
    fire_mode = False   # the fire tool: armed with F, burns on click/drag
    flames = []         # [world_x, world_y, elapsed] flame puffs to animate
    dominate_id = None  # Master Mode: creature currently being isolated (hold I)
    dominate_days = 0.0 # subjective days of isolation piled on it this hold
    order = None        # Master Mode standing order (None=follow / gather / disperse / halt)
    hovered_id = None   # id of the creature the cursor is currently over
    tick_accumulator = 0.0
    running = True

    while running:
        # Capped so returning from a blocking screen (help, save confirmation)
        # resumes at normal pace instead of fast-forwarding through a huge backlog.
        dt = min(clock.tick(60) / 1000.0, 0.25)
        for event in events():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    world = _new_world(mode, len(world.predators), init_pop, seed_genome,
                                       adaptive_traits, learning)
                elif event.key == pygame.K_UP:
                    speed = min(200, speed + (1 if speed < 10 else 10))
                elif event.key == pygame.K_DOWN:
                    speed = max(1, speed - (1 if speed <= 10 else 10))
                elif event.key == pygame.K_n:
                    fx, fy = world.rng.uniform([10, 10], [WIDTH - 10, HEIGHT - 10])
                    world.add_food(fx, fy)
                    teach_nearby(world, fx, fy, LEARN_FOOD_REWARD)
                elif event.key == pygame.K_p and not master_mode:
                    px, py = world.rng.uniform([0, 0], [WIDTH, HEIGHT])
                    world.add_predator(px, py)
                    teach_nearby(world, px, py, LEARN_PREDATOR_REWARD)
                elif event.key == pygame.K_LEFTBRACKET and not master_mode:
                    world.remove_predator()
                elif event.key == pygame.K_RIGHTBRACKET and not master_mode:
                    world.add_random_predator()
                elif event.key == pygame.K_s:
                    save_world(world, DEFAULT_SAVE_FILE)
                    flash_message(screen, font, lang, TEXT[lang]["save_confirmed"].format(file=DEFAULT_SAVE_FILE))
                elif event.key == pygame.K_g:
                    show_graph(screen, font, world, lang)
                elif event.key == pygame.K_t:
                    show_family(screen, font, world, lang)
                elif event.key == pygame.K_c:
                    run_compare_ui(screen, font, world, lang, init_pop, seed_genome)
                elif event.key == pygame.K_d:
                    show_translator(screen, font, world, lang)
                elif event.key in (pygame.K_QUESTION, pygame.K_SLASH):
                    show_faq(screen, font, lang)
                elif event.key == pygame.K_f:
                    fire_mode = not fire_mode      # arm / disarm the fire tool
                elif event.key == pygame.K_h:
                    show_help(screen, font, lang)
                elif event.key == pygame.K_v:
                    hud_expanded = not hud_expanded
                    HUD_H = EXPANDED_HUD_H if hud_expanded else MINIMAL_HUD_H
                    SCALE_Y = (SCREEN_H - HUD_H) / HEIGHT
                elif event.key == pygame.K_m:
                    sound_muted = not sound_muted
                elif master_mode and event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    order = {pygame.K_1: None, pygame.K_2: "gather",
                             pygame.K_3: "disperse", pygame.K_4: "halt"}[event.key]
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                mx, my = event.pos
                if my <= HUD_H:
                    hud_expanded = not hud_expanded
                    HUD_H = EXPANDED_HUD_H if hud_expanded else MINIMAL_HUD_H
                    SCALE_Y = (SCREEN_H - HUD_H) / HEIGHT
                else:
                    wx, wy = mx / SCALE_X, (my - HUD_H) / SCALE_Y
                    if master_mode:
                        # Master Mode: right-click births a new creature; left
                        # click does nothing on its own (the flock can't starve,
                        # so there is no feeding) - arm the fire tool F to kill.
                        if event.button == 3:
                            world.add_creature(wx, wy)
                        elif fire_mode:
                            burn_at(world, wx, wy, flames)
                    elif event.button == 3:
                        world.add_predator(wx, wy)
                        teach_nearby(world, wx, wy, LEARN_PREDATOR_REWARD)
                    elif fire_mode:
                        burn_at(world, wx, wy, flames)   # left-click burns while armed
                    else:
                        world.add_food(wx, wy)
                        teach_nearby(world, wx, wy, LEARN_FOOD_REWARD)
            elif event.type == pygame.MOUSEMOTION and fire_mode and event.buttons[0]:
                mx, my = event.pos                        # drag the fire brush
                if my > HUD_H:
                    burn_at(world, mx / SCALE_X, (my - HUD_H) / SCALE_Y, flames)

        # the mouse cursor is the player's "hand": creatures feel it, and it
        # carries whatever they last learned to associate with it (approach
        # food, flee predators). Only over the field, not the HUD strip.
        mx, my = pygame.mouse.get_pos()
        world.hand_pos = (mx / SCALE_X, (my - HUD_H) / SCALE_Y) if my > HUD_H else None
        world.order = order if master_mode else None   # broken creatures obey it

        if not paused:
            tick_accumulator += dt
            tick_interval = 1.0 / speed
            while tick_accumulator >= tick_interval:
                world.step()
                tick_accumulator -= tick_interval
        else:
            tick_accumulator = 0.0

        hovered_id = update_listening(sound_channel, tones, world, pygame.mouse.get_pos(),
                                       HUD_H, sound_muted, hovered_id)

        # Master Mode: holding I over a creature isolates it in accelerated
        # time, breaking its will (obedience up, subjective months of solitude).
        dominating = None
        if master_mode and pygame.key.get_pressed()[pygame.K_i] and hovered_id is not None:
            tgt = next((c for c in world.creatures
                        if c.id == hovered_id and c.alive and c.mind is not None), None)
            if tgt is not None:
                world.dominate(tgt, DOMINATE_RATE * dt)
                dominate_days = (dominate_days if dominate_id == hovered_id else 0.0) + dt * DOMINATE_DAYS_PER_SEC
                dominate_id = hovered_id
                dominating = tgt
        if dominating is None:
            dominate_id, dominate_days = None, 0.0

        draw(screen, font, world, paused, speed, mode, lang, hud_expanded,
             trained=seed_genome is not None, muted=sound_muted, hovered_id=hovered_id)

        # Master Mode overlay: the isolation readout over the creature you're
        # breaking, and a dark vignette to sell the "alone in the void" mood.
        if dominating is not None:
            veil = pygame.Surface((SCREEN_W, SCREEN_H - HUD_H), pygame.SRCALPHA)
            veil.fill((0, 0, 0, min(150, int(dominating.mind.obedience * 150))))
            screen.blit(veil, (0, HUD_H))
            sx, sy = int(dominating.pos[0] * SCALE_X), int(dominating.pos[1] * SCALE_Y) + HUD_H
            pygame.draw.circle(screen, (235, 150, 90), (sx, sy),
                               int(6 + 10 * dominating.mind.obedience), width=2)
            msg = TEXT[lang]["master_isolating"].format(
                cid=dominating.id, span=_subjective_span(dominate_days, lang),
                pct=dominating.mind.obedience)
            banner = font.render(msg, True, (245, 170, 110))
            screen.blit(banner, (SCREEN_W // 2 - banner.get_width() // 2, HUD_H + 30))

        # flame puffs where creatures burned, flickering out over FLAME_DUR
        for f in flames:
            f[2] += dt
        flames[:] = [f for f in flames if f[2] < FLAME_DUR]
        for fx, fy, el in flames:
            sx, sy = int(fx * SCALE_X), int(fy * SCALE_Y) + HUD_H
            frac = el / FLAME_DUR
            for k, col in enumerate(FLAME_COLORS):
                r = max(1, int((7 - k * 2) * (1.0 - frac)))
                jitter = int((k + 1) * 2 * math.sin(el * 40 + k))
                pygame.draw.circle(screen, col, (sx + jitter, sy - int(frac * 10) - k * 2), r)

        # the fire tool: a red brush ring at the cursor + an armed banner
        if fire_mode:
            mx, my = pygame.mouse.get_pos()
            if my > HUD_H:
                pygame.draw.circle(screen, (235, 90, 40), (mx, my), int(FIRE_RADIUS * SCALE_X), width=2)
            banner = font.render(TEXT[lang]["hud_fire_armed"], True, (245, 130, 60))
            screen.blit(banner, (SCREEN_W // 2 - banner.get_width() // 2, HUD_H + 6))

        # Master Mode: an uprising alert flashes when the free flock's terror
        # is tipping your grip over (takes priority over the standing hint).
        if master_mode and (world.master_unrest() or 0.0) >= UPRISING_UNREST:
            if int(pygame.time.get_ticks() / 250) % 2 == 0:   # flash
                al = font.render(TEXT[lang]["master_uprising"], True, (245, 80, 60))
                screen.blit(al, (SCREEN_W // 2 - al.get_width() // 2, HUD_H + 6))
        elif master_mode and dominating is None and not fire_mode:
            banner = font.render(TEXT[lang]["master_banner"], True, (200, 150, 110))
            screen.blit(banner, (SCREEN_W // 2 - banner.get_width() // 2, HUD_H + 6))
            oname = TEXT[lang]["order_follow"] if order is None else TEXT[lang]["order_" + order]
            ol = font.render(TEXT[lang]["master_order_line"].format(name=oname), True, (235, 150, 90))
            screen.blit(ol, (SCREEN_W // 2 - ol.get_width() // 2, HUD_H + 26))

        pygame.display.flip()

    if sound_channel is not None:
        sound_channel.stop()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
