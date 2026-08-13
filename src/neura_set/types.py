"""Shared data types passed between NEURA-SET's four layers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class SectionLabel(str, Enum):
    INTRO = "intro"
    BUILD = "build"
    DROP = "drop"
    BREAKDOWN = "breakdown"
    VERSE = "verse"
    CHORUS = "chorus"
    OUTRO = "outro"
    UNKNOWN = "unknown"


@dataclass
class NoteEvent:
    """A single MIDI-like note event, in beats relative to clip start."""

    pitch: int  # MIDI note number, 0-127
    start_beat: float
    duration_beats: float
    velocity: int = 100  # 1-127

    def __post_init__(self) -> None:
        if not 0 <= self.pitch <= 127:
            raise ValueError(f"pitch out of MIDI range: {self.pitch}")
        if not 1 <= self.velocity <= 127:
            raise ValueError(f"velocity out of MIDI range: {self.velocity}")
        if self.duration_beats <= 0:
            raise ValueError("duration_beats must be positive")


@dataclass
class MusicalContext:
    """Snapshot of what the perception layer currently hears."""

    timestamp: float = field(default_factory=time.time)
    tempo_bpm: float = 120.0
    key_root_pc: int = 0  # pitch class 0-11 (0=C)
    key_is_minor: bool = False
    chord_root_pc: int | None = None
    chord_is_minor: bool | None = None
    rms_energy: float = 0.0
    spectral_centroid_hz: float = 0.0
    onset_density_per_beat: float = 0.0
    section: SectionLabel = SectionLabel.UNKNOWN
    recent_pitches: list[int] = field(default_factory=list)


@dataclass
class Proposal:
    """A generated musical idea awaiting human validation."""

    id: str
    notes: list[NoteEvent]
    context: MusicalContext
    generator_name: str
    style: str = "default"
    created_at: float = field(default_factory=time.time)
