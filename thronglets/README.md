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
**trust or fear you**, and passes what it learned on to its offspring, so a
kind or cruel run compounds across generations. When it's on, it's shown
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

## Run the measurements yourself (`report.py`)

Every number this project claims came from running worlds headlessly and reading
them. `report.py` puts that instrument in your hands and writes the result to a
file you can send to someone:

```bash
python3 report.py                  # 3 seeds x 1500 ticks, six scenarios
python3 report.py --quick          # 2 seeds x 600 ticks, a rough first look
python3 report.py --seeds 5 --ticks 3000 --out long_run.txt

# try a change without committing to it - your game is untouched
python3 report.py --quick --out before.txt
python3 report.py --quick --set SIGNAL_ALARM_DA=0.25 --out after.txt
```

`--set` is the companion to the tuning screen: the screen is for *playing* with a
value, this is for *measuring* one. Nothing is pinned, but the header records the
change, so two runs make a comparable pair without you having to remember what
you tried. Out-of-range values, locked parameters and unknown names are refused
with the reason.

It plays six scenarios - hunted and unhunted with nobody touching the game, a
hand that only wanders, a hand that feeds, a hand that burns, and learning
switched off as a control - and reports **every metric as mean ± standard
deviation across seeds, with the range**. The spread is not decoration: two
seeds of the same setup routinely differ more than a real effect does, so a
figure without one cannot be argued with. Population, births, deaths, energy
percentiles, mood and its spread, the emotion split, disposition, what the flock
decided to do about you, what a predator came to mean, what each call came to
mean, vocabulary agreement per state, homonyms, evolved traits.

**The file opens with the parameters actually in force**, including anything
pinned in the tuning screen, plus seeds, tick count, versions and the commit.
That header is the most important part: since parameters are now editable, a
measurement that doesn't say what it was measured under is not evidence of
anything.

It closes by **re-measuring the claims this README makes** - and distinguishes
two kinds, because conflating them inverts meanings. A claim that two things come
out *different* (calls only mean something where there was something to learn)
is reported as both sides plus the gap, and passes only if the gap clears the
spread. A claim that something *doesn't happen* (a hand that only moves is not
blamed) is an equivalence test, checked against a threshold with a meaning in the
game - the ±0.05 band the HUD itself calls *"doesn't know you yet"*. Run through
the difference test, that second kind would report "the gap clears the spread"
about two values that are both essentially zero, which reads as the exact
opposite of the claim.

It is not fast - these numbers only exist by living the worlds out. On one
ordinary laptop `--quick` took about 3 minutes and the standard sweep about 14.
Progress prints as it goes so you can tell it from a hang.

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

## Headless check

`simulation.py` has no pygame dependency, so the core can be run and tested
without a display:

```bash
python test_smoke.py
```

This runs several thousand ticks and asserts the population survives and
vocabulary agreement increases — i.e. that a language is actually emerging,
not just that the window doesn't crash. It runs with learning **off**, so it
covers the original core.

The learned mind gets its own check, because **none of it is visible from
watching the game** — a flock whose learning has silently stopped still moves,
still has colours, still breeds; only the numbers show that cruelty has stopped
teaching fear:

```bash
python test_learning.py            # everything, about five minutes
python test_learning.py --quick    # the instant half, a few seconds
```

Each check guards against a failure that actually happened while this was being
built: backpropagation against a directly measured slope; a newborn holding *no*
opinions rather than faint random ones; kindness and cruelty teaching opposite
things; dread reaching a hand that is only *closing in*; one shock correcting the
whole run-up to it; re-living shocks deepening a rare lesson (replay on versus
off, same seed); the flock's own calls meaning something only where there was
something to learn (with predators versus without); a mind surviving save/load
unchanged — **along with the arc of how it got there** — and an older save
degrading gracefully; the flock's decisions accounting for the whole population,
so a divided flock stays distinguishable from an indifferent one; and the flock
still being alive at the end. With learning off, every learned readout must
decline to answer rather than invent one. Every world is seeded, so two runs
print the same numbers.

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
creatures as **big coloured heads on two little feet**, each with an
expressive face (white eyes, nose, mouth) - **the head's colour is the
signal it's emitting** (the same 6-token palette as everywhere else), so
its colour is its status. When a creature actually moves its two feet
**step in time with it** - opposite feet swinging fore and aft and
lifting on each stride, with a matching side-to-side head waddle - while
a standing one just breathes with a gentle bob. Soft contact shadows, a
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

