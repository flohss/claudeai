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

There are three views, all sharing the same simulation core — the two
below, plus the 3D page described just after (served by `main_web.py`):

- `main.py` — a pygame window (nicer, needs a display + pygame installed).
- `main_web.py` — a local web server (standard library only, no new
  dependency) with an HTML/canvas page you open in any browser. Works
  anywhere, including Termux.

**The 3D view lives in the browser.** Start `main_web.py` and open
`http://localhost:8765/3d` (or press the `3D` button on the 2D page). It is the
same running world as the 2D page - the simulation stays in Python, the page
only draws what the server reports - rendered with three.js: a physically-based
sky whose sun really moves and lights the scene, soft shadows, ambient light
taken from that same sky, filmic tone mapping, bloom on what glows (the call
each creature is making, a predator's eyes), instanced grass that bends in the
wind, seasons, rain and snow. Click a creature to read its mind, right-click it
to stroke, feed, hit or kill it; the dock at the bottom holds the food,
predator and fire tools, the time of day, the season and the weather. Nothing to
install and nothing fetched from the internet: three.js is vendored under
`web3d/vendor/` (MIT licence, included). Three quality levels, chosen in the
dock; "high" adds ambient occlusion and wants a real graphics card.

The earlier OpenGL proof of concept (`main_gl.py`, which needed `moderngl`)
has been removed: this page replaces it.

### Desktop (pygame)

```bash
pip install -r requirements.txt
python main.py
```

The window opens **maximised**, not fullscreen — this is a thing you leave
running beside other windows, and seizing the whole display was a hostile
default. Drag it to any size you like: the world is stretched per-axis to
fill exactly whatever it is given, so there are no letterbox bars at any
window shape, and the HUD and every screen follow along live. `F11` (or
`Alt+Enter`, from any screen, menus included) takes the full display and
gives it back, landing on the exact window you left. `ESC` quits.

At the start menu, `P` opens the parameter screen and **`T` opens Measure** —
the report from `report.py`, run from inside the game. Tick which of the seven
tests you want, set the seeds and the ticks, and it writes
`thronglets_report_<date>.txt` beside the game. It calls the *same function* the
command line calls, so the two cannot disagree; verified by diffing a run from
each, which came out byte-for-byte identical. What it adds is the thing the
command line cannot give you: while you are choosing, it times a real world on
**your** machine and shows what the run will cost — because `7 × 16 × 200000` is
22.4 million ticks and *six days*, and a terminal will start that without a
word. `ESC` stops a run within a second or two, mid-world.

**`V` runs the other family of tests** — the pass/fail guards (`test_all.py`),
which answer "is anything broken?" rather than producing numbers. It shows each
suite's status live and the output as it comes, and states plainly that it runs
against **built-in** values: `test_smoke` and `test_learning` never import
`tuning`, and `test_tuning` resets to built-in before every probe, so a pass
means the game *as shipped* is sound and says nothing about parameters you have
pinned. If you have any pinned, it warns you before you start.

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
| `?`           | FAQ - curated questions and answers                          |
| `F`           | fire tool - arm it, then left-click or drag to burn creatures |
| `H`           | in-game notice explaining the mechanics                      |
| `V`           | show/hide the full HUD (or click the top HUD strip)          |
| `M`           | mute the proximity-listening sound                          |
| left click    | place food (or, while the fire tool is armed, burn)          |
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
predator and they learn to flee it.** Creatures that trust you come from a
good way off and gather loosely near the cursor, holding a respectful
standoff rather than piling onto the exact point (so they no longer crowd it
or set off the proximity chime by themselves). Over a session the flock comes to
**trust or fear you**, and passes some of what it learned on to its offspring -
but it does **not** compound across generations, and the honest number matters
here. A newborn keeps `INHERIT_BLEND = 0.85` of its parents' learned weights, so
every birth sheds 15%. Measured: teach a flock hard, then take your hand away
forever, and **86%** of the lesson survives 2000 ticks, **18%** survives 4000, and
by 6000 ticks - about eight generations of turnover - it is **gone**, oscillating
around zero. The real decay runs faster than the blend arithmetic alone, because
the living keep learning too: they don't merely forget you, they re-learn your
absence.

When it's on, it's shown
several ways: a colour-coded line on its own row under the HUD header (*"the
flock trusts you (+76%)"* / *"…fears you"*). That line has a real **neutral
band** — a flock nobody has touched reads *"doesn't know you yet"*, not
*"is wary of you"*. It has to: a creature is born valuing every situation at
exactly `0.0`, holding no opinion of you whatsoever, so without a neutral band
the very first thing a player saw was an accusation they had done nothing to
earn. The band matches the ±0.05 dead zone the gauge beside it already used, so
the words and the colour can no longer contradict each other, and the wording
now lives once in `i18n.py` — the 3D view had its own copy with the same flaw.
Under that line, the expanded HUD adds the thing the average cannot show: a
**stacked bar of what the flock has actually decided** — how many are *coming*,
how many *fleeing*, how many *ignoring you*, right now. A flock split down the
middle between coming to you and running from you averages out to exactly the
same number as one that is uniformly indifferent, and those are very different
rooms to be standing in; one reads as two strong blocks, the other as a wall of
grey. There is also a **disposition sparkline** at the top of
the Graph screen (`G`) that plots that feeling over time next to the
vocabulary curves. That arc belongs to the **world**, not to the window, so it
is **saved and restored with everything else**: resuming a game used to bring
back every creature's mind while leaving the story of how they came to feel that
way completely blank, which is the wrong half to keep. And - surfacing the same
inner life the 3D view shows -
**each creature is filled with the colour of its emotion** (calm grey-green,
happy green, sad blue, fearful red), so a mood spreading through the flock is
visible as a **wave of colour** rolling across the field; the signal-token
ring around each creature is unchanged. **Hover a creature and its spatial
memory is painted on the ground** - green tiles over the patches it trusts,
red over the ones it fears, its mental map of the world laid bare. The
disposition itself is drawn as a small **gauge** in the HUD (filling
green/right as the flock trusts you, red/left as it fears you), and the
expanded HUD carries a **colour key** naming each mood colour and the
memory tiles. (With learning off, none of this appears - the observatory,
unchanged.)

**Master Mode** is a third choice on the opening screen (`M`, alongside
resume and new game), inspired by the *White Christmas* Black Mirror episode.
It starts a fresh game with learning forced on and hands you a darker power:
**hover a creature and hold `I` to isolate it in accelerated time** - a few
real seconds pass, but the creature lives through subjective *weeks and
months of total solitude* (a counter shows how long), which breaks its will.
As its **obedience** climbs from 0 to 100%, its mood is hollowed out (deep,
numb despair) and it drains to a hollow grey with a small "collar" ring. A
broken creature obeys: it comes to heel at your cursor and stays, **no matter
how much it fears you** - obedience overrides trust and fear alike, and it
obeys **promptly**: though its will is hollowed out, the body snaps to the
command at full speed (crisper the more broken it is), ignoring the sluggish
torpor that low mood would otherwise impose - dead inside, prompt outside. Once you
have broken some, you **command them with number keys**: `1` follow (heel at
your cursor), `2` gather (huddle tightly onto the cursor from anywhere on the
map), `3` disperse (driven outward), `4` halt (freeze in place). Only broken
creatures obey; the still-free ignore you. The HUD shows the flock's average
obedience and the current order, and the state of the flock is saved with the
game.

**But domination has to be maintained - the flock fights back.** Breaking
and killing terrorises the still-free creatures (the same trauma-spread as a
normal game), and a frightened free creature standing near a broken one
slowly **loosens its will** (solidarity), so a broken creature left among
frightened, still-free kin has its obedience eroded and can **break free
again**. So you can't just break a few and relax: you have to isolate the
broken (order them to *gather* away from the free, or *disperse* the free),
subdue the whole flock, or cull the frightened - faster than fear can spread
and undo your grip. When too much of the free flock is terrified it tips into
an **uprising** (a flashing HUD alert): the erosion accelerates, and the
frightened free creatures stop fleeing and **actively charge the broken ones
to tear them free** - a visible liberating mob swarming your servants. The HUD
gauge shows both your **obedience** (grey) and the flock's **unrest** (a red
sliver) so you can see your hold slipping.

Master Mode also reshapes the world around your rule: **no predators at all**,
**no reproduction** (the flock never grows on its own), and **no hunger** -
your domain sustains the flock, so creatures never starve or age to death and
you never have to feed them (which sidesteps the trap where feeding to keep
them alive would make them adore you). The only deaths are the ones you deal
with the fire tool (`F`); there's no feeding (left-click does nothing on its
own), and **right-click births a new creature**, so the population only ever
changes by your own hand. The HUD shows the flock's **obedience** rather than
its trust (in Master Mode affection is irrelevant - only obedience governs),
and a broken creature is easy to spot on the field: it drains to a **hollow
grey with a dark "collar" ring** and stays visibly empty for good, its will
not healing back on its own. (All of this is Master Mode only; a normal game
is untouched.) Master Mode is saved with the
game, so resuming a saved Master game (`R` on the opening screen) brings you
back into Master Mode - obedience, broken minds and all - rather than an
ordinary run.

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

