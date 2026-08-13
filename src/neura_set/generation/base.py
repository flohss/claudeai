"""Common interface every music generator implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from neura_set.types import MusicalContext, NoteEvent


class Generator(ABC):
    """A Generator turns a MusicalContext into a short note continuation.

    Implementations range from the built-in rule/Markov generator to a
    wrapped pretrained Transformer (see transformer_generator.py).
    """

    name: str = "base"

    @abstractmethod
    def generate(
        self,
        context: MusicalContext,
        length_beats: float = 4.0,
        note_duration_beats: float = 0.5,
    ) -> list[NoteEvent]:
        """Produce a note sequence consistent with `context`."""
        raise NotImplementedError

    def train(self, notes: Sequence[NoteEvent], context: MusicalContext) -> None:
        """Optional: adapt to what the human just played. No-op by default."""
        return None
