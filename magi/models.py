"""Structures de données du système MAGI.

Ce module ne dépend d'aucun fournisseur de LLM : il décrit uniquement le
vocabulaire de la délibération (votes, verdicts, tours de débat, décision
finale) et les règles déterministes qui transforment un ensemble de votes en
statut système.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable

# Noms canoniques des trois agents du triumvirat.
MELCHIOR = "MELCHIOR-1"
BALTHASAR = "BALTHASAR-2"
CASPER = "CASPER-3"
ORCHESTRATOR = "MAGI-ORCHESTRATOR"

AGENT_ORDER = (MELCHIOR, BALTHASAR, CASPER)


class Vote(str, Enum):
    """Vote individuel émis par un agent MAGI."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONDITIONAL = "CONDITIONAL"

    @classmethod
    def coerce(cls, raw: Any) -> "Vote":
        """Convertit une valeur brute de LLM en vote valide.

        Les modèles renvoient régulièrement des variantes ("approve",
        "APPROVED.", "conditionnel"). Toute valeur non reconnue retombe sur
        CONDITIONAL, qui est le vote le plus neutre : il n'accorde ni ne
        refuse, et force donc la poursuite du débat.
        """
        if isinstance(raw, cls):
            return raw
        text = str(raw or "").strip().upper()
        text = "".join(ch for ch in text if ch.isalpha())
        if text.startswith("APPROV") or text in {"YES", "OUI", "ACCEPT", "ACCEPTE"}:
            return cls.APPROVED
        if text.startswith("REJECT") or text.startswith("REFUS") or text in {"NO", "NON", "DENY", "DENIED"}:
            return cls.REJECTED
        return cls.CONDITIONAL


class SystemStatus(str, Enum):
    """Statut global émis par l'orchestrateur à l'issue de la délibération."""

    UNANIMOUS_APPROVAL = "UNANIMOUS APPROVAL"
    MAJORITY_APPROVAL = "MAJORITY APPROVAL"
    CONDITIONAL_APPROVAL = "CONDITIONAL APPROVAL"
    REJECTED = "REJECTED"

    @property
    def is_approval(self) -> bool:
        return self is not SystemStatus.REJECTED


@dataclass
class AgentVerdict:
    """Analyse structurée produite par un agent pour un tour donné."""

    agent: str
    vote: Vote
    confidence_score: float
    key_arguments: list[str] = field(default_factory=list)
    detailed_analysis: str = ""
    round_index: int = 0
    model: str = ""
    latency_ms: int = 0
    # True lorsque le verdict est un repli local (appel LLM en échec) et non
    # une véritable analyse du modèle.
    degraded: bool = False
    error: str | None = None

    def __post_init__(self) -> None:
        self.vote = Vote.coerce(self.vote)
        try:
            score = float(self.confidence_score)
        except (TypeError, ValueError):
            score = 0.0
        self.confidence_score = min(1.0, max(0.0, score))
        self.key_arguments = [str(a).strip() for a in (self.key_arguments or []) if str(a).strip()]
        self.detailed_analysis = str(self.detailed_analysis or "").strip()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["vote"] = self.vote.value
        return data

    def summary(self, max_args: int = 3) -> str:
        """Rendu compact réinjecté aux pairs pendant le débat."""
        lines = [
            f"[{self.agent}] vote={self.vote.value} confiance={self.confidence_score:.2f}",
        ]
        for argument in self.key_arguments[:max_args]:
            lines.append(f"  - {argument}")
        if self.detailed_analysis:
            lines.append(f"  Analyse : {self.detailed_analysis}")
        return "\n".join(lines)


@dataclass
class DebateRound:
    """Un tour de délibération : les trois verdicts émis simultanément."""

    index: int
    verdicts: list[AgentVerdict] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    duration_ms: int = 0

    @property
    def votes(self) -> list[Vote]:
        return [v.vote for v in self.verdicts]

    @property
    def is_unanimous(self) -> bool:
        votes = self.votes
        return bool(votes) and len(set(votes)) == 1

    def vote_map(self) -> dict[str, Vote]:
        return {v.agent: v.vote for v in self.verdicts}

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "duration_ms": self.duration_ms,
            "unanimous": self.is_unanimous,
            "verdicts": [v.to_dict() for v in self.verdicts],
        }


