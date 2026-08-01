"""Run the measurements yourself and get a full numeric log out.

Everything in this project that claims a number - the README, the commit
messages, the answers to "why are they doing that?" - came from running worlds
headlessly and reading them. This puts the same instrument in your hands: one
command, a text file, every figure with its spread across seeds.

    python3 report.py                  # the standard sweep: 3 seeds x 1500 ticks
    python3 report.py --quick          # 2 seeds x 600 ticks, a rough first look
    python3 report.py --seeds 5 --ticks 3000 --out long_run.txt

To try a parameter WITHOUT committing to it, --set changes it for that run only:

    python3 report.py --quick --out before.txt
    python3 report.py --quick --set SIGNAL_ALARM_DA=0.25 --out after.txt

Nothing is pinned and your game is untouched, but the header records what was
tried - so the two files are a comparable pair without having to remember what
you changed. Values outside a parameter's safe range, locked parameters and
unknown names are all refused with the reason.

It is not fast, because there is no shortcut: these numbers only exist by living
the worlds out. Timed on one ordinary laptop: --quick about 3 minutes, the
standard sweep about 14. Yours will differ. Progress prints to the terminal as it
goes, so you can tell it apart from a hang.

The file it writes is meant to be *sent to someone*, so it is self-contained:
it opens with the parameters actually in force (including any you pinned in the
tuning screen), the seeds, the tick count and the versions - because a number
measured under changed parameters means nothing without them, and a log that
does not say so is worse than no log.

Every figure is reported as mean +/- standard deviation across seeds, with the
range, because a single run of a stochastic world tells you very little: two
seeds of the same setup routinely differ more than a real effect does. Where a
claim is a COMPARISON (calls only mean something where there was something to
learn), both sides are run and the gap is reported with both spreads, so you can
see whether the gap is bigger than the noise.
"""

import argparse
import datetime
import os
import platform
import statistics
import subprocess
import sys

import numpy as np

import simulation as S
import tuning as T
from i18n import STATE_LABELS

STATE_ORDER = (S.DANGER, S.FOOD, S.DISTRESS, S.MATE, S.IDLE)
ACT_NAMES = {S.ACT_APPROACH: "approach", S.ACT_FLEE: "flee", S.ACT_IGNORE: "ignore"}


# --- running one world ------------------------------------------------------

def play(seed, ticks, hand="none", act=None, hunted=True, learning=True,
         adaptive=True, per_step=2, master=False, break_every=0):
    """One life, played a particular way.

    `hand` is how the cursor behaves: "none" (you never touch the game),
    "idle" (it sits still in the middle), or "wander" (it drifts through the
    flock the way a real hand does). `act` is what you do to whoever is within
    reach - +1.0 feeds, -1.0 burns, None just watches. That split matters: a
    hand that only moves and a hand that acts teach completely different
    lessons, and conflating them is the mistake that makes people think the
    flock fears them for nothing."""
    world = S.World(init_pop=60, seed=seed, learning=learning,
                    adaptive_traits=adaptive, manual_predators=not hunted)
    world.master_mode = master
    rng = np.random.default_rng(seed)
    pos = np.array([S.WIDTH * 0.5, S.HEIGHT * 0.5])
    for _ in range(ticks):
        if hand != "none":
            if hand == "wander":
                pos = np.clip(pos + rng.normal(0, 1.6, 2), [0, 0], [S.WIDTH, S.HEIGHT])
            world.hand_pos = pos
            if act is not None:
                alive = [c for c in world.creatures if c.alive]
                reach = [c for c in alive
                         if np.linalg.norm(np.asarray(c.pos) - pos)
                         < S.HAND_PERCEPTION * 0.5]
                for c in reach[:per_step]:
                    world.deliver_experience(c, act)
        # Master Mode is a whole game mode; leaving it out of the report meant
        # obedience, unrest and uprisings were never measured at all
        if break_every and world.tick % break_every == 0:
            alive = [c for c in world.creatures if c.alive and c.mind is not None]
            if alive:
                world.dominate(alive[int(rng.integers(len(alive)))], 0.35)
        world.step()
    return world


