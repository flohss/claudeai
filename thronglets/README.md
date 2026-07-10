# Thronglets

A tiny artificial-life sandbox, inspired by the "Thronglets" from the Black
Mirror episode *Plaything* (S7E4) — little creatures that live inside a
simulation and end up with a language of their own.

This isn't a reproduction of anything from the show (that's fiction). It's a
real, if deliberately small, model of how a shared vocabulary can emerge from
**natural selection**, not machine learning:

- Each creature is born with a genome deciding which of 6 "tokens" (colors)
  it emits when it's **idle**, has **spotted food**, wants to **mate**, or
  senses a nearby **predator** — and separately, how it reacts on hearing
  each token from a neighbor (move toward it, away from it, or ignore it).
- Predators roam the world and kill any creature they catch. They spawn in
  small waves over time (like food patches do), up to a cap, rather than all
  existing from tick 0 — so the world gets more dangerous the longer it runs.
  Spotting one puts a creature in a "danger" state, using the exact same
  signal/response machinery as food and mate calls — so an alarm call is
  just another word that can (or might not) emerge, not a special-cased
  mechanic.
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

There are two renderers, sharing the same simulation core:

- `main.py` — a pygame window (nicer, needs a display + pygame installed).
- `main_tui.py` — a plain terminal renderer using only the standard library's
  `curses` module + numpy. No GUI, no pygame, no X server. This is the one
  to use on **Termux**.

### Desktop (pygame)

```bash
pip install -r requirements.txt
python main.py
```

| Key         | Effect                                  |
|-------------|------------------------------------------|
| `SPACE`     | pause / resume                          |
| `UP` / `DOWN` | speed up / slow down the simulation   |
| `R`         | reset to a fresh world                  |
| left click  | drop a food patch where you click       |
| `ESC`       | quit                                    |

### Termux (Android)

Getting pygame's SDL2 dependencies to compile on Termux is a known pain
(needs the X11 repo, clang, `sdl2-dev`, and a running Termux:X11 session —
see [this issue](https://github.com/termux/termux-packages/issues/6233) if
you want to fight that battle). It's not needed here: `main_tui.py` draws
the whole simulation with colored characters directly in your terminal.

```bash
pkg update
pkg install python
pip install numpy
git clone <this repo's URL>   # or copy the thronglets/ folder over
cd claudeai/thronglets
python main_tui.py
```

Creatures show up as a colored `o` (colored by whatever token they're
currently signaling, white if silent), food as green `.`, predators as a red
`X`. Controls: `space`=pause, `f`=drop a food patch, `r`=reset, `+`/`-`=speed,
`q`=quit.
Works best in a wide/tall terminal — Termux's default font is fairly large,
so consider shrinking it (pinch to zoom, or Termux's font settings) to see
more of the world at once.

Both renderers show a HUD with, for each internal state (danger / food-call /
mate-call / idle), every token currently in use and what share of the living
population uses it — the numbers to watch are how fast a single token pulls
ahead of the pack (starting near chance, ~17%, since there are 6 tokens) and
whether it stays there.

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

- A cost to signaling (so "idle chatter" stops crowding out other meanings —
  see the homonymy problem below)
- Evolvable traits beyond signaling (speed, senses, metabolism)
- A "translator" panel logging the emerging token → meaning dictionary over time
- Swapping the fixed 2D field for a proper toroidal world, or a richer
  pixel-art renderer for the creatures themselves
- Replacing rule-based genomes with small neural nets trained via multi-agent
  RL, closer to real emergent-communication research

## A known quirk: homonyms

Each state's dominant token is decided independently, so nothing stops two
different states from converging on the *same* color by chance — a listener
who hears that color can't tell which meaning was intended. Since `idle` is
by far the most common state, this is usually what "wins" any collision,
drowning out the rarer, more useful signal in noise. It sometimes resolves
itself over further generations (a population can drift away from the
collision on its own), but nothing guarantees it will, or that it'll stay
resolved. A per-signal energy cost (see "where to take it next" above) would
make this self-correcting instead of a matter of luck.

## Honest caveat

This was built in a container without a display. The mechanics are verified
via `test_smoke.py` (population survives, vocabulary converges across
multiple random seeds), and `main_tui.py` was smoke-tested inside a real
pseudo-terminal (colors, HUD and moving creatures all render correctly).
`main.py`'s pygame window has *not* been eyeballed live — worth a quick
visual check the first time you run it locally.
