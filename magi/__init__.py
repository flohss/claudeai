"""MAGI — moteur de délibération multi-agents inspiré d'Evangelion.

Trois modèles de langage aux doctrines opposées analysent une requête, débattent
entre eux lorsqu'ils divergent, puis un orchestrateur rend une décision unique.

Exemple minimal :

    import asyncio
    from magi import MagiSystem, load_config

    system = MagiSystem(load_config("magi.yaml"))
    decision = asyncio.run(system.deliberate("Faut-il migrer vers Rust ?"))
    print(decision.status.value, decision.final_answer)
"""

from .agent import MagiAgent
from .backends import LiteLLMBackend, LLMBackend, LLMError, SimulatedBackend, build_backend
from .config import AgentConfig, MagiConfig, default_config, find_default_config, load_config
from .events import EventCollector, EventQueue, EventType, MagiEvent
from .models import (
    AGENT_ORDER,
    BALTHASAR,
    CASPER,
    MELCHIOR,
    ORCHESTRATOR,
    AgentVerdict,
    DebateRound,
    MagiDecision,
    SystemStatus,
    Vote,
    resolve_status,
    tally_votes,
)
from .orchestrator import MagiSystem

__version__ = "1.0.0"

__all__ = [
    "MagiSystem",
    "MagiAgent",
    "MagiConfig",
    "AgentConfig",
    "MagiDecision",
    "DebateRound",
    "AgentVerdict",
    "SystemStatus",
    "Vote",
    "MagiEvent",
    "EventType",
    "EventCollector",
    "EventQueue",
    "LLMBackend",
    "LLMError",
    "LiteLLMBackend",
    "SimulatedBackend",
    "build_backend",
    "load_config",
    "default_config",
    "find_default_config",
    "resolve_status",
    "tally_votes",
    "MELCHIOR",
    "BALTHASAR",
    "CASPER",
    "ORCHESTRATOR",
    "AGENT_ORDER",
    "__version__",
]
