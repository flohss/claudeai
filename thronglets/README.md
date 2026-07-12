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
- Predators roam the world and kill any creature they catch. Spotting one
  puts a creature in a "danger" state, using the exact same signal/response
  machinery as food and mate calls — so an alarm call is just another word
  that can (or might not) emerge, not a special-cased mechanic. Each
  predator independently hunts whichever creature is nearest to it, and
  gently pushes away from other predators that get too close, so a pack
  doesn't collapse onto a single point when creatures cluster together.
- Food and predators can each be **automatic** (food spawns in periodic
  patches; predators all appear at once) or **manual** (nothing spawns on
  its own — you place every food patch and every predator yourself). You
  pick which, once, at startup in all three renderers — it's not something
  you toggle mid-run.
- Nobody is told what a token should mean. Creatures whose signaling and
  listening genes happen to help them (and their offspring) find food or
  mates survive and reproduce more; genomes mutate a little at each birth.
- Over generations, population-wide agreement on "which token means food"
  and "which token means mate" climbs from chance level toward a real
  consensus — a small language being born purely from selection pressure.
- Signals also carry real information: a creature can *hear* a call from
  farther away than it can *see* food itself, so listening to others is
  genuinely useful, not just decorative.
- All three renderers have an in-game notice (`h`/`H` in pygame and the
  terminal, a "Notice" button on the web page) explaining the mechanics
  above without leaving the running simulation.
- The whole interface is available in English or French, chosen once at
  startup in pygame/terminal, or toggled anytime (even mid-run) with the
  buttons at the top of the web page — including the state names
  themselves (`food-call`/`nourriture`, `mate-call`/`partenaire`,
  `alarm-call`/`alerte`, `idle`/`inactif`).

## Run it

There are three renderers, all sharing the same simulation core:

- `main.py` — a pygame window (nicer, needs a display + pygame installed).
- `main_tui.py` — a plain terminal renderer using only the standard library's
  `curses` module + numpy. No GUI, no pygame, no X server.
- `main_web.py` — a local web server (standard library only, no new
  dependency) with an HTML/canvas page you open in any browser. Works
  anywhere, including Termux.

### Desktop (pygame)

```bash
pip install -r requirements.txt
python main.py
```

