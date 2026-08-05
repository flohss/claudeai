"""Bus d'événements de la délibération.

Le noyau ignore qui l'observe : il émet des événements, et l'interface (CLI,
serveur web, tests) s'y abonne. C'est ce qui permet d'afficher le débat en
direct sans que l'orchestrateur ne connaisse le moindre détail d'affichage.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable

log = logging.getLogger("magi.events")


class EventType(str, Enum):
    DELIBERATION_STARTED = "deliberation_started"
    ROUND_STARTED = "round_started"
    AGENT_THINKING = "agent_thinking"
    AGENT_VERDICT = "agent_verdict"
    AGENT_ERROR = "agent_error"
    ROUND_COMPLETED = "round_completed"
    DEBATE_SKIPPED = "debate_skipped"
    CONVERGED = "converged"
    SYNTHESIS_STARTED = "synthesis_started"
    DECISION = "decision"
    FAILED = "failed"


@dataclass
class MagiEvent:
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type.value, "timestamp": self.timestamp, **self.payload}


# Un observateur peut être synchrone ou asynchrone : les deux sont acceptés.
EventSink = Callable[[MagiEvent], Awaitable[None] | None]


async def emit(sink: EventSink | None, event_type: EventType, **payload: Any) -> None:
    """Notifie l'observateur sans jamais compromettre la délibération.

    Une interface qui plante ne doit pas interrompre le débat : l'exception est
    journalisée puis avalée.
    """
    if sink is None:
        return
    try:
        result = sink(MagiEvent(event_type, payload))
        if inspect.isawaitable(result):
            await result
    except Exception:  # noqa: BLE001 - un observateur défaillant reste isolé
        log.exception("observateur d'événements en échec sur %s", event_type.value)


class EventCollector:
    """Observateur mémorisant tous les événements. Pratique pour les tests."""

    def __init__(self) -> None:
        self.events: list[MagiEvent] = []

    def __call__(self, event: MagiEvent) -> None:
        self.events.append(event)

    def of_type(self, event_type: EventType) -> list[MagiEvent]:
        return [e for e in self.events if e.type is event_type]

    @property
    def types(self) -> list[EventType]:
        return [e.type for e in self.events]


class EventQueue:
    """Observateur poussant les événements dans une file asyncio.

    Utilisé par le serveur web pour convertir la délibération en flux SSE.
    """

    def __init__(self, maxsize: int = 0) -> None:
        self.queue: asyncio.Queue[MagiEvent | None] = asyncio.Queue(maxsize=maxsize)

    async def __call__(self, event: MagiEvent) -> None:
        await self.queue.put(event)

    async def close(self) -> None:
        await self.queue.put(None)

    async def __aiter__(self):
        while True:
            event = await self.queue.get()
            if event is None:
                return
            yield event
