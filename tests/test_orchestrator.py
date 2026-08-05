"""Workflow de délibération : parallélisme, débat, convergence, mode dégradé."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import replace

import pytest

from magi.backends import CompletionRequest, LLMError, SimulatedBackend
from magi.config import default_config
from magi.events import EventCollector, EventType
from magi.models import BALTHASAR, CASPER, MELCHIOR, ORCHESTRATOR, SystemStatus, Vote
from magi.orchestrator import MagiSystem


def verdict_json(agent: str, vote: str, confidence: float = 0.8, argument: str = "argument") -> str:
    return json.dumps({
        "agent": agent,
        "vote": vote,
        "confidence_score": confidence,
        "key_arguments": [argument],
        "detailed_analysis": f"analyse de {agent}",
    }, ensure_ascii=False)


SYNTHESIS_JSON = json.dumps({
    "final_answer": "Réponse de synthèse du conseil.",
    "conditions": ["condition vérifiable"],
    "dissent": "",
    "synthesis_reasoning": "arbitrage",
}, ensure_ascii=False)


class ScriptedBackend:
    """Backend piloté par un script, pour contrôler exactement chaque tour.

    `script` reçoit la requête et renvoie soit une chaîne, soit une exception à
    lever (pour simuler une panne de fournisseur).
    """

    name = "scripted"

    def __init__(self, script) -> None:
        self.script = script
        self.calls: list[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> str:
        self.calls.append(request)
        result = self.script(request)
        if isinstance(result, BaseException):
            raise result
        return result

    def calls_for(self, agent: str) -> list[CompletionRequest]:
        return [c for c in self.calls if c.agent == agent]


def make_system(script, rounds: int = 2) -> MagiSystem:
    config = replace(default_config(), max_debate_rounds=rounds, backend="scripted")
    return MagiSystem(config, ScriptedBackend(script))


def votes_script(per_round: dict[int, dict[str, str]]):
    """Fabrique un script à partir d'une table {tour: {agent: vote}}."""

    def script(request: CompletionRequest):
        if request.agent == ORCHESTRATOR:
            return SYNTHESIS_JSON
        table = per_round.get(request.round_index, per_round[max(per_round)])
        return verdict_json(request.agent, table[request.agent])

    return script


class TestFirstRound:
    async def test_unanimous_approval_skips_the_debate(self):
        system = make_system(votes_script({0: dict.fromkeys(
            (MELCHIOR, BALTHASAR, CASPER), "APPROVED")}))
        collector = EventCollector()

        decision = await system.deliberate("Question ?", on_event=collector)

        assert decision.status is SystemStatus.UNANIMOUS_APPROVAL
        assert decision.rounds_used == 1, "aucun tour de débat ne doit être engagé"
        assert EventType.DEBATE_SKIPPED in collector.types
        assert EventType.ROUND_STARTED in collector.types

    async def test_unanimous_rejection_also_skips_the_debate(self):
        system = make_system(votes_script({0: dict.fromkeys(
            (MELCHIOR, BALTHASAR, CASPER), "REJECTED")}))
        decision = await system.deliberate("Question ?")

        assert decision.status is SystemStatus.REJECTED
        assert decision.rounds_used == 1

    async def test_agents_receive_no_peer_information_in_round_one(self):
        system = make_system(votes_script({0: dict.fromkeys(
            (MELCHIOR, BALTHASAR, CASPER), "APPROVED")}))
        await system.deliberate("Question ?")

        for call in system.backend.calls:
            if call.agent != ORCHESTRATOR:
                assert "POSITIONS DES AUTRES MAGI" not in call.user

    async def test_agents_are_queried_in_parallel(self):
        async def slow_complete(request):
            await asyncio.sleep(0.25)
            if request.agent == ORCHESTRATOR:
                return SYNTHESIS_JSON
            return verdict_json(request.agent, "APPROVED")

        system = make_system(lambda r: None)
        system.backend.complete = slow_complete  # type: ignore[method-assign]

        started = time.perf_counter()
        await system.deliberate("Question ?")
        elapsed = time.perf_counter() - started

        # Trois agents en parallèle (0,25 s) puis la synthèse (0,25 s) : très
        # en dessous des 1,0 s qu'exigerait une exécution séquentielle.
        assert elapsed < 0.75, f"exécution apparemment séquentielle ({elapsed:.2f}s)"


