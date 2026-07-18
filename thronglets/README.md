# Thronglets

A tiny artificial-life sandbox, inspired by the "Thronglets" from the Black
Mirror episode *Plaything* (S7E4) — little creatures that live inside a
simulation and end up with a language of their own.

This isn't a reproduction of anything from the show (that's fiction). It's a
real, if deliberately small, model of how a shared vocabulary can emerge from
**natural selection**, not machine learning:

- Each creature is born with a genome deciding which of 6 "tokens" (colors)
  it emits when it's **idle**, has **spotted food**, wants to **mate**,
  senses a nearby **predator**, or is **critically low on energy with no
  food in sight** — and separately, how it reacts on hearing each token
  from a neighbor (move toward it, away from it, or ignore it).
- Predators roam the world and kill any creature they catch. Spotting one
  puts a creature in a "danger" state, using the exact same signal/response
  machinery as food and mate calls — so an alarm call is just another word
  that can (or might not) emerge, not a special-cased mechanic. Each
  predator independently hunts whichever creature is nearest to it, and
  gently pushes away from other predators that get too close, so a pack
  doesn't collapse onto a single point when creatures cluster together.
- A creature whose energy drops critically low with no food visible enters
  **distress** - a fifth state, ranked below food (spotting actual food
  always wins) but above mating (survival first). It's not a special case
  either: same signal/response machinery, a color that may or may not come
  to mean anything to a creature's neighbors.
- Food and predators can each be **automatic** (food spawns in periodic
  patches; predators all appear at once) or **manual** (nothing spawns on
  its own). You pick which, once, at startup in all three renderers — it's
  not something you toggle mid-run. Either way, you can always add food or
  a predator yourself at any time (keyboard shortcuts / mouse clicks, see
  below) — manual mode just means nothing *else* spawns them for you.
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
- The running game — the actual population, with whatever language it has
  evolved on its own, not just the trained-AI vocabulary — can be saved and
  resumed later (`s`/`S` to save in the terminal/pygame, a "Save" button on
  the web page). If a save exists, every renderer offers to resume it right
  at startup, before asking anything else.

## Run it

There are two renderers, both sharing the same simulation core:

- `main.py` — a pygame window (nicer, needs a display + pygame installed).
- `main_web.py` — a local web server (standard library only, no new
  dependency) with an HTML/canvas page you open in any browser. Works
  anywhere, including Termux.

There's also `main_gl.py`, a *true 3D* proof of concept (optional `moderngl`
dependency) — see the Bonus section below.

### Desktop (pygame)

```bash
pip install -r requirements.txt
python main.py
```

