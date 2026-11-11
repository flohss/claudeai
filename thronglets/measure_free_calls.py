"""Do calls matter in the no-code model? (python3 measure_free_calls.py)

Runs the same no-code worlds twice: once normally, once DEAF (creatures still
call and still pay for it, but no call reaches any brain). If calls carried
anything useful, the hearing worlds would do better. Prints, per arm, the
average flock size over the last part of the run and the spread between worlds;
a difference only counts if it clears twice the larger spread.

    python3 measure_free_calls.py --seeds 12 --ticks 40000
"""

import argparse
import statistics

import numpy as np

import simulation as S


def run(seed, deaf, ticks, last):
    w = S.World(init_pop=60, seed=seed, free=True)
    w.free_deaf = deaf
    pops, talk = [], []
    for t in range(1, ticks + 1):
        w.step()
        if t > ticks - last:
            alive = w._alive()
            pops.append(len(alive))
            if t % 50 == 0 and alive:
                talk.append(np.mean([c.token != 0 for c in alive]))
    return float(np.mean(pops)), float(np.mean(talk)) if talk else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--ticks", type=int, default=40000)
    args = ap.parse_args()
    last = max(1, args.ticks * 3 // 8)
    arms = {False: [], True: []}
    for seed in range(args.seeds):
        for deaf in (False, True):
            pop, talk = run(seed, deaf, args.ticks, last)
            arms[deaf].append(pop)
            print(f"world {seed:>2} {'deaf   ' if deaf else 'hearing'}  flock {pop:5.1f}  calling {talk:4.0%}",
                  flush=True)
    mh, md = statistics.mean(arms[False]), statistics.mean(arms[True])
    sh, sd = statistics.stdev(arms[False]), statistics.stdev(arms[True])
    bar = 2 * max(sh, sd)
    print(f"\nhearing {mh:.1f} +- {sh:.1f}   deaf {md:.1f} +- {sd:.1f}   gap {mh - md:+.1f}   bar {bar:.1f}")
    print("calls help the flock" if mh - md > bar else
          "calls hurt the flock" if md - mh > bar else
          "NOT SHOWN: hearing makes no measurable difference")


if __name__ == "__main__":
    main()