## Two models, side by side: classic, or no code at all

At the start you choose what kind of creature lives in the world. Neither
replaces the other.

| | Classic (default) | No code |
|---|---|---|
| Where behaviour comes from | Written by hand: a priority list (danger, food, distress, mate) and a hand-set urge for each | Nothing written: an inherited neural network decides the step and the call |
| What evolves | The vocabulary (and the body, if enabled) | The whole brain (and the body, if enabled) |
| From the first second | Creatures already flee and forage | Creatures are clumsy; most founders are hopeless |
| Learned mind, Master Mode, trained language | Available | Not available (they are built on the classic creature) |

How to choose it: in the 2D game, the "Which kind of creature?" screen (`1` /
`2`); in both browser pages, the "Kind of creature" list on the start card. A
saved game remembers its model.

**What the no-code creature is.** Its genome carries a small network (25 inputs,
8 hidden units, 8 outputs). The inputs are only what it perceives: which way the
nearest food, hunter and neighbour lie and how near, its own energy, each call
it can hear as a direction, where it stands, two random numbers and a constant.
The outputs are a step and a score for each possible call. Nothing tells it that
food is good or a hunter bad. The world does the teaching: food in reach
restores energy, a hunter in reach kills, and whoever is alive and fed leaves
children with a slightly altered copy of its network.

