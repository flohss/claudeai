"""Shared state-label translations.

This is the one piece of UI text whose *meaning* (not just wording) is
identical across all three renderers, so it lives in one place instead of
being copy-pasted three times. Each renderer keeps its own menu/HUD/help
text locally, since the wording differs per platform anyway.
"""

from simulation import DANGER, DISTRESS, FOOD, IDLE, MATE, TRAIT_HEARING, TRAIT_METABOLISM, TRAIT_SPEED, TRAIT_VISION

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
