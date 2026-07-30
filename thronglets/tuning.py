"""Every number that shapes the simulation, in one place you can see and change.

simulation.py is deliberately a wall of named constants - each one a decision
about how these creatures work, most of them arrived at by measuring something.
This module makes that wall *visible and editable* from inside the game, and
lets a value you like become the new default for every future run.

Two design choices worth knowing:

**Descriptions are harvested from simulation.py, not retyped here.** Each
constant already carries the comment that explains it, written next to the code
that uses it. Copying those into a second list would guarantee the two drift
apart; instead this reads them out of the source at import. The screen therefore
cannot go stale, and there is exactly one place to edit a parameter's meaning.

**Some parameters are shown but locked.** Network shape, feature-vector indices,
token counts, world dimensions and the affect-map grid are not preferences,
they are the shape of the data: changing one mid-flight would not retune the
simulation, it would break it (a Mind's weight matrices are built to a fixed
size, and saved minds are restored to it). They are listed anyway - the point of
the screen is to see everything - marked with why they cannot be moved.

Overrides live in a small JSON file next to the save, so a tuned setup survives
restarts and can be shared or deleted like any other file.
"""

import json
import os
import re

import simulation as S

PARAMS_FILE = "thronglets_params.json"

# The built-in value of every tunable, captured at import BEFORE any override is
# applied - so "reset to built-in" always has something true to return to, even
# after a session has been running with custom values for hours.
BUILTIN = {}

# name -> why it cannot be changed. Shown in the screen, greyed out.
LOCKED = {
    "N_STATES": "the situations a creature can be in - fixed by the simulation",
    "N_TOKENS": "the size of the flock's alphabet - genomes and networks are built to it",
    "N_TRAITS": "how many physical traits a genome carries",
    "N_ACTIONS": "the choices the actor picks between - the policy head's width",
    "LEARN_HIDDEN": "hidden units in a mind - weight matrices are built to this",
    "F_SIGNAL": "an index into the feature vector, not a setting",
    "REPLAY_SIZE": "the fixed length of a mind's memory of shocks",
    "MEM_COLS": "affect-map width - saved minds are restored to this grid",
    "MEM_ROWS": "affect-map height - saved minds are restored to this grid",
    "WIDTH": "world width - positions in a save are relative to it",
    "HEIGHT": "world height - positions in a save are relative to it",
}

# Grouped the way someone LOOKING for a parameter would group them - by what
# they do to the creatures - rather than by name prefix.
GROUPS = [
    ("senses", "Senses and distances", "Sens et distances", [
        "SEE_RADIUS", "HEAR_RADIUS", "DANGER_RADIUS", "EAT_RADIUS", "MATE_RADIUS",
        "CROWD_RADIUS", "CROWD_CAP", "FOOD_PERCEPTION", "PREDATOR_PERCEPTION",
        "HAND_PERCEPTION", "TRAUMA_PERCEPTION", "MOOD_CONTAGION_RADIUS", "REBEL_RADIUS",
    ]),
    ("motion", "Movement", "Deplacement", [
        "SPEED", "WANDER_STRENGTH", "DRIVE_STRENGTH", "FLEE_STRENGTH",
        "DISTRESS_SEARCH_STRENGTH", "MEM_MOVE_STRENGTH", "EDGE_MARGIN", "EDGE_PUSH",
    ]),
    ("body", "Body and energy", "Corps et energie", [
        "MAX_ENERGY", "INIT_ENERGY", "METABOLISM", "MAX_AGE", "DISTRESS_ENERGY",
        "SPEED_ENERGY_COST", "VISION_ENERGY_COST", "HEARING_ENERGY_COST", "SIGNAL_COST",
    ]),
    ("breeding", "Reproduction and inheritance", "Reproduction et heredite", [
        "MATE_ENERGY", "MATE_COST", "MIN_MATE_AGE", "BUD_ENERGY", "BUD_COST",
        "MAX_POPULATION", "MUTATION_RATE", "MUTATION_SCALE",
        "INHERIT_BLEND", "INHERIT_NOISE", "MEM_INHERIT", "MOOD_INHERIT",
    ]),
    ("world", "Food and predators", "Nourriture et predateurs", [
        "FOOD_VALUE", "FOOD_SPAWN_INTERVAL", "MAX_FOOD",
        "DEFAULT_PREDATOR_COUNT", "MAX_PREDATORS", "PREDATOR_SPEED",
        "PREDATOR_HUNT_RADIUS", "PREDATOR_KILL_RADIUS",
        "PREDATOR_SEPARATION_RADIUS", "PREDATOR_SEPARATION_STRENGTH",
    ]),
    ("calls", "Calls and their meaning", "Cris et leur sens", [
        "SIGNAL_STRENGTH", "SIGNAL_ALARM_DV", "SIGNAL_ALARM_DA",
        "SIGNAL_ALARM_MIN", "SIGNAL_ALARM_FULL",
    ]),
    ("mood", "Mood: valence and arousal", "Humeur : valence et eveil", [
        "MOOD_DECAY", "MOOD_VALENCE_REST", "MOOD_AROUSAL_REST",
        "MOOD_GLOOM_WEIGHT", "MOOD_GLOOM_AROUSAL", "MOOD_GLOOM_ONSET",
        "MOOD_FEED_DV", "MOOD_FEED_DA", "MOOD_HARM_DV", "MOOD_HARM_DA",
        "MOOD_WITNESS", "MOOD_CONTAGION", "VALENCE_CLIP",
        "MOOD_RESTLESS", "MOOD_PANIC_FLEE", "MOOD_SOCIAL",
        "MOOD_SPEED_FLOOR", "MOOD_SPEED_GAIN",
    ]),
    ("hand", "Your hand", "Ta main", [
        "HAND_APPROACH_SCALE", "HAND_MOVE_STRENGTH", "HAND_STANDOFF",
        "HAND_CALL_RANGE", "HAND_GATHER",
    ]),
    ("learning", "Learning", "Apprentissage", [
        "LEARN_RATE", "CRITIC_RATE", "GAMMA", "TD_LAMBDA", "DECIDE_TEMP",
        "LOOKAHEAD", "ACTION_HOLD", "REWARD_EAT", "OBSERVE_RATE",
        "TRAUMA_RATE", "PREDATOR_TRAUMA_RATE", "PARAM_CLIP",
        "REPLAY_PER_STEP", "REPLAY_THRESHOLD", "REPLAY_RATE",
    ]),
    ("places", "Memory of places", "Memoire des lieux", [
        "MEM_DECAY", "MEM_FOOD", "MEM_HARM", "MEM_WITNESS", "MEM_CLIP",
    ]),
    ("master", "Master Mode", "Mode Maitre", [
        "EROSION_PER_AFRAID", "UPRISING_UNREST", "UPRISING_EROSION_MULT",
        "REBEL_RALLY_STRENGTH",
    ]),
    ("history", "Bookkeeping", "Journalisation", [
        "VOCAB_HISTORY_INTERVAL",
    ]),
    ("locked", "Fixed shape (cannot be changed)", "Structure figee (non modifiable)",
     list(LOCKED)),
]


