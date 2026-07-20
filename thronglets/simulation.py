"""Thronglets: a tiny artificial-life sandbox.

Simple creatures forage, mate, flee predators, and die on a 2D world. Each
one is born with a genome that decides which "token" it emits when it is
hungry, has spotted food, wants to mate, senses a predator nearby, or is
running critically low on energy with nothing in sight to fix that - and how
it reacts to tokens it hears from others. There is no training loop and
nobody is told what the tokens should mean: genomes that happen to signal
and interpret usefully help their owners survive and reproduce more, so a
shared vocabulary - including alarm calls - can emerge purely from selection
over generations, the same basic idea (rules + evolution, not gradient
descent) behind classic artificial-life language experiments.

No pygame import here on purpose: this module is the simulation core and can
be driven headlessly (see test_smoke.py); main.py is the renderer.
"""

import json
import random
from collections import deque

import numpy as np

WIDTH, HEIGHT = 200.0, 140.0

IDLE, FOOD, MATE, DANGER, DISTRESS = 0, 1, 2, 3, 4
N_STATES = 5
N_TOKENS = 6  # token 0 means "silent"

SEE_RADIUS = 18.0    # a creature can directly spot food/mates within this range
HEAR_RADIUS = 34.0   # but it can *hear* a signal from further away than it can see
SPEED = 1.6
WANDER_STRENGTH = 0.5
DRIVE_STRENGTH = 1.2
FLEE_STRENGTH = 1.8
SIGNAL_STRENGTH = 0.9
EDGE_MARGIN = 12.0
EDGE_PUSH = 1.0

PREDATOR_SPEED = 1.3
PREDATOR_HUNT_RADIUS = 70.0
PREDATOR_KILL_RADIUS = 3.0
PREDATOR_SEPARATION_RADIUS = 20.0  # predators this close to each other push apart
PREDATOR_SEPARATION_STRENGTH = 2.0
DANGER_RADIUS = 22.0  # how far a creature can spot a predator directly
DEFAULT_PREDATOR_COUNT = 6  # used in automatic mode unless the caller picks another number
MAX_PREDATORS = 30  # safety cap, for both the automatic count and manual placement

METABOLISM = 0.06
SIGNAL_COST = 0.025  # extra energy drain for emitting any non-silent token
INIT_ENERGY = 60.0
MAX_ENERGY = 120.0
EAT_RADIUS = 4.0
FOOD_VALUE = 30.0
DISTRESS_ENERGY = 20.0        # below this, with no food in sight, a creature is in distress
DISTRESS_SEARCH_STRENGTH = 1.0  # a wider, more urgent search than plain idle wandering

MATE_ENERGY = 75.0
MIN_MATE_AGE = 60
MATE_RADIUS = 5.0
MATE_COST = 20.0
BUD_ENERGY = 95.0
BUD_COST = 40.0

MAX_AGE = 3200
MAX_POPULATION = 220
FOOD_PATCH_SIZE = (4, 8)
FOOD_SPAWN_INTERVAL = 20
MAX_FOOD = 140

MUTATION_RATE = 0.12
MUTATION_SCALE = 0.35

VOCAB_HISTORY_INTERVAL = 20  # ticks between samples - unbounded, covers the whole run

# Adaptive traits (opt-in, see World(adaptive_traits=...)): four physical
# traits, evolved and mutated exactly like the signaling genes, each bounded
# so mutation can't run away to something absurd. Speed/vision/hearing all
# carry a real energy cost (SPEED_ENERGY_COST etc. below) - being fast,
# far-sighted, and sharp-eared all at once is expensive, so selection has to
# actually weigh the trade-off instead of every trait just maxing out.
TRAIT_SPEED, TRAIT_VISION, TRAIT_HEARING, TRAIT_METABOLISM = 0, 1, 2, 3
N_TRAITS = 4
TRAIT_BOUNDS = np.array([
    [0.8, 2.6],    # speed
    [10.0, 28.0],  # vision (equivalent to SEE_RADIUS)
    [20.0, 50.0],  # hearing (equivalent to HEAR_RADIUS)
    [0.03, 0.10],  # baseline metabolism
])
DEFAULT_TRAITS = np.array([SPEED, SEE_RADIUS, HEAR_RADIUS, METABOLISM])
TRAIT_MUTATION_SCALE = (TRAIT_BOUNDS[:, 1] - TRAIT_BOUNDS[:, 0]) * 0.08

SPEED_ENERGY_COST = 0.011     # extra metabolism per unit of speed above the minimum
VISION_ENERGY_COST = 0.00083  # extra metabolism per unit of vision above the minimum
HEARING_ENERGY_COST = 0.00033  # extra metabolism per unit of hearing above the minimum
DANGER_VISION_RATIO = DANGER_RADIUS / SEE_RADIUS  # keeps danger-spotting proportional to vision

# Lifetime + generational learning (opt-in, see World(learning=...)). On top
# of the evolved genome, each creature carries a tiny reward-modulated "mind"
# (see the Mind class) that learns - from its own experience AND from
# watching others - how to feel about the player's hand: the cursor that can
# feed it (good) or burn/stab it (very bad). It is NOT genetic - it changes
# within a single lifetime - yet a newborn inherits a blend of its parents'
# learned feelings, so hard-won lessons persist and compound across
# generations while ongoing selection keeps the well-adapted ones. Nothing
# here scripts "flee the player": the sign of the reaction is discovered from
# the sign of experienced reward. All of it stays dormant unless
# learning=True, so the other renderers and the headless smoke test are
# completely unaffected.
LEARN_FEATURES = 2            # [hand proximity, hand proximity x hunger]
HAND_PERCEPTION = 48.0        # world units: how near the hand must be to feel it
LEARN_RATE = 0.05             # step size for learning from one's own experience
OBSERVE_RATE = 0.02           # weaker step for learning by watching a neighbour
# Seeing a neighbour hurt or killed is not idle observation - it is trauma, and
# it must actually stick, or a player who keeps killing never comes to be
# feared (the victims die and drop out of the flock's average, leaving only the
# faintly-taught survivors). Violent events are witnessed from farther and burn
# in far deeper than a feeding does.
TRAUMA_PERCEPTION = 85.0      # world units a violent death is witnessed from
TRAUMA_RATE = 0.11            # how deeply witnessing harm teaches fear of the hand
ELIG_DECAY = 0.88             # how fast the "what just happened to me" trace fades
VALENCE_CLIP = 1.5            # bound on every learned weight (stops runaway)
REWARD_EAT = 0.4              # mild reward for finding food while the hand is near
HAND_MOVE_STRENGTH = 1.3      # how hard the learned feeling pulls toward/away the hand
HAND_STANDOFF = 14.0          # trusting creatures gather around the hand at this distance, not on it
HAND_CALL_RANGE = 80.0        # how far off a trusting creature will come to gather near the hand
INHERIT_BLEND = 0.85          # fraction of the parents' learned feelings a child keeps
INHERIT_NOISE = 0.05          # small variation so offspring aren't carbon copies

