"""Orchestrateur MAGI : conduite du débat et synthèse finale.

Séquence appliquée par `MagiSystem.deliberate()` :

  1. analyse indépendante — les trois agents sont interrogés en parallèle et
     ne voient pas les réponses des autres ;
  2. débat contradictoire — tant qu'il reste du désaccord et des tours
     disponibles, chaque agent reçoit les positions adverses et révise la
     sienne ;
  3. synthèse — le statut système est calculé par le noyau à partir des votes
     finaux, puis un quatrième modèle rédige la réponse à l'utilisateur.
"""

from __future__ import annotations

import asyncio
import logging
import time

from .agent import MagiAgent
from .backends import CompletionRequest, LLMBackend, LLMError, build_backend
from .config import MagiConfig, default_config
from .events import EventSink, EventType, emit
from .models import (
    AgentVerdict,
    DebateRound,
    MagiDecision,
    SystemStatus,
    Vote,
    consensus_confidence,
    resolve_status,
    tally_votes,
)
from .parsing import JSONExtractionError, coerce_str_list, extract_json
from .prompts import synthesis_prompt

log = logging.getLogger("magi.orchestrator")


class MagiSystem:
    """Le conseil complet : trois agents délibérants et un orchestrateur."""

    def __init__(self, config: MagiConfig | None = None, backend: LLMBackend | None = None) -> None:
        self.config = config or default_config()
        self.backend = backend or build_backend(
            self.config.backend,
            latency=self.config.simulated_latency,
            max_retries=self.config.max_retries,
        )
        self.agents = [MagiAgent(cfg, self.backend) for cfg in self.config.agents]

    # -- API publique -------------------------------------------------------

    async def deliberate(
        self,
        query: str,
        context: str = "",
        on_event: EventSink | None = None,
    ) -> MagiDecision:
        """Exécute la délibération complète et retourne la décision finale."""
        if not query or not query.strip():
            raise ValueError("la requête soumise au conseil est vide")

        started = time.perf_counter()
        await emit(
            on_event,
            EventType.DELIBERATION_STARTED,
            query=query,
            agents=[{"name": a.name, "model": a.model, "temperature": a.config.temperature}
                    for a in self.agents],
            max_rounds=self.config.max_debate_rounds,
            backend=self.backend.name,
        )

        rounds: list[DebateRound] = []

        # --- Étape 1 : analyse indépendante --------------------------------
        first = await self._run_round(
            0, on_event, lambda agent: agent.analyze(query, context, 0)
        )
        rounds.append(first)

        # --- Étape 2 : débat contradictoire --------------------------------
        if first.is_unanimous and self.config.stop_on_unanimity:
            await emit(on_event, EventType.DEBATE_SKIPPED,
                       reason="unanimité dès le premier tour",
                       vote=first.votes[0].value)
        else:
            await self._run_debate(query, rounds, on_event)

        # --- Étape 3 : synthèse --------------------------------------------
        final = rounds[-1].verdicts
        status = resolve_status(final)
        await emit(on_event, EventType.SYNTHESIS_STARTED,
                   status=status.value,
                   tally={v.value: c for v, c in tally_votes(final).items()},
                   model=self.config.orchestrator.model)

        synthesis = await self._synthesize(query, status, rounds)

        decision = MagiDecision(
            query=query,
            status=status,
            final_answer=synthesis["final_answer"],
            rounds=rounds,
            conditions=synthesis["conditions"],
            dissent=synthesis["dissent"],
            synthesis_reasoning=synthesis["synthesis_reasoning"],
            consensus_confidence=consensus_confidence(final, status),
            total_duration_ms=int((time.perf_counter() - started) * 1000),
            degraded=any(v.degraded for v in final) or synthesis["degraded"],
        )
        await emit(on_event, EventType.DECISION, decision=decision.to_dict())
        return decision

    def deliberate_sync(self, query: str, context: str = "",
                        on_event: EventSink | None = None) -> MagiDecision:
        """Enveloppe synchrone, pour les appelants qui ne gèrent pas asyncio."""
        return asyncio.run(self.deliberate(query, context, on_event))

    # -- étapes internes ----------------------------------------------------

    async def _run_round(self, index: int, on_event: EventSink | None, call) -> DebateRound:
        """Interroge les trois agents en parallèle et collecte leurs verdicts.

        Chaque agent est encapsulé pour émettre son propre événement dès qu'il
        a terminé : l'interface affiche donc les verdicts au fil de l'eau, sans
        attendre le plus lent du tour.
        """
        await emit(on_event, EventType.ROUND_STARTED, round=index,
                   agents=[a.name for a in self.agents])
        started = time.perf_counter()

        async def run(agent: MagiAgent) -> AgentVerdict:
            await emit(on_event, EventType.AGENT_THINKING, round=index,
                       agent=agent.name, model=agent.model)
            verdict = await call(agent)
            event = EventType.AGENT_ERROR if verdict.degraded else EventType.AGENT_VERDICT
            await emit(on_event, event, round=index, verdict=verdict.to_dict())
            return verdict

        verdicts = await asyncio.gather(*(run(agent) for agent in self.agents))

        # L'ordre de `gather` suit celui des agents, pas celui des réponses :
        # l'affichage reste stable d'un tour à l'autre.
        debate_round = DebateRound(
            index=index,
            verdicts=list(verdicts),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        await emit(on_event, EventType.ROUND_COMPLETED, round=index,
                   unanimous=debate_round.is_unanimous,
                   tally={v.value: c for v, c in tally_votes(debate_round.verdicts).items()},
                   duration_ms=debate_round.duration_ms)
        return debate_round

    async def _run_debate(self, query: str, rounds: list[DebateRound],
                          on_event: EventSink | None) -> None:
        """Enchaîne les tours de débat jusqu'à accord, stabilité ou épuisement."""
        for index in range(1, self.config.max_debate_rounds + 1):
            previous = rounds[-1]
            by_agent = {v.agent: v for v in previous.verdicts}

            def call(agent: MagiAgent, _by_agent=by_agent, _index=index):
                peers = [v for name, v in _by_agent.items() if name != agent.name]
                return agent.rebut(query, _by_agent[agent.name], peers, _index)

            current = await self._run_round(index, on_event, call)
            rounds.append(current)

            if current.is_unanimous and self.config.stop_on_unanimity:
                await emit(on_event, EventType.CONVERGED, round=index,
                           reason="unanimité atteinte", vote=current.votes[0].value)
                return

            # Si personne n'a bougé, un tour de plus produira le même résultat
            # pour un coût d'API identique : on arrête le débat ici.
            if self.config.stop_on_convergence and current.vote_map() == previous.vote_map():
                await emit(on_event, EventType.CONVERGED, round=index,
                           reason="positions stabilisées, aucun vote modifié")
                return

    async def _synthesize(self, query: str, status: SystemStatus,
                          rounds: list[DebateRound]) -> dict:
        """Fait rédiger la décision finale par l'orchestrateur."""
        final = rounds[-1].verdicts
        tally = tally_votes(final)
        tally_label = ", ".join(f"{vote.value}={count}" for vote, count in tally.items())

        cfg = self.config.orchestrator
        request = CompletionRequest(
            model=cfg.model,
            system=cfg.system_prompt,
            user=synthesis_prompt(
                query=query,
                status_label=status.value,
                tally_label=tally_label,
                transcript=self._transcript(rounds),
                rounds_used=len(rounds),
            ),
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            timeout=cfg.timeout,
            agent=cfg.name,
            json_mode=cfg.json_mode,
            extra=dict(cfg.extra),
        )

        try:
            payload = extract_json(await self.backend.complete(request))
        except (LLMError, JSONExtractionError) as exc:
            log.error("orchestrateur indisponible (%s) : repli sur la synthèse locale", exc)
            return self._fallback_synthesis(status, final, str(exc))
        except Exception as exc:  # noqa: BLE001
            log.exception("orchestrateur : erreur inattendue")
            return self._fallback_synthesis(status, final, str(exc))

        answer = str(payload.get("final_answer", "")).strip()
        if not answer:
            return self._fallback_synthesis(status, final, "réponse finale vide")

        return {
            "final_answer": answer,
            "conditions": coerce_str_list(payload.get("conditions")),
            "dissent": str(payload.get("dissent", "")).strip(),
            "synthesis_reasoning": str(payload.get("synthesis_reasoning", "")).strip(),
            "degraded": False,
        }

    @staticmethod
    def _transcript(rounds: list[DebateRound]) -> str:
        """Met la délibération à plat pour l'orchestrateur."""
        blocks: list[str] = []
        for debate_round in rounds:
            label = "TOUR 1 — ANALYSE INDÉPENDANTE" if debate_round.index == 0 \
                else f"TOUR {debate_round.index + 1} — DÉBAT CONTRADICTOIRE"
            blocks.append(f"### {label}")
            for verdict in debate_round.verdicts:
                blocks.append(
                    f"{verdict.agent} ({verdict.model}) — vote {verdict.vote.value}, "
                    f"confiance {verdict.confidence_score:.2f}"
                    + (" [INSTANCE INDISPONIBLE]" if verdict.degraded else "")
                )
                for argument in verdict.key_arguments:
                    blocks.append(f"  • {argument}")
                if verdict.detailed_analysis:
                    blocks.append(f"  Analyse : {verdict.detailed_analysis}")
                blocks.append("")
        return "\n".join(blocks).strip()

    @staticmethod
    def _fallback_synthesis(status: SystemStatus, verdicts: list[AgentVerdict],
                            reason: str) -> dict:
        """Synthèse construite en Python quand l'orchestrateur est injoignable.

        Le débat a bien eu lieu et ses conclusions sont exploitables : on les
        restitue brutes plutôt que de perdre toute la délibération. La réponse
        est explicitement marquée comme dégradée.
        """
        supporters = [v for v in verdicts if not v.degraded]
        arguments: list[str] = []
        for verdict in sorted(supporters, key=lambda v: v.confidence_score, reverse=True):
            for argument in verdict.key_arguments[:2]:
                arguments.append(f"{verdict.agent} : {argument}")

        headline = {
            SystemStatus.UNANIMOUS_APPROVAL: "Le conseil approuve à l'unanimité.",
            SystemStatus.MAJORITY_APPROVAL: "Le conseil approuve à la majorité.",
            SystemStatus.CONDITIONAL_APPROVAL: "Le conseil approuve sous conditions.",
            SystemStatus.REJECTED: "Le conseil rejette la proposition.",
        }[status]

        body = "\n".join(f"- {a}" for a in arguments) or "- Aucun argument exploitable collecté."
        conditions = [
            v.key_arguments[0]
            for v in supporters
            if v.vote in (Vote.CONDITIONAL, Vote.REJECTED) and v.key_arguments
        ]

        return {
            "final_answer": (
                f"{headline}\n\n"
                f"⚠ Synthèse dégradée : l'orchestrateur n'a pas pu être interrogé ({reason}). "
                "Les arguments ci-dessous proviennent directement des agents, sans arbitrage "
                "éditorial.\n\n" + body
            ),
            "conditions": conditions,
            "dissent": ", ".join(
                f"{v.agent} ({v.vote.value})" for v in supporters if v.vote is not Vote.APPROVED
            ),
            "synthesis_reasoning": f"Synthèse locale de repli. Cause : {reason}",
            "degraded": True,
        }
