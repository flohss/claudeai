"""Serveur web du système MAGI.

Expose la délibération en Server-Sent Events : l'interface reçoit chaque
verdict au moment où l'agent le rend, sans attendre la fin du débat.

    magi serve --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from .config import MagiConfig, find_default_config, load_config, load_env_file
from .events import EventQueue, EventType, MagiEvent
from .models import AGENT_ORDER
from .orchestrator import MagiSystem

log = logging.getLogger("magi.server")

STATIC_DIR = Path(__file__).parent / "static"

# Durée maximale d'une délibération côté serveur. Sans plafond, un fournisseur
# qui ne répond jamais laisserait la connexion SSE ouverte indéfiniment.
DELIBERATION_TIMEOUT = 600.0


def create_app(config: MagiConfig | None = None) -> FastAPI:
    config = config or load_config(find_default_config())
    app = FastAPI(title="MAGI System", version="1.0.0", docs_url="/api/docs")
    app.state.config = config

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        page = STATIC_DIR / "index.html"
        if not page.exists():
            raise HTTPException(500, "interface introuvable : magi/static/index.html")
        return HTMLResponse(page.read_text(encoding="utf-8"))

    @app.get("/api/config")
    async def get_config() -> JSONResponse:
        cfg: MagiConfig = app.state.config
        return JSONResponse({
            "backend": cfg.backend,
            "max_debate_rounds": cfg.max_debate_rounds,
            "agents": [
                {"name": a.name, "model": a.model, "temperature": a.temperature}
                for a in cfg.agents
            ],
            "orchestrator": {"name": cfg.orchestrator.name, "model": cfg.orchestrator.model},
            "missing_api_keys": cfg.missing_api_keys(),
            "agent_order": list(AGENT_ORDER),
        })

    @app.get("/api/deliberate")
    async def deliberate_stream(
        q: str = Query(..., min_length=1, description="requête soumise au conseil"),
        context: str = Query("", description="contexte additionnel"),
        backend: str | None = Query(None, pattern="^(litellm|simulated)$"),
        rounds: int | None = Query(None, ge=0, le=5),
    ) -> StreamingResponse:
        """Flux SSE de la délibération complète."""
        cfg: MagiConfig = app.state.config
        if backend:
            cfg = cfg.with_backend(backend)
        if rounds is not None:
            cfg = replace(cfg, max_debate_rounds=rounds)

        missing = cfg.missing_api_keys()
        if missing:
            raise HTTPException(
                400,
                "Clés d'API manquantes : " + ", ".join(sorted(set(missing.values())))
                + ". Relancez avec backend=simulated pour une démonstration hors ligne.",
            )

        return StreamingResponse(
            _event_stream(MagiSystem(cfg), q, context),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # empêche nginx de bufferiser le flux
            },
        )

    @app.post("/api/deliberate")
    async def deliberate_once(payload: dict) -> JSONResponse:
        """Délibération classique, réponse unique en fin de traitement."""
        query = str(payload.get("query", "")).strip()
        if not query:
            raise HTTPException(400, "champ 'query' requis")

        cfg: MagiConfig = app.state.config
        if payload.get("backend") in {"litellm", "simulated"}:
            cfg = cfg.with_backend(payload["backend"])
        if isinstance(payload.get("rounds"), int):
            cfg = replace(cfg, max_debate_rounds=max(0, min(5, payload["rounds"])))

        try:
            decision = await asyncio.wait_for(
                MagiSystem(cfg).deliberate(query, str(payload.get("context", ""))),
                timeout=DELIBERATION_TIMEOUT,
            )
        except asyncio.TimeoutError:
            raise HTTPException(504, "délibération interrompue : délai dépassé") from None
        return JSONResponse(decision.to_dict())

    return app


async def _event_stream(system: MagiSystem, query: str, context: str):
    """Convertit les événements du noyau en messages SSE."""
    queue = EventQueue()

    async def run() -> None:
        try:
            await asyncio.wait_for(
                system.deliberate(query, context, queue), timeout=DELIBERATION_TIMEOUT
            )
        except asyncio.TimeoutError:
            await queue(MagiEvent(EventType.FAILED, {"error": "délai de délibération dépassé"}))
        except Exception as exc:  # noqa: BLE001 - l'erreur doit atteindre le navigateur
            log.exception("délibération en échec")
            await queue(MagiEvent(EventType.FAILED, {"error": str(exc)}))
        finally:
            await queue.close()

    task = asyncio.create_task(run())
    try:
        async for event in queue:
            yield f"event: {event.type.value}\ndata: {json.dumps(event.to_dict(), ensure_ascii=False)}\n\n"
        yield "event: close\ndata: {}\n\n"
    finally:
        # Le client a fermé l'onglet : inutile de continuer à consommer des tokens.
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


app = None  # rempli à la demande par `uvicorn magi.server:get_app`


def get_app() -> FastAPI:
    """Point d'entrée ASGI : `uvicorn 'magi.server:get_app' --factory`.

    Ce chemin ne passe pas par la CLI : il charge donc lui-même le .env.
    """
    load_env_file()
    return create_app()
