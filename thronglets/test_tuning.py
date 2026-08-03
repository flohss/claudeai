"""Headless checks for the tuning screen's registry (no pygame needed).

The screen lets a player drag any of ~105 constants to either end of its range.
That turns a whole class of values that used to be unreachable into values a
curious person will absolutely try - and several of them are divisors. Sliding
one to zero is not an extreme setting, it is a crash, or worse a silent NaN
(DECIDE_TEMP at zero yields NaN rather than raising, quietly corrupting every
decision a creature makes).

So the important check here is brute force: put EVERY parameter at each end of
its range, run a world, and demand it neither raises nor goes non-finite. That
is how HEAR_RADIUS was caught - it flows into a traits array that is divided by
later, so its name never appears next to a slash and no amount of reading the
source would have found it.

    python3 test_tuning.py            # everything, including the slow sweep
    python3 test_tuning.py --quick    # skip the 214-extreme sweep
"""

import argparse
import contextlib
import io
import os
import tempfile
import warnings

import numpy as np

import simulation as S
import tuning as T


def _run_world(seed=1, ticks=60, adaptive=True):
    """A short life with the hand placed and learning on, so the divisors that
    only matter when a hand exists actually get exercised."""
    with contextlib.redirect_stdout(io.StringIO()):
        world = S.World(init_pop=20, seed=seed, learning=True, adaptive_traits=adaptive)
        world.hand_pos = np.array([S.WIDTH * 0.5, S.HEIGHT * 0.5])
        for _ in range(ticks):
            world.step()
    return world


def _finite(world):
    for c in world.creatures:
        if c.alive and c.mind is not None:
            if not (np.isfinite(c.mind.valence) and np.isfinite(c.mind.arousal)):
                return False
            if not np.all(np.isfinite(c.mind.memory)):
                return False
    return True


def check_every_extreme_is_survivable():
    """Both ends of every parameter's range must produce a world that runs."""
    failures = []
    with warnings.catch_warnings():
        # a divide that yields NaN instead of raising must fail here too
        warnings.simplefilter("error", RuntimeWarning)
        for name in T.tunables():
            for end, value in (("min", T.RANGES[name][0]), ("max", T.RANGES[name][1])):
                T.reset_to_builtin()
                T.apply({name: value})
                try:
                    if not _finite(_run_world(adaptive=(end == "max"))):
                        failures.append(f"{name} {end}={value}: went non-finite")
                except Exception as exc:                      # noqa: BLE001
                    failures.append(f"{name} {end}={value}: "
                                    f"{type(exc).__name__}: {str(exc)[:60]}")
    T.reset_to_builtin()
    print(f"  {len(T.tunables()) * 2} extremes tried, {len(failures)} broke the world")
    for line in failures[:10]:
        print(f"    {line}")
    assert not failures, "a value the tuning screen allows breaks the simulation"


def check_divisors_never_reach_zero():
    """Every parameter the simulation divides by must have a range that stops
    short of zero - the property the sweep above is protecting."""
    for name in T.DIVISORS:
        assert name in T.RANGES, f"{name} is listed as a divisor but is not tunable"
        assert T.RANGES[name][0] > 0, f"{name} can still be set to zero"
    print(f"  {len(T.DIVISORS)} divisors, all floored above zero")


def check_paired_parameters_cannot_divide_by_zero():
    """A floor per parameter cannot express a constraint BETWEEN two of them:
    gloom divides by (MOOD_GLOOM_ONSET - DISTRESS_ENERGY), which is zero when
    they are set equal. That one is guarded in the simulation itself."""
    T.reset_to_builtin()
    T.apply({"MOOD_GLOOM_ONSET": S.DISTRESS_ENERGY})
    try:
        assert _finite(_run_world()), "equal gloom bounds produced a non-finite mood"
    finally:
        T.reset_to_builtin()
    print("  MOOD_GLOOM_ONSET == DISTRESS_ENERGY survives")


