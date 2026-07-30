"""Headless checks for the learned mind (no pygame/display needed).

test_smoke.py covers the simulation core with learning OFF. This covers what
the opt-in Mind actually does, because none of it is visible from watching the
game: a flock whose learning has silently stopped still moves, still has
colours, still breeds. Only the numbers show that cruelty has stopped teaching
fear.

Every check here corresponds to a real failure that was hit while building this
system - a reward scale that made creatures reinforce whatever they happened to
be doing, lessons taught in a fabricated situation that no creature was ever
in, warning calls that carried nothing a listener didn't already know, and a
learned flight response that drove the population extinct. None of them were
visible in play.

Runs in about five minutes; --quick does the instant half in seconds. Every
world is seeded, so two runs of this file print the same numbers - and the
thresholds sit well clear of those numbers. A failure here means something
really changed, not that a run got unlucky.

    python3 test_learning.py            # everything
    python3 test_learning.py --quick    # skip the slow ecosystem checks
"""

import argparse
import os
import tempfile

import numpy as np

import simulation as S


# --- helpers ---------------------------------------------------------------

def minds(world):
    return [c.mind for c in world.creatures if c.alive and c.mind is not None]


def hand_session(seed, reward, ticks=600, per_step=None):
    """A session played the way a person plays: the cursor wanders through the
    flock and acts on whoever is within reach of it, so what a creature gets
    depends on what it chose to do about the hand."""
    world = S.World(init_pop=40, seed=seed, manual_predators=True, learning=True)
    rng = np.random.default_rng(seed)
    hand = np.array([S.WIDTH * 0.5, S.HEIGHT * 0.5])
    for _ in range(ticks):
        alive = [c for c in world.creatures if c.alive]
        if len(alive) < 3:
            break
        hand = np.clip(hand + rng.normal(0, 1.5, 2), [0, 0], [S.WIDTH, S.HEIGHT])
        world.hand_pos = hand
        reach = [c for c in alive
                 if np.linalg.norm(np.asarray(c.pos) - hand) < S.HAND_PERCEPTION * 0.5]
        for c in (reach[:per_step] if per_step else reach):
            world.deliver_experience(c, reward)
        world.step()
    return world


def predator_meaning(world):
    """How much worse the flock expects a moment with a predator on it to be
    than one with none in sight. Negative means it understands what they are."""
    ms = minds(world)
    if not ms:
        return float("nan")
    near = np.mean([m.value(S.Mind.features(0, 0.2, 0, 0, predator=1.0)) for m in ms])
    far = np.mean([m.value(S.Mind.features(0, 0.2, 0, 0, predator=0.0)) for m in ms])
    return float(near - far)


def worst_call_meaning(world):
    """The most dreaded of the flock's own signal colours."""
    ms = minds(world)
    if not ms:
        return 0.0
    return min(float(np.mean([m.signal_meaning(k) for m in ms]))
               for k in range(1, S.N_TOKENS))


# --- the checks ------------------------------------------------------------

def check_gradient_is_correct():
    """Backpropagation must agree with the slope measured directly. If this
    drifts, everything downstream is learning from a wrong direction."""
    m = S.Mind()
    rng = np.random.default_rng(1)
    for k in m.p:
        m.p[k] = m.p[k] + rng.normal(0, 0.4, m.p[k].shape)
    x = S.Mind.features(0.7, 0.3, 0.5, 0.4, 0.2, 0.6, 0.5,
                        signals=np.linspace(0.1, 0.9, S.N_SIGNALS))
    analytic, eps, worst = m._grad_value(x), 1e-6, 0.0
    for k in m.p:
        shape, base = m.p[k].shape, m.p[k].ravel().copy()
        flat = np.asarray(analytic[k], dtype=float).ravel()
        for i in range(base.size):
            up = base.copy(); up[i] += eps
            m.p[k] = up.reshape(shape); hi = m.value(x)
            dn = base.copy(); dn[i] -= eps
            m.p[k] = dn.reshape(shape); lo = m.value(x)
            worst = max(worst, abs((hi - lo) / (2 * eps) - flat[i]))
        m.p[k] = base.reshape(shape)
    print(f"  backprop vs measured slope, worst disagreement: {worst:.2e}")
    assert worst < 1e-5, "backpropagation no longer matches the real gradient"


