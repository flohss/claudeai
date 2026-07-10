"""Thronglets: a tiny artificial-life sandbox.

Simple creatures forage, mate, flee predators, and die on a 2D world. Each
one is born with a genome that decides which "token" it emits when it is
hungry, has spotted food, wants to mate, or senses a predator nearby, and how
it reacts to tokens it hears from others. There is no training loop and
nobody is told what the tokens should mean: genomes that happen to signal
and interpret usefully help their owners survive and reproduce more, so a
shared vocabulary - including alarm calls - can emerge purely from selection
over generations, the same basic idea (rules + evolution, not gradient
descent) behind classic artificial-life language experiments.

No pygame import here on purpose: this module is the simulation core and can
be driven headlessly (see test_smoke.py); main.py is the renderer.
"""

import numpy as np

WIDTH, HEIGHT = 200.0, 140.0

IDLE, FOOD, MATE, DANGER = 0, 1, 2, 3
N_STATES = 4
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

PREDATOR_COUNT = 3
PREDATOR_SPEED = 1.3
PREDATOR_HUNT_RADIUS = 70.0
PREDATOR_KILL_RADIUS = 3.0
DANGER_RADIUS = 22.0  # how far a creature can spot a predator directly

METABOLISM = 0.06
INIT_ENERGY = 60.0
MAX_ENERGY = 120.0
EAT_RADIUS = 4.0
FOOD_VALUE = 30.0

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


class Genome:
    __slots__ = ("emission_logits", "response_weights")

    def __init__(self, emission_logits, response_weights):
        self.emission_logits = emission_logits
        self.response_weights = response_weights

    def token_for(self, state):
        return int(np.argmax(self.emission_logits[state]))

    @staticmethod
    def random(rng):
        return Genome(
            emission_logits=rng.normal(0, 0.6, size=(N_STATES, N_TOKENS)),
            response_weights=rng.normal(0, 1.0, size=N_TOKENS),
        )

    @staticmethod
    def crossover(a, b, rng):
        mask_e = rng.random(a.emission_logits.shape) < 0.5
        mask_r = rng.random(a.response_weights.shape) < 0.5
        child = Genome(
            np.where(mask_e, a.emission_logits, b.emission_logits).copy(),
            np.where(mask_r, a.response_weights, b.response_weights).copy(),
        )
        child.mutate(rng)
        return child

    def clone(self, rng):
        child = Genome(self.emission_logits.copy(), self.response_weights.copy())
        child.mutate(rng)
        return child

    def mutate(self, rng):
        mask_e = rng.random(self.emission_logits.shape) < MUTATION_RATE
        self.emission_logits += mask_e * rng.normal(0, MUTATION_SCALE, self.emission_logits.shape)
        mask_r = rng.random(self.response_weights.shape) < MUTATION_RATE
        self.response_weights += mask_r * rng.normal(0, MUTATION_SCALE, self.response_weights.shape)


