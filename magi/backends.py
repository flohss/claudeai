"""Abstraction des fournisseurs de LLM.

Le noyau MAGI ne connaît qu'une interface : `LLMBackend.complete()`. Deux
implémentations sont fournies :

- `LiteLLMBackend` : passe par LiteLLM, ce qui permet d'affecter un modèle
  différent à chaque agent (Anthropic, OpenAI, Google, Mistral, Ollama…) avec
  la même signature d'appel.
- `SimulatedBackend` : n'appelle aucune API. Il fabrique des verdicts
  déterministes à partir d'un hachage de la requête. Il sert aux tests, aux
  démonstrations hors ligne et au développement de l'interface — le texte
  produit est du remplissage, pas du raisonnement.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from .models import BALTHASAR, CASPER, MELCHIOR, ORCHESTRATOR

log = logging.getLogger("magi.backend")


class LLMError(RuntimeError):
    """Échec d'appel au fournisseur, après épuisement des tentatives."""


@dataclass
class CompletionRequest:
    """Tout ce dont un backend a besoin pour produire une réponse."""

    model: str
    system: str
    user: str
    temperature: float = 0.5
    max_tokens: int = 1400
    timeout: float = 90.0
    agent: str = ""
    round_index: int = 0
    json_mode: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


class LLMBackend(Protocol):
    """Contrat minimal attendu par le noyau."""

    name: str

    async def complete(self, request: CompletionRequest) -> str:
        """Retourne le texte brut produit par le modèle."""
        ...


# --------------------------------------------------------------------------
# Backend réel
# --------------------------------------------------------------------------


class LiteLLMBackend:
    """Appelle n'importe quel fournisseur supporté par LiteLLM.

    Les erreurs transitoires (429, 5xx, coupures réseau) sont réessayées avec
    un backoff exponentiel ; les erreurs de configuration (clé absente, modèle
    inconnu) échouent immédiatement, car réessayer ne les corrigera pas.
    """

    name = "litellm"

    _RETRYABLE = ("rate limit", "429", "timeout", "timed out", "overloaded",
                  "503", "502", "500", "connection", "temporarily")
    _FATAL = ("api key", "authentication", "not found", "does not exist",
              "invalid model", "permission", "unsupported")

    def __init__(self, max_retries: int = 3, base_delay: float = 1.5) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._drop_json_mode: set[str] = set()

    async def complete(self, request: CompletionRequest) -> str:
        import litellm  # import différé : le backend simulé ne doit rien exiger

        litellm.drop_params = True  # ignore silencieusement les params non supportés

        messages = [
            {"role": "system", "content": request.system},
            {"role": "user", "content": request.user},
        ]

        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "timeout": request.timeout,
            **request.extra,
        }
        if request.json_mode and request.model not in self._drop_json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = await litellm.acompletion(**kwargs)
                return self._extract_text(response)
            except Exception as exc:  # noqa: BLE001 - LiteLLM remonte des types variés
                last_error = exc
                message = str(exc).lower()

                # Le modèle refuse le mode JSON natif : on le retire et on
                # retombe sur le parseur tolérant, sans consommer de tentative.
                if "response_format" in message and "response_format" in kwargs:
                    self._drop_json_mode.add(request.model)
                    kwargs.pop("response_format")
                    log.warning("%s : mode JSON natif désactivé pour %s", request.agent, request.model)
                    continue

                if any(token in message for token in self._FATAL):
                    raise LLMError(f"{request.model} : {exc}") from exc

                if attempt == self.max_retries - 1 or not any(t in message for t in self._RETRYABLE):
                    break

                delay = self.base_delay * (2**attempt)
                log.warning("%s : tentative %d/%d échouée (%s), nouvel essai dans %.1fs",
                            request.agent, attempt + 1, self.max_retries, exc, delay)
                await asyncio.sleep(delay)

        raise LLMError(f"{request.model} : {last_error}") from last_error

    @staticmethod
    def _extract_text(response: Any) -> str:
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, KeyError) as exc:
            raise LLMError(f"réponse illisible du fournisseur : {response!r}") from exc
        if isinstance(content, list):  # certains fournisseurs renvoient des blocs
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not content or not str(content).strip():
            raise LLMError("réponse vide du fournisseur")
        return str(content)


# --------------------------------------------------------------------------
# Backend simulé
# --------------------------------------------------------------------------

# Termes qui déplacent le curseur de risque perçu dans la simulation. Ils ne
# servent qu'à rendre la démonstration hors ligne crédible.
_RISK_TERMS = (
    "supprim", "delete", "drop", "prod", "production", "irréversible", "irreversible",
    "données personnelles", "personal data", "rgpd", "gdpr", "santé", "health",
    "enfant", "minor", "arme", "weapon", "surveillance", "biométri", "biometric",
    "licenci", "layoff", "mot de passe", "password", "credential", "sécurité", "security",
)
_EFFORT_TERMS = ("migrer", "migrate", "réécrire", "rewrite", "refonte", "urgent",
                 "vendredi", "friday", "deadline", "legacy", "monolith")