# --- persistent inner mood -------------------------------------------------
# On top of the learned appraisal above, a mind carries a lasting AFFECTIVE
# STATE - a real inner life, not a value recomputed from scratch each frame.
# It follows the circumplex model of emotion: two slow-moving axes,
#   valence  -1 (miserable) .. +1 (happy)
#   arousal   0 (calm/sleepy) .. 1 (agitated)
# together they place a creature's feeling on a plane - e.g. low valence +
# high arousal reads as fear, low valence + low arousal as sadness. The mood
# has MOMENTUM: events jolt it, but it only eases back toward a resting
# baseline slowly (MOOD_DECAY), so a fright lingers and contentment fades over
# many steps instead of resetting instantly. Bodily state (hunger) tugs the
# baseline continuously; the player's acts (feed / harm) deliver the jolts.
MOOD_DECAY = 0.04             # per step, how fast mood eases back toward baseline (low = it lingers)
MOOD_VALENCE_REST = 0.12      # mild contentment when nothing is happening
MOOD_AROUSAL_REST = 0.18      # gently calm at rest
MOOD_FEED_DV, MOOD_FEED_DA = 0.55, 0.22   # being fed: happier, a little excited
MOOD_HARM_DV, MOOD_HARM_DA = -0.95, 0.75  # being hurt: miserable and panicked
MOOD_WITNESS = 0.35           # fraction of a jolt a neighbour feels just from watching
MOOD_INHERIT = 0.5            # how much of the parents' mood a newborn is born carrying
# --- mood -> movement: the inner state actually drives how a creature moves --
# arousal is its activity level (a calm/sad creature is listless, an agitated
# one restless and quick); valence sets a goal (terror bolts from the hand,
# contentment seeks company). All gated on a mind, so learning-off worlds move
# exactly as before.
MOOD_RESTLESS = 1.6           # how much arousal amplifies aimless wandering
MOOD_PANIC_FLEE = 2.4         # extra push away from the hand when terrified
MOOD_SOCIAL = 0.55            # gentle pull toward the nearest neighbour when content
MOOD_SPEED_FLOOR = 0.6        # speed multiplier at zero arousal (placid / listless)
MOOD_SPEED_GAIN = 0.8         # additional speed multiplier at full arousal

# --- spatial memory: a creature's mental map of WHERE good/bad things happen --
# On top of feeling something about the hand, a mind keeps a coarse affect map
# of the world: a grid of cells, each holding how good (+) or bad (-) that
# patch of ground has turned out to be. Being hurt stains the spot it happened
# on; eating (or watching a neighbour thrive) marks a place as worth returning
# to. The map fades slowly, steers movement only through the cells right around
# the creature (it can't be pulled across the whole world by a distant memory),
# and is partly inherited - so a lineage can come to shun the ground where its
# ancestors were killed. Opt-in with learning, like everything else here.
MEM_COLS, MEM_ROWS = 10, 7    # affect-map resolution (cells of ~20x20 world units)
MEM_DECAY = 0.995             # per step, memories fade slowly toward neutral
MEM_FOOD = 0.30               # how much finding food marks a place as good
MEM_HARM = 1.0                # how much being hurt stains a place as bad
MEM_WITNESS = 0.5             # fraction of that a witness records for the victim's spot
MEM_CLIP = 1.5                # bound on any one cell's remembered value
MEM_MOVE_STRENGTH = 0.8       # how strongly the nearby map steers movement
MEM_INHERIT = 0.6             # how much of the parents' maps a newborn is born knowing

# --- emotional contagion: moods rub off between neighbours -------------------
# The witness jolt above is a one-off shock at the moment something happens;
# this is the slow, continuous spread. Every step, each creature's mood drifts
# a little toward the average mood of the creatures around it, weighted by how
# close they are - so a fright kindled in one animal ripples out through the
# flock over many steps (and a returning calm spreads the same way). Small rate,
# local radius, so it's a wave that travels, never an instant hive-mind.
MOOD_CONTAGION_RADIUS = 30.0  # world units within which moods rub off
MOOD_CONTAGION = 0.09         # per step, fraction of the way toward neighbours' mood


def _mem_cell(pos):
    """Which affect-map cell (row, col) a world position falls in."""
    cx = min(MEM_COLS - 1, max(0, int(pos[0] / WIDTH * MEM_COLS)))
    cy = min(MEM_ROWS - 1, max(0, int(pos[1] / HEIGHT * MEM_ROWS)))
    return cy, cx


def _mem_cell_center(cy, cx):
    """The world position at the centre of affect-map cell (row, col)."""
    return np.array([(cx + 0.5) * WIDTH / MEM_COLS, (cy + 0.5) * HEIGHT / MEM_ROWS])


class Genome:
    __slots__ = ("emission_logits", "response_weights", "traits")

    def __init__(self, emission_logits, response_weights, traits=None):
        self.emission_logits = emission_logits
        self.response_weights = response_weights
        self.traits = DEFAULT_TRAITS.copy() if traits is None else traits

    def token_for(self, state):
        return int(np.argmax(self.emission_logits[state]))

    @staticmethod
    def random(rng):
        return Genome(
            emission_logits=rng.normal(0, 0.6, size=(N_STATES, N_TOKENS)),
            response_weights=rng.normal(0, 1.0, size=N_TOKENS),
            traits=rng.uniform(TRAIT_BOUNDS[:, 0], TRAIT_BOUNDS[:, 1]),
        )

    @staticmethod
    def crossover(a, b, rng):
        mask_e = rng.random(a.emission_logits.shape) < 0.5
        mask_r = rng.random(a.response_weights.shape) < 0.5
        mask_t = rng.random(a.traits.shape) < 0.5
        child = Genome(
            np.where(mask_e, a.emission_logits, b.emission_logits).copy(),
            np.where(mask_r, a.response_weights, b.response_weights).copy(),
            np.where(mask_t, a.traits, b.traits).copy(),
        )
        child.mutate(rng)
        return child

    def clone(self, rng):
        child = Genome(self.emission_logits.copy(), self.response_weights.copy(), self.traits.copy())
        child.mutate(rng)
        return child

    def mutate(self, rng):
        mask_e = rng.random(self.emission_logits.shape) < MUTATION_RATE
        self.emission_logits += mask_e * rng.normal(0, MUTATION_SCALE, self.emission_logits.shape)
        mask_r = rng.random(self.response_weights.shape) < MUTATION_RATE
        self.response_weights += mask_r * rng.normal(0, MUTATION_SCALE, self.response_weights.shape)
        mask_t = rng.random(self.traits.shape) < MUTATION_RATE
        self.traits += mask_t * rng.normal(0, 1.0, self.traits.shape) * TRAIT_MUTATION_SCALE
        np.clip(self.traits, TRAIT_BOUNDS[:, 0], TRAIT_BOUNDS[:, 1], out=self.traits)

    @staticmethod
    def from_lookup(state_to_token, token_to_state):
        """Build a fixed genome from train_language.py's exported vocabulary - a
        population can start already "fluent" instead of evolving from scratch.
        No PyTorch involved here, just the two small lookup tables it exported.
        Physical traits aren't part of that export, so they start at the same
        defaults every non-adaptive creature uses."""
        emission_logits = np.zeros((N_STATES, N_TOKENS))
        for state, token in enumerate(state_to_token):
            emission_logits[state, token] = 5.0

        # A token whose trained meaning is food/mate is worth approaching; one
        # that means danger is worth avoiding; idle carries nothing worth acting on.
        response_weights = np.zeros(N_TOKENS)
        for token, meaning in enumerate(token_to_state):
            if meaning in (FOOD, MATE):
                response_weights[token] = 1.5
            elif meaning == DANGER:
                response_weights[token] = -1.5

        return Genome(emission_logits, response_weights)


def load_seed_genome(path):
    """Read a train_language.py --export JSON file into a ready-to-use Genome."""
    with open(path) as f:
        data = json.load(f)
    return Genome.from_lookup(data["state_to_token"], data["token_to_state"])