@dataclass
class MagiDecision:
    """Résultat complet d'une délibération MAGI."""

    query: str
    status: SystemStatus
    final_answer: str
    rounds: list[DebateRound] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    dissent: str = ""
    synthesis_reasoning: str = ""
    consensus_confidence: float = 0.0
    total_duration_ms: int = 0
    degraded: bool = False

    @property
    def final_verdicts(self) -> list[AgentVerdict]:
        return self.rounds[-1].verdicts if self.rounds else []

    @property
    def rounds_used(self) -> int:
        return len(self.rounds)

    def tally(self) -> dict[Vote, int]:
        return tally_votes(self.final_verdicts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "status": self.status.value,
            "final_answer": self.final_answer,
            "conditions": self.conditions,
            "dissent": self.dissent,
            "synthesis_reasoning": self.synthesis_reasoning,
            "consensus_confidence": round(self.consensus_confidence, 4),
            "total_duration_ms": self.total_duration_ms,
            "degraded": self.degraded,
            "rounds_used": self.rounds_used,
            "tally": {vote.value: count for vote, count in self.tally().items()},
            "rounds": [r.to_dict() for r in self.rounds],
        }


def tally_votes(verdicts: Iterable[AgentVerdict]) -> dict[Vote, int]:
    """Compte les votes par catégorie, en garantissant les trois clés."""
    counts = {Vote.APPROVED: 0, Vote.CONDITIONAL: 0, Vote.REJECTED: 0}
    for verdict in verdicts:
        counts[verdict.vote] = counts.get(verdict.vote, 0) + 1
    return counts


def resolve_status(verdicts: Iterable[AgentVerdict]) -> SystemStatus:
    """Applique les règles de vote du système MAGI.

    Le statut est calculé en Python, jamais délégué au LLM de synthèse : un
    modèle qui hallucine « UNANIMOUS APPROVAL » sur deux refus rendrait tout le
    dispositif de délibération décoratif.

    Règles, dans l'ordre :
      1. trois APPROVED               -> UNANIMOUS APPROVAL
      2. deux REJECTED ou plus        -> REJECTED (minorité de blocage)
      3. majorité absolue d'APPROVED  -> MAJORITY APPROVAL
      4. majorité non bloquante       -> CONDITIONAL APPROVAL
      5. tout le reste                -> REJECTED
    """
    verdicts = list(verdicts)
    if not verdicts:
        return SystemStatus.REJECTED

    counts = tally_votes(verdicts)
    total = len(verdicts)
    approved = counts[Vote.APPROVED]
    rejected = counts[Vote.REJECTED]
    conditional = counts[Vote.CONDITIONAL]

    if approved == total:
        return SystemStatus.UNANIMOUS_APPROVAL
    if rejected >= 2:
        return SystemStatus.REJECTED
    if approved > total / 2:
        return SystemStatus.MAJORITY_APPROVAL
    if approved + conditional > total / 2:
        return SystemStatus.CONDITIONAL_APPROVAL
    return SystemStatus.REJECTED


def consensus_confidence(verdicts: Iterable[AgentVerdict], status: SystemStatus) -> float:
    """Confiance agrégée du système, entre 0 et 1.

    On moyenne la confiance des agents alignés sur l'issue retenue, puis on
    pénalise proportionnellement au poids de la dissidence. Un verdict dégradé
    (échec d'appel LLM) ne compte pas comme un soutien.
    """
    verdicts = [v for v in verdicts if not v.degraded]
    if not verdicts:
        return 0.0

    if status is SystemStatus.REJECTED:
        aligned = [v for v in verdicts if v.vote is Vote.REJECTED]
    elif status is SystemStatus.CONDITIONAL_APPROVAL:
        aligned = [v for v in verdicts if v.vote in (Vote.APPROVED, Vote.CONDITIONAL)]
    else:
        aligned = [v for v in verdicts if v.vote is Vote.APPROVED]

    if not aligned:
        return 0.0

    base = sum(v.confidence_score for v in aligned) / len(aligned)
    dissent_ratio = 1 - (len(aligned) / len(verdicts))
    return round(max(0.0, base * (1 - 0.5 * dissent_ratio)), 4)
