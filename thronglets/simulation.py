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


class Creature:
    __slots__ = ("pos", "energy", "age", "genome", "state", "token", "alive", "id")

    def __init__(self, pos, energy, genome):
        self.pos = pos
        self.energy = energy
        self.age = 0
        self.genome = genome
        self.state = IDLE
        self.token = 0
        self.alive = True
        self.id = -1  # assigned by World._register_birth right after construction


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
                 predator_count=None, seed_genome=None, adaptive_traits=False):
        self.rng = np.random.default_rng(seed)
        self.adaptive_traits = adaptive_traits
        self.tick = 0
        self._next_id = 0
        self.lineage = {}
        self.creatures = []
        if seed_genome is None:
            for _ in range(init_pop):
                c = Creature(self.rng.uniform([0, 0], [WIDTH, HEIGHT]), INIT_ENERGY, Genome.random(self.rng))
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
                self._register_birth(c, (), 0)
                self.creatures.append(c)
        self.food = []
        self.predators = []
        self.manual_food = manual_food
        self.manual_predators = manual_predators
        self.births = 0
        self.deaths = 0
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

    def step(self):
        self.tick += 1
        self._sense_and_signal()
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
        return [c for c in self.creatures if c.alive]

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
            self._register_birth(child, (c.id,), self.lineage[c.id]["gen"] + 1)
            newborns.append(child)
            c.energy -= BUD_COST

        for child in newborns:
            if len(self.creatures) < MAX_POPULATION:
                self.creatures.append(child)
                self.births += 1

    def _age_and_cull(self):
        for c in self.creatures:
            if not c.alive:
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
    helper, shared by main.py and main_tui.py so they agree on the cutoff."""
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