What is still fixed by hand, and has to be: the senses and the physics. Those
are the body and the world, not the behaviour.

**Does anything actually appear?** Measured, not assumed. `World.free_probe()`
shows every living brain a piece of food (then a hunter) in 8 directions with
nothing else in sight and looks at which way it steps: 0 means it makes no
difference, +1 means straight at the food (or straight away from the hunter).
Watching real movement would not do - a hunter ends up behind whatever is
moving, so even a brain blind to hunters looks like it is fleeing.

Eight worlds each, 30,000 ticks, founders at 0.00 +- 0.03 on both:

| Setting | To food | Bar (2x spread) | Away from hunters | Bar |
|---|---|---|---|---|
| 60 founders, fixed bodies | **+0.75** | 0.42 | +0.36 | 0.54 |
| 100 founders, evolving bodies | **+0.62** | 0.48 | +0.50 | 0.54 |

So: **walking toward food reliably appears on its own** (it clears the bar in
both settings). **Fleeing hunters appears in most worlds but not reliably** -
five or six worlds in eight reach +0.4 to +0.8, the others stay near zero, and
the average does not clear the bar. It is shown on screen as it is, not claimed.

**Two honest limits.**

- *Newcomers.* Founders have random brains and a flock can die out before
  anything worth inheriting exists. So below 14 alive, one newcomer arrives per
  tick - an exact copy of a random survivor. That is help from outside the
  world; it is counted and displayed ("newcomers") so it never passes for the
  flock's own success. The first 10,000 ticks typically need 20-180 of them;
  a world that has found its feet needs none.
- *The vocabulary panel.* A no-code creature has no situation labels. The panel
  still sorts calls by situation, but the situation is the observer's label,
  tallied from what was actually called lately. Whether the calls *mean*
  anything to the listeners has not been measured yet.

The classic model is untouched by all this: its four reference worlds produce
the same fingerprint as before, bit for bit. `python3 test_free.py` checks the
promises above (including the food result over six worlds), and it is part of
`test_all.py` and of the Checks screen.

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

**With learning on it shows both halves of a word.** Down the left, the word
itself — which colour means which state, *inherited*, selected over generations.
Down the right, **what living with that call actually taught them it foretells**
— a bar growing red for dread, green for welcome, with the number and a plain
reading (*dreaded* / *welcomed* / *still just noise*). The pairing is the whole
point of the screen now: a colour's **shape** is evolved, its **meaning** is
lived, and you can see the two side by side. A flock that has never met a
predator shows a full column of *still just noise* — the same words, no
experience to give them weight. (Which particular call picks up the dread varies
between runs; see the note on that in the learning section.)

## Digging deeper

The day-to-day of *building* this - running the measurements, what the numbers
actually say, the checks that guard each claim, and the things that turned out
to be wrong - lives in **[NOTES.md](NOTES.md)**. It is a lab notebook, not a
manual: read it if you want to change the simulation or argue with a figure.

## Parameters: every number, in one place (`P` at startup)

`simulation.py` is deliberately a wall of named constants - each one a decision
about how these creatures work, most of them arrived at by measuring something.
Press `P` on the opening screen to **see that whole wall and change it**, grouped
the way you'd go looking for something rather than by name: senses and distances,
movement, body and energy, reproduction, food and predators, calls and their
meaning, mood, your hand, learning, memory of places, Master Mode.