def check_born_with_no_opinions():
    """A creature must start knowing nothing - not holding faint random
    opinions it never earned."""
    m = S.Mind()
    calls = [m.signal_meaning(k) for k in range(1, S.N_TOKENS)]
    pi = m.policy(S.Mind.features(1.0, 0.0))
    print(f"  newborn: disposition {m.disposition():+.4f}, every call {max(map(abs, calls)):.4f}, "
          f"choices {pi.round(3)}")
    assert abs(m.disposition()) < 1e-9, "a newborn already had a view of the player"
    assert max(map(abs, calls)) < 1e-9, "a newborn already had views about the flock's calls"
    assert abs(pi.max() - 1.0 / S.N_ACTIONS) < 1e-9, "a newborn already favoured an action"


def check_kindness_and_cruelty_teach_opposite_things():
    kind = hand_session(0, +1.0).disposition_summary()
    cruel_world = hand_session(1, -1.0, per_step=3)
    cruel = cruel_world.disposition_summary()
    print(f"  after being fed:    disposition {kind:+.3f}  (positive = comes to you)")
    print(f"  after being burned: disposition {cruel:+.3f}  (negative = flees you)")
    assert kind > 0.15, "kindness stopped teaching the flock to approach"
    assert cruel < -0.05, "cruelty stopped teaching the flock to flee"
    return cruel_world


def check_dread_travels_backward_in_time(cruel_world):
    """The point of TD: a burned flock must dread a hand that is CLOSING IN
    more than the same hand sitting still. Nothing says it should; it can only
    come from the value of one moment being learned from the next."""
    ms = minds(cruel_world)
    still = np.mean([m.value(S.Mind.features(0.6, 0.2, 0.0, 0.0)) for m in ms])
    lunging = np.mean([m.value(S.Mind.features(0.6, 0.2, 0.0, 1.0)) for m in ms])
    print(f"  hand still {still:+.3f} vs hand lunging {lunging:+.3f}  "
          f"(gap {still - lunging:+.3f})")
    assert lunging < still, "a lunging hand is no longer dreaded before it lands"


def check_one_shock_teaches_the_whole_approach():
    """TD(lambda) must correct the run-up to a shock, not only its last step."""
    def run(lam):
        S.TD_LAMBDA, m, rng = lam, S.Mind(), np.random.default_rng(0)
        early = S.Mind.features(0.2, 0.2)
        before = m.value(early)
        for p in (0.2, 0.4, 0.6, 0.8, 1.0):
            m.sense(S.Mind.features(p, 0.2), rng)
        m.reinforce(-1.0)
        m.sense(S.Mind.features(1.0, 0.2), rng)
        return m.value(early) - before

    keep = S.TD_LAMBDA
    try:
        spread, single = run(0.9), run(0.0)
    finally:
        S.TD_LAMBDA = keep
    print(f"  correction reaching the START of the approach: "
          f"TD(0.9) {spread:+.5f} vs TD(0) {single:+.5f}")
    assert spread < 0, "the run-up to a shock no longer inherits it"
    assert abs(spread) > abs(single) * 2, "TD(lambda) reaches no further back than TD(0)"


TICKS = 1200
SEEDS = (5, 9)


def _lived_world(seed, predators=True):
    world = S.World(init_pop=60, seed=seed, learning=True,
                    manual_predators=not predators)
    for _ in range(TICKS):
        world.step()
    return world


def build_shared_worlds():
    """The long-running worlds, built once. Several checks ask different
    questions of the same lived life, so building one world per question would
    triple the runtime for no extra confidence."""
    worlds = {"hunted": {s: _lived_world(s) for s in SEEDS},
              "quiet": {s: _lived_world(s, predators=False) for s in SEEDS}}
    keep = S.REPLAY_PER_STEP
    try:                                  # the same hunted life, without replay
        S.REPLAY_PER_STEP = 0
        worlds["no_replay"] = _lived_world(SEEDS[0])
    finally:
        S.REPLAY_PER_STEP = keep
    return worlds


