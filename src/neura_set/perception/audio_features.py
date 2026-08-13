"""Low-level audio feature extraction built on librosa.

All functions operate on a mono float32 numpy buffer, so they work the same
whether the buffer came from a live soundcard callback or a wav file.
"""

from __future__ import annotations

import numpy as np
import librosa

from neura_set.config import AudioConfig, DEFAULT_CONFIG

# Krumhansl-Kessler key profiles, used to estimate the global key from a
# chroma vector via correlation with each of the 24 rotated profiles.
_MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
_MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)


def estimate_tempo(y: np.ndarray, config: AudioConfig = DEFAULT_CONFIG.audio) -> float:
    """Estimate tempo in BPM using librosa's onset-strength-based tracker."""
    onset_env = librosa.onset.onset_strength(
        y=y, sr=config.sample_rate, hop_length=config.hop_length
    )
    tempo = librosa.feature.rhythm.tempo(
        onset_envelope=onset_env, sr=config.sample_rate, hop_length=config.hop_length
    )
    return float(tempo[0]) if len(tempo) else 0.0


def chroma_vector(y: np.ndarray, config: AudioConfig = DEFAULT_CONFIG.audio) -> np.ndarray:
    """Average chromagram (12-bin pitch class energy) over the buffer."""
    chroma = librosa.feature.chroma_cqt(
        y=y, sr=config.sample_rate, hop_length=config.hop_length
    )
    return chroma.mean(axis=1)


def estimate_key(chroma: np.ndarray) -> tuple[int, bool]:
    """Estimate (root pitch class, is_minor) from a 12-bin chroma vector
    by correlating against all 24 rotations of the Krumhansl-Kessler profiles.
    """
    best_score = -np.inf
    best_root, best_is_minor = 0, False
    for root in range(12):
        for profile, is_minor in ((_MAJOR_PROFILE, False), (_MINOR_PROFILE, True)):
            rotated = np.roll(profile, root)
            score = float(np.corrcoef(chroma, rotated)[0, 1])
            if score > best_score:
                best_score, best_root, best_is_minor = score, root, is_minor
    return best_root, best_is_minor


def rms_energy(y: np.ndarray, config: AudioConfig = DEFAULT_CONFIG.audio) -> float:
    rms = librosa.feature.rms(y=y, hop_length=config.hop_length)
    return float(rms.mean())


def spectral_centroid(y: np.ndarray, config: AudioConfig = DEFAULT_CONFIG.audio) -> float:
    centroid = librosa.feature.spectral_centroid(
        y=y, sr=config.sample_rate, hop_length=config.hop_length
    )
    return float(centroid.mean())


def onset_density_per_beat(
    y: np.ndarray, tempo_bpm: float, config: AudioConfig = DEFAULT_CONFIG.audio
) -> float:
    """Average number of onsets per beat over the buffer."""
    onsets = librosa.onset.onset_detect(
        y=y, sr=config.sample_rate, hop_length=config.hop_length, units="time"
    )
    duration_s = len(y) / config.sample_rate
    if duration_s <= 0 or tempo_bpm <= 0:
        return 0.0
    n_beats = duration_s * tempo_bpm / 60.0
    return len(onsets) / n_beats if n_beats > 0 else 0.0
