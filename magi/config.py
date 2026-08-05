"""Configuration du système MAGI.

La configuration par défaut est utilisable telle quelle ; un fichier YAML
permet ensuite de réaffecter librement un modèle à chaque agent, sans toucher
au code. Les valeurs `${VAR}` sont résolues depuis l'environnement.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .models import AGENT_ORDER, BALTHASAR, CASPER, MELCHIOR, ORCHESTRATOR
from .prompts import AGENT_SYSTEM_PROMPTS, ORCHESTRATOR_SYSTEM

_ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")

# Clé d'API attendue par famille de modèles, pour un diagnostic lisible avant
# le premier appel plutôt qu'une erreur 401 en plein débat.
_PROVIDER_KEYS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gpt": "OPENAI_API_KEY",
    "o1": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "vertex": "VERTEX_PROJECT",
    "mistral": "MISTRAL_API_KEY",
    "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "xai": "XAI_API_KEY",
    "cohere": "COHERE_API_KEY",
}


@dataclass
class AgentConfig:
    """Paramétrage d'un agent : quel modèle, quelle tempérture, quelle doctrine."""

    name: str
    model: str
    temperature: float = 0.5
    max_tokens: int = 1400
    system_prompt: str = ""
    json_mode: bool = True
    timeout: float = 90.0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def required_env_key(self) -> str | None:
        """Nom de la variable d'environnement probablement nécessaire."""
        model = self.model.lower()
        for token, env_key in _PROVIDER_KEYS.items():
            if token in model:
                return env_key
        return None


@dataclass
class MagiConfig:
    """Configuration complète du conseil."""

    agents: list[AgentConfig]
    orchestrator: AgentConfig
    backend: str = "litellm"
    max_debate_rounds: int = 2
    stop_on_unanimity: bool = True
    stop_on_convergence: bool = True
    simulated_latency: float = 0.15
    max_retries: int = 3

    def agent(self, name: str) -> AgentConfig:
        for cfg in self.agents:
            if cfg.name == name:
                return cfg
        raise KeyError(f"agent inconnu : {name}")

    def missing_api_keys(self) -> dict[str, str]:
        """Clés d'API absentes de l'environnement, par agent concerné."""
        if self.backend != "litellm":
            return {}
        missing: dict[str, str] = {}
        for cfg in [*self.agents, self.orchestrator]:
            key = cfg.required_env_key
            if key and not os.environ.get(key):
                missing[cfg.name] = key
        return missing

    def with_backend(self, backend: str) -> "MagiConfig":
        return replace(self, backend=backend)


def default_config() -> MagiConfig:
    """Trois modèles de familles différentes, comme dans le MAGI d'origine.

    Le triumvirat n'a d'intérêt que si les instances divergent réellement. Trois
    fournisseurs distincts et trois températures échelonnées maximisent cette
    divergence : Melchior est froid (rigueur), Casper est chaud (scepticisme
    créatif), Balthasar se tient entre les deux.
    """
    return MagiConfig(
        agents=[
            AgentConfig(
                name=MELCHIOR,
                model="anthropic/claude-opus-5",
                temperature=0.2,
                system_prompt=AGENT_SYSTEM_PROMPTS[MELCHIOR],
            ),
            AgentConfig(
                name=BALTHASAR,
                model="openai/gpt-4o",
                temperature=0.5,
                system_prompt=AGENT_SYSTEM_PROMPTS[BALTHASAR],
            ),
            AgentConfig(
                name=CASPER,
                model="gemini/gemini-2.5-pro",
                temperature=0.85,
                system_prompt=AGENT_SYSTEM_PROMPTS[CASPER],
            ),
        ],
        orchestrator=AgentConfig(
            name=ORCHESTRATOR,
            model="anthropic/claude-sonnet-5",
            temperature=0.3,
            max_tokens=2000,
            system_prompt=ORCHESTRATOR_SYSTEM,
        ),
    )


def load_env_file(path: str | Path | None = None) -> dict[str, str]:
    """Charge un fichier `.env` dans l'environnement du processus.

    Écrit à la main plutôt que via python-dotenv : le besoin se limite à des
    clés d'API, et une dépendance de plus pour quinze lignes se justifierait
    mal — surtout sous Windows, où l'équivalent shell d'un `export` groupé
    n'existe pas et où ce fichier est le seul moyen commode de fournir ses clés.

    Les variables déjà définies dans l'environnement ne sont jamais écrasées :
    une clé exportée à la main doit primer sur le fichier.

    Retourne les variables effectivement posées.
    """
    file_path = Path(path) if path else Path.cwd() / ".env"
    if not file_path.is_file():
        return {}

    applied: dict[str, str] = {}
    for raw_line in file_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()

        name, _, value = line.partition("=")
        name = name.strip()
        if not name.replace("_", "").isalnum():
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if not value or name in os.environ:
            continue

        os.environ[name] = value
        applied[name] = value

    return applied


