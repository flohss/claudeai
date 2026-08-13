import asyncio

import pytest

from neura_set.orchestrator import Orchestrator
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