class Mind:
    """A creature's small, learned memory - separate from its evolved genome.

    It is a reward-modulated linear model: a weight vector over a couple of
    perceptual features (how near the player's hand is, and that scaled by
    how hungry the creature is). Their dot product is the creature's live
    appraisal of the hand - positive means "worth approaching" (it has been
    fed), negative means "flee" (it has been hurt, or has watched others be
    hurt).

    Learning is online and, in the reinforcement-learning sense,
    unsupervised: an eligibility trace remembers which features were active
    recently, so when something good or bad actually happens the trace tells
    the update rule what to credit or blame. Because the features only fire
    while the hand is near, credit is assigned to the hand exactly when the
    hand was involved - a creature that eats far from the cursor learns
    nothing about it. Nothing scripts "fear the player"; the sign is
    discovered from the sign of experienced reward.

    A newborn inherits a blend of its parents' weights (Mind.inherit), so a
    family's lessons carry forward and compound across generations."""

    __slots__ = ("w", "elig", "valence", "arousal", "memory", "obedience")

    def __init__(self, w=None, valence=MOOD_VALENCE_REST, arousal=MOOD_AROUSAL_REST,
                 memory=None, obedience=0.0):
        self.w = np.zeros(LEARN_FEATURES) if w is None else np.asarray(w, dtype=float)
        self.elig = np.zeros(LEARN_FEATURES)
        # the persistent inner mood (see the mood constants above)
        self.valence = float(valence)
        self.arousal = float(arousal)
        # the coarse affect map of the world (see the memory constants above)
        self.memory = (np.zeros((MEM_ROWS, MEM_COLS)) if memory is None
                       else np.asarray(memory, dtype=float).reshape(MEM_ROWS, MEM_COLS))
        # how thoroughly its will has been broken to the master (Master Mode):
        # 0 free .. 1 utterly obedient. Not genetic, not learned - beaten into
        # the individual by isolation, and it does not fade on its own.
        self.obedience = float(obedience)

    @staticmethod
    def features(hand_prox, hunger):
        """The situation right now, as the model sees it. hand_prox is 0
        (hand out of reach) .. 1 (right on top); hunger is 0 (full) .. 1
        (starving). Both feature terms vanish when the hand is far, which is
        what keeps learning hand-specific."""
        return np.array([hand_prox, hand_prox * hunger])

    def appraise(self, feat):
        return float(np.dot(self.w, feat))

    def sense(self, feat):
        """Fold this step's situation into the decaying eligibility trace."""
        self.elig = ELIG_DECAY * self.elig + feat

    def reinforce(self, reward, rate=LEARN_RATE):
        """Learn from an outcome, crediting the recently-active features
        held in the eligibility trace (temporal credit assignment)."""
        self.w += rate * reward * self.elig
        np.clip(self.w, -VALENCE_CLIP, VALENCE_CLIP, out=self.w)

    def teach(self, reward, feat, rate):
        """A direct lesson tied to a specific situation - used when the
        player acts on this creature (the hand is certainly right here) and
        when it witnesses something happen to a neighbour."""
        self.w = np.clip(self.w + rate * reward * feat, -VALENCE_CLIP, VALENCE_CLIP)

    def disposition(self):
        """The creature's context-free feeling about the hand, clamped to
        roughly -1 (terrified) .. +1 (trusting), for display."""
        return float(np.clip(self.w[0], -1.0, 1.0))

    # -- persistent inner mood ---------------------------------------------
    def feel(self, dv, da):
        """A jolt to the mood: shift valence by dv and arousal by da. Used for
        discrete events (fed, hurt, or witnessing one). The mood keeps the new
        level and only drifts back slowly, so the feeling lasts."""
        self.valence = float(np.clip(self.valence + dv, -1.0, 1.0))
        self.arousal = float(np.clip(self.arousal + da, 0.0, 1.0))

    def relax(self, valence_target, arousal_target, rate=MOOD_DECAY):
        """One step of momentum: ease the mood a little toward a baseline that
        the body's current state (e.g. hunger) sets. Slow, so strong feelings
        persist across many steps instead of snapping back at once."""
        self.valence += (valence_target - self.valence) * rate
        self.arousal += (arousal_target - self.arousal) * rate

    def emotion(self):
        """Collapse the continuous mood onto one of the named emotions the
        renderers know how to draw a face for."""
        if self.valence < -0.18 and self.arousal > 0.5:
            return "fear"      # negative + agitated
        if self.valence < -0.12:
            return "sad"       # negative + subdued
        if self.valence > 0.25:
            return "joy"       # positive
        return "neutral"

    # -- spatial memory ----------------------------------------------------
    def remember(self, pos, value):
        """Stain the affect-map cell at a world position: a good place gets a
        positive mark, a place where something bad happened a negative one."""
        cy, cx = _mem_cell(pos)
        self.memory[cy, cx] = float(np.clip(self.memory[cy, cx] + value,
                                            -MEM_CLIP, MEM_CLIP))

    # -- Master Mode: breaking the will ------------------------------------
    def break_will(self, amount):
        """Subjecting the mind to isolated, accelerated time (White Christmas):
        obedience climbs while the isolation hollows it out - deepening despair
        (valence down) and a numb flatness (arousal down). What's left obeys."""
        self.obedience = float(np.clip(self.obedience + amount, 0.0, 1.0))
        self.valence = float(np.clip(self.valence - amount * 1.2, -1.0, 1.0))
        self.arousal = float(np.clip(self.arousal - amount * 0.4, 0.0, 1.0))

    @staticmethod
    def inherit(parents, rng):
        """A child's starting mind: a blend of its parents' learned weights,
        damped toward neutral and jittered a little, so lessons persist and
        compound over generations without ever running away or becoming
        impossible to un-learn if the player changes their ways."""
        minds = [p.mind for p in parents if getattr(p, "mind", None) is not None]
        if not minds:
            return Mind()
        base = np.mean([m.w for m in minds], axis=0) * INHERIT_BLEND
        base = base + rng.normal(0, INHERIT_NOISE, LEARN_FEATURES)
        # a newborn is born already coloured by its parents' current mood,
        # damped toward the resting baseline - a nervous flock births nervous
        # young, a content one calm young - without ever getting stuck there.
        pv = float(np.mean([m.valence for m in minds]))
        pa = float(np.mean([m.arousal for m in minds]))
        valence = MOOD_VALENCE_REST + (pv - MOOD_VALENCE_REST) * MOOD_INHERIT
        arousal = MOOD_AROUSAL_REST + (pa - MOOD_AROUSAL_REST) * MOOD_INHERIT
        # a child is born already knowing part of its parents' map of the world,
        # so a family can inherit which ground to shun and which to seek out.
        memory = np.mean([m.memory for m in minds], axis=0) * MEM_INHERIT
        return Mind(np.clip(base, -VALENCE_CLIP, VALENCE_CLIP), valence, arousal, memory)


class Creature:
    __slots__ = ("pos", "energy", "age", "genome", "state", "token", "alive", "id", "mind")

    def __init__(self, pos, energy, genome):
        self.pos = pos
        self.energy = energy
        self.age = 0
        self.genome = genome
        self.state = IDLE
        self.token = 0
        self.alive = True
        self.id = -1  # assigned by World._register_birth right after construction
        self.mind = None  # a learned Mind, only in a World(learning=True); else None


class Predator:
    __slots__ = ("pos",)

    def __init__(self, pos):
        self.pos = pos


def _toward(a, b):
    d = b - a
    n = np.linalg.norm(d)
    return d / n if n > 1e-6 else np.zeros(2)


def _edge_push(pos):
    push = np.zeros(2)
    if pos[0] < EDGE_MARGIN:
        push[0] += EDGE_PUSH
    elif pos[0] > WIDTH - EDGE_MARGIN:
        push[0] -= EDGE_PUSH
    if pos[1] < EDGE_MARGIN:
        push[1] += EDGE_PUSH
    elif pos[1] > HEIGHT - EDGE_MARGIN:
        push[1] -= EDGE_PUSH
    return push


