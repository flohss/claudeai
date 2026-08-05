"""Règles de vote et agrégation — la partie du système qui ne doit jamais
dépendre du bon vouloir d'un LLM."""

from __future__ import annotations

import pytest

from magi.models import (
    BALTHASAR,
    CASPER,
    MELCHIOR,
    AgentVerdict,
    DebateRound,
    SystemStatus,
    Vote,
    consensus_confidence,
    resolve_status,
    tally_votes,
)


def verdict(agent: str, vote: Vote, confidence: float = 0.8, **kwargs) -> AgentVerdict:
    return AgentVerdict(agent=agent, vote=vote, confidence_score=confidence, **kwargs)


def council(*votes: Vote) -> list[AgentVerdict]:
    return [verdict(name, vote) for name, vote in zip((MELCHIOR, BALTHASAR, CASPER), votes)]


class TestVoteCoercion:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("APPROVED", Vote.APPROVED),
            ("approved", Vote.APPROVED),
            ("  Approve.  ", Vote.APPROVED),
            ("OUI", Vote.APPROVED),
            ("REJECTED", Vote.REJECTED),
            ("reject", Vote.REJECTED),
            ("Refusé", Vote.REJECTED),
            ("DENIED", Vote.REJECTED),
            ("CONDITIONAL", Vote.CONDITIONAL),
            ("conditionnel", Vote.CONDITIONAL),
        ],
    )
    def test_recognised_variants(self, raw, expected):
        assert Vote.coerce(raw) is expected

    @pytest.mark.parametrize("raw", [None, "", "peut-être", 42, {"vote": "x"}])
    def test_unknown_falls_back_to_conditional(self, raw):
        # CONDITIONAL est le repli neutre : il ne peut ni créer une unanimité
        # ni provoquer un rejet.
        assert Vote.coerce(raw) is Vote.CONDITIONAL

    def test_idempotent(self):
        assert Vote.coerce(Vote.REJECTED) is Vote.REJECTED


class TestVerdictNormalisation:
    def test_confidence_is_clamped(self):
        assert verdict(MELCHIOR, Vote.APPROVED, 1.7).confidence_score == 1.0
        assert verdict(MELCHIOR, Vote.APPROVED, -3).confidence_score == 0.0

    def test_non_numeric_confidence_becomes_zero(self):
        assert AgentVerdict(MELCHIOR, Vote.APPROVED, "élevée").confidence_score == 0.0

    def test_blank_arguments_are_dropped(self):
        v = AgentVerdict(MELCHIOR, Vote.APPROVED, 0.5, key_arguments=["  ", "réel", ""])
        assert v.key_arguments == ["réel"]

    def test_summary_contains_vote_and_arguments(self):
        v = verdict(CASPER, Vote.REJECTED, 0.61, key_arguments=["postulat non vérifié"])
        text = v.summary()
        assert "CASPER-3" in text and "REJECTED" in text
        assert "0.61" in text and "postulat non vérifié" in text


