"""Ties the individual feature extractors into a single MusicalContext.

Each analyze() call only sees a 4-second rolling window, which is too
short and too self-referential for raw tempo/section estimates to be
usable live: a fresh tempo/self-similarity computation on every tick
flickers wildly (confirmed live: 140 -> 115 -> 148 -> 112 BPM and
intro/drop/verse/chorus flipping every 2 seconds on nothing but spoken
voice). Analyzer smooths across ticks instead of trusting each one in
isolation — see _EMA and _SectionDebouncer below.
"""

from __future__ import annotations

from collections import deque

import numpy as np

from neura_set.config import AudioConfig, DEFAULT_CONFIG
from neura_set.types import MusicalContext, SectionLabel
from neura_set.perception import audio_features as feats
from neura_set.perception.chord_detection import detect_chord
from neura_set.perception.structure_segmentation import label_section


class _EMA:
    """Exponential moving average. `alpha` is the weight given to each new
    sample — smaller means smoother/slower to react, larger means closer
    to the raw signal."""

    def __init__(self, alpha: float) -> None:
        self.alpha = alpha
        self.value: float | None = None

    def update(self, x: float) -> float:
        self.value = x if self.value is None else (1 - self.alpha) * self.value + self.alpha * x
        return self.value


class _SectionDebouncer:
    """Only changes the reported section once the same candidate has come
    up `confirm_ticks` times in a row, instead of relaying every tick's
    (noisy) instantaneous guess."""

    def __init__(self, confirm_ticks: int = 3) -> None:
        self._history: deque[SectionLabel] = deque(maxlen=confirm_ticks)
        self.active = SectionLabel.UNKNOWN

    def update(self, candidate: SectionLabel) -> SectionLabel:
        self._history.append(candidate)
        if len(self._history) == self._history.maxlen and len(set(self._history)) == 1:
            self.active = candidate
        return self.active


class Analyzer:
    """Stateful analyzer: call `analyze(buffer)` on each new audio window
    to get an updated MusicalContext. Keeps a running estimate of the
    global key so it doesn't flicker frame to frame like the chord does,
    and smooths tempo/section the same way (see module docstring).
    """

    def __init__(
        self,
        config: AudioConfig = DEFAULT_CONFIG.audio,
        tempo_smoothing: float = 0.3,
        energy_baseline_smoothing: float = 0.08,
        section_confirm_ticks: int = 3,
    ) -> None:
        self.config = config
        self._key_root_pc = 0
        self._key_is_minor = False
        self._key_locked = False
        self._tempo_ema = _EMA(tempo_smoothing)
        # Slow-moving "recent normal level" baseline: comparing each tick's
        # RMS against this (instead of a whole-track average, which a live
        # stream doesn't have) is what relative_energy/label_section needs
        # to tell a quiet moment from a loud one.
        self._energy_baseline = _EMA(energy_baseline_smoothing)
        self._section_debouncer = _SectionDebouncer(section_confirm_ticks)

    def analyze(self, y: np.ndarray) -> MusicalContext:
        if len(y) == 0 or np.allclose(y, 0):
            return MusicalContext(tempo_bpm=0.0)

        raw_tempo = feats.estimate_tempo(y, self.config)
        tempo = self._tempo_ema.update(raw_tempo) if raw_tempo > 0 else (self._tempo_ema.value or 0.0)

        chroma = feats.chroma_vector(y, self.config)
        chord_root, chord_is_minor, chord_conf = detect_chord(chroma)

        if not self._key_locked and chord_conf > 0.6:
            self._key_root_pc, self._key_is_minor = feats.estimate_key(chroma)
            self._key_locked = True

        rms = feats.rms_energy(y, self.config)
        centroid = feats.spectral_centroid(y, self.config)
        onset_density = feats.onset_density_per_beat(y, tempo, self.config)

        baseline = self._energy_baseline.update(rms) if rms > 0 else (self._energy_baseline.value or rms)
        relative_energy = rms / baseline if baseline and baseline > 0 else 1.0
        section = self._section_debouncer.update(label_section(relative_energy))

        return MusicalContext(
            tempo_bpm=tempo,
            key_root_pc=self._key_root_pc,
            key_is_minor=self._key_is_minor,
            chord_root_pc=chord_root if chord_conf > 0.4 else None,
            chord_is_minor=chord_is_minor if chord_conf > 0.4 else None,
            rms_energy=rms,
            spectral_centroid_hz=centroid,
            onset_density_per_beat=onset_density,
            section=section,
        )

    def reset_key_lock(self) -> None:
        """Call when starting analysis on a new song."""
        self._key_locked = False
