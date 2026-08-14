"""Wires perception -> decision -> generation -> action into one async loop.

This is the "main()" of NEURA-SET: every `analysis_interval_seconds` it
pulls the latest audio window, updates the MusicalContext, asks the
DecisionAgent whether it's a good moment to speak up, and if so generates
a proposal, stages it in Ableton (if configured) and pushes it to the web
UI. Accept/reject clicks from the UI route back through `_on_feedback`
into the decision agent (so it learns what's welcome) and the generator
(so a Markov model trains on what the human just played).
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import FastAPI

from neura_set.action.ableton_controller import AbletonController
from neura_set.action.osc_client import AbletonOSCClient
from neura_set.config import DEFAULT_CONFIG, NeuraSetConfig
from neura_set.decision.agent import DecisionAgent
from neura_set.generation.base import Generator
from neura_set.generation.markov_generator import MarkovGenerator
from neura_set.generation.style import apply_style
from neura_set.interface.app import InterfaceServer
from neura_set.perception.analyzer import Analyzer
from neura_set.perception.audio_capture import AudioCapture
from neura_set.types import MusicalContext, Proposal

logger = logging.getLogger("neura_set.orchestrator")

_MIN_NOTE_DURATION_BEATS = 0.25
_MAX_NOTE_DURATION_BEATS = 2.0


def _note_duration_from_context(context: MusicalContext) -> float:
    """How long generated notes should be, from how sparse the human's
    playing was — confirmed live: generation always used a fixed 0.5-beat
    duration regardless of input, so long held/sung notes never came back
    as long notes. `onset_density_per_beat` (attacks per beat) is already
    computed by the perception layer but was never consumed anywhere:
    few onsets per beat (a sustained note) should propose long notes back,
    many onsets (rapid notes/syllables) should propose short ones.
    """
    density = context.onset_density_per_beat
    if density <= 0:
        return _MAX_NOTE_DURATION_BEATS  # no attacks detected at all: one long held tone
    return max(_MIN_NOTE_DURATION_BEATS, min(_MAX_NOTE_DURATION_BEATS, 1.0 / density))


class Orchestrator:
    def __init__(
        self,
        config: NeuraSetConfig = DEFAULT_CONFIG,
        generator: Generator | None = None,
        ableton_track_id: int | None = None,
        style: str = "default",
        analysis_interval_seconds: float = 2.0,
    ) -> None:
        self.config = config
        self.analysis_interval_seconds = analysis_interval_seconds
        self.style = style

        self.capture = AudioCapture(config.audio)
        self.analyzer = Analyzer(config.audio)
        self.decision = DecisionAgent(config.decision)
        self.generator = generator or MarkovGenerator()
        self.interface = InterfaceServer()
        self.interface.on_feedback = self._on_feedback

        self.osc_client: AbletonOSCClient | None = None
        self.ableton: AbletonController | None = None
        if ableton_track_id is not None:
            self.osc_client = AbletonOSCClient(config.osc)
            self.ableton = AbletonController(self.osc_client, ableton_track_id, config.osc)

        self._proposals: dict[str, tuple[Proposal, int | None]] = {}
        self._running = False
        self._loop_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self.capture.start()
        if self.osc_client:
            self.osc_client.start()
        self._loop_task = asyncio.create_task(self._perception_loop())

    async def stop(self) -> None:
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
        self.capture.stop()
        if self.osc_client:
            self.osc_client.stop()

    async def _perception_loop(self) -> None:
        # This runs as a detached background task (see start()): nothing
        # awaits it, so an uncaught exception here would silently end the
        # whole loop forever with no visible error — confirmed live, a
        # single bad tick (e.g. a librosa edge case on real, non-silent
        # audio) killed analysis permanently while the rest of the app kept
        # responding normally. Catch per-tick instead of per-run so one bad
        # analysis doesn't take down the whole session.
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                buffer = self.capture.read_window()
                context = await loop.run_in_executor(None, self.analyzer.analyze, buffer)
                logger.debug(
                    "niveau audio (rms)=%.4f seuil=%.4f tempo=%.0f section=%s",
                    context.rms_energy,
                    self.decision.config.min_rms_energy,
                    context.tempo_bpm,
                    context.section.value,
                )
                if self.decision.should_propose(context):
                    await self._maybe_propose(context)
            except Exception:
                logger.exception("échec de l'analyse audio sur ce cycle, on continue")
            await asyncio.sleep(self.analysis_interval_seconds)

    async def _maybe_propose(self, context: MusicalContext) -> None:
        note_duration_beats = _note_duration_from_context(context)
        notes = self.generator.generate(context, note_duration_beats=note_duration_beats)
        notes = apply_style(notes, self.style)
        if not notes:
            return

        proposal = Proposal(
            id=str(uuid.uuid4()),
            notes=notes,
            context=context,
            generator_name=self.generator.name,
            style=self.style,
        )
        if not self.decision.filter_candidate(proposal):
            return
        self.decision.register_proposal(proposal)

        clip_id = self.ableton.stage_proposal(proposal) if self.ableton else None
        self._proposals[proposal.id] = (proposal, clip_id)

        await self.interface.push_proposal(proposal)
        logger.info(
            "proposed %d notes (%s/%s, section=%s)",
            len(notes), self.generator.name, self.style, context.section.value,
        )

    async def _on_feedback(self, proposal_id: str, accepted: bool) -> None:
        entry = self._proposals.pop(proposal_id, None)
        if entry is None:
            return
        proposal, clip_id = entry
        self.decision.record_feedback(proposal_id, accepted)
        self.generator.train(proposal.notes, proposal.context)
        if self.ableton and clip_id is not None:
            if accepted:
                self.ableton.accept(clip_id)
            else:
                self.ableton.reject(clip_id)


def create_app(orchestrator: Orchestrator) -> FastAPI:
    app = orchestrator.interface.app

    @app.on_event("startup")
    async def _startup() -> None:
        await orchestrator.start()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await orchestrator.stop()

    return app