def check_reliving_shocks_deepens_rare_lessons(worlds):
    """Replay exists because a predator kill happens once while the quiet
    stretch after it erodes the lesson. Same seed, replay on and off."""
    on_world = worlds["hunted"][SEEDS[0]]
    off, on = predator_meaning(worlds["no_replay"]), predator_meaning(on_world)
    print(f"  what a predator means: {off:+.3f} without replay, {on:+.3f} with it")
    assert on < off, "re-living shocks no longer deepens the rare lesson"
    assert on < -0.05, "the predator lesson is too faint to matter"
    held = max(len(m.replay) for m in minds(on_world))
    assert held <= S.REPLAY_SIZE, "a creature is holding more memories than it should"


def check_calls_mean_what_experience_taught(worlds):
    """The words are evolved and identical either way; only lived experience
    differs. Which call picks up the dread is NOT reproducible - that is why
    this asks whether any call did, not which one."""
    a = float(np.mean([worst_call_meaning(worlds["hunted"][s]) for s in SEEDS]))
    b = float(np.mean([worst_call_meaning(worlds["quiet"][s]) for s in SEEDS]))
    print(f"  most dreaded call: {a:+.4f} in a world with predators, {b:+.4f} without")
    assert a < -0.02, "no call ever came to mean anything"
    assert a < b - 0.015, "a world with nothing to warn about produced just as much dread"


def check_a_mind_survives_being_saved():
    world = hand_session(3, +1.0, ticks=250)
    before = world.disposition_summary()
    arc = list(world.disposition_history)
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        S.save_world(world, path)
        reloaded = S.load_world(path)
        after = reloaded.disposition_summary()
        print(f"  disposition across save/load: {before:+.5f} -> {after:+.5f}")
        assert abs(before - after) < 1e-6, "a mind changed when written to disk and back"
        # the ARC has to come back too, not just the minds - resuming a game
        # used to restore what the flock felt while losing how it got there
        print(f"  the arc of how they got there: {len(arc)} points -> "
              f"{len(reloaded.disposition_history)}")
        assert arc and list(reloaded.disposition_history) == arc, \
            "the flock's history with the player was lost on save/load"
    finally:
        os.remove(path)
    # a save from an older architecture must not crash the loader
    stale = S.Mind({"W1": [[0.0] * 5] * 6, "b1": [0.0] * 6, "W2": [0.0] * 6, "b2": 0.0},
                   0.3, 0.4, None, 0.5)
    assert stale.p["W1"].shape == (S.LEARN_HIDDEN, S.LEARN_FEATURES)
    assert abs(stale.valence - 0.3) < 1e-9 and abs(stale.obedience - 0.5) < 1e-9
    print("  a save from an older mind: starts fresh, keeps its mood and obedience")


def check_the_flock_still_survives_learning(worlds):
    """Learning must not cost the flock its life - a learned response gating a
    lethal behaviour once drove every seed extinct."""
    lived = [worlds["hunted"][s] for s in SEEDS] + [worlds["no_replay"]]
    pops = [sum(c.alive for c in w.creatures) for w in lived]
    print(f"  population after {TICKS} ticks among predators: {pops}")
    assert all(p > 10 for p in pops), f"a population collapsed under learning: {pops}"


def check_learning_off_changes_nothing():
    """The whole system is opt-in. With it off, no creature may carry a mind,
    and every learned readout must decline to answer rather than invent one."""
    world = S.World(init_pop=40, seed=8)
    for _ in range(200):
        world.step()
    assert all(c.mind is None for c in world.creatures), "a mind appeared with learning off"
    for name in ("disposition_summary", "choice_summary", "signal_meanings"):
        assert getattr(world, name)() is None, f"{name}() answered with learning off"
    assert not world.disposition_history, "an arc was recorded with learning off"
    print("  learning off: no minds, no readouts, no arc - the core is untouched")


