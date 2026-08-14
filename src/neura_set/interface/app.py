"""FastAPI + WebSocket app: pushes proposals to the browser, relays
accept/reject clicks back to the orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Awaitable, Callable

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, Response

from neura_set.interface.websocket_manager import ConnectionManager
from neura_set.types import MusicalContext, Proposal

FeedbackCallback = Callable[[str, bool], Awaitable[None]]

STATIC_DIR = Path(__file__).parent / "static"

# Serving a manifest + icon lets Android Chrome offer "Add to Home screen":
# the page then launches full-screen, with its own icon and theme color,
# indistinguishable from an installed app. No build step needed — the icon
# is a plain inline SVG, so there's no binary asset to ship alongside the code.
_MANIFEST = {
    "name": "NEURA-SET",
    "short_name": "NEURA-SET",
    "description": "Votre co-producteur musical, à l'écoute",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#f7f7fb",
    "theme_color": "#6c5ce7",
    "orientation": "portrait",
    "icons": [
        {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}
    ],
}

_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">
  <rect width="192" height="192" rx="40" fill="#6c5ce7"/>
  <text x="96" y="132" font-size="104" text-anchor="middle" font-family="sans-serif">🎹</text>
</svg>"""


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


def _context_to_json(context: MusicalContext) -> dict:
    return {
        "tempo_bpm": context.tempo_bpm,
        "key_root_pc": context.key_root_pc,
        "key_is_minor": context.key_is_minor,
        "chord_root_pc": context.chord_root_pc,
        "chord_is_minor": context.chord_is_minor,
        "section": context.section.value,
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
            return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        @app.get("/manifest.webmanifest")
        async def manifest() -> JSONResponse:
            return JSONResponse(_MANIFEST, media_type="application/manifest+json")

        @app.get("/icon.svg")
        async def icon() -> Response:
            return Response(content=_ICON_SVG, media_type="image/svg+xml")

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

    async def push_context(self, context: MusicalContext) -> None:
        """Broadcast the current listening state on every analysis tick —
        distinct from push_proposal, which only fires when there's
        actually something to accept/reject. Lets the UI show a live
        tempo/key/section readout instead of only updating when a
        proposal happens to land."""
        await self.manager.broadcast(
            {"type": "context", "context": _context_to_json(context)}
        )
