"""Shared audio cleanup helpers for record_sample.py and clone_voice.py."""
import numpy as np


def trim_silence(audio: np.ndarray, samplerate: int, threshold_db: float = -40.0, pad_ms: int = 150) -> np.ndarray:
    """Trim leading/trailing silence based on an amplitude threshold, keeping a small padding."""
    mono = audio.mean(axis=1) if audio.ndim > 1 else audio
    threshold = 10 ** (threshold_db / 20.0)
    above = np.where(np.abs(mono) > threshold)[0]
    if above.size == 0:
        return audio
    pad = int(samplerate * pad_ms / 1000)
    start = max(0, above[0] - pad)
    end = min(len(mono), above[-1] + pad)
    return audio[start:end]


def normalize_loudness(audio: np.ndarray, target_dbfs: float = -20.0) -> np.ndarray:
    """RMS-normalize to a target loudness, with a peak safety limiter."""
    if audio.size == 0:
        return audio
    rms = np.sqrt(np.mean(np.square(audio)))
    if rms < 1e-9:
        return audio
    gain = (10 ** (target_dbfs / 20.0)) / rms
    normalized = audio * gain
    peak = np.max(np.abs(normalized))
    if peak > 0.99:
        normalized = normalized * (0.99 / peak)
    return normalized.astype(np.float32)