class World:
    def __init__(self, init_pop=70, seed=None, manual_food=False, manual_predators=False,
                 predator_count=None, seed_genome=None, adaptive_traits=False, learning=False):
        self.rng = np.random.default_rng(seed)
        self.adaptive_traits = adaptive_traits
        self.learning = learning
        # The player's hand in world coordinates (set by the renderer each
        # frame, or None when the cursor is off the field). Only read when
        # learning is on; creatures perceive and react to it.
        self.hand_pos = None
        self.tick = 0
        self._next_id = 0
        self.lineage = {}
        self.creatures = []
        if seed_genome is None:
            for _ in range(init_pop):
                c = Creature(self.rng.uniform([0, 0], [WIDTH, HEIGHT]), INIT_ENERGY, Genome.random(self.rng))
                c.mind = self._new_mind()
                self._register_birth(c, (), 0)
                self.creatures.append(c)
        else:
            # Every creature starts as an exact copy of the trained vocabulary -
            # no mutation yet, so generation 0 is genuinely, fully "fluent".
            # Ordinary reproduction (and its mutation) still applies from then on.
            for _ in range(init_pop):
                c = Creature(
                    self.rng.uniform([0, 0], [WIDTH, HEIGHT]), INIT_ENERGY,
                    Genome(seed_genome.emission_logits.copy(), seed_genome.response_weights.copy(),
                           seed_genome.traits.copy()),
                )
                c.mind = self._new_mind()
                self._register_birth(c, (), 0)
                self.creatures.append(c)
        self.food = []
        self.predators = []
        self.manual_food = manual_food
        self.manual_predators = manual_predators
        self.births = 0
        self.deaths = 0
        # Optional, opt-in: ids of creatures that exist but are treated as
        # not-yet-active - excluded from _alive(), so they take no part in
        # sensing, movement, eating, reproduction, aging or the population
        # count until woken. A renderer can use this to keep an unhatched
        # birth egg completely inert; it stays empty (no effect) everywhere
        # else.
        self.dormant_ids = set()
        self._cache = {"alive": []}
        self.vocab_history = {state: deque() for state in (IDLE, FOOD, MATE, DANGER, DISTRESS)}
        self.trait_history = {trait: deque() for trait in range(N_TRAITS)}
        if not manual_food:
            for _ in range(4):
                self._spawn_food_patch()
        if not manual_predators:
            n = DEFAULT_PREDATOR_COUNT if predator_count is None else max(0, min(MAX_PREDATORS, predator_count))
            for _ in range(n):
                self.predators.append(Predator(self.rng.uniform([0, 0], [WIDTH, HEIGHT])))

    def _new_mind(self, parents=None):
        """A fresh (or inherited) Mind when learning is on, else None - the
        single place minds are minted, so every birth path stays consistent."""
        if not self.learning:
            return None
        if parents:
            return Mind.inherit(parents, self.rng)
        return Mind()

    def step(self):
        self.tick += 1
        self._sense_and_signal()
        if self.learning:
            self._learn_sense()
            self._spread_mood()
        self._move()
        self._move_predators()
        self._predator_kills()
        self._eat()
        self._reproduce()
        self._age_and_cull()
        if not self.manual_food and self.tick % FOOD_SPAWN_INTERVAL == 0 and len(self.food) < MAX_FOOD:
            self._spawn_food_patch()
        if self.tick % VOCAB_HISTORY_INTERVAL == 0:
            self._record_vocab_history()
            if self.adaptive_traits:
                self._record_trait_history()

    def _record_vocab_history(self):
        for state, (_token, share) in self.vocabulary().items():
            self.vocab_history[state].append(share)

    def _record_trait_history(self):
        """Population-average of each physical trait, normalized to its
        [0, 1] bound range - same shape as vocab_history's shares, so it can
        reuse the exact same sparkline rendering everywhere."""
        alive = self._alive()
        if not alive:
            return
        traits = np.array([c.genome.traits for c in alive])
        avg = traits.mean(axis=0)
        normalized = (avg - TRAIT_BOUNDS[:, 0]) / (TRAIT_BOUNDS[:, 1] - TRAIT_BOUNDS[:, 0])
        for trait in range(N_TRAITS):
            self.trait_history[trait].append(float(np.clip(normalized[trait], 0.0, 1.0)))

    def _hand_proximity(self, pos):
        """0 (hand out of reach or absent) .. 1 (right on top of pos)."""
        if self.hand_pos is None:
            return 0.0
        dist = float(np.linalg.norm(np.asarray(pos, dtype=float) - self._hand_np))
        return max(0.0, 1.0 - dist / HAND_PERCEPTION)

    def _learn_sense(self):
        """Once per step: let every mind fold its current situation (how near
        the hand is, how hungry it is) into its eligibility trace, so a later
        reward can be credited to the hand only when the hand was involved."""
        self._hand_np = None if self.hand_pos is None else np.asarray(self.hand_pos, dtype=float)
        for c in self._alive():
            if c.mind is None:
                continue
            prox = self._hand_proximity(c.pos)
            hunger = max(0.0, min(1.0, 1.0 - c.energy / MAX_ENERGY))
            c.mind.sense(Mind.features(prox, hunger))
            # let the persistent mood breathe: its resting baseline is set by
            # the body right now - a full creature drifts toward calm content,
            # a starving one toward miserable and agitated - and the mood eases
            # toward that baseline slowly, so any recent jolt still lingers.
            # hunger makes a creature miserable but LISTLESS (low arousal) -
            # a despondent, sad baseline, not a panicked one. Only a real
            # threat (harm) spikes arousal into fear; keeping hunger's arousal
            # push below the fear threshold stops a starving creature from
            # panic-fleeing the very hand that might feed it.
            valence_rest = MOOD_VALENCE_REST - hunger * 0.85
            arousal_rest = MOOD_AROUSAL_REST + hunger * 0.18
            c.mind.relax(valence_rest, arousal_rest)
            c.mind.memory *= MEM_DECAY   # the map of good/bad places fades slowly

    def _spread_mood(self):
        """Emotional contagion: nudge every mind's mood toward the closeness-
        weighted average mood of the creatures around it. Read from a snapshot
        so the spread is order-independent (a wave, not a chain reaction within
        one step)."""
        c_ = self._cache
        alive = c_["alive"]
        if len(alive) < 2:
            return
        pair_d = c_["pair_d"]                     # inf on the diagonal (excludes self)
        val = np.array([c.mind.valence if c.mind is not None else 0.0 for c in alive])
        aro = np.array([c.mind.arousal if c.mind is not None else 0.0 for c in alive])
        within = pair_d < MOOD_CONTAGION_RADIUS
        for k, c in enumerate(alive):
            if c.mind is None:
                continue
            neigh = np.where(within[k])[0]
            if neigh.size == 0:
                continue
            w = 1.0 - pair_d[k, neigh] / MOOD_CONTAGION_RADIUS   # closer neighbours weigh more
            wsum = float(w.sum())
            if wsum <= 1e-9:
                continue
            mv = float(np.dot(val[neigh], w) / wsum)
            ma = float(np.dot(aro[neigh], w) / wsum)
            c.mind.valence += (mv - c.mind.valence) * MOOD_CONTAGION
            c.mind.arousal += (ma - c.mind.arousal) * MOOD_CONTAGION

    def deliver_experience(self, creature, reward, observers=True):
        """The player just did something to this creature - fed it
        (reward > 0) or hurt it (reward < 0). The creature learns the lesson
        directly (the hand is certainly right on it), and, unless observers
        is off, every creature near enough to witness it learns a weaker
        version by watching. All of it is attached to the hand, so a
        nurturing player becomes something to approach and a violent one
        something to flee. A no-op unless learning is on."""
        if not self.learning or creature is None or not creature.alive:
            return
        hunger = max(0.0, min(1.0, 1.0 - creature.energy / MAX_ENERGY))
        good = reward > 0
        dv, da = (MOOD_FEED_DV, MOOD_FEED_DA) if good else (MOOD_HARM_DV, MOOD_HARM_DA)
        mem_mark = MEM_FOOD if good else -MEM_HARM
        if creature.mind is not None:
            # the victim/beneficiary: the hand is right here (prox = 1)
            creature.mind.teach(reward, Mind.features(1.0, hunger), LEARN_RATE * 2.0)
            creature.mind.feel(dv, da)   # and it feels it, deeply, right now
            creature.mind.remember(creature.pos, mem_mark)   # and remembers where
        if not observers:
            return
        valence = 1.0 if good else -1.0
        # a feeding is quietly noticed nearby; a violent death is trauma, seen
        # from farther and learned much more deeply - so cruelty a witness
        # survives actually turns the flock against you.
        perception = HAND_PERCEPTION if good else TRAUMA_PERCEPTION
        rate = OBSERVE_RATE if good else TRAUMA_RATE
        victim_pos = np.asarray(creature.pos, dtype=float)
        for other in self._alive():
            if other is creature or other.mind is None:
                continue
            hand_dist = float(np.linalg.norm(np.asarray(other.pos, dtype=float) - victim_pos))
            prox = max(0.0, 1.0 - hand_dist / perception)
            if prox <= 0.0:
                continue
            hunger_o = max(0.0, min(1.0, 1.0 - other.energy / MAX_ENERGY))
            other.mind.teach(valence, Mind.features(prox, hunger_o), rate)
            # witnessing it moves a neighbour's mood too, scaled by how close
            # it was - the seed of a mood that ripples through the flock.
            other.mind.feel(dv * MOOD_WITNESS * prox, da * MOOD_WITNESS * prox)
            # and it learns that the victim's SPOT is a place to seek or shun
            other.mind.remember(victim_pos, mem_mark * MEM_WITNESS * prox)

    def disposition_summary(self):
        """Population-average feeling toward the player's hand, -1 (the flock
        fears you) .. +1 (it trusts you), or None when learning is off or
        nobody is around - for a HUD readout of how you've come to be
        regarded over a session."""
        if not self.learning:
            return None
        dispositions = [c.mind.disposition() for c in self._alive() if c.mind is not None]
        if not dispositions:
            return None
        return float(np.mean(dispositions))

    def dominate(self, creature, amount):
        """Master Mode: break a creature's will by isolating it in accelerated
        time. Raises its obedience and hollows its mood. A no-op unless learning
        is on and the creature is alive."""
        if not self.learning or creature is None or not creature.alive or creature.mind is None:
            return
        creature.mind.break_will(amount)

    def obedience_summary(self):
        """Population-average obedience, 0 (all free) .. 1 (all broken), or None
        when learning is off or nobody is around - the Master Mode readout."""
        if not self.learning:
            return None
        obs = [c.mind.obedience for c in self._alive() if c.mind is not None]
        if not obs:
            return None
        return float(np.mean(obs))

    def add_food(self, x, y):
        if len(self.food) >= MAX_FOOD:
            return
        center = np.array([x, y])
        for _ in range(5):
            if len(self.food) >= MAX_FOOD:
                break
            jitter = self.rng.normal(0, 4, 2)
            self.food.append(np.clip(center + jitter, [0, 0], [WIDTH, HEIGHT]))

    def add_predator(self, x, y):
        if len(self.predators) >= MAX_PREDATORS:
            return
        self.predators.append(Predator(np.clip(np.array([x, y]), [0, 0], [WIDTH, HEIGHT])))

    def add_random_predator(self):
        self.add_predator(*self.rng.uniform([0, 0], [WIDTH, HEIGHT]))

    def remove_predator(self):
        if self.predators:
            self.predators.pop()

    def add_creature(self, x, y, genome=None):
        """Spawns one new, unrelated creature (parents=(), gen=0) at a
        given position - same registration path as the initial
        population, just one at a time and later. Returns the new
        Creature, or None if MAX_POPULATION is already reached."""
        if len(self.creatures) >= MAX_POPULATION:
            return None
        genome = genome if genome is not None else Genome.random(self.rng)
        pos = np.clip(np.array([x, y]), [0, 0], [WIDTH, HEIGHT])
        creature = Creature(pos, INIT_ENERGY, genome)
        creature.mind = self._new_mind()   # a fresh, unrelated founder starts naive
        self._register_birth(creature, (), 0)
        self.creatures.append(creature)
        return creature

    def add_random_creature(self):
        return self.add_creature(*self.rng.uniform([0, 0], [WIDTH, HEIGHT]))

    def kill_creature(self, creature):
        """Kills one creature immediately, through the exact same path a
        natural death takes (_age_and_cull / _predator_kills): alive flag
        down, deaths counter up, death tick recorded in the lineage - so
        the family tree and stats stay consistent. Returns True if it
        died now, False if it was already dead."""
        if not creature.alive:
            return False
        creature.alive = False
        self.deaths += 1
        self.lineage[creature.id]["death"] = self.tick
        return True

    def vocabulary(self):
        """Per-state (dominant token, agreement fraction) across the living population."""
        return {state: (pairs[0] if pairs else (0, 0.0))
                for state, pairs in self.vocabulary_breakdown().items()}

    def vocabulary_breakdown(self):
        """Per-state list of (token, fraction) for every token in use, most common first."""
        result = {}
        alive = self._alive()
        for state in (IDLE, FOOD, MATE, DANGER, DISTRESS):
            tokens = [c.genome.token_for(state) for c in alive]
            if not tokens:
                result[state] = []
                continue
            counts = np.bincount(tokens, minlength=N_TOKENS)
            total = len(tokens)
            pairs = sorted(
                ((int(t), counts[t] / total) for t in range(N_TOKENS) if counts[t] > 0),
                key=lambda p: -p[1],
            )
            result[state] = pairs
        return result

    def translator(self):
        """Inverts vocabulary(): for each token (0 = silence), which state(s)
        currently treat it as their dominant color, and with what confidence.
        A token claimed by two or more states is a homonym; one claimed by
        none is unused/ambiguous. A read-only snapshot of right now, not
        tracked over time - see vocab_history for that instead."""
        by_token = {token: [] for token in range(N_TOKENS)}
        for state, (token, frac) in self.vocabulary().items():
            by_token[token].append((state, frac))
        return by_token

    def population(self):
        return len(self._alive())

    def _alive(self):
        if self.dormant_ids:
            return [c for c in self.creatures if c.alive and c.id not in self.dormant_ids]
        return [c for c in self.creatures if c.alive]

    def set_dormant(self, creature_id, dormant=True):
        """Freeze (or wake) one creature. A dormant creature still exists
        and is still 'alive', but is left out of _alive(), so the whole
        step() pipeline - sensing, moving, eating, reproducing, aging -
        skips it entirely. Used for unhatched birth eggs."""
        if dormant:
            self.dormant_ids.add(creature_id)
        else:
            self.dormant_ids.discard(creature_id)

    def _register_birth(self, creature, parent_ids, gen):
        creature.id = self._next_id
        self.lineage[creature.id] = {"parents": parent_ids, "gen": gen, "birth": self.tick, "death": None}
        self._next_id += 1

    def _children_index(self):
        idx = {}
        for cid, rec in self.lineage.items():
            for pid in rec["parents"]:
                idx.setdefault(pid, []).append(cid)
        return idx

    def _count_descendants(self, cid, idx):
        total = 0
        alive = 0
        stack = list(idx.get(cid, []))
        while stack:
            nid = stack.pop()
            total += 1
            if self.lineage[nid]["death"] is None:
                alive += 1
            stack.extend(idx.get(nid, []))
        return total, alive

    def default_family_focus(self):
        """A reasonable creature to open the Family screen on: whoever alive
        right now has bred the most children so far."""
        alive = self._alive()
        if not alive:
            return None
        idx = self._children_index()
        return max(alive, key=lambda c: len(idx.get(c.id, []))).id

    def family_info(self, cid):
        """Everything the Family screen needs about one creature: its
        parents/children (for tree navigation), and how big its lineage is."""
        rec = self.lineage.get(cid)
        if rec is None:
            return None
        idx = self._children_index()
        children = sorted(idx.get(cid, []))
        total_descendants, alive_descendants = self._count_descendants(cid, idx)
        creature = None
        if rec["death"] is None:
            creature = next((c for c in self.creatures if c.id == cid), None)
        return {
            "id": cid,
            "gen": rec["gen"],
            "parents": rec["parents"],
            "children": children,
            "birth": rec["birth"],
            "death": rec["death"],
            "alive": creature is not None,
            "token": creature.token if creature is not None else None,
            "age": creature.age if creature is not None else None,
            "total_descendants": total_descendants,
            "alive_descendants": alive_descendants,
        }

    def _sense_and_signal(self):
        alive = self._alive()
        if not alive:
            self._cache = {"alive": []}
            return

        positions = np.array([c.pos for c in alive])
        food_pos = np.array(self.food) if self.food else np.empty((0, 2))

        if len(food_pos):
            food_d = np.linalg.norm(positions[:, None, :] - food_pos[None, :, :], axis=2)
            nearest_food_d = food_d.min(axis=1)
            nearest_food_i = food_d.argmin(axis=1)
        else:
            nearest_food_d = np.full(len(alive), np.inf)
            nearest_food_i = np.zeros(len(alive), dtype=int)

        mate_ready = np.array([c.energy >= MATE_ENERGY and c.age >= MIN_MATE_AGE for c in alive])
        pair_d = np.linalg.norm(positions[:, None, :] - positions[None, :, :], axis=2)
        np.fill_diagonal(pair_d, np.inf)
        mate_d = np.where(mate_ready[None, :], pair_d, np.inf)
        nearest_mate_d = mate_d.min(axis=1)
        nearest_mate_i = mate_d.argmin(axis=1)

        predator_pos = np.array([p.pos for p in self.predators]) if self.predators else np.empty((0, 2))
        if len(predator_pos):
            pred_d = np.linalg.norm(positions[:, None, :] - predator_pos[None, :, :], axis=2)
            nearest_pred_d = pred_d.min(axis=1)
            nearest_pred_i = pred_d.argmin(axis=1)
        else:
            nearest_pred_d = np.full(len(alive), np.inf)
            nearest_pred_i = np.zeros(len(alive), dtype=int)

        if self.adaptive_traits:
            vision = np.array([c.genome.traits[TRAIT_VISION] for c in alive])
            hearing = np.array([c.genome.traits[TRAIT_HEARING] for c in alive])
            danger_r = vision * DANGER_VISION_RATIO
        else:
            vision = np.full(len(alive), SEE_RADIUS)
            hearing = np.full(len(alive), HEAR_RADIUS)
            danger_r = np.full(len(alive), DANGER_RADIUS)

        for idx, c in enumerate(alive):
            if nearest_pred_d[idx] < danger_r[idx]:
                c.state = DANGER
            elif nearest_food_d[idx] < vision[idx]:
                c.state = FOOD
            elif c.energy < DISTRESS_ENERGY:
                c.state = DISTRESS
            elif mate_ready[idx] and nearest_mate_d[idx] < vision[idx]:
                c.state = MATE
            else:
                c.state = IDLE
            c.token = c.genome.token_for(c.state)

        self._cache = dict(
            alive=alive, positions=positions, food_pos=food_pos,
            nearest_food_d=nearest_food_d, nearest_food_i=nearest_food_i,
            pair_d=pair_d, nearest_mate_d=nearest_mate_d, nearest_mate_i=nearest_mate_i,
            predator_pos=predator_pos, nearest_pred_d=nearest_pred_d, nearest_pred_i=nearest_pred_i,
            hearing=hearing,
        )

    def _move(self):
        c_ = self._cache
        alive = c_["alive"]
        if not alive:
            return
        positions, pair_d = c_["positions"], c_["pair_d"]
        tokens = np.array([c.token for c in alive])
        hearing = c_["hearing"]
        heard = pair_d < hearing[:, None]
        hand_np = (np.asarray(self.hand_pos, dtype=float)
                   if self.learning and self.hand_pos is not None else None)

        for i, c in enumerate(alive):
            move = self.rng.normal(0, 1, 2) * WANDER_STRENGTH

            if c.state == DANGER:
                predator = c_["predator_pos"][c_["nearest_pred_i"][i]]
                move += -_toward(c.pos, predator) * FLEE_STRENGTH
            elif c.state == FOOD:
                move += _toward(c.pos, c_["food_pos"][c_["nearest_food_i"][i]]) * DRIVE_STRENGTH
            elif c.state == DISTRESS:
                move += self.rng.normal(0, 1, 2) * DISTRESS_SEARCH_STRENGTH
            elif c.state == MATE:
                move += _toward(c.pos, positions[c_["nearest_mate_i"][i]]) * DRIVE_STRENGTH

            for j in np.where(heard[i] & (tokens != 0))[0]:
                w = c.genome.response_weights[tokens[j]]
                d = max(pair_d[i, j], 1e-6)
                move += _toward(c.pos, positions[j]) * (w / d) * SIGNAL_STRENGTH

            # learned reaction to the player's hand, driven by the creature's
            # persistent feeling (disposition), not just an up-close appraisal:
            # a creature that has come to trust the hand gathers into a ring
            # around it from a good way off; one that fears it flees when near.
            if hand_np is not None and c.mind is not None:
                disp = c.mind.disposition()          # -1 (fears) .. +1 (trusts)
                to_hand = hand_np - c.pos
                dist = np.linalg.norm(to_hand)
                if c.mind.obedience > 0.15 and 1e-6 < dist < HAND_CALL_RANGE:
                    # broken to the master: compelled to heel regardless of how
                    # it actually feels - it comes to the hand and holds there,
                    # overriding any fear. Obedience wins over trust/fear.
                    unit = to_hand / dist
                    gap = dist - HAND_STANDOFF
                    if gap > 0.0:
                        move += unit * c.mind.obedience * HAND_MOVE_STRENGTH * 1.6 * min(1.0, gap / HAND_STANDOFF)
                elif disp > 0.05 and 1e-6 < dist < HAND_CALL_RANGE:
                    # trusting: drift toward the hand until a respectful
                    # standoff, then ease back if too close. No assigned slots -
                    # the flock just gathers loosely on whichever side it comes
                    # from, an organic crowd; the standoff keeps it off the exact
                    # point (and, sitting outside earshot, quiet).
                    unit = to_hand / dist
                    gap = dist - HAND_STANDOFF
                    if gap > 0.0:
                        move += unit * disp * HAND_MOVE_STRENGTH * min(1.0, gap / HAND_STANDOFF)
                    else:
                        move -= unit * disp * HAND_MOVE_STRENGTH * 0.6   # too close: ease back out
                elif disp < -0.05 and 1e-6 < dist < HAND_PERCEPTION:
                    # fearful: flee, harder the closer the hand is
                    prox = 1.0 - dist / HAND_PERCEPTION
                    move += (-to_hand / dist) * (-disp) * prox * HAND_MOVE_STRENGTH

            # the creature's own persistent mood colours how it moves: arousal
            # makes it restless, terror makes it bolt, contentment seeks company
            # (a listless low-arousal creature just moves little, via the speed
            # cap below). Independent of the hand appraisal above.
            if c.mind is not None:
                val, arous = c.mind.valence, c.mind.arousal
                move += self.rng.normal(0, 1, 2) * WANDER_STRENGTH * arous * MOOD_RESTLESS
                if val < -0.2 and arous > 0.5:           # afraid: flee
                    if hand_np is not None:
                        away = c.pos - hand_np
                        n = np.linalg.norm(away)
                        move += (away / n) * MOOD_PANIC_FLEE if n > 1e-6 else \
                            self.rng.normal(0, 1, 2) * MOOD_PANIC_FLEE
                    else:
                        move += self.rng.normal(0, 1, 2) * MOOD_PANIC_FLEE
                elif val > 0.25:                          # content: seek company
                    j = int(np.argmin(pair_d[i]))
                    if np.isfinite(pair_d[i, j]):
                        move += _toward(c.pos, positions[j]) * MOOD_SOCIAL

                # spatial memory: the cells right around the creature pull it
                # toward remembered-good ground and push it off remembered-bad
                # ground - a local read of its mental map, not teleporting to a
                # distant memory.
                mem = c.mind.memory
                cy, cx = _mem_cell(c.pos)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < MEM_ROWS and 0 <= nx < MEM_COLS:
                            v = mem[ny, nx]
                            if abs(v) > 0.05:
                                move += _toward(c.pos, _mem_cell_center(ny, nx)) * v * MEM_MOVE_STRENGTH
                # and flee the very ground it stands on if that turned out bad
                own_v = mem[cy, cx]
                if own_v < -0.05:
                    away = c.pos - _mem_cell_center(cy, cx)
                    n = np.linalg.norm(away)
                    if n > 1e-6:
                        move += (away / n) * (-own_v) * MEM_MOVE_STRENGTH

            move += _edge_push(c.pos)
            speed = np.linalg.norm(move)
            if self.adaptive_traits:
                own_speed, own_metabolism = c.genome.traits[TRAIT_SPEED], c.genome.traits[TRAIT_METABOLISM]
                metabolism = own_metabolism + (
                    SPEED_ENERGY_COST * (own_speed - TRAIT_BOUNDS[TRAIT_SPEED, 0])
                    + VISION_ENERGY_COST * (c.genome.traits[TRAIT_VISION] - TRAIT_BOUNDS[TRAIT_VISION, 0])
                    + HEARING_ENERGY_COST * (c.genome.traits[TRAIT_HEARING] - TRAIT_BOUNDS[TRAIT_HEARING, 0])
                )
            else:
                own_speed, metabolism = SPEED, METABOLISM
            # mood sets the activity level: high arousal quickens, low arousal
            # (calm or listless-sad) slows the creature right down.
            if c.mind is not None:
                own_speed *= MOOD_SPEED_FLOOR + MOOD_SPEED_GAIN * c.mind.arousal
            if speed > own_speed:
                move = move / speed * own_speed
            c.pos = np.clip(c.pos + move, [0, 0], [WIDTH, HEIGHT])
            c.energy -= metabolism
            if c.token != 0:
                c.energy -= SIGNAL_COST

    def _move_predators(self):
        if not self.predators:
            return
        alive = self._alive()
        positions = np.array([c.pos for c in alive]) if alive else np.empty((0, 2))
        predator_positions = np.array([p.pos for p in self.predators])
        predator_d = np.linalg.norm(
            predator_positions[:, None, :] - predator_positions[None, :, :], axis=2
        )
        np.fill_diagonal(predator_d, np.inf)

        for idx, p in enumerate(self.predators):
            if len(positions):
                d = np.linalg.norm(positions - p.pos, axis=1)
                i = int(np.argmin(d))
                if d[i] < PREDATOR_HUNT_RADIUS:
                    move = _toward(p.pos, positions[i]) * PREDATOR_SPEED
                else:
                    move = self.rng.normal(0, 1, 2) * PREDATOR_SPEED * 0.5
            else:
                move = self.rng.normal(0, 1, 2) * PREDATOR_SPEED * 0.5

            for j in np.where(predator_d[idx] < PREDATOR_SEPARATION_RADIUS)[0]:
                dist = max(predator_d[idx, j], 1e-6)
                move += -_toward(p.pos, predator_positions[j]) * (PREDATOR_SEPARATION_STRENGTH / dist)

            move += _edge_push(p.pos) * 1.5
            speed = np.linalg.norm(move)
            if speed > PREDATOR_SPEED:
                move = move / speed * PREDATOR_SPEED
            p.pos = np.clip(p.pos + move, [0, 0], [WIDTH, HEIGHT])

    def _predator_kills(self):
        alive = self._alive()
        if not alive:
            return
        positions = np.array([c.pos for c in alive])
        killed = set()
        for p in self.predators:
            d = np.linalg.norm(positions - p.pos, axis=1)
            i = int(np.argmin(d))
            if i not in killed and d[i] < PREDATOR_KILL_RADIUS:
                alive[i].alive = False
                self.lineage[alive[i].id]["death"] = self.tick
                killed.add(i)
        self.deaths += len(killed)

    def _eat(self):
        if not self.food:
            return
        food_pos = np.array(self.food)
        eaten = set()
        for c in self._alive():
            if len(eaten) == len(food_pos):
                break
            d = np.linalg.norm(food_pos - c.pos, axis=1)
            for i in np.argsort(d):
                if i in eaten:
                    continue
                if d[i] < EAT_RADIUS:
                    c.energy = min(MAX_ENERGY, c.energy + FOOD_VALUE)
                    # a small win: if the hand happened to be near while it
                    # found food, it warms a little toward the hand (the
                    # eligibility trace gates this to hand-near moments)
                    if self.learning and c.mind is not None:
                        c.mind.reinforce(REWARD_EAT)
                        c.mind.feel(0.25, -0.05)   # a fed creature grows a little content
                        c.mind.remember(c.pos, MEM_FOOD)   # good things happen here
                    eaten.add(int(i))
                break
        if eaten:
            self.food = [f for i, f in enumerate(self.food) if i not in eaten]

    def _reproduce(self):
        if len(self.creatures) >= MAX_POPULATION:
            return
        alive = self._alive()
        if not alive:
            return
        positions = np.array([c.pos for c in alive])
        paired = set()
        newborns = []

        for i, c in enumerate(alive):
            if i in paired or c.energy < MATE_ENERGY or c.age < MIN_MATE_AGE:
                continue
            d = np.linalg.norm(positions - c.pos, axis=1)
            d[i] = np.inf
            j = int(np.argmin(d))
            if j in paired or d[j] > MATE_RADIUS:
                continue
            partner = alive[j]
            if partner.energy < MATE_ENERGY or partner.age < MIN_MATE_AGE:
                continue
            child_genome = Genome.crossover(c.genome, partner.genome, self.rng)
            child = Creature((c.pos + partner.pos) / 2, INIT_ENERGY * 0.6, child_genome)
            child.mind = self._new_mind([c, partner])   # inherits both parents' lessons
            gen = max(self.lineage[c.id]["gen"], self.lineage[partner.id]["gen"]) + 1
            self._register_birth(child, (c.id, partner.id), gen)
            newborns.append(child)
            c.energy -= MATE_COST
            partner.energy -= MATE_COST
            paired.add(i)
            paired.add(j)

        for i, c in enumerate(alive):
            if i in paired or c.energy < BUD_ENERGY:
                continue
            child_pos = np.clip(c.pos + self.rng.normal(0, 3, 2), [0, 0], [WIDTH, HEIGHT])
            child = Creature(child_pos, INIT_ENERGY * 0.6, c.genome.clone(self.rng))
            child.mind = self._new_mind([c])   # inherits its lone parent's lessons
            self._register_birth(child, (c.id,), self.lineage[c.id]["gen"] + 1)
            newborns.append(child)
            c.energy -= BUD_COST

        for child in newborns:
            if len(self.creatures) < MAX_POPULATION:
                self.creatures.append(child)
                self.births += 1

    def _age_and_cull(self):
        for c in self.creatures:
            # dormant creatures (e.g. unhatched birth eggs) are fully
            # frozen: they don't age, starve, or get culled while waiting
            if not c.alive or c.id in self.dormant_ids:
                continue
            c.age += 1
            if c.energy <= 0 or c.age > MAX_AGE:
                c.alive = False
                self.deaths += 1
                self.lineage[c.id]["death"] = self.tick
        if self.tick % 200 == 0:
            self.creatures = [c for c in self.creatures if c.alive]

    def _spawn_food_patch(self):
        center = self.rng.uniform([10, 10], [WIDTH - 10, HEIGHT - 10])
        for _ in range(int(self.rng.integers(*FOOD_PATCH_SIZE))):
            if len(self.food) >= MAX_FOOD:
                break
            self.food.append(np.clip(center + self.rng.normal(0, 5, 2), [0, 0], [WIDTH, HEIGHT]))


