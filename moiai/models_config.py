"""
Model configuration — persists user's choice of model per role to a JSON file.
Loaded at api.py import time so all modules see the correct model constants.
"""

import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "data" / "models.json"

# All models available for selection
AVAILABLE_MODELS: dict[str, str] = {
    "claude-opus-4-7":           "Opus 4.7   — le plus capable, le plus cher",
    "claude-sonnet-4-6":         "Sonnet 4.6 — équilibré (défaut conversations)",
    "claude-haiku-4-5-20251001": "Haiku 4.5  — rapide et économique (défaut extraction)",
}

# Roles and their human-readable descriptions
ROLES: dict[str, str] = {
    "chat":    "Conversation principale",
    "smart":   "Condensation / narration",
    "fast":    "Extraction, curiosité, résumés, recherche",
    "analyse": "Synthèse /résumés et analyses ponctuelles",
}

_DEFAULTS: dict[str, str] = {
    "chat":    "claude-sonnet-4-6",
    "smart":   "claude-sonnet-4-6",
    "fast":    "claude-haiku-4-5-20251001",
    "analyse": "claude-haiku-4-5-20251001",
}


def load() -> dict[str, str]:
    """Load config from disk; fall back to defaults for any missing key."""
    if _CONFIG_PATH.exists():
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            return {k: data.get(k, v) for k, v in _DEFAULTS.items()}
        except Exception:
            pass
    return dict(_DEFAULTS)


def save(config: dict[str, str]) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def get_model(role: str) -> str:
    return load().get(role, _DEFAULTS.get(role, "claude-sonnet-4-6"))


def set_model(role: str, model: str) -> None:
    config = load()
    config[role] = model
    save(config)
