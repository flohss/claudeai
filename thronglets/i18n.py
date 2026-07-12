"""Shared state-label translations.

This is the one piece of UI text whose *meaning* (not just wording) is
identical across all three renderers, so it lives in one place instead of
being copy-pasted three times. Each renderer keeps its own menu/HUD/help
text locally, since the wording differs per platform anyway.
"""

from simulation import DANGER, DISTRESS, FOOD, IDLE, MATE

LANGUAGES = ("en", "fr")

STATE_LABELS = {
    "en": {IDLE: "idle", FOOD: "food-call", MATE: "mate-call", DANGER: "alarm-call", DISTRESS: "distress-call"},
    "fr": {IDLE: "inactif", FOOD: "nourriture", MATE: "partenaire", DANGER: "alerte", DISTRESS: "detresse"},
}