def measure(world):
    """Everything worth knowing about a world, as flat named numbers."""
    alive = [c for c in world.creatures if c.alive]
    out = {"population": len(alive), "births": world.births, "deaths": world.deaths}
    # a bare death count cannot say whether a collapse was predation or hunger
    for cause, n in getattr(world, "deaths_by", {}).items():
        out[f"died_{cause}"] = float(n)
    if not alive:
        return out

    energy = np.array([c.energy for c in alive])
    out["energy_mean"] = float(energy.mean())
    for pct in (10, 25, 50, 75, 90):
        out[f"energy_p{pct}"] = float(np.percentile(energy, pct))
    out["hunger_mean"] = float(1.0 - energy.mean() / S.MAX_ENERGY)

    ages = np.array([c.age for c in alive])
    out["age_mean"] = float(ages.mean())

    # language: how far the flock has agreed on a word for each state
    for state, (_token, share) in world.vocabulary().items():
        out[f"agree_{STATE_LABELS['en'][state]}"] = float(share)
    claimed = [tok for tok, (st, _s) in
               ((tok, cl[0]) for tok, cl in world.translator().items() if cl)]
    out["homonyms"] = float(len(claimed) - len(set(claimed)))

    if world.adaptive_traits:
        traits = np.array([c.genome.traits for c in alive])
        for i, name in enumerate(("speed", "vision", "hearing", "metabolism")):
            out[f"trait_{name}"] = float(traits[:, i].mean())

    # how deep the family tree has grown - a run that never breeds looks
    # identical to one that breeds constantly on population alone
    gens = [world.lineage[c.id]["gen"] for c in alive if c.id in world.lineage]
    if gens:
        out["generation_mean"] = float(np.mean(gens))
        out["generation_max"] = float(max(gens))

    minds = [c.mind for c in alive if c.mind is not None]
    if not minds:
        return out

    valence = np.array([m.valence for m in minds])
    arousal = np.array([m.arousal for m in minds])
    out["valence_mean"] = float(valence.mean())
    out["valence_median"] = float(np.median(valence))
    out["valence_sd_within"] = float(valence.std())
    out["arousal_mean"] = float(arousal.mean())
    out["arousal_sd_within"] = float(arousal.std())
    emotions = [m.emotion() for m in minds]
    for name in ("joy", "neutral", "sad", "fear"):
        out[f"felt_{name}"] = emotions.count(name) / len(emotions)

    disp = world.disposition_summary()
    if disp is not None:
        out["disposition"] = disp
    choices = world.choice_summary()
    if choices:
        for act, frac in choices.items():
            out[f"chose_{ACT_NAMES[act]}"] = frac

    # what the flock learned the world means
    near = np.mean([m.value(S.Mind.features(0, 0.2, 0, 0, predator=1.0)) for m in minds])
    far = np.mean([m.value(S.Mind.features(0, 0.2, 0, 0, predator=0.0)) for m in minds])
    out["predator_means"] = float(near - far)
    meanings = world.signal_meanings() or {}
    if meanings:
        out["call_most_dreaded"] = min(meanings.values())
        out["call_most_welcome"] = max(meanings.values())
        for token, value in sorted(meanings.items()):
            out[f"call_{token}_means"] = value
        # do they AGREE about what a call means, or is the average hiding a
        # flock that has learned five different things?
        spread = [float(np.std([m.signal_meaning(t) for m in minds])) for t in meanings]
        out["call_disagreement"] = float(np.mean(spread))

    # dread reaching a hand that is only CLOSING IN is a headline claim of this
    # project and was missing from the log entirely
    still = np.mean([m.value(S.Mind.features(0.6, 0.2, 0.0, 0.0)) for m in minds])
    lunging = np.mean([m.value(S.Mind.features(0.6, 0.2, 0.0, 1.0)) for m in minds])
    out["hand_still_worth"] = float(still)
    out["hand_lunging_worth"] = float(lunging)
    out["anticipation_gap"] = float(still - lunging)

    # the map of good and bad places each creature carries
    memory = np.array([m.memory for m in minds])
    out["places_marked_good"] = float((memory > 0.05).mean())
    out["places_marked_bad"] = float((memory < -0.05).mean())
    out["places_strongest_mark"] = float(np.abs(memory).max())

    # Master Mode
    ob = world.obedience_summary()
    if ob is not None:
        out["obedience"] = ob
        out["broken_fraction"] = float(np.mean([m.obedience > 0.01 for m in minds]))
        unrest = world.master_unrest()
        if unrest is not None:
            out["unrest"] = unrest

    # where the relationship travelled, not just where it ended up
    arc = list(world.disposition_history)
    if len(arc) > 1:
        out["disposition_start"] = float(arc[0])
        out["disposition_end"] = float(arc[-1])
        out["disposition_lowest"] = float(min(arc))
        out["disposition_highest"] = float(max(arc))
    return out


# --- aggregating across seeds ----------------------------------------------

def across(runs):
    """mean, sd, min, max for each metric over a list of per-seed measurements.

    Metrics missing from some runs (a world that died out has no moods) are
    averaged over the runs that HAVE them, and the count is reported, rather
    than being silently treated as zero."""
    keys = []
    for run in runs:
        for k in run:
            if k not in keys:
                keys.append(k)
    stats = {}
    for k in keys:
        vals = [r[k] for r in runs if k in r]
        stats[k] = {
            "n": len(vals),
            "mean": statistics.fmean(vals),
            "sd": statistics.stdev(vals) if len(vals) > 1 else 0.0,
            "min": min(vals),
            "max": max(vals),
        }
    return stats


