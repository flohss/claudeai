"""Named style presets applied as a post-processing pass on generated notes.

This stands in for the "style embeddings" described in the project brief.
A real style-transfer model would condition generation directly (e.g. a
learned embedding fed into the Transformer); until one is trained, these
presets reshape any generator's output — density, register, velocity,
swing — which is enough to make a `techno` proposal feel different from
an `ambient` one without needing labeled training data.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from neura_set.types import NoteEvent


@dataclass(frozen=True)
class StyleParams:
    density: float = 1.0  # fraction of notes kept (thinning for sparse styles)
    register_offset: int = 0  # semitones
    velocity_scale: float = 1.0
    swing: float = 0.0  # 0..0.5, delays every other 8th note
    legato: float = 1.0  # duration multiplier


STYLES: dict[str, StyleParams] = {
    "default": StyleParams(),
    "techno": StyleParams(density=1.0, velocity_scale=1.1, swing=0.0, legato=0.9),
    "ambient": StyleParams(density=0.5, register_offset=12, velocity_scale=0.6, legato=2.5),
    "jazz": StyleParams(density=0.85, velocity_scale=0.95, swing=0.33, legato=0.85),
    "lofi": StyleParams(density=0.7, register_offset=-12, velocity_scale=0.75, swing=0.2, legato=1.1),
}


def apply_style(notes: list[NoteEvent], style_name: str) -> list[NoteEvent]:
    params = STYLES.get(style_name, STYLES["default"])
    out: list[NoteEvent] = []
    for i, note in enumerate(notes):
        if params.density < 1.0 and random.random() > params.density:
            continue
        start = note.start_beat
        if params.swing and i % 2 == 1:
            start += params.swing * 0.5
        pitch = max(0, min(127, note.pitch + params.register_offset))
        velocity = max(1, min(127, int(note.velocity * params.velocity_scale)))
        duration = max(0.01, note.duration_beats * params.legato)
        out.append(
            NoteEvent(
                pitch=pitch, start_beat=start, duration_beats=duration, velocity=velocity
            )
        )
    return out
