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

Move the mouse near a creature to hear it: a tone plays for whatever it's
currently signaling (one fixed pitch per color, so alarm-call always
sounds the same note wherever it comes from), and fades out as you move
away or it falls silent. It's a way to listen to one creature at a time
instead of the whole population's noise. If your machine has no audio
device the game just runs silently - it never crashes over something
this optional.

`N`/`P`, and left/right click, all work the same whether the world is
running in automatic or manual mode - the mode only decides whether food
and predators *also* keep spawning on their own. The HUD starts collapsed to
the tick/population line plus a one-line summary (each state's single
strongest color) - `V`, or a click anywhere on that top strip, unfolds the
full controls list, per-state top-3-plus-other breakdown, and legend.

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

On launch you're asked to press `E`/`F` for English or French, `enter`
defaulting to French. If a save from a previous run exists, you're then
asked whether to resume it — say yes and the population, food, and
predators come back exactly as you left them, skipping every other
question. Otherwise: `A` (automatic) or `M` (manual), how many creatures to
start with (1-220, `enter` to confirm or skip for the default of 100), a
yes/no for whether physical traits evolve too (`y`/`n` in English, `o`/`n`
in French, on by default — see
[Adaptive traits](#adaptive-traits-on-by-default) below), then a yes/no for
whether to start already speaking a pre-trained language (see below,
`y`/`n` in English, `o`/`n` in French) — every screen defaults to
French/automatic/100/with-traits/no if you just hit `enter` through all of
them, and all choices stick for the whole run.

Creatures show up as a colored `o` (colored by whatever token they're
currently signaling, white if silent), food as green `.`, predators as a red
`X`. Controls: `space`=pause, `n`=drop a food patch at a random spot,
`p`=add a predator at a random spot, `r`=reset, `+`/`-`=speed, `q`=quit,
`[`/`]`=remove/add a predator right now, `s`=save to `thronglets_save.json`,
`g`=vocabulary-over-time graph, `t`=family tree, `c`=compare seeds,
`d`=translator, `Shift+F`=FAQ, `h`=in-game notice (paginated so it fits any
terminal height), `v`=show/hide the full HUD. `n` and `p` work the same in
automatic or manual mode. The HUD starts collapsed to the tick/population
line plus a one-line summary (each state's single strongest color), freeing
most of the terminal for the world - `v` unfolds the full controls list,
per-state top-3-plus-other breakdown, and legend. There's no reliable mouse
support in a terminal, so manual mode also offers a keyboard-cursor precision
tool: the arrow keys move it, `tab` switches between food/predator, `enter`
places whatever's currently selected exactly there. There's no proximity
sound here either (pygame and web have it) - a terminal has no
dependency-free way to synthesize distinct tones per token, unlike
`pygame.mixer` or the browser's Web Audio API.
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

## Bonus: a pseudo-3D view with optional mic/camera "sensors" (`main_vr.py`)

```bash
python main_vr.py
```

A separate, standalone pygame window with a classic "pseudo-3D driving
game" ground-plane projection (things shrink and converge toward a
horizon line as they get farther away) instead of the top-down view the
other three renderers use. It reproduces the creatures' *look* - round
yellow body, big eyes, blue lower half, all drawn as simple original
shapes, not a copy of the show's or the licensed game's actual pixel
art - over a basic sky/sun/hills/grass landscape.

This is **not** real VR: no headset, no stereoscopic or WebXR/OpenXR
output, nothing here targets or was tested with any VR hardware. It's a
2D screen trick that reads as roughly 3D.

Unlike a static demo, this runs a real `simulation.py` `World` - the
creatures here are the genuine evolving population, and the colored ring
around one is its actual current signal, same meaning as every other
renderer. It starts with exactly **one** creature, not hatched yet - it
sits on screen as a speckled egg. Left-click it a few times to crack it
open (the HUD counts the clicks); nothing in the world moves or steps
until it hatches, so there's no risk of a predator finding it first.
Once hatched, `LEFT`/`RIGHT` pans the view (or click and drag with the
mouse), the scroll wheel zooms in/out, `SPACE` pauses, `UP`/`DOWN` change
speed, `R` resets back to a fresh egg, `ESC` quits.

The lone starting creature is deliberately unable to reproduce on its
own, no matter how much energy it has - the population can only grow
past one by using the needs panel's fifth button (an egg icon) to add a
second creature yourself. Once there are two or more, reproduction
(pairing and budding both) becomes fully automatic exactly like the
other renderers, no further clicking required. Every creature born this
way, whether it arrived through that button or through ordinary
reproduction afterward, gets the same treatment as the very first one:
it starts life as an egg sitting at its real, moving position, fully
alive and simulated the whole time, but it doesn't render, sound, or
otherwise reveal itself as a creature until you find it and click it
open too. The HUD shows how many new eggs are waiting whenever there are
any. One that dies before being hatched just quietly disappears - no
leftover egg.

Standing still doesn't mean frozen: each creature blinks on its own
schedule and wanders a couple of pixels in place between simulation
steps, purely cosmetic idle motion meant to make it read as alive rather
than a static sprite sitting on the grass.

By default the whole population sounds at once: every evolved signal
(token) currently used by a living creature plays continuously and
together, a running chorus rather than silence until you go hunting for
it. Press `G` to turn that off and hear only individual creatures.
Hovering the mouse over a creature always plays a sustained tone for its
evolved signal too, independently of the chorus toggle - the same
proximity-listening idea as `main.py`/`main_web.py`, adapted for a 3D
view: "closest to the cursor" is judged by *screen* position rather than
world position, since depth already changes how big and how far apart
things look. Press `M` to mute everything.

The background is a bit more filled in now too, and reads coherently
back to front the way a real landscape would: a jagged rocky mountain
range spans the *entire* horizon as the true back of the world (not an
isolated outcrop), a dense forest sits at middle distance in front of
it, and the open plain where the population actually lives has just a
handful of trees standing on their own near the camera, plus scattered
boulders. Trees tower several times a creature's height rather than
standing barely taller than one, and rocks read as boulders instead of
pebbles. A river winds across the field toward the camera - a muddy
shore, a darker deep-water band, a lighter shallow center, and a couple
of softly drifting sparkle lines, rather than a single flat-colored
ribbon. Its source sits right where the forest ends, touching the
forest band without overlapping it, so the water reads as coming from
just past the trees instead of fading into empty ground. Trees and
rocks are depth-sorted together with the
creatures and predators, so a creature correctly stands in front of a
nearby tree or disappears behind a farther one instead of scenery and
population overlapping like two unrelated layers, and they pan with the
view along with everything else.

Every new game gets its own landscape - a fresh launch, or pressing `R`,
regenerates the tree/rock/grass placement, the hill silhouette, and
where the river sits, all drawn from a random seed. That's deliberate:
`generate_landscape()` takes an optional seed, so a *specific* layout
can be reproduced later - not wired up to anything yet, but there so a
future save/load feature can restore a saved game's exact terrain
instead of randomizing over it.

Lighting is faked rather than simulated in real 3D, but tracks the sun
and moon anyway: shadows stretch and swing around over the course of the
day - short and centered under everything at solar/lunar noon, long and
cast to one side near sunrise and sunset. The ground itself is scattered
with small grass-tuft marks instead of being one flat color band, for a
bit of texture instead of a perfectly uniform field.

Scrolling zooms in and out on that landscape, Minecraft-style: it
magnifies the whole scene around a fixed point on the horizon instead of
moving the camera forward, so every distance keeps the same size ratio
to every other distance as you zoom - nothing gets distorted, it's
purely "closer/farther," with proportions preserved the whole way.

The sky runs its own day/night cycle the whole time (a full loop every
24 real minutes - one in-game hour per real minute - running even before
the egg hatches) - the sun and moon
arc across the sky on opposite halves of the loop, never both up at once,
with a warm sunrise/sunset tint at each crossing. Sky, hills, ground, grid,
and trees all blend smoothly between their day and night colors, stars
fade in once the sun is down, and a soft blue wash settles over the whole
scene (population included) as it gets dark. It's purely atmospheric -
doesn't change how anything behaves, just how it looks.

**Optional sensors** (loosely inspired by the show's idea of a
camera/microphone giving the Thronglets an outside signal to react to):
press `A` to turn on the microphone, `C` for the webcam. When either
picks up something loud or something moving, it adds a transient
predator - like a real sighting - and lets the population's own
already-evolved alarm response do the rest; it never touches genomes or
state directly. **Both are off by default** - nothing is captured unless
you explicitly press the key, and the HUD always shows `mic: ON/off` and
`camera: ON/off` so it's never listening silently. `[`/`]` lower/raise how
loud or how much motion it takes to trigger - there's no way to calibrate
this from a container with no microphone or camera, so treat the default
as a starting point and tune it once you're on a real machine. If the
required library isn't installed, or there's no hardware, or permission
is denied, that sensor just reports `unavailable` - the game never
crashes over something this optional.

The sensors need two extra packages the core game doesn't:

```bash
pip install -r requirements-vr.txt
```

(`sounddevice` for the microphone, `opencv-python-headless` for the
webcam.) On Linux, `sounddevice` also needs the system PortAudio library
(e.g. `apt install portaudio19-dev`) - without it, the import itself
fails and the mic just reports unavailable, same as any other missing
piece.

Once hatched, a small needs panel appears top-left with five clickable
icons: a pizza (hunger), a glass of water (thirst), a bar of soap
(cleanliness), a toy (joy), and an egg. Each need slowly drains on its
own - about two minutes from full to empty if left alone - and clicking
its icon tops it back up to full. Feeding the pizza also restores some
of the creature's *real* `simulation.py` energy, same field the other
renderers read from; the other two need icons are local to this window
and don't touch the simulation. Neglect all four for long enough and the
creature's expression turns visibly worried - there's no harsher penalty
than that, it's just something to look after while you watch it. The
fifth icon isn't a decaying need at all - it's a button: click it any
time to add a brand-new creature to the world as another egg to go
track down and hatch, which is also the *only* way past a
single-creature population (see above).

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
multiple random seeds); `main_tui.py`'s startup prompt, n/p quick-place keys,
cursor movement, manual placement, and the paginated in-game notice were
all driven end to end inside a real pseudo-terminal (read back through a
VT100 emulator) — including on a genuinely small 24-row terminal, which is
what caught the notice screen needing pagination in the first place (it
silently ran off the bottom of a normal-sized terminal otherwise), and
`main_web.py`'s start screen, n/p keys, predator count, left/right-click-to-place, and
notice modal were all confirmed working end to end in a real headless
browser. `main.py`'s pygame window was exercised headlessly (SDL's dummy
driver) to confirm the new logic doesn't crash, but hasn't been eyeballed
live — worth a quick visual check the first time you run it locally.