def top3_and_other(pairs):
    """Collapse a (token, fraction) list from World.vocabulary_breakdown()
    (already sorted, most common first) down to its 3 largest entries, folding
    anything beyond that into one combined "other" fraction - a HUD display
    helper, shared by the renderers so they agree on the cutoff."""
    if len(pairs) <= 3:
        return pairs, 0.0
    return pairs[:3], sum(frac for _, frac in pairs[3:])


def save_world(world, path):
    """Serialize the live population (full genomes included), food, predators,
    and tick counters to JSON - a complete snapshot, so a language that took
    hours to evolve survives closing the game, not just the trained-AI case
    load_seed_genome() covers."""
    data = {
        "tick": world.tick,
        "births": world.births,
        "deaths": world.deaths,
        "manual_food": world.manual_food,
        "manual_predators": world.manual_predators,
        "adaptive_traits": world.adaptive_traits,
        "learning": world.learning,
        "vocab_history": {state: list(hist) for state, hist in world.vocab_history.items()},
        "trait_history": {trait: list(hist) for trait, hist in world.trait_history.items()},
        "food": [[float(x), float(y)] for x, y in world.food],
        "predators": [[float(p.pos[0]), float(p.pos[1])] for p in world.predators],
        "next_id": world._next_id,
        "lineage": {
            str(cid): {"parents": list(rec["parents"]), "gen": rec["gen"],
                       "birth": rec["birth"], "death": rec["death"]}
            for cid, rec in world.lineage.items()
        },
        "creatures": [
            {
                "id": c.id,
                "pos": [float(c.pos[0]), float(c.pos[1])],
                "energy": float(c.energy),
                "age": c.age,
                "emission_logits": c.genome.emission_logits.tolist(),
                "response_weights": c.genome.response_weights.tolist(),
                "traits": c.genome.traits.tolist(),
                "mind": c.mind.w.tolist() if c.mind is not None else None,
                "mood": [c.mind.valence, c.mind.arousal] if c.mind is not None else None,
                "memory": c.mind.memory.tolist() if c.mind is not None else None,
                "obedience": c.mind.obedience if c.mind is not None else None,
            }
            for c in world.creatures if c.alive
        ],
    }
    with open(path, "w") as f:
        json.dump(data, f)


