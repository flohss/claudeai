"""Rule-based decision agent.

Decides WHEN to propose (cooldown, structure-awareness, don't overstay a
welcome the human keeps rejecting) and WHAT to actually send (novelty
filtering against recently accepted proposals, so NEURA-SET doesn't keep
re-suggesting the same line). This is the default; `rl_agent.py` sketches
a reinforcement-learning upgrade path once enough accept/reject feedback
has been collected to train on.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from neura_set.config import DecisionConfig, DEFAULT_CONFIG
from neura_set.types import MusicalContext, NoteEvent, Proposal, SectionLabel


def pitch_sequence_similarity(a: list[NoteEvent], b: list[NoteEvent]) -> float:
    """Fraction of aligned positions with matching pitch, normalized by
    the longer sequence's length. Simple, deterministic, real."""
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    matches = sum(1 for i in range(n) if a[i].pitch == b[i].pitch)
    return matches / max(len(a), len(b))


@dataclass
class FeedbackStats:
    accepted: int = 0
    rejected: int = 0

    @property
    def acceptance_rate(self) -> float:
        total = self.accepted + self.rejected
        return self.accepted / total if total else 0.5


class DecisionAgent:
    """Gatekeeper between the generation layer and the action layer."""

    # Sections where the human is actively driving dense material — a
    # co-producer earns its keep in the sparse sections instead.
    BUSY_SECTIONS = {SectionLabel.DROP, SectionLabel.CHORUS}

    def __init__(self, config: DecisionConfig = DEFAULT_CONFIG.decision) -> None:
        self.config = config
        self._last_proposal_time: float = 0.0
        self._pending: list[Proposal] = []
        self._recent_accepted: list[Proposal] = []
        self._stats_by_section: dict[SectionLabel, FeedbackStats] = {}

    def should_propose(self, context: MusicalContext, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        if context.rms_energy < self.config.min_rms_energy:
            return False  # silence / no input signal — nothing to react to yet
        if now - self._last_proposal_time < self.config.min_seconds_between_proposals:
            return False
        if len(self._pending) >= self.config.max_pending_proposals:
            return False
        if context.section in self.BUSY_SECTIONS:
            return False
        stats = self._stats_by_section.get(context.section)
        if stats and (stats.accepted + stats.rejected) >= 4 and stats.acceptance_rate < 0.15:
            return False  # keeps getting rejected here — back off
        return True

    def filter_candidate(self, candidate: Proposal) -> bool:
        """True if `candidate` is novel enough relative to recently
        accepted proposals to be worth sending."""
        for prior in self._recent_accepted[-10:]:
            if pitch_sequence_similarity(candidate.notes, prior.notes) >= self.config.novelty_similarity_threshold:
                return False
        return True

    def register_proposal(self, proposal: Proposal, now: float | None = None) -> None:
        self._last_proposal_time = now if now is not None else time.time()
        self._pending.append(proposal)

    def record_feedback(self, proposal_id: str, accepted: bool) -> None:
        proposal = next((p for p in self._pending if p.id == proposal_id), None)
        if proposal is None:
            return
        self._pending.remove(proposal)
        stats = self._stats_by_section.setdefault(proposal.context.section, FeedbackStats())
        if accepted:
            stats.accepted += 1
            self._recent_accepted.append(proposal)
        else:
            stats.rejected += 1

    @property
    def pending_count(self) -> int:
        return len(self._pending)
