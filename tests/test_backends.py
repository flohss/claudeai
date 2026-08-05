"""Backends LLM : politique de réessai, repli JSON, simulation hors ligne."""

from __future__ import annotations

import json

import pytest

from magi.backends import (
    CompletionRequest,
    LiteLLMBackend,
    LLMError,
    SimulatedBackend,
    build_backend,
)
from magi.models import BALTHASAR, CASPER, MELCHIOR, ORCHESTRATOR


def request(**kwargs) -> CompletionRequest:
    base = dict(model="openai/gpt-4o", system="doctrine", user="REQUÊTE\n---\nQuestion ?\n---",
                agent=MELCHIOR)
    base.update(kwargs)
    return CompletionRequest(**base)


class FakeResponse:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]


@pytest.fixture
def litellm_module(monkeypatch):
    """Remplace litellm par un double contrôlable."""
    import litellm

    monkeypatch.setattr("asyncio.sleep", _instant_sleep)
    return litellm


async def _instant_sleep(_seconds):
    return None


class TestLiteLLMBackend:
    async def test_successful_call(self, litellm_module, monkeypatch):
        async def acompletion(**kwargs):
            return FakeResponse('{"vote": "APPROVED"}')

        monkeypatch.setattr(litellm_module, "acompletion", acompletion)
        assert await LiteLLMBackend().complete(request()) == '{"vote": "APPROVED"}'

    async def test_parameters_are_forwarded(self, litellm_module, monkeypatch):
        captured = {}

        async def acompletion(**kwargs):
            captured.update(kwargs)
            return FakeResponse("{}")

        monkeypatch.setattr(litellm_module, "acompletion", acompletion)
        await LiteLLMBackend().complete(
            request(model="anthropic/claude-opus-5", temperature=0.2, max_tokens=900)
        )

        assert captured["model"] == "anthropic/claude-opus-5"
        assert captured["temperature"] == 0.2
        assert captured["max_tokens"] == 900
        assert captured["messages"][0]["role"] == "system"
        assert captured["messages"][1]["content"].startswith("REQUÊTE")

    async def test_transient_errors_are_retried(self, litellm_module, monkeypatch):
        attempts = {"n": 0}

        async def acompletion(**kwargs):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise RuntimeError("rate limit exceeded (429)")
            return FakeResponse("ok")

        monkeypatch.setattr(litellm_module, "acompletion", acompletion)
        assert await LiteLLMBackend(base_delay=0).complete(request()) == "ok"
        assert attempts["n"] == 3

    async def test_retries_are_bounded(self, litellm_module, monkeypatch):
        attempts = {"n": 0}

        async def acompletion(**kwargs):
            attempts["n"] += 1
            raise RuntimeError("service temporarily unavailable (503)")

        monkeypatch.setattr(litellm_module, "acompletion", acompletion)
        with pytest.raises(LLMError):
            await LiteLLMBackend(max_retries=2, base_delay=0).complete(request())
        assert attempts["n"] == 2

    async def test_authentication_errors_fail_immediately(self, litellm_module, monkeypatch):
        attempts = {"n": 0}

        async def acompletion(**kwargs):
            attempts["n"] += 1
            raise RuntimeError("Missing API key for provider")

        monkeypatch.setattr(litellm_module, "acompletion", acompletion)
        with pytest.raises(LLMError, match="API key"):
            await LiteLLMBackend(base_delay=0).complete(request())
        # Réessayer une clé absente ne fait que perdre du temps.
        assert attempts["n"] == 1

    async def test_json_mode_is_dropped_when_unsupported(self, litellm_module, monkeypatch):
        seen: list[bool] = []

        async def acompletion(**kwargs):
            has_format = "response_format" in kwargs
            seen.append(has_format)
            if has_format:
                raise RuntimeError("response_format is not supported by this model")
            return FakeResponse("{}")

        monkeypatch.setattr(litellm_module, "acompletion", acompletion)
        backend = LiteLLMBackend(base_delay=0)

        assert await backend.complete(request(json_mode=True)) == "{}"
        assert seen == [True, False]

        # Le modèle est mémorisé : le second appel n'essaie plus le mode JSON.
        seen.clear()
        await backend.complete(request(json_mode=True))
        assert seen == [False]

    async def test_empty_response_is_an_error(self, litellm_module, monkeypatch):
        async def acompletion(**kwargs):
            return FakeResponse("   ")

        monkeypatch.setattr(litellm_module, "acompletion", acompletion)
        with pytest.raises(LLMError, match="vide"):
            await LiteLLMBackend(base_delay=0).complete(request())

    async def test_block_style_content_is_flattened(self, litellm_module, monkeypatch):
        async def acompletion(**kwargs):
            return FakeResponse([{"type": "text", "text": '{"vote": '}, {"type": "text", "text": '"APPROVED"}'}])

        monkeypatch.setattr(litellm_module, "acompletion", acompletion)
        assert json.loads(await LiteLLMBackend().complete(request()))["vote"] == "APPROVED"


