"""Interface web : endpoints REST et flux SSE."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from magi.config import default_config

fastapi_testclient = pytest.importorskip("fastapi.testclient")
TestClient = fastapi_testclient.TestClient


@pytest.fixture
def client():
    from magi.server import create_app

    config = replace(default_config(), backend="simulated",
                     simulated_latency=0.0, max_debate_rounds=1)
    with TestClient(create_app(config)) as test_client:
        yield test_client


class TestStaticAndConfig:
    def test_index_serves_the_interface(self, client):
        response = client.get("/")
        assert response.status_code == 200
        body = response.text
        assert "MAGI" in body
        for label in ("PROPOSAL", "AGREEMENT", "DENIAL"):
            assert label in body, f"le bloc d'état {label} doit être présent"

    def test_config_endpoint(self, client):
        payload = client.get("/api/config").json()
        assert payload["backend"] == "simulated"
        assert [a["name"] for a in payload["agents"]] == payload["agent_order"]
        assert payload["missing_api_keys"] == {}


class TestPostDeliberate:
    def test_returns_a_complete_decision(self, client):
        response = client.post("/api/deliberate", json={"query": "Faut-il indexer cette table ?"})
        assert response.status_code == 200

        payload = response.json()
        assert payload["status"] in {
            "UNANIMOUS APPROVAL", "MAJORITY APPROVAL", "CONDITIONAL APPROVAL", "REJECTED"
        }
        assert payload["final_answer"]
        assert len(payload["rounds"][0]["verdicts"]) == 3

    def test_empty_query_is_rejected(self, client):
        assert client.post("/api/deliberate", json={"query": "   "}).status_code == 400

    def test_rounds_are_capped(self, client):
        payload = client.post(
            "/api/deliberate", json={"query": "Question ?", "rounds": 99}
        ).json()
        assert payload["rounds_used"] <= 6


class TestSseStream:
    def _events(self, raw: str) -> list[dict]:
        events = []
        for block in raw.strip().split("\n\n"):
            for line in block.splitlines():
                if line.startswith("data: "):
                    payload = line[6:]
                    if payload.strip() != "{}":
                        events.append(json.loads(payload))
        return events

    def test_stream_emits_the_full_lifecycle(self, client):
        with client.stream("GET", "/api/deliberate",
                           params={"q": "Faut-il activer le cache ?", "backend": "simulated"}) as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]
            events = self._events("".join(r.iter_text()))

        types = [e["type"] for e in events]
        assert types[0] == "deliberation_started"
        assert types[-1] == "decision"
        assert types.count("agent_verdict") + types.count("agent_error") >= 3

        decision = events[-1]["decision"]
        assert decision["final_answer"]
        assert decision["rounds"]

    def test_verdicts_carry_everything_the_interface_needs(self, client):
        with client.stream("GET", "/api/deliberate",
                           params={"q": "Question ?", "backend": "simulated"}) as r:
            events = self._events("".join(r.iter_text()))

        verdicts = [e["verdict"] for e in events if e["type"] in ("agent_verdict", "agent_error")]
        assert verdicts
        for verdict in verdicts:
            assert set(verdict) >= {
                "agent", "vote", "confidence_score", "key_arguments",
                "detailed_analysis", "latency_ms", "degraded",
            }

    def test_missing_query_is_a_client_error(self, client):
        assert client.get("/api/deliberate").status_code == 422

    def test_invalid_backend_is_rejected(self, client):
        response = client.get("/api/deliberate", params={"q": "Question ?", "backend": "voodoo"})
        assert response.status_code == 422

    def test_live_backend_without_keys_is_refused_upfront(self, client, monkeypatch):
        for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        response = client.get("/api/deliberate", params={"q": "Question ?", "backend": "litellm"})
        assert response.status_code == 400
        assert "API" in response.json()["detail"]