- `UP`/`DOWN` to move, `LEFT`/`RIGHT` to change (hold `SHIFT` for ×10 steps)
- `BACKSPACE` resets the one under the cursor; `R` resets everything
- **`D` makes the current values your defaults** for every future run
- anything you moved shows in amber next to what it was born as, so you can
  always see how far you have wandered from the original

Two things are worth knowing about how this is built.

**The descriptions are not retyped.** Every constant already carries the comment
explaining it, written next to the code that uses it; `tuning.py` harvests those
out of `simulation.py` at import rather than keeping a second copy that would
drift. So the screen cannot go stale, and there is exactly one place to edit a
parameter's meaning. (Building this found 31 constants with no comment at all -
they got one, which improved the source as well as the screen.)

**Some parameters are shown but locked.** Network shape, feature-vector indices,
token counts, world dimensions and the affect-map grid are not preferences,
they're the shape of the data: a mind's weight matrices are built to a fixed size
and saved minds are restored to it, so changing one mid-flight wouldn't retune
the simulation, it would break it. They're listed anyway - the point is to see
the whole machine in one place - greyed out, each saying *why* it can't move, and
the cursor still walks onto them so you can read them.

**No setting the screen offers can break the world**, and getting that right
took two methods rather than one. Roughly fifteen of these constants are
*divisors*: sliding one to zero isn't an extreme setting, it's a crash - or
worse, `DECIDE_TEMP` at zero yields `NaN` instead of raising, quietly corrupting
every decision a creature makes. Searching the source for `/ NAME` and `% NAME`
found most of them, but missed `HEAR_RADIUS`, which flows into a traits array
that gets divided by later, so its name never appears next to a slash. Sweeping
every parameter to both extremes and running a world found that one - but the
first sweep missed three others purely because it never positioned a hand. Both
methods, then: divisors get a floor above zero, the one constraint that spans
*two* parameters (`MOOD_GLOOM_ONSET` vs `DISTRESS_ENERGY`) is guarded in the
simulation itself, and `test_tuning.py` re-runs the whole sweep - 210 extremes,
warnings promoted to errors so a silent `NaN` fails too - along with a check
that every numeric constant in `simulation.py` is on the screen at all, so a
parameter added later can't quietly go missing from the list that claims to show
everything.

Your defaults live in `thronglets_params.json` next to the save file, holding
**only what differs** from the built-in values - so it stays a readable record of
what you changed, and a parameter you reset disappears from it. Delete the file
and you're back to stock. Nothing else in the codebase knows the screen exists:
it writes into `simulation.py`'s module globals, and the simulation goes on
reading its own constants exactly as before.

## FAQ

A curated in-game FAQ (`?` in pygame - `f` now arms the fire tool - `Shift+F`
in the terminal since lowercase `f` is already the manual food-drop key, an "FAQ" button on the
web page) answers nine questions that actually came up while building and
playing this - why creatures cluster near food they're not eating, whether
distress leads to cooperation, why adaptive metabolism always bottoms out,
how siblings end up with wildly different generation numbers, why a
creature can end up mating with its own descendant, why even a trained
vocabulary can drift, what homonyms are, why a single playthrough isn't
proof of anything, and how the trained-AI language actually differs from
the evolved one. Paginated the same way as the Notice screen.

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
yes loads `language_model.json` from the current folder automatically.

**You don't have to train anything, either.** The project ships a trained
language of its own, `default_language.json`, and that is what the AI-language
option falls back to when you have no `language_model.json` of your own - so it
works out of the box, with no PyTorch and no waiting. A language you trained
yourself always wins; the bundled one is only the default. It is resolved next
to the source files rather than the working directory, so it is found however
you launch the game, and a missing or corrupted copy degrades quietly to the
ordinary evolved-from-scratch language rather than crashing.

It was produced with `train_language.py --episodes 8000 --seed 3 --uniform`,
picked out of a sweep of seeds on two criteria that matter in play:

| state | token |
|---|---|
| idle | **0 - silent** |
| food-call | 3 |
| mate-call | 5 |
| alarm-call | 2 |
| distress-call | 1 |

**No two calls share a colour** - the homonymy that blind evolutionary drift
keeps producing is gone - and **idle maps to silence**, which is the reading you
want: a calm creature simply says nothing, and the field stays quiet until
something is actually worth calling about. Most seeds train to 100% accuracy but
spend token 0 on a state that ought to be audible (a mute food-call, say); this
one spends it on idle. Verified in a real 1500-tick run: every state's token is
used by 100% of the flock, with no audible homonyms.

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
first time you run it locally. The 3D page was driven in a real headless
browser with software WebGL, which checks that it works and how it looks but
not how fast it runs on a real graphics card.