class TestSimulatedBackend:
    async def test_produces_valid_agent_json(self):
        backend = SimulatedBackend(latency=0)
        for agent in (MELCHIOR, BALTHASAR, CASPER):
            payload = json.loads(await backend.complete(request(agent=agent)))
            assert payload["agent"] == agent
            assert payload["vote"] in {"APPROVED", "REJECTED", "CONDITIONAL"}
            assert 0.0 <= payload["confidence_score"] <= 1.0
            assert payload["key_arguments"]

    async def test_output_is_marked_as_simulated(self):
        payload = json.loads(await SimulatedBackend(latency=0).complete(request()))
        assert "SIMULATION" in payload["detailed_analysis"]

    async def test_deterministic_for_identical_input(self):
        backend = SimulatedBackend(latency=0)
        first = await backend.complete(request())
        second = await backend.complete(request())
        assert first == second

    async def test_different_agents_diverge(self):
        backend = SimulatedBackend(latency=0)
        outputs = {a: await backend.complete(request(agent=a))
                   for a in (MELCHIOR, BALTHASAR, CASPER)}
        assert len(set(outputs.values())) == 3

    async def test_risky_queries_push_balthasar_towards_caution(self):
        backend = SimulatedBackend(latency=0)
        risky = ("REQUÊTE\n---\nSupprimer les données personnelles de santé "
                 "en production sans sauvegarde ?\n---")
        votes = []
        for suffix in range(12):  # plusieurs formulations pour lisser le hachage
            payload = json.loads(await backend.complete(
                request(agent=BALTHASAR, user=risky.replace("?", f"? #{suffix}"))
            ))
            votes.append(payload["vote"])
        assert votes.count("APPROVED") < len(votes) / 2

    async def test_orchestrator_synthesis_shape(self):
        user = ("REQUÊTE UTILISATEUR\n---\nQuestion ?\n---\n"
                "STATUT SYSTÈME CALCULÉ PAR LE NOYAU : UNANIMOUS APPROVAL\n")
        payload = json.loads(await SimulatedBackend(latency=0).complete(
            request(agent=ORCHESTRATOR, user=user)
        ))
        assert payload["final_answer"]
        assert payload["conditions"] == []
        assert payload["dissent"] == ""

    async def test_rejected_status_yields_conditions(self):
        user = ("REQUÊTE UTILISATEUR\n---\nQuestion ?\n---\n"
                "STATUT SYSTÈME CALCULÉ PAR LE NOYAU : REJECTED\n")
        payload = json.loads(await SimulatedBackend(latency=0).complete(
            request(agent=ORCHESTRATOR, user=user)
        ))
        assert payload["conditions"]


class TestBuildBackend:
    @pytest.mark.parametrize("name", ["simulated", "SIMULATED", "offline", "mock", "demo"])
    def test_simulated_aliases(self, name):
        assert isinstance(build_backend(name), SimulatedBackend)

    @pytest.mark.parametrize("name", ["litellm", "live", "real", ""])
    def test_litellm_aliases(self, name):
        assert isinstance(build_backend(name), LiteLLMBackend)

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="backend inconnu"):
            build_backend("telepathie")