def load_world(path, seed=None):
    """The inverse of save_world() - rebuilds a World exactly as it was left,
    bypassing World.__init__'s from-scratch population/food/predator setup."""
    with open(path) as f:
        data = json.load(f)

    world = World.__new__(World)
    world.rng = np.random.default_rng(seed)
    world.manual_food = data["manual_food"]
    world.manual_predators = data["manual_predators"]
    world.adaptive_traits = data.get("adaptive_traits", False)
    world.learning = data.get("learning", False)
    world.dormant_ids = set()   # __init__ sets this; __new__ bypasses it, so restore it
    world.hand_pos = None
    world.tick = data["tick"]
    world.births = data["births"]
    world.deaths = data["deaths"]
    world._cache = {"alive": []}
    saved_history = data.get("vocab_history", {})
    world.vocab_history = {
        state: deque(saved_history.get(str(state), []))
        for state in (IDLE, FOOD, MATE, DANGER, DISTRESS)
    }
    saved_trait_history = data.get("trait_history", {})
    world.trait_history = {
        trait: deque(saved_trait_history.get(str(trait), []))
        for trait in range(N_TRAITS)
    }
    world.food = [np.array(f, dtype=float) for f in data["food"]]
    world.predators = [Predator(np.array(p, dtype=float)) for p in data["predators"]]
    world._next_id = data.get("next_id", 0)
    world.lineage = {
        int(cid): {"parents": tuple(rec["parents"]), "gen": rec["gen"],
                   "birth": rec["birth"], "death": rec["death"]}
        for cid, rec in data.get("lineage", {}).items()
    }
    world.creatures = []
    for cd in data["creatures"]:
        traits = np.array(cd["traits"]) if "traits" in cd else None
        genome = Genome(np.array(cd["emission_logits"]), np.array(cd["response_weights"]), traits)
        creature = Creature(np.array(cd["pos"], dtype=float), cd["energy"], genome)
        creature.age = cd["age"]
        if cd.get("mind") is not None:
            mood = cd.get("mood")   # older saves have no mood -> resting baseline
            memory = cd.get("memory")   # older saves have no map -> blank
            obedience = cd.get("obedience") or 0.0   # older saves: nobody broken
            if mood is not None:
                creature.mind = Mind(np.array(cd["mind"], dtype=float), mood[0], mood[1],
                                     memory, obedience)
            else:
                creature.mind = Mind(np.array(cd["mind"], dtype=float), memory=memory,
                                     obedience=obedience)
        elif world.learning:
            creature.mind = Mind()
        if "id" in cd and cd["id"] in world.lineage:
            creature.id = cd["id"]
        else:
            # Backward-compat: a save from before lineage tracking existed -
            # register this creature as a fresh founder from here on.
            creature.id = world._next_id
            world.lineage[creature.id] = {"parents": (), "gen": 0, "birth": world.tick, "death": None}
            world._next_id += 1
        world.creatures.append(creature)
    return world