def check_dread_from_calls_is_bounded_and_lets_go():
    """Hearing a dreaded call must move the resting mood, not deliver a jolt
    every step. This was a real bug: feel() is for discrete events, and calling
    it once per step while the calling lasted accumulated without bound - it
    produced ALL of the fear in an idle world and shifted the median mood by
    +/-0.2 on its own. So: dread must build toward the baseline, stop there, and
    drain away once the voices do."""
    m = S.Mind()
    loud = S.Mind.features(0, 0.2, 0, 0,
                           signals=np.array([1.0] + [0.0] * (S.N_SIGNALS - 1)))
    for _ in range(400):
        m.teach(-1.0, loud, S.LEARN_RATE * 2)
    alarm = m.value(S.Mind._hushed(loud)) - m.value(loud)
    assert alarm > S.SIGNAL_ALARM_MIN, "the call never became dreaded, so this proves nothing"
    dread = max(-1.0, min(1.0, alarm / S.SIGNAL_ALARM_FULL))
    floor = S.MOOD_VALENCE_REST - dread * S.SIGNAL_ALARM_DV

    for _ in range(600):                       # the voices keep on and on
        m.relax(floor, S.MOOD_AROUSAL_REST + dread * S.SIGNAL_ALARM_DA)
    settled = m.valence
    assert settled >= floor - 1e-6, \
        f"dread ran past its own baseline ({settled:+.3f} < {floor:+.3f}) - it is accumulating again"
    for _ in range(600):                       # and then silence
        m.relax(S.MOOD_VALENCE_REST, S.MOOD_AROUSAL_REST)
    print(f"  under a dreaded call {settled:+.3f} (baseline {floor:+.3f}, cannot pass it), "
          f"after silence {m.valence:+.3f}")
    assert m.valence > settled + 0.05, "dread never let go once the calling stopped"


def check_the_flock_can_be_divided():
    """The averaged disposition cannot tell a split flock from an indifferent
    one, which is what choice_summary exists for. Both must be readable."""
    world = hand_session(0, +1.0, ticks=400)
    choices = world.choice_summary()
    assert choices is not None and abs(sum(choices.values()) - 1.0) < 1e-9, \
        "the choice breakdown does not account for the whole flock"
    meanings = world.signal_meanings()
    assert meanings is not None and set(meanings) == set(range(1, S.N_TOKENS)), \
        "the learned meanings do not cover every audible call"
    print("  choices " + "  ".join(f"{k}={v:.0%}" for k, v in sorted(choices.items())) +
          f"   |  learned meanings for {len(meanings)} calls")


# --- runner ----------------------------------------------------------------

FAST = [
    ("backpropagation is correct", check_gradient_is_correct),
    ("a creature is born with no opinions", check_born_with_no_opinions),
    ("one shock teaches the whole approach", check_one_shock_teaches_the_whole_approach),
    ("learning stays opt-in", check_learning_off_changes_nothing),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true",
                        help="skip the slow ecosystem checks (keeps the instant ones)")
    args = parser.parse_args()

    checks = list(FAST)
    if not args.quick:
        lived = {}   # filled in by the first slow check, shared by the rest

        def kindness_and_cruelty():
            lived["cruel"] = check_kindness_and_cruelty_teach_opposite_things()

        def live_several_lives():
            print(f"  living {2 * len(SEEDS) + 1} worlds of {TICKS} ticks "
                  f"(hunted, unhunted, and one hunted without replay)...")
            lived["worlds"] = build_shared_worlds()

        checks += [
            ("kindness and cruelty teach opposite things", kindness_and_cruelty),
            ("dread travels backward in time",
             lambda: check_dread_travels_backward_in_time(lived["cruel"])),
            ("a mind survives being saved", check_a_mind_survives_being_saved),
            ("dread from a call is bounded and lets go",
             check_dread_from_calls_is_bounded_and_lets_go),
            ("a flock can be divided, not just averaged", check_the_flock_can_be_divided),
            ("living out several whole lives", live_several_lives),
            ("re-living shocks deepens rare lessons",
             lambda: check_reliving_shocks_deepens_rare_lessons(lived["worlds"])),
            ("calls mean what experience taught",
             lambda: check_calls_mean_what_experience_taught(lived["worlds"])),
            ("the flock survives learning",
             lambda: check_the_flock_still_survives_learning(lived["worlds"])),
        ]

    for name, fn in checks:
        print(f"{name}:")
        fn()
    print(f"\nOK: {len(checks)} checks passed - the flock still learns.")


if __name__ == "__main__":
    main()
