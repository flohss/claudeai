"""Agent MAGI : un modèle, une doctrine, un vote.

L'agent encapsule le cycle complet d'une prise de parole : construction du
message, appel au backend, extraction du JSON, réparation en cas de sortie
malformée, et repli neutre si le modèle reste injoignable.
"""

from __future__ import annotations

import logging
import time

from .backends import CompletionRequest, LLMBackend, LLMError
from .config import AgentConfig
from .models import AgentVerdict, Vote
from .parsing import JSONExtractionError, coerce_str_list, extract_json
from .prompts import debate_prompt, initial_analysis_prompt

log = logging.getLogger("magi.agent")

# Consigne de réparation envoyée quand la première réponse n'est pas du JSON.
_REPAIR_INSTRUCTION = """Ta réponse précédente n'était pas un objet JSON exploitable.

Réponse rejetée :
---
{bad_output}
---

Reformule EXACTEMENT la même analyse sous forme d'un unique objet JSON valide,
sans texte autour, sans balise Markdown, conforme au schéma de ta directive.
Ne commence pas par une phrase d'introduction. Le premier caractère de ta
réponse doit être {{ et le dernier }}."""


class MagiAgent:
    """Une instance du triumvirat."""

    def __init__(self, config: AgentConfig, backend: LLMBackend) -> None:
        self.config = config
        self.backend = backend

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def model(self) -> str:
        return self.config.model

    async def analyze(self, query: str, context: str = "", round_index: int = 0) -> AgentVerdict:
        """Tour 1 : analyse indépendante, sans connaissance des pairs."""
        return await self._deliberate(initial_analysis_prompt(query, context), round_index)

    async def rebut(
        self,
        query: str,
        own_previous: AgentVerdict,
        peers: list[AgentVerdict],
        round_index: int,
    ) -> AgentVerdict:
        """Tour n : réévaluation à la lumière des positions adverses."""
        prompt = debate_prompt(
            query=query,
            own_previous=own_previous.summary(),
            peer_summaries=[p.summary() for p in peers],
            round_index=round_index,
        )
        return await self._deliberate(prompt, round_index)

    # -- interne ------------------------------------------------------------

    async def _deliberate(self, user_prompt: str, round_index: int) -> AgentVerdict:
        started = time.perf_counter()
        request = CompletionRequest(
            model=self.config.model,
            system=self.config.system_prompt,
            user=user_prompt,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout=self.config.timeout,
            agent=self.name,
            round_index=round_index,
            json_mode=self.config.json_mode,
            extra=dict(self.config.extra),
        )

        try:
            raw = await self.backend.complete(request)
        except LLMError as exc:
            return self._degraded(f"appel au modèle en échec : {exc}", round_index, started)
        except Exception as exc:  # noqa: BLE001 - un agent isolé ne fait pas tomber le conseil
            log.exception("%s : erreur inattendue", self.name)
            return self._degraded(f"erreur inattendue : {exc}", round_index, started)

        try:
            payload = extract_json(raw)
        except JSONExtractionError as first_error:
            log.warning("%s : sortie non-JSON, tentative de réparation", self.name)
            try:
                repaired = await self.backend.complete(
                    CompletionRequest(
                        **{
                            **request.__dict__,
                            "user": _REPAIR_INSTRUCTION.format(bad_output=raw[:1500]),
                            "temperature": 0.0,
                        }
                    )
                )
                payload = extract_json(repaired)
            except Exception as exc:  # noqa: BLE001 - dernier filet avant repli
                return self._degraded(
                    f"sortie illisible après réparation : {first_error} / {exc}", round_index, started
                )

        return self._verdict_from_payload(payload, round_index, started)

    def _verdict_from_payload(self, payload: dict, round_index: int, started: float) -> AgentVerdict:
        # Le nom d'agent renvoyé par le modèle n'est jamais retenu : seule
        # compte l'identité déclarée dans la configuration.
        return AgentVerdict(
            agent=self.name,
            vote=Vote.coerce(payload.get("vote")),
            confidence_score=payload.get("confidence_score", 0.5),
            key_arguments=coerce_str_list(payload.get("key_arguments")),
            detailed_analysis=str(payload.get("detailed_analysis", "")),
            round_index=round_index,
            model=self.config.model,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def _degraded(self, reason: str, round_index: int, started: float) -> AgentVerdict:
        """Verdict de repli lorsqu'un agent n'a pas pu se prononcer.

        Le vote retenu est CONDITIONAL : c'est le seul qui n'altère pas
        mécaniquement l'issue. Il ne peut ni fabriquer une unanimité (qui exige
        trois APPROVED) ni provoquer un rejet (qui exige deux REJECTED). Le
        drapeau `degraded` exclut par ailleurs ce verdict du calcul de
        confiance et le signale dans toutes les interfaces.
        """
        log.error("%s indisponible : %s", self.name, reason)
        return AgentVerdict(
            agent=self.name,
            vote=Vote.CONDITIONAL,
            confidence_score=0.0,
            key_arguments=[f"{self.name} n'a pas pu rendre d'analyse."],
            detailed_analysis=(
                f"Instance indisponible pendant ce tour. Motif : {reason}. "
                "Le vote est neutralisé et ne doit pas être interprété comme une position."
            ),
            round_index=round_index,
            model=self.config.model,
            latency_ms=int((time.perf_counter() - started) * 1000),
            degraded=True,
            error=reason,
        )
