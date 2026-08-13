"""Song-structure segmentation via self-similarity novelty detection.

Implements the standard Foote (2000) novelty-curve approach: build a
self-similarity matrix over chroma+RMS frames, correlate a checkerboard
kernel along the diagonal to get a novelty curve, and pick its peaks as
section boundaries. Sections are then coarsely labeled by relative
energy, which is a useful proxy in electronic music (low energy =
breakdown/intro, high energy = drop/chorus) without needing a trained
classifier.
"""

from __future__ import annotations

import numpy as np
import librosa

from neura_set.config import AudioConfig, DEFAULT_CONFIG
from neura_set.types import SectionLabel


def _checkerboard_kernel(size: int) -> np.ndarray:
    axis = np.arange(size) - size // 2
    kernel = np.outer(np.sign(axis + 0.5), np.sign(axis + 0.5))
    gaussian = np.outer(
        np.exp(-0.5 * (axis / (size / 4)) ** 2),
        np.exp(-0.5 * (axis / (size / 4)) ** 2),
    )
    return kernel * gaussian


def novelty_curve(
    y: np.ndarray, config: AudioConfig = DEFAULT_CONFIG.audio, kernel_size: int = 32
) -> np.ndarray:
    chroma = librosa.feature.chroma_cqt(
        y=y, sr=config.sample_rate, hop_length=config.hop_length
    )
    rms = librosa.feature.rms(y=y, hop_length=config.hop_length)
    features = np.vstack([chroma, rms])
    features = features / (np.linalg.norm(features, axis=0, keepdims=True) + 1e-9)

    sim = features.T @ features  # self-similarity matrix
    n = sim.shape[0]
    kernel = _checkerboard_kernel(min(kernel_size, n))
    k = kernel.shape[0]
    half = k // 2

    padded = np.pad(sim, half, mode="edge")
    novelty = np.zeros(n)
    for i in range(n):
        window = padded[i : i + k, i : i + k]
        novelty[i] = float(np.sum(window * kernel))

    novelty -= novelty.min()
    if novelty.max() > 0:
        novelty /= novelty.max()
    return novelty


def find_boundaries(
    novelty: np.ndarray, min_distance_frames: int = 40, threshold: float = 0.3
) -> list[int]:
    """Peak-pick the novelty curve into a sorted list of frame indices."""
    peaks: list[int] = []
    for i in range(1, len(novelty) - 1):
        if novelty[i] < threshold:
            continue
        if novelty[i] >= novelty[i - 1] and novelty[i] >= novelty[i + 1]:
            if not peaks or i - peaks[-1] >= min_distance_frames:
                peaks.append(i)
    return peaks


def label_section(relative_energy: float) -> SectionLabel:
    """Coarse energy-based label. relative_energy is this section's mean
    RMS divided by the track's overall mean RMS."""
    if relative_energy < 0.4:
        return SectionLabel.INTRO
    if relative_energy < 0.7:
        return SectionLabel.BREAKDOWN
    if relative_energy < 1.1:
        return SectionLabel.VERSE
    if relative_energy < 1.4:
        return SectionLabel.CHORUS
    return SectionLabel.DROP


def segment(
    y: np.ndarray, config: AudioConfig = DEFAULT_CONFIG.audio
) -> list[tuple[float, float, SectionLabel]]:
    """Return a list of (start_seconds, end_seconds, SectionLabel)."""
    if len(y) < config.hop_length * 8:
        return [(0.0, len(y) / config.sample_rate, SectionLabel.UNKNOWN)]

    novelty = novelty_curve(y, config)
    boundary_frames = [0, *find_boundaries(novelty), len(novelty) - 1]
    boundary_frames = sorted(set(boundary_frames))

    rms = librosa.feature.rms(y=y, hop_length=config.hop_length)[0]
    overall_mean = float(rms.mean()) or 1e-9

    segments: list[tuple[float, float, SectionLabel]] = []
    for start_f, end_f in zip(boundary_frames[:-1], boundary_frames[1:]):
        start_t = librosa.frames_to_time(
            start_f, sr=config.sample_rate, hop_length=config.hop_length
        )
        end_t = librosa.frames_to_time(
            end_f, sr=config.sample_rate, hop_length=config.hop_length
        )
        seg_energy = float(rms[start_f:end_f].mean()) if end_f > start_f else 0.0
        segments.append((float(start_t), float(end_t), label_section(seg_energy / overall_mean)))
    return segments