def _harvest_docs():
    """Read each constant's own trailing comment out of simulation.py.

    Handles both `NAME = value  # why` and the paired `A, B = 1, 2  # why` form
    (where the one comment describes both). A constant with no comment simply
    has no description - better an honest blank than an invented sentence."""
    docs = {}
    try:
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "simulation.py"), encoding="utf-8").read()
    except OSError:
        return docs
    for line in src.splitlines():
        m = re.match(r"^([A-Z][A-Z0-9_]*)(?:\s*,\s*([A-Z][A-Z0-9_]*))?\s*=\s*[^#]*#\s*(.+)$",
                     line)
        if m:
            note = m.group(3).strip()
            for name in (m.group(1), m.group(2)):
                if name:
                    docs.setdefault(name, note)
    return docs


DOCS = _harvest_docs()


def _range_for(name, value):
    """A sane slider range around the built-in value.

    Derived rather than hand-listed: anything a parameter's own default tells us
    is more trustworthy than a hundred bounds typed from memory. Values that are
    clearly a 0..1 fraction get 0..1; a signed mood delta gets -1..1; everything
    else gets a generous span around its default, never crossing zero if the
    default doesn't."""
    if name in ("GAMMA", "TD_LAMBDA", "MOOD_DECAY", "MUTATION_RATE", "OBSERVE_RATE",
                "MOOD_CONTAGION", "MOOD_INHERIT", "MEM_INHERIT", "INHERIT_BLEND",
                "MOOD_SPEED_FLOOR", "MEM_DECAY", "REPLAY_RATE"):
        return 0.0, 1.0
    if value < 0:
        return min(-1.0, value * 4.0), 0.0
    if 0.0 < value <= 1.0:
        return 0.0, max(1.0, value * 4.0)
    return 0.0, value * 4.0


def _step_for(value):
    span = abs(value) if value else 1.0
    if span <= 1.0:
        return 0.01
    if span <= 20.0:
        return 0.5
    return max(1.0, round(span / 40.0))


def tunables():
    """Every editable parameter name, in the order the screen shows them."""
    return [n for _, _, _, names in GROUPS for n in names if n not in LOCKED]


def capture_builtins():
    """Snapshot the values compiled into simulation.py. Called once at import,
    before any override touches them."""
    if BUILTIN:
        return
    for _, _, _, names in GROUPS:
        for name in names:
            if hasattr(S, name):
                BUILTIN[name] = getattr(S, name)


capture_builtins()

RANGES = {n: _range_for(n, BUILTIN[n]) for n in BUILTIN if n not in LOCKED}
STEPS = {n: _step_for(BUILTIN[n]) for n in BUILTIN if n not in LOCKED}


def current():
    """What the simulation is running with right now."""
    return {n: getattr(S, n) for n in BUILTIN if hasattr(S, n)}


def is_int(name):
    return isinstance(BUILTIN.get(name), int) and not isinstance(BUILTIN.get(name), bool)


def apply(values):
    """Push values into simulation.py's module globals.

    This is the only way the screen changes anything: the simulation keeps
    reading its own constants exactly as before, so nothing downstream needs to
    know a tuning screen exists."""
    for name, value in values.items():
        if name in LOCKED or name not in BUILTIN:
            continue
        setattr(S, name, int(round(value)) if is_int(name) else float(value))


def reset_to_builtin():
    apply(dict(BUILTIN))


def load(path=PARAMS_FILE):
    """Read saved defaults. Unknown or locked names are ignored, so a file from
    an older version cannot break startup."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items()
            if k in BUILTIN and k not in LOCKED and isinstance(v, (int, float))}


def save(values, path=PARAMS_FILE):
    """Make these the defaults for every future run.

    Only values that actually differ from the built-in are written, so the file
    stays a readable record of what you changed rather than a dump of
    everything - and a parameter you reset disappears from it."""
    changed = {n: v for n, v in values.items()
               if n in BUILTIN and n not in LOCKED
               and abs(float(v) - float(BUILTIN[n])) > 1e-12}
    if not changed:
        if os.path.exists(path):
            os.remove(path)
        return 0
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(changed, fh, indent=2, sort_keys=True)
    return len(changed)


def load_and_apply(path=PARAMS_FILE):
    """Called once at startup, before any world is built."""
    saved = load(path)
    if saved:
        apply(saved)
    return saved