def check_the_registry_covers_the_source():
    """Every numeric constant in simulation.py must be either tunable or
    explicitly locked - so a parameter added later cannot silently go missing
    from the screen that claims to show everything."""
    import re
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "simulation.py"), encoding="utf-8").read()
    found = set()
    for m in re.finditer(r"^([A-Z][A-Z0-9_]*)(?:\s*,\s*([A-Z][A-Z0-9_]*))?\s*=\s*"
                         r"(-?[\d.]+)\s*(?:,\s*(-?[\d.]+)\s*)?(?:#.*)?$", src, re.M):
        for name in (m.group(1), m.group(2)):
            if name:
                found.add(name)
    listed = set(T.BUILTIN)
    missing = sorted(found - listed)
    print(f"  {len(found)} numeric constants in simulation.py, {len(missing)} not on the screen")
    for name in missing:
        print(f"    {name}")
    assert not missing, "the screen claims to show everything but does not"


def check_descriptions_come_from_the_source():
    """Every tunable must carry a harvested description. A blank one means a
    constant lost its comment, which is exactly the drift this design avoids."""
    blank = [n for n in T.tunables() if not T.DOCS.get(n)]
    print(f"  {len(T.tunables())} tunables, {len(blank)} without a description")
    for name in blank:
        print(f"    {name}")
    assert not blank, "a parameter has no comment in simulation.py to show"


def check_defaults_round_trip():
    """Pinning, reloading and clearing must all do exactly what they say."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)
    try:
        T.reset_to_builtin()
        moved = T.BUILTIN["SEE_RADIUS"] + 3.0
        T.apply({"SEE_RADIUS": moved})
        n = T.save(T.current(), path)
        assert n == 1, f"expected exactly one changed value written, got {n}"
        assert set(T.load(path)) == {"SEE_RADIUS"}, "the file holds more than what changed"

        T.reset_to_builtin()
        assert S.SEE_RADIUS == T.BUILTIN["SEE_RADIUS"], "reset did not restore the built-in"
        T.load_and_apply(path)
        assert S.SEE_RADIUS == moved, "a pinned default did not come back"

        T.reset_to_builtin()
        T.save(T.current(), path)
        assert not os.path.exists(path), "the file survived having nothing left to say"
        print("  pin -> reset -> reload -> clear all behave")
    finally:
        T.reset_to_builtin()
        if os.path.exists(path):
            os.remove(path)


def check_locked_parameters_refuse_to_move():
    """apply() must ignore the structural ones however it is called - the screen
    is not the only caller, a hand-edited defaults file reaches here too."""
    before = {n: getattr(S, n) for n in T.LOCKED}
    T.apply({n: 999 for n in T.LOCKED})
    after = {n: getattr(S, n) for n in T.LOCKED}
    assert before == after, "a locked parameter was changed"

    # and a hand-edited file naming one must be filtered on the way in, not
    # trusted because it is on disk
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"N_TOKENS": 99, "NOT_A_REAL_PARAM": 1, "SEE_RADIUS": 21.0}')
        loaded = T.load(path)
        assert loaded == {"SEE_RADIUS": 21.0}, f"load() let something through: {loaded}"
    finally:
        os.remove(path)
    print(f"  {len(T.LOCKED)} locked parameters stayed put, and are filtered out of a file")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true",
                    help="skip the slow every-extreme sweep; the registry, "
                         "divisor, lock and round-trip guards still run")
    args = ap.parse_args()
    checks = [
        ("the registry covers the source", check_the_registry_covers_the_source),
        ("descriptions come from the source", check_descriptions_come_from_the_source),
        ("divisors never reach zero", check_divisors_never_reach_zero),
        ("locked parameters refuse to move", check_locked_parameters_refuse_to_move),
        ("defaults round-trip", check_defaults_round_trip),
        ("paired parameters cannot divide by zero",
         check_paired_parameters_cannot_divide_by_zero),
        ("every extreme is survivable", check_every_extreme_is_survivable),
    ]
    if args.quick:
        checks = [(t, f) for t, f in checks if f is not check_every_extreme_is_survivable]
    for title, fn in checks:
        print(f"{title}:")
        fn()
    print(f"\nOK: {len(checks)} checks passed - nothing the screen offers breaks the world.")


if __name__ == "__main__":
    main()
