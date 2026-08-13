"""Real-time chord recognition via chroma template matching.

This is a lightweight, dependency-free stand-in for the CNN chord
recognizer mentioned in the project brief. It is accurate enough for
triads over a clean mix and runs in well under a millisecond, which
matters for a real-time loop. Swap in a trained CNN (e.g. over CQT
frames, à la Korzeniowski & Widmer) by implementing the same
`detect_chord(chroma) -> (root_pc, is_minor, confidence)` signature.
"""

from __future__ import annotations

import numpy as np

_TRIAD_INTERVALS = {
    "major": (0, 4, 7),
    "minor": (0, 3, 7),
}


def _triad_template(root: int, quality: str) -> np.ndarray:
    template = np.zeros(12)
    for interval in _TRIAD_INTERVALS[quality]:
        template[(root + interval) % 12] = 1.0
    return template


_TEMPLATES: list[tuple[int, bool, np.ndarray]] = [
    (root, quality == "minor", _triad_template(root, quality))
    for root in range(12)
    for quality in ("major", "minor")
]


def detect_chord(chroma: np.ndarray) -> tuple[int, bool, float]:
    """Return (root_pitch_class, is_minor, confidence in [0, 1]).

    `chroma` is a 12-bin pitch-class energy vector (e.g. from
    ``audio_features.chroma_vector``).
    """
    if np.allclose(chroma, 0):
        return 0, False, 0.0

    norm_chroma = chroma / (np.linalg.norm(chroma) + 1e-9)
    best_score = -np.inf
    best_root, best_is_minor = 0, False
    for root, is_minor, template in _TEMPLATES:
        norm_template = template / np.linalg.norm(template)
        score = float(np.dot(norm_chroma, norm_template))
        if score > best_score:
            best_score, best_root, best_is_minor = score, root, is_minor

    confidence = max(0.0, min(1.0, best_score))
    return best_root, best_is_minor, confidence
