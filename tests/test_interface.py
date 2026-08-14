import asyncio

from fastapi.testclient import TestClient

from neura_set.interface.app import _context_to_json
from neura_set.orchestrator import Orchestrator, create_app
from neura_set.types import MusicalContext, SectionLabel


def test_context_to_json_shape():
    ctx = MusicalContext(
        tempo_bpm=128.0,
        key_root_pc=2,
        key_is_minor=True,
        chord_root_pc=9,
        chord_is_minor=False,
        section=SectionLabel.CHORUS,
    )
    payload = _context_to_json(ctx)
    assert payload == {
        "tempo_bpm": 128.0,
        "key_root_pc": 2,
        "key_is_minor": True,
        "chord_root_pc": 9,
        "chord_is_minor": False,
        "section": "chorus",
    }


def test_push_context_broadcasts_to_connected_clients():
    orch = Orchestrator(ableton_track_id=None)
    app = create_app(orch)
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        ctx = MusicalContext(tempo_bpm=90.0, section=SectionLabel.INTRO)
        asyncio.run(orch.interface.push_context(ctx))
        msg = ws.receive_json()

    assert msg["type"] == "context"
    assert msg["context"]["tempo_bpm"] == 90.0
    assert msg["context"]["section"] == "intro"