The window opens fullscreen at the desktop's own resolution, stretching
the world to fill the screen exactly (no letterbox bars, whatever the
screen's aspect ratio) — `ESC` quits back to the desktop.

On launch you're asked to press `E`/`F` for English or French, `ENTER`
defaulting to French. If a save from a previous run exists
(`thronglets_save.json`), you're then asked whether to resume it — say yes
and everything else is skipped, you're straight back where you left off.
Otherwise you pick `A` (automatic) or `M` (manual), how many creatures to
start with (type a number, 1-220, `ENTER` to confirm or skip for the
default of 100), `Y`/`N` (`O`/`N` in French) for whether physical traits
(speed, vision, hearing, metabolism) evolve too — see
[Adaptive traits](#adaptive-traits-on-by-default) below, on by default — then
`Y`/`N`/`T` (`O`/`N`/`T` in French) for whether to start already speaking a
pre-trained language, train a fresh one live right there, or skip it (see
below for both) — every screen defaults to French/automatic/100/with-traits/no
if you just hit `ENTER` through all of them, and they stick for the whole run
(`R` resets using them again, it doesn't ask a second time).

| Key           | Effect                                                       |
|---------------|----------------------------------------------------------------|
| `SPACE`       | pause / resume                                              |
| `UP` / `DOWN` | speed up / slow down the simulation                         |
| `R`           | reset to a fresh world (same mode, same predator count)      |
| `N`           | drop a food patch at a random spot                            |
| `P`           | add a predator at a random spot                               |
| `[` / `]`     | remove / add a predator right now (also sets the reset count) |
| `S`           | save the running game to `thronglets_save.json`               |
| `G`           | vocabulary-over-time graph                                  |
| `T`           | family tree - browse ancestors/descendants                  |
| `C`           | compare seeds - is a result reproducible?                   |
| `D`           | translator - what each color currently means                |
| `F`           | FAQ - curated questions and answers                          |
| `H`           | in-game notice explaining the mechanics                      |
| `V`           | show/hide the full HUD (or click the top HUD strip)          |
| `M`           | mute the proximity-listening sound                          |
| left click    | place food (or expand/collapse the HUD if clicked there)     |
| right click   | place a predator                                              |
| `ESC`         | quit                                                         |

Move the mouse **onto** a creature to hear it: a single struck, bell-like
note plays once for whatever it's currently signaling (one fixed pitch per
color, so alarm-call always sounds the same note wherever it comes from).
Sliding onto another creature strikes that one's note; resting the cursor
stays silent - a note per creature you touch, not a drone held for as long
as you hover (the same behaviour as the VR view). If your machine has no
audio device the game just runs silently - it never crashes over something
this optional.

`N`/`P`, and left/right click, all work the same whether the world is
running in automatic or manual mode - the mode only decides whether food
and predators *also* keep spawning on their own. The HUD starts collapsed to
the tick/population line plus a one-line summary (each state's single
strongest color) - `V`, or a click anywhere on that top strip, unfolds the
full controls list, per-state top-3-plus-other breakdown, and legend.

**Optionally, the flock learns who you are.** This is a **start-screen
choice, off by default** - a bare run stays pure natural selection, the
game's original spirit, and the learned mind is something you opt into
rather than an imposed default. Turn it on and the same emergent-learning
system as the VR view (the opt-in `Mind` in `simulation.py`) runs here,
with your mouse cursor as the "hand." The two things you place are the
lesson: **drop food near a creature and it - plus every creature close
enough to witness it - learns your hand is worth approaching; drop a
predator and they learn to flee it.** Over a session the flock comes to
**trust or fear you**, and passes what it learned on to its offspring, so a
kind or cruel run compounds across generations. When it's on, it's shown
two ways: a colour-coded line on its own row under the HUD header (*"the
flock trusts you (+76%)"* / *"…fears you"*), and a **disposition sparkline** at the top of
the Graph screen (`G`) that plots that feeling over time next to the
vocabulary curves. (With learning off, neither appears - the observatory,
unchanged.)

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
English and French at any time, including mid-run (French by default) —
this one isn't a one-time choice like the others. The world doesn't exist
yet — if a save from a previous run exists, a **Resume saved game** button
appears on the start screen and skips every other question. Otherwise,
pick automatic or manual mode, how many creatures to start with (pre-filled
with 100), whether physical traits evolve too (checked by default — see
[Adaptive traits](#adaptive-traits-on-by-default) below), and whether to
activate a pre-trained language (unchecked by default), and those four stick
for the whole run (Reset doesn't ask again). Once
started, the page polls the server a few times a second for a fresh
snapshot and draws it to a `<canvas>`; buttons
handle pause/reset/speed. `+`/`- predateurs`
remove or add a predator immediately (also setting how many a reset will
use). `N`/`P` on the keyboard drop a food patch / add a predator at a
random spot, left-click the world to place food, right-click to place a
predator - all four work the same in automatic or manual mode, which only
decides whether food and predators also keep spawning on their own. A
**Save** button writes the running game to
`thronglets_save.json`, a **Family** button opens the genealogy browser
(arrow keys or on-screen ▲▼◀▶ buttons to navigate), a **Compare** button
opens the seed-comparison panel, a **Translator** button opens the
color-to-meaning dictionary, an **FAQ** button opens the curated
questions/answers, and a **Notice** button opens an explainer of the
mechanics without pausing the simulation
underneath. The HUD starts collapsed to the tick/population line plus a
one-line summary (each state's single strongest color) - `V`, or a click on
that line, unfolds the mode/settings text and the full top-3-plus-other
vocabulary breakdown. Move the mouse over a creature (or close to one) to
hear it - a tone plays for whatever it's currently signaling, one fixed
pitch per color, fading out as the mouse moves away or the creature falls
silent; a **Mute** button (or `M`) turns it off. It uses the browser's
Web Audio API directly, no plugin or extra permission needed, and starts
the first time you click a start button (browsers require a click before
they'll let a page play audio).

All three renderers show a HUD with, for each internal state (danger / food-call /
distress-call / mate-call / idle), the 3 most common tokens currently in use and
what share of the living population uses each (anything beyond that gets folded
into a single "other" bucket, so the row stays readable even when many colors
are still splitting the vote early on) — the numbers to watch are how fast a
single token pulls ahead of the pack (starting near chance, ~17%, since there
are 6 tokens) and whether it stays there.

A separate **Graph** screen (`g`/`G` in pygame and the terminal, a "Graph"
button on the web page — the same pattern as the in-game notice) plots each
state's dominant-token share over time as a proper curve: a sample every 20
ticks, covering the *entire* run from tick 0 to now, compressed to fit the
screen rather than a recent-only window - so the curve never loses its
earliest history, it just gets progressively more zoomed out the longer a
game runs. A rising line is a color pulling ahead, a falling one is a
consensus breaking apart, a flat line at the bottom is no agreement yet.
This history rides along with `s`/save (so a resumed game keeps its curve,
not just its population) but resets on `r`/reset, same as everything else
about the world.

Speed is measured in real time, not rendered frames: the default `x1` is a
genuine one tick per second, slow enough to actually watch a single decision
happen, and `x10`/`x50`/etc. scale from that same one-second baseline
(capped at `x200`) rather than from whatever frame rate the renderer happens
to draw at.

Every creature is tracked back to its parent(s) - a **Family** screen
(`t`/`T` in pygame and the terminal, a "Family" button on the web page, same
pattern as the Graph/Notice screens) is an ego-centric genealogy browser
rather than one giant tree crammed onto a screen: it shows one creature at a
time - its generation number, whether it's alive or when it died, its
parent(s), its children, and how many total descendants it has (and how many
of those are still alive) - and the arrow keys walk the tree from there (up
to a parent, down to a first child, left/right between siblings). Since
mating just picks the nearest eligible neighbor with no notion of family,
it's entirely possible - and something you may actually run into - for a
creature to end up mating with its own descendant; the browser doesn't hide
this, a lineage isn't a strict tree. Opening it doesn't reset or pause
anything (the web version even keeps ticking live behind it); unlike
Graph/Notice, which dismiss on any key, `t`/`ESC` close this one specifically
since the arrow keys are busy navigating.

## Adaptive traits (on by default)

By default every creature also has its own speed, vision range, hearing
range, and metabolism, on top of signaling and listening. **"Adaptive
evolution"** is asked about at startup right after population size, in all
three renderers — on by default, but you can turn it off if you'd rather
keep physical stats fixed and isolate how just signaling/listening evolve.
When it's on, those four physical traits are part of the genome too:
inherited from parents, mutated a little at each birth, and bounded within a
sane range. A faster, sharper-sensed creature isn't a free upgrade, though —
speed, vision, and hearing each add to that individual's energy cost per
tick, so a genome that maxes everything out just starves faster. Selection
has to actually weigh "can sense more of the world" against "burns energy
faster doing it," the same kind of real trade-off that already exists
between signaling and staying silent.

When adaptive traits are on, the **Graph** screen gains a second section
below the vocabulary curves: the population's average speed, vision,
hearing, and metabolism over time, each as a share of that trait's allowed
range (same sampling cadence and full-run coverage as the vocabulary curves).
It's the same kind of evidence as watching a token's share climb - a rising
or falling line means selection is actually pushing that trait somewhere,
not just letting it drift. This section is hidden entirely when adaptive
traits are off, since there's nothing to show (every creature has the same
fixed stats).

## Comparing seeds: is a result reproducible, or did you just get lucky?

A single playthrough only tells you what happened on *that* run - maybe
speed happened to evolve high because selection genuinely favors it, or
maybe it's just where that particular random walk wandered. The **Compare**
screen (`c`/`C` in pygame and the terminal, a "Compare" button on the web
page - same pattern as Graph/Family) answers that by running several
independent, headless worlds back-to-back with identical settings (same
population, predator count, adaptive-traits flag, and starting
vocabulary/language as your current game) and only the RNG seed differing,
then summarizing what happened across all of them:

- **Language**: each state's dominant color per seed, plus how many of the
  seeds ended up collision-free - the same question `train_language.py
  --sweep` asks, but for the evolved (not gradient-trained) population.
- **Physical traits** (only offered if adaptive evolution is on): mean,
  standard deviation, min, and max for each trait's final value across the
  seeds - a wide spread means that trait's outcome is mostly noise; a tight
  spread means it's a genuine, repeatable result.

Three depths to pick from - quick (4 seeds x 8,000 ticks), thorough (8 x
40,000), or expert (16 x 60,000, prioritizing more seeds over more ticks
since that's what actually buys statistical confidence). Unlike a script run
from the command line, this runs one seed at a time in the background while
showing live progress, and `ESC`/Cancel stops it early without losing
whatever seeds already finished. It's a side experiment - it builds its own
worlds from scratch and never touches the game you're actually playing.

## Translator: what does each color mean right now?

The HUD and Graph screens are organized by *state* - for "food-call," which
color is winning? The **Translator** screen (`d`/`D` in pygame and the
terminal, a "Translator" button on the web page) flips that around: for each
of the six tokens (including silence), which state currently treats it as
its dominant color, and with what confidence. A token nobody's settled on
yet shows as unused/ambiguous; a token two states are both using is flagged
as a homonym right there instead of you having to notice it by eye across
five separate HUD rows. Unlike the Graph screen this is a frozen snapshot of
right now, not a history - open it again later to see how the mapping has
moved on.

## FAQ

A curated in-game FAQ (`F` in pygame, `Shift+F` in the terminal since
lowercase `f` is already the manual food-drop key, an "FAQ" button on the
web page) answers nine questions that actually came up while building and
playing this - why creatures cluster near food they're not eating, whether
distress leads to cooperation, why adaptive metabolism always bottoms out,
how siblings end up with wildly different generation numbers, why a
creature can end up mating with its own descendant, why even a trained
vocabulary can drift, what homonyms are, why a single playthrough isn't
proof of anything, and how the trained-AI language actually differs from
the evolved one. Paginated the same way as the Notice screen.

## Headless check

`simulation.py` has no pygame dependency, so the core can be run and tested
without a display:

```bash
python test_smoke.py
```

This runs several thousand ticks and asserts the population survives and
vocabulary agreement increases — i.e. that a language is actually emerging,
not just that the window doesn't crash.

## Bonus: a *true* 3D proof-of-concept (`main_gl.py`)

```
pip install moderngl        # only needed for this renderer
python main_gl.py
```

The other renderers are 2D. `main_gl.py` is the real thing: an **OpenGL**
scene with a perspective camera you can orbit, a
**procedural mountain terrain** (rolling valley, distant massifs, and a
lake carved right into the height field with an animated water surface),
three-dimensional trees and rocks that sit on the slopes, and the
creatures as **little bodies** (head, torso, arms along the sides, legs,
camera-facing eyes) walking the ground - every creature the same: a
**yellow body in blue clothes**, each wrapped in a **faint, misty coloured
haze that shows the signal it's emitting** (the same 6-token palette as
everywhere else). Soft contact shadows, a
gradient sky with a sun glow, and distance fog give it real depth. The
population is a genuine `simulation.py` World, stepped every frame - they are
real creatures at their real
positions, in the same 6-token colours as everywhere else.

It now has a full **day/night cycle, seasons and weather**, driven by the
3D lighting rather than flat tints:

- **Day/night**: the sun - then, once it sets, the moon - travels a real
  arc across the sky. The whole scene is lit from that moving body, the
  sky gradient shifts from dawn orange through midday blue to a starry
  night, and the fog takes the horizon's colour so distance always matches
  the hour.
- **Seasons**: spring / summer / autumn / winter recolour the canopies and
  the ground - fresh green, deep green, autumn orange, and a snow-dusted
  white winter over a white ground. Seasonal ground life grows too:
  **flowers bloom in spring and summer**, **red-capped mushrooms come up in
  autumn**, and the winter ground is shaded as drifting snow.
- **Weather**: clear / rain / snow. Rain and snow are real 3D particles
  falling around the camera; both overcast the sky and dim the light, and
  snow whitens the world further.

**It's interactive, and the flock learns who you are.** The mouse cursor is
your hand (the opt-in `Mind` from `simulation.py`): **click a creature to
select and feed it** - a kindness it, and the creatures near enough to
witness it, learn to approach - and **right-click to startle it**, which
teaches fear. A 2D HUD shows the season/weather/clock/population, the
flock's overall feeling toward you (*"the flock trusts you (+45%)"*), and a
panel for the selected creature (colour, generation, energy, and its own
feeling). Little touches of life round it out: the canopies sway, the
creatures bob, birds drift overhead, the lake mirrors the sky, shadows
lengthen with the low sun, and a soft ambient drone plays.

`moderngl` is the one extra dependency and it is only imported when you run
this file, so the other renderers keep working with just numpy + pygame.

Controls: `LEFT-drag` orbits the camera, the scroll wheel zooms, **left-
click a creature** to select + feed it, **right-click** to startle it, `S`
cycles the season, `W` cycles the weather, `T` toggles fast time, `ESC`
quits. (On a machine without a GPU the scene still renders through Mesa's
software rasterizer; `python main_gl.py --headless --phase=0.5
--season=autumn --weather=rain` writes a PNG of any hour/season/weather.)

## Where to take it next

The simulation core (`simulation.py`) and renderer (`main.py`) are split on
purpose so this is easy to extend:

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
directly minimize communication error, using the same 5-state/6-token
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
idle-heavy skew the real simulation has: 4 out of 10 seeds converged to a
perfect, collision-free code (100% listener accuracy) - a real difference
from the evolved version, where two states landing on the same color is
common and can persist indefinitely. But it's a tighter squeeze than it
looks: 5 states now have to fit into 6 tokens (only one spare, instead of
two), so it's less forgiving than the original 4-state setup. The 6 seeds
that still collided always merged two of the three *rarest* states
(`distress-call`, `alarm-call`, `mate-call`, each well under 15% of
samples) into one token, never touching `food-call` or `idle`, and capped
accuracy around 80%. With `--uniform` (equal frequency for all 5 states)
instead, it's clean almost every time (9/10 in our sweep) - much better
than the skewed case, but no longer the literal 100% guarantee it was with
4 states: fitting 5 states into 6 tokens leaves only one token of slack
even without a frequency skew working against it.

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
maps to, and vice versa) baked out of the trained networks. Both
renderers can start a population already speaking that clean vocabulary,
with `--language`:

```bash
python main.py            --language language_model.json
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

### Training live, from inside `main.py`

You don't have to leave the game or touch a terminal to train one: on the
AI-language screen, press `T` instead of `Y`/`N` to train a fresh seed
right there. This is the same `train()` used by `train_language.py --sweep`,
just called directly - `main.py` imports `train_language` lazily, only when
you press `T`, so nothing else in the game needs PyTorch installed. This
still needs `pip install -r requirements-rl.txt` to work; if it isn't
installed, pressing `T` gives a clear message and the game starts without
AI instead of crashing, same as a missing `language_model.json`.

Training one seed shows live progress right in the window - it takes a
little while (the same few thousand training steps `--sweep` runs per
seed), `ESC` cancels it early. Rather than just a step counter, you get a
fill-up progress bar and elapsed-time/steps-per-second, a one-line
explanation of what loss and accuracy actually mean, and - the most useful
part - the current state->color guess for all five states, updating live as
it trains, so you can watch the mapping actually settle instead of staring
at an abstract loss number. Each attempt picks a fresh random seed (not
0, 1, 2, 3... - there's no reason a seed's number would predict anything
about its outcome). Once a seed finishes, its result is shown - clean or
collision, overall accuracy - and you choose:

| Key   | Effect                                                          |
|-------|------------------------------------------------------------------|
| `V`   | use this seed - exports it to `language_model.json` and starts the game with it (only offered if this seed came out clean) |
| `N`   | keep this one's result, try another random seed instead          |
| `ESC` | give up - start the game without AI                              |

This is the interactive version of watching `--sweep`'s collision-rate
table scroll by and then re-running with `--seed` on whichever one looked
good, except you never leave the game window and don't need to remember a
seed number - you just watch each one train and decide as you go.

**Does the clean vocabulary survive being handed to blind evolution?**
Running seeded worlds for 20,000 ticks shows agreement on all five states
staying at or extremely close to 100% the entire way, for as long as the
population survives - once selection has nothing left to gain from
reshuffling an already-optimal, collision-free code, there's essentially
no pressure pushing it away from that optimum. Population itself can still
boom and crash from ordinary resource pressure (the food supply is fixed
regardless of headcount) independently of how clean the vocabulary is -
the same extinction risk that was always possible in this simulation, not
something the trained vocabulary introduces: in a 5-seed spot-check, 1 run
died out this way around tick 2700 after a population boom outran the food
supply, the other 4 held a clean vocabulary the whole time they were alive.

## A known quirk: homonyms

Each state's dominant token is decided independently, so nothing stops two
different states from converging on the *same* color by chance — a listener
who hears that color can't tell which meaning was intended. Since `idle` is
by far the most common state, this is usually what "wins" any collision,
drowning out the rarer, more useful signal in noise. With 5 states sharing
6 tokens (only one spare instead of two), there's less room to avoid
collisions than before `distress-call` existed.

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
multiple random seeds); `main_web.py`'s start screen, n/p keys, predator
count, left/right-click-to-place, and notice modal were all confirmed
working end to end in a real headless browser. `main.py`'s pygame window
was exercised headlessly (SDL's dummy driver) to confirm the logic doesn't
crash, but hasn't been eyeballed live — worth a quick visual check the
first time you run it locally. `main_gl.py`'s scene is rendered off-screen
through Mesa's software OpenGL (llvmpipe under a virtual framebuffer) to
check the look across seasons and weather.