_AGENT_FLAVOUR = {
    MELCHIOR: {
        "lens": "viabilité technique",
        "args": [
            "Les prémisses techniques sont vérifiables et cohérentes avec l'état de l'art.",
            "Le coût d'implémentation reste dans un ordre de grandeur raisonnable.",
            "Une donnée chiffrée manque pour trancher : le volume réel à traiter.",
            "La chaîne causale invoquée n'est pas établie par les éléments fournis.",
        ],
        "analysis": (
            "Analyse factuelle et logique de la proposition. Les éléments vérifiables "
            "soutiennent {stance} ; l'incertitude résiduelle porte sur les paramètres "
            "non quantifiés de la requête."
        ),
    },
    BALTHASAR: {
        "lens": "protection humaine",
        "args": [
            "Aucun préjudice irréversible identifié pour les personnes concernées.",
            "Le bénéfice et le risque ne reposent pas sur les mêmes populations.",
            "Un mécanisme de retour arrière doit exister avant toute exécution.",
            "Le traitement de données sensibles impose une base légale explicite.",
        ],
        "analysis": (
            "Évaluation des conséquences humaines. Le scénario de préjudice le plus "
            "plausible reste {stance_soft}, sous réserve des garde-fous énoncés dans "
            "les arguments."
        ),
    },
    CASPER: {
        "lens": "faisabilité opérationnelle",
        "args": [
            "Le plan suppose une disponibilité des équipes qui n'est pas démontrée.",
            "L'effet de second ordre le plus probable est un contournement du processus.",
            "Un test peu coûteux départagerait les hypothèses avant tout engagement.",
            "Les deux autres MAGI raisonnent sur un périmètre plus étroit que le réel.",
        ],
        "analysis": (
            "Examen sceptique des postulats implicites. Rien n'invalide {stance} de "
            "façon décisive, mais l'exécution reste le maillon faible du dispositif."
        ),
    },
}

_PEER_VOTE_RE = re.compile(r"vote=(APPROVED|REJECTED|CONDITIONAL)")