class Creature:
    __slots__ = ("pos", "energy", "age", "genome", "state", "token", "alive")

    def __init__(self, pos, energy, genome):
        self.pos = pos
        self.energy = energy
        self.age = 0
        self.genome = genome
        self.state = IDLE
        self.token = 0
        self.alive = True


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
    def __init__(self, init_pop=70, seed=None):
        self.rng = np.random.default_rng(seed)
        self.creatures = [
            Creature(self.rng.uniform([0, 0], [WIDTH, HEIGHT]), INIT_ENERGY, Genome.random(self.rng))
            for _ in range(init_pop)
        ]
        self.food = []
        self.predators = [
            Predator(self.rng.uniform([0, 0], [WIDTH, HEIGHT])) for _ in range(PREDATOR_COUNT)
        ]
        self.tick = 0
        self.births = 0
        self.deaths = 0
        self._cache = {"alive": []}
        for _ in range(4):
            self._spawn_food_patch()

    def step(self):
        self.tick += 1
        self._sense_and_signal()
        self._move()
        self._move_predators()
        self._predator_kills()
        self._eat()
        self._reproduce()
        self._age_and_cull()
        if self.tick % FOOD_SPAWN_INTERVAL == 0 and len(self.food) < MAX_FOOD:
            self._spawn_food_patch()

    def vocabulary(self):
        """Per-state (dominant token, agreement fraction) across the living population."""
        return {state: (pairs[0] if pairs else (0, 0.0))
                for state, pairs in self.vocabulary_breakdown().items()}

    def vocabulary_breakdown(self):
        """Per-state list of (token, fraction) for every token in use, most common first."""
        result = {}
        alive = self._alive()
        for state in (IDLE, FOOD, MATE, DANGER):
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

    def population(self):
        return len(self._alive())

    def _alive(self):
        return [c for c in self.creatures if c.alive]

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

        for idx, c in enumerate(alive):
            if nearest_pred_d[idx] < DANGER_RADIUS:
                c.state = DANGER
            elif nearest_food_d[idx] < SEE_RADIUS:
                c.state = FOOD
            elif mate_ready[idx] and nearest_mate_d[idx] < SEE_RADIUS:
                c.state = MATE
            else:
                c.state = IDLE
            c.token = c.genome.token_for(c.state)

        self._cache = dict(
            alive=alive, positions=positions, food_pos=food_pos,
            nearest_food_d=nearest_food_d, nearest_food_i=nearest_food_i,
            pair_d=pair_d, nearest_mate_d=nearest_mate_d, nearest_mate_i=nearest_mate_i,
            predator_pos=predator_pos, nearest_pred_d=nearest_pred_d, nearest_pred_i=nearest_pred_i,
        )

    def _move(self):
        c_ = self._cache
        alive = c_["alive"]
        if not alive:
            return
        positions, pair_d = c_["positions"], c_["pair_d"]
        tokens = np.array([c.token for c in alive])
        heard = pair_d < HEAR_RADIUS

        for i, c in enumerate(alive):
            move = self.rng.normal(0, 1, 2) * WANDER_STRENGTH

            if c.state == DANGER:
                predator = c_["predator_pos"][c_["nearest_pred_i"][i]]
                move += -_toward(c.pos, predator) * FLEE_STRENGTH
            elif c.state == FOOD:
                move += _toward(c.pos, c_["food_pos"][c_["nearest_food_i"][i]]) * DRIVE_STRENGTH
            elif c.state == MATE:
                move += _toward(c.pos, positions[c_["nearest_mate_i"][i]]) * DRIVE_STRENGTH

            for j in np.where(heard[i] & (tokens != 0))[0]:
                w = c.genome.response_weights[tokens[j]]
                d = max(pair_d[i, j], 1e-6)
                move += _toward(c.pos, positions[j]) * (w / d) * SIGNAL_STRENGTH

            move += _edge_push(c.pos)
            speed = np.linalg.norm(move)
            if speed > SPEED:
                move = move / speed * SPEED
            c.pos = np.clip(c.pos + move, [0, 0], [WIDTH, HEIGHT])
            c.energy -= METABOLISM

    def _move_predators(self):
        if not self.predators:
            return
        alive = self._alive()
        positions = np.array([c.pos for c in alive]) if alive else np.empty((0, 2))
        for p in self.predators:
            if len(positions):
                d = np.linalg.norm(positions - p.pos, axis=1)
                i = int(np.argmin(d))
                if d[i] < PREDATOR_HUNT_RADIUS:
                    move = _toward(p.pos, positions[i]) * PREDATOR_SPEED
                else:
                    move = self.rng.normal(0, 1, 2) * PREDATOR_SPEED * 0.5
            else:
                move = self.rng.normal(0, 1, 2) * PREDATOR_SPEED * 0.5
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
            newborns.append(Creature((c.pos + partner.pos) / 2, INIT_ENERGY * 0.6, child_genome))
            c.energy -= MATE_COST
            partner.energy -= MATE_COST
            paired.add(i)
            paired.add(j)

        for i, c in enumerate(alive):
            if i in paired or c.energy < BUD_ENERGY:
                continue
            child_pos = np.clip(c.pos + self.rng.normal(0, 3, 2), [0, 0], [WIDTH, HEIGHT])
            newborns.append(Creature(child_pos, INIT_ENERGY * 0.6, c.genome.clone(self.rng)))
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
        if self.tick % 200 == 0:
            self.creatures = [c for c in self.creatures if c.alive]

    def _spawn_food_patch(self):
        center = self.rng.uniform([10, 10], [WIDTH - 10, HEIGHT - 10])
        for _ in range(int(self.rng.integers(*FOOD_PATCH_SIZE))):
            if len(self.food) >= MAX_FOOD:
                break
            self.food.append(np.clip(center + self.rng.normal(0, 5, 2), [0, 0], [WIDTH, HEIGHT]))