def table(stats, seeds_n):
    lines = [f"  {'metric':<24} {'mean':>11} {'sd':>10} {'min':>11} {'max':>11}"]
    lines.append(f"  {'-' * 24} {'-' * 11} {'-' * 10} {'-' * 11} {'-' * 11}")
    for k, s in stats.items():
        flag = "" if s["n"] == seeds_n else f"  (n={s['n']})"
        lines.append(f"  {k:<24} {s['mean']:>11.4f} {s['sd']:>10.4f} "
                     f"{s['min']:>11.4f} {s['max']:>11.4f}{flag}")
    return lines


# --- the scenarios ----------------------------------------------------------

SCENARIOS = [
    ("hunted, you never touch it", dict(hand="none", hunted=True)),
    ("unhunted, you never touch it", dict(hand="none", hunted=False)),
    ("hunted, hand wanders (no acts)", dict(hand="wander", hunted=True)),
    ("hunted, hand feeds", dict(hand="wander", act=+1.0, hunted=True)),
    ("hunted, hand burns", dict(hand="wander", act=-1.0, hunted=True)),
    ("hunted, learning OFF (control)", dict(hand="none", hunted=True, learning=False)),
    ("MASTER MODE, breaking wills", dict(hand="wander", hunted=False, master=True,
                                         break_every=120)),
]


def header(seeds, ticks):
    out = ["=" * 78,
           "THRONGLETS - measurement report",
           "=" * 78,
           f"generated   {datetime.datetime.now().isoformat(timespec='seconds')}",
           f"seeds       {list(seeds)}",
           f"ticks       {ticks} per world",
           f"python      {platform.python_version()}   numpy {np.__version__}",
           f"platform    {platform.platform()}"]
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                cwd=os.path.dirname(os.path.abspath(__file__)),
                                capture_output=True, text=True, timeout=5)
        if commit.returncode == 0:
            out.append(f"commit      {commit.stdout.strip()}")
    except (OSError, subprocess.SubprocessError):
        pass

    # The most important lines in the file. Any number below was produced under
    # THESE parameters; without them the log cannot be compared to anything.
    changed = {n: getattr(S, n) for n in T.tunables()
               if abs(getattr(S, n) - T.BUILTIN[n]) > 1e-12}
    out.append("")
    if changed:
        out.append(f"PARAMETERS CHANGED FROM BUILT-IN ({len(changed)}) - every number below "
                   "was measured under these:")
        for name, value in sorted(changed.items()):
            out.append(f"  {name:<26} {value:<12g} (built-in {T.BUILTIN[name]:g})")
    else:
        out.append("parameters: all at their built-in values, nothing pinned or changed")
    return out


def _side(label, stats):
    return (f"  {label:<34} {stats['mean']:+.4f} +/- {stats['sd']:.4f}   "
            f"[{stats['min']:+.4f} .. {stats['max']:+.4f}]")


def differs(claim, left_label, left, right_label, right, key):
    """A claim that two things come out DIFFERENT, reported as both sides plus
    the gap. A gap only means something next to the noise it has to beat, so
    the spreads sit beside it rather than a bare difference."""
    a, b = left[key], right[key]
    gap = a["mean"] - b["mean"]
    noise = max(a["sd"], b["sd"])
    verdict = ("holds: the gap clears the spread" if abs(gap) > noise * 2
               else "NOT SHOWN: the gap is inside the spread - treat as unproven")
    return ["", f"CLAIM: {claim}", _side(left_label, a), _side(right_label, b),
            f"  gap {gap:+.4f}   largest sd {noise:.4f}   -> {verdict}"]


def two_metrics(claim, stats, left_label, left_key, right_label, right_key,
                gap_key, note):
    """A claim comparing two measurements from the SAME scenario.

    Not every claim is one setup against another: "a lunging hand is dreaded
    more than a still one" is two questions asked of one flock, so the seeds
    are shared and the gap has its own spread across them rather than being a
    difference of two independent means."""
    gap = stats[gap_key]
    verdict = ("holds: the lunge is dreaded more" if gap["mean"] > 0
               else "BROKEN: the lunge is not dreaded more")
    return ["", f"CLAIM: {claim}", f"  ({note})",
            _side(left_label, stats[left_key]), _side(right_label, stats[right_key]),
            f"  gap {gap['mean']:+.4f} +/- {gap['sd']:.4f}   "
            f"[{gap['min']:+.4f} .. {gap['max']:+.4f}]   -> {verdict}"]


