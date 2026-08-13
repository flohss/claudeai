"""Ties the individual feature extractors into a single MusicalContext."""

from __future__ import annotations

import numpy as np

from neura_set.config import AudioConfig, DEFAULT_CONFIG
from neura_set.types import MusicalContext, SectionLabel
from neura_set.perception import audio_features as feats
from neura_set.perception.chord_detection import detect_chord
from neura_set.perception.structure_segmentation import segment as segment_structure


class Analyzer:
    """Stateful analyzer: call `analyze(buffer)` on each new audio window
    to get an updated MusicalContext. Keeps a running estimate of the
    global key so it doesn't flicker frame to frame like the chord does.
    """

    def __init__(self, config: AudioConfig = DEFAULT_CONFIG.audio) -> None:
        self.config = config
        self._key_root_pc = 0
        self._key_is_minor = False
        self._key_locked = False

    def analyze(self, y: np.ndarray) -> MusicalContext:
        if len(y) == 0 or np.allclose(y, 0):
            return MusicalContext(tempo_bpm=0.0)

        tempo = feats.estimate_tempo(y, self.config)
        chroma = feats.chroma_vector(y, self.config)
        chord_root, chord_is_minor, chord_conf = detect_chord(chroma)

        if not self._key_locked and chord_conf > 0.6:
            self._key_root_pc, self._key_is_minor = feats.estimate_key(chroma)
            self._key_locked = True

        rms = feats.rms_energy(y, self.config)
        centroid = feats.spectral_centroid(y, self.config)
        onset_density = feats.onset_density_per_beat(y, tempo, self.config)

        section = SectionLabel.UNKNOWN
        try:
            segments = segment_structure(y, self.config)
            if segments:
                section = segments[-1][2]
        except Exception:
            pass

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
