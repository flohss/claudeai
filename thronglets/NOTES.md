# Thronglets - notes from the workbench

Everything this project claims about itself came from running worlds headlessly
and reading the numbers. This file is where that work lives: how to run the
measurements yourself, what they say, the checks that guard each claim, and -
kept deliberately - the hypotheses that turned out to be wrong.

The [README](README.md) describes the game. This describes how we know what it
does.

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