def stays_within(claim, sides, key, band, band_name):
    """A claim that something does NOT happen - which is a different test, and
    reporting it like a difference inverts its meaning.

    "A hand that only moves is not blamed" is a claim of *equivalence*: both
    sides should sit near zero. Run through the difference test above it would
    read "the gap clears the spread", i.e. exactly the opposite of the claim.
    So it is measured against a threshold with a meaning in the game instead -
    the +/-0.05 band the HUD itself calls "doesn't know you yet"."""
    lines = ["", f"CLAIM: {claim}",
             f"  (measured against {band_name}: +/-{band})"]
    worst = 0.0
    for label, stats in sides:
        s = stats[key]
        lines.append(_side(label, s))
        worst = max(worst, abs(s["mean"]), abs(s["min"]), abs(s["max"]))
    verdict = (f"holds: nothing strayed past {band} (furthest {worst:.4f})"
               if worst <= band else
               f"BROKEN: something reached {worst:.4f}, outside the band")
    lines.append(f"  -> {verdict}")
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=int, default=3, help="how many seeds per scenario")
    ap.add_argument("--ticks", type=int, default=1500, help="ticks per world")
    ap.add_argument("--out", default="thronglets_report.txt", help="file to write")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                    help="try a parameter without pinning it as your default, e.g. "
                         "--set SIGNAL_ALARM_DA=0.25 . Repeatable. The header records "
                         "it, so two runs make a comparable pair.")
    ap.add_argument("--quick", action="store_true",
                    help="2 seeds x 600 ticks - a rough first look, roughly a third "
                         "of the time")
    args = ap.parse_args()
    if args.quick:
        args.seeds, args.ticks = 2, 600

    # --set lands AFTER any pinned defaults, so a value you are trying beats the
    # one you have saved. Both show up in the header either way.
    for item in args.set:
        name, _, raw = item.partition("=")
        name = name.strip()
        if name not in T.BUILTIN:
            ap.error(f"unknown parameter {name!r} - see the P screen for the list")
        if name in T.LOCKED:
            ap.error(f"{name} cannot be changed: {T.LOCKED[name]}")
        try:
            value = float(raw)
        except ValueError:
            ap.error(f"{name} needs a number, got {raw!r}")
        lo, hi = T.RANGES[name]
        if not lo <= value <= hi:
            ap.error(f"{name}={value:g} is outside its safe range {lo:g}..{hi:g}")
        T.apply({name: value})

    seeds = [5 + 4 * i for i in range(args.seeds)]
    lines = header(seeds, args.ticks)
    collected = {}

    total = len(SCENARIOS) * len(seeds)
    done = 0
    for title, kwargs in SCENARIOS:
        runs = []
        for seed in seeds:
            done += 1
            print(f"[{done}/{total}] {title}  seed {seed}", file=sys.stderr, flush=True)
            runs.append(measure(play(seed, args.ticks, **kwargs)))
        stats = across(runs)
        collected[title] = stats
        lines += ["", "-" * 78, title.upper(), "-" * 78]
        lines += table(stats, len(seeds))

    lines += ["", "=" * 78, "CLAIMS THIS PROJECT MAKES, RE-MEASURED", "=" * 78]
    lines += differs(
        "a call means something only where there was something to learn",
        "with predators", collected["hunted, you never touch it"],
        "without predators", collected["unhunted, you never touch it"],
        "call_most_dreaded")
    lines += differs(
        "kindness and cruelty teach opposite things",
        "after being fed", collected["hunted, hand feeds"],
        "after being burned", collected["hunted, hand burns"],
        "disposition")
    lines += stays_within(
        "a hand that only moves is not blamed for anything",
        [("hand wanders, never acts", collected["hunted, hand wanders (no acts)"]),
         ("you never touch it at all", collected["hunted, you never touch it"])],
        "disposition", 0.05, "the HUD's own neutral band")
    lines += two_metrics(
        "dread reaches a hand that is only closing in, before it lands",
        collected["hunted, hand burns"],
        "a still hand is worth", "hand_still_worth",
        "the same hand lunging", "hand_lunging_worth", "anticipation_gap",
        "measured on the burned flock - one that was never hurt has no reason "
        "to dread either")
    lines += stays_within(
        "an unhunted flock is not afraid of anything",
        [("unhunted, you never touch it", collected["unhunted, you never touch it"])],
        "felt_fear", 0.05, "a twentieth of the flock")

    lines += ["", "=" * 78,
              "Send this file along with what you were asking about.",
              "=" * 78]

    text = "\n".join(lines) + "\n"
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    print(f"written to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    T.load_and_apply()      # measure what the player actually plays with
    main()