**It starts with eggs.** The world begins empty: you **right-click the
ground to lay the first two eggs** yourself, and they hatch after a few
seconds; every creature born from reproduction afterwards also arrives as
an egg that hatches on its own.

**It's interactive, and the flock learns who you are.** The mouse cursor is
your hand (the opt-in `Mind` from `simulation.py`): **left-click a creature
to select it**, and **right-click for a menu** of care acts (**Feed / Wash
/ Play**) and the episode's dark side (**Stab / Burn / Hit with a rock**).
Kind acts teach that creature - and the ones near enough to witness them -
to approach; cruel ones teach fear and kill **with an animation** (a stab
shudder, a creature wreathed in flame, a rock that squashes it flat).

**Under the hood, each mind is a small neural network that predicts - and
decides from its predictions.** Eight perceptions feed it: how near the hand
is, how hungry the creature is, their product, how crowded it is right here,
how fast the hand is closing in, how near a predator is, how near food is, and
its own agitation. They pass through a hidden `tanh` layer to one output - the
creature's learned estimate of *how good this moment is about to turn out*.

It learns by **temporal-difference reinforcement learning**, trained by real
backpropagation. Every step it measures its own surprise -

> `surprise = reward + γ·(what the next moment looks worth) − (what this one looked worth)`

\- and trains the network to shrink it, so the estimate comes to *predict*
what is coming rather than merely record what came. Because the estimate
**bootstraps** off itself, dread travels **backward in time**: being burned
teaches *"hand on me = agony"*, and TD then quietly teaches *"hand closing on
me = about to be agony."* A mistreated flock learns to **bolt at the approach
rather than at the touch** - anticipation that is learned, never coded. (In a
headless run, a burned flock ends up valuing a *lunging* hand measurably worse
than the same hand sitting still.)

**Nothing scripts what to do about you, either.** To act, a creature looks one
step ahead: it imagines the hand a little nearer and a little further, asks its
own network what each would be worth, and picks between approaching, fleeing
and ignoring by softmax over those imagined values. So a creature flees only
because it *predicts* that closer is worse. Sampling rather than always taking
the best is what keeps it exploring, and it commits to a choice for a moment so
its behaviour reads as intent rather than a twitch.

Two details keep the lessons honest. Learning is driven by **surprise**, not by
raw reward, so an outcome that merely meets expectations teaches nothing and
arbitrary habits never snowball. And a witness learns a lesson **diluted by how
far off it stood**, which is what gives the network its sense that near the hand
is worth much more - or much less - than far from it. A newborn inherits a
blend of its parents' whole network, so hard-won predictions compound across
generations. It stays numpy-only, opt-in, and fully saved/loaded with the world.

**One shock teaches the whole approach, not just its last step.** Learning uses
**TD(λ)**: each moment leaves a fading imprint, and a surprise corrects every
recent moment at once, faded by how long ago it was. So a creature can connect a
blow to the run-up that preceded it from a *single* experience, instead of
needing the sequence over and over. Measured against plain one-step TD, a single
shock moves the *start* of an approach about four times as far.

**The shape of a word is inherited; its meaning is lived.** This is where the
two halves of the project finally meet. *Which* colour a creature cries for
danger is **evolved** - selected over generations, inherited, the thing the
Translator screen reads off. But what that colour **means** - what it predicts
is about to happen - is now **learned**, inside one lifetime, from whatever
actually followed that call. Each creature perceives how loudly every signal
colour is being called nearby, and TD does the rest. A flock that has lived
among predators comes to dread some of its own calls; **a flock that has never
met one hears the very same words as noise.** Measured across three seeds, the
most dreaded call lands at **-0.045** in a world with predators and **-0.002**
in one without - a nineteenfold difference from experience alone, with the words
themselves unchanged. Once a call *does* mean something, hearing it is
frightening in itself: the word moves a creature before the thing it warns of
ever arrives. A newborn values every call at exactly `0.0` - it has no opinions
to begin with, only ones it earned.

