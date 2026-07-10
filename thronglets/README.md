# Thronglets

A tiny artificial-life sandbox, inspired by the "Thronglets" from the Black
Mirror episode *Plaything* (S7E4) — little creatures that live inside a
simulation and end up with a language of their own.

This isn't a reproduction of anything from the show (that's fiction). It's a
real, if deliberately small, model of how a shared vocabulary can emerge from
**natural selection**, not machine learning:

- Each creature is born with a genome deciding which of 6 "tokens" (colors)
  it emits when it's **idle**, has **spotted food**, or wants to **mate** —
  and separately, how it reacts on hearing each token from a neighbor
  (move toward it, away from it, or ignore it).
- Nobody is told what a token should mean. Creatures whose signaling and
  listening genes happen to help them (and their offspring) find food or
  mates survive and reproduce more; genomes mutate a little at each birth.
- Over generations, population-wide agreement on "which token means food"
  and "which token means mate" climbs from chance level toward a real
  consensus — a small language being born purely from selection pressure.
- Signals also carry real information: a creature can *hear* a call from
  farther away than it can *see* food itself, so listening to others is
  genuinely useful, not just decorative.

## Run it

```bash
pip install -r requirements.txt
python main.py
```

Controls:

| Key         | Effect                                  |
|-------------|------------------------------------------|
| `SPACE`     | pause / resume                          |
| `UP` / `DOWN` | speed up / slow down the simulation   |
| `R`         | reset to a fresh world                  |
| left click  | drop a food patch where you click       |
| `ESC`       | quit                                    |

The HUD at the top shows, for each internal state (idle / food-call /
mate-call), the token most of the living population uses for it and what
fraction agree — that percentage is the thing to watch: it starts near
chance (~17%, since there are 6 tokens) and climbs as a convention emerges.

## Headless check

`simulation.py` has no pygame dependency, so the core can be run and tested
without a display:

```bash
python test_smoke.py
```

This runs several thousand ticks and asserts the population survives and
vocabulary agreement increases — i.e. that a language is actually emerging,
not just that the window doesn't crash.

## Where to take it next

The simulation core (`simulation.py`) and renderer (`main.py`) are split on
purpose so this is easy to extend:

- Predators / a danger state and alarm calls
- Evolvable traits beyond signaling (speed, senses, metabolism)
- A "translator" panel logging the emerging token → meaning dictionary over time
- Swapping the fixed 2D field for a proper toroidal world, or a richer
  pixel-art renderer for the creatures themselves
- Replacing rule-based genomes with small neural nets trained via multi-agent
  RL, closer to real emergent-communication research

## Honest caveat

This was built and tuned headlessly in a container without a display — the
mechanics are verified via `test_smoke.py` (population survives, vocabulary
converges across multiple random seeds), but the actual on-screen rendering
hasn't been eyeballed in a live window. Worth a quick visual check the first
time you run `main.py` locally.