class TestDebate:
    async def test_disagreement_triggers_a_debate_round(self):
        system = make_system(
            votes_script({
                0: {MELCHIOR: "APPROVED", BALTHASAR: "REJECTED", CASPER: "CONDITIONAL"},
                1: dict.fromkeys((MELCHIOR, BALTHASAR, CASPER), "APPROVED"),
            }),
            rounds=2,
        )
        collector = EventCollector()
        decision = await system.deliberate("Question ?", on_event=collector)

        assert decision.rounds_used == 2
        assert decision.status is SystemStatus.UNANIMOUS_APPROVAL
        assert EventType.CONVERGED in collector.types

    async def test_debate_prompt_contains_peer_positions_but_not_the_agent_itself(self):
        system = make_system(
            votes_script({
                0: {MELCHIOR: "APPROVED", BALTHASAR: "REJECTED", CASPER: "CONDITIONAL"},
                1: {MELCHIOR: "APPROVED", BALTHASAR: "REJECTED", CASPER: "CONDITIONAL"},
            }),
            rounds=1,
        )
        await system.deliberate("Question ?")

        debate_call = [c for c in system.backend.calls_for(MELCHIOR) if c.round_index == 1][0]
        peers_block = debate_call.user.split("POSITIONS DES AUTRES MAGI")[1]
        assert BALTHASAR in peers_block and CASPER in peers_block
        assert MELCHIOR not in peers_block, "un agent ne doit pas se voir listé parmi ses pairs"

    async def test_stops_when_no_vote_changes(self):
        frozen = {MELCHIOR: "APPROVED", BALTHASAR: "REJECTED", CASPER: "CONDITIONAL"}
        system = make_system(votes_script({0: frozen, 1: frozen, 2: frozen}), rounds=3)
        collector = EventCollector()

        decision = await system.deliberate("Question ?", on_event=collector)

        # Un tour de débat suffit à constater l'immobilisme : les tours 2 et 3
        # sont économisés.
        assert decision.rounds_used == 2
        converged = collector.of_type(EventType.CONVERGED)
        assert converged and "stabilisées" in converged[0].payload["reason"]

    async def test_convergence_stop_can_be_disabled(self):
        frozen = {MELCHIOR: "APPROVED", BALTHASAR: "REJECTED", CASPER: "CONDITIONAL"}
        config = replace(default_config(), max_debate_rounds=2,
                         stop_on_convergence=False, backend="scripted")
        system = MagiSystem(config, ScriptedBackend(votes_script({0: frozen})))

        decision = await system.deliberate("Question ?")
        assert decision.rounds_used == 3

    async def test_zero_rounds_means_no_debate_at_all(self):
        system = make_system(
            votes_script({0: {MELCHIOR: "APPROVED", BALTHASAR: "REJECTED", CASPER: "APPROVED"}}),
            rounds=0,
        )
        decision = await system.deliberate("Question ?")

        assert decision.rounds_used == 1
        assert decision.status is SystemStatus.MAJORITY_APPROVAL