def _expand(value: Any) -> Any:
    """Résout `${VAR}` et `${VAR:-defaut}` dans les chaînes."""
    if isinstance(value, str):
        return _ENV_RE.sub(lambda m: os.environ.get(m.group(1), m.group(2) or ""), value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def _merge_agent(base: AgentConfig, data: dict[str, Any]) -> AgentConfig:
    """Applique un bloc YAML par-dessus une configuration d'agent existante."""
    data = _expand(data or {})
    known = {"model", "temperature", "max_tokens", "json_mode", "timeout", "extra"}
    updates = {k: v for k, v in data.items() if k in known and v is not None}

    # Deux façons de personnaliser la doctrine : la remplacer entièrement
    # (system_prompt) ou l'étendre (system_prompt_append).
    if data.get("system_prompt"):
        updates["system_prompt"] = str(data["system_prompt"])
    elif data.get("system_prompt_file"):
        updates["system_prompt"] = Path(str(data["system_prompt_file"])).read_text(encoding="utf-8")
    if data.get("system_prompt_append"):
        prompt = updates.get("system_prompt", base.system_prompt)
        updates["system_prompt"] = f"{prompt}\n\nDIRECTIVE COMPLÉMENTAIRE\n{data['system_prompt_append']}"

    if "temperature" in updates:
        updates["temperature"] = max(0.0, min(2.0, float(updates["temperature"])))
    if "max_tokens" in updates:
        updates["max_tokens"] = max(256, int(updates["max_tokens"]))

    return replace(base, **updates)


def config_from_dict(data: dict[str, Any], base: MagiConfig | None = None) -> MagiConfig:
    """Construit une configuration à partir d'un mapping (YAML déjà chargé)."""
    config = base or default_config()
    data = data or {}

    agents_data = data.get("agents") or {}
    if isinstance(agents_data, list):  # forme liste : [{name: ..., model: ...}]
        agents_data = {item.get("name"): item for item in agents_data if isinstance(item, dict)}

    agents = [_merge_agent(cfg, agents_data.get(cfg.name, {})) for cfg in config.agents]
    orchestrator = _merge_agent(
        config.orchestrator,
        data.get("orchestrator") or agents_data.get(ORCHESTRATOR, {}),
    )

    top = _expand({k: v for k, v in data.items() if k not in {"agents", "orchestrator"}})
    return MagiConfig(
        agents=agents,
        orchestrator=orchestrator,
        backend=str(top.get("backend", config.backend)),
        max_debate_rounds=max(0, int(top.get("max_debate_rounds", config.max_debate_rounds))),
        stop_on_unanimity=bool(top.get("stop_on_unanimity", config.stop_on_unanimity)),
        stop_on_convergence=bool(top.get("stop_on_convergence", config.stop_on_convergence)),
        simulated_latency=float(top.get("simulated_latency", config.simulated_latency)),
        max_retries=max(1, int(top.get("max_retries", config.max_retries))),
    )


def load_config(path: str | Path | None = None) -> MagiConfig:
    """Charge la configuration depuis un YAML, puis applique les surcharges d'env.

    Ordre de priorité croissant : défauts intégrés < fichier YAML < variables
    d'environnement (MAGI_BACKEND, MAGI_ROUNDS, MAGI_MELCHIOR_MODEL, …).
    """
    config = default_config()

    if path:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"configuration introuvable : {file_path}")
        import yaml

        raw = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"{file_path} : la racine du YAML doit être un mapping")
        config = config_from_dict(raw, config)

    return _apply_env_overrides(config)


def _apply_env_overrides(config: MagiConfig) -> MagiConfig:
    env_agent_keys = {
        MELCHIOR: "MAGI_MELCHIOR_MODEL",
        BALTHASAR: "MAGI_BALTHASAR_MODEL",
        CASPER: "MAGI_CASPER_MODEL",
    }
    agents = [
        replace(cfg, model=os.environ[env_agent_keys[cfg.name]])
        if cfg.name in env_agent_keys and os.environ.get(env_agent_keys[cfg.name])
        else cfg
        for cfg in config.agents
    ]

    orchestrator = config.orchestrator
    if os.environ.get("MAGI_ORCHESTRATOR_MODEL"):
        orchestrator = replace(orchestrator, model=os.environ["MAGI_ORCHESTRATOR_MODEL"])

    backend = os.environ.get("MAGI_BACKEND", config.backend)
    rounds = config.max_debate_rounds
    if os.environ.get("MAGI_ROUNDS", "").isdigit():
        rounds = int(os.environ["MAGI_ROUNDS"])

    return replace(config, agents=agents, orchestrator=orchestrator,
                   backend=backend, max_debate_rounds=rounds)


def find_default_config() -> Path | None:
    """Cherche un magi.yaml dans le répertoire courant ou à la racine du projet."""
    for candidate in (Path.cwd() / "magi.yaml", Path.cwd() / "magi.yml",
                      Path(__file__).resolve().parent.parent / "magi.yaml"):
        if candidate.exists():
            return candidate
    return None


__all__ = [
    "AgentConfig",
    "MagiConfig",
    "default_config",
    "config_from_dict",
    "load_config",
    "load_env_file",
    "find_default_config",
    "AGENT_ORDER",
]