That fright shifts the **resting mood**, it is not a jolt. Being called to is a
condition that holds, not an event that happens - and getting that distinction
wrong was a real bug worth recording. Delivering a jolt on every step while the
calling lasted accumulated without bound: measured on an idle world, it produced
**100% of the fear** (16% of the flock afraid with it, **0%** with it disabled)
and shifted the median mood by **±0.2** on its own, swamping hunger, predators
and everything the player did. As a baseline it behaves: dread builds over about
a hundred ticks while the voices keep up, **stops at that baseline instead of
running past it**, and drains away when they stop - at the same `MOOD_DECAY` pace
as every other feeling. A world with nothing to fear now reads as calm (0% afraid,
91% neutral) rather than manufacturing fear out of noise.

One honest limit: *which* call picks up the dread is **not** reproducible. It is
often the alarm call, but not reliably - other calls (distress, for instance)
also ring out when things are going badly, and a creature that hears a warning
is usually close enough to feel the predator itself, so the credit is genuinely
ambiguous. What reproduces is the thing being claimed here: that meaning comes
from experience rather than from inheritance.

For any of that to be learnable, a warning has to tell you something you don't
already know - so a creature now feels a predator only close up
(`PREDATOR_PERCEPTION`), **deliberately shorter than earshot** (`HEAR_RADIUS`).
With perception wider than hearing, as it was before, a call was always
redundant, and the creatures correctly learned it was worthless noise. That is
exactly why alarm calls exist in nature: they extend your senses through others.

**And you can look inside one.** All of this used to run entirely unseen. In the
2D view, hovering a creature (with learning on) now opens a small panel showing
its learned inner life directly: **what it expects of this very moment** (its own
value estimate, as a signed bar), **what it has decided to do about you** -
come to you / get away / ignore you - and how sure it is, **how badly its last
expectation was violated**, and finally **the moments it cannot stop going
over**: its replay buffer, worst first, each named by whatever it was about
(your hand, a predator, food) and coloured by whether it turned out good or
bad. A creature that has been mostly fed and twice burned reads as six green
memories of your hand and two red ones. A row of colour swatches shows **what
the flock's calls have come to mean to this one** - the swatch is the evolved,
inherited word, the bar beside it the meaning it learned for itself. The spatial memory is still painted on
the ground at the same time, so you get the map and the mind together.

**A creature keeps its worst moments, and goes back over them.** Learning only
in the instant wastes the rarest lessons: a burning, or a neighbour taken by a
predator, happens *once*, while the long quiet stretch that follows steadily
erodes it. So each creature carries a handful of the moments that most violated
its expectations - along with what they turned out to be worth - and **re-lives
a couple of them every step**, learning from each many times over. Space is
finite, so a new shock only ever displaces a milder one: what a creature holds
on to is always the worst of what it has lived. (This is prioritised experience
replay, the idea that made deep reinforcement learning work, and here it reads
as rumination.) It is not idle flavour - it is measured: the predator lesson,
which used to fade almost to nothing, comes out **about seven times deeper**
with replay on (−0.05 → −0.40), and the dread of a closing hand doubles.
Memories are *not* inherited and *not* saved with the world - only what they
taught is.

**And you are not the only teacher - the world teaches too.** A predator taking
a neighbour is no longer a silent event: every creature near enough to see it
learns from it, exactly as they learn from your cruelty. The lesson attaches to
*predators*, not to you, so a flock can come to understand what a hunter means
while remaining completely unbothered by a player who has never touched it (in a
headless run: after a life among predators, `V(predator on me)` sits well below
`V(none in sight)`, while the untouched hand stays neutral). The kill also
leaves an **emotional and spatial scar** - fear ripples out through the flock by
contagion, and the ground where it happened is marked as somewhere to shun.

**Flight from a predator, though, stays innate - and that is a finding, not an
oversight.** Making it learned was implemented and measured, and it fails for a
real reason: a creature that must learn to run is eaten *during the lesson*
(the flock collapsed to a single survivor within 500 ticks). Worse, gating a
lethal behaviour on a lagging estimate makes the ecosystem oscillate - at one
setting the learned urge inverted, which would have had creatures walking into
predators. Real prey animals are born with anti-predator reflexes for exactly
this reason. So the reflex is innate; what experience adds is *meaning*, mood
and memory.