class TestDegradedMode:
    async def test_a_failing_agent_does_not_stop_the_council(self):
        def script(request: CompletionRequest):
            if request.agent == CASPER:
                return LLMError("fournisseur injoignable")
            if request.agent == ORCHESTRATOR:
                return SYNTHESIS_JSON
            return verdict_json(request.agent, "APPROVED")

        system = make_system(script, rounds=0)
        collector = EventCollector()
        decision = await system.deliberate("Question ?", on_event=collector)

        casper = [v for v in decision.final_verdicts if v.agent == CASPER][0]
        assert casper.degraded and casper.vote is Vote.CONDITIONAL
        assert casper.confidence_score == 0.0
        assert decision.degraded
        # Les deux agents valides gardent leur voix.
        assert decision.status is SystemStatus.MAJORITY_APPROVAL
        assert EventType.AGENT_ERROR in collector.types

    async def test_malformed_json_triggers_one_repair_attempt(self):
        attempts: dict[str, int] = {}

        def script(request: CompletionRequest):
            if request.agent == ORCHESTRATOR:
                return SYNTHESIS_JSON
            attempts[request.agent] = attempts.get(request.agent, 0) + 1
            if attempts[request.agent] == 1:
                return "Je pense que c'est une bonne idée, franchement."
            return verdict_json(request.agent, "APPROVED")

        system = make_system(script, rounds=0)
        decision = await system.deliberate("Question ?")

        assert not decision.degraded
        assert decision.status is SystemStatus.UNANIMOUS_APPROVAL
        assert attempts[MELCHIOR] == 2, "une seule tentative de réparation attendue"

    async def test_persistent_garbage_produces_a_degraded_verdict(self):
        def script(request: CompletionRequest):
            if request.agent == ORCHESTRATOR:
                return SYNTHESIS_JSON
            return "toujours pas de JSON"

        system = make_system(script, rounds=0)
        decision = await system.deliberate("Question ?")

        assert all(v.degraded for v in decision.final_verdicts)
        assert decision.status is SystemStatus.CONDITIONAL_APPROVAL

    async def test_orchestrator_failure_falls_back_to_a_local_synthesis(self):
        def script(request: CompletionRequest):
            if request.agent == ORCHESTRATOR:
                return LLMError("orchestrateur hors service")
            return verdict_json(request.agent, "APPROVED", argument="argument décisif")

        system = make_system(script, rounds=0)
        decision = await system.deliberate("Question ?")

        assert decision.status is SystemStatus.UNANIMOUS_APPROVAL
        assert decision.degraded
        # Le débat n'est pas perdu : ses arguments sont restitués.
        assert "argument décisif" in decision.final_answer
        assert "dégradée" in decision.final_answer

    async def test_empty_synthesis_also_falls_back(self):
        empty = json.dumps({"final_answer": "   ", "conditions": []})

        def script(request: CompletionRequest):
            if request.agent == ORCHESTRATOR:
                return empty
            return verdict_json(request.agent, "APPROVED")

        decision = await make_system(script, rounds=0).deliberate("Question ?")
        assert decision.degraded and decision.final_answer.strip()


class TestSynthesisInput:
    async def test_orchestrator_receives_the_full_transcript_and_the_computed_status(self):
        system = make_system(
            votes_script({
                0: {MELCHIOR: "APPROVED", BALTHASAR: "REJECTED", CASPER: "APPROVED"},
                1: {MELCHIOR: "APPROVED", BALTHASAR: "REJECTED", CASPER: "APPROVED"},
            }),
            rounds=1,
        )
        await system.deliberate("Faut-il migrer ?")

        prompt = system.backend.calls_for(ORCHESTRATOR)[0].user
        assert "MAJORITY APPROVAL" in prompt
        assert "TOUR 1 — ANALYSE INDÉPENDANTE" in prompt
        assert "TOUR 2 — DÉBAT CONTRADICTOIRE" in prompt
        assert "Faut-il migrer ?" in prompt
        for agent in (MELCHIOR, BALTHASAR, CASPER):
            assert agent in prompt

    async def test_status_is_computed_by_the_core_not_by_the_model(self):
        # L'orchestrateur affirme l'unanimité alors que les votes disent l'inverse.
        lying = json.dumps({
            "final_answer": "Tout le monde est d'accord.",
            "conditions": [], "dissent": "", "synthesis_reasoning": "",
        })

        def script(request: CompletionRequest):
            if request.agent == ORCHESTRATOR:
                return lying
            return verdict_json(request.agent, "REJECTED")

        decision = await make_system(script, rounds=0).deliberate("Question ?")
        assert decision.status is SystemStatus.REJECTED


