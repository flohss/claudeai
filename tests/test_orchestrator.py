import asyncio

import pytest

from neura_set.orchestrator import _note_duration_from_context, Orchestrator
from neura_set.types import MusicalContext, SectionLabel


class _FlakyAnalyzer:
    """Raises on the first call, then behaves — simulates a librosa edge
    case on real (non-silent) audio, which is what killed the perception
    loop before it caught exceptions per-tick."""

    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, buffer):  # noqa: ANN001
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("boom")
        return MusicalContext(section=SectionLabel.VERSE, rms_energy=0.5, tempo_bpm=120)


class _StubCapture:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def read_window(self):
        return None


@pytest.mark.asyncio
async def test_perception_loop_survives_analysis_exception():
    orch = Orchestrator(ableton_track_id=None, analysis_interval_seconds=0.01)
    orch.analyzer = _FlakyAnalyzer()
    orch.capture = _StubCapture()

    await orch.start()
    try:
        for _ in range(200):
            if orch.analyzer.calls >= 2:
                break
            await asyncio.sleep(0.01)
    finally:
        await orch.stop()

    assert orch.analyzer.calls >= 2, "loop died after the first exception instead of continuing"


def test_note_duration_is_long_for_sustained_input():
    # a held note produces ~0 onsets per beat over the analysis window
    context = MusicalContext(onset_density_per_beat=0.0)
    assert _note_duration_from_context(context) == 2.0


def test_note_duration_is_short_for_rapid_input():
    context = MusicalContext(onset_density_per_beat=4.0)  # fast syllables/notes
    assert _note_duration_from_context(context) == 0.25


def test_note_duration_falls_back_to_default_range_for_moderate_input():
    context = MusicalContext(onset_density_per_beat=1.0)
    assert _note_duration_from_context(context) == 1.0
