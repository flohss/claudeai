# Thronglets - notes from the workbench

Everything this project claims about itself came from running worlds headlessly
and reading the numbers. This file is where that work lives: how to run the
measurements yourself, what they say, the checks that guard each claim, and -
kept deliberately - the hypotheses that turned out to be wrong.

The [README](README.md) describes the game. This describes how we know what it
does.

**Measurement debt, incurred and paid.** Cultural transmission landed inside the
very path several published figures were measured on, so they were re-measured
on the current code rather than assumed:

- *Dreaded call*: means barely moved (-0.047 / -0.004 over eight seeds, was
  -0.045 / -0.002 before culture) but the between-world spread roughly tripled
  at small samples - culture amplifies whatever each world happened to learn.
  Consequence: on a default 3-seed run, report.py's own claims section can now
  flag this one as "unproven" purely from the sd estimate; at eight seeds it
  clears the bar cleanly (gap 0.043 vs a 2-sigma bar of 0.033) with no overlap
  between the sixteen worlds. If that claim matters to you, run --seeds 8.
- *Kindness vs cruelty*: the gap GREW under culture (+0.43 vs +0.28) - culture
  amplifies what you teach, in both directions.
- *Runtimes*, machine alone on current code: --quick 3m13, standard sweep
  12m39. The earlier "about 3 / about 14" were close but predate culture.

The general lesson stands: a measured claim describes the code it was measured
on. When the simulation changes inside a measured path, the figure is debt until
it is re-run.

## Why trust kills: deaths now carry a cause

`deaths` was a single number, which cannot answer the one question worth asking
when a population moves: predators, or hunger? It is now split four ways -
`predator`, `starved`, `age`, `killed` (by your own hand) - reconciling exactly
with the total, carried through a save, and reported by `report.py` as
`died_predator` and friends. Hunger and old age had shared a single branch and
so were indistinguishable; starving young and dying full of years are not the
same event for a flock.

The first thing it measured corrected the story this project had been telling.
Feeding the flock does gather them into danger - **predator kills rise 61%**
(55.0 alone against 88.8 when fed, over four seeds x 2000 ticks, higher in
4/4). They pick "approach" far more often, they cluster around a wandering hand,
and the predators eat well.

But they also **starve less** (128.8 -> 114.8) and **breed more** (202.5 ->
223.2), and the two effects cancel: final population 78.8 ± 6.2 alone against
79.8 ± 7.3 fed. Feeding does not thin the flock here, it *changes what kills
them* - trading famine for predation.

Which means the earlier claim that kindness collapses populations was
overstated. That figure (42.7 ± 26.8, with one world in eight dying out) came
from `report.py`'s three-seed default, and its enormous spread was the warning:
the collapse is a tail event, not the typical outcome. Four seeds at 2000 ticks
produced no collapse at all. What is solid is the cause shift; what is not is
the death toll.

## Knowledge that pays: dread now makes flight harder

Until now, everything a creature learned went into what it *felt* - mood, the
colour of its body, which call it answered - and none of it into whether it
lived. A flock could understand predators perfectly and die at exactly the rate
of a flock that understood nothing. That is a real gap in an artificial-life
game: knowing is supposed to be worth something.

Wiring it up naively had already been tried, and the source still carries the
warning: *"a creature that must learn to run is eaten during the lesson"* - the
flock fell to one survivor in 500 ticks. The failure was in **replacing** the
innate reflex with a learned one, so this arrangement never touches it.
`FLEE_STRENGTH` is a floor. A creature reads its own value head twice - once for
a world with a predator on it, once without - and the gap is its `dread`. That
dread scales a *bonus*: `KNOWLEDGE_FLEE_GAIN = 0.6` at `KNOWLEDGE_FLEE_FULL =
0.25` of dread, refreshed every `KNOWLEDGE_REFRESH = 60` ticks and staggered by
creature id so the whole flock never recomputes on the same tick. An ignorant
creature is bit-for-bit as fast as it was; there is no lesson to survive.

Five seeds x 2500 ticks, gain 0.0 against 0.6:

| | 0.0 | 0.6 | gap | 2x largest spread |
|---|---|---|---|---|
| population | 78.4 ± 8.1 | 95.4 ± 6.1 | **+17.0** | 16.3 → shown |
| died_predator | 81.2 ± 19.0 | 50.0 ± 12.3 | −31.2 | 38.0 → not shown |
| died_starved | 155.2 | 160.6 | +5.4 | — |
| speed trait | 1.759 | 1.857 | +0.098 | — |

The flock is bigger, and that clears the bar. The obvious *mechanism* - fewer
creatures eaten - does not, even though it fell in 5/5 seeds, because kills
scatter far more between worlds than population does. Reporting the direction
without the claim is the honest version. Two side effects worth watching: harder
running costs energy, so starvation ticks up, and the inherited speed trait
drifts upward - selection appears to be favouring runners, which is the kind of
feedback loop that needs a much longer run before anyone calls it evolution.

## "Food is still read negatively" - two answers, only one of them a bug

Reported from play, four times over. Each earlier answer was a story built on
one measurement; this one separates two things that were being confused.

**What the creature learned.** `V(food right here) - V(nothing)` measured
**-0.0015 +/- 0.0230** over 5 seeds x 2500 ticks. Zero. Food was never read
negatively - the learned value simply had no opinion.

**What the game displayed.** Memories labelled "food" sat at **-0.26** and were
**43% of everything a creature ruminates on**. That is what a player actually
sees, so the report was right even though the premise was not.

The label was picking the strongest perception, and the perception radii are
not comparable - food 60 world units, hand 48, predator 26. Food is the loudest
thing in view in 47% of living moments, so it collected the blame:

| | old rule | new rule |
|---|---|---|
| memories labelled food | 42.8% | 21.2% |
| ...with a predator in sight | 35.1% | **0.0%** |
| their average target | -0.261 | -0.193 |

Inside the old food group the value tracked predator proximity at **-0.52** and
food proximity at **+0.04**. The food was scenery. A memory is now named for the
event: perceptible predator > hand > food, and food only when nothing else is
there.

That alone left food at -0.193 against -0.204 for memories about nothing at all
- no worse than an empty moment, but still nothing to like. The cause was a
reward scale nobody had checked: a meal moved the estimate by `REWARD_EAT x
(1 - GAMMA)` = **+0.012**, a predator by **-0.48**. Eating was one fortieth of
being hunted. Swept:

| REWARD_EAT | V(food) | population | eaten | starved | flee share |
|---|---|---|---|---|---|
| 0.4 | -0.002 ± 0.023 | 89.4 ± 7.4 | 44.0 ± 6.8 | 182.2 ± 5.2 | 0.341 |
| 1.5 | +0.028 ± 0.019 | 91.0 ± 8.0 | 40.8 ± 9.1 | 185.6 ± 9.7 | 0.326 |
| **4.0** | **+0.067 ± 0.021** | 95.0 ± 7.5 | 51.8 ± 16.6 | 171.8 ± 10.2 | 0.340 |

4.0 is the lowest value tried whose reading clears the bar (gap +0.069 against
2x the largest spread, 0.046); 1.5 does not. Nothing else moved demonstrably -
population, kills and starvation all stayed inside their spreads, the flee share
did not budge, and the hand's standing stayed at -0.01, so this did not buy
warmth toward the player by the back door. Kills drifted up (44.0 -> 51.8) with
a spread far too wide to call, which is the direction to watch: a flock that
values food more may cluster on it more.

With both changes, food memories sit at **-0.062** and **43% of them are
positive**, against 3% of predator memories. The panel can finally show a
creature that something good happened to it.

## The predicted side effect: "a predator, +0.28" in green

Reported straight after the reward change, and correctly anticipated as a
consequence of it. A meal is banked with `reinforce()` and paid into the NEXT
step's TD error, which corrects the value of the state the creature was IN. If
a hunter was within perception at that moment, `F_PREDATOR` was lit in that
same state, so the credit spreads across everything that was on. There is no
way to separate them inside one perception vector.

**14.4%** of meals are taken with a hunter within perception (measured by
hooking the eater itself - a first attempt measured whether *anyone* was near a
predator on a tick where *any* food was eaten, which is ~1 by construction and
means nothing), and **32.7%** of kept food memories have a hunter in them too.

The first question was whether this is cosmetic or whether it had eaten into
the flock's dread - which since two commits earlier drives how hard they run,
so a poisoned `V(predator)` costs lives. It has not, over 5 seeds x 2500 ticks:

| | REWARD_EAT 0.4 | REWARD_EAT 4.0 | gap | bar |
|---|---|---|---|---|
| V(predator) | -0.2779 ± 0.0157 | -0.2976 ± 0.0368 | -0.020 | 0.074 → not shown |
| mean dread | 0.2611 ± 0.0207 | 0.2822 ± 0.0338 | +0.021 | 0.068 → not shown |
| avg predator memory | -0.4764 | -0.4782 | — | — |
| **positive predator memories** | **1.1%** | **3.6%** | — | — |
| most positive one | +0.285 | +0.276 | — | — |

So the learning is intact, and if anything a shade more afraid. What tripled is
purely how often the panel prints a green line next to "a predator" - and the
worst offender is the same size as it always was. The leak predates the reward
change; the bigger reward only made it visible.

The fix is therefore in the wording, not the simulation. A hunter can never
*make* a moment good: the only lesson predators hand out is `teach(-prox, ...)`
and they give no reward at all, so a moment that turned out better than
expected with a hunter in frame was driven by something else in it. **A good
surprise therefore never gets the predator's name** - it falls through to
whatever else was in the frame. Afterwards:

| the panel shows | n | share | mean | green |
|---|---|---|---|---|
| a predator | 1254 | 39.7% | -0.502 | **0.0%** |
| food | 992 | 31.4% | -0.056 | 44.7% |
| a moment | 911 | 28.9% | -0.186 | 21.7% |

A first attempt gave those moments their own label, "despite a hunter", on the
grounds that a meal snatched under a hunter's nose is a real thing worth
naming. That was rejected: the panel's vocabulary is four words and it should
stay four words. The 42 displaced memories land where they belong anyway - on
the meal that drove them, or on "a moment", which has always been what this
panel says when the flock cannot credit a shock to anything it can name.

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

### The same thing without the terminal: press T at startup

The Measure screen runs `report.build_report` - *the same function* the command
line calls, not a second copy of it, because two screens computing the same
numbers by two routes end up disagreeing and you cannot tell which to believe.
You pick which of the seven tests to run, the seeds and the ticks, and it writes
`thronglets_report_<date>.txt` beside the game.

What it adds over the command line is the part the command line cannot give you:
**what the run will cost, before you start it.** While you are still choosing, a
background thread is timing a real world built the way the report builds them -
same starting population, learning on, predators in - and the screen shows this
machine's actual rate and the estimate that follows from it. Over an hour it
turns orange and says so.

That exists because of a specific near-miss. Asked for "the biggest test
possible", the answer that came back was `--seeds 16 --ticks 200000`, which
nobody had multiplied out: 7 x 16 x 200000 is **22.4 million ticks**, and at the
43 ticks/second measured on the machine it was suggested from, **146 hours**.
Six days. The arithmetic is trivial and invisible, and a terminal will start
that run without a word.

Picking a subset means some claims cannot be checked - a claim is a comparison
and needs both its sides. The report lists those under `NOT CHECKED` with the
scenarios that were missing, rather than quietly checking fewer claims than it
appears to.

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

## How a lesson fades, and the culture that slows it

Inheritance leaking is deliberate - it really is lossy in life. What was missing
was the other half. Real populations tolerate lossy inheritance because **the
living re-transmit knowledge to each other constantly**, and until recently these
creatures had no such channel at all: `OBSERVE_RATE` fires only inside
`deliver_experience`, so nothing let a creature that knew something teach one
that didn't. The leak was never refilled.

**They have a culture now.** Every step, a creature edges its appraisal of the
moment it is living toward what its neighbours make of theirs (`CULTURE_RADIUS`,
`CULTURE_RATE`) - standing close, they see much the same scene, so their
judgement is evidence about it. This is learning from the demeanour of those
around you, which is how a fear of something outlives everyone who ever met it.
Measured against the same experiment: teaching a flock and then withdrawing your
hand forever, culture **nearly tripled** how far the lesson reached (peak +0.054
to +0.159) and more than doubled what remained 3000 ticks later (+0.017 to
+0.040).

Three properties keep it from becoming an echo chamber, and getting them right
took two failed attempts worth recording:

- **It averages**, so it can never push a belief past the strongest neighbour. A
  flock that was taught nothing stays at nothing - hearsay cannot manufacture
  evidence, and a check asserts it.
- **It is weighted by conviction.** Plain proximity-weighted averaging is
  diffusion: when only a few have been taught, the many who have not drag them
  back toward ignorance harder than they pull anyone forward. It measurably made
  things *worse*. Weighting each neighbour by how pronounced its appraisal is
  fixes the direction of flow - a creature with nothing to say says nothing.
- **It never touches the replay buffer.** `teach()` normally files a moment as a
  lesson worth re-living, but this fires every step for every creature and the
  buffer holds only `REPLAY_SIZE` moments, so it was evicting the rare shocks
  the buffer exists to preserve. That single side effect wrecked both the feature
  *and* the control run measuring it, until the buffer became the suspect. Hence
  `teach(..., keep=False)`.

### Cruelty is fewer memories, and deeper

A creature keeps only its `REPLAY_SIZE` most shocking moments and re-lives them.
Look inside those buffers after a session and the asymmetry is stark - measured
over five seeds, and it clears this project's own bar by six times the spread:

| | memories that contain your hand | disposition reached |
|---|---|---|
| you burn them | **25.3% ± 5.2** | **-0.219 ± 0.032** |
| you feed them | **66.5% ± 6.7** | +0.112 ± 0.028 |

A fed flock holds **2.6x more** memories of you, yet a burned flock arrives at a
feeling **twice as strong**. Per memory, cruelty is roughly **five times** as
potent. Five seeds out of five, no exceptions.

The reason is behavioural, and nobody wrote it: a fed creature *comes to you* (it
picks "approach" 48% of the time against 33% at rest), so it accumulates
experience of you. A burned one *flees*, and stops gathering evidence about you
at all. **Cruelty teaches avoidance, and avoidance prevents you from ever
learning that someone might mean you well.**

This is also why fear is far more reproducible than trust - the spread on a
burned flock's disposition is 0.032 against 0.071 for a fed one, and 7.5 against
16.5 on how much survives 3000 ticks later. A handful of violent lessons all
point the same way; trust depends on how much contact happened to accumulate,
which is luck.

Two hypotheses died on the way to this. The replay buffer is **not** inherited
(`inherit()` returns a fresh one), so it cannot carry a trauma past the death of
whoever lived it - and it turned out not to be preferentially filled by trauma
either, but by kindness. The measurement inverted the guess in both directions.

What culture does **not** do is defeat the decay, and that is the honest limit:
diffusion spreads what exists, it cannot generate. Stop teaching and the 15%
per-birth leak still drains the total to zero, just from a much larger starting
pool and more slowly.

The obvious next move - raise `INHERIT_BLEND` too - was tried and **does not
survive measurement**, which is worth recording because the first run was so
convincing. On one seed, 0.99 produced a lesson that kept *growing* after the
hand withdrew (+0.071 at its peak, +0.109 six thousand ticks later) and still
held +0.032 at 24,000 ticks where everything else sat at zero. On five seeds it
falls apart: 0.99 beats 0.85 at +12,000 ticks on **three of five**, two of them
end negative, and the mean gap of +0.013 is dwarfed by a spread of 0.030. By the
standard this project applies everywhere else - an effect counts only if it
clears twice its spread - that is **unproven**. What does hold across seeds is
the shorter horizon: at +3000 and +6000 ticks 0.99 retains far more (+0.066 vs
+0.026, +0.060 vs +0.005). So `INHERIT_BLEND` is left at 0.85. Both constants
are in the `P` screen if you want to explore further, but do it on several seeds:
the single-seed result here was beautiful and wrong.

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
print the same numbers **on the same machine** - but not across machines. Running
the identical seeds on Linux (numpy 2.4.6) and Windows (numpy 2.5.1) produced
visibly different worlds: 190 deaths against 198, and a flock that died out on
one machine while surviving on the other. The random stream is the same;
floating-point arithmetic is not, and this simulation is chaotic enough that a
last-bit difference compounds into a different history. What crosses machines is
the *effects*: the learned value of a predator agreed to within 0.003, the most
dreaded call to within 0.004, and all five claims held on both. That is the
better guarantee, and the reason `report.py` averages over seeds and prints
spreads instead of quoting single worlds.
