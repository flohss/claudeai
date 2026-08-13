from neura_set.config import DecisionConfig
from neura_set.decision.agent import DecisionAgent
from neura_set.types import MusicalContext, NoteEvent, Proposal, SectionLabel


def make_proposal(pid: str, section: SectionLabel = SectionLabel.VERSE, pitch: int = 60) -> Proposal:
    context = MusicalContext(section=section, rms_energy=0.5)
    notes = [NoteEvent(pitch=pitch, start_beat=i * 0.5, duration_beats=0.5) for i in range(4)]
    return Proposal(id=pid, notes=notes, context=context, generator_name="test")


def test_should_propose_respects_cooldown():
    config = DecisionConfig(min_seconds_between_proposals=10.0)
    agent = DecisionAgent(config)
    context = MusicalContext(section=SectionLabel.VERSE, rms_energy=0.5)
    now = 1000.0

    assert agent.should_propose(context, now=now) is True
    agent.register_proposal(make_proposal("p1", context.section), now=now)
    assert agent.should_propose(context, now=now + 5) is False
    assert agent.should_propose(context, now=now + 11) is True


def test_should_propose_avoids_busy_sections():
    agent = DecisionAgent()
    context = MusicalContext(section=SectionLabel.DROP, rms_energy=0.5)
    assert agent.should_propose(context, now=100.0) is False


def test_should_propose_blocks_on_silence():
    agent = DecisionAgent()
    silent_context = MusicalContext(section=SectionLabel.VERSE, rms_energy=0.0)
    assert agent.should_propose(silent_context, now=100.0) is False

    playing_context = MusicalContext(section=SectionLabel.VERSE, rms_energy=0.5)
    assert agent.should_propose(playing_context, now=100.0) is True


def test_filter_candidate_rejects_near_duplicate():
    config = DecisionConfig(novelty_similarity_threshold=0.9)
    agent = DecisionAgent(config)

    p1 = make_proposal("p1", pitch=60)
    agent.register_proposal(p1, now=0.0)
    agent.record_feedback("p1", accepted=True)

    p2 = make_proposal("p2", pitch=60)  # identical pitches to the accepted one
    assert agent.filter_candidate(p2) is False

    p3 = make_proposal("p3", pitch=72)  # clearly different
    assert agent.filter_candidate(p3) is True


def test_agent_backs_off_after_repeated_rejections():
    config = DecisionConfig(min_seconds_between_proposals=0.0)
    agent = DecisionAgent(config)
    context = MusicalContext(section=SectionLabel.VERSE, rms_energy=0.5)

    for i in range(4):
        p = make_proposal(f"p{i}", context.section)
        agent.register_proposal(p, now=float(i))
        agent.record_feedback(f"p{i}", accepted=False)

    assert agent.should_propose(context, now=100.0) is False