class SimulatedBackend:
    """Génère des verdicts plausibles sans aucun appel réseau.

    Déterministe pour une requête donnée (hachage SHA-256), ce qui rend les
    tests reproductibles. À partir du deuxième tour, chaque agent dérive vers
    la position majoritaire de ses pairs avec une probabilité modérée : cela
    reproduit la convergence sans la garantir.
    """

    name = "simulated"

    def __init__(self, latency: float = 0.15) -> None:
        self.latency = latency

    async def complete(self, request: CompletionRequest) -> str:
        if self.latency:
            await asyncio.sleep(self.latency * random.uniform(0.6, 1.4))

        if request.agent == ORCHESTRATOR:
            return json.dumps(self._synthesis(request), ensure_ascii=False)
        return json.dumps(self._verdict(request), ensure_ascii=False)

    # -- verdicts d'agent ---------------------------------------------------

    def _verdict(self, request: CompletionRequest) -> dict[str, Any]:
        query = self._extract_query(request.user)
        rng = self._rng(request.agent, query, request.round_index)
        flavour = _AGENT_FLAVOUR.get(request.agent, _AGENT_FLAVOUR[MELCHIOR])

        risk = self._term_score(query, _RISK_TERMS)
        effort = self._term_score(query, _EFFORT_TERMS)
        vote = self._choose_vote(request, rng, risk, effort)

        stance = {"APPROVED": "l'approbation", "REJECTED": "le refus",
                  "CONDITIONAL": "une approbation sous conditions"}[vote]
        stance_soft = {"APPROVED": "faible et réversible", "REJECTED": "grave et mal maîtrisé",
                       "CONDITIONAL": "modéré mais atténuable"}[vote]

        args = list(flavour["args"])
        rng.shuffle(args)
        confidence = round(min(0.97, max(0.35, rng.gauss(0.74, 0.11))), 2)
        if request.round_index > 0:
            confidence = round(min(0.97, confidence + 0.05), 2)  # le débat affermit

        return {
            "agent": request.agent,
            "vote": vote,
            "confidence_score": confidence,
            "key_arguments": args[:3],
            "detailed_analysis": (
                f"[SIMULATION — aucun appel LLM] Angle : {flavour['lens']}. "
                + flavour["analysis"].format(stance=stance, stance_soft=stance_soft)
            ),
        }

    def _choose_vote(self, request: CompletionRequest, rng: random.Random,
                     risk: float, effort: float) -> str:
        # Biais de personnalité : Melchior juge la viabilité, Balthasar le
        # risque humain, Casper l'exécution.
        weights = {
            MELCHIOR: {"APPROVED": 0.55 - 0.2 * effort, "CONDITIONAL": 0.3, "REJECTED": 0.15 + 0.2 * effort},
            BALTHASAR: {"APPROVED": 0.4 - 0.3 * risk, "CONDITIONAL": 0.35 + 0.1 * risk, "REJECTED": 0.25 + 0.2 * risk},
            CASPER: {"APPROVED": 0.3, "CONDITIONAL": 0.45 + 0.1 * effort, "REJECTED": 0.25 + 0.1 * effort},
        }.get(request.agent, {"APPROVED": 0.4, "CONDITIONAL": 0.35, "REJECTED": 0.25})

        # Lors des tours de débat, deux forces s'opposent : l'inertie (un agent
        # ne renie pas sa position sans raison) et la pression du consensus.
        if request.round_index > 0:
            own_block = request.user.split("TA POSITION AU TOUR PRÉCÉDENT")[-1]
            own_block = own_block.split("POSITIONS DES AUTRES MAGI")[0]
            own = _PEER_VOTE_RE.findall(own_block)
            if own:
                weights[own[0]] = weights.get(own[0], 0.3) + 1.1

            peers = _PEER_VOTE_RE.findall(request.user.split("POSITIONS DES AUTRES MAGI")[-1])
            if peers:
                majority = max(set(peers), key=peers.count)
                if peers.count(majority) >= 2:
                    weights[majority] = weights.get(majority, 0.3) + 0.9

        total = sum(max(0.01, w) for w in weights.values())
        draw = rng.random() * total
        cumulative = 0.0
        for vote, weight in weights.items():
            cumulative += max(0.01, weight)
            if draw <= cumulative:
                return vote
        return "CONDITIONAL"

    # -- synthèse de l'orchestrateur ---------------------------------------

    def _synthesis(self, request: CompletionRequest) -> dict[str, Any]:
        status_match = re.search(r"STATUT SYSTÈME CALCULÉ PAR LE NOYAU : (.+)", request.user)
        status = status_match.group(1).strip() if status_match else "REJECTED"
        query = self._extract_query(request.user)
        votes = _PEER_VOTE_RE.findall(request.user)
        rejected = votes.count("REJECTED")

        if status == "UNANIMOUS APPROVAL":
            answer = (
                f"Le conseil MAGI approuve à l'unanimité. Les trois instances convergent : "
                f"MELCHIOR-1 valide la viabilité technique, BALTHASAR-2 ne relève aucun préjudice "
                f"irréversible, CASPER-3 n'identifie pas d'obstacle d'exécution bloquant. "
                f"La proposition peut être engagée en l'état."
            )
            conditions: list[str] = []
        elif status == "REJECTED":
            answer = (
                f"Le conseil MAGI rejette la proposition. {rejected} instance(s) sur 3 ont opposé "
                f"un refus que le débat contradictoire n'a pas levé. Les objections portent sur le "
                f"fond et non sur la forme : une reformulation ne suffirait pas."
            )
            conditions = ["Revoir la proposition sur les points contestés avant toute nouvelle soumission."]
        else:
            answer = (
                f"Le conseil MAGI accorde une approbation partielle. Une majorité soutient la "
                f"proposition, mais des réserves subsistent sur l'exécution et la maîtrise du risque. "
                f"L'engagement n'est recommandé que si les conditions ci-dessous sont remplies."
            )
            conditions = [
                "Définir un critère d'arrêt vérifiable avant le lancement.",
                "Prévoir un mécanisme de retour arrière testé.",
            ]

        return {
            "final_answer": f"[SIMULATION — aucun appel LLM] {answer}\n\nRequête traitée : « {query[:200]} »",
            "conditions": conditions,
            "dissent": "" if status == "UNANIMOUS APPROVAL" else
                       "La position minoritaire porte sur les effets de second ordre non mesurés.",
            "synthesis_reasoning": (
                "Synthèse simulée : le statut est repris du noyau, les arguments sont agrégés "
                "par pondération de confiance."
            ),
        }

    # -- utilitaires --------------------------------------------------------

    @staticmethod
    def _extract_query(user_prompt: str) -> str:
        parts = user_prompt.split("---")
        return parts[1].strip() if len(parts) > 1 else user_prompt.strip()

    @staticmethod
    def _term_score(text: str, terms: tuple[str, ...]) -> float:
        lowered = text.lower()
        hits = sum(1 for term in terms if term in lowered)
        return min(1.0, hits / 3)

    @staticmethod
    def _rng(agent: str, query: str, round_index: int) -> random.Random:
        seed = hashlib.sha256(f"{agent}|{query}|{round_index}".encode()).hexdigest()
        return random.Random(int(seed[:16], 16))


def build_backend(kind: str, **kwargs: Any) -> LLMBackend:
    """Fabrique un backend à partir de son nom ('litellm' ou 'simulated')."""
    kind = (kind or "litellm").strip().lower()
    if kind in {"simulated", "simulation", "mock", "offline", "demo"}:
        return SimulatedBackend(**{k: v for k, v in kwargs.items() if k == "latency"})
    if kind in {"litellm", "live", "real"}:
        return LiteLLMBackend(**{k: v for k, v in kwargs.items() if k in {"max_retries", "base_delay"}})
    raise ValueError(f"backend inconnu : {kind!r} (attendu : 'litellm' ou 'simulated')")