class TestEventStream:
    async def test_event_sequence(self):
        system = make_system(votes_script({0: dict.fromkeys(
            (MELCHIOR, BALTHASAR, CASPER), "APPROVED")}))
        collector = EventCollector()
        await system.deliberate("Question ?", on_event=collector)

        types = collector.types
        assert types[0] is EventType.DELIBERATION_STARTED
        assert types[-1] is EventType.DECISION
        assert types.count(EventType.AGENT_THINKING) == 3
        assert types.count(EventType.AGENT_VERDICT) == 3
        assert EventType.SYNTHESIS_STARTED in types

    async def test_a_broken_observer_does_not_break_the_deliberation(self):
        def exploding_sink(event):
            raise RuntimeError("interface en panne")

        system = make_system(votes_script({0: dict.fromkeys(
            (MELCHIOR, BALTHASAR, CASPER), "APPROVED")}))
        decision = await system.deliberate("Question ?", on_event=exploding_sink)

        assert decision.status is SystemStatus.UNANIMOUS_APPROVAL

    async def test_async_observers_are_supported(self):
        received: list[EventType] = []

        async def async_sink(event):
            await asyncio.sleep(0)
            received.append(event.type)

        system = make_system(votes_script({0: dict.fromkeys(
            (MELCHIOR, BALTHASAR, CASPER), "APPROVED")}))
        await system.deliberate("Question ?", on_event=async_sink)

        assert EventType.DECISION in received


class TestValidation:
    @pytest.mark.parametrize("query", ["", "   ", "\n"])
    async def test_empty_query_is_rejected(self, query):
        system = make_system(votes_script({0: dict.fromkeys(
            (MELCHIOR, BALTHASAR, CASPER), "APPROVED")}))
        with pytest.raises(ValueError, match="vide"):
            await system.deliberate(query)


class TestSimulatedBackend:
    async def test_offline_deliberation_produces_a_complete_decision(self):
        config = replace(default_config(), backend="simulated",
                         simulated_latency=0.0, max_debate_rounds=1)
        decision = await MagiSystem(config).deliberate("Faut-il réécrire le monolithe ?")

        assert decision.final_answer
        assert len(decision.final_verdicts) == 3
        assert not decision.degraded
        assert decision.status in set(SystemStatus)

    async def test_results_are_deterministic_for_a_given_query(self):
        config = replace(default_config(), backend="simulated",
                         simulated_latency=0.0, max_debate_rounds=0)
        query = "Faut-il chiffrer les sauvegardes ?"

        first = await MagiSystem(config).deliberate(query)
        second = await MagiSystem(config).deliberate(query)

        assert first.tally() == second.tally()

    async def test_serialisation_round_trip(self):
        config = replace(default_config(), backend="simulated", simulated_latency=0.0)
        decision = await MagiSystem(config).deliberate("Question de test ?")

        payload = json.loads(json.dumps(decision.to_dict(), ensure_ascii=False))
        assert payload["status"] == decision.status.value
        assert len(payload["rounds"]) == decision.rounds_used
        assert set(payload["tally"]) == {"APPROVED", "CONDITIONAL", "REJECTED"}

    async def test_simulated_backend_makes_no_network_call(self, monkeypatch):
        import litellm

        async def forbidden(*args, **kwargs):
            raise AssertionError("le backend simulé ne doit émettre aucun appel réseau")

        monkeypatch.setattr(litellm, "acompletion", forbidden)
        config = replace(default_config(), backend="simulated", simulated_latency=0.0)
        assert await MagiSystem(config).deliberate("Question ?")
