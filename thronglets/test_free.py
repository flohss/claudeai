"""Headless checks for the no-code model (World(free=True)).

The game offers two models side by side. The classic one writes the creatures'
instincts by hand; the no-code one writes none and lets an inherited brain find
its own behaviour. The promises checked here are the ones a player relies on:

  * choosing one model never disturbs the other (the classic model must behave
    exactly as it did before the second one existed);
  * a no-code world really has no hand-written behaviour to fall back on;
  * a no-code world survives a save and a reload;
  * and the headline claim - that creatures born with random brains end up
    walking toward food without anyone telling them to - holds over several
    worlds, not one lucky one.

    python3 test_free.py            # everything (about a minute)
    python3 test_free.py --quick    # skip the multi-world evolution check
"""

import argparse
import os
import statistics
import sys
import tempfile

import numpy as np

import simulation as S

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""), flush=True)
    if not ok:
        FAILED.append(name)


def _snapshot(world):
    return (world.tick, world.births, world.deaths,
            tuple(round(float(v), 9) for c in world.creatures for v in (c.pos[0], c.pos[1], c.energy)))


def test_classic_untouched():
    """A classic world carries no brain, no rescue and none of the bookkeeping."""
    w = S.World(init_pop=30, seed=3)
    for _ in range(300):
        w.step()
    check("classic creatures carry no brain", all(c.genome.brain is None for c in w.creatures))
    check("classic world brings in no newcomers", w.immigrants == 0)
    check("classic world has no probe to report", w.free_probe() == (None, None))
    a, b = S.World(init_pop=30, seed=3), S.World(init_pop=30, seed=3, free=False)
    for _ in range(300):
        a.step(); b.step()
    check("classic run is repeatable", _snapshot(a) == _snapshot(b) == _snapshot(w))


def test_free_basics():
    w = S.World(init_pop=40, seed=5, free=True)
    check("every founder has a brain", all(c.genome.brain is not None for c in w.creatures))
    seek, flee = w.free_probe()
    check("random founders neither seek food nor flee hunters",
          abs(seek) < 0.15 and abs(flee) < 0.15, f"seek {seek:+.2f}, flee {flee:+.2f}")
    for _ in range(600):
        w.step()
    check("children inherit a brain", all(c.genome.brain is not None for c in w.creatures))
    check("nothing went non-finite",
          all(np.isfinite(c.pos).all() and np.isfinite(c.energy) for c in w.creatures))
    check("the world is kept alive", w.population() > 0)
    check("the vocabulary panel has something to show",
          any(pairs for pairs in w.vocabulary_breakdown().values()))
    try:
        S.World(init_pop=5, seed=1, free=True, learning=True)
        check("the two models cannot be mixed", False)
    except ValueError:
        check("the two models cannot be mixed", True)
    added = w.add_creature(10, 10)
    check("a creature added by hand gets a brain too", added is None or added.genome.brain is not None)


def test_save_load():
    w = S.World(init_pop=30, seed=9, free=True, adaptive_traits=True)
    for _ in range(400):
        w.step()
    path = os.path.join(tempfile.mkdtemp(), "free.json")
    S.save_world(w, path)
    r = S.load_world(path)
    check("a reloaded world is still no-code", r.free and not r.learning)
    alive = [c for c in w.creatures if c.alive]
    same = len(alive) == len(r.creatures) and all(
        np.allclose(a.genome.brain[0], b.genome.brain[0]) and np.allclose(a.genome.brain[1], b.genome.brain[1])
        for a, b in zip(alive, r.creatures))
    check("every brain comes back as it was saved", same)
    check("the gauges and the rescue count come back",
          r.immigrants == w.immigrants and r.free_probe() == w.free_probe())
    for _ in range(100):
        r.step()
    check("a reloaded world keeps running", r.population() > 0)


def test_emergence(seeds=6, ticks=15000):
    """The claim itself. Bar: the average gain must clear twice the spread
    between worlds - the same rule every other measurement in the project uses."""
    gains = []
    for seed in range(seeds):
        w = S.World(init_pop=60, seed=seed, free=True)
        before = w.free_probe()[0]
        for _ in range(ticks):
            w.step()
        after = w.free_probe()[0]
        gains.append(after - before)
        print(f"    world {seed}: to food {before:+.2f} -> {after:+.2f}", flush=True)
    mean, sd = statistics.mean(gains), statistics.stdev(gains)
    check("brains born random come to walk toward food, on their own",
          mean > 2 * sd and mean > 0.3, f"gain {mean:+.2f}, spread {sd:.2f}, bar {2 * sd:.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true", help="skip the multi-world evolution check")
    args = ap.parse_args()
    for test in (test_classic_untouched, test_free_basics, test_save_load):
        print(test.__name__, flush=True)
        test()
    if not args.quick:
        print("test_emergence", flush=True)
        test_emergence()
    print(f"\n{'ALL OK' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