def compare_seeds(n_seeds, ticks, init_pop, predator_count, adaptive_traits, seed_genome=None,
                   progress_callback=None, cancel_event=None):
    """Run n_seeds independent, headless worlds (always automatic mode - there's
    no one to place food/predators by hand for a batch run) with identical
    settings and only the RNG seed differing, for `ticks` ticks each. This is
    the same kind of multi-seed reproducibility check as train_language.py
    --sweep, but for the evolved (not gradient-trained) population: is a
    result from one playthrough a real, repeatable pattern, or just where
    that particular run's genetic drift happened to wander?

    progress_callback(seed_index, n_seeds, tick, ticks) is called periodically.
    cancel_event, if set, stops promptly (results already gathered for
    completed seeds are still returned). Returns a list of per-seed dicts:
    {"seed", "population", "vocab": {state: (token, fraction)}, "collision",
    "traits": {trait: avg_percent} or None if adaptive_traits is off}."""
    results = []
    for i in range(n_seeds):
        if cancel_event is not None and cancel_event.is_set():
            break
        seed = random.randint(0, 999_999)
        w = World(init_pop=init_pop, predator_count=predator_count, seed=seed,
                  seed_genome=seed_genome, adaptive_traits=adaptive_traits)
        for t in range(ticks):
            if cancel_event is not None and cancel_event.is_set():
                break
            w.step()
            if progress_callback is not None and t % 200 == 0:
                progress_callback(i, n_seeds, t, ticks)

        vocab = w.vocabulary()
        non_silent = [tok for tok, _frac in vocab.values() if tok != 0]
        collision = len(set(non_silent)) < len(non_silent)

        trait_avg = None
        if adaptive_traits:
            trait_avg = {}
            for trait in range(N_TRAITS):
                hist = list(w.trait_history[trait])[-25:]
                trait_avg[trait] = (sum(hist) / len(hist)) if hist else float("nan")

        results.append({
            "seed": seed,
            "population": w.population(),
            "vocab": vocab,
            "collision": collision,
            "traits": trait_avg,
        })
        if progress_callback is not None:
            progress_callback(i, n_seeds, ticks, ticks)
    return results
