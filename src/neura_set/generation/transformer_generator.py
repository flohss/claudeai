"""Extension point for a real generative model (Music Transformer, MusicGen, ...).

This is deliberately NOT a working model: fine-tuning or hosting a
Transformer is out of scope for this scaffold (no GPU, no training data,
no checkpoint available at build time). What's here is the integration
surface so swapping it in later is a matter of implementing `_load` and
`_sample`, not redesigning the pipeline — `MarkovGenerator` already
implements the same `Generator` interface and is the default in
`orchestrator.py`.

Two concrete integration paths, both slotting into `generate()` below:

1. Magenta-style Music Transformer (self-hosted, PyTorch/TF checkpoint):
   - Tokenize `context` (key, chord, tempo, recent_pitches) into whatever
     event vocabulary the checkpoint expects (e.g. REMI/MIDI-like tokens).
   - Run the model's `.generate()` / sampling loop conditioned on those
     tokens, decode back to NoteEvents.

2. Meta MusicGen (audio-domain, via `transformers`/`audiocraft`):
   - MusicGen generates audio, not MIDI, so it fits better as a "render
     a reference audio phrase" step than direct clip injection; convert
     back to notes only if you add a transcription step (e.g. basic-pitch).

Either way, keep this class's public signature identical to
`generation.base.Generator` so the decision layer never needs to know
which backend produced a Proposal.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from neura_set.generation.base import Generator
from neura_set.types import MusicalContext, NoteEvent


class TransformerGenerator(Generator):
    name = "transformer"

    def __init__(self, checkpoint_path: str | Path | None = None) -> None:
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        self._model = None
        if self.checkpoint_path is not None:
            self._model = self._load(self.checkpoint_path)

    def _load(self, checkpoint_path: Path):  # noqa: ANN201
        raise NotImplementedError(
            "No checkpoint loader wired up yet. Implement this once you have a "
            "fine-tuned Music Transformer / MusicGen checkpoint to load, e.g.:\n"
            "    model = torch.load(checkpoint_path)\n"
            "    model.eval()\n"
            "    return model"
        )

    def generate(
        self,
        context: MusicalContext,
        length_beats: float = 4.0,
        note_duration_beats: float = 0.5,
    ) -> list[NoteEvent]:
        if self._model is None:
            raise NotImplementedError(
                "TransformerGenerator has no loaded model. Pass checkpoint_path=, "
                "implement _load()/this method's sampling loop, or use "
                "MarkovGenerator (generation.markov_generator) which works today."
            )
        raise NotImplementedError("Sampling loop not implemented — see module docstring.")

    def train(self, notes: Sequence[NoteEvent], context: MusicalContext) -> None:
        # Online fine-tuning of a Transformer checkpoint from live playing is
        # expensive and out of scope; retraining should happen offline on a
        # corpus of MIDI, not per-session. Left as a no-op intentionally.
        return None
