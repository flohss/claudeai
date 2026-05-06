"""
User-adjustable context and behavior settings — persisted to JSON.
All modules read values at call time via get() so changes are immediate.
"""

import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "data" / "settings.json"

# (label, hint, min, max)
PARAMS: dict[str, tuple[str, str, int, int]] = {
    "personnes_contexte":  ("Personnes dans le contexte",            "tu en as {people} en base",   1,   50),
    "faits_contexte":      ("Faits dans le contexte",                "tu en as {facts} en base",    10,  200),
    "messages_historique": ("Messages d'historique chargés",         "fenêtre de conversation",     10,  100),
    "résumés_contexte":    ("Résumés de conversations anciens",      "3 résumés ≈ ~18 phrases",     0,   20),
    "faits_par_personne":  ("Faits liés par personne",               "croisement nom ↔ faits",      0,   10),
    "notes_longueur":      ("Longueur notes personnes (caractères)", "tronqué dans le contexte",    50,  1000),
    "seuil_auto_résumé":   ("Seuil résumé automatique (messages)",   "0 = désactivé",               0,   500),
    "contexte_unifié":     ("Contexte unifié (1=oui, 0=non)",        "nécessite /condenser d'abord", 0,   1),
    "mots_portrait":       ("Mots du portrait unifié",               "défaut 750",                  300, 32000),
    "curiosité_active":    ("Bloc de curiosité (1=oui, 0=non)",      "questions suggérées à l'IA",  0,   1),
}

DEFAULTS: dict[str, int] = {
    "personnes_contexte":  8,
    "faits_contexte":      60,
    "messages_historique": 30,
    "résumés_contexte":    3,
    "faits_par_personne":  4,
    "notes_longueur":      200,
    "seuil_auto_résumé":   80,
    "contexte_unifié":     0,
    "mots_portrait":       750,
    "curiosité_active":    1,
}


def load() -> dict[str, int]:
    if _CONFIG_PATH.exists():
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            return {k: int(data.get(k, v)) for k, v in DEFAULTS.items()}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(config: dict[str, int]) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def get(key: str) -> int:
    return load().get(key, DEFAULTS[key])


def set_param(key: str, value: int) -> None:
    config = load()
    config[key] = value
    save(config)