The window opens fullscreen at the desktop's own resolution, stretching
the world to fill the screen exactly (no letterbox bars, whatever the
screen's aspect ratio) — `ESC` quits back to the desktop.

On launch you're asked to press `E`/`F` for English or French, then `A`
(automatic) or `M` (manual), then how many creatures to start with (type a
number, 1-220, `ENTER` to confirm or skip for the default of 70), then
`Y`/`N` (`O`/`N` in French) for whether to start already speaking a
pre-trained language (see below) — the world isn't created until all four
are answered, and they stick for the whole run (`R` resets using them
again, it doesn't ask a second time).

| Key           | Effect                                                       |
|---------------|----------------------------------------------------------------|
| `SPACE`       | pause / resume                                              |
| `UP` / `DOWN` | speed up / slow down the simulation                         |
| `R`           | reset to a fresh world (same mode, same predator count)      |
| `P`           | toggle what manual clicks place (food / predator)             |
| `[` / `]`     | remove / add a predator right now (also sets the reset count) |
| `H`           | in-game notice explaining the mechanics                      |
| left click    | place food (auto mode) or whatever's selected (manual mode)  |
| `ESC`         | quit                                                         |

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

On launch you're asked to press `E`/`F` for English or French, `A`
(automatic) or `M` (manual), then type how many creatures to start with
(1-220, `enter` to confirm or skip for the default of 70), then a yes/no
for whether to start already speaking a pre-trained language (see below,
`y`/`n` in English, `o`/`n` in French) — all four choices stick for the
whole run.

Creatures show up as a colored `o` (colored by whatever token they're
currently signaling, white if silent), food as green `.`, predators as a red
`X`. Controls: `space`=pause, `f`=drop a food patch (auto mode only),
`r`=reset, `+`/`-`=speed, `q`=quit, `p`=toggle food/predator placement,
`[`/`]`=remove/add a predator right now, `h`=in-game notice (paginated so it
fits any terminal height). There's no reliable mouse support in a terminal,
so manual mode uses a keyboard cursor instead: the arrow keys move it,
`enter` places whatever's currently selected.
Works best in a wide/tall terminal — Termux's default font is fairly large,
so consider shrinking it (pinch to zoom, or Termux's font settings) to see
more of the world at once.

### Web (any device with a browser)

No new dependency at all beyond numpy — the server is built on Python's
standard `http.server`, and the page is a single self-contained HTML file
served from memory.

```bash
python main_web.py                  # defaults to port 8765
python main_web.py --port 9000      # or pick your own port
```

Then open `http://localhost:8765` (swap in your port) in any browser on the
same device. Two small buttons at the top switch the whole page between
English and French at any time, including mid-run — this one isn't a
one-time choice like the others. The world doesn't exist yet — a start
screen asks you to pick automatic or manual mode, how many creatures to
start with (defaults to 70), and whether to activate a pre-trained
language (see below), and those three stick for the whole run (Reset
doesn't ask again). Once
started, the page polls the server a few times a second for a fresh
snapshot and draws it to a `<canvas>`; buttons
handle pause/reset/speed and what a manual placement adds. `+`/`- predateurs`
remove or add a predator immediately (also setting how many a reset will
use), tapping/clicking the world places food (auto mode) or whatever's
selected (manual mode), and a **Notice** button opens an explainer of the
mechanics without pausing the simulation underneath.

All three renderers show a HUD with, for each internal state (danger / food-call /
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

- A fifth state (e.g. "distress" - critically low energy with no food in
  sight, distinct from an ordinary food-call)
- Evolvable traits beyond signaling (speed, senses, metabolism)
- A "translator" panel logging the emerging token → meaning dictionary over time
- Swapping the fixed 2D field for a proper toroidal world, or a richer
  pixel-art renderer for the creatures themselves
- Feeding `train_language.py`'s per-agent diversity back in - it currently
  trains one shared Speaker/Listener pair (a "population" that's forced to
  agree with itself by construction); training several pairs with random
  pairing per episode would be a fairer comparison to the evolved version's
  actual population diversity

## The gradient-trained version: `train_language.py`

`simulation.py`'s colors emerge from blind evolutionary drift - nothing in
that model is actually optimizing for successful communication, only
surviving long enough to reproduce. `train_language.py` is a separate,
optional experiment that trains a real Speaker and Listener network with
backpropagation (Gumbel-Softmax for a differentiable discrete channel) to
directly minimize communication error, using the same 4-state/6-token
vocabulary for a fair comparison. It needs PyTorch:

```bash
pip install -r requirements-rl.txt
python train_language.py            # one run, with training progress printed
python train_language.py --sweep 10 # 10 independent seeds, collision-rate summary
```

This needs a genuinely heavy dependency not expected to work on Termux -
unlike the three renderers, it's a standalone script, and doesn't touch
`simulation.py` or the real-time game.

Training starts from scratch and forgets everything the moment the process
ends, unless you save it: a normal run automatically writes the trained
Speaker/Listener to `language_model.pt` (customize with `--checkpoint`).
To look at what a past run learned without retraining:

```bash
python train_language.py --load
```

**What actually happened when we ran it**, sampling states with the same
idle-heavy skew the real simulation has: 8 out of 10 seeds converged to a
perfect, collision-free code (100% listener accuracy) - a real difference
from the evolved version, where two states landing on the same color is
common and can persist indefinitely. But it wasn't 10/10: the 2 seeds that
still collided always merged the two *rarest* states (`mate-call` and
`alarm-call`, each well under 15% of samples) into one token, capping
accuracy at ~75%. With `--uniform` (equal frequency for all 4 states)
instead, it's 100% clean and near-instant every time.

So gradient descent doesn't magically solve the underlying issue, it just
attacks it far more directly and far more often: with a skewed class
distribution, the loss saved by correctly separating a rare class from
another rare class is tiny next to the loss from the frequent classes, so
occasionally the network settles for merging them anyway - a cleaner,
quantifiable version of the exact same "the frequent state drowns out the
rare one" dynamic behind the evolved version's homonymy, not an escape
from it.

## Feeding the trained language into the real game

`train_language.py` always finishes by writing `language_model.json` (see
`--export`) - a tiny, PyTorch-free lookup table (which token each state
maps to, and vice versa) baked out of the trained networks. All three
renderers can start a population already speaking that clean vocabulary,
with `--language`:

```bash
python main.py            --language language_model.json
python main_tui.py        --language language_model.json
python main_web.py        --language language_model.json
```

You don't have to remember that flag, though: if you launch any renderer
without `--language`, right after picking the mode and the starting
population you're asked "Activer le langage pre-entraine par IA ?" (`O`/`N`
in pygame and the terminal, a checkbox on the web start screen) - answering
yes loads `language_model.json` from the current folder automatically. If
that file doesn't exist yet (you haven't run `train_language.py` there),
you get a clear message and the game starts normally instead of crashing.

Every creature in generation 0 gets an exact copy of the trained genome
(a spiked emission for its trained token per state, and response weights
that approach food/mate tokens and flee the danger token) - no PyTorch is
imported by the game itself, only the small JSON file is read. The header
shows a `[trained vocabulary]` tag so it's obvious the population didn't
start from scratch. Ordinary mutation and reproduction still apply from
tick 1 onward, so this seeds the starting point, it doesn't freeze the
language in place.

**Does the clean vocabulary survive being handed to blind evolution?**
Running seeded worlds for 50,000 ticks (multiple seeds, well past several
hundred generations) shows agreement on all four states staying at or
extremely close to 100% the entire way - occasionally a single mutant
copy of a token shows up (99% instead of 100%) before being outcompeted
again, but no state ever drifts back into a real collision. Once
selection has nothing left to gain from reshuffling an already-optimal,
collision-free code, there's essentially no pressure pushing it away from
that optimum - mutation keeps proposing alternatives, they just keep
losing to the token that already works.

## A known quirk: homonyms

Each state's dominant token is decided independently, so nothing stops two
different states from converging on the *same* color by chance — a listener
who hears that color can't tell which meaning was intended. Since `idle` is
by far the most common state, this is usually what "wins" any collision,
drowning out the rarer, more useful signal in noise.

There's a per-signal energy cost (`SIGNAL_COST` in `simulation.py`) that
makes needless "idle chatter" costly, which helps but doesn't guarantee a
clean vocabulary — across seeds it still sometimes lets two states share a
token. A stronger, more targeted fix (explicitly penalizing a genome when
two of its states share a dominant token) was considered and deliberately
left out, to keep the outcome driven by selection rather than a rule
designed to force a specific result. In practice the collision does
sometimes resolve itself over further generations - and sometimes doesn't.

## Honest caveat

This was built in a container without a display. The mechanics are verified
via `test_smoke.py` (population survives, vocabulary converges across
multiple random seeds); `main_tui.py`'s startup prompt, placing toggle,
cursor movement, manual placement, and the paginated in-game notice were
all driven end to end inside a real pseudo-terminal (read back through a
VT100 emulator) — including on a genuinely small 24-row terminal, which is
what caught the notice screen needing pagination in the first place (it
silently ran off the bottom of a normal-sized terminal otherwise), and
`main_web.py`'s start screen, placing, predator count, click-to-place, and
notice modal were all confirmed working end to end in a real headless
browser. `main.py`'s pygame window was exercised headlessly (SDL's dummy
driver) to confirm the new logic doesn't crash, but hasn't been eyeballed
live — worth a quick visual check the first time you run it locally.
