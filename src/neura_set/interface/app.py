"""FastAPI + WebSocket app: pushes proposals to the browser, relays
accept/reject clicks back to the orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Awaitable, Callable

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from neura_set.interface.websocket_manager import ConnectionManager
from neura_set.types import Proposal

FeedbackCallback = Callable[[str, bool], Awaitable[None]]

STATIC_DIR = Path(__file__).parent / "static"


def _proposal_to_json(proposal: Proposal) -> dict:
    return {
        "id": proposal.id,
        "generator_name": proposal.generator_name,
        "style": proposal.style,
        "created_at": proposal.created_at,
        "notes": [
            {
                "pitch": n.pitch,
                "start_beat": n.start_beat,
                "duration_beats": n.duration_beats,
                "velocity": n.velocity,
            }
            for n in proposal.notes
        ],
        "context": {
            "tempo_bpm": proposal.context.tempo_bpm,
            "key_root_pc": proposal.context.key_root_pc,
            "key_is_minor": proposal.context.key_is_minor,
            "section": proposal.context.section.value,
        },
    }


class InterfaceServer:
    """Owns the FastAPI app. `on_feedback(proposal_id, accepted)` is set
    by the orchestrator to route accept/reject clicks into the decision
    agent + Ableton controller."""

    def __init__(self) -> None:
        self.app = FastAPI(title="NEURA-SET")
        self.manager = ConnectionManager()
        self.on_feedback: FeedbackCallback | None = None
        self._register_routes()

    def _register_routes(self) -> None:
        app = self.app

        @app.get("/", response_class=HTMLResponse)
        async def index() -> str:
            return (STATIC_DIR / "index.html").read_text()

        @app.websocket("/ws")
        async def ws_endpoint(websocket: WebSocket) -> None:
            await self.manager.connect(websocket)
            try:
                while True:
                    message = await websocket.receive_json()
                    if message.get("type") in ("accept", "reject") and self.on_feedback:
                        await self.on_feedback(
                            message["proposal_id"], message["type"] == "accept"
                        )
            except WebSocketDisconnect:
                await self.manager.disconnect(websocket)

    async def push_proposal(self, proposal: Proposal) -> None:
        await self.manager.broadcast(
            {"type": "proposal", "proposal": _proposal_to_json(proposal)}
        )