class TestResolveStatus:
    def test_three_approvals_is_unanimous(self):
        assert resolve_status(council(Vote.APPROVED, Vote.APPROVED, Vote.APPROVED)) \
            is SystemStatus.UNANIMOUS_APPROVAL

    def test_two_approvals_is_majority(self):
        assert resolve_status(council(Vote.APPROVED, Vote.APPROVED, Vote.CONDITIONAL)) \
            is SystemStatus.MAJORITY_APPROVAL

    def test_two_rejections_block_even_with_one_approval(self):
        # La minorité de blocage prime sur le décompte des approbations.
        assert resolve_status(council(Vote.APPROVED, Vote.REJECTED, Vote.REJECTED)) \
            is SystemStatus.REJECTED

    def test_single_rejection_does_not_block_a_majority(self):
        assert resolve_status(council(Vote.APPROVED, Vote.APPROVED, Vote.REJECTED)) \
            is SystemStatus.MAJORITY_APPROVAL

    def test_conditional_majority(self):
        assert resolve_status(council(Vote.CONDITIONAL, Vote.CONDITIONAL, Vote.REJECTED)) \
            is SystemStatus.CONDITIONAL_APPROVAL

    def test_one_of_each_is_conditional(self):
        assert resolve_status(council(Vote.APPROVED, Vote.CONDITIONAL, Vote.REJECTED)) \
            is SystemStatus.CONDITIONAL_APPROVAL

    def test_three_rejections(self):
        assert resolve_status(council(Vote.REJECTED, Vote.REJECTED, Vote.REJECTED)) \
            is SystemStatus.REJECTED

    def test_empty_council_rejects(self):
        assert resolve_status([]) is SystemStatus.REJECTED

    def test_unanimity_requires_all_three_approvals(self):
        # Deux APPROVED et un CONDITIONAL ne doivent jamais produire l'unanimité.
        status = resolve_status(council(Vote.APPROVED, Vote.APPROVED, Vote.CONDITIONAL))
        assert status is not SystemStatus.UNANIMOUS_APPROVAL

    def test_degraded_verdict_cannot_fabricate_unanimity(self):
        verdicts = [
            verdict(MELCHIOR, Vote.APPROVED),
            verdict(BALTHASAR, Vote.APPROVED),
            verdict(CASPER, Vote.CONDITIONAL, 0.0, degraded=True),
        ]
        assert resolve_status(verdicts) is SystemStatus.MAJORITY_APPROVAL

    def test_two_degraded_verdicts_cannot_force_a_rejection(self):
        verdicts = [
            verdict(MELCHIOR, Vote.APPROVED),
            verdict(BALTHASAR, Vote.CONDITIONAL, 0.0, degraded=True),
            verdict(CASPER, Vote.CONDITIONAL, 0.0, degraded=True),
        ]
        assert resolve_status(verdicts) is SystemStatus.CONDITIONAL_APPROVAL


class TestTally:
    def test_all_categories_present(self):
        counts = tally_votes(council(Vote.APPROVED, Vote.APPROVED, Vote.APPROVED))
        assert counts == {Vote.APPROVED: 3, Vote.CONDITIONAL: 0, Vote.REJECTED: 0}


class TestConsensusConfidence:
    def test_unanimous_confidence_is_the_mean(self):
        verdicts = [
            verdict(MELCHIOR, Vote.APPROVED, 0.9),
            verdict(BALTHASAR, Vote.APPROVED, 0.8),
            verdict(CASPER, Vote.APPROVED, 0.7),
        ]
        assert consensus_confidence(verdicts, SystemStatus.UNANIMOUS_APPROVAL) == pytest.approx(0.8)

    def test_dissent_lowers_confidence(self):
        verdicts = [
            verdict(MELCHIOR, Vote.APPROVED, 0.9),
            verdict(BALTHASAR, Vote.APPROVED, 0.9),
            verdict(CASPER, Vote.REJECTED, 0.9),
        ]
        score = consensus_confidence(verdicts, SystemStatus.MAJORITY_APPROVAL)
        assert score < 0.9
        assert score == pytest.approx(0.9 * (1 - 0.5 * (1 / 3)), abs=1e-3)

    def test_degraded_agents_are_excluded(self):
        verdicts = [
            verdict(MELCHIOR, Vote.APPROVED, 0.9),
            verdict(BALTHASAR, Vote.APPROVED, 0.9),
            verdict(CASPER, Vote.CONDITIONAL, 0.0, degraded=True),
        ]
        # Le verdict dégradé ne doit pas être compté comme une dissidence.
        assert consensus_confidence(verdicts, SystemStatus.MAJORITY_APPROVAL) == pytest.approx(0.9)

    def test_no_usable_verdict_gives_zero(self):
        verdicts = [verdict(MELCHIOR, Vote.CONDITIONAL, 0.0, degraded=True)]
        assert consensus_confidence(verdicts, SystemStatus.REJECTED) == 0.0


class TestDebateRound:
    def test_unanimity_detection(self):
        assert DebateRound(0, council(Vote.APPROVED, Vote.APPROVED, Vote.APPROVED)).is_unanimous
        assert not DebateRound(0, council(Vote.APPROVED, Vote.APPROVED, Vote.REJECTED)).is_unanimous

    def test_empty_round_is_not_unanimous(self):
        assert not DebateRound(0, []).is_unanimous

    def test_vote_map_is_keyed_by_agent(self):
        round_ = DebateRound(0, council(Vote.APPROVED, Vote.REJECTED, Vote.CONDITIONAL))
        assert round_.vote_map() == {
            MELCHIOR: Vote.APPROVED,
            BALTHASAR: Vote.REJECTED,
            CASPER: Vote.CONDITIONAL,
        }
