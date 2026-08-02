"""Shared state-label translations.

This is the one piece of UI text whose *meaning* (not just wording) is
identical across all three renderers, so it lives in one place instead of
being copy-pasted three times. Each renderer keeps its own menu/HUD/help
text locally, since the wording differs per platform anyway.
"""

from simulation import (DANGER, DISTRESS, FOOD, IDLE, MATE, TRAIT_HEARING,
                        TRAIT_METABOLISM, TRAIT_SPEED, TRAIT_VISION,
                        F_HAND, F_PREDATOR, F_FOOD)

LANGUAGES = ("en", "fr")

STATE_LABELS = {
    "en": {IDLE: "idle", FOOD: "food-call", MATE: "mate-call", DANGER: "alarm-call", DISTRESS: "distress-call"},
    "fr": {IDLE: "inactif", FOOD: "nourriture", MATE: "partenaire", DANGER: "alerte", DISTRESS: "detresse"},
}

TRAIT_LABELS = {
    "en": {TRAIT_SPEED: "speed", TRAIT_VISION: "vision", TRAIT_HEARING: "hearing",
           TRAIT_METABOLISM: "metabolism"},
    "fr": {TRAIT_SPEED: "vitesse", TRAIT_VISION: "vision", TRAIT_HEARING: "ouie",
           TRAIT_METABOLISM: "metabolisme"},
}

# How the flock has come to regard the player, -1 .. +1, put into words. Each
# entry is the LOWER bound of its band, so the first one a value clears wins.
#
# The middle band matters more than it looks. A creature is born valuing every
# situation at exactly 0.0 - it holds no opinion of the player whatsoever - and
# a flock nobody has touched sits right there. Without a neutral band that
# reads as "no opinion", the HUD tells a player who has done nothing at all
# that the flock is wary of them, which is both false and the first thing they
# see. Wide enough to cover the small drift of an untouched flock, and matched
# to the +/-0.05 dead zone the pygame HUD's gauge already uses, so the words
# and the gauge colour can never contradict each other.
DISPO_LABELS = {
    "en": [(0.5, "adores you"), (0.15, "trusts you"), (0.05, "is getting used to you"),
           (-0.05, "doesn't know you yet"), (-0.15, "is wary of you"),
           (-0.5, "fears you"), (-1.1, "is terrified of you")],
    "fr": [(0.5, "t'adore"), (0.15, "te fait confiance"), (0.05, "s'habitue a toi"),
           (-0.05, "ne te connait pas encore"), (-0.15, "se mefie de toi"),
           (-0.5, "te craint"), (-1.1, "est terrifie par toi")],
}


def disposition_label(value, lang="en"):
    """Put a -1 .. +1 disposition into words in `lang`."""
    for threshold, label in DISPO_LABELS.get(lang, DISPO_LABELS["en"]):
        if value >= threshold:
            return label
    return DISPO_LABELS.get(lang, DISPO_LABELS["en"])[-1][1]


# What a remembered moment was ABOUT. Shared for the same reason the
# disposition wording is: the MEANING has to be identical in all three
# renderers, and this particular rule took a measurement to get right - having
# it in three places is having it wrong in two of them eventually.
MEMORY_LABELS = {
    "en": {"hand": "your hand", "predator": "a predator", "food": "food", "other": "a moment"},
    "fr": {"hand": "ta main", "predator": "un predateur", "food": "la nourriture",
           "other": "un instant"},
}


def memory_label(feat, target, lang="en"):
    """Name a kept memory: the rarest thing present, not the loudest.

    Taking whichever perception was strongest quietly blamed food for almost
    everything, because the perception radii are not comparable - food is
    noticed from 60 world units, the hand from 48, a predator only from 26, so
    food is the loudest single thing in view in 47% of living moments. Measured
    across 5 seeds, 1186 of 2773 kept memories were labelled "food", 489 of
    them with a predator in sight; inside that group the value tracked the
    PREDATOR's distance (-0.52) and not the food's (+0.04). The food was
    scenery. So a memory is named for the event in it.

    The sign matters too. A hunter can never MAKE a moment good - the only
    lesson predators hand out is negative and they give no reward at all - but
    a meal is credited to the state the creature was in, and 14.4% of meals are
    taken with a hunter within perception. So a good surprise never gets the
    predator's name; it falls through to whatever else was in the frame.
    """
    words = MEMORY_LABELS.get(lang, MEMORY_LABELS["en"])
    if feat[F_PREDATOR] >= 0.1 and target <= 0.0:
        return words["predator"]
    if feat[F_HAND] >= 0.2:
        return words["hand"]
    if feat[F_FOOD] >= 0.4:
        return words["food"]
    return words["other"]