**Each creature carries a persistent inner mood** - a real affective state,
not a value recomputed each frame. Following the circumplex model of
emotion, it runs on two slow-moving axes, **valence** (miserable ↔ happy)
and **arousal** (calm ↔ agitated), and it has *momentum*: being fed or
hurt jolts it, deprivation tints it, and it only eases back toward a resting
baseline slowly - so a fright genuinely lingers and contentment fades over
many seconds instead of resetting instantly.

Going hungry shades that baseline, but deliberately does **not** own it. This
flock lives on the edge — in a settled world the median creature holds around
27 energy of 120, and the lower quarter sits *below* the threshold the
simulation itself calls distress — so treating any hunger as misery pinned
essentially every creature to "sad" for life (measured: **94%** of the flock).
The body colour then said nothing, and a player who had only moved their mouse
across the field was left certain they had terrified a flock they had never
once touched. Hunger now only bites as a creature falls toward that distress
line, and even at its worst it stays smaller than a single jolt from being fed
or hurt. That ordering is the point: the mood you *see* is mostly about what has
been **done** to a creature, which is what the colour is there to show, with
deprivation shading it rather than deciding it. Blue now means *this one is
really in trouble* — a world with no predators reads as sad-but-calm (crowded,
underfed), one with predators as frightened-but-fed, and the two are finally
telling you different things. Witnessing something happen to
a neighbour moves your own mood too, and a newborn is born already coloured
by its parents' mood (a nervous flock births nervous young). Moods are also
**contagious**: every moment a creature's feeling drifts a little toward
that of the creatures around it, weighted by how close they are - so a
fright kindled in one animal **ripples out through the flock** over the
following moments (and a returning calm spreads the same way), a travelling
wave rather than an instant hive-mind. That mood
drives what you see: the **expressive little face** (white eyes with
pupils, a nose, a mouth) shows joy / sadness / fear / calm straight from
the valence-arousal plane, and an agitated creature visibly **breathes
faster and trembles** where a calm one is almost still. **The mood also
drives how a creature actually moves**: arousal is its activity level, so
an agitated one darts about restlessly while a listless, low-arousal
(sad or calm) one barely stirs; and valence sets a goal - a terrified
creature **bolts away from your hand**, a content one **drifts toward the
nearest neighbour** to be near company. So you don't just read a face,
you watch a frightened flock scatter and a happy one gather.

**Each creature also keeps a mental map of the world.** On top of a feeling
about the hand, a mind remembers *where* good and bad things happened - a
coarse affect map of the ground. Being hurt stains the spot it happened on;
finding food (or watching a neighbour thrive there) marks a place as worth
returning to. The map fades slowly, steers movement only through the cells
right around a creature (a distant memory can't teleport it), and is
**partly inherited**, so a lineage can come to shun the very ground where
its ancestors were killed. **Select a creature and its map is painted on
the ground** - green over places it trusts, red over places it fears -
literally its consciousness made visible; the map is saved and restored
with the game. A 2D HUD shows the
season/weather/clock/population, the flock's overall feeling toward you
(*"the flock trusts you (+45%)"*), and a panel for the selected creature
with its live mood (emotion, valence, arousal). The mood rides along with
save/load, so a traumatised or happy flock is still that way when you
resume. Little touches of life round it out:
the canopies sway, the creatures bob, birds drift overhead, the lake mirrors
the sky, and shadows lengthen with the low sun.

`moderngl` is the one extra dependency and it is only imported when you run
this file, so the other renderers keep working with just numpy + pygame.

Controls: `LEFT-drag` orbits the camera, the scroll wheel zooms, **left-
click a creature** to select it, **right-click a creature** for its
care/harm menu, **right-click bare ground** to lay one of the first two
eggs, `S` cycles the season, `W` cycles the weather, `T` toggles fast time,
`ESC` quits. (On a machine without a GPU the scene still renders through Mesa's
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
first time you run it locally. `main_gl.py`'s scene is rendered off-screen
through Mesa's software OpenGL (llvmpipe under a virtual framebuffer) to
check the look across seasons and weather.
